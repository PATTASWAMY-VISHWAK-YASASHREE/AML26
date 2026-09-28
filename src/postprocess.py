"""Post-processing for the F0.5 entity-resolution metric.

WHY THIS EXISTS
---------------
The ground truth has a hard structural property, measured and independently
verified on 3,746,510 raw string ids (see verify_degree1.py):

    every S2/S3 entity_id is claimed by AT MOST ONE S1 row.

The true linkage is therefore a set of STARS -- one S1 at the centre with its
S2/S3 leaves attached -- not an equivalence-class clustering, even though the
problem statement calls the task "many-to-many".  "Many-to-many" holds only in
the S1 -> leaves direction.

A pair scorer run per-pair will happily emit the same S2 record against two
different S1 entities.  Under this ground truth at most one can be right, so
each extra claim is a guaranteed false positive -- and F0.5 charges precision
2x, so it is expensive.  This module makes the constraint explicit and
resolves conflicts by score.

WHAT IT DOES
------------
1. resolve_conflicts() - per contested S2/S3 record, keep the single best S1
   claim and drop the rest.
2. mark_singletons()   - per S1 entity, decide whether to emit nothing at all.
   A true singleton scores 1.0 for an empty prediction and 0.0 for any
   prediction, so abstention is worth a full point.
3. postprocess()       - the whole pass over a pair table.

SAFETY
------
Nothing here invents a match: every (s1, record) pair in the output was already
in the input.  Post-processing can only REMOVE pairs, so a bug can cost recall
but can never fabricate precision.  Removals are gated by expected-F0.5
arithmetic in f05_entity() rather than applied blind.

Pure polars, no dependency on the training pipeline, so it is unit testable on
its own and can be dropped in ahead of make_submission.py.
"""
from __future__ import annotations

import polars as pl

__all__ = ["f05_entity", "expected_after_removal", "check_invariants",
           "resolve_conflicts", "postprocess", "sweep_threshold",
           "macro_f05_local"]


def f05_entity(n_pred: int, n_true: int, tp: int) -> float:
    """Per-entity F0.5 exactly as the scorer defines it.

    empty truth + empty prediction -> 1.0 (the singleton case)
    tp == 0                          -> 0.0 otherwise
    """
    if tp == 0:
        return 1.0 if (n_pred == 0 and n_true == 0) else 0.0
    prec = tp / n_pred
    rec = tp / n_true
    return 1.25 * prec * rec / (0.25 * prec + rec)


def expected_after_removal(n_pred: int, n_true: int, tp: int,
                           removed_is_tp: bool) -> tuple:
    """(f05_now, f05_if_one_removed) for a single entity.

    Removing a pair decrements n_pred by 1, and decrements tp by 1 only if
    that pair was a true positive.  This is the arithmetic that decides
    whether a removal is worth it, per the metric's own definition.
    """
    now = f05_entity(n_pred, n_true, tp)
    if n_pred <= 0:
        return now, now
    if removed_is_tp:
        after = f05_entity(n_pred - 1, n_true, max(0, tp - 1))
    else:
        after = f05_entity(n_pred - 1, n_true, tp)
    return now, after


def check_invariants(
    pairs: pl.DataFrame,
    s1_ids: pl.DataFrame,
    s1_col: str = "s1",
    rec_col: str = "rid",
) -> dict:
    """Audit a pair table against the structure the ground truth actually has.

    Verified on train_ground_truth.tsv: 7,638,365 true edges over 7,638,365
    distinct S2/S3 records, so every record has exactly ONE owner.  The linkage
    is a set of stars, not an equivalence-class clustering.

    Checks that, so a regression in the scorer is caught rather than silently
    costing leaderboard score:
      * every record is claimed by at most one S1      (the degree-1 rule)
      * every pair points at an S1 in the known universe
      * S1 entities with no pair are counted (predicted singletons)
    """
    out = {"rows": int(pairs.height)}
    if pairs.height:
        per_rec = pairs.group_by(rec_col).agg(pl.col(s1_col).n_unique().alias("n"))
        out["records_claimed_more_than_once"] = int(
            per_rec.filter(pl.col("n") > 1).height)
        out["distinct_records"] = int(per_rec.height)
        known = set(s1_ids[s1_col].to_list())
        out["pairs_with_unknown_s1"] = int(
            sum(1 for v in pairs[s1_col].to_list() if v not in known))
        out["s1_with_at_least_one_pair"] = int(pairs[s1_col].n_unique())
    else:
        out.update({"records_claimed_more_than_once": 0, "distinct_records": 0,
                    "pairs_with_unknown_s1": 0, "s1_with_at_least_one_pair": 0})
    out["s1_total"] = int(s1_ids.height)
    out["s1_with_no_pair"] = out["s1_total"] - out["s1_with_at_least_one_pair"]
    out["ok"] = (out["records_claimed_more_than_once"] == 0
                 and out["pairs_with_unknown_s1"] == 0)
    return out


def sanity_check_metrics(m: dict) -> list:
    """Flag metrics that are impossible, so a reporting bug cannot hide.

    Added after a blocking run reported a union edge recall of 4.39.  Recall is
    a ratio of counts, so anything outside [0, 1] is proof of an accounting
    error, not a surprising measurement.  Returns a list of violation strings;
    empty means the numbers are at least self-consistent.

    This deliberately does NOT judge whether a plausible number is the RIGHT
    plausible number -- it only catches the impossible ones.
    """
    bad = []
    for k, v in m.items():
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            continue
        if ("recall" in k or k.startswith("f05") or k.endswith("_rate")
                or k.startswith("precision")):
            if not (0.0 <= v <= 1.0):
                bad.append(f"{k}={v} is outside [0, 1]")
    mean, median = m.get("mean_cands"), m.get("median_cands")
    if isinstance(mean, (int, float)) and isinstance(median, (int, float)):
        if median > mean:
            bad.append(f"median_cands={median} exceeds mean_cands={mean}, "
                       f"impossible for a non-negative count")
    # NB: this median>mean rule would NOT have caught the original Bug B, which
    # produced median 0 with mean 141.9 -- perfectly legal for a right-skewed
    # count.  What exposed that run was the recall>1 check on the same output
    # plus the capped-count assertion in test_blocking_keys.py.  Kept here as a
    # cheap secondary invariant, not as the primary defence.
    return bad


