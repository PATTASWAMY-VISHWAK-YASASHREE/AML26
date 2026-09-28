# D119 — remaining gaps in `ADDR_CANON_FR`

## Headline

**`ADDR_CANON_FR` has no material gap left for this dataset, and the one big finding
standing against it — the French function words — is roughly 37.5% smaller than the
established narrative states and is almost entirely inert in the pipeline.**

Three results, in order of importance:

1. **CONFIRMED, new: the established 16.40% function-word figure is inflated by ~37.5%.**
   `normalize.py:333-335` resolves a French region by matching a *whole comma-component*
   and then `continue`s, so the tokens of `"Pays de la Loire"`, `"Hauts de France"`,
   `"Pas de Calais"` and `"Ile de France"` are **never emitted into `atoks` at all**.
   The profile cannot see this because it flattens components. Removing the
   region-consumed `de`/`la` gives a pipeline-visible function-word mass of
   **1,229,094 = 10.25%**, not 1,966,401 = 16.40%. The `test_s2` figure moves from
   **15.41% -> 10.68%**.

2. **CONFIRMED, new: the "dilutes IDF" mechanism is self-cancelling, and the
   "hurts blocking" mechanism does not exist.** `idf = ln(n/df)` with
   `n = 1,694,445` France rows and `df <= occurrences`, so `idf(de) >= ln(1694445/1050023) = 0.4785`
   against a ceiling of 14.343 — IDF already discounts these words by ~28x. And
   `keys.py:42` requires `len >= 3` for a blocking token, so `de/la/du/le` (2 chars)
   **never become blocking keys**; `des` is already in `ADDR_GENERIC` (`keys.py:16`);
   `les` (3,685) exceeds `S1_MAXCAP=300` and is dropped as non-selective.

3. **The remaining street-type gap is 0.55% of listed mass and no single entry is
   load-bearing.** The 16 unambiguous French way-types total **26,447 (0.2205%)**;
   the plausible-but-ambiguous set adds 40,002 (0.3335%). The largest unhandled
   candidate, `cour` (9,403 = 0.078%), is smaller than the already-handled `place`
   (13,363).

**Verdict on the work order's framing:** a clean bill of health, with one cheap
SPECULATIVE addition (`cour` -> `crs`) and one argument I argue *against* making.

---

## 0. Ground truth and reproduction checks

Dictionaries were extracted from `_upstream/src/normalize.py` by regex over the dict
literals (not hand-transcribed). The extraction reproduces D081/D082's structure
exactly, which validates the read:

| Quantity | Value | Source |
|---|---|---|
| `ADDR_CANON_COMMON` keys | 177 | regex over `normalize.py:153-198` |
| `ADDR_CANON_FR` keys | 68 | regex over `normalize.py:199-214` |
| COMMON after the 7-key drop tuple | 170 | `normalize.py:321` |
| **effective France canon** | **219** | `{**COMMON-7, **FR}` |
| France rows (s1+s2+s3) | 259,452 + 703,378 + 731,615 = **1,694,445** | `by_country["France"].rows` |
| listed France addr-token mass | 2,253,877 + 4,745,780 + 4,993,261 = **11,992,918** | `sum(addr_tokens["France"])` |
| distinct tokens (union) | **4,441** | union of three top-4000 lists |

`addr_tokens` is the **top 4000 per country per file** (`build_profile.py:27,140`), and
`build_profile.py:130-133` prunes hapax tokens every 8 chunks. Absence from this list is
therefore *not* proof of non-occurrence. Every "unhandled" claim below means **"not in
the top 4000"**, never "does not occur".

Baseline reproduction (validates the profile read):
`de+la+du+des` in `test_s2` = 381,880 + 176,186 + 90,693 + 82,399 = **731,158**;
731,158 / 4,745,780 = **15.41%** — the established figure, exactly.

---

## 1. NEW DEFECT — the function-word figure is inflated ~37.5% (CONFIRMED)

### 1.1 The mechanism

`normalize_address` (`normalize.py:328-352`) iterates comma-separated components and
tests each against the state map **before** tokenising:

```python
    for c in comps:
        ...
        ck = re.sub(r"[^a-z0-9& ]+", " ", c).replace("&", " and ")
        ck = " ".join(ck.split())
        if ck in smap:
            state = smap[ck]
            continue                      # <-- normalize.py:334-335
```

`smap` is `FR_REGIONS` for France (`normalize.py:250`), and **four of its 14 keys
contain `de` or `la`** (`normalize.py:243-249`):

| `FR_REGIONS` key | value | contains |
|---|---|---|
| `hauts de france` | `hdf` | `de` |
| `pas de calais` | `hdf` | `de` |
| `pays de la loire` | `pdl` | `de`, `la` |
| `ile de france` | `idf` | `de` |

(The `ck` regex turns hyphens into spaces, so `"Hauts-de-France"` -> `"hauts de france"`
still matches — the guard is not defeated by hyphenation.)

So one `de` is **consumed and discarded** for every row whose region component is one of
those four. The profile builder has no equivalent guard: `build_profile.py:126-127`
splits on `[,;]` and then does `at.update(TOKEN_RE.findall(comp))` — it counts region
tokens as ordinary address tokens.

### 1.2 The measurement

Sizing each region key by its **rarest** constituent (a component match requires all
its words), from `addr_tokens["France"]` summed over the three test files:

| region key | sizing token | count | `de` consumed | `la` consumed |
|---|---|---|---|---|
| `hauts de france` | `hauts` | 289,655 | 289,655 | — |
| `pays de la loire` | `pays` | 207,396 | 207,396 | 207,396 |
| `pas de calais` | `pas` | 29,032 | 29,032 | — |
| `ile de france` | `ile` | 1,914 | 1,914 | 1,914 |
| **total consumed** | | | **527,997** | **209,310** |

Cross-check on the sizer: `france` = 293,150 ~= `hauts` (289,655) + `ile` (1,914) = 291,569;
`loire` = 334,419 ~= `pays` (207,396) + `atlantique` (128,348) = 335,744. Both close to
within ~1%, which is what makes this sizing credible.

| quantity | value | % of 11,992,918 |
|---|---|---|
| profile six-word mass (established) | 1,966,401 | **16.396%** |
| minus region-consumed `de` | −527,997 | |
| minus region-consumed `la` | −209,310 | |
| **pipeline-visible six-word mass** | **1,229,094** | **10.248%** |
| overstatement in the established figure | | **37.5%** |

Per source (respecting the "never quote one source as a France-wide rate" rule):

| file | profile four-word | profile % | region-consumed | **pipeline-visible %** |
|---|---|---|---|---|
| `test_s1` | 440,035 | 19.52% | — | — |
| `test_s2` | 731,158 | **15.41%** | 230,650 | **10.68%** |
| `test_s3` | 779,599 | 15.61% | — | — |
| all three (six words) | 1,966,401 | 16.396% | 737,307 | **10.248%** |

**Bounds, stated honestly.** 527,997 / 209,310 are *upper bounds* on consumption
(`pays`/`hauts`/`pas`/`ile` could in principle appear outside the exact component form —
`pas` is also the adverb "not"). So the true pipeline-visible share lies in
**[10.25%, 16.40%]**, and the point estimate is 10.25%. The correction is real and
one-directional; its exact size is a range, not a point.

**Second-order consequence.** The profile denominator is also inflated: the
non-`de`/`la` `FR_REGIONS` component tokens alone total **2,205,764**. The pipeline's
true `atoks` mass is therefore materially below 11,992,918, which pushes the
pipeline-visible *share* back **up** from 10.25%. Both corrections push the same way;
the honest statement is that the established 16.40% is an over-estimate of the mass
that reaches the features, by roughly a third.

---

## 2. Would adding `de/la/du/des/le/les` help or hurt? (the required two-sided argument)

### 2.1 The case FOR (the established position)

These six are in neither `ADDR_CANON_COMMON` nor `ADDR_CANON_FR`, and none is a key of
the effective 219-key France canon, so they survive into `atoks` uncanonicalised. They
are **1.16 of the 7.078 listed address tokens per France row** (1,229,094 / 1,694,445 and
11,992,918 / 1,694,445), i.e. **16.4% of the profile token set** and, after section 1,
**~10% of what the pipeline actually emits**. They therefore:

- inflate `qa_len` / `sa_len` (`features.py:112`) and the intersection `a_inter`
  (`features.py:112`) for **every** French pair, compressing `a_jac` and `a_cont`
  (`features.py:123-124`) toward 1.0;
- inflate the input to `a_ratio` / `a_tsort` / `a_tset` / `a_partial`
  (`features.py:83-86`), which are **unweighted** RapidFuzz ratios on the `atoks` string;
- inflate `s1_addr_dups` (`stage2.py:98`), an exact-`atoks` match count that becomes
  less selective as more addresses collapse to the same string.

The `a_jac` arithmetic, worked: two French addresses in the same city,
`{rue, de, la, paix, bordeaux}` vs `{rue, de, la, liberation, bordeaux}` ->
`a_inter` = 4, `a_cont` = 4/5 = **0.800** for what is almost certainly a non-match.
After deletion: `{rue, paix, bordeaux}` vs `{rue, liberation, bordeaux}` -> `a_inter` = 2,
`a_cont` = 2/3 = **0.667**. A true match stays at 1.000 either way. So deletion
**compresses the non-match distribution downward while leaving matches untouched** —
exactly the shape a ranker wants.

### 2.2 The case AGAINST — three objections, all measured

**(a) The IDF-dilution rationale is self-cancelling.** `token_idf`
(`features.py:13-20`) sets `idf = ln(n / df)` per `(country, tok)`, with
`df` = records containing the token. Because `df <= occurrences` and
`n = 1,694,445`:

| token | occurrences | `idf` **lower bound** `ln(n/occ)` | ceiling `ln(n/1)` |
|---|---|---|---|
| `de` | 1,050,023 | **0.4785** | 14.343 |
| `la` | 481,231 | 1.2588 | 14.343 |
| `du` | 220,355 | 2.0399 | 14.343 |
| `des` | 199,183 | 2.1409 | 14.343 |
| `le` | 11,924 | 4.9566 | 14.343 |
| `les` | 3,685 | 6.1308 | 14.343 |
| *(`rue`, already handled)* | 728,583 | 0.8440 | 14.343 |
| *(`moulin`, unhandled)* | 7,048 | 5.4824 | 14.343 |
| *token with occ = 3* | 3 | 13.2440 | 14.343 |

Unseen tokens are imputed `idf = 12.0` (`features.py:31,36`). So `de` already carries at
most **0.4785/13.244 = 3.6%** of the weight of a rare token — IDF is *designed* to
discount frequent terms and is already doing it. The established claim that these words
"dilute IDF weighting" describes a mechanism that is largely self-neutralised. Note the
pipeline already ships a canon entry with a *lower* IDF (`rue`/`r` -> `rue`, bound 0.844)
and treats that as correct.

**(b) The blocking argument is void — deletion cannot help recall.** `keys.py:39-43`
builds blocking tokens from `atoks`:

```python
toks  = ...filter(~pl.element().is_in(ADDR_GENERIC) & (pl.element() != ""))   # line 39
alph  = toks...filter(~...isdigit() & (pl.element().str.len_chars() >= 3))      # line 42
```

| token | len | in `ADDR_GENERIC`? | generates an `alph` key? | occ | over `S1_MAXCAP=300`? |
|---|---|---|---|---|---|
| `de` | 2 | no | **no** (`len < 3`) | 1,050,023 | yes |
| `la` | 2 | no | **no** | 481,231 | yes |
| `du` | 2 | no | **no** | 220,355 | yes |
| `le` | 2 | no | **no** | 11,924 | yes |
| `les` | 3 | no | **yes** | 3,685 | **yes -> dropped** |
| `des` | 3 | **yes** (`keys.py:16`) | **no** | 199,183 | yes |

So **all six are already inert for candidate generation**: four by the length gate, one
by `ADDR_GENERIC`, and `les` because its document frequency is 12x the cap. The
established France finding that "blocking caps are healthy" is therefore *unaffected* by
this decision, and adding the words buys **zero** recall.

