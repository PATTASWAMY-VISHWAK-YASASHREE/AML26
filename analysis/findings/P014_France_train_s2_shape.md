# P014 — [France] train_s2: shape, null rates, length distribution

**Status: COMPLETE (headline is negative, and that is the correct answer).**
**Agent:** b04b · **Family:** A-profile · **Profile input:** `analysis_out/profile/train_s2.json`
**Source of every number below:** the compact profile JSON. **No raw TSV was opened.**
**Paired work:** P013 (same question for `train_s1`) — §5 covers the deltas and does not
duplicate it.

---


## 1. HEADLINE — THE FRANCE SLICE IN train_s2 IS EMPTY

**There is no `France` key anywhere in `train_s2.json`.** Not a zero-valued entry — the
key is *absent*, from all four country-keyed maps:

```
$ j.country_rows  ->  keys: India, US
$ j.by_country    ->  keys: India, US
$ j.name_tokens   ->  keys: India, US
$ j.addr_tokens   ->  keys: India, US
```

### The field and the arithmetic

| Quantity | Value |
|---|---|
| `train_s2.json` → `rows` (whole file) | **5,034,616** |
| `country_rows["US"]` | 3,016,817 |
| `country_rows["India"]` | 2,017,799 |
| `country_rows` keys present | `India`, `US` — **no `France`** |
| Sum of `country_rows` | 3,016,817 + 2,017,799 = **5,034,616 = `rows` exactly** |
| **France rows in train_s2** | **0** |
| **France share of train_s2** | **0 / 5,034,616 = 0.000000% — exactly 0** |

The sum closing on `rows` to the row is the denominator check the brief demands: the
country breakdown is **complete**, so France is not hiding inside it.

### Why "absent key" is structurally guaranteed, not an accident

`build_profile.py:81-91` — `country_rows[c] += 1` (line 82) and
`stats[c] = {...}` (line 85) are both reached **only inside the per-row loop**. A
`dict(country_rows)` (line 139) therefore cannot emit a key for a country with zero
rows. **Absence of the key is the encoding of "zero rows."** It is a structural proof
that the stream never saw `country == "France"`, not a silent serialisation failure.

## 2. CONSEQUENCE — EVERY FRANCE RATE IN THIS WORK ORDER IS **UNDEFINED**, NOT 0%

The work order asks, per France: empty-name rate, empty-address rate, mean name length,
mean address length, the name-length histogram, digit-in-name rate, comma-in-address
rate, entity_id prefix validity. **None is computable.** Each is `f(France)/rows(France)`
and `rows(France) = 0` → **0/0**.

I explicitly decline to print these as `0%`. "0% France empty-name rate in train_s2"
would assert that 0 France rows lacked names; the truth is that **no France row was
observed at all**. A zero denominator is not a zero rate.

> ### ⚠️ THE TRAP, STATED PLAINLY
> **Any France rate computed against a train-file France denominator is meaningless.**
> This is the exact error behind the retracted *"100% of France rows resolve a state"*
> figure in this project. If you are handed `100%`, `0%` or `50%` for any France **train**
> statistic, check the denominator first. If it came from a train file, it is an artifact.

## 3. THIS IS THE EXPECTED AND CORRECT ANSWER

France has **zero training rows in all three train files** — measured, not inferred:

| Profile | `rows` | `country_rows` keys | France |
|---|---|---|---|
| `train_s1.json` | 2,206,821 | `US`, `India` | **absent** |
| `train_s2.json` | **5,034,616** | `India`, `US` | **absent** |
| `train_s3.json` | 5,285,603 | `US`, `India` | **absent** |
| `test_s1.json` | 1,732,544 | `US`, `France`, `India` | 259,452 |
| `test_s2.json` | 4,887,273 | `India`, `France`, `US` | 703,378 |
| `test_s3.json` | 5,082,316 | `India`, `France`, `US` | 731,615 |

