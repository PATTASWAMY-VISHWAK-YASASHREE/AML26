# D125 — France `addr_tokens`: city and place-name coverage

> **Revision note.** A prior draft of this file existed. I re-derived every figure from the
> profile and found **three errors and one omission** in it, all corrected below and listed in
> §Corrections. The headline number (≈85 % top-10 concentration) survived; its *interpretation*
> did not.

## Headline

French place names are **not cleanly separable** from street words, and the top-30 unigram list is
a mixture of **five** vocabularies, not four: only **12 of the top 30 (40 %)** are places. City is
already an **unintentional blocking key** but **only ever in compound form** — `keys.py` has no key
kind that emits a lone address token — so "add city as a blocking key" is a **no-op, not a
recommendation**. The genuinely new defect is that **19 French canonical tokens are missing from
`ADDR_GENERIC`**, so 336,623 token occurrences leak into the key vocabulary — and the biggest
single new finding is that **French elision with a typographic apostrophe (U+2019) is not handled
at all**, splitting `l'Église` into two tokens where the ASCII form yields one.

## Scope, denominators and method

All figures come from `analysis_out/profile/test_s{1,2,3}.json`, fields `by_country.France.*` and
`addr_tokens.France`. No raw TSV was opened.

| source | France rows (`by_country.France.rows`) | share of all-France |
|---|---:|---:|
| test_s1 | 259,452 | 15.31 % |
| test_s2 | 703,378 | 41.51 % |
| test_s3 | 731,615 | 43.18 % |
| **total** | **1,694,445** | 100 % |

259,452 + 703,378 + 731,615 = 1,694,445. Sanity check passed: `sum(len_hist.values()) == rows` for
all three France slices (e.g. s1 = 259,452). `addr_tokens.France` is capped at `TOPN = 4000`
(`build_profile.py:27,140`) and pruned of `count == 1` every 8 chunks (`:45-48`), so it is a
truncated head. Listed mass: 2,253,877 (s1) + 4,745,780 (s2) + 4,993,261 (s3) = **11,992,918**
occurrences over **4,441** merged distinct tokens (3,519 retained in all three files).

### The unit error that invalidates most published "France %" figures — read this first

`addr_tokens` counts **token occurrences, not rows**. A row contributes one count per token
occurrence, so a multi-word place splits across two tokens, and a row containing a token twice is
counted twice. Therefore **`occurrences / rows` is occurrences per row — it is NOT a percentage of
rows**, and it can exceed 100 %.

This is not pedantry. Three concrete cases in this very analysis:

* `de` alone is 1,050,023 occurrences = **61.98 per 100 French rows**, not "62 % of rows".
* The `s1` region-head rate computes to **100.15 per 100 rows**, which looks like an impossible
  error but is simply a token-occurrence rate (a row may carry two region tokens).
* Defect 2's "19.87 %" is **19.87 occurrences per 100 rows**, and a single row can contribute
  several of the leakers.

The profile has **no field mapping a token back to a row**, and **no field recording which
comma-separated component a token came from** (`build_profile.py:126-127` pools all components
into one counter). Every rate below is therefore stated as *occurrences per 100 rows* and labelled
as a bound. The established row-level figure of **84.58 %** (`analyse_france.py`, from raw data)
is the only true row-fraction available, and it is used below purely as a cross-check.

## (a) Top places and their shares

The raw top-30 merged unigrams classified by hand — **five** vocabularies:

| class | tokens | occurrences | % of top-30 mass |
|---|---|---:|---:|
| place | bordeaux, nantes, lille, saint, calais, tourcoing, dunkerque, roubaix, nazaire, pessac, buch, teste | 1,656,926 | 23.4 % |
| function word | de, la, du, des | 1,950,792 | 27.6 % |
| region | loire, france, hauts, nouvelle, aquitaine, pays | 1,609,953 | 22.7 % |
| street type | rue, avenue | 855,080 | 12.1 % |
| abbreviation | r, n | 474,648 | 6.7 % |
| department | nord, gironde, atlantique | 431,146 | 6.1 % |
| fragment | l | 99,889 | 1.4 % |
| **total** | 30 | **7,078,434** | 100 % |

(Percentages are of top-30 mass, not of all mass. **Correction:** the prior draft classed `r`, `n`
and `l` together as "fragment". `r` and `n` are **not** fragments — see §Corrections.)

**Merged top-10 distinct places**, using `min` over a multi-word place's constituent tokens (the
generic component is shared with other places, so `min` is the conservative proxy):

| # | place | proxy | occurrences | s1 | s2 | s3 | occ/100 rows |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | Bordeaux | `bordeaux` | 277,474 | 43,634 | 114,608 | 119,232 | 16.376 |
| 2 | Nantes | `nantes` | 238,748 | 37,624 | 98,429 | 102,695 | 14.090 |
| 3 | Lille | `lille` | 221,585 | 34,931 | 91,622 | 95,032 | 13.077 |
| 4 | Calais | `calais` | 128,762 | 15,967 | 55,273 | 57,522 | 7.599 |
| 5 | Tourcoing | `tourcoing` | 115,914 | 18,284 | 47,908 | 49,722 | 6.841 |
| 6 | Dunkerque | `dunkerque` | 111,538 | 17,582 | 45,959 | 47,997 | 6.583 |
| 7 | Roubaix | `roubaix` | 107,111 | 16,827 | 44,317 | 45,967 | 6.321 |
| 8 | Saint-Nazaire | `nazaire` | 88,016 | 13,864 | 36,278 | 37,874 | 5.194 |
| 9 | Pessac | `pessac` | 81,815 | 12,837 | 33,729 | 35,249 | 4.828 |
| 10 | La Teste-de-Buch | `teste` | 72,268 | 11,381 | 29,862 | 31,025 | 4.265 |

Arithmetic: 277,474 / 1,694,445 = 16.376 occurrences per 100 rows. Per-source column, e.g.
Bordeaux s1 = 43,634 / 259,452 = 16.814.

Ranks 11–15: Cap-Ferret (`cap` 61,600), Pornic 50,117, Saint-Herblain 44,846, Le Boucau (`baule`)
44,231, Villenave-d'Ornon (`escoublac`) 44,201.

**`saint` is not a place count.** It has 141,364 occurrences (8.343 per 100 rows), far above
`nazaire` 88,016, because it is simultaneously a commune prefix, a street element (Rue
Saint-Martin) and part of Saint-Herblain. This is why the naive sum (1,515,562) overstates the
top-10 total and the min-token proxy is used. **CONFIRMED**, and unrecoverable from the profile
(gap 6).

## (b) Share of French rows inside the top 10 places

Summed min-token proxy over the ten places above:
277,474 + 238,748 + 221,585 + 128,762 + 115,914 + 111,538 + 107,111 + 88,016 + 81,815 + 72,268
= **1,443,231** occurrences.

