"""Explode the official training labels into a compact Parquet edge table."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from pathlib import Path

import duckdb


def lit(path: Path | str) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--memory-limit", default="1200MB")
    args = p.parse_args()

    # Safety: refuse to write anywhere that would clobber the official dataset.
    # --out is user-supplied and the ground-truth TSV is the single most
    # irreplaceable file; pointing --out at it would destroy the dataset.
    out_path = args.out.resolve()
    dataset_root = args.dataset.resolve()
    gt_path = (dataset_root / "train" / "train_ground_truth.tsv").resolve()
    if out_path == gt_path:
        raise SystemExit(f"refusing to run: --out {out_path} is the official ground-truth TSV")
    try:
        out_path.relative_to(dataset_root)
    except ValueError:
        pass
    else:
        raise SystemExit(
            f"refusing to run: --out {out_path} is inside the official dataset directory {dataset_root}"
        )
    if out_path.suffix.lower() == ".tsv":
        raise SystemExit(f"refusing to run: --out {out_path} looks like a raw TSV; use a .parquet destination")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Run-scoped spill directory: concurrent runs must not share one, and it is
    # removed on every exit path.
    tmp = out_path.parent / f"links_tmp_{os.getpid()}"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    # Publish through a staging file so the previous good artifact survives any
    # failure between "start reading inputs" and "artifact is complete".
    staging = out_path.with_name(out_path.name + f".staging.{os.getpid()}")
    if staging.exists():
        staging.unlink()
    try:
        con = duckdb.connect(":memory:")
        con.execute("SET threads=?", [int(args.threads)])
        con.execute(f"SET memory_limit={lit(args.memory_limit)}")
        con.execute(f"SET temp_directory={lit(tmp)}")
        con.execute("SET preserve_insertion_order=false")
        gt = lit(gt_path)
        start = time.perf_counter()
        con.execute(f"""
          COPY (
            SELECT source1_entity_id, u.target_id
            FROM read_csv({gt}, delim='\\t', header=true,
              columns={{'source1_entity_id':'VARCHAR','matched_entity_ids':'VARCHAR'}}) AS r,
              UNNEST(string_split(r.matched_entity_ids, ',')) AS u(target_id)
            WHERE r.matched_entity_ids IS NOT NULL AND r.matched_entity_ids <> ''
          ) TO {lit(staging)} (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)
        """)
        counted = con.execute(f"SELECT count(*) FROM read_parquet({lit(staging)})").fetchone()
        if counted is None or counted[0] is None:
            raise RuntimeError(f"could not count rows of staging file {staging}")
        count = int(counted[0])
        # Verify before publishing: the destination must be complete and readable.
        if count <= 0:
            raise RuntimeError("refusing to publish an empty edge table; check the ground-truth path")
        os.replace(staging, out_path)
        meta = {"rows": count, "elapsed_seconds": time.perf_counter() - start, "path": str(out_path)}
        out_path.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(meta, indent=2))
        con.close()
    finally:
        if staging.exists():
            staging.unlink()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
