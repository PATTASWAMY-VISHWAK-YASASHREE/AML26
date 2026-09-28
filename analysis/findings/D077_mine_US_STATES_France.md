# D077 — mine evidence to extend US_STATES for France

## Headline

`FR_REGIONS` is not the problem, but the *denominator* used to clear it is too narrow: the earlier "state resolves for 100.00% of France rows (259,452 / 259,452)" figure is exactly the `test_s1` France row count, and across all three test splits France has 1,694,445 rows of which **43,411 (2.5620%) carry no comma in a non-empty address and can therefore never resolve a state** — a hard ceiling of 97.4380%, not 100%. Separately, and independent of `FR_REGIONS`, the profile exposes **six France-only address tokens that no dictionary handles, led by `ge` at 41,120 occurrences**, plus a genuine `LEET` defect: French ordinals (`3eme`, `1er`, `1ere`, `3e`) are rewritten into garbage (`eeme`, `ler`, `lere`, `ee`) in 1,111 name-token occurrences.

Two clean "no defect" results are also confirmed, and one measurement caveat materially limits everything below.

## Findings

All counts are `addr_tokens[France]` / `name_tokens[France]` occurrences summed over
`test_s1 + test_s2 + test_s3` (the only splits containing France; `country_rows` in
`train_s1..s3` has no `France` key at all). Denominator for all "per 1k" rates is
total France rows = 259,452 + 703,378 + 731,615 = **1,694,445**.

### F0. Scope correction to REFUTED-2 (not a re-derivation)

The instruction says REFUTED-2 is settled and not to redo it. I am not re-deriving its
conclusion — which I confirm below — but its quoted denominator is one split, and that
matters for any downstream claim of "100%".

Arithmetic invariant, exact, from `by_country[France]`:

`rows - addr_empty == has_comma + (rows - addr_empty - has_comma)`, i.e. every France row
is either address-empty, comma-bearing, or non-empty-and-comma-free.

| split | rows | addr_empty | has_comma | non-empty & comma-free | rows that can carry a state |
|---|---|---|---|---|---|
| test_s1 | 259,452 | 0 | 259,452 | 0 | 259,452 (100.0000%) |
| test_s2 | 703,378 | 21,537 | 681,661 | 180 | 681,661 (96.9125%) |
| test_s3 | 731,615 | 21,541 | 709,921 | 153 | 709,921 (97.0348%) |
| **total** | **1,694,445** | **43,078** | — | **333** | **1,651,034 (97.4380%)** |

- 43,078 rows (2.5423% of France rows) have an **empty** `business_address`. Verified
  against the real code: `normalize_address('', 'France')` returns `state=''`.
- 333 rows (0.0197%) are non-empty but comma-free. A comma-free row can *only* resolve if
  the whole address is a bare region name — verified: `normalize_address('Nord','France')`
  returns `state='hdf'`. So 333 is an upper bound on recoverable rows, not a shortfall.
- **Hard no-state count: 43,078 = 2.5423% of France rows.** Ceiling: 97.4380%.

Control (same invariant, other countries): US test_s1 = 100.0000%, US test_s2 = 97.0552%,
US test_s3 = 97.1570%; India 97.7183% / 97.5368%. France is in line with the other
countries, so this is a source-2/3 property, **not** a France defect.

**Confirmation of REFUTED-2's substance** (independent check, different evidence): the
`FR_REGIONS` canonical values `hdf`, `idf`, `naq`, `pdl` occur **0 times each** in the

### F1. Region/state candidates not in `FR_REGIONS` (ranked)

`FR_REGIONS` has 14 keys -> 4 canonical values. These 11 single-token French
region/department names occur in France addresses and are **not** keys:

| rank | token | test_s1 | test_s2 | test_s3 | total | per 1k FR rows | status |
|---|---|---|---|---|---|---|---|
| 1 | marne | 423 | 994 | 1,061 | 2,478 | 1.46 | LIKELY |
| 2 | lorraine | 334 | 825 | 789 | 1,948 | 1.15 | LIKELY |
| 3 | alsace | 311 | 744 | 758 | 1,813 | 1.07 | LIKELY |
| 4 | bretagne | 222 | 505 | 535 | 1,262 | 0.74 | LIKELY |
| 5 | gard | 135 | 305 | 320 | 760 | 0.45 | LIKELY |
| 6 | normandie | 139 | 288 | 329 | 756 | 0.45 | LIKELY |
| 7 | auvergne | 89 | 213 | 218 | 520 | 0.31 | LIKELY |
| 8 | martinique | 75 | 166 | 173 | 414 | 0.24 | LIKELY |
| 9 | picardie | 38 | 79 | 98 | 215 | 0.13 | LIKELY |
| 10 | vienne | 35 | 82 | 77 | 194 | 0.11 | LIKELY |
| 11 | guyane | 27 | 0 | 0 | 27 | 0.02 | SPECULATIVE |
| | **total** | | | | **10,387** | **6.13** | |