**1,443,231 / 1,694,445 = 85.174 occurrences per 100 rows.**

**This is an UPPER BOUND on the row share, not an estimate of it.** *Correction: the prior draft
stated the residual "at most 251,214 rows (14.825 %) sit outside the top 10" and called it "an
upper bound; the true figure is somewhat lower" — the direction is backwards.* Because a row
contributes ≥ 1 occurrence when it contains the place, occurrences ≥ rows, so:

* rows **inside** top 10 **≤ 1,443,231** (85.174 %)
* rows **outside** top 10 **≥ 251,214** (14.826 %)

Per source, each with its own denominator (never mixed):

| source | top-10 occurrences | France rows | occ/100 rows (upper bound) |
|---|---:|---:|---:|
| test_s1 | 222,931 | 259,452 | 85.924 |
| test_s2 | 597,985 | 703,378 | 85.016 |
| test_s3 | 622,315 | 731,615 | 85.060 |

Stable to within 0.9 pp across all three sources, so this is a property of the French data, not of
one source's formatting. **Cross-check against the established row-level 84.58 %** from
`analyse_france.py`: 84.58 ≤ 85.174, so the bound is satisfied and the true row share lies between
the two. The prior draft's residual direction would have implied ≥ 14.825 % outside, which the
independent row-level work (≤ 15.42 % outside) also permits — but the *stated inequality* was
wrong and would mislead anyone sizing a tail-handling fix.

The three metro areas behind it are Bordeaux (Nouvelle-Aquitaine), Nantes (Pays de la Loire) and
Lille/Roubaix/Tourcoing/Dunkerque/Calais (Hauts-de-France) — which is also why only three regions
and three departments dominate.

## (c) Are places cleanly separable from street words?

**No — not from the profile, and only partially in the pipeline.**

1. **The profile destroys component identity.** `build_profile.py:126-127` splits on `[,;]` then
   pools every component into one counter per country. Component index is discarded. The work
   order's `{axis}` framing and the "region before or after city" ordering question are
   **unanswerable** from this profile. Hard gap, not an inference.
2. **The profile tokeniser shatters accented place names.** `TOKEN_RE = [a-z0-9]+`
   (`build_profile.py:28`) does not strip accents, so `Mérignac` → `m` + `rignac` and
   `Lège-Cap-Ferret` → `l` + `ge` + `cap` + `ferret`. Evidence in 3 of 3 files: `rignac` 51,156
   vs `merignac` 14,416 (3.5×); `ge` 41,120 vs `lege` 11,261 (3.6×); and `merignac`/`lege` are
   **exactly 0 in s1**, so s1 writes them accented while s2/s3 split. **This is an artefact of the
   profile builder, not a pipeline defect** — `normalize.py:317` calls `strip_accents()`, verified:
   `'175 Rue de la Mérignac, Mérignac'` → `['175','rue','de','la','merignac','merignac']`.
3. **In the pipeline separation exists but is untestable here.** `normalize.py:322-352` splits on
   `,` and builds `city_comps`, shipped as `acity` by `prep.py:17` and consumed by
   `features.py:87-90`. But `city_comps` collects **every digit-free component**, verified:
   `'45 Rue de l'Église, Tourcoing'` → `city_comps = ['rue de l eglise', 'tourcoing']`, so the
   street component is also labelled a city. The profile cannot measure how often that misfires.
4. **Street-type words are canonically mapped and largely suppressed** — this part works.
   `rue` 728,583, `avenue` 126,497, `boulevard` 38,275 all reach canonical forms present in
   `ADDR_GENERIC`, and `keys.py:39` drops `ADDR_GENERIC` tokens before key generation.

## NEW DEFECT: typographic apostrophe (U+2019) splits French elisions

`normalize.py:342` does `_non_alnum.split(c.replace("'", ""))` — it strips the **ASCII**
apostrophe only. The typographic apostrophe U+2019 is left in place, and
`_non_alnum = [^a-z0-9]+` (`normalize.py:269`) then treats it as a separator:

| input | tokens |
|---|---|
| `45 Rue de l'Eglise, Tourcoing` (ASCII U+0027) | `['45','rue','de','leglise','tourcoing']` |
| `45 Rue de l'Église, Tourcoing` (U+2019) | `['45','rue','de','l','eglise','tourcoing']` |

The same address therefore yields **two different token vectors**, and in the U+2019 form a
meaningless one-character token `l` is emitted. `normalize_name` (`:273`) has the same blind spot
for `’` in business names.

This is a **plausible high-volume mechanism** for much of the profile's junk single-char unigram
mass, and it is **French-specific** — elision (`l'`, `d'`, `qu'`, `n'`, `c'`, `j'`) is exactly where
U+2019 appears. Supporting profile evidence: `l` 99,889 occurrences and `ge` 41,120 are both large,
and `l − ge = 58,769` occurrences of `l` cannot be explained by `Lège` alone.
**Marked LIKELY, not CONFIRMED**: I cannot prove the source text uses U+2019 rather than ASCII,
because the profile tokeniser discards the character. Confirming it needs one grep over the raw
addresses, which this machine cannot do.

Impact *if* real: `l`, `d`, `c`, `j`, `qu` are all < 3 chars and are dropped by the `len >= 3`
filter at `keys.py:42`, so the **blocking-key** impact is limited; the cost lands on the
IDF-weighted **features** path (`features.py:120-123`) instead. Priority: **MEDIUM**.

## (d) Blocking collisions — and the defects this surfaced

### DEFECT 1: s1 and s2/s3 use different address vocabularies

Region/department head tokens, as occurrences per 100 rows of each source's France rows:

| token | s1 | s2 | s3 |
|---|---:|---:|---:|
| `hauts` (Hauts-de-France) | 39.205 | 12.585 | 13.589 |
| `nouvelle` (Nouvelle-Aquitaine) | 32.881 | 10.576 | 11.358 |
| `pays` (Pays de la Loire) | 28.064 | 8.969 | 9.773 |
| **region heads subtotal** | **100.15** | **32.13** | **34.72** |
| `nord` (Nord) | 0.077 | **10.714** | **10.449** |
| `gironde` (Gironde) | 0.024 | **10.678** | **10.336** |
| `atlantique` (Loire-Atlantique) | 0.098 | **9.056** | **8.802** |
| **department heads subtotal** | **0.20** | **30.45** | **29.59** |

s1 is **504.5×** more region-flavoured (259,840 / 515 occurrences); s2 and s3 are ~1 : 1. s2/s3
also *mix* both conventions inside the same file. This independently corroborates the re-scoped
REFUTED-2.

My component-level ceiling on rows whose address contains a resolvable region-or-department token:

| source | region comps | dept comps | total | occ/100 rows |
|---|---:|---:|---:|---:|
| s1 | 259,840 | 515 | 260,355 | 100.35 |
| s2 | 225,997 | 214,163 | 440,160 | 62.58 |
| s3 | 254,016 | 216,468 | 470,484 | 64.31 |
| **total** | | | **1,170,999** | **69.11** |

My 69.11 sits just under the work order's independent 71.10 (1,204,739 / 1,694,445); the residual
is explained by my count omitting `pas de calais` (`pas` 29,032 occurrences) and `loire
atlantique` spelled whole, both of which *are* in `FR_REGIONS`. **The "100 % of France" figure is a
test_source1-only artefact and s1 is 15.31 % of French rows.** Note `FR_REGIONS` is *not* the
bottleneck for the three department names — `nord`, `gironde`, `loire atlantique`, `pas de calais`
are all present at `normalize.py:244-247`. The bottleneck is rows carrying no mappable component.

### DEFECT 2: 19 French canonical tokens leak into the blocking keys

`keys.token_lists` builds `alph` from address tokens **not** in `ADDR_GENERIC` (`keys.py:39`),
keeps those of length ≥ 3, sorts **longest-first**, `head(9)` (`keys.py:42-43`).
`ADDR_CANON_FR` (`normalize.py:199-214`) emits 19 canonical values **absent** from `ADDR_GENERIC`
— verified by importing both dictionaries and taking
`set(ADDR_CANON_FR.values()) - set(ADDR_GENERIC)`:

`bat, bis, crs, fbg, gen, lieu, lieudit, mal, pres, prof, quai, res, rte, saint, sainte, za, zac, zi, zone`

All 19 are ≥ 3 chars **or** have zero measured mass (`za`, `zi` are 2 chars but never occur), so
all 336,623 occurrences are eligible to reach `alph`:

| canonical | surface spellings | occurrences | occ/100 rows |
|---|---|---:|---:|
| `saint` | saint, st | 166,818 | 9.845 |
| `bis` | bis, b | 69,757 | 4.117 |
| `rte` | rte, route, rt | 29,927 | 1.766 |
| `crs` | crs, cours | 13,281 | 0.784 |
| `res` | res, residence | 13,088 | 0.772 |
| `quai` | quai, q, qu | 13,004 | 0.767 |
| `sainte` | sainte, ste | 8,077 | 0.477 |
| `gen` | gen, general, gal | 6,078 | 0.359 |
| `mal` | mal, marechal | 4,730 | 0.279 |
| `bat` | bat, batiment | 3,745 | 0.221 |
| `fbg` | fbg, faubourg, fg | 3,046 | 0.180 |
| `prof` | prof, professeur | 2,485 | 0.147 |
| `pres` | pres, president | 2,380 | 0.140 |
| `lieu` / `zone` | — | 207 | 0.012 |
| **total** | | **336,623** | **19.866** |

The two worst offenders are pure street grammar: **`saint`** (a saint-prefix on thousands of
unrelated streets and communes) and **`bis`** (the house-number suffix in "5 bis"). Verified
end-to-end: `normalize_address('5 Rue des Lilas, Saint-Nazaire')` →
`toks = ['5','rue','des','lilas','saint','nazaire']` → `alph = ['nazaire','lilas','saint']`.

**Mitigating factor, stated honestly:** `alph` is longest-first, so the 3-char leakers are pushed
down and only make the cut when the address yields fewer than 9 longer tokens. `saint` (5 chars) is
the one that genuinely competes. The leak dilutes rather than dominates.

### DEFECT 3: street-type abbreviations differ sharply by source

rate = abbr / (full + abbr), within one source:

| street type | full | abbrev | s1 | s2 | s3 |
|---|---|---|---:|---:|---:|
| rue | `rue` | `r` | 1.5 % | **40.4 %** | **38.8 %** |
| avenue | `avenue` | `av` | 6.7 % | **37.5 %** | **35.7 %** |
| boulevard | `boulevard` | `bd` | 17.4 % | **45.3 %** | **44.0 %** |
| place | `place` | `pl` | 23.2 % | **55.4 %** | **53.3 %** |
| chemin | `chemin` | `ch` | 25.2 % | **50.9 %** | **49.0 %** |
| impasse | `impasse` | `imp` | 4.1 % | **43.7 %** | **42.2 %** |
| route | `route` | `rte` | 8.2 % | **46.9 %** | **45.5 %** |
| cours | `cours` | `crs` | 0.0 % | **41.6 %** | **39.9 %** |
| quai | `quai` | `q` | 1.7 % | **41.7 %** | **40.4 %** |

`ADDR_CANON_FR` maps both spellings to the same canonical value, so this is **not a matching
bug** — it is a *volume* fact that explains why the s2/s3 unigram `r` is 182,872 against s1's
2,543, and it means any s1-tuned threshold is mis-set for 84.7 % of French rows.

### Is city already a blocking key? Yes — but only in compound form

Verified by running `keys.token_lists` and `keys.make_keys` on real French addresses:

| address | resulting `alph` |
|---|---|
| `175 Boulevard du President Franklin Roosevelt, Bordeaux` | `['roosevelt','franklin','bordeaux','pres']` |
| `45 Rue de l'Abbé de l'Epée, Tourcoing` | `['tourcoing','abbe','epee']` |
| `12 Rue Dunkerque, Lille` | `['dunkerque','lille']` |

City names are ≥ 5 chars, are not in `ADDR_GENERIC`, and are therefore **sorted to the front of
`alph`** by the longest-first rule. Row 3 is the key evidence for (c): `Dunkerque` (a street) and
`Lille` (the city) are **indistinguishable to the key builder**.

**Correction to the prior draft:** it asserted "a bare city key would be dropped outright —
1,454× over cap", implying a key kind that emits a lone city token. **No such key kind exists.**
Inspecting `keys.py:56-73`, the five kinds are: 0 NA = name-token × addr-token, 1 NN = name-token
pair, 2 AA = num × addr-token and addr-token × addr-token, 3 F = full name, 4 T = single **name**
token. A run of `make_keys` over 4 French rows returned kinds `{0: 16, 2: 24, 3: 4, 4: 4}` — no
singleton-address-token kind. City therefore only ever enters **compound** keys, and the cap
arithmetic must be done on those compounds, not on the bare token.

### Should city be a blocking key? No — and the caps answer it

Redoing the cap arithmetic on the **s1 index** (which is what `S1_MAXCAP` actually governs;
`blocking.py:13,16`) and on the **compound** keys that really exist:

* `CAPS = {0:50, 1:50, 2:30, 3:50, 4:20}`, `S1_MAXCAP = 300` (`keys.py:23-26`).
* The AA (kind 2) cap is **30**; `df > 30` keys are dropped at query time (`blocking.py:34`), and
  `df > 300` keys never enter the s1 index at all (`blocking.py:13`).
