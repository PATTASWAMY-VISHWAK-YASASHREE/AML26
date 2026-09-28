# Implementation-oriented entity-resolution benchmark checklist

**Target:** small business-name/address linkage task with S1 queries linked to S2/S3 entity **sets**; empty-set/singleton queries matter; official score is macro per-S1 F0.5. The test country adds France, so a country-specific equality rule or source/ID-derived feature is unsafe.

**Purpose:** a fast, reproducible proxy benchmark before implementation on the hidden data. The checklist specifies candidate-generation and matching ablations, failure signals, and leakage tests. It is a benchmark design, not a claim that any method will win.

## 1. Use a small public proxy

### Primary proxy: Fodors–Zagats restaurants

Use the **CompERBench augmented version**:

- 533 Fodors query records and 331 Zagat target records.
- 112 positive and 554 negative labeled pairs across fixed train/validation/test files.
- Fields include name, address, city, phone, and type; map this to the challenge as:
  - `entity_id = subject_id`
  - `business_name = name`
  - `business_address = addr + ", " + city`
  - drop `phone` and `type`
  - add a constant placeholder `country = "US"` only to exercise the pipeline; do not infer generalization from this field.
- Download:
  - repository: https://data.dws.informatik.uni-mannheim.de/benchmarkmatchingtasks/
  - fixed gold: https://doi.org/10.3886/E127242V1
  - original CC0 package (533/331 records): https://doi.org/10.32614/CRAN.package.restaurant

Direct files:

```text
https://data.dws.informatik.uni-mannheim.de/benchmarkmatchingtasks/data/restaurants_%28Fodors-Zagats%29/records.zip
https://data.dws.informatik.uni-mannheim.de/benchmarkmatchingtasks/data/restaurants_%28Fodors-Zagats%29/gs_train.csv
https://data.dws.informatik.uni-mannheim.de/benchmarkmatchingtasks/data/restaurants_%28Fodors-Zagats%29/gs_val.csv
https://data.dws.informatik.uni-mannheim.de/benchmarkmatchingtasks/data/restaurants_%28Fodors-Zagats%29/gs_test.csv
```

The gold files contain **sampled pairs**, not a complete negative table. Therefore:

1. For a real end-to-end blocking test, reconstruct positive links from all 112 gold positives; every other cross-table pair is an **unknown**, not automatically a negative.
2. For supervised matching ablations only, use the official labeled subset (466/134/66 pairs) exactly.
3. Never interpret omitted candidate pairs as labeled negatives. DeepMatcher's public instructions explicitly describe candidate-only labeling and warn that reworked `tableA/tableB` files may not correspond directly to the original source tables: https://github.com/anhaidgroup/deepmatcher/blob/master/Datasets.md

The proxy is strictly one-to-one and has no country shift, so it cannot validate one-to-many or France generalization. Add the small synthetic policy tests in §7 rather than pretending the public benchmark covers them.

### Optional company-domain confirmation run

After the restaurant proxy, repeat only the frozen top two configurations on the 641-row open company ground truth (`name`, `country`, `state`, `registered_address`; 313 real, 328 spurious). It is a better business/domain sanity check, but its S1/S2/S3 and country structure differs from the target.

- Data/paper: https://doi.org/10.5281/zenodo.824192
- Paper: https://doi.org/10.3390/s19163446

Do not tune on both datasets and then report the best result as if it were an untouched test.

## 2. Freeze the evaluation contract first

Write these as executable tests before running any model:

```text
target_id[i] = sorted(set(candidate target IDs with score[i,j] >= threshold_i))
```

- The empty set is legal.
- Never force top-1, one prediction per source, or one target per query.
- A target may be selected by multiple S1 queries; do not apply global one-to-one assignment unless the official labels explicitly require it.
- Optimize exactly macro per-S1 F0.5, including true empty-set queries. Confirm the official singleton convention rather than assuming that “singleton” means “one target.” If predicting an empty list is required for a true singleton, encode that directly in the scorer.
- Keep secondary diagnostics: macro F1, precision, recall, predicted-set size distribution, and score by true-set-size bucket (0, 1, 2+).

Use nested, entity-isolated validation for learned components:

1. Build connected components from **all positive edges**; assign components, not pairs, to folds.
2. Outer folds estimate generalization.
3. Within each outer-train set, reserve a threshold/policy fold.
4. Fit normalization dictionaries, IDF, hard-negative models, classifiers, and calibrators using only outer-train records/pairs.
5. Fit the final decision threshold on the inner policy predictions, then apply it once to the untouched outer fold.

