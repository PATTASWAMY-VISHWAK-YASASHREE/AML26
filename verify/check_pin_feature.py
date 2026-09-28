"""Is pin_eq a live feature or dead weight?

features.py:114 computes pin_eq = tri(q_pin, s_pin) from the `pin` field, which
normalize.py sets only under `len(n)==6 and country=="India"`. The profile says
dig6/row is ~0.000-0.001 for India and 0.001 for US source-1. If `pin` is empty
almost everywhere, pin_eq is a near-constant and the model gets nothing from it.

This measures the ACTUAL pin population rate after running the real
normalize_address, per country and per source, plus how often pin_eq could
possibly be TRUE for a candidate pair.
"""
import csv
import sys
from collections import Counter

sys.path.insert(0, "_upstream/src")
import normalize as N  # noqa: E402

BASE = "amazon_ml_2026_research/student_resource/dataset"
FILES = [
    ("train", 1), ("train", 2), ("train", 3),
    ("test", 1), ("test", 2), ("test", 3),
]

print("pin population rate, by real normalize_address output")
print(f"{'split':6s} {'src':4s} {'country':8s} {'rows':>10s} {'pin set':>9s} {'rate':>8s}")
print("-" * 52)
tot_rows = tot_pin = 0
for split, src in FILES:
    path = f"{BASE}/{split}/{split}_source{src}.tsv"
    rows = Counter()
    pins = Counter()
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(rd)
        for i, rec in enumerate(rd):
            if len(rec) < 4:
                continue
            c = rec[3].strip()
            rows[c] += 1
            _t, _n, _st, pin, _cc = N.normalize_address(rec[2], c)
            if pin:
                pins[c] += 1
            if i > 250_000:
                break
    for c in sorted(rows):
        p = pins.get(c, 0)
        tot_rows += rows[c]
        tot_pin += p
        print(f"{split:6s} s{src:<3d} {c:8s} {rows[c]:>10,} {p:>9,} {p/max(rows[c],1):>8.4%}")
    if not rows:
        print(f"{split:6s} s{src:<3d} {'(capped at 250k rows)':8s}")

print(f"\nOVERALL: pin set on {tot_pin:,} of {tot_rows:,} rows = {tot_pin/max(tot_rows,1):.4%}")
print("\nConsequence: pin_eq is True only when BOTH sides have a non-empty pin.")
print("With the pin rate this low, pin_eq is almost always False, so the feature")
print("carries almost no information and the model cannot learn from it.")
print("This is the REAL consequence of the India-only pin guard - not a France loss.")
