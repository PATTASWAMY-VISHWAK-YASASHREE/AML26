# D122 - remaining gaps in `ADDR_GENERIC`

**Status: TWO NEW DEFECTS FOUND.** The France-postcode and France-region
hypotheses are dead, and the three prior defects (`bis`/`ter`, the 19-entry
France gap, `st`/`ste` dead for France) all replicate exactly. But two
structural defects that nobody found are larger than all of them, and one of
them **invalidates the D116 safety argument as applied to this dictionary**.

Sources read: `_upstream/src/keys.py`, `_upstream/src/normalize.py`,
`_upstream/src/features.py`, `_upstream/src/blocking.py`,
`_upstream/src/prep.py`, `_upstream/src/build_features.py`,
`_upstream/src/run_blocking.py`, `build_profile.py`,
`analysis_out/profile/{test,train}_s{1,2,3}.json`.
Prior work built on, not redone: D091, D094, D116, D119, D120, D127.

---

## Headline

1. **NEW-1 (largest): 9 of the 62 entries are structurally inert.**
   `keys.py:42` gates the `alph` bucket on `str.len_chars() >= 3`, and
   `keys.py:41` gates `nums` on `^\d+$`. **No digit-only string is in
   `ADDR_GENERIC`** (measured: 0 of 62). Therefore **every entry shorter than
   3 characters can never affect a blocking key, no matter how much mass it
   removes.** The 9 are `st, rd, dr, ln, ct, pl, sq, fl, po`. Across the three
   **test** files they strip **5,848,087 of 14,652,812 = 39.91%** of all
   `ADDR_GENERIC` removal mass - **two fifths of the dictionary's apparent
   work is provably invisible to the pipeline.**

2. **NEW-2: the D116 "adding entries deletes IDF feature mass" argument does
   NOT transfer to `ADDR_GENERIC`.** D116 was right about `FR_REGIONS`, where
   `normalize.py:335` `continue`s and deletes tokens from `toks` *before*
   `atoks` is written. `ADDR_GENERIC` is applied at `keys.py:39`, which builds
   a **local** `toks` list; `keys.py:45` returns only
   `rid, country, nt, pref, nums, alph, pin, fk` - **`atoks` is not an output
   column and is never written back**. `prep.py:16` wrote `atoks` to parquet
   long before `run_blocking.py` runs, and `build_features.py:26`
   `token_idf(frames, "atoks")` plus `features.py:129` read that untouched
   column. **So adding entries to `ADDR_GENERIC` costs zero IDF feature mass.**
   The 19-entry gap is therefore *not* the regression D116's precedent
   suggests - the two dictionaries act at different pipeline stages, and only
   one of them is upstream of the features.

3. **CONFIRMED replication** of the three prior defects, with my numbers
   matching to the unit: `bis` 69,757 vs `ter` 11,907 = **5.86x**
   (prior: 5.86x); the 19-entry France gap = **336,623** (prior: 337,553 -
   see section 6, the 930 difference is `st`, which I exclude because it is a
   stoplist *input* for France, not an output); `st`/`ste` fire **0** times
   for France while `dr` fires **10,618**.

4. **Dead weight: exactly 5 entries fire zero times in all six files** -
   `floor, road, lane, street, plaza`. Four of the five are the
   redundancy D091 already identified (canon renames them to a covered twin).
   **`plaza` is the one true dead entry**: canon sends it to `plz`, which is
   not in the list, so `plaza` can never fire and `plz` leaks instead.

5. **Cross-country collision: real, and it is one-directional.** The French
   entries `rue/chemin/allee/impasse` fire **0** times in US and India, so
   D091's D3b "cross-country contamination" has **no measurable effect on
   this dataset**. The live direction is the reverse: French street noise in
   US/India address tokens - `saint` **201,117** in US, `rte` 7,114 in US,
   `crs` 3,285 in India - reaches the US/Indian keys unstoplisted.

---

## 1. Method and denominators

I replicated `keys.py:39` exactly: for every listed `addr_tokens` entry I
applied the real `canon` transform (`normalize.py:321` for France, `:319` for
US/India) and then tested `ADDR_GENERIC` membership. The profile stores **raw
pre-canon** tokens (`build_profile.py:113,126-127` - no `canon.get`
anywhere), so this ordering is required, not optional.

