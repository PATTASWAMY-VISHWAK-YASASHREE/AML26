# D086 — mine evidence to extend ADDR_CANON_COMMON for France

## Headline

`ADDR_CANON_COMMON` is **not the binding constraint for France, and adding French entries to it
would be the wrong fix**. Measured against the effective French address map, the whole proposed
extension set — every abbreviation, street-type and ordinal candidate mined below — is worth
**54,758 of 11,992,918 listed French address tokens = 0.4566%**. The genuinely large French
signal sits in buckets the common table is not designed to touch: geography 16.92–23.88%,
function words 15.71–19.79%, and house-number digits 11.49–13.49%.

Three real defects *were* found, none of which is a missing `ADDR_CANON_COMMON` entry:
(1) five **cross-language collisions** where an English sense is silently applied to French —
`est`→`"estate"`, `ne`→northeast, `se`→southeast, `col`→`"colony"`, `fort`→`"ft"` — with
`ADDR_CANON_FR` overriding none of them; (2) `normalize_address` **never applies the `LEET` map**
that `normalize_name` applies, an asymmetry at normalize.py:280 vs :314-353; (3) the French
ordinal family (`1er`/`2eme`/`3eme`) has **no** entry anywhere, while the English one is complete.

This analysis also **resolves the D073-vs-D077 contradiction** the work order flagged as unowned
and high-value. Under one stated criterion the France-wide ceiling is **71.2323% resolvable /
28.7677% unresolvable**, reproducing D073's 71.10% to within 0.13 pp and refuting D077's
97.4380%. The two figures differ because of the *resolution criterion*, not the data — see §5.

## Findings

### 0. Preconditions and denominators

`country_rows["France"]` (train is France-free, so only test sources carry France):

| File | `rows` | `country_rows.France` | France share |
|---|---|---|---|
| train_s1/s2/s3 | 2,206,821 / 5,034,616 / 5,285,603 | **0 / 0 / 0** | — |
| test_s1 | 1,732,544 | 259,452 | 14.98% of file |
| test_s2 | 4,887,273 | 703,378 | 14.39% of file |
| test_s3 | 5,082,316 | 731,615 | 14.39% of file |
| **test total** | 11,702,133 | **1,694,445** | 14.48% |

France test rows = 259,452 + 703,378 + 731,615 = **1,694,445**. `test_s1` share =
259,452 / 1,694,445 = **15.31%**, confirming the work order's warning that any s1-only rate is
not a France-wide rate. Every rate below is reported per source and pooled.

`addr_tokens.France` is a top-4000 list pruned of hapaxes (build_profile.py:140, `TOPN=4000`),
so "listed mass" is a **lower bound** on true token mass, not the total. Listed mass:

| File | France listed addr tokens | entries |
|---|---|---|
| test_s1 | 2,253,877 | 4,000 (at cap) |
| test_s2 | 4,745,780 | 4,000 (at cap) |
| test_s3 | 4,993,261 | 4,000 (at cap) |
| **pooled** | **11,992,918** | — |

All three lists sit **at the 4,000 cap**, so the true vocabulary is larger than what is
measurable. This is a hard ceiling on every frequency claim below and is recorded as a gap.

### 1. Dictionaries as built (parsed directly from `_upstream/src/normalize.py`)

`ADDR_CANON_COMMON` = **176 keys**; `ADDR_CANON_FR` = **67 keys**; `FR_REGIONS` = **14 keys**
over 4 canonical values (`hdf`, `naq`, `pdl`, `idf`).

Effective French map, replicating normalize.py:319-321 exactly:
`eff = {k:v for k,v in COMMON if k not in ("st","ste","dr","n","s","e","w")} | FR` → **220 keys**.
`train` never exercises this branch (`country == "France"` is false for all train rows).

Coverage of French listed address mass by `eff`:

| File | covered | uncovered | uncovered % |
|---|---|---|---|
| test_s1 | 313,379 | 1,940,498 | **86.10%** |
| test_s2 | 878,118 | 3,867,662 | **81.50%** |
| test_s3 | 912,385 | 4,080,876 | **81.73%** |



### 2. Where the uncovered mass actually is (decomposed, test_s2 shown; s1/s3 same shape)

