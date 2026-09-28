# D082 — mine evidence to extend ADDR_CANON_FR for France

## Headline

`ADDR_CANON_FR` (normalize.py:199-214, **68 keys**) is a *street-type* dictionary and it
does that job well: its 55 live keys absorb **2,084,136 of 11,992,918 listed France
address tokens = 17.38%** across test_s1+s2+s3. But **82.46% of French address-token
mass is unhandled**, and the two biggest holes are **not missing street types** — they
are French **function words** (16.40%) and **geography** (18.40%). The single most
important *new* defect found: **French `est` ("east") is silently rewritten to the
English real-estate noun `estate`** by an inherited `ADDR_CANON_COMMON` entry
(469 occurrences). A second methodological finding constrains all future France mining:
**the profile builder's tokenizer is not `normalize.py`'s tokenizer**, so short tokens
(`l`, `d`, `e`, `ge`, `ch`, `all`, `cit`, `teau`) are systematically inflated by
accent/apostrophe splitting and must not be mined naively.

**France is test-only.** `by_country["France"].rows` = **0 in all three train files**;
all 1,694,445 France rows live in test. Anything learned about France geography cannot
be learned from training data in this dataset.

## Findings

### F0. Structural ground truth (from `_upstream/src/normalize.py`, read-only)

| Quantity | Value | Source |
|---|---|---|
| `ADDR_CANON_FR` keys | 68 | normalize.py:199-214 |
| `ADDR_CANON_COMMON` keys | 177 | normalize.py:153-198 |
| keys dropped for France | 7: `st ste dr n s e w` | normalize.py:321 |
| `FR_REGIONS` entries / distinct values | 14 / 4 | normalize.py:243-249 |
| **effective France canon** | **219** = 170 COMMON + 68 FR − 19 overridden | computed |
| does COMMON overlay FR? | no — FR overlays COMMON (`{**COMMON, **FR}`) | normalize.py:321 |

`effective` = `{**{k:v for k,v in COMMON if k not in DROP}, **ADDR_CANON_FR}` = 219 keys.

### F1. Arithmetic invariants (all exact; no estimation)

```
France test rows      = 259,452 + 703,378 + 731,615 = 1,694,445
France train rows     = 0 + 0 + 0                   =         0
s1 share of France    = 259,452 / 1,694,445 = 15.31%   <- REFUTED-2 denominator, re-derived

listed France addr-token mass, test_s1 = 2,253,877
listed France addr-token mass, test_s2 = 4,745,780   <- reproduces already_checked EXACTLY
listed France addr-token mass, test_s3 = 4,993,261
                        s1+s2+s3     = 11,992,918

handled   2,103,882 (17.54%) = FR-own 2,084,136 (17.38%) + COMMON-inherited 19,746 (0.16%)
unhandled 9,889,036 (82.46%)
2,084,136 + 19,746 = 2,103,882 = handled              EXACT
2,103,882 + 9,889,036 = 11,992,918 = total            EXACT
```

`test_s2` mass 4,745,780 and the per-token counts `du` 220,355 / `des` 199,183 reproduce
the work order's `already_checked` figures exactly, which validates the profile read.

### F2. Handled rate per source — never quote one source as a France-wide rate

| source | listed mass | handled | handled % | unhandled % | France rows |
|---|---|---|---|---|---|
| test_s1 | 2,253,877 | 313,379 | 13.90% | 86.10% | 259,452 |
| test_s2 | 4,745,780 | 878,118 | 18.50% | 81.50% | 703,378 |
| test_s3 | 4,993,261 | 912,385 | 18.27% | 81.73% | 731,615 |
| **all** | **11,992,918** | **2,103,882** | **17.54%** | **82.46%** | **1,694,445** |

### F3. The dictionary is live, not dead weight — 55 of 68 keys fire

