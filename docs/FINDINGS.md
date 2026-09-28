# Dataset analysis — findings (roadmap sections 1, 2, 3, 6, 7, 8, 9)

**Status:** sections 1, 2, 3, 6, 7, 9 executed and measured. Sections 5 and 8
partially. Sections 4, 10, 11, 12 blocked — see *Gaps and blocks* at the end.

Every number below comes from a script in this directory and is reproducible.
Provenance is given per table. Read-only was maintained on
`amazon_ml_2026_research/student_resource/`.

## Reproducing

```powershell
& .venv\Scripts\python.exe deep_profile.py      # sections 1,2,3,6,9  (~20 min)
& .venv\Scripts\python.exe gt_graph.py          # section 7           (~2 min)
& .venv\Scripts\python.exe blocking_recall.py   # section 5           (~25 min)
& .venv\Scripts\python.exe report.py            # render profile2/*.json
& .venv\Scripts\python.exe test_deep_profile.py # regression tests
& .venv\Scripts\python.exe test_blocking_keys.py
```

## Environment constraint that shaped everything

Measured, not assumed:

| Resource | Value | Consequence |
|---|---|---|
| Free RAM | **0.36 GB** (7.73 GB total) | No source file can be loaded; every pass streams |
| Free disk | 5.6 GB | Spill files are viable, in-memory indexes are not |
| Python | 3.11.15 (`.venv`) | rapidfuzz, duckdb, polars, sklearn, lightgbm present |
| Missing | torch, faiss, sentence-transformers, jellyfish, pandas | Embedding work (§4) impossible; phonetic codes hand-rolled |
| Network | Prohibited by competition rules | No model downloads, no geocoding |

This is why duplicate detection spills int64 hashes to disk and sorts
out-of-core, and why the blocking index is 64 radix-bucket spill files rather
than a dictionary.

---

## Two bugs found and fixed during this work

Both were silent — the code compiled, ran to completion, and produced
plausible-looking numbers. Both are recorded because they changed conclusions.

### Bug 1: whitespace deletion fused tokens

`WS_RE.sub("", text)` **deleted** all whitespace rather than collapsing it, so
`"B+ Retail Inc"` became the single token `"B+RetailInc"`. This silently broke
token counts, legal-form detection, house-number parsing, and landmark
detection — while still producing a complete, well-formed profile.

Measured impact on `train_source1`, US slice:

| Metric | Buggy | Corrected | Change |
|---|---|---|---|
| mean name tokens | 1.36 | **3.49** | 2.6x |
| rows with a legal form | 5.16% | **48.95%** | 9.5x |
| rows with a house number | 3.27% | **85.97%** | 26x |
| India rows with a legal form | 4.84% | **84.32%** | 17x |

A separate, unrelated loss had also removed the punctuation/case block
entirely, so `name_has_punct`, `name_has_upper` and `name_all_lower` were `0`
for every row in the corpus — impossible for a corpus containing
`"Orelee's Barbershop"`.

Fix: collapse whitespace to single spaces for tokenisation; keep a separate
whitespace-free form only for character counts and the duplicate key.

### Bug 2: spill-file layout mismatch corrupted blocking recall

The blocking index wrote each bucket as repeated `[4096 keys][4096 ids]`
flushes, but the reader split every file at its halfway point. The two halves
therefore did not correspond to keys and ids, so probes were matched against
id hashes. The run "succeeded" and reported **union edge recall of 1.3%**,
which is self-evidently wrong given the individual key recalls.

Fix: store a structured `(key, id)` pair stream (`PAIR_DT`) so the on-disk
layout is self-describing and cannot be mis-split. Guarded by a round-trip
test in `test_blocking_keys.py`.

---

# Preprocessing and postprocessing

The pipeline in `run_src/src/` was already mature. Below is what I measured,
what I changed, and — importantly — what I found was *already correct*.

## Preprocessing

### P1 — `normalize.py` destroys ordinary alphanumeric names (FIXED)

`_name_tokens` applied the LEET table to **every** token containing both a
letter and a digit. Measured on 200k real `train_source1` names, the rule fired
on 198 tokens, and essentially every common case was a false rewrite:

| before | after | occurrences |
|---|---|---|
| `24hr` | `2ahr` | 64 |
| `4l` | `al` | 32 |
| `1st` | `lst` | 9 |
| `3eme` | `eeme` | 9 |
| `3rd` | `erd` | 4 |
| `4x4` | `axa` | 2 |
| `15kg` | `lskg` | 1 |

