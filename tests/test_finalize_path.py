"""End-to-end test of the FINALIZE path of the edited make_submission.py.

FINALIZE is the only code this task adds that actually produces the deliverable
(the two submission TSVs), and it cannot be exercised on the real data without
first running the whole pipeline.  This builds a tiny synthetic work dir with the
exact columns make_submission's write path reads, runs FINALIZE=1 for real, and
checks the two TSVs come out with the right headers, row counts and non-empty
ids.  It also checks the COUNTRIES/FINALIZE mutual-exclusion guard.

usage: python test_finalize_path.py <base_dir>
"""
import os, shutil, subprocess, sys, glob

B = sys.argv[1]
SRC = os.path.join(B, "run_src", "src")
PY = sys.executable
T = os.path.join(os.environ["TEMP"], "_finalize_test")
shutil.rmtree(T, ignore_errors=True)
os.makedirs(T)
W = os.path.join(T, "work")
O = os.path.join(T, "out")
os.makedirs(W)
os.makedirs(O)

import polars as pl

# 3 Source-1 entities per country, 2 queries each.  rid is global across s2+s3,
# exactly as run_blocking builds it.
s1_rows, q_rows, best_rows = [], [], []
rid = 0
for country, s1_ids, q_ids in (("India", ["S1I1", "S1I2", "S1I3"], ["S2I1", "S3I1"]),
                               ("US", ["S1U1", "S1U2"], ["S2U1", "S3U1"])):
    for k, e in enumerate(s1_ids):
        s1_rows.append({"rid": rid, "country": country, "ncore": f"name {k}",
                        "atoks": "", "entity_id": e})
        # two queries pointing at this S1: a confident one and a weak one
        for j, (p1, p2) in enumerate(((0.9, 0.95), (0.05, 0.01))):
            qid_ = f"{q_ids[0]}_{k}_{j}" if j else q_ids[0]
            q_rows.append({"rid": rid + 1, "country": country, "entity_id": qid_,
                           "ncore": f"name {k}", "atoks": "", "anums": ""})
            best_rows.append({"rid": rid + 1, "s1": rid, "p1": p1, "p2": p2})
        rid += 1

pl.DataFrame(s1_rows).write_parquet(os.path.join(W, "test_s1.parquet"))
pl.DataFrame(q_rows).write_parquet(os.path.join(W, "test_q.parquet"))
by_c = {}
for r in best_rows:
    c = "India" if r["s1"] < 3 else "US"
    by_c.setdefault(c, []).append(r)
for c, rows in by_c.items():
    pl.DataFrame(rows).write_parquet(os.path.join(W, f"best_{c}.parquet"))

# the 5 shipped models, so CF=True and the meta files load
for m in ("model_stage1_cf.json", "model_stage1_f0.txt", "model_stage1_f1.txt",
          "model_stage2_cf.json", "model_stage2_cf.txt"):
    shutil.copy2(os.path.join(B, "_upstream", "models", m), os.path.join(W, m))

fails = []


def run(env_extra, label):
    env = dict(os.environ, **env_extra)
    r = subprocess.run([PY, os.path.join(SRC, "make_submission.py"), W, O],
                       capture_output=True, text=True, env=env)
    return r


print("--- 1. FINALIZE=1 produces both TSVs ---")
r = run({"FINALIZE": "1", "COUNTRIES": ""}, "finalize")
print("   rc=%d" % r.returncode)
for line in r.stdout.strip().splitlines()[:6]:
    print("   |", line)
if r.returncode != 0:
    print("   STDERR:", r.stderr.strip()[-1500:])
if r.returncode != 0:
    fails.append("FINALIZE rc=%d: %s" % (r.returncode, r.stderr.strip()[-600:]))
else:
    for f, hdr in (("matching_results.tsv", "source1_entity_id\tmatched_entity_ids"),
                   ("candidate_pairs.tsv", "source1_entity_id\tcandidate_entity_ids")):
        p = os.path.join(O, f)
        if not os.path.isfile(p):
            fails.append(f"{f} not written")
            continue
        lines = open(p, encoding="utf-8").read().splitlines()
        ok_hdr = lines[0] == hdr
        ok_rows = len(lines) - 1 == 5           # 3 India + 2 US Source-1 entities
        ne = sum(1 for x in lines[1:] if x.split("\t")[1].strip())
        print(f"   {f:<22} header={ok_hdr} rows={len(lines)-1}/{ok_rows} non-empty={ne}/{len(lines)-1}")
        if not ok_hdr:
            fails.append(f"{f} header is {lines[0]!r}")
        if not ok_rows:
            fails.append(f"{f} has {len(lines)-1} data rows, expected 5")
        if ne != len(lines) - 1:
            fails.append(f"{f} only {ne}/{len(lines)-1} rows carry ids")

print("--- 2. FINALIZE is idempotent (re-run produces the same file) ---")
before = open(os.path.join(O, "matching_results.tsv"), encoding="utf-8").read()
r = run({"FINALIZE": "1", "COUNTRIES": ""}, "finalize2")
after = open(os.path.join(O, "matching_results.tsv"), encoding="utf-8").read()
print("   rc=%d  identical=%s" % (r.returncode, before == after))
if before != after:
    fails.append("FINALIZE is not idempotent")

print("--- 3. COUNTRIES + FINALIZE together is refused ---")
r = run({"FINALIZE": "1", "COUNTRIES": "India"}, "both")
refused = r.returncode != 0 and "not both" in (r.stdout + r.stderr)
print("   rc=%d  refused=%s" % (r.returncode, refused))
if not refused:
    fails.append("COUNTRIES+FINALIZE was not refused")

print("--- 4. unknown COUNTRIES is refused with a clear message ---")
r = run({"FINALIZE": "", "COUNTRIES": "Atlantis"}, "unknown")
ok = r.returncode != 0 and "unknown COUNTRIES" in (r.stdout + r.stderr)
print("   rc=%d  refused=%s" % (r.returncode, ok))
if not ok:
    fails.append("unknown COUNTRIES was not refused cleanly")

shutil.rmtree(T, ignore_errors=True)
print()
print("FINALIZE TEST:", "PASS" if not fails else "FAIL")
for f in fails:
    print("  -", f)
sys.exit(1 if fails else 0)
