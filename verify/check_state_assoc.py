"""Final discriminator: does the leading 5-digit track the STATE, as a ZIP must?

T1 (check_zip_vs_housenum.py) already refuted the ZIP reading -- no city
clustering, 0/537 cities above a 30% top-prefix share. This adds the one test
that separates the two readings most sharply, and it is the reason a ZIP cannot
hide: even a synthetic ZIP is normally allocated per state.

  S1 STATE / PREFIX ASSOCIATION. A ZIP's leading digits are allocated by
     region, so knowing the prefix should narrow the state a lot. A house
     number carries no geography, so prefix and state should be independent.
     Measure: the share of rows in the most common state for each 2-digit
     prefix, versus the share for the most common prefix within each state.
     ZIP -> both high. House number -> both near the base rate.

  S2 RANGE TOKENS. Already-seen but worth counting formally: "10100 -14100
     Greenwell Springs Road" is a house-number RANGE. A ZIP is never a range,
     so any row whose leading number is followed by a dash-and-number is
     conclusive on its own.

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
US_STATES = {"al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi",
             "id", "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi",
             "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc",
             "nd", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut",
             "vt", "va", "wa", "wv", "wi", "wy", "dc"}
RANGE = re.compile(r"^\s*\d{4,6}\s*[-–]\s*\d{4,6}\b")

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "test", "test_source1.tsv")
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 1_500_000

us = 0
prefix_state = defaultdict(Counter)   # 2-digit prefix -> Counter of state
state_prefix = defaultdict(Counter)   # state -> Counter of prefix
state_all = Counter()
prefix_all = Counter()
ranges = 0
range_ex = []
lead_n = 0

with open(path, encoding="utf-8", errors="replace", newline="") as fh:
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    next(rd)
    for rec in rd:
        if len(rec) < 4 or rec[3].strip() != "US":
            continue
        us += 1
        a = rec[2]
        st = ""
        comps = [c.strip() for c in a.split(",") if c.strip()]
        if comps and comps[-1].lower().strip(".") in US_STATES:
            st = comps[-1].lower().strip(".")
        if RANGE.match(a):
            ranges += 1
            if len(range_ex) < 8:
                range_ex.append(a[:88])
        m = DIG5.match(a.strip())
        if m and st:
            lead_n += 1
            p = m.group(0)[:2]
            prefix_state[p][st] += 1
            state_prefix[st][p] += 1
            state_all[st] += 1
            prefix_all[p] += 1
        if us >= LIMIT:
            break

print(f"file {os.path.relpath(path, ROOT)}")
print(f"US rows {us:,}   rows with leading 5-digit AND a state code: {lead_n:,}\n")

print("S2 RANGE TOKENS (conclusive if any exist)")
print(f"   US addresses of the form '<n> - <n> ...' : {ranges:,}")
for e in range_ex:
    print(f"      {e}")
print("   A ZIP code is never a range. A house number often is.")
print()

print("S1 STATE / PREFIX ASSOCIATION")
tot = lead_n or 1
ps = []
for p, c in prefix_state.items():
    if sum(c.values()) < 20:
        continue
    ps.append(max(c.values()) / sum(c.values()))
sp = []
for st, c in state_prefix.items():
    if sum(c.values()) < 20:
        continue
    sp.append(max(c.values()) / sum(c.values()))
ps.sort(reverse=True)
sp.sort(reverse=True)
if ps:
    print(f"   prefixes examined (>=20 rows) : {len(ps):,}")
    print(f"   mean share in the single most common STATE, per prefix : "
          f"{sum(ps) / len(ps):.2%}")
    print(f"   best prefix -> one state covers {ps[0]:.2%} of its rows")
    print(f"   states examined (>=20 rows)   : {len(sp):,}")
    print(f"   mean share in the single most common PREFIX, per state : "
          f"{sum(sp) / len(sp):.2%}")
    print(f"   best state -> one prefix covers {sp[0]:.2%} of its rows")
    print()
    print(f"   base rate: most common state overall = "
          f"{max(state_all.values()) / tot:.2%}; most common prefix overall = "
          f"{max(prefix_all.values()) / tot:.2%}")
    print("   If prefix and state were independent, both means would sit near the")
    print("   base rate. A real ZIP allocation drives both far above it.")

print("\nREADING")
if ps:
    a = sum(ps) / len(ps)
    b = max(state_all.values()) / tot
    if a > 3 * b:
        print(f"   Prefix predicts state ({a:.2%} vs {b:.2%} base rate) -> GEOGRAPHIC,")
        print("   the signature of a postal code. Reading B would hold.")
    else:
        print(f"   Prefix does NOT predict state ({a:.2%} vs {b:.2%} base rate) ->")
        print("   the number carries no geography, the signature of a HOUSE NUMBER.")
        print("   Combined with S2 and T1, the US postal-signal reading is refuted")
        print("   three independent ways: N0's US fix should be DROPPED, not rescoped.")