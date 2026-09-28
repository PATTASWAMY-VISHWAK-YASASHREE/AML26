"""Characterise the ADDR_CANON_COMMON defect flagged by task D072.

D072 reported a real defect in ADDR_CANON_COMMON but did not characterise it.
This checks the structural risks directly against the source:

  1. tokens mapped to "" (deleted) - could any be load-bearing?
  2. per-country canon map: France drops {st,ste,dr,n,s,e,w} from common
  3. street-type tokens that collide with city names (measured on France data)
  4. French street types present in the data that neither table maps
"""
import ast
import re
import sys
from collections import Counter

sys.path.insert(0, "_upstream/src")
import normalize as N  # noqa: E402
import keys as K      # noqa: E402

src = open("_upstream/src/normalize.py", encoding="utf-8").read()
tables = {}
for node in ast.parse(src).body:
    if isinstance(node, ast.Assign):
        nm = getattr(node.targets[0], "id", "")
        if nm in ("ADDR_CANON_COMMON", "ADDR_CANON_FR"):
            tables[nm] = ast.literal_eval(node.value)

COMMON, FR = tables["ADDR_CANON_COMMON"], tables["ADDR_CANON_FR"]
DROPPED_FOR_FR = {"st", "ste", "dr", "n", "s", "e", "w"}

print("=== 1. entries that DELETE a token (map to '') ===")
dels = {k: v for k, v in COMMON.items() if v == ""}
print(f"  ADDR_CANON_COMMON: {len(dels)} entries map to '' -> {sorted(dels)}")
fdels = {k: v for k, v in FR.items() if v == ""}
print(f"  ADDR_CANON_FR    : {len(fdels)} entries map to '' -> {sorted(fdels)}")

print("\n=== 2. tokens France DROPS from the common map ===")
print(f"  dropped for France: {sorted(DROPPED_FOR_FR)}")
still = {k: COMMON[k] for k in DROPPED_FOR_FR if k in COMMON}
print(f"  of those, present in COMMON: {still}")
print(f"  of those, present in ADDR_CANON_FR: "
      f"{ {k: FR[k] for k in DROPPED_FOR_FR if k in FR} }")
gap = [k for k in DROPPED_FOR_FR if k in COMMON and k not in FR]
print(f"  => {len(gap)} token(s) have NO mapping at all under France: {gap}")
if gap:
    print("     These keep their raw form in France but are canonicalised in")
    print("     US/India - a silent cross-country inconsistency.")

print("\n=== 3. street-type tokens that are also French city names ===")
# French cities observed in the data (top 40 from earlier analysis)
CITIES = set("""bordeaux nantes lille tourcoing dunkerque roubaix calais saint-nazaire
pessac la-teste-de-buch merignac lege-cap-ferret pornic la-baule-escoublac
saint-herblain lomme le-clion hellemmes""".split())
street_vals = {v for v in COMMON.values() if v} | {v for v in FR.values() if v}
coll = sorted(CITIES & street_vals)
print(f"  canonical street values: {len(street_vals)}")
print(f"  collisions with observed French cities: {coll if coll else 'NONE'}")

print("\n=== 4. French street-type words in the data that neither table maps ===")
PATH = ("amazon_ml_2026_research/student_resource/dataset/test/test_source1.tsv")
# candidate street words = frequent address tokens that are alphabetic
import csv
freq = Counter()
with open(PATH, encoding="utf-8", errors="replace", newline="") as fh:
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    next(rd)
    for i, rec in enumerate(rd):
        if len(rec) < 4 or rec[3].strip() != "France":
            continue
        toks, _n, _s, _p, _c = N.normalize_address(rec[2], "France")
        freq.update(toks)
        if i > 80_000:
            break

allkeys = set(COMMON) | set(FR)
GENERIC = set(K.ADDR_GENERIC)   # lives in keys.py, not normalize.py
unmapped = [(t, c) for t, c in freq.most_common(150)
            if t not in allkeys and t not in GENERIC and not t.isdigit()
            and len(t) > 2]
print("  frequent French address tokens NOT in either canon table and not")
print("  in ADDR_GENERIC (candidates for unhandled street/place words):")
for t, c in unmapped[:22]:
    print(f"    {c:>7,}  {t}")
print(f"\n  (showing {min(22, len(unmapped))} of {len(unmapped)} candidates)")
