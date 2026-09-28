#!/usr/bin/env python3
"""
decoy_shim.py - memory-safe driver for the v4 decoy post-filter.

WHY THIS EXISTS
---------------
`_upstream/src/decoy_postfilter.py` calls

    read_tsv(path) = pl.read_csv(path, separator="\\t", quote_char=None, infer_schema=False)

four times, which materialises whole files as all-Utf8 frames. Measured on this
machine (psapi PeakWorkingSetSize, exact same call):

    after test_source1.tsv   peak =  461.2 MB
    after train_source1.tsv peak =  809.2 MB   (only to obtain 3 country strings)
    after test_source2.tsv   peak = 1590.1 MB
    after test_source3.tsv   peak = 1954.7 MB   <- dataset read alone
    pl.concat([s2, s3])      peak = 1954.7 MB   rows = 9,969,589

That is ~2.8x the on-disk size, >=1.95 GB before any pair logic runs, so it
cannot run in a 600-800 MB free-RAM budget. That is the cause of the earlier
OOM kill.

WHAT THIS SCRIPT DOES
---------------------
It IMPORTS the upstream module and replaces ONLY the I/O function
(`read_tsv`) with a streaming, early-projected, semi-join-pushed-down reader.
The rule logic (rules (a)/(b), STRONG/WEAK, n_same_d, f05, house_no, the
--extra/--hidden stages) is executed by upstream's own `main()` and is never
re-implemented here, so semantics are identical and auditable.

Nothing under _upstream/ is modified. This file lives outside it.

COLUMN PROJECTION (requirement: only entity_id + house number)
-------------------------------------------------------------
Upstream's `main()` only *uses* `country`, the house number and `n_same_d`.
The name/address columns are touched only when writing the --removed audit
CSV. So the reader projects, per source, exactly:

    test_source1.tsv : entity_id, country, house_no
    test_source2.tsv : entity_id, house_no
    test_source3.tsv : entity_id, house_no
    train_source1.tsv: country            (DISTINCT only)

`house_no` is computed inside duckdb with upstream's own HOUSE_NO regex
(verified byte-identical to polars' `str.extract`, including "007 Foo"->7).
The synthetic `business_address` handed back to upstream is `CAST(h AS VARCHAR)
|| ' '`, which HOUSE_NO re-parses to exactly `h`; `business_name` is ''.
The real names/addresses are re-fetched afterwards, only for the handful of
REMOVED pairs, to build a genuinely useful audit file.

The 509 MB / 506 MB sources are never fully materialised: duckdb streams them
with an explicit memory_limit and spills to disk, and the semi-join against
the matching file's id sets is pushed into the plan.

usage:
    python decoy_shim.py --matching in.tsv --dataset <student_resource/dataset> \\
        --out out.tsv [--removed removed_pairs.tsv] [--dry-run] [--structural]

NOTE: v4 is the default and only supported rule stage. `--extra`/`--hidden`
are deliberately NOT offered: EXTRA_CLASSES contains no France rows, so
--extra is a no-op for France, and on a France-only matching file upstream
crashes at decoy_postfilter.py:114 because an empty `chosen` makes
`pl.DataFrame([], schema=[...], orient="row")` produce Null-typed join keys.
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes
import importlib.util
import os
import sys
import time

import duckdb
import polars as pl

DEFAULT_SRC = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "_upstream", "src", "decoy_postfilter.py"
)


# --------------------------------------------------------------------------
# peak RSS via psapi (high-water mark, survives short-lived allocations)
# --------------------------------------------------------------------------
class _PMC(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


_PS = ctypes.windll.psapi.GetProcessMemoryInfo
_PS.argtypes = [ctypes.wintypes.HANDLE, ctypes.c_void_p, ctypes.wintypes.DWORD]
_PS.restype = ctypes.wintypes.BOOL
_PROC = ctypes.windll.kernel32.GetCurrentProcess()
_PMI = _PMC()
_PMI.cb = ctypes.sizeof(_PMC)


def peak_mb() -> float:
    """Process peak working set in MiB since process start."""
    _PS(ctypes.wintypes.HANDLE(_PROC), ctypes.byref(_PMI), ctypes.wintypes.DWORD(_PMI.cb))
    return _PMI.PeakWorkingSetSize / 1048576.0


def load_upstream(path: str):
    """Import _upstream/src/decoy_postfilter.py as a module (read-only)."""
    if not os.path.isfile(path):
        raise SystemExit(f"cannot find upstream module: {path}")
    spec = importlib.util.spec_from_file_location("upstream_decoy_postfilter", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # register so dataclasses/typing behave
    spec.loader.exec_module(mod)
    required = ("main", "read_tsv", "house_no", "explode_matches", "f05",
                "STRONG", "WEAK", "HOUSE_NO")
    missing = [r for r in required if not hasattr(mod, r)]
    if missing:
        raise SystemExit(f"upstream module is missing {missing}; refusing to guess its behaviour")
    return mod


# --------------------------------------------------------------------------
# duckdb streaming layer
# --------------------------------------------------------------------------
SRC_COLS = ("{'entity_id':'VARCHAR','business_name':'VARCHAR',"
            "'business_address':'VARCHAR','country':'VARCHAR'}")
MATCH_COLS = ("{'source1_entity_id':'VARCHAR','matched_entity_ids':'VARCHAR'}")

STRONG = [3, 4, 5, 7, 9, 11, 13, 21]
WEAK = [1, 2]
ALL_OFF = STRONG + WEAK
_LAST_Q: dict = {}          # populated by print_sym_q; returned by the estimators


def _q(path: str) -> str:
    """Quote a filesystem path as a SQL literal."""
    return "'" + os.path.abspath(path).replace("\\", "/").replace("'", "''") + "'"


def _inlist(xs) -> str:
    return "(" + ",".join(str(int(x)) for x in xs) + ")"


def open_duckdb(tmpdir: str, mem_mb: int) -> "duckdb.DuckDBPyConnection":
    os.makedirs(tmpdir, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{int(mem_mb)}MB'")
    con.execute(f"SET temp_directory='{os.path.abspath(tmpdir).replace(chr(92), '/')}'")
    con.execute("SET threads=2")            # bound concurrent buffers
    con.execute("SET preserve_insertion_order=false")
    return con


def register_matching(con, matching: str) -> tuple:
    """Load the matching file once; derive the two id whitelists.

    The matching file is the ONLY thing that has to fit in RAM (it is ~23 MB
    for a full 1.73 M-row submission); the 509 MB / 506 MB sources do not.
    """
    con.execute(
        "CREATE OR REPLACE TABLE m_raw AS SELECT * FROM read_csv("
        + _q(matching)
        + ", delim='\\t', header=true, quote='', escape='', columns="
        + MATCH_COLS + ")"
    )
    con.execute("CREATE OR REPLACE TABLE m_s1 AS "
                "SELECT DISTINCT source1_entity_id AS s1 FROM m_raw")
    con.execute(
        "CREATE OR REPLACE TABLE m_rid AS SELECT DISTINCT rid FROM ("
        "  SELECT unnest(str_split(coalesce(matched_entity_ids,''), ',')) AS rid FROM m_raw"
        ") WHERE rid <> ''"
    )
    n_s1 = con.execute("SELECT count(*) FROM m_s1").fetchone()[0]
    n_rid = con.execute("SELECT count(*) FROM m_rid").fetchone()[0]
    return n_s1, n_rid


def _house_expr(house_re: str) -> str:
    """SQL that yields the house number with upstream's own regex."""
    return f"try_cast(regexp_extract(business_address, '{house_re}', 1) AS BIGINT)"


