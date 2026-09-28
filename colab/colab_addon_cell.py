"""
Colab ADD-ON cell: honest resource report, 12 GB sizing, typed decisions, sweep.

PASTE THIS AFTER the main pipeline cell finishes. It does not re-run the
pipeline - it reads artefacts the pipeline already wrote.

=============================================================================
ABOUT THE T4 GPU - READ BEFORE ASSUMING IT HELPS
=============================================================================
This pipeline has NO GPU code path. A T4 will sit at ~0% for the whole run.
That is not a misconfiguration; it is what the workload is:

  * Candidate generation and the feature build run inside DuckDB, which is
    CPU-only. There is no CUDA backend for it.
  * The scorer is sklearn's LogisticRegression - CPU, fitted on a ~2% sample
    (~800k rows). A T4 has far more compute than that needs.
  * String similarity is rapidfuzz, a tuned C++ library. A GPU string kernel is
    very unlikely to beat it here, and the host<->device transfer alone can
    cost more than the compute it saves.

THE ACTUAL BOTTLENECK is memory bandwidth and disk spill during candidate
generation, not arithmetic. That is why the original run died with "could not
allocate block of size 256.0 KiB (5.5 GiB/5.5 GiB)". A GPU does not fix an
out-of-memory condition - the per-channel COPY fix in er_pipeline.py did.

So this cell REPORTS the GPU honestly instead of pretending to use it. Real GPU
acceleration means rewriting candidate generation (cuDF) and the scorer
(XGBoost device="cuda" / cuML) - a different project with different OOM
behaviour, not a flag to flip.

For this workload a HIGH-RAM CPU runtime is worth far more than the T4. The cell
tells you which runtime you actually have.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def report_resources() -> dict:
    """Report what the runtime actually is, rather than assuming."""
    info = {}
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=30)
        info["gpu_present"] = out.returncode == 0 and bool(out.stdout.strip())
        info["gpu_raw"] = (out.stdout or out.stderr).strip()
    except Exception as exc:
        info["gpu_present"] = False
        info["gpu_raw"] = f"nvidia-smi unavailable: {type(exc).__name__}"
    if info.get("gpu_present"):
        info["gpu_note"] = ("GPU PRESENT but unused by this pipeline: DuckDB is "
                            "CPU-only, scorer is sklearn. A HIGH-RAM runtime "
                            "would help this workload more than the T4.")

    try:
        kb = {}
        with open("/proc/meminfo") as f:
            for ln in f:
                if ":" in ln:
                    kb[ln.split(":")[0]] = int(ln.split()[1])
        total = kb.get("MemTotal", 0) / 1024 ** 2
        info["ram_total_gb"] = round(total, 2)
        info["ram_available_gb"] = round(kb.get("MemAvailable", 0) / 1024 ** 2, 2)
        info["ram_class"] = ("HIGH-RAM" if total > 20 else
                             "STANDARD ~12GB" if total > 10 else "SMALL")
    except Exception as exc:
        info["ram_error"] = f"{type(exc).__name__}: {exc}"

    for p in ("/content", "/content/drive"):
        try:
            st = os.statvfs(p)
            info[f"disk_free_gb::{p}"] = round(st.f_bavail * st.f_frsize / 1024 ** 3, 2)
        except Exception:
            pass
    return info


RES = report_resources()
print("=" * 72)
print("RESOURCE REPORT")
print("=" * 72)
for k, v in RES.items():
    print(f"  {k:<28} {v}")
print()
if RES.get("ram_class", "").startswith("STANDARD"):
    print("  12 GB runtime detected. If candidate generation OOMs, edit")
    print("  er_pipeline.py CFG in THIS order:")
    print("     max_candidates   10   -> 5     (biggest lever, small recall cost)")
    print("     max_token_df     5000 -> 2000  (shrinks the rare-token table)")
    print("     memory_limit     6GB  -> 4GB   (headroom for Python + OS)")
    print("  Leave `threads` alone - that tracks vCPU count, not RAM.")
    print("  Then delete WORK_DIR/duck.db so the cache fingerprint changes.")
    print()
print("  T4 note: it is not the bottleneck. Using it means rewriting cuDF +")
print("  XGBoost(cuda) - a rewrite, not a switch.")
print()


def find_workdir():
    for base in (os.environ.get("ER_WORK_DIR"), "/content/drive/MyDrive/er_run",
                 "/content/er_run"):
        if base and Path(base).exists():
            return Path(base)
    return None


WORK = find_workdir()
print(f"work dir: {WORK}")
if WORK is None:
    print("ERROR: no pipeline output found - run the main cell first.", flush=True)
    raise SystemExit(1)

# =============================================================================
#  EXPORT THE SCORE, SO THE DECISION POLICY BECOMES RE-TUNABLE
# =============================================================================
# WHAT THIS CELL EXPORTS, AND A NAMING CORRECTION
# `p1`/`p2` are the UPSTREAM two-stage names (select_T.py's blocking threshold T,
# then crossfit.py's match score). er_pipeline.py is a SINGLE-stage scorer: one
# LogisticRegression, one score, one threshold. There is no p1 in it. So the
# export below is `s1, tid, p2, country` where p2 == the pipeline's single score.
# Naming it p2 keeps it joinable with the upstream tables, but do not read it as
# a second-stage probability - it is the only score there is.
#
# WHY THIS MATTERS: er_pipeline thresholds this score and then DISCARDS it. A
# false merge does not merely dilute the score - metrics.py scores 0.0 for the
# whole S1 entity. So the threshold is the highest-leverage knob in the system,
# and it is currently unreviewable after the fact. This export is what makes it
# reviewable.
import json  # noqa: E402
import duckdb  # noqa: E402

NORM = Path(WORK) / "norm"
model_path = NORM / "model.json"
if not model_path.exists():
    print(f"ERROR: {model_path} missing.")
    print("Re-run cell5 so the pipeline writes model.json, then re-run this cell.")
    raise SystemExit(1)

MODEL = json.loads(model_path.read_text(encoding="utf-8"))
COEF, INTERCEPT = MODEL["coef"], MODEL["intercept"]
BASE_T = MODEL["threshold"]
print(f"model: {len(COEF)} features, intercept={INTERCEPT:.4f}, threshold={BASE_T:.4f}")


def sigmoid_sql(expr: str) -> str:
    """DuckDB has no sigmoid, so clamp before exp() to avoid overflow."""
    return f"(1.0 / (1.0 + exp(-greatest(-60.0, least(60.0, {expr})))) )"


SCORE_SQL = sigmoid_sql(" + ".join(
    f"({w:.10f}) * coalesce({c}, 0)" for w, c in zip(COEF, MODEL["features"])))

con = duckdb.connect(str(WORK / "duck.db"), read_only=True)
s2 = con.execute(
    "SELECT column_name FROM (DESCRIBE "
    f"SELECT * FROM read_parquet({str(NORM / 'test_s2.parquet')!r}))").fetchall()
s2_cols = [r[0] for r in s2]
country_expr = ("country" if "country" in s2_cols
                else "'US' AS country")
print(f"test_s2 columns: {s2_cols}")

# One row per (S1, candidate) with its score. Out-of-core: DuckDB streams this,
# Python never holds the full candidate set.
con.execute(f"""
    CREATE OR REPLACE TABLE scored AS
    SELECT f.sid AS s1, f.tid AS tid, {SCORE_SQL} AS p2, {country_expr} AS country
    FROM read_parquet({str(NORM / 'test_feat.parquet')!r}) f
    JOIN read_parquet({str(NORM / 'test_s2.parquet')!r}) t
      ON f.tid = t.entity_id