Why only LIKELY, not CONFIRMED — and this is the single most important caveat in this
report: `normalize_address` matches a region only when an **entire comma-component**
equals a key (`if ck in smap`). A token count is therefore *not* a row count and not a
state-signal count. `marne` at 2,478 occurrences is equally consistent with 2,478 rows of
"... , Marne" **and** with street-name usage such as "rue de la Marne", which resolves
nothing. `build_profile.py` splits the address on `[,;]` and updates a **flattened**
counter per component (`at.update(TOKEN_RE.findall(comp))`), so component identity is
discarded. I cannot recover which component a token came from. Order-of-magnitude is
consistent with the ~1,100 legacy-name rows the work order mentions, but I cannot confirm
any individual token is a region component.

Verified variant gaps in `FR_REGIONS` (run against the real `normalize_address`):

| input component | state | note |
|---|---|---|
| `Hauts-de-France` | `hdf` | resolved |
| `Haut de France` | `''` | **unresolved** — singular variant is not a key |
| `Nord-Pas-de-Calais` | `''` | **unresolved** — hyphenated two-dept form is not a key |
| `Nord Pas-de-Calais` | `''` | **unresolved** — same |
| `Pas-de-Calais` | `hdf` | resolved |
| `Loire-Atlantique` | `pdl` | resolved |
| `Ile-de-France` | `idf` | resolved |
| `Vendée` | `pdl` | resolved (accents stripped upstream) |
| `Aquitaine` / `Lorraine` / `Bretagne` | `''` | unresolved, not keys |

`haut` (singular) occurs 2,263 times in the France address stream vs `hauts` 289,655.

### F2. Abbreviation / street-type candidates (ranked, with controls)

`in_canon` = present in `ADDR_CANON_FR` or `ADDR_CANON_COMMON`.

| token | France | US | India | in_canon | status | rationale |
|---|---|---|---|---|---|---|
| ge | 41,120 | 0 | 0 | no | LIKELY | prefixes `general` (4,826 -> canon `gen`) and `gen` (1,227 -> `gen`); also prefixes `georges` (10,957), `george` (1,361), `germain` (950) |
| pr | 5,881 | 0 | 0 | no | SPECULATIVE | prefixes `professeur` (2,485 -> `prof`), `president` (1,884 -> `pres`), also `prairie`/`princesse`/`prosper` |
| cit | 5,580 | 0 | 1,589 | no | LIKELY | French `Cité`; `cite` (2,546) is France-only |
| cite | 2,546 | 0 | 0 | no | **CONFIRMED** | French `Cité` street type, absent from `ADDR_CANON_FR` while `impasse`/`place`/`square`/`chemin`/`cours`/`faubourg` are present |
| haut | 2,263 | 0 | 0 | no | LIKELY | singular `Haut`; `haut de france` does not resolve (F1) |
| es | 2,168 | 0 | 0 | no | SPECULATIVE | prefixes `est` (469 -> canon `estate`), `esplanade` (878), `espagne` (755), `esp` (611) |
| alle | 502 | 0 | 0 | no | CONFIRMED | misspelling/truncation of `allee` (17,779 -> canon `allee`) |
| avneue | 482 | 0 | 0 | no | CONFIRMED | misspelling of `avenue` (126,497 -> canon `ave`) |
| allees | 187 | 0 | 0 | no | CONFIRMED | plural misspelling of `allee` |

### F3. Leetspeak: `LEET` is net-positive but mangles French ordinals

`LEET` (normalize.py:256) maps `0->o 1->l 3->e 4->a 5->s 6->g 7->t 8->b @->a $->s`. It is
applied in `_name_tokens` **only when a token has both a letter and a digit**, and — verified
— it is **not** applied to address tokens (`"LEET" in inspect.getsource(normalize_address)`
is `False`).

Genuine leetspeak in France business names decodes **correctly** (run through the real
`_name_tokens`): `5arl->sarl`, `5as->sas`, `5asu->sasu`, `5a->sa`, `c1ub->club`,
`amica1e->amicale`, `mais0n->maison`, `uni0n->union`, `c0mite->comite`,
`ass0ciation->association`. Total **1,949** occurrences (1.15 per 1k France rows) —
CONFIRMED working.