The CompERBench fixed pair split is useful for reproducing the supplied matching benchmark, but train/validation share many source and target records (verified: 56/67 validation source IDs occur in training and 66/67 target IDs occur in training). Do not call its accuracy an unseen-entity estimate.

## 3. Normalization ladder

Generate several representations instead of replacing raw text with one lossy canonical form.

| ID | Representation | Exact implementation |
|---|---|---|
| N0 | raw | original Unicode string |
| N1 | conservative | Unicode NFKC; `casefold`; map non-breaking spaces to space; collapse whitespace; preserve letters/digits; retain a separate accent-stripped view |
| N2 | compact | N1 tokens joined without separators; do not drop digits |
| N3 | name no-parenthetical | N1 after removing parenthesized/location qualifiers and generic trailing business words (`restaurant`, `cafe`, `hotel`, `bar`, `grill`, etc. only when learned or manually approved from train split) |
| N4 | name token-sorted | N1 name tokens sorted, repeated tokens retained |
| N5 | address parsed | parse leading house number, remaining street tokens, unit/floor marker and value, postal-like token, and city; preserve unknown fragments |
| N6 | country-agnostic abbreviation map | only a small train-fitted or manually approved map (`street/st`, `road/rd`, `avenue/ave`, `boulevard/blvd`); keep raw and parsed features |

Normalization is representation engineering, not evidence that two strings match. Cite and benchmark conservative Unicode/string handling rather than claiming a universally safe canonical form. String-similarity comparisons also show that metric behavior depends on field, length, and error type: https://people.csail.mit.edu/emax/public_html/papers/approximate-string-matching/iiweb03.pdf

**Never:** strip every non-ASCII character, drop all numbers, sort tokens before every edit-distance feature, infer gender/nationality from names, or invent France-specific expansions not supported by training data.

## 4. Candidate-generation implementations

Always report, for every blocker:

- positive-pair recall over all 112 known positives;
- recall by positive source and target;
- candidates/query median, p95, and max;
- fraction of queries with zero candidates;
- wall time and peak memory;
- the IDs of all missed positives.

### B0 — exhaustive oracle

Score all `533 * 331 = 176,423` cross pairs. This is mandatory on the proxy and is the fallback if the real data are still small enough to enumerate.

### B1 — exact keys

Create an inverted index and union pairs sharing any of:

```text
country_norm
N1_name_compact
N1_name_sorted
N1_address_compact
parsed house-number + first two alphabetic street tokens
N1 name rare token
N1 address rare token
```

Use token document frequency learned on the training corpus; remove only ubiquitous country/address tokens. A fixed `df <= 0.01*N` is a starting sweep, not a universal constant.

### B2 — character n-gram posting index

Index padded word-boundary character n-grams:

- names: `n=3`;
- address: `n=3` or `n=4`;
- separately test `n=2,3,4` on names and `n=3,4,5` on addresses;
- for each n-gram shared by a query and target, require a minimum count `c` such as `{1,2,3}`;
- use prefix filtering / length filtering if implemented and tested; do not assume it is recall-safe.

Character grams catch word reorder, punctuation, and transpositions. They are not a universal recall guarantee; every `n,c` pair must be scored against the complete positive set.

### B3 — MinHash/LSH

- Build MinHash on the same name/address n-gram sets.
- Sweep `num_perm={64,128,256}` and `(bands,rows)={(32,2),(64,2),(16,4),(32,4)}`.
- Keep exact Jaccard as the final candidate acceptance test; LSH is only the retrieval shortcut.
- On 864 records, compare against B2/exact retrieval and reject LSH unless it preserves the B2 positive recall within `0.002` while reducing work.

MinHash estimates set resemblance/containment and LSH groups similar keys, but approximation error is controlled by the representation and hash parameters: https://doi.org/10.1109/SEQUEN.1997.666900 and https://doi.org/10.1145/509907.509965.

### B4 — ANN/vector retrieval

- `Flat` exact cosine first.
- `IVFFlat` and `HNSW` only after exact cosine establishes the recall ceiling.
- Build a **joint corpus** of normalized name plus address; query each S1 against target records only.
- Sweep `k={20,50,100}` and, for HNSW, `ef_construction={100,200}` and `ef_search={50,100,200}`.
- Record candidate recall before any top-k cutoff.

