# P002 — [US] train_s2: shape, null rates, length distribution

## Headline

US train_source2 is 3,016,817 rows — 59.9215% of the 5,034,616-row file — and it is
clean on every integrity axis measured: **zero** empty names, **zero** malformed
`entity_id` prefixes, and a name-length histogram that sums exactly to the row count.
The one thing worth acting on is a **new, previously unremarked structural invariant**:
in this slice `has_comma` (2,905,696) equals `rows − addr_empty` (3,016,817 − 111,121 =
2,905,696) *exactly*, meaning **100.00% of non-empty US addresses contain a comma** and
the 3.68% of rows with empty addresses are the *only* rows lacking one. This is a
US-wide invariant (it holds in all four US slices across train and test), so
`has_comma` carries **no information beyond `addr_empty` for US** and any feature or
quality gate built on it is a duplicate of the address-emptiness signal.

## Findings

All figures from `analysis_out/profile/train_s2.json`, field `by_country.US`, unless noted.
Builder semantics confirmed by reading `build_profile.py` (lines 79–136), which is what
fixes the meaning of every field quoted here. Slice header: `split=train`, `source=2`,
`cols=[entity_id, business_name, business_address, country]`.

### Shape and share

| Quantity | Value | Arithmetic / source field |
|---|---|---|
| File rows | 5,034,616 | `rows` |
| US rows | 3,016,817 | `by_country.US.rows` |
| India rows | 2,017,799 | `country_rows.India` |
| Countries present | `India`, `US` — **no France** | `country_rows` keys |
| US share of file | **59.9215%** | 3,016,817 / 5,034,616 = 0.599215 |
| India share of file | 40.0785% | 2,017,799 / 5,034,616 |

**France is absent from train entirely** — `country_rows` has no `France` key for this
slice, consistent with the competition design that France appears only in test.

### Null / integrity rates (all ÷ `by_country.US.rows` = 3,016,817)

| Field | Count | Rate | Note |
|---|---|---|---|
| `name_empty` | 0 | **0.0000%** | exact zero |
| `addr_empty` | 111,121 | 3.6834% | 111121/3016817 = 0.036834 |
| `prefix_bad` | 0 | **0.0000%** | exact zero; every `entity_id` starts `S2-` |
| `has_comma` | 2,905,696 | 96.3166% | 2905696/3016817 |
| `has_digit_name` | 193,041 | 6.3988% | 193041/3016817 = 0.063988 |
| `alpha_only_addr` | 184,605 | 6.1192% | non-empty addr containing no digit |
| `dig5` | 323,824 | 10.7340% | standalone 5-digit runs, lookaround-guarded |
| `dig6` | 42,026 | 1.3931% | standalone 6-digit runs |

`prefix_bad` is a genuine, non-vacuous check: `build_profile.py:94` tests
`eid.startswith(f"S{src}-")` per row, so 0/3,016,817 means the source-file
partition and the `entity_id` prefix agree for 100% of US rows. **The `S2-` prefix is
a valid, zero-defect join/partition key for this slice.**

### Lengths

| Quantity | Value | Arithmetic |
|---|---|---|
| Mean name length | **23.5543** chars | `name_chars` 71,059,009 / 3,016,817 |
| Mean address length | **31.5310** chars | `addr_chars` 95,123,286 / 3,016,817 (all rows) |
| Mean address length, non-empty only | 32.7368 | 95,123,286 / 2,905,696 |
| Mean name tokens/row | 3.5514 | `name_tokens` 10,713,782 / 3,016,817 |
| Address digits/row | 3.7514 | `num_digits` 11,317,142 / 3,016,817 |
| Address digit share of address chars | 11.8973% | 11,317,142 / 95,123,286 |

Note `num_digits` counts digits in the **address only** (`build_profile.py:114`,
`sum(ch.isdigit() for ch in ba)`), not the name. The digit-in-name signal is
`has_digit_name` (6.3988%) and is a separate field.

### Name-length histogram (`len_hist`, buckets by tens)

`sum(len_hist) = 3,016,817` — **exactly matches `rows`**, so the histogram is complete
and no bucket is missing or double-counted.

