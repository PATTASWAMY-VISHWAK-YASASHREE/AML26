# P004 — [US] test_s1: shape, null rates, length distribution

Source of record: `analysis_out/profile/test_s1.json` (`split=test`, `source=1`).
No raw `*.tsv` was opened; `_upstream/` was read read-only. Every number below is a
named profile field or arithmetic on named fields, and field semantics were pinned
by reading `build_profile.py` (lines 92–127) *before* quoting anything.

## Headline

The US slice of `test_source1` is **663,106 rows, 38.2735% of the 1,732,544-row
file**, and it is clean on every integrity axis: `name_empty = 0`, `addr_empty = 0`,
`prefix_bad = 0`, and `len_hist` sums *exactly* to 663,106.

The substantive result is that **this file's cleanliness is a property of the
source, not of the country or the split.** I measured the same identity across all
six profile files: **`train_s1` and `test_s1` are null-free and comma-complete for
every country they contain (0 empty addresses, 0 comma-less addresses), while
`train_s2/s3` and `test_s2/s3` carry 2.28%–3.68% empty addresses.** That has a
direct consequence for the record: the earlier measurement of French state
resolution — "100.00% (259,452 / 259,452), zero unmatched" — was computed on
`test_s1`, the one file where a comma-less address is *impossible by construction*.
The bound is real for the file it was measured on and should not be quoted as a
corpus-wide figure. P005 independently found the 180 comma-less France rows in
`test_s2`; this work explains **why they could not have appeared in the file that
was originally measured.**

## Findings

### 1. Shape and share of file

| Quantity | Value | Field / arithmetic |
|---|---|---|
| Rows in file | 1,732,544 | `rows` |
| US rows | 663,106 | `by_country.US.rows` |
| India rows | 809,986 | `country_rows.India` |
| France rows | 259,452 | `country_rows.France` |
| **US share of file** | **38.2735%** | 663,106 / 1,732,544 = 0.382735 |
| India share | 46.7502% | 809,986 / 1,732,544 |
| France share | 14.9763% | 259,452 / 1,732,544 |
| Countries present | `US`, `India`, `France` | `country_rows` keys |
| Columns | `entity_id, business_name, business_address, country` | `cols` |

**Invariant 1 (holds exactly):** `country_rows` sums to `rows` —
809,986 + 259,452 + 663,106 = 1,732,544. No country is hidden, and the three
`by_country[*].rows` values independently agree with `country_rows`.

### 2. Null / integrity rates (all ÷ `by_country.US.rows` = 663,106)

| Field | Count | Rate | Arithmetic |
|---|---|---|---|
| `name_empty` | **0** | **0.0000%** | exact zero |
| `addr_empty` | **0** | **0.0000%** | exact zero |
| `prefix_bad` | **0** | **0.0000%** | exact zero |
| `has_comma` | 663,106 | **100.0000%** | 663106/663106 = 1.0 |
| `has_digit_name` | 17,142 | 2.5851% | 17142/663106 = 0.025851 |
| `alpha_only_addr` | **1** | **0.000151%** | 1/663106 = 0.0000015 |
| `dig5` (occurrences) | 72,802 | 0.109789/row | 72802/663106 |
| `dig6` (occurrences) | 793 | 0.001196/row | 793/663106 |
| `num_digits` (occurrences) | 2,763,442 | 4.167421/row | 2763442/663106 |

Three of these are exact zeros, and all three are non-vacuous checks because the
builder evaluates them per row: `prefix_bad` at `build_profile.py:94`
(`eid.startswith(f"S{src}-")` with `src=1`), `name_empty` at line 98, and
`addr_empty` at line 100. So `S1-` is a valid partition key for **100%** of US rows
here, and **no prefix repair or null handling is warranted for this slice.**

`alpha_only_addr = 1` is worth a second look: `build_profile.py:117` is
`if ba and not any(ch.isdigit() for ch in ba)`, so this counts **non-empty
addresses containing no digit at all**. Exactly **one** US address in 663,106 is
entirely alphabetic. I cannot identify which one — the profile keeps no sample
strings — so I report the count, not its content.

`dig5`/`dig6` are **occurrence counts** (`len(findall(...))`, lines 115–116), not
row counts. A row holding two 6-digit runs counts twice, so 793 is an **upper
bound** on US rows carrying a standalone 6-digit number. I report them as
occurrences-per-row throughout and never as row rates.

### 3. Lengths