All three train sums close on their own `rows` (verified: `sum_eq_rows=True` for all six
files). Total train rows = 2,206,821 + 5,034,616 + 5,285,603 = **12,527,040, France = 0**.
Total France test rows = 259,452 + 703,378 + 731,615 = **1,694,445**.

**The France train-vs-test contrast, in one line: France is 0.000% of 12,527,040
training rows and 34.7% of 4,694,445 test rows.** France is a *test-only* country in
this competition.

The codebase already encodes this (read-only, pinned clone at 8445b7f):

- `_upstream/src/crossfit.py:112` — `for c in ("US", "India"):` — stage-2 crossfit is
  hard-coded to two countries; **France is never trained on**. Line 122 concatenates
  `cf_best_{c}` over the same tuple, so the model set has no France member.
- `_upstream/src/decoy_postfilter.py:17-18` — *"the country has no training labels
  (e.g. France in the test set)"* — label-free France is handled by rule (b), decoy
  post-filtering by prior, **not** by a learned per-country threshold.

## 4. WHAT train_s2 ACTUALLY CONTAINS — US AND INDIA, WITH REAL NUMBERS

So the France-vs-train contrast is on the record. Denominator for every rate below is
**that country's own `rows`**, per the brief's rule that per-country stats are totals
across the slice.

### 4.1 Shape and share

| | US | India |
|---|---|---|
| `rows` | **3,016,817** | **2,017,799** |
| **Share of train_s2** | **59.9215%** | **40.0785%** |
| **Total file rows** | **5,034,616** | 3,016,817 + 2,017,799 = 5,034,616 ✓ |

### 4.2 The requested statistics, for the two countries that exist

| Statistic | Profile field | US | India |
|---|---|---|---|
| Empty-name rate | `name_empty` | **0.0000%** (0) | **0.0000%** (0) |
| Empty-address rate | `addr_empty` | **3.6834%** (111,121) | **2.8668%** (57,846) |
| Mean name length | `name_chars / rows` | **23.5543** | **27.4199** |
| Mean address length (all rows) | `addr_chars / rows` | **31.5310** | **68.1963** |
| Mean address length (non-empty only) | `addr_chars / (rows − addr_empty)` | **32.7368** | **70.2090** |
| Digit-in-name rate | `has_digit_name` | **6.3988%** (193,041) | **3.1021%** (62,595) |
| Comma-in-address rate | `has_comma` | **96.3166%** (2,905,696) | **97.1332%** (1,959,953) |
| entity_id prefix validity | `prefix_bad` | **0 — 0.0000%** | **0 — 0.0000%** |
| Name-token occurrences / row | `name_tokens / rows` | 3.5514 | 2.8929 |
| Address digits / row | `num_digits / rows` | 3.75135 | 4.08113 |
| `dig5` / row (guarded) | `dig5` | 0.10734 | 0.01138 |
| `dig6` / row (guarded) | `dig6` | 0.01393 | 0.00023 |
| Alpha-only address rate | `alpha_only_addr` | 6.1192% | 5.8167% |

**`prefix_bad` is clean.** `build_profile.py:94` tests `eid.startswith(f"S{src}-")`, and
`train_s2.json` has `source: 2`, so the guard string is `S2-`. Zero violations for both
countries. *(Caveat: because the guard string is derived from the file's own source
number, this field can only ever detect a mis-prefixed source — it cannot detect a
malformed id that still starts `S2-`. It is a weak check, and passing it is a weaker
result than it looks.)*

### 4.3 Name-length histogram (the requested distribution)

`len_hist` key = `int(len(business_name) // 10 * 10)` — a **name** length floored to tens
(line 104). Both bin sets **sum exactly to `rows`**, a clean internal consistency check.

