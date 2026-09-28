"""Tests for postprocess.py.

Two things must hold:
  1. postprocess() only ever REMOVES pairs (it cannot invent a match).
  2. resolve_conflicts() agrees with the measured ground-truth structure: one
     S2/S3 record belongs to at most one S1, so keeping the best-scoring claim
     per record is the best available single decision.

Also checks f05_entity() against the scorer definition in metrics.py, since a
mismatch there would silently mis-rank every decision.

Run: & .venv\\Scripts\\python.exe test_postprocess.py
"""
import os
import sys

import polars as pl

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "run_src", "src"))
import postprocess as P  # noqa: E402
from metrics import macro_f05  # noqa: E402

fails = []


def eq(label, got, want):
    if got != want:
        fails.append(f"{label}: got {got!r} want {want!r}")


def close(label, got, want, tol=1e-9):
    if abs(got - want) > tol:
        fails.append(f"{label}: got {got!r} want ~{want!r}")


# --- f05_entity must match the scorer ------------------------------------
eq("f05 empty/empty = 1.0", P.f05_entity(0, 0, 0), 1.0)
eq("f05 pred/empty = 0.0", P.f05_entity(2, 0, 0), 0.0)
eq("f05 empty/true  = 0.0", P.f05_entity(0, 2, 0), 0.0)
# the README's own worked example
close("f05 README example", P.f05_entity(3, 2, 2), 0.7142857, 1e-6)
# a perfect prediction
close("f05 perfect", P.f05_entity(2, 2, 2), 1.0)

# cross-check against the real scorer on a tiny frame
s1_ids = pl.DataFrame({"s1": [1, 2, 3]})
truth = pl.DataFrame({"s1": [1, 2, 3], "rid": [10, 20, 30]})
pred = pl.DataFrame({"s1": [1, 2, 3], "rid": [10, 20, 99]})
close("macro_f05 agrees on 3 entities", macro_f05(pred, truth, s1_ids),
      2.0 / 3.0, 1e-9)

# --- resolve_conflicts ----------------------------------------------------
pairs = pl.DataFrame({
    "s1":   [1, 1, 2, 2, 3],
    "rid":  [10, 11, 10, 12, 13],
    "p2":   [0.9, 0.8, 0.4, 0.7, 0.5],
})
out = P.resolve_conflicts(pairs)
# rid 10 is contested (s1=1 @0.9 vs s1=2 @0.4): s1=1 must win
got = {(r["s1"], r["rid"]) for r in out.iter_rows(named=True)}
eq("contested record goes to best score", (1, 10) in got, True)
eq("contested loser dropped", (2, 10) in got, False)
# uncontested records all survive
eq("uncontested survive", len(out), 4)
# no record appears twice
eq("one row per record", out.height, out["rid"].n_unique())

# a tie must resolve deterministically to the lower s1
tie = pl.DataFrame({"s1": [5, 2], "rid": [7, 7], "p2": [0.5, 0.5]})
eq("tie breaks to lower s1", P.resolve_conflicts(tie)["s1"].item(), 2)

# empty input must not explode
eq("empty input", P.resolve_conflicts(pairs.head(0)).height, 0)

# --- safety property: output is always a subset of input ------------------
import random  # noqa: E402

random.seed(3)
for trial in range(200):
    n = random.randint(0, 60)
    p = pl.DataFrame({
        "s1": [random.randint(1, 8) for _ in range(n)],
        "rid": [random.randint(1, 10) for _ in range(n)],
        "p2": [round(random.random(), 3) for _ in range(n)],
    })
    for ms in (None, 0.5, 0.9):
        o = P.postprocess(p, min_score=ms)
        in_set = set(map(tuple, p.select("s1", "rid").iter_rows()))
        out_set = set(map(tuple, o.select("s1", "rid").iter_rows()))
        if not out_set <= in_set:
            fails.append(f"trial {trial} ms={ms}: postprocess INVENTED pairs")
            break
        if ms is not None and o.height > p.height:
            fails.append(f"trial {trial} ms={ms}: postprocess grew the pair set")

# --- min_score ordering: cut BEFORE resolving ---------------------------
# A weak claim must not win a record and block a stronger one.  With rid 10
# contested by s1=1 @0.10 and s1=2 @0.90, min_score=0.5 must let s1=2 win.
contested = pl.DataFrame({"s1": [1, 2], "rid": [10, 10],
                          "p2": [0.10, 0.90]})
res = P.postprocess(contested, min_score=0.5)
eq("weak claim cut before resolve", res["s1"].item(), 2)
res2 = P.postprocess(contested, min_score=None)
eq("no cut keeps the best", res2["s1"].item(), 2)