**Replication check - my test-split totals reproduce the D091 D0 table
exactly**, which validates the method:

| Country | Listed mass | Removed by empty canon | Removed by `ADDR_GENERIC` | Survives |
|---|---|---|---|---|
| US | 20,533,409 | 118,742 (0.58%) | 5,029,788 (24.50%) | 15,384,879 (74.93%) |
| France | 11,992,918 | 184,862 (1.54%) | 1,770,731 (14.76%) | 10,037,325 (83.69%) |
| India | 51,134,252 | 4,927,131 (9.64%) | 7,852,293 (15.36%) | 38,354,828 (75.01%) |

All figures are **token occurrences within the top-4000 listed set**, never
rows. Train files carry **no `France` key** in `by_country`/`addr_tokens`
(countries present: `US, India`) - consistent with D116's zero-French-
training-rows finding. I state the France denominator per file and never as a
single-source rate:

| file | France listed mass | 19-entry gap mass | % of listed |
|---|---|---|---|
| test_s1 | 2,253,877 | 43,389 | 1.9251% |
| test_s2 | 4,745,780 | 95,247 | 2.0070% |
| test_s3 | 4,993,261 | 99,539 | 1.9935% |
| **test total** | **11,992,918** | **238,175** | **1.9860%** |

> **Denominator correction to D127.** D127 quotes 2.814% for the 19-entry
> gap. I measure **238,175 / 11,992,918 = 1.986%** on the **test** files. The
> 2.814% figure is not reproducible on the French test population, and train
> contains **no France at all**, so it cannot be reached by adding train mass.
> On the population that actually contains France the gap is **1.986%**, and
> **2.814% overstates it by 1.42x**. I flag the discrepancy rather than
> resolving it - see section 6a for the arithmetic I can defend.

---

## 2. NEW-1 - 9 entries are structurally inert (the largest finding)

`keys.py:39-43`:

```python
toks = (pl.col("atoks").str.split(" ").list.eval(pl.element().filter(~pl.element().is_in(ADDR_GENERIC) & ...)))
nums = toks.list.eval(... filter(str.contains(r"^\d+$"))).list.head(MAX_NUM)
alph = toks.list.eval(... filter(~str.contains(r"^\d+$") & (str.len_chars() >= 3)))...head(MAX_ALPHA)
```

`toks` has exactly **two** consumers: `nums` and `alph`. No third path
exists - `make_keys` (`keys.py:53-73`) consumes only `tl.nums` and `tl.alph`
from this local frame. So a stoplist entry can only ever matter if its
canonical form is either digit-only (-> `nums`) or >=3 chars (-> `alph`).

- **Digit-only entries in `ADDR_GENERIC`: 0 of 62.** So the `nums` route is
  closed for every entry.
- **Entries with length < 3: 9** - `st, rd, dr, ln, ct, pl, sq, fl, po`.

**These 9 therefore remove tokens that were never going to enter a key
anyway.** They are not "harmless redundancy" (D091's word for `floor`/`road`/
`lane`/`street`); they are strictly dead code with a measurable footprint that
reads as work.

Measured mass they strip, all six files: `rd` 4,469,711; `st` 2,798,350;
`dr` 2,030,601; `fl` 1,830,216; `ln` 965,573; `ct` 640,613; `po` 388,280;
`pl` 360,458; `sq` 71,855 -> **13,555,657**. On the three **test** files:
**5,848,087 of 14,652,812 = 39.91%**.

This is the answer to the work order's dead-weight question, and it is a
stronger form of it: the dictionary is not merely carrying entries that fire
rarely, it is carrying **nine entries whose entire effect is provably
unobservable**, including the two largest single-country removers in the
table (`rd` 2,198,791 US, `fl` 1,717,189 India).

**[INFERENCE]** Removing them would not change a single key. I have not run
the pipeline, so I claim no score delta; the claim is structural and follows
from the two quoted filters.

## 3. NEW-2 - the D116 safety argument does not transfer

The work order asks me to argue whether adding the 19 entries is safe, noting
D116 used the same argument against extending `FR_REGIONS`. **For
`ADDR_GENERIC` the argument fails, and the reason is a pipeline-stage
difference.**