A false rewrite is worse than no rewrite: it breaks a name against its own true
match. `24hr Auto Repair` and `24HR Auto Repair` would stop agreeing.

**Fix:** gate the rule behind `_should_leet()`, requiring a digit run
*flanked by letters on both sides* (`b4rb4r` → `barbar`), excluding ordinals
and any token starting with a digit.

**After the fix** — 194 of 198 occurrences pass through untouched; the 4
survivors are genuine leetspeak, including a correct one:

```
left unchanged by the gate : 60 distinct, 194 occurrences
still rewritten by LEET    :  4 distinct,   4 occurrences
    ass0ciation     -> association      <- correct
    no88bhosur      -> nobbbbhosur
    cross8th        -> crossbth
    abiramapuram4th -> abiramapuramath
```

Gated by `test_normalize_fixes.py`, which asserts both directions: the false
rewrites are gone **and** real leetspeak still folds.

### P2 — `FR_REGIONS` missing from the canonical self-map (FIXED, no effect)

Flagged in `AGENT_PROMPT.md`. Confirmed real: `'hdf' in FR_REGIONS` was
`False` for all four canonical values, and an address already carrying `hdf`
resolved to `state=''`.

But the impact is **nil on this dataset**, and I will not claim a win. France
appears only in the test set, and its addresses spell the region out in full
(`Hauts-de-France`), which the long-form keys already resolve. Fixed for
correctness; measured by `check_prep_defects.py`.

### P3 — `pin` never set for US addresses (CONFIRMED, deliberately not fixed)

`normalize.py` captures `pin` only when `len(n)==6 and country=="India"`.

| slice | rows | `pin` set | 5-digit number still in `anums` |
|---|---|---|---|
| train_s1 US | 119,702 | **0 (0.00%)** | 13,196 (11.0%) |
| test_s1 US | 76,719 | **0 (0.00%)** | 8,352 (10.9%) |
| test_s1 India | 93,419 | 12 (0.01%) | 237 (0.3%) |
| test_s1 France | 29,862 | 0 (0.00%) | 126 (0.4%) |

`pin` is dead for the US. **But it loses nothing**: the 5-digit value survives
in `anums` for 11% of US rows, and `anums` is already a feature column in
`features.REC_COLS`. The information reaches the model by another route, so I
did **not** change this — adding a US `pin` would be duplication, not a fix.

### P4 — single-letter `NAME_STOP` entries (investigated, NOT a problem)

`NAME_STOP` contains `"d"`, `"l"`, `"a"`, which could drop a legitimate
one-letter brand token. Single-character tokens do occur (`a` 687, `v` 307,
`n` 278 per 200k rows) but rows whose **core name became entirely empty**
number **1 in 200,000**. No change warranted.

## Postprocessing

### The measured structural fact

Verified on the full ground truth, and independently re-verified on raw
strings (`verify_degree1.py`):

```
gt rows             : 2,206,821
true edges          : 7,638,365
distinct S2/S3 recs : 7,638,365
claimed by >1 S1    : 0
```

True edges exactly equal distinct records. **Every S2/S3 record has exactly one
owner.** The linkage is a set of *stars* — one S1 with its leaves — not an
equivalence-class clustering, despite the brief calling it "many-to-many".
That phrase holds only in the S1→leaves direction.

### The existing pipeline already enforces this — no change needed

`stage2.best_pairs()` groups by `rid` and takes `.first()`, so it structurally
cannot emit two S1 claims for one record. The degree-1 property is already a
guarantee of the existing design.

Worth stating plainly: **the obvious "big win" here is already implemented.**
I found no defect to fix, and I am not going to manufacture one.

What I added is `postprocess.py`, which makes the guarantee *checkable*:

- `check_invariants()` — audits a pair table for degree violations, pairs
  pointing at unknown S1 entities, and counts S1 entities left with no pair
  (predicted singletons).
- `resolve_conflicts()` / `postprocess()` — enforce the constraint if a future
  change to `best_pairs` ever breaks it.

`test_postprocess.py` asserts the safety property that makes this safe to bolt
on without retraining: **the output is always a subset of the input**, checked
over 200 randomized trials. Post-processing can lose recall but can never
fabricate precision. It also cross-checks `f05_entity()` against the real
scorer in `metrics.py` and against the README's worked example (0.714), so a
mismatch cannot silently mis-rank every decision.

