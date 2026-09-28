"""Second official-data blocking pilot: canonical keys plus rare token channels.

The pilot samples S1 IDs with DuckDB's hash() and indexes the full target corpus.
NOTE: DuckDB's hash() is NOT stable across engine versions, so the sampled ID
set (and therefore every number below) depends on the recorded
`duckdb_version`; the sample is approximately 1/sample_mod of S1, not a fixed
1/1000 subset. Aggregate candidate volume and known-positive hits only; not a
final model or a score estimate.
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
    p.add_argument("--sample-mod", type=int, default=1000)
    p.add_argument("--target", type=int, choices=(2, 3), required=True)
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--memory-limit", default="500MB")
    p.add_argument("--max-token-df", type=int, default=5000)
    args = p.parse_args()
    if args.sample_mod < 1:
        # DuckDB's modulo-by-zero returns NULL rather than raising, so a 0 sample
        # silently reports zero candidates everywhere: a meaningless but
        # legitimate-looking benchmark.
        p.error(f"--sample-mod must be >= 1, got {args.sample_mod}")
    if args.max_token_df < 1:
        # Same failure mode: `df <= 0` matches nothing, so every token channel
        # reports zero candidates while still looking like a valid result.
        p.error(f"--max-token-df must be >= 1, got {args.max_token_df}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.parent / f"pilot_v2_{args.target}_tmp_{os.getpid()}"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(":memory:")
    con.execute("SET threads=?", [int(args.threads)])
    con.execute(f"SET memory_limit={lit(args.memory_limit)}")
    con.execute(f"SET temp_directory={lit(tmp)}")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"CREATE VIEW s1 AS SELECT * FROM read_parquet({lit(args.normalized / 'train_s1.parquet')})")
    con.execute(f"CREATE VIEW target AS SELECT * FROM read_parquet({lit(args.normalized / f'train_s{args.target}.parquet')})")
    con.execute(f"CREATE VIEW links AS SELECT * FROM read_parquet({lit(args.links)})")
    con.execute(f"CREATE TEMP TABLE qs AS SELECT * FROM s1 WHERE hash(entity_id) % {args.sample_mod} = 0")
    con.execute("CREATE TEMP TABLE gold AS SELECT l.source1_entity_id, l.target_id FROM links l JOIN qs q ON q.entity_id=l.source1_entity_id WHERE l.target_id LIKE ?", [f"S{args.target}-%"])
    # Canonical expressions are deliberately simple and deterministic.
    con.execute("""
      CREATE TEMP VIEW qbase AS
      SELECT *,
        array_to_string(list_sort(string_split(n_name, ' ')), ' ') AS n_sorted,
        replace(n_name, ' ', '') AS n_compact,
        array_to_string(list_sort(list_filter(string_split(n_name, ' '), x -> lower(x) NOT IN ('llc','inc','incorporated','ltd','limited','pvt','private','company','co','corp','corporation','the'))), ' ') AS n_core_sorted,
        array_to_string(list_sort(string_split(n_addr, ' ')), ' ') AS a_sorted,
        replace(n_addr, ' ', '') AS a_compact
      FROM qs
    """)
    con.execute("""
      CREATE TEMP TABLE tbase AS
      SELECT *,
        array_to_string(list_sort(string_split(n_name, ' ')), ' ') AS n_sorted,
        replace(n_name, ' ', '') AS n_compact,
        array_to_string(list_sort(list_filter(string_split(n_name, ' '), x -> lower(x) NOT IN ('llc','inc','incorporated','ltd','limited','pvt','private','company','co','corp','corporation','the'))), ' ') AS n_core_sorted,
        array_to_string(list_sort(string_split(n_addr, ' ')), ' ') AS a_sorted,
        replace(n_addr, ' ', '') AS a_compact
      FROM target
    """)
    # Per-sample-id country lookup. A correlated `WHERE entity_id=... LIMIT 1`
    # subquery re-executes for every candidate row and has no defined pick when
    # the id is absent.
    con.execute("CREATE TEMP VIEW qmeta AS SELECT DISTINCT entity_id, country FROM qbase")
    channels = {
        "name_exact": "q.n_name=t.n_name AND q.n_name<>''",
        "name_sorted_exact": "q.n_sorted=t.n_sorted AND q.n_name<>''",
        "name_core_sorted_exact": "q.n_core_sorted=t.n_core_sorted AND q.n_core_sorted<>''",
        "name_compact_exact": "q.n_compact=t.n_compact AND q.n_compact<>''",
        "address_exact": "q.n_addr=t.n_addr AND q.n_addr<>''",
        "address_sorted_exact": "q.a_sorted=t.a_sorted AND q.n_addr<>''",
        "address_compact_exact": "q.a_compact=t.a_compact AND q.n_addr<>''",
        "name3_address5": "left(q.n_name,3)=left(t.n_name,3) AND left(q.n_addr,5)=left(t.n_addr,5) AND q.n_name<>'' AND q.n_addr<>''",
        "name5_address3": "left(q.n_name,5)=left(t.n_name,5) AND left(q.n_addr,3)=left(t.n_addr,3) AND q.n_name<>'' AND q.n_addr<>''",
        "name4_address4": "left(q.n_name,4)=left(t.n_name,4) AND left(q.n_addr,4)=left(t.n_addr,4) AND q.n_name<>'' AND q.n_addr<>''",
        "name_core3_address5": "left(q.n_core_sorted,3)=left(t.n_core_sorted,3) AND left(q.n_addr,5)=left(t.n_addr,5) AND q.n_core_sorted<>'' AND q.n_addr<>''",
    }
    out: dict[str, object] = {
        "target": args.target,
        "sample_mod": args.sample_mod,
        "duckdb_version": duckdb.__version__,
    }
    start = time.perf_counter()
    gold_links = int(con.execute("SELECT count(*) FROM gold").fetchone()[0])
    for channel, predicate in channels.items():
        sql = f"""
        WITH c AS (
          SELECT q.entity_id AS sid, t.entity_id AS tid
          FROM qbase q JOIN tbase t ON q.country=t.country AND {predicate}
        ), counts AS (
          SELECT sid, count(*) AS n FROM c GROUP BY sid
        ), hit AS (
          SELECT count(*) AS n FROM gold g JOIN c ON c.sid=g.source1_entity_id AND c.tid=g.target_id
        )
        SELECT (SELECT count(*) FROM c), (SELECT count(*) FROM counts),
               (SELECT coalesce(avg(n),0) FROM counts),
               (SELECT coalesce(approx_quantile(n,0.5),0) FROM counts),
               (SELECT coalesce(approx_quantile(n,0.9),0) FROM counts),
               (SELECT coalesce(approx_quantile(n,0.99),0) FROM counts),
               (SELECT coalesce(max(n),0) FROM counts),
               (SELECT n FROM hit)
        """
        row = con.execute(sql).fetchone()
        hits = int(row[7])
        out[channel] = {
            "candidate_pairs": int(row[0]), "covered_s1": int(row[1]),
            "mean_per_covered_s1": float(row[2]), "p50": float(row[3]),
            "p90": float(row[4]), "p99": float(row[5]), "max": float(row[6]),
            "known_positive_hits": hits,
            "known_positive_recall": hits / gold_links if gold_links else None,
        }
    # Shared rare name/address tokens. A target token must occur no more than
    # max-token-df times in the target corpus, preventing common-word explosions.
    for field, label in (("n_name", "name_token"), ("n_addr", "address_token")):
        sql = f"""
        WITH qt AS (
          SELECT q.entity_id AS sid, x.token
          FROM qbase q, UNNEST(string_split(q.{field}, ' ')) AS x(token)
          WHERE length(x.token) >= 4
        ), qd AS (SELECT DISTINCT token FROM qt),
        tf AS (
          SELECT x.token, count(*) AS df
          FROM target t, UNNEST(string_split(t.{field}, ' ')) AS x(token)
          WHERE x.token IN (SELECT token FROM qd)
          GROUP BY x.token
        ), qgood AS (
          SELECT qt.sid, qt.token
          FROM qt JOIN tf ON tf.token=qt.token
          WHERE tf.df <= {args.max_token_df}
        ), c AS (
          SELECT DISTINCT qg.sid, t.entity_id AS tid
          FROM qgood qg
          JOIN qmeta m ON m.entity_id=qg.sid
          JOIN target t ON t.country=m.country,
            UNNEST(string_split(t.{field}, ' ')) AS x(token)
          WHERE x.token=qg.token
        ), counts AS (
          SELECT sid, count(*) AS n FROM c GROUP BY sid
        ), hit AS (
          SELECT count(*) AS n FROM gold g JOIN c ON c.sid=g.source1_entity_id AND c.tid=g.target_id
        )
        SELECT (SELECT count(*) FROM c), (SELECT count(*) FROM counts),
               (SELECT coalesce(avg(n),0) FROM counts),
               (SELECT coalesce(approx_quantile(n,0.5),0) FROM counts),
               (SELECT coalesce(approx_quantile(n,0.9),0) FROM counts),
               (SELECT coalesce(approx_quantile(n,0.99),0) FROM counts),
               (SELECT coalesce(max(n),0) FROM counts),
               (SELECT n FROM hit)
        """
        row = con.execute(sql).fetchone()
        hits = int(row[7])
        out[label] = {
            "candidate_pairs": int(row[0]), "covered_s1": int(row[1]),
            "mean_per_covered_s1": float(row[2]), "p50": float(row[3]),
            "p90": float(row[4]), "p99": float(row[5]), "max": float(row[6]),
            "known_positive_hits": hits, "max_token_df": args.max_token_df,
            "known_positive_recall": hits / gold_links if gold_links else None,
        }
    out["sample_s1"] = int(con.execute("SELECT count(*) FROM qs").fetchone()[0])
    out["sample_gold_links"] = gold_links
    out["elapsed_seconds"] = time.perf_counter() - start
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, sort_keys=True))
    con.close()
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
