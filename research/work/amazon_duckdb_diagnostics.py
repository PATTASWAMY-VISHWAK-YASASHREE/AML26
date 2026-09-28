"""Bounded DuckDB diagnostics for the official Amazon ER files.

Only aggregates and schema/count checks are emitted. The raw TSV files remain
read-only and are queried through file-backed views.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import duckdb


def lit(path: Path | str) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def q(con: duckdb.DuckDBPyConnection, sql: str, params: list | None = None):
    return con.execute(sql, params or []).fetchall()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--memory-limit", default="2GB")
    args = p.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # with_suffix('.tmp') would resolve to the DB file's own path when it already
    # ends in .tmp; use a dedicated directory instead.
    spill = args.out.parent / "duckdb_tmp"
    spill.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(args.db), read_only=True)
    con.execute("SET threads=?", [int(args.threads)])
    con.execute("SET memory_limit=?", [str(args.memory_limit)])
    con.execute("SET temp_directory=?", [str(spill)])
    start = time.perf_counter()
    result: dict[str, object] = {}

    result["country_counts"] = {
        split: {row[0]: int(row[1]) for row in q(con, f"SELECT country, count(*) FROM {split}_s1 GROUP BY country ORDER BY country")}
        for split in ("train", "test")
    }
    result["id_ranges"] = {}
    for view in ("train_s1", "train_s2", "train_s3", "test_s1", "test_s2", "test_s3"):
        result["id_ranges"][view] = {
            "min": q(con, f"SELECT min(entity_id) FROM {view}")[0][0],
            "max": q(con, f"SELECT max(entity_id) FROM {view}")[0][0],
            "distinct": int(q(con, f"SELECT count(DISTINCT entity_id) FROM {view}")[0][0]),
        }

    # File-backed normalized views. The expression is intentionally simple and
    # deterministic; a Python normalizer is used later for Unicode/address rules.
    for view in ("train_s1", "train_s2", "train_s3", "test_s1", "test_s2", "test_s3"):
        con.execute(
            f"CREATE OR REPLACE TEMP VIEW {view}_n AS SELECT entity_id, country, lower(trim(regexp_replace(regexp_replace(coalesce(business_name,''), '[^[:alnum:]]+', ' ', 'g'), '\\s+', ' ', 'g'))) AS n_name, lower(trim(regexp_replace(regexp_replace(coalesce(business_address,''), '[^[:alnum:]]+', ' ', 'g'), '\\s+', ' ', 'g'))) AS n_addr FROM {view}"
        )

    result["exact_key_stats"] = {}
    for view in ("train_s1", "train_s2", "train_s3", "test_s1", "test_s2", "test_s3"):
        result["exact_key_stats"][view] = {
            "name_nonempty": int(q(con, f"SELECT count(*) FROM {view}_n WHERE n_name <> ''")[0][0]),
            "addr_nonempty": int(q(con, f"SELECT count(*) FROM {view}_n WHERE n_addr <> ''")[0][0]),
            # Empty-key bucket sizes: if these were ever used as a block key, every
            # one of these rows would collide with every other, so the report must
            # expose the false-positive contribution rather than hide it.
            "name_empty_rows": int(q(con, f"SELECT count(*) FROM {view}_n WHERE n_name = ''")[0][0]),
            "addr_empty_rows": int(q(con, f"SELECT count(*) FROM {view}_n WHERE n_addr = ''")[0][0]),
            "name_distinct": int(q(con, f"SELECT count(DISTINCT n_name) FROM {view}_n")[0][0]),
            "addr_distinct": int(q(con, f"SELECT count(DISTINCT n_addr) FROM {view}_n")[0][0]),
            "name_duplicate_rows": int(q(con, f"SELECT coalesce(sum(n-1),0) FROM (SELECT n_name, count(*) n FROM {view}_n WHERE n_name <> '' GROUP BY n_name)")[0][0]),
            "addr_duplicate_rows": int(q(con, f"SELECT coalesce(sum(n-1),0) FROM (SELECT n_addr, count(*) n FROM {view}_n WHERE n_addr <> '' GROUP BY n_addr)")[0][0]),
            # Rows that share a key when the empty string is allowed to be a key.
            "name_empty_collision_pairs": int(q(con, f"SELECT count(*) * (count(*) - 1) / 2 FROM (SELECT n_name FROM {view}_n WHERE n_name = '')")[0][0]),
            "addr_empty_collision_pairs": int(q(con, f"SELECT count(*) * (count(*) - 1) / 2 FROM (SELECT n_addr FROM {view}_n WHERE n_addr = '')")[0][0]),
        }

    # Full ground-truth link audit. Empty list is represented by no unnested row.
    gt_lit = lit(args.dataset / "train/train_ground_truth.tsv")
    result["ground_truth"] = {
        "rows": int(q(con, f"SELECT count(*) FROM read_csv({gt_lit}, delim='\\t', header=true, columns={{'source1_entity_id':'VARCHAR','matched_entity_ids':'VARCHAR'}})")[0][0]),
    }
    # Link-level exact-block recall against each target source. The join is on
    # explicit entity IDs, never on names, and only reports aggregates.
    result["positive_link_block_audit"] = {}
    for target_source, target_view in ((2, "train_s2_n"), (3, "train_s3_n")):
        sql = f"""
        WITH gt AS (
          SELECT source1_entity_id, unnest(string_split(coalesce(matched_entity_ids,''), ',')) AS target_id
          FROM read_csv({gt_lit}, delim='\\t', header=true, columns={{'source1_entity_id':'VARCHAR','matched_entity_ids':'VARCHAR'}})
          WHERE matched_entity_ids IS NOT NULL AND matched_entity_ids <> ''
        ), links AS (
          SELECT s.country AS s_country, t.country AS t_country,
                 s.n_name=t.n_name AND s.n_name<>'' AS name_exact,
                 s.n_addr=t.n_addr AND s.n_addr<>'' AS addr_exact,
                 (s.n_name=t.n_name AND s.n_name<>'') OR (s.n_addr=t.n_addr AND s.n_addr<>'') AS either_exact
          FROM gt JOIN train_s1_n s ON s.entity_id=gt.source1_entity_id
          JOIN {target_view} t ON t.entity_id=gt.target_id
          WHERE gt.target_id LIKE 'S{target_source}-%'
        )
        SELECT (SELECT count(*) FROM gt WHERE target_id LIKE 'S{target_source}-%') AS expected_links,
               count(*) AS resolved_links,
               GREATEST(0, (SELECT count(*) FROM gt WHERE target_id LIKE 'S{target_source}-%') - count(*)) AS unresolved_links,
               coalesce(sum(CASE WHEN name_exact THEN 1 ELSE 0 END), 0) AS name_exact_hits,
               coalesce(sum(CASE WHEN addr_exact THEN 1 ELSE 0 END), 0) AS addr_exact_hits,
               coalesce(sum(CASE WHEN either_exact THEN 1 ELSE 0 END), 0) AS either_exact_hits,
               coalesce(sum(CASE WHEN s_country=t_country THEN 1 ELSE 0 END), 0) AS country_agreement_hits
        FROM links
        """
        row = q(con, sql)[0]
        expected_links, resolved_links, unresolved_links = int(row[0]), int(row[1]), int(row[2])
        name_hits, addr_hits, either_hits, country_hits = (int(x) for x in row[3:7])
        # Denominator is expected_links (all gold links), not resolved_links: a link
        # whose target ID does not resolve used to be dropped silently, shrinking
        # the denominator and overstating quality with no warning.
        result["positive_link_block_audit"][f"S{target_source}"] = {
            "expected_links": expected_links,
            "resolved_links": resolved_links,
            "unresolved_links": unresolved_links,
            "country_agreement": country_hits / resolved_links if resolved_links else None,
            "name_exact_recall": name_hits / expected_links if expected_links else None,
            "addr_exact_recall": addr_hits / expected_links if expected_links else None,
            "either_exact_recall": either_hits / expected_links if expected_links else None,
        }

    result["elapsed_seconds"] = time.perf_counter() - start
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    con.close()


if __name__ == "__main__":
    main()