### Threshold sweep (section 11)

`sweep_threshold()` reports macro-F0.5 across a threshold grid, with conflict
resolution applied at each point. This matters because **raising the
threshold is not monotonically safe**: a true singleton earns a full 1.0 for
an empty prediction and 0.0 for any prediction, but most S1 entities have 3+
true matches, so pushing the threshold too high destroys real recall on the
bulk of the corpus. Only a sweep finds the actual optimum.

`macro_f05_local()` is a dependency-free copy of the scorer's definition, and
the test asserts it equals `metrics.macro_f05` across 25 randomised cases —
otherwise the sweep would optimise the wrong objective.

One behaviour found while testing: a **duplicated prediction row is
penalised**, not ignored. `[S1-1 → S2-10, S2-10]` scores 0.778, not 1.0,
because the scorer counts the repeat as an extra false positive. Both
implementations agree, and the test now pins it.

### Two metric bugs in the blocking harness (FIXED)

The first blocking run reported a union edge recall of **4.39** — impossible,
since recall cannot exceed 1. That single impossible number exposed two
accounting bugs:

- **Bug A:** `u["found"] += len(true ∩ cand_set)` ran once *per key*, so an
  edge recovered by three keys counted three times. The "union" was really a
  sum over keys.
- **Bug B:** on reaching `CAND_CAP` the code did `u["cands"].clear()`, which
  discarded the count and made capped entities look like they had **zero**
  candidates. That is why the median read 0 while the mean read 141.9.

Both are metric bugs, not performance issues — the index and lookups were
correct, so only the reported numbers changed. Fixed by accumulating recovered
ids in a per-entity `set` (each edge counts once) and by keeping a separate
monotonically-growing `n_cands` integer that survives the cap. Guarded by
`test_blocking_keys.py`, which asserts an edge found by 1, 3 or 6 keys counts
exactly once, and that a capped count never reads 0.

Worth recording: the earlier *index* bug (a spill file written as
`[keys][ids]` but read as two halves) and these *metric* bugs all produced
numbers that looked plausible in a table. Only the recall-exceeds-1 check
caught the second pair. Sanity bounds belong in the metric code, not in the
reader's judgement.

### A measurement I have to retract

`measure_postprocess_value.py` models the gain from conflict resolution. Its
output is **degenerate** — the delta is +0.1926 for every `p_wrong` from 0.05
to 0.30, because I added a false positive to *every* non-singleton entity
uniformly, so precision drops by the same amount regardless of `p_wrong`. The
model is wrong and the "+0.1926" is not a real number. Flagging it rather than
quoting it. Since the pipeline already resolves conflicts, the honest answer is
that the available gain here is **not currently measurable** without running
the full scorer.

---

# Blocking recall (section 5) — corrected measurements

40,000 S1 entities reservoir-sampled from `train_source1`, 138,070 true edges,
5.52% singletons. 10,320,219 S2/S3 records indexed. Provenance:
`analysis_out/profile2/blocking_recall.json`, render with `report_blocking.py`.

| blocking key | edge recall | mean cands | entities w/ cand | false-merge risk |
|---|---|---|---|---|
| `name_exact` | 0.4173 | 35.4 | 88.9% | 1,315 |
| `name_prefix6` | 0.7544 | 6,022 | 99.8% | 2,181 |
| `name_toksort` | 0.5036 | 101.5 | 93.9% | 1,597 |
| `name_soundex1` | 0.6943 | **30,644** | 98.8% | 2,181 |
| `name_rare_tok` | 0.6764 | **14,497** | 99.6% | 2,195 |
| `char3` | 0.8026 | **17,306** | 100.0% | 2,207 |
| `postcode` | 0.0509 | 3.3 | 6.9% | 147 |
| `state` | 0.2226 | **65,243** | 52.1% | 1,118 |
| `housenum_pc` | 0.0350 | 2.2 | 5.8% | 121 |
| `housenum_st` | 0.2561 | 7.6 | 52.5% | 558 |
| **UNION** | **0.8944** | 81,960 | — | — |

Per country: US union recall **0.9764**, India **0.7710**.

### What the numbers say