def stream_s1(con, path: str, house_re: str) -> "pl.DataFrame":
    """test_source1.tsv -> (entity_id, business_name, business_address, country)
    for rows referenced by the matching file only."""
    sql = (
        "SELECT entity_id, "
        "       '' AS business_name, "
        "       COALESCE(CAST(hn AS VARCHAR) || ' ', '') AS business_address, "
        "       country "
        "FROM (SELECT entity_id, country, " + _house_expr(house_re) + " AS hn "
        "      FROM read_csv(" + _q(path) +
        ", delim='\\t', header=true, quote='', escape='', columns=" + SRC_COLS + ") "
        "      WHERE entity_id IN (SELECT s1 FROM m_s1))"
    )
    return con.execute(sql).pl()


def stream_recs(con, path: str, house_re: str) -> "pl.DataFrame":
    """test_source{2,3}.tsv -> (entity_id, business_name, business_address, country)
    for rows referenced by matched_entity_ids only."""
    sql = (
        "SELECT entity_id, "
        "       '' AS business_name, "
        "       COALESCE(CAST(hn AS VARCHAR) || ' ', '') AS business_address, "
        "       country "
        "FROM (SELECT entity_id, country, " + _house_expr(house_re) + " AS hn "
        "      FROM read_csv(" + _q(path) +
        ", delim='\\t', header=true, quote='', escape='', columns=" + SRC_COLS + ") "
        "      WHERE entity_id IN (SELECT rid FROM m_rid))"
    )
    return con.execute(sql).pl()


