# D124 â€” France name_tokens: city and place-name coverage

## Headline

The work order asks for the "exact top-30 places" **on the France `name_tokens` axis**.
That list contains **zero place names**. The top 30 of the name axis is entirely
legal-form, organisational and function vocabulary (`sarl`, `sas`, `france`, `club`,
`eurl`, `amicale`); the highest-ranked true city, `bordeaux`, sits at **rank 41**. Places
are only cleanly visible on **`addr_tokens`**, where `bordeaux` is rank 8 and the ten
named cities occupy ranks 8â€“30. The premise is wrong about the axis and right about the
conclusion: the distribution is severely concentrated, with the ten leading place tokens
carrying **1,443,294 occurrences against 1,694,445 French rows = 85.18 per 100 rows**.

Two answers to the risk question, and they differ from the framing in the work order.
**City should not be a blocking key â€” and structurally it cannot be one**: `keys.py`
feeds address tokens only into *conjunctive* keys (number x word, word x word), never
bare. And the collision worry is therefore misplaced at the city level; the real
dictionary defect found here is that **19 of the 29 non-empty canonical outputs of
`ADDR_CANON_FR` have no entry in the `ADDR_GENERIC` stoplist** in `keys.py`, 13 of which
actually occur, carrying **238,175 occurrences = 14.06 per 100 French rows**.

## Findings

### 0. Scope, denominators, and two arithmetic invariants

All figures are computed over **all three test sources jointly**. Denominators are
`by_country.France.rows`, which is a different population from the name/addr token mass.

| Source | France rows | share of France | France name-token mass |
|---|---|---|---|
| test_s1 | 259,452 | 15.31% | 828,812 |
| test_s2 | 703,378 | 41.52% | 2,421,234 |
| test_s3 | 731,615 | 43.17% | 2,525,838 |
| **Total** | **1,694,445** | 100.00% | **5,775,884** |

**Invariant 1 â€” row counts close exactly.** 259,452 + 703,378 + 731,615 = **1,694,445**,
the same France population asserted in `already_checked`. I am measuring the same rows.

**Invariant 2 â€” `len_hist` is a complete partition of the France slice in every source.**
Sums are 259,452 / 703,378 / 731,615, each equal to that source's `rows`. There is no
residual bucket, which also confirms the bucketing is `len(business_name)//10*10`
(`build_profile.py:104-105`).

Name-token mass per row = 5,775,884 / 1,694,445 = **3.409 tokens per French row**.

**Truncation.** The name list is capped at `TOPN=4000` (`build_profile.py:27`) *and*
pruned of `count<=1` tokens every 8 chunks (`build_profile.py:45-49, 128-133`), so it is
both truncated and lossy:

| Source | true mass | listed (top-4000) sum | residual | residual % |
|---|---|---|---|---|
| s1 | 828,812 | 762,328 | 66,484 | 8.02% |
| s2 | 2,421,234 | 2,184,755 | 236,479 | 9.77% |
| s3 | 2,525,838 | 2,263,412 | 262,426 | 10.39% |

Every "share of name mass" figure below is therefore a **lower bound**. The 9.8% pooled

### 1. (a) The exact top-30 of France `name_tokens` â€” no place names in it

France-wide, `name_tokens` merged across s1+s2+s3. The `place?` column is my
classification, not a profile field.

