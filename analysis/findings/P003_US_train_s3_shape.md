# P003 — [US] train_s3: shape, null rates, length distribution

Source file: `analysis_out/profile/train_s3.json` (split `train`, source `3`).
No raw `*.tsv` was opened. All figures below come from named fields of that one
profile file, or from arithmetic on them. Code references are to
`_upstream/src/*.py`, which was read read-only.

## Headline

The US slice of `train_source3` is **3,170,056 rows (59.98% of the 5,285,603-row
file)** and is structurally clean: **zero empty names, zero malformed
`entity_id` prefixes**, and a tight name-length distribution with 74.5% of names
at 20–29 characters. Two things are worth flagging. First, the address field is
**almost perfectly comma-delimited** — `has_comma` = 3,059,088 is *exactly*
`rows − addr_empty` (3,170,056 − 110,968), i.e. **every non-empty US address
contains at least one comma and no empty one does**. Second, and this is the
part that matters for the pipeline, `normalize.py:337` gates `pin` on
`country == "India"`, but the measured 6-digit density is **103x higher in the
US than in India in this very slice** (US `dig6`/row = 0.01335 vs India 0.000194)
— so the gate is oriented away from the country that actually carries the signal.
This is *not* a re-derivation of the refuted France finding: the refuted claim was
about France, and the correction in `already_checked` covers US source-1. This is
the same defect measured on **train_s3**, a different file, and it points the
other way from what the gate assumes.

## Findings

### 1. Shape and share of file

| Quantity | Value | Profile field / arithmetic |
|---|---|---|
| Rows in file | 5,285,603 | `rows` |
| US rows | 3,170,056 | `by_country.US.rows` (= `country_rows.US`) |
| India rows | 2,115,547 | `by_country.India.rows` |
| **US share of file** | **59.9753%** | 3,170,056 / 5,285,603 |
| India share of file | 40.0247% | 2,115,547 / 5,285,603 |
| Country count | 2 (`US`, `India`) | `by_country` keys — **no France in train** |
| Columns | `entity_id, business_name, business_address, country` | `cols` |
| US : India row ratio | 1.498x | 3,170,056 / 2,115,547 |

`3,170,056 + 2,115,547 = 5,285,603` — the two country blocks account for 100% of
rows, so no third country is hidden in this file.

### 2. Null / emptiness rates (US, then India for contrast)

| Metric | US | Rate (÷ US rows) | India | Rate (÷ India rows) |
|---|---|---|---|---|
| `name_empty` | **0** | **0.0000%** | 0 | 0.0000% |
| `addr_empty` | 110,968 | **3.5005%** | 64,948 | 3.0700% |
| `prefix_bad` | **0** | **0.0000%** | 0 | 0.0000% |

Arithmetic: 110,968 / 3,170,056 = 0.035005; 64,948 / 2,115,547 = 0.030700.

**Reading:** `name_empty = 0` and `prefix_bad = 0` mean the US slice has no name
nulls and no `entity_id` prefix violations at all — a clean result, not a defect.
The 3.5% address null rate is the only null-ish quantity in the slice, and
`prep.py:23` (`df["business_address"].fill_null("")`) already absorbs it, so it
degrades gracefully to an empty token list rather than raising.

### 3. Lengths and digit statistics

| Metric | US | India |
|---|---|---|
| `name_chars` | 76,009,139 | 57,199,388 |
| **mean name length** | **23.977 ch** = 76,009,139 / 3,170,056 | 27.038 ch = 57,199,388 / 2,115,547 |
| `addr_chars` | 121,873,446 | 125,040,524 |
| **mean addr length (all rows)** | **38.445 ch** = 121,873,446 / 3,170,056 | 59.106 ch = 125,040,524 / 2,115,547 |
| **mean addr length (non-empty only)** | **39.840 ch** = 121,873,446 / 3,059,088 | 60.975 ch = 125,040,524 / 2,050,599 |
| `name_tokens` / name | 3.635 = 11,522,038 / 3,170,056 | 3.324 = 7,032,501 / 2,115,547 |
| `num_digits` / row | 3.979 = 12,614,249 / 3,170,056 | 3.772 = 7,979,194 / 2,115,547 |
| `has_digit_name` | 199,652 → **6.2981%** | 71,195 → 3.3653% |
| `alpha_only_addr` | 164,957 → 5.2036% | 145,433 → 6.8748% |

The two mean-address figures differ because `addr_chars` counts empty strings as
0 characters; I give both so the denominator is never ambiguous.

`has_digit_name` at 6.30% is the rate at which a business name contains a digit —
material for `keys.py:35-38`, which derives blocking prefixes from `ncore` only.

### 4. Name-length histogram (US, `len_hist`)

