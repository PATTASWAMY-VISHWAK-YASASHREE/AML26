# D094 - mine evidence to extend ADDR_GENERIC for France

## Headline

`ADDR_CANON_FR` (`normalize.py:199-214`) is **already comprehensive for the street-type
vocabulary that actually dominates this dataset** - 13 of the highest-volume French
street words (`rue`, `avenue`, `boulevard`, `impasse`, `allee`, `chemin`, `place`,
`route`, `cours`, `quai`, `square`, `faubourg`, `residence`) are already mapped to a
canonical form. The genuinely unhandled mass is **45,443 token occurrences across all
1,694,445 France test rows = 0.0268 occurrences per row**, and no single candidate
exceeds 5,580. **A clean "no meaningful change needed" for the region table, and only a
minor, low-value extension for the street-type and abbreviation tables.**

The one **new** defect I did find is not a missing dictionary entry at all: it is a
**leetspeak false positive that actively destroys valid French data**. `LEET`
(`normalize.py:256`) is applied unconditionally to any name token containing both a
letter and a digit (`normalize.py:279-280`), and its digit-to-letter map is
`0-o 1-l 3-e 4-a 5-s 6-g 7-t 8-b`. That map **mangles French ordinal suffixes**,
turning `1er`->`ler`, `3eme`->`eeme`, `3e`->`ee`, `1ere`->`lere`, `7eme`->`teme`.
**1,111 confirmed occurrences (20.9% of the 5,307 France name tokens containing a
digit)** are corrupted this way; a further 1,943 occurrences of the ambiguous token
`4l` are also corrupted but I cannot determine their intent from the profile (see F4c).
This is the mirror image of the known defect list and is worth more than every
dictionary addition combined.

---

## Findings

### F0. Denominators and scope (from `country_rows` / `by_country`)

| split | `rows` (file) | France `rows` | share of split |
|---|---|---|---|
| test_s1 | 1,732,544 | 259,452 | 14.98% |
| test_s2 | 4,887,273 | 703,378 | 14.39% |
| test_s3 | 5,082,316 | 731,615 | 14.39% |
| **test total** | 11,702,133 | **1,694,445** | 14.48% |

France test rows = 259,452 + 703,378 + 731,615 = **1,694,445**, arithmetic shown because
the whole deliverable is denominated on it. `train_s1.json` has **no `France` key** in
`by_country` / `addr_tokens` (countries present: `US,India`), consistent with the

### F1. ADDR_CANON_FR coverage is already high where it matters

`ADDR_CANON_FR` has **68 entries**; merged with `ADDR_CANON_COMMON` (177 entries) minus
the 7 France-excluded keys at `normalize.py:321` (`st, ste, dr, n, s, e, w`), the
effective France address canon has **222 keys**. I built this set by parsing
`normalize.py:153-214` directly, so the key list is exact, not transcribed.

Top France address tokens by volume, with the canon value each currently receives
(field: `addr_tokens.France`, summed over test_s1+s2+s3):

| token | occurrences | current canon value | status |
|---|---|---|---|
| rue | 728,583 | `rue` | already mapped |
| avenue | 126,497 | `ave` | already mapped |
| boulevard | 38,275 | `blvd` | already mapped |
| impasse | 21,102 | `impasse` | already mapped |
| allee | 17,779 | `allee` | already mapped |
| chemin | 15,244 | `chemin` | already mapped |
| place | 13,363 | `pl` | already mapped |
| route | 17,932 | `rte` | already mapped |
| cours | 8,761 | `crs` | already mapped |
| quai | 8,089 | `quai` | already mapped |
| square | 4,933 | `sq` | already mapped |
| faubourg | 3,046 | `fbg` | already mapped |
| residence | 4,748 | `res` | already mapped |

Every French street-type word above rank 3,000 in the data is already in the table. This
is a **negative result and I am reporting it as such.**

### F2. Ranked candidate table - street types missing from ADDR_CANON_FR

Only **accent-free** words are quoted, because of the tokeniser defect in G1 (accented
words are split by the profiler and their fragments are not pipeline-representative).
All counts are `addr_tokens.France` occurrences summed over the three test files.

