"""Regression: changing the config must not reuse stale per-channel files.

The per-channel candidate files are an optimisation, and an optimisation that
can silently return results from a different configuration is worse than no
optimisation. This reproduces the exact failure: a run is killed part-way
through stage_candidates, leaving channel files behind, and the next run uses a
different max_token_df / max_candidates. The final candidate set must be built
entirely from the NEW configuration.
"""
from __future__ import annotations

import random
import sys
import tempfile
from pathlib import Path

import duckdb

import er_pipeline as P

HDR = "entity_id\tbusiness_name\tbusiness_address\tcountry\n"


def build(ds: Path) -> None:
    rng = random.Random(9)
    names = ["acme cafe", "globex mart", "initech works", "soylent clinic",
             "umbrella depot", "stark labs"]
    for split in ("train", "test"):
        (ds / split).mkdir(parents=True, exist_ok=True)
        for src, n in ((1, 200), (2, 500), (3, 500)):
            rows = [HDR]
            for i in range(n):
                rows.append(f"S{src}-{i:05d}\t{rng.choice(names)}\t"
                            f"{rng.randint(1, 30)} main st\tUS\n")
            (ds / split / f"{split}_source{src}.tsv").write_text("".join(rows), encoding="utf-8")
    (ds / "train" / "train_ground_truth.tsv").write_text(
        "source1_entity_id\tmatched_entity_ids\nS1-00000\t\n", encoding="utf-8")


def candidates(con, norm: Path, split: str) -> set:
    out = norm / f"{split}_cand.parquet"
    return set(con.execute(
        f"SELECT sid, tid, prio FROM read_parquet({P.lit(out)})").fetchall())


def run_stage(con, norm: Path, ds: Path, *, max_token_df: int, cap: int) -> set:
    """Run just the candidate stage under a given config, then invalidate it."""
    P.CFG.update(max_token_df=max_token_df, max_candidates=cap)
    paths = P.find_dataset_files(ds)
    fp = P.source_fingerprint(paths)
    P.stage_normalize(con, paths, norm, fp)
    P.stage_tokens(con, norm, fp)
    for split in ("train", "test"):
        out = norm / f"{split}_cand.parquet"
        out.unlink(missing_ok=True)
        out.with_name(out.name + ".meta.json").unlink(missing_ok=True)
        P.stage_candidates(con, norm, split, out, fp)
    got = candidates(con, norm, "train")
    # Simulate an interrupted run: drop only the merged output, as a crash
    # between the merge and mark_cached would.
    for split in ("train", "test"):
        for p in norm.glob(f"{split}_cand.parquet*"):
            p.unlink(missing_ok=True)
    return got


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="chan_stale_"))
    ds = base / "dataset"
    work = base / "w"
    norm = work / "er_work" / "norm"
    norm.mkdir(parents=True, exist_ok=True)
    build(ds)
    con = P.connect(work / "er_work" / "er.duckdb", work / "er_work" / "tmp")
    failures = []
    try:
        # Config A, then a *different* config B. If channel files are reused
        # across configs, B silently inherits A's token-channel candidates.
        a = run_stage(con, norm, ds, max_token_df=5000, cap=30)
        b = run_stage(con, norm, ds, max_token_df=500, cap=12)
        print(f"  config A (df=5000, cap=30): {len(a)} train pairs")
        print(f"  config B (df=500,  cap=12): {len(b)} train pairs")

        # Reference: build config B in a pristine directory. Nothing may be
        # reused, so this must equal B exactly.
        clean = base / "clean"
        cnorm = clean / "er_work" / "norm"
        cnorm.mkdir(parents=True, exist_ok=True)
        P.CFG.update(max_token_df=500, max_candidates=12)
        paths = P.find_dataset_files(ds)
        fp = P.source_fingerprint(paths)
        P.stage_normalize(con, paths, cnorm, fp)
        P.stage_tokens(con, cnorm, fp)
        P.stage_candidates(con, cnorm, "train", cnorm / "train_cand.parquet", fp)
        P.stage_candidates(con, cnorm, "test", cnorm / "test_cand.parquet", fp)
        ref = set(con.execute(
            f"SELECT sid, tid, prio FROM read_parquet({P.lit(cnorm / 'train_cand.parquet')})"
        ).fetchall())
        print(f"  pristine rebuild of B      : {len(ref)} train pairs")

        if b == ref:
            print("  PASS reused-after-crash run matches a pristine rebuild")
        else:
            print("  FAIL reused run differs from a pristine rebuild "
                  f"(missing {len(ref - b)}, extra {len(b - ref)})")
            failures.append("stale channel files contaminated the result")

        if a == b:
            print("  WARNING configs A and B produced identical sets - this test "
                  "data is too uniform to detect reuse; treat the PASS above as "
                  "weak evidence")
        else:
            print("  PASS the two configs really do differ, so the check is meaningful")

        leftovers = sorted(p.name for p in norm.glob("*_cand_*_ch*.parquet"))
        if leftovers:
            print(f"  FAIL leftover channel files: {leftovers}")
            failures.append("channel files not cleaned up")
        else:
            print("  PASS no leftover channel files")
    finally:
        con.close()
    if failures:
        raise SystemExit("FAILURES: " + "; ".join(failures))
    print("\nper-channel files are correctly fingerprinted")
    return 0


if __name__ == "__main__":
    sys.exit(main())