def stream_train_countries(con, path: str) -> "pl.DataFrame":
    """train_source1.tsv -> DISTINCT country only (upstream uses nothing else)."""
    sql = ("SELECT DISTINCT country FROM read_csv(" + _q(path)
           + ", delim='\\t', header=true, quote='', escape='', columns="
           + SRC_COLS + ")")
    return con.execute(sql).pl()


def matching_frame(con) -> "pl.DataFrame":
    """The matching file as the 2-column Utf8 frame upstream's main() expects."""
    return con.execute(
        "SELECT source1_entity_id, coalesce(matched_entity_ids, '') AS matched_entity_ids FROM m_raw"
    ).pl()


# --------------------------------------------------------------------------
# +k / -k asymmetry baseline  (TEST-SIDE ONLY, no labels of any kind)
# --------------------------------------------------------------------------
# WHY NO LABELS ARE NEEDED
#   The estimator never reads ground truth. It runs on the model's OWN
#   predicted pairs: for a candidate pair the house-number delta is
#   d = h(record) - h(S1). Generator decoys only ever produce POSITIVE d
#   (fixed offsets +1,+2,+3,+4,+5,+7,+9,+11,+13,+21); true-match number noise
#   is typo-like and SYMMETRIC, so it contributes equally to count(+k) and
#   count(-k) and cancels in the difference. Hence
#
#       q_k = (count(+k) - count(-k)) / count(+k)
#
#   estimates the decoy share of the +k class, and the negative baseline is
#   simply the model's own -k output for that country. This is the same
#   quantity upstream's v6 `hidden_offset_rule` estimates at run time per
#   (country, shared) cell, with min_q = 0.5.
LEGAL_TOKENS = (
    "sarl|sas|sasu|sa|sca|scs|eurl|eurpl|sci|sel|snc|sp|mon|selarl|scea|gie|association|fondation|"
    "llc|inc|corp|co|ltd|lp|llp|plc|pc|pa|group|company|holdings|pvt|private|and|sons|enterprises|"
    "industries|traders|associates|solutions|services|technologies|the|of|de|la|le|du|des|les|et|un|une"
)


def materialise_house_tables(con, dataset: str, house_re: str) -> None:
    """Persist (entity_id, country, house_no) for referenced rows only.

    Both 509 MB / 506 MB sources are streamed with the semi-join pushed into
    the plan, so only matched rows are ever held.
    """
    test = os.path.join(dataset, "test")

    def rd(name):
        return ("read_csv(" + _q(name) + ", delim='\\t', header=true, quote='', escape='', columns="
                + SRC_COLS + ")")

    con.execute(
        "CREATE OR REPLACE TABLE h_s1 AS SELECT entity_id, country, " + _house_expr(house_re)
        + " AS hn FROM " + rd(os.path.join(test, "test_source1.tsv"))
        + " WHERE entity_id IN (SELECT s1 FROM m_s1)"
    )
    con.execute(
        "CREATE OR REPLACE TABLE h_rec AS SELECT entity_id, " + _house_expr(house_re)
        + " AS hn FROM (SELECT entity_id, business_address FROM " + rd(os.path.join(test, "test_source2.tsv"))
        + " UNION ALL SELECT entity_id, business_address FROM " + rd(os.path.join(test, "test_source3.tsv"))
        + ") WHERE entity_id IN (SELECT rid FROM m_rid)"
    )


