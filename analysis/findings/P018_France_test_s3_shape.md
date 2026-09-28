# P018 — [France] `test_s3`: shape, null rates, length distribution

## Headline

`test_s3` France is **731,615 rows = 14.395307% of the 5,082,316-row `test_s3` file** and
**43.177265% of all 1,694,445 France test rows**. The slice is **structurally clean**:
`name_empty = 0`, `prefix_bad = 0`, 97.034779% comma-bearing addresses. It is
**1.0401x `test_s2`** and **2.8198x `test_s1`**, so a France conclusion drawn here is a
conclusion about the plurality of French test data.

**The s3-specific check I was asked to run came back NEGATIVE: France's `test_s3` does
NOT encode geography as codes.** Every French department signal in s3 is a **full word**
(`gironde` 75,621; `nord` 76,449; `calais` 57,522; `atlantique` 64,398), and the numeric
INSEE department codes sit on a smooth monotone decay that is unmistakably the
**house-number** distribution, not a code channel. This is a real negative result and it
matters, because France has **no** `FR_REGIONS` self-map loop entry (`normalize.py:252`)
— the exact mechanism that is load-bearing for 4,520,547 Indian rows. **France does not
need that loop entry**, and the s3-specific French risk does not exist.

> **STATUS: COMPLETE.** Every figure measured directly from
> `analysis_out/profile/test_s3.json` field `by_country["France"]`, cross-checked against
> `test_s1.json` and `test_s2.json`. Arithmetic shown throughout. **No new defect found.**

---

## 0. Ground truth and denominator integrity

Source: `analysis_out/profile/test_s3.json`, `by_country["France"]`.
Field semantics per `build_profile.py:84-118`.

**The classic scoping tell from `FLEET_BRIEF.md` is clean — this report is NOT s1-scoped:**

```
sum(country_rows) = 2,405,000 + 731,615 + 1,945,701 = 5,082,316 = rows   OK
by_country["France"].rows = 731,615 = country_rows["France"]            OK
```

`len_hist` totals **731,615 = rows** exactly (section 3). Every rate below divides by
**731,615** unless a denominator is stated inline.

### Cross-file context

| file | file rows | France rows | France share of that file |
|---|---:|---:|---:|
| `test_s1` | 1,732,544 | 259,452 | 14.974015% |
| `test_s2` | 4,887,273 | 703,378 | 14.392007% |
| **`test_s3`** | **5,082,316** | **731,615** | **14.395307%** |
| all three | 11,702,133 | 1,694,445 | 14.478399% |

**How big is this slice?** `test_s3` is **43.430681%** of all test rows
(5,082,316 / 11,702,133), and France-in-s3 is **43.177265%** of the France test
population. France overall is **14.478399%** of all test rows. The two shares being
within 0.25 pp of each other is a coincidence, not a bias — but it does mean a France
conclusion measured here rests on the plurality slice.

---

## 1. Null rates

| quantity | value | rate (/ 731,615) | 95% CI (binomial) |
|---|---:|---:|---|
| `rows` | 731,615 | — | — |
| `name_empty` | **0** | **0.000000%** | [0, 0.000524%] |
| `addr_empty` | 21,541 | **2.944308%** | ±0.038736 pp → rows [21,258, 21,824] |
| `prefix_bad` | **0** | **0.000000%** | [0, 0.000524%] |

- **`name_empty = 0` is exact and total.** Not one of the 731,615 French names in s3 is
  empty or whitespace-only. This is a census count, not an estimate.
- **`addr_empty` is the only null in the slice, at 2.944308%.** Compare the three
  sources: s1 **0.000000%**, s2 **3.061938%**, s3 **2.944308%**. s1 has *literally
  zero* empty addresses and a 100.000000% comma rate. **Empty addresses are an
  s2/s3-family trait, not a France-wide trait** — two disjoint populations, not a
  continuum. Pooled over all three France test files:
  `43,078 / 1,694,445 = 2.542307%`.