Do not introduce ANN just because it is available. HNSW trades memory/build time for fast approximate search: https://doi.org/10.1109/TPAMI.2018.2889473. Exact `IndexFlatIP` is a better correctness baseline; FAISS distinguishes exact and approximate index families: https://github.com/facebookresearch/faiss/wiki/Faiss-indexes.

### B5 — deterministic edit-distance index (optional)

For very short normalized names, test a BK-tree or deletion-neighborhood index using Levenshtein threshold 1 or 2. It is not suitable for long, token-reordered addresses. Deletion neighborhoods and BK-trees are classic exact-radius retrieval constructions, but the proxy must reveal their cost/failure profile:

- https://doi.org/10.1145/2457317.2457387
- https://doi.org/10.1145/362003.362025

### B6 — sorted neighborhood (optional)

Generate variants that move the first token to the end and index on a shared rare token plus first three sorted compact characters. Test window `w={2,5,10}`. It is cheap but should be an additive channel; do not make it the sole recall path.

### Required blocker ablations

Run these exact deletions/additions from the same full-recall union:

1. `exact name only`
2. `exact address only`
3. `exact name OR address`
4. `+ rare name token`
5. `+ rare address token`
6. `+ name char-3 grams`
7. `+ address char-3 grams`
8. `+ MinHash union`
9. `+ vector exact top-50`
10. `+ vector exact top-100`
11. `+ HNSW top-100` (only if a corpus is large enough)
12. `+ sorted-neighborhood` (if implemented)

Promote no blocker that loses known positives. On the Fodors–Zagats proxy, the complete gold has 112 positives, so a single miss is already `0.991` positive-pair recall.

## 5. Pairwise feature matrix

Compute features only after candidate generation; retain B0 for feature ablations.

### Core lexical features, for name and address separately

1. exact equality after each applicable normalization variant;
2. length ratio and absolute length difference;
3. normalized Levenshtein similarity;
4. Damerau/OSA similarity;
5. Jaro and Jaro–Winkler with `prefix_weight in {0.0, 0.1}`;
6. token-set Jaccard;
7. token-sort Jaccard;
8. overlap coefficient `|A∩B| / min(|A|,|B|)`;
9. containment `|A∩B| / min(...)` only for short sets or as a diagnostic;
10. char-3 and char-4 gram Jaccard;
11. word TF-IDF cosine (`1,2` grams);
12. character TF-IDF cosine (`char_wb`, `2–4` or `3–5` grams);
13. longest common token and longest common substring fraction.

Do not manually count characters; use a tested implementation such as RapidFuzz. Jaro–Winkler is designed with a prefix bonus, so it is a weak standalone business-name metric: https://rapidfuzz.github.io/RapidFuzz/Usage/Distance/JaroWinkler.html and https://stat.cmu.edu/NCRN/PUBLIC/RLClassFiles/HW/Winkler1990.pdf. TF-IDF is a corpus-dependent weighting scheme, not a universal synonym model: https://stat.cmu.edu/NCRN/PUBLIC/RLClassFiles/HW/salton_termWeighting.pdf.

### Address-specific features

- parsed house-number equality and edit similarity;
- unit/floor marker and unit-number equality;
- postal-like token equality;
- street-token Jaccard after abbreviation normalization;
- directional-token equality/conflict;
- all-number-set Jaccard;
- conflict features: same house number but different street; same street but different house number; same building number but different unit;
- raw address similarity retained alongside parsed features.

A learned probabilistic address parser is not the first move for this tiny, four-field task. It becomes justified only if regular parsing demonstrably misses structured components and enough labels exist to train/validate it. Address parsing literature shows why components and hierarchical/order variation matter: https://doi.org/10.1145/2666310.2666471 and https://doi.org/10.1109/ICDMW.2016.0039.

### Cross-pair/context features

- source indicator (`S2` vs `S3`) only if enough pairs exist for both sources;
- same-country indicator, but **not** raw country equality as an always-on hard feature;
- query candidate count after retrieval;
- best, second-best, and best-minus-second margin among candidates;
- rank of pair under name-only, address-only, and combined similarity;
- target name/address frequency, but computed without validation labels.

## 6. Exact modeling and hard-negative ablations

### M0 — deterministic rule scorer

No training. Start with:

```text
score = 0.55*name_lexical + 0.35*address_lexical + 0.10*numeric/consistency
```

Sweep the three weights on a coarse grid (`0.55/0.35/0.10`, then each weight ±0.10 with the remainder split), but tune only the weights and threshold on the inner policy fold.

### M1 — logistic regression

