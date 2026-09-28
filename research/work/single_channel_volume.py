"""Measure candidate volume for a single exact blocking channel.

Single-channel mode avoids retaining several large hash aggregations at once on
a 7.7 GB host. Results are written after each channel.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from contextlib import closing
from pathlib import Path

import duckdb


def lit(path: Path | str) -> str:
    return "'" + str(path).replace("'", "''") + "'"


PREDICATES = {
    "name_prefix_3": "left(s.n_name, 3) = left(t.n_name, 3) AND s.n_name <> ''",
    "name_prefix_5": "left(s.n_name, 5) = left(t.n_name, 5) AND s.n_name <> ''",
    "name_suffix_5": "right(s.n_name, 5) = right(t.n_name, 5) AND s.n_name <> ''",
    "address_prefix_5": "left(s.n_addr, 5) = left(t.n_addr, 5) AND s.n_addr <> ''",
    "address_prefix_8": "left(s.n_addr, 8) = left(t.n_addr, 8) AND s.n_addr <> ''",
    "name3_addr5": "left(s.n_name, 3) = left(t.n_name, 3) AND left(s.n_addr, 5) = left(t.n_addr, 5) AND s.n_name <> '' AND s.n_addr <> ''",
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--normalized", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--target", type=int, choices=(2, 3), required=True)
    p.add_argument("--channel", choices=sorted(PREDICATES), required=True)
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--memory-limit", default="900MB")
    args = p.parse_args()
    if args.threads < 1:
        p.error(f"--threads must be >= 1, got {args.threads}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Deterministic per (target, channel) dir: clear stale spill files from a
    # previously aborted run before reusing it.
    tmp = args.out.parent / f"volume_{args.target}_{args.channel}_tmp"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    with closing(duckdb.connect(":memory:")) as con:
        con.execute("SET threads=?", [int(args.threads)])
        con.execute(f"SET memory_limit={lit(args.memory_limit)}")
        con.execute(f"SET temp_directory={lit(tmp)}")
        con.execute("SET preserve_insertion_order=false")
        for source in (1, args.target):
            con.execute(f"CREATE VIEW train_s{source} AS SELECT * FROM read_parquet({lit(args.normalized / f'train_s{source}.parquet')})")
        predicate = PREDICATES[args.channel]
        start = time.perf_counter()
        sql = f"""
        WITH per_source AS (
          SELECT s.entity_id, count(*) AS c
          FROM train_s1 s JOIN train_s{args.target} t ON {predicate}
          GROUP BY s.entity_id
        )
        SELECT coalesce(sum(c),0), count(*), coalesce(avg(c),0),
               coalesce(approx_quantile(c, 0.5),0), coalesce(approx_quantile(c, 0.9),0),
               coalesce(approx_quantile(c, 0.99),0), coalesce(max(c),0)
        FROM per_source
        """
        row = con.execute(sql).fetchone()
        result = {
            "target": args.target, "channel": args.channel,
            # count(*) not count(t.entity_id): the latter undercounts if the
            # target entity_id can be NULL.
            "candidate_pairs": int(row[0]), "covered_s1": int(row[1]),
            "mean_per_covered_s1": float(row[2]), "p50": float(row[3]),
            "p90": float(row[4]), "p99": float(row[5]), "max": float(row[6]),
            "elapsed_seconds": time.perf_counter() - start,
        }
    # Write via a sibling temp file + os.replace so a crash cannot leave
    # truncated JSON behind.
    staging = args.out.with_name(args.out.name + f".tmp{os.getpid()}")
    staging.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(staging, args.out)
    shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
