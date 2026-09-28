# D120 â€” remaining gaps in `ADDR_CANON_COMMON`, the France path

## Headline

**The 7-key exclusion at `normalize.py:321` is a provable no-op, and four of the seven are doubly
dead. No change needed there. The real gap is one line wide and it is not in the exclusion list:
`ADDR_CANON_FR` corrupts three more French words that `ADDR_CANON_COMMON` already claims.**

1. **The exclusion cannot change any output, for any input string.** All 7 keys are **self-maps** in
   `ADDR_CANON_COMMON` (`COMMON[k] == k` for all 7). `normalize.py:347` evaluates `t = canon.get(t, t)`,
   so "key absent" and "key present mapping to itself" are *the same operation*. This is stronger than
   D086's diff-based proof and it needs no data at all.
2. **`st`, `ste`, `dr`, `n` are removed and then immediately re-added.** `ADDR_CANON_FR` is merged
   **after** the filter (line 321, `**ADDR_CANON_FR`), so those four resolve to their *French* values
   regardless of the exclusion.
3. **The one live consequence is `n` â†’ `""`**, 106,424 occurrences = **0.8874%** of French listed
   address mass â€” the largest token deletion in the effective French map. It is delivered by
   `ADDR_CANON_FR:213`, not by the exclusion, and it is *correct* French (*numÃ©ro*).
4. **New confirmed cross-language collisions D086 did not flag: `centre`â†’`ctr` (967),
   `village`â†’`vill` (770), `point`â†’`pt` (938).** With the already-known `est`(469), `col`(125),
   `fort`(1,923) that is **5,192 = 0.0433%** of listed mass being silently given an English sense
   (1,923+967+938+770+469+125 = 5,192; 5,192/11,992,918 = 0.0433%).

## 0. Denominators

| File | `rows` | `country_rows.France` | France listed addr mass | entries |
|---|---|---|---|---|
| train_s1/s2/s3 | 2,206,821 / 5,034,616 / 5,285,603 | 0 / 0 / 0 | â€” | â€” |
| test_s1 | 1,732,544 | 259,452 | 2,253,877 | 4,000 (at cap) |
| test_s2 | 4,887,273 | 703,378 | 4,745,780 | 4,000 (at cap) |
| test_s3 | 5,082,316 | 731,615 | 4,993,261 | 4,000 (at cap) |
| **pooled** | 11,702,133 | **1,694,445** | **11,992,918** | â€” |

France rows = 259,452 + 703,378 + 731,615 = **1,694,445**; `test_s1` is 15.31% of that, so no
s1-only rate is quoted anywhere below. All three `addr_tokens.France` lists are at the 4,000 cap
(`build_profile.py:140` `most_common(TOPN)`, `:27` `TOPN = 4000`); the 4000th entry has count
**23 / 58 / 60**, so absence below means **"not in the top 4000"**, never "does not occur".

**Component-skip check (per the D119 correction).** `normalize.py:333-335` matches a *whole*
comma-component against `STATE_MAPS` and then `continue`s, so tokens inside a matched component never
reach `atoks`. I verified no `FR_REGIONS` key contains any of the 7 excluded tokens, nor `est`,
`col`, `fort`, `centre`, `village`, `point` or `h`, as a standalone token: **0 hits** over all 14
region keys. Every count below is therefore genuinely pipeline-visible, not hidden by the state skip.

## 1. What the 7 keys are â€” source quoted

All 7 sit in the directional / street-abbreviation block:

```python
154 |    "street": "st", "st": "st", "str": "st", "strt": "st",
157 |    "drive": "dr", "dr": "dr", "drv": "dr",
171 |    "north": "n", "n": "n", "south": "s", "s": "s", "so": "s", "east": "e", "e": "e",
172 |    "west": "w", "w": "w", "northeast": "ne", "ne": "ne", "northwest": "nw", "nw": "nw",
174 |    "suite": "ste", "ste": "ste", "apartment": "apt", "apt": "apt", "floor": "fl", "fl": "fl",
```

**Abbreviation, full word, or both? â€” Abbreviations only.** The exclusion tuple
`(â€œstâ€,â€œsteâ€,â€œdrâ€,â€œnâ€,â€œsâ€,â€œeâ€,â€œwâ€)` contains only the 1-3 character short form of each concept and
never the full word. The full words `street`, `suite`, `drive`, `north`, `south`, `east`, `west` are
**not** excluded and stay live in the French map. Measured France occurrences of every one of them
(plus `str`, `strt`, `drv`, `so`): **0 in the top 4000 of all three test sources**. So the
abbreviation-only exclusion happens to be safe on this dataset â€” but by luck of the data, not design.