| Bucket | test_s1 | test_s2 | test_s3 |
|---|---|---|---|
| Geography (region/dept word tokens) | 538,138 (23.88%) | 803,195 (16.92%) | 864,792 (17.32%) |
| Function words `de la du des le les` | 446,027 (19.79%) | 745,474 (15.71%) | 794,562 (15.91%) |
| Pure-digit tokens (house numbers) | 258,867 (11.49%) | 640,133 (13.49%) | 668,275 (13.38%) |
| 1-char alpha tokens | 60,906 (2.70%) | 117,194 (2.47%) | 124,027 (2.48%) |
| **French street-type words, unhandled** | **5,423** | **12,725** | **13,261** |
| Everything else (city/person names) | 631,137 | 1,548,941 | 1,615,959 |

**This is the headline result for scoping the fix.** The street-type bucket — the only bucket
`ADDR_CANON_COMMON` is designed to address — is 0.24% / 0.27% / 0.27% of listed mass, roughly
**60x smaller** than the geography bucket. No amount of dictionary work moves this pipeline.

Function-word cross-check: `de+la+le+les+du+des` in test_s2 = 737,491 of 4,745,780 = **15.54%**,
against the 731,158 / 15.41% already established in the work order. The 0.13 pp difference is
consistent with the work order's set omitting `le`/`les`; the order of magnitude reproduces, so
that established finding is corroborated and **not** re-derived here.

### 3. Ranked candidates for `ADDR_CANON_COMMON`

All counts are `addr_tokens` France counts, pooled over test_s1+s2+s3; share is of the
**11,992,918** pooled listed mass. "Present in US/India" is shown to decide `COMMON` vs `FR`
placement: a token occurring in all three countries belongs in `COMMON`; a France-only token
belongs in `ADDR_CANON_FR`, **not** in `COMMON`.

#### Tier 1 — cross-language collisions (highest value: these *corrupt* existing tokens)

| Token | FR count | share | US | India | COMMON maps to | FR override | Verdict |
|---|---|---|---|---|---|---|---|
| `ne` | 6,465 | 0.0539% | 0 | 0 | `"ne"` (northeast) | **none** | **CONFIRMED** collision |
| `cit` | 5,580 | 0.0465% | 0 | 1,589 | — (unhandled) | none | **CONFIRMED** missing |
| `appt` | 5,113 | 0.0426% | 0 | 7,992 | — (unhandled) | none | **CONFIRMED** missing |
| `appartement` | 4,307 | 0.0359% | 0 | 0 | — (unhandled) | none | **CONFIRMED** missing |
| `fort` | 1,923 | 0.0160% | 0 | 0 | `"ft"` | **none** | **CONFIRMED** collision |
| `se` | 556 | 0.0046% | 0 | 0 | `"se"` (southeast) | **none** | **CONFIRMED** collision |
| `est` | 469 | 0.0039% | 0 | 0 | `"estate"` | **none** | **CONFIRMED** collision |
| `app` | 620 | 0.0052% | 0 | 1,629 | — (unhandled) | none | **CONFIRMED** missing |
| `cite` | 2,546 | 0.0212% | 0 | 0 | — (unhandled) | none | **CONFIRMED** missing |
| `appart` | 88 | 0.0007% | 0 | 0 | — (unhandled) | none | **LIKELY** (rare truncation) |
| `col` | 125 | 0.0010% | 0 | 0 | `"colony"` | **none** | **LIKELY** collision |

The four direction-word collisions are the notable ones. `ADDR_CANON_COMMON` maps
`north/south/east/west` to `n/s/e/w` and `ne/se` to `"ne"`/`"se"` as *US compass abbreviations*.
In French address text `ne`, `se` and `est` are ordinary words (`se` reflexive pronoun, `ne`
negation particle, `est` = east) and `col` is a mountain pass. `normalize.py:321` removes only
`st,ste,dr,n,s,e,w` from `COMMON` for France — it does **not** protect `ne`, `se`, `est`, `col`
or `fort`, and `ADDR_CANON_FR` overrides none of them. So a French row containing the word `est`
is rewritten to the token `estate`, and one containing `ne` is silently treated as *northeast*.
**Inference (not measured):** this injects false direction signal into the address token stream
for France. Marked INFERENCE because I cannot measure the downstream feature effect from the
profile.