- Standardize features.
- Class weights: compare `None` with `balanced`; do not assume balancing improves F0.5.
- Fit on official proxy train pairs; select probability threshold on validation **predictions**, never in-sample train scores.
- Use the entire threshold grid, including “predict empty.”

### M2 — gradient boosting

Start with deterministic LightGBM/CatBoost or scikit-learn histogram gradient boosting:

```text
learning_rate = 0.03
max_depth = 4
min_child_samples = 20
n_estimators = 300
subsample/colsample not used unless supported safely
l2_regularization = 1.0
random_state = 17
```

Then compare only one shallow alternative (`max_depth=2` or `num_leaves=7`) to detect overfit. Small proxy data cannot justify a large tree sweep. LightGBM's original paper motivates efficient histogram-based GBDT: https://proceedings.neurips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html

Feature-group ablations, each removing one block from the best M2:

1. remove exact/name features;
2. remove edit distances;
3. remove Jaccard/overlap;
4. remove TF-IDF;
5. remove parsed address features;
6. remove context/rank/margin features;
7. retain only name;
8. retain only address;
9. retain only name + address;
10. remove country/source;
11. add raw country/source back only to demonstrate shortcut risk.

### M3 — hard-negative mining

Use out-of-fold M1 scores only:

1. For each training S1 and source, retain top `K={5,10,20}` known negatives;
2. union with all positives and `K` sampled negatives across each S1;
3. deduplicate pairs;
4. train M2 on this union;
5. compare against all official labeled negatives and against random-negative-only sampling.

Expected signal: hard-negative training should improve false-positive rates among similar names/addresses. Failure signal: F0.5 or fold variance worsens because the miner over-focuses on one ambiguity family. Hard-negative selection can itself turn unknown or unobserved matches into false training negatives, so mine only from the official negative set. See the false-negative analysis: https://doi.org/10.1145/3511808.3557343.

### M4 — ranking add-on (only if M2 still struggles)

Add a small within-query rank feature from M2. Do not use a learned listwise ranker until the pairwise model is stable; RankNet's original formulation illustrates the extra objective complexity: https://doi.org/10.1145/1102351.1102363.

## 7. One-to-many and empty-set policy tests

The restaurant proxy is one-to-one, so create **policy-only synthetic fixtures** from its records; keep their outputs separate from reported proxy scores.

Create three deterministic cases:

1. **empty:** 20 S1 queries have truth `{}`;
2. **one-to-one:** 20 S1 queries each have one target;
3. **one-to-two:** 20 S1 queries each have the original target plus a deterministic variant of that target (case change, whitespace/punctuation, one abbreviation, or one character deletion; do not change house number).

For the one-to-two case, evaluate all four policies:

```text
top-1
top-k only for k=2,3,5
single global threshold
margin rule: select all >= tau, with optional second score >= tau2
```

Also test an S2/S3 collision: the two true targets for one S1 come from different sources. Expected good behavior is to keep both. A global one-to-one assignment or unconditional top-1 must visibly fail this fixture.

For every threshold/cap, report:

- macro F0.5 overall and per truth-size bucket;
- singleton precision/recall;
- count and precision of false links on empty queries;
- predicted-set size p50/p95/max;
- tie count at the threshold.

If the official singleton convention is not known, omit the actual singleton score and label this fixture “policy smoke test,” not a leaderboard estimate.

## 8. Calibration and precision-heavy threshold selection

Compare:

- **M0 raw score**;
- **M1/M2 raw score**;
- temperature scaling;
- Platt/logistic calibration;
- isotonic calibration only if the calibration split has enough positives; otherwise its flexible step function can overfit.

Primary and secondary calibration sources:

- Guo et al., temperature scaling: https://proceedings.mlr.press/v70/guo17a.html
- Kull et al., beta calibration: https://proceedings.mlr.press/v54/kull17a.html

Report Brier score and reliability curve, but select the operational operating point by macro per-S1 F0.5.

### Threshold procedure

1. Generate out-of-fold scores on the inner policy set.
2. Evaluate every unique score plus the `predict-empty` option.
3. Choose the threshold maximizing macro F0.5.
4. If two thresholds tie, choose the more conservative one only if its lower confidence bound remains within one bootstrap standard error; otherwise report the instability.
5. Recompute on outer folds; do not re-optimize on outer results.
6. If enough inner data, fit a source-specific threshold; otherwise use one threshold.
7. Avoid a hard `top-k` cap unless a one-to-two fixture and the real labeled data both justify it.

