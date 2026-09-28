# task_0003 — MEMORY / OOM AUDIT of `_upstream/run_all.sh`

Author: memory/perf engineer (task_0003). Workspace
`C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)`.
`_upstream/` is a pristine clone at `8445b7f` and was **not modified**
(`git status --short` shows only three untracked `src/__pycache__/*.pyc`).

---

## 0. TL;DR — the three findings that change the plan

1. **The full pipeline CANNOT complete on this machine — and the binding
   constraint is DISK, not RAM.** `C:` has **6.87 GB free**. The pipeline needs
   **~12 GB** for a test-only run and **~23 GB** end-to-end.
2. **4.21 GB of stale DuckDB spill is sitting on disk.**
   `amazon_ml_2026_research\.tmp\duckdb_temp_storage_*.tmp`, all timestamped
   2026-09-25 20:31, summing to 4,518,576,128 bytes. Leftovers from a killed
   run. Deleting them is the highest-value action available.
3. **~75% of the pipeline does not need to run at all.** `_upstream/models/`
   already ships the *cross-fitted* models `crossfit.py` would otherwise spend
   hours and 8-14 GB producing. `learn_translit.py` is also skippable because
   `normalize.py:84` loads a dictionary that already exists in the clone.
   Skipping both removes the two most memory-hungry stages.

RAM note: free physical RAM was **640 MB** at audit time (brief said 809 MB) of
7,913 MB total, 12 logical CPUs. Critically, `C:\pagefile.sys` is
**33,787 MB allocated / 5,241 MB in use**, so Windows pages rather than kills.
Free physical RAM is a *throughput* problem, not a hard-failure mode. The
earlier "480 MB scan OOM-kill" is better explained by the DuckDB
`could not allocate block of size 256.0 KiB (5.5 GiB/5.5 GiB used)` error
recorded in `test_pipeline_tight_memory.py:3-5` — an allocator ceiling, not a
kernel OOM. **Disk, not RAM, is what will actually stop this.**

---

## 1. Scope change: France has ZERO training rows — CONFIRMED

Confirmed twice, independently.

### 1a. `analysis_out/profile/*.json` (`country_rows`)

```
train_s1  country_rows = {"US": 1323633, "India": 883188}
train_s2  country_rows = {"India": 2017799, "US": 3016817}
train_s3  country_rows = {"US": 3170056, "India": 2115547}
test_s1   country_rows = {"US": 663106, "France": 259452, "India": 809986}
test_s2   country_rows = {"India": 2312565, "France": 703378, "US": 1871330}
test_s3   country_rows = {"India": 2405000, "France": 731615, "US": 1945701}
```

No `France` key in any train file. France total in test = 1,694,445.

### 1b. Byte-level streaming scan of the raw TSVs (no dataframe)

Last tab-field of every line, 4 MiB at a time, pure Python:

```
train 1 {b'country': 1, b'US': 1323633, b'India': 883188}
train 2 {b'country': 1, b'India': 2017799, b'US': 3016817}
train 3 {b'country': 1, b'US': 3170056, b'India': 2115547}
test  1 {b'country': 1, b'US': 663106, b'France': 259452, b'India': 809986}
test  2 {b'country': 1, b'India': 2312565, b'France': 703378, b'US': 1871330}
test  3 {b'country': 1, b'India': 2405000, b'France': 731615, b'US': 1945701}
```

Exactly reproduces 1a. **`France = 0` training rows is fact, not inference.**

### 1c. `crossfit.py:112` — France is never trained on. CONFIRMED.

```python
112:    for c in ("US", "India"):
```

and again at line 122:

```python
122:    best = pl.concat([pl.read_parquet(f"{W}/cf_best_{c}.parquet") for c in ("US", "India")], how="diagonal_relaxed")
```

The tuple is hard-coded. Had France appeared in train, `cf_best_France.parquet`
would never be built and line 122 would throw `FileNotFoundError`. The code is
only correct *because* France is test-only.

### 1d. `decoy_postfilter.py:17-18` — the codebase already knows. CONFIRMED.

```
17:      (b) the country has no training labels (e.g. France in the test set) and d is any decoy
18:          offset (+1..+21 list). Without labels for that country the model is least calibrated.
```

### 1e. Judgement: memory problem or scoring problem?

**Both — and they pull in opposite directions.**

*Scoring*: a France-untrained model is the single largest scoring risk.
259,452 France S1 entities = **14.98% of the 1,732,544 test S1 rows**;
France contributes 1,694,445 of 11,702,133 test rows. The stage-2 model has
*zero* French gradient-boosting splits — every `state_eq`, `pin_eq` and
`city_*` feature is applied out of distribution, and `model_stage2_cf.json`
records `thr = 0.65` tuned *only* on US+India validation rows.
`decoy_postfilter.py` rule (b) exists precisely to compensate. Worth more than
any dictionary tuning.

*Memory*: mildly helpful, and the help is **much smaller than it looks.** France
is 14.98% of test S1 and 14.4% of test queries — it is the *smallest* of the
three countries by query count (US 3,817,031; India 4,717,565; France
1,434,993). Dropping training data does not shrink the **test** feature build
at all, which is the dominant cost. So this does **not** let us skip French test
work; it only lets us skip French *training*, which we skip anyway because the
models are pre-built.

**Verdict: treat the France finding as a scoring risk to report, not as a
memory saving.**

---

## 2. `work_index.sqlite` — is there a prepared index?

**No. The table is empty.** Schema exists, zero rows:

```sql
CREATE TABLE t(source TEXT,id TEXT,name TEXT,address TEXT,country TEXT)
CREATE INDEX t_name ON t(name)
CREATE INDEX t_addr  ON t(address)
```
```python
>>> c.execute('select count(*) from t').fetchone()
(0,)
```

A 20,480-byte file with a 0-byte WAL. **It will save nothing.** It is also not
the schema the pipeline uses (no `ncore`/`atoks`/`rid`), so it could not be
substituted for `{split}_cand.parquet` even if populated. Dead weight.

---

## 3. Dataset facts used throughout

Files live in `dataset/train/` and `dataset/test/`, **not** directly in
`dataset/`.

