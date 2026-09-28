# Amazon ML Challenge 2026 — Verified Contract Addendum

This addendum incorporates the exact contract in the pasted 2026 brief.

## Authoritative output contract

### `matching_results.tsv`

- UTF-8 tab-separated file.
- Exact header: `source1_entity_id<TAB>matched_entity_ids`.
- Exactly one row for every `entity_id` in `test_source1.tsv`.
- Empty second field means a true-singleton prediction.
- IDs are comma-separated without quoting.
- No duplicate IDs within a list.
- Only S2/S3 IDs present in the test target files are allowed.

### `candidate_pairs.tsv`

- UTF-8 tab-separated file.
- Exact header: `source1_entity_id<TAB>candidate_entity_ids`.
- Exactly one row for every S1 test entity.
- Empty second field means blocking found no plausible candidate.
- This is the final candidate set fed to the matching model, not an earlier intermediate blocking list.
- Every final matched ID must appear in the corresponding candidate list.

The subset invariant is therefore mandatory:

`matched_entity_ids(S1-i) ⊆ candidate_entity_ids(S1-i)`

The candidate file is not leaderboard-scored, but it is used to audit blocking quality and reproducibility. A final match absent from the candidate file is a pipeline bug, even if the portal validator happens to accept the matching file.

## Official scoring semantics

The score is macro F0.5, computed per S1 entity and then averaged:

`F0.5 = (1.25 × Precision × Recall) / (0.25 × Precision + Recall)`

For each entity:

- true matches and predicted matches are compared as sets;
- no predicted links for a true singleton scores 1.0;
- any predicted link for a true singleton scores 0.0;
- one-to-many predictions are allowed;
- false positives are penalized more heavily than false negatives.

The implementation in `work/amazon_policy.py` follows these semantics directly.

## Data and fairness rules

- Input and output files are TSV, not CSV.
- Training countries are US and India; test includes France as an open-set label.
- Do not filter out France or hard-code a US/India-only model.
- Every French S1 test entity must still appear in both output files.
- External business lookup, geocoding, public registries, commercial ER APIs, and internet-derived augmentation are prohibited.
- The final model must be MIT/Apache 2.0 licensed and no larger than 8 billion parameters.

## Package contract

The final archive must contain:

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

The code must regenerate both output files from the provided data without network access. The methodology document must explain blocking, features/model design, and relevant validation decisions.

## Local validation status

Implemented and tested in the research workspace:

- exact TSV headers and empty-field serialization;
- every-S1-row requirement;
- S2/S3 target-prefix and existence checks;
- duplicate target-ID checks;
- final-match subset-of-candidates check;
- zero/one/many fixture;
- singleton scoring semantics;
- no one-to-one cap.

The test command used was:

```bash
python -m unittest amazon_ml_2026_research.work.test_amazon_contract amazon_ml_2026_research.work.test_amazon_policy amazon_ml_2026_research.work.test_fodors_benchmark amazon_ml_2026_research.work.test_policy_fixtures -v
```

Result: 14 tests passed.

A separate synthetic end-to-end contract smoke test also returned:

`PASS: synthetic zero/one/many contract fixture`

This is local contract validation, not a score. The actual Amazon data and official portal validator still need to be supplied before producing a real submission.
