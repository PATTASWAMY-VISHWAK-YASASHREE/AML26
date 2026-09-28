# P017 — [France] `test_s2`: shape, null rates, length distribution

## Headline

`test_s2` France is **703,378 rows = 14.3920% of the 4,887,273-row `test_s2` file** and
**41.5108% of all 1,694,445 France test rows**. The slice is **structurally sound**:
zero empty names, zero `entity_id` prefix violations, 96.91% comma-bearing addresses.
It is **2.7110x larger than `test_s1`** and near-identical in shape to `test_s3`, so
conclusions measured here generalise to the **84.69% of French rows living in s2+s3**,
but *not* to s1. **No new defect found.**

> **STATUS: COMPLETE.** All figures measured directly from `analysis_out/profile/test_s2.json`.
> Two corrections to the work order's own numbers are recorded in §6 and §8.

---

## 0. Ground truth and reproduction checks

Source: `analysis_out/profile/test_s2.json`, field `by_country["France"]`.
Semantics per `build_profile.py:84-118`.

Denominator integrity check (the classic tell from `FLEET_BRIEF.md`):

```
sum(country_rows) = 2,312,565 + 703,378 + 1,871,330 = 4,887,273 = rows  OK
by_country["France"].rows = 703,378 = country_rows["France"]          OK
```

No other country leaks into this report. All rates below divide by **703,378**, the
`test_s2` France row count, unless the denominator is stated inline.

Cross-file context (`by_country["France"].rows` from each profile):

| file | file rows | France rows | France share of that file |
|---|---:|---:|---:|
| `test_s1` | 1,732,544 | 259,452 | 14.9740% |
| **`test_s2`** | **4,887,273** | **703,378** | **14.3920%** |
| `test_s3` | 5,082,316 | 731,615 | 14.3940% |
| all three | 11,702,133 | 1,694,445 | 14.4784% |

`test_s2` itself is **41.7620%** of all test rows (4,887,273 / 11,702,133). France as a
whole is **6.0107%** of all test rows.

---

## 1. Null rates

| quantity | value | rate (/ 703,378) | 95% CI (binomial) |
|---|---:|---:|---|
| `rows` | 703,378 | - | - |
| `name_empty` | **0** | **0.000000%** | [0, 0.000524%] |
| `addr_empty` | 21,537 | **3.061938%** | +/-0.0403 pp (21,254-21,820 rows) |
| `prefix_bad` | **0** | **0.000000%** | [0, 0.000524%] |

- **`name_empty = 0` is exact and total.** France has no missing business names in this
  slice. This is stronger than "a low rate" - there is not one.
- **`addr_empty = 3.0619%` is the only null in the slice.** Note `test_s1` France has
  `addr_empty = 0` and 100% comma rate; the empties are an **s2/s3-family trait**, not a
  France-wide trait. `test_s3` = 2.9443%. Two disjoint populations, not a continuum.
- **`prefix_bad = 0`**: every one of the 703,378 France `entity_id` values starts with
  `S2-` (`build_profile.py:94-95` checks `startswith("S2-")`). Also 0 in s1 and s3.
  **entity_id prefix validity for this slice is 100.000000%.**

## 2. Lengths

| quantity | value | per row |
|---|---:|---:|
| `name_chars` | 14,843,398 | **21.1030** |
| `addr_chars` | 27,816,963 | **39.5477** (all rows; empties contribute 0) |
| `addr_chars` / non-empty rows | 27,816,963 / 681,841 | **40.7968** |
| `name_tokens` | 2,421,234 | 3.4423 |
| `num_digits` (ADDRESS only) | 1,360,296 | 1.9339 |

`num_digits` counts digits in the **address only** (`build_profile.py:114`), never the name.

## 3. Name-length histogram (`len_hist`, bucket = `len(bn)//10*10`)

| bucket | rows | % of 703,378 |
|---|---:|---:|
| 0-9 | 25,983 | 3.6940% |
| 10-19 | 300,981 | 42.7908% |
| 20-29 | 276,828 | 39.3569% |
| 30-39 | 87,987 | 12.5092% |
| 40-49 | 11,301 | 1.6067% |
| 50-59 | 296 | 0.0421% |
| 60-69 | 2 | 0.0003% |
| **total** | **703,378** | **100.0000%** |

