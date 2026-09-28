"""Small-sample blocking pilot for the official data.

This avoids the pathological full-corpus prefix self-join. It samples S1 IDs
with DuckDB's hash() and reports aggregate candidate volume plus known-positive
recall for additive channels. NOTE: DuckDB's hash() is NOT stable across
engine versions, so the sampled ID set (and therefore every number below)
depends on the recorded `duckdb_version`; it is a planning experiment, not a
final model.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
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
    args = p.parse_args()
    if args.sample_mod < 1:
        # DuckDB's `% 0` yields NULL, so the sample would be EMPTY and every
        # statistic below would be a misleading 0.
        p.error(f"--sample-mod must be a positive integer, got {args.sample_mod}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Run-scoped spill directory: a name derived only from --target collides
    # between concurrent runs and leaves stale files behind.
    tmp = Path(tempfile.mkdtemp(prefix=f"pilot_{args.target}_"))
    con = duckdb.connect(":memory:")
    try:
        con.execute("SET threads=?", [int(args.threads)])
        con.execute(f"SET memory_limit={lit(args.memory_limit)}")
        con.execute(f"SET temp_directory={lit(tmp)}")
        con.execute("SET preserve_insertion_order=false")
        con.execute(f"CREATE VIEW s1 AS SELECT * FROM read_parquet({lit(args.normalized / 'train_s1.parquet')})")
        con.execute(f"CREATE VIEW target AS SELECT * FROM read_parquet({lit(args.normalized / f'train_s{args.target}.parquet')})")
        con.execute(f"CREATE VIEW links AS SELECT * FROM read_parquet({lit(args.links)})")
        con.execute(f"CREATE TEMP TABLE qs AS SELECT * FROM s1 WHERE hash(entity_id) % {args.sample_mod} = 0")
        con.execute("CREATE TEMP TABLE gold AS SELECT l.source1_entity_id, l.target_id FROM links l JOIN qs q ON q.entity_id=l.source1_entity_id WHERE l.target_id LIKE ?", [f"S{args.target}-%"])
        channels = {
            "name_exact": "q.n_name=t.n_name AND q.n_name<>''",
            "name_prefix_3": "left(q.n_name,3)=left(t.n_name,3) AND q.n_name<>''",
            "name_prefix_5": "left(q.n_name,5)=left(t.n_name,5) AND q.n_name<>''",
            "address_prefix_5": "left(q.n_addr,5)=left(t.n_addr,5) AND q.n_addr<>''",
            "name3_address5": "left(q.n_name,3)=left(t.n_name,3) AND left(q.n_addr,5)=left(t.n_addr,5) AND q.n_name<>'' AND q.n_addr<>''",
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
              FROM qs q JOIN target t ON q.country=t.country AND {predicate}
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
                # The ratio was previously never computed: the denominator was
                # reported separately and the hits were left as a raw count.
                "known_positive_recall": hits / gold_links if gold_links else None,
            }
        out["sample_s1"] = int(con.execute("SELECT count(*) FROM qs").fetchone()[0])
        out["sample_gold_links"] = gold_links
        out["elapsed_seconds"] = time.perf_counter() - start
    finally:
        con.close()
        shutil.rmtree(tmp, ignore_errors=True)
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