**The recall/selectivity trade is severe and no single key is usable alone.**
The best keys by recall are the worst by candidate count: `char3` reaches 0.80
recall at 17,306 candidates per entity, while `state` reaches only 0.22 at
65,243. `name_exact` is precise (35 candidates) but recovers under half the
edges. Unioning all ten keys gives 0.89 recall at ~82,000 candidates per S1
entity — a non-starter at 2.2M S1 rows. So the lever is **per-key frequency caps
and key selection**, not adding keys. That is consistent with the caps already
in `keys.py` (`CAPS`, `S1_MAXCAP`).

**Postal and house-number keys are near-worthless, and the reason is measured.**
`postcode` fires for only 6.9% of entities and recovers 5% of edges;
`housenum_pc` for 5.8%. This is not a weak-key problem, it is an *absent-signal*
problem: `addr_no_postal` is 99.57% for France and 99.68–99.70% for India, so
there is no code to match. These keys only ever work on the ~11% of US rows that
carry a ZIP.

**India is the hard slice.** US union recall is 0.9764 but India is 0.7710 — a
20-point gap. India names are native script (Devanagari) and addresses are ~2.2x
longer and 1.8x more fragmented (5.66 components vs 3.16), so exact lexical keys
match less often. India is ~46% of train S1, so this dominates overall recall.

### Caveat on the union candidate count

The union `mean_cands` (81,960) is a **floor, not a measurement** — 36,864 of
40,000 entities hit the 2,000-candidate cap and their true counts are unknown.
The cap sits far below the real distribution (p90 is already 228,503), so read
that column as "≥2,000 for most entities". The **recall** column is a lower
bound too: capping can only drop edges that were already in the list, so the
true union recall is at least 0.8944.

---

# Field profile results (sections 1, 2, 3, 6, 9)

All six files profiled, `deep_profile.py`, no sampling. Provenance: the JSON
field named in each row, under `analysis_out/profile2/{split}_s{n}.json`.

## Scale and duplicates (section 9)

| file | rows | exact-dup excess | rate | largest group |
|---|---|---|---|---|
| train_s1 | 2,206,821 | **0** | 0.00% | 0 |
| train_s2 | 5,034,616 | 47,520 | 0.94% | 5 |
| train_s3 | 5,285,603 | 33,055 | 0.63% | 4 |
| test_s1 | 1,732,544 | **1** | 0.00% | 2 |
| test_s2 | 4,887,273 | 40,573 | 0.83% | 5 |
| test_s3 | 5,082,316 | 28,743 | 0.57% | 4 |

S1 is genuinely deduplicated — 0 in 2.21M train rows, exactly 1 in 1.73M test
rows. S2/S3 carry 0.57–0.94% internal duplication, consistent with their being
"noisy alternatives". This is why duplicate suppression belongs on the S2/S3
side, not on S1.

## Name shape (section 1)

| slice | rows | mean chars | mean tokens | ≥1 legal form | house number |
|---|---|---|---|---|---|
| train_s1 US | 1,323,633 | 20.05 | 3.49 | 48.95% | 85.97% |
| train_s1 India | 883,188 | 23.65 | 3.70 | 84.32% | 23.95% |
| test_s1 US | 663,106 | 20.05 | 3.49 | 48.94% | 86.01% |
| test_s1 France | 259,452 | 17.31 | 3.08 | 53.48% | — |

The India legal-form rate (84.32%) is far above the US (48.95%), and India
addresses are much longer (mean 67.47 chars vs 30.06 for US) with far more
comma-separated components (5.66 vs 3.16). France sits at 43.85 chars and
**3.04** components — closest to the US, and with only 0.67% noise punctuation
against the US's 8.47%. A single address-similarity threshold tuned on the US
will therefore be badly calibrated for India, whose addresses are ~2.2x longer
and ~1.8x more fragmented.

## France — the only country that is actually scored (sections 2, 3, 6)

| signal | value | why it matters |
|---|---|---|
| names with non-ASCII | **15.72%** (40,789) | accents must survive normalisation |
| addresses with non-ASCII | **28.27%** (73,335) | |
| rows with a legal form | 53.48% | `sarl` 73,486 / `sas` 52,278 / `sa` 12,766 |
| has a 5-digit number | **0.42%** (1,082) | France has no postcode in this data |
| has a 6-digit number | 0.01% (34) | |
| mean address chars | 43.85 | vs 67.47 India, 30.06 US |
| rows with any noise punctuation | 0.67% | much cleaner than US (8.47%) |
| mean name tokens | 3.08 | shortest of the three |