**All 7 are self-maps** (dict parsed directly out of the source: **177** `ADDR_CANON_COMMON` keys
recovered, **68** `ADDR_CANON_FR` keys, effective France map **219** keys, **63** of the 177 `COMMON`
keys are self-maps, and all 7 excluded keys are among them):

| key | `COMMON[k]` | self-map? | in `ADDR_CANON_FR`? | effective value for France |
|---|---|---|---|---|
| `st` | `st` | yes | yes â†’ `saint` (:207) | `saint` |
| `ste` | `ste` | yes | yes â†’ `sainte` (:207) | `sainte` |
| `dr` | `dr` | yes | yes â†’ `dr` (:208, *docteur*) | `dr` |
| `n` | `n` | yes | yes â†’ `""` (:213) | **`""` â€” deleted** |
| `s` | `s` | yes | no | *absent â†’ passthrough* |
| `e` | `e` | yes | no | *absent â†’ passthrough* |
| `w` | `w` | yes | no | *absent â†’ passthrough* |

## 2. Why the exclusion is a no-op â€” the code path, traced

`normalize.py:341-350`, the token loop:

```python
342 |        for t in _non_alnum.split(c.replace("'", "")):
343 |            if not t:
344 |                continue
345 |            if t.isdigit():
346 |                t = t.lstrip("0") or "0"
347 |            t = canon.get(t, t)
348 |            if t:
349 |                ctoks.append(t)
350 |        toks.extend(ctoks)
```

`canon.get(t, t)` returns `canon[t]` when the key is present, else `t` itself. So for a **self-map**
key `k`:

- key present, `canon[k] == k` â†’ returns `k`
- key absent â†’ returns `t`, which **is** `k`

**Both branches return the identical string.** Deleting a self-map from the dict is provably
information-preserving at this call site, for every possible input. No data needed, no dependence on
what `ADDR_CANON_FR` does. This is a strictly stronger argument than D086 Â§6, which built `eff` and
`eff'`, found 3 differences, and had to reason case by case about `s`/`e`/`w`.

For `st`/`ste`/`dr`/`n` the removal is *doubly* dead, because `ADDR_CANON_FR` is merged **after** the
filter and wins on conflict (line 321: `{**{â€¦COMMON minus 7â€¦}, **ADDR_CANON_FR}`):

```python
207 |    "saint": "saint", "st": "saint", "sainte": "sainte", "ste": "sainte",
208 |    "general": "gen", "gen": "gen", "gal": "gen", "docteur": "dr", "dr": "dr",
213 |    "no": "", "n": "", "numero": "", "null": "", "na": "",
```

## 3. The one live consequence: `n` â†’ `""`, at 0.8874%

| File | `n` count | % of that file's listed mass |
|---|---|---|
| test_s1 | 2,648 | 0.1175% |
| test_s2 | 51,535 | 1.0859% |
| test_s3 | 52,241 | 1.0462% |
| **pooled** | **106,424** | **0.8874%** of 11,992,918 |

Arithmetic: 2,648/2,253,877 = 0.1175%; 51,535/4,745,780 = 1.0859%; 52,241/4,993,261 = 1.0462%.

This is **not** the exclusion list's doing â€” `n` is deleted by `ADDR_CANON_FR:213` whether or not the
exclusion exists. It is the largest single token deletion in the effective French map, so it is worth
stating plainly. The s1â†’s2 jump is **19.7x** (2,648 â†’ 52,241), the same cross-source artefact
signature D086 Â§7 found for short tokens (Â§6 below).

**Inference, marked as such:** in French address text `n` is overwhelmingly the abbreviation for
*numÃ©ro* (`nÂ°`, `NÂ° 5`, `n 12`) â€” a house-number marker carrying no identity. Deleting it is
**correct behaviour, not a defect**, and the 19.7x jump is consistent with s2/s3 using `NÂ°` far more
than s1 rather than with any language fact. **I propose no change.** The point is that the exclusion
list's *intended* effect arrives by a different route, which is exactly why the list can go.

**Cannot verify** how many of the 106,424 are *north* rather than *numÃ©ro* â€” the profile has no
component structure. Labelled a gap, not estimated.