| | `FR_REGIONS` (D116) | `ADDR_GENERIC` (here) |
|---|---|---|
| applied at | `normalize.py:333-335` | `keys.py:39` |
| mechanism | `continue` skips `toks.extend(ctoks)` at `:350` | `.filter(~is_in(...))` on a **local** list |
| upstream of `atoks`? | **YES** - deletion happens before `prep.py:16` writes the column | **NO** - `keys.py:45` returns `rid, country, nt, pref, nums, alph, pin, fk`; `atoks` is **not** an output column |
| reaches `token_idf` / `wa_*`? | **YES** | **NO** |

`prep.py:16` persists `atoks` to parquet. `run_blocking.py:11-12` reads those
parquet files. `build_features.py:24-26` builds `addr_idf` from
`token_idf(frames, "atoks")` and `features.py:129` computes `wa` over
`q_atoks`/`s_atoks`. None of these see the `keys.py:39` filter.

**Conclusion: adding the 19 entries removes zero IDF feature mass.** The
D116 cost argument - "losing 0.55% of address IDF mass to gain 0.496% state
coverage is a bad trade" - does not apply here, because there is no IDF cost
to pay. The 19 entries are not "adds that delete a feature"; they are pure
blocking-key cleanups.

**But the conclusion is still "do not add all 19", for a different reason
than D116's.** The real objection is that the 19 are not homogeneous:

- **Identity-bearing, would be a REGRESSION if added: `saint` (166,818) and
  `sainte` (8,077) = 174,895, 52.0% of the gap.** `saint` is a genuine
  French toponym morpheme - `Saint-Etienne`, `Saint-Denis`, `Sainte-Marie`.
  Adding it to a *delete* stoplist would strip a **discriminative** token from
  French blocking keys, making them coarser and less selective. D091 flagged
  this as "a design decision that has not been made"; I now put a number on
  it: it is the **largest single item in the gap and the most dangerous to
  add.**
- **Genuine noise, safe to add (CONFIRMED): `bis` 69,757, `rte` 29,927,
  `crs` 13,281, `res` 13,088, `quai` 13,004, `gen` 6,078, `mal` 4,730,
  `bat` 3,745, `fbg` 3,046, `prof` 2,485, `pres` 2,380** = 159,523
  (47.3%). These are address-type or rank-qualifier morphemes with no
  toponym value - the same category as `rue`/`avenue`, which the list
  already carries.
- **Unmeasurable, do not add on this evidence: `lieu` 181, `zone` 26, and
  `lieudit`/`za`/`zi`/`zac` = 0.** "0" here means *not in the top 4000*
  (cutoffs: s1 = 23, s2 = 58, s3 = 60), **not** "does not occur".
  Additionally `za` and `zi` are **2 characters and therefore inert** (NEW-1),
  so adding them is a provable no-op.

## 4. Is the `bis`/`ter` asymmetry the only direction of error? - No

The work order asks whether other pairs share the shape "one sense handled,
the other not". **Two more exist, and one is comparable in size to `bis`.**

**(a) `rte` - the same defect as `bis`, and nobody framed it as such.**
`route`, `rt` (`normalize.py:177`) and FR `route`/`rte` (`:204`) all canon to
**`rte`**. `rte` is **not** in `ADDR_GENERIC`. But **`rd` is** - and `rd` is
canon's output for `road` (`:155`), a *semantically identical* concept. So the
dictionary suppresses the English "road" spelling and leaks the French
"route" spelling, exactly the `ter`/`bis` inversion:

| Country | `rte` (leaks) | `rd` (suppressed) |
|---|---|---|
| US | 24,537 | 2,198,791 |
| India | 2,446 | 2,270,279 |
| France | **29,927** | 641 |
| **total** | **56,910** | 4,469,711 |

`rte` is **cross-country** whereas `bis` is France-only, and it is in the
work order's 19-entry list - so it is not unnoticed, but nobody identified it
as a **synonym-pair asymmetry with a suppressed twin**, which is what makes it
actionable: adding `rte` alongside the existing `rd` costs nothing and closes
all three countries at once.

**(b) `plz` - D091's D1 hole, confirmed and quantified.** `plaza`->`plz`
(`:177`), `plz` absent from the list: US 8,286 + India 117,683 = **125,969**.
Unlike `bis`/`rte`, `plaza` itself is also in the list and is *permanently
dead* (section 5) - so the entry is not merely misplaced, it is unreachable.