""")
n = con.execute("SELECT count(*) FROM scored").fetchone()[0]
print(f"scored candidate pairs: {n:,}")

# Per-S1 best candidate, with the runner-up's score kept so the policy layer can
# ask a MARGIN question ("how much better is the best than the 2nd?") and not
# only an absolute-threshold question.
con.execute(f"""
    CREATE OR REPLACE TABLE best_per_s1 AS
    SELECT s1, tid, p2, country FROM (
        SELECT *, row_number() OVER (PARTITION BY s1 ORDER BY p2 DESC, tid) AS rk
        FROM scored
    ) WHERE rk = 1
""")
con.execute("""
    CREATE OR REPLACE TABLE margin AS
    SELECT s1, tid AS best_tid, p2 AS best_p2, second_p2,
           best_p2 - second_p2 AS gap
    FROM (
        SELECT s1, tid, p2,
               lead(p2) OVER (PARTITION BY s1 ORDER BY p2 DESC, tid) AS second_p2,
               row_number() OVER (PARTITION BY s1 ORDER BY p2 DESC, tid) AS rk
        FROM scored
    ) WHERE rk = 1
""")

export = WORK / "policy_scores.parquet"
con.execute(f"COPY margin TO {str(export)!r} (FORMAT PARQUET)")
n_s1 = con.execute("SELECT count(*) FROM margin").fetchone()[0]
print(f"exported: {export}  ({n_s1:,} S1 entities)")

# DuckDB has NO width_bucket() - it raises CatalogException. Verified in
# test_addon_sql.py. An explicit CASE works on every DuckDB build.
bucket_sql = """CASE
        WHEN best_p2 < 0.1 THEN 1 WHEN best_p2 < 0.2 THEN 2
        WHEN best_p2 < 0.3 THEN 3 WHEN best_p2 < 0.4 THEN 4
        WHEN best_p2 < 0.5 THEN 5 WHEN best_p2 < 0.6 THEN 6
        WHEN best_p2 < 0.7 THEN 7 WHEN best_p2 < 0.8 THEN 8
        WHEN best_p2 < 0.9 THEN 9 ELSE 10 END"""
print("\nscore distribution of the per-S1 best candidate:")
rows = con.execute(f"""
    SELECT {bucket_sql} AS bucket, count(*) AS n,
           round(avg(best_p2), 4) AS mean_best_p2
    FROM margin GROUP BY bucket ORDER BY bucket