## 4. Does it pollute the IDF-weighted features? (`features.py:120-123`)

The chain, traced end to end rather than assumed:

`prep.py:13` `toks, nums, st, pin, cc = N.normalize_address(a, c)`
â†’ `prep.py:16` `out["atoks"].append(" ".join(toks))`
â†’ `features.py:98` `sp("q_atoks").alias("qa")`, `sp("s_atoks").alias("sa")`
â†’ `features.py:112` `lens("qa").alias("qa_len"), inter("qa","sa").alias("a_inter")`
â†’ `features.py:123-124` `a_jac`, `a_cont`
â†’ `features.py:129` `_weighted_overlap(â€¦, addr_idf, "wa")` â†’ `w_sum` at `:145`.

So canonicalisation does feed those features. **But the exclusion list contributes nothing to them**,
per Â§2. What matters instead is which `COMMON` keys actually *rewrite* a token on the French path.
Parsing all 177 `COMMON` keys, resolving each through the effective France map, and summing
`addr_tokens.France`:

| `COMMON` key | effective value | France count | % listed mass | verdict |
|---|---|---|---|---|
| `e` | *(absent)* | 45,410 | 0.3786% | passthrough â€” accent debris, see Â§6 |
| `s` | *(absent)* | 12,701 | 0.1059% | passthrough â€” accent debris, see Â§6 |
| `h` | `""` | 5,020 | 0.0419% | deleted (`COMMON:196`) |
| `fort` | `ft` | 1,923 | 0.0160% | **cross-language, CONFIRMED** |
| `centre` | `ctr` | 967 | 0.0081% | **cross-language, CONFIRMED (new)** |
| `point` | `pt` | 938 | 0.0078% | **cross-language, CONFIRMED (new)** |
| `village` | `vill` | 770 | 0.0064% | **cross-language, CONFIRMED (new)** |
| `est` | `estate` | 469 | 0.0039% | **cross-language, CONFIRMED** |
| `col` | `colony` | 125 | 0.0010% | **cross-language, CONFIRMED** |
| `w` | *(absent)* | 104 | 0.0009% | passthrough |

Set aside the three accent-debris passthroughs (`e`, `s`, `w`) and the `h` deletion, which the
already-settled "empty mappings are harmless" ruling covers. The **genuine cross-language rewrites
still live for France total 5,192 = 0.0433%** of listed mass (1,923+967+938+770+469+125).

**Three entries D086 did not flag, which I add here:**

- `centre` â†’ `ctr`, **967** (0.0081%). `COMMON:178` `"center": "ctr", "centre": "ctr"`. French
  *centre* is an ordinary French word (*centre-ville*, the *Centre* region). `ADDR_CANON_FR` has no
  entry. **CONFIRMED** collision.

## 5. Directionals: are `COMMON`'s and `FR`'s directional keys consistent?

The work order asks specifically whether a mismatch between the two tables' directional keys would
be a real defect. **Answer: the two tables are consistent â€” `ADDR_CANON_FR` contains no directional
key at all, so there is nothing to contradict. But no French compass word is in either table, and one
of the four is actively corrupted.**

Confirmed by parsing all 68 `ADDR_CANON_FR` keys (lines 199-214): no `nord`, `sud`, `est`, `ouest`, and
no `n`/`s`/`e`/`w` other than the `"n": ""` deletion at line 213.

| French compass word | France count | % listed mass | in COMMON? | in FR? | effective behaviour |
|---|---|---|---|---|---|
| `nord` | 152,011 | 1.2675% | no | no â€” it *is* an `FR_REGIONS` key | consumed as `state` at :333 |
| `sud` | 1,254 | 0.0105% | no | no | passthrough unchanged |
| `ouest` | 1,221 | 0.0102% | no | no | passthrough unchanged |
| `est` | 469 | 0.0039% | **yes â†’ `estate`** | no | **corrupted â†’ `estate`** |

**This is the one real inconsistency in the compass family.** `COMMON:186` reads
`"estate": "estate", "est": "estate"` â€” an *industrial estate* sense â€” and French `est` (= *east*) is
silently rewritten to it, while its three siblings `sud` / `ouest` / `nord` pass through untouched.
Four French compass words; exactly one is corrupted. **CONFIRMED**, 469 occurrences (0.0039%).

