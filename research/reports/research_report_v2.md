# Amazon ML Challenge 2026
## Research dossier and executable proxy-validation report

**Prepared:** 25 September 2026  
**Evidence boundary:** the Amazon training/test files were not available during this run. Results below are local contract tests and public-proxy diagnostics, not leaderboard scores.

## Executive decision

Build a deterministic two-stage entity-resolution system:

1. Validate the official TSV contract and preserve every ID as a string.
2. Canonicalize names and addresses without destroying raw values.
3. Generate S1→S2 and S1→S3 candidates with complementary blocking routes.
4. Freeze the final candidate manifest and hash it.
5. Score exactly the candidate manifest.
6. Choose zero, one, or many links per S1 entity using a precision-heavy policy.
7. Validate both output files, run reproducibility checks, and package the method.

The public Fodors–Zagats experiment makes the central point measurable: rare name-token blocking recovered 112/112 known positive pairs with 1,186 candidate rows. Exact name blocking recovered 83/112; exact address blocking recovered 39/112. The classifier cannot recover a positive pair that candidate generation discarded.

The Fodors pair models reached 1.000 pair F0.5 on the supplied test labels, but that number is not an Amazon estimate. The public split is sampled and not entity-isolated, so it is a plumbing and leakage diagnostic only.

## 1. Authoritative contract from the supplied brief

### Input files

All files are UTF-8 tab-separated values. Read them with an explicit tab delimiter; comma-separated parsing is incorrect.

Each source file contains:

- `entity_id`: unique ID whose prefix identifies S1, S2, or S3;
- `business_name`: potentially abbreviated, misspelled, transliterated, or reordered;
- `business_address`: potentially partial, reordered, landmark-based, or formatted differently;
- `country`: an open-set string label.

Training labels are in `train_ground_truth.tsv`:

- `source1_entity_id`;
- `matched_entity_ids`: comma-separated S2/S3 IDs, empty for a true singleton.

Training covers US and India. Test additionally contains France. Do not filter France, hard-code a two-country vocabulary, or omit French S1 rows.

### Required outputs

`matching_results.tsv` is the only leaderboard-scored file:

```text
source1_entity_id\tmatched_entity_ids
S1-00001\tS2-00047,S2-00193,S3-00812
S1-00002\tS3-00004
S1-00003\t
```

`candidate_pairs.tsv` contains the final candidate set fed to the model:

```text
source1_entity_id\tcandidate_entity_ids
S1-00001\tS2-00047,S2-00193,S3-00812,S3-00999
S1-00002\tS3-00004
S1-00003\t
```

Both files require exactly one row per test S1 entity. Empty second fields are valid. IDs in either list must be unique, must begin with `S2-` or `S3-`, and must exist in the relevant test target file.

The candidate file is not scored on the leaderboard, but it is audited. It must be the last set of pairs passed to the model, not an earlier intermediate block. The required invariant is:

`matched_entity_ids(S1-i) ⊆ candidate_entity_ids(S1-i)`

### Metric

The challenge computes macro F0.5 over S1 entities:

`F0.5 = (1.25 × Precision × Recall) / (0.25 × Precision + Recall)`

For each entity, truth and prediction are sets. A true singleton with an empty prediction scores 1.0. A true singleton with any predicted link scores 0.0. One-to-many predictions are valid.

### Package and fair play

The archive must contain:

```text
<team_name>_submission.zip
├── output/
│   ├── matching_results.tsv
│   └── candidate_pairs.tsv
├── code/
│   └── business_entity_resolution/
│       ├── src/
│       ├── README.md
│       └── requirements.txt
└── Documentation_template.md
```

The final model must be MIT/Apache 2.0 licensed and no larger than 8 billion parameters. External business lookup, commercial ER APIs, government registries, geocoding services, and internet-derived augmentation are prohibited. Public proxy data is for offline method validation only and must not enter Amazon training or submission artifacts.

## 2. Research synthesis

### Fellegi–Sunter and learned pair evidence