* A bare city token in s1: Bordeaux 43,634 = 145.4× `S1_MAXCAP`; Nantes 37,624 = 125.4×; Lille
  34,931 = 116.4×. All far over.
* The realistic compound is `(house_number, city)`. **Correction:** the prior draft computed this
  over *all three* sources (518 distinct numbers, 1,567,275 numeric mass, 277,474 Bordeaux
  occurrences → 535.7/cell → 17.9× cap), mixing an all-source numerator with an s1-only cap.
  Corrected to **s1 only**, where the cap applies: **373** distinct numeric tokens, mass 258,867,
  median 128 per distinct number. Bordeaux s1 = 43,634 / 373 = **117.0 per cell = 3.9× the cap of
  30**. Under a uniform-spread assumption the typical `(num, city)` cell is *still* above cap, but
  the margin is 3.9×, not 17.9× — and 223 of the 373 numbers occur ≤ 200 times, so many cells
  could be sub-cap. **The profile cannot settle this** (gap 2).

**Conclusion (inference, arithmetically grounded):** the caps already perform the collision
suppression a hand-rolled city block would be added to do, and since no bare-city key kind exists,
adding city as an explicit blocking key is a **no-op at best** and reintroduces non-selectivity at
worst. This is the one place where the honest recommendation is **no change**. The residual risk is
not collisions but **budget dilution**: city tokens and the 19 Defect-2 leakers compete for the
same 9 `alph` slots, longest-first.

## Interpretation (clearly marked as inference)

1. *Inference.* With ~85 % of French rows inside 10 places, France is effectively **three
   metro-areas**, not one country. A retrieval design tuned on 85 %-concentrated data will look
   fine on French validation and fail on any fourth cluster.
2. *Inference.* Because s1 and s2/s3 disagree on region-vs-department **and** on abbreviation rate,
   any French threshold or dictionary tuned on s1 alone is mis-calibrated for 84.7 % of French rows.
   This is the most actionable structural fact here.
3. *Inference.* The `saint`/`bis` leak is a precision loss in `alph`; because `alph` is
   longest-first and both are short, expect a measurable recall gain, not a step change.
4. *Inference.* City-as-blocking-key is already answered by the code structure: the caps make it
   inoperative. The genuine lever is the `alph` slot budget, not the key set.
5. *Inference.* If the U+2019 finding is real, the cost lands on the IDF feature path rather than
   the key path, so it would show up as diffuse scoring noise rather than blocking misses.

## Gaps (fields not collected — no estimates substituted)

1. **No component/axis field.** Tokens are pooled across comma-separated components
   (`build_profile.py:126-127`). Any question about *which component* a token came from —
   including the work order's `{axis}` framing and the region-before-or-after-city ordering
   question — is **unanswerable** from this profile.
2. **No row-level co-occurrence.** The `(number, city)` cell sizes in §(d) are *inferred* from
   marginals under a uniform-spread assumption, not measured. A true contingency table would
   settle the AA-cap arithmetic exactly.
3. **No `alph`-occupancy histogram.** The profile cannot say how many `alph` tokens a typical
   French address yields, so the "dilution" magnitude in Defect 2 is unquantified.
4. **No distinct-city count.** The vocabulary is truncated at 4,000 tokens per source, so the true
   number of distinct French places is unknown; the 5,960 figure in the work order came from a
   different tool and is not reproducible here.
5. **Accent folding is a profile artefact.** `rignac`/`merignac` are the *same* place under two
   spellings and cannot be summed naively; the true split is unrecoverable from the profile.
6. **`saint` is not separable from a place** — place prefix, street element and commune prefix
   simultaneously. No way to apportion its 141,364 occurrences.
7. **U+2019 prevalence is unknown.** The profile tokeniser discards the apostrophe character, so
   the elision-splitting defect is confirmed in the *code* but unquantified in the *data*.

## Recommendations (prioritised)

1. **HIGH — add the 19 missing French canonical forms to `ADDR_GENERIC` in `_upstream/src/keys.py`.**
   Add `saint, sainte, bis, rte, crs, quai, res, gen, mal, bat, fbg, prof, pres, lieu, lieudit,
   zone, za, zi, zac`. A one-line-list change, provably safe (all are street/building grammar,
   never business-identifying), removing 336,623 occurrences — 19.866 per 100 French rows — from
   the key vocabulary and freeing `alph` slots. **CONFIRMED** by the profile.
2. **HIGH — do not tune any French threshold or dictionary on `test_source1` alone.** s1 is 15.31 %
   of French rows and uses a different address convention (regions, 1.5 % `r` abbreviation) from
   s2/s3 (departments, ~40 % `r`). **CONFIRMED.**
3. **MEDIUM — normalise U+2019/U+02BC to ASCII `'` in `normalize.py`** before the apostrophe
   strip at line 342, and likewise at line 273 in `normalize_name`. One-line change, makes French
   elision tokenise identically regardless of apostrophe style. **LIKELY** — code defect
   CONFIRMED, data prevalence UNVERIFIED (gap 7). Expected effect: removes spurious 1-char tokens
   from the IDF feature path; blocking-key effect is small because `keys.py:42` already drops
   tokens < 3 chars.
4. **MEDIUM — reconcile the region-resolvability contradiction (2.56 % vs 28.90 % unresolvable) and
   add the remaining modern French region names to `FR_REGIONS`.** My ceiling is 69.11 %, the work
   order's is 71.10 %; the gap is rows carrying no region *or* department component at all. The
   *legacy* names are **not** where it lives: Bretagne 1,262, Alsace 1,813, Lorraine 1,948,
   Bourgogne 713, Normandie 756, Champagne 195, Auvergne 520, Midi 392, Centre 967, Martinique
   414, Picardie 215, Poitou 96, Provence 291, Franche-Comté 418 = **10,000 occurrences = 0.590
   per 100 rows**. **LIKELY** for the cause, **CONFIRMED** for the legacy size.
5. **LOW / NO CHANGE — do not add city as a blocking key.** No bare-city key kind exists, and the
   `df` caps already drop the city-bearing compound keys. State this explicitly so no one
   "fixes" it later.
6. **NO CHANGE — the s1/s2/s3 abbreviation split is not a matching bug.** `ADDR_CANON_FR` maps both
   spellings to the same canonical token; verified end-to-end. It matters for threshold calibration
   (rec 2), not token identity.
7. **NO CHANGE — accent handling in the pipeline.** `normalize.py:317` `strip_accents()` correctly
   folds `Mérignac → merignac`, `Lège-Cap-Ferret → lege cap ferret`. The `m`/`rignac` and `l`/`ge`
   fragmentation is an artefact of `build_profile.py`'s `TOKEN_RE`, not a pipeline defect. If the
   profile is ever rebuilt, `TOKEN_RE` should strip accents first — otherwise every future agent
   will re-derive this false trail. (Note: stripping accents in the profile would also mask the
   U+2019 defect, so the two profile fixes should be considered together.)