**Correction to D086.** D086 Tier-1 lists `ne`â†’northeast (6,465) and `se`â†’southeast (556) as CONFIRMED
collisions that treat French words as US compass points. At the token level that is **not true**.
`COMMON:172-173` define `"ne": "ne"` and `"se": "se"` â€” both are **self-maps**, so
`canon.get("ne","ne")` returns `ne` and the token is **byte-identical before and after**. The 6,465
`ne` and 556 `se` occurrences are not rewritten at all. The only residual effect is that `ne` becomes a
*recognised* token to `token_idf` (`features.py:13-20`) instead of an unknown one taking
`fill_null(12.0)` at `features.py:31,36`, which very slightly lowers its IDF. That is far weaker than
corruption. `nw` and `sw` are 0 in France.

Consequently D086's **Tier-1 total of 27,792 is overstated**: the confirmed-corruption subset is
**2,517** (`est` 469 + `col` 125 + `fort` 1,923) = 0.0210% of listed mass. I add 2,675 more
(`centre` 967 + `point` 938 + `village` 770) = 0.0223%, for a true figure of **5,192 = 0.0433%**.

## 6. The `e` / `s` mass is not directional signal

`e` = 45,410 and `s` = 12,701 look like the exclusion list's biggest beneficiaries. They are not.
`build_profile.py:28` uses `TOKEN_RE = re.compile(r"[a-z0-9]+")` against `ba.lower()` â€” **without
`strip_accents`** â€” whereas `normalize.py:317` calls `strip_accents()` *before* tokenising. Every
accented French word is therefore shredded by the profiler into fragments that the real pipeline keeps

## 7. Dead weight and coverage of `ADDR_CANON_COMMON` for France

- **177 keys** total; **144 of 177 have zero occurrences** in the French top-4000 of all three test
  sources. The entire India-specific block (`COMMON:190-195`: `bengaluru`, `bombay`, `gurugram`,
  `trivandrum`, `calcutta`, `madras`, `poona`, `odisha`, `keralam`, `ahmadabad`, `vishakhapatnam`,
  `vizag`, `mysuru`, `mangaluru`, `cochin`, `belagavi`, `kozhikode`, `calicut`) plus the
  `nagar`/`taluk`/`tq`/`phase`/`sector` group are dead weight **for France only**.
  **This is by design and costs nothing at runtime** â€” `canon.get` is a dict lookup. **Do not "fix" it
  by deleting them: they are load-bearing for India.** No defect, no recommendation.
- All 177 keys together account for **628,736 = 5.243%** of French listed address mass, dominated by
  the *agreeing* overrides: `avenue` 126,497, `no` 72,021, `av` 57,361, `boulevard` 38,275,
  `bd` 25,273, `route` 17,932, `place` 13,363, `square` 4,933, `na` 1,397 â€¦
  Overridden-and-agreeing total **550,775**; overridden-and-*changed* = `n` (106,424 â†’ `""`),
  `st` (25,454 â†’ `saint`), `ste` (591 â†’ `sainte`).
- `st` â†’ `saint` is **correct** for France: `COMMON` meant *street*, `ADDR_CANON_FR:207` means
  *saint*, and French `saint` occurs 141,364 times pooled. This is the exclusion list's second
  genuinely successful case, and it works **because of the FR override, not because of the exclusion**.

### `ADDR_GENERIC` interaction â€” a real asymmetry, but out of scope

`keys.py:14-19` defines a 62-entry `ADDR_GENERIC` list, applied at `keys.py:39`
(`filter(~pl.element().is_in(ADDR_GENERIC))`) to strip generic tokens before blocking keys are built.
Three of the seven excluded keys are in it (`st`, `ste`, `dr`), as is `rue`. The *French* canonical
values mostly are not:

| FR canonical value | France count | in `ADDR_GENERIC`? |
|---|---|---|
| `rue` | 728,583 | yes |
| `impasse` | 21,102 | yes |
| `ave` | 21,614 | yes |
| `allee` | 17,779 | yes |
| `chemin` | 15,244 | yes |
| `pl` | 12,989 | yes |
| `ter` | 7,896 | yes |
| `blvd` | 6,046 | yes |
| **`saint`** | **141,364** | **NO** |
| **`bis`** | **52,072** | **NO** |
| `rte` | 11,995 | NO |
| `res` | 8,340 | NO |
| `quai` | 8,089 | NO |
| `sainte` | 7,486 | NO |
| `crs` | 4,520 | NO |
| `bat` | 1,767 | NO |
| `gen` | 1,227 | NO |
| `mal` | 612 | NO |
| `pres` | 496 | NO |