Threshold tuning is policy selection, not calibration. Thresholded F-measure is sensitive to the class/decision mix, which is another reason to avoid Platt/isotonic as a prerequisite for selecting a raw-score threshold: https://proceedings.mlr.press/v89/bascol19a.html.

## 9. France-shift smoke test without external lookups

The public proxy is US-only. Do not manufacture real French labels from outside data. Instead run two tests:

1. **Synthetic invariance test:** set proxy `country=""` on both sides. Any score that collapses has a hidden country hard dependency.
2. **Leave-one-country-out on the real training set:** hold out all France, or hold out the largest non-France country, then score the held-out country only. Because hidden test France cannot be inspected, freeze feature definitions and hyperparameters on non-France folds before the final run.

Additional rules:

- normalize country values with a fixed map, but never use an external registry or infer country from the address string;
- keep `same_country` as a feature, not a blocking hard condition;
- do not one-hot country and let a one-hot branch replace name/address evidence;
- for French-like stress inputs, add accent-preserving and accent-stripped views without deleting the original representation.

The leakage-safe evaluation literature argues that partitioning can create bias when data-generating processes are not aligned with evaluation data. Use a real country-held-out split, not random pairs, when testing the actual shift: https://doi.org/10.1038/s41467-025-58606-8.

## 10. Leakage traps and guard tests

| Trap | Guard |
|---|---|
| Random pair split repeats records | Split positive connected components; assert zero record/component overlap between outer train and test |
| Validation pairs are absent from gold and called negative | Keep an `unknown` state; label only supplied negatives |
| TF-IDF/IDF fit on all records before split | Fit vectorizer on each outer-train corpus only |
| Hard negatives mined from validation/test | Mine only from inner-training known negatives |
| Threshold picked on test or on the same scores used to report performance | Inner policy fold only; freeze before outer test |
| Training M2 then scoring it in-sample for the threshold | Use out-of-fold predictions for threshold/calibration |
| `country` or source hard block prevents France/cross-source matches | Never hard-block on country/source; report held-out-country recall |
| Source IDs, target IDs, pair IDs, row order, or class codes enter features | Exclude them; assert feature list has no ID/label-derived columns |
| Blocker tuned to 100% recall on the same 112 positives used to report performance | Treat blocker development as a labeled experiment; disclose it; use a second public dataset or component holdout before final claims |
| Gold connected component accidentally includes negative links | Build components from positive edges only |
| Global one-to-one assignment | Prohibited for the target metric; run the collision fixture |
| Hard cap chosen because proxy is one-to-one | Cap only if real one-to-many evidence supports it |
| External gazetteer/phone data smuggled in | Proxy uses only supplied fields; the challenge design uses no external lookup |
| Surrogate France labels built from web search | Not allowed; use only real held-out-country labels or synthetic policy tests |
| Metric implementation excludes empty/singletons | Unit-test scorer against hand-written 0/1/2-target examples |

## 11. Expected failure signals: stop or back off

- **Any positive-pair blocker miss:** add a channel; do not try to recover with a larger model.
- **Candidate recall high but final F0.5 drops:** inspect address conflict, threshold, or policy—not the blocker.
- **Exact normalized name/address collapses to zero candidates on the raw gold:** split orientation/source tables correctly and verify gold mapping; do not “fix” it with fuzzy thresholds.
- **MinHash/HNSW loses positive recall versus exact index:** keep exact posting/Flat retrieval; ANN is not earning complexity.
- **Fuzzy-only method has high positive recall but many false common-name links:** require address/numeric agreement and let the model learn the tradeoff.
- **Accent folding alone:** usually a recall aid, not a safe standalone match signal.
- **Address parser extracts the wrong number or unit:** compare raw and parsed branches; never overwrite raw address.
- **Country feature dominates importance or held-out-France recall collapses:** remove raw country one-hot/hard rules; re-run leave-country-out.
- **Hard-negative mining boosts precision but kills multi-positive recall:** reduce `K`, cap by ambiguity family, or include random negatives.
- **Calibration improves Brier but lowers F0.5:** calibration is wrong for the task; keep raw scores and tune the metric on the policy split.
- **Thresholds vary wildly across folds:** the small proxy is too noisy; prefer simpler M0/M1, stronger regularization, and report uncertainty.
- **A model beats rules only in-sample or on one seed:** reject it.

## 12. Ranked implementation ladder

Promote one rung only after the previous rung passes its guard.