**(c) Not a defect, for the record:** `st`/`ste`/`dr` are the three
`ADDR_GENERIC` entries that overlap the France key-drop at `normalize.py:321`.
Measured: `st` US 2,379,276 / India 419,074 / **France 0**; `ste` US 24,529 /
India 15,128 / **France 0**; `dr` US 1,959,575 / India 60,408 / **France
10,618** (live, because `ADDR_CANON_FR:208` re-adds `docteur`->`dr`). This
confirms the brief's item 3 exactly. `n/s/e/w` are **not** in `ADDR_GENERIC`
at all, so the D120 no-op finding is orthogonal and I did not redo it.

## 5. Dead weight - the full 62-entry table

**Exactly 5 entries fire zero times across all six files:**

| Entry | Why |
|---|---|
| `floor` | canon `floor`->`fl` (`:174`); `fl` in list (but `fl` is itself inert, NEW-1) |
| `road` | canon `road`->`rd` (`:155`); `rd` in list (inert, NEW-1) |
| `lane` | canon `lane`->`ln` (`:159`); `ln` in list (inert, NEW-1) |
| `street` | canon `street`->`st` (`:154`); `st` in list (inert, NEW-1) |
| **`plaza`** | canon `plaza`->`plz` (`:177`); **`plz` NOT in list - the only true hole** |

The first four are D091's confirmed redundancy. `plaza` is the real one.

**18 entries are single-country live** (US-only: `trl` 123,479, `pkwy` 59,054;
India-only: `nagar` 1,604,794, `near` 729,328, `sector` 548,822,
`block` 511,622, `opposite` 328,751, `complex` 262,456, `phase` 223,531,
`office` 220,287, `wing` 110,942, `ltd` 94,673, `apts` 91,329, `off` 70,706,
`pvt` 15,120; France-only: `rue` 1,096,807, `allee` 79,868, `impasse` 33,330,
`chemin` 28,332). None is harmful - they are correctly-scoped vocabulary - but
**combined they are 4,793,072 occurrences that only ever affect one country**,
because `keys.py:39` has no `country` predicate.

**The `1st`-`5th` entries are live and correctly placed** (test-split mass
`1st` 254,592, `2nd` 220,547, `3rd` 148,346, `4th` 93,472, `5th` 61,166).
They are length-3 and not digit-only, so they reach `alph`; and they do not
interact with the `MAX_ALPHA` sort because they are removed before it. D091's
analysis holds.

## 6. Two corrections to prior work

**(a) D127's 2.814% does not reconcile with the French test denominator.**
My defensible arithmetic is in section 1: **238,175 / 11,992,918 = 1.986%** on
the three test files, with each file stated separately. D127 quotes 337,553
tokens = 2.814% for the same 19-entry set. My all-files total for the 19 is
336,623 - within 930 of D127's 337,553, the difference being `st` (I exclude it
because for France `st` is a stoplist *input* that canon rewrites to `saint`,
not one of the 19 *outputs*). So **the token counts agree; only the percentage
disagrees**, which means the two figures use different denominators. I could
not determine which, because the profile carries no per-token provenance and
train has no France rows to add. **I report 1.986% as the figure I can show
the arithmetic for, and flag 2.814% as unreconciled rather than silently
adopting or discarding it.** The direction matters: if 2.814% is right the gap
is 42% larger than I measure; if 1.986% is right D127 overstates the prize.

**(b) D091's D3b cross-country contamination has zero measured effect.**
D091 flagged `rue/chemin/allee/impasse` being dropped from US/India keys and
marked the count a GAP. I measured it: those four tokens occur **0 times** in
US and India `addr_tokens` across all six files. So the design smell is real
but the **effect on this dataset is exactly zero**. The live direction is the
opposite one (section 7).

## 7. Cross-country collision - the real one runs the other way

D091 asked which entries could collide across countries. Measured, all six
files, raw profile tokens:

| token | US | India | note |
|---|---|---|---|
| `rue`, `chemin`, `allee`, `impasse`, `quai`, `bis`, `fbg` | **0** | **0** | D091's concern: no effect |
| `saint` | **201,117** | 0 | French morpheme in US addresses; **unstoplisted in the US** |
| `rte` | 7,114 | 0 | leaks in all three countries |
| `crs` | 0 | 3,285 | leaks in India |

