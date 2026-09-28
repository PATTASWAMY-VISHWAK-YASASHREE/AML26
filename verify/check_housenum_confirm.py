"""Confirm the house-number reading, and check what the leading 5-digit collides with.

check_zip_vs_housenum.py found the leading 5-digit does NOT cluster by city
(mean top-prefix share 9.82%, 0/537 cities above 30%) and its first-digit
distribution is Zipf-like (70% '1'), not a postal allocation. Both say HOUSE
NUMBER, refuting the "that is the ZIP" reading.

Two further checks before this is written up as settled:

  C1 STREET-NUMBER COMPANIONSHIP. If the leading 5-digit is a house number it
     should behave like one: pair with the following street word, and repeat
     across the dataset for the same building. Measure how often the SAME
     (5-digit, street-token) pair recurs. A house number repeats for a real
     building; a ZIP pairs with thousands of distinct street names.

  C2 VALUE REUSE. If these are house numbers, the same 5-digit should appear
     many times paired with DIFFERENT street names. If they were ZIPs, each
     value would pair with a huge variety of streets too -- but the decisive
     asymmetry is that a house-number value should be dominated by a FEW
     street tokens, whereas a ZIP value is spread thin.

  C3 THE DECISIVE ASYMMETRY. A ZIP is a property of the CITY: every address in
     a city shares it. A house number is a property of the BUILDING. So for
     the most common 5-digit values, compare how concentrated their street
     tokens are vs how concentrated a real city's rows are.

Read-only, streaming, bounded.
"""
from __future__ import annotations

import csv
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(ROOT, "amazon_ml_2026_research", "student_resource", "dataset")
DIG5 = re.compile(r"(?<!\d)\d{5}(?!\d)")

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "test", "test_source1.tsv")
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 1_500_000

us = 0
pair = Counter()            # (5digit, street-ish token after it) -> count
val_streets = defaultdict(Counter)   # 5digit -> Counter of following tokens
val_count = Counter()
same_building = 0
rows_lead = 0

with open(path, encoding="utf-8", errors="replace", newline="") as fh:
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    next(rd)
    for rec in rd:
        if len(rec) < 4 or rec[3].strip() != "US":
            continue
        us += 1
        a = rec[2]
        m = DIG5.match(a.strip())
        if m:
            rows_lead += 1
            z = m.group(0)
            val_count[z] += 1
            rest = a.strip()[len(z):]
            toks = re.findall(r"[a-z]+", rest.lower())
            if toks:
                t = toks[0]
                pair[(z, t)] += 1
                val_streets[z][t] += 1
        if us >= LIMIT:
            break

print(f"file {os.path.relpath(path, ROOT)}")
print(f"US rows {us:,}   leading-5-digit rows {rows_lead:,}\n")
print(f"distinct 5-digit values : {len(val_count):,}")
print(f"distinct (value, next-token) pairs : {len(pair):,}")
print(f"mean distinct street tokens per value : "
      f"{sum(len(v) for v in val_streets.values()) / max(len(val_count), 1):.2f}")

dupes = [(k, c) for k, c in pair.items() if c > 1]
recurring = sum(c for _k, c in dupes)
print(f"(value, street) pairs recurring >1 time : {len(dupes):,} "
      f"covering {recurring:,} rows")
if rows_lead:
    print(f"share of leading-5-digit rows whose exact (number, street) repeats : "
          f"{recurring / rows_lead:.2%}")

print("\nC1/C3 top recurring (5-digit, next token) pairs -- a house number")
print("   repeating for the same building looks like this:")
for (z, t), c in pair.most_common(12):
    print(f"      {z} {t:22s} x{c}")

print("\nC2 concentration of the most common 5-digit values")
print("   A house number concentrates on a few streets; a ZIP spreads over all.")
for z, n in val_count.most_common(8):
    streets = val_streets[z]
    top = streets.most_common(3)
    share = top[0][1] / n if n else 0
    print(f"   {z}: n={n:>4}  distinct streets={len(streets):>4}  "
          f"top street share={share:6.2%}  top3={[(t, c) for t, c in top]}")

print("\nREADING")
if pair:
    rep = recurring / rows_lead
    if rep > 0.05:
        print(f"   {rep:.2%} of leading-5-digit rows repeat an exact (number, street)")
        print("   pair. Numbers attached to a specific recurring street token are")
        print("   BUILDING identifiers -> house numbers. Confirms reading A: the US")
        print("   has no postal signal here and the N0 US fix should be dropped.")
    else:
        print(f"   Only {rep:.2%} repeat an exact (number, street) pair, which is")
        print("   ambiguous -- see C3 concentration above before concluding.")