| Bin (name chars) | US | % of US | India | % of India |
|---|---|---|---|---|
| 0–9 | 91,611 | 3.0367% | 28,388 | 1.4069% |
| 10–19 | 959,916 | 31.8188% | 374,217 | 18.5458% |
| **20–29** | **1,258,076** | **41.7021%** ← mode | **783,287** | **38.8189%** ← mode |
| 30–39 | 583,593 | 19.3447% | 656,183 | 32.5197% |
| 40–49 | 110,015 | 3.6467% | 156,257 | 7.7439% |
| 50–59 | 12,496 | 0.4142% | 17,813 | 0.8828% |
| 60–69 | 1,040 | 0.0345% | 1,409 | 0.0698% |
| 70–79 | 69 | 0.0023% | 190 | 0.0094% |
| 80–89 | 1 | 0.0000% | 39 | 0.0019% |
| 90–99 | — | — | 13 | 0.0006% |
| 100–109 | — | — | 3 | 0.0001% |
| **Sum** | **3,016,817** | **= rows ✓** | **2,017,799** | **= rows ✓** |

Both countries are unimodal at 20–29 chars. India is shifted one bin right of the US at
every tail (its 30–39 bin alone is 32.5% of rows, versus 19.3% for the US), consistent
with its longer mean name (27.42 vs 23.55).


---


## 5. HOW train_s2 DIFFERS FROM train_s1 (P013's file — deltas only)

P013 owns `train_s1`; I list only what **changed**.

| Quantity | train_s1 | train_s2 | Delta |
|---|---|---|---|
| `rows` | 2,206,821 | 5,034,616 | +2,827,795 (**2.28x**) |
| US share | 59.9792% | 59.9215% | -0.0577pp |
| India share | 40.0208% | 40.0785% | +0.0577pp |
| **France share** | **0.0000%** | **0.0000%** | **0 - identical** |
| `addr_empty` US / India | **0 / 0** | **111,121 / 57,846** | **the big one** |
| `has_comma` US / India | 100% / 100% | 96.3166% / 97.1332% | mirror of the above |
| Mean name len US / India | 22.4651 / 26.3863 | 23.5543 / 27.4199 | +1.0892 / +1.0336 |
| **Digit-in-name US / India** | 2.6060% / 0.1235% | **6.3988% / 3.1021%** | **x2.46 / x25.1** |
| Mean addr len US / India | 34.9624 / 77.6996 | 31.5310 / 68.1963 | -3.4314 / -9.5033 |
| `alpha_only_addr` US | 0.0001% (1 row) | 6.1192% (184,605) | explodes |
| Name tokens/row India | 3.7016 | 2.8929 | -0.8087 |

**What is genuinely different:**

1. **The France answer does not change at all.** 0.0% in both. This is the point worth
   carrying: the France-train absence is **invariant to source**, so P013 and P014 are
   not two independent claims about a marginal population — they are one fact confirmed
   twice.
2. **`addr_empty` is the dominant structural change: 0 -> 3.7% / 2.9%.** This is the
   finding I did not expect; develop it in section 6.
3. **Digit-in-name jumps in both countries**, India by 25x. The two countries move
   independently in magnitude but in the *same direction*, which argues for a
   source-level property rather than a per-country one.
4. **The country mix is unchanged.** The 0.06pp share shift is below the ~0.03-0.04pp
   standard-error scale, so I am **not** claiming the mix genuinely shifted — the ~60/40
   US/India split is stable across train sources.

## 6. NEW FINDING — `addr_empty` AND `has_comma` ARE EXACT COMPLEMENTS, AND IT IS A SOURCE PROPERTY

**CONFIRMED by measurement.** In `train_s2`, for both countries:

```
US:    3,016,817 - 111,121 (addr_empty) - 2,905,696 (has_comma) = 0
India: 2,017,799 -  57,846 (addr_empty) - 1,959,953 (has_comma) = 0
```

**Every non-empty address in train_s2 contains a comma. To the row.** Not "essentially
all" — zero exceptions out of 4,930,871 non-empty addresses.

Checking all six files for rows that are **non-empty *and* comma-free**:

| File | US | India | France |
|---|---|---|---|
| train_s1 | 0 | 0 | - |
| train_s2 | **0** | **0** | - |
| train_s3 | 0 | 1 | - |
| test_s1 | 0 | 0 | 0 |
| test_s2 | 0 | 2 | **180** (0.025591%) |
| test_s3 | 0 | 1 | **153** (0.020913%) |