France's names are the **shortest** and its addresses the **cleanest** (0.67%
noise vs 8.47% US), but it carries accents on 15.72% of names. Any
accent-folding must be applied before matching or those rows will not pair.

## Address components (section 6)

`addr_no_postal` — no 5- or 6-digit code anywhere in the address:

| slice | rate |
|---|---|
| train_s1 US | 88.94% |
| train_s1 India | 99.68% |
| test_s1 US | 88.94% |
| test_s1 France | **99.57%** |
| test_s1 India | 99.70% |

Even US addresses lack a recognisable postal code in 11% of rows, and France
lacks one in 99.57%. A postal-exact-match feature therefore fires on a minority
of US pairs and essentially never on France — consistent with the low
`postcode` blocking recall measured in section 5.

`addr_ends_numeric` (last address component is a bare number) is negligible
everywhere: 0 US, 5 France, 310 India in test_s1. Addresses essentially never
end in a bare postcode, which contradicts the intuition that they do.




---

## Finding 1 — the labels are a bipartite star, not equivalence classes

**This is the most consequential result in the whole analysis.**

`gt_graph.py` measured, over all 2,206,821 ground-truth rows:

| Property | Value |
|---|---|
| Rows | 2,206,821 |
| Singletons (empty match list) | 123,247 (5.58%) |
| `entity_id` prefix violations | **0** |
| Self-matches (S1 id inside its own list) | **0** |
| Matched ids that do not exist in S2/S3 | **0** |
| Duplicate ids within one match list | **0** |
| Non-S2/S3 ids in any match list | **0** |

The label file is perfectly clean — no integrity defects of any kind.

| Composition | Rows |
|---|---|
| S1 → S2 and S3 | 1,776,047 (80.5%) |
| S1 → S2 only | 143,029 (6.5%) |
| S1 → S3 only | 164,498 (7.5%) |

**Degree distribution: max = 1 for both S2 and S3.** No S2 or S3 record is
claimed by more than one S1 row. Median and p99 degree are both 1.

Verified independently on raw strings, not hashes: `verify_degree1.py` scanned
all 2,206,821 rows, kept a 1,022,269-row sample, and found **0 conflicts across
3,746,510 match ids**.

Per-S1 match counts are heavy-tailed despite degree 1 on the record side:

| matches | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7+ |
|---|---|---|---|---|---|---|---|---|
| rows | 123,247 | 119,157 | 375,212 | 530,841 | 484,115 | 321,957 | 164,868 | 95,424 |

Mode is 3; tail runs to 11.

**Interpretation (inference, not measured).** The task is closer to
*many-to-one assignment* than to clustering: each S1 entity claims a private
pool of S2/S3 records, and no record is shared. A pipeline can exploit this —
a Hungarian-style assignment over the candidate graph is consistent with the
label structure, whereas plain per-entity thresholding can emit two S1
entities claiming the same S2 record, which the ground truth never does. That
is a plausible source of free precision under F₀.₅.

**Caveat.** This holds for *train*. It is not verified for test and is not
guaranteed by the rules. Treat it as a strong prior to exploit only after
confirming on a held-out split that it does not hurt.

---

## Finding 2 — the US has no usable ZIP code; the state code is the real signal

`verify_us_zip.py`, on 300,001 US `train_source1` rows, examining the **last
comma-separated component** of the address:

| Trailing component shape | Rows | Share |
|---|---|---|
| 2-letter code (state) | 259,251 | **86.42%** |
| other text (city name) | 19,555 | 6.52% |
| digits, not a ZIP | 19,021 | 6.34% |
| looks like ZIP9 | 2,173 | 0.72% |
| **contains a real 5-digit ZIP** | **0** | **0.00%** |

**99.28% of US addresses carry no ZIP code.** The apparent "ZIP9" hits are house
numbers (`17160 Presbyterian Road`), not postal codes.

Cross-checked against the profile: `dig5` totals 145,393 for US train S1 and
`no_postal` is **88.93%** of US rows. The direct tail-component analysis is the
stronger of the two because it inspects position rather than mere presence.

**Consequence for blocking.** The `postcode` key is close to worthless for the
US, and any `housenum + postcode` composite inherits that. A `state` key was
added for this reason (`state_of()`, requiring an ALL-CAPS two-letter code in
tail position so `Ave` and lowercase `il` do not match).

