
# P005 — [US] test_s2: shape, null rates, length distribution

Source of record: `analysis_out/profile/test_s2.json` (`split=test`, `source=2`).
No raw `*.tsv` was opened. Every number below is a named profile field or arithmetic
on named fields. Field semantics were pinned by reading `build_profile.py`
(lines 79–136) before quoting anything. `_upstream/src/normalize.py` was read
read-only, and imported read-only to demonstrate mechanism on **synthetic strings**.

## Headline

The US slice of `test_source2` is **1,871,330 rows, 38.290% of the 4,887,273-row
file**, and it is clean on every integrity axis: **zero** empty names, **zero**
malformed `entity_id` prefixes, and a name-length histogram that sums *exactly* to
the row count. It is more than large enough to conclude from (every rate below is
pinned to ±0.04pp at 95%).

The important result of this work order is not a US defect — it is that **the
US-wide comma invariant that siblings P002/P003 reported is exact but not
universal, and it breaks on France in the very file I was assigned.** Across all
six profile files the identity `has_comma == rows − addr_empty` holds for
**11,990,643 / 11,990,643 US rows (zero exceptions)**, but for **France it fails
on 180 rows in test_s2** and 153 in test_s3. Those rows parse to a single
component, and `normalize.py` requires a *whole* component to equal a region key
before it will emit a state — so **France's state resolution in test_s2 is
bounded above at 99.9744%, not 100.00%**. The `already_checked` note quoting
"100.00% (259,452 / 259,452, zero unmatched)" is correct, but it was measured on
**test_s1 only**, which happens to contain exactly zero comma-less France rows.
This is new, and it is France-specific.

## Findings

### 1. Shape and share of file

| Quantity | Value | Field / arithmetic |
|---|---|---|
| Rows in file | 4,887,273 | `rows` |
| US rows | 1,871,330 | `by_country.US.rows` |
| India rows | 2,312,565 | `country_rows.India` |
| France rows | 703,378 | `country_rows.France` |
| **US share of file** | **38.2899%** | 1,871,330 / 4,887,273 = 0.382899 |
| India share | 47.3183% | 2,312,565 / 4,887,273 |
| France share | 14.3918% | 703,378 / 4,887,273 |
| Countries present | `US`, `India`, `France` | `country_rows` keys |
| Columns | `entity_id, business_name, business_address, country` | `cols` |

**Invariant 1 (holds):** `country_rows` sums to `rows` —
2,312,565 + 703,378 + 1,871,330 = 4,887,273. No country is hidden, and the three
`by_country[*].rows` values independently agree with `country_rows`.

### 2. Null / integrity rates (all ÷ `by_country.US.rows` = 1,871,330)

| Field | Count | Rate | Arithmetic |
|---|---|---|---|
| `name_empty` | **0** | **0.0000%** | exact zero |
| `addr_empty` | 55,107 | **2.9448%** | 55107/1871330 = 0.029448 |
| `prefix_bad` | **0** | **0.0000%** | exact zero |
| `has_comma` | 1,816,223 | 97.0552% | 1816223/1871330 |
| `has_digit_name` | 115,616 | **6.1783%** | 115616/1871330 = 0.061783 |
| `alpha_only_addr` | 93,584 | 5.0009% | 93584/1871330 = 0.050009 |
| `dig5` | 205,296 | 0.10971/row | 205296/1871330 |
| `dig6` | 26,757 | 0.01430/row | 26757/1871330 |

`prefix_bad = 0` is a non-vacuous check: `build_profile.py:94` evaluates
`eid.startswith(f"S{src}-")` per row with `src=2`, so 0/1,871,330 means the
`S2-` prefix is a valid partition key for **100%** of US rows in this file.
**No prefix repair is needed.**

### 3. Lengths

| Quantity | Value | Arithmetic |
|---|---|---|
| Mean name length | **24.2854** chars | `name_chars` 45,446,046 / 1,871,330 |
| Mean address length (all rows) | **31.8433** chars | `addr_chars` 59,589,379 / 1,871,330 |
| Mean address length (non-empty only) | 32.8095 | 59,589,379 / 1,816,223 |
| Mean name tokens/row | 3.6569 | `name_tokens` 6,843,339 / 1,871,330 |

| Address digits/row | 3.8344 | `num_digits` 7,175,415 / 1,871,330 |
| Address digit share of address chars | 12.0414% | 7,175,415 / 59,589,379 |

The two mean-address figures differ by exactly the null rate, because
`build_profile.py:102-103` adds `len(bn)`/`len(ba)` of the **stripped** string and
`len("") == 0`. `num_digits` counts digits in the **address only**
(`build_profile.py:114`, `sum(ch.isdigit() for ch in ba)`); the digit-in-name
signal is the separate `has_digit_name` field.