`saint` (1.1787% of listed mass) and `bis` (0.4342%) are the two largest French address tokens reaching
`keys.py:39` unfiltered. `saint` is a toponym prefix (*Saint-Jacques*) and is genuinely discriminative,
so filtering it would be **wrong**. `bis` is the French *bis* (secondary building, `12 bis`) and is
noise. **This concerns `keys.ADDR_GENERIC`, not `ADDR_CANON_COMMON`**, so it is outside this work
order â€” recorded for whoever owns blocking keys, with counts, and **no defect claimed**.


## 8. Direct answers to the work order's five questions

1. **Which entries are the 7 keys, and are they abbreviations or full words?**
   Abbreviations only, all 1-3 characters: `st` (street), `ste` (suite), `dr` (drive), `n` (north),
   `s` (south), `e` (east), `w` (west) â€” `normalize.py:154, 157, 171-172, 174`. No full word is excluded.
2. **What does France do with those tokens instead?**
   `st`â†’`saint`, `ste`â†’`sainte`, `dr`â†’`dr` (*docteur*), `n`â†’`""` (deleted) â€” all via
   `ADDR_CANON_FR:207, 208, 213`, merged *after* the filter at line 321. `s`/`e`/`w` have no FR entry
   and pass through untouched via `canon.get(t, t)` at line 347.
3. **Does dropping them lose information or create a gap?**
   **No.** All 7 are self-maps, so removal is provably information-preserving. The `n`â†’`""` deletion is
   real but comes from `ADDR_CANON_FR`, not the exclusion, and is semantically correct French. It does
   reach the IDF features via `prep.py:16` â†’ `features.py:98, 112, 123-124, 129`, but the exclusion
   list contributes exactly zero to that chain.
4. **Are the two tables' directional keys consistent?**
   **Yes** â€” `ADDR_CANON_FR` has no directional key at all, so nothing can conflict. The real gap is
   that *no* French compass word is in either table, and `est` is actively corrupted to `estate` (469)
   while `nord`, `sud`, `ouest` pass through.
5. **Is dropping them harmless?**
   **Yes, provably and completely** â€” delete the tuple at line 321 and no output changes for any input
   string. **Recommendation: leave line 321 alone.**

## Recommendations, in confidence order

- **CONFIRMED â€” no change to the exclusion list.** Provably a no-op (Â§2). Editing it manufactures risk
  for zero gain. Leaving it in place also documents intent, and since `ADDR_CANON_COMMON` is a shared
  table, removing the guard would let a future *US-side* edit to `st`/`dr` silently change French
  behaviour.
- **CONFIRMED â€” add `"est": "est"` to `ADDR_CANON_FR`** (469, 0.0039%). Cheapest correct fix; matches
  exactly how `st`/`ste`/`n` are already resolved. Fixes the only corrupted member of the French
  compass.
- **CONFIRMED â€” add `centre` (967), `point` (938), `village` (770) to `ADDR_CANON_FR`.** Same defect
  class, same fix shape. With `est`: 3,144 = 0.0262% of listed mass.
