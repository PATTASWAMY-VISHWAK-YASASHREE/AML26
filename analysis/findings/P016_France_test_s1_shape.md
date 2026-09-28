# P016 — [France] test_s1: shape, null rates, length distribution

**Status: COMPLETE.** **Agent:** b07 · **Family:** A-profile ·
**Profile input:** `analysis_out/profile/test_s1.json` (plus `test_s2`/`test_s3` for the
representativeness control). No raw TSV was opened. All arithmetic in PowerShell.

---

## 0. HEADLINE

**`test_s1` France is a 259,452-row slice that is *structurally unlike* the other 84.69%
of France, and every one of its headline numbers is a trap.**

1. **France share of the FILE is 14.98%** (`259,452 / 1,732,544`). France share of
   *France* is **15.31%** (`259,452 / 1,694,445`). Both are small; the second is the
   number that was misused.
2. **NEW STRUCTURAL FINDING: s1 is not a random sample of France — it is a different
   ROLE.** `run_blocking.py:11-12` shows `s1` is the *candidate/index* side and `q` is
   the *query* side built from S2+S3. `make_submission.py:66` emits
   `source1_entity_id` from `test_s1`. **s1 France is the answer-key side, so its
   259,452 rows are exactly the French rows the submission must be scored on** — while
   s2/s3 France (1,434,993 rows) are the *search* corpus. The "15.31% is
   unrepresentative" warning is **correct for row-level properties but structurally
   wrong for coverage claims**. See §5 — this is the one place I partly disagree with
   the framing in my work order, and I show the code.
3. **On every row-level shape statistic, s1 France is an outlier and the direction is
   consistent: s1 is cleaner and longer.** Empty-address rate is **0.0000%** vs
   **2.5423%** pooled. Mean address length is **50.07** vs **41.34** pooled (**+21.1%**).
   The bias is ~100x the statistical noise. Details in §3/§4.

**Verdict on representativeness: NO. Do not generalise s1 France numbers to France.**
**Verdict on defect: none found in this slice.** `prefix_bad = 0/259,452`, `name_empty =
0/259,452`, `len_hist` sums to `rows` exactly. The only actionable items are the
**population-scoping discipline** in §7, which is already fleet policy.

---

## 1. SHAPE — every requested figure, with the denominator shown

Source: `analysis_out/profile/test_s1.json` → `by_country["France"]`.
Every rate is `field / rows` where `rows = 259,452`.

| quantity | field | numerator | value | rate |
|---|---|---|---|---|
| rows | `rows` | — | **259,452** | — |
| empty name | `name_empty` | 0 | **0** | **0 / 259,452 = 0.000000%** |
| empty address | `addr_empty` | 0 | **0** | **0 / 259,452 = 0.000000%** |
| mean name length (chars) | `name_chars / rows` | 5,039,314 | — | **19.4229** |
| mean address length (chars) | `addr_chars / rows` | 12,990,984 | — | **50.0709** |
| mean name tokens | `name_tokens / rows` | 828,812 | — | **3.1945** |
| digit-in-name | `has_digit_name` | 2,002 | — | **2,002 / 259,452 = 0.7716%** |
| comma-in-address | `has_comma` | 259,452 | — | **259,452 / 259,452 = 100.0000%** |
| entity_id prefix invalid | `prefix_bad` | 0 | — | **0 / 259,452 = 0.000000%** |
| (aux) alpha-only address | `alpha_only_addr` | 1,089 | — | **1,089 / 259,452 = 0.4197%** |
| (aux) digits in address | `num_digits / rows` | 510,818 | — | **1.9688 / row** |
| (aux) lookaround-guarded dig5 | `dig5 / rows` | 1,082 | — | **0.004170 / row** |
| (aux) lookaround-guarded dig6 | `dig6 / rows` | 34 | — | **0.000131 / row** |

**`has_comma = 100.0000%` is exact, not rounded.** `259,452 / 259,452`. Every France row
in `test_s1` carries a comma. This is a whole-file property, not a France one: US
`663,106/663,106` and India `809,986/809,986` in the same file are also exactly 100%.
`test_s1` has **zero empty addresses and zero comma-free addresses in all three
countries** — it is a pre-normalised, fully-populated file. `test_s2`/`test_s3` are not.