**Two consequences:**

**(a) `addr_empty = 0` is a property of source-1, not of the country.** All three
source-1 files report `addr_empty = 0.0000%` for *every* country, including France
(259,452 rows). Any "missing address" threshold or null-handling assumption validated on
source-1 is validating on a population where the failure mode **never occurs**, and will
then mis-apply to the 2.9-3.7% of s2 rows that are genuinely empty. *This is a
measurement-trap warning, not a code defect* — I have not traced whether any threshold
was actually tuned on source-1, and I am not claiming one was.

**(b) France is the only country with a non-trivial count of non-empty, comma-free
addresses** — 180 rows in test_s2, 153 in test_s3 — while the US is exactly 0 in all six
files. These are the only places in the entire dataset where a real address lacks the
comma structure everything else has.

*INFERRED, not measured:* any component-splitting logic that assumes a comma is present
will mishandle those 180 rows. `build_profile.py`'s `ADDR_SPLIT = [,;]` would yield a
single component for them, so **the profile cannot show their token content** — they are
defined by an absence the collector does not record. At 0.026% this is **not
scoring-material**; I am recording it as a correctness note and explicitly **not**
recommending a fix.
## 7. FRANCE test_s2 — FOR THE TRAIN-VS-TEST CONTRA ONLY

France has no train rows, so the **only** France s2 population available is `test_s2`
(703,378 rows, **14.3920%** of that file). Included so the contrast is on the record with
real numbers. **This is not a substitute answer to the work order.**

| Statistic | France **test_s2** | US train_s2 | India train_s2 |
|---|---|---|---|
| rows | 703,378 | 3,016,817 | 2,017,799 |
| empty-name rate | **0.0000%** | 0.0000% | 0.0000% |
| empty-address rate | **3.0619%** | 3.6834% | 2.8668% |
| mean name length | **21.1030** | 23.5543 | 27.4199 |
| mean addr length (all rows) | **39.5477** | 31.5310 | 68.1963 |
| mean addr length (non-empty) | **40.7968** | 32.7368 | 70.2090 |
| digit-in-name rate | **1.1115%** | 6.3988% | 3.1021% |
| comma-in-address rate | **96.9125%** | 96.3166% | 97.1332% |
| `prefix_bad` | **0** | 0 | 0 |
| name tokens/row | 3.4423 | 3.5514 | 2.8929 |
| `dig5` / row | 0.00514 | 0.10734 | 0.01138 |
| `alpha_only_addr` rate | 3.7897% | 6.1192% | 5.8167% |

France's `len_hist` (name length, floored to tens) also sums exactly to 703,378:
0–9: 25,983 · 10–19: 300,981 · 20–29: 276,828 · 30–39: 87,987 · 40–49: 11,301 ·
50–59: 296 · 60–69: 2.

**The contrast that matters:** France's address length (39.55) is **25% longer than the
US** (31.53) while its name is **10% shorter** (21.10 vs 23.55), and its digit-in-name
rate (1.11%) is the lowest of the three by 3–6x. France is trained on by **no** country
model, and its shapes sit outside the US/India envelope on both axes at once.
*(INFERENCE: this implies France is uncalibrated. The means are measured; the
consequence is inference.)*

## 8. PROFILE FIELD SEMANTICS USED (read `build_profile.py` first)

Quoting these correctly is the difference between a right and a wrong conclusion here:

- **`num_digits` counts digits in the ADDRESS only** — `sum(ch.isdigit() for ch in ba)`,
  line 114. It is a raw digit **count**, not a row count, and **not** a name measure. It
  is **not** the digit-in-name figure. The digit-in-name figure is `has_digit_name`, a
  separate **row** count (line 106).
- **`dig5` / `dig6` are lookaround-guarded** — `(?<!\d)\d{5}(?!\d)` and
  `(?<!\d)\d{6}(?!\d)`, lines 29-30. A digit inside a longer digit run does **not**
  count. My `dig5/row` figures use these guarded values.