| # | token | count | % of name mass | place? |
|---|---|---|---|---|
| 1 | sarl | 358,676 | 6.21% | no â€” legal form |
| 2 | sas | 252,882 | 4.38% | no â€” legal form |
| 3 | france | 157,343 | 2.72% | no â€” country word |
| 4 | s | 136,182 | 2.36% | no â€” single-letter fragment |
| 5 | club | 122,195 | 2.12% | no â€” organisation type |
| 6 | de | 100,867 | 1.75% | no â€” function word |
| 7 | eurl | 100,795 | 1.75% | no â€” legal form |
| 8 | sa | 82,278 | 1.42% | no â€” legal form |
| 9 | d | 80,655 | 1.40% | no â€” single-letter fragment |
| 10 | amicale | 79,613 | 1.38% | no â€” organisation type |
| 11 | sasu | 73,614 | 1.27% | no â€” legal form |
| 12 | sci | 63,630 | 1.10% | no â€” legal form |
| 13 | a | 63,142 | 1.09% | no â€” single-letter fragment |
| 14 | maison | 61,373 | 1.06% | no â€” trade word |
| 15 | du | 60,732 | 1.05% | no â€” function word |
| 16 | ecole | 58,804 | 1.02% | no â€” organisation type |
| 17 | centre | 56,194 | 0.97% | no â€” generic ("centre commercial") |
| 18 | groupe | 55,316 | 0.96% | no â€” trade word |
| 19 | comite | 53,381 | 0.92% | no â€” organisation type |
| 20 | com | 49,784 | 0.86% | no â€” abbreviation fragment |
| 21 | union | 49,247 | 0.85% | no â€” organisation type |
| 22 | fils | 46,583 | 0.81% | no â€” company-designation word |
| 23 | l | 45,951 | 0.80% | no â€” single-letter fragment |
| 24 | des | 44,387 | 0.77% | no â€” function word |
| 25 | veloppement | 44,238 | 0.77% | no â€” accent fragment (see section 4) |
| 26 | sportive | 43,661 | 0.76% | no â€” organisation type |
| 27 | cie | 39,275 | 0.68% | no â€” abbreviation |
| 28 | amis | 37,380 | 0.65% | no â€” organisation type |
| 29 | e | 35,433 | 0.61% | no â€” single-letter fragment |
| 30 | primaire | 34,769 | 0.60% | no â€” school type |

**Zero of these 30 is a French place name.** `france` (rank 3) is the country; `maison`
and `fils` are company-naming vocabulary, not toponyms.

### 2. Where the cities actually are, and at what rank

Same ten places, both axes. The rank gap is the whole finding.

| Place token | name rank | name count | addr rank | addr count | addr per 100 rows |
|---|---|---|---|---|---|
| bordeaux | 41 | 31,401 | **8** | 277,474 | 16.38 |
| nantes | 47 | 27,226 | **11** | 238,748 | 14.09 |
| lille | 50 | 25,716 | **12** | 221,585 | 13.08 |
| calais | 87 | 11,874 | **19** | 128,762 | 7.60 |
| tourcoing | 79 | 13,274 | **22** | 115,914 | 6.84 |
| dunkerque | 81 | 12,950 | **23** | 111,538 | 6.58 |
| roubaix | 82 | 12,586 | **24** | 107,111 | 6.32 |
| nazaire (Saint-) | 93 | 10,274 | **27** | 88,016 | 5.19 |
| pessac | 99 | 9,037 | **28** | 81,815 | 4.83 |
| buch (Teste-de-) | 102 | 7,958 | **29** | 72,331 | 4.27 |

`saint` alone is addr rank 18 (141,364) but is **not** a place: it is a saint-namesake
prefix shared by many toponyms and street names.

**Multi-word place names do not survive as single tokens.** `saint-nazaire` and
`teste-de-buch` are absent from both token lists as such; only their fragments
(`saint`+`nazaire`, `teste`+`buch`) appear. This is a direct consequence of
`TOKEN_RE = [a-z0-9]+` (`build_profile.py:28`) splitting on the hyphen. The pipeline's
own tokeniser differs again, so a French multi-word commune is **three** distinct tokens
in the profile and a different number again in production.

### 3. (b) Concentration of the top 10 places, with the denominator stated

Sum of the ten leading place-token **occurrences** on the `addr_tokens` axis:

    277,474 + 238,748 + 221,585 + 128,762 + 115,914
  + 111,538 + 107,111 +  88,016 +  81,815 +  72,331 = 1,443,294

    1,443,294 / 1,694,445 = 85.18 occurrences per 100 French rows

**This is a token-occurrence sum, not a row count, and I will not present it as one.**
A row whose address contains two of the ten (e.g. `teste` *and* `buch` for La
Teste-de-Buch) is counted twice, so 1,443,294 is an **upper bound** on the number of
rows that carry a top-10 place. The row share is therefore **<= 85.18%**. The profile
discards component structure (`build_profile.py:126-127` flattens components into one
counter), so the true row share is not recoverable here â€” a gap, not an estimate.

The concentration is not a Source-1 artifact. Per source, the same ten tokens cover:

| Source | France rows | top-10 occurrence sum | per 100 rows |
|---|---|---|---|
| s1 | 259,452 | 222,942 | 85.93 |
| s2 | 703,378 | 598,004 | 85.02 |
| s3 | 731,615 | 622,348 | 85.06 |

Spread of 0.91 points across all three sources, so no single source is driving the result
â€” but note the per-source figures are *not* a France-wide row rate, for the reason above.

### 4. Separability: places vs street words, and the tokeniser artifacts

**Places are cleanly separable from street words on the `addr_tokens` axis, and not at
all on the `name_tokens` axis.** On the address axis the two families occupy disjoint rank
bands and both are individually identifiable: street types are `rue` (rank 2, 728,583),
`avenue` (rank 21, 126,497), plus `chemin`/`impasse`/`allee` below the cut. Place and
region tokens are the remaining high-frequency mass. This separability is what makes the
address axis the usable one â€” and it is precisely what the name axis lacks, because the
name axis is dominated by legal forms.

**D081's warning applies directly to this task, and I can now show the mechanism.** The
profile tokeniser is `[a-z0-9]+` applied to a string that was *not* accent-stripped, so
an accented character acts as a **delimiter** and splits a word in two:

| input | profile tokens |
|---|---|
| `dÃ©veloppement` | `['d', 'veloppement']` |
| `rÃ©sidence` | `['r', 'sidence']` |
| `Saint-Ã‰tienne` | `['saint', 'tienne']` |
| `ChÃ¢lons` | `['ch', 'lons']` |
| `crÃ¨che` | `['cr', 'che']` |
| `HÃ´tel` | `['h', 'tel']` |

Confirmed against the profile, with production-pipeline counterparts:

| fragment | name count | addr count | verdict |
|---|---|---|---|
| `veloppement` | 44,238 | 0 | **artifact** â€” real word is `dÃ©veloppement` |
| `cole` | 29,147 | 505 | **artifact** â€” real word is `Ã©cole` (`ecole`, 58,804, is the clean form) |
| `sidence` | 950 | 1,467 | **artifact** â€” real word is `rÃ©sidence` |
| `tienne` | 0 | 667 | **artifact** â€” from `Saint-Ã‰tienne` |
| `chal` | 0 | 8,318 | **artifact per D081** â€” producer string not isolated, not relied on here |

So the single-letter and short-fragment tokens at name ranks 4, 9, 13, 23, 29 and the
`veloppement` at rank 25 are **profile-only artifacts**, not real place or business
vocabulary, and they cannot occur in the pipeline. Conversely every **place** token in
section 2 is accent-free and is a real toponym.

**This is not a defect in `_upstream`.** `normalize.py:264-266` defines `strip_accents()`
via `unicodedata.normalize("NFKD", ...)` dropping `unicodedata.combining` characters,
which maps `Ã©` to `e` correctly. The production pipeline transliterates; only the profile
builder deletes. The consequence is a **measurement caveat** for anyone reading these
profiles as a vocabulary list â€” a downstream consumer could "discover" a phantom gap.

### 5. (c) The blocking question â€” asked and answered structurally

**Should city be a blocking key? No â€” and it is already impossible, by construction.**
This is not a judgement call, it is readable off `keys.py`:

- Address tokens enter `token_lists()` only as `alph` / `nums` / `pin` (`keys.py:39-44`),
  and are only ever emitted as **kind 2** keys: `num x alph` (`keys.py:65`) and
  `alph x alph` pair (`keys.py:66-68`).
- Address tokens *also* reach **kind 0** keys, where they are conjoined with a core-name
  token (`keys.py:60`).
- There is no key kind that emits a bare address token. Kinds 1, 3 and 4 are built from
  `n_only`, the **name** axis (`keys.py:57, 61, 70, 71`).

So a city can never stand alone as a key. It only ever helps *disambiguate* a key that
already contains a house number, a street word or a name token. The work order's
"if many distinct businesses share one city and a street, does that create blocking
collisions" concern is answered by the schema: the key is `number x city`, so a
collision requires the *same house number in the same city*, which is far more selective
than city alone.