**(c) The "merges distinct places" worry is mostly a non-issue, and I can show why
with the data.** The usual counter-example is "Rue de la Paix" vs "Rue de la Reine".
Deleting `de`/`la` gives `rue paix` vs `rue reine` — still distinct, because the
*discriminating* token is the name, which always survives. Function words are never the
sole discriminator between two French odonyms. The genuine residual risk is
**article-bearing commune names**: `le` 11,924 and `les` 3,685 (0.130% of mass) are
low-frequency precisely because most French articles are elided into the following word
by `normalize.py:342` (`c.replace("'", "")` -> `l'Eglise` -> `leglise`). So the
`Le Mans` / `Mans` collision class has a measured exposure of **at most 15,609 tokens
(0.13%)**.

### 2.3 Verdict

**Split the decision. Do NOT add `de`, `du`, `des` to `ADDR_CANON_FR` as a
"canonicalisation" change on the strength of the established rationale; DO treat
French function-word suppression as a separate, real, and *stopword-shaped* decision.**

- `de` + `du` + `des` = 1,469,561 profile mass. Arguments (a) and (b) show the stated
  mechanism is ~3.6%-weighted at most on the IDF side and **zero** on the blocking side.
  The only surviving justification is the unweighted `a_cont`/`a_jac`/`a_tset`
  compression in 2.1, which is real but modest and **unmeasured in effect** — I have no
  pair-level data (see Gaps).
- `la` + `le` + `les` = 496,840 profile mass, of which 209,310 `la` is already consumed
  by region components (section 1). Pipeline-visible: **287,530**. These carry the
  article-in-place-name collision risk, so they need a *different* justification than
  the others and I do not have one.
- Ranking: if forced to act, **`cour` -> `crs` first, function words last.**

I explicitly **decline to recommend** adding the six to `ADDR_CANON_FR` on this
evidence. The finding is real but the mechanism is misdiagnosed: this is a stopword
problem in the unweighted similarity features, not a dictionary-completeness problem,
and the correct home for it is a stopword filter applied to the `atoks` string
(symmetrically in `features.py` and `stage2.py`), not 6 entries in a street-type table.

---

## 3. Street-type / address-type gaps, enumerated

Every French street-type token **in the top 4000** of `addr_tokens["France"]` that the
effective 219-key France canon does **not** map, grouped. `HANDLED` rows are shown for
contrast. Counts are s1+s2+s3; `%` is of 11,992,918.

### 3.1 Currently handled (for scale)

`rue` 728,583 (6.075%) · `saint` 141,364 · `avenue` 126,497 · `boulevard` 38,275 ·
`impasse` 21,102 · `route` 17,932 · `allee` 17,779 · `chemin` 15,244 · `place` 13,363 ·
`cours` 8,761 · `quai` 8,089 · `sainte` 7,486 · `square` 4,933 · `residence` 4,748 ·
`faubourg` 3,046 · `fort` 1,923 · `batiment` 1,978 · `lieu` 181 · `zone` 26.

### 3.2 Group A — unambiguous French way-types, not mapped (**CONFIRMED**, 26,447 = 0.2205%)

| token | mass | % | note |
|---|---|---|---|
| `cour` | 9,403 | 0.0784% | abbrev. of `cours` -> `crs` |
| `clos` | 3,588 | 0.0299% | also a noun |
| `passage` | 3,167 | 0.0264% | |
| `lotissement` | 1,788 | 0.0149% | |
| `mail` | 1,731 | 0.0144% | French "mall", a listed street type |
| `chaussee` | 1,125 | 0.0094% | see accent note, section 4 |
| `hameau` | 1,067 | 0.0089% | |
| `esplanade` | 878 | 0.0073% | |
| `sentier` | 618 | 0.0052% | |
| `ruelle` | 593 | 0.0049% | |
| `parvis` | 587 | 0.0049% | |
| `sente` | 562 | 0.0047% | also the verb "sente" |
| `venelle` | 481 | 0.0040% | |
| `entree` | 445 | 0.0037% | |
| `rond` | 411 | 0.0034% | "rond-point" |
| `passerelle` | 261 | 0.0022% | |
| `allees` | 187 | 0.0016% | |
| **total** | **26,447** | **0.2205%** | |

