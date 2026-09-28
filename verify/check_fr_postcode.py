"""Refutes report finding F1 ("France loses postal codes").

Counts France rows in test_source1.tsv containing a standalone 5-digit number.
Result: 1,072 of 259,452 rows (0.413%). French addresses carry house numbers,
not postcodes, so the India-only `pin` guard has no French signal to lose.

Cited by FRANCE_FINDINGS.md (section: RETRACTED / F1).
"""
import csv
import re

PATH = ("amazon_ml_2026_research/student_resource/dataset/test/test_source1.tsv")
DIG5 = re.compile(r"(?<!\d)\d{5}(?!\d)")

n = c = 0
with open(PATH, encoding="utf-8", errors="replace", newline="") as fh:
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    next(rd)
    for rec in rd:
        if len(rec) >= 4 and rec[3].strip() == "France":
            n += 1
            if DIG5.search(rec[2]):
                c += 1

print(f"France rows {n:,}; with standalone 5-digit {c:,} ({c / max(n, 1):.3%})")