| Quantity | Value | Arithmetic |
|---|---|---|
| Mean name length | **22.4633** chars | `name_chars` 14,895,554 / 663,106 |
| Mean address length | **34.9661** chars | `addr_chars` 23,186,242 / 663,106 |
| Mean address length (non-empty only) | 34.9661 | same denominator — `addr_empty = 0` |
| Mean name tokens/row | 3.4863 | `name_tokens` 2,311,785 / 663,106 |
| Address digits/row | 4.1674 | `num_digits` 2,763,442 / 663,106 |
| Address digit share of address chars | 11.9185% | 2,763,442 / 23,186,242 |

### 4. Name-length histogram (`len_hist`, bucketed by `len//10*10`)

| Name length | Rows | % of US rows | Cumulative % |
|---|---|---|---|
| 0–9 | 18,617 | 2.8075% | 2.8075% |
| 10–19 | 227,566 | 34.3182% | 37.1257% |
| **20–29** | **301,714** | **45.5001%** | 82.6259% |
| 30–39 | 104,345 | 15.7358% | 98.3616% |
| 40–49 | 10,328 | 1.5575% | 99.9192% |
| 50–59 | 518 | 0.0781% | 99.9973% |
| 60–69 | 18 | 0.0027% | 100.0000% |
| **Total** | **663,106** | **100.0000%** | — |

**Invariant 2 (holds, exactly):** `len_hist` sums to `rows`, 663,106 = 663,106.
The top bucket is 60–69 with 18 rows.

**Consistency check.** Summing per-bucket minimum and maximum possible
`name_chars` bounds the total to [11,880,390 , 17,848,344]. The measured
`name_chars` = 14,895,554 falls inside, implying a mean offset of **+4.547 chars**
above each bucket floor. The histogram and the character total are mutually
consistent — they are not independent, but they do not contradict.

The distribution is sharply concentrated: **82.63% of US names are ≤29 chars** and
**99.92% are ≤49**. Because `name_empty = 0`, all 18,617 rows in the 0–9 bucket hold
names of length 1–9, not empty strings.

### 5. Is the slice large enough to conclude from? — Yes

n = 663,106. 95% binomial Wald half-widths, 1.96·√(p(1−p)/n):

| Field | Rate | 95% CI half-width | Rows equivalent |
|---|---|---|---|
| `has_digit_name` | 2.5851% | ±0.0382pp | ±253 |
| `dig5` | 10.9789%/row | ±0.0752pp | ±499 |
| `dig6` | 0.1196%/row | ±0.0083pp | ±55 |
| `alpha_only_addr` | 0.000151% | ±0.0003pp | ±2 |

Every rate is pinned to within ±0.08pp. The `alpha_only_addr = 1` result is
reported as a **count**, not a rate, precisely because its rate (±2 rows) is of the
same order as the count itself.

### 6. NEW FINDING — the null-free / comma-complete property is per **source**, not per country

I tested the comma identity `has_comma == rows − addr_empty` (i.e. *every non-empty
address contains a comma*) across all six files and all three countries:

| File | rows | `addr_empty` | rate | comma-less | null-free? | comma-complete? |
|---|---|---|---|---|---|---|
| **train_s1** | 2,206,821 | **0** | 0.0000% | **0** | **yes** | **yes** |
| **test_s1** | 1,732,544 | **0** | 0.0000% | **0** | **yes** | **yes** |
| train_s2 | 5,034,616 | 168,967 | 3.3561% | 0 | no | yes |
| train_s3 | 5,285,603 | 175,916 | 3.3282% | 1 | no | ~yes |
| test_s2 | 4,887,273 | 129,408 | 2.6479% | 182 | no | no |
| test_s3 | 5,082,316 | 136,098 | 2.6779% | 154 | no | no |

Per-country `addr_empty` rates make the split unmistakable:

| File | US | India | France |
|---|---|---|---|
| train_s1 | **0.0000%** | **0.0000%** | — |
| **test_s1** | **0.0000%** | **0.0000%** | **0.0000%** |
| train_s2 | 3.6834% | 2.8668% | — |
| train_s3 | 3.5005% | 3.0700% | — |
| test_s2 | 2.9448% | 2.2816% | 3.0619% |
| test_s3 | 2.8430% | 2.4632% | 2.9443% |

**Reading.** Every source-1 file is exactly null-free and exactly comma-complete
for every country it contains; every source-2/3 file has a 2.3%–3.7% address-null
rate for every country. The property tracks the **source index**, with no
exceptions in 15 country-slices. *Inference:* this reflects two different address
generators or two different export pipelines, one per source index — the profile
contains no generator or provenance metadata, so I cannot say which, and I do not
claim to know.

### 7. The second asymmetry: US `dig6` by source

