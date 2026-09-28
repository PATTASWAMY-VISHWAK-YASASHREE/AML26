"""Verify the dig5/dig6 COUNT table asserted in the P004 deliverable.

P004's section 7 tabulates US dig5/row, dig6/row and the raw dig6 count for all
six profile files, and section 8 quotes per-country dig5. Re-derives each from
analysis_out/profile/ and reports PASS/MISMATCH per cell, so the claim can be
checked without re-reading the .md. Read-only.
"""
import glob
import json
import os

# (dig5_per_row, dig6_count) exactly as printed in P004 section 7
DOC = {
    "train_s1": (0.109844, 1656),
    "test_s1":  (0.109789, 793),
    "train_s2": (0.107340, 42026),
    "train_s3": (0.107802, 42321),
    "test_s2":  (0.109706, 26757),
    "test_s3":  (0.110140, 26760),
}

print(f"{'file':10s} {'dig5/row':>10s} {'doc':>10s} {'':4s} "
      f"{'dig6':>7s} {'doc':>7s} {'':4s} {'dig6/row':>9s}")
bad = 0
for f in sorted(glob.glob("analysis_out/profile/*.json")):
    name = os.path.basename(f)[:-5]
    us = json.load(open(f, encoding="utf-8"))["by_country"]["US"]
    r = us["rows"]
    d5, d6 = us["dig5"] / r, us["dig6"]
    e5, e6 = DOC[name]
    ok5 = abs(d5 - e5) < 1e-6
    ok6 = us["dig6"] == e6
    bad += (not ok5) + (not ok6)
    print(f"{name:10s} {d5:>10.6f} {e5:>10.6f} {'OK' if ok5 else 'BAD':4s} "
          f"{us['dig6']:>7,} {e6:>7,} {'OK' if ok6 else 'BAD':4s} {d5 and us['dig6'] / r:>9.6f}")

print()
print("P004 section 8 / REFUTED-1 check (test_s1):")
d = json.load(open("analysis_out/profile/test_s1.json", encoding="utf-8"))
fr, us = d["by_country"]["France"], d["by_country"]["US"]
print(f"  France dig5 = {fr['dig5']:,} over {fr['rows']:,} rows = "
      f"{fr['dig5'] / fr['rows']:.6f}/row   (doc 1,082 / 0.004170)")
print(f"  US/France dig5 per-row ratio = "
      f"{(us['dig5'] / us['rows']) / (fr['dig5'] / fr['rows']):.1f}x  (doc 26x)")
print(f"  US share of file = {100 * us['rows'] / d['rows']:.4f}%  (doc 38.2735%)")
print()
print("ALL CELLS MATCH" if bad == 0 else f"{bad} MISMATCHES")