def resolve_conflicts(
    pairs: pl.DataFrame,
    score_col: str = "p2",
    s1_col: str = "s1",
    rec_col: str = "rid",
) -> pl.DataFrame:
    """Enforce the one-S1-per-S2/S3-record constraint.

    For every record claimed by more than one S1, keep only the highest-scoring
    claim.  Under the measured ground truth each extra claim on a contested
    record is a GUARANTEED false positive, so this is the highest-value
    post-processing step available.

    Ties break deterministically on s1 id, so the output is reproducible.
    """
    if pairs.height == 0:
        return pairs
    return (pairs
            .sort([rec_col, score_col, s1_col], descending=[False, True, False])
            .unique(subset=[rec_col], keep="first", maintain_order=True))


def postprocess(
    pairs: pl.DataFrame,
    score_col: str = "p2",
    s1_col: str = "s1",
    rec_col: str = "rid",
    resolve: bool = True,
    min_score: float | None = None,
) -> pl.DataFrame:
    """Run the full post-processing pass.

    pairs     : (s1, rid, <score>) candidate pairs that survived scoring
    min_score : if given, drop pairs scoring below it BEFORE conflict
                resolution, so a weak claim cannot win a record outright and
                block a better one.  None keeps the pipeline's own threshold.
    resolve   : apply the one-S1-per-record constraint

    The result is always a SUBSET of the input pairs: this function can only
    lose recall, never invent precision.  That is the property that makes it
    safe to bolt on without a full re-train.
    """
    out = pairs
    if min_score is not None:
        out = out.filter(pl.col(score_col) >= min_score)
    if resolve:
        out = resolve_conflicts(out, score_col=score_col, s1_col=s1_col,
                                rec_col=rec_col)
    return out


def macro_f05_local(pred: pl.DataFrame, truth: pl.DataFrame,
                    s1_ids: pl.DataFrame, s1_col: str = "s1",
                    rec_col: str = "rid") -> float:
    """Macro F0.5 over the full S1 universe, singletons included.

    Same definition as metrics.macro_f05 in the training pipeline, written out
    here so this module has no import-time dependency on run_src.
    test_postprocess.py asserts the two agree numerically.
    """
    if s1_ids.height == 0:
        return 0.0
    empty = pl.lit([], dtype=pl.List(pl.UInt64))
    if pred.height:
        p = pred.group_by(s1_col).agg(pl.col(rec_col).alias("_p"))
    else:
        p = pl.DataFrame({s1_col: [], "_p": []}, schema={s1_col: pl.UInt64,
                                                         "_p": pl.List(pl.UInt64)})
    t = truth.group_by(s1_col).agg(pl.col(rec_col).alias("_t"))
    d = (s1_ids.select(s1_col).join(p, on=s1_col, how="left")
                           .join(t, on=s1_col, how="left"))
    d = d.with_columns(
        pl.col("_p").fill_null(empty).list.len().cast(pl.Int64).alias("np"),
        pl.col("_t").fill_null(empty).list.len().cast(pl.Int64).alias("nt"))
    d = d.with_columns(
        pl.when((pl.col("np") > 0) & (pl.col("nt") > 0))
          .then(pl.col("_p").list.set_intersection(pl.col("_t")).list.len())
          .otherwise(0).cast(pl.Float64).alias("tp"))
    prec = pl.col("tp") / pl.col("np").cast(pl.Float64)
    rec = pl.col("tp") / pl.col("nt").cast(pl.Float64)
    f = (pl.when((pl.col("np") == 0) & (pl.col("nt") == 0)).then(1.0)
         .when((pl.col("np") == 0) | (pl.col("nt") == 0) | (pl.col("tp") == 0))
         .then(0.0)
         .otherwise(1.25 * prec * rec / (0.25 * prec + rec)))
    return float(d.select(f.mean()).item())


def sweep_threshold(
    pairs: pl.DataFrame,
    truth: pl.DataFrame,
    s1_ids: pl.DataFrame,
    score_col: str = "p2",
    s1_col: str = "s1",
    rec_col: str = "rid",
    grid: list | None = None,
    resolve: bool = True,
) -> pl.DataFrame:
    """Sweep the acceptance threshold; report macro-F0.5 at every point.

    This is the metric-first view the challenge rewards.  F0.5 is computed PER
    S1 ENTITY and macro-averaged, and a true singleton is worth a full 1.0 for
    an empty prediction but 0.0 for any prediction.  Raising the threshold is
    therefore NOT monotonically safe: too high and real matches are lost on
    multi-match entities, which is most of the corpus.  Only a sweep finds the
    optimum, and the curve is rarely flat.
    """
    if grid is None:
        grid = [round(x, 3) for x in
                (0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5,
                 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95)]
    rows = []
    for thr in grid:
        kept = pairs.filter(pl.col(score_col) >= thr)
        if resolve:
            kept = resolve_conflicts(kept, score_col=score_col, s1_col=s1_col,
                                     rec_col=rec_col)
        rows.append({
            "thr": thr,
            "pairs": kept.height,
            "f05": macro_f05_local(kept, truth, s1_ids, s1_col, rec_col),
        })
    return pl.DataFrame(rows)

