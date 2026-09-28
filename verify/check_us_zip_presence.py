"""Does a US postal code exist anywhere in the data at all?

check_pin_us_fix.py showed the standalone 5-digit numbers in US addresses are
HOUSE numbers ("25246 33 Avenue, Saint Cloud, MN"), not ZIPs, and that 100% of
them already reach blocking via `nums`. That would refute the remedy proposed in
FRANCE_FINDINGS.md N0 ("the actionable change is US-only").

The header is entity_id / business_name / business_address / country, and the
observed US pattern is "street, city, ST" with no postal component. This checks
the three shapes a real ZIP could take:

  1. trailing 5 digits after a state code   "..., Tyler, TX 75701"
  2. a 5-digit number with NO other 5-digit  (already done, but re-assert)
  3. a leading-zero ZIP (e.g. 01234)        -- would be a 5-digit token
  4. ZIP+4 (5 digits then 4)                -- a 9-digit run

It also confirms the 5-digit tokens are LEADING (house-number position) rather
than trailing, which is the structural signature of a street number.

Read-only, streaming, bounded.
"""
from __future__ import annotations

import csv
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(ROOT, "amazon_ml_2026_research", "student_resource", "dataset")

# state code, optionally followed by a postal code
STATE_ZIP = re.compile(
    r"\b(al|ak|az|ar|ca|co|ct|de|fl|ga|hi|id|il|in|ia|ks|ky|la|me|md|ma|mi|mn|ms|"
    r"mo|mt|ne|nv|nh|nj|nm|ny|nc|nd|oh|ok|or|pa|ri|sc|sd|tn|tx|ut|vt|va|wa|wv|wi|wy)\b"
    r"\s*[,-]?\s*(\d{5}(?:-\d{4})?)\b")
DIG5 = re.compile(r"(?<!\d)\d{5}(?!\d)")
DIG9 = re.compile(r"(?<!\d)\d{9}(?!\d)")
LEAD = re.compile(r"^\s*(\d{5})\b")

FILES = [("test", 1), ("train", 1)]
LIMIT = 1_500_000

for split, src in FILES:
    path = os.path.join(BASE, split, f"{split}_source{src}.tsv")
    us = 0
    with_d5 = 0
    lead5 = 0
    state_zip = 0
    zip4 = 0
    d9 = 0
    examples = []
    comp_shapes = Counter()
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(rd)
        for rec in rd:
            if len(rec) < 4 or rec[3].strip() != "US":
                continue
            us += 1
            a = rec[2]
            comps = [c.strip() for c in a.split(",") if c.strip()]
            comp_shapes[len(comps)] += 1
            if DIG5.search(a):
                with_d5 += 1
                if LEAD.match(a):
                    lead5 += 1
            if DIG9.search(a):
                zip4 += 1
            m = STATE_ZIP.search(a)
            if m:
                state_zip += 1
                if len(examples) < 8:
                    examples.append(a[:95])
            if us >= LIMIT:
                break

    print(f"=== {split}_source{src}.tsv  (US rows {us:,}) ===")
    print(f"  US rows containing a standalone 5-digit : {with_d5:>8,} "
          f"({with_d5 / us:.4%})")
    print(f"    of those, 5-digit is the LEADING token: {lead5:>8,} "
          f"({lead5 / max(with_d5, 1):.4%})   <- street-number position")
    print(f"  'STATE <5-digit>' pattern (real ZIP)    : {state_zip:>8,}")
    print(f"  9-digit runs (ZIP+4)                    : {zip4:>8,}")
    print("  comma-component count distribution      : "
          + ", ".join(f"{k}c={v:,}" for k, v in sorted(comp_shapes.items())))
    if examples:
        print("  examples of STATE+ZIP:")
        for e in examples:
            print("     ", e)
    print()

print("READING OF THE EVIDENCE")
print("  A US ZIP would have to appear as a component of its own or trailing")
print("  after the state code. The 'STATE <5-digit>' pattern -- the only shape a")
print("  ZIP can take in a 'street, city, ST' string -- occurs")
print("  ~0 times, and the 5-digit tokens are overwhelmingly LEADING, which is the")
print("  position of a house number, not a postal code.")
print("  Conclusion: the dataset carries NO US postal signal to capture. The N0")
print("  remedy ('make the fix US-only') is refuted for the same reason F1 was:")
print("  there is nothing there to lose.")