### 1b. Name-length histogram

`len_hist` is keyed on `len(bn) // 10 * 10` (`build_profile.py:104-105`), so bucket `"0"`
means **length 0–9**, not "empty". Since `name_empty = 0`, no row in this bucket is
actually empty. France-only columns.

| bucket | n | % of 259,452 |
|---|---|---|
| 0–9 | 2,719 | 1.048% |
| 10–19 | 142,909 | 55.081% |
| 20–29 | 102,124 | 39.361% |
| 30–39 | 11,627 | 4.481% |
| 40–49 | 72 | 0.028% |
| 50–59 | 1 | 0.000% |
| **sum** | **259,452** | **100.000%** |

**Denominator check: 2,719 + 142,909 + 102,124 + 11,627 + 72 + 1 = 259,452 = `rows`
exactly.** The histogram is complete and accounts for every French row in the file.

The distribution is sharply **truncated**: 94.44% of names fall in 10–29 chars and only
**0.028%** exceed 39 chars. `test_s2` reaches 60–69 and `test_s3` reaches 70–79. A
name-length threshold tuned on s1 France would be badly mis-calibrated for the rest of
France.

### 1c. entity_id prefix validity — the check the order asked for, actually run

`build_profile.py:94` defines the check:

```python
if not eid.startswith(f"S{src}-"):
    s["prefix_bad"] += 1
```

- `test_s1` France: `prefix_bad = 0` → **100.0000% of France s1 entity_ids begin `S1-`.**
  Zero malformed.
- Whole file, all three countries summed: `0 / 1,732,544` = **0.000000%**.
- I extended the check to all six profiles: `prefix_bad = 0` in **every** country of
  **every** file (train s1/s2/s3 and test s1/s2/s3).

**Important semantic correction, because this field is easy to misread:** the check
tests `S{src}-` where `src` is the *source number*, and it is applied **identically to
train and test**. So `prefix_bad = 0` in `train_s1` means train entity_ids *also* start
with `S1-`. **The `S` prefix encodes SOURCE, not SPLIT.** It is not a train/test
discriminator, and reading it as one would be wrong.

The prefix *is* load-bearing downstream, which is why the check is worth running:
`stage2.py:106` does `pl.when(pl.col("entity_id").str.starts_with("S2")).then(2).
otherwise(3)` to tag each query's source. That logic is applied to the `q` (S2+S3) side,
not to s1, but a malformed prefix anywhere would silently fall into the `otherwise(3)`
branch rather than raise. **Measured result: no such rows exist. No defect.**

**Caveat (gap):** `build_profile.py` stores no `entity_id` samples, so I can confirm the
*prefix* and its count but cannot verify the *suffix* format, uniqueness, or
cross-file ID disjointness. Those are not checkable from the profile. Not estimated.

---

## 2. WHAT SHARE OF THE FILE IS FRANCE

Two different denominators, and conflating them is how the original error happened.

| denominator | arithmetic | value |
|---|---|---|
| France share **of `test_s1`** | 259,452 / 1,732,544 | **14.9752%** |
| France share of **all test rows** | 1,694,445 / 11,702,133 | **14.4798%** |
| **`test_s1` share of France** | 259,452 / 1,694,445 | **15.3119%** |
| `test_s2` share of France | 703,378 / 1,694,445 | 41.5108% |
| `test_s3` share of France | 731,615 / 1,694,445 | 43.1773% |
| France rows s1 never touches | 703,378 + 731,615 = 1,434,993 | **84.6881%** |

`test_s1` France is the **minority slice on both denominators**: 14.98% of its own file,
and 15.31% of France. A conclusion drawn here is a conclusion about roughly one row in
seven.

---

## 3. IS THE SLICE LARGE ENOUGH TO CONCLUDE FROM?

**Two separate questions, with opposite answers.**

**(a) Statistically — yes, amply.** At n = 259,452 the 95% CI half-width for a
proportion at worst case p = 0.5 is `1.96 x sqrt(0.25 / 259,452) = 0.1924%`. The
digit-in-name rate of 0.7716% is therefore known to about +/-0.19pp. There is no
sampling-noise problem here at all.

**(b) As a basis for generalising to France — no.** The problem is not noise, it is
**bias**, and the bias is ~100x the noise:

| statistic | s1 France | s2+s3 France | pooled France | s1 bias vs pooled |
|---|---|---|---|---|
| empty-address rate | **0.0000%** | 3.0020% | 2.5423% | **-2.5423 pp (undefined relative)** |
| comma-in-address rate | **100.0000%** | 96.9748% | 97.4380% | **+2.5620 pp** |
| mean address length | **50.0709** | 39.7623 | 41.3407 | **+8.7302 chars (+21.1%)** |
| mean name length | 19.4229 | 21.1220 | 20.8618 | -1.4389 chars (-6.9%) |
| mean name tokens | 3.1945 | 3.4475 | 3.4087 | -0.2140 (-6.3%) |
| digit-in-name rate | **0.7716%** | 1.1089% | 1.0572% | **-0.2856 pp (-27.0%)** |
| alpha-only-address rate | **0.4197%** | 3.7291% | 3.2224% | **8.88x understated** |

Arithmetic for the s2+s3 column: `s2+s3 France rows = 703,378 + 731,615 = 1,434,993`;
`addr_chars = 27,816,963 + 29,241,603 = 57,058,566` → `/1,434,993 = 39.7623`;
`addr_empty = 21,537 + 21,541 = 43,078` → `3.0020%`;
`has_comma = 681,661 + 709,921 = 1,391,582` → `96.9748%`.
Pooled France over all three files: `rows = 1,694,445`, `addr_empty = 43,078`
→ `2.5423%`, `has_comma = 1,651,034` → `97.4380%`, `addr_chars = 70,049,550`
→ `41.3407`.

The empty-address row is the sharpest: **s1 has literally zero**, so no amount of
weighting or extrapolation recovers the pooled 2.5423% from s1 data. And the
`alpha_only_addr` gap is nearly an order of magnitude.

**Conclusion: the slice is large enough to measure *itself* precisely and far too
unrepresentative to describe France.** Precision is not the binding constraint;
population choice is.

---

## 4. WHY s1 IS UNREPRESENTATIVE — QUANTIFIED, NOT ASSERTED

### 4a. The geography encoding differs (D128, independently re-derived)

I recomputed the discriminator densities from `addr_tokens["France"]` rather than
quoting D128. Region discriminators `hauts`/`nouvelle`/`pays`; department
discriminators `nord`/`gironde`/`calais`/`atlantique`.

| source | France rows | region tokens | density | dept tokens | density |
|---|---|---|---|---|---|
| **test_s1** | 259,452 | 259,840 | **100.15%** | 16,482 | **6.35%** |
| test_s2 | 703,378 | 225,997 | 32.13% | 269,436 | 38.31% |
| test_s3 | 731,615 | 254,016 | 34.72% | 273,990 | 37.45% |

Individual tokens, s1: `hauts` 101,717 · `nouvelle` 85,311 · `pays` 72,812 (= 259,840)
versus `nord` 200 · `gironde` 62 · `calais` 15,967 · `atlantique` 253 (= 16,482).

My densities differ slightly from D128's (100.7% / 6.8% / 32.6% / 38.7%) because I used a
fixed 3-token region set and 4-token department set; D128's exact membership is not
published. **The qualitative conclusion is identical and is the point: s1 is
region-encoded, s2/s3 are department-encoded, a ~5.7x swing in department density.**

**Density is token occurrences / France rows, so it exceeds 100% for s1** because a
region name contributes 2–3 tokens per row. **It is a concentration indicator, never a
row count.** `101,717 + 85,311 + 72,812 = 259,840` is close to but **not equal to**
259,452 — the excess 388 is the multi-token decomposition, plus rows carrying more than
one region token. (This also means I can **not** reproduce the retracted figure's
arithmetic `101,521 + 85,197 + 72,734 = 259,452`; my measured values differ. The
conclusion survives regardless.)

### 4b. Address shape differs — the s1 file is pre-cleaned

| | test_s1 | test_s2 | test_s3 |
|---|---|---|---|
| France empty-address rate | **0.000%** | 3.062% | 2.944% |
| France comma rate | **100.000%** | 96.912% | 97.035% |
| France mean addr chars | **50.07** | 39.55 | 39.97 |
| France mean name chars | 19.42 | 21.10 | 21.14 |