Sums exactly to `rows`. The 0-9 bucket contains 25,983 rows and **zero** empties
(`name_empty = 0`), so all of them are 1-9 characters. Distribution is tight and
right-skewed: **85.84%** of French names in s2 are 29 characters or fewer
(603,792 / 703,378), **98.35%** are 39 or fewer, and **99.96%** are under 50.

## 4. Digit-in-name and comma-in-address

| quantity | value | rate (/ 703,378) | 95% CI |
|---|---:|---:|---|
| `has_digit_name` | 7,818 | **1.111493%** | +/-0.0245 pp (7,646-7,990) |
| `has_comma` | 681,661 | **96.912471%** | +/-0.0404 pp (681,377-681,945) |
| `has_comma` / non-empty addr | 681,661 / 681,841 | **99.973601%** | - |
| `alpha_only_addr` | 26,656 | 3.789712% | - |
| `dig5` (lookaround-guarded) | 3,613 | 0.005137 / row | - |
| `dig6` (lookaround-guarded) | 130 | 0.000185 / row | - |

- `dig5`/`dig6` are **lookaround-guarded** (`build_profile.py:29-30`): a digit inside a
  longer digit run does not count. 0.005137/row confirms the settled finding that French
  addresses carry house numbers, not postcodes - leave the `pin` guard alone.
- **Digit-in-name is a France-vs-US structural difference**, not a defect: France 1.1115%
  vs US 6.178% vs India 2.879% in this same file. French legal-form suffixes (`sarl`,
  `sas`, `eurl`, `sasu`, `sci` - the top five France `name_tokens`) are alphabetic.
- Rows with **no usable address number at all** = `addr_empty` + `alpha_only_addr` =
  21,537 + 26,656 = **48,193 rows = 6.8517%** (the two sets are disjoint by construction,
  `build_profile.py:117`). Their overlap with other fields is **a gap** - the profile
  records only marginals.

## 5. Is the slice large enough to conclude from?

**Yes, comfortably.** 703,378 rows gives a 95% CI half-width of **+/-0.041 pp** on a ~3%
rate. These are census counts over the file, not sample estimates, so the CIs above only
describe hypothetical re-sampling of the same distribution, not measurement error. The
practical point: differences of >=0.1 pp between sources in this report are real;
differences of <0.01 pp are not.

**Which France conclusions does this slice speak for?**

| population | rows | share of France | s2 conclusions valid? |
|---|---:|---:|---|
| `test_s1` France | 259,452 | 15.31% | **No** - different shape (0% addr_empty, 100% comma, mean addr 50.07 vs 39.55) |
| `test_s2` France | 703,378 | 41.51% | - |
| `test_s3` France | 731,615 | 43.19% | **Yes** - near-identical (mean name 21.140 vs 21.103, mean addr 39.969 vs 39.548) |
| s2+s3 combined | 1,434,993 | **84.69%** | **Yes** |

---

## 6. `test_s2`-specific: the `n` -> `""` deletion, per file

`ADDR_CANON_FR` maps `"n": ""` (`normalize.py:214`), and `normalize.py:349-350` drops any
token whose canonical value is falsy (`if t:`). So every standalone `n` token is deleted
from `atoks`.

The brief's 0.8874% is **pooled over all three test files**. The per-file split, `n`
occurrences divided by that file's own `sum(addr_tokens["France"])`:

| file | `n` occurrences | listed France addr mass | **rate, own denominator** |
|---|---:|---:|---:|
| `test_s1` | 2,648 | 2,253,877 | **0.117486%** |
| **`test_s2`** | **51,535** | **4,745,780** | **1.085912%** |
| `test_s3` | 52,241 | 4,993,261 | **1.046230%** |
| pooled | 106,424 | 11,992,918 | 0.887390% |

**`test_s2`'s own share is 1.0859% — 1.2237x the pooled 0.8874%, and 9.2x the s1 rate.**
s2 carries **48.4242%** of all 106,424 deletions while holding 41.5108% of French rows.
The pooled figure understates s2 by 0.199 pp.