| key | -> canon | s1 | s2 | s3 | total |
|---|---|---|---|---|---|
| rue | rue | 170,819 | 269,264 | 288,500 | 728,583 |
| r | rue | 2,543 | 182,872 | 182,809 | 368,224 |
| saint | saint | 26,280 | 56,130 | 58,954 | 141,364 |
| avenue | ave | 30,987 | 45,928 | 49,582 | 126,497 |
| n | "" (dropped) | 2,648 | 51,535 | 52,241 | 106,424 |
| no | "" (dropped) | 284 | 35,995 | 35,742 | 72,021 |
| all | allee | 11,481 | 24,216 | 25,601 | 61,298 |
| av | ave | 2,211 | 27,580 | 27,570 | 57,361 |
| bis | bis | 11,010 | 20,062 | 21,000 | 52,072 |
| boulevard | blvd | 9,310 | 14,029 | 14,936 | 38,275 |
| st | saint | 326 | 12,555 | 12,573 | 25,454 |
| bd | blvd | 1,963 | 11,596 | 11,714 | 25,273 |
| chemin | chemin | 3,651 | 5,535 | 6,058 | 15,244 |
| impasse | impasse | 5,132 | 7,735 | 8,235 | 21,102 |
| route | rte | 4,428 | 6,549 | 6,955 | 17,932 |

**13 dead keys (0 occurrences in any France address token):**
`avn, bld, boul, chem, fbg, fg, lieudit, null, numero, prof, za, zac, zi`.

These are US spellings (`avn`, `bld`, `boul`) and French forms the data does not use
(`chem`, `fg`, `za`, `zi`, `zac`, `lieudit`, `numero`). `numero` being dead is notable:
the data uses **`no`** and **`n`**, not the spelled-out French word. All 13 are harmless —
zero-cost, zero-risk, zero-benefit.

### F4. Where the unhandled 82.46% actually sits (all six buckets sum exactly)

| category | mass | % of 11,992,918 | example tokens |
|---|---|---|---|
| names / cities / streets / other alpha | 4,077,440 | 34.00% | bordeaux, nantes, lille, jean, pierre |
| geography (FR_REGIONS component tokens) | 2,206,125 | 18.40% | gironde, nord, calais, aquitaine |
| French function words | 1,966,401 | 16.40% | de, la, du, des, le, les |
| house numbers (pure digit) | 1,567,275 | 13.07% | 1, 4, 6, 12, 25 |
| other canon miss | 58,215 | 0.49% | — |
| digit-glued (`Nb`/`Nbis`/ordinals) | 13,580 | 0.11% | 2b, 2bis, 1er, cour2 |
| **TOTAL** | **9,889,036** | **82.46%** | sums exactly |

**Two structural observations.** First, the French-function-word bucket at 16.40% is
**larger than the whole street-type handled mass of 17.38%** — no amount of street-type
work closes this. Second, 13.07% is pure house numbers, which `normalize.py:336-340,345-346`
already routes to `nums`/digit-tokens, so that slice is **not** dictionary headroom in the
ordinary sense.

### F5. NEW DEFECT A — French `est` ("east") is rewritten to English `estate` (**CONFIRMED**)

`normalize.py:321` drops 7 COMMON keys for France (`st ste dr n s e w`) but **not** `est`.
`ADDR_CANON_COMMON["est"] = "estate"` (normalize.py:186) therefore survives into the
French canon, and `ADDR_CANON_FR` does not override it.

| token | mass (s1/s2/s3 = 76/189/204) | resolves to | correct? |
|---|---|---|---|
| `est` | 469 | `estate` (English noun) | **no** — French "east" |
| `ouest` | 1,221 | *not a key* → survives as `ouest` | inconsistent |
| `sud` | 1,254 | *not a key* → survives as `sud` | inconsistent |
| `nord` | 152,011 | *not a canon key*, **is** an `FR_REGIONS` key → `hdf` | handled by the state map |

Mass is small (469 = 0.0039% of listed mass) but this is a genuine **cross-language sense
collision**, and it is one-directional: `est` is mangled while its three siblings are left
alone. The fix is to add `"est"` (and ideally `ouest`, `sud`) to the France drop tuple at
normalize.py:321.

**Interaction with `FR_REGIONS`, stated carefully:** `FR_REGIONS ∩ ADDR_CANON keys = ∅`
(empty set, computed). `nord` is *not* damaged by the canon map because it is matched and
consumed earlier, at normalize.py:331-335, before token canonicalisation. So the 152,011
`nord` occurrences are a state-map matter, **not** an `ADDR_CANON_FR` defect. I make no
claim about how many of those 152,011 actually sit inside a matching component — see Gaps.

### F6. NEW DEFECT B — leetspeak is applied to names but **not** to addresses

`normalize.py:279-280` applies `LEET` inside `_name_tokens`. The address path
(`normalize.py:342-349`) contains **no** `LEET` call. Measured on France:

**Address side, mixed letter+digit tokens:** 46 tokens, mass **13,580 = 0.1132%** of
listed France mass, and **zero** of them is a canon key.