### 4. Name-length histogram (`len_hist`, bucketed by `len//10*10`)

| Name length | Rows | % of US rows |
|---|---|---|
| 0–9 | 48,007 | 2.5650% |
| 10–19 | 543,976 | 29.0694% |
| 20–29 | 788,682 | 42.1460% |
| 30–39 | 399,910 | 21.3699% |
| 40–49 | 80,348 | 4.2940% |
| 50–59 | 9,546 | 0.5101% |
| 60–69 | 799 | 0.0427% |
| 70–79 | 58 | 0.0031% |
| 80–89 | 4 | 0.0002% |
| **Total** | **1,871,330** | **100.0000%** |

**Invariant 2 (holds, exactly):** `len_hist` sums to `rows`, 1,871,330 = 1,871,330.
Cumulative: 31.634% of names are ≤19 chars, **95.150% are ≤39 chars**, and only
0.556% exceed 49 chars. Because `name_empty = 0`, all 48,007 rows in the 0–9
bucket hold names of length 1–9, not empty strings.

**Consistency check on the histogram.** Summing the per-bucket minimum and
maximum possible `name_chars` gives a bound of
[36,954,240 , 53,796,210] and the measured `name_chars` = 45,446,046 falls inside
it, implying a mean offset of +4.538 chars above each bucket floor. The
histogram and the character total are mutually consistent.

### 5. Is the slice large enough to conclude from? — Yes

n = 1,871,330. 95% binomial half-widths:

| Field | Rate | 95% CI half-width | Rows equivalent |
|---|---|---|---|
| `addr_empty` | 2.9448% | ±0.0242pp | ±453 |
| `has_digit_name` | 6.1783% | ±0.0345pp | ±646 |
| `has_comma` | 97.0552% | ±0.0242pp | ±453 |
| `alpha_only_addr` | 5.0009% | ±0.0312pp | ±584 |

Every rate is known to four decimal places; the smallest effect discussed below
(180 rows = 0.0096pp) is **~19x smaller than the sampling error on `addr_empty`**,
which is precisely why it is only detectable as an *exact integer* discrepancy
against a structural identity rather than as a rate difference.

### 6. THE NEW FINDING — the comma invariant is exact for US and **breaks for France**

**Identity:** `has_comma == rows − addr_empty`, i.e. *every non-empty address
contains a comma.*

| File | Country | rows | non-empty | `has_comma` | **comma-less** | % of rows |
|---|---|---|---|---|---|---|
| train_s1 | US | 1,323,633 | 1,323,633 | 1,323,633 | **0** | 0.0000% |
| train_s2 | US | 3,016,817 | 2,905,696 | 2,905,696 | **0** | 0.0000% |
| train_s3 | US | 3,170,056 | 3,059,088 | 3,059,088 | **0** | 0.0000% |
| test_s1 | US | 663,106 | 663,106 | 663,106 | **0** | 0.0000% |
| **test_s2** | **US** | **1,871,330** | **1,816,223** | **1,816,223** | **0** | **0.0000%** |
| test_s3 | US | 1,945,701 | 1,890,384 | 1,890,384 | **0** | 0.0000% |
| test_s1 | France | 259,452 | 259,452 | 259,452 | **0** | 0.0000% |
| **test_s2** | **France** | **703,378** | **681,841** | **681,661** | **180** | **0.0256%** |
| **test_s3** | **France** | **731,615** | **710,074** | **709,921** | **153** | **0.0209%** |
| test_s2 | India | 2,312,565 | 2,259,801 | 2,259,799 | 2 | 0.0001% |
| test_s3 | India | 2,405,000 | 2,345,760 | 2,345,759 | 1 | 0.0000% |
| train_s3 | India | 2,115,547 | 2,050,599 | 2,050,598 | 1 | 0.0000% |

Pooled: **US 0 of 11,990,643 (0.000000%)**; **France 333 of 1,694,445
(0.01965%)**; India 4 of 10,544,085 (0.00004%).

The US identity is not approximate — it is exact to the row in all six files.

**Why it matters, demonstrated on the real code** (`normalize.py:322-352`,
imported read-only, run on synthetic strings only):

```python
comps = [c.strip() for c in s.split(",")]        # line 322
...
if ck in smap:                                   # line 333 - WHOLE component
    state = smap[ck]; continue
...
if not any(ch.isdigit() for ch in c) and ctoks:  # line 351 - digit-free only
    city_comps.append(" ".join(ctoks))
```

