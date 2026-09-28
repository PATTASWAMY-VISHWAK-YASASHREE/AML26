# P013 — [France] train_s1: shape, null rates, length distribution

**Status: COMPLETE (headline is negative).**
**Agent:** b04 · **Family:** A-profile · **Profile input:** `analysis_out/profile/train_s1.json`
**Source of every number below:** the compact profile JSON. No raw TSV was opened.

---

## 1. HEADLINE — THE FRANCE SLICE IN train_s1 IS EMPTY

**There is no `France` key anywhere in `train_s1.json`.** The profile was built with
`json.dump` from a `dict(country_rows)`, so a country with zero rows simply produces no
key at all — absence, not a zero entry.

```
$ j.country_rows  ->  keys: US, India
$ j.by_country    ->  keys: US, India
$ j.name_tokens   ->  keys: US, India
$ j.addr_tokens   ->  keys: US, India
```

The field and the arithmetic:

| Quantity | Value |
|---|---|
| `train_s1.json` → `rows` (whole file) | **2,206,821** |
| `country_rows["US"]` | 1,323,633 |
| `country_rows["India"]` | 883,188 |
| `country_rows` keys present | `US`, `India` — **no `France`** |
| Sum of `country_rows` | 1,323,633 + 883,188 = **2,206,821 = `rows` exactly** |
| **France rows in train_s1** | **0** |
| **France share of train_s1** | **0 / 2,206,821 = 0.000000% — exactly 0** |

The sum closing on `rows` to the row is the denominator check the brief asks for: the
country breakdown is complete and France is not hiding inside it.

## 2. CONSEQUENCE — EVERY FRANCE RATE REQUESTED IN THIS WORK ORDER IS UNDEFINED

The work order asks for, per France: empty-name rate, empty-address rate, mean name
length, mean address length, the name-length histogram, digit-in-name rate,
comma-in-address rate, and entity_id prefix validity. **None of these can be computed
for this slice.** Each is a ratio of the form `f(France) / rows(France)`, and
`rows(France) = 0`. They are 0/0 — **undefined, not 0%**.

I am explicitly declining to report these as "0%". A "0% France empty-name rate in
train_s1" would be a fabricated figure: it asserts that 0 France rows lacked names,
whereas the truth is that no France rows were observed at all. **Reporting is what the
retracted "100% of France rows resolve a state" figure did in the opposite direction** —
it read a zero-denominator artifact as a measured rate.

> ### ⚠️ THE TRAP, STATED PLAINLY
> **Any France rate computed against a train-file France denominator is meaningless.**
> That is exactly the error that produced the retracted figure earlier in this project.
> If you are handed "100%" (or "0%", or "50%") for any France train statistic, check
> the denominator first. If it came from a train file, it is an artifact.

## 3. WHY THIS IS THE EXPECTED, CORRECT ANSWER (not a data gap)

France has **zero training rows in any of the three train files** — measured, not
inferred:

| Profile file | `rows` | `country_rows` keys | France |
|---|---|---|---|
| `train_s1.json` | 2,206,821 | `US`, `India` | **absent** |
| `train_s2.json` | 5,034,616 | `India`, `US` | **absent** |
| `train_s3.json` | 5,285,603 | `US`, `India` | **absent** |
| `test_s1.json` | 1,732,544 | `US`, `France`, `India` | 259,452 |
| `test_s2.json` | 4,887,273 | `India`, `France`, `US` | 703,378 |
| `test_s3.json` | 5,082,316 | `India`, `France`, `US` | 731,615 |

Total train rows across all three sources: 2,206,821 + 5,034,616 + 5,285,603 =
**12,527,040, of which France = 0**.
Total France test rows: 259,452 + 703,378 + 731,615 = **1,694,445**.

The codebase already encodes this. Two independent confirmations, both verified by
reading the pinned clone at 8445b7f (read-only):

