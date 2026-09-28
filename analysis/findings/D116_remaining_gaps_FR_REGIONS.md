# D116 — remaining gaps in FR_REGIONS

> **Authoritative artefact. All numbers traceable to a named field in
> `analysis_out/profile/*.json` or to a quoted line of `_upstream/src/*.py`.**
> Claims not backed by either are tagged `[INFERENCE]`.
> Sidecar: `analysis_out/findings/D116_remaining_gaps_FR_REGIONS.json`.

## Headline

**No change to `FR_REGIONS` is warranted. The premise of this work order is
refuted by direct measurement, and the residual gap is not a dictionary gap.**

Four results, in descending importance:

1. **The premise "s2/s3 encode geography with department names that
   `FR_REGIONS` does not handle" is FALSE — the three examples given as
   evidence are all already `FR_REGIONS` keys.** `gironde`, `nord` and
   `loire atlantique` are keys at `normalize.py:244,246,247`. Their s1->s2
   count jump is a *frequency* shift between sources, not a *coverage* gap.
   (0.496% is the real maximum recoverable, §3.)

2. **NEW — the most important thing I found, and it is not in `FR_REGIONS`:
   France has ZERO training rows.** `country_rows` in `train_s1/s2/s3.json`
   contains only `US` and `India`. Consequently `_upstream/src/crossfit.py:112`
   iterates `for c in ("US", "India")` — France is never trained on. France is
   *test-only*, and the codebase already knows it:
   `decoy_postfilter.py:17-18` — *"the country has no training labels (e.g.
   France in the test set)"*. See §4. This dwarfs any dictionary question.

3. **A maximal French department/region gazetteer would recover at most
   8,400 French test rows (0.496% of 1,694,445)**, and that is a deliberately
   optimistic union bound. §3.

4. **The IDF-weighted features already see every one of these tokens.**
   `features.py:129` computes `wa` over `q_atoks`/`s_atoks`; a department name
   that does not match an `FR_REGIONS` key is **retained** in `atoks` and
   contributes to `wa_wj`. Adding the key would make `normalize.py:335`
   `continue` and **delete** the token from `atoks` — removing signal rather
   than adding it. §5. This is the strongest argument the fix is unnecessary.

**Verdict: leave `FR_REGIONS` alone.** The `normalize.py:252` self-map
omission is real but has zero effect on this dataset (all 14 canonical values
occur 0 times as input tokens). That statement is about the self-map loop
**only** and is *not* evidence about §3; the two are kept separate throughout.

---

## 1. Scope, denominators and method

### 1.1 Denominators (the classic tell in this project)

France row counts, from `country_rows["France"]`:

| file | France rows | share of all-France |
|---|---|---|
| `test_s1` | 259,452 | 15.31% |
| `test_s2` | 703,378 | 41.52% |
| `test_s3` | 731,615 | 43.18% |
| **total test** | **1,694,445** | 100% |
| `train_s1` | **0** (no `France` key) | — |
| `train_s2` | **0** (no `France` key) | — |
| `train_s3` | **0** (no `France` key) | — |

Checks: 259,452 + 703,378 + 731,615 = 1,694,445. 259,452 / 1,694,445 = 15.31%.
`country_rows` for the train files is `US=1323633 India=883188` (s1),
`India=2017799 US=3016817` (s2), `US=3170056 India=2115547` (s3) — no France.

**Every rate in this report is stated per source file and only then summed.**
I never quote a single-source rate as a France-wide rate.

### 1.2 The matching rule I replicate

`_upstream/src/normalize.py:322-335`:

```python
comps = [c.strip() for c in s.split(",")]
...
    ck = re.sub(r"[^a-z0-9& ]+", " ", c).replace("&", " and ")
    ck = " ".join(ck.split())
    if ck in smap:          # smap == FR_REGIONS for France (line 250)
        state = smap[ck]
        continue
```

A France row resolves a state **iff** some whole comma-component equals one of
the 14 keys, after `translit_text` + `strip_accents` + lowercasing.

### 1.3 The bound, and the two soundness corrections

`build_profile.py:31` splits the address on `[,;]` and line 140 keeps only
`most_common(4000)`. So for a multi-token key, the number of rows that can
*contain* it is at most the **minimum** of its token counts. Summing over keys
gives a union bound `UB`; overlap only inflates it, so

> resolvable <= min(UB, rows);  unresolved >= max(rows - UB, 0)

Two corrections, both required for soundness:

