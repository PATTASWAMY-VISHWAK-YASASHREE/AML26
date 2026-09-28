"""AUTHORITATIVE pin rate on FULL files, replacing the 6.2% sample in N0.

check_pin_feature.py:44-45 has `if i > 250_000: break`, so the N0 table in
FRANCE_FINDINGS.md was built from ~250k rows per file: 1,500,012 rows total
against a dataset of 24,229,173 rows (6.2%). Its per-slice 'rows' column is a
file PREFIX, not the slice population -- e.g. it lists France test s1 as 37,323
where analysis_out/profile/test_s1.json reports 259,452.

That does not make the N0 conclusion wrong, but it makes the evidence weaker
than presented. This rescans FULL files with no cap so the denominators are
real. It also separates the two claims:

  * 'pin is never set for US/France' is guaranteed by CONSTRUCTION -- the guard
    at normalize.py:337 is `len(n) == 6 and country == "India"`, so a non-India
    row cannot take that branch at all. No scan is needed to establish it.
  * the India pin RATE is a genuine data question and is what needs measuring.

Read-only. Writes nothing.
"""
from __future__ import annotations

import csv
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True  # keep the pristine _upstream tree clean
sys.path.insert(0, os.path.join(ROOT, "_upstream", "src"))
import normalize as N  # noqa: E402

BASE = os.path.join(ROOT, "amazon_ml_2026_research", "student_resource", "dataset")
FILES = [("train", 1), ("train", 2), ("train", 3),
         ("test", 1), ("test", 2), ("test", 3)]
MAXROW = int(sys.argv[1]) if len(sys.argv) > 1 else 0   # 0 = no cap

print("pin population rate from FULL files (no row cap unless MAXROW given)")
print(f"{'split':6s} {'src':4s} {'country':8s} {'rows':>12s} {'pin set':>8s} {'rate':>10s}")
print("-" * 56)
tot_rows = tot_pin = 0
per_country_rows = Counter()
per_country_pin = Counter()
for split, src in FILES:
    path = os.path.join(BASE, split, f"{split}_source{src}.tsv")
    rows, pins = Counter(), Counter()
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(rd)
        for i, rec in enumerate(rd):
            if MAXROW and i > MAXROW:
                break
            if len(rec) < 4:
                continue
            c = rec[3].strip()
            rows[c] += 1
            if N.normalize_address(rec[2], c)[3]:
                pins[c] += 1
    for c in sorted(rows):
        p = pins.get(c, 0)
        tot_rows += rows[c]
        tot_pin += p
        per_country_rows[c] += rows[c]
        per_country_pin[c] += p
        print(f"{split:6s} s{src:<3d} {c:8s} {rows[c]:>12,} {p:>8,} {p / max(rows[c], 1):>10.6%}")
    del rows, pins

print("-" * 56)
print(f"{'TOTAL':6s} {'':4s} {'':8s} {tot_rows:>12,} {tot_pin:>8,} {tot_pin / max(tot_rows, 1):>10.6%}")
print()
print("per-country totals across all six FULL files:")
for c in sorted(per_country_rows):
    n, p = per_country_rows[c], per_country_pin[c]
    print(f"   {c:8s} rows {n:>12,}   pin set {p:>7,}   rate {p / max(n, 1):.6%}")
print()
print("VERDICT")
nz = [c for c in per_country_pin if per_country_pin[c] > 0 and c != "India"]
print(f"   countries with a non-zero pin count other than India: {nz or 'NONE'}")
print("   Expected and required: normalize.py:337 guards on country == 'India', so")
print("   US and France CANNOT set pin regardless of data. That part of N0 is a")
print("   code-level certainty, not a statistical claim.")
print(f"   India pin rate on the full dataset: "
      f"{per_country_pin['India']:,}/{per_country_rows['India']:,} = "
      f"{per_country_pin['India'] / max(per_country_rows['India'], 1):.6%}")