## Corrections to the prior draft of this file

| # | Prior claim | Status | Correction |
|---|---|---|---|
| 1 | "at most 251,214 rows (14.825 %) sit outside the top 10… an upper bound" | **wrong direction** | Occurrences ≥ rows, so outside is a **lower** bound (≥ 251,214) and inside an **upper** bound (≤ 85.174 %). |
| 2 | "A bare city key would be dropped outright — 1,454× over cap" | **no such key kind** | `keys.py:56-73` emits no singleton-address-token kind; city appears only in compound keys. Cap arithmetic redone on compounds. |
| 3 | `(num, city)` = 535.7/cell = 17.9× cap, from 518 numbers / 277,474 Bordeaux | **mixed denominators** | The cap governs the **s1 index**. s1-only: 373 numbers, 43,634 Bordeaux → 117.0/cell = **3.9×**, and 223 numbers occur ≤ 200×. |
| 4 | `r`, `n`, `l` all "fragments" from accent shattering | **partly wrong** | `r` is overwhelmingly the *rue* abbreviation: 365,681 of 368,224 (99.31 %) is in s2/s3 where the abbrev rate is ~40 %; s1 has only 2,543 against `rue` 170,819. Same for `n` (97.51 % in s2/s3). Only `l` is a fragment. |
| 5 | (omission) | **new finding** | U+2019 typographic apostrophe is not handled in `normalize.py:342`/`:273`, splitting `l'Église` into `l` + `eglise`. |
| 6 | legacy regions "14,253 occurrences = 0.84 %" | **arithmetic** | Recount excluding `aquitaine` (part of *nouvelle aquitaine*, not legacy) gives **10,000 = 0.590**. Same qualitative conclusion. |

Unchanged and re-verified: France row counts and shares; the top-10 place table and the 85.174
figure; the region/department split and 504.5× ratio; the 19 Defect-2 leakers and 336,623 total;
all nine abbreviation rates; the resolvable ceiling 1,170,999 = 69.11 %; and the conclusion that
region handling is **not** settled.

## Explicit statement on the two `already_checked` items

* **REFUTED-1 (France postal-code loss).** Not re-derived, and nothing here bears on it. For the
  record my s1 figures are consistent: `dig5` = 1,082 and `dig6` = 34 over 259,452 s1 France rows.
  The top-30 addr list is dominated by house numbers (1 = 8,195 … 17 = 4,277), confirming French
  addresses carry numbers but not postcodes.
* **REFUTED-2 (France region claim).** **Re-scoping confirmed, with numbers.** The "100 %" is a
  `test_source1`-only denominator. My independent component-level ceiling is **69.11 %** across all
  three sources vs the work order's 71.10 %; both agree the s1 figure does not generalise. I also
  identify the mechanism: s1 writes regions (100.15 occ/100 rows) while s2/s3 write departments
  (30.45 / 29.59), and ~31 % of French rows carry neither. French geography is **not** settled.

---

## Scope, denominators and method

Everything below is computed from `analysis_out/profile/test_s{1,2,3}.json`, fields
`by_country.France.*` and `addr_tokens.France`. No raw TSV was opened.

France rows (profile field `by_country.France.rows`):

| source | France rows | share of all-France |
|---|---:|---:|
| test_s1 | 259,452 | 15.31 % |
| test_s2 | 703,378 | 41.51 % |
| test_s3 | 731,615 | 43.18 % |
| **total** | **1,694,445** | 100 % |

Arithmetic: 259,452 + 703,378 + 731,615 = 1,694,445.

`addr_tokens.France` is capped at `TOPN = 4000` per source (`build_profile.py:27,140`) and is
pruned of `count == 1` tokens every 8 chunks (`build_profile.py:45-48,128-133`), so it is a
**truncated head, not the full vocabulary**. Listed mass (sum of the retained counts):
2,253,877 (s1) + 4,745,780 (s2) + 4,993,261 (s3) = **11,992,918**.

**Arithmetic invariant verified.** `sum(by_country[c].len_hist.values()) == by_country[c].rows`
holds for all 9 country×source slices of the test split, France included (e.g. s1 France
142,909+102,124+11,627+2,719+72+1 = 259,452). The profile is internally consistent.

### One methodological warning that shapes every number below

`addr_tokens` counts **token occurrences, not rows**. A row contributes one count per token
occurrence, so a place whose name is written with two words contributes to both tokens, and a row
containing the place twice is counted twice. **The profile has no field that maps a token back to
a row, and no field that records which component a token came from.** Consequently:

* "share of rows" figures below are **proxies**, explicitly labelled.
* Shares of *listed mass* are upper bounds on the true share of total address-token mass, because
  the 4,000-token truncation discards the tail.

I flag every place where this bites rather than papering over it.

---

## (a) The exact top places and their shares

The raw top-30 of the merged `addr_tokens.France` head is **not** a place list. Classifying each
of the top 30 by hand:

| class | tokens | count |
|---|---|---:|
| place | bordeaux, nantes, lille, saint, calais, tourcoing, dunkerque, roubaix, nazaire, pessac, buch, teste | 12 |
| region / department | loire, france, hauts, nouvelle, aquitaine, pays, nord, gironde, atlantique | 9 |
| function word | de, la, du, des | 4 |
| street type | rue, avenue | 2 |
| fragment | r, n, l | 3 |
| **total** | | **30** |

So **only 12 of the top 30 unigrams (40 %) are places.** The work order's premise that the
"French city distribution" is top-10 concentrated is correct, but the top-30 *unigram* list is a
mixture of four vocabularies.

**Merged top-10 distinct places.** For a multi-word place I use the count of its most specific
token as a proxy for its row count (`min` over the constituent tokens), because the generic
component is shared with other places.

| # | place | proxy token(s) | combined | s1 | s2 | s3 | % of all France rows |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | Bordeaux | `bordeaux` | 277,474 | 43,634 | 114,608 | 119,232 | 16.376 % |
| 2 | Nantes | `nantes` | 238,748 | 37,624 | 98,429 | 102,695 | 14.090 % |
| 3 | Lille | `lille` | 221,585 | 34,931 | 91,622 | 95,032 | 13.077 % |
| 4 | Calais | `calais` | 128,762 | 15,967 | 55,273 | 57,522 | 7.599 % |
| 5 | Tourcoing | `tourcoing` | 115,914 | 18,284 | 47,908 | 49,722 | 6.841 % |
| 6 | Dunkerque | `dunkerque` | 111,538 | 17,582 | 45,959 | 47,997 | 6.583 % |
| 7 | Roubaix | `roubaix` | 107,111 | 16,827 | 44,317 | 45,967 | 6.321 % |
| 8 | Saint-Nazaire | `nazaire` | 88,016 | 13,864 | 36,278 | 37,874 | 5.194 % |
| 9 | Pessac | `pessac` | 81,815 | 12,837 | 33,729 | 35,249 | 4.828 % |
| 10 | La Teste-de-Buch | `teste`/`buch` (min) | 72,268 | 11,381 | 29,862 | 31,025 | 4.265 % |

