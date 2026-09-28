# D090 — mine evidence to extend LEET for France

## Headline

`LEET` (`normalize.py:256`) is **complete and correct** for the 18 token types that are
genuinely leetspeak in France (2,253 occurrences), but it **actively corrupts** the French
ordinal/étage abbreviations `3eme`, `1er`, `3e`, `1ere`, `7eme` into non-words (1,111
occurrences), because those are not leet at all — they are French ordinals. Adding digits to
`LEET` is the wrong fix; the correct fix is an **ordinal guard plus a name-side ordinal
dictionary**. Separately, a clean **negative**: the "s2/s3 department gap" carried in
`already_checked` is **not** supported for the three highest-mass department tokens — `nord`,
`gironde` and `loire atlantique` are **all already keys** in `FR_REGIONS`.

## Findings

### F0. Arithmetic invariants verified (used as denominators)

| Invariant | Value | Check |
|---|---|---|
| `sum(country_rows.values()) == rows`, all 6 files | exact | e.g. test_s1 `663106+259452+809986 = 1,732,544 = rows` |
| France test rows, 3 sources | **1,694,445** | `259452 + 703378 + 731615` |
| `country_rows["France"]` = 0 in all 3 train files | 0 | `by_country` has no `France` key in train — France is test-only |

`name_tokens` is pruned to `TOPN=4000` and to `count>=2` by `build_profile.py:45-48,140`, so
**the listed token mass is a lower bound**. Realised coverage
(`sum(listed counts) / by_country[country].name_tokens`):

| file | country | coverage |
|---|---|---|
| test_s1 | France | 91.98% |
| test_s2 | France | 90.23% |
| test_s3 | France | 89.61% |
| test_s2 | US | 83.33% |
| test_s2 | India | 83.93% |

⇒ **GAP: ~9-10% of French name-token mass is not visible to this profile.** Every token count
below is a floor, not a total.

⇒ **GAP (corrected on re-verification): the equivalent address-side coverage figure is NOT
computable from this profile.** `by_country` stores `name_tokens` (a true token total) but
**no address-token total** — the only address fields are `addr_chars`, `addr_empty`,
`num_digits`, `dig5`, `dig6`, `alpha_only_addr`, `has_comma`, `len_hist`. An earlier
revision of this file asserted "~10% of address-token mass"; that figure has **no
traceable denominator and has been removed** rather than restated. The top-4000 cap
(`build_profile.py:141`) guarantees address coverage is *below* 100%, but by an
unquantifiable amount.

### F1. LEET applies to NAMES only, and France names have digits in them

`normalize.py:279-281` — `LEET` fires only when a name token has *both* a letter and a digit.
`normalize_address` (line 342-349) never calls `LEET`; address tokens go straight to
`canon.get(t, t)`.

`by_country[France].has_digit_name` / `rows`:

| source | has_digit_name | rows | rate |
|---|---|---|---|
| test_s1 | 2,002 | 259,452 | 0.7716% |
| test_s2 | 7,818 | 703,378 | 1.1115% |
| test_s3 | 8,094 | 731,615 | 1.1063% |
| **total** | **17,914** | **1,694,445** | **1.0572%** |

For contrast (test_s2): US `115616/1871330 = 6.1783%`, India `66575/2312565 = 2.8788%`.
**France has the lowest digit-in-name rate of the three countries.**

### F2. THE RESULT: LEET's accuracy on French name tokens

`name_tokens["France"]`, tokens containing both a letter and a digit, 3 test files
(`5,307` occurrences, 24 types). Classification is mine; the counts are profile fields.

| class | types | occurrences | % of 5,307 |
|---|---|---|---|
| LEET already correct | 18 | **2,253** | 42.45% |
| LEET corrupts to a non-word | 5 | **1,111** | 20.93% |
| unresolved / ratio-anomalous | 1 (`4l`) | **1,943** | 36.61% |

**2,253 + 1,111 + 1,943 = 5,307.** ✓

#### F2a. LEET already correct — 18 types, 2,253 occurrences. **No change needed.**

