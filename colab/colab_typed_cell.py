"""
COLAB CELL 2 — typed decisions + re-tunable threshold, no re-scoring.

PASTE THIS AFTER THE MAIN amazon_ml_colab_cell.py CELL. It needs nothing new
installed and it does NOT re-run the pipeline.

WHY THIS EXISTS
`_upstream/src/make_submission.py:62` already writes every scored pair to
    {work}/test_best_pred_cf.parquet      (or test_best_pred.parquet without CF)
with columns rid, s1, p1, p2 - i.e. the stage-1 candidate-ranker probability and
the stage-2 final-matcher probability. Those values are currently thresholded
and then DISCARDED.

This cell uses them. Because the expensive part (blocking, features, p1, p2) has
already happened, the threshold can be changed and re-applied in seconds, per
country, with no model and no re-scoring.

WHY THE THRESHOLD MATTERS SO MUCH
From `_upstream/src/metrics.py:15-16`, for one S1 entity:
    gold empty AND pred empty     ->  1.0
    gold empty AND pred nonempty ->  0.0
Abstaining on a singleton earns a PERFECT 1.0; a single false merge there earns a
TOTAL 0.0. The score is macro-averaged per entity, so one false merge does not
dilute - it zeroes a whole entity. The optimal policy is therefore much more
conservative than "maximise pair accuracy", and it is worth checking where the
optimum actually is rather than trusting the default THR2.

RAM: this cell is cheap. It streams one parquet of scored pairs; the heavy
stages already ran in cell 1.

NOTE ON HONESTY: the rewrite of matching_results.tsv below reproduces the exact
contract (one row per S1 entity, comma-joined sorted ids, empty string for none,
LF endings, header line). It is deliberately NOT run automatically - the default
is to PRINT the analysis and leave your existing submission alone. Rewriting a
submission is the one step here that is hard to undo, so it is opt-in.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import polars as pl

# ---------------------------------------------------------------- locate scores
WORK = Path(WORK_DIR)
cf = WORK / "test_best_pred_cf.parquet"
plain = WORK / "test_best_pred.parquet"
src = cf if cf.exists() else plain
if not src.exists():
    raise FileNotFoundError(
        f"No scored pairs at {cf} or {plain}. Run the main cell first.")

best = pl.read_parquet(src)
print(f"scored pairs : {best.height:,}   from {src.name}")
print(f"columns      : {best.columns}")

# Test-side entity ids, so the output can be written contract-correct.
# BOTH keys are required: the aggregation is keyed on "s1" while the output
# column is "source1_entity_id". Selecting only entity_id and renaming it
# destroys the join key - this is exactly how make_submission.py:66-70 does it.
qid = pl.read_parquet(WORK / "test_q.parquet", columns=["rid", "entity_id"])
s1_ids = (pl.read_parquet(WORK / "test_s1.parquet", columns=["rid", "entity_id"])
          .rename({"rid": "s1", "entity_id": "source1_entity_id"}))

P1_MIN = 0.02     # matches make_submission.py:44

# ------------------------------------------------------- what p2 actually looks like
# Print the distribution BEFORE choosing anything. Under macro F0.5 the useful
# operating points live in the upper tail, so a summary of the tail matters more
# than the mean.
q = [0.50, 0.90, 0.99, 0.999, 0.9999]
qs = best.select(
    pl.col("p2").quantile(q[0], "nearest").alias("q50"),
    pl.col("p2").quantile(q[1], "nearest").alias("q90"),
    pl.col("p2").quantile(q[2], "nearest").alias("q99"),
    pl.col("p2").quantile(q[3], "nearest").alias("q999"),
    pl.col("p2").quantile(q[4], "nearest").alias("q9999"),
    pl.col("p2").mean().alias("mean"),
).row(0, named=True)
print("\np2 distribution")
for k in ("mean", "q50", "q90", "q99", "q999", "q9999"):
    print(f"  {k:<7} {qs[k]:.6f}")
print(f"\n  pairs with p2 >= 0.02 : "
      f"{best.filter(pl.col('p2') >= P1_MIN).height:,}")

# ------------------------------------------------------------------ the sweep
# Match/abstain counts per threshold. This is the decision aid: it shows exactly
# what each policy would emit, without re-scoring anything.
GRID = [0.02, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99]
live = best.filter(pl.col("p1") >= P1_MIN)
print("\n thr      match     abstain    S1 with >=1 match   % of live")
for thr in GRID:
    m = live.filter(pl.col("p2") >= thr)
    n_s1 = m.select(pl.col("s1").n_unique()).item() if m.height else 0
    print(f" {thr:<6} {m.height:>9,}  {live.height - m.height:>9,}  "
          f"{n_s1:>17,}  {100.0 * m.height / max(live.height, 1):>6.2f}%")

# Current operating point, for reference.
try:
    import json as _json
    meta = _json.loads((WORK / "model_stage2_cf.json").read_text())
    cur = float(meta.get("thr", 0.5))
except Exception:
    cur = None
if cur is not None:
    cm = live.filter(pl.col("p2") >= cur).height
    print(f"\n current THR2 = {cur:.6f} -> {cm:,} pairs "
          f"({100.0 * cm / max(live.height, 1):.2f}% of live)")


# ------------------------------------------------------------------ OPT-IN REWRITE
# Set NEW_THR to a float to re-emit matching_results.tsv at that threshold.
# Leave it as None to keep the existing submission untouched (the default).
#
# This reproduces the contract exactly, matching er_pipeline.stage_write_outputs:
#   - one row per S1 entity in test_source1, INCLUDING those with no match
#   - matched ids comma-joined and sorted
#   - empty string, not a null, when there is no match
#   - LF line endings (the official validator strips only \n, so a stray CR would
#     end up inside the last id of every row)
#   - the exact header line
NEW_THR = None            # <-- e.g. 0.9
OUT_DIR = Path(OUT)       # the same out dir cell 1 used

if NEW_THR is not None:
    acc = (live.filter(pl.col("p2") >= NEW_THR)
           .select("rid", "s1")
           .join(qid, on="rid", how="inner"))
    grouped = (acc.group_by("s1")
                  .agg(pl.col("entity_id").sort().str.join(",")
                        .alias("matched_entity_ids")))
    out_df = (s1_ids.join(grouped, on="s1", how="left")
                    .select("source1_entity_id",
                            pl.col("matched_entity_ids").fill_null("")))
    out_df = out_df.sort("source1_entity_id")

    target = OUT_DIR / "matching_results.tsv"
    backup = target.with_suffix(".tsv.bak")
    if target.exists():
        shutil.copy2(target, backup)
        print(f"\nbacked up existing submission -> {backup.name}")

    body = out_df.write_csv(separator="\t", quote_style="never",
                            include_header=False, line_terminator="\n")
    target.write_bytes(b"source1_entity_id\tmatched_entity_ids\n"
                       + body.encode("utf-8"))

    n_with = out_df.filter(pl.col("matched_entity_ids") != "").height
    print(f"rewrote {target.name}: {out_df.height:,} S1 rows, "
          f"{n_with:,} with >=1 match, threshold {NEW_THR}")
    print("RE-RUN validate_outputs from cell 1 before submitting.")
else:
    print("\nNEW_THR is None: your submission is untouched. Set NEW_THR to a "
          "float above to re-emit at a different threshold.")

# ------------------------------------------------------------------ audit dump
# A typed, auditable side-car. Does NOT touch either official submission.
audit = (best.with_columns(
            pl.when(pl.col("p1") < P1_MIN).then(pl.lit("NO_CANDIDATE"))
              .when(pl.col("p2") >= (NEW_THR if NEW_THR is not None else (cur or 0.5)))
              .then(pl.lit("MATCH"))
              .otherwise(pl.lit("ABSTAIN")).alias("decision"))
          .with_columns(
            pl.when(pl.col("p2") >= 0.90).then(pl.lit("very_high"))
              .when(pl.col("p2") >= 0.70).then(pl.lit("high"))
              .when(pl.col("p2") >= 0.40).then(pl.lit("medium"))
              .when(pl.col("p2") >= 0.10).then(pl.lit("low"))
              .otherwise(pl.lit("very_low")).alias("confidence")))
audit.write_parquet(WORK / "typed_decisions.parquet")
print(f"wrote {WORK / 'typed_decisions.parquet'}  ({audit.height:,} rows)")
print(audit.group_by("decision").len().sort("decision"))