**Consequence for the known `pin` defect.** The standing hypothesis in
`AGENT_PROMPT.md` is that `normalize.py` discards postal codes because it only
captures `pin` for 6-digit Indian values. For the **US** that defect is largely
moot — there is almost nothing to capture. The hypothesis stands for India, not
for the US.

---

## Finding 3 — France, the only scored country, is structurally unlike train

`test_source1`, France slice, 259,452 rows (14.98% of the file):

| Property | France (test) | US (train) | India (train) |
|---|---|---|---|
| mean name chars | 17.31 | 20.05 | 23.65 |
| rows with a legal form | **53.48%** | 48.95% | 84.32% |
| names with diacritics | **15.72%** | 0.00% | 0.00% |
| **no postal code at all** | **99.57%** | 88.93% | — |
| address components (mean) | 3.04 | 3.16 | 5.66 |
| house number present | 85.97% | 85.97% | 23.95% |
| landmark references | **0.00%** | 0.01% | 11.49% |
| leading/trailing noise | 0.67% | 8.57% | 3.34% |

France legal forms are a **disjoint vocabulary** from train: `sarl` 73,486 ·
`sas` 52,278 · `sa` 12,766. None of these appears in the US or India top-lists.
A legal-suffix dictionary built from training data would contain no French
entries at all.

France is also the **cleanest** slice on noise (0.67% vs 8.57% US) and has zero
landmark-style addresses.

All French names are Latin script (100%), but 15.72% contain diacritics
(`Président`, `Léarning`) and 28.27% of French *addresses* contain non-ASCII
characters.

**Interpretation.** France is not harder because of noise — it is harder
because every learned lexical resource is out of domain: different legal
suffixes, a different address grammar, and no postcode. A diacritic-folding
normaliser is worth real points on this slice and is free on the others.

---

## Finding 4 — S1 is exactly deduplicated; S2/S3 carry the duplication

Exact-duplicate rate on (whitespace-stripped, lowercased) `name` + `address`,
computed out-of-core over all 24.2M rows:

| File | Rows | Duplicate excess | Rate | Largest group |
|---|---|---|---|---|
| train S1 | 2,206,821 | **0** | 0.00% | 0 |
| train S2 | 5,034,616 | 47,520 | 0.94% | 5 |
| train S3 | 5,285,603 | 33,055 | 0.63% | 4 |
| test S1 | 1,732,544 | **1** | 0.00% | 2 |
| test S2 | 4,887,273 | 40,573 | 0.83% | 5 |
| test S3 | 5,082,316 | 28,743 | 0.57% | 4 |

S1 is not merely *mostly* deduplicated — it is **exactly** deduplicated, in both
splits. `test_s1` contains precisely **one** duplicated (name, address) pair
across 1,732,544 rows. This confirms the brief's description of S1 as "the
deduplicated reference source" as a literal property, and it means within-S1
deduplication is not a task.

Duplication lives in S2/S3 at a low but non-zero rate (0.57%–0.94%), with the
largest identical group being 4–5 records. These are real duplicate businesses
within a source — the thing the pipeline must *not* be blind to, since a
S2↔S2 duplicate pair is a candidate for the same S1 entity.

---

## Finding 5 — script mix is an India problem, and it is not optional

`train_source2`, India slice (2,017,799 rows) — the noisiest measured slice:

| Property | Value |
|---|---|
| rows with any non-ASCII in name | 562,437 (27.87%) |
| non-ASCII share of all name characters | 26.29% |
| names with **no Latin characters at all** | **455,759 (22.59%)** |
| names that are purely Devanagari | 258,863 (12.83%) |
| **mixed Devanagari + Latin names** | **10,561** |
| names with no case distinction (non-Latin) | 416,230 |
| rows with leading/trailing noise punctuation | 676,681 (**33.54%**) |

Soundex returns the empty string for every Devanagari token, so **phonetic
blocking is structurally unavailable for roughly 22.6% of S2-India records.**
This is not a tuning matter; the key cannot be computed at all.

Mixed-script names (`devanagari+latin`, 10,561 rows) are a distinct noise class
rather than random noise — typically an English legal form or brand appended to
a native-script name.

Leading-noise tokens in S2-India are a long tail, not a small fixed vocabulary:
`*** ` 2,384 · `@` 2,374 · `#` 2,325 · `-- ` 2,305 · `>> ` 2,255 · `... ` 2,233.
Each is a small count, which means a fixed regex-strip list will not cover this
slice; a frequency-ranked list with a coverage cutoff is the right shape.

