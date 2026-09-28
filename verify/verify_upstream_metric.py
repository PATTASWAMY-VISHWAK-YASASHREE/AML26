"""Independently verify the upstream pipeline's F_0.5 against sklearn.

This matters more than any style issue: a wrong macro metric silently corrupts
threshold selection AND every reported score, and nothing else in the pipeline
would reveal it. metrics.py uses the PDF form

    F_0.5 = 1.25 * P * R / (0.25 * P + R)

which should be identical to sklearn's fbeta_score(beta=0.5). This checks that
on randomised cases, including the singleton edge cases the challenge calls out
explicitly (a true singleton predicted empty scores 1.0, predicted non-empty 0.0)
and including that singletons stay in the averaging denominator.
"""
from __future__ import annotations

import importlib.util
import random
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).parent
METRICS = ROOT / "_upstream" / "src" / "metrics.py"

# This review already made one mistake worth guarding against: an earlier code
# review claimed `5*TP + 4*FP + FN` was wrong and must become `5*TP + 1*FP + 4*FN`.
# That claim was false. beta weights RECALL, so the extra weight belongs on FN.
# Everything below is checked against sklearn, not against that claim.
EXPECTED_FORM = "1.25 * prec * rec / (0.25 * prec + rec)"


def load():
    spec = importlib.util.spec_from_file_location("up_metrics", METRICS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    from sklearn.metrics import fbeta_score

    m = load()
    src = METRICS.read_text(encoding="utf-8")
    assert EXPECTED_FORM in src, f"metrics.py no longer uses {EXPECTED_FORM!r}"

    rng = random.Random(0)
    mismatches = 0
    checked = 0

    for trial in range(400):
        n_entities = rng.randint(1, 6)
        universe = [f"e{i}" for i in range(n_entities)]
        targets = [f"r{i}" for i in range(8)]
        truth_rows, pred_rows, eval_rows = [], [], []
        for e in universe:
            k = rng.randint(0, 3)
            gold = rng.sample(targets, k)
            truth_rows += [(e, t) for t in gold]
            # predictions: a random subset of gold plus possible false positives
            fp = rng.sample([t for t in targets if t not in gold],
                            rng.randint(0, 2))
            keep = rng.sample(gold, rng.randint(0, len(gold)))
            pred_rows += [(e, t) for t in keep + fp]
            eval_rows.append((e,))
        truth = pl.DataFrame(truth_rows or [("x", "y")], schema=["s1", "rid"], orient="row")
        pred = pl.DataFrame(pred_rows or [("x", "y")], schema=["s1", "rid"], orient="row")
        ev = pl.DataFrame(eval_rows, schema=["s1"], orient="row")
        got = m.macro_f05(pred, truth, ev)

        # Reference: per-entity F_0.5 with sklearn, singletons scoring 1.0/0.0
        # per the challenge contract, averaged over the whole evaluation universe.
        vals = []
        for (e,) in eval_rows:
            g = {t for (a, t) in truth_rows if a == e}
            p = {t for (a, t) in pred_rows if a == e}
            if not g and not p:
                vals.append(1.0)
            elif not g or not p:
                vals.append(0.0)
            else:
                y = [1 if t in g else 0 for t in targets]
                yp = [1 if t in p else 0 for t in targets]
                vals.append(float(fbeta_score(y, yp, beta=0.5, zero_division=0.0)))
        want = sum(vals) / len(vals)
        checked += 1
        if abs(got - want) > 1e-9:
            mismatches += 1
            if mismatches <= 3:
                print(f"  MISMATCH trial {trial}: upstream={got:.6f} sklearn={want:.6f}")
    print(f"compared {checked} randomised cases against sklearn fbeta_score(beta=0.5)")

    # The contract's two explicit singleton rules. polars ignores `schema` when
    # orient="row" and the data is empty, so build the frames explicitly. All
    # three must share a dtype: metrics.py fills with List(pl.UInt32), so use u32
    # throughout (s1 = 1, the rid values are the target ids).
    U32 = pl.UInt32

    def frame(rows):
        return pl.DataFrame({"s1": pl.Series([r[0] for r in rows], dtype=U32),
                             "rid": pl.Series([r[1] for r in rows], dtype=U32)})

    def one(gold, pred):
        return m.macro_f05(frame(pred), frame(gold), frame([(1, 0)]))

    empty = one([], [])
    print(f"  true singleton, empty prediction -> {empty}  (contract: 1.0)")
    false_merge = one([], [(1, 0)])   # entity 1 predicted one target, but has none
    print(f"  true singleton, false merge      -> {false_merge}  (contract: 0.0)")

    ok = (mismatches == 0 and abs(empty - 1.0) < 1e-12 and abs(false_merge) < 1e-12)
    if mismatches:
        print(f"\nFAIL: {mismatches} mismatches vs sklearn")
        return 1
    if not ok:
        print("\nFAIL: singleton handling does not match the contract")
        return 1
    print("\nupstream macro_f05 matches sklearn exactly, and the singleton "
          "contract rules hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
