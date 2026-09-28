"""Direct France analysis - the only country in the test set, absent from training.

Streaming, low-memory. Answers the questions the refuted findings were standing
in the way of: what do French addresses actually contain, and is anything about
them a problem for the upstream normaliser?
"""
import csv
import re
import sys
from collections import Counter

PATH = (sys.argv[1] if len(sys.argv) > 1 else
        "amazon_ml_2026_research/student_resource/dataset/test/test_source1.tsv")

TOKEN = re.compile(r"[a-z0-9]+")
LEAD_NUM = re.compile(r"^\s*(\d+)\s*(bis|ter|quater)?\b")
ANY_NUM = re.compile(r"\d+")
EMPTYISH = ("null", "<null>", "n/a", "na", "none")

n = 0
lead_num = 0
bis_ter = 0
no_digit = 0
no_comma = 0
comps = Counter()          # position of region component
city_at = Counter()        # index of the city-looking component
n_comps = Counter()
region_first = 0
region_last = 0
region_mid = 0
places = Counter()
region_words = {
    "hauts-de-france", "nouvelle-aquitaine", "pays de la loire", "ile-de-france",
    "bretagne", "normandie", "grand est", "occitanie", "lorraine", "alsace",
    "picardie", "limousin", "corse", "nord-pas-de-calais",
}
street = {
    "rue", "boulevard", "bd", "avenue", "av", "chemin", "impasse", "place",
    "allee", "cours", "quai", "faubourg", "route", "square", "rte",
}
with open(PATH, encoding="utf-8", errors="replace", newline="") as fh:
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    next(rd)
    for rec in rd:
        if len(rec) < 4 or rec[3].strip() != "France":
            continue
        n += 1
        addr = rec[2]
        low = addr.lower().strip()
        if not low or low in EMPTYISH:
            continue
        m = LEAD_NUM.match(low)
        if m:
            lead_num += 1
            if m.group(2):
                bis_ter += 1
        if not ANY_NUM.search(low):
            no_digit += 1
        parts = [p.strip() for p in low.split(",") if p.strip()]
        n_comps[len(parts)] += 1
        if len(parts) == 1:
            no_comma += 1
        ridx = [i for i, p in enumerate(parts) if p in region_words]
        if ridx:
            if ridx[0] == 0:
                region_first += 1
            elif ridx[0] == len(parts) - 1:
                region_last += 1
            else:
                region_mid += 1
        for p in parts:
            toks = TOKEN.findall(p)
            if not toks:
                continue
            if toks[0] in street or p in street:
                continue
            if p in region_words:
                continue
            if ANY_NUM.fullmatch(toks[0]):
                continue
            places[" ".join(toks)] += 1

print(f"France rows analysed: {n:,}\n")
print("--- numeric content ---")
print(f"  leading house number      {lead_num:>8,}  ({lead_num/n:6.2%})")
print(f"  of those, bis/ter suffix   {bis_ter:>8,}  ({bis_ter/n:6.2%})")
print(f"  NO digit anywhere         {no_digit:>8,}  ({no_digit/n:6.2%})")
print("\n--- address structure ---")
print(f"  single component (no comma) {no_comma:>7,}  ({no_comma/n:6.2%})")
print(f"  component count distribution:")
for k, v in sorted(n_comps.items())[:8]:
    print(f"      {k:>2} comps: {v:>8,}  ({v/n:6.2%})")
tot = region_first + region_last + region_mid
print(f"\n--- region component POSITION (of {tot:,} rows with a region) ---")
print(f"  region first   {region_first:>8,}  ({region_first/tot:6.2%})")
print(f"  region middle  {region_mid:>8,}  ({region_mid/tot:6.2%})")
print(f"  region last    {region_last:>8,}  ({region_last/tot:6.2%})")
print("\n--- top 25 place-like components ---")
for p, c in places.most_common(25):
    print(f"  {c:>8,}  {c/n:6.3%}  {p}")
top10 = sum(c for _, c in places.most_common(10))
print(f"\n  top-10 places cover {top10:,} rows = {top10/n:.2%} of France")
print(f"  distinct place components seen: {len(places):,}")