def print_sym_q(con, hist_sql: str, label: str, min_q: float = 0.5) -> dict:
    """hist_sql must expose columns (country, d, n). Returns {country: q}."""
    sql = (
        "SELECT country, "
        "  sum(CASE WHEN d IN " + _inlist(ALL_OFF) + " THEN n ELSE 0 END) AS plus, "
        "  sum(CASE WHEN d IN " + _inlist([-x for x in ALL_OFF]) + " THEN n ELSE 0 END) AS minus, "
        "  sum(CASE WHEN d = 0 THEN n ELSE 0 END) AS d0, sum(n) AS total "
        "FROM (" + hist_sql + ") GROUP BY country ORDER BY country"
    )
    rows = con.execute(sql).fetchall()
    out_q: dict = {}
    globals()["_LAST_Q"] = out_q
    print(f"\n  [{label}]  +k/-k asymmetry, TEST-side only (no labels used)")
    print("    formula: q = (count(+k) - count(-k)) / count(+k);"
          " the -k baseline is the")
    print("    model's own negative-offset output, so no ground truth is involved.")
    if not rows:
        print("    (no candidate pairs with parsable house numbers)")
        return out_q
    hdr = (f"    {'country':<10} {'pairs':>12} {'d==0':>12} {'count(+k)':>12} "
           f"{'count(-k)':>12} {'q':>8}  verdict")
    print(hdr)
    for country, plus, minus, d0, total in rows:
        q = (plus - minus) / plus if plus else float("nan")
        verdict = "DECOY-LIKE" if (plus and q >= min_q) else ("weak" if plus else "n/a")
        print(f"    {str(country):<10} {total:>12,} {d0:>12,} {plus:>12,} {minus:>12,} "
              f"{q:>8.4f}  {verdict}")
        if plus:
            out_q[str(country)] = q
    return out_q


def estimate_model_side(con, min_q: float = 0.5) -> None:
    """q over the pairs the model actually predicted (v6-style, label-free)."""
    hist = (
        "SELECT s1.country AS country, r.hn - s1.hn AS d, count(*) AS n "
        "FROM (SELECT source1_entity_id AS s1id, "
        "             unnest(str_split(coalesce(matched_entity_ids,''), ',')) AS rid "
        "      FROM m_raw) p "
        "JOIN h_s1 s1 ON s1.entity_id = p.s1id "
        "JOIN h_rec r  ON r.entity_id = p.rid "
        "WHERE p.rid <> '' AND s1.hn IS NOT NULL AND r.hn IS NOT NULL "
        "  AND (r.hn - s1.hn) BETWEEN -30 AND 30 "
        "GROUP BY 1, 2"
    )
    print_sym_q(con, hist, "model-side: predicted pairs", min_q)
    return _LAST_Q


def estimate_structural(con, dataset: str, house_re: str, min_q: float = 0.5) -> None:
    """q over name+street-blocked candidate pairs - the decoy signature.

    Independent of the model: same name (legal suffix stripped) AND same
    street. This is the quantity that measured 0.9689 for France on the real
    test set, and it survives a weak or empty model.
    """
    test = os.path.join(dataset, "test")
    skey = ("regexp_replace(lower(regexp_replace(business_address, '[0-9]+', ' ', 'g')),"
            "'[^a-z ]+', ' ', 'g')")
    nkey = ("array_to_string(list_sort(list_filter(regexp_extract_all("
            "lower(business_name),'[a-z]{2,}'), "
            "x -> NOT regexp_matches(x, '^(?:" + LEGAL_TOKENS + ")$'))), ' ')")

    def src(name):
        return ("SELECT business_name, business_address, " + skey + " AS skey, " + nkey
                + " AS nkey, " + _house_expr(house_re) + " AS hn FROM read_csv(" + _q(name)
                + ", delim='\\t', header=true, quote='', escape='', columns=" + SRC_COLS + ")")

    con.execute("CREATE OR REPLACE TEMP TABLE a1 AS SELECT nkey, skey, hn, count(*) n FROM ("
                + src(os.path.join(test, "test_source1.tsv"))
                + ") WHERE hn IS NOT NULL AND nkey <> '' GROUP BY 1,2,3")
    con.execute("CREATE OR REPLACE TEMP TABLE r1 AS SELECT nkey, skey, hn, count(*) n FROM ("
                + src(os.path.join(test, "test_source2.tsv")) + " UNION ALL "
                + src(os.path.join(test, "test_source3.tsv"))
                + ") WHERE hn IS NOT NULL AND nkey <> '' GROUP BY 1,2,3")
    hist = ("SELECT 'ALL' AS country, b.hn - a.hn AS d, sum(a.n * b.n) AS n "
            "FROM a1 a JOIN r1 b ON a.nkey = b.nkey AND a.skey = b.skey "
            "WHERE (b.hn - a.hn) BETWEEN -30 AND 30 GROUP BY 1, 2")
    print_sym_q(con, hist, "structural: name+street blocked", min_q)
    con.execute("DROP TABLE IF EXISTS a1")
    con.execute("DROP TABLE IF EXISTS r1")
    return _LAST_Q