French ordinals hit the same table and are **destroyed**:

| ordinal token | occurrences (names) | `_name_tokens` output | verdict |
|---|---|---|---|
| 3eme | 748 | `eeme` | corrupted |
| 1er | 131 | `ler` | corrupted |
| 3e | 121 | `ee` | corrupted |
| 1ere | 102 | `lere` | corrupted |
| 7eme | 9 | `teme` | corrupted |
| 2eme | 0 | `2eme` (safe — `2` is not in `LEET`) | — |
| **total corrupted** | **1,111** | | 0.66 per 1k France rows |

Per split: test_s1 186, test_s2 447, test_s3 478.

In the **address** stream the same ordinals survive as literals because `LEET` is not
applied there: `1er` 1,963, `2eme` 697, `3eme` 350 — and none of the three is in any
canon dict, so French ordinal street/address markers are unhandled on both paths.

`4l` (1,943 occurrences, 311/835/797) decodes to `al`. I cannot determine its intended
expansion from the profile — **SPECULATIVE**, no action recommended.

### F4. Fused building suffixes: `12 bis` and `12bis` normalise differently

Standalone `bis` is handled (`ADDR_CANON_FR` maps `bis`->`bis`, `b`->`bis`) and occurs
**52,072** times. But fused forms are not, because `canon.get('12bis', '12bis')` misses
and `LEET` is not applied to addresses:

- `<n>b` fused: 3,427 occurrences
- `<n>bis` fused: 1,405 occurrences
- **total fused: 4,832** (2.85 per 1k France rows)

Verified against the real code:

- `normalize_address('12 bis avenue de la Paix','France')` -> `['12','bis','ave','de','la','paix']`
- `normalize_address('12bis avenue de la Paix','France')` -> `['12bis','ave','de','la','paix']`

Same address, two different token streams — a real blocking/feature mismatch.

Also unhandled in addresses: `cour2` (3,872), `chem1` (1,102), `espl1` (311), `chau1` (177)
— French `Cour 2` / `Chemin 1` / `Esplanade 1` compounds, 5,462 occurrences combined.
Same root cause: digit-fused compounds are neither split nor canon-mapped.

## Interpretation

*Inference, clearly marked as such.*

1. **The `FR_REGIONS` coverage question is settled and should stay settled.** The
   canonical codes `hdf/idf/naq/pdl` never appear in the data, so the missing self-map
   loop is inert. Widening `FR_REGIONS` is low priority.
2. **The real France risk is in `ADDR_CANON_FR`, not in `FR_REGIONS`.** Six France-only

## Gaps

