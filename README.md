# AML26 — business entity resolution

Amazon ML Challenge 2026. Out-of-core entity resolution over 23M records
using DuckDB, with the research and audit trail behind it.

Scored metric: macro-averaged per-entity F0.5 over Source-1 entities.

## Read this first

The metric has two properties that drive every design decision here. Both come
from `metrics.py:15-18`:

| gold | pred | score |
|---|---|---|
| empty | empty | **1.0** |
| empty | non-empty | **0.0** |
| non-empty | — | `5·TP / (5·TP + 4·FP + FN)` |

**Abstaining on a true singleton earns a perfect 1.0.** **One false merge on a
true singleton scores 0.0** — and because the score is macro-averaged per
entity, that does not dilute the average, it zeroes a whole entity.

So over-prediction is punished hard and under-prediction is nearly free. Most
entity-resolution code optimises pair accuracy and gets this exactly backwards.
`src/typed_decisions.py` is the decision layer built around it, with a closed
`MATCH / ABSTAIN / NO_CANDIDATE` schema.

### The F0.5 formula

```
F0.5 = 5·TP / (5·TP + 4·FP + FN)
```

Beta weights **recall**, so the extra weight lands on FN, not FP. This is easy
to transpose by accident. A review once told four separate files to change it
to `5·TP + FP + 4·FN` — that is the F2 formula. The brief's own worked example
settles it (TP=2, FP=1, FN=0 → stated **0.714**):

- shipped form `10/14` = 0.714 ✓
- transposed form `10/11` = 0.909 ✗
- `sklearn.fbeta_score(beta=0.5)` = 0.7143 ✓

`tests/test_f05_formula.py` pins all 36 cases against sklearn so this cannot
be broken again.

## Run it

Colab, single cell, nothing to upload — the pipeline is embedded:

```
colab/amazon_ml_colab_cell.py
```

Split into six cells under `colab/colab_cells/` (see `00_RUN_ORDER.md`) if you
would rather paste less. `colab/colab_addon_cell.py` adds the typed-decision
side-car and the threshold sweep.

Locally:

```bash
pip install -r requirements.txt
python src/er_pipeline.py /content
```

## Hardware

**A GPU does not help here.** Every stage is CPU: DuckDB has no CUDA backend,
and the scorer is scikit-learn fitted on a 2% sample. The bottleneck is memory
bandwidth and disk spill.

The failure mode that matters is OOM, not slowness. The first death was
`could not allocate block of size 256.0 KiB (5.5 GiB/5.5 GiB used)`.

Use a HIGH-RAM runtime. Verified on 2 vCPU / 12 GB.

If candidate generation OOMs, change these in order:

1. `max_candidates` 10 → 5
2. `max_token_df` 1500 → 600
3. `memory_limit` 6GB → 4GB

Leave `threads` alone, then delete `duck.db` so the cache fingerprint changes.


## The three OOM fixes

In `src/er_pipeline.py`:

1. **Each blocking channel is its own streaming `COPY`.** Previously all seven
   were `UNION ALL`-ed into one query, so DuckDB held every channel's join
   output at once.
2. **Narrow projections.** The views were `SELECT *`, dragging token-list
   columns through 10M target rows per join. Each channel now projects only
   what it uses.
3. **Spilling is enabled** via `max_temp_directory_size`. Without it DuckDB
   raises instead of writing to disk.

Capping early per channel is provably lossless: priority is constant within a
channel, so anything surviving the final top-N is necessarily inside its own
channel's top-N. `tests/test_candidate_equivalence.py` checks this against a
no-early-cap reference at caps of 5 / 30 / 1000 on data built to force mass key
collisions.

### Measured cap / recall trade-off

22,691 train Source-1 entities, full 10M-row target corpus, all seven channels.
Reproduce with `verify/probe_cap_recall.py`.

| cap | cands/S1 | gold recall |
|---|---|---|
| 5 | 4.89 | 0.4108 |
| 6 | 5.84 | 0.4279 |
| 8 | 7.74 | 0.4502 |
| **10** | **9.63** | **0.4652** |
| 15 | 14.31 | 0.4909 |
| 20 | 18.96 | 0.5081 |