Fellegi and Sunter frame linkage as agreement/disagreement evidence across fields. The practical competition implementation is a supervised pair classifier, but its probabilities are intermediate evidence. The final decision must be optimized for entity-level set F0.5 rather than pair accuracy.

Source: Fellegi, I. P. and Sunter, A. B. (1969), “A Theory for Record Linkage”, Journal of the American Statistical Association. https://doi.org/10.1080/01621459.1969.10501049

### Blocking and retrieval

Blocking sets the recall ceiling. Exact keys are cheap but brittle. Rare-token postings improve recall; character n-grams tolerate spelling and punctuation changes. High-frequency tokens can explode candidate counts, so use frequency caps, rare-token routes, and per-route top-K quotas.

Magellan and DeepMatcher provide useful modular feature and benchmark patterns, but neither removes the need to measure the actual challenge candidate contract.

Sources:

- Magellan: https://sites.google.com/site/anhaidgroup/useful-stuff/the-magellan-data-repository
- DeepMatcher: https://github.com/anhaidgroup/deepmatcher
- DeepMatcher paper: https://doi.org/10.1145/3183713.3196926

### Neural and pretrained text methods

DeepMatcher and Ditto show that learned text representations can help. For a 72-hour offline challenge, start with deterministic lexical features, logistic regression, and shallow GBDT. Add a permitted encoder only if validation shows that lexical ranking is the remaining bottleneck.

Ditto: https://arxiv.org/abs/2004.00584

### Canonicalization and address parsing

Preserve raw fields and create separate normalized forms for Unicode/case, punctuation, sorted tokens, compact name, name core, address tokens, house number, street, locality, postal code, unit/floor, and country. Do not destructively replace the original strings. The brief explicitly expects legal suffixes, DBA/trade names, transliteration, missing components, landmarks, and reordered address fields.

FEBRL is useful for controlled corruption and missingness tests, not as Amazon training data: https://github.com/J535D165/FEBRL-fork-v0.4.2

### Approximate retrieval

MinHash/LSH, TF-IDF nearest neighbors, and HNSW are later-stage options. Use them only after exact/token/character routes show a measured recall gap or runtime problem. An approximate index that drops known positives is worse than a larger exact candidate set because no downstream model can recover an omitted pair.

## 3. Public proxy data

### Primary: Fodors–Zagats

The University of Mannheim CompERBench Fodors–Zagats restaurant dataset is the closest public proxy because it contains business names, addresses, cities, and pair labels.

URL: http://data.dws.informatik.uni-mannheim.de/benchmarkmatchingtasks/datasets/foZa.html

Local archive: `amazon_ml_2026_research/sources/fodors_zagats/records.zip`

Verified:

- 533 Fodors records;
- 331 Zagat records;
- 176,423 cross-table pairs;
- 112 known positives across the supplied files;
- 466 train, 134 validation, and 66 test pair rows;
- name, address, city, phone, and cuisine/type fields;
- archive size below 1 GB.

The supplied split is not entity-isolated: many source and target IDs appear in multiple files. Unlisted cross-table pairs are unknown, not automatically negative.

### Secondary proxies

Downloaded DeepMatcher/Magellan archives:

- Amazon-Google: 143 KB;
- DBLP-ACM: 263 KB;
- Walmart-Amazon: 984 KB;
- Dirty Walmart-Amazon: 0.98 MB.

They are useful for testing retrieval and pair-ranking code, but they are not structurally equivalent to the business/address/country challenge. They remain quarantined from Amazon artifacts.

## 4. Executable proxy results

### Blocking ablation

| Method | Known-positive recall | Candidate rows | Mean candidates/left |
|---|---:|---:|---:|
| Exact name | 74.11% | 84 | 0.16 |
| Exact address | 34.82% | 54 | 0.10 |
| Name OR exact address | 84.82% | 111 | 0.21 |
| Name token | 100.00% | 2,637 | 4.95 |
| Rare name token (df ≤ 20) | 100.00% | 1,186 | 2.23 |
| Rare address token (df ≤ 20) | 96.43% | 2,528 | 4.74 |
| Rare name OR rare address | 100.00% | 3,570 | 6.70 |
| Full name/address character grams | 100.00% | 79,868 | 149.85 |

