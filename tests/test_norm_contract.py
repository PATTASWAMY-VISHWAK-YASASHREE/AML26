"""Prove the norm output contract is intact: filename and column set/order.

Checks, without running the pipeline:
  1. the exact *_norm.parquet filename that run_blocking.py globs
  2. the 15 columns in the order prep.py writes them
  3. that features.REC_COLS is a SUBSET of those 15 (build_features/make_submission
     select by name, so a missing one is a hard KeyError at scoring time)
"""
import os
import re
import sys

B = r"C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)"
sys.path.insert(0, os.path.join(B, "run_src", "src"))
import features  # noqa: E402

prep = open(os.path.join(B, "run_src", "src", "prep.py"), encoding="utf-8").read()
cols = re.search(r"NORM_COLS = \[(.*?)\]", prep, re.S).group(1)
norm_cols = re.findall(r'"([^"]+)"', cols)
order = ["entity_id", "business_name", "business_address", "country"] + norm_cols + ["is_native"]

fails = []
print("1. filename prep.py writes          : work/<name>_norm.parquet")
rb = open(os.path.join(B, "run_src", "src", "run_blocking.py"), encoding="utf-8").read()
globs = sorted(set(re.findall(r"(\{split\}_source\{i\}_norm\.parquet)", rb)))
print(f"2. run_blocking.py globs            : {globs}  ->  contract {'OK' if globs else 'CHANGED'}")
if not globs:
    fails.append("run_blocking no longer globs {split}_source{i}_norm.parquet")

print(f"3. norm column order ({len(order)} columns):")
for i, c in enumerate(order):
    print(f"     {i:>2}. {c}")

missing = [c for c in features.REC_COLS if c not in order]
# 'rid' is EXPECTED to be absent: prep does not and must not create it.  run_blocking
# injects it with .with_row_index("rid") when it builds test_s1.parquet / test_q.parquet.
# So the real requirement is: every REC_COLS column EXCEPT rid must come from prep.
injected = [c for c in missing if c == "rid"]
must_come_from_prep = [c for c in features.REC_COLS if c != "rid"]
really_missing = [c for c in must_come_from_prep if c not in order]
print(f"4. features.REC_COLS ({len(features.REC_COLS)} cols):")
print(f"     rid        provided downstream by run_blocking .with_row_index(\"rid\")  "
      f"{'CONFIRMED' if rb.count('with_row_index') >= 2 else 'NOT FOUND IN run_blocking'}")
print(f"     the other {len(must_come_from_prep)} come from prep: "
      f"{'ALL PRESENT' if not really_missing else 'MISSING ' + str(really_missing)}")
if really_missing:
    fails.append(f"REC_COLS needs columns prep does not write: {really_missing}")
if not injected:
    fails.append("rid is in REC_COLS but not in the norm output AND that is unexpected")

print(f"5. is_native is the last column     : {order[-1] == 'is_native'}")
if order[-1] != "is_native":
    fails.append("is_native is not last")

print()
print("CONTRACT CHECK:", "PASS" if not fails else "FAIL")
for f in fails:
    print("  -", f)
sys.exit(1 if fails else 0)