**Correction to the brief's framing:** `n` is not the only token deleted this way.
`ADDR_CANON_COMMON` (`normalize.py:197-198`) maps `number/no/nos/num/h/hno/house/door/
plot/flat/shop/null/na/none/nil` to `""`, and all survive into the effective France canon
(`normalize.py:322` drops only `st, ste, dr, n, s, e, w` from COMMON, and `n` is
re-supplied by `ADDR_CANON_FR:214`). Measuring the whole empty-mapping family:

| file | empty-mapped occurrences (in top 4000) | rate, own denominator |
|---|---:|---:|
| `test_s1` | 4,280 (`n` 2648, `no` 284, `h` 1051, `na` 297) | 0.189895% |
| **`test_s2`** | **90,040** (`n` 51535, `no` 35995, `h` 1990, `na` 520) | **1.897265%** |
| `test_s3` | 90,542 (`n` 52241, `no` 35742, `h` 1979, `na` 580) | 1.813284% |
| pooled | 184,862 | 1.1245% |

**The true empty-mapping deletion in s2 is 1.8973% of its own listed address mass — not
1.0859%, not 0.8874%**: 2.14x the pooled figure, and 66.76% of the whole family's mass
sits in s2. `number/nos/num/hno/house/door/plot/flat/shop/none/nil` are **not in the top
4000** for France in any test file, so their true counts are unknown and this table is a
**lower bound**. Tokens are **occurrences, not rows**.

**Verdict: not a defect.** Deleting a house-number marker before feature extraction is the
intended behaviour, and `n`/`no` are unselective anyway (`keys.py:42` requires `len >= 3`,
so neither can ever become a blocking key). This is a denominator correction, not a code
recommendation.

## 7. `test_s2`-specific: the French function-word mass (use 10.68%, not 15.41%)

From `addr_tokens["France"]` in `test_s2` (ranks in brackets):

| token | occurrences | rank | % of 4,745,780 |
|---|---:|---:|---:|
| `de` | 381,880 | 1 | 8.0467% |
| `la` | 176,186 | 4 | 3.7125% |
| `du` | 90,693 | 9 | 1.9110% |
| `des` | 82,399 | 12 | 1.7363% |
| `le` | 4,882 | 110 | 0.1029% |
| `les` | 1,451 | 245 | 0.0306% |
| **six-word total** | **737,491** | | **15.5399%** |
| four-word `de+la+du+des` | 731,158 | | 15.4065% |

**These profile figures are the RETRACTED ones.** The established 15.41% for test_s2 is
731,158 / 4,745,780 reproduced exactly above — the tell that the retraction applied here.

**The correct figure is 10.68%**, because `normalize.py:333-335` tests a whole
comma-component against `FR_REGIONS` and `continue`s, so the `de`/`la` inside
`"Pays de la Loire"`, `"Hauts de France"`, `"Pas de Calais"` and `"Ile de France"` never
reach `atoks` at all. `build_profile.py:126-127` has no equivalent guard, so the profile
counts them. D119 sizes region-consumed mass in s2 at **230,650** occurrences.

Reproduced both ways from the same inputs:

```
six-word:  737,491 - 230,650 = 506,841  ->  506,841 / 4,745,780 = 10.6798%  ~= 10.68%
four-word: 731,158 - 230,650 = 500,508  ->  500,508 / 4,745,780 = 10.5464%
```

**Arithmetic note on D119:** the 10.68% in D119's per-source table is the **six-word**
figure (10.6798%), while the "profile four-word" column beside it shows 731,158. The
four-word visible share is 10.5464%. The brief's instruction to use 10.68% is right and I
use it; flagging only so the two are not confused later.

`build_profile.py` **flattens components**, so a token count here is **not automatically
pipeline-visible**. Per the settled brief, **`ADDR_CANON_FR` has no material gap here; no
fix is proposed and `FR_REGIONS` must not be extended** (D116: adding keys makes line 335
`continue` and deletes live feature mass).

## 8. `test_s2`-specific: department-style geography tokens

| token | s2 occurrences | s2 rank | `FR_REGIONS` key? |
|---|---:|---:|---|
| `nord` | 75,362 | 13 | yes -> `hdf` |
| `gironde` | 75,104 | 14 | yes -> `naq` |
| `atlantique` | 63,697 | 17 | only within `loire atlantique` |
| `calais` | 55,273 | 20 | only within `pas de calais` |