- `_upstream/src/crossfit.py:112` — `for c in ("US", "India"):`. The stage-2
  crossfit loop is hard-coded to two countries. **France is never trained on, by
  construction.** Line 122 concatenates `cf_best_{c}` over the same two-country tuple.
- `_upstream/src/decoy_postfilter.py:17-18` — the rule is stated as *"the country has
  no training labels (e.g. France in the test set)"*. The authors documented the
  condition in prose.

So the France-train gap is **intentional and correctly handled downstream**, not an
oversight to fix. The label-free path is decoy post-filtering by prior
(`decoy_postfilter.py` rule (b)), not a learned per-country threshold.


## 4. THE CONTRAST, WITH REAL NUMBERS (what this slice *can* support)

Since the France-train cell is empty, here are the two countries that do occupy
train_s1, and the France **test** slice, so the train-vs-test contrast is on the record.

All rates derived as `f / by_country[c].rows` per the profile's semantics.

| Statistic (profile field) | US (train_s1) | India (train_s1) | **France (test_s1)** |
|---|---|---|---|
| `rows` | 1,323,633 | 883,188 | 259,452 |
| Share of its file | 59.9805% | 40.0195% | 14.9762% |
| `name_empty` / rate | 0 / 0.0000% | 0 / 0.0000% | 0 / 0.0000% |
| `addr_empty` / rate | 0 / 0.0000% | 0 / 0.0000% | 0 / 0.0000% |
| `name_chars`/rows | 29,735,558 → **22.4651** | 23,304,068 → **26.3863** | 5,039,314 → **19.4229** |
| `addr_chars`/rows | 46,277,429 → **34.9624** | 68,623,397 → **77.6996** | 12,990,984 → **50.0709** |
| `has_digit_name` / rate | 34,494 / **2.6060%** | 1,091 / **0.1235%** | 2,002 / **0.7716%** |
| `has_comma` / rate | 1,323,633 / **100.0000%** | 883,188 / **100.0000%** | 259,452 / **100.0000%** |
| `prefix_bad` / rate | 0 / **0.000000%** | 0 / **0.000000%** | 0 / **0.000000%** |
| `dig5` / per row | 145,393 / 0.10984 | 2,668 / 0.00302 | 1,082 / 0.00417 |
| `dig6` / per row | 1,656 / 0.00125 | 182 / 0.00021 | 34 / 0.00013 |
| `alpha_only_addr` | 1 / 0.0001% | 77,036 / 8.7225% | not queried |

**France mean name is 3.0 chars shorter than the nearest train country** (19.42 vs
22.47 US) and French addresses are 43% longer than US (50.07 vs 34.96). This is a real
distribution shift and it is consistent with France being label-free: nothing in the
pipeline calibrates to the French name/address length profile. *(Marked as INFERENCE
about consequence; the three means above are the measured part.)*

Note `dig5/row` for France test_s1 is **0.00417**, which reproduces the
already-checked figure in the work order (0.004). **No conflict** — consistent, and I
am not re-deriving that finding.

## 5. NAME-LENGTH HISTOGRAM (train_s1) — `len_hist` key = `len(business_name)//10*10`

Both bins sums equal `rows` exactly (verified), so the histograms are complete partitions.

**US (denominator 1,323,633):**
```
   0-9     37,180    2.809%
  10-19   454,546   34.341%
  20-29   601,278   45.426%   <- mode
  30-39   208,949   15.786%
  40-49    20,636    1.559%
  50-59     1,015    0.077%
  60-69        29    0.002%
  ----------------------
      sum 1,323,633  == rows  OK
```

**India (denominator 883,188):**
```
   0-9      8,142    0.922%
  10-19   168,704   19.102%
  20-29   379,327   42.950%   <- mode
  30-39   296,081   33.524%
  40-49    29,678    3.360%
  50-59       987    0.112%
  60-69       185    0.021%
  70-79        56    0.006%
  80-89        24    0.003%
  90-99         2    0.000%
 100-109        2    0.000%
  ----------------------
      sum   883,188  == rows  OK
```