Percentages are `combined / 1,694,445`. Example: 277,474 / 1,694,445 = 16.376 %.

Ranks 11–15, for completeness: Cap-Ferret (`cap` 61,600 / 3.635 %), Mérignac
(`merignac` 14,416 unaccented **plus** `rignac` 51,156 from the accented spelling — 0.851 % +
3.019 %), Pornic 50,117 (2.958 %), Saint-Herblain 44,846 (2.647 %), Le Boucau 44,231 (2.610 %).

**Note on `saint`.** `saint` has 141,364 occurrences (8.343 % of France rows), far more than
`nazaire` (88,016). The excess is *other* Saint-names and saint-bearing street names
(Saint-Herblain, Rue Saint-Martin). This is exactly why the naive sum
(1,656,926 = 97.786 %) is wrong and the min-token proxy is used instead.

---


## (b) Share of French rows inside the top 10 places

**Headline: ≈ 85.17 % of all French test rows carry one of the top-10 place tokens.**

Arithmetic (min-token proxy, summed over the 10 places above):
277,474 + 238,748 + 221,585 + 128,762 + 115,914 + 111,538 + 107,111 + 88,016 + 81,815 + 72,268
= **1,443,231**; 1,443,231 / 1,694,445 = **85.175 %**.

Per source, with each source's own denominator (never mixing them):

| source | top-10 proxy | France rows | share |
|---|---:|---:|---:|
| test_s1 | 222,931 | 259,452 | **85.924 %** |
| test_s2 | 597,985 | 703,378 | **85.016 %** |
| test_s3 | 622,315 | 731,615 | **85.060 %** |

The concentration is **stable to within 0.9 pp across all three sources**, so this is a property of
the French data, not of one source's formatting. The three metro areas behind it are
Bordeaux (Nouvelle-Aquitaine), Nantes (Pays de la Loire) and Lille/Roubaix/Tourcoing/Dunkerque/
Calais (Hauts-de-France) — which is also why only three regions and three departments dominate.

Residual: at most 1,694,445 ≈ 1,443,231 = **251,214 rows (14.825 %)** sit outside the top 10.
This is an upper bound; the true figure is somewhat lower because the proxy counts
token occurrences, not rows.

---

## (c) Are places cleanly separable from street words?

**No — not from the profile, and only partially in the pipeline.** Three separate reasons:

1. **The profile destroys component identity.** `build_profile.py:126-127` splits the address on
   `[,;]` and then tokenises each component, but updates **one pooled counter per country**:
   `at.update(TOKEN_RE.findall(comp))`. Component index is discarded. The work order asks about
   the `{axis}`/component structure; **the profile has no axis and no component field at all.**
   This is a hard gap, not an inference.

2. **The profile tokenizer shatters accented place names.** `TOKEN_RE = [a-z0-9]+`
   (`build_profile.py:28`) does **not** strip accents, so `Mérignac` is counted as `m` + `rignac`
   and `Lège-Cap-Ferret` as `l` + `ge` + `cap` + `ferret`. Evidence: `rignac` 51,156 vs
   `merignac` 14,416 (3.5×), and `ge` 41,120 vs `lege` 11,261 (3.6×) — in 3 of 3 files. This
   produces the junk unigrams `r` (368,224), `n` (106,424), `l` (99,889), `m` (56,527),
   `d` (50,816), `e` (45,410), which together are 33.907 % of the top-30 mass.
   **This is an artefact of the profile builder, not a pipeline defect** — `normalize.py:317`
   calls `strip_accents()`, verified: `'175 Rue de la Mérignac, Mérignac'` →
   `['175','rue','de','la','merignac','merignac']`. Anyone reading these tokens as evidence of
   upstream tokenisation would be wrong.

3. **In the pipeline, separation exists but is untestable from the profile.**
   `normalize.py:322-352` does split on `,` and builds `city_comps`, and `prep.py:17` ships it as
   `acity`, consumed by `features.py:87-90` (`city_tset`, `city_last`). So the *pipeline* does
   distinguish city from street. But `city_comps` is populated for **every** digit-free component
   (verified: `'...Bretagne'` also lands in `city_comps`), and the profile cannot tell us how
   often that misfires.

**Separable in one narrow sense:** street-type words *are* canonically mapped and largely
suppressed. `rue` 728,583, `avenue` 126,497, `boulevard` 38,275, plus `impasse`/`imp`,
`chemin`/`ch`, `place`/`pl` all map to canonical forms that **are** in `ADDR_GENERIC` and are
therefore dropped before key generation. That part works.

---

## (d) Blocking collisions — and the two NEW defects this surfaced

### DEFECT 1 (NEW, high value): s1 and s2/s3 use different address vocabularies

This is previously unremarked and it is large. Region/department head tokens, as a percentage of
each source's France rows:

| token | s1 | s2 | s3 |
|---|---:|---:|---:|
| `hauts` (Hauts-de-France) | 39.205 % | 12.585 % | 13.589 % |
| `nouvelle` (Nouvelle-Aquitaine) | 32.881 % | 10.576 % | 11.358 % |
| `pays` (Pays de la Loire) | 28.064 % | 8.969 % | 9.773 % |
| **region heads subtotal** | **100.15 %** | **32.13 %** | **34.72 %** |
| `nord` (Nord) | 0.077 % | **10.714 %** | **10.449 %** |
| `gironde` (Gironde) | 0.024 % | **10.678 %** | **10.336 %** |
| `atlantique` (Loire-Atlantique) | 0.098 % | **9.056 %** | **8.802 %** |
| **department heads subtotal** | **0.20 %** | **30.45 %** | **29.59 %** |

s1 is **504.5×** more region-flavoured than department-flavoured; s2 and s3 are roughly **1 : 1**.
s2/s3 also *mix* both conventions inside the same file.

**This independently corroborates the re-scoped REFUTED-2.** My own ceiling on rows whose
address contains a resolvable region-or-department component:

| source | region comps | dept comps | resolvable ≤ | % |
|---|---:|---:|---:|---:|
| s1 | 259,840 | 515 | 260,355 | 100.35 % |
| s2 | 225,997 | 214,163 | 440,160 | 62.58 % |
| s3 | 254,016 | 216,468 | 470,484 | 64.31 % |
| **total** | | | **1,170,999** | **69.11 %** |

My **69.11 %** sits just under the work order's independently-measured **71.10 %** ceiling
(1,204,739 / 1,694,445), and the residual is explained: my count omits
`pas de calais` (14,325 / 14,528) and `loire atlantique` spelled whole, both of which *are* in
`FR_REGIONS` and would add a few more. **So: I confirm the re-scoped figure and give the
mechanism. The "100 % of France" claim is a test_source1-only artefact, and s1 is only 15.31 %
of French rows.** The remaining ~31 % of French rows have no region *or* department component
at all.