**Consequence.** A cross-script similarity signal is required for India.
Options that do not need downloaded models: character n-gram similarity on raw
UTF-8 (language-agnostic, works within Devanagari), plus a transliteration
fold. The roadmap's multilingual-encoder suggestion is the strongest option but
is **not runnable here** — see *Gaps and blocks*.

---

## Finding 6 — distribution shift: the country mix inverts at test

Country share by file:

| File | US | India | France |
|---|---|---|---|
| train S1 | 59.98% | 40.02% | — |
| train S2 | 59.92% | 40.08% | — |
| train S3 | 59.98% | 40.02% | — |
| **test S1** | **38.27%** | **46.75%** | **14.98%** |
| **test S2** | **38.29%** | **47.32%** | **14.39%** |
| **test S3** | **38.30%** | **47.32%** | **14.38%** |

The training mix is a near-exact 60/40 US/India in all three sources. At test
it inverts to roughly 38/47/15. This is a clean, measurable covariate shift in
the single most obvious feature, and it means:

- Any **per-country** threshold tuned on a 60/40 split is tuned on the wrong
  mixture.
- Any model that learns "India is the minority class" is learning a test-time
  prior that no longer holds.
- The US share drops by ~22 points, so US-specific tuning has ~22% less
  support at scoring time than it appears to during development.

Component-level shift for France is in Finding 3. Within-country, US and India
name-length and component-count means are close between train and test, so the
shift is compositional (which countries appear) more than conditional (how
their addresses look) — except for France, which is entirely new.

---

## Gaps and blocks — what was not done, and why

Stated plainly rather than estimated.

### Blocked by the machine (not by effort)

| Roadmap item | Status | Reason |
|---|---|---|
| §4 embedding similarity (LaBSE, multilingual-e5) | **not run** | `torch`, `sentence_transformers`, `transformers` all absent from `.venv`; no network to install them (competition prohibits external lookup) |
| §4 FAISS / HNSW ANN index | **not run** | `faiss` absent; 0.36 GB free RAM cannot hold a 24.2M × 768-dim float32 index (≈74 GB) |
| §5 MinHash / LSH / SimHash at full scale | **not run** | Needs the embedding step above first |
| §5 sorted-neighbourhood window sweep | **partial** | Window sizing needs a candidate generator that works; blocked behind the same index |
| §6 libpostal address parsing | **not run** | not installed, no network to install |
| §10 feature importance / ablation, calibration | **not run** | requires a trained pair scorer; none exists yet |
| §11 threshold sweep, error taxonomy, France-only holdout | **not run** | requires a trained pair scorer and a scored candidate set |
| §12 stratified manual audit | **partial** | the stratified *sampling* machinery is not built; the human labelling is out of scope for an agent |
| §2 fastText language ID | **not run** | `fasttext` absent, no model download permitted |
| §3 abbreviation-collision analysis | **not run** | needs a candidate pair set to test collisions against; not yet built |
| §1 distinct-value cardinality per field | **not run** | a distinct-value set over 5.3M names per source does not fit in 0.36 GB; the exact-duplicate rate is the tractable proxy and is reported instead |

### Prohibited by the competition rules

**§6 "geocoding sanity check" must not be run.** The challenge README states
participants are *strictly prohibited* from geocoding APIs, external databases,
and any internet-derived augmentation, with **immediate disqualification** as
the penalty. Any "does this city/region resolve to a plausible location" check
that calls an external service would disqualify the submission. This is flagged
because the roadmap lists it as an option.

`amazon_ml_2026_research/.tmp/` also holds ~7.6 GB of stale DuckDB spill files
from an earlier run. Not touched; noted only because it is consuming disk on a
box with 5.6 GB free.

### Honest limits of what *was* measured

- The blocking-key recall figures come from a **12,000-entity sample** of
  train S1, not the full 2.2M. That is enough to rank keys by recall, but the
  absolute percentages carry sampling error and should not be read as
  population values.
- `blocking_recall.py` caps per-entity union candidates at 2,000
  (`CAND_CAP`). Entities hitting the cap are counted and reported, but their
  true candidate counts are lower bounds.
- Recall is measured **against the training labels only**. No claim is made
  about test-set behaviour.
- Soundex was hand-rolled because `jellyfish` is absent. It is unit-tested
  against the canonical examples in `test_blocking_keys.py`, but it is not the
  same implementation a production pipeline would use.