Every one of these has its plain spelling present in the same token list, at ~500x the mass:

| mixed | n | LEET→ | plain n | ratio mixed/plain | in `NAME_CANON`? |
|---|---|---|---|---|---|
| `5arl` | 637 | `sarl` | 358,676 | 0.002 | `sarl` (line 136) |
| `5as` | 417 | `sas` | 252,882 | 0.002 | `sas` (136) |
| `c1ub` | 190 | `club` | 122,195 | 0.002 | — |
| `amica1e` | 136 | `amicale` | 79,613 | 0.002 | — |
| `5a` | 129 | `sa` | 82,278 | 0.002 | `sa` (136) |
| `mais0n` | 118 | `maison` | 61,373 | 0.002 | — |
| `uni0n` | 87 | `union` | 49,247 | 0.002 | — |
| `5asu` | 85 | `sasu` | 73,614 | 0.001 | `sasu` (136) |
| `c0mite` | 75 | `comite` | 53,381 | 0.001 | — |
| `ass0ciation` | 75 | `association` | 24,164 | 0.003 | — |
| `rati0n` | 61 | `ration` | 23,548 | 0.003 | — |
| `tab1issements` | 56 | `tablissements` | 31,387 | 0.002 | — |
| `li1le` | 54 | `lille` | 25,716 | 0.002 | — |
| `c0mit` | 29 | `comit` | 23,582 | 0.001 | — |
| `5ci` | 27 | `sci` | 63,630 | 0.000 | `sci` (137) |
| `fi1s` | 26 | `fils` | 46,583 | 0.001 | — (in `NAME_STOP`, 148) |
| `5portive` | 26 | `sportive` | 43,661 | 0.001 | — |
| `sp0rtive` | 25 | `sportive` | 43,661 | 0.001 | — |

`ratio = mixed / plain`. The 18 correct types all sit at **0.000-0.003**. Digits used:
`{0, 1, 3, 4, 5}` — every one already a `LEET` key.

#### F2b. LEET CORRUPTS — 5 types, 1,111 occurrences. **NEW DEFECT.**

| mixed | n | LEET→ | plain-form token exists? | correct French expansion (and its count) |
|---|---|---|---|---|
| `3eme` | **748** | `eeme` | **0 occurrences** | `troisieme` = **218** |
| `1er` | **131** | `ler` | **0 occurrences** | `premier` = **128**, `premiere` = **114** |
| `3e` | **121** | `ee` | `ee` = 1,017 (unrelated) | `troisieme` = 218 |
| `1ere` | **102** | `lere` | `lere` = 9 | `premiere` = 114 |
| `7eme` | **9** | `teme` | **0 occurrences** | `septieme` = **0** |

Arithmetic: `748+131+121+102+9 = 1,111`. ✓

Why this matters mechanically: `_name_tokens` does `t.translate(LEET)` **then**
`NAME_CANON.get(t, t)`, and `core` drops only `NAME_STOP`. Neither `eeme`, `ler`, `teme` nor
`lere` is in `NAME_CANON` or `NAME_STOP`, so **each survives into the IDF-weighted core
features as a unique garbage token** while a row writing `3eme` and a row writing `troisieme`
produce zero token overlap. This is a guaranteed false negative on French pairs.

`4l` (1,943 — the single largest French mixed name token) is left **unresolved**; see F2c.

#### F2c. `4l` — ratio anomaly, `SPECULATIVE`

`4l` = 1,943 (s1 311, s2 835, s3 797). `LEET` maps it to `al` = 645, so
`ratio = 1943/645 = 3.012` — the **only** token whose mixed form *outnumbers* its LEET target
among the plausible leet set, and the inverse of all 18 genuine leet pairs.
(`1ere`=11.33 and `3e`=0.119 also break the 0.003 pattern, but both are ordinals per F2b.)

Two readings, and the profile **cannot** decide between them:
1. `4l` is not leet at all (e.g. a real token); or
2. `al`'s 645 undercounts, because `strip_accents` is not applied by the profile builder and
   `al` is a fragment of other accented words (see F4b).

