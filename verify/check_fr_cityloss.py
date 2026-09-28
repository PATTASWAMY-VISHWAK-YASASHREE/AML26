"""Real France defect: a postal-code-prefixed city component loses the city.

normalize_address line 351 classifies a component as 'city' only if it contains
NO digits:
    if not any(ch.isdigit() for ch in c) and ctoks: city_comps.append(...)
So "33000 Bordeaux" is NOT recorded as a city, while "Bordeaux" is. France
commonly writes the code inline with the city. Quantify how often, and check
whether the token still reaches the blocking keys (it appears to - toks keeps
'bordeaux' via TOKEN_RE).
"""
import csv
import re
import sys
from collections import Counter

sys.path.insert(0, "_upstream/src")
import normalize as N  # noqa: E402

PATH = ("amazon_ml_2026_research/student_resource/dataset/test/test_source1.tsv")
CP = re.compile(r"[,;]")
LEAD5 = re.compile(r"^\s*\d{5}\s+(?=\D)")

n = 0
has_city = 0
city_lost = 0
lost_examples = []
kept_examples = []
comp_pos = Counter()

with open(PATH, encoding="utf-8", errors="replace", newline="") as fh:
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    next(rd)
    for rec in rd:
        if len(rec) < 4 or rec[3].strip() != "France":
            continue
        n += 1
        addr = rec[2]
        toks, nums, st, pin, comps = N.normalize_address(addr, "France")
        if comps:
            has_city += 1
        if LEAD5.search(addr):
            city_lost += 1
            if len(lost_examples) < 12:
                lost_examples.append((addr[:60], comps))
        elif comps and len(kept_examples) < 6:
            kept_examples.append((addr[:60], comps))
        for i, c in enumerate([x.strip() for x in CP.split(addr.lower())]):
            if LEAD5.match(c):
                comp_pos[i] += 1

print(f"France source-1 rows: {n:,}")
print(f"rows where city_comps is populated : {has_city:,} ({has_city/n:.2%})")
print(f"rows with a 'NNNNN City' component  : {city_lost:,} ({city_lost/n:.2%})")
print(f"  -> city LOST from city_comps in    : {city_lost:,} rows "
      f"({city_lost/n:.2%} of all France rows)")
print(f"\nposition of the code-prefixed component: {dict(sorted(comp_pos.items()))}")

print("\nexamples where the city is LOST:")
for a, c in lost_examples:
    print(f"  {a:60s} -> city_comps={c}")
print("\nexamples where the city is KEPT:")
for a, c in kept_examples:
    print(f"  {a:60s} -> city_comps={c}")

print("\n=== does the token still reach blocking keys? ===")
for addr in ["33000 Bordeaux, 175 Rue Wilson", "Bordeaux, 175 Rue Wilson"]:
    toks, nums, st, pin, comps = N.normalize_address(addr, "France")
    print(f"  {addr:34s} toks={toks} nums={nums} city_comps={comps}")