**On the DF cap.** `S1_MAXCAP = 300` (`keys.py:26`) is applied to the Source-1 index
(`blocking.py:13`), and the query side additionally caps by kind with `CAPS[2] = 30` for
kind 2 (`blocking.py:23, 34`). Since city-bearing keys are kind 2, the binding ceiling is
**30**, not 300. I can bound the situation but not resolve it: the *token* frequency of
`bordeaux` in s1 is 43,634 = 145x the 300 cap, but the **key** DF is at most that and
typically far lower, because 43,634 rows spread across many house numbers. The profile
does not materialise keys, so the true key DF is a **gap**.

Supporting context, all France-wide: `num_digits / rows` = 3,286,447 / 1,694,445 =
**1.940**, and `alpha_only_addr` = 54,602 / 1,694,445 = **3.22%** â€” so ~96.8% of French
rows carry at least one house number to pair a city with. Only 389 of the 4000 listed s1
address tokens exceed the 300 cap, and 199 of 4000 name tokens do.

### 6. New defect found: `ADDR_CANON_FR` outputs missing from `ADDR_GENERIC`

`normalize_address` maps French address tokens through `ADDR_CANON_FR`
(`normalize.py:320-321`, defined `normalize.py:199-214`). Those canonical outputs are
then filtered by `ADDR_GENERIC` in `keys.py:14-19` when building `alph`
(`keys.py:39`). A canonical output that `ADDR_GENERIC` does not list therefore **survives
into the blocking vocabulary** â€” it is never suppressed.

`ADDR_CANON_FR` has **30 distinct outputs** (`''` plus 29 non-empty). **20 are absent from
`ADDR_GENERIC`**, of which one is `''` â€” which *is* handled, because `keys.py:39` filters
`element != ""`. So the true figure is **19 of the 29 non-empty canonical outputs missing**.

Of those 19, **13 actually occur** in French addresses and leak:

| canonical output | addr occurrences | per 100 French rows | source form |
|---|---|---|---|
| saint | 141,364 | 8.34 | `saint`, `st` (rue/place/boulevard names) |
| bis | 52,072 | 3.07 | `bis`, `b` â€” "175 **bis**" house-number suffix |
| rte | 11,995 | 0.71 | `route`, `rte` â€” street type |
| res | 8,340 | 0.49 | `residence`, `res` |
| quai | 8,089 | 0.48 | `quai`, `q` â€” street type |
| sainte | 7,486 | 0.44 | `sainte`, `ste` |
| crs | 4,520 | 0.27 | `cours`, `crs` â€” street type |
| bat | 1,767 | 0.10 | `batiment`, `bat` |
| gen | 1,227 | 0.07 | `general`, `gen` |
| mal | 612 | 0.04 | `marechal`, `mal` |
| pres | 496 | 0.03 | `president`, `pres` |
| lieu | 181 | 0.01 | `lieu` |
| zone | 26 | 0.00 | `zone` |
| **total** | **238,175** | **14.06** | |

The 6 that never occur (`fbg`, `lieudit`, `prof`, `za`, `zac`, `zi`) carry 0 occurrences
in the France `addr_tokens` axis and are harmless as measured â€” though `za`/`zac`/`zi`
would matter for industrial addresses not present here.

**`rte` and `quai` are the clear-cut defect (`CONFIRMED`).** `ADDR_GENERIC` already lists
`rue`, `chemin`, `allee` and `impasse` (`keys.py:17-18`) â€” the French street words it does
know â€” but omits `rte` and `quai`, which `ADDR_CANON_FR` itself produces from `route`
and `quai`. These are street types, semantically identical to the ones already suppressed.

**`bis` is a strong candidate (`CONFIRMED` as a leak, `LIKELY` as a defect).** 3.07 per 100
rows, and `ADDR_CANON_FR` maps the bare token `b` to `bis` (`normalize.py:211`), so a
single stray `b` in any French address becomes a blocking token.

**`saint` is a judgement call, flagged, not a recommendation.** It is the largest leak at
8.34 per 100 rows, but `saint` is *deliberately* normalised (`normalize.py:207` maps
`st` to `saint`, which is correct French usage), and it is simultaneously a place fragment, a
street-name word and a business-name word. Adding it to `ADDR_GENERIC` would suppress a
token the pipeline appears to want. `SPECULATIVE` â€” a human should decide.

## Interpretation

*Inference, clearly marked as such.*