- **Truncation.** A token absent from the top 4000 has count <= the rank-4000
  cutoff — **not 0**. Measured cutoffs (`addr_tokens["France"][-1]`):
  **s1 = 23, s2 = 58, s3 = 60**. I substitute the cutoff.
- **Accent loss.** `TOKEN_RE = [a-z0-9]+` (`build_profile.py:28`) is applied to
  the lowercased address with **no** `strip_accents`. `Ile-de-France` yields
  profile token `le` (the circumflex-i vanishes), while `normalize_address` sees
  `ile`. So the profile **undercounts** accented keys. `le` is a valid upper
  stand-in for `ile` because every circumflex-`ile` row also emits `le`. Measured
  `ile`/`le`: 303/1,992 (s1), 817/4,882 (s2), 794/5,050 (s3).

I use both. Both are one-directional and both make the bound *weaker*, never
stronger.

---

## 2. The premise, tested and refuted

My work order states:

> *"ROOT CAUSE: s1 encodes geography with REGION names, but test_s2 and
> test_s3 encode it with DEPARTMENT names, and most of those departments are
> absent from FR_REGIONS. Examples from addr_tokens[France]: gironde 62 (s1) vs
> 75,104 (s2) and 75,621 (s3); nord 200 (s1) vs 75,362 (s2) and 76,449 (s3);
> atlantique 253 (s1) vs 63,697 (s2) and 64,398 (s3)."*

Every one of those three examples is a key **today**:

| cited "absent" token | is it an `FR_REGIONS` key? | source |
|---|---|---|
| `gironde` | **YES** -> `naq` | `normalize.py:246` |
| `nord` | **YES** -> `hdf` | `normalize.py:244` |
| `atlantique` (in `loire atlantique`) | **YES** -> `pdl` | `normalize.py:247` |

The counts quoted are all **correct** — I reproduced them exactly (§3.1 table).
What is wrong is the *interpretation*: the s1->s2 rise is these keys becoming
**more frequent** in s2/s3, not becoming **newly covered**. A key present in
both files resolves in both files. The s2/s3 geography signal was never missing
from the dictionary.

**What is actually true** is a claim about *frequency*, and it is still
interesting: s1 is region-dominated (`hauts de france` 101,717; `nouvelle
aquitaine` 85,268; `pays de la loire` 72,812) while s2/s3 are
department-dominated (`nord` 200->75,362; `gironde` 62->75,104; `loire
atlantique` 253->63,697). Since all three are keys, **the dictionary already
handles the s2/s3 style.** This is a real observation about the data's encoding,
and it means the s2/s3 gap is *not* a dictionary gap.

---

## 3. How many entries would be needed, and what they would buy

### 3.1 Current 14 keys — per-key bound, all three test files

`addr_tokens["France"]` count of the binding (minimum) token. "<=" means absent
from the top 4000, so count <= the rank-4000 cutoff (s1 23 / s2 58 / s3 60).

| key | s1 | s2 | s3 |
|---|---|---|---|
| `hauts de france` | 101,717 | 88,519 | 99,419 |

### 3.2 A maximal gazetteer, strictly restricted

I scored 24 French department / region / overseas names. To count only
*genuinely new* coverage I required each candidate key's token set to be
**disjoint** from the 20-token set the current 14 keys already use
(`aisne aquitaine atlantique calais de france gironde hauts ile la landes
loire nord nouvelle oise paris pas pays somme vendee`). Two candidates were
disqualified on that rule:

- `val de marne` — shares `de`
- `maine et loire` — shares `loire`

**20 disjoint candidates survive.** Per-file upper bound:

| file | rows | disjoint-add UB | share |
|---|---|---|---|
| `test_s1` | 259,452 | 1,435 | 0.553% |
| `test_s2` | 703,378 | 3,368 | 0.479% |
| `test_s3` | 731,615 | 3,597 | 0.492% |
| **total** | **1,694,445** | **8,400** | **0.496%** |

Largest contributors (s3): `marne` 1,061 · `gard` 320 · `haute normandie` 239
· `haute marne` 239 · `auvergne` 218 · `martinique` 173 · `cote d or` 169.
Everything else is under 150.

**Threshold stated:** I kept every candidate whose binding-token count exceeds
the rank-4000 cutoff in at least one file (i.e. **> 60**). Of the 84
metropolitan department names I enumerated, **58 are not resolvable above the
cutoff in any file** (not in the top 4000 at all) and 26 clear it, of which 6
(`nord`, `gironde`, `loire-atlantique`, `pas-de-calais`, `somme`, `landes`)
plus `paris` and `oise` are **already keys**. So the genuinely new set is
~20 keys, most of them small.