# --------------------------------------------------------------------------
# blast radius (dry run)
# --------------------------------------------------------------------------
def _expected_f05_delta(m: int, r: int, qbar: float, f05) -> float:
    """Upstream's own expected-F0.5 gate arithmetic, for reporting only.

    Mirrors decoy_postfilter.ev_select(): E[F0.5 after removing all r
    candidates] - E[F0.5 keeping all r]. It decides nothing here (v4 is
    ungated); it is printed so the blast radius can be judged.
    """
    from math import comb
    return sum(
        comb(r, j) * qbar**j * (1 - qbar) ** (r - j)
        * (f05(m - r, 0, r - j) - f05(m - j, j, 0))
        for j in range(r + 1)
    )


def _normalise_removed(df: "pl.DataFrame") -> "pl.DataFrame":
    """Upstream renames to audit headers before write_csv; map back to canonical."""
    if df is None:
        return None
    have = set(df.columns)
    s1c = "s1" if "s1" in have else "source1_entity_id"
    ridc = "rid" if "rid" in have else "removed_entity_id"
    dc = "d" if "d" in have else "house_number_offset"
    rn = "business_name" if "business_name" in have else "removed_name"
    ra = "business_address" if "business_address" in have else "removed_address"
    return df.select(
        pl.col(s1c).cast(pl.Utf8).alias("s1"),
        pl.col(ridc).cast(pl.Utf8).alias("rid"),
        pl.col("country").cast(pl.Utf8).alias("country"),
        pl.col(dc).cast(pl.Float64).alias("d"),
        pl.col("s1_name").cast(pl.Utf8) if "s1_name" in have else pl.lit("", dtype=pl.Utf8).alias("s1_name"),
        pl.col("s1_address").cast(pl.Utf8) if "s1_address" in have else pl.lit("", dtype=pl.Utf8).alias("s1_address"),
        pl.col(rn).cast(pl.Utf8).alias("removed_name"),
        pl.col(ra).cast(pl.Utf8).alias("removed_address"),
    )


def _kept_pairs(out: "pl.DataFrame") -> "pl.DataFrame":
    return (out.select("source1_entity_id", pl.col("matched_entity_ids").fill_null(""))
               .with_columns(pl.col("matched_entity_ids").str.split(","))
               .explode("matched_entity_ids")
               .filter(pl.col("matched_entity_ids").is_not_null() & (pl.col("matched_entity_ids") != ""))
               .rename({"source1_entity_id": "s1", "matched_entity_ids": "rid"}))