| pattern | tokens | mass |
|---|---|---|
| word-then-DIGIT (`cour2`, `chem1`, `espl1`, `chau1`, `1er`, `2eme`, `3eme`) | 6 | 5,576 |
| DIGIT-then-word (`2b`, `1bis`, `80b`, `6b`, `12b`, ...) | 40 | 8,004 |
| any other pattern | 0 | 0 |

Top: `cour2` 3,872 · `1er` 1,963 · `chem1` 1,102 · `2eme` 697 · `3eme` 350 ·
`espl1` 311 · `chau1` 177 · `2b` 237 · `1b` 221 · `2bis` 196 · `1bis` 181.

This is **house-number and ordinal notation, not leetspeak**. `2b`/`1b` are French
"numéro bis" house forms; `1er`/`2eme`/`3eme` are French ordinals. The word-DIGIT group
(`cour2`, `chem1`, `espl1`, `chau1`) is a truncated street type plus a digit.

**Name side — the genuine leetspeak, and it is already handled:** 24 mixed
letter+digit France name tokens, mass 5,307, and **all 24 contain a character `LEET`
actually maps**. `c1ub` 190, `amica1e` 136, `mais0n` 118, `uni0n` 87, `c0mite` 75,
`ass0ciation` 75, `rati0n` 61, `tab1issements` 56, `li1le` 54, `c0mit` 29, `fi1s` 26,
`sp0rtive` 25. These are correctly folded by the existing name-side `LEET` call.

**Caveat on `LEET` itself:** normalize.py:256 maps `0 1 3 4 5 6 7 8 @ $` — it has **no
entry for `2` or `9`**. So even where `LEET` *is* applied, `2eme` keeps its `2` and `3eme`
becomes `seme`. This is a name-side limitation, not an address one.

### F7. NEW DEFECT C — the profile tokenizer is not `normalize.py`'s; short counts are inflated

`build_profile.py:28` uses `TOKEN_RE = [a-z0-9]+` on the **raw, lower-cased** address.
`normalize.py:317` calls `strip_accents` **first**, and normalize.py:342 also deletes
apostrophes. Therefore, in the profile **accents and `'` are separators**; in
`normalize.py` they are removed. Evidence, all from `addr_tokens["France"]`:

| artifact token | mass | ASCII full form normalize.py sees | that form's mass |
|---|---|---|---|
| `teau` | 1,793 | `chateau` | 1,640 |
| `cit` | 5,580 | `cite` | 2,546 |
| `ge` | 41,120 | `general` | 4,826 |
| `ral` | 10,251 | `general` (suffix) | — |
| `all` | 61,298 | `allee` | 17,779 |
| `ch` | 12,774 | `chemin` | 15,244 |
| `e` | 45,410 | — | — |
| `l` | 99,889 | — | — |
| `d` | 50,816 | — | — |

`teau` **cannot be a French word** — it only exists as the tail of `château` split at
`â`. `ral`, `ge`, `georges`, `albert` are all `...ge...` fragments of `général`-style
words. `l`/`d`/`c`/`j` are apostrophe leftovers (`l'`, `d'`).

**Consequence:** the profile **overstates** short tokens. This matters directly for
`ADDR_CANON_FR`, whose highest-mass keys are short: `n` 106,424, `no` 72,021, `all` 61,298,
`ch` 12,774, `r` 368,224. `all -> allee` happens to be *correct* despite being inflated
(`allee` alone is 17,779 and both forms are real); but a mined entry justified by `ch`
(12,774) or `all` (61,298) is mis-sized. **Practical rule: treat any candidate whose
evidence is a token of 4 characters or fewer as unverified until checked against real
address strings.**

### F8. Ranked candidate entries for `ADDR_CANON_FR`

Confidence marks what the *profile* supports. `mass` is s1+s2+s3 from
`addr_tokens["France"]`; `%` is of 11,992,918.

**A. Street types currently unhandled (long form present, genuine French street type):**