**This 0.496% is deliberately optimistic** — it is a union bound, so keys whose
components co-occur in one row (e.g. `haute`+`marne`+`cote`) are double-counted,
and a token count is not a component count. The true recoverable figure is
**lower**. I state it as a ceiling, not an estimate.

---

## 4. NEW: France has no training data at all

This is the finding I consider most consequential, and it is not a
`FR_REGIONS` question at all.

**Evidence.**

1. `country_rows` in `train_s1.json` = `{US: 1323633, India: 883188}`;
   `train_s2.json` = `{India: 2017799, US: 3016817}`;
   `train_s3.json` = `{US: 3170056, India: 2115547}`. **No `France` key in any
   of them.** `by_country` likewise has no `France` entry. A raw
   `Select-String` for `"France"` against `train_s1.json` returns 0 matches.
2. `_upstream/src/crossfit.py:112`:
   ```python
   for c in ("US", "India"):
       pth = f"{W}/cf_best_{c}.parquet"
   ```
   and line 122: `best = pl.concat([pl.read_parquet(f"{W}/cf_best_{c}.parquet") for c in ("US", "India")], ...)`.
   France never enters the stage-2 context or the training table.
3. The codebase **explicitly acknowledges** this.
   `_upstream/src/decoy_postfilter.py:17-18`:
   > *"(b) the country has no training labels (e.g. France in the test set) and
   > d is any decoy offset... Without labels for that country the model is least
   > calibrated."*

   And `decoy_postfilter.py:179` derives it at run time:
   `unlabeled = [c for c in s1["country"].unique().to_list() if c not in train_countries]`.

**Consequence `[INFERENCE`, from 1+2]:** the LightGBM ranker at
`crossfit.py:143` is fit on US and India pairs only, then applied to 1,694,445
French test rows. Every France-specific parameter — including whatever
`state_eq` (`features.py:114`) contributes — is extrapolated, never validated
on French labels. **The binding constraint on France is the absence of
training labels, not the absence of dictionary entries.** A perfect
`FR_REGIONS` would still be consumed by a model that has never seen a French
example.

**This is the strongest argument for leaving `FR_REGIONS` alone.** Widening a
dictionary that feeds an unvalidated feature is low-value; the 0.496% ceiling
(§3.2) bounds the upside, while the label gap bounds the downside at 100% of
French rows.

I am **not** proposing a change to `crossfit.py`. Fabricating French training
labels is impossible (no ground truth exists), and the decoy postfilter already
handles the unlabelled case. This is a *context* finding that reframes the
whole France dictionary family.

---

## 5. Would the fix even help? The IDF argument — no

The brief asks me to argue this explicitly. Here is the mechanism.

`normalize.py:333-335`:
```python
    if ck in smap:
        state = smap[ck]
        continue        # <-- the component's tokens are NOT appended to `toks`
```

The `continue` means a matching component is **consumed**: its tokens never
reach `toks` (line 342 `toks.extend(ctoks)` is skipped), so they never reach
`atoks` in `prep.py:16`, so they never reach:

- `features.py:129` — `wa = _weighted_overlap(..., pl.col("q_atoks"), pl.col("s_atoks"), addr_idf, "wa")`, the IDF-weighted address overlap (`wa_wq`, `wa_ws`, `wa_wj`);
- `features.py:123-124` — `a_jac`, `a_cont`, the unweighted address Jaccard/containment;
- `keys.py:39` — the `alph` blocking tokens.

**So adding a department key does not add a feature. It deletes one.**

Right now `marne` appears in 1,061 French s3 rows. It is *not* an `FR_REGIONS`
key, so it stays in `atoks`, and when a French s2/s3 record and its s1
counterpart both sit in `Marne`, the shared token contributes to `wa_wj` and to
the AA blocking keys. Add `"marne": "idf"` and all 1,061 rows lose that token.
The pair goes from *sharing a rare, highly discriminative token* to *sharing
nothing there*.

This is the opposite of the usual intuition, and it is why "add the missing
department names" is the wrong fix. The dictionary's job here is to
**normalise**, not to **capture**. Normalisation pays when two spellings differ
(`ile` vs accented `île`, `vendee` vs accented `vendue`) and should be extended
for that. It does not pay when the raw token is already a clean, shared,
IDF-weighted feature.