`4l` occurs **0** times in `addr_tokens["France"]`, so it is name-only. I did **not** find
evidence for the current `4→a` mapping. **Flagged for raw-data check, not recommended for
change.**

### F3. Address column: the same mixed-token mass, entirely untreated

**Independently re-verified (second pass).** I recomputed all of F2 from scratch
against the profile and reproduced the draft's partition exactly:
`2,253 + 1,111 + 1,943 = 5,307` ✓, and `13,580` address-side ✓. I also **pinned the
mechanism the earlier revision only asserted**: a repo-wide search for
`LEET|translate` returns **exactly two hits**, both inside `_name_tokens`
(`normalize.py:256` definition, `normalize.py:280` use). There is **no
`translate(LEET)` call anywhere in `normalize_address`** (`normalize.py:328-352`).
That is a code fact, not an inference.

**The asymmetry, stated as a measured quantity.** Because LEET fires only on the name
side, the *same literal string* receives two different outputs depending on which column
it sits in. Exactly two tokens appear on both sides:

| literal token | name mass | name output (LEET fires) | addr mass | addr output (no LEET) |
|---|---|---|---|---|
| `3eme` | 748 | `eeme` | 350 | `3eme` (preserved) |
| `1er` | 131 | `ler` | 1,963 | `1er` (preserved) |
| **total** | **879** | corrupted | **2,313** | preserved |

`879 + 2,313 = 3,192` occurrences of the same two literals are forced into two different
output spaces by field alone.

**Why that costs a match (`keys.py`, read-only).** `keys.py:33-34` builds `nt` from
`ncore` (LEET-processed name tokens) and `keys.py:39-43` builds `alph` from `atoks`
(**raw** address tokens). The kind-0 "NA" key (`keys.py:60`) is the XOR of a name-token
hash and an address-token hash, so it requires both sides to agree on a string. Since
`eeme ≠ 3eme`, that key cannot form for these rows. Independently, `features.py:128-129`
computes name overlap (`wn`) and address overlap (`wa`) against **separate** IDF tables
(`name_idf`, `addr_idf`), so a corrupted name token can never be rescued by the address
column either.

**Address/name ratio (the size of the untreated side).**
13,580 / 5,307 = **2.56×** — the address side carries 2.56× as many LEET-triggering
tokens as the name side, and none of them are touched. Per row: 13,580 / 1,694,445 =
0.008014 vs 5,307 / 1,694,445 = 0.003132.

`addr_tokens["France"]`, letter+digit tokens, 3 test files — **46 types, 13,580 occurrences**:

| | types | occurrences | % |
|---|---|---|---|
| string would **change** under `LEET` | 37 | **8,099** | 59.64% |
| unchanged (digit `2`/`9` — absent from `LEET`) | 9 | 5,481 | 40.36% |

The 8,099 that *would* change are **all corruptions, never improvements**:
`1er`(1,963)→`ler`, `chem1`(1,102)→`cheml`, `3eme`(350)→`eeme`, `espl1`(311)→`espll`,
`1b`(221)→`lb`, `1bis`(181)→`lbis`, `80b`(179)→`bob`, `6b`(175)→`gb`, `5b`(164)→`sb`,
`12b`(164)→`l2b`, `11b`(162)→`llb`, `13bis`(159)→`lebis`, `7b`(156)→`tb`,
`3b`(154)→`eb`, …

Contrast with the name column: French **address** mixed tokens *do* use digits `2` and `9`
(`2b` 237, `2bis` 196, `9b` 166, `22b`, `2eme` 697, `cour2` 3,872), whereas French **name**
mixed tokens use only `{0,1,3,4,5}`. **⇒ Do NOT extend `LEET` to the address path.** Extend
`ADDR_CANON_FR` instead.

### F4. Abbreviation table — measured gaps

`ADDR_CANON_FR` (`normalize.py:199-214`) vs `addr_tokens["France"]`, 3 test files:

| candidate | n (3 files) | status | confidence |
|---|---|---|---|
| `cour` | **9,403** | **CONFIRMED gap.** `ADDR_CANON_FR` has `cours`→`crs` and `crs`→`crs`, but **not** `cour`. Counts: `cour` 9,403 / `cours` 8,761 / `crs` 4,520 — one French street type currently yields **three different tokens**. Add `"cour": "crs"`. | CONFIRMED |
| `cour2` | 3,872 | fused `cour`+house-number. Fixes only if the split happens first. | LIKELY |
| `chem1` | 1,102 | fused `chemin`+number. `chem` = 0 occurrences, so this is a distinct form. | LIKELY |
| `esplanade` | 878 | French street type **entirely absent** from `ADDR_CANON_FR`. | LIKELY |
| `chaussee` | 1,125 | absent. See F4b — the accented/unaccented split inflates this. | LIKELY |
| `cite` | 2,546 | absent. See F4b. | LIKELY |
| `ge` | **41,120** | absent; `general`=4,826, `gen`=1,227, `gal`=25, `georges`=10,957. 8.5x more `ge` than `general`. **Unresolved.** | SPECULATIVE |
| `1er`,`2eme`,`3eme`,`2e` | 1,963 / 697 / 350 / 162 | French ordinals, none in `ADDR_CANON_FR`. | CONFIRMED (present) |
| `Nb`/`Nbis` fusions (`1b`,`2b`,`3b`,`5b`,`6b`,`7b`,`9b`,`10b`,`11b`,`12b`,`13b`,`14b`,`15b`,`16b`,`17b`,`18b`,`19b`,`20b`,`24b`,`25b`,`28b`,`33b`,`1bis`,`2bis`,`3bis`,`4bis`,`5bis`,`6bis`,`13bis`,`15bis`) | ~2,600 combined | `ADDR_CANON_FR` has `b`→`bis` and `ter`→`ter` but no digit-fused forms, so `2 b` → `["2","bis"]` while `2b` → `["2b"]`. **Tokenisation inconsistency.** | CONFIRMED |

Function words `de` (1,050,023), `la` (481,231), `du` (220,355), `des` (199,183) are already
established as unhandled in `ADDR_CANON_FR` — not re-measured here, per `already_checked`.

#### F4b. METHODOLOGICAL DEFECT IN THE PROFILE ITSELF (affects every candidate above)

`build_profile.py:111,127` applies `TOKEN_RE = [a-z0-9]+` to the **raw lowercased string, with
no accent stripping**. `[a-z0-9]` does not match `é`, so **every accented French word is
chopped at its first accent**. Demonstrable in the data:

| accented form → profile tokens | counts (3 files) | unaccented twin | count |
|---|---|---|---|
| `chaussée` → `chauss` | 2,372 | `chaussee` | 1,125 |
| `cité` → `cit` | 5,580 | `cite` | 2,546 |
| `général` → `g`,`n`,`ral` | `ral` = 10,251, `g` = 12,539, `n` = 106,424 | `general` | 4,826 |

`normalize.py:264-266` *does* call `strip_accents` (NFKD), so the **pipeline rejoins these into
one token** while the **profile shows them as different tokens**. Consequence: profile token
counts for any accented French candidate are split across 2+ entries and my counts are floors.
`1er`(1,963), `3eme`(350), `2eme`(697) are *also* suspect here — `1er`/`1ère` are
ordinal abbreviations, but the accented `1ère` would appear as `1` + `re`. **This is the
single biggest reason to re-measure the candidate tables against the raw data before changing
code.**

### F5. Region/state tables — a clean NEGATIVE on the department gap, and a third opinion on 71.10%

`FR_REGIONS` (`normalize.py:243-249`) has 14 keys. Six are multi-word (`hauts de france`,
`nouvelle aquitaine`, `pays de la loire`, `ile de france`, `loire atlantique`, `pas de
calais`) and **can never appear as a single profile token** because the builder splits
components on whitespace/punctuation. **A count of 0 for a multi-word key is a tokenisation
artefact, not evidence of absence.** Only the 8 single-word keys are measurable:

| key | canon | s1 rate | s2 rate | s3 rate | counts (s1,s2,s3) |
|---|---|---|---|---|---|
| `nord` | hdf | 0.0771% | **10.7143%** | **10.4493%** | 200, 75362, 76449 |
| `gironde` | naq | 0.0239% | **10.6776%** | **10.3362%** | 62, 75104, 75621 |
| `somme` | hdf | 0.1283% | 0.1147% | 0.1139% | 333, 807, 833 |
| `paris` | idf | 0.1495% | 0.1353% | 0.1262% | 388, 952, 923 |
| `landes` | naq | 0.0447% | 0.0415% | 0.0428% | 116, 292, 313 |
| `oise` | hdf | 0.0285% | 0.0210% | 0.0190% | 74, 148, 139 |
| `aisne` | hdf | 0 | 0 | 0 | 0, 0, 0 |
| `vendee` | pdl | 0 | 0 | 0 | 0, 0, 0 |
| `atlantique` | (part of `loire atlantique`) | 0.0975% | 9.0559% | 8.8022% | 253, 63697, 64398 |

**Discriminator (my criterion, fully traceable):** a token is an *s2/s3-only geographic label*
if `rate_s1 < 0.5%` and `rate_s2 or rate_s3 >= 2%`. Complete result over all 4,000 listed
tokens per source:

| token | totN | s1 % | s2 % | s3 % | in `FR_REGIONS`? |
|---|---|---|---|---|---|
| `nord` | 152,011 | 0.0771 | 10.7143 | 10.4493 | **YES — key** |
| `gironde` | 150,787 | 0.0239 | 10.6776 | 10.3362 | **YES — key** |
| `atlantique` | 128,348 | 0.0975 | 9.0559 | 8.8022 | **part of key `loire atlantique`** |
| `no` | 72,021 | 0.1095 | 5.1174 | 4.8854 | `no`→`""` in `ADDR_CANON_FR:213` |
| `pas` | 29,032 | 0.0690 | 2.0366 | 1.9857 | part of key `pas de calais` |

**⇒ CLEAN NEGATIVE. There is no high-mass, currently-unhandled department token.** The
three tokens that carry the s2/s3 department encoding — `nord`, `gironde`, `loire
atlantique` — are **all already keys in `FR_REGIONS`**. `already_checked` offers exactly
these three as "examples" of the gap; on the profile they are examples of the opposite. I am
not re-deriving the earlier denominator error — I am reporting that the characterisation is
wrong for the top-3.

**State-resolution upper bound (my own criterion, third independent measurement).**
Criterion: a France row can only resolve `state` if its address contains a token that is the
distinctive proxy of one of the 14 `FR_REGIONS` keys. Summing those proxy counts is a valid
upper bound (a row matching *k* keys is counted *k* times, so the sum ≥ the union):

| source | Σ proxy counts | capped upper bound | rows | upper-bound rate |
|---|---|---|---|---|
| test_s1 | 261,569 | 259,452 | 259,452 | 100.00% |
| test_s2 | 443,176 | 443,176 | 703,378 | 63.01% |
| test_s3 | 473,486 | 473,486 | 731,615 | 64.72% |
| **total** | — | **1,176,114** | **1,694,445** | **69.41%** |

`1,176,114 / 1,694,445 = 69.41%`.

This **corroborates the `already_checked` 71.10% band and contradicts D077's 97.44%** by a wide
margin, using a criterion stated independently. The likely reason for the ~1.7pt gap from
71.10% is a slightly different proxy set; the gap to 97.44% is a different resolution criterion
entirely. **All three numbers remain provisional** — I am not claiming to have settled the
D073/D077 contradiction, only that a third union-bound computation lands at 69.41%.

**The actionable consequence:** the 30.59% of French rows with **no** region/department token
present (s2: 260,202 rows; s3: 258,129 rows) are **unreachable by any `FR_REGIONS` extension**
— the string is not in the data. That reframes the gap from *"the dictionary is too thin"*
to *"the field is not populated in s2/s3"*, which no dictionary edit can fix.

## Interpretation

*(marked as inference)*