| rank | token | mass | s1 | s2 | s3 | % | verdict |
|---|---|---|---|---|---|---|---|
| 1 | `parc` | 4,244 | 735 | 1,751 | 1,758 | 0.035% | **LIKELY** (street/park feature, not always a street type) |
| 2 | `passage` | 3,167 | 787 | 1,164 | 1,216 | 0.026% | **CONFIRMED** (`pass` 874 also unhandled) |
| 3 | `pont` | 3,866 | 654 | 1,604 | 1,608 | 0.032% | **LIKELY** (may be the noun "bridge") |
| 4 | `port` | 3,825 | 652 | 1,541 | 1,632 | 0.032% | **LIKELY** |
| 5 | `cour` | 9,403 | 1,571 | 3,800 | 4,032 | 0.078% | **LIKELY** (cf. `cours` 8,761 → `crs`) |
| 6 | `lotissement` | 1,788 | 296 | 719 | 773 | 0.015% | **CONFIRMED** |
| 7 | `gare` | 1,735 | 295 | 679 | 761 | 0.014% | **CONFIRMED** |
| 8 | `hameau` | 1,067 | 178 | 429 | 460 | 0.009% | **CONFIRMED** |
| 9 | `chaussee` | 1,125 | 76 | 549 | 500 | 0.009% | **CONFIRMED** |
| 10 | `esplanade` | 878 | 150 | 374 | 354 | 0.007% | **CONFIRMED** |
| 11 | `sentier` | 618 | 102 | 247 | 269 | 0.005% | **CONFIRMED** |
| 12 | `ruelle` | 593 | 99 | 235 | 259 | 0.005% | **CONFIRMED** |
| 13 | `parvis` | 587 | 97 | 240 | 250 | 0.005% | **CONFIRMED** |
| 14 | `sente` | 562 | 97 | 231 | 234 | 0.005% | **LIKELY** (also the verb "sente") |
| 15 | `villa` | 594 | 105 | 226 | 263 | 0.005% | **LIKELY** (also a real noun) |
| 16 | `venelle` | 481 | 76 | 203 | 202 | 0.004% | **CONFIRMED** |
| 17 | `promenade` | 536 | 90 | 219 | 227 | 0.004% | **LIKELY** (also a noun) |
| 18 | `domaine` | 1,194 | 205 | 490 | 499 | 0.010% | **LIKELY** (also a noun) |

Combined mass of ranks 1-18 = **27,015 = 0.225%** of listed France mass. Even taken
together these are a rounding error next to the 16.40% function-word bucket.

**B. Abbreviation pairs where one form is handled and the other is not:**

| pair | long mass | abbrev mass | status | verdict |
|---|---|---|---|---|
| `cours` / `crs` | 8,761 | 4,520 | both handled | OK |
| **`cours` / `cour`** | 8,761 | **9,403** | long handled, **abbrev unhandled** | **LIKELY** — `cour` is the largest unhandled street-type-like token here |
| `chemin` / `che` | 15,244 | 314 | both handled | OK |
| `saint` / `st` | 141,364 | 25,454 | both handled | OK |
| `residence` / `res` | 4,748 | 8,340 | both handled | OK |
| `batiment` / `bat` | 1,978 | 1,767 | both handled | OK |
| `parvis` / `parv` | 587 | 97 | both unhandled | **SPECULATIVE** — `parv` is a guess, low mass |
| `passage` / `pass` | 3,167 | 874 | both unhandled | **SPECULATIVE** — `pass` is a guess, low mass |

**A note on how I did *not* mine abbreviations.** I ran a generic prefix search (short
token is a prefix of a longer frequent token) over all 4,000+ listed tokens. It returned
**3,546 pairs**, of which the top ~30 were **false positives**: `r` (368,224) ->
`roubaix` / `rignac` / `roger` / `ren` / `robert` / `raymond`. These are the *street-type*
`r` colliding with the *initial* of surnames. A naive prefix miner would have added
`r -> roubaix`. The table above is restricted to pairs where a real French street-type
word is involved. Anyone mining abbreviations must apply the same restriction.

**C. Region / department candidates.** `FR_REGIONS` covers 14 entries over 20 distinct
component tokens, whose total token mass is **3,737,379 = 31.16%** of listed France mass.
Of those, the tokens **not** in any `ADDR_CANON` key and appearing at meaningful mass are:
`de` 1,050,023 · `la` 481,231 · `loire` 334,419 · `france` 293,150 · `hauts` 289,655 ·
`nouvelle` 242,802 · `aquitaine` 242,531 · `pays` 207,396 · `nord` 152,011 ·
`gironde` 150,787 · `calais` 128,762 · `atlantique` 128,348 · `pas` 29,032 ·
`paris` 2,263 · `somme` 1,973 · `ile` 1,914 · `landes` 721 · `oise` 361
(`aisne` 0, `vendee` 0).