| file | bytes | rows |
|---|---|---|
| train_source1.tsv | 210,069,713 | 2,206,821 |
| train_source2.tsv | 489,301,488 | 5,034,499 |
| train_source3.tsv | 503,705,637 | 5,285,482 |
| train_ground_truth.tsv | 127,015,583 | 2,206,821 |
| test_source1.tsv | 175,022,086 | 1,732,544 |
| test_source2.tsv | 509,456,422 | 4,887,151 |
| test_source3.tsv | 506,002,772 | 5,082,195 |

train S1 = 2,206,821; train queries = 10,319,981; test S1 = 1,732,544;
test queries = 9,969,589. Per test country — US S1 663,106 / q 3,817,031;
India S1 809,986 / q 4,717,565; France S1 259,452 / q 1,434,993.

---

## 4. Per-stage audit

### Stage 1 — `convert.py` (7 files)

* **Whole-file read?** **YES — red flag.** `convert.py:9`
  `pl.read_csv(f"{src}/{split}/{name}.tsv", ...)` materialises the whole TSV.
  Worst case `train_source3.tsv`: 5.29M rows x 3 Utf8 columns. Polars stores
  each string as a 16-byte view into a contiguous buffer, so 5.29M x 3 x 16 B
  = 254 MB of views + ~420 MB of character data, plus read buffer, plus
  `fill_null` and `write_parquet` transients.
* **Peak:** 0.9–1.4 GB. **Chunked?** No. **Threads:** polars defaults to 12 here.
* **OOM risk: HIGH** as written, **LOW** with a one-line change.
* **Mitigation:** streaming scan — identical output, ~120–200 MB:
  ```python
  pl.scan_csv(f"{src}/{split}/{name}.tsv", separator="\t", quote_char=None,
              infer_schema=False).sink_parquet(f"{out}/{name}.parquet")
  ```
  Add `.with_columns(pl.all().fill_null(""))` *before* `sink_parquet` if the
  null-fill matters (sink_parquet streams, so it stays bounded).
  If the shipped models are used, **convert the three test files only** and
  skip all four train files.

### Stage 2 — `learn_translit.py` — **SKIP ENTIRELY**

* **Whole-file read?** **YES, four times, plus two `.to_list()` explosions.**
  `:30` whole GT parquet; `:33` whole train_source1; `:36`
  `pl.concat([read_parquet(source2), read_parquet(source3)])` — **that concat
  alone is ~1 GB of the ~1.2 GB of train s2+s3 parquet** — then filters for
  Indic script. `:39` builds join `j`. `:41` and `:52` each `.to_list()` two
  columns of `j`, materialising **7.6M true pairs x 2 Python strings ≈ 1.5 GB**
  of CPython objects on top of the frames.
