"""
Typed decision layer — the Jev discipline, applied to entity resolution.

WHAT "JEV" ACTUALLY IS (checked online 2026-09-27)
There is no software architecture called "Jev". The only tech "Jev" is a
proprietary model from TypeSafe AI (released 15 Sep 2026). Its relevant design
properties are:
  - returns TYPED values with probabilities, never prose;
  - three primitives: Choice (one of a defined set), Score (ordered level),
    Noul (yes/no with probability);
  - schema-constrained: "the model cannot return a value outside the supplied
    schema", which the vendor claims removes hallucination and type errors.

The transferable thing is NOT a framework. It is a discipline: never emit an
untyped, uncalibrated, unauditable prediction.

HONEST AUDIT OF WHAT THE PIPELINE ALREADY DOES
  [DONE] Typed output       matching_results.tsv is a fixed 2-column contract.
  [DONE] Schema constraint  predictions are filtered FROM THE CANDIDATE SET, so a
                            match can never be an id that blocking never saw.
                            Same idea as Jev's closed schema.
  [DONE] Choice primitive   exactly one best S1 per query (stage2.build/assign).
  [DONE] Per-option probability INTERNALLY: p1 and p2 exist for every candidate.
  [GAP]  Probability never reaches the OUTPUT. p2 is thresholded then discarded.
  [GAP]  Abstention is not a first-class decision, only a global threshold cut.
  [GAP]  One global THR2 for every country, including one with no labels.

WHY THE ABSTENTION GAP IS THE EXPENSIVE ONE
From _upstream/src/metrics.py:15-16, for one S1 entity:
    gold empty AND pred empty     ->  1.0
    gold empty AND pred nonempty ->  0.0
Abstaining on a singleton earns a PERFECT 1.0; a single false merge there earns a
TOTAL 0.0. Because the score is macro-averaged per entity, one false merge does
not dilute - it zeroes a whole entity. Abstention is therefore worth far more
than marginal pair accuracy, and there is currently no per-query mechanism for
it. Jev's `Noul` primitive is exactly the missing mechanism.

WHAT THIS MODULE DOES
Emits a TYPED, CLOSED-SCHEMA decision per query with an explicit decision and a
confidence bucket, so the policy can be re-tuned WITHOUT re-running the model and
every decision is auditable.

    decision in {MATCH, ABSTAIN, NO_CANDIDATE}   <- closed set, no "other"

It writes a SIDE-CAR. The two official submission files are never modified: the
validator requires them byte-exact and an extra column would fail the contract.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

MATCH = "MATCH"
ABSTAIN = "ABSTAIN"
NO_CANDIDATE = "NO_CANDIDATE"
DECISIONS = (MATCH, ABSTAIN, NO_CANDIDATE)   # the closed schema

# Confidence is a CLOSED ordered scale, not free text, so a policy can never be
# misconfigured into an unscoreable state.
BUCKETS = ("very_low", "low", "medium", "high", "very_high")

def bucket(p) -> str:
    """Map a probability onto the closed BUCKETS scale.

    Cut points are PLACEHOLDERS, not fitted values - they must be re-derived on
    held-out train data before use. Stated here so nobody mistakes them for
    calibrated boundaries.
    """
    if p is None:
        return "very_low"
    try:
        p = float(p)
    except (TypeError, ValueError):
        return "very_low"
    if math.isnan(p):
        return "very_low"
    if p >= 0.90:
        return "very_high"
    if p >= 0.70:
        return "high"
    if p >= 0.40:
        return "medium"
    if p >= 0.10:
        return "low"
    return "very_low"


def decide(p2, thr: float, p1=None, p1_min: float = 0.02) -> str:
    """The typed decision for ONE query, from its two probabilities.

    p2 is the final matcher's probability; p1 is the candidate ranker's, used
    only to reject pairs the stage-2 model was never trained on.

    Returns one of DECISIONS. Never raises, never invents a fourth value - the
    whole point is that the output space is closed.
    """
    if p2 is None or p1 is None:
        return NO_CANDIDATE
    try:
        p2f, p1f = float(p2), float(p1)
    except (TypeError, ValueError):
        return NO_CANDIDATE
    if math.isnan(p2f) or math.isnan(p1f):
        return ABSTAIN          # uncertain, never MATCH
    if p1f < p1_min:
        return NO_CANDIDATE
    return MATCH if p2f >= thr else ABSTAIN


def apply_policy(records, thr: float, p1_min: float = 0.02):
    """Apply a threshold policy to already-scored records.

    `records` is an iterable of dicts with keys rid, s1, p1, p2.
    Returns (rows, summary). This is the re-tunable layer: change `thr` and
    re-run THIS - no model, no features, no blocking.
    """
    rows = []
    counts = {MATCH: 0, ABSTAIN: 0, NO_CANDIDATE: 0}
    for r in records:
        d = decide(r.get("p2"), thr, r.get("p1"), p1_min)
        counts[d] += 1
        rows.append({
            "rid": r.get("rid"), "s1": r.get("s1"),
            "p1": r.get("p1"), "p2": r.get("p2"),
            "decision": d, "confidence": bucket(r.get("p2")),
        })
    summary = {
        "threshold": thr, "p1_min": p1_min, "counts": counts,
        "match_rate": round(counts[MATCH] / len(rows), 6) if rows else 0.0,
    }
    return rows, summary


def sweep_policies(records, thresholds, p1_min: float = 0.02):
    """Match counts across a threshold grid, from ONE scoring pass.

    The operational payoff of the discipline: the expensive part (blocking,
    features, scoring) happens once; the cheap part (policy) is re-evaluated as
    often as wanted. The output is a strictly typed count, not a re-scored model.
    """
    return [apply_policy(records, thr, p1_min)[1] for thr in thresholds]


def selftest() -> int:
    print("typed-decision selftest")
    ok = True

    def check(label, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {label:<46} -> {str(got)[:18]:<18} {'PASS' if good else 'FAIL'}")

    # The closed schema must actually be closed.
    check("DECISIONS has exactly 3 members", len(DECISIONS), 3)
    check("decide() never emits a 4th value",
          set(decide(v, 0.5, 0.9) for v in (None, 0.0, 0.5, 1.0)),
          {MATCH, ABSTAIN, NO_CANDIDATE})

    # Boundary behaviour - where a threshold bug actually costs score.
    check("p2 exactly at threshold -> MATCH", decide(0.5, 0.5, 0.9), MATCH)
    check("p2 just below threshold -> ABSTAIN", decide(0.4999, 0.5, 0.9), ABSTAIN)
    check("p1 below p1_min -> NO_CANDIDATE", decide(0.99, 0.5, 0.01), NO_CANDIDATE)
    check("p1 exactly at p1_min -> decided", decide(0.99, 0.5, 0.02), MATCH)
    check("missing p2 -> NO_CANDIDATE", decide(None, 0.5, 0.9), NO_CANDIDATE)
    check("NaN p2 -> ABSTAIN, never MATCH", decide(float("nan"), 0.5, 0.9), ABSTAIN)
    check("non-numeric p2 -> NO_CANDIDATE", decide("x", 0.5, 0.9), NO_CANDIDATE)

    recs = [{"rid": f"q{i}", "s1": f"s{i}", "p1": 0.9, "p2": v}
            for i, v in enumerate([0.99, 0.80, 0.60, 0.30, 0.05])]
    rows, summary = apply_policy(recs, thr=0.70)
    check("at thr=0.70 counts", summary["counts"],
          {MATCH: 2, ABSTAIN: 3, NO_CANDIDATE: 0})
    check("every row has a valid decision",
          all(r["decision"] in DECISIONS for r in rows), True)
    check("every row has a valid confidence bucket",
          all(r["confidence"] in BUCKETS for r in rows), True)

    # The whole point: re-tuning must NOT need re-scoring.
    _, hi = apply_policy(recs, thr=0.90)
    _, lo = apply_policy(recs, thr=0.10)
    check("higher threshold -> fewer matches",
          hi["counts"][MATCH] < lo["counts"][MATCH], True)

    grid = sweep_policies(recs, [0.1, 0.5, 0.7, 0.9])
    check("sweep returns one summary per threshold", len(grid), 4)
    check("sweep MATCH counts are non-increasing",
          all(grid[i]["counts"][MATCH] >= grid[i + 1]["counts"][MATCH]
              for i in range(len(grid) - 1)), True)

    print("selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="typed decision layer (Jev discipline)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--decisions", type=Path,
                    help="JSON/JSONL of {rid,s1,p1,p2} exported from make_submission")
    ap.add_argument("--out", type=Path, default=Path("typed_decisions.tsv"))
    ap.add_argument("--grid", type=float, nargs="*", default=None)
    args = ap.parse_args()

    if args.selftest or not args.decisions:
        return selftest()
    if not args.decisions.exists():
        print(f"ERROR: {args.decisions} not found", flush=True)
        return 2

    raw = args.decisions.read_text(encoding="utf-8")
    recs = (json.loads(raw) if raw.lstrip().startswith("[")
            else [json.loads(ln) for ln in raw.splitlines() if ln.strip()])

    grid = args.grid or [0.02, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    summary = sweep_policies(recs, grid)
    print(f"queries: {len(recs):,}")
    print("thr     MATCH   ABSTAIN  NO_CAND  match_rate")
    for s in summary:
        c = s["counts"]
        print(f"{s['threshold']:<7} {c[MATCH]:<7} {c[ABSTAIN]:<8} "
              f"{c[NO_CANDIDATE]:<8} {s['match_rate']:.4f}")

    rows, _ = apply_policy(recs, grid[len(grid) // 2])
    head = ("rid", "s1", "p1", "p2", "decision", "confidence")
    lines = ["\t".join(head)]
    lines += ["\t".join(str(r[k]) for k in head) for r in rows]
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.out}: {len(rows)} decisions, {len(DECISIONS)}-value closed schema")
    print("NOTE: the two official submission TSVs are untouched by this module.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