1. **Accented French place names are invisible to the profile — this bounds every
   region claim in F1.** `build_profile.py` uses `TOKEN_RE = re.compile(r"[a-z0-9]+")`
   and never strips accents, so `Vende`+`e` is tokenised as `vend` + `e`. Evidence:
   `vendee` = 0 but `vend` = 230; and `rhone`, `pyrenees`, `finistere`, `herault`,
   `lozere`, `cotes` are **all exactly 0**. The pipeline itself is fine —
   `strip_accents` runs before matching, verified: `Vende`->`vendee`->`pdl`. So the
   zero counts are a **profile measurement artefact, not evidence of absence**, and I
   cannot rank or rule out any accented department (Rhone, Finistere, Lozere,
   Herault, Cotes-d'Armor, Pyrenees-Atlantiques, ...). This is a gap in my evidence, and
   it is the reason no F1 row is marked CONFIRMED.
2. **Component identity is lost.** `addr_tokens` is flattened per `[,;]` component, so
   I cannot tell a region component from a street-name token. This is why F1 is LIKELY
   and not CONFIRMED, and it is unfixable without a re-scan.
3. **Top-4000 truncation floor.** `addr_tokens`/`name_tokens` are cut at 4,000 entries
   per country per file. The rank-4000 count is 23 / 58 / 60 (address) and 9 / 25 / 26
   (name) for test_s1/2/3. A token with a true count below that floor can be absent from
   the list entirely, so **absence of a low-count candidate is not evidence of absence**.
   In particular `2eme` = 0 in `name_tokens` is inside the floor and is inconclusive.
4. **`city_comps` / component-order behaviour is not measured at all** — the profile
   records no component list, so I could not test the region-before-city vs
   city-before-region inconsistency the work order flags. Untouched by this report.
5. **No per-row data.** Every rate here is token-occurrence-based. Row-level rates for
   the F1 candidates are unknown.
6. **I could not verify the earlier "~1,100 rows of legacy names" figure** — the profile
   has no field for it, and F1's 10,387 token occurrences cannot be converted to rows.

## Recommendations

Prioritised. Nothing here is speculative-only; items 1-3 are directly traceable to a
counted field.

1. **Add `cite`/`cit` -> `cite` to `ADDR_CANON_FR`.** 2,546 (`cite`) + 5,580 (`cit`)
   occurrences, France-only for `cite`. `Cite` is a standard French street type and
   sits alongside `impasse`, `place`, `square`, `chemin`, `cours`, `faubourg`, which are
   all already mapped. Expected effect: unifies `Cite`/`cit` spellings. CONFIRMED gap.
2. **Add misspelling entries `avneue`->`ave`, `alle`->`allee`, `allees`->`allee`.**
   482 + 502 + 187 occurrences, all zero in test_s1, all France-only. Zero-risk: these
   canonical targets already exist. CONFIRMED gaps.
3. **Add a French-ordinal guard to `LEET` application.** Skip tokens matching
   `^[0-9]+(er|ere|eme|e)$` before `LEET.translate`. Removes 1,111 corrupted
   occurrences (`3eme`->`eeme`, `1er`->`ler`) while preserving the 1,949 genuine
   leetspeak decodes. Add `1er`/`2eme`/`3eme` to `ADDR_CANON_FR` for the address path
   (3,010 occurrences there). Highest value-per-line of anything in this report.
4. **Split fused building suffixes in `normalize_address` before canon lookup.**
   Rewrite `^[0-9]+b(is)?$` to `[num, 'bis']` and add `^cour[0-9]+$`-style handling.
   4,832 fused-suffix occurrences plus ~5,462 `cour2`/`chem1`/`espl1`/`chau1`
   occurrences. Fixes the verified `12bis` != `12 bis` mismatch that can break blocking.
5. **LIKELY, moderate priority: add `ge`->`gen` to `ADDR_CANON_FR`** (41,120
   occurrences, France-only, and `general`/`gen` already map to `gen`). **Verify
   first** — `ge` also prefixes `georges`/forename tokens, so confirm it is the
   `General` abbreviation and not a truncated given name before changing the dictionary.
6. **Do NOT widen `FR_REGIONS` yet.** F1's 10,387 occurrences are plausible candidates
   but unconfirmed (Gaps 1-2), and REFUTED-2 already shows coverage is not the binding
   constraint. Revisit only if a re-scan that preserves accents and component identity
   is run. `haut de france` (singular) and `nord pas de calais` are the two cheap
   variant keys to add if you do — both are verified-missing and cost nothing.
7. **No change needed** for the `pin` guard, the `FR_REGIONS` self-map loop, or the
   empty-address rate. All three are either already-covered, inert, or data properties
   matching the other countries.

   tokens carrying >=482 occurrences each pass through untranslated, and the two
   highest-frequency misspellings (`avneue`, `alle`) are pure loss: `avenue` and `allee`
   already have canon entries that these spellings miss. This is a cheap, safe win.
3. **`LEET` needs a French-ordinal guard, not removal.** It correctly decodes 1,949
   genuine leetspeak occurrences and corrupts 1,111 ordinals. A guard that skips
   tokens matching `^[0-9]+(er|ere|eme|e)$` keeps the gain and removes the loss.
4. **Fused-suffix normalisation is a recall risk for blocking.** `12bis` vs `12 bis`
   producing different token streams means a candidate pair that a human would call a
   match can be missed. 4,832 occurrences is small in absolute terms but these are
   *addresses*, which is the field entity resolution keys on.
5. **The 2.5423% of France rows with empty addresses is a data property, not a bug**,
   and it matches US/India rates. It should not drive a code change — but it does mean
   any "state resolves for X% of France" claim must state its denominator.

| citadelle | 24 | 0 | 0 | no | SPECULATIVE | too rare to act on |

Source-drift signal (not a dictionary claim): `alle`, `allees`, `avneue` are all **0 in
test_s1** and non-zero only in test_s2/test_s3 — the misspellings are introduced by
sources 2 and 3, not source 1.

France address token stream. So the missing self-map loop at `normalize.py:252`
(`for _m in (US_STATES, IN_STATES)` omits `FR_REGIONS`) has zero measurable effect,
because those codes never appear in the data at all.