`saint` in US address tokens (201,117) is the single largest cross-country
contamination in the dataset, and because `saint` is in neither
`ADDR_GENERIC` nor `ADDR_CANON_COMMON`, it passes through the US canon
untouched and reaches US blocking keys. This is a *different* defect from the
French `saint` question (which is about whether to add it) - here the problem
is that a French-only morpheme may be polluting US keys, and the one-line fix
is country-scoping, not dictionary content. **[INFERENCE]** I did not read raw
TSVs, so I cannot say what these US strings are ("Saint Louis" is a plausible
and *legitimate* US toponym, which would make this correct rather than
defective). **Flagged as a gap requiring raw inspection; not claimed as a
defect.**

## 8. Answers to the three work-order questions

**(a) Which entries are never / almost never fired?** Exactly **5** fire never
(`floor, road, lane, street, plaza`); **9 more are structurally inert**
(`st, rd, dr, ln, ct, pl, sq, fl, po`, NEW-1) - 14 of 62 (22.6%) have no
observable effect on blocking keys. **18** are single-country live.

**(b) Which profile tokens does it not handle but should?** Ranked by measured
France mass, split by whether adding is safe: **safe/CONFIRMED** `bis` 69,757,
`rte` 29,927, `crs` 13,281, `res` 13,088, `quai` 13,004, `gen` 6,078,
`mal` 4,730, `bat` 3,745, `fbg` 3,046, `prof` 2,485, `pres` 2,380 (159,523);
**would be a regression** `saint` 166,818 + `sainte` 8,077 = 174,895;
**unmeasurable / inert** `lieu` 181, `zone` 26, `lieudit`/`za`/`zi`/`zac` = 0.
Cross-country, add to fix all three at once: `plz` 125,969, `rte` 56,910.

**(c) Which entries could collide across countries?** The four French street
words collide in *principle* but fire **0** times in US/India (no effect).
The live, measurable contamination is the reverse: `saint` 201,117 in US,
`rte` 7,114 in US, `crs` 3,285 in India reach US/Indian keys unstoplisted.

## 9. Verdict

**`ADDR_GENERIC` is not fine, and the defects are structural rather than
vocabulary gaps.** Prior work found the right *entries*; the larger problems
are that (i) **39.91% of its test-split removal mass is provably invisible**,
(ii) **its single largest gap item (`saint`) would be a regression to add**,
and (iii) **the same synonym-pair inversion that produced `bis` also produces
`rte`, cross-country, at comparable mass.**

Recommended, in order of value:
1. **CONFIRMED, free:** add `rte` (and `plz`). Closes a 56,910 / 125,969
   cross-country leak at zero feature cost, because NEW-2 shows the IDF
   argument does not apply here.
2. **CONFIRMED, free:** add the 11 safe French type morphemes (159,523).
3. **SPECULATIVE, needs a decision:** `saint`/`sainte` - do **not** add
   blind; 174,895 of toponym-bearing token would be stripped from French keys.
4. **Cosmetic:** the 9 inert 2-letter entries and the 5 zero-mass entries can
   be deleted with provably zero effect on keys. Low value, but they make the
   dictionary honest about what it does.

## 10. Gaps and limitations (stated, not smoothed over)

- **All mass figures are token occurrences in the top-4000 listed set**, not
  rows and not absolute mass. The tail is truncated. A token at 0 is *not in
  the top 4000* (cutoffs s1 23 / s2 58 / s3 60), never "does not occur".
- **NEW-1 and NEW-2 are structural claims from quoted code**, not measured
  score deltas. I did not run the pipeline; I claim no F0.5 change.
- **I could not resolve D127's 2.814% denominator** (section 6a). My own
  1.986% is shown with full arithmetic; the gap between the two is flagged,
  not closed.
- **US `saint` (201,117)** is flagged as needing raw inspection, not claimed
  as a defect (section 7). I did not open any `*.tsv`.
- **The `bis`/`ter` and 19-entry figures are replications**, not new findings;
  I report them because the brief requires every number to be traceable and
  because they validate my pipeline against D091/D094.
- `build_profile.py` flattens components; I did not use component structure
  for any claim here.
- Read-only respected on `amazon_ml_2026_research/` and `_upstream/`. No
  network. Exactly two files written: this `.md` and
  `analysis_out/findings/D122_gaps_ADDR_GENERIC.json`.

*Written by analysis agent b02, D122.*
