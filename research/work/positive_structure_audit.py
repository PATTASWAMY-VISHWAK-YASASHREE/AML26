"""Aggregate structural audit of positive training links.

Prints only counts/distributions, never raw business text or IDs.
"""
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


def scalar(con, sql: str):
    return con.execute(sql).fetchone()[0]


def rate(con, sql: str) -> float | None:
    """NULL-safe rate: avg() over an empty set returns NULL, not 0.0.

    float(None) raises TypeError and would kill the whole audit after the
    expensive joins, so an undefined rate is surfaced as None.
    """
    value = scalar(con, sql)
    return None if value is None else float(value)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--normalized", type=Path, required=True)
    p.add_argument("--links", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--memory-limit", default="900MB")
    args = p.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    spill = args.out.parent / f"structure_tmp_{os.getpid()}"
    if spill.exists():
        shutil.rmtree(spill, ignore_errors=True)
    spill.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(":memory:")
    con.execute("SET threads=?", [int(args.threads)])
    con.execute(f"SET memory_limit={lit(args.memory_limit)}")
    con.execute(f"SET temp_directory={lit(spill)}")
    con.execute("SET preserve_insertion_order=false")
    for source in (1, 2, 3):
        con.execute(f"CREATE VIEW train_s{source} AS SELECT * FROM read_parquet({lit(args.normalized / f'train_s{source}.parquet')})")
    con.execute(f"CREATE VIEW links AS SELECT * FROM read_parquet({lit(args.links)})")
    start = time.perf_counter()
    out: dict[str, object] = {}
    for target_source in (2, 3):
        target = f"train_s{target_source}"
        # Project the target country so country_pairs / target_country are real
        # distributions instead of the permanently empty `if False else {}`.
        base = f"""
        SELECT s.country, t.country AS t_country, s.n_name, s.n_addr, t.n_name AS t_name, t.n_addr AS t_addr
        FROM links l JOIN train_s1 s ON s.entity_id=l.source1_entity_id
        JOIN {target} t ON t.entity_id=l.target_id
        WHERE l.target_id LIKE 'S{target_source}-%'
        """
        # Materialized once: this join feeds ~20 aggregate queries per target and
        # would otherwise be recomputed by each of them.
        con.execute(f"CREATE OR REPLACE TEMP TABLE pos AS {base}")
        key = f"S{target_source}"
        out[key] = {}
        out[key]["links"] = int(scalar(con, "SELECT count(*) FROM pos"))
        out[key]["country_pairs"] = {
            f"{a}->{b}": int(n)
            for a, b, n in con.execute(
                "SELECT country, t_country, count(*) FROM pos GROUP BY country, t_country ORDER BY 1, 2"
            ).fetchall()
        }
        out[key]["positive_name_prefix_lengths"] = {}
        for length in (1, 2, 3, 4, 5, 6, 8, 10):
            # Guard: left('',n)=left('',n) is true, which would inflate short prefixes.
            out[key]["positive_name_prefix_lengths"][str(length)] = rate(
                con,
                f"SELECT avg(CASE WHEN n_name<>'' AND t_name<>'' AND left(n_name,{length})=left(t_name,{length}) THEN 1.0 ELSE 0.0 END) FROM pos",
            )
        out[key]["positive_address_prefix_lengths"] = {}
        for length in (3, 5, 8, 10, 12, 15):
            out[key]["positive_address_prefix_lengths"][str(length)] = rate(
                con,
                f"SELECT avg(CASE WHEN n_addr<>'' AND t_addr<>'' AND left(n_addr,{length})=left(t_addr,{length}) THEN 1.0 ELSE 0.0 END) FROM pos",
            )
        out[key]["positive_exact_name"] = rate(con, "SELECT avg(CASE WHEN n_name=t_name AND n_name<>'' THEN 1.0 ELSE 0.0 END) FROM pos")
        out[key]["positive_exact_address"] = rate(con, "SELECT avg(CASE WHEN n_addr=t_addr AND n_addr<>'' THEN 1.0 ELSE 0.0 END) FROM pos")
        out[key]["source_country"] = {str(c): int(n) for c, n in con.execute("SELECT country,count(*) FROM pos GROUP BY country ORDER BY country").fetchall()}
        out[key]["target_country"] = {str(c): int(n) for c, n in con.execute("SELECT t_country,count(*) FROM pos GROUP BY t_country ORDER BY t_country").fetchall()}
        out[key]["empty_name"] = rate(con, "SELECT avg(CASE WHEN n_name='' OR t_name='' THEN 1.0 ELSE 0.0 END) FROM pos")
        out[key]["empty_address"] = rate(con, "SELECT avg(CASE WHEN n_addr='' OR t_addr='' THEN 1.0 ELSE 0.0 END) FROM pos")
    out["elapsed_seconds"] = time.perf_counter() - start
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, sort_keys=True))
    con.close()
    shutil.rmtree(spill, ignore_errors=True)


if __name__ == "__main__":
    main()