| Bucket | Range (chars) | Count | Share | Cumulative |
|---|---|---|---|---|
| 0 | 0–9 | 91,611 | 3.0367% | 3.0367% |
| 10 | 10–19 | 959,916 | 31.8188% | 34.8555% |
| 20 | 20–29 | 1,258,076 | 41.7021% | 76.5576% |
| 30 | 30–39 | 583,593 | 19.3447% | 95.9023% |
| 40 | 40–49 | 110,015 | 3.6467% | 99.5490% |
| 50 | 50–59 | 12,496 | 0.4142% | 99.9632% |
| 60 | 60–69 | 1,040 | 0.0345% | 99.9977% |
| 70 | 70–79 | 69 | 0.0023% | 100.0000% |
| 80 | 80–89 | 1 | 0.0000% | 100.0000% |

- **Median falls in bucket 20–29** (cumulative crosses 50% inside that bucket: 34.8555%
  → 76.5576%).
- Names are short: **76.5576% are ≤29 chars** and 99.5490% are ≤49 chars.
- Right tail is effectively empty (1 row in the 80s).
- Consistency check: the bucket-implied mean range is [19.01, 28.01] chars
  (`sum(bucket*count)/rows` to `sum((bucket+9)*count)/rows`), and the exact mean 23.5543
  sits inside it. The histogram and `name_chars` agree.

### The `has_comma` invariant (new observation)

`has_comma` = 2,905,696 and `rows − addr_empty` = 3,016,817 − 111,121 = 2,905,696. These
are **equal to the row**. Since `has_comma` counts rows whose address contains `,` and no
empty string can contain a comma, equality means every non-empty address has ≥1 comma.

I tested this invariant across **all six profile files** (15 country-slices):

| Slice | Country | non-empty | has_comma | deficit |
|---|---|---|---|---|
| train_s1 | US | 1,323,633 | 1,323,633 | 0 |
| train_s2 | **US** | **2,905,696** | **2,905,696** | **0** |
| train_s3 | US | 3,059,088 | 3,059,088 | 0 |
| test_s1 | US | 663,106 | 663,106 | 0 |
| test_s2 | US | 1,816,223 | 1,816,223 | 0 |
| test_s3 | US | 1,890,384 | 1,890,384 | 0 |
| test_s1 | France | 259,452 | 259,452 | 0 |
| test_s2 | France | 681,841 | 681,661 | **180** (0.0264%) |
| test_s3 | France | 710,074 | 709,921 | **153** (0.0215%) |
| test_s2 | India | 2,259,801 | 2,259,799 | 2 (0.0001%) |
| test_s3 | India | 2,345,760 | 2,345,759 | 1 (0.0000%) |

**The invariant is exact for every US slice in the entire dataset** (6/6, zero deficit,
including all three test slices). It is violated only by a handful of France/India test
rows.

### Is the slice large enough to conclude from?

Yes, comfortably. At n = 3,016,817 the 95% binomial CI half-width is:

| Rate | p | 95% CI half-width |
|---|---|---|
| `addr_empty` | 0.036834 | ±0.000213 (±0.021 pp) |
| `has_digit_name` | 0.063988 | ±0.000276 (±0.028 pp) |
| `dig5` | 0.107340 | ±0.000349 (±0.035 pp) |
| `dig6` | 0.013931 | ±0.000132 (±0.013 pp) |
| `alpha_only_addr` | 0.061192 | ±0.000270 (±0.027 pp) |

Every rate is pinned to within ±0.04 percentage points. At this n, even the rarest
feature I measured (`dig6`, 1.39%) has thousands of supporting rows (42,026), so these
are population-level facts about US train_s2, not sample noise.

## Interpretation

*Marked as inference. The measurements above are fact; what follows is my reading.*

1. **No data-quality defect exists in this slice.** Zero empty names and zero bad
   `entity_id` prefixes over 3M rows means no cleaning or filtering is warranted for
   US train_s2. Recommending a null-handling pass here would be manufacturing work.

2. **`has_comma` is a redundant feature for US — this is the actionable finding.**
   Since `has_comma ≡ (addr_nonempty)` exactly for all US data, a model feature or a
   data-quality gate keyed on "address contains a comma" is a relabelling of
   "address is non-empty". It adds no discriminative power and, worse, it will look
   meaningful on US validation while being pure noise on any slice where the invariant
   breaks. *Inference*: if such a feature exists downstream, it is a candidate for
   removal. I did not search the feature builder for it — flagged as a follow-up, not
   a confirmed defect.