s1 France addresses are **10.3 characters longer on average** and carry a mandatory
region component, which is exactly why s1 rows are longer: the extra characters are the
administrative component s2/s3 lack. **INFERENCE (marked):** the s1 file appears
pre-filtered to fully-populated, comma-delimited, admin-tagged records. The profile
cannot prove a filtering step — but it can prove s1 is structurally different, and the
difference is systematic and directional, not noise.

**Name-length distributions diverge too.** Bucket `%` of each source's France rows:

| bucket | s1 % | s2 % | s3 % | pooled % |
|---|---|---|---|---|
| 0–9 | **1.048** | 3.694 | 4.904 | 3.812 |
| 10–19 | **55.081** | 42.791 | 41.831 | 44.258 |
| 20–29 | 39.361 | 39.357 | 37.937 | 38.745 |
| 30–39 | **4.481** | 12.509 | 13.076 | 11.525 |
| 40–49 | **0.028** | 1.607 | 2.096 | 1.576 |
| 50–59 | **0.000** | 0.042 | 0.148 | 0.081 |
| 60–69 | **0.000** | 0.000 | 0.007 | 0.003 |
| 70–79 | **0.000** | 0.000 | 0.000 | 0.000 |

s1 is massively over-concentrated in 10–19 and has essentially no long tail. Any
length- or character-cap hyperparameter fitted on s1 France would be fitted on a
distribution with ~100x less tail mass than the corpus it will score.

---

## 5. THE ONE PLACE I PARTLY DISAGREE WITH MY WORK ORDER

My order says: *"be explicit that any conclusion drawn from it generalises to only
15.31% of French rows."*

**For row-level descriptive statistics, that is exactly right and §4 proves it.**

**For coverage/participation claims it is wrong**, and the code says so unambiguously:

```python
# run_blocking.py:11-12
pl.scan_parquet(f"{W}/{split}_source1_norm.parquet").with_row_index("rid").sink_parquet(f"{W}/{split}_s1.parquet")
pl.concat([pl.scan_parquet(f"{W}/{split}_source{i}_norm.parquet") for i in (2, 3)]).with_row_index("rid").sink_parquet(f"{W}/{split}_q.parquet")

# make_submission.py:66,69
s1 = pl.read_parquet(f"{W}/test_s1.parquet", columns=["rid", "entity_id"]).rename({... .alias("source1_entity_id")})
match = (s1.join(acc.group_by("s1")..., on="s1", how="left")
```

and `features.py:1`: *"Pairwise feature computation for (query = Source2/3 record,
candidate = Source1 record)."*

So: **s1 is the candidate/answer-key side; s2+s3 are the query side. The submission's
`source1_entity_id` column is drawn from `test_s1`.** Every French s1 row is a unit the
model must produce an answer for.

**Implication — this sharpens rather than weakens the trap warning, in a different
direction:** the retracted "100% of France rows resolve a state" figure was wrong as a
*coverage* claim over France rows, but s1 France is genuinely 100% of the **scored**
French units. Two different populations, two different correct statements:

- "What share of French **scored units** does s1 France represent?" → **100%.**
- "What share of French **rows** does s1 France represent?" → **15.31%.**

Both are true. The retracted figure slid between them. **Any future France claim must
name which population it means.** I flag this because the work order's own framing
would have me assert the 15.31% figure as a coverage statement, and that assertion
would itself be a scoping error of exactly the kind this project has already paid for
once.

---

## 6. GAPS — what the profile cannot settle

- **No `entity_id` values are stored.** Prefix validity is confirmed; suffix format,
  uniqueness and cross-file disjointness are **not checkable**. Not estimated.
- **`len_hist` is the NAME length only** (`build_profile.py:104`, on `bn`). There is
  **no address-length histogram** in the profile — only the mean. A claim about the
  address-length *distribution* would be a gap.
- **No per-row data.** Every figure above is an aggregate or a token occurrence sum.
  `addr_tokens`/`name_tokens` are **top 4000** per country (min values 23/58/60 for
  test s1/s2/s3 France), so a token missing from them is **"not in the top 4000"**,
  never "does not occur".
- **The profile FLATTENS comma components** (`build_profile.py:126-127`), so no
  per-component rate — including "share of rows with N components" — is derivable.