- **CONFIRMED â€” `fort`â†’`ft` (1,923, 0.0160%) is the largest single cross-language rewrite** and has the
  strongest cross-country evidence (1,923 FR vs 9,716 US / 1,120 India in D086's table). Already in
  D086; restated here so the number is in the sidecar.
- **Do NOT** add French ordinals, street types or function words to `ADDR_CANON_COMMON`. D086 measured
  the entire candidate set at 0.4566% of listed mass against a 16.9-23.9% geography bucket. French
  entries belong in `ADDR_CANON_FR`; putting them in `COMMON` would apply them to US and India.
  (The French function-word claim is separately retracted by D119 â€” no function words warranted.)
- **LIKELY â€” fix `build_profile.py:28`** to `strip_accents()` before `TOKEN_RE`, matching
  `normalize.py:317`. Confirmed here via the 71.9x `r` cross-source ratio. Until this is fixed, **no
  short-token (<4 char) claim from these profiles is trustworthy**, including the `e`/`s` figures in
  this document.

## Gaps and limits â€” stated, never estimated

1. **No component structure.** `addr_tokens` is a flat bag per country; `,`/`;` boundaries are gone.
   Every rate here is a *token* rate, not a row rate. I cannot say how many *rows* contain `est`.
2. **Top-4000 truncation.** All three France lists are at the cap. "144 of 177 zero-occurrence" means
   **not in the top 4000**; the 4000th entry has count 23/58/60, so any token with fewer than 23
   occurrences in test_s1 is invisible.
3. **Hapaxe pruning.** `build_profile.py:45-48` drops count-1 tokens periodically, so listed mass
   under-counts by an unknown amount.
4. **Downstream scoring effect unmeasured.** I can trace `atoks` into `features.py` but cannot quantify
   how much any rewrite moves the model score. Every "expected effect" statement is an INFERENCE.
5. **`n` sense unresolved.** I cannot separate *numÃ©ro* from *north* within the 106,424. Labelled.
6. **Train is France-free** (`country_rows.France` = 0 in all three train profiles), so no French
   dictionary entry can be validated against a ground truth.

## Relationship to D086, and to the settled findings

**Confirmed independently (built on, not repeated):** the exclusion list is a no-op (D086 Â§6 â€” I have
the stronger data-free proof in Â§2); the `est`/`col`/`fort` collisions, at identical counts
469/125/1,923; the 11,992,918 pooled French listed mass; the `build_profile.py:28` accent defect; that
French dictionary entries belong in `ADDR_CANON_FR`, not `ADDR_CANON_COMMON`.

**Correction to D086:** `ne` and `se` are self-maps (`COMMON:172-173`) and are **not** rewritten, so
the Tier-1 corruption subset is 2,517 rather than the stated 27,792.

**Added beyond D086:** `centre`â†’`ctr` (967), `point`â†’`pt` (938), `village`â†’`vill` (770); the
`n`â†’`""` deletion at 0.8874%; the `ADDR_GENERIC`/`saint`+`bis` observation; the 144-of-177 dead-weight
census; and that the exclusion list covers abbreviations only while all seven full words are absent
from the French data.

**Not re-derived, per the brief:** US_STATES / IN_STATES / FR_REGIONS coverage; the France-postcode
refutation; `pin_eq` / `alt_tset`; France blocking caps; address component order; the empty-mapping
ruling; the LEET ordinal defect (D120 touches no shared normalisation code, so the enlarged
`24hr`/`1st` scope does not apply here); and the D119 function-word retraction.

whole. The cross-source signature confirms it:

| token | s1 | s2 | s3 | pooled | s3/s1 |
|---|---|---|---|---|---|
| `r` | 2,543 | 182,872 | 182,809 | 368,224 | **71.9x** |
| `n` | 2,648 | 51,535 | 52,241 | 106,424 | 19.7x |
| `d` | 8,403 | 20,787 | 21,626 | 50,816 | 2.6x |
| `b` | 2,642 | 7,286 | 7,757 | 17,685 | 2.9x |
| `s` | 2,648 | 4,847 | 5,206 | 12,701 | 2.0x |
| `e` | 12,840 | 15,611 | 16,959 | 45,410 | 1.3x |

`e` and `s` are largely fragments of *hÃ´tel*, *gÃ©nÃ©ral*, *Ã©cole* â€” not the French compass words. Since
both pass through unchanged anyway, no conclusion changes; it only means the exclusion list's largest
apparent beneficiaries do not exist.

- `village` â†’ `vill`, **770** (0.0064%). `COMMON:189` `"village": "vill"`. French *village* is a
  standard place word, and *village* also occurs inside French place names. **CONFIRMED** collision.
- `point` â†’ `pt`, **938** (0.0078%). `COMMON:168` `"point": "pt"`. French *point* (*point de vue*,
  *Rendez-Vous Point*). **CONFIRMED** collision.

Same defect class as `est`, same fix shape (`ADDR_CANON_FR` entry, not `ADDR_CANON_COMMON`).


**Net effect of the exclusion list on France: exactly zero tokens changed, for every input string.**

For scale, the mass that actually passes through these 7 keys in France is
**190,940 = 25,454(`st`) + 591(`ste`) + 256(`dr`) + 106,424(`n`) + 12,701(`s`) + 45,410(`e`) +
104(`w`)** = 1.5921% of the 11,992,918 listed French address tokens. Not one of those 190,940
occurrences is altered by removing the keys, because for a self-map `canon[k] == k` and
`canon.get(k, k) == k` are the same return value.