# --- resolving can only help when ground truth is a star ----------------
# Contested rid 10, true owner is s1=1.  Resolving keeps s1=1, so the false
# positive on s1=2 disappears and s1=2 becomes a correct singleton.
pairs2 = pl.DataFrame({"s1": [1, 2], "rid": [10, 10], "p2": [0.9, 0.4]})
tr = pl.DataFrame({"s1": [1], "rid": [10]})
univ = pl.DataFrame({"s1": [1, 2]})
f_before = macro_f05(pairs2, tr, univ)
f_after = macro_f05(P.resolve_conflicts(pairs2), tr, univ)
close("resolve raises macro F0.5 on a star truth", f_after, 1.0, 1e-9)
if f_after <= f_before:
    fails.append(f"resolve did not improve: {f_before} -> {f_after}")

# and it must not hurt when the higher score is the correct one
pairs3 = pl.DataFrame({"s1": [1, 2], "rid": [10, 10], "p2": [0.4, 0.9]})
tr3 = pl.DataFrame({"s1": [2], "rid": [10]})
f3 = macro_f05(P.resolve_conflicts(pairs3), tr3, univ)
close("resolve picks the true owner when it scores higher", f3, 1.0, 1e-9)

if fails:
    print("FAIL")
    for f in fails:
        print("  " + f)
    raise SystemExit(1)
print("all postprocess tests passed")


# --- check_invariants ----------------------------------------------------
good = pl.DataFrame({"s1": [1, 1, 2], "rid": [10, 11, 12], "p2": [0.9, 0.8, 0.7]})
univ2 = pl.DataFrame({"s1": [1, 2, 3]})
inv = P.check_invariants(good, univ2)
eq("invariants ok on clean data", inv["ok"], True)
eq("invariants count records", inv["distinct_records"], 3)
eq("invariants count contested", inv["records_claimed_more_than_once"], 0)
eq("invariants count s1 with pairs", inv["s1_with_at_least_one_pair"], 2)
eq("invariants count s1 with none", inv["s1_with_no_pair"], 1)

bad = pl.DataFrame({"s1": [1, 2], "rid": [10, 10], "p2": [0.9, 0.8]})
invb = P.check_invariants(bad, univ2)
eq("invariants flag a contested record", invb["records_claimed_more_than_once"], 1)
eq("invariants not ok on bad data", invb["ok"], False)

unknown = pl.DataFrame({"s1": [99], "rid": [10], "p2": [0.5]})
invu = P.check_invariants(unknown, univ2)
eq("invariants flag an unknown s1", invu["pairs_with_unknown_s1"], 1)
eq("invariants not ok on unknown s1", invu["ok"], False)

eq("invariants on empty table", P.check_invariants(good.head(0), univ2)["ok"], True)

# --- the pipeline already satisfies this, by construction ---------------
# stage2.best_pairs() groups by rid and takes .first(), so it can only ever
# emit ONE s1 per rid.  Assert that here so the invariant is not a duplicate
# of something already guaranteed -- and so a future change to best_pairs
# that breaks it fails here first.
import stage2  # noqa: E402

pred = pl.DataFrame({"rid": [10, 10, 11], "s1": [1, 2, 3], "p1": [0.9, 0.4, 0.7]})
bp = stage2.best_pairs(pred)
eq("stage2.best_pairs emits one row per rid", bp.height, bp["rid"].n_unique())
eq("stage2.best_pairs keeps the argmax", bp.filter(pl.col("rid") == 10)["s1"].item(), 1)
eq("best_pairs output passes the invariant",
   P.check_invariants(bp.select("s1", "rid"), univ2)["records_claimed_more_than_once"], 0)

# --- macro_f05_local must equal the real scorer -------------------------
# If these diverge, sweep_threshold would optimise the wrong objective, so the
# agreement is asserted over random cases rather than assumed.
import random as _rnd  # noqa: E402

_rnd.seed(11)
for trial in range(25):
    n_s1 = _rnd.randint(3, 12)
    n_rec = _rnd.randint(5, 30)
    univ = pl.DataFrame({"s1": list(range(n_s1))})
    sch = {"s1": pl.UInt64, "rid": pl.UInt64}
    tr_rows = [(s, _rnd.randrange(n_rec)) for s in range(n_s1)
               for _ in range(_rnd.randint(0, 3))]
    pr_rows = [(s, _rnd.randrange(n_rec)) for s in range(n_s1)
               for _ in range(_rnd.randint(0, 3))]
    tdf = (pl.DataFrame(tr_rows, schema=sch, orient="row") if tr_rows
           else pl.DataFrame({"s1": [], "rid": []}, schema=sch))
    pdf = (pl.DataFrame(pr_rows, schema=sch, orient="row") if pr_rows
           else pl.DataFrame({"s1": [], "rid": []}, schema=sch))
    want = macro_f05(pdf, tdf, univ)
    got = P.macro_f05_local(pdf, tdf, univ)
    if abs(want - got) > 1e-9:
        fails.append(f"macro_f05_local disagrees with metrics.macro_f05 on "
                     f"trial {trial}: {got} vs {want}")
        break

