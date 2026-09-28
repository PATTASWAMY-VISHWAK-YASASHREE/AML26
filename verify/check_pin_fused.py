"""Are the 118 'captured' Indian pins actually POSTAL CODES?

check_pin_cause.py found India has 118 rows with a 6-digit number and the guard
captured all 118. But the samples looked like text/number CONCATENATION rather
than a postal code:
    "Chetpet Madras600038"      <- city name fused to the PIN
    "Navanagar T72 P2 H217172"  <- house + plot fused, no PIN boundary

If the captured values are mostly fused/concatenated tokens, then even the rows
the guard 'works' on do not carry a clean postal signal, and the feature is dead
for a third reason: there is no trustworthy PIN to capture.

Checks, on Indian rows only, streaming and bounded:
  1. is the 6-digit run immediately preceded by a letter (fused city/plot)?
  2. is it a whole whitespace-delimited token (clean, standalone PIN)?
  3. is it a plausible Indian PIN by first-digit region prefix (1-9)?

Read-only.
"""
from __future__ import annotations

import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True  # keep the pristine _upstream tree clean
sys.path.insert(0, os.path.join(ROOT, "_upstream", "src"))
import normalize as N  # noqa: E402

BASE = os.path.join(ROOT, "amazon_ml_2026_research", "student_resource", "dataset")
DIG6 = re.compile(r"(?<!\d)\d{6}(?!\d)")
FUSED = re.compile(r"[A-Za-z]\d{6}\b")          # letters immediately before
CLEAN = re.compile(r"(?:^|\s)\d{6}(?:\s|$)")    # standalone whitespace token

path = os.path.join(BASE, "train", "train_source1.tsv")
LIMIT = 1_500_000

fused = clean = standalone = total = 0
pref = {}
ex_fused, ex_clean = [], []

with open(path, encoding="utf-8", errors="replace", newline="") as fh:
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    next(rd)
    n = 0
    for rec in rd:
        if len(rec) < 4 or rec[3].strip() != "India":
            continue
        n += 1
        a = rec[2]
        _t, _nums, _s, pin, _cc = N.normalize_address(a, "India")
        if not pin:
            continue
        total += 1
        pref[pin[0]] = pref.get(pin[0], 0) + 1
        f = bool(FUSED.search(a))
        c = bool(CLEAN.search(a))
        fused += f
        clean += c
        standalone += (not f)
        if f and len(ex_fused) < 8:
            ex_fused.append((pin, a[:88]))
        if c and len(ex_clean) < 8:
            ex_clean.append((pin, a[:88]))
        if n >= LIMIT:
            break

print(f"Indian rows scanned            : {n:,}")
print(f"rows where pin was captured    : {total:,}")
if total:
    print(f"  preceded by a letter (FUSED) : {fused:,} ({fused / total:.2%})")
    print(f"  a clean whitespace token     : {clean:,} ({clean / total:.2%})")
    print(f"  not fused                    : {standalone:,} ({standalone / total:.2%})")
    print(f"  first-digit distribution     : {dict(sorted(pref.items()))}")

print("\nfused examples (city/plot glued to digits):")
for p, a in ex_fused:
    print(f"   pin={p}  {a}")
print("\nclean examples:")
for p, a in ex_clean:
    print(f"   pin={p}  {a}")

print("\nREADING")
if total:
    print(f"  {fused / total:.1%} of captured values are fused to a preceding word,")
    print("  which is the signature of a formatting artefact, not a postal code.")
    print(f"  A real Indian PIN appears as its own token in only {clean / total:.1%}")
    print("  of these rows.")
