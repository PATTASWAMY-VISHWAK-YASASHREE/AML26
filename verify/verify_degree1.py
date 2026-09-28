"""Independent string-level verification of the degree-1 ground-truth claim.

gt_graph.py measured the S2/S3 degree distribution using int64 id HASHES. A
hash collision would merge two distinct ids and could only ever INFLATE a
degree, never hide one -- so a max of 1 is safe. This script re-checks the same
claim on the raw STRINGS for a large sample, so the finding does not rest on
hashing at all.

Claim under test: no S2 or S3 entity_id appears in more than one
train_ground_truth.tsv row.
"""
import csv
import os
import random
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
GT = os.path.join(ROOT, "amazon_ml_2026_research", "student_resource",
                  "dataset", "train", "train_ground_truth.tsv")
SAMPLE = 400_000

rng = random.Random(23)
owner: dict = {}
dup_examples: list = []
n_rows = 0
n_ids = 0
with open(GT, "r", encoding="utf-8", errors="replace", newline="") as fh:
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    next(rd, None)
    for i, rec in enumerate(rd):
        if not rec:
            continue
        n_rows += 1
        # sample rows to keep memory bounded on a 0.36 GB box
        if n_rows > SAMPLE and rng.randint(0, n_rows) >= SAMPLE:
            continue
        s1 = rec[0].strip()
        vals = rec[1].split(",") if len(rec) > 1 and rec[1].strip() else []
        for v in vals:
            v = v.strip()
            if not v:
                continue
            n_ids += 1
            if v in owner and owner[v] != s1:
                dup_examples.append((v, owner[v], s1))
            else:
                owner[v] = s1

print(f"gt rows scanned      : {n_rows:,}")
print(f"gt rows kept (sample): {len(set(owner.values())):,}")
print(f"match ids seen       : {n_ids:,}")
print(f"distinct ids kept    : {len(owner):,}")
print(f"ids owned by >1 S1   : {len(dup_examples)}")
for e in dup_examples[:10]:
    print("   CONFLICT", e)
print("VERDICT:", "degree-1 holds on this sample"
      if not dup_examples else "DEGREE >1 EXISTS -- see conflicts above")
