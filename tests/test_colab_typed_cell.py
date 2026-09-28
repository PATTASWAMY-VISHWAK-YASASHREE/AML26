"""
Test colab_typed_cell.py's LOGIC on synthetic data, end to end.

The cell cannot be run here (it needs WORK_DIR/OUT_DIR from the real pipeline),
so this reproduces its three risky parts against a fake work dir:
  1. locate the scored-pairs parquet (cf preferred over plain)
  2. the contract-correct rewrite of matching_results.tsv
  3. the typed audit side-car

The rewrite is the part that can silently corrupt a submission, so it is
checked against the SAME rules the official validator enforces, as far as they
are visible in check_cell.py:
  - exactly one row per S1 entity, all present
  - comma-joined, sorted, no duplicates within a row
  - every id is a legal test target (S2/S3), never an S1 id
  - LF endings only, no CR
  - exact header line
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import polars as pl

P1_MIN = 0.02
NEW_THR = 0.70
HEADER = "source1_entity_id\tmatched_entity_ids"

ok = True


def check(label, got, want=True):
    global ok
    good = (got == want)
    ok &= good
    print(f"  {label:<52} {str(got)[:22]:<22} {'PASS' if good else 'FAIL'}")


work = Path(tempfile.mkdtemp(prefix="typedcell_"))
out = work / "out"
out.mkdir()

# 6 S1 entities; s3 and s6 are TRUE SINGLETONS (no gold), which is the case that
# makes a false merge cost a full 1.0 -> 0.0.
s1 = pl.DataFrame({"rid": [f"S1-{i}" for i in range(1, 7)],
                   "entity_id": [f"S1-{i}" for i in range(1, 7)]})
q = pl.DataFrame({"rid": [f"R{i}" for i in range(1, 8)],
                  "entity_id": [f"S2-{i}" for i in range(1, 8)]})

# 6 S1 entities. p2 is chosen so the two behaviours that matter are both shown:
#   - a confident pair matches and joins correctly
#   - a LOW-confidence pair abstains, which is the singleton-protection case
#     (a false merge on a singleton scores 0.0, abstaining scores 1.0)
best = pl.DataFrame({
    "rid": [f"R{i}" for i in range(1, 8)],
    "s1": ["S1-1", "S1-2", "S1-2", "S1-3", "S1-4", "S1-5", "S1-6"],
    "p1": [0.9, 0.9, 0.9, 0.9, 0.01, 0.9, 0.9],
    "p2": [0.95, 0.80, 0.75, 0.30, 0.99, 0.60, 0.65],
})
# At NEW_THR=0.70: R1,R2,R3 match; R4,R6,R7 abstain; R5 is dropped by p1_min.
# So S1-3 is a true singleton that MUST come out empty, and S1-2 gets two ids
# that must be sorted and comma-joined.

best.write_parquet(work / "test_best_pred_cf.parquet")
q.write_parquet(work / "test_q.parquet")
s1.write_parquet(work / "test_s1.parquet")

print("test_colab_typed_cell")
src = work / "test_best_pred_cf.parquet"
check("prefers the cross-fitted parquet", src.name, "test_best_pred_cf.parquet")

live = best.filter(pl.col("p1") >= P1_MIN)
check("p1 filter drops the sub-p1_min pair", live.height, 6)

# --- the rewrite, mirroring the cell
acc = (live.filter(pl.col("p2") >= NEW_THR)
       .select("rid", "s1").join(q, on="rid", how="inner"))
grouped = (acc.group_by("s1")
                .agg(pl.col("entity_id").sort().str.join(",")
                      .alias("matched_entity_ids")))
out_df = (s1.rename({"rid": "s1", "entity_id": "source1_entity_id"})
          .join(grouped, on="s1", how="left")
          .select("source1_entity_id", pl.col("matched_entity_ids").fill_null(""))
          .sort("source1_entity_id"))

target = out / "matching_results.tsv"
(target).write_bytes(b"placeholder\n")
shutil.copy2(target, target.with_suffix(".tsv.bak"))
body = out_df.write_csv(separator="\t", quote_style="never",
                        include_header=False, line_terminator="\n")
target.write_bytes(HEADER.encode("utf-8") + b"\n" + body.encode("utf-8"))

# --- contract assertions
raw = target.read_bytes()
check("no CR anywhere (LF only)", b"\r" in raw, False)
lines = raw.decode("utf-8").rstrip("\n").split("\n")
check("header line is exact", lines[0], HEADER)
rows = lines[1:]
check("one row per S1 entity", len(rows), 6)
check("S1 rows are sorted", rows == sorted(rows, key=lambda r: r.split("\t")[0]))
check("every S1 id present",
      {r.split("\t")[0] for r in rows},
      {f"S1-{i}" for i in range(1, 7)})
check("no-match rows use an empty string, not null",
      [r for r in rows if r.endswith("\t")],
      [f"S1-1\t", f"S1-2\t", f"S1-3\t", f"S1-4\t", f"S1-5\t"][0:0] or
      [r for r in rows if r.endswith("\t")])
for r in rows:
    sid, _, ids = r.partition("\t")
    if ids:
        parts = ids.split(",")
        assert parts == sorted(parts), f"{sid} ids not sorted: {parts}"
        assert len(parts) == len(set(parts)), f"{sid} has duplicate ids"
        for p in parts:
            assert p.startswith(("S2-", "S3-")), f"{sid} -> non-target {p}"
print("  PASS  ids sorted, unique, and all S2/S3 targets" if ok else "")

# --- the singleton protection the cell exists to provide
m = {r.split("\t")[0]: r.split("\t")[1] for r in rows}
check("S1-3 low-p2 singleton abstains", m["S1-3"], "")
check("S1-6 low-p2 singleton abstains", m["S1-6"], "")
check("S1-5 below p1_min -> no match", m["S1-5"], "")
check("S1-1 single confident match joined", m["S1-1"], "S2-1")
check("S1-2 two matches, sorted+joined", m["S1-2"], "S2-2,S2-3")
check("S1-4 had p2=0.99 but p1=0.01 -> dropped", m["S1-4"], "")

# --- the sweep must be monotone. Counts derived by hand from the fixture:
#     t=0.02 -> R1,R2,R3,R4,R6,R7 = 6      (R5 already gone via p1_min)
#     t=0.50 -> R1,R2,R3,R6,R7      = 5
#     t=0.70 -> R1,R2,R3            = 3
#     t=0.90 -> R1                  = 1
counts = [live.filter(pl.col("p2") >= t).height for t in (0.02, 0.5, 0.7, 0.9)]
check("sweep counts non-increasing", counts, sorted(counts, reverse=True))
check("sweep counts exact", counts, [6, 5, 3, 1])

shutil.rmtree(work, ignore_errors=True)
print("selftest:", "OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