| candidate | occurrences | proposed canonical | confidence |
|---|---|---|---|
| cit / cite | 5,580 / 2,546 | `cite` | **CONFIRMED** (see G1 caveat) |
| appt / appart | 5,113 / 88 | `apt` | **CONFIRMED** |
| parc | 4,244 | `parc` | **CONFIRMED** |
| clos | 3,588 | `clos` | **LIKELY** |
| passage / pass | 3,167 / 874 | `passage` | **CONFIRMED** |
| plage | 2,054 | `plage` | **CONFIRMED** |
| jardin | 1,644 | `jardin` | **CONFIRMED** |
| mail | 1,731 | `mail` | **LIKELY** (collides with English "mail") |
| domaine | 1,194 | `domaine` | **CONFIRMED** |
| chaussee | 1,125 | `chaussee` | **CONFIRMED** |
| hameau | 1,067 | `hameau` | **CONFIRMED** |
| esplanade | 878 | `esplanade` | **CONFIRMED** |
| sentier | 618 | `sentier` | **CONFIRMED** |
| parvis | 587 | `parvis` | **CONFIRMED** |
| villa | 594 | `villa` | **LIKELY** (proper-noun risk) |
| sente | 562 | `sente` | **SPECULATIVE** |
| promenade | 536 | `promenade` | **CONFIRMED** |
| venelle | 481 | `venelle` | **CONFIRMED** |
| immeuble | 434 | `immeuble` | **CONFIRMED** |
| rond | 411 | `rond` | **SPECULATIVE** (`rond` alone is a fragment risk) |
| marche | 370 | `marche` | **LIKELY** |
| halle | 291 | `halle` | **CONFIRMED** |
| allees | 187 | `allee` | **CONFIRMED** |
| portail | 150 | `portail` | **CONFIRMED** |
| galerie | 144 | `galerie` | **LIKELY** |

**Aggregate impact:** the CONFIRMED/LIKELY accent-free candidates above total
**45,443 occurrences over 1,694,445 France test rows = 0.0268 occurrences per row**.
Even if every one is added and every one is a true improvement, the ceiling on the
effect is ~2.7% of one token per row. `appt` (5,113) and `cit` (5,580) dominate this set
and both are already only marginally outside the existing table.

**`fbg` is not a gap:** `faubourg` occurs 3,046 times and `ADDR_CANON_FR:205` maps both
`fbg` and `fg` to `fbg`, but the token `fbg` itself is **absent from the top-4000**
profile for France, i.e. the data spells the word out. The abbreviation is defined and

### F3. Abbreviation-table evidence (token pairs)

I searched for pairs where one form plausibly abbreviates the other and both occur often.
**Every high-frequency pair is already handled** - measured, with the short form's current
canon value:

| long form | count | short form | count | short form maps to |
|---|---|---|---|---|
| avenue | 126,497 | av | 57,361 | `ave` OK |
| boulevard | 38,275 | bd | 25,273 | `blvd` OK |
| allee | 17,779 | all | 61,298 | `allee` OK |
| place | 13,363 | pl | 12,989 | `pl` OK |
| chemin | 15,244 | ch | 12,774 | `chemin` OK |
| saint | 141,364 | st | 25,454 | `saint` OK |
| impasse | 21,102 | imp | 12,228 | `impasse` OK |
| route | 17,932 | rte | 11,995 | `rte` OK |
| cours | 8,761 | crs | 4,520 | `crs` OK |
| residence | 4,748 | res | 8,340 | `res` OK |
| square | 4,933 | sq | 458 | `sq` OK |
| quai | 8,089 | q | 4,283 | `quai` OK |
| docteur | 10,362 | dr | 256 | `dr` OK |
| sainte | 7,486 | ste | 591 | `sainte` OK |

The **only** unhandled abbreviation pairs of any volume are `appartement`/`appt`,
`cite`/`cit` and `passage`/`pass` - all three already in F2 and all small. **The
abbreviation table needs no material extension.**

### F4. Leetspeak - a NEW DEFECT, and it runs backwards

The work order asked for "digits or symbols inside otherwise-alphabetic words". In France
**address** tokens that pattern is almost entirely *not* leetspeak but French
addressing grammar (see F5). In France **name** tokens the pattern is genuinely leetspeak
- and `LEET` is what breaks it.

I simulated `normalize.py:256` exactly over all 24 France name tokens containing both a
letter and a digit (5,307 occurrences total, `name_tokens.France`):

