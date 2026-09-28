"""Integration check: postprocess works on the REAL pipeline's table shapes.

test_postprocess.py proves the logic on toy frames. This checks the column
names and dtypes that stage2.build() and make_submission.py actually produce,
so the module can be dropped in without a silent KeyError at scoring time.

Read-only. No model, no features: it only exercises schema compatibility.
"""
import os
import sys

import polars as pl

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "run_src", "src"))
import postprocess as P  # noqa: E402
import stage2  # noqa: E402

fails = []


def eq(label, got, want):
    if got != want:
        fails.append(f"{label}: got {got!r} want {want!r}")


# --- the shape stage2.best_pairs() returns ------------------------------
pred = pl.DataFrame({
    "rid": [10, 10, 11, 12],
    "s1":  [1, 2, 3, 4],
    "p1":  [0.91, 0.22, 0.77, 0.05],
})
best = stage2.best_pairs(pred)
eq("best_pairs columns", set(best.columns) >= {"rid", "s1", "p1"}, True)
eq("best_pairs one row per rid", best.height, 3)

# postprocess must accept that frame using the pipeline's own column names
pairs = best.select("s1", "rid", "p1")
out = P.postprocess(pairs, score_col="p1", s1_col="s1", rec_col="rid")
eq("postprocess keeps best_pairs height", out.height, 3)
eq("postprocess preserves columns", set(out.columns) == {"s1", "rid", "p1"}, True)
eq("postprocess keeps the argmax row", out.filter(pl.col("rid") == 10)["s1"].item(), 1)

# --- the shape make_submission.py writes --------------------------------
# make_submission filters best on p2 >= THR then joins qid for entity_id.
qid = pl.DataFrame({"rid": [10, 11, 12], "entity_id": ["S2-1", "S2-2", "S3-1"]})
joined = out.join(qid, on="rid")
eq("join to entity_id works", joined.height, 3)
eq("entity_id present", "entity_id" in joined.columns, True)

# grouped into the comma-joined submission form
sub = (joined.group_by("s1")
             .agg(pl.col("entity_id").sort().str.join(",").alias("matched_entity_ids")))
eq("submission aggregation works", sub.height, 3)

# --- the S1 universe for check_invariants ------------------------------
# best_pairs keeps the argmax s1 per rid, so the survivors are s1 = 1, 3, 4.
# The universe must therefore CONTAIN 4.  Using {1,2,3} here is a genuine
# violation (s1=4 is not a known Source-1 entity) and check_invariants
# correctly refuses to call that table clean -- which is the behaviour we want.
s1 = pl.DataFrame({"rid": [1, 2, 3, 4], "entity_id": ["S1-a", "S1-b", "S1-c", "S1-d"]})
univ = s1.select(pl.col("rid").alias("s1"))
inv = P.check_invariants(out, univ)
eq("invariants on real pipeline output", inv["ok"], True)
eq("invariants sees 4 s1", inv["s1_total"], 4)
eq("invariants counts the unmatched s1", inv["s1_with_no_pair"], 1)

# and prove the check actually bites on a real violation: drop 4 from the universe
bad_univ = pl.DataFrame({"s1": [1, 2, 3]})
invb = P.check_invariants(out, bad_univ)
eq("invariants flags an s1 outside the universe",
   invb["pairs_with_unknown_s1"], 1)
eq("invariants not ok when s1 is unknown", invb["ok"], False)

# --- dtype tolerance: p1 is Float32 in the pipeline ---------------------
f32 = pairs.with_columns(pl.col("p1").cast(pl.Float32))
o32 = P.postprocess(f32, score_col="p1", s1_col="s1", rec_col="rid")
eq("float32 scores work", o32.height, 3)
eq("float32 winner is the argmax",
   o32.filter(pl.col("rid") == 10)["s1"].item(), 1)

# --- a tie at the threshold must be resolved, not duplicated ------------
tied = pl.DataFrame({"s1": [1, 2], "rid": [10, 10], "p1": [0.5, 0.5]})
eq("exact tie resolved to one row", P.resolve_conflicts(tied, score_col="p1").height, 1)

# --- empty and single-row frames must not raise -------------------------
eq("empty frame", P.postprocess(pairs.head(0), score_col="p1").height, 0)
eq("single row", P.postprocess(pairs.head(1), score_col="p1").height, 1)
eq("empty invariants", P.check_invariants(pairs.head(0), univ)["ok"], True)

if fails:
    print("FAIL")
    for f in fails:
        print("  " + f)
    raise SystemExit(1)
print("postprocess integrates with the real pipeline schemas")