- **`has_comma` tests the RAW address string** (line 108), not the split components.
- **`prefix_bad`** counts rows where `entity_id` does not start with `S{src}-`
  (line 94). `train_s2.json` has `source: 2`, so the guard is `S2-`.
- **All per-country stats are totals across the whole slice**; every rate above is
  derived by dividing by that country's `rows`.
- **`name_tokens` / `addr_tokens` are the top 4000 per country AND are periodically
  pruned** (`prune()`, `PRUNE_EVERY=8`, keeps only `v > 1`), so token counts are **lower
  bounds with a pruned tail**. A token missing from the list means **"not in the top
  4000"**, never "does not occur". I make no claim that depends on token absence.
- **`build_profile.py` FLATTENS address components** — `ADDR_SPLIT = [,;]` then
  `TOKEN_RE.findall` per component (lines 126-127) — so a token count is **not
  automatically a pipeline-visible quantity**. Tokens inside a whole comma-component are
  not what `normalize.py` exposes to `atoks`. Relevant to the RETRACTED function-word
  finding; I repeat no part of it.
- **The profile counts TOKEN OCCURRENCES, never ROWS** for `name_tokens`.

## 9. IS THE SLICE LARGE ENOUGH TO CONCLUDE FROM?

**For France train the question is UNDEFINED, not answered negatively.** There is no
slice, so there is no sample size and no confidence interval. You cannot draw a France
train conclusion at any n, because **n = 0**.

For the two populations that do exist, the sample sizes are overwhelming —
3,016,817 and 2,017,799 rows. The worst-case standard error at p = 0.25 is
**0.0288pp** (US) and **0.0352pp** (India), so every train_s2 rate in this file is far
inside any sampling-error concern. The 0.0577pp train_s1↔train_s2 share difference is
**below** that resolution and I explicitly do not claim it is real. France test_s2 at
703,378 rows is ample for its own descriptive stats (SE 0.0596pp) — that is precisely
the kind of population the retracted 100% figure mis-scoped.

**The honest caveat:** sampling error is not the dominant uncertainty in this file. The
real limits are **truncation** (top 4000 tokens, pruned tail) and **component
flattening**, both properties of the collector rather than of the sample size.

## 10. GAPS AND LIMITS

- **Not measurable:** anything requiring a France *train* denominator. Not a gap in
  effort — a gap in the data, unfixable from the provided files.
- **Not measurable:** France *train* `name_tokens` / `addr_tokens` tables. The keys are
  absent.
- **Not measured:** the content of the 180 France test_s2 non-empty comma-free
  addresses. The profile cannot isolate them.
- **Not measured:** whether the digit-in-name jump between train_s1 and train_s2 is a
  deliberate source artifact or a generator difference. The profile measures the rate,
  not the cause.
- **INFERRED, not measured:** that France's out-of-envelope shapes imply it is
  uncalibrated (section 7).
- I re-derived nothing in the brief's ALREADY RULED OUT list, and did not repeat the
  RETRACTED French function-word finding.

## 11. NEW DEFECTS FOUND

**None.** `prefix_bad = 0`, `name_empty = 0`, and all three `len_hist` bin sets (US,
India, France test_s2) reconcile exactly to their `rows`. The France-zero-train condition
is already known and already handled correctly in code. Per the evidence standard, **"no
defect found" is the result** — I am not manufacturing a recommendation to look
productive.

Two things are worth carrying forward, and **neither is a code defect**:

1. **The denominator warning (section 2)** — a reporting-discipline hazard. The exact
   error behind the retracted "100% of France rows resolve a state" figure.
2. **The `addr_empty` / `has_comma` complementarity (section 6)** — a measurement trap.
   `addr_empty = 0` in source-1 is a *source* property, and France test_s2/test_s3 hold
   the only non-empty comma-free addresses in the dataset.

---

*Companion sidecar: `analysis_out/findings/P014_France_train_s2_shape.json` (validated
to parse). Paired task: P013 (France train_s1), which reaches the same France-empty
headline.*