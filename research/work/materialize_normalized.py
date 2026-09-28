"""Materialize compact normalized Parquet shards for the official data.

Raw TSVs stay untouched. Each shard contains IDs, country, and deterministic
lowercase alphanumeric name/address keys used by the blocking stage.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import duckdb


def lit(value: Path | str) -> str:
    """Render a value as a SQL string literal, escaping embedded quotes.

    Used for every path and setting that is interpolated into SQL, so a value
    containing a quote cannot break out of the literal.
    """
    return "'" + str(value).replace("'", "''") + "'"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--memory-limit", default="1500MB")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    # NOTE: with_suffix() replaces the final extension, so `--out data/normalized.v2`
    # would yield `data/normalized.tmp` and collide with a sibling run. Append instead.
    spill = args.out.with_name(args.out.name + ".tmp")
    spill.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(":memory:")
    con.execute("SET threads=?", [int(args.threads)])
    con.execute(f"SET memory_limit={lit(args.memory_limit)}")
    con.execute(f"SET temp_directory={lit(spill)}")
    con.execute("SET preserve_insertion_order=false")
    con.execute("SET enable_progress_bar=false")
    counts: dict[str, int] = {}
    started = time.perf_counter()
    for split, folder in (("train", "train"), ("test", "test")):
        for source in (1, 2, 3):
            raw = args.dataset / folder / f"{split}_source{source}.tsv"
            out = args.out / f"{split}_s{source}.parquet"
            # Build the shard under a staging name, verify it, then publish it with
            # os.replace (atomic on the same filesystem). The previous good shard is
            # never unlinked up front, so an interrupt leaves either the old shard
            # or the new one -- never a missing/truncated file advertised by a stale
            # manifest.json.
            staging = out.with_name(out.name + f".staging.{os.getpid()}")
            if staging.exists():
                staging.unlink()
            sql = f"""
            COPY (
              SELECT entity_id, country,
                lower(trim(regexp_replace(regexp_replace(coalesce(business_name, ''), '[^[:alnum:]]+', ' ', 'g'), '\\s+', ' ', 'g'))) AS n_name,
                lower(trim(regexp_replace(regexp_replace(coalesce(business_address, ''), '[^[:alnum:]]+', ' ', 'g'), '\\s+', ' ', 'g'))) AS n_addr
              FROM read_csv({lit(raw)}, delim='\\t', header=true,
                columns={{'entity_id':'VARCHAR','business_name':'VARCHAR','business_address':'VARCHAR','country':'VARCHAR'}},
                ignore_errors=false)
            ) TO {lit(staging)} (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)
            """
            con.execute(sql)
            counted = con.execute(f"SELECT count(*) FROM read_parquet({lit(staging)})").fetchone()
            if counted is None or counted[0] is None:
                raise RuntimeError(f"could not count rows of staging shard {staging}")
            rows = int(counted[0])
            os.replace(staging, out)
            counts[out.stem] = rows
            print(json.dumps({"shard": out.name, "rows": counts[out.stem]}), flush=True)
    meta = {
        "dataset": str(args.dataset),
        "out": str(args.out),
        "counts": counts,
        "threads": args.threads,
        "memory_limit": args.memory_limit,
        "elapsed_seconds": time.perf_counter() - started,
        "normalization": "lowercase; replace non-alphanumeric runs with spaces; collapse whitespace",
    }
    (args.out / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))
    con.close()


if __name__ == "__main__":
    main()