Observed outputs:

| Input (France) | `state` | `city_comps` |
|---|---|---|
| `'175 Boulevard du President Franklin Roosevelt'` (digit-bearing) | `''` | `[]` |
| `'rue de la Paix'` (digit-free, not a region) | `''` | `['rue de la paix']` |
| `'ile de france'` (digit-free, IS a region key) | `'idf'` | `[]` |
| `'Bordeaux'` | `''` | `['bordeaux']` |

A comma-less address is a **single** component, so a state is emitted only if the
*entire* address string equals a region key — which is impossible for a real
street address. If that whole address contains a house number, it also fails the
digit-free test at line 351, so `city_comps` is empty too: **the row loses both
its region and its city signal.**

**Consequence for France, stated as a bound.** The 180 comma-less France rows in
test_s2 *cannot* resolve a state unless the entire address is a region name, so:

- state resolution in France test_s2 is **at most (703,378 − 180) / 703,378 =
  99.9744%**, a shortfall of **at most 180 rows**;
- test_s3: at most 99.9791% (≤153 rows);
- test_s1: 100.0000% (0 such rows) — which is why the earlier measurement saw
  zero unmatched.

This is an **upper bound on the shortfall, not a measured failure count.** The
profile cannot tell me what those 180 strings contain (see Gaps).

### 7. Relation to the two REFUTED findings

- **REFUTED-1 (French postal codes discarded by the `pin` guard).** I did **not**
  re-derive it, and my evidence does **not** support it. US `dig5`/row here is
  0.10971, consistent with the 0.110 figure in the `already_checked` block, so US
  rows are rich in 5-digit numbers. France in *this* file has `dig5` = 3,613 over
  703,378 rows = 0.00514/row, matching the 0.005 quoted for test_s2. The pin guard
  is a real code defect whose impact is on **US source-1 / India**, not France.
- **REFUTED-2 (FR_REGIONS too thin ⇒ no usable state signal).** I did not
  re-derive the core claim, and I largely **agree** with it: `FR_REGIONS` has 14
  entries covering 4 canonical values, and state resolution is near-total.
  **But I must flag one qualification, loudly, with the numbers:** the
  "100.00% (259,452 / 259,452, zero unmatched)" figure is true for **test_s1
  only**. In test_s2 the provable upper bound is **99.9744% (180 rows)**, and in
  test_s3 **99.9791% (153 rows)**. This does not rehabilitate REFUTED-2 — 0.026%
  is immaterial next to a 14-vs-52 dictionary gap — but it corrects a number that
  was carried into the record as file-independent, and it is France-specific.

## Interpretation (inference, marked as such)

1. **The US comma invariant is safe to rely on and safe to stop relying on.**
   `has_comma` is provably an exact alias of `addr_empty` for all 11,990,643 US
   rows in the corpus, so a US feature gated on comma presence is a duplicate of
   the address-null signal. *Inference*: I did not read the feature builder, so I
   cannot say whether such a feature exists — the follow-up is to grep
   `build_features.py` / `features.py` for comma conditions. No accuracy change is
   expected on US either way.
2. **The invariant is a property of the US address *generator*, not of the
   pipeline.** Its exactness across six files and 12M rows, and its
   near-exactness for India, suggests the US/India addresses are emitted from a
   fixed `"street, city, state zip"` template. France, which is generated
   differently (and is the only scored country), leaks 180 template violations.
   *Inference*, from the pattern — the profile contains no generator information.
3. **The France leak is small but points at a real robustness hole.** 0.026% of
   France rows is too small to move the leaderboard, but it is a *category* of
   input the normalizer cannot represent at all: single-component addresses. A
   city-then-region or region-then-city ordering assumption would break the same
   way. *Inference* about ordering — the profile collects no component-position
   data (see Gaps), so I cannot confirm any ordering assumption exists in
   `build_features.py`.

## Gaps

Fields **not collected** by `build_profile.py`, therefore not answerable here and
**not estimated** anywhere above:

- **Content of the 180 comma-less France rows.** I can prove they are
  non-empty, comma-free, and single-component. I **cannot** say whether they are
  region names (which would still resolve a state), whether they carry a house
  number (which would also kill `city_comps`), or what their token content is.
  The 180 figure is therefore strictly an **upper bound** on state loss. Closing
  this needs a `n_comps` field.

- **No `n_comps` / component-count / component-position field.** This is the
  single largest blind spot in the profile and it is what blocks the
  component-order question raised in my `already_checked` block.
  `build_profile.py:126` splits on `[,;]` only to feed the token counter, and
  **discards the component count**.
