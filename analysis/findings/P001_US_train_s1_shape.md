# P001 — [US] train_s1: shape, null rates, length distribution

Source of record: `analysis_out/profile/train_s1.json` (`split=train`, `source=1`).
No raw `*.tsv` was opened. Every number below is a named profile field or arithmetic
on named fields; field semantics were pinned by reading `build_profile.py`
(lines 79–136) before quoting anything.

## Headline

The US slice of `train_source1` is **1,323,633 rows, 59.9792% of the 2,206,821-row
file**, and it is immaculate on every integrity axis: **zero** empty names, **zero**
empty addresses, **zero** malformed `entity_id` prefixes, and a name-length histogram
that sums *exactly* to the row count. It is far too large to be anything but
conclusive (every rate below is pinned to ±0.086pp at 95%).

The genuinely new result is a **corpus-level structural split that no prior task in
this fleet has reported**: `addr_empty` is *identically zero for every country in
both source-1 files*, and non-zero in every source-2 and source-3 file. Source 1 is
not a random sample of the corpus — it is generated with a null-free template. The
same boundary shows up in a second, independent field: US `dig6`/row is **0.00125
here versus 0.0134–0.0143 in sources 2 and 3**, a **~11x** collapse, while US
`dig5`/row is essentially unchanged (0.10984 here vs 0.10780–0.10979). This
independently **confirms the `already_checked` note that the pin gap bites US
source-1**, and it does so on `train_s1`, a file that note did not cite.

> **Correction log (applied after an independent recomputation pass).** Two
> arithmetic errors in the first draft were found and fixed; both are recorded
> here so the numbers are auditable rather than silently amended:
> 1. Sources 2–3 empty addresses are **610,389**, not 552,870 (recomputed as the
>    sum of `addr_empty` over all ten source-2/3 country-slices).
> 2. The "`pin` gate would lift eligible US rows from 1,656 to ~42,000 in this
>    file" claim was wrong: 42,321 is `train_s3`'s US `dig6`, not `train_s1`'s.
>    In *this* file the corresponding bound is 147,049 (`dig5` + `dig6`).
>    See Recommendation 2, which also now states the direction correctly.
>
> The §5 histogram bound was independently re-derived and is **correct as
> written**: `len_hist` buckets are `len//10*10`, so bucket `k` spans `k..k+9` and
> the tight bound is [23,717,420 , 35,630,117], which contains the measured
> `name_chars` of 29,735,558.

## Findings

### 1. Shape and share of file

| Quantity | Value | Field / arithmetic |
|---|---|---|
| Rows in file | 2,206,821 | `rows` |
| US rows | 1,323,633 | `by_country.US.rows` |
| India rows | 883,188 | `country_rows.India` |
| **US share of file** | **59.9792%** | 1,323,633 / 2,206,821 = 0.599792 |
| India share | 40.0208% | 883,188 / 2,206,821 |
| Countries present | `US`, `India` | `country_rows` keys — **no France in train** |
| Columns | `entity_id, business_name, business_address, country` | `cols` |
| US : India row ratio | 1.4985x | 1,323,633 / 883,188 |

**Invariant 1 (holds):** 1,323,633 + 883,188 = 2,206,821 = `rows`. No third country
is hidden, and the `by_country[*].rows` values agree with `country_rows`.

### 2. Null / integrity rates (all ÷ `by_country.US.rows` = 1,323,633)

| Field | Count | Rate | Arithmetic |
|---|---|---|---|
| `name_empty` | **0** | **0.0000%** | exact zero |
| `addr_empty` | **0** | **0.0000%** | exact zero — see §3, this is not a typo |
| `prefix_bad` | **0** | **0.0000%** | exact zero |
| `has_comma` | 1,323,633 | **100.0000%** | 1,323,633 / 1,323,633 |
| `has_digit_name` | 34,494 | **2.6060%** | 34494 / 1323633 = 0.026060 |
| `alpha_only_addr` | **1** | **0.00008%** | 1 / 1323633 = 0.00000076 |
| `dig5` | 145,393 | 0.109844/row | 145393 / 1323633 |
| `dig6` | 1,656 | 0.001251/row | 1656 / 1323633 |

`prefix_bad = 0` is a non-vacuous check: `build_profile.py:94` evaluates
`eid.startswith("S1-")` per row, so 0/1,323,633 means the `S1-` prefix is a valid
partition key for **100%** of US rows. **No prefix repair is needed.**

