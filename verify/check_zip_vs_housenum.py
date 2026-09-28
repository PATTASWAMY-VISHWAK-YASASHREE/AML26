"""DECISIVE TEST: are the leading 5-digit US numbers ZIPs or house numbers?

Two agents disagree about the same measurement, and the disagreement decides
whether FRANCE_FINDINGS N0 needs a US fix at all:

  reading A (N0-R)  the leading 5-digit is a HOUSE number, so there is no US
                    postal signal and the fix should be dropped entirely.
  reading B          the convention is "<zip> <street>, <city>, <state>", so the
                    leading 5-digit IS the ZIP and the fix is worth a rescope.

Both agree on the raw facts: 10.9% of US rows contain a standalone 5-digit, it
leads its component 98% of the time, and the state closes the string 86% of the
time. They disagree on what the number MEANS. Reading A cites "STATE <5-digit>"
never occurring; reading B cites position.

This separates them using a property of the DATA itself, needing no external ZIP
table, because ZIP structure is intrinsic:

  T1 GEOGRAPHIC CLUSTERING. A ZIP is a geographic unit: rows sharing a
     (city, state) should share the ZIP prefix. House numbers are per-building
     and spread near-uniformly over 00000-99999. Per city, measure the share of
     rows whose 5-digit falls in that city's most common 3-digit prefix.
     ZIP -> high. House number -> ~chance.

  T2 FIRST-DIGIT SKEW. Real US ZIPs are not uniform over 0-9; they concentrate
     in ranges assigned decades ago. A house-number field is ~uniform.

T1 is decisive alone. Read-only, streaming, bounded.
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

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "test", "test_source1.tsv")
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 1_500_000

us = lead = 0
first_digit = Counter()
pref_by_city = defaultdict(Counter)
city_n = Counter()
n_lead = Counter()
samples_multi = []

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
            z = m.group(0)
            lead += 1
            first_digit[z[0]] += 1
            comps = [c.strip() for c in a.split(",") if c.strip()]
            if comps and comps[-1].lower().strip(".") in US_STATES:
                st = comps[-1].lower().strip(".")
                city = comps[-2].lower() if len(comps) >= 2 else ""
            else:
                st, city = "", comps[0].lower() if comps else ""
            if city:
                pref_by_city[(city, st)][z[:3]] += 1
                city_n[(city, st)] += 1
            k = len(DIG5.findall(a))
            n_lead[k] += 1
            if k > 1 and len(samples_multi) < 6:
                samples_multi.append(a[:88])
        if us >= LIMIT:
            break

print(f"file {os.path.relpath(path, ROOT)}")
print(f"US rows {us:,}   leading-5-digit rows {lead:,} ({lead / max(us, 1):.2%})\n")

print("T1 GEOGRAPHIC CLUSTERING  (decisive)")
print("   Per (city,state) with >=20 rows: share of leading 5-digits falling in")
print("   that city's single most common 3-digit prefix.")
print("   ZIP -> HIGH (geographic unit).  House number -> ~chance (per-building).\n")
shares = []
rich = []
for key, c in city_n.items():
    if c < 20:
        continue
    top, tc = pref_by_city[key].most_common(1)[0]
    shares.append(tc / c)
    rich.append((tc / c, key, c, top))
shares.sort(reverse=True)
rich.sort(reverse=True)
if shares:
    n = len(shares)
    mean = sum(shares) / n
    print(f"   cities examined (>=20 rows) : {n:,}")
    print(f"   mean top-prefix share      : {mean:.2%}")
    print(f"   median                     : {shares[n // 2]:.2%}")
    print(f"   min                        : {shares[-1]:.2%}")
    hi = sum(1 for s in shares if s > 0.30)
    print(f"   cities with share > 30%    : {hi:,} / {n:,} ({hi / n:.2%})")
    print("\n   highest-share cities (top 8):")
    for sh, key, c, top in rich[:8]:
        print(f"      {key[0][:28]:28s} {key[1]:3s} n={c:>5,} top3={top} share={sh:6.2%}")

print("\nT2 FIRST-DIGIT SKEW (uniform = 10.00% each)")
tot = sum(first_digit.values()) or 1
for k, v in sorted(first_digit.items()):
    print(f"   {k}: {v:>8,}  {v / tot:7.2%}  {'#' * int(round(v / tot * 200))}")

print("\nT3 context: standalone 5-digit count per row")
for k, v in sorted(n_lead.items()):
    print(f"   {k} : {v:>8,}  ({v / tot:.2%})")
if samples_multi:
    print("   rows with >1 such number (samples):")
    for s in samples_multi:
        print("      ", s)

print("\nREADING")
if shares:
    m = sum(shares) / len(shares)
    if m > 0.30:
        print(f"   Mean top-prefix share {m:.2%} is far above chance -> the leading 5-digit")
        print("   CLUSTERS BY CITY, the signature of a POSTAL CODE. Reading B holds:")
        print("   convention is '<zip> <street>, <city>, <state>'; US postal signal real.")
    else:
        print(f"   Mean top-prefix share {m:.2%} is near chance -> the leading 5-digit does")
        print("   NOT cluster by city, the signature of a HOUSE NUMBER. Reading A holds:")
        print("   no US postal signal; N0's US fix should be dropped, not rescoped.")