| Bucket (chars) | Count | % of US | Cumulative % |
|---|---|---|---|
| 0–9 | 117,192 | 3.697% | 3.697% |
| 10–19 | 968,304 | 30.545% | 34.242% |
| **20–29** | **1,276,652** | **40.272%** | **74.514%** |
| 30–39 | 628,392 | 19.823% | 94.337% |
| 40–49 | 149,220 | 4.707% | 99.044% |
| 50–59 | 26,607 | 0.839% | 99.884% |
| 60–69 | 3,417 | 0.108% | 99.991% |
| 70–79 | 259 | 0.008% | 100.000% |
| 80–89 | 13 | 0.000% | 100.000% |
| **Total** | **3,170,056** | 100% | — |

The bucket sum equals `by_country.US.rows` exactly (verified: diff = 0), so the
histogram is complete and loses no rows. The distribution is unimodal and
right-skewed with a hard ceiling: **99.044% of US names are ≤49 characters and
only 0.956% reach 50+** (26,607 + 3,417 + 259 + 13 = 30,296; 30,296 / 3,170,056
= 0.9557%). The US histogram's top bucket is 80–89, whereas India's extends to
120 — US names are markedly shorter (mean 23.98 vs 27.04), consistent with
India's compounding multi-word transliterations.

### 5. Comma structure — an exact identity

| Quantity | US | India |
|---|---|---|
| `rows` | 3,170,056 | 2,115,547 |
| `addr_empty` | 110,968 | 64,948 |
| `rows − addr_empty` | **3,059,088** | 2,050,599 |
| `has_comma` | **3,059,088** | 2,050,598 |
| Difference | **0** | **1** |
| `has_comma` / rows | 96.4995% | 96.9299% |

For the US, `has_comma` equals `rows − addr_empty` **to the row**. The only
consistent reading is that **100% of non-empty US addresses contain at least one
comma**, which is exactly the structure `normalize.py:322` (`comps = [c.strip()
for c in s.split(",")]`) depends on for component-wise state matching. India is
off by exactly one row (2,050,599 vs 2,050,598), implying a single Indian
address with content but no comma. I flag that as a curiosity, not a defect.

This matters because the whole `state` resolution path in `normalize.py:328-335`
matches *whole comma components* against `STATE_MAPS`. The US slice is uniformly
comma-delimited, so that path is well-founded here.

### 6. Digit-run density and the `pin` gate

`normalize.py:336-338` captures `pin` only when `len(n) == 6 and country ==
"India"`. The profile's `dig5` / `dig6` count standalone digit runs of exactly
5 and 6 digits.

| | US | India |
|---|---|---|
| `dig5` | 341,738 → **10.7802%**/row | 22,317 → 1.0549%/row |
| `dig6` | 42,321 → **1.3350%**/row | 410 → **0.01938%**/row |
| `dig6`/`dig5` ratio | 0.124 | 0.018 |

**US/India `dig6` ratio = 42,321 / 410 = 103.2x.** The US carries 103x the
six-digit density of the one country the gate admits, despite holding only 1.498x
the rows. Per-row: US 0.01335 vs India 0.000194, a **69x** per-row gap.

Consistent with the `already_checked` note that US ZIPs (5-digit) are lost to the
gate, `dig5` dominates the US at 10.78% while `dig6` is 1.34%. The India side is
the part that surprises: only **410 Indian rows in the entire 5.29M-row file
(0.0194% of India, 0.0078% of the file)** can ever satisfy the gate. Measured
against `run_blocking.py:9` and `keys.py:44,58`, which promote `pin` into a
first-class blocking key (`"pin" + pin`), that key is **effectively inert for
India and entirely absent for the US in this slice.**

## Interpretation

*The following is inference, clearly separated from the measurements above.*

1. **The `pin` gate is inverted for this slice (high confidence, direct from
   measurement + code).** `pin` is a blocking key, so its value is the number of
   candidate pairs it can generate. Confining it to India caps it at 410 rows
   (0.0194% of India) while 42,321 US rows carrying a 6-digit number (1.3350% of
   US) are excluded. Extending the gate to the US would raise the address-side
   blocking key population from ≤410 to ≤42,731 rows — a 104x increase in the
   rows eligible to contribute that key. Whether that *improves* recall depends
   on false-positive volume, which I cannot measure from this profile.

2. **The empty-address rate is not a defect and is already handled (high
   confidence).** `prep.py:23` null-fills before normalisation, so 110,968 US
   rows produce an empty `atoks` rather than an error. A 3.5% address-null rate
   is a recall ceiling on those rows, not a crash risk.

3. **The uniform comma structure is favourable, not a problem (high
   confidence).** Because 100% of non-empty US addresses are comma-delimited,
   `normalize_address`'s component loop sees a consistent field layout, which is
   the precondition for its exact-match state lookup to work at all.

4. **Name-length concentration argues against truncating `ncore` early (low
   confidence, advisory).** With 99.04% of US names ≤49 chars and 74.5% in a
   single 10-wide bucket, any character-budget truncation used for blocking keys
   would need to sit above ~50 chars to avoid collisions in the tail. I have no
   measurement of the current budget, so treat this as a caution, not a finding.

