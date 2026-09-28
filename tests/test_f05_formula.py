"""Decide the F_0.5 dispute against the challenge PDF's own worked example.

A code review claimed er_pipeline.entity_f05 was "critical"-wrong and had to
become 5*TP/(5*TP + 1*FP + 4*FN). The shipped code already used
5*TP/(5*TP + 4*FP + FN). This script settles it, and pins the shipped form so
the same bad "fix" is not re-applied later.
"""
from __future__ import annotations

import itertools

import numpy as np
from sklearn.metrics import fbeta_score

import er_pipeline as m

# --- The PDF's worked example, verbatim -------------------------------------
# "Your model predicts S1-00001 matches [S2-00047, S2-00193, S3-00812].
#  Ground truth says S1-00001 matches [S2-00047, S3-00812].
#  Precision = 2/3, Recall = 2/2 = 1.0
#  F_0.5 = (1.25 x 0.667 x 1.0) / (0.25 x 0.667 + 1.0) = 0.714"
TP, FP, FN = 2, 1, 0
pdf_stated = 0.714
sklearn = fbeta_score(np.array([1, 1, 0]), np.array([1, 1, 1]), beta=0.5, zero_division=0.0)
original = 5 * TP / (5 * TP + 4 * FP + 1 * FN)
review = 5 * TP / (5 * TP + 1 * FP + 4 * FN)

print("PDF example: TP=2 FP=1 FN=0  (P=2/3, R=1.0)")
print(f"  PDF states the answer is        {pdf_stated}")
print(f"  sklearn fbeta_score(beta=0.5)  {sklearn:.4f}")
print(f"  ORIGINAL 5TP/(5TP+4FP+1FN)     {original:.4f}   <- matches the PDF")
print(f"  REVIEW   5TP/(5TP+1FP+4FN)     {review:.4f}   <- contradicts the PDF")
print()

# --- First principles -------------------------------------------------------
# PDF formula:  F_b = (1+b^2)*P*R / (b^2*P + R)      (beta weights RECALL)
# With P = TP/(TP+FP), R = TP/(TP+FN), simplifying gives
#     F_b = (1+b^2)*TP / [ (1+b^2)*TP + b^2*FN + FP ]
# b=0.5, times 4:  F_0.5 = 5*TP / (5*TP + 4*FP + FN)
print("Algebra: F_b = (1+b^2)*TP / [(1+b^2)*TP + b^2*FN + FP]")
print("  -> b=0.5 gives 5*TP / (5*TP + 4*FP + FN). The extra weight is on FN,")
print("     the RECALL-side error. The review swapped FP and FN.")
print()

assert abs(original - pdf_stated) < 0.001, "original disagrees with the PDF"
assert abs(original - sklearn) < 1e-9, "original disagrees with sklearn"
assert abs(review - pdf_stated) > 0.1, "review form unexpectedly agrees with the PDF"

# --- Pin the shipped implementation to sklearn over many (gold, pred) pairs --
UNIVERSE = ["a", "b", "c", "d"]
SETS = [{"a"}, {"a", "b"}, {"a", "b", "c"}, {"a", "c"}, {"a", "d"}, {"a", "b", "c", "d"}]
checked = 0
for gold, pred in itertools.product(SETS, SETS):
    y = np.array([1 if t in gold else 0 for t in UNIVERSE])
    yp = np.array([1 if t in pred else 0 for t in UNIVERSE])
    ref = fbeta_score(y, yp, beta=0.5, zero_division=0.0)
    got = m.entity_f05(gold, pred)
    assert abs(ref - got) < 1e-9, f"gold={gold} pred={pred} sklearn={ref} ours={got}"
    checked += 1
print(f"entity_f05 matches sklearn fbeta_score(beta=0.5) on {checked} (gold, pred) pairs")
print("entity_f05(singleton, empty prediction) =",
      m.entity_f05(set(), set()), "(contract: 1.0)")
print("entity_f05(singleton, false merge)     =",
      m.entity_f05(set(), {"a"}), "(contract: 0.0)")
print()
print("VERDICT: the shipped denominator 5*TP + 4*FP + FN is CORRECT.")
print("         The review's 'critical' F0.5 finding is a false positive.")