Candidate count falls roughly linearly; recall cost is real but sublinear. The
default is 10.

The brief states `candidate_pairs.tsv` is *not* scored on the leaderboard — it
is reviewed for blocking quality. Shrinking it buys no leaderboard points, so
do not trade it against `matching_results.tsv`.

## Findings

`docs/FRANCE_FINDINGS.md` has the full record. It opens with an index because
the body is append-only: the sequence of wrong turns is itself the evidence.

Four of my own claims were wrong and are retracted there:

| Claim | Reality |
|---|---|
| France loses postal codes | False. France `dig5/row` = 0.004 vs US 0.110 — French addresses carry house numbers |
| `FR_REGIONS` too thin | Partly false. Regions in the data all resolve; the real gap is the query side |
| Pin asymmetry is country-based | Inverted. It is source-based (US s1 0.001 vs s2/s3 0.013) |
| French function-word signal | Inflated ~37.5% and misdiagnosed |

All four came from reading code instead of running it. The rule the docs hold
themselves to now: a claim ships with the script that produced it, or it does
not ship.

What survived measurement:

- **Ligatures are silently deleted.** NFKD does not decompose `œ/æ/ß`, and the
  downstream `[^a-z0-9]+` regex deletes the survivor. `Cœur`, `Fœur` and
  `Sœur` all collapse to token `ur`. 0.011% of France rows.
- **Two dead features.** `pin_eq` fires on 0.0% of rows, `alt_tset` under 1%.
- **Every France dictionary is already correct.** Six audits of `FR_REGIONS`,
  `ADDR_CANON_FR`, `ADDR_CANON_COMMON` and `ADDR_GENERIC` all returned "no
  change". Completing `FR_REGIONS` would delete live IDF feature mass.

The gap that remains: the top three French cities are ~43.7% of every French
test file (`bordeaux` 277k, `nantes` 239k, `lille` 222k) and carry no
administrative token. A city→region table is the one change that would move
France, and it cannot be built from the current profile because the profiler
flattens address components and keeps no co-occurrence data.

`docs/ER_research_vs_upstream_report.pdf` compares this pipeline against the
upstream repo. Every finding in it was re-tested before publication; four of
eight were withdrawn or partly withdrawn, and the priority table was re-ranked
as a result.

## Layout

| Path | Contents |
|---|---|
| `src/` | The pipeline. `er_pipeline.py` is the main deliverable. |
| `colab/` | Colab cells, single-cell and split |
| `tests/` | 26 test modules |
| `verify/` | Verification scripts. Every documented claim has one. |
| `fleet/` | Roster and sidecar tooling for the analysis fleet |
| `analysis/` | Work orders, per-task findings, dataset profile |
| `docs/` | Research, findings, PDF report, checklists |
| `patch/` | Upstream repo plus one proposed change |
| `research/` | Earlier DuckDB audit work |

`python verify/repo_gate.py` checks that the required deliverables exist as
real non-empty files, that no dataset or log file is tracked, and that every
tracked `.py` and `.json` parses. It exists because a staging mistake once left
the repository with no pipeline in it at all while every other check passed.

## Limitations

- **No full end-to-end run has completed on the 2.4 GB dataset.** Local RAM is
  about 0.95 GB. Every number here comes from the profile JSONs or reduced runs.
- **`val_f05 = 0.986` in the upstream model JSON is not a test estimate.** The
  validation set V is used three times: stage-1 early stopping, stage-2
  threshold selection, and the reported score itself. Measured optimism from
  that single selection step is about 2.4%, so the real problem is
  distribution shift — V is US and India only, while test adds France, a
  country with zero training rows. The submission is unaffected; the reported
  number is.
- **The threshold sweep has never run.** It needs real scores from a full run.
- **The GPU is unused on purpose.**

## Provenance

`patch/` is the upstream repository
`PATTASWAMY-VISHWAK-YASASHREE/amazonsummerML` with one proposed change
(`test_leet_ordinal_guard.py`). It belongs to its authors and is included for
reference. The competition dataset is not redistributed.

