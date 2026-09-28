"""Verify the F1 postal-code claim against RAW test data for France only.

The profile says France has dig5/row = 0.004, which would refute the report's
claim that French 5-digit codes are being discarded in bulk. Read only the France
lines of test_source1.tsv, streaming, to check.
"""
import csv
import re
import sys

PATH = (sys.argv[1] if len(sys.argv) > 1 else
        "amazon_ml_2026_research/student_resource/dataset/test/test_source1.tsv")
LIMIT = 400_000

DIG5 = re.compile(r"(?<!\d)\d{5}(?!\d)")
ANYNUM = re.compile(r"\d+")

n = 0
with_digit = 0
with_5 = 0
samples = []
per_country = {}

with open(PATH, encoding="utf-8", errors="replace", newline="") as fh:
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    hdr = next(rd)
    print("header:", hdr, flush=True)
    for rec in rd:
        if len(rec) < 4:
            continue
        c = rec[3].strip()
        if c != "France":
            continue
        n += 1
        addr = rec[2]
        if ANYNUM.search(addr):
            with_digit += 1
            if DIG5.search(addr):
                with_5 += 1
            if len(samples) < 25 and ANYNUM.search(addr):
                samples.append(addr[:110])
        pc = per_country.setdefault(c, {"n": 0, "digit": 0, "d5": 0})
        pc["n"] += 1
        if ANYNUM.search(addr):
            pc["digit"] += 1
        if DIG5.search(addr):
            pc["d5"] += 1
        if n >= LIMIT:
            break

print(f"\nFrance rows scanned: {n:,}")
if n:
    print(f"  with any digit : {with_digit:,} ({with_digit / n:.3%})")
    print(f"  with a 5-digit : {with_5:,} ({with_5 / n:.3%})")
print("\nsample France addresses containing digits:")
for s in samples:
    print("   ", s)