`has_digit_name` at 2.6060% is the rate at which a business name contains a digit —
material for `keys.py:35-38`, which derives blocking prefixes from `ncore` only.
Note it is **2.4x lower here than in train_s3** (6.2981%), so this is another
source-dependent quantity, not a corpus constant.

### 3. NEW FINDING — source 1 is null-free, and the boundary is exact

`addr_empty` and `dig6`/row recomputed by this agent across **all six** profile files:

| File | Country | rows | `addr_empty` | `dig6`/row |
|---|---|---|---|---|
| train_s1 | US | 1,323,633 | **0** | **0.00125** |
| train_s1 | India | 883,188 | **0** | 0.00021 |
| test_s1 | US | 663,106 | **0** | **0.00120** |
| test_s1 | India | 809,986 | **0** | 0.00020 |
| test_s1 | **France** | 259,452 | **0** | 0.00013 |
| train_s2 | US | 3,016,817 | 111,121 | 0.01393 |
| train_s2 | India | 2,017,799 | 57,846 | 0.00023 |
| train_s3 | US | 3,170,056 | 110,968 | 0.01335 |
| train_s3 | India | 2,115,547 | 64,948 | 0.00019 |
| test_s2 | US | 1,871,330 | 55,107 | 0.01430 |
| test_s2 | India | 2,312,565 | 52,764 | 0.00022 |
| test_s2 | France | 703,378 | 21,537 | 0.00018 |
| test_s3 | US | 1,945,701 | 55,317 | 0.01375 |
| test_s3 | India | 2,405,000 | 59,240 | 0.00022 |
| test_s3 | France | 731,615 | 21,541 | 0.00016 |

**Two exact, previously unremarked invariants:**

1. **`addr_empty` == 0 in every source-1 file, for every country including
   France** — 5 country-slices, 3,939,365 rows, zero empty addresses. It is
   non-zero in all 10 source-2/3 country-slices. This is a clean partition on the
   `source` field, not a gradual difference.
2. **US `dig6`/row collapses ~11x in source 1** (0.00125 / 0.00120) versus sources
   2–3 (0.01335–0.01430), while US `dig5`/row is flat (0.10984 / 0.10979 versus
   0.10780–0.10979). India is flat on both. So the collapse is **US-and-6-digit
   specific**, not a general source-1 sparseness.

`alpha_only_addr` corroborates the same boundary from a third angle: US is **1**
(row) in each source-1 file versus 82,467–184,605 (4.2–6.1% of rows) in sources
2–3, while India is *high* in source 1 (77,036 = 8.7225%) and comparable
throughout. Read against `build_profile.py:117` (`if ba and not any(ch.isdigit()
for ch in ba)`), this means essentially every US source-1 address contains a digit
and essentially no Indian one does — a generator difference in address formatting
consistent with the `dig5`/`dig6` split above.

### 4. Lengths

| Quantity | Value | Arithmetic |
|---|---|---|
| Mean name length | **22.4651** chars | `name_chars` 29,735,558 / 1,323,633 |
| Mean address length | **34.9624** chars | `addr_chars` 46,277,429 / 1,323,633 |
| Mean name tokens/row | 3.4888 | `name_tokens` 4,617,935 / 1,323,633 |
| `num_digits`/row | 4.1667 | 5,515,205 / 1,323,633 |
| Address digit share | 11.9177% | 5,515,205 / 46,277,429 |

Because `addr_empty = 0` here, the all-rows and non-empty denominators are
**identical**, so no dual-denominator caveat is needed (unlike P003/P005). US
addresses are shorter here than in train_s3 (34.96 vs 38.45 chars) and US names
(22.47 vs 23.98). India is longer on both (26.39 name, 77.70 addr chars).

### 5. Name-length histogram (`len_hist`, bucketed by `len//10*10`)

| Name length | Rows | % of US rows | Cumulative % |
|---|---|---|---|
| 0–9 | 37,180 | 2.8089% | 2.8089% |
| 10–19 | 454,546 | 34.3408% | 37.1497% |
| **20–29** | **601,278** | **45.4263%** | **82.5761%** |
| 30–39 | 208,949 | 15.7860% | 98.3621% |
| 40–49 | 20,636 | 1.5590% | 99.9211% |
| 50–59 | 1,015 | 0.0767% | 99.9978% |
| 60–69 | 29 | 0.0022% | 100.0000% |
| **Total** | **1,323,633** | **100.0000%** | — |

