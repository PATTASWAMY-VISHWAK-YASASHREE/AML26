"""Build and evaluate exact-name blocking on the official normalized shards.

This is a first real-data baseline, not the final matcher. It keeps only
integer IDs and normalized strings in DuckDB/Parquet and reports candidate
recall and candidate volume without writing a giant Python list.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import duckdb


def lit(path: Path | str) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def maybe_float(value) -> float | None:
    """avg() over an empty set returns NULL; float(None) raises TypeError."""
    return None if value is None else float(value)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--normalized", type=Path, required=True)
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--memory-limit", default="1500MB")
    args = p.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    spill = args.out.parent / "blocking_tmp"
    spill.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(":memory:")
    con.execute("SET threads=?", [int(args.threads)])
    con.execute(f"SET memory_limit={lit(args.memory_limit)}")
    con.execute(f"SET temp_directory={lit(spill)}")
    con.execute("SET preserve_insertion_order=false")
    # Only the train views are queried. Creating all six also made the script
    # fail outright when the test shards had never been materialized.
    for source in (1, 2, 3):
        con.execute(f"CREATE VIEW train_s{source} AS SELECT * FROM read_parquet({lit(args.normalized / f'train_s{source}.parquet')})")
    gt = lit(args.dataset / "train/train_ground_truth.tsv")
    start = time.perf_counter()
    result: dict[str, object] = {}
    for target_source in (2, 3):
        target = f"train_s{target_source}"
        sql = f"""
        WITH gt_links AS (
          SELECT source1_entity_id, unnest(string_split(coalesce(matched_entity_ids,''), ',')) AS target_id
          FROM read_csv({gt}, delim='\\t', header=true,
            columns={{'source1_entity_id':'VARCHAR','matched_entity_ids':'VARCHAR'}})
          WHERE matched_entity_ids IS NOT NULL AND matched_entity_ids <> ''
        ), pos AS (
          SELECT g.source1_entity_id, g.target_id,
                 s.n_name=t.n_name AND s.n_name<>'' AS blocked
          FROM gt_links g JOIN train_s1 s ON s.entity_id=g.source1_entity_id
          JOIN {target} t ON t.entity_id=g.target_id
          WHERE g.target_id LIKE 'S{target_source}-%'
        ), candidates AS MATERIALIZED (
          -- MATERIALIZED: this huge equi-join is referenced three times below and
          -- DuckDB inlines multiply-referenced CTEs, re-running it each time.
          SELECT s.entity_id AS source1_entity_id, t.entity_id AS target_id
          FROM train_s1 s JOIN {target} t
            ON s.country=t.country AND s.n_name=t.n_name
          WHERE s.n_name <> ''
        )
        SELECT (SELECT count(*) FROM pos) AS positive_links,
               (SELECT avg(CASE WHEN blocked THEN 1.0 ELSE 0.0 END) FROM pos) AS name_exact_recall,
               (SELECT count(*) FROM candidates) AS candidate_pairs,
               (SELECT count(DISTINCT source1_entity_id) FROM candidates) AS covered_s1,
               (SELECT count(*) FROM pos p JOIN candidates c ON c.source1_entity_id=p.source1_entity_id AND c.target_id=p.target_id) AS recovered_positive_links
        """
        # The predicate is written correctly inline above. The previous version
        # patched it in with sql.replace(), which silently no-ops if the
        # placeholder is ever reformatted -- reporting name_exact_recall=1.0 for
        # every target.
        row = con.execute(sql).fetchone()
        result[f"S{target_source}"] = {
            "positive_links": int(row[0]),
            "name_exact_recall": maybe_float(row[1]),
            "candidate_pairs": int(row[2]),
            "covered_s1": int(row[3]),
            "recovered_positive_links": int(row[4]),
        }
    result["elapsed_seconds"] = time.perf_counter() - start
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    con.close()


if __name__ == "__main__":
    main()