def report_blast_radius(removed, out, f05, q_by_country: dict) -> None:
    """Print exactly what WOULD be removed, before anything is written."""
    print("\n" + "=" * 78)
    print("BLAST RADIUS  (dry run - nothing has been written)")
    print("=" * 78)
    if removed is None or removed.height == 0:
        print("  no pairs would be removed.")
        return

    rem = removed.select("s1", "rid", "country", "d")
    kept = _kept_pairs(out)
    pairs_in = rem.height + kept.height
    print(f"\n  pairs in               : {pairs_in:,}")
    print(f"  pairs WOULD be removed : {rem.height:,}"
          f"  ({100.0 * rem.height / pairs_in if pairs_in else 0:.2f}% of pairs)")

    m_in = (rem.group_by("s1").len().rename({"len": "r"})
            .join(kept.group_by("s1").len().rename({"len": "k"}), on="s1", how="full", coalesce=True)
            .with_columns(pl.col("r").fill_null(0).cast(pl.Int64),
                          pl.col("k").fill_null(0).cast(pl.Int64)))
    m_in = m_in.with_columns((pl.col("r") + pl.col("k")).alias("m"))   # total predicted BEFORE removal
    j = m_in

    print(f"\n  {'country':<12} {'pairs removed':>14} {'S1 emptied 1->0':>17} "
          f"{'S1 reduced m->m-r':>18} {'q':>9}  verdict")
    tot_sing = tot_emp = 0
    affected = {}
    for ctry in sorted(rem["country"].unique().to_list()):
        s1_c = rem.filter(pl.col("country") == ctry).select("s1").unique()["s1"]
        jj = j.filter(pl.col("s1").is_in(s1_c))
        emptied = jj.filter((pl.col("m") == 1) & (pl.col("k") == 0)).height
        reduced = jj.filter((pl.col("m") > 1) & (pl.col("k") > 0)).height
        singles = jj.filter(pl.col("m") == 1).height
        tot_sing += singles
        tot_emp += emptied
        affected[ctry] = jj
        q = q_by_country.get(ctry)
        qtxt = f"{q:.4f}" if q is not None else "n/a"
        if q is None:
            verdict = "no asymmetry data - inspect offsets"
        elif emptied and q < 0.51:
            verdict = "RISKY: empties singletons at q<0.51"
        elif q >= 0.51:
            verdict = "OK: q>=0.51, safe even for singletons"
        else:
            verdict = "OK: no singleton emptied"
        print(f"  {str(ctry):<12} {rem.filter(pl.col('country') == ctry).height:>14,} "
              f"{emptied:>17,} {reduced:>18,} {qtxt:>9}  {verdict}")

    print("\n  SINGLETON RISK (the macro-F0.5 trap): a true singleton scores 1.0 when")
    print("  empty and 0.0 for any match, so wrongly emptying one costs a full 1.0.")
    if tot_sing:
        print(f"    S1 with exactly 1 predicted pair : {tot_sing:,}")
        print(f"    of those, emptied by this rule   : {tot_emp:,}  "
              f"({100.0 * tot_emp / tot_sing:.2f}%)")
    else:
        print("    (none)")

    print("\n  removed by (country, house_number_offset) - uniform over the offset list"
          "\n  is the generator's decoy signature; typo-like noise would peak at +/-1,2:")
    cur = None
    for country, d, n in rem.group_by(["country", "d"]).len().sort(["country", "d"]).iter_rows():
        if country != cur:
            cur = country
            print(f"    {country}:")
        tag = "STRONG" if d in STRONG else ("weak" if d in WEAK else "other")
        print(f"      d={int(d):>4} ({tag:<6}) {n:>8,}")

    print("\n  expected per-S1 F0.5 change under upstream's own gate arithmetic:")
    for ctry, jj in affected.items():
        r_tot = int(jj["r"].sum())
        if r_tot <= 0:
            continue
        q = q_by_country.get(ctry, 1.0)
        ev = sum(_expected_f05_delta(int(m), int(r), q, f05)
                 for m, r in zip(jj["m"], jj["r"]) if r > 0)
        print(f"    {str(ctry):<12} n_S1_affected={jj.height:>7,}  removed_pairs={r_tot:>7,}  "
              f"sum E[dF0.5] = {ev:+.2f}   (positive => removal should help)")


# --------------------------------------------------------------------------
# driver: patch ONLY the I/O, then run upstream's own main()
# --------------------------------------------------------------------------
def install_streaming_read_tsv(dpf, con, dataset: str, house_re: str) -> dict:
    """Replace upstream's eager read_tsv with the streaming reader.

    Upstream's main() is untouched; every rule, constant and helper it uses
    (STRONG, WEAK, house_no, explode_matches, rule (a)/(b)) is executed from
    the upstream source.
    """
    test = os.path.join(dataset, "test")
    train = os.path.join(dataset, "train")
    cache: dict = {}

    def read_tsv(path, *args, **kwargs):
        key = os.path.normcase(os.path.abspath(str(path)))
        if key in cache:
            return cache[key]
        base = os.path.basename(key)
        if key == os.path.normcase(os.path.abspath(test)) and base == "test_source1.tsv":
            frame = stream_s1(con, path, house_re)
        elif base in ("test_source2.tsv", "test_source3.tsv"):
            frame = stream_recs(con, path, house_re)
        elif base == "train_source1.tsv":
            frame = stream_train_countries(con, path)
        elif base in ("matching_results.tsv",) or key.endswith(".tsv") and "matched" in base:
            frame = matching_frame(con)
        else:
            # the matching file (2 Utf8 columns) - small by construction
            frame = pl.read_csv(path, separator="\t", quote_char=None, infer_schema=False)
        cache[key] = frame
        return frame

    dpf.read_tsv = read_tsv
    return cache