**(a) LEET correctly repairs 18 tokens (2,253 occurrences, 42.5%)** - genuine leetspeak,
already handled: `mais0n`->`maison` (118), `uni0n`->`union` (87), `c0mite`->`comite` (75),
`ass0ciation`->`association` (75), `rati0n`->`ration` (61), `tab1issements`->`tablissements`
(56), `li1le`->`lille` (54), `c1ub`->`club` (190), `c0mit`->`comit` (29), `fi1s`->`fils` (26),
`sp0rtive`->`sportive` (25), plus the `5`-for-`S` legal-form family `5arl`->`sarl` (637),
`5as`->`sas` (417), `5asu`->`sasu` (85), `5a`->`sa` (129), `5ci`->`sci` (27),
`5portive`->`sportive` (26), `amica1e`->`amicale` (136).

**(b) LEET DESTROYS 5 confirmed French ordinal tokens (1,111 occurrences, 20.9%).**
These are ordinals, not leetspeak:

| token | occurrences | LEET output | damage |
|---|---|---|---|
| 3eme | 748 | `eeme` | corrupt |
| 1er | 131 | `ler` | corrupt |
| 3e | 121 | `ee` | corrupt |
| 1ere | 102 | `lere` | corrupt |
| 7eme | 9 | `teme` | corrupt |
| **subtotal** | **1,111** | | **20.9% of 5,307** |

**(c) `4l` (1,943 occurrences, 36.6%) is corrupted but AMBIGUOUS - I will not claim it.**
`4l` -> `al` via `LEET`. This is the single largest digit-bearing France name token, but
`4l` is **not** a standard French ordinal suffix, and I cannot determine from the profile
what it represents. It could be a truncated unit/level designator, a mis-parse of `4L`, or
a leetspeak `al`. **I am marking it SPECULATIVE and excluding it from the confirmed
subtotal.** If it is ordinal-like, the true corruption figure is 1,111 + 1,943 =
**3,054 = 57.5%**; if it is genuine leetspeak that *should* become `al`, the figure is
1,111 = 20.9%. **Both numbers are shown; the honest confirmed figure is 1,111.**
Resolving this requires the raw `business_name` values, which I did not read.

Full partition of the 5,307 France name-token occurrences containing a digit:

| category | occurrences | share |
|---|---|---|
| LEET correctly repairs (genuine leetspeak) | 2,253 | 42.5% |
| LEET destroys (confirmed ordinals) | 1,111 | 20.9% |
| LEET corrupts, intent ambiguous (`4l`) | 1,943 | 36.6% |
| total | 5,307 | 100% |


### F5. Address-side digit tokens are French grammar, NOT leetspeak

This is the trap the work order walks into, and I am flagging it so nobody "fixes" it.
`normalize_address` (`normalize.py:314-353`) **never calls `LEET`** - only
`_name_tokens` does (`normalize.py:279-280`). So the France address digit-tokens are
untouched by design. They are legitimate French forms:

| token | occurrences | reading |
|---|---|---|
| cour2 | 3,872 | "cour 2" (courtyard no. 2) |
| 1er | 1,963 | "1er" = premier, ordinal |
| chem1 | 1,102 | "chemin 1" |
| 2eme / 3eme | 697 / 350 | ordinals |
| 2b, 1b, 80b, 5b... | 237, 221, 179... | "batiment B" |
| 2bis, 1bis | 196, 181 | "bis" = secondary entrance |
| espl1, chau1, cite1 | 311, 177, 89 | truncated street-type words |

**Recommendation: do not add a leet pass to `normalize_address`.** Doing so would
corrupt 3,872 `cour2` and 1,102 `chem1` tokens. This is a CONFIRMED *no-change* finding.

### F6. Region / department table - a clean negative result

`FR_REGIONS` (`normalize.py:243-249`) has **14 keys and 4 canonical values**
(`hdf, naq, pdl, idf`). I enumerated the departments and regions that appear as France
address tokens and checked each against `FR_REGIONS`. Using the **minimum** of the
component word counts as an upper bound on the number of address components that could
match (a department only resolves if *all* its words co-occur, so `min` is the correct
upper bound and `sum` would be wrong):