**CORRECTION TO THE WORK ORDER — its four headline numbers are NOT s2 figures.** The brief
states these tokens are `nord` 152,011, `gironde` 150,787, `calais` 128,762, `atlantique`
128,348 "in this slice". Those are **sums over s1+s2+s3**, verified to the row:

```
nord        75,362 (s2) + 76,449 (s3) +      200 (s1) = 152,011  = brief
gironde     75,104 (s2) + 75,621 (s3) +       62 (s1) = 150,787  = brief
calais      55,273 (s2) + 57,522 (s3) + 15,967 (s1) = 128,762  = brief
atlantique  63,697 (s2) + 64,398 (s3) +      253 (s1) = 128,348  = brief
```

The **s2-only** values are **75,362 / 75,104 / 55,273 / 63,697**. This is exactly the
one-source-as-many error `FLEET_BRIEF.md` warns about, and it propagated into my own work
order. The qualitative conclusion survives (all four dominate s2, all are `FR_REGIONS` keys
or key fragments), but **`calais` in s2 is 2.33x smaller than quoted (55,273, not
128,762)** — 15,967 of the quoted mass is s1-only, the *region*-style source. The s2 order
is `nord` > `gironde` > `atlantique` > `calais`, not the brief's order.

**s2 internal shares** (occurrences / 703,378 rows — occurrences, not rows, and not
automatically pipeline-visible): `nord` 10.7143%, `gironde` 10.6776%, `atlantique` 9.0559%,
`calais` 7.8582%. All four are `FR_REGIONS` keys or fragments (`normalize.py:244-250`),
consistent with D128's finding that s2 encodes geography with department names.

## 9. Side observation — D077's "97.4380% resolvable" is exactly the France comma rate

Not my task, but the arithmetic is a one-liner and it independently confirms D128. D077
reported 97.4380% France-resolvable; the pooled France `has_comma` rate is:

```
(259,452 + 681,661 + 709,921) / 1,694,445 = 1,651,034 / 1,694,445 = 97.4380%   exact
```

D077's number is the pooled France comma rate to four decimals, reproducing D128's
"criterion mismatch" conclusion from a different direction.

## 10. New defects

**None.** Re-checked and *not* defective: `entity_id` prefixes (0 bad), empty names (0),
the postal-code question (`dig5` 0.005137/row, the settled REFUTED-1), and the
`FR_REGIONS` / function-word questions (both settled; reproduced above at correct
denominators).

The one substantive item is a **measurement correction, not a code defect**: the `n`
deletion per-file split (section 6) and the pooled-vs-s2 department counts (section 8).
Both point the same way — **s2-specific figures were quoted at pooled or s1-contaminated
denominators.**

## 11. Gaps (fields the profile does not collect)

- **No cross-field overlaps.** `addr_empty AND has_comma`, `addr_empty AND has_digit_name`
  etc. are not recorded; the profile holds marginals only. My
  `rows_no_address_number = 48,193` is valid **only** because `alpha_only_addr` requires
  `ba` non-empty (`build_profile.py:117`), making the sets disjoint by construction.
- **`len_hist` is bucketed at 10 chars only**; the exact per-length distribution and the
  median are not recoverable.
- **`entity_id` validity is `startswith("S2-")` only** (`build_profile.py:94`); full
  entity_id format validity is not verifiable from the profile.
- **`addr_tokens` / `name_tokens` are top 4000 per country.** `number/nos/num/hno/house/
  door/plot/flat/shop/none/nil` are **not in the top 4000** for France in any test file,
  so section 6's empty-mapping total is a **lower bound**. Never read absence as
  non-occurrence.
- **Token counts are occurrences, never rows.** No row-level France statistic is
  derivable from `addr_tokens`.
- **`build_profile.py` flattens address components**, so no `addr_tokens` count is
  automatically pipeline-visible; region-consumed mass is invisible to the profile.


*Sections 1-5 are the shape report proper; 6-9 are the s2-specific measurements; 10-11 are defects and gaps.*
