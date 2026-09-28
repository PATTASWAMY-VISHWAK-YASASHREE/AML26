"""Measure candidate volume and per-S1 load for exact blocking channels."""
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
    p.add_argument("--normalized", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--memory-limit", default="1200MB")
    args = p.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.parent / f"volume_tmp_{os.getpid()}"
    if tmp.exists():
        # Stale spill files from a previous aborted run can be silently mixed in.
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(":memory:")
    con.execute("SET threads=?", [int(args.threads)])
    con.execute(f"SET memory_limit={lit(args.memory_limit)}")
    con.execute(f"SET temp_directory={lit(tmp)}")
    con.execute("SET preserve_insertion_order=false")
    for source in (1, 2, 3):
        con.execute(f"CREATE VIEW train_s{source} AS SELECT * FROM read_parquet({lit(args.normalized / f'train_s{source}.parquet')})")
    # Total S1 rows: `covered_s1` alone cannot express how much of S1 a channel
    # actually covers.
    s1_total = int(con.execute("SELECT count(*) FROM train_s1").fetchone()[0])
    predicates = {
        "name_prefix_3": "left(s.n_name, 3) = left(t.n_name, 3) AND s.n_name <> ''",
        "name_prefix_5": "left(s.n_name, 5) = left(t.n_name, 5) AND s.n_name <> ''",
        "name_suffix_5": "right(s.n_name, 5) = right(t.n_name, 5) AND s.n_name <> ''",
        "address_prefix_5": "left(s.n_addr, 5) = left(t.n_addr, 5) AND s.n_addr <> ''",
        "address_prefix_8": "left(s.n_addr, 8) = left(t.n_addr, 8) AND s.n_addr <> ''",
        "name3_addr5": "left(s.n_name, 3) = left(t.n_name, 3) AND left(s.n_addr, 5) = left(t.n_addr, 5) AND s.n_name <> '' AND s.n_addr <> ''",
    }
    out: dict[str, object] = {}
    start = time.perf_counter()
    for target_source in (2, 3):
        out[f"S{target_source}"] = {}
        # Projected keys are built ONCE per target: previously each of the six
        # queries re-scanned train_s1 and the target shard and recomputed the
        # left()/right() projections.
        con.execute("CREATE OR REPLACE TEMP TABLE s_keys AS SELECT entity_id, n_name, n_addr FROM train_s1")
        con.execute(f"CREATE OR REPLACE TEMP TABLE t_keys AS SELECT entity_id, n_name, n_addr FROM train_s{target_source}")
        for name, predicate in predicates.items():
            sql = f"""
            WITH per_source AS (
              SELECT s.entity_id, count(*) AS c
              FROM s_keys s JOIN t_keys t ON {predicate}
              GROUP BY s.entity_id
            )
            SELECT coalesce(sum(c),0), count(*), coalesce(avg(c),0),
                   coalesce(approx_quantile(c, 0.5),0), coalesce(approx_quantile(c, 0.9),0),
                   coalesce(approx_quantile(c, 0.99),0), coalesce(max(c),0)
            FROM per_source
            """
            row = con.execute(sql).fetchone()
            covered = int(row[1])
            out[f"S{target_source}"][name] = {
                "candidate_pairs": int(row[0]), "covered_s1": covered,
                "total_s1_rows": s1_total,
                "s1_coverage_ratio": covered / s1_total if s1_total else None,
                "mean_per_covered_s1": float(row[2]), "p50": float(row[3]),
                "p90": float(row[4]), "p99": float(row[5]), "max": float(row[6]),
            }
    out["elapsed_seconds"] = time.perf_counter() - start
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, sort_keys=True))
    con.close()
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