| File | US `dig5`/row | US `dig6`/row | US `dig6` count |
|---|---|---|---|
| train_s1 | 0.109844 | **0.001251** | 1,656 |
| **test_s1** | 0.109789 | **0.001196** | **793** |
| train_s2 | 0.107340 | 0.013931 | 42,026 |
| train_s3 | 0.107802 | 0.013350 | 42,321 |
| test_s2 | 0.109706 | 0.014298 | 26,757 |
| test_s3 | 0.110140 | 0.013753 | 26,760 |

US `dig5`/row is flat across all six files (0.1073–0.1101, a 2.6% spread), but
US `dig6`/row **splits cleanly by source**: ~0.0012 on source 1 versus ~0.0134–0.0143

## Relation to the two REFUTED findings

- **REFUTED-1 ("French postal codes are discarded by the `pin` guard").** Not
  re-derived, and **not supported**. France in this file has `dig5` = 1,082 over
  259,452 rows = **0.004170/row**, against US 0.109789 — a 26x gap in the direction
  the refutation predicts. The `pin` guard's impact is on US source-1
  (`dig6`/row 0.001196 here) and India, not on France.
- **REFUTED-2 ("`FR_REGIONS` is too thin, so France has no usable state signal").**
  I did not re-derive this and cannot test it from the profile — no `state`,
  `region` or `city` field is collected. But I **do** flag a scoping correction to
  the "100.00% (259,452 / 259,452)" figure carried in the record: those 259,452 rows
  are the **France rows of `test_s1`**, a file in which a comma-less address is
  impossible (§6). The figure is correct for `test_s1`; it is not a corpus-wide
  property of French state resolution. P005 measured the corresponding bounds
  (≤180 rows in `test_s2`, ≤153 in `test_s3`). This does **not** rehabilitate
  REFUTED-2 — 0.026% is immaterial next to a 14-vs-52 dictionary gap — it corrects
  the scope of a number that was carried forward as file-independent.

## Interpretation

*Everything in this section is inference, separated from the measurements above.*

1. **Test-time address quality depends on which source file you score.** If the
   leaderboard scores `test_s1` and `test_s2/s3` together, then the France rows in
   the scored set are split between one file with a 0% address-null rate and two
   with ~3%. Any conclusion of the form "French addresses are complete" is an
   artifact of having looked at `test_s1`. *Inference* about scoring composition —
   the profile records no split weights.
2. **The source-1 null-free property is worth confirming before it is relied on.**
   If source 1 is a curated or deduplicated export, then null-handling code paths
   are exercised *only* by sources 2/3, and a regression test built on `test_s1`
   alone would pass while testing nothing. *Inference* — I did not read the export
   or ingestion code.
3. **The sharp name-length concentration argues against truncating `ncore` early.**
   With 82.63% of US names ≤29 chars and 99.92% ≤49, a character budget for blocking
   keys would need to sit above ~50 chars to avoid concentrating collisions in the
   tail. I have not measured the current budget, so treat this as a caution.

## Gaps

Fields **not collected** by `build_profile.py`, therefore not answerable here and
**not estimated** anywhere above:

- **No `n_comps` / component-count / component-position field.** This is the
  single largest blind spot in the profile. `build_profile.py:126` splits on
  `[,;]` only to feed the token counter and **discards the component count**.
  Without it I cannot say what the 180 comma-less France rows in `test_s2` contain,
  and I cannot settle the component-order question raised in `already_checked`.
- **No `state` / `city` / `region` field.** `normalize_address`'s outputs are never
  captured by the profiler, so every state-resolution statement in this document
  is either a direct count of comma-less rows or a *bound* derived from upstream
  code — never a direct measurement of state resolution.
- **No sample strings.** `alpha_only_addr = 1` cannot be traced to the address it

## Recommendations

1. **[High priority, NEW] Never quote a per-file rate as a corpus-wide rate.**
   Record the null-free / comma-complete property of source 1 alongside the file
   counts in `profile.log`. Concretely: the "100.00% French state resolution"
   figure is a `test_s1` figure. Expected effect: prevents a wrong number being
   carried into the record a third time. Cost: one line.
2. **[High priority] Add a `n_comps` field to `build_profile.py`** recording
   `len([c for c in ba.split(",") if c.strip()])` per row, plus the index of the
   component containing a 5-/6-digit run. One field converts P005's ≤180-row bound
   into a measured count and is the only route to the component-order question.
   Expected effect: pure diagnostic, no pipeline change, one extra streaming
   counter at negligible cost.
