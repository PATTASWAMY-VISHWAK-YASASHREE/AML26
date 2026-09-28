"""Measure candidate-size vs recall with ALL blocking channels.

Why now: the brief says an approach producing a SMALLER candidate set per S1
entity is ranked HIGHER, beyond the leaderboard score. max_candidates is
therefore a direct ranking lever, not just a recall knob, and the optimum moves
sharply down. Optimising only for F0.5 (as earlier work here did) pushed the cap
to 20 - now the wrong direction.

Measures the real curve on a sample of actual S1 entities against the full
target corpus, using the same 7 channels the pipeline uses. Only ~3 GB disk is
free, so the token posting table is restricted to tokens occurring in the
sample, avoiding a 30M-row materialisation.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import duckdb

import er_pipeline as P

ROOT = Path(__file__).parent
NORM = ROOT / "amazon_ml_2026_research" / "work" / "normalized"
LINKS = ROOT / "amazon_ml_2026_research" / "work" / "train_links.parquet"
TMP = ROOT / "_cap_probe"
SAMPLE = 30_000
CAPS = (3, 5, 6, 8, 10, 15, 20)
MIN_TOKEN_LEN = 4
MAX_TOKEN_DF = 1500

EXACT = [(1, "n_name"), (2, "n_sorted"), (3, "n_core_sorted"),
         (4, "n_addr"), (5, "a_sorted")]
TOKENS = ((6, "name", "n_name"), (7, "addr", "n_addr"))


def lit(v) -> str:
    return "'" + str(v).replace("'", "''") + "'"


def build(con, s1p, s2p, s3p) -> int:
    t0 = time.time()
    con.execute(f"""
        COPY (SELECT * FROM read_parquet({lit(s1p)})
              WHERE hash(entity_id) % 97 = 0 LIMIT {SAMPLE})
        TO {lit(TMP / 's1.parquet')} (FORMAT PARQUET)""")
    n_s1 = con.execute(
        f"SELECT count(*) FROM read_parquet({lit(TMP / 's1.parquet')})").fetchone()[0]
    print(f"S1 sample: {n_s1:,} entities ({time.time() - t0:.0f}s)", flush=True)

    for kind, src in (("name", "n_name"), ("addr", "n_addr")):
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE samp_tok AS
            SELECT DISTINCT '{kind}' AS kind, token FROM (
              SELECT unnest(list_filter(string_split(coalesce({src}, ''), ' '),
                                      x -> length(x) >= {MIN_TOKEN_LEN})) AS token
              FROM read_parquet({lit(TMP / 's1.parquet')}))""")
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE post AS
            WITH t AS (
              SELECT entity_id, country, '{kind}' AS kind,
                     unnest(list_filter(string_split(coalesce({src}, ''), ' '),
                                        x -> length(x) >= {MIN_TOKEN_LEN})) AS token
              FROM (SELECT * FROM read_parquet({lit(s2p)})
                    UNION ALL SELECT * FROM read_parquet({lit(s3p)}))),
            d AS (SELECT kind, token, count(DISTINCT entity_id) df
                  FROM t JOIN samp_tok USING (kind, token) GROUP BY 1, 2)
            SELECT t.kind, t.token, t.entity_id, t.country
            FROM t JOIN d USING (kind, token) WHERE d.df <= {MAX_TOKEN_DF}""")
        c = con.execute("SELECT count(*), count(DISTINCT token) FROM post").fetchone()
        print(f"  {kind} postings: {c[0]:,} rows / {c[1]:,} tokens "
              f"({time.time() - t0:.0f}s)", flush=True)
        con.execute(f"COPY post TO {lit(TMP / f'post_{kind}.parquet')} (FORMAT PARQUET)")

    parts = [f"""
        SELECT {prio} AS prio, s.entity_id AS sid, t.entity_id AS tid
        FROM (SELECT entity_id, country, {key} AS k
              FROM read_parquet({lit(TMP / 's1.parquet')})) s
        JOIN (SELECT entity_id, country, {key} AS k FROM read_parquet({lit(s2p)})
              UNION ALL
              SELECT entity_id, country, {key} AS k FROM read_parquet({lit(s3p)})) t
          ON s.country = t.country AND s.k = t.k
        WHERE s.k IS NOT NULL""" for prio, key in EXACT]
    for prio, kind, src in TOKENS:
        parts.append(f"""
            SELECT {prio} AS prio, p.sid, q.entity_id AS tid
            FROM (SELECT entity_id AS sid, country,
                    unnest(list_filter(string_split(coalesce({src}, ''), ' '),
                                       x -> length(x) >= {MIN_TOKEN_LEN})) AS token
                  FROM read_parquet({lit(TMP / 's1.parquet')})) p
            JOIN read_parquet({lit(TMP / f'post_{kind}.parquet')}) q
              ON q.kind = {lit(kind)} AND q.token = p.token AND q.country = p.country""")
    con.execute(f"""
        COPY (WITH raw AS ({(" UNION ALL " + chr(10)).join(parts)}),
                 d AS (SELECT sid, tid, min(prio) prio FROM raw GROUP BY 1, 2),
                 r AS (SELECT sid, tid, prio,
                              row_number() OVER (PARTITION BY sid ORDER BY prio, tid) rn
                       FROM d)
              SELECT sid, tid, prio, rn FROM r)
        TO {lit(TMP / 'cand.parquet')} (FORMAT PARQUET)""")
    npair = con.execute(
        f"SELECT count(*) FROM read_parquet({lit(TMP / 'cand.parquet')})").fetchone()[0]
    print(f"candidates uncapped: {npair:,} pairs, {npair / n_s1:.1f}/S1 "
          f"({time.time() - t0:.0f}s)\n", flush=True)

    con.execute(f"""
        COPY (SELECT g.source1_entity_id AS sid, g.target_id AS tid
              FROM read_parquet({lit(LINKS)}) g
              JOIN read_parquet({lit(TMP / 's1.parquet')}) s
                ON s.entity_id = g.source1_entity_id)
        TO {lit(TMP / 'gold.parquet')} (FORMAT PARQUET)""")
    return n_s1


def normalize(con) -> dict:
    """Materialise the full key set for the TRAIN split from the raw TSVs.

    The shards in work/normalized came from an older materialization and lack
    n_sorted / n_core_sorted / a_sorted / token lists, so the 7-channel probe
    cannot run against them. Rebuilding here (train only, ~400 MB) keeps the
    measurement honest rather than silently probing a weaker 2-channel proxy.
    """
    ds = ROOT / "amazon_ml_2026_research" / "student_resource" / "dataset" / "train"
    out = TMP / "norm"
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for src, path in ((1, ds / "train_source1.tsv"),
                      (2, ds / "train_source2.tsv"),
                      (3, ds / "train_source3.tsv")):
        dst = out / f"train_s{src}.parquet"
        if dst.exists():
            continue
        con.execute(f"""
            COPY (SELECT
                entity_id,
                {P._norm_expr('business_name')} AS n_name,
                {P._norm_expr('business_address')} AS n_addr,
                nullif(nullif(trim(coalesce(country,'')),''),'nan') AS country,
                -- DuckDB allows referencing an earlier alias in the same SELECT,
                -- so n_name / n_addr are reused rather than recomputed.
                nullif(array_to_string(list_sort(string_split(n_name, ' ')), ' '),'')
                    AS n_sorted,
                nullif(array_to_string(list_sort({P._core_tokens('n_name')}), ' '),'')
                    AS n_core_sorted,
                nullif(array_to_string(list_sort(string_split(n_addr, ' ')), ' '),'')
                    AS a_sorted
              FROM read_csv({lit(path)}, delim='\t', header=true, ignore_errors=false))
            TO {lit(dst)} (FORMAT PARQUET, COMPRESSION ZSTD)""")
        n = con.execute(f"SELECT count(*) FROM read_parquet({lit(dst)})").fetchone()[0]
        print(f"  normalized train_s{src}: {n:,} rows ({time.time() - t0:.0f}s)",
              flush=True)
    return {1: out / "train_s1.parquet", 2: out / "train_s2.parquet",
            3: out / "train_s3.parquet"}


def main() -> int:
    if not LINKS.exists():
        print("train_links.parquet missing")
        return 1
    TMP.mkdir(exist_ok=True)
    con = duckdb.connect()
    con.execute("SET threads=2")
    con.execute("SET memory_limit='3GB'")
    con.execute(f"SET temp_directory={lit(TMP)}")
    con.execute("SET preserve_insertion_order=false")
    try:
        shards = normalize(con)
        n_s1 = build(con, shards[1], shards[2], shards[3])

        gold = con.execute(
            f"SELECT count(*) FROM read_parquet({lit(TMP / 'gold.parquet')})").fetchone()[0]
        print(f"gold links for the sample: {gold:,}\n")
        print(f"  {'cap':>4}  {'cands/S1':>9}  {'total pairs':>12}  {'gold recall':>11}")
        rows = []
        for cap in CAPS:
            kept, hit = con.execute(f"""
                WITH k AS (SELECT sid, tid, rn
                           FROM read_parquet({lit(TMP / 'cand.parquet')}) WHERE rn <= {cap})
                SELECT (SELECT count(*) FROM k),
                       (SELECT count(*) FROM (SELECT * FROM k) k
                        JOIN read_parquet({lit(TMP / 'gold.parquet')}) g
                          ON g.sid = k.sid AND g.tid = k.tid)
            """).fetchone()
            rec = hit / gold if gold else 0.0
            rows.append((cap, kept / n_s1, rec))
            print(f"  {cap:>4}  {kept / n_s1:>9.2f}  {kept:>12,}  {rec:>11.4f}")
        print()
        b_cap, b_per, b_rec = rows[-1]
        for cap, per, rec in rows:
            print(f"  cap={cap:>3} vs {b_cap}: "
                  f"{100 * (b_per - per) / b_per:5.1f}% fewer candidates, "
                  f"{100 * (b_rec - rec) / max(b_rec, 1e-9):4.2f}% relative recall cost")
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