def enrich_removed(con, dataset: str, removed: "pl.DataFrame") -> "pl.DataFrame":
    """Fill the audit columns with the REAL name/address.

    Only the removed pairs are re-fetched (a few thousand rows), so the big
    sources are scanned a second time but never materialised.
    """
    if removed is None or removed.height == 0:
        return removed
    pairs = removed.select("s1", "rid")
    con.register("rem_pairs", pairs)
    test = os.path.join(dataset, "test")

    def lookup(name, key, alias_n, alias_a, join_col):
        sql = ("SELECT r." + join_col + ", t.business_name AS " + alias_n
               + ", t.business_address AS " + alias_a
               + " FROM rem_pairs r JOIN read_csv(" + _q(name)
               + ", delim='\\t', header=true, quote='', escape='', columns=" + SRC_COLS
               + ") t ON t.entity_id = r." + key)
        return sql

    s1q = (lookup(os.path.join(test, "test_source1.tsv"), "s1", "s1_name", "s1_address", "s1")
           + " UNION ALL "
           + lookup(os.path.join(test, "test_source2.tsv"), "s1", "s1_name", "s1_address", "s1")
           + " UNION ALL "
           + lookup(os.path.join(test, "test_source3.tsv"), "s1", "s1_name", "s1_address", "s1"))
    recq = (lookup(os.path.join(test, "test_source2.tsv"), "rid", "removed_name", "removed_address", "rid")
            + " UNION ALL "
            + lookup(os.path.join(test, "test_source3.tsv"), "rid", "removed_name", "removed_address", "rid"))
    con.execute("CREATE OR REPLACE TEMP TABLE lk_s1 AS " + s1q)
    con.execute("CREATE OR REPLACE TEMP TABLE lk_r AS " + recq)
    # drop the placeholders first, otherwise the join makes *_right suffixed columns
    df = (removed.drop(["s1_name", "s1_address", "removed_name", "removed_address"])
               .join(con.execute("SELECT * FROM lk_s1").pl(), on="s1", how="left")
               .join(con.execute("SELECT * FROM lk_r").pl(), on="rid", how="left"))
    con.unregister("rem_pairs")
    con.execute("DROP TABLE IF EXISTS lk_s1")
    con.execute("DROP TABLE IF EXISTS lk_r")
    return df


# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="decoy_shim.py",
        description="Memory-safe driver for _upstream/src/decoy_postfilter.py (v4 rules).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--matching", required=True, help="matching_results.tsv to filter")
    ap.add_argument("--dataset", required=True, help="student_resource/dataset (has train/ and test/)")
    ap.add_argument("--out", required=True, help="filtered matching_results.tsv to write")
    ap.add_argument("--removed", default=None, help="audit TSV of removed pairs")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the blast radius and write nothing")
    ap.add_argument("--structural", action="store_true",
                    help="also run the model-independent name+street asymmetry estimate")
    ap.add_argument("--upstream", default=DEFAULT_SRC, help="path to decoy_postfilter.py")
    ap.add_argument("--duckdb-mem-mb", type=int, default=256, help="duckdb memory_limit (default 256)")
    ap.add_argument("--tmpdir", default=None, help="duckdb spill directory")
    ap.add_argument("--min-q", type=float, default=0.5, help="verdict threshold (default 0.5)")
    return ap


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    try:                                     # Windows consoles default to cp1252
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if not os.path.isfile(a.matching):
        raise SystemExit(f"not found: {a.matching}")
    for sub in ("test/test_source1.tsv", "test/test_source2.tsv",
                "test/test_source3.tsv", "train/train_source1.tsv"):
        if not os.path.isfile(os.path.join(a.dataset, *sub.split("/"))):
            raise SystemExit(f"dataset is missing {sub}: {a.dataset}")

    t0 = time.time()
    dpf = load_upstream(a.upstream)
    print(f"upstream module : {a.upstream}")
    print(f"  HOUSE_NO      : {dpf.HOUSE_NO}")
    print(f"  STRONG        : {dpf.STRONG}")
    print(f"  WEAK          : {dpf.WEAK}")
    print("  rule stages   : v4 only (rules a+b, ungated). --extra/--hidden are")
    print("                  intentionally not exposed - see module docstring.")

    tmpdir = a.tmpdir or os.path.join(
        os.path.dirname(os.path.abspath(a.out)) or ".", "_decoy_shim_tmp")
    con = open_duckdb(tmpdir, a.duckdb_mem_mb)
    print("\nprojection (only what the rules need):")
    print("  test_source1.tsv : entity_id, country, house_no  (rows in matching file only)")
    print("  test_source2.tsv : entity_id, house_no           (rids in matched_entity_ids only)")
    print("  test_source3.tsv : entity_id, house_no           (rids in matched_entity_ids only)")
    print("  train_source1.tsv: country                       (DISTINCT only)")
    print(f"duckdb memory_limit = {a.duckdb_mem_mb} MB, spill -> {tmpdir}")

    n_s1, n_rid = register_matching(con, a.matching)
    print(f"\nmatching file     : {a.matching}")
    print(f"  rows={con.execute('SELECT count(*) FROM m_raw').fetchone()[0]:,}"
          f"  distinct s1={n_s1:,}  distinct rid={n_rid:,}")

    house_re = dpf.HOUSE_NO
    materialise_house_tables(con, a.dataset, house_re)

    print("\n" + "-" * 78)
    print("ASYMMETRY BASELINE (+k/-k, estimated from TEST-side data only)")
    print("-" * 78)
    q_by_country = estimate_model_side(con, a.min_q)
    if a.structural:
        estimate_structural(con, a.dataset, house_re, a.min_q)
    print(f"\n  q per country (used for the risk verdicts): "
          f"{ {k: round(v, 4) for k, v in q_by_country.items()} }")

    install_streaming_read_tsv(dpf, con, a.dataset, house_re)

    captured: dict = {}
    real_write_csv = pl.DataFrame.write_csv

    def capture(self, file=None, *args, **kwargs):
        captured[os.path.abspath(str(file))] = self
        return None

    out_arg = os.path.join(tmpdir, "__dryrun_out.tsv") if a.dry_run else a.out
    rem_arg = os.path.join(tmpdir, "__dryrun_removed.tsv")
    saved_argv = sys.argv
    sys.argv = ["decoy_postfilter.py", "--matching", a.matching, "--dataset", a.dataset,
                "--out", out_arg, "--removed", rem_arg]
    print("\n" + "-" * 78)
    print("RUNNING UPSTREAM main()  (rules executed by upstream source, streaming I/O)")
    print("-" * 78)
    pl.DataFrame.write_csv = capture
    try:
        dpf.main()
    except SystemExit:
        pass
    finally:
        sys.argv = saved_argv
        pl.DataFrame.write_csv = real_write_csv

    out_df = captured.get(os.path.abspath(out_arg))
    removed_df = _normalise_removed(captured.get(os.path.abspath(rem_arg)))
    if out_df is None:
        raise SystemExit("upstream main() did not produce an output frame")

    report_blast_radius(removed_df, out_df, dpf.f05, q_by_country)

    if a.dry_run:
        print("\nDRY RUN: nothing was written. Re-run without --dry-run to commit.")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        out_df.write_csv(a.out, separator="\t", quote_style="never")
        print(f"\nwrote {a.out}  ({out_df.height:,} rows)")
        if a.removed:
            audit = (enrich_removed(con, a.dataset, removed_df) if removed_df.height
                     else removed_df)
            audit = audit.select(
                pl.col("s1").alias("source1_entity_id"),
                pl.col("rid").alias("removed_entity_id"),
                "country", pl.col("d").alias("house_number_offset"),
                "s1_name", "s1_address", "removed_name", "removed_address",
            ).sort("source1_entity_id")
            audit.write_csv(a.removed, separator="\t", quote_style="never")
            print(f"wrote {a.removed}  ({audit.height:,} rows, real names/addresses)")

    print(f"\npeak RSS = {peak_mb():.0f} MB   wall = {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())