These are retrieval recall measurements over the union of known positives in the three public label files, not a complete truth table.

### Pair-ranking diagnostic

Logistic regression and histogram gradient boosting were trained on the supplied Fodors train pairs, threshold-selected on validation, and evaluated on the supplied test pairs. Both reached 1.000 pair F0.5 on the 66-row test file. This is an optimistic diagnostic because the split is sampled and not entity-isolated. It is not evidence that the Amazon test score will be 1.0.

### Contract and policy tests

The local suite verifies:

- every S1 row is required;
- empty TSV fields serialize correctly;
- S2/S3 prefixes and target existence;
- duplicate target IDs are rejected;
- final matches are a subset of candidates;
- true singleton empty prediction scores 1.0;
- false singleton merge scores 0.0;
- one-to-many predictions are not capped.

Result: 14 tests passed. The synthetic end-to-end contract smoke test returned `PASS: synthetic zero/one/many contract fixture`.

## 5. Recommended implementation

```text
Raw TSV records
   ↓
Schema validation; preserve IDs as strings
   ↓
Raw-preserving canonicalization
   ↓
Independent S2/S3 blocking indexes
   ├─ exact normalized name
   ├─ sorted/core name
   ├─ rare name tokens
   ├─ character n-grams
   ├─ address tokens/postal/house number
   └─ bounded fallback
   ↓
Route-specific top-K + union + deterministic deduplication
   ↓
Freeze and hash candidate_pairs.tsv
   ↓
Batch pair scoring: lexical + address + learned model
   ↓
Calibration and S2/S3 threshold search
   ↓
Zero/one/many entity decision
   ↓
matching_results.tsv + independent validator + package
```

### Candidate routes

Start with:

1. exact normalized name;
2. sorted-token name;
3. name core after conservative legal-suffix handling;
4. rare name-token postings;
5. character trigrams;
6. exact normalized address;
7. address-token postings;
8. postal/PIN plus house number;
9. postal/PIN plus street;
10. a bounded name-only fallback.

Store route provenance for every candidate. Do not apply one global top-K blindly; use route-specific quotas and a global cap only after measuring recall.

### Pair features

Use name and address similarity separately:

- exact;
- ratio;
- token-sort;
- token-set;
- Jaccard;
- character trigram overlap;
- missing-field indicators;
- house-number/postal agreement;
- country equality and country-missingness;
- route indicators;
- candidate rank and score margin.

Train logistic regression and shallow GBDT first. Mine hard negatives from high-scoring nonmatches. Add a neural encoder only after measuring a remaining error gap.

### Entity policy

Score every candidate, then select candidates above a source-specific threshold. Preserve multiple links. Do not apply Hungarian assignment. Explicitly test the empty-list decision, because a false merge on a true singleton scores 0.0 while a correct empty list scores 1.0.

## 6. Validation design

### Entity-isolated holdout

Partition by S1 entity, not by individual pair. Carry all target links for held-out S1 entities into the held-out set. This prevents one entity’s links from leaking across train and validation.

### Retrieval metrics

Report:

- positive-pair recall;
- per-S1 full-hit recall;
- candidate count distribution;
- reduction ratio versus Cartesian pairs;
- recall by country;
- recall by truth cardinality: zero, one, many;
- recall by missing-field pattern.

### Model and policy metrics

Track pair precision, recall, F1, F0.5, average precision, calibration, per-entity F0.5, macro F0.5, singleton score, false-merge rate, and full-set exact match. Keep S2 and S3 results separate.

## 7. 72-hour plan

### Hours 0–6: contract and baseline

- Obtain the official sample and validator.
- Freeze schemas, headers, and ID rules.
- Parse TSV explicitly.
- Implement raw-preserving normalization.
- Run exact name/address baselines and record recall/runtime.

### Hours 6–18: high-recall blocking

- Add rare-token, n-gram, address, postal, and house-number routes.
- Keep route provenance.
- Measure recall by country, missingness, and cardinality.
- Select route quotas from the recall/candidate-count curve.