3. **The address is a comma-delimited multi-component field for US.**
   `normalize.py:322` does `s.split(",")` with no fallback, so component extraction is
   structurally safe for 100% of non-empty US rows. This corroborates the component-order
   concern raised for France, but shows the US side is not at risk from that failure mode.

4. **`dig5` is 7.71× `dig6`** (323,824 / 42,026), consistent with US ZIP+4 style
   addresses where a 5-digit ZIP is common and 6-digit runs are rarer. *Inference*:
   these are ZIP-derived, not house numbers. I did not verify this by inspecting rows.

5. **The France test-set rows with no comma (180 in test_s2, 153 in test_s3) are the
   only place the invariant breaks.** *Inference*: for those ~333 rows the
   `split(",")` path yields a single component, so they may resolve state/city worse than
   their neighbours. At 0.02–0.03% of France rows the effect on the score is almost
   certainly negligible. I am **not** claiming this is exploitable — only that it is the
   first measured asymmetry between US and France address framing.


### Relation to the two REFUTED findings

I did not attempt to re-derive either. For the record, this slice is **consistent** with
REFUTED-1 and does not contradict it: US `dig5`/row here is 0.107, i.e. US rows are
*rich* in 5-digit numbers, which is the opposite of the French situation that refuted it.
My data therefore **does not** support REFUTED-1, and I found no evidence against
REFUTED-2 either (no region/state fields are collected in the profile at all — see Gaps).

## Gaps

Fields **not collected** by `build_profile.py`, so not answerable from the profile and
not estimated anywhere above:

- **Per-component address structure.** No field records how many comma-separated
  components an address has, their order, or which component holds the city/state/ZIP.
  I can prove ≥2 components exist for every non-empty US address (from the comma
  invariant) but **not** their order or count. This is the single biggest gap and it
  blocks direct testing of the French component-order question.
- **No state / region / city fields at all.** `normalize_address`'s `state` output is not
  captured by the profiler, so nothing here can independently confirm or refute
  REFUTED-2.
- **No `pin` field.** Whether the 6-digit `dig6` runs are US ZIP+4 or Indian PINs cannot
  be separated per-row; `dig6` is a raw count only.
- **No whitespace/quality variants of "empty".** The builder `.strip()`s before testing
  emptiness, so a name of `"   "` is already counted as empty. I cannot distinguish
  true-empty from whitespace-only.
- **No distinct-name or duplicate-entity counts.** `name_tokens` is capped at top-4000
  and pruned of hapax, so it cannot give vocabulary size, type-token ratio, or the
  number of unique businesses. I report the 3.5514 tokens/row as a mean only, and the
  token cap means the 3,681 short (1–9 char) tokens I counted are a *lower bound* on
  what the 91,611 short-name rows draw from.
- **No `has_digit_name` cross-tab with `len_hist`.** I cannot say whether the 193,041
  digit-bearing names are concentrated in the 0–9 bucket.

## Recommendations

1. **Do not add null-handling or prefix-repair logic for US.** `name_empty` and
   `prefix_bad` are both exactly 0. Expected effect: none; this recommendation is to
   *avoid* wasted effort.
2. **Audit for and drop any feature gated on `has_comma` for the US path** (or document
   it as an alias of address-emptiness). Rationale: it is provably redundant on 100% of
   US rows across train and test. Expected effect: no accuracy change on US; removes a
   feature that would silently mis-generalise if the invariant ever broke. **Priority:
   medium. This is an inference about downstream code I have not read** — the follow-up
   is to grep the feature builder for `has_comma` / comma conditions.
3. **No dictionary change is warranted from this slice.** Nothing measured here is a
   normalisation gap; the address and name fields are structurally well-formed. I
   propose **no** `CONFIRMED` / `LIKELY` / `SPECULATIVE` dictionary entries, because this
   work order is a shape/null-rate profile and produced no evidence of a normalisation
   defect.
4. **If another agent has budget, collect per-component address structure** (component
   count, per-component digit/alpha flags, and the index of the component containing a
   5-/6-digit number) for France. That single addition would settle the component-order
   question flagged in my work order and is currently the largest blind spot in the
   profile as a whole.