""").fetchall()
print(f"  {'bucket':<8}{'n':>12}{'mean_best_p2':>14}")
for b, n, m in rows:
    print(f"  {f'[{b}/10]':<8}{n:>12,}{m:>14}")

n_match = con.execute("SELECT count(*) FROM margin WHERE best_p2 >= ?",
                      [BASE_T]).fetchone()[0]
print(f"\nbaseline threshold from the pipeline : {BASE_T:.4f}")
print(f"would MATCH at baseline             : {n_match:,} of {n_s1:,} "
      f"({100.0 * n_match / max(n_s1, 1):.1f}%)")
print("  NOTE: that is a MATCH RATE, not a score. The real F0.5 needs the")
print("  held-out tune split; see cell7. Do not tune on France test labels.")

# =============================================================================
#  EXPORT THE HELD-OUT TUNE SPLIT, THEN SWEEP WITH THE VALIDATED TOOL
# =============================================================================
# WHY NOT REIMPLEMENT F0.5 IN SQL HERE
# metrics.py has specific per-entity semantics (abstaining on a gold-empty
# entity scores 1.0; a false merge on that entity scores 0.0, and the score is
# macro-averaged per Source-1 entity). Re-deriving that in SQL here would be a
# second, unverified implementation that could silently disagree with the
# scorer. So this cell only EXTRACTS the held-out rows, and sweep_threshold.py
# - already cross-checked against er_pipeline.py - does the scoring.
#
# WHY THE TUNE SPLIT AND NOT TEST
# The test set's France labels do not exist, and tuning against test is how you
# manufacture a leaderboard number that does not generalise. er_pipeline already
# emits `is_tune = hash(sid) % 2` on TRAIN, so a held-out split is free.
con = duckdb.connect(str(WORK / "duck.db"), read_only=True)
train_feat = NORM / "train_feat.parquet"

n_tune = con.execute(
    f"SELECT count(*) FROM read_parquet({str(train_feat)!r}) WHERE is_tune = 1"
).fetchone()[0]
if n_tune == 0:
    print("ERROR: no is_tune=1 rows - cannot tune honestly. Stopping.")
    con.close()
    raise SystemExit(1)
print(f"held-out tune rows: {n_tune:,}")

# Best is NOT pre-selected here: sweep_threshold.py scores whole candidate SETS
# per entity (metrics.py macro-averages over the predicted set), so it needs every
# pair, not just the argmax. Capped at MAX_PAIRS with a deterministic hash filter,
# because loading the full held-out set into numpy is the same RAM mistake that
# OOM-killed the local run.
MAX_PAIRS = 400_000

# The feature parquet carries sid/tid/features/label/is_tune but NOT country, so
# country has to be joined on. Inspect rather than assume, or the COPY fails.
tf_cols = {r[0] for r in con.execute(
    f"DESCRIBE SELECT * FROM read_parquet({str(train_feat)!r})").fetchall()}
print(f"train_feat columns: {sorted(tf_cols)}")

if "country" in tf_cols:
    ctry_expr = "f.country"
else:
    src2 = NORM / "train_s2.parquet"
    s2c = {r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_parquet({str(src2)!r})").fetchall()}
    # t2 is deduplicated so t2.country needs no aggregate. Using any_value()
    # would silently turn the whole statement into an aggregate query and
    # DuckDB would then demand a GROUP BY over f.sid - a crash discovered on
    # Colab AFTER the pipeline has already run. test_addon_sql.py proves the
    # correct form.
    ctry_expr = "t2.country"
    ctry_src = (f"FROM read_parquet({str(train_feat)!r}) f "
                f"LEFT JOIN (SELECT DISTINCT entity_id, country "
                f"FROM read_parquet({str(src2)!r})) t2 ON f.tid = t2.entity_id")
print(f"country expression: {ctry_expr}")

tune_out = WORK / "tune_scores.parquet"
con.execute(f"""
    COPY (
      SELECT f.sid AS s1, f.tid AS tid, f.label AS label,
             {ctry_expr} AS country,
             {SCORE_SQL} AS p2
      {ctry_src}
      WHERE f.is_tune = 1
        AND hash(f.sid) % 1000 < 250      -- ~25% of held-out S1s
    ) TO {str(tune_out)!r} (FORMAT PARQUET)
