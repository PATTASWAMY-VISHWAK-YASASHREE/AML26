"""Precise France coverage: replicate normalize_address's EXACT matching logic.

The previous check used substring matching, which is far looser than the real
code. normalize.py does: split address on commas, strip each component to
[a-z0-9& ], then test `if ck in smap` -- an EXACT component match against
STATE_MAPS["France"], which is FR_REGIONS.
"""
import ast
import csv
import re
import sys
from collections import Counter

sys.path.insert(0, "_upstream/src")

NORM = "_upstream/src/normalize.py"

# pull FR_REGIONS straight out of the source so this cannot drift
tree = ast.parse(open(NORM, encoding="utf-8").read())
FR_REGIONS = None
for node in tree.body:
    if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "FR_REGIONS":
        FR_REGIONS = ast.literal_eval(node.value)
assert FR_REGIONS, "FR_REGIONS not found"
print(f"FR_REGIONS: {len(FR_REGIONS)} entries, {len(set(FR_REGIONS.values()))} distinct values")

PATH = (sys.argv[1] if len(sys.argv) > 1 else
        "amazon_ml_2026_research/student_resource/dataset/test/test_source1.tsv")

EMPTYISH = ("null", "<null>", "n/a", "na", "none")


def normalise_state(addr):
    """Exact replication of the state-extraction part of normalize_address."""
    found = ""
    for c in addr.lower().split(","):
        c = c.strip()
        if not c or c in EMPTYISH:
            continue
        ck = re.sub(r"[^a-z0-9& ]+", " ", c).replace("&", " and ")
        ck = " ".join(ck.split())
        if ck in FR_REGIONS:
            found = FR_REGIONS[ck]
    return found


n = 0
hit = 0
unmatched = Counter()
with open(PATH, encoding="utf-8", errors="replace", newline="") as fh:
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    next(rd)
    for rec in rd:
        if len(rec) < 4 or rec[3].strip() != "France":
            continue
        n += 1
        if normalise_state(rec[2]):
            hit += 1
        else:
            for c in rec[2].lower().split(","):
                ck = re.sub(r"[^a-z0-9& ]+", " ", c).replace("&", " and ")
                unmatched[" ".join(ck.split())] += 1

print(f"\nFrance rows: {n:,}")
print(f"state resolved via FR_REGIONS: {hit:,} ({hit / max(n,1):.2%})")
print(f"state NOT resolved           : {n - hit:,} ({(n - hit) / max(n,1):.2%})")
print("\ntop 20 unmatched components (candidate expansions):")
for c, k in unmatched.most_common(20):
    print(f"  {k:>8,}  {c!r}")