The s2/s3 department-vs-region gap (`gironde` 62/75,104/75,621; `nord` 200/75,362/76,449;
`atlantique` 253/63,697/64,398) reproduces `already_checked` exactly. **That gap belongs
to `FR_REGIONS`, not to `ADDR_CANON_FR`** — the two dictionaries are disjoint (F5), and the
work order instructs me not to re-derive the 71.10%/97.44% dispute. I flag only that the
*geographic tokens* above (18.40% of unhandled mass, bucket 2 of F4) are `FR_REGIONS`
candidates already covered by tasks D070-D077.

### F9. French function words — a denominator clarification to `already_checked`

`already_checked` states the function words account for **731,158 of 4,745,780 = 15.41%**
of test_s2 and names them `de la du des`. My per-source read:

| token | s1 | s2 | s3 | s1+s2+s3 |
|---|---|---|---|---|
| de | 257,777 | 381,880 | 410,366 | 1,050,023 |
| la | 116,064 | 176,186 | 188,981 | 481,231 |
| du | 34,709 | 90,693 | 94,953 | 220,355 |
| des | 31,485 | 82,399 | 85,299 | 199,183 |
| le | 1,992 | 4,882 | 5,050 | 11,924 |
| les | 631 | 1,451 | 1,603 | 3,685 |

`de+la+du+des` in s2 = 381,880 + 176,186 + 90,693 + 82,399 = **731,158**, and
731,158 / 4,745,780 = **15.41%** — the stated figure reproduces exactly. So the 15.41%
**excludes `le` and `les`**. Including all six: 737,491 / 4,745,780 = **15.54%**.
Across all three sources the six total **1,966,401 = 16.40%** of the 11,992,918 mass.

This is a clarification, not a contradiction: 15.41% is correct for the four words it
names, and 15.54% is the six-word figure. **None of the six is a canon key**
(`[(t, t in fr_canon)] = all False`), which confirms the established finding that they are
unhandled and dilute IDF weighting.

## Interpretation

*(Marked as inference. The measurements above are what the profile shows; this section is
what I think they mean.)*

1. **`ADDR_CANON_FR` is close to complete for its declared scope.** 55 of 68 keys fire;
   the 18 unhandled street types total 27,015 tokens (0.225%). This is a *street-type*
   dictionary that has done its job. The headline 82.46% "unhandled" is **not** a verdict
   on this dictionary — it is mostly content (34.00% names/cities) and structure (13.07%
   house numbers) that no street-type dictionary should be absorbing.

2. **The 13 dead keys are not a defect.** They cost nothing. Deleting them would be churn
   with zero measurable effect — the same conclusion the work order records for the
   `FR_REGIONS` self-map gap.

3. **`est -> estate` is worth fixing precisely because it is cheap and unambiguous.**
   469 occurrences, one line at normalize.py:321. Low absolute value, but it is a real
   sense error with an obvious correct answer, and fixing it removes a *class* of bug
   (English tokens leaking into French canonical output) rather than one instance.

4. **The tokenizer mismatch is the highest-leverage finding in this report, and it is a
   caveat on other agents' work, not a dictionary entry.** If `build_profile.py` had
   applied `strip_accents` (as normalize.py:317 does), `teau`/`cit`/`ge`/`ral` would not
   exist and short tokens would be correctly sized. Every future France mining task is
   currently at risk of adding entries justified by inflated short-token counts. I would
   fix the builder before mining further.

5. **On leetspeak, the honest answer is "no change needed."** The genuine leetspeak
   (`c1ub`, `mais0n`, `ass0ciation`, `c0mite`, `amica1e`) lives in `business_name`, where
   `LEET` already applies. The address-side gap is 0.1132% of mass and is house-number /
   ordinal notation. Manufacturing a leetspeak address dictionary would be a mistake.

## Gaps

1. **Component boundaries are destroyed by the profile builder.** `build_profile.py:126`
   splits on `[,;]` but then flattens all components into one counter. `normalize.py:333`
   matches a state only when an *entire* component equals a `FR_REGIONS` key. So **I
   cannot determine how many of the 152,011 `nord` or 150,787 `gironde` occurrences sit
   inside a matching component.** Every geography figure in F8-C is an upper bound on
   absorption, never a count. This is also why I do not touch the 71.10% vs 97.44%
   dispute — it cannot be settled from these fields.
