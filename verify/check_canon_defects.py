"""The two real ADDR_CANON issues, quantified against real data.

These are the only two defects the dictionary audits left standing, so this
settles them rather than restating them.

ISSUE A - 15 ADDR_CANON_COMMON entries map to "" and DELET the token.
  The risk is concentrated in short tokens: 'h' and 'hno' are plausible
  standalone address tokens, while 'null'/'na'/'none' are obviously safe.
  Deleting a load-bearing token removes it from atoks, which changes the
  blocking keys built from it (keys.py:39-43) and the address features.
  Question: does deleting 'h'/'hno' actually cost anything on this data?

ISSUE B - France drops {st,ste,dr,n,s,e,w} from the common map, and w/e/s have
  no mapping at all under France, while US/India canonicalise them.
  Question: how often do w/e/s actually appear in French addresses, and does the
  inconsistency change any canonical token?
"""
import ast
import csv
import sys
from collections import Counter

sys.path.insert(0, "_upstream/src")
import normalize as N  # noqa: E402

src = open("_upstream/src/normalize.py", encoding="utf-8").read()
COMMON = FR = None
for node in ast.parse(src).body:
    if isinstance(node, ast.Assign):
        nm = getattr(node.targets[0], "id", "")
        if nm == "ADDR_CANON_COMMON":
            COMMON = ast.literal_eval(node.value)
        elif nm == "ADDR_CANON_FR":
            FR = ast.literal_eval(node.value)

BASE = "amazon_ml_2026_research/student_resource/dataset"
CAP = 120_000

# ---------------------------------------------------------------- ISSUE A
DELETING = sorted(k for k, v in COMMON.items() if v == "")
SUSPECT = {"h", "hno", "house", "door", "plot", "flat", "shop", "num",
           "number", "nos"}

print("=" * 72)
print("ISSUE A - do the token-deleting entries cost anything?")
print("=" * 72)
print(f"{len(DELETING)} entries map to '': {DELETING}\n")
print("Frequency of each deleting token as a RAW (pre-canon) address token,")
print("per country. If a suspect token is frequent, deleting it is costly.\n")

raw = Counter()
rows = Counter()
for split in ("test", "train"):
    for s in (1, 2, 3):
        p = f"{BASE}/{split}/{split}_source{s}.tsv"
        with open(p, encoding="utf-8", errors="replace", newline="") as fh:
            rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
            next(rd)
            for i, rec in enumerate(rd):
                if len(rec) < 4:
                    continue
                c = rec[3].strip()
                if c not in ("US", "India", "France"):
                    continue
                rows[c] += 1
                # tokens BEFORE canon, mirroring the _non_alnum split at
                # normalize.py:342
                for comp in rec[2].lower().split(","):
                    for t in N._non_alnum.split(comp):
                        if t and t in SUSPECT:
                            raw[(c, t)] += 1
                if i > CAP:
                    break

print(f"{'token':8s} " + "  ".join(f"{c:>10s}" for c in ("US", "India", "France")))
for t in sorted(SUSPECT):
    cells = []
    for c in ("US", "India", "France"):
        n = raw.get((c, t), 0)
        cells.append(f"{n:>10,}" if n else "         .")
    print(f"{t:8s} " + "  ".join(cells))

print(f"\nrows scanned: " + ", ".join(f"{c}={rows[c]:,}" for c in
                                      ("US", "India", "France")))
total_suspect = sum(raw.values())
print(f"total occurrences of any suspect token: {total_suspect:,}")
print("\nVERDICT A: if the suspect column is mostly '.' then deleting these is")
print("harmless on this dataset. If a token is frequent, the deletion is real.")

# ---------------------------------------------------------------- ISSUE B
print("\n" + "=" * 72)
print("ISSUE B - France w/e/s gap")
print("=" * 72)
DROPPED = {"w", "e", "s"}
gap = sorted(DROPPED - set(FR))
print(f"tokens in the France drop-set with NO mapping in ADDR_CANON_FR: {gap}")
print(f"their COMMON mappings: "
      f"{ {k: COMMON[k] for k in gap if k in COMMON} }\n")

for split in ("test",):
    for s in (1, 2, 3):
        p = f"{BASE}/{split}/{split}_source{s}.tsv"
        hits = Counter()
        nfr = 0
        with open(p, encoding="utf-8", errors="replace", newline="") as fh:
            rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
            next(rd)
            for i, rec in enumerate(rd):
                if len(rec) < 4 or rec[3].strip() != "France":
                    continue
                nfr += 1
                for comp in rec[2].lower().split(","):
                    for t in N._non_alnum.split(comp):
                        if t in DROPPED:
                            hits[t] += 1
                if i > CAP:
                    break
        tot = sum(hits.values())
        print(f"  {split}_source{s}: France rows={nfr:,}  w/e/s tokens={tot:,}"
              f"  {dict(hits)}")

print("\nVERDICT B: these are rare directionals. But note the REAL asymmetry -")
print("'st' means 'saint' in France but 'street' in US, which is exactly why")
print("France drops it. That part is correct design, not a defect.")