### 3.3 Group B — plausible street/address features, noun sense also common (**LIKELY**, 40,002 = 0.3335%)

`moulin` 7,048 · `parc` 4,244 · `pont` 3,866 · `port` 3,825 · `fontaine` 3,553 ·
`cite` 2,546 · `gare` 1,735 · `jardin` 1,644 · `chateau` 1,640 · `tour` 1,465 ·
`chapelle` 1,366 · `domaine` 1,194 · `palais` 1,124 · `canal` 1,004 · `universite` 879 ·
`promenade` 536 · `villa` 594 · `faculte` 337 · `halle` 291 · `manoir` 288 ·
`campus` 261. (`sente` counted once, in A.)

`moulin` (7,048) is the largest Group B entry and is **a name element, not a street
type** ("Rue du Moulin"); I list it so the fleet does not have to re-derive that it
should not be added.

### 3.4 Explicitly NOT street types — do not add

Measured high, France-only, and **place names**, not address types. This is the single
most useful negative result in the report, because a naive frequency miner would have
added every one of them:

| token | mass | what it actually is |
|---|---|---|
| `teste` | 72,268 | **"La Teste-de-Buch"**, a commune near Bordeaux |
| `buch` | 72,331 | ditto (the `-de-` compound) |
| `cap` | 61,600 | **"Cap Ferret"**, the headland / commune |
| `ferret` | 60,275 | ditto |

The near-exact pairing (`teste` 72,268 vs `buch` 72,331; `cap` 61,600 vs `ferret` 60,275)
is the signature of a hyphenated compound split by `TOKEN_RE = [a-z0-9]+`
(`build_profile.py:28`) at the hyphen. The pipeline splits them too (it does not strip
hyphens — only accents, at `normalize.py:317`), so `cap`/`teste` are real pipeline
tokens. They are place names either way.

Also excluded: `moulin` 7,048, `fontaine` 3,553, `jardin` 1,644, `chateau` 1,640,
`tour` 1,465, `chapelle` 1,366, `palais` 1,124, `maine` 645 (also a US state token,
16,849 in US — never add), `canal` 1,004 (US 2,895 / India 5,491 — shared, never add),
and animal/colour nouns that are business names: `chevaux` 416, `cheval` 385, `renard`
315, `lapin` 203, `rat` 231, `bouvier` 81, `poulain` 242, `tonkin` 263, `toile` 90,
`laine` 90, `peau` 23. All are **absent from US and India**, confirming they are
French business-name vocabulary leaking into the address field, not address types.

### 3.5 The biggest single unhandled mass is not a street type at all

`teste` + `cap` = **133,868 = 1.116%** of listed France mass — **larger than the entire
Group A + Group B street-type gap (66,449 = 0.554%) combined.** This single comparison
is the strongest argument that the street-type dictionary is not where the remaining
French address mass sits.

---

## 4. Why the top-4000 profile **understates** several candidates (tokenizer mismatch)

`build_profile.py:28` tokenises the **raw** address; `normalize.py:317` applies
`strip_accents` **first**. Accents are therefore separators in the profile and removed in
the pipeline, so accented words appear in the profile as *both* a head fragment and a
merged form. Measured:

| accented word | profile head-fragment | profile merged form | pipeline sees |
|---|---|---|---|
| `chaussée` | `chauss` **2,372** | `chaussee` **1,125** | `chaussee` only |
| `cité` | `cit` 5,580 | `cite` 2,546 | `cite` only |
| `château` | `ch` 12,774 | `chateau` 1,640 | `chateau` only |
| `église` | `glise` 378 | `eglise` 747 | `eglise` only |
| `école` | `col` 125 | `ecole` 1,560 | `ecole` only |
| `égalité` | `galit` 97 | `egalite` 575 | `egalite` only |
| `marché` | `march` 450 | `marche` 370 | `marche` only |
| `santé` | `sant` 80 | `sante` 250 | `sante` only |

