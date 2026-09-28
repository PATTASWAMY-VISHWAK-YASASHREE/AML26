"""Does the ligature gap actually matter? Count real occurrences in France rows.

strip_accents uses NFKD + drop-combining-marks, which does NOT decompose the
ligatures oe/ae/OE/AE, nor sharp-s, o-stroke or d-stroke. _non_alnum then splits
on [^a-z0-9]+, so a surviving ligature is DELETED, not just left accented:
  "Œuvre" -> "uvre"
  "Forêts" -> "Forets"  (this one folds fine, e is a combining-mark case)
So the damage is silent character DROPPING, which can make two different French
names collide. Count how many rows are affected and show concrete examples.
"""
import csv
import re
import sys
import unicodedata
from collections import Counter

PATH = (sys.argv[1] if len(sys.argv) > 1 else
        "amazon_ml_2026_research/student_resource/dataset/test/test_source1.tsv")

# characters that survive NFKD + combining-mark removal
SURVIVORS = {
    "œ": "oe", "Œ": "OE",   # oe ligature
    "æ": "ae", "Æ": "AE",   # ae ligature
    "ß": "ss",              # sharp s
    "ø": "o", "Ø": "O",     # o stroke
    "đ": "d", "Đ": "D",     # d stroke
    "ł": "l", "Ł": "L",     # l stroke
    "ħ": "h", "ð": "d", "Ð": "D", "þ": "th", "Þ": "Th",
    "ı": "i", "ŋ": "n", "Ŋ": "N",
}

n = 0
affected = 0
rows_with = Counter()
examples = []

def surviving(s):
    return {c for c in s if c in SURVIVORS}

with open(PATH, encoding="utf-8", errors="replace", newline="") as fh:
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    next(rd)
    for rec in rd:
        if len(rec) < 4 or rec[3].strip() != "France":
            continue
        n += 1
        name, addr = rec[1], rec[2]
        hit = surviving(name) | surviving(addr)
        if hit:
            affected += 1
            for c in hit:
                rows_with[c] += 1
            if len(examples) < 20:
                examples.append((name[:44], addr[:52], "".join(sorted(hit))))
        if n >= 250000:
            break

print(f"France rows scanned            : {n:,}")
print(f"rows with a surviving ligature : {affected:,} ({affected/max(n,1):.3%})\n")
print("by character:")
for c, k in rows_with.most_common():
    print(f"  {c!r} U+{ord(c):04X} -> should fold to {SURVIVORS[c]!r}   rows={k:,}")

print("\nexamples (name, address, offending chars):")
for nm, ad, ch in examples:
    print(f"  {nm:44s} | {ad:52s} | {ch!r}")

print("\n--- collision demo: what _non_alnum does to the survivors ---")
non_alnum = re.compile(r"[^a-z0-9]+")
for w in ["Œuvre", "Cœur", "Fœur", "Sœur", "Auberge", "Manœuvre", "Ex æquo",
          "Straßburger", "Ødegård", "Łódź", "Þórshöfn"]:
    s = "".join(c for c in unicodedata.normalize("NFKD", w)
                if not unicodedata.combining(c))
    toks = [t for t in non_alnum.split(s.lower()) if t]
    print(f"  {w:16s} -> strip_accents {s:16s} -> tokens {toks}")