**Invariant 2 (holds, exactly):** `len_hist` sums to `rows`, 1,323,633 = 1,323,633.
The distribution is sharply unimodal — 45.4% in one bucket — with a hard ceiling at
60–69; US train_s3 reached 80–89. Only 1,044 rows (0.0789%) reach 50+.

**Consistency check.** Per-bucket min/max possible `name_chars` bound the total to
[23,717,420 , 35,630,117]; measured `name_chars` = 29,735,558 falls inside. The
histogram and the character total are mutually consistent.

### 6. Is the slice large enough to conclude from? — Yes, decisively

n = 1,323,633. A proportion near 0.5 has a 95% margin of error of ±0.0852pp
(1.96·√(0.25/1,323,633)). Differences above ~0.2pp are real. The 11x `dig6` gap in
§3 is orders of magnitude beyond any sampling concern. **One scope caveat:** this
file contains no France rows, so nothing here speaks to the only scored country.

## Interpretation

*The following is inference, clearly separated from the measurements above.*

1. **Source 1 comes from a stricter generator than sources 2/3 (high confidence —
   the partition is exact, not statistical).** Four independent fields move
   together at the source boundary: `addr_empty` (0 vs 55k–111k), US `dig6`/row
   (~11x), US `alpha_only_addr` (1 vs 82k–185k), and US `has_digit_name`
   (2.61% vs 6.30%). *Inference* from the pattern: the source-1 address template
   always emits a street number and a ZIP, and never emits a missing field. The
   profile contains no generator information, so the template itself is not
   observable — only its consequences.
2. **The `pin` gate is confirmed to bite US source-1, on a second file (high
   confidence).** `already_checked` records this for "US source-1" with
   `dig6`/row 0.001. I measure 0.00125 on `train_s1` and 0.00120 on `test_s1`,
   against 0.01335–0.01430 in US sources 2–3 — the same ~11x gap, now on two files
   rather than one. What the note did **not** say, and what §3 adds, is that this is
   a *source-specific* effect confined to the US: `dig5` is unaffected, and India is
   unaffected on both fields. So the defect is precisely "US source-1 addresses
   carry 5-digit ZIPs that the India-only gate discards."
3. **The US comma invariant is exact here for a trivial reason (high confidence).**
   `has_comma` = 1,323,633 = 100% because `addr_empty` = 0. The identity
   `has_comma == rows − addr_empty` that P003 and P005 report therefore holds
   *vacuously* in source 1 — it is not independent evidence of a fixed address
   template here, unlike in sources 2/3 where it carries information.
4. **Do not extrapolate any null rate from this file to the corpus (high
   confidence, practical consequence).** An agent that profiled only source 1
   would conclude the dataset has no missing addresses at all. It does not: 610,389
   empty addresses exist across sources 2–3.

## Gaps

Fields **not collected** by `build_profile.py`, therefore not answerable here and
**not estimated** anywhere above:

- **Which source-1 rows lack a ZIP.** `dig6`/`dig5` are *occurrence* counts
  (`len(findall(...))`, lines 115–116), not row counts. The 1,656 is an upper bound
  on US source-1 rows carrying a standalone 6-digit run, and 145,393 an upper bound
  on 5-digit runs. I report occurrences/row, never row rates.
- **No row-level `has_5digit` / `has_6digit` boolean**, so distinct-row rates are
  unavailable. This is the same gap P003 and P005 flagged; it is now the third
  task to hit it, which is itself worth recording.
- **The identity of the single `alpha_only_addr` US row.** I can state that
  exactly one US address in this file contains no digit at all. I cannot say what
  it is. Almost certainly a data-quality curiosity, not a defect.
- **No `pin` field.** `normalize_address`'s output is never captured, so §3 speaks
  to the *input* the gate would admit, not to rows that actually received a pin.
- **No `state` / `city` / region field**, and no component-count or
  component-position field. The component-order question raised in `already_checked`
  is unreachable from this profile.
- **Whether the "source 1 vs 2/3" boundary has a cause I can name.** I can prove the
  partition; I cannot attribute it. Marked as inference in §3 rather than asserted.
- **No duplicate-row or unique-entity count**, so the number of distinct businesses
  behind 1,323,633 rows is not derivable, nor the achievable ER target rate.

## Recommendations

