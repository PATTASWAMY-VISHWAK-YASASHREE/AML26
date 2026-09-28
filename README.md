# AML26 — Amazon ML Challenge 2026 (Business Entity Resolution)

Out-of-core entity resolution for the Amazon ML Challenge 2026, plus the
research and audit work that shaped it.

Scored metric: **macro-averaged per-entity F0.5** over Source-1 entities.

---

## TL;DR — read this first

Two things about the official metric drive every design decision here.

`metrics.py:15-16` (upstream, byte-compatible with the brief):

| gold | pred | score |
|---|---|---|
| empty | empty | **1.0** |
| empty | non-empty | **0.0** |
| non-empty | — | `5·TP / (5·TP + 4·FP + FN)` |

1. **Abstaining on a true singleton is free — it scores a perfect 1.0.**
2. **One false merge on a true singleton scores a total 0.0.** Because the
   score is macro-averaged *per entity*, a false positive does not dilute the
   average, it **zeroes an entire entity**.

So over-prediction is catastrophically punished and under-prediction is
nearly free. Most entity-resolution models optimise pair accuracy and get
this exactly backwards. See `src/typed_decisions.py` for the
`MATCH / ABSTAIN / NO_CANDIDATE` decision layer built around it.

### F0.5 formula — do not "fix" this

`F0.5 = 5·TP / (5·TP + 4·FP + FN)`

**beta weights recall**, so the extra weight lands on FN, not FP. This is easy
to get backwards, and a review once told four separate files to change it to
`5·TP + FP + 4·FN`. That is the F2 formula and it is wrong. The brief's own
worked example settles it (TP=2, FP=1, FN=0 → stated **0.714**):

- shipped form `10/14` = **0.714** ✓
- "fixed" form `10/11` = 0.909 ✗
- `sklearn.fbeta_score(beta=0.5)` = 0.7143 ✓

`tests/test_f05_formula.py` pins all 36 cases against sklearn so this cannot
be broken again.

---

## Layout

| Path | What it is |
|---|---|
| `src/` | The pipeline. `er_pipeline.py` is the main deliverable. |
| `colab/` | Copy-paste Colab cells, including the single-cell build |
| `tests/` | 26 test modules (`test_*.py`) |
| `verify/` | 45 one-off verification scripts — every claim in the docs has one |
| `docs/` | Research, findings, checklists, the PDF report |
| `analysis/` | Fleet work orders, per-task findings, dataset profile |
| `patch/` | Upstream repo + the one code change proposed against it |
| `research/` | Earlier DuckDB audit work carried over from `amazon_ml_2026_research` |

## Running it

`colab/amazon_ml_colab_cell.py` is the single self-contained cell (embedded
pipeline, no upload needed). `colab/` also has a 6-cell split in
`colab/colab_cells/`, and `colab/colab_addon_cell.py` for the typed-decision
side-car and threshold sweep.

Locally:

```bash

## Hardware notes

- **A GPU does not help.** Every stage is CPU: DuckDB has no CUDA backend,
  and the scorer is scikit-learn on a 2% sample. The bottleneck is memory
  bandwidth and disk spill, not arithmetic.
- **The failure mode that matters is OOM, not speed.** The original death was
  `could not allocate block of size 256.0 KiB (5.5 GiB/5.5 GiB used)`.
- **Use a HIGH-RAM runtime, not a T4.** Verified on 2 vCPU / 12 GB.

If candidate generation OOMs, in this order: `max_candidates 10→5`, then
`max_token_df 1500→600`, then `memory_limit 6GB→4GB`. Leave `threads` alone,
then delete `duck.db` so the cache fingerprint changes.

---

## The three OOM fixes in `src/er_pipeline.py`

1. **All 7 blocking channels run as separate streaming `COPY`s**, not one
   giant `UNION ALL`. DuckDB previously had to hold every channel's join
   output simultaneously.
2. **Narrow projections.** The views were `SELECT *`, dragging token-list
   columns through 10M target rows per join. Each channel projects only what
   it uses.
3. **Spilling is enabled** (`max_temp_directory_size`). Without it DuckDB
   raises instead of writing to disk.

The per-channel early cap is **provably lossless** — priority is constant
within a channel, so anything surviving the final top-N is necessarily within
its own channel's top-N. `tests/test_candidate_equivalence.py` proves it
against a no-early-cap reference at caps of 5 / 30 / 1000 on data built to
force mass key collisions.

### Measured cap / recall trade-off

Real train data, 22,691 Source-1 entities, full 10M-row target corpus,
all 7 channels:

| cap | cands/S1 | gold recall |
|---|---|---|
| 5 | 4.89 | 0.4108 |
| 6 | 5.84 | 0.4279 |
| 8 | 7.74 | 0.4502 |
| **10** | **9.63** | **0.4652** |
| 15 | 14.31 | 0.4909 |
| 20 | 18.96 | 0.5081 |

Reproduce with `verify/probe_cap_recall.py`. **Note:** the brief says
`candidate_pairs.tsv` is *not* scored on the leaderboard — it is reviewed for
blocking quality. So shrinking it buys no leaderboard points, only ranking
credit, and must not be traded against `matching_results.tsv` score.

---

## Findings

Full detail in `docs/FRANCE_FINDINGS.md`. The headline is a set of
**retractions**:

| Original claim | Measured reality |
|---|---|
| France loses postal codes | False. France `dig5/row` = 0.004 vs US 0.110 — French addresses carry house numbers, not postcodes |
| `FR_REGIONS` too thin, no state signal | Partly false. All regions in the data resolve; the real gap is the *query* side |
| Pin asymmetry is country-based | Inverted. It is **source**-based (US s1 0.001 vs s2/s3 0.013) |

Every one of those came from reasoning about code instead of running it. The
rule the docs now hold themselves to: **a claim ships with the script that
produced it, or it does not ship.**

### What is real

- **Ligatures silently deleted.** `strip_accents()` uses NFKD, which does not
  decompose `œ/æ/ß`; the downstream `[^a-z0-9]+` regex then deletes the
  survivor. `Cœur`/`Fœur`/`Sœur` all collapse to token `ur`. 0.011% of France
  rows — a genuine false-merge vector, and the one code fix in `patch/`.
- **Two dead features.** `pin_eq` is 0.0% and `alt_tset` under 1% — the backing
  fields are almost never populated, so the features are constant.
- **Every France dictionary is already correct.** `FR_REGIONS`,
  `ADDR_CANON_FR`, `ADDR_CANON_COMMON`, `ADDR_GENERIC` — six separate audits,
  all "no change". Extending `FR_REGIONS` would *delete* live IDF feature mass.

### The opportunity that remains

**Top-3 French cities ≈ 43.7% of every French test file** (`bordeaux` 277k,
`nantes` 239k, `lille` 222k) and carry no administrative token. A
city→region table is the only change that would move France — and it cannot be
built from the current profile, because the profiler flattens address
components and keeps no co-occurrence data. **A component-level rescan is the
highest-value unstarted work.**

---

## Honest limitations

- **No full end-to-end run has completed on the 2.4 GB dataset.** Local RAM is
  ~0.95 GB. Every number here comes from the profile JSONs or from reduced
  runs, and is labelled as such.
- **`val_f05 = 0.986` in the upstream model JSON is not a trustworthy test
  estimate.** The validation set V is used three times: stage-1 early
  stopping, stage-2 threshold selection, and the reported score itself. It
  picks the boosting rounds, picks the threshold, then grades itself.
  Measured optimism from that single selection step is only **~2.4%**, so the
  real reason to distrust 0.986 is **distribution shift** — V contains only
  US and India, while the test set adds **France, a country with zero training
  rows**. The submission itself is unaffected; the threshold is applied to
  test. This is a reporting problem, not a correctness one.
- **The GPU is unused on purpose** (see Hardware notes).
- **The threshold sweep has never been run** — it needs real scores from a
  full run.

---

## Provenance

`patch/` is the upstream repo `PATTASWAMY-VISHWAK-YASASHREE/amazonsummerML`
with one proposed change (`test_leet_ordinal_guard.py`). Upstream is
copyrighted by its authors and is included here for reference with attribution.
The competition dataset is **not** redistributed — see `.gitignore`.

pip install -r requirements.txt
python src/er_pipeline.py /content
```
