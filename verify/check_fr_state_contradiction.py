"""Adjudicate the D073 vs D077 France state-resolution contradiction.

Both reports measured the same population (France test rows) and disagree by an
order of magnitude. This recomputes the shared denominator straight from the
compact profile so the disagreement is characterised, not just restated.

READ-ONLY on the profile. No raw TSV is opened.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PROF = os.path.join(ROOT, "analysis_out", "profile")

tot = 0
per = {}
for name in ("test_s1", "test_s2", "test_s3"):
    with open(os.path.join(PROF, f"{name}.json"), encoding="utf-8") as f:
        p = json.load(f)
    n = p["by_country"]["France"]["rows"]
    per[name] = n
    tot += n

print("France test rows, from by_country[France].rows:")
for k, v in per.items():
    print(f"  {k}: {v:,}")
print(f"  TOTAL: {tot:,}")

s1 = per["test_s1"]
print(f"\ntest_s1 share      : {s1}/{tot} = {100 * s1 / tot:.2f}%")
print("Both D073 and D077 use this same denominator, so the")
print("disagreement is NOT about which rows count.\n")

# The 100% claim: 101,521 + 85,197 + 72,734
legacy = 101_521 + 85_197 + 72_734
print(f"REFUTED 100% claim arithmetic: 101,521 + 85,197 + 72,734 = {legacy:,}")
print(f"  equals test_s1 row count ({s1:,})?  {legacy == s1}")
print("  -> the three 'modern region' totals sum to exactly source-1,")
print("     which is the tell that the 100% was a single-source artefact.\n")

# D073 sidecar internal consistency
print("D073 sidecar (.json) decomposition:")
parts = [457_385, 487_902, 259_452]
print(f"  457,385 + 487,902 + 259,452 = {sum(parts):,}")
print(f"  claimed resolvable 1,204,739  -> consistent: {sum(parts) == 1_204_739}")
print(f"  {tot:,} - 1,204,739 = {tot - 1_204_739:,}  (claimed 489,706)")
print(f"  489,706 / {tot:,} = {100 * 489_706 / tot:.2f}%  (claimed 28.90%)\n")

print("D073 report (.md) decomposition:")
print("  claims 1,213,296 resolvable / 481,149 unresolvable")
print(f"  1,213,296 + 481,149 = {1_213_296 + 481_149:,}  vs total {tot:,}"
      f"  -> consistent: {1_213_296 + 481_149 == tot}")
print("  so the .md is internally consistent TOO, but disagrees with its own")
print("  .json sidecar by 8,557 rows. Two different numbers, both summing")
print("  correctly => they were computed by different means, not mis-added.\n")

print("D077 (quarantined) claims 43,411 unresolvable = "
      f"{100 * 43_411 / tot:.4f}%")
print("\nCONCLUSION: the denominator is agreed; the tests are not comparable.")
print("Do not quote any single percentage until one criterion is fixed.")