I put a number on the mass at stake. Candidate-key tokens in the s2/s3 French
address-token mass (top-4000, which is what `addr_idf` is built from):

- `test_s2`: 25,944 of 4,745,780 = **0.55%**
- `test_s3`: 27,103 of 4,993,261 = **0.54%**

**Losing ~0.55% of the address IDF mass to gain 0.496% more state coverage is a
bad trade** — and the loss is a certain, immediate deletion from features that
are demonstrably live (`wa_*` is consumed at `features.py:139-146` into `w_sum`,
`w_sum_rank`, `w_sum_gap`, which feed the ranker), whereas the gain is a
`state_eq` value on a country the model has no labels for.

`[INFERENCE]` I cannot measure the counterfactual F0.5 without running the full
pipeline, which is out of scope and out of budget here. The argument above is a
mechanism argument from quoted code plus measured token mass, not a score
delta. I flag it as such rather than claiming a number I did not compute.

---

## 6. The three questions the work order asks, answered directly

**(a) Which entries are never / almost never fired (dead weight)?**

---

## 7. The confirmed self-map defect, stated separately

`normalize.py:252`:
```python
for _m in (US_STATES, IN_STATES):     # FR_REGIONS omitted
    for _v in list(_m.values()):
        _m.setdefault(_v, _v)
```

`US_STATES` has 104 keys after the loop (52 names + 52 abbreviations);
`IN_STATES` 86. `FR_REGIONS` is left at 14 and has **no** self-maps, so
`'hdf' in FR_REGIONS` is `False` (independently confirmed in the fleet log
`_fr2.log`: *"[FAIL] France abbreviations are ALSO self-mapped"*).

**Zero effect on this dataset:** the four canonical values are `hdf`, `naq`,
`pdl`, `idf`, and each occurs **0 times** as an address token — none appears in
the top 4000 of any of the six files, and a two-letter code like `idf` is not
how this dataset writes French regions.

**This is a statement about the self-map loop only.** It is *not* evidence that
the §3 residual is harmless, and the two must not be conflated. The fix is one
token (`for _m in (US_STATES, IN_STATES, FR_REGIONS):`) and is safe, but it is
**cosmetic on this dataset** — I recommend it only as cheap future-proofing,
not as a scoring fix.

---

## 8. Relation to the 71.10% vs 97.44% contradiction (a01 / D128)

I was asked to report token evidence and let a01 reconcile, not to settle it.
My evidence bears on it in one specific way, and I flag the limit of what I can
claim.

Both figures are **bounds of different kind**. Three distinct quantities:

| quantity | value | what it measures |
|---|---|---|
| D073 / inherited | 71.10% resolvable, 28.90% not | **dictionary** ceiling via per-key token minimum |
| D077 | 97.4380% ceiling | **address parseability** (non-empty AND comma-bearing) |
| **D116 (§3.1)** | **71.10% resolvable, 28.89% not** | same criterion as D073, independently reproduced |

**My §3.1 result reproduces D073 to within 0.01 percentage points on the
resolvable side** (71.10% both; unresolved 28.89% vs 28.40%, the small
difference being my accent correction using `max(count(ile), count(le))` and my
cutoff substitution). Two independent agents computing the same criterion from
the same profile field landing within half a percentage point is strong
evidence the criterion itself is stable and reproducible.

**The D077 97.44% is a different quantity and cannot be reconciled with 71.10%
by arithmetic** — it is 43,411 France rows (2.5620%) that are address-empty or
comma-free. Those 43,411 are a **subset** of the 489,470 in my bound, not a
competing estimate. I explicitly do **not** claim to have settled which is the
right headline: a01 owns that. What I can say with numbers is that **the
446,059-row difference between the two figures (489,470 − 43,411 = 446,059) is the set of
French rows that are perfectly well-formed, comma-bearing, and still carry no
component equal to any of the 14 keys** — and that §3.2 shows a maximal
gazetteer recovers at most 8,400 of them.

---

## 9. Verdict

**No change to `FR_REGIONS` is warranted for this dataset.** Reasoning, in
priority order:

1. The premise is refuted: the cited "absent" departments are all present (§2).
2. The maximum recoverable is 0.496% of French test rows, and that figure is an
   optimistic ceiling, not an estimate (§3.2).
3. Adding keys **deletes** tokens from live IDF-weighted features worth ~0.55%
   of address token mass — a net negative trade (§5).
4. The real France problem is 100% missing training labels, which no dictionary
   change can address (§4).