""")

# Fetch in chunks so we never materialise the whole table in one result set.
sids, tids, labels, scores, countries = [], [], [], [], []
CHUNK = 50_000
while sum(len(x) for x in (sids,)) < MAX_PAIRS:
    off = len(sids)
    rows = con.execute(f"""
        SELECT s1, tid, label, p2, country
        FROM read_parquet({str(tune_out)!r})
        LIMIT {CHUNK} OFFSET {off}
    """).fetchall()
    if not rows:
        break
    for s1, tid, lab, p2, ctry in rows:
        sids.append(s1); tids.append(tid); labels.append(int(lab))
        scores.append(float(p2)); countries.append(ctry or "?")
    if len(sids) % (CHUNK * 4) == 0:
        print(f"  ...{len(sids):,} pairs")

if not sids:
    print("ERROR: held-out export is empty. Stopping rather than reporting a fake sweep.")
    con.close()
    raise SystemExit(1)

import numpy as np  # noqa: E402
npz_path = WORK / "tune_scores.npz"
np.savez_compressed(
    npz_path,
    sids=np.array(sids, dtype=object),
    tids=np.array(tids, dtype=object),
    labels=np.array(labels, dtype=np.int8),
    scores=np.array(scores, dtype=np.float64),
    countries=np.array(countries, dtype=object),
)
n_ent = len(set(sids))
print(f"exported held-out pairs : {len(sids):,}  ({n_ent:,} S1 entities)")
print(f"npz                     : {npz_path} "
      f"({npz_path.stat().st_size / 2**20:.1f} MB)")
if len(sids) >= MAX_PAIRS:
    print(f"  NOTE: hit the {MAX_PAIRS:,} pair cap, so this sweep is over a")
    print("  subsample. Fine for picking a threshold; raise the cap on a")
    print("  HIGH-RAM runtime before trusting the final F0.5 to 4 decimals.")
con.close()

# -----------------------------------------------------------------------------
#  Score the sweep with the validated tool (selftest first)
# -----------------------------------------------------------------------------
import subprocess  # noqa: E402
import sys  # noqa: E402

HERE = Path.cwd()
for name in ("typed_decisions.py", "sweep_threshold.py"):
    if not (HERE / name).exists():
        print(f"\nERROR: {name} not found in {HERE}.")
        print("Upload it next to the notebook, or run its --selftest locally first.")
        raise SystemExit(1)

for name in ("typed_decisions.py", "sweep_threshold.py"):
    r = subprocess.run([sys.executable, name, "--selftest"],
                       capture_output=True, text=True)
    tail = ((r.stdout or "").strip().splitlines() or ["(no output)"])[-1]
    print(f"  {name:<22} selftest exit={r.returncode}  {tail}")
    if r.returncode != 0:
        print((r.stdout + r.stderr)[-2000:])
        raise SystemExit(1)

# --scores takes the NPZ of sids/tids/labels/scores(/countries). It derives the
# gold entity universe itself, so there is deliberately no --truth flag.
r = subprocess.run([sys.executable, "sweep_threshold.py",
                    "--scores", str(npz_path),
                    "--out", str(WORK / "threshold_sweep.json")],
                   capture_output=True, text=True)
print(r.stdout)
if r.returncode != 0:
    print("sweep failed:", (r.stdout + r.stderr)[-3000:])
raise SystemExit(r.returncode)

con.close()