**Consequence for ranking.** `chaussee` (1,125) is the **worst-sized** candidate in
Group A: the same word appears 2,372 times as `chauss`, so its true pipeline mass is
**~3,497**, not 1,125 — a 3.1x undercount, and the only Group A entry whose true rank
materially exceeds its measured rank. Conversely `cite`, `chateau`, `eglise`, `ecole`,
`egalite`, `marche`, `sante` are also undercounted, but all sit in Group B or lower.
This reproduces and sharpens D081 section 8 / D082 F7; the practical rule stands:
**treat any candidate evidenced by a token of 4 characters or fewer as unverified.**

**Per-source form stability.** For every Group A/B candidate the `s2/s3` ratio is
0.86–1.08, i.e. the *written form* is stable across the query sources. The `s1/s2` ratio
is uniformly ~0.41 — that is a **row-count** artefact (259,452 / 703,378 = 0.369), not
a form change, and it must not be read as "source 1 spells these differently".
Exception: `chaussee` (s1/s2 = 0.138) and `cite` (0.117) are low because their
*fragments* `chauss` / `cit` are concentrated in s1, which is further confirmation of
the accent split.

---

## 5. Ranked recommendations

| # | Proposal | Evidence | Expected impact | Mark |
|---|---|---|---|---|
| 1 | Add `"cour": "crs"` to `ADDR_CANON_FR` | `cour` 9,403 vs handled `cours` 8,761 -> `crs`; the long form is mapped, the abbreviation is not — a pure asymmetry | 9,403 tokens (0.078%) folded onto an existing canonical form; consistent with `rue`/`r`->`rue`, `av`/`ave`->`ave` | **LIKELY** |
| 2 | Add self-maps `"passage"`, `"lotissement"`, `"hameau"`, `"esplanade"`, `"sentier"`, `"ruelle"`, `"parvis"`, `"venelle"`, `"mail"`, `"allees"`, `"passerelle"`, `"rond"` | Group A, section 3.2 | 17,044 tokens (0.142%); takes the "one form handled, sibling not" class to zero once `cour` is in | **CONFIRMED** unhandled; **LIKELY** useful |
| 3 | Add `"chaussee": "chaussee"`, but **re-derive its size after fixing `build_profile.py`** | true mass ~3,497, not 1,125 (section 4) | removes a 3.1x mis-sized entry | **LIKELY** |
| 4 | Add `"clos"`, `"sente"`, `"entree"` | Group A, but each is also a common noun | 4,595 (0.038%) | **SPECULATIVE** |
| 5 | Group B (`parc`, `pont`, `port`, `cite`, `gare`, `villa`, `campus`, …) | noun sense dominates for several; `moulin`/`fontaine`/`jardin` are name elements | up to 40,002 (0.334%) | **SPECULATIVE** — needs human sense review |
| 6 | **Do NOT add** `de/la/le/les` to `ADDR_CANON_FR` | section 2.2(a)(b)(c): IDF already discounts them ~28x, they cannot reach blocking at all, and `la/le/les` carry an article-collision class | would be churn with an unmeasured effect | **declined** |
| 7 | **Do NOT add** `teste`, `buch`, `cap`, `ferret`, `moulin`, `fontaine`, `jardin`, `chateau`, `canal`, `maine`, or any animal/colour noun | section 3.4 — place names, name elements, or shared with US/India | prevents the largest single class of wrong entries | **CONFIRMED negative** |
| 8 | **Fix `build_profile.py:28` to apply `strip_accents` before `findall`** | section 4; inherited from D081 section 8 / D082 F7 | corrects `chauss`/`cit`/`ch`/`galit`/`col` and re-sizes every short token; **prerequisite for trusting any future mining of this table** | **CONFIRMED** (highest value per line) |
| 9 | Add a `state_resolved` per-country counter to the profile builder | would have made section 1 exact instead of a range | instrumentation, not a dictionary entry | **SPECULATIVE** |

**No change needed** to the 13 dead keys (`avn`, `bld`, `boul`, `chem`, `fbg`, `fg`,
`lieudit`, `numero`, `null`, `prof`, `za`, `zi`, `zac`) — inert, zero cost, and they make
the table look complete. Do not delete them: churn for no measurable gain.