The work order's premise â€” that city names should be visible on the `name_tokens` axis â€”
is a property of the *raw data organisation*, not of the data: French business names
begin with their legal form (`Sarl`, `Sas`, `Eurl`, `Sa`) in the overwhelming majority of
cases, which is why `sarl` alone is 6.21% of French name-token mass. Any dictionary mined
from the name axis for France would mine corporate-form vocabulary and find no toponyms.

Because the ten named places cover ~85 per 100 rows, city is a strong *signal* and a
terrible *key*. The upstream code already treats it that way: cities only ever appear
conjoined with a house number or a name token, and the kind-2 query cap of 30 keeps the
residual collision risk low. **No change to the blocking scheme is warranted, and I am not
manufacturing a recommendation to justify the task.**

The one change I do argue for is in `keys.py`, not the blocking scheme: `ADDR_GENERIC`
should list the French street types that `ADDR_CANON_FR` emits. `rte` and `quai` are
unambiguous. This is a small, safe, additive change that suppresses ~20,084 occurrences
(1.19 per 100 rows) of pure street-type noise from the blocking vocabulary.

## Gaps

1. **True row share of the top 10 places is not recoverable.** 1,443,294 is a
   token-occurrence sum, an upper bound on rows, not a row count. `build_profile.py:126-127`
   flattens address components into one counter, so multi-word communes double-count.
2. **Key-level document frequency is not measurable from the profile.** Profiles hold
   token counts; blocking keys are hashes of token combinations. Every statement in
   section 5 about the 300 / 30 caps is structural, from `keys.py`, not measured key DF.
3. **Component order is not observable.** Whether a row reads "Bordeaux, Nouvelle-Aquitaine"
   or "Nouvelle-Aquitaine, La Teste-de-Buch" cannot be recovered, so I cannot label a
   component as "the city" without the raw TSV (forbidden on this machine).
4. **Accent-free tokens cannot separate place from street namesake.** `saint` 8.34 per 100
   rows aggregates `Saint-Nazaire`, `Saint-Etienne`, `Rue Saint-Joseph` and a saint-namesake
   business name indistinguishably.
5. **I did not measure s1/s2/s3 department coverage** that `already_checked` flags as
   unowned. Doing it correctly needs component structure (gap 3), so I deliberately did not
   publish a competing union-bound figure alongside the unreconciled 71.10% / 97.44%
   contradiction.
6. **`chal` (8,318) is listed as an artifact per D081 but I could not isolate a producer
   string**, so no conclusion here rests on it.
7. **End-to-end score effect of the section 6 leak is unquantified.** The defect is
   confirmed at the vocabulary level; measuring its effect on F0.5 requires running the
   pipeline, which is out of scope for a profile-only agent.

## Recommendations

1. **Add `rte`, `quai` (and `crs`) to `ADDR_GENERIC` in `keys.py`.** `CONFIRMED`.
   ~20,084 occurrences (1.19 per 100 French rows) of street-type noise enter blocking
   tokens purely because `ADDR_CANON_FR` emits forms the stoplist does not know. Additive,
   France-scoped in effect, no risk to other countries.
2. **Add `bis` to `ADDR_GENERIC`.** `LIKELY`. 3.07 per 100 rows, and the bare-`b` to
   `bis` rule means incidental single letters are amplified. Note the pipeline needs `bis`
   *for the address string*; only the blocking-key path should suppress it.
3. **Decide `saint` explicitly â€” do not add it by default.** `SPECULATIVE`. Largest leak
   (8.34 per 100 rows) but plausibly wanted. Flagged for a human.
4. **Do NOT add a city blocklist, and do NOT make city a blocking key.** `CONFIRMED`
   unnecessary. The design already prevents it structurally, and the `CAPS[2] = 30` cap
   bounds what remains. A hand-maintained French city stoplist would be redundant with a
   mechanism that is already correct.
5. **Mine any future French toponymy dictionary from `addr_tokens`, not `name_tokens`.**
   `CONFIRMED` by the rank gap in section 2.
6. **Re-run the profile builder with accents stripped** (`strip_accents`-equivalent)
   before any vocabulary work. `CONFIRMED` as a measurement defect in the tooling, not in
   the pipeline. Until then, treat every short name-axis fragment (`s`, `d`, `a`, `l`, `e`,
   `veloppement`, `cole`, `sidence`) as an artifact, not as a gap in the pipeline.
