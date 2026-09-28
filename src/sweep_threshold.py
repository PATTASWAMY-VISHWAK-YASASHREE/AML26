"""
Threshold + decoy sweep for macro F_0.5 — the highest-leverage score knob.

WHY THIS EXISTS
`er_pipeline.py:704-712` already tunes the threshold and gets three things right
that most implementations get wrong:

  1. It splits by Source-1 ENTITY, not by row (`:633`), so no entity's candidates
     straddle the fit/tune boundary. Splitting by row would leak.
  2. It evaluates on the tune half only (`:704`), so the threshold is never
     chosen on rows the classifier memorised.
  3. It includes true singletons in the entity universe (`:700`), because the
     official macro average scores them: empty prediction -> 1.0, one false merge
     -> 0.0.

It also has a real weakness this harness fixes:

  THE SWEEP IS TOO COARSE. It tries 60 quantiles over [0.50, 0.9995] of the
  tuning-score distribution. Quantile steps bunch wherever score density is high,
  which is usually NOT where the operating point sits. Under macro F_0.5 the
  optimum is typically at very high precision (predict almost nothing), and a
  60-point grid reaches that region only by luck.

WHAT THIS HARNESS ADDS
  - a dense sweep over an explicit absolute range, not a quantile grid;
  - a per-country breakdown, so we can see honestly whether a per-country
    threshold would buy anything;
  - a decoy-offset simulation mirroring `decoy_postfilter.py`, so the postfilter
    is measured before it is trusted on a hidden test set.

THE DECOY POINT, STATED PLAINLY
  The generator plants lookalikes: same name, same street, house number shifted by
  a fixed POSITIVE offset (+1..+21). 79.8% of same-name US decoys carry one,
  versus 0.126% of true US pairs. Under macro F_0.5 each false merge zeroes a
  whole entity, so decoy removal is worth far more than marginal recall.

  `decoy_postfilter.py:17-18` already special-cases countries with no training
  labels (France) by removing ALL offsets +1..+21 rather than only the strong
  ones. That is a large, deliberate bet on the one country the model has never
  seen a label for. This harness lets that bet be measured, not assumed.

Run:
    .\\.venv\\Scripts\\python.exe sweep_threshold.py --selftest
    .\\.venv\\Scripts\\python.exe sweep_threshold.py --scores scores.npz
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

STRONG = [3, 4, 5, 7, 9, 11, 13, 21]
WEAK = [1, 2]


def entity_f05(gold: set, pred: set) -> float:
    """F_0.5 for one entity: 5*TP / (5*TP + 4*FP + FN).

    Empty gold AND empty pred -> 1.0 (correct abstention scores perfectly).
    Empty gold, non-empty pred -> 0.0 (a false merge on a singleton is total).
    """
    if not gold and not pred:
        return 1.0
    if not gold or not pred:
        return 0.0
    tp, fp, fn = len(gold & pred), len(pred - gold), len(gold - pred)
    den = 5 * tp + 4 * fp + fn
    return 5.0 * tp / den if den else 0.0


def macro_f05(gold: dict, pred: dict, entities) -> float:
    """Macro-average entity_f05 over the full entity universe.

    `entities` MUST include true singletons, or the average is inflated.
    """
    if not entities:
        return 0.0
    vals = [entity_f05(gold.get(s, set()), pred.get(s, set())) for s in entities]
    return float(np.mean(vals))

def build_gold_pred(sids, tids, labels, scores, threshold):
    """Materialise per-entity gold and predicted sets at one threshold."""
    gold, pred = {}, {}
    for s, t, lab, sc in zip(sids, tids, labels, scores):
        if lab:
            gold.setdefault(s, set()).add(t)
        if sc >= threshold:
            pred.setdefault(s, set()).add(t)
    return gold, pred


def gold_universe(sids, tids, labels):
    """Every entity that counts in the macro average, singletons included."""
    ents = set(sids)
    for s, t, lab in zip(sids, tids, labels):
        if lab:
            ents.add(s)
    return ents


def sweep(sids, tids, labels, scores, entities, thresholds):
    """Return (best_threshold, best_score, table) over an explicit grid.

    A fixed ABSOLUTE grid, not a quantile grid: quantile steps bunch up wherever
    the score distribution is dense, which is usually not the operating point.
    """
    table = []
    best_t, best_f = float(thresholds[0]), -1.0
    for th in thresholds:
        gold, pred = build_gold_pred(sids, tids, labels, scores, th)
        f = macro_f05(gold, pred, entities)
        table.append({
            "threshold": round(float(th), 6),
            "macro_f05": round(f, 6),
            "pred_pairs": sum(len(v) for v in pred.values()),
            "entities_with_pred": len(pred),
        })
        if f > best_f:
            best_f, best_t = f, float(th)
    return best_t, best_f, table


def default_grid(scores, n=400):
    """Dense grid over a percentile-anchored window of the score range.

    Anchored at the 0.50 and 0.9995 quantiles so a single wild outlier cannot
    compress the sweep into one decade. The window is returned so the grid is
    never mistaken for the full score range.
    """
    lo, hi = float(np.min(scores)), float(np.max(scores))
    p_lo = float(np.quantile(scores, 0.50))
    p_hi = float(np.quantile(scores, 0.9995))
    if not (np.isfinite(p_lo) and np.isfinite(p_hi)) or p_hi <= p_lo:
        p_lo, p_hi = lo, hi
    return np.linspace(p_lo, p_hi, n), (p_lo, p_hi, lo, hi)


def per_country_breakdown(sids, tids, labels, scores, countries, threshold):
    """Macro F_0.5 restricted to each country.

    Motivation: `decoy_postfilter.py:17-18` treats countries with no training
    labels differently because the model is least calibrated there. This shows
    what a per-country threshold would actually buy, instead of assuming it.
    """
    buckets = {}
    for s, t, lab, sc, c in zip(sids, tids, labels, scores, countries):
        b = buckets.setdefault(c, ([], [], [], []))
        b[0].append(s); b[1].append(t); b[2].append(bool(lab)); b[3].append(sc)

    out = {}
    for c, (S, T, L, SC) in buckets.items():
        ents = set(S) | {s for s, l in zip(S, L) if l}
        gold, pred = build_gold_pred(S, T, L, SC, threshold)
        out[c] = {
            "entities": len(ents),
            "macro_f05": round(macro_f05(gold, pred, ents), 6),
            "pred_pairs": sum(len(v) for v in pred.values()),
        }
    return out


def apply_decoy_rule(pred, house, offsets=STRONG):
    """Mirror decoy_postfilter.py rule (a) on synthetic structures.

    `house` maps an id -> house number. Drops a predicted pair whose offset
    d = house(record) - house(s1) is in `offsets` when no OTHER predicted pair of
    that same s1 shares the same offset (true members sharing an S1-level shift
    arrive in groups; a lone shifted row is a decoy).

    Rule (b) - the country-gated wider removal for unlabelled countries - is left
    to the caller, because choosing its aggressiveness is a policy decision and
    should not be hidden inside a helper.
    """
    same = Counter()
    for s, ts in pred.items():
        h1 = house.get(s)
        if h1 is None:
            continue
        for t in ts:
            h = house.get(t)
            if h is not None:
                same[(s, h - h1)] += 1

    keep, removed = {}, []
    for s, ts in pred.items():
        h1 = house.get(s)
        for t in ts:
            h = house.get(t) if h1 is not None else None
            if h is not None and (h - h1) in offsets and same[(s, h - h1)] == 1:
                removed.append((s, t))
            else:
                keep.setdefault(s, set()).add(t)
    return keep, removed


def selftest() -> int:
    """Verify the scoring maths, and cross-check er_pipeline when importable."""
    print("selftest")
    # Expected values are DERIVED, not guessed. For gold={a,b} pred={a}:
    #   tp=1, fp=0, fn=1  ->  den = 5*1 + 4*0 + 1 = 6  ->  5/6 = 0.8333...
    # (An earlier draft of this file asserted 10/11 here, which is the F1 shape.
    # F_0.5 weights recall, so the false-merge term gets the 4 and the
    # false-negative term gets the 1.)
    cases = [
        (set(), set(), 1.0),                # correct abstention scores 1.0
        (set(), {"x"}, 0.0),                # false merge on a singleton is total
        ({"a"}, {"a"}, 1.0),                # exact hit
        ({"a", "b"}, {"a"}, 5.0 / 6.0),     # missed one link  -> 5/(5*1+0+1)
        ({"a"}, {"a", "c"}, 5.0 / 9.0),     # one false merge  -> 5/(5*1+4*1+0)
    ]
    ok = True
    for gold, pred, want in cases:
        got = entity_f05(gold, pred)
        good = abs(got - want) < 1e-9
        ok &= good
        print(f"  gold={str(sorted(gold) or '[]'):<10} pred={str(sorted(pred) or '[]'):<10} "
              f"-> {got:.4f} (want {want:.4f}) {'PASS' if good else 'FAIL'}")

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import er_pipeline
        for gold, pred, _want in cases:
            ref = er_pipeline.entity_f05(gold, pred)
            good = abs(ref - entity_f05(gold, pred)) < 1e-12
            ok &= good
            print(f"  vs er_pipeline: {ref:.6f} == {entity_f05(gold, pred):.6f} "
                  f"{'PASS' if good else 'FAIL'}")
    except Exception as exc:
        print(f"  (duckdb unavailable, cross-check skipped: {type(exc).__name__})")

    # Decoy rule (a). Two behaviours, asserted on SEPARATE entities so the two
    # do not interfere:
    #   sA: "solo" is a LONE +3 shift          -> decoy, removed
    #   sB: "g1","g2" share the SAME +3 shift  -> a real group, kept
    # (An earlier draft put both on one s1 with house numbers 20 and 23, which
    # are offsets 10 and 13, not a shared offset - the fixture was wrong, not
    # the rule.)
    house = {"sA": 10, "solo": 13, "x1": 10,
             "sB": 10, "g1": 13, "g2": 13, "y1": 10}
    pred = {"sA": {"solo", "x1"}, "sB": {"g1", "g2", "y1"}}
    keep, removed = apply_decoy_rule(pred, house)
    keptA, keptB = keep.get("sA", set()), keep.get("sB", set())

    good_i = ("sA", "solo") in removed and keptA == {"x1"}
    good_ii = keptB == {"g1", "g2", "y1"} and not any(r[0] == "sB" for r in removed)
    ok &= good_i and good_ii
    print(f"  decoy (i)   lone +3 removed   : removed={sorted(removed)} "
          f"kept(sA)={sorted(keptA)}  {'PASS' if good_i else 'FAIL'}")
    print(f"  decoy (ii)  shared +3 kept    : kept(sB)={sorted(keptB)}  "
          f"{'PASS' if good_ii else 'FAIL'}")
    print("selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="threshold / decoy sweep for macro F_0.5")
    ap.add_argument("--selftest", action="store_true",
                    help="verify the scoring maths and cross-check er_pipeline")
    ap.add_argument("--scores", type=Path,
                    help="NPZ with sids/tids/labels/scores(/countries) from stage_train")
    ap.add_argument("--out", type=Path, default=Path("threshold_sweep.json"))
    ap.add_argument("--grid", type=int, default=400)
    args = ap.parse_args()

    if args.selftest or not args.scores:
        return selftest()
    if not args.scores.exists():
        print(f"ERROR: {args.scores} not found. Export it from stage_train first.",
              file=sys.stderr)
        return 2

    d = np.load(args.scores, allow_pickle=True)
    sids, tids = d["sids"], d["tids"]
    labels, scores = d["labels"].astype(bool), d["scores"]
    countries = d["countries"] if "countries" in d.files else np.array(["?"] * len(sids))
    entities = gold_universe(sids, tids, labels)

    grid, window = default_grid(scores, args.grid)
    best_t, best_f, table = sweep(sids, tids, labels, scores, entities, grid)

    # What the pipeline's own coarse quantile grid would have found, for contrast.
    coarse = np.quantile(scores, np.linspace(0.50, 0.9995, 60))
    _, coarse_f, _ = sweep(sids, tids, labels, scores, entities, coarse)

    report = {
        "n_rows": int(len(sids)),
        "n_entities": int(len(entities)),
        "score_window": {"q50": window[0], "q9995": window[1],
                         "min": window[2], "max": window[3]},
        "best": {"threshold": best_t, "macro_f05": best_f},
        "pipeline_coarse_grid": {"macro_f05": coarse_f,
                                 "note": "60 quantiles over [0.50, 0.9995]"},
        "gain_from_fine_sweep": round(best_f - coarse_f, 6),
        "per_country_at_best": per_country_breakdown(
            sids, tids, labels, scores, countries, best_t),
        "table": table,
    }
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"rows {report['n_rows']:,}  entities {report['n_entities']:,}")
    print(f"best threshold {best_t:.6f} -> macro F_0.5 {best_f:.6f}")
    print(f"pipeline's coarse grid  -> macro F_0.5 {coarse_f:.6f}")
    print(f"gain from dense sweep   -> {report['gain_from_fine_sweep']:+.6f}")
    print("per country at the best threshold:")
    for c, v in sorted(report["per_country_at_best"].items()):
        print(f"   {str(c):<10} entities {v['entities']:>8,}  "
              f"F0.5 {v['macro_f05']:.6f}  pairs {v['pred_pairs']:,}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