---

## Gaps / limits of this analysis

1. **No pair-level data.** The profile has token counts, not candidate pairs. I can show
   that `a_cont` is compressed (arithmetic in 2.1) but **cannot** measure the effect on
   score. Recommendation 6 is declined for exactly this reason.
2. **Section 1 is a range, not a point.** The region-consumption figures (527,997 /
   209,310) are upper bounds, so pipeline-visible function-word mass is in
   [1,229,094, 1,966,401] = [10.25%, 16.40%]. Sizing each region key by its rarest
   constituent is the method; it is corroborated to ~1% by the `france` and `loire`
   cross-checks but is not exact.
3. **Component boundaries are destroyed by the profile builder.** `build_profile.py:126`
   splits on `[,;]` and flattens. I can infer region-component consumption from token
   co-occurrence, but I cannot see which component any token came from. This is the same
   limitation D082 Gaps section 1 records, and it is what forces section 1 into a range.
4. **Street-type vs noun sense is not decidable from token counts.** The Group A/B split
   is linguistic judgement, marked as such. `sente` (verb), `clos` (enclosure/adjective),
   `parc`/`port`/`pont`/`villa` (nouns) are genuinely ambiguous.
5. **Top-4000 truncation.** No "does not occur" claim is made anywhere. Tokens pruned as
   hapax by `build_profile.py:130-133` are invisible; a street type appearing once in
   480 MB cannot be detected here.
6. **Train-side France is unmeasurable** — `by_country["France"].rows` = 0 in all three
   train files. Nothing in this report can be cross-validated against training data.
7. **No raw strings were opened** and no network was used, per the hard constraints.
   Every number above comes from `analysis_out/profile/test_s{1,2,3}.json` or from quoted
   lines of `_upstream/src/*.py`.

---

## Cross-check against the work order's `already_checked`

- **REFUTED-1 (French postcodes lost to the `pin` guard)** — not re-derived. This task
  does not touch `pin`. No claim either way.
- **REFUTED-2 / `FR_REGIONS` coverage** — not re-derived, and I quote **no** France-wide
  state-resolution rate. Section 1 uses `FR_REGIONS` only to establish *which tokens are
  discarded before tokenisation*, which is a statement about `normalize.py:333-335`, not
  about region adequacy. The 71.10% / 97.44% dispute is untouched and remains open.
- **The function-word finding** — I **confirm** the direction and **correct the
  magnitude**: 15.41% (s2) and 16.40% (all) are profile figures; pipeline-visible is
  ~10.68% (s2) and ~10.25% (all), and the stated *mechanism* (IDF dilution + blocking)
  is measurably weak to non-existent. I agree the words are unhandled; I do not agree
  that `ADDR_CANON_FR` is the place to fix them.
- **Component ordering (D126)** — not re-examined, as instructed.
- **`ADDR_CANON_COMMON`** — not audited; a02 owns it. The one cross-dictionary fact I
  rely on is that the France overlay is `{**COMMON-7, **FR}` (`normalize.py:321`) and
  that `ADDR_CANON_FR` overrides 4 COMMON keys.

**New defect found: yes — one, and it is quantitative rather than behavioural.**
The France region guard at `normalize.py:333-335` silently discards ~37.5% of the
function-word mass that the profile attributes to French addresses, so the headline
"function words are 16.40% of French address mass" overstates what the pipeline actually
processes by roughly a third. No behavioural defect was found in `ADDR_CANON_FR`
itself.

---

*Provenance: every figure derives from `analysis_out/profile/test_s{1,2,3}.json` fields
`addr_tokens["France"]` and `by_country["France"].rows`, plus quoted lines of
`_upstream/src/{normalize,keys,features,stage2}.py` (read-only) and
`build_profile.py`. The upstream dictionaries were extracted by regex over the dict
literals rather than hand-transcribed. Denominators are stated with every rate. No raw
`*.tsv` was opened; no network was used; nothing in `_upstream/` or the dataset was
modified.*






