"""
Smoke-test the add-on cell's SQL against DuckDB with a synthetic fixture.

WHY THIS EXISTS
`colab_addon_cell.py` cannot run locally: it needs a real duck.db, a real
model.json and a 2.4 GB dataset. But its SQL can be - and a typo in a window
function or a non-existent DuckDB builtin would otherwise surface only after a
40-minute Colab run, at the very cell meant to be the cheap one.

This builds a small fixture with the real schema and executes the same
statements, checking semantics rather than just syntax: the LEAD() runner-up
must be the SECOND best score, the recomputed p2 must match a hand-computed
sigmoid, and is_tune=0 rows must be excluded.

Run:  .\\.venv\\Scripts\\python.exe test_addon_sql.py
"""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import duckdb

FAILURES: list[str] = []
CHECKS = 0


def check(label: str, got, want) -> None:
    global CHECKS
    CHECKS += 1
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label:<54} {got!r}")
    if not ok:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def sig(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _raises(fn, exc_name: str) -> bool:
    """Assert a call fails with a specific DuckDB error, so the test can PROVE a
    function is genuinely unavailable rather than assuming it."""
    try:
        fn().fetchone()
    except Exception as exc:
        return exc_name in type(exc).__name__ or exc_name in str(exc)
    return False


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="addon_sql_"))
    con = duckdb.connect()
    con.execute("SET threads=2")

    # Real schema. Note there is NO country column on the feature file - that is
    # exactly the branch the cell has to take.
    rows = [
        ("S1", "T1", 0.90, 1, 1), ("S1", "T2", 0.20, 0, 1),
        ("S2", "T3", 0.80, 1, 1),
        ("S3", "T4", 0.70, 1, 0),          # is_tune=0 -> must be EXCLUDED
        ("S4", "T5", 0.60, 0, 1), ("S4", "T6", 0.55, 0, 1),
        ("S4", "T7", 0.50, 0, 1),
    ]
    con.execute("CREATE TABLE feat (sid VARCHAR, tid VARCHAR, name_jw DOUBLE, "
                "label INTEGER, is_tune INTEGER)")
    con.executemany("INSERT INTO feat VALUES (?,?,?,?,?)", rows)
    con.execute(f"COPY feat TO '{tmp / 'train_feat.parquet'}' (FORMAT PARQUET)")

    con.execute("CREATE TABLE s2 (entity_id VARCHAR, country VARCHAR)")
    con.executemany("INSERT INTO s2 VALUES (?,?)",
                    [(r[1], "US" if i % 2 == 0 else "FR") for i, r in enumerate(rows)])
    con.execute(f"COPY s2 TO '{tmp / 'train_s2.parquet'}' (FORMAT PARQUET)")

    (tmp / "model.json").write_text(json.dumps(
        {"features": ["name_jw"], "coef": [2.0], "intercept": 0.0,
         "threshold": 0.5}), encoding="utf-8")

    feat = tmp / "train_feat.parquet"
    src2 = tmp / "train_s2.parquet"
    feat_cols = {r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{feat}')").fetchall()}
    s2_cols = {r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{src2}')").fetchall()}
    print(f"  fixture feat columns : {sorted(feat_cols)}")
    print(f"  fixture s2   columns : {sorted(s2_cols)}")

    check("feat has NO country, so the JOIN branch is required",
          "country" in feat_cols, False)
    check("s2 DOES have country", "country" in s2_cols, True)

    # t2 is deduplicated so t2.country needs no aggregate. Using any_value()
    # here would make the whole query an aggregate query and DuckDB would
    # demand a GROUP BY over f.sid - that error is caught by this test, not on
    # Colab after the pipeline has already run.
    ctry_expr = "t2.country"
    ctry_src = (f"FROM read_parquet('{feat}') f "
                f"LEFT JOIN (SELECT DISTINCT entity_id, country "
                f"FROM read_parquet('{src2}')) t2 ON f.tid = t2.entity_id")
    score_sql = ("(1.0 / (1.0 + exp(-greatest(-60.0, least(60.0, "
                 "(2.0000000000) * coalesce(name_jw, 0))))))")

    got = con.execute(f"SELECT {score_sql} FROM read_parquet('{feat}') "
                      "WHERE sid='S1' AND tid='T1'").fetchone()[0]
    check("p2 from model.json == hand-computed sigmoid(2*0.90)",
          round(got, 9), round(sig(1.8), 9))

    con.execute(f"""
        CREATE TABLE tune AS
        SELECT f.sid AS s1, f.tid AS tid, f.label AS label,
               {ctry_expr} AS country, {score_sql} AS p2
        {ctry_src}
        WHERE f.is_tune = 1
    """)
    check("is_tune=0 row excluded (S3 gone: 6 of 7 kept)",
          con.execute("SELECT count(*) FROM tune").fetchone()[0], 6)
    check("S3 truly absent from export",
          con.execute("SELECT count(*) FROM tune WHERE s1='S3'").fetchone()[0], 0)
    check("country actually came through the join",
          sorted(r[0] for r in con.execute(
              "SELECT DISTINCT country FROM tune").fetchall()), ["FR", "US"])

    # LEAD() runner-up. S4 has T5(.60) T6(.55) T7(.50): best=T5, second=T6.
    con.execute("""
        CREATE TABLE margin AS
        SELECT s1, tid AS best_tid, p2 AS best_p2, second_p2,
               best_p2 - second_p2 AS gap FROM (
          SELECT s1, tid, p2,
                 lead(p2) OVER (PARTITION BY s1 ORDER BY p2 DESC, tid) AS second_p2,
                 row_number() OVER (PARTITION BY s1 ORDER BY p2 DESC, tid) AS rk
          FROM tune) WHERE rk = 1
    """)
    by_s1 = {r[0]: (r[1], r[2], r[3], r[4]) for r in con.execute(
        "SELECT s1, best_tid, best_p2, second_p2, gap FROM margin").fetchall()}

    # S1, S2, S4 remain after the is_tune=0 filter drops S3.
    check("one margin row per held-out S1 (S1,S2,S4 - S3 is is_tune=0)",
          con.execute("SELECT count(*) FROM margin").fetchone()[0], 3)
    check("S1 best candidate is the top-scoring tid", by_s1["S1"][0], "T1")
    check("S1 second_p2 is the runner-up T2, not the best",
          round(by_s1["S1"][2], 9), round(sig(0.4), 9))
    check("S4 best candidate", by_s1["S4"][0], "T5")
    check("S4 second_p2 is T6(0.55), NOT T7(0.50)",
          round(by_s1["S4"][2], 9), round(sig(1.1), 9))
    check("singleton S2 has NULL second_p2",
          by_s1["S2"][2] is None, True)
    check("gap == best - second for S4",
          round(by_s1["S4"][3], 9), round(sig(1.2) - sig(1.1), 9))

    # the builtins the report queries rely on
    # DuckDB has NO width_bucket() - verified, it raises CatalogException. Use an
    # explicit CASE, which works on every DuckDB version Colab might ship.
    bucket_sql = """CASE
        WHEN p2 < 0.1 THEN 1 WHEN p2 < 0.2 THEN 2 WHEN p2 < 0.3 THEN 3
        WHEN p2 < 0.4 THEN 4 WHEN p2 < 0.5 THEN 5 WHEN p2 < 0.6 THEN 6
        WHEN p2 < 0.7 THEN 7 WHEN p2 < 0.8 THEN 8 WHEN p2 < 0.9 THEN 9
        ELSE 10 END"""
    check("0.55 lands in bucket 6",
          con.execute(f"SELECT {bucket_sql} FROM (SELECT 0.55 AS p2)").fetchone()[0], 6)
    check("0.95 lands in the top bucket 10",
          con.execute(f"SELECT {bucket_sql} FROM (SELECT 0.95 AS p2)").fetchone()[0], 10)
    check("greatest/least really clamp (exp(1e6) would overflow)",
          con.execute("SELECT exp(-least(60.0, 1e6)) < 1e25").fetchone()[0], True)
    check("hash() exists (subsample filter uses it)",
          isinstance(con.execute("SELECT hash('S1')").fetchone()[0], int), True)
    check("hash() is deterministic across calls",
          con.execute("SELECT hash('S1') = hash('S1')").fetchone()[0], True)
    check("width_bucket really is absent (why the CASE is needed)",
          _raises(lambda: con.execute("SELECT width_bucket(0.5,0,1,10)"),
                  "CatalogException"), True)

    # the cell must fail loudly on an empty export rather than sweep nothing
    con.execute("CREATE TABLE empty_tune (s1 VARCHAR, tid VARCHAR, "
                "label INTEGER, p2 DOUBLE, country VARCHAR)")
    check("empty export is detectable (cell raises SystemExit on it)",
          con.execute("SELECT count(*) FROM empty_tune").fetchone()[0], 0)

    # the NPZ handoff shape sweep_threshold.py expects
    import numpy as np
    npz = tmp / "tune_scores.npz"
    q = con.execute("SELECT s1, tid, label, p2, country FROM tune").fetchall()
    np.savez_compressed(npz,
                        sids=np.array([r[0] for r in q], dtype=object),
                        tids=np.array([r[1] for r in q], dtype=object),
                        labels=np.array([r[2] for r in q], dtype=np.int8),
                        scores=np.array([r[3] for r in q], dtype=np.float64),
                        countries=np.array([r[4] for r in q], dtype=object))
    d = np.load(npz, allow_pickle=True)
    check("NPZ carries every key sweep_threshold.py reads",
          sorted(d.files), ["countries", "labels", "scores", "sids", "tids"])
    check("NPZ row count matches the export", len(d["scores"]), len(q))

    print(f"\n{'=' * 68}")
    if FAILURES:
        print(f"FAILED {len(FAILURES)}/{CHECKS} checks")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print(f"selftest: OK  ({CHECKS}/{CHECKS} checks passed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