1. **[High priority, NEW] Treat `source` as a stratification variable; never pool
   across it when reporting rates.** `addr_empty`, US `dig6`/row, US
   `alpha_only_addr` and US `has_digit_name` all change discontinuously at the
   source-1 boundary. Expected effect: purely analytical — it prevents the single
   most likely class of wrong conclusion from this dataset, namely reporting a
   corpus-level null rate that is really a sources-2/3 rate. No pipeline change.
2. **[Medium priority, corroborating] The `pin` gate defect now has two
   independent file-level measurements** (`train_s1` 0.00125, `test_s1` 0.00120 vs
   0.01335–0.01430 in US sources 2/3). This raises confidence that the fix belongs
   in the *gate condition* (`normalize.py:337`) and not in per-file special-casing.
   *The fix's recall/precision tradeoff remains SPECULATIVE* — no profile field
   measures the false-positive cost of admitting more US rows into a blocking key.
   Expected effect: if widened to `len(n) in (5, 6)`, the US rows in *this* file
   eligible for a `pin` blocking key rise from 1,656 to at most 147,049
   (145,393 `dig5` + 1,656 `dig6` occurrences) — but note that is an *upper bound* on
   distinct rows, and 1,656 → 42,321 is the equivalent comparison in
   `train_s3`, not here. The relevant point for this slice is the **inverse** of the
   usual framing: source 1 is where the gate discards the *least*, so widening it
   helps sources 2/3 far more than it helps source 1.
3. **[No change] No null handling, prefix repair, or name handling is warranted for
   US train_s1.** `name_empty`, `addr_empty` and `prefix_bad` are all exact zeros.
   Manufacturing a fix here would be noise.
4. **[No change] No dictionary entry is warranted from this slice.** This work order
   is a shape/null-rate profile; it produced evidence about *how addresses are
   generated*, not a missing normalisation token. No `CONFIRMED`/`LIKELY`/
   `SPECULATIVE` entries are proposed.
5. **[Low priority, informational] Record the vacuous-invariance trap.** P003 and
   P005 both treat `has_comma == rows − addr_empty` as evidence of a fixed address
   template. In source 1 that identity holds *because* `addr_empty = 0`, so it
   proves nothing there. Worth stating so later agents do not over-read it.

## Relation to the two REFUTED findings

Stated plainly, as required:

- **REFUTED-1 (French postal codes discarded by the `pin` guard).** Not
  re-derived, and **my evidence does not support it**. This file has no France
  rows. I measured US `dig5`/row = 0.109844, consistent with the 0.110 quoted for the
  US, and the France figures in `already_checked` (0.004 in test_s1) stand
  unchallenged. What I add is the *US source-1* correction the note flagged as
  already-covered, now measured on `train_s1` as well.
- **REFUTED-2 (`FR_REGIONS` too thin ⇒ no usable state signal).** Out of scope:
  `train_source1` contains only `US` and `India`. I make no claim about it.

## Confidence markers

| Claim | Marker | Basis |
|---|---|---|
| US train_s1 = 1,323,633 rows, 59.9792% of file | **CONFIRMED** | `rows`, `by_country.US.rows`, arithmetic shown |
| `name_empty` = `addr_empty` = `prefix_bad` = 0 | **CONFIRMED** | exact zeros, `build_profile.py:94,98,100` |
| `len_hist` sums exactly to `rows` | **CONFIRMED** | exact integer identity |
| `country_rows` sums exactly to `rows` | **CONFIRMED** | exact integer identity |
| `addr_empty` = 0 in all 5 source-1 country-slices | **CONFIRMED** | recomputed from all six profile files |
| US `dig6`/row ≈ 11x lower in source 1 | **CONFIRMED** | 0.00125/0.00120 vs 0.01335–0.01430 |
| US `alpha_only_addr` = 1 in each source-1 file | **CONFIRMED** | direct field value |
| Source 1 uses a stricter generator template | **INFERENCE (high confidence)** | four fields move together; no generator data exists |
| `has_comma` identity is *vacuous* in source 1 | **CONFIRMED** | follows from `addr_empty` = 0 |
| The `pin` fix should target the gate condition | **LIKELY** | two files agree; defect is source-specific |
| Recall/precision cost of widening the `pin` gate | **SPECULATIVE** | not measured by any profile field |
| Component-order / city analysis | **SPECULATIVE (abandoned)** | fields not collected in this profile |