| department/region | min-bound | in `FR_REGIONS`? |
|---|---|---|
| hauts de france | 289,655 | yes, hdf |
| nouvelle aquitaine | 242,531 | yes, naq |
| pays de la loire | 207,396 | yes, pdl |
| nord | 152,011 | yes, hdf |
| gironde | 150,787 | yes, naq |
| loire atlantique | 128,348 | yes, pdl |
| pas de calais | 29,032 | yes, hdf |
| paris | 2,263 | yes, idf |
| somme | 1,973 | yes, hdf |
| ile de france | 1,914 | yes, idf |
| landes | 721 | yes, naq |
| oise | 361 | yes, hdf |
| **maine et loire** | 645 | **MISSING** |
| **marne** | 2,478 | **MISSING** |
| **val de marne** | 1,124 | **MISSING** |
| **haute garonne** | 257 | **MISSING** |
| **bas rhin / haut rhin** | 244 / 244 | **MISSING** |
| **val d oise** | 361 | **MISSING** |
| **moselle** | 222 | **MISSING** |
| **orne** | 113 | **MISSING** |

`aisne`, `vendee`, `sarthe`, `mayenne`, `charente`, `dordogne`, `calvados`, `finistere`
and `seine maritime` have at least one component word **absent from the top-4000**, so I
cannot bound them - **gap, see G3.**

**Sum of min-bounds for departments ALREADY in `FR_REGIONS` = 1,206,992.**
**Sum of min-bounds for departments MISSING from `FR_REGIONS` = 5,688.**
5,688 / 1,694,445 = **0.336%** of France test rows.

So even a perfect, complete French department table would touch at most **~0.34%** of
France rows by this measure. The 14-entry `FR_REGIONS` is not the bottleneck. This is
consistent with the re-scoped REFUTED-2 conclusion that France region handling is
adequate, arrived at independently and by a different method (token min-bounds rather
than component matching).

**Note on the s1/s2/s3 split (a real structural difference, not a region defect).** The
region *vocabulary* differs sharply by source, from `addr_tokens.France`:

| token | test_s1 | test_s2 | test_s3 |
|---|---|---|---|
| hauts | 101,717 | 88,519 | 99,419 |
| france | 102,319 | 89,929 | 100,902 |
| nouvelle | 85,311 | 74,392 | 83,099 |
| pays | 72,812 | 63,086 | 71,498 |
| nord | 200 | 75,362 | 76,449 |
| gironde | 62 | 75,104 | 75,621 |
| calais | 15,967 | 55,273 | 57,522 |
| atlantique | 253 | 63,697 | 64,398 |

---

## Interpretation

*Inference, clearly marked as such.*

1. **The address dictionaries for France are in good shape.** The high-frequency French
   street vocabulary is already canonicalised, and the abbreviation pairs are already
   collapsed to a single canonical token. Whoever built `ADDR_CANON_FR` did it against
   real data. My expectation was that this table would be full of obvious holes; it is not.

2. **The real France risk is on the name side, not the address side.** The `LEET`
   ordinal corruption (F4) is a *loss* mechanism: it takes valid, well-formed French
   tokens and turns them into non-words, which lowers the chance that two spellings of
   the same business name match. A dictionary addition can only add signal; this
   actively destroys it. It is also cheap to fix and testable offline.

3. **The 0.34% department bound is an upper bound, not an estimate.** Because I used
   `min` over component words, the true number of France rows whose state fails to
   resolve *because of a missing department* is at most 0.34%. Most France rows that lack a
   state presumably lack any region-like component at all - that is a data property,
   not a dictionary gap, and no dictionary change can fix it. **I am explicitly not
   claiming a France-wide state-resolution rate**; the profile cannot support one (G2).

4. **The `2`/`9` omission in `LEET` is a latent inconsistency.** It means `2eme` and
   `2bis` are currently safe by accident while `1er` and `3eme` are not. If anyone
   "fixes" `LEET` by adding `2` and `9` (for leetspeak reasons) without adding the
   ordinal guard, they will *newly* break the 697 `2eme` and 196 `2bis` address tokens.
   The guard must land together with, or before, any `LEET` change.

---

## Gaps