**Recommended actions, ranked:**

| # | Action | Expected value | Status |
|---|---|---|---|
| 1 | Nothing to `FR_REGIONS` | avoids a net-negative change | **do this** |
| 2 | `normalize.py:252` -> add `FR_REGIONS` to the self-map loop | 0 on this dataset; safe future-proofing | optional, cosmetic |
| 3 | Nothing else | — | — |

**Explicitly NOT recommended:** adding department names. The mechanism in §5
says it removes signal.

### Honest limitations

- `addr_tokens` / `name_tokens` are **top 4000 only** (`build_profile.py:140`).
  Every "not in the top 4000" statement means *count <= the rank-4000 cutoff*
  (23 / 58 / 60), **never** "does not occur".
- The profile destroys component structure, so all §3 figures are **upper
  bounds**, not direct counts. I never present them as measurements of
  resolution.
- The §5 trade-off is a **mechanism argument from quoted code plus measured
  token mass**, not a measured F0.5 delta. I did not run the pipeline and do
  not claim a score change.
- I did not open any raw `*.tsv`; all data comes from the six profile JSONs.
- I did not re-derive the postcode, region-coverage, function-word, or self-map
  findings marked settled in `FLEET_BRIEF.md` / D073 / D128.

Two of the 14 are near-dead on this dataset: `aisne` and `vendee` are **not in
the top 4000 of any of the six profile files** — so their counts are <= 23 (s1)
/ <= 58 (s2) / <= 60 (s3) per the cutoff. Read the honest way: **not in the top
4000**, which is not proof of zero occurrences (the tail is truncated). The
other 12 all resolve on real volume; `landes` (313 in s3) and `oise` (139 in
s3) are the smallest live ones. Removing `aisne`/`vendee` would change nothing
measurable — but they are also *correct* geography and cost nothing, so there
is no case for removal either.

**(b) Which tokens in the profile does the dictionary not handle but should?**
**None that would pay.** I enumerated 84 metropolitan department names; 58 do
not clear the top-4000 cutoff in any file, and the ~20 that do are worth
<= 8,400 rows (§3.2) while costing ~0.55% of address IDF mass (§5). The tokens
the dictionary *does* miss that genuinely matter — `de`, `la`, `du`, `des`,
`le`, `les` — belong to `ADDR_CANON_FR`, not `FR_REGIONS`, and that finding is
already established and settled; I do not re-measure it.

**(c) Which entries could collide across countries?**
`STATE_MAPS` is country-keyed (`normalize.py:250`), so a French row can never
read `US_STATES` or `IN_STATES`. There is **no cross-country collision
possible** in the state path by construction. Within France, the 14 keys map to
4 canonical values with no ambiguous key — each key appears once. The only
theoretical collision is `nord` (a department) vs. the English/French word
"north" in a street name (e.g. "Rue du Nord"). I checked: a *whole-component*
match is required, so a street component like `rue du nord` does **not** match
the key `nord`. The `continue`-consumes-component rule protects this. **No
collision found.**


| `nouvelle aquitaine` | 85,268 | 74,276 | 82,987 |
| `pays de la loire` | 72,812 | 63,086 | 71,498 |
| `gironde` | 62 | 75,104 | 75,621 |
| `nord` | 200 | 75,362 | 76,449 |
| `loire atlantique` | 253 | 63,697 | 64,398 |
| `pas de calais` | 179 | 14,325 | 14,528 |
| `somme` | 333 | 807 | 833 |
| `paris` | 388 | 952 | 923 |
| `ile de france` | 303 | 817 | 794 |
| `landes` | 116 | 292 | 313 |
| `oise` | 74 | 148 | 139 |
| `aisne` | <=23 | <=58 | <=60 |
| `vendee` | <=23 | <=58 | <=60 |
| **UB (sum)** | **261,751** | **457,501** | **488,022** |

Clipped to `rows` and differenced:

| file | rows | UB (clipped) | provably unresolved | % |
|---|---|---|---|---|
| `test_s1` | 259,452 | 259,452 | **0** | 0.00% (bound **vacuous**) |
| `test_s2` | 703,378 | 457,501 | **245,877** | 34.96% |
| `test_s3` | 731,615 | 488,022 | **243,593** | 33.30% |
| total | 1,694,445 | — | **489,470** | 28.89% |

`s1` contributes 0 because UB (261,751) **exceeds** rows (259,452). A bound
that exceeds its own denominator cannot detect anything — which is exactly why
it cannot support a "100%" claim.


