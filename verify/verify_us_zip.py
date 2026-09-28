"""Verify the 'US addresses have no ZIP' finding against raw rows.

deep_profile reports addr_no_postal = 88.9% for US train S1, meaning almost no
US address contains a standalone 5-digit code -- even though the first few rows
of the file look like "..., High Point, NC" with no ZIP. If that is right, the
`postcode` blocking key is nearly useless for US, which changes which keys the
pipeline should lean on. This counts the shape of the trailing address
component directly, on a sample, with no reference to the profile.
"""
import csv
import os
import re
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "amazon_ml_2026_research", "student_resource",
                 "dataset", "train", "train_source1.tsv")
LIMIT = 300_000

DIG = re.compile(r"\d")
D5 = re.compile(r"(?<!\d)\d{5}(?!\d)")
D9 = re.compile(r"(?<!\d)\d{5}(?:\s*-\s*\d{4})?(?!\d)")

tail_kind = Counter()
has5 = 0
has9 = 0
n = 0
examples = {"zip5": [], "zip9": [], "no_zip": []}

with open(P, "r", encoding="utf-8", errors="replace", newline="") as fh:
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    next(rd, None)
    for rec in rd:
        if len(rec) < 4:
            continue
        if rec[3].strip() != "US":
            continue
        n += 1
        if n > LIMIT:
            break
        a = rec[2].strip()
        if not a:
            tail_kind["<empty>"] += 1
            continue
        comps = [c.strip() for c in re.split(r"[,;]", a) if c.strip()]
        tail = comps[-1] if comps else ""
        if D9.search(tail):
            tail_kind["zip9"] += 1
            has9 += 1
            if len(examples["zip9"]) < 5:
                examples["zip9"].append(tail)
        elif D5.search(tail):
            tail_kind["zip5"] += 1
            has5 += 1
            if len(examples["zip5"]) < 5:
                examples["zip5"].append(tail)
        elif DIG.search(tail):
            tail_kind["digits_other"] += 1
        elif len(tail) == 2 and tail.isalpha():
            tail_kind["2-letter (state?)"] += 1
        else:
            tail_kind["other_text"] += 1
            if len(examples["no_zip"]) < 8:
                examples["no_zip"].append(tail)

print(f"US rows sampled        : {n:,}")
print(f"tail has ZIP5          : {has5:,}  ({100 * has5 / n:.2f}%)")
print(f"tail has ZIP9          : {has9:,}  ({100 * has9 / n:.2f}%)")
print(f"tail has NO postal     : {n - has5 - has9:,}  "
      f"({100 * (n - has5 - has9) / n:.2f}%)")
print("\ntail component shape:")
for k, v in tail_kind.most_common():
    print(f"   {k:22s} {v:>9,}  ({100 * v / n:.2f}%)")
print("\nZIP9 tail examples   :", examples["zip9"])
print("ZIP5 tail examples   :", examples["zip5"])
print("no-ZIP tail examples :", examples["no_zip"])