### Hours 18–32: pair ranking

- Train logistic regression and shallow GBDT.
- Mine hard negatives.
- Calibrate scores.
- Tune S2/S3 thresholds on entity-isolated validation.
- Inspect France-like and missing-field errors.

### Hours 32–48: policy and robustness

- Test zero/one/many behavior.
- Simulate unseen country labels.
- Test transliteration, punctuation, suffixes, unit/floor, and reordered addresses.
- Verify full-hit recall and candidate/output subset invariance.

### Hours 48–60: package

- Freeze candidate manifest and model.
- Regenerate outputs from a clean directory.
- Run official and independent validators.
- Check deterministic reruns, hashes, package contents, and no-network execution.

### Hours 60–72: buffer

- Fix only evidence-backed failures.
- Keep the last known-good outputs.
- Do not mix pre-freeze and post-freeze artifacts.

## 8. What not to do

- Do not force one-to-one assignment.
- Do not treat unknown cross-table pairs as negatives.
- Do not trust the Fodors fixed split as an independent entity score.
- Do not filter France or hard-code US/India.
- Do not use external registries, geocoders, ER APIs, or internet augmentation.
- Do not write an intermediate blocking list as `candidate_pairs.tsv`.
- Do not submit without every S1 row and the subset invariant.

## 9. Reproduction

From the project root:

```bash
python -m unittest amazon_ml_2026_research.work.test_amazon_contract amazon_ml_2026_research.work.test_amazon_policy amazon_ml_2026_research.work.test_fodors_benchmark amazon_ml_2026_research.work.test_policy_fixtures -v
python amazon_ml_2026_research/work/amazon_contract_smoke.py
python amazon_ml_2026_research/work/fodors_benchmark.py --data-root amazon_ml_2026_research/sources/fodors_zagats --out amazon_ml_2026_research/work/fodors_results.json
python amazon_ml_2026_research/work/fodors_ablations.py --data-root amazon_ml_2026_research/sources/fodors_zagats --out amazon_ml_2026_research/work/fodors_ablations.json
```

## 10. Source register

1. Fellegi, I. P.; Sunter, A. B. (1969). A Theory for Record Linkage. https://doi.org/10.1080/01621459.1969.10501049
2. Christen, P. (2012). Data Matching: Concepts and Techniques for Record Linkage, Entity Resolution, and Duplicate Detection. Springer. https://doi.org/10.1007/978-3-642-31164-2
3. Herzog, S.; Scheuren, F.; Winkler, W. (2007). The FEBRL Data Sets. https://archive.ub.uni-heidelberg.de/volltextserver/6389
4. Papadakis, G.; Christen, P. (2011). A Survey of Blocking and Filtering Techniques for Entity Resolution. https://dl.acm.org/doi/10.1145/1993636.1993743
5. Batela, D. (2020). A Practical Comparison of Blocking Methods for Entity Resolution. https://link.springer.com/article/10.1007/s41060-020-00183-3
6. Sanlavsky, Y.; Gal, A.; et al. (2022). Ditto. https://arxiv.org/abs/2004.00584
7. Mudgal, S.; et al. (2018). DeepMatcher. https://doi.org/10.1145/3183713.3196926
8. Magellan project and data repository. https://sites.google.com/site/anhaidgroup/useful-stuff/the-magellan-data-repository
9. FEBRL repository. https://github.com/J535D165/FEBRL-fork-v0.4.2
10. CompERBench Fodors–Zagats task and data. http://data.dws.informatik.uni-mannheim.de/benchmarkmatchingtasks/datasets/foZa.html
11. Amazon ML Challenge 2026 Unstop page. https://unstop.com/hackathons/amazon-ml-challenge-2026-amazon-1743604
12. Supplied brief: `C:/Users/pvish/Downloads/Emails Comms_ Amazon ML Challenge 2026.pdf`.

## Evidence boundary

The Amazon dataset was unavailable during this run. No Amazon predictions, official score, or final submission ZIP was produced. The verified outputs are local contract tests and public-proxy diagnostics.