**France in train_s1: the histogram does not exist.** `by_country.France` is absent,
so `len_hist` for France is not an empty histogram — it is an absent key. Do not read
the absence as "France names are 0 characters long".

## 6. PROFILE FIELD SEMANTICS I RELIED ON (from `build_profile.py`)

Read before quoting anything above. These are the traps:

- `num_digits` counts digits in the **ADDRESS only** — `sum(ch.isdigit() for ch in ba)`,
  line 114. It is a raw digit count, not a row count, and not a name measure.
  *(I did not use `num_digits` for any headline figure; the digit-in-name figure uses
  `has_digit_name`, a separate ROW count, line 106.)*
- `dig5` / `dig6` are **lookaround-guarded**: `(?<!\d)\d{5}(?!\d)` and
  `(?<!\d)\d{6}(?!\d)`, lines 29-30. A digit inside a longer digit run does **not**
  count. My `dig5/row = 0.00417` for France uses these guarded values.
- All per-country stats are **totals across the whole slice**; every rate above is
  derived by dividing by that country's `rows`.
- `prefix_bad` counts rows where `entity_id` does **not** start with `S{src}-`
  (line 94), where `src` is the file's own source number. `train_s1.json` has
  `source: 1`, so the guard string is `S1-`. **`prefix_bad = 0` for both US and India:
  entity_id prefix validity is clean.** (France test_s1 also 0.)
- `name_tokens` / `addr_tokens` are the **top 4000** per country and the counters are
  **periodically pruned** (`prune()`, `PRUNE_EVERY=8`), so token counts are
  lower bounds with a pruned tail, and a token missing from the list means
  "**not in the top 4000**", never "does not occur". I made no claim that depends on
  token absence.
- `build_profile.py` **flattens** address components: `ADDR_SPLIT = [,;]` then
  `TOKEN_RE.findall` per component (lines 126-127), but `has_comma` (line 108) tests
  the *raw* string. So a token count is not automatically a pipeline-visible quantity
  — tokens inside a whole comma-component are not what `normalize.py` exposes to
  `atoks`. Relevant to the RETRACTED function-word finding; I repeat no part of it.
- The profile counts **TOKEN OCCURRENCES, never ROWS**, for `name_tokens`.

## 7. IS THE SLICE LARGE ENOUGH TO CONCLUDE FROM?

**The question is undefined for the France-train cell, not answered negatively.** There
is no slice, so there is no sample size and no confidence interval. You cannot draw a
France train conclusion here at any n, because n = 0.

For the two populations that *are* present, the sample sizes are overwhelming
(1.32M and 0.88M rows) and every rate above is far inside any sampling-error
concern — the standard error on the US 2.6060% digit-in-name rate is
`sqrt(0.02606*0.97394/1323633)` = **0.0138pp** (India's is 0.0037pp). Those
numbers are as firm as this dataset permits. France **test_s1** at 259,452 rows is
likewise large enough for its own descriptive stats (that is precisely the population
the retracted 100% figure mis-scoped to).

## 8. GAPS AND LIMITS OF THIS FINDING

- **Not measured:** anything requiring a France *train* denominator. Not a gap in
  effort — a gap in the data, and unfixable from the provided files.
- **Not measured:** `name_tokens` / `addr_tokens` content for France train. The key is
  absent, so there is no France-train token table.
- **Inferred, not measured:** that the US/India name-length gap implies France is
  uncalibrated. The means are measured; the consequence is marked INFERENCE.
- I did not re-derive anything in the brief's ALREADY RULED OUT list.

## 9. NEW DEFECTS FOUND

**None.** `prefix_bad = 0`, `name_empty = 0`, `addr_empty = 0`, and both `len_hist`
bin sets reconcile exactly to `rows`. The France-zero-train condition is already known
and already handled in code. Per the evidence standard, "no defect found" is the
result — I am not manufacturing a recommendation to look productive.

The one thing worth carrying forward is the **denominator warning in §2**, which is a
reporting-discipline hazard rather than a code defect.
