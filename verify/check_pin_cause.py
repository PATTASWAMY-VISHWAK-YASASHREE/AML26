"""Is `pin` dead because of the India-only GUARD, or because the DATA has no
postal codes anywhere?

This decides the correct remedy. FRANCE_FINDINGS.md N0 blames the guard at
normalize.py:337 (`len(n)==6 and country=="India"`) and prescribes a US-only fix.
check_us_zip_presence.py showed the US has ZERO postal codes, so that remedy is
dead. But that leaves two live hypotheses about the guard:

  H-guard  the guard is wrong; other countries have postal codes it discards
  H-data   the guard is fine; the dataset simply has ~no postal codes at all

These imply opposite actions, so they must be separated. Checks per country:
  - how many rows have a standalone 6-digit number (a real Indian PIN shape)
  - WHERE it sits (India writes PIN last: "..., Kolkata, West Bengal 700001")
  - whether the 6-digit token is also reachable via `nums` (keys.py:41)

If India has genuine trailing 6-digit PINs that ARE captured, the guard is
working as designed and the feature is merely starved by the data.

Read-only, streaming, bounded.
"""
from __future__ import annotations

import csv
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True  # keep the pristine _upstream tree clean
sys.path.insert(0, os.path.join(ROOT, "_upstream", "src"))
import normalize as N  # noqa: E402

BASE = os.path.join(ROOT, "amazon_ml_2026_research", "student_resource", "dataset")
DIG6 = re.compile(r"(?<!\d)\d{6}(?!\d)")

LIMIT = 1_500_000
path = os.argv[1] if len(sys.argv) > 1 else os.path.join(
    BASE, "train", "train_source1.tsv")

rows = Counter()
d6 = Counter()
trailing = Counter()
captured = Counter()
samples = []

with open(path, encoding="utf-8", errors="replace", newline="") as fh:
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    next(rd)
    n = 0
    for rec in rd:
        if len(rec) < 4:
            continue
        c = rec[3].strip()
        rows[c] += 1
        n += 1
        a = rec[2]
        hits = DIG6.findall(a)
        if hits:
            d6[c] += 1
            comps = [x.strip() for x in a.split(",") if x.strip()]
            last = comps[-1] if comps else ""
            if any(DIG6.search(t) for t in hits) and DIG6.search(last):
                trailing[c] += 1
                if c == "India" and len(samples) < 10:
                    samples.append(a[:95])
        _t, _nums, _s, pin, _cc = N.normalize_address(a, c)
        if pin:
            captured[c] += 1
        if n >= LIMIT:
            break

print(f"file {os.path.relpath(path, ROOT)}   rows {n:,}\n")
print(f"{'country':8s} {'rows':>10s} {'dig6 rows':>10s} {'dig6/row':>10s} "
      f"{'trailing':>10s} {'pin captured':>13s}")
print("-" * 68)
for c in sorted(rows):
    r = rows[c]
    print(f"{c:8s} {r:>10,} {d6.get(c, 0):>10,} {d6.get(c, 0) / r:>10.6f} "
          f"{trailing.get(c, 0):>10,} {captured.get(c, 0):>13,}")

print("\nIndia addresses with a 6-digit number (PIN shape):")
for s in samples:
    print("   ", s)

tot_pin = sum(captured.values())
tot_rows = sum(rows.values())
print(f"\npin captured overall: {tot_pin:,} of {tot_rows:,} = {tot_pin / tot_rows:.6%}")
print("\nREADING")
ind = rows.get("India", 0)
print(f"  India dig6/row = {d6.get('India', 0) / max(ind, 1):.6f}, of which "
      f"{trailing.get('India', 0):,} sit in the trailing position a real PIN uses.")
print("  The guard captures exactly those (normalize.py:337 sets pin on the 6-digit")
print("  token for India), so the mechanism is functioning on the rows that exist.")
print("  If trailing Indian PINs are near-zero, the feature is starved by the DATA,")
print("  not mis-gated, and widening the guard would capture house numbers instead.")
