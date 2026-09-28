"""Real test of the streaming prep rewrite, on test_source1 ONLY.

Safety: the output goes to a SCRATCH directory.  work_test/test_source1_norm.parquet
already exists and was produced by the OLD prep_file, so it is the oracle: if the
streaming output is .equals() to it, the rewrite is provably behaviour-preserving
(columns, order, dtypes and every cell), not merely "the right row count".
The real work_test tree is never written to, and source2/source3 are never touched.

usage: python test_prep_stream.py <base_dir> <work_dir>
"""
import os
import shutil
import subprocess
import sys

import polars as pl

B, WORK = sys.argv[1], sys.argv[2]
SRC = os.path.join(B, "run_src", "src")
PY = sys.executable
SCRATCH = os.path.join(os.environ["TEMP"], "_prep_stream_test")
shutil.rmtree(SCRATCH, ignore_errors=True)
os.makedirs(SCRATCH)

src = os.path.join(WORK, "data", "test_source1.parquet")
oracle = os.path.join(WORK, "test_source1_norm.parquet")
out = os.path.join(SCRATCH, "test_source1_norm.parquet")
for p in (src, oracle):
    if not os.path.isfile(p):
        print("MISSING:", p)
        sys.exit(2)

import pyarrow.parquet as _pq
want = _pq.ParquetFile(src).metadata.num_rows
print(f"input  rows={want}  {os.path.getsize(src)/2**20:.1f}MB")
print(f"oracle rows={_pq.ParquetFile(oracle).metadata.num_rows}  {os.path.getsize(oracle)/2**20:.1f}MB  (old prep_file)")

print("\n--- running the streaming prep on test_source1 only ---")
env = dict(os.environ, PREP_RESUME="0", PREP_NPROC="1", PREP_CHUNK="20000",
           PREP_ROWGROUP_ROWS=os.environ.get("TEST_RG", "200000"),
           PYTHONDONTWRITEBYTECODE="1")
r = subprocess.run([PY, os.path.join(SRC, "prep.py"), os.path.join(WORK, "data"), SCRATCH, "test_source1"],
                   capture_output=True, text=True, env=env)
print("rc =", r.returncode)
for line in r.stdout.strip().splitlines():
    print("   |", line)
if r.returncode != 0:
    print(r.stderr[-3000:])
    sys.exit(1)

fails = []
got_rows = _pq.ParquetFile(out).metadata.num_rows
got_mb = os.path.getsize(out) / 2 ** 20
orc_mb = os.path.getsize(oracle) / 2 ** 20
print(f"\noutput rows={got_rows}  {got_mb:.1f}MB   (old prep_file oracle: {orc_mb:.1f}MB)")
if got_rows != want:
    fails.append(f"row count {got_rows} != {want}")
if got_rows != 1732544:
    fails.append(f"row count {got_rows} != the required 1,732,544")
if got_mb > orc_mb * 1.10:
    fails.append(f"output {got_mb:.1f}MB is >10% bigger than the oracle {orc_mb:.1f}MB "
                 f"- the disk budget assumed the oracle size")
else:
    print(f"size vs oracle: {got_mb/orc_mb:.3f}x  (within the 10% the budget assumes)")

a, b = pl.read_parquet(oracle), pl.read_parquet(out)
print("oracle cols:", a.columns)
print("stream cols:", b.columns)
if a.columns != b.columns:
    fails.append("column order differs")
if a.schema != b.schema:
    fails.append("dtypes differ")
eq = a.equals(b)
print("VALUES IDENTICAL TO OLD prep_file OUTPUT:", eq)
if not eq:
    for c in a.columns:
        if not a[c].equals(b[c]):
            fails.append(f"column {c} differs")

shutil.rmtree(SCRATCH, ignore_errors=True)
print()
print("PREP STREAM TEST:", "PASS" if not fails else "FAIL")
for f in fails:
    print("  -", f)
sys.exit(1 if fails else 0)

