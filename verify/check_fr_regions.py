"""Which French region/departement labels actually appear in the data?

Reads only the France rows of one test source file, streaming.
"""
import csv
import re
import sys
from collections import Counter

PATH = (sys.argv[1] if len(sys.argv) > 1 else
        "amazon_ml_2026_research/student_resource/dataset/test/test_source1.tsv")

REGIONS = [
    "auvergne-rhone-alpes", "basse-normandie", "bourgogne-franche-comte",
    "bretagne", "centre-val de loire", "corse", "grand est", "hauts-de-france",
    "ile-de-france", "normandie", "nouvelle-aquitaine", "occitanie",
    "pays de la loire", "provence-alpes-cote d'azur",
    "provence-alpes-cote dazur", "ile de france", "franche-comte",
    "nord-pas-de-calais", "limousin", "picardie", "poitou-charentes",
    "midi-pyrenees", "aquitaine", "champagne-ardenne", "lorraine",
    "alsace", "haute-normandie", "basse-saxe", "la reunion",
]
REGIONS = [r.lower() for r in REGIONS]

# what FR_REGIONS currently maps
CURRENT = {
    "hauts de france": "hdf", "nord": "hdf", "pas de calais": "hdf",
    "somme": "hdf", "aisne": "hdf", "oise": "hdf",
    "nouvelle aquitaine": "naq", "gironde": "naq", "landes": "naq",
    "pays de la loire": "pdl", "loire atlantique": "pdl", "vendee": "pdl",
    "ile de france": "idf", "paris": "idf",
}

COMP = re.compile(r"[,;]")
n = 0
comp_counter = Counter()          # exact component strings
region_hits = Counter()           # which region name matched
covered = 0
examples_uncovered = []

with open(PATH, encoding="utf-8", errors="replace", newline="") as fh:
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    next(rd)
    for rec in rd:
        if len(rec) < 4 or rec[3].strip() != "France":
            continue
        n += 1
        addr = rec[2]
        low = addr.lower()
        comps = [c.strip() for c in COMP.split(low)]
        for c in comps:
            comp_counter[c] += 1
        matched = False
        for r in REGIONS:
            if r in low:
                region_hits[r] += 1
                matched = True
        norm = " ".join(addr.lower().replace("-", " ").split())
        for key in CURRENT:
            if key in norm:
                covered += 1
                matched = True
                break
        if not matched and len(examples_uncovered) < 15:
            examples_uncovered.append(addr[:100])

print(f"France rows: {n:,}")
print(f"rows whose address contains a known region name : {sum(region_hits.values()):,}")
print(f"rows matchable by CURRENT FR_REGIONS keys        : {covered:,} "
      f"({covered / max(n,1):.2%})")
print("\nregion name frequency in France addresses:")
for r, c in region_hits.most_common():
    print(f"  {c:>8,}  {r}")
print("\ntop 30 raw comma-components in France addresses:")
for c, k in comp_counter.most_common(30):
    print(f"  {k:>8,}  {c!r}")
print("\nexamples with NO recognisable region:")
for e in examples_uncovered:
    print("   ", e)