3. **[Medium priority] Build null-handling regression tests on a source-2/3 slice,
   not on `test_s1`.** `train_s1` and `test_s1` contain **zero** empty addresses, so
   any null-path test constructed from them asserts nothing. Expected effect: the
   test suite starts exercising the paths that sources 2/3 actually use.
4. **[No change] Do not add null handling, prefix repair, or name handling for US
   `test_s1`.** `name_empty`, `addr_empty` and `prefix_bad` are all exact zeros.
   Manufacturing a fix here would be noise, and the 2.6%–3.7% null rates that
   *do* exist live in sources 2/3 where `prep.py:23` (`fill_null("")`) already
   absorbs them.
5. **[No change] No dictionary entry is warranted from this slice.** This work order
   is a shape/null-rate profile. It produced evidence of a *per-source data
   property*, not a missing normalisation token, so I propose no
   `CONFIRMED`/`LIKELY`/`SPECULATIVE` dictionary entries.
6. **[Low priority, informational] Audit any feature gated on `has_comma` for the US
   path.** In this file `has_comma` = `rows` exactly and `addr_empty` = 0, so the two
   are trivially aliased here. *Inference* — I did not read the feature builder, so
   I cannot say whether such a gate exists.

## Confidence markers

| Claim | Marker | Basis |
|---|---|---|
| US test_s1 = 663,106 rows, 38.2735% of file | **CONFIRMED** | `rows`, `by_country.US.rows`, arithmetic shown |
| `country_rows` sums exactly to `rows` | **CONFIRMED** | exact integer identity |
| `len_hist` sums exactly to `rows` | **CONFIRMED** | exact integer identity |
| `name_empty` = `addr_empty` = `prefix_bad` = 0 | **CONFIRMED** | exact zeros, `build_profile.py:94,98,100` |
| `has_comma` = rows (100%) | **CONFIRMED** | exact |
| US `dig5`/row = 0.109789, `dig6`/row = 0.001196 | **CONFIRMED** | direct fields, arithmetic shown |
| France `dig5`/row = 0.004170 vs US 0.109789 | **CONFIRMED** | direct fields |
| `alpha_only_addr` = 1 | **CONFIRMED as a count** | direct field; content unknown |
| Both source-1 files null-free and comma-complete, all countries | **CONFIRMED** | 15 country-slices, zero exceptions |
| Source index (not country/split) drives the property | **CONFIRMED** | the pattern; "source index" as the *label* is inference |
| *Why* sources differ (two generators / two pipelines) | **SPECULATIVE** | no provenance metadata in the profile |
| The 100% French state-resolution figure is `test_s1`-scoped | **CONFIRMED as a scoping correction** | file identity of the 259,452 rows |
| Scored-set composition mixes null-bearing and null-free files | **SPECULATIVE** | no split weights recorded |
| `ncore` truncation below ~50 chars would hurt | **SPECULATIVE (advisory)** | current budget not measured |

  counts, and no `dig5`/`dig6` occurrence can be attributed to a specific row.
- **No row-level `has_5digit` / `has_6digit` boolean.** `dig5`/`dig6` are occurrence
  counts, so distinct-row rates are bounded above, not measured.
- **No true-empty vs whitespace-only distinction.** The builder `.strip()`s before
  testing emptiness (lines 96–97), so `"   "` is already counted as empty. In this
  file that distinction is moot (`addr_empty = 0`), but it matters for sources 2/3.
- **Which prefix convention `prefix_bad` tests is not recorded** in the profile. I
  verified in `build_profile.py:94` that it is `startswith(f"S{src}-")` with
  `src=1`, so I can report that the `S1-` prefix holds for 100% of US rows.
- **Token counters are top-4000 and hapax-pruned** (`prune`, line 45), so no
  vocabulary size, type-token ratio, or unique-business count is derivable.
- **No duplicate-row or unique-entity count**, so I cannot say how many distinct
  businesses these 663,106 US rows represent.

on sources 2/3, a **~12x jump**. This is the source-1 asymmetry the `already_checked`
block flags as already covered ("US dig6/row 0.001 there vs 0.013-0.014 in US
source-2/3"). My figures reproduce it on `test_s1` (0.001196) independently; I am
**not** re-deriving it as a new finding, and I did not re-test the France-postcode
version of the claim.


Because `addr_empty = 0`, the two mean-address figures are **identical by
construction** — there is no null/non-null denominator split to make. This is the
one place where this slice differs structurally from its siblings, and it is why
I report a single number rather than the pair P002/P003/P005 report.

`num_digits` counts digits in the **address only** (`build_profile.py:114` uses
`ba`, not `bn`); digit-in-name is the separate `has_digit_name` field.
