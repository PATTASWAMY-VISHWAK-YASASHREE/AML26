"""Measure exact-key blocking recall for several deterministic key families.

The script uses only the persisted training edges and normalized Parquet shards.
It reports positive-link recall, not a fabricated end-to-end score.
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


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--normalized", type=Path, required=True)
    p.add_argument("--links", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--memory-limit", default="1200MB")
    args = p.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    spill = args.out.parent / f"key_audit_tmp_{os.getpid()}"
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
    # Key families are deliberately simple, deterministic, and country-agnostic
    # at the SQL layer. The country is reported as a diagnostic, not used as a
    # hard production block because France is unseen in training.
    expressions = {
        "name_exact": "s.n_name = t.n_name AND s.n_name <> ''",
        "address_exact": "s.n_addr = t.n_addr AND s.n_addr <> ''",
        "name_prefix_3": "left(s.n_name, 3) = left(t.n_name, 3) AND s.n_name <> ''",
        "name_prefix_5": "left(s.n_name, 5) = left(t.n_name, 5) AND s.n_name <> ''",
        "name_suffix_5": "right(s.n_name, 5) = right(t.n_name, 5) AND s.n_name <> ''",
        "address_prefix_5": "left(s.n_addr, 5) = left(t.n_addr, 5) AND s.n_addr <> ''",
        "address_prefix_8": "left(s.n_addr, 8) = left(t.n_addr, 8) AND s.n_addr <> ''",
        "name_or_address_exact": "(s.n_name = t.n_name AND s.n_name <> '') OR (s.n_addr = t.n_addr AND s.n_addr <> '')",
    }
    result: dict[str, object] = {}
    start = time.perf_counter()
    for target_source in (2, 3):
        target = f"train_s{target_source}"
        # One query per target: previously the same 3-way join was re-executed
        # once per key family (8x per target). Each family is now a conditional
        # sum over the single join.
        selects = ["count(*) AS links"]
        for name, predicate in expressions.items():
            selects.append(f"sum(CASE WHEN {predicate} THEN 1 ELSE 0 END) AS r_{name}")
            # Country agreement is reported over the links THIS family recovers;
            # averaging over all gold links yields 1.0 for every family.
            selects.append(
                f"sum(CASE WHEN {predicate} AND s.country=t.country THEN 1 ELSE 0 END) AS a_{name}"
            )
        sql = f"""
        SELECT {', '.join(selects)}
        FROM links l
        JOIN train_s1 s ON s.entity_id=l.source1_entity_id
        JOIN {target} t ON t.entity_id=l.target_id
        WHERE l.target_id LIKE 'S{target_source}-%'
        """
        row = con.execute(sql).fetchone()
        # sum() over an empty set is NULL: a target source with no joined positive
        # links must not raise TypeError.
        links = int(row[0] or 0)
        result[f"S{target_source}"] = {}
        for i, name in enumerate(expressions):
            recovered = int(row[1 + 2 * i] or 0)
            agree = int(row[2 + 2 * i] or 0)
            result[f"S{target_source}"][name] = {
                "positive_links": links,
                "recovered_links": recovered,
                "recall": recovered / links if links else 0.0,
                "country_agreement": agree / recovered if recovered else None,
            }
    result["elapsed_seconds"] = time.perf_counter() - start
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    con.close()
    shutil.rmtree(spill, ignore_errors=True)


if __name__ == "__main__":
    main()