- **`prefix_bad = 0`**: every one of the 731,615 France `entity_id` values in this file
  starts with `S3-` (`build_profile.py:94-95` checks `startswith(f"S{src}-")`, and this
  profile's `source` field is `3`). **entity_id prefix validity for this slice is
  100.000000%.** Also 0 for the US and India rows in the same file, and 0 for France in
  s1 and s2. No prefix contamination anywhere in `test_s3`.

## 2. Lengths

| quantity | value | per row |
|---|---:|---:|
| `name_chars` | 15,466,518 | **21.1402** |
| `addr_chars` | 29,241,603 | **39.9686** (all rows; empties contribute 0) |
| `addr_chars` / non-empty rows | 29,241,603 / 710,074 | **41.1811** |
| `name_tokens` | 2,525,838 | 3.4524 |
| `num_digits` (**ADDRESS only**) | 1,415,333 | 1.9345 |

- `num_digits` counts digits in the **address only** (`build_profile.py:114`), never in
  the name. Use section 4's `has_digit_name` for the name.
- Mean name length 21.1402 chars is within 0.04% of s2's 21.1030 — a stable French
  naming convention across all three sources.

## 3. Name-length histogram (`len_hist`, bucket key = `len(name)//10*10`)

| bucket | rows | % of 731,615 |
|---|---:|---:|
| 0-9 | 35,882 | 4.9045% |
| 10-19 | 306,044 | 41.8313% |
| 20-29 | 277,555 | 37.9373% |
| 30-39 | 95,665 | 13.0759% |
| 40-49 | 15,337 | 2.0963% |
| 50-59 | 1,082 | 0.1479% |
| 60-69 | 48 | 0.0066% |
| 70-79 | 2 | 0.0003% |
| **total** | **731,615** | **100.0000%** |

`total == rows` exactly. The 0-9 bucket holds 35,882 rows and **`name_empty = 0`**, so
all of them are 1-9 characters. Cumulative: **84.6731%** of French s3 names are ≤29
chars (619,481), **97.7490%** ≤39 (715,146), **99.8453%** ≤49 (730,483). Tight and
right-skewed, matching s1 and s2.

## 4. Digit-in-name and comma-in-address

| quantity | value | rate (/ 731,615) | 95% CI |
|---|---:|---:|---|
| `has_digit_name` | 8,094 | **1.106320%** | ±0.023968 pp → rows [7,919, 8,269] |
| `has_comma` | 709,921 | **97.034779%** | ±0.038869 pp → rows [709,637, 710,205] |
| `has_comma` / non-empty addr | 709,921 / 710,074 | **99.978453%** | — |
| `alpha_only_addr` | 26,857 | 3.670920% | ±0.043090 pp |
| `dig5` (lookaround-guarded) | 3,909 | 0.005343 / row | — |
| `dig6` (lookaround-guarded) | 115 | 0.000157 / row | — |

- **Digit-in-name is a France-vs-US/India structural difference, not a defect:**
  France **1.106320%** vs US **6.0735%** vs India **3.1686%** in this same file. The
  dominant French name tokens are alphabetic legal forms — `sarl` 144,483, `sas` 101,750,
  `eurl` 42,295, `sasu` 31,684, `sci` 27,897.
- `dig5`/`dig6` are **lookaround-guarded** (`build_profile.py:29-30`): a digit inside a
  longer digit run does not count. 0.005343/row re-confirms the settled finding that
  French addresses carry **house numbers**, not postcodes. **Leave the `pin` guard
  alone** — no new evidence against it, and none in its favour for France.
- Rows with **no usable address number at all** = `addr_empty` + `alpha_only_addr` =
  21,541 + 26,857 = **48,398 rows = 6.615228%**. The two sets are disjoint by
  construction (`build_profile.py:117` requires `ba` non-empty). Their **overlap with
  any other field is a GAP** — the profile stores marginals only, never a cross-tab.
- Pooled comma rate over all three France test files: 1,651,034 / 1,694,445 =
  **97.438040%**.

## 5. Is the slice large enough to conclude from?

**Yes, comfortably — and it is the right slice to conclude from.** 731,615 rows gives a
95% CI half-width of **±0.039 pp** on the ~3% `addr_empty` rate and **±0.024 pp** on the
~1% digit-in-name rate.

Two honest caveats on what the CIs mean:

1. These are **census counts over the file, not sample estimates**. The binomial CIs
   above describe hypothetical re-sampling of the same distribution, not measurement
   error in the profile build. They are a useful *sense of scale* check, nothing more.
2. **43.177265% coverage is not majority coverage of France.** A shape statistic measured
   here generalises to s3 with certainty and to s2 with high confidence (the two slices
   are near-identical: mean name 21.1402 vs 21.1030, `addr_empty` 2.9443% vs 3.0619%,
   `has_comma` 97.0348% vs 96.9125%, digit-in-name 1.1063% vs 1.1115%). It does **not**
   generalise to s1, which differs on the one field that matters here: s1 has
   **0.000000%** empty addresses and **100.000000%** commas. **Any France-wide claim
   should be read as "s2+s3 France, 84.69% of French test rows", or stated against the
   pooled 1,694,445 denominator explicitly.** Never quote this file's rate as a
   France-wide rate.

## 6. The s3-specific measurement: is there a France code-vs-name shift?

**This is the high-value check from the work order, and the answer is NO.**

### 6a. The India contrast, reproduced on the same fields

India in s3 encodes states as two-letter codes; s1 inverts this completely:

| token | s3 count | s3 per 1k rows | s1 count |
|---|---:|---:|---:|
| `mh` | 371,434 | **154.442** | 1,855 |
| `maharashtra` | 22,537 | 9.371 | 176,366 |
| `ka` | 139,927 | 58.182 | 2,235 |
| `karnataka` | 9,324 | 3.877 | 65,298 |
| `up` | 142,312 | 59.173 | 604 |
| `uttar` | 12,618 | 5.247 | 69,321 |

The code form dominates s3 by **16.5x** (`mh` vs `maharashtra`) and the name form
dominates s1 by **95.1x**. That is the `IN_STATES` self-map loop being load-bearing.

### 6b. France shows the opposite: full words, no codes

| token | s3 count | s3 per 1k | s2 count | s1 count |
|---|---:|---:|---:|---:|
| `gironde` | 75,621 | 103.362 | 75,104 | 62 |
| `nord` | 76,449 | 104.493 | 75,362 | 200 |
| `calais` | 57,522 | 78.623 | 55,273 | 15,967 |
| `atlantique` | 64,398 | 88.022 | 63,697 | 253 |
| `hauts` | 99,419 | 135.890 | 88,519 | 101,717 |
| `france` | 100,902 | 137.917 | 89,929 | 102,319 |
| `nouvelle` | 83,099 | 113.583 | 74,392 | 85,311 |
| `aquitaine` | 82,987 | 113.430 | 74,276 | 85,268 |
| `loire` | 135,367 | 185.025 | 126,216 | 72,836 |

Every French geographic signal in s3 is a **full word**, and s3 is indistinguishable from
s2 on all of them. s1 differs — it carries region names like `hauts`/`france`/`nouvelle`
at near-equal weight and almost no department names — but that is the s1-vs-s2/s3 split
already characterised in D128, **not** a code shift.

### 6c. The numeric codes are house numbers, provably

I checked whether INSEE department codes appear as tokens. They do, but on a **smooth
monotone decay with no spike at any department code**:

```
01:298  02:279  03:313 ... 09:225          <- zero-padded house numbers, ~200-300
10:14556 11:13884 12:13821 13:12640 14:13402 15:12795 16:12238 17:11395
18:11026 19:10798 20:10352 21:9908 22:10061 23:9605 24:9365 25:8697 ...
30:7589 31:7025 32:6843 33:6359 34:6404 35:6262 36:5942 ...
50:3917 51:3863 52:3554 53:3414 54:3323 55:3345 ...
70:2252 71:2172 72:2149 73:1933 74:2156 75:2015 76:1849 77:1887 ...
90:1491 91:1467 92:1365 93:1296 94:1346 95:1370 96:1323 97:1272 98:1257 99:1231
```

The counts fall monotonically from `10:14556` to `99:1231` — a textbook house-number
frequency curve. **Decisive test:** `gironde` occurs 75,621 times as a *word*. If s3 also
encoded Gironde as the code `33`, then `33` would be at least ~75,000. It is **6,359**,
sitting exactly where the house-number curve predicts, between `32:6843` and `34:6404`.
The same holds for every other code: `59`=2,910 (the curve expects ~2,900, between
`58:3071` and `60:2957`), `44`=4,666, `62`=2,787, `75`=2,015, `92`=1,365. **No department
code carries any geographic mass.** These numbers *are* in the top-4000 token list, so the
low values are real, not truncation artefacts — this argument does not rest on absence.

### 6d. Conclusion on the code-vs-name question

> **CONFIRMED (negative).** France's `test_s3` contains **no** French department
> abbreviation or code form that is absent from s1. There is no France analogue of the
> Indian `mh`-vs-`maharashtra` inversion, and therefore **no France-specific s3
> geographic-resolution defect**. The `IN_STATES` self-map loop is not needed for France
> at any source, which is consistent with `normalize.py:252` omitting `FR_REGIONS` and
> with the already-measured "zero effect" of that omission.

This does **not** touch the open s2/s3 **department-name-vs-region-name** gap (D128,
contradiction still unresolved between 28.90% and 2.5620% unresolvable). That gap is
about *dictionary coverage of full words*; this section is about *token form*. They are
independent and both stand.

## 7. Secondary: s3's France token tail is an s2 clone, not an s3 innovation

Tokens present in s3's France `addr_tokens` but absent from s1's: **340**. Of those,
**261 also appear in s2** (61,441 s3 occurrences = **1.230478%** of the 4,993,261 listed
France s3 address-token mass). Only **79 are unique to s3**, with a maximum count of
**122** (`037`, 0.167 per 1k). Top of the s1-absent set:

| token | s3 count | per 1k | s2 count |
|---|---:|---:|---:|
| `ave` | 10,822 | 14.792 | 10,792 |
| `merignac` | 7,267 | 9.933 | 7,149 |
| `lege` | 5,603 | 7.658 | 5,658 |
| `blvd` | 3,046 | 4.163 | 3,000 |
| `crs` | 2,260 | 3.089 | 2,260 |

**Inference (marked as such):** s1 uses spelled-out street types and a different
geographic vocabulary; s2 and s3 are near-clones of each other that use abbreviations
(`ave`, `blvd`, `crs`, `psg`) and carry the department-name channel. The s2-to-s3
divergence is 79 tokens with a max count of 122 — an order of magnitude below the
s1-to-s3 gap of 340 tokens with a max count of 10,822. **s3 is not a new encoding
regime; it is s2 with a different row sample.**

### 7a. Minor observation: a French street-type typo tail (not actionable)

s3 France carries a visible misspelling tail for `avenue`: `avenue` 49,582 (67.771/1k),
`av` 27,570, `bd` 11,714, `ave` 10,822, plus `aveue` 277, `aveneu` 260, `avnue` 259,
`aveune` 258, `avneue` 254, `avene` 240, `aevnue` 237 — **1,785 occurrences** across
those seven typo forms, all absent from s1 and shared with s2. This is an
OCR/transcription tail, not a code channel, and at 1,785/4,993,261 = 0.036% of listed
address-token mass it is far below anything actionable. **Reported for completeness;
no recommendation.**

## 8. Defect assessment

**No new defect found.** Explicitly:

- Shape (sections 1-4) is clean: 0 empty names, 0 prefix violations, 97.03% comma rate.
- The s3-specific code-vs-name hypothesis is **refuted** (section 6) — the opposite of
  the Indian pattern, and consistent with the existing code.
- `dig5`/`dig6` per row (0.005343 / 0.000157) re-confirm the settled "French addresses
  carry house numbers" result. **The `pin` guard should be left alone.**
- France s3's token regime matches s2, so any s2-measured French finding carries to s3
  with high confidence — the s2/s3 department-coverage gap (D128) applies here at
  **43.177265%** weight.
- Per the work order I do **not** repeat the retracted French function-word figure; the
  correct pooled value is 10.25% (D119) and `ADDR_CANON_FR` has no material gap.

**Gaps this report could not close** (profile does not collect them):

1. **No cross-tabs.** Overlap of `addr_empty`/`alpha_only_addr` with `has_digit_name`,
   `has_comma`, or any token class is **unmeasurable** from these marginals.
2. **Token lists are top-4000 per country per file.** Absence from
   `name_tokens`/`addr_tokens` is **not** proof of non-occurrence. I have written
   "not in the top 4000" throughout and made no non-occurrence claims from it. (The
   section 6c code argument does **not** rely on truncation: the codes *are* in the top
   4000, at low values.)
3. **No per-row `entity_id` values**, so prefix validity is a profile-level aggregate
   (`prefix_bad` = 0) and cannot be decomposed further.
4. **No city field.** Cities are only visible as `addr_tokens` (`merignac`, `lege`,
   `sohier`, `reaumur`...), so city-as-a-feature questions remain open here.
5. **French region/department resolution rates are NOT re-derived** in this report —
   D128's 28.90% vs 2.5620% contradiction is still unresolved and I have no new
   evidence bearing on it.

---

*Measured 2026-09-27 from `analysis_out/profile/{test_s1,test_s2,test_s3}.json`,
field `by_country["France"]`. PowerShell only; no Python, no network, no raw TSV access.
Profile semantics verified against `build_profile.py:29-31, 84-118`.*