Note `FR_REGIONS` is *not* the bottleneck for the three department names — `nord`, `gironde`,
`loire atlantique`, `pas de calais` are all present in `_upstream/src/normalize.py:243-249`.
The bottleneck is rows that carry no mappable component.

### DEFECT 2 (NEW, high value): 19 French canonical tokens leak into the blocking keys

`keys.token_lists` builds `alph` from address tokens that are **not** in `ADDR_GENERIC`
(`keys.py:59-63`), then keeps those of length ≥ 3, sorted **longest-first**, `head(9)`.
`ADDR_CANON_FR` (`normalize.py:199-214`) emits 19 canonical forms that are **absent** from
`ADDR_GENERIC`, so they survive into the key vocabulary:

`bat, bis, crs, fbg, gen, lieu, lieudit, mal, pres, prof, quai, res, rte, saint, sainte, za, zac, zi, zone`

Measured mass of their surface spellings in French addresses (all three sources):

| canonical | raw spellings counted | combined | % of France rows |
|---|---|---:|---:|
| `saint` | saint, st | 166,818 | 9.845 % |
| `bis` | bis, b | 69,757 | 4.117 % |
| `rte` | rte, route, rt | 29,927 | 1.766 % |
| `sainte` | sainte, ste | 8,077 | 0.477 % |
| `crs` | crs, cours | 13,281 | 0.784 % |
| `quai` | quai, q, qu | 13,004 | 0.767 % |
| `res` | res, residence | 13,088 | 0.772 % |
| `gen` | gen, general, gal | 6,078 | 0.359 % |
| `mal` | mal, marechal | 4,730 | 0.279 % |
| `bat` | bat, batiment | 3,745 | 0.221 % |
| `fbg` | fbg, faubourg, fg | 3,046 | 0.180 % |
| `prof` | prof, professeur | 2,485 | 0.147 % |
| `pres` | pres, president | 2,380 | 0.140 % |

| `lieu`/`zone`/`za`/`zi`/`zac`/`lieudit` | — | 207 | 0.012 % |
| **total** | | **336,623** | **19.866 %** |

The two worst offenders are pure street-grammar noise: **`saint` at 9.845 %** (a saint-prefix on
thousands of unrelated streets and communes) and **`bis` at 4.117 %** (the French house-number
suffix in "5 bis"). Neither is a *place*. Verified end-to-end that they reach `alph`:
`normalize_address('5 Rue des Lilas, Saint-Nazaire')` → `toks = ['5','rue','des','lilas','saint','nazaire']`
→ `alph = ['nazaire','lilas','saint']`.

**Mitigating factor, stated honestly:** `alph` is sorted longest-first, so short leakers
(`bis`, `rte`, `res`, `crs`, `gen`, `mal`, `bat` — all length 3) are pushed *down* the list and
only make the cut when the address yields fewer than 9 longer tokens. `saint` (length 5) is the
one that genuinely competes. So the leak dilutes rather than dominates — but at 9.845 % of rows
it is the single largest non-place contaminant in the French key vocabulary.


### DEFECT 3 (NEW, moderate): street-type abbreviations differ sharply by source

The same street type is written two ways, and the split is almost entirely by source:

| street type | full word | abbrev | s1 abbr rate | s2 abbr rate | s3 abbr rate |
|---|---|---|---:|---:|---:|
| rue | `rue` | `r` | 1.5 % | **40.4 %** | **38.8 %** |
| avenue | `avenue` | `av` | 6.7 % | **37.5 %** | **35.7 %** |
| boulevard | `boulevard` | `bd` | 17.4 % | **45.3 %** | **44.0 %** |
| place | `place` | `pl` | 23.2 % | **55.4 %** | **53.3 %** |
| chemin | `chemin` | `ch` | 25.2 % | **50.9 %** | **49.0 %** |
| impasse | `impasse` | `imp` | 4.1 % | **43.7 %** | **42.2 %** |
| route | `route` | `rte` | 8.2 % | **46.9 %** | **45.5 %** |
| cours | `cours` | `crs` | 0.0 % | **41.6 %** | **39.9 %** |
| quai | `quai` | `q` | 1.7 % | **41.7 %** | **40.4 %** |

(rate = abbr / (full + abbr), within one source.)

`ADDR_CANON_FR` **does** map both spellings to the same canonical value
(`r→rue`, `av→ave`, `bd→blvd`, `pl→pl`, `ch→chemin`, `imp→impasse`, `rte→rte`, `crs→crs`,
`q→quai`), so this is **not** a matching bug — it is a *volume* fact that explains why the
s2/s3-derived unigram `r` (182,872 in s2) is so large, and it means any s1-tuned threshold will
mis-set on s2/s3.

### Is city already a blocking key? Yes — unintentionally

Verified by running `keys.token_lists` on real French addresses:

| address | `atoks` | resulting `alph` |
|---|---|---|
| `175 Boulevard du President Franklin Roosevelt, Bordeaux, Nouvelle-Aquitaine` | `['175','blvd','du','pres','franklin','roosevelt','bordeaux']` | `['roosevelt','franklin','bordeaux','pres']` |
| `45 Rue de l Abbe de l Epee, Tourcoing, Nord` | `['45','rue','de','l','abbe','de','l','epee','tourcoing']` | `['tourcoing','abbe','epee']` |
| `12 Rue Dunkerque, Lille, Hauts-de-France` | `['12','rue','dunkerque','lille']` | `['dunkerque','lille']` |

City names are ≥ 5 characters, are not in `ADDR_GENERIC`, and are therefore **sorted to the front
of `alph`** by the longest-first rule. They then generate `kind 2` (AA) keys via
`num × alph` and `alph × alph` (`keys.py:73-79`). Note row 3: `Dunkerque` (a street) and `Lille`
(the city) are indistinguishable to the key builder — direct evidence for the non-separability in
(c).

### Should city be a blocking key? No — and the caps already prove it

The `df` caps do the arithmetic for us:

* `CAPS = {0:50, 1:50, 2:30, 3:50, 4:20}`, `S1_MAXCAP = 300` (`keys.py:33-37`).
* The AA (kind 2) cap is **30**; keys with `df > 30` are dropped at query time, and
  keys with `df > 300` never enter the s1 index at all (`blocking.py:16,30`).
* Bordeaux alone occurs **43,634** times in test_s1 = **1,454×** the AA cap of 30 and **145×**
  `S1_MAXCAP`. Nantes 37,624 = 1,254×. Lille 34,931 = 1,164×.
* A bare city key would therefore be **dropped outright** — it is not even a collision, it is a
  no-op.