- **No `pin` field, and no row-level `has_5digit` / `has_6digit` boolean.**
  `dig5`/`dig6` are *occurrence* counts (`len(findall(...))`, lines 115–116), not
  row counts, so 205,296 is an upper bound on US rows carrying a standalone
  5-digit run. I report them as occurrences/row, never as row rates.
- **Whether `alpha_only_addr` includes empty addresses.** `build_profile.py:117`
  is `if ba and not any(...)`, so empty addresses are **excluded** — reading the
  builder resolves the ambiguity P003 flagged as a gap. I verified this in source
  rather than inferring it. The count 93,584 is a subset of the 1,816,223
  non-empty rows (5.1527% of non-empty).
- **No `state` / `city` / `region` field.** `normalize_address`'s outputs are
  never captured by the profiler, so §6 is a *bound derived from upstream code
  plus the comma identity*, not a direct measurement of state resolution.
- **No true-empty vs whitespace-only distinction.** The builder `.strip()`s before
  testing emptiness (lines 96–101), so `"   "` is already counted as empty.
- **Token counters are top-4000 and pruned of hapax** (`prune`, line 45), so no
  vocabulary size, type-token ratio, or unique-business count is derivable.

## Recommendations

1. **[High priority, NEW] Add a `n_comps` field to `build_profile.py`.** Record
   `len([c for c in ba.split(",") if c.strip()])` per row. One field converts my
   bound (≤180 France rows) into a measured count, and it is also the only way to
   settle the component-order question that two prior rounds have flagged and
   could not reach. Expected effect: pure diagnostic, no pipeline change, one
   extra streaming counter at negligible cost.
2. **[Medium priority] Make `normalize_address` tolerate single-component
   addresses.** Currently `normalize.py:333` requires a whole component to equal
   a region key. A fallback that runs region matching on the *last* (or first)
   comma-component's trailing tokens would recover state for those rows.
   *Confidence: the failure mechanism is **CONFIRMED** (demonstrated on real code);
   the fix and its recall/precision tradeoff are **SPECULATIVE** — the profile
   cannot tell me what the 180 strings are, so I cannot estimate the gain.
   Expected effect: ≤180 France rows in test_s2 and ≤153 in test_s3 regain a
   region signal. Do **not** expect a leaderboard move at 0.026%.
3. **[No change] Do not add null handling, prefix repair, or name handling for
   US test_s2.** `name_empty = 0` and `prefix_bad = 0` are exact zeros. The
   2.9448% address-null rate is already absorbed by `prep.py:23`
   (`fill_null("")`). Manufacturing a fix here would be noise.
4. **[No change] No dictionary entry is warranted from this slice.** I propose no
   `CONFIRMED`/`LIKELY`/`SPECULATIVE` normalisation-dictionary entries: this work
   order is a shape/null-rate profile and produced evidence of a *parser*
   robustness gap, not a missing token.
5. **[Low priority, informational] Record the comma invariant as a
   corpus-level fact with its exception count**, so future agents do not
   re-generalise it from US to France. The honest statement is: *exact for
   11,990,643 US rows; violated by 333 France rows (0.0197%) and 4 India rows.*

## Confidence markers

| Claim | Marker | Basis |
|---|---|---|
| US test_s2 = 1,871,330 rows, 38.2899% of file | **CONFIRMED** | `rows`, `by_country.US.rows`, arithmetic shown |
| `len_hist` sums exactly to `rows` | **CONFIRMED** | exact integer identity |
| `country_rows` sums exactly to `rows` | **CONFIRMED** | exact integer identity |
| `name_empty` = 0, `prefix_bad` = 0 | **CONFIRMED** | exact zeros, `build_profile.py:94,98` |
| US comma invariant exact in all 6 files | **CONFIRMED** | 0 exceptions in 11,990,643 rows |
| France test_s2 has 180 comma-less non-empty rows | **CONFIRMED** | exact integer `703,378 − 21,537 − 681,661` |
| A comma-less component yields `state = ''` | **CONFIRMED** | executed real `normalize.py` on synthetic strings |
| France state resolution ≤ 99.9744% in test_s2 | **CONFIRMED as a bound** | arithmetic; the *attainability* is untested |
| Those 180 rows also lose `city_comps` | **LIKELY** | true iff they contain a house number; profile cannot tell |
| The invariant reflects a fixed generator template | **SPECULATIVE (inference)** | pattern-based, no generator data |
| A last-component region fallback would help | **SPECULATIVE** | fix not measured, content of the 180 unknown |
| Component order is inconsistent in French rows | **SPECULATIVE (abandoned)** | no `n_comps`/position field exists |