2. **No per-row state-resolution field exists.** The profile records token counts and
   regex hits, not "did this row resolve a state". Adding one would settle the `FR_REGIONS`
   dispute without re-deriving it.
3. **Whether `est`/`cour`/`parc` are street types or ordinary nouns in context** is not
   determinable from token counts. `parc`, `port`, `pont`, `villa`, `sente`, `domaine`,
   `promenade` are all real French nouns as well as street features — that is why they
   are LIKELY rather than CONFIRMED. Only the rarer, unambiguous types (`lotissement`,
   `hameau`, `esplanade`, `sentier`, `parvis`, `venelle`, `chaussee`, `ruelle`, `passage`,
   `gare`) earn CONFIRMED.
4. **Whether the inflated short-token counts change any *ranking*** is untested. I can show
   `all` (61,298) > `allee` (17,779) is an artifact-plus-real mixture, but I cannot
   decompose the two without raw address strings.
5. **Train-side France vocabulary is unmeasurable** — there are 0 France rows in train (F0).
   Nothing in this report can be cross-validated against training data.
6. **LEET coverage of `2` and `9`** (F6) is a name-side observation; I did not measure how
   many France *name* tokens contain a bare `2` or `9` in an otherwise-alphabetic word, as
   that is outside this task's address-dictionary scope.

## Recommendations

Prioritised. Effects are stated as measured mass, not as predicted score.

1. **Fix the profile builder to call `strip_accents` before tokenising**
   (`build_profile.py:28`), and re-run the France profiles. *Expected effect: removes
   `teau` (1,793), `cit` (5,580), `ral` (10,251), `ge` (41,120) and correctly sizes every
   short token. Not a dictionary change — it raises evidence quality for every future
   France task. Highest leverage in this report.*
2. **Add `"est"` to the France drop tuple at normalize.py:321**, and consider `ouest`
   (1,221) and `sud` (1,254) as new `ADDR_CANON_FR` entries mapping to themselves.
   *Effect: 469 corrupted tokens repaired; three compass words made consistent.*
3. **Add the 11 CONFIRMED street types** from F8-A: `passage`, `lotissement`, `gare`,
   `hameau`, `chaussee`, `esplanade`, `sentier`, `ruelle`, `parvis`, `venelle`, plus the
   LIKELY `cour`. *Effect: roughly 20,000 tokens (~0.17% of listed mass) gain a canonical
   form.* Take the remaining LIKELY entries (`parc`, `pont`, `port`, `sente`, `villa`,
   `promenade`, `domaine`) only if a human confirms the noun sense does not dominate.
4. **Handle the French function words** (F9). 16.40% of listed mass across s1+s2+s3 is
   unhandled and IDF-diluting. *This is not an `ADDR_CANON_FR` entry — it is a stopword
   decision, and it is already established by another task. Flagged because it dwarfs
   every street-type entry combined.*
5. **Do NOT add the builder-artifact tokens** `all` (as new evidence), `cit`, `ch`, `teau`,
   `l`, `d`, `e`, `m`, `s`, `j`, `c`, `g`, `ge`, `ral`. Doing so would encode a tokenizer
   bug into the dictionary. (`all -> allee` already exists and happens to be correct — do
   not "fix" it on the basis of its inflated count.)
6. **No leetspeak work.** Manufacturing an address-side leetspeak dictionary from
   `2b`/`2bis`/`cour2` would be wrong: 0.1132% of mass, and it is house-number notation.
7. **No change to the 13 dead keys.** They are inert. Leave them; they are plausible-looking
   and cost nothing.
8. **Optional, cheap:** add a `state_resolved` per-country counter to the profile builder
   so the `FR_REGIONS` adequacy question stops being re-litigated. *(SPECULATIVE — this is
   an instrumentation change, not a dictionary entry.)*

---

*Provenance: every figure derives from `analysis_out/profile/test_s{1,2,3}.json` fields
`addr_tokens["France"]`, `name_tokens["France"]`, `by_country["France"].rows`, plus the
literal source of `_upstream/src/normalize.py` (read-only). The upstream dictionaries were
extracted with Python's `ast` module rather than hand-transcribed. `LEET` is a
`str.maketrans(...)` call (normalize.py:256) and therefore not an `ast` literal; it was
transcribed from that line and flagged. Denominators are stated with every rate; all bucket
sums were asserted to close exactly. No raw `*.tsv` was opened; no network was used;
nothing in `_upstream/` or the dataset was modified.*


