# D093 - Mine evidence to extend `ADDR_GENERIC` for India

**Task:** D093 (family B-dictionary). **Status: PARTIAL / in progress.**
**Deliverable:** `analysis_out/findings/D093_mine_ADDR_GENERIC_India.md`
**Sources:** `_upstream/src/keys.py`, `_upstream/src/normalize.py`,
`_upstream/src/features.py`, `_upstream/src/prep.py`, `build_profile.py`,
`analysis_out/profile/{test,train}_s{1,2,3}.json`.
Built on, not redone: D091 (ground truth), D094, D118, D122, D095, D116.

## HEADLINE

**Do not extend `ADDR_GENERIC` for India, and India is the *strongest* case yet for
NOT extending it.** Three measured reasons:

1. **Extending it is FREE of feature cost but NOT of blocking cost, and for India the
   blocking cost is where the mass is.** `ADDR_GENERIC` is applied at `keys.py:39` on a
   *local* list; `keys.py:45` returns `rid, country, nt, pref, nums, alph, pin, fk` and
   **`atoks` is not an output column**. `prep.py:16` already wrote `atoks` to parquet, and
   `features.py:129` computes `wa` over that untouched column. So adding an entry removes
   **zero** IDF feature mass (D122 NEW-2). But it removes a token from `alph`, and
   `keys.py:42` requires `len >= 3` to reach `alph` at all - so a 2-char addition is a
   **provable no-op**, and a >=3-char addition is a **pure blocking selectivity loss**.

2. **The s3 asymmetry is real and it is per-file, not pooled.** India writes the state in
   full in s1/s2 and as a **two-letter code** in s3. A 2-char code can never become a
   blocking key (`keys.py:42`), so s3 state resolution rests entirely on the `state`
   FIELD (`normalize.py:333` -> `q_state`/`s_state` -> `features.py:114` `state_eq`),
   **not on blocking**. Quantified in section 3.

3. **India already carries 9 INDIA-ONLY entries in `ADDR_GENERIC` that no other country
   needs** (D122 measured 13 India-only). The list is already India-saturated; the gap is
   not "add more Indian words", it is that the words it *has* are the ones the pipeline
   structurally cannot use.

Per-source-file `ADDR_GENERIC` removal rate for **India** (my own replication of
`keys.py:39`; the profile stores **raw pre-canon** tokens per `build_profile.py:113,126-127`):

| file | India rows | listed addr-token mass | removed by `ADDR_GENERIC` | removed by empty canon |
|---|---|---|---|---|
| train_s1 | 883,188 | 9,395,284 | 1,559,376 (16.60%) | 714,083 (7.60%) |
| train_s2 | 2,017,799 | 18,762,478 | 3,034,485 (16.17%) | 1,860,043 (9.91%) |
| train_s3 | 2,115,547 | 18,171,162 | 2,595,245 (14.28%) | 1,780,306 (9.80%) |
| test_s1 | 809,986 | 8,617,430 | 1,428,573 (16.58%) | 654,650 (7.60%) |
| test_s2 | 2,312,565 | 21,702,626 | 3,484,481 (16.06%) | 2,187,215 (10.08%) |
| test_s3 | 2,405,000 | 20,814,196 | 2,939,239 (14.12%) | 2,085,266 (10.02%) |
| **total** | **10,544,085** | **97,463,176** | **15,041,399 (15.43%)** | **9,281,563 (9.52%)** |

**Reproduction check that validates the method:** the test-split listed masses
(8,617,430 / 21,702,626 / 20,814,196) reproduce **D091's D0 table to the unit** for India
(test_s1 8,617,430, test_s2 21,702,626, test_s3 20,814,196). My test-split removal totals
1,428,573 + 3,484,481 + 2,939,239 = **7,852,293** = D091/D122's India figure exactly.

**Note the s1/s2-vs-s3 split immediately: the removal rate is measurably LOWER in s3
(14.28% / 14.12%) than in s1/s2 (16.60% / 16.17% / 16.58% / 16.06%)** - a ~2.3 point gap.
That is the first hint that s3 Indian addresses carry a *different* token mix, which
section 3 quantifies.


No `*.tsv` was opened. No network access. Read-only on `_upstream/`.