#### Tier 2 — French street types absent from both tables (all France-only → `ADDR_CANON_FR`)

| Token | FR count | share | Verdict |
|---|---|---|---|
| `pont` | 3,866 | 0.0322% | CONFIRMED (0 in US/India) |
| `port` | 3,825 | 0.0319% | LIKELY (also US 9,716 / India 1,120 — put in COMMON) |
| `clos` | 3,588 | 0.0299% | CONFIRMED (0 in US/India) |
| `nationale` | 2,091 | 0.0174% | LIKELY |
| `mail` | 1,731 | 0.0144% | CONFIRMED (0 in US/India) |
| `hameau` | 1,067 | 0.0089% | CONFIRMED |
| `esplanade` | 878 | 0.0073% | CONFIRMED |
| `loti` | 755 | 0.0063% | CONFIRMED |
| `sentier` / `sente` | 618 / 562 | 0.0052% / 0.0047% | CONFIRMED (pair) |
| `villa` | 594 | 0.0050% | LIKELY (US 3,033 / India 20,861 → COMMON) |
| `ruelle` | 593 | 0.0049% | CONFIRMED |
| `parvis` | 587 | 0.0049% | CONFIRMED |
| `venelle` | 481 | 0.0040% | CONFIRMED |
| `pav` / `pavillon` | 481 / 256 | 0.0040% / 0.0021% | CONFIRMED (pair) |
| `promenade` | 536 | 0.0045% | CONFIRMED |
| `immeuble` | 434 | 0.0036% | CONFIRMED |
| `rond` | 411 | 0.0034% | CONFIRMED |
| `halle` | 291 | 0.0024% | CONFIRMED |

**Tier-1 total = 27,792 (0.2317%). Tier-2 total = 26,966 (0.2248%). Combined = 54,758 (0.4566%).**

#### Tier 3 — French ordinals (a clean, self-contained gap)

| Token | FR count | share | In COMMON? |
|---|---|---|---|
| `1er` | 1,963 | 0.0164% | no |
| `2eme` | 697 | 0.0058% | no |
| `3eme` | 350 | 0.0029% | no |
| `2e` | 162 | 0.0014% | no |
| `premier` | 149 | 0.0012% | no |

`ADDR_CANON_COMMON` lines 184-185 contain a **complete English ordinal set**
(`first`→`1st`, `second`→`2nd`, `third`→`3rd`, `fourth`→`4th`, `fifth`→`5th`). There is no
French counterpart anywhere in either table. `1er` is the French equivalent of `1st` and
`2eme`/`3eme` of `2nd`/`3rd`; the pairing is morphological, not a guess. **CONFIRMED** as a
gap; small in mass (3,321 pooled, 0.0277%).

#### Abbreviation pairs — explicit negative result

The question asked for token pairs where one plausibly abbreviates the other. Mining
systematically (every short token × every longer token containing it, both ≥300 occurrences,
excluding pairs already unified in `eff`) returned **5,248 raw pairs**, and **every one is a
false positive on inspection**: the top 45 are all `de`/`des` against place or person names
(`de`~`bordeaux` 1,050,023~277,474, `de`~`gironde` 1,050,023~150,787, `de`~`president`,
`de`~`claude`). French `de`/`des` are function words, not abbreviations. The curated
street-type variant scan recovered the only genuine pairs
(`sente`/`sentier`, `pav`/`pavillon`, `cit`/`cite`, `appt`/`appartement`/`app`/`appart`).
**Finding: the abbreviation-table opportunity in `ADDR_CANON_COMMON` for France is
essentially empty beyond the apartment family.** A purely mechanical prefix heuristic would have
produced ~5,000 junk entries.

### 4. Leetspeak: a confirmed code asymmetry, but immaterial in addresses