## Is the slice large enough to conclude from?

**Yes, comfortably.** At n = 3,170,056, a proportion near 0.5 has a 95% margin
of error of roughly ±0.055 percentage points (1.96·√(0.25/3,170,056)), and the
3.5005% address-null rate carries roughly ±0.020 pp. Differences of more than a
tenth of a percentage point are real. Two caveats on scope, not on precision:

- **This slice cannot speak to France.** `train_source3` contains only `US` and
  `India`. Any France claim needs the `test_s1/2/3` profiles, which I did not open.
- **Per-row `dig5`/`dig6` count occurrences, not distinct rows.** The 0.01938%
  India `dig6` figure is a count of standalone 6-digit runs per 2,115,547 rows. A
  row with two 6-digit runs counts twice, so the true *fraction of rows* holding
  one is ≤0.01938%. The conclusion (the gate is inert for India) holds either
  way, since the upper bound is the number I used.

## Gaps

Stated explicitly rather than estimated:

- **No per-row flag for "contains a 5/6-digit number".** `dig5`/`dig6` are
  occurrence counts. Exact row-level rates are unavailable; my figures are
  occurrences-per-row and are upper bounds on distinct-row rates.
- **`num_digits` provenance is ambiguous.** The field name does not say whether
  it counts digits in the name, the address, or both. I report it as a raw
  per-row ratio (3.979 US / 3.772 India) and draw no conclusion from it.
- **`alpha_only_addr` may include empty addresses.** 164,957 − 110,968 = 53,989
  non-empty alphabetic US addresses; the profile does not document whether the
  110,968 empty ones are counted in that 164,957.
- **The `entity_id` prefix rule is not in the profile.** `prefix_bad = 0` is a
  clean result, but I could not verify *which* prefix convention was checked, so
  I report only that zero rows were flagged.
- **No duplicate-row or unique-entity count was collected**, so I cannot say how
  many distinct businesses the 3,170,056 US rows represent, nor whether the
  entity-resolution target rate within this slice is achievable.
- **No `city` or component-position breakdown** in this profile; the
  component-order question raised in `already_checked` is out of reach here.

## Recommendations

1. **[Medium priority] Re-examine the `country == "India"` condition on
   `normalize.py:337`.** Evidence: US `dig6`/row 0.01335 vs India 0.000194, a 69x
   per-row gap; 42,321 US rows vs 410 India rows carry a 6-digit run. Expected
   effect: the `pin` blocking key goes from ≤410 eligible rows to ≤42,731 across
   the file, a 104x increase in address-side key population. *Before changing
   it*, measure the false-positive rate this admits — the profile cannot answer
   that, and a 104x key increase is not automatically a win. Note the
   `already_checked` block already flags the US side; this work order supplies
   the independent train_s3 measurement and shows the India side is nearly
   vacuous, which the earlier note did not quantify.
2. **[Low priority, no change] Do not "fix" the 3.5% empty-address rate.** It is
   already absorbed by `prep.py:23`, and `name_empty`/`prefix_bad` are both 0.
   Manufacturing a change here would be noise.
3. **[Informational] No change needed for comma/component handling.** With
   `has_comma` == `rows − addr_empty` exactly, US addresses are uniformly
   comma-delimited and the existing component-splitting logic is well-founded on
   this slice. Leave it alone.
4. **[Low priority] Consider adding a row-level `has_5digit` / `has_6digit`
   boolean to the profile schema** so a future round can report distinct-row
   rates rather than occurrence-per-row upper bounds, and can settle questions
   like this one without a bounds argument.

## Relation to the two refuted findings

Stated plainly, as required:

- **REFUTED-1 (French postal codes discarded by the pin guard).** I did **not**
  re-derive this. My slice contains no France rows at all, so it can neither
  confirm nor contradict a France claim. My §6 result concerns the **US and
  India in train_s3** and 6-digit runs, not French 5-digit postcodes.
- **REFUTED-2 (FR_REGIONS too thin).** Out of scope for this file; no France
  rows exist in `train_source3`. I make no claim about it.

Nothing in my evidence supports either refuted finding.

## Recommendation confidence markers

| Item | Marker | Basis |
|---|---|---|
| US `dig6`/row = 0.01335, India = 0.000194 | **CONFIRMED** | direct profile fields, arithmetic shown |
| `has_comma` == `rows − addr_empty` for US | **CONFIRMED** | exact integer identity on two profile fields |
| `pin` gate admits ≤410 India rows | **CONFIRMED** | `dig6` = 410, an upper bound |
| `pin` gate excludes 42,321 US rows | **CONFIRMED** | `dig6` = 42,321 |
| The gate *should* be widened to the US | **LIKELY** | signal asymmetry is measured; recall benefit is not |
| False-positive cost of widening | **SPECULATIVE** | not measured by any profile field |
| Component-order / city analysis | **SPECULATIVE (abandoned)** | fields not collected in this profile |