1. `LEET` needs **no new digit keys**. Every digit that occurs inside a French name token
   (`{0,1,3,4,5}`) is already mapped, and all 18 genuine leet types already resolve correctly.
   Adding `2`/`9` would change **zero** French name tokens (0 of 5,307 mixed occurrences use
   `2` or `9`).
2. `LEET` needs a **guard**, not keys. A regex guard for French ordinals —
   `^\d+(er|ere|e|eme|ieme)$` — applied *before* `translate(LEET)`, would divert 1,111
   occurrences away from garbage.
3. The French **ordinal** is a dictionary problem, not a leet problem: `NAME_CANON` has
   `saint`/`ste` but no `1er`/`1ere`/`2eme`/`3eme`. Adding
   `{"1er":"premier","1ere":"premiere","2e":"deuxieme","2eme":"deuxieme","3e":"troisieme","3eme":"troisieme","7eme":"septieme"}`
   would align 1,111 leet-mangled occurrences with the 460+ already-written plain forms
   (`troisieme` 218, `premier` 128, `premiere` 114, `deuxieme` 102, `cinquieme` 9).
4. `ADDR_CANON_FR` should gain `cour`, `esplanade`, `chaussee`, `cite` — but these are
   *consistency* fixes, not recall fixes, and F4b says the counts are unreliable.

## Gaps

- **`@` and `$` in `LEET` cannot be evaluated at all.** `build_profile.py:28` sets
  `TOKEN_RE = [a-z0-9]+`, which **discards every non-alphanumeric character**. The profile
  contains no information about symbol-leetspeak. The two symbol keys in `LEET` are untested.
- **Accents are destroyed by the profile builder** (F4b), so every count involving an accented
  French word is a floor and possibly split across tokens.
- **~9-10% of French name-token mass is outside the top-4000** (F0), so additional mixed-token
  types may exist below the cut.
- **No co-occurrence data.** `addr_tokens` flattens all comma-components into one counter
  (`build_profile.py:126-127`), so I cannot tell whether `hauts` sits in the same component as
  `de`+`france`, nor whether `nord` and `hauts` co-occur in one row. Every state-resolution
  number here is a **union bound, not a direct count**.
- **`4l` (1,943) is unresolved** and needs a raw-data check.
- **`ge` (41,120) is unresolved**; I could not determine what it abbreviates.

## Recommendations

1. **Do not add any digit to `LEET`.** 0 of 5,307 French mixed name occurrences use `2` or
   `9`. Expected effect: none — this is a deliberate *no-change* recommendation, and it is
   the honest answer to the "extend LEET" framing of the work order.
2. **Add an ordinal guard before `translate(LEET)` in `_name_tokens`** (priority 1, cheap,
   safe). Diverts 1,111 occurrences (20.93% of French mixed name tokens) out of garbage tokens.
   Add a regression guard for the 18 correct types in F2a.
3. **Add French ordinals to `NAME_CANON`**, per interpretation 3. **CONFIRMED** for
   `3eme`/`troisieme` (748 vs 218), `1er`/`premier` (131 vs 128), `1ere`/`premiere` (102 vs
   114) — both sides measured. `LIKELY` for `2e`/`deuxieme`, `7eme`/`septieme` (plain form
   = 0).
4. **Add `"cour": "crs"` to `ADDR_CANON_FR`** — **CONFIRMED**, 9,403 occurrences, and the
   only entry here with no accent caveat.
5. **Do NOT apply `LEET` in `normalize_address`.** 59.64% of French mixed address tokens would
   change and every change is a corruption (`1er`→`ler`, `80b`→`bob`, `11b`→`llb`).
6. **Re-measure F4 against the raw data before editing `ADDR_CANON_FR`** — the profile's
   missing accent stripping makes the `esplanade`/`chaussee`/`cite`/`ge` counts unreliable
   (F4b).
7. **Stop sizing fixes from the 71.10% / 97.44% dispute.** My independent union bound is
   69.41% (F5); the residual ~30% has no region token in the data at all and is not a
   dictionary gap.