- **The profile does not strip accents**; the pipeline does (`normalize.py:317`). Any
  accented-token count here is an undercount.
- **I did not re-verify the pipeline-visible effect of any of this.** Per the brief's
  limit, a token count is not automatically a pipeline-visible quantity. I traced
  `entity_id` prefixes to `stage2.py:106` because that is a direct consumer. I did
  **not** trace the length/empty-address statistics to any consumer, so I make **no**
  downstream-effect claim for them.

---

## 7. RECOMMENDATION

**Process, not code — no code change is warranted from this slice.**

1. **`CONFIRMED` — no defect in this slice.** `prefix_bad` 0/259,452; `name_empty`
   0/259,452; `addr_empty` 0/259,452; `len_hist` closes on `rows`. Nothing to fix.
2. **`CONFIRMED` — do not quote any s1-France statistic as a France statistic.** §4
   shows 2.5–21% biases, and the empty-address bias is unbounded because s1's value is
   exactly zero.
3. **`CONFIRMED` — France is test-only.** `country_rows` in all three train profiles has
   keys `US, India` only, and each sums exactly to `rows` (1,323,633 + 883,188 =
   2,206,821; 3,016,817 + 2,017,799 = 5,034,616; 3,170,056 + 2,115,547 = 5,285,603).
   **No France training data exists**, so there is no French train/test consistency
   check available and no way to calibrate s1 against French labels. (Consistent with
   P013/P014/P015, which all found the France train slices empty.)
4. **`LIKELY` — add a population tag to every France figure.** The cheapest durable fix
   is a convention, not code: every France number carries its denominator
   (`test_s1 France` / `France test` / `France scored units`). §5 shows the three are
   genuinely different quantities and the project has already shipped one wrong
   figure from conflating two of them.
5. **`SPECULATIVE` — if a French length/null profile is ever needed for tuning, it must
   come from s2+s3 (1,434,993 rows), not s1.** s1 has no long-name tail and no empty
   addresses. *Inference, marked as such: I have not shown that any current
   hyperparameter was fitted on s1 France — that would need the training logs.*

---

## 8. PROVENANCE

| figure | field / source |
|---|---|
| all s1 France shape stats | `analysis_out/profile/test_s1.json` → `by_country["France"]` |
| s2/s3 comparison | `test_s2.json`, `test_s3.json` → `by_country["France"]` |
| pooled France | sum over the three `by_country["France"]` blocks, ÷ 1,694,445 |
| file row counts | `rows` in each profile |
| France test-only | `country_rows` in `train_s1/s2/s3.json` |
| prefix semantics | `build_profile.py:94`; `stage2.py:106`; `run_blocking.py:11-12`; `make_submission.py:66,69`; `features.py:1` |
| hist bucket semantics | `build_profile.py:104-105` |
| `num_digits` / `dig5` / `dig6` semantics | `build_profile.py:29-30, 114-116` (address only; dig5/dig6 lookaround-guarded) |
| top-4000 truncation | `build_profile.py:27, 139` |
| `FR_REGIONS` | `_upstream/src/normalize.py:243-249` (read-only) |

All computation in PowerShell (`ConvertFrom-Json`). Python is broken on this box. No
raw TSV opened. No network access. `_upstream/` and the dataset untouched.


**Implication — this sharpens rather than weakens the trap warning, in a different
direction:** the retracted "100% of France rows resolve a state" figure was wrong as a
*coverage* claim over France rows, but s1 France is genuinely 100% of the **scored**
French units. Two different populations, two different correct statements:

- "What share of French **scored units** does s1 France represent?" → **100%.**
- "What share of French **rows** does s1 France represent?" → **15.31%.**

Both are true. The retracted figure slid between them. **Any future France claim must
name which population it means.** I flag this because the work order's own framing
would have me assert the 15.31% figure as a coverage statement, and that assertion
would itself be a scoping error of exactly the kind this project has already paid for
once.

population choice is.

**Verdict on defect: none found in this slice.** `prefix_bad = 0/259,452`, `name_empty =
0/259,452`, `len_hist` sums to `rows` exactly. The only actionable items are the
**population-scoping discipline** in §7, which is already fleet policy.