1. **G1 - The profile tokeniser is not the pipeline tokeniser, and it distorts France
   more than any other country.** `build_profile.py:28` uses
   `TOKEN_RE = re.compile(r"[a-z0-9]+")` and applies it to `ba.lower()` at line 113
   **without** accent stripping. `normalize.py:317` calls `strip_accents(s).lower()` and
   splits with `_non_alnum` at line 342. Consequence: an accented French word is emitted
   by the profiler as **fragments**. Measured:
   * `allee` 17,779 vs fragment `all` **61,298**
   * `cite` 2,546 vs `cit` **5,580**
   * `chaussee` 1,125 vs `chauss` **2,372**
   * `residence` 4,748 vs `sidence` **1,467** (independently noted by D081)
   * `general` 4,826 vs `n` 106,424; `ecole` 1,560 vs `cole` 505; `chateau` 1,640 vs `te` 857

   This is a **systematic over-count of every accented French street word and a
   fragmentation of short tokens**. I have handled it by quoting **only accent-free**
   candidates in F2/F3, and by refusing to treat `all`, `cit`, `sidence`, `chauss` as
   independent vocabulary. **The 5,580 figure for `cit` is therefore an UPPER BOUND** that
   mixes genuine `Cit.` abbreviations with fragments of `Cite`; the true abbreviation
   count is lower and I cannot separate the two from the profile.
   *This is the same class of defect D081 reported from the other direction, and it is
   large enough that any other agent quoting France token counts should re-check against
   it.*

2. **G2 - The profile cannot measure state-resolution rate at any denominator.**
   `build_profile.py` counts tokens but records **no component or row-level
   co-occurrence**; it splits on `ADDR_SPLIT` at line 126 and discards the grouping. So I
   cannot count "France rows with no resolvable state". The re-scoped REFUTED-2 gives a
   71.10% ceiling across all three test sources; I have **not** reproduced, extended or
   contested that figure, and I make no France-wide rate claim. My 0.336% is a
   *dictionary-gap* bound (rows recoverable by adding departments), which is a strictly
   different and much weaker quantity.

3. **G3 - Departments whose component words fall outside the top-4000 are unbounded.**
   `build_profile.py:27` sets `TOPN = 4000`, and `prune()` (line 45) also drops hapax
   tokens every 8 chunks. `aisne`, `vendee`, `sarthe`, `mayenne`, `charente`, `dordogne`,
   `calvados`, `finistere`, `seine maritime` cannot be bounded. Their true France
   frequency may be non-zero. **I am not estimating them.**


---

## Recommendations

**Priority 1 - Guard `LEET` against French ordinals. (NEW defect, CONFIRMED)**
In `_name_tokens` (`normalize.py:279-280`), skip the `t.translate(LEET)` call when the
token matches `^\d+(er|ere|eme|e)$`.
Expected effect: restores **1,111 confirmed France name-token occurrences (20.9% of the
France digit-token mass)** that are currently corrupted, plus up to 1,943 more if `4l`
proves to be ordinal-like (G5). It is France-specific in effect because ordinal suffixes
are a French address/naming convention, but the guard is safe globally since `1er`/`3eme`
are not English tokens.
**Do this before, or together with, any change to the `LEET` digit map** - see
Interpretation point 4.

**Priority 2 - Add the clearly-safe street types. (CONFIRMED)**
`appt` and `appart` to `apt`, `parc`, `passage`/`pass`, `domaine`, `chaussee`, `sentier`,
`venelle`, `esplanade`, `parvis`, `hameau`, `portail`, `halle`, `plage`, `jardin`,
`immeuble`, `allees` to `allee`.
Expected effect: ~30,000 token occurrences, about 0.018 per France row. **Be honest about
the ceiling: this is a marginal gain, not a fix.** It is cheap and low-risk, which is the
only argument for doing it.

**Priority 3 - Add `cit` to `cite`, but treat the count as unreliable.**
Both forms are frequent (5,580 / 2,546) and clearly a pair, but per G1 the `cit` figure
is contaminated by `Cite` fragments. Confirm against the raw data before quoting a
benefit. Marked **LIKELY** for that reason.

**Priority 4 - Add the 9 missing departments to `FR_REGIONS`. (LIKELY, low value)**
`maine et loire` to `pdl`, `val de marne` to `idf`, `val d oise` to `idf`, `marne` to
`idf`, `haute garonne` to `naq`, plus `haut rhin`, `bas rhin`, `moselle`, `orne`.
Upper bound on impact: **0.336% of France rows**. Do it for completeness, not for score.
The last four would introduce **new canonical values** for regions this dataset barely
uses - that is a schema change and should be reviewed separately rather than slipped
into a dictionary edit.