* **Peak:** 3.5–5.0 GB. The single largest RAM stage. **Chunked?** No.
* **OOM risk: HIGH → eliminate by deletion.**
* **Proof it is skippable:** `run_all.sh:8` does `cd "$(dirname "$0")/src"` and
  `run_all.sh:10` passes `resources/indic_token_dict.json` as the output path —
  it **overwrites a file that already exists in the clone**:
  `_upstream/src/resources/indic_token_dict.json`, 47,788 bytes, thousands of
  Indic→Latin entries. `normalize.py:81-86` is the only consumer:
  ```python
  83:    if _DICT is None:
  84:        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "indic_token_dict.json")

### Stage 4 — `run_blocking.py train` / `run_blocking.py test`

* **Whole-file read?** Partially — it is already **per-country** (`:14`,
  `:16` writes `_tmp_q_{country}.parquet` with `row_group_size=100000`). Good
  design. The problem is downstream.
* **Peak:** 3.0–5.0 GB. Cause is `blocking.py:20 query()`:
  * `keys.py` emits **~90 blocking keys per row** (`na` = up to 5 name x 13
    address tokens = 65; `nn` = C(5,2) = 10; `aa` = 3 + C(4,2) = 9; `f` = 1;
    `t` = 5).
  * `:33` `j = k2.select("rid","key","na").join(idx, on="key")` — with `CAPS` up
    to 300 for no-address queries, a 40,000-row chunk can join out to **tens of
    millions** of rows.
  * `out = []` at `:22` **accumulates every chunk's result for the whole country
    before `pl.concat(out)` at `:40`.** US test = 96 chunks resident at once.
* **Chunked?** Geometrically yes (`:26`), materially no (accumulated).
* **Defaults:** `run_blocking.py:8 TOPK, REL = 50, 0.2`; `:27 chunk=40000`;
  `build_s1_index` default `chunk=100000`.
* **OOM risk: HIGH.**
* **Mitigation:** (1) `chunk=40000 -> 8000` (5x smaller join peak); (2) **stream
  `sc` to `{cand}_{country}_{i:04d}.parquet` per chunk** — `:32` already
  lazy-concats them, so this is a pure loop-body change and the single biggest
  win in this stage; (3) `TOPK 50 -> 25` roughly halves retained candidate rows
  and the final ranker prunes to 3.97/S1 anyway (README), so recall loss is
  small; keep `REL = 0.2` (that is the real filter); (4)
  `make_keys_chunked(..., 100000 -> 50000)`.

### Stage 5 — `build_features.py train / trainT / trainRest / test`

* **Whole-file read?** For every **train** mode, **YES**: `:30-31`
  `pl.read_parquet(f"{W}/train_cand.parquet", ...)` and
  `pl.read_parquet(f"{W}/train_s1.parquet", ...)` are both resident for the
  entire stage. Train `cand` ~45M rows x 6 cols ≈ 900 MB, train_s1 2.2M rows x
  13 string cols ≈ 700 MB. `run()` then does `pairs.sort("rid")` + `group_by` +
  `cum_sum` (more copies) before any chunking begins. The **`test`** mode is
  already per-country (`:107-113`) — the good case.
* **Peak:** 2.5–4.0 GB **at the shipped `CHUNK`**, because
  `build_features.py:17 CHUNK = 600000` is a **hard-coded module constant, not
  env-tunable**. Per 600k-pair chunk, `compute_features`:
  * `features.py:64` `p.join(qq).join(ss)` — 600k rows x **25 string columns**
    ≈ 840 MB of views + data.
  * `:67-90` ten `.to_list()` calls → 6.6M CPython strings ≈ 400 MB.
  * `:96-102` `sp(...)` builds list-of-list columns for 8 token fields —
    another 0.6–1.0 GB.
  * `_weighted_overlap` is called **twice** (`:128`, `:129`), each exploding to
    one row per (pair, token) — a further 2-3x blowup.
  Peak scales linearly in `CHUNK`.
* **nproc default:** `features.py:24 process.cpdist(..., workers=2)` — already
  conservative, keep at 2 (rapidfuzz workers are threads, so they are cheap).

### Stage 6 — `select_T.py`

* **Whole-file read?** No — `scan_parquet` + `collect(engine="streaming")`
  throughout (`:8`, `:11`).
* **Peak:** 150–300 MB (`s1t` = 4% of 2.2M = 88k rows; `qt` a streamed distinct
  rid list).
* **OOM risk: LOW.** No change needed. (Moot if models are shipped.)

### Stage 7 — `crossfit.py` — **SKIP ENTIRELY (the killer)**

* **Whole-file read?** Effectively yes, twice over.
* **`stage1()` peak: 5.3–8 GB.** `:23 MAX_PAIRS = 10_500_000`. `:78`
  `Xs.append(d.select(cols).to_numpy().astype(np.float32))` accumulates to
  10.5M rows = **2.65 GB**. `:81 X = np.concatenate(Xs)` allocates a **second**
  2.65 GB copy before the first is freed (`del Xs` is on the same line, but peak
  is already 5.3 GB). `:85 lgb.Dataset(X).construct()` then builds the uint8
  binned matrix (10.5M x 63 = 660 MB) **while `X` is still referenced by the
  caller**, and LightGBM doubles it internally for the histogram build.
* **`stage2_train()` peak: 8–14 GB. The worst stage.** `:129-131`:
  ```python
  for pre, d in iter_rows(home):
      feats.append(d.join(keys, on=["rid", "s1"]))
  F = pl.concat(feats, how="diagonal_relaxed"); del feats
  ```
  This accumulates **the entire cross-fitted training feature set** — every
  `train_val` + `train_T` + `train_trn` + `train_rest` part — in RAM: ~45M rows
  x 66 columns ≈ 12 GB raw. `:132 F.join(best, ...)` copies it again; `:136`
  `tr`/`va` splits copy it twice more; `:143-144`
  `tr.select(cols).to_numpy().astype(np.float32)` = 840 MB per copy, and
  `free_raw_data=True` does not help because `tr` is a polars frame, not numpy.
* **Threads:** `num_threads=2` (`:65`, `:142`) — already conservative.
* **OOM risk: CRITICAL.** The README's "peak memory stays under about 6 GB" is
  optimistic and not reproducible for the `trainRest` path as shipped.
* **Mitigation: do not run it** (§5). If it must: `MAX_PAIRS 10.5M -> 1.5M`
  (X ≈ 380 MB, concatenate peak 760 MB), and replace the `feats` accumulator
  with a two-pass design that never holds `F` whole (write the joined table to
  parquet, stream it back in row groups, construct `lgb.Dataset` per group with
  `free_raw_data=True`).

### Stage 8 — `make_submission.py`

* **Whole-file read?** Partially, and already **per-country** for stage 2
  (`:47`). But:
  * `:30-38` `res = []` accumulates stage-1 output for **all countries** before
    `pl.concat(res).write_parquet(pred_path)` — 53M rows x 12 B x 2 ≈ **1.3 GB**.
  * `:45` `s1dups = stage2.s1_duplicates(pl.read_parquet(f"{W}/test_s1.parquet",
    columns=["rid","country","ncore","atoks"]))` — the **entire** test S1
    (1.73M rows, two string columns) in one frame, then `stage2.py:97-98`
    `pl.len().over(["country","atoks"])` window over a string column.
    ~400-600 MB, and the one **global** (non-per-country) structure here.
  * `:49` `pred_c = scan(pred_path).join(qtext.rid).collect()` per country — for
    **US**, 3.82M queries x ~30 candidates = **~114M rows x 12 B ≈ 1.4 GB**.
  * `:50` `cf = pl.concat([read_part(p).select("rid","s1","a_tset","nf_tset") ...])`
    per country — same 114M rows x 16 B ≈ **1.8 GB** for US.
  * `stage2.py:84` `cf.join(best...)` inside `candidate_competition` makes

---

## 5. What can be skipped outright — the biggest win

### 5a. The cross-fitted models are already in the repo

`_upstream/models/` (all tracked files, `git status` clean):

| file | bytes | content |
|---|---|---|
| `model_stage1_cf.json` | 709 | `cols` = the 63 stage-1 features |
| `model_stage1_f0.txt` | 13,777,364 | LightGBM booster, 870 trees |
| `model_stage1_f1.txt` | 13,301,048 | LightGBM booster, 870 trees |
| `model_stage2_cf.json` | 1,080 | `cols` = 84 features, **`thr` = 0.65**, `val_f05` = 0.98612 |
| `model_stage2_cf.txt` | 9,212,800 | LightGBM booster |

`make_submission.py:15` decides which path to take purely by file existence:

```python
15: CF = os.path.exists(f"{W}/model_stage2_cf.txt")
16: if CF:
17:     m1_meta = json.load(open(f"{W}/model_stage1_cf.json"))
18:     m1_files = [f"{W}/model_stage1_f0.txt", f"{W}/model_stage1_f1.txt"]
19:     m2_meta = json.load(open(f"{W}/model_stage2_cf.json")); m2_file = f"{W}/model_stage2_cf.txt"
```

So: **copy `_upstream/models/*` into `$WORK/` and `make_submission.py` takes the
`CF=True` branch automatically.** The feature-column contract is exact —
`model_stage1_cf.json` lists 63 columns and `model_stage1_f0.txt` header says
`max_feature_idx=62`; `model_stage2_cf.json` lists those 63 plus the 21 columns
that `stage2.build` appends (`p1, p1_2nd, n_p1_gt01, n_cand_all, p1_margin,
c_n_oth, c_sum_oth, c_n_hi_oth, c_n_same_src, c_n_other_src, c_max_oth,
qq_n_tset, qq_a_tset, qq_sum, qq_num_eq, cc_max_a_oth, cc_max_n_oth,
cc_n_addr_hi_oth, cc_n_name_hi_oth, cc_n_both_hi_oth, s1_name_dups,
s1_addr_dups`) = 84. Matches `stage2.py:102-113` exactly.

**Consequence — these six `run_all.sh` steps become unnecessary:**

| run_all.sh line | step | why it is now dead |
|---|---|---|
| 10 | `learn_translit.py` | dict already in `src/resources/` (Stage 2 above) |
| 14 | `build_features.py train` | only produces V + 2M training queries, consumed solely by `crossfit.py` |
| 15 | `select_T.py` | only defines T, consumed solely by `crossfit.py` |

---

## 6. Per-country isolation in `make_submission.py` — verified, and how to push it further

### 6a. Verification: clusters provably cannot cross countries

**Two independent guarantees, not one:**

1. **Structural (strongest).** Every blocking key is country-prefixed —
   `keys.py:49-50`:
   ```python
   def _h(col, country, seed):
       return (pl.col("country") + ":" + pl.col(col)).hash(seed=seed)
   ```
   A French query hashes only against French S1 keys. A cluster is therefore
   country-pure *by construction of the key space*, not by convention. This also
   means France's untrained model cannot be rescued by cross-country evidence —
   there is none available by design.

2. **Control flow.** `make_submission.py:47` `for c in countries:` calls
   `stage2.build(pred_c, qtext, cf, s1dups)` once per country. Every grouping in
   `stage2.py` that forms a cluster — `context_features` (`:34 group_by("s1")`),
   `qq_features` (`:60 join(mem, on="s1")`), `candidate_competition` (`:86
   group_by("rid")`), `s1_duplicates` (`:97 over(["country","ncore"])`) — is
   scoped to a single country's `s1`/`rid` domain. `run_blocking.py:14` and
   `build_features.py:107` do the same on their side.

### 6b. Is that enough at 640 MB free? **No — and the reason is important.**

Per-country isolation buys a reduction from "three countries at once" to "the
largest country at once". Measured:

| country | test queries | share | share of ~53M candidate pairs |
|---|---|---|---|
| US | 3,817,031 | 38.3% | ~57% |
| India | 4,717,565 | 47.3% | ~29% |
| France | 1,434,993 | 14.4% | ~14% |

So the best case is a **~1.75x** reduction, not an order of magnitude — and it
is already implemented. The residual problem is that a *single* country's
working set is already too large (US: 114M candidate rows ≈ 1.4 GB for
`pred_c` plus 1.8 GB for `cf`).

**Push isolation one level further: per-country x per-rid-window.**
`stage2.build` is correct for *any* rid-subset as long as the subset is
**rid-contiguous**, because a query `rid` never links to another `rid` — all
stage-2 context is keyed on `s1` (shared S1) and within-query. So:

```python
# make_submission.py, replace the per-country loop body
WINDOW = 400_000            # queries per window; tune down if RAM-bound
for c in countries:
    rids = (pl.scan_parquet(f"{W}/test_q.parquet")
              .filter(pl.col("country") == c)
              .select("rid").sort("rid").collect()["rid"].to_list())
    for lo in range(0, len(rids), WINDOW):
        sub = pl.DataFrame({"rid": rids[lo:lo + WINDOW]})
        qtext  = (pl.scan_parquet(f"{W}/test_q.parquet")
                     .join(sub.lazy(), on="rid")
                     .select("rid","entity_id","ncore","atoks","anums").collect())
        pred_c = pl.scan_parquet(pred_path).join(sub.lazy(), on="rid").collect()

---

## 7. Per-stage memory budget table

RAM columns are peak **resident** for the stage as written on this box
(12 threads, 640 MB free, 33 GB pagefile). "Mitigated" assumes every change in
§8 is applied. Disk deltas are for the **test-only** path.

| # | Stage | Whole-file read | Peak as-written | Peak mitigated | OOM risk | Disk delta |
|---|---|---|---|---|---|---|
| 0 | *reclaim `\.tmp` spill* | — | — | — | — | **−4.21 GB** |
| 1 | `convert.py` (test x3) | YES `read_csv` | 0.9–1.4 GB | 120–200 MB | HIGH→LOW | +0.70 GB |
| 2 | `learn_translit.py` | YES x4 + 2x `.to_list()` | 3.5–5.0 GB | **SKIPPED (0)** | HIGH→NONE | 0 |
| 3 | `prep.py` (test x3) | YES + `parts` list | 3.5–4.5 GB | 300–450 MB | HIGH→LOW | +1.00 GB |
| 4 | `run_blocking.py test` | per-country, `out` accumulates | 3.0–5.0 GB | 500–800 MB | HIGH→MED | +0.50 GB |
| 4b | `test_cand.parquet` concat | lazy (`run_blocking.py:32`) | +0.5 GB | +0.5 GB | LOW | +0.50 GB (delete per-country parts after) |
| 5 | `token_idf` (inside build_features) | lazy + streaming | 0.3–0.5 GB | 0.3 GB | MED | +0.01 GB |
| 6 | `build_features.py test` | per-country, 600k chunks | 2.5–4.0 GB | **250–400 MB** (`CHUNK=50k`) | HIGH→LOW | **+7.40 GB** ← binding |
| 7 | `build_features train/T/rest` (x3) | YES | 3.5–5.0 GB | **SKIPPED (0)** | HIGH→NONE | 0 (would be +6.30 GB) |
| 8 | `select_T.py` | NO, streaming | 0.15–0.30 GB | **SKIPPED (0)** | LOW | 0 |
| 9 | `crossfit.py s1` | effectively YES | 5.3–8.0 GB | **SKIPPED (0)** | CRITICAL→NONE | 0 |
| 10 | `crossfit.py s2` | YES (concats all parts) | **8–14 GB** | **SKIPPED (0)** | CRITICAL→NONE | 0 |
| 11 | `make_submission.py` | per-country | 4.0–6.0 GB | 1.0–1.5 GB (ridged) | HIGH→MED | +0.80 GB |
| — | `output/*.tsv` | streaming write | 0.05 GB | 0.05 GB | LOW | +0.15 GB |

**Totals**

| path | RAM peak | Disk needed |
|---|---|---|
| full `run_all.sh` as shipped | **14 GB** | **~23 GB** |
| test-only, no patches | 6.0 GB | ~12.1 GB |
| test-only + shipped models + all mitigations | **1.5 GB** | **~11.1 GB** |
| disk available now | — | **6.87 GB** |
| disk after reclaiming stale spill | — | **~11.1 GB** |

The 7.40 GB line for `feat/test_*_part*.parquet` is derived from ~53M test
candidate pairs (README: 30.5/S1 after retrieval) x ~66 columns (~52 float32 +
~27 B of ints) at ~140 B/row after zstd. It is the single largest item and it
is what makes even the mitigated test-only path **fail to fit**.

---

## 8. Exact mitigation settings

### 8a. Environment (every stage, no code change)

```powershell
$b='C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)'
$env:POLARS_MAX_THREADS   = '2'    # polars reads this at import; box has 12 logical CPUs
$env:OMP_NUM_THREADS      = '2'    # LightGBM / OpenMP

### 8c. DuckDB, if the alternative `er_pipeline.py` is used instead

`er_pipeline.py:33-36` exposes exactly the right knobs, and
`test_pipeline_tight_memory.py` proves it completes under a 256 MB budget on
synthetic data. Defaults are `memory_limit="6GB"`, `temp_directory_size="40GB"`,
`threads=min(8, cpu_count)`. For this box:

```python
P.CFG.update(threads=2, memory_limit="600MB", temp_directory_size="6GB",
             max_candidates=8, train_sample_pct=1, candidate_sample_rows=300_000)
spill = r"C:\Users\pvish\AppData\Local\Temp\er_spill"   # LOCAL disk, not OneDrive
P.run(work_dir=..., dataset_dir=..., spill_dir=spill)
```

Two warnings from its own docstring (`er_pipeline.py:883-897`) that this audit
confirms: (i) **put the spill directory on fast local disk, never on OneDrive** —
that is exactly where the 4.21 GB of orphaned spill now sits, and OneDrive
file-watcher traffic over multi-GB spill is pathological; (ii) it needs a real
spill budget or DuckDB refuses to spill. Also note `er_pipeline.py:36`: the
candidate stage alone can emit **tens of GB** of spill — so it is *not* a way
around the disk ceiling either, it is a way of *staying inside the RAM ceiling
while spending disk*.

### 8d. The decisive change: do not materialise `feat/test_*` at all

`feat/test_*_part*.parquet` at 7.40 GB does not fit. **Fuse steps 6 and 11** —
compute features, predict, and keep only the best pair per `rid` — in a single
streaming pass. Per country and per rid-window, keep only:

- `best` (one row per `rid`: s1, p1, p1_2nd, n_p1_gt01, n_cand_all, p1_margin)
- the five `cc_*` aggregates over the **non-best** candidates (computable in the
  same pass without keeping `cf`)
- the `qq_*` aggregates (needs a second pass over the window only)

That drops stage 6's disk from **7.40 GB to ~0.30 GB** and the whole test-only
path from 11.1 GB to **~4.0 GB**, which fits inside the 11.1 GB available after
reclaiming the spill with >2x headroom. It also removes `pred_test_cf.parquet`
(0.6 GB) and `test_best_pred_cf.parquet` (0.2 GB) as materialised artifacts.

---

## 9. Safe execution order

**Rule: get a VALID submission on disk before anything else. Then improve it.**

### Phase 0 — reclaim disk (2 minutes, DO THIS FIRST)

```powershell
$b='C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)'
# 4,518,576,128 bytes of orphaned spill from a run killed on 2026-09-25 20:31
Remove-Item "$b\amazon_ml_2026_research\.tmp\duckdb_temp_storage_*.tmp" -Force
Get-Volume -DriveLetter C | Select-Object @{n='FreeGB';e={[math]::Round($_.SizeRemaining/1GB,2)}}
```
Expected: **6.87 GB -> ~11.1 GB.**

### Phase 1 — generate the VALID fallback submission (5 min, 50 MB RAM) — **highest priority**

Produce the all-empty baseline from §10 **now**, run the official validator on
it, and keep the two TSVs permanently. This costs nothing, needs no pipeline,
and guarantees a submittable artifact exists before any long job starts.

### Phase 2 — arm the shipped models (1 minute, 0 RAM)

```powershell
$W="$b\work"; New-Item -ItemType Directory -Force $W | Out-Null
Copy-Item "$b\_upstream\models\*" $W\

---

## 10. Minimal viable VALID baseline submission — exact spec

### 10a. Why an all-empty submission is worth having immediately

From `metrics.py:11-18`:
```python
f = (pl.when((pl.col("np") == 0) & (pl.col("nt") == 0)).then(1.0)
     .when((pl.col("np") == 0) | (pl.col("nt") == 0) | (pl.col("tp") == 0)).then(0.0)
     .otherwise(...))
```
An S1 with no true matches (`np==0, nt==0`) scores **1.0** for an empty
prediction. An S1 with true matches scores **0.0** if we predict nothing.

Measured on `train_ground_truth.tsv` (byte-level scan, no dataframe):
```
GT rows          = 2206821
singletons (0)   = 123247 (5.58%)
total true pairs = 7638365
mean matches/S1  = 3.461
hist: 0->123247  1->119157  2->375212  3->530841  4->484115  5->321957  6->164868
```

So the all-empty submission scores **≈ 0.056** (the singleton rate), assuming
test matches train's distribution. That is a real, non-zero floor: it converts
"no submission" into "a valid ~5.6% submission" for the cost of one streaming
pass over `test_source1.tsv`. It also establishes the honest reference point
that any France-dictionary or threshold change must beat.

**The asymmetry that makes this the right conservative posture:** under this
metric, *every* prediction added to a singleton S1 converts a guaranteed 1.0
into a near-certain 0.0. A baseline must therefore be **recall-poor on
singletons by construction**: predict nothing unless very confident.

### 10b. Exact generator — ~50 MB RAM, ~30 s, no pipeline

```python
# make_baseline.py  (workspace root; NEVER inside _upstream)
from pathlib import Path

DS = Path(r"C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)"
          r"\amazon_ml_2026_research\student_resource\dataset")
OUT = Path(r"C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)\output")
OUT.mkdir(parents=True, exist_ok=True)

seen = set()
with (DS / "test" / "test_source1.tsv").open(encoding="utf-8") as f, \
     (OUT / "matching_results.tsv").open("w", encoding="utf-8", newline="") as m, \
     (OUT / "candidate_pairs.tsv").open("w", encoding="utf-8", newline="") as c:
    next(f)                                    # skip the header
    m.write("source1_entity_id\tmatched_entity_ids\n")    # TAB, exact spelling
    c.write("source1_entity_id\tcandidate_entity_ids\n")
    for line in f:
        if not line.strip():
            continue
        s1 = line.split("\t", 1)[0].strip()
        if s1 in seen:                          # validator: no duplicate S1 rows
            continue

### 10d. Tiering — each step is strictly additive; stop wherever you run out of time

| tier | content | expected | cost |
|---|---|---|---|
| **0** | all-empty (§10b) | ~0.056 | 30 s, 50 MB |
| **1** | empty + **exact** normalized match (name-core AND address-token-set), one top hit per S1, and **never** fill a candidate whose `atoks` is empty | > 0.056 | needs only the `prep.py` test output |
| **2** | tier 1 + the shipped stage-1/stage-2 models at `thr=0.65` | ~0.9+ | the full test-only path of §9 |
| **3** | tier 2 + `decoy_postfilter.py` (its rule (b) is *designed* for the untrained France) | best available | one extra pass |

Tier 1's guard rails come straight from the metric: require a non-empty
`atoks` match (a name-only match on an address-less record is exactly the false
positive that burns a guaranteed 1.0), and emit at most one ID per S1
(beta = 0.5 weights precision ~4x recall, so a wrong second guess is expensive).

### 10e. One fix to fold in while you are there

`decoy_postfilter.py` needs a `--dataset` scan to estimate decoy shares and, in
its `--hidden` mode, loads matched IDs into Python sets. On this box that is the
same class of OOM as `crossfit.py`. Run it **per country** on
`matching_results.tsv` slices, or just its rule (b) which needs only the
predicted pairs plus `test_source1.tsv` addresses — both small
(France: 259,452 S1 rows ≈ 60 MB).

---

## 11. Final judgement

**Can the full pipeline complete in 809 MB free RAM?**

**No — but RAM is the wrong thing to worry about.** Three independent reasons:

1. **Disk, decisively.** 6.87 GB free (11.1 GB after reclaiming the orphaned
   spill) against ~23 GB for the full run and ~12 GB for a test-only run. The
   `feat/` tables alone are ~13.7 GB. No amount of chunk tuning fixes this.
2. **`crossfit.py` is 8-14 GB by construction** (`MAX_PAIRS=10.5M` doubled by
   `np.concatenate`, then the whole 45M-row cross-fit table `pl.concat`ed in
   `stage2_train`). It cannot be chunked into 809 MB without being rewritten.
3. **Free physical RAM is not a hard limit here.** The pagefile is 33,787 MB
   with 5,241 MB already committed, so a polars/NumPy process will page, not be
   killed. The realised failure mode will be *slowness* and — far worse —
   **disk exhaustion**, which does kill.

**Minimal viable path to a submission — three options, in order of preference:**

1. **Shipped models + test-only + fused streaming scorer (§5, §8d, §9).**

---

## 13. Execution log — the fallback was generated and VALIDATED

`make_baseline.py` (written to the workspace root, **not** into `_upstream`) was
run and the **official validator** was run against its output. This is not a
proposal; it is a verified artifact.

```
$ python make_baseline.py
rows written : 1732544
duplicates skipped : 0
expected     : 1732544 (all S1- prefixed)

$ python utils/validate_submission.py --matching  output/matching_results.tsv \
                                      --candidate output/candidate_pairs.tsv \
                                      --test-dir  .../dataset/test
  required S1 entities: 1732544
  matching_results.tsv: 1732544 rows (1732544 empty, 0 non-empty).
  candidate_pairs.tsv: 1732544 rows (1732544 empty, 0 non-empty).
PASS - no blocking issues found. Safe to submit.
EXIT CODE: 0
```

Artifacts now on disk at
`C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)\output\`:

| file | bytes |
|---|---|
| `matching_results.tsv` | 24,063,927 (22.9 MB) |
| `candidate_pairs.tsv` | 24,063,929 (22.9 MB) |

Both headers are exact and tab-separated:
```
source1_entity_id<TAB>matched_entity_ids
source1_entity_id<TAB>candidate_entity_ids
```

**So a valid, submittable fallback already exists and costs 48 MB of disk.**
Expected score ≈ 0.056 (the 5.58% singleton rate measured in §10a). Everything
in §9 Phase 4 is now pure upside.

`_upstream/` was re-verified clean after all work:
`git status --short` -> only three untracked `src/__pycache__/*.pyc`; `git diff
--stat HEAD` -> empty.

   Best expected score, ~4.0 GB disk / ~1.5 GB RAM peak. Skips 6 of 12 stages.
   Needs the `scan_csv` / `CHUNK` / streaming patches in `patch_upstream/` and
   the Phase-0 disk reclaim. **This is the recommendation.**
2. **Shipped models + test-only, unmaterialised features blocked by disk.**
   If §8d is too large a change, drop the `test_cand.parquet` concat (0.5 GB,
   rewrite `make_submission.py` to read the three per-country files directly)
   and shrink `TOPK` to 20. Gets to ~9 GB. Still needs the Phase-0 reclaim.
3. **Exact-match-only baseline (§10 tiers 0-1).** ~30 s, 50 MB RAM, no pipeline
   at all. Expected 0.056 to perhaps 0.3. **Generate this regardless, in
   Phase 1, before anything else runs** — it is the insurance policy.

**Do not** attempt the full `run_all.sh` on this machine. And note that
`_upstream` must stay pristine: every mitigation in §8b belongs in
`patch_upstream/`, applied as an overlay or a copy of the source tree, never as
an edit to the clone.

---

## 12. Evidence index

| claim | evidence |
|---|---|
| France has 0 train rows | profile `country_rows` + independent byte scan of the TSVs (§1a/1b) |
| France skipped in training | `crossfit.py:112`, `:122` (§1c) |
| codebase knows France is test-only | `decoy_postfilter.py:17-18` (§1d) |
| `work_index.sqlite` is empty | `select count(*) from t` -> `(0,)` (§2) |
| models already shipped | `_upstream/models/*`, 5 files, tracked (§5a) |
| `learn_translit` skippable | `normalize.py:84` + existing `src/resources/indic_token_dict.json` (Stage 2) |
| whole-file reads | `convert.py:9`, `prep.py:22`, `learn_translit.py:30/33/36`, `build_features.py:30-31` (§4) |
| blocking key fan-out ~90/row | `keys.py:53-73` (Stage 4) |
| `CHUNK` is hard-coded | `build_features.py:17` (Stage 5) |
| `crossfit` peak 8-14 GB | `crossfit.py:23`, `:78-85`, `:129-144` (Stage 7) |
| clusters cannot cross countries | `keys.py:49-50` (structural) + `make_submission.py:47` (control flow) (§6a) |
| singleton rate 5.58% | byte scan of `train_ground_truth.tsv` (§10a) |
| submission contract | `validate_submission.py:48-49`, `:158-163`, `:181-198`, `:274-284` (§10c) |
| disk 6.87 GB free, 4.21 GB reclaimable | `Get-Volume C`; `.tmp\duckdb_temp_storage_*.tmp` |
| pagefile 33,787 MB | `Win32_PageFileUsage` |
| `_upstream` unmodified | `git -C _upstream status --short` (only untracked `__pycache__`) |

        seen.add(s1)
        m.write(f"{s1}\t\n")                   # empty second field = singleton
        c.write(f"{s1}\t\n")
print("rows written:", len(seen))
```

Measured ground truth for this loop: **1,732,544 rows**, all prefixed `S1-`.

### 10c. Why it passes the official validator

`validate_submission.py:48-49` fixes the headers:
```python
MATCHING_HEADER  = ["source1_entity_id", "matched_entity_ids"]
CANDIDATE_HEADER = ["source1_entity_id", "candidate_entity_ids"]
```
* `required = read_ids(test_source1.tsv)` (`:243`) -> all 1,732,544 S1 ids.
  Every one is emitted exactly once -> no "missing entity" error.
* `seen` guarantees no duplicate `source1_entity_id` rows (`:181-185`).
* Empty second field -> `ids = []` (`:158-163`) -> no intra-list duplicates
  (`:186-189`), no self-matches (`:191-194`), no bad prefixes (`:195-198`).
* `candidate_pairs.tsv` **is present**, so the `:274-284` "not found — required
  in your final submission zip" error does not fire. It is genuinely required:
  "candidate_pairs.tsv (required) ... When absent, its checks are silently
  skipped ... the run **fails**" (docstring, lines 18-22).
* `matched ⊆ candidate` holds trivially (both empty) -> no subset warning.
* The ID-existence check is **off by default** (`:262-268`) precisely because
  loading all S2/S3 ids costs a few GB. Leave it off.

Verify:
```powershell
cd "$b\amazon_ml_2026_research\student_resource"
& "$b\.venv\Scripts\python.exe" utils/validate_submission.py `
    --matching  "$b\output\matching_results.tsv" `
    --candidate "$b\output\candidate_pairs.tsv" `
    --test-dir  "$b\amazon_ml_2026_research\student_resource\dataset\test"
```

# -> make_submission.py will set CF=True automatically
```

### Phase 3 — free RAM before every heavy step

The box is at 640 MB free. Close OneDrive sync, browsers and the IDE. Check
before starting:
```powershell
Get-CimInstance Win32_OperatingSystem |
  Select-Object @{n='FreeMB';e={[math]::Round($_.FreePhysicalMemory/1024)}}
```

### Phase 4 — test-only pipeline, in this order

| order | command | why here |
|---|---|---|
| 1 | `convert.py` (test only, `scan_csv`→`sink_parquet`) | no dependencies; cheap after the patch |
| 2 | `prep.py` (test only, `nproc=1`, streamed) | needs 1; produces `_norm.parquet` |
| 3 | `run_blocking.py test` | needs 2; **run France first, India second, US last** so a US OOM does not cost you France+India |
| 4 | `build_features.py test` | needs 3; `CHUNK=50000`; **or use the fused streaming scorer of §8d and skip the parquet entirely** |
| 5 | `make_submission.py` (rid-windowed) | needs 4; consumes the Phase-2 models |
| 6 | `utils/validate_submission.py` | gate before you trust anything |

`run_blocking.py` and `build_features.py` are already resumable — both skip a
country whose `{split}_cand_{country}.parquet` already exists
(`run_blocking.py:15`, `build_features.py:60`). Use that: run France alone,
then India, then US, so a failure costs one country, not the run.

### Phase 5 — deferred to LAST (only if time remains, and only with disk to spare)

Anything that touches train data. Not because it improves the submission — the
models are already trained — but only to produce provenance. In order:
`learn_translit` (verify the shipped dict), `convert` train, `prep` train,
`run_blocking train`, `build_features train` (+T/rest), `select_T`,
`crossfit all`. **Budget 10.8 GB of disk; do not start until the submission is
safe.**

### What can be skipped / deferred / must run — summary

| disposition | steps |
|---|---|
| **Skip entirely** | `learn_translit`, `build_features train`, `select_T`, `build_features trainT`, `build_features trainRest`, `crossfit` |
| **Must run** | `convert` (test), `prep` (test), `run_blocking test`, `build_features test`, `make_submission` |
| **Defer to last** | every train-side step (provenance only, if disk allows) |

$env:MKL_NUM_THREADS      = '2'
$env:OPENBLAS_NUM_THREADS = '2'
$env:RAYON_NUM_THREADS    = '2'
$env:FEAT_CHUNK           = '50000'   # honoured only after the build_features.py patch
$env:N_TRAIN_Q            = '500000'  # only if you ever run build_features train
```

`POLARS_MAX_THREADS` is the important one — polars defaults to the core count
(12 here), and every `group_by`/`join` in this pipeline will otherwise
multi-thread its buffers.

### 8b. Code-level constants (patch into `patch_upstream/`, never edit `_upstream`)

| file:line | current | set to | effect |
|---|---|---|---|
| `convert.py:9` | `pl.read_csv(...)` | `pl.scan_csv(...).sink_parquet(...)` | streaming, −1.2 GB |
| `prep.py:21` | `nproc=2, chunk=50000` | `nproc=1, chunk=5000` | −1 worker (Windows spawn), −transient |
| `prep.py:27-32` | `parts` accumulator | stream each chunk to its own parquet | −2.5 GB |
| `build_features.py:17` | `CHUNK = 600000` | `int(os.environ.get("FEAT_CHUNK", 50000))` | **−2.4 GB — highest leverage** |
| `build_features.py:75` | `B = 1_200_000` | `200_000` | −rid-batch in `trainRest` |
| `features.py:24` | `workers=2` | keep `2` | already right |
| `run_blocking.py:27` | `chunk=40000` | `8000` | −join peak 5x |
| `run_blocking.py:8` | `TOPK, REL = 50, 0.2` | `25, 0.2` | −candidate rows ~2x |
| `blocking.py:22,40` | `out = []` … `pl.concat(out)` | stream each chunk to `{cand}_{country}_{i:04d}.parquet`; `:32` already lazy-concats | **−3 GB** |
| `blocking.py:9` | `chunk=100000` | `50000` | −index build peak |
| `crossfit.py:23` | `MAX_PAIRS = 10_500_000` | `1_500_000` (only if it must run) | −4.7 GB |
| `make_submission.py:30-38` | `res` accumulator | stream per part | −0.6 GB |
| `make_submission.py:45` | global `s1dups` | precompute per country | −0.3 GB |
| `make_submission.py:47` | `for c in countries` | add rid-windowing (§6b, `WINDOW=400_000`) | −3.5 GB |

        cf     = (pl.concat([read_part(p).select("rid","s1","a_tset","nf_tset")
                             for p in sorted(glob.glob(f"{W}/feat/test_{c}_part*.parquet"))])
                    .join(sub.lazy(), on="rid"))          # <- add this filter
        best   = stage2.build(pred_c, qtext, cf, s1dups)
        ...    # score; append only the (rid, s1, p1, p2) rows
```

The one thing that must **not** be windowed is `s1dups` at `:45` — it is keyed
on `s1` and is legitimately global (a windowed version would under-count
duplicates for S1 entities whose queries straddle a window boundary). It is only
~400-600 MB; compute it once, or precompute per country (it is
`over(["country", ...])`, so it partitions cleanly anyway).

With `WINDOW = 400_000` the US per-window working set is ~12M candidate rows
≈ 150 MB + 190 MB ≈ 350 MB, and stage 8 drops from 4-6 GB to **~1.0-1.5 GB**.
Combined with `CHUNK=50000` upstream, the whole test path fits in roughly
**1.5 GB peak**, which pages comfortably given the 33 GB pagefile.

| 16 | `build_features.py trainT` | ditto |
| 17 | `build_features.py trainRest` | ditto |
| 19 | `crossfit.py all` | its 4 output models are already shipped |

That is **6 of 12 steps**, and they are precisely the 8-14 GB ones. It also
eliminates the need to convert or normalise **any** train source file, and the
need to touch `train_ground_truth.tsv` at all.

**Caveat to state in the methodology write-up:** the shipped models were fit
upstream on the full train set, so a submission produced this way is *not* a
fresh end-to-end reproduction on this machine. Honest framing: "we reproduce the
pipeline's inference half and reuse the reference release's trained weights;
`crossfit.py` is provided and runnable but was not re-executed on this
hardware." Either way, **run the shipped-model path first** — it is hours
cheaper and it de-risks the deadline.

### 5b. Stages that must still run (test-only)

```
convert.py (test_source1/2/3 only) -> run_blocking.py test
-> build_features.py test -> make_submission.py
```

    another copy.
* **Peak:** 4–6 GB (US is the peak country).
* **Threads:** `num_threads=2` at `:35` and `:57` — already correct.
* **OOM risk: HIGH.**
* **Mitigation:** stream `res` per part; and **push the per-country isolation
  one level further, to per-country x per-rid-window** (§6).

* **OOM risk: HIGH.**
* **Mitigation (highest leverage in the whole pipeline):**
  1. **`CHUNK = 600000 -> 50000`** (12x). Peak 2.5-4.0 GB → **250-400 MB**.
     Make it env-tunable: `CHUNK = int(os.environ.get("FEAT_CHUNK", 50000))`.
  2. `:75 B = 1_200_000 -> 200_000` (the rid-batch in `trainRest`).
  3. Train modes: never hold `cand`/`s1` whole — `scan_parquet` + filter to the
     chunk's `rid`/`s1` set.
  4. Test mode: additionally project `REC_COLS` only; drop `nfull`/`acity` after
     the rapidfuzz stage if still tight.
  5. **The whole stage is unnecessary** if you use the shipped models — §5.

  85:        _DICT = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
  ```
  The dictionary is loaded from the clone's `resources/` regardless of whether
  `learn_translit.py` ever ran. **Delete this step: 5 GB peak → 0, no
  behavioural change.**

### Stage 3 — `prep.py` (6 files)

* **Whole-file read?** **YES — worst offender.** `:22`
  `df = pl.read_parquet(inp)`. Then `:23-24` three `.to_list()` calls. `:25`
  builds `jobs` as a **full second materialisation** (Python list slices copy
  the list, and `.to_list()` already created every string). `:30` accumulates
  `parts` — **every output row of the whole file as Python objects** (8 new
  `str` per row: nfull, ncore, nalt, atoks, anums, state, pin, acity). For
  train_source3 that is 5.29M x 8 = 42M CPython strings ≈ 2.5 GB. `:32`
  `pl.concat([df, pl.concat(parts)])` doubles the resident set again.
* **Peak:** 3.5–4.5 GB for train_source3.
* **Chunked?** Nominally (`chunk=50000`) but results are **accumulated, not
  streamed** — effectively whole-file.
* **nproc default:** `:21 nproc=2`. On Windows `multiprocessing.Pool`
  **spawns** (not forks) — 2 workers = 2 extra interpreters (~120 MB each) and
  no copy-on-write sharing. On a 640 MB box **`nproc=2` is a net loss; use 1.**
* **OOM risk: HIGH.**
* **Mitigation:** (1) `nproc=1, chunk=5000`; (2) write each chunk's result
  immediately instead of appending to `parts`:
  ```python
  for i in range(0, df.height, chunk):   # or iterate parquet row groups
      r = _proc((names[i:i+chunk], addrs[i:i+chunk], cs[i:i+chunk]))
      pl.DataFrame(r, schema=...).write_parquet(f"{outp[:-8]}_{i:08d}.parquet")
  ```
  or use `pl.scan_parquet(inp).map_batches(...)` so the driver never holds the
  file. Peak → **300–450 MB**.