1. **R0 — correct exhaustive oracle:** normalize, parse, score all pairs, hand-check positives, verify metric and output format.
2. **R1 — deterministic rules:** exact + Jaro–Winkler + Levenshtein + Jaccard + parsed-number consistency; global threshold optimized on policy data.
3. **R2 — high-recall blocking union:** exact inverted keys + rare tokens + character n-gram posting index; no ANN.
4. **R3 — sparse retrieval features:** word and char TF-IDF cosine, MinHash (if it preserves recall) and exact Flat top-k.
5. **R4 — logistic regression:** interpretable nonlinear threshold over the full lexical feature set.
6. **R5 — hard-negative logistic/GBDT:** out-of-fold mining, then shallow gradient boosting.
7. **R6 — calibrated policy:** temperature or Platt only if it helps held-out reliability; metric-optimized global/source threshold; retain multi-output decisions.
8. **R7 — scale-only ANN:** HNSW/IVF only if candidate enumeration is too large and measured recall matches exact retrieval.
9. **R8 — learned address parser or listwise ranker:** only after error analysis shows a persistent, sizeable residual failure mode.

For the hidden data, R0/R1 are safety anchors. R2 likely matters if the corpus is nontrivial. R4/R5 should be attempted only with clean entity-isolated folds and hard negatives. R7/R8 are not first moves.

## 13. One-page experiment log schema

For every run, append:

```yaml
run_id:
  proxy: fz_comperbench
  fold: component_fold_1
  normalization: N1+N5
  candidate_method: B2_name3_c1__address3_c2
  candidate_recall: 0.0
  median_candidates: 0
  p95_candidates: 0
  features: core_lexical_v1
  model: lgbm_shallow_v1
  hard_negative_k: 10
  calibration: none
  policy: global_threshold
  threshold: 0.0
  macro_f05: 0.0
  macro_f1: 0.0
  macro_precision: 0.0
  macro_recall: 0.0
  empty_query_false_link_rate: 0.0
  predicted_set_p95: 0
  seed: 17
  notes: ""
```

## 14. Minimum ablation set if time is short

Run exactly these, in order:

1. exhaustive exact rules;
2. rules + Jaro/Levenshtein;
3. rules + Jaccard;
4. rules + TF-IDF;
5. exact-key blocker;
6. exact + rare-token blocker;
7. exact + char-3 blocker;
8. add MinHash only if candidate count is material;
9. logistic regression;
10. shallow GBDT;
11. GBDT + top-10 hard negatives per query/source;
12. raw score vs temperature/Platt;
13. global threshold vs one-to-two policy fixture;
14. no-country-feature vs country-shortcut diagnostic.

Do not run a neural matcher, LLM, external gazetteer, or a large AutoML sweep on this proxy. The benchmark is too small; such steps increase selection variance without resolving the blocking, leakage, and one-to-many questions.

## Sources

- Blocking/indexing survey: https://doi.org/10.1145/3377455
- Data-indexing survey: https://doi.org/10.1109/TKDE.2011.127
- Broder MinHash/resemblance: https://doi.org/10.1109/SEQUEN.1997.666900
- Charikar similarity/LSH: https://doi.org/10.1145/509907.509965
- HNSW: https://doi.org/10.1109/TPAMI.2018.2889473
- Deletion neighborhoods: https://doi.org/10.1145/2457317.2457387
- BK-tree: https://doi.org/10.1145/362003.362025
- Jaro–Winkler: https://stat.cmu.edu/NCRN/PUBLIC/RLClassFiles/HW/Winkler1990.pdf
- String metric comparison: https://people.csail.mit.edu/emax/public_html/papers/approximate-string-matching/iiweb03.pdf
- TF-IDF: https://stat.cmu.edu/NCRN/PUBLIC/RLClassFiles/HW/salton_termWeighting.pdf
- Address parsing: https://doi.org/10.1145/2666310.2666471
- Address parser: https://doi.org/10.1109/ICDMW.2016.0039
- Hard-negative/false-negative risk: https://doi.org/10.1145/3511808.3557343
- Temperature calibration: https://proceedings.mlr.press/v70/guo17a.html
- Beta calibration: https://proceedings.mlr.press/v54/kull17a.html
- Thresholded F-measure: https://proceedings.mlr.press/v89/bascol19a.html
- LightGBM: https://proceedings.neurips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html
- Fodors–Zagats fixed proxy: https://doi.org/10.3886/E127242V1
- Original CC0 restaurant package: https://doi.org/10.32614/CRAN.package.restaurant
- Company ground truth: https://doi.org/10.5281/zenodo.824192