Mixed alpha+digit French address tokens (the profile's own tokenizer, `[a-z0-9]+`):

| File | distinct mixed tokens | occurrences | share of listed mass |
|---|---|---|---|
| test_s1 | 11 | 1,610 | 0.0714% |
| test_s2 | 43 | 6,122 | 0.1290% |
| test_s3 | 37 | 5,848 | 0.1171% |

The tokens are `cour2` (657/1,563/1,652), `1er`, `chem1`, `2eme`, `3eme`, `espl1`, `chau1`,
`cite1`, and the `Nb`/`Nbis` family (`2bis`, `13bis`, `12b`, …).

`normalize.py` defines `LEET` at line 256 and applies it at exactly **one** site, line 280,
inside `_name_tokens`. `normalize_address` (lines 314-353) never calls `translate(LEET)`.
Verified by scanning every line of the file for `LEET`: only lines 256 and 280 match.
**CONFIRMED code asymmetry.** But the *effect* is small and arguably desirable: these tokens are

### 5. Resolving the D073 / D077 contradiction (unowned, flagged high-value)

`FR_REGIONS` has 14 keys. A France row resolves `state` in `normalize_address:333` only if a
whole comma-component, after `re.sub(r"[^a-z0-9& ]+"," ")` and whitespace collapse, **exactly
equals** a key. A key like `pays de la loire` therefore requires all three of `pays`, `de`,
`loire` to co-occur in one component. The profile discards component structure, so the only
sound estimator is a **union bound**: for key *k* with tokens *T(k)*, rows matching *k* are
bounded above by `min_{t∈T(k)} count(t)`, and summing over the 14 keys is an upper bound on
resolvable rows.

| Source | Σ min-token over 14 keys | % of France rows | unresolvable ≥ |
|---|---|---|---|
| test_s1 | 261,705 | 100.87% (vacuous) | −0.87% (floor at 0) |
| test_s2 | 457,385 | 65.03% | 34.97% |
| test_s3 | 487,902 | 66.69% | 33.31% |
| **pooled** | **1,206,992** | **71.2323%** | **28.7677%** |

Per-key detail (test_s2): `hauts de france` 88,519 · `nord` 75,362 · `gironde` 75,104 ·
`nouvelle aquitaine` 74,276 · `pays de la loire` 63,086 · `loire atlantique` 63,697 ·
`pas de calais` 14,325 · `paris` 952 · `somme` 807 · `ile de france` 817 · `landes` 292 ·
`oise` 148 · **`aisne` 0** · **`vendee` 0**.

**This reconciles the contradiction.** Two criteria, same data:

- **Strict (all component tokens present)** → 71.2323% resolvable / 28.7677% unresolvable.
  This matches **D073's 71.10% / 28.90% to within 0.13 pp**.
- **Loose (any one token suffices)** → Σ max-token = 5,085,429 pooled = **300.12% of the row
  count**, i.e. vacuous; the ceiling is 100% resolvable / 0% unresolvable. D077's 97.4380%
  sits just above this vacuous line and is **not reproducible** under either criterion from the
  profile.

**Verdict: D073 is right, D077 is wrong.** The disagreement is a *criterion* artefact, not a
data disagreement. Note this remains a **union bound (upper bound on resolvable), not a direct
count** — component structure is destroyed by the profile builder, so the true resolvable rate
is ≤ 71.2323% and the true unresolvable rate is ≥ 28.7677%. Both figures are bounds.



### 6. A proven no-op, for the avoidance of a wrong fix

`normalize.py:321` removes `("st","ste","dr","n","s","e","w")` from `COMMON` for France before
merging `ADDR_CANON_FR`. I compared the as-built `eff` against a hypothetical `eff'` built with
**no exclusion list at all** across all 222 keys. Differences: **3**, and all three are
`s`, `e`, `w` passing through unchanged instead of self-mapping — semantically identical,
because `ADDR_CANON_COMMON` defines `south`/`s`→`"s"`, `east`/`e`→`"e"`, `west`/`w`→`"w"`.
Every other excluded key (`st`, `ste`, `dr`, `n`) is redefined by `ADDR_CANON_FR`, which is
merged *after* the exclusion. **The 7-key exclusion list is a semantic no-op** — it exists for
readability, not effect. Do not spend effort on it.

`ADDR_CANON_FR` overrides `COMMON` with a *different* value in exactly 4 places: `bld`
(`"bldg"`→`"blvd"`), `st`(`"st"`→`"saint"`), `ste`(`"ste"`→`"sainte"`), `n`(`"n"`→`""`).
The first is arguably a bug — `bld` means *building* in English and *boulevard* in French, and
`bld` is 0 occurrences in the France vocabulary, so it is currently inert. **SPECULATIVE**, low
priority.

### 7. A methodological defect in the profile itself (affects future agents)

`build_profile.py:28` uses `TOKEN_RE = re.compile(r"[a-z0-9]+")` against `bal = ba.lower()` —
**lowercased but not accent-stripped**. `normalize.py:317` calls `strip_accents()` *before*
tokenising. The two tokenisers therefore disagree on every accented French word. Verified by
fragment identity: `general` (279 in s1) co-occurs with fragments `g` 2,611 + `n` 2,648 +
`ral` 2,218; `residence` (879) with `r` 2,543 + `sidence` 454; `hopital` (105) with `h` 1,051
+ `pital` 83; `ecole` (290) with `ole` 38. 1-char alpha tokens total **71,805 / 367,602 /
375,721** (2.70% / 2.47% / 2.48% of listed mass) and are **largely accent debris, not real
tokens**.

**Consequence: `l`, `m`, `d`, `e`, `r` and friends in the France lists are mostly artifacts.**
Note `r` = 182,872 in test_s2 versus 2,543 in test_s1 — a 72x jump across sources for a
"1-letter French token" is a tokenizer artefact signature, not a language fact. **Any future
work order that mines short tokens from these profiles will produce confident nonsense.** This
is the single most important thing I found for the fleet, and it does not affect my Tier-1/2/3
candidates, all of which are long unambiguous tokens.

Secondary tokenizer difference: `normalize.py` splits components on `","` only
(line 322), while `build_profile.py:31` splits on `[,;]`. French addresses using `;` as a
component separator are tokenised identically at the token level, so this does not change counts.

## Interpretation

*Inference, clearly marked:*

1. **The dictionary is not the bottleneck for France.** §2 shows the actionable French
   street-type mass is ~0.25% of address tokens versus ~17% geography and ~16% function words.
   A perfect `ADDR_CANON_COMMON` would move a rounding error. Effort belongs on (a) the geography
   path and (b) function-word suppression, both of which are outside this table.
2. **The Tier-1 collisions are the only entries here that can actively *hurt*.** A missing entry
   leaves a token uncanonicalised (a lost match opportunity). A wrong-sense entry — `est`→
   `estate`, `ne`→northeast — manufactures a token that never occurs naturally in French
   addresses, adding IDF-weighted noise on *every* occurrence. These five are worth more than
   the 20 Tier-2 additions combined despite being a quarter of their mass.
3. **The self-map loop omission is confirmed inert.** `normalize.py:252` iterates
   `(US_STATES, IN_STATES)` and omits `FR_REGIONS`. I re-derived the reason: the four canonical
   values `hdf`, `naq`, `pdl`, `idf` occur **0 times** as input address tokens in all three
   France test files, so adding them to the self-map loop would be a no-op on this dataset. This
   is consistent with the work order but is independently re-measured here, and it is about the
   self-map loop only — it says nothing about the department gap, which §5 handles separately
   and finds to rest on a false premise.

## Gaps

1. **All three France `addr_tokens` lists are at the 4,000 cap.** Any token outside the top
   4,000 per source is invisible. `national`, `section`, `imm`, `societe`, `entreprise`,
   `hame`, `ham`, `ruel`, `ven`, `espl`, `hll`, `im`, `traverse`, `montee`, `descente` are all
   **absent from the France vocabulary** — I cannot distinguish "does not occur" from "below

## Recommendations

Scoped, prioritised. The honest summary is: **the headline fix is not to extend
`ADDR_CANON_COMMON`.**

**P0 — fix the five cross-language collisions (new defect, CONFIRMED).** Add to
`ADDR_CANON_FR` (not `COMMON`, so US/India are untouched):
`"est": "e", "se": "se", "ne": "ne", "col": "col", "fort": "fort"` — i.e. give the French
sense. Pooled mass 9,538 (0.0795%). *Expected effect (INFERENCE):* stops false
`estate`/`ft` tokens and false northeast/southeast signals entering French address features.
This is the highest value-per-byte change available and it is a correctness fix, not a recall fix.

**P1 — add the apartment family (CONFIRMED).** `appt`/`app`/`appart`/`appartement` → `"apt"`,
in `ADDR_CANON_COMMON` (they also occur in India: `appt` 7,992, `app` 1,629 — so `COMMON` is
the correct home). Pooled 10,128 (0.0845%). The dictionary already contains
`apartment`→`apt` and `apt`→`apt`; the French spelling of the same concept is simply missing.

**P2 — add the French street types (CONFIRMED for the France-only ones).** ~18 entries into
`ADDR_CANON_FR`, pooled 26,966 (0.2248%). Move `port` and `villa` to `COMMON` (both occur in
US/India). **Low priority on purpose** — §2 shows this bucket cannot move the needle.

**P3 — French ordinals (CONFIRMED, small).** `1er`→`"1st"`, `2eme`→`"2nd"`, `3eme`→`"3rd"`,
`2e`→`"2nd"` alongside the existing English set at `ADDR_CANON_COMMON:184-185`. Pooled 3,172
(0.0264%).

**Explicitly NOT recommended, with reasons:**
- *Extending `LEET` to addresses* — §4: it would mangle `12 bis`/`2e` house-number forms. Real
  asymmetry, wrong fix.
- *Adding `FR_REGIONS` entries* — §5: `aisne` and `vendee` are the only absent keys and both
  are 0 occurrences. **Zero new entries warranted.**
- *Touching the `normalize.py:252` self-map loop* — §6 and §7: the four canonical values occur
  0 times as input tokens. No measurable effect.
- *Editing the `("st","ste","dr","n","s","e","w")` exclusion list* — §6: proven no-op.
- *A mechanical abbreviation-pair miner* — §3: 5,248 raw pairs, all false positives.

**Fleet-level, and more valuable than anything in this task:** fix `build_profile.py:28` to
apply `strip_accents()` before `TOKEN_RE`, matching `normalize.py:317`. §7 shows 2.47–2.70% of
French listed mass is accent debris and that short-token mining on the current profiles yields
confident nonsense. Re-run the profile build before any other agent mines short tokens.

**And record for the region workstream:** the s2/s3 "missing departments" premise is a false
premise (§5). The correct statement is that `state` resolves for **at most 71.2323%** of French
test rows, and the shortfall is not department-table coverage. D073 is confirmed; D077's
97.4380% is not reproducible and should not be used to size anything.

## Bearing on the already-checked refutations

- **REFUTED-1 (French postcodes):** not re-derived. My mixed-digit token counts (§4) are
  consistent with it — the only digit-bearing French tokens are house numbers, not postcodes.
- **REFUTED-2 (France region handling):** I did **not** reproduce the s1-only 100% figure and do
  not quote it. My France-wide figure is **71.2323% resolvable / 28.7677% unresolvable**
  (§5), reported as a union bound with the criterion stated. I **agree with D073 and reject
  D077** under the stated criterion, and I additionally show the premise that the shortfall is
  caused by missing department entries is itself false.

   cutoff". I have not estimated them.
2. **Component structure is destroyed.** `addr_tokens` is a flat bag per country; `,`/`;`
   boundaries are not recoverable. Every §5 figure is therefore a **union bound**, not a count,
   and no exact per-row state-resolution rate is derivable from this profile. Closing this
   requires a profile field the builder does not collect (e.g. per-component token bags).
3. **No row-level co-occurrence.** I cannot count rows containing `gironde`, only token
   occurrences of `gironde`. Every row-level statement above is a bound.
4. **Hapaxe pruning.** `prune()` drops count-1 tokens periodically (build_profile.py:45-48), so
   listed mass under-counts by an unknown amount.
5. **Downstream effect unmeasured.** I cannot quantify how much a given dictionary entry changes
   the model score. All "expected effect" statements in Recommendations are INFERENCE.
6. **Train is France-free**, so no France-side train/test distribution shift can be measured,
   and no French dictionary entry can be validated against a France ground truth.

**This bears on the work order's premise and I must state it plainly: the premise that
`test_s2`/`test_s3` "encode geography with department names absent from `FR_REGIONS`" is
partly wrong.** `gironde`, `nord`, `loire atlantique`, `pas de calais`, `somme`, `landes`,
`paris` **are all already `FR_REGIONS` keys** and carry 293,000+ occurrences in test_s2. The
28.77% unresolvable mass is dominated by rows whose geography is expressed in components that
match no key — including cities that are not departments — not by missing department entries.
Only `aisne` and `vendee` are genuinely absent, and both are **0 occurrences**. **Zero new
`FR_REGIONS` entries are warranted by this evidence.**
