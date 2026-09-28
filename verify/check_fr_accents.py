"""France-specific risk: accents, and how normalize.py handles them.

French place names are heavily accented (Mérignac, Lège-Cap-Ferret, Côte-d'Azur).
My earlier token analysis stripped accents via [a-z0-9]+, so I must check whether
the real normaliser preserves them or folds them - because if it folds them, two
different places could collide, and if it preserves them, then a source using
unaccented text will not match.

Streams the France rows of one test file.
"""
import csv
import re
import sys
import unicodedata
from collections import Counter

PATH = (sys.argv[1] if len(sys.argv) > 1 else
        "amazon_ml_2026_research/student_resource/dataset/test/test_source1.tsv")

n = 0
with_accent = 0
accented_examples = Counter()
# how strip_accents (normalize.py:264) would fold them
fold_map = Counter()

with open(PATH, encoding="utf-8", errors="replace", newline="") as fh:
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    next(rd)
    for rec in rd:
        if len(rec) < 4 or rec[3].strip() != "France":
            continue
        n += 1
        txt = rec[1] + " " + rec[2]
        found = [ch for ch in txt if ord(ch) > 127]
        if found:
            with_accent += 1
            for ch in set(found):
                accented_examples[ch] += 1
                fold_map[unicodedata.normalize("NFKD", ch).encode(
                    "ascii", "ignore").decode()] += 1
        if n >= 200000:
            break

print(f"France rows scanned: {n:,}")
print(f"rows containing a non-ASCII character: {with_accent:,} "
      f"({with_accent/max(n,1):.2%})\n")
print("top accented characters, with their NFKD->ascii folding:")
print(f"  {'char':6s} {'codepoint':10s} {'count':>8s}  folds to")
for ch, c in accented_examples.most_common(15):
    folded = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode()
    print(f"  {ch!r:6s} U+{ord(ch):04X}     {c:>8,}  {folded!r}")
print("\nCollisions caused by folding (two distinct chars -> same ascii):")
inv = {}
for ch, c in accented_examples.items():
    f = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode()
    inv.setdefault(f, []).append(ch)
coll = {k: v for k, v in inv.items() if len(v) > 1}
if coll:
    for k, v in coll.items():
        print(f"  {k!r} <- {v}")
else:
    print("  none in the top characters")