What about the more plausible `(house_number, city)` pair? France has **518 distinct numeric
tokens** in the retained head, total numeric mass 1,567,275, median 492 per distinct number.
Bordeaux's 277,474 occurrences spread over 518 numbers average **535.7 per cell — 17.9× the cap
of 30**. So the *typical* `(num, city)` AA key is also above cap and gets dropped. Only 112
numeric tokens occur ≤ 200 times and could form sub-cap cells at all.

**Conclusion (inference, but arithmetically grounded):** the cap mechanism is already doing the
collision suppression that a hand-rolled city block would be added to do. Adding city as an
explicit blocking key would be *at best* redundant and *at worst* reintroduce exactly the
non-selectivity the caps were added to remove. This is the one place where the honest
recommendation is **no change**.

The residual risk is not collisions but **budget dilution**: city tokens and the 19 Defect-2
leakers compete for the same 9 `alph` slots, longest-first.

---

## Interpretation (clearly marked as inference)

1. *Inference.* With ~85 % of French rows inside 10 places, France is effectively **three
   metro-areas**, not one country. A retrieval design tuned on 85 %-concentrated data will look
   fine on French validation and fail on any fourth cluster.
2. *Inference.* Because s1 and s2/s3 disagree on region-vs-department **and** on abbreviation
   rate, any French threshold or dictionary tuned on s1 alone is mis-calibrated for 84.7 % of
   French rows. This is the most actionable structural fact in this report.
3. *Inference.* The `saint`/`bis` leak is a pure precision loss in `alph`: keys built on them
   match thousands of unrelated French businesses. Because `alph` is longest-first and both are
   short, the loss is bounded — expect a measurable recall gain, not a step change.
4. *Inference.* City-as-blocking-key is already answered by the data: the caps make it
   inoperative. The genuine lever is the `alph` slot budget, not the key set.

---

## Gaps (fields not collected — no estimates substituted)

1. **No component/axis field.** `addr_tokens` pools tokens across comma-separated components
   (`build_profile.py:126-127`). Any question about *which component* a token came from —
   including the work order's `{axis}` framing and the "region before or after city" ordering
   question — is **unanswerable** from this profile.
2. **No row-level co-occurrence.** `num × city` cell sizes in §(d) are *inferred* from marginals
   (a uniform-spread argument), not measured. A true (number, city) contingency table would settle
   the AA-cap arithmetic exactly.
3. **No `alph`-occupancy histogram.** The profile cannot say how many `alph` tokens a typical
   French address yields, so the "dilution" magnitude in Defect 2 is unquantified.
4. **No distinct-city count.** The vocabulary is truncated at 4,000 tokens, so the true number of
   distinct French places (and hence the true long tail beyond the top 10) is unknown.
5. **Accent folding is a profile artefact.** `rignac`/`merignac` cannot be summed naively because
   they are the *same* place under two spellings. I could not recover the true split from the
   profile.
6. **`saint` is not separable from a place.** It is simultaneously a place prefix
   (Saint-Nazaire), a street element (Rue Saint-Martin) and a commune prefix. The profile offers
   no way to apportion its 141,364 occurrences.

---

## Recommendations (prioritised)

1. **HIGH — add the 19 missing French canonical forms to `ADDR_GENERIC` in `_upstream/src/keys.py`.**
   Add at minimum: `saint, sainte, bis, rte, crs, quai, res, gen, mal, prof, pres, bat, fbg,
   lieu, lieudit, zone, za, zi, zac`. This is a one-line-list change, it is provably safe
   (all 19 are street/building grammar, never business-identifying), and it removes 336,623
   token occurrences — 19.866 % of French rows — from the key vocabulary. **CONFIRMED** by the
   profile. Expected effect: fewer wasted `alph` slots, more of the 9 available for real street
   and place tokens.
2. **HIGH — do not tune any French threshold or dictionary on `test_source1` alone.**
   s1 is 15.31 % of French rows and uses a different address convention (regions, 1.5 %
   `r` abbreviation) from s2/s3 (departments, ~40 % `r`). If any s1-derived French artefact
   exists in the current pipeline it is mis-set for 84.7 % of French rows. **CONFIRMED.**
3. **MEDIUM — investigate the ~31 % of French rows with no resolvable region/department
   component** (my ceiling: 1,170,999 / 1,694,445 = 69.11 % resolvable; the work order's
   independent ceiling is 71.10 %). Adding the remaining modern French region names to
   `FR_REGIONS` is cheap. But note the *legacy* names (Bretagne, Alsace, Lorraine, Bourgogne,
   Normandie, Champagne, Auvergne, Midi, Centre, Martinique) total only **14,253 occurrences =
   0.84 %** of French rows — so they are **not** where the missing 31 % lives. The gap is rows
   carrying no region-like component at all. **LIKELY**; the legacy-size figure is **CONFIRMED**.
4. **LOW / NO CHANGE — do not add city as a blocking key.** The `df` caps (AA = 30,
   `S1_MAXCAP` = 300) already drop both bare-city keys (1,454× over cap for Bordeaux) and the
   typical `(num, city)` key (17.9× over cap). Adding one would be redundant at best. State this
   explicitly so no one "fixes" it later.
5. **NO CHANGE — the s1/s2/s3 abbreviation split is not a matching bug.** `ADDR_CANON_FR` maps
   `r→rue`, `av→ave`, `bd→blvd`, `ch→chemin`, `imp→impasse`, `rte→rte`, `crs→crs`, `q→quai`
   correctly, and both spellings collapse to the same canonical token. Verified end-to-end. The
   split matters for threshold calibration (rec 2), not for token identity.
6. **NO CHANGE — accent handling.** `normalize.py:317` calls `strip_accents()` and correctly folds
   `Mérignac → merignac`, `Lège-Cap-Ferret → lege cap ferret`. The `m`/`rignac` fragmentation is
   an artefact of `build_profile.py`'s `TOKEN_RE`, not a pipeline defect. If the profile is ever
   rebuilt, `TOKEN_RE` should strip accents first — otherwise every future agent will
   re-derive this false trail.

---

## Explicit statement on the two `already_checked` items

* **REFUTED-1 (France postal-code loss).** Not re-derived, and nothing in this report bears on
  it. For the record, my s1 figures are consistent with it: `dig5` = 1,082 and `dig6` = 34 over
  259,452 s1 France rows.
* **REFUTED-2 (France region claim).** **Re-scoping confirmed, with numbers.** The famous
  "100 %" is a `test_source1`-only denominator. My independent component-level estimate is
  **69.11 %** across all three sources; the work order's is 71.10 %; both agree the s1 figure
  does not generalise. I also identify the *mechanism* nobody had: s1 writes regions
  (100.15 % of rows) while s2/s3 write departments (30.45 % / 29.59 %), and roughly 31 % of
  French rows carry neither. French geography is **not** settled.