# A duplicated prediction row must be penalised, not silently ignored -- the
# scorer's list.set_intersection counts the repeat as an extra false positive
# (0.778 rather than 1.0).  macro_f05_local must reproduce that exactly, so the
# assertion is that it MATCHES the real scorer, not that it "fixes" anything.
dup = pl.DataFrame({"s1": [1, 1, 2], "rid": [10, 10, 20]})
t1b = pl.DataFrame({"s1": [1, 2], "rid": [10, 20]})
u1b = pl.DataFrame({"s1": [1, 2]})
close("duplicate rows penalised identically to the scorer",
      P.macro_f05_local(dup, t1b, u1b),
      macro_f05(dup, t1b, u1b), 1e-9)
if P.macro_f05_local(dup.unique(), t1b, u1b) <= P.macro_f05_local(dup, t1b, u1b):
    fails.append("de-duplicating a prediction should RAISE macro_f05_local")

# predicting nothing: the true singleton scores 1.0, the missed entity 0.0
allnone = pl.DataFrame({"s1": [], "rid": []},
                       schema={"s1": pl.UInt64, "rid": pl.UInt64})
t2b = pl.DataFrame({"s1": [1], "rid": [10]})
u2b = pl.DataFrame({"s1": [1, 2]})
close("empty prediction: singleton 1.0, missed entity 0.0",
      P.macro_f05_local(allnone, t2b, u2b), 0.5, 1e-9)

# --- sweep_threshold -----------------------------------------------------
pairs3 = pl.DataFrame({
    "s1":  [1, 1, 2, 2, 3],
    "rid": [10, 11, 20, 21, 30],
    "p2":  [0.95, 0.55, 0.40, 0.85, 0.10],
})
truth3 = pl.DataFrame({"s1": [1, 1, 2], "rid": [10, 11, 21]})
univ3 = pl.DataFrame({"s1": [1, 2, 3]})   # s1=3 is a true singleton
sw = P.sweep_threshold(pairs3, truth3, univ3, grid=[0.1, 0.5, 0.6, 0.9])
eq("sweep returns one row per grid point", sw.height, 4)
r01 = sw.filter(pl.col("thr") == 0.1)["f05"].item()
r09 = sw.filter(pl.col("thr") == 0.9)["f05"].item()
if not (r09 > r01):
    fails.append(f"raising the threshold did not help: {r01} -> {r09}")
pc = sw["pairs"].to_list()
if pc != sorted(pc, reverse=True):
    fails.append(f"pair count not monotone in threshold: {pc}")
for row in sw.iter_rows(named=True):
    direct = P.macro_f05_local(
        P.resolve_conflicts(pairs3.filter(pl.col("p2") >= row["thr"])),
        truth3, univ3)
    if abs(direct - row["f05"]) > 1e-9:
        fails.append(f"sweep f05 mismatch at thr={row['thr']}")
        break



if fails:
    print("FAIL")
    for f in fails:
        print("  " + f)

# --- sanity_check_metrics ------------------------------------------------
# Guards the reporting layer, not the computation.  It exists because one run
# reported edge_recall = 4.39, impossible for a ratio of counts.
if not P.sanity_check_metrics({"edge_recall": 4.391}):
    fails.append("sanity_check_metrics missed an out-of-range recall")
if not P.sanity_check_metrics({"f05": 1.4}):
    fails.append("sanity_check_metrics missed an out-of-range f05")
if not P.sanity_check_metrics({"singleton_rate": -0.1}):
    fails.append("sanity_check_metrics missed a negative rate")
if not P.sanity_check_metrics({"median_cands": 10, "mean_cands": 2}):
    fails.append("sanity_check_metrics missed median > mean")
_good = P.sanity_check_metrics({"edge_recall": 0.81, "f05": 0.72,
                                "singleton_rate": 0.055,
                                "mean_cands": 5.0, "median_cands": 2,
                                "pairs": 100})
if _good:
    fails.append(f"sanity_check_metrics false-positived: {_good}")
# booleans, None and non-numeric values must be ignored, not crash it
if P.sanity_check_metrics({"edge_recall": True, "f05": None,
                           "rows": 10, "keys": ["a"]}):
    fails.append("sanity_check_metrics mis-handled non-numeric values")


    raise SystemExit(1)
print("all postprocess tests passed")