**Explicitly NOT recommended:**
* **Do not add a leet pass to `normalize_address`.** It would corrupt 3,872 `cour2` and
  1,102 `chem1` tokens (F5). CONFIRMED no-change.
* **Do not expand the abbreviation tables further.** All 14 high-frequency pairs are
  already collapsed (F3). No evidence of a gap.
* **Do not mine the 1-2 char profile token tail for dictionary entries** - 35.6% of
  retained occurrences are apostrophe/accent fragments (G1, G4).
* **Do not treat the s1 region-token counts as France-wide.** See F0 and G2.

**Suggested tooling follow-up (outside my two-file write budget):** re-run
`build_profile.py` with `strip_accents` applied before `TOKEN_RE`, and preserve
component grouping. That single change would remove G1 and G4 and make every future
France token count directly pipeline-representative. It is the highest-value change to
the *analysis* tooling, and I estimate it matters more to this project's conclusions than
any dictionary edit in this report.

---

## Provenance

All figures derive from `analysis_out/profile/{test_s1,test_s2,test_s3}.json` fields
`rows`, `country_rows`, `by_country[France].*`, `addr_tokens.France` and
`name_tokens.France`, plus `_upstream/src/normalize.py:109-256` read directly.
No raw `*.tsv` was opened. No network access. Read-only respected on the dataset and
`_upstream/`. Exactly two files written: this deliverable and the JSON sidecar
`analysis_out/findings/D094_mine_ADDR_GENERIC_France.json`.

4. **G4 - Apostrophe/elision handling is unmeasured.** `normalize.py:342` does
   `c.replace("'", "")` *before* splitting, so `l'herblain` becomes the single token
   `lherblain` in the pipeline. The profiler splits on the apostrophe, emitting `l`
   (99,889) and `herblain` (44,846) separately - I confirmed `lherblain` is **absent**
   from the top-4000. So every apostrophe elision in the profile is split. This does not
   affect my accent-free candidates but it means the profile's short-token tail
   (4,264,808 occurrences in 1-2 char tokens, 35.6% of all retained occurrences) is
   **largely artifact** and must not be mined for dictionary entries.

5. **G5 - `4l` cannot be classified from the profile.** See F4c. The 1,943 occurrences
   are corrupted by `LEET` either way, but whether that is damage or a correct repair
   depends on the raw `business_name` value, which I did not read. **Not estimated.**

6. **G6 - No `test_sX` address field for France was read raw.** Per the RAM constraint I
   worked exclusively from the six profile JSONs. Every number above is traceable to
   `addr_tokens`, `name_tokens`, `by_country` or `rows`; nothing is derived from the TSVs.


test_s1 is dominated by the three **region** names (Hauts-de-France, Nouvelle-Aquitaine,
Pays de la Loire); test_s2 and test_s3 additionally use **department** names
(Nord, Gironde, Pas-de-Calais, Loire-Atlantique) at volume. Both spellings are already
in `FR_REGIONS`, so both resolve. This is a *source-format* difference worth knowing
for any future France modelling, and it is **independent evidence that the s1-only
100% figure cannot be extrapolated to s2/s3** - the strings being matched are not the
same strings.

Root cause: `LEET` maps `1-l`, `3-e`, `4-a`, `5-s`, `6-g`, `7-t`, `8-b`, `0-o` but
**deliberately omits `2` and `9`**. That is why `2eme` (697 addr occurrences) and `2bis`
survive intact while `1er` and `3eme` are destroyed - an inconsistency in the table
itself. The correct fix is **not** to extend `LEET` but to **guard it**: skip the
leet transform when the token is a leading ordinal in a French suffix pattern
(`^\d+(er|ere|eme|eme|e)$`). I mark this **CONFIRMED** - the token counts and the
transform simulation are both exact.

unused.

competition setup: France is test-only, so there is **no French ground truth to learn
abbreviations from**, which is exactly why this mining is needed.

> **Corroboration of the re-scoped REFUTED-2.** I independently confirm the denominator
> problem: test_s1 France is 259,452 / 1,694,445 = **15.31%** of French rows. Any
> s1-only rate is not a France-wide rate. I do **not** restate the 100% figure and I make
> no France-wide state-resolution claim - see Gaps.
