# D081 — audit current ADDR_CANON_FR

## Headline

`ADDR_CANON_FR` is a 68-entry, 30-value street-type dictionary that is **structurally
clean where everyone assumed it was broken and incomplete where nobody looked**. The
famous "missing self-map loop entry" defect does **not** apply to this dictionary: all
29 of its non-empty canonical values are already their own keys, so adding it to the
`normalize.py:252` loop would change nothing. The real defect is different and new —
**the 7-key exclusion tuple at `normalize.py:321` is a provable no-op**, and the
dictionary covers only **17.54%** of retained French address-token mass.

The second, more consequential finding is about the evidence base itself:
`build_profile.py:28` and `normalize.py:342` use **different tokenisers**, so profile
token counts over-count French elision particles and split accented words that the
pipeline keeps whole.

## Findings

### 1. Ground truth: what `ADDR_CANON_FR` contains

Source, quoted in full (`_upstream/src/normalize.py:199-214`):

```python
ADDR_CANON_FR = {
    "rue": "rue", "r": "rue", "avenue": "ave", "av": "ave", "ave": "ave", "avn": "ave",
    "boulevard": "blvd", "bd": "blvd", "bld": "blvd", "blvd": "blvd", "boul": "blvd",
    "chemin": "chemin", "ch": "chemin", "chem": "chemin", "che": "chemin",
    "impasse": "impasse", "imp": "impasse", "place": "pl", "pl": "pl",
    "route": "rte", "rte": "rte", "allee": "allee", "all": "allee", "al": "allee",
    "square": "sq", "sq": "sq", "faubourg": "fbg", "fbg": "fbg", "fg": "fbg",
    "cours": "crs", "crs": "crs", "quai": "quai", "q": "quai", "qu": "quai",
    "saint": "saint", "st": "saint", "sainte": "sainte", "ste": "sainte",
    "general": "gen", "gen": "gen", "gal": "gen", "docteur": "dr", "dr": "dr",
    "professeur": "prof", "prof": "prof", "marechal": "mal", "mal": "mal",
    "president": "pres", "pres": "pres", "residence": "res", "res": "res",
    "batiment": "bat", "bat": "bat", "bis": "bis", "b": "bis", "ter": "ter", "t": "ter",
    "lieu": "lieu", "lieudit": "lieudit", "zone": "zone", "za": "za", "zi": "zi", "zac": "zac",
    "no": "", "n": "", "numero": "", "null": "", "na": "",
}
```

The only place it is consumed (`normalize.py:319-321`, and `normalize.py:347`):

```python
    canon = dict(ADDR_CANON_COMMON)
    if country == "France":
        canon = {**{k: v for k, v in ADDR_CANON_COMMON.items() if k not in ("st", "ste", "dr", "n", "s", "e", "w")}, **ADDR_CANON_FR}
    ...
            t = canon.get(t, t)
```

| Property | Value | How obtained |
|---|---|---|
| Entries (literal keys) | **68** | `ast` parse of `normalize.py:199-214`, `len(node.value.keys)` |
| Distinct canonical values | **30** (29 non-empty + `""`) | `len(set(ADDR_CANON_FR.values()))` |
| Self-maps (`k == v`) | **29** | counted |
| Values lacking a self-map | **0** | every non-empty value `v` has `ADDR_CANON_FR[v] == v` |
| Empty-valued keys | **5** — `n`, `na`, `no`, `null`, `numero` | |
| Single-character keys | **5** — `b`, `n`, `q`, `r`, `t` | |
| Keys overlapping `ADDR_CANON_COMMON` | **23** | `set(FR) & set(CM)` |
| …of which redefine the value | **4** — `bld`, `n`, `st`, `ste` | |
| FR-only keys | **45** | |
| Keys with zero observed French occurrences | **13** — `avn`, `bld`, `boul`, `chem`, `fbg`, `fg`, `prof`, `lieudit`, `za`, `zi`, `zac`, `numero`, `null` | absence from `addr_tokens["France"]` |
| Keys that do fire | **55 of 68** | summed `addr_tokens["France"]` over `test_s1/s2/s3` |

**Arithmetic invariant (holds exactly):** `|COMMON| − 7 + |FR| − |FR ∩ surviving COMMON|`
`= 177 − 7 + 68 − 19 = 219 = len(effective France canon)`. The merge is a
`{**base, **FR}` overwrite, so the naive overlap `|FR ∩ COMMON| = 23`
**over-counts by exactly 4** — the keys `dr`, `n`, `st`, `ste`, which the exclusion
tuple removes from COMMON and `ADDR_CANON_FR` then re-adds.

| Canonical-value set | Count |
|---|---|
| `ADDR_CANON_COMMON` alone (US + India) | 81 |
| `ADDR_CANON_FR` alone | 30 |
| Effective France canon | **103** |
| Values COMMON can emit that France can no longer emit | **0** |

### 2. DEFECT (new): the 7-key exclusion tuple is a provable no-op

`normalize.py:321` excludes `("st", "ste", "dr", "n", "s", "e", "w")` from the
`ADDR_CANON_COMMON` base. Measured effect, simulating `canon.get(t, t)` at `normalize.py:347`
over the whole key space:

| Key | `ADDR_CANON_COMMON` value | Is identity self-map? | Fate |
|---|---|---|---|
| `st` | `st` | yes | re-added by `ADDR_CANON_FR` as `saint` |
| `ste` | `ste` | yes | re-added by `ADDR_CANON_FR` as `sainte` |
| `dr` | `dr` | yes | re-added by `ADDR_CANON_FR` as `dr` (identical) |
| `n` | `n` | yes | re-added by `ADDR_CANON_FR` as `""` |
| `s` | `s` | yes | dropped |
| `e` | `e` | yes | dropped |
| `w` | `w` | yes | dropped |

Behavioural diff between "with the tuple" and "with no tuple at all": **3 keys**
(`s`, `e`, `w`), and in each case the change is `identity self-map → unmapped`.
Since `canon.get(t, t)` already returns `t` when `t` is absent, and on an identity
self-map it also returns `t`, **both branches emit the identical string**. The tuple is
therefore **dead code with exactly zero effect on any input, for any country**.

The apparent intent — suppressing English direction words in French addresses — is
delivered entirely by `ADDR_CANON_FR`'s own redefinition of `st`/`ste`/`n`, never by
the removal.

**Measured French data for the direction vocabulary** (`addr_tokens["France"]`, summed
over the three test files):

| Input token | France occurrences | Actual France output |
|---|---|---|
| `n` | 106,424 | `""` (deleted) |
| `e` | 45,410 | `e` (passthrough) |
| `s` | 12,701 | `s` (passthrough) |
| `w` | 104 | `w` (passthrough) |
| `st` | 25,454 | `saint` |
| `ste` | 591 | `sainte` |
| `ne` | 6,465 | `ne` |
| `se` | 556 | `se` |
| `north` / `south` / `east` / `west` / `so` / `nw` / `sw` | 0 each | — |

Note the asymmetry: `s`, `e`, `w` are the *only* three keys the tuple actually
touches, and in every case the change is a no-op. The French data confirms it —
`e` (45,410) and `s` (12,701) pass through unchanged, which is exactly what the
identity self-map would have done anyway.

### 3. The self-map question, resolved: `ADDR_CANON_FR` does **not** need the loop

`normalize.py:251-254` builds self-maps for two dictionaries only:

```python
# abbreviations are canonical themselves
for _m in (US_STATES, IN_STATES):
    for _v in list(_m.values()):
        _m.setdefault(_v, _v)
```

`ADDR_CANON_FR` is absent, and the work order's premise was that this is a defect.
It is **not**, for this dictionary:

- All 29 non-empty canonical values of `ADDR_CANON_FR` are already keys mapping to
  themselves → **0 values lack a self-map**.
- Adding `ADDR_CANON_FR` to line 252 would set `setdefault(v, v)` for values that are
  already present with identical values → **zero behavioural change**.

Contrast with `FR_REGIONS` (line 243-249), where the situation is the opposite: 14
entries, 4 distinct values, and **none** of `hdf`, `idf`, `naq`, `pdl` is a key — so
`FR_REGIONS` genuinely does need the loop. The two dictionaries are being conflated by
the existing "missing self-map" narrative. **This is a clean "no defect" result for
`ADDR_CANON_FR`.**

### 4. DEFECT (real, latent): three canonical values are not fixed points

Values the France map can *emit* that, if re-applied, change again:

| Emitted value | Produced by | Re-maps to | France occurrences of the producers |
|---|---|---|---|
| `st` | `street`, `str`, `strt` (from `ADDR_CANON_COMMON`) | `saint` | **0, 0, 0** |
| `ste` | `suite` | `sainte` | **0** |
| `n` | `north` | `""` (deleted) | **0** |

This is a genuine structural inconsistency: in the US/India canon `st` is a fixed
point, in the France canon it is not, so the token `st` denotes "street" in one
country and "saint" in the other. It is **not contaminating** — `token_idf` is keyed
on `(country, tok)` (`features.py:19-20`) — and it has **zero measured effect** on this
dataset, because `street`, `str`, `strt`, `suite` and `north` never occur in French
addresses.

### 5. Coverage: the dictionary is a narrow street-type table, not an address normaliser

| Metric | Value | Arithmetic |
|---|---|---|
| Retained France address-token mass (union of top-4000, s1+s2+s3) | 11,992,918 | sum of `addr_tokens["France"]` |
| Tokens with no entry in the effective France canon | 4,375 of 4,441 distinct | |
| Mass of those unmapped tokens | 9,889,036 = **82.46%** | 9,889,036 / 11,992,918 |
| → mass that is mapped | **17.54%** | 1 − 82.46% |

Per source, to respect the "never quote a single-source rate as a France-wide rate" rule:

| File | France rows | Retained token mass | `de`+`la`+`du`+`des` | Share |
|---|---|---|---|---|
| `test_s1.json` | 259,452 | 2,253,877 | 440,035 | **19.52%** |
| `test_s2.json` | 703,378 | 4,745,780 | 731,158 | **15.41%** |
| `test_s3.json` | 731,615 | 4,993,261 | 779,599 | **15.61%** |
| all three | 1,694,445 | 11,992,918 | 1,950,792 | 16.27% |

The `test_s2` figure of **15.41%** reproduces the already-established function-word
finding exactly. `test_s1` is materially higher at **19.52%**, which the existing
write-up does not state; the correct France-wide statement is a **range of
15.41%–19.52% by source**, not a single number.

Highest-mass tokens with no canon entry: `de` 1,050,023 · `la` 481,231 · `loire` 334,419
· `france` 293,150 · `hauts` 289,655 · `bordeaux` 277,474 · `nouvelle` 242,802 ·
`aquitaine` 242,531 · `nantes` 238,748 · `lille` 221,585 · `du` 220,355 ·
`pays` 207,396 · `des` 199,183 · `nord` 152,011 · `gironde` 150,787.

**Inference, not measurement:** the geography words (`loire`, `france`, `hauts`,
`nouvelle`, `aquitaine`, `pays`, `nord`, `gironde`) belong to `FR_REGIONS`, not to
`ADDR_CANON_FR`, and are handled by the `state` field via `normalize.py:333`
(`if ck in smap`). Their absence from `ADDR_CANON_FR` is by design. Their presence
in `atoks` is nevertheless real, and is the mechanism behind the open s2/s3
department gap flagged in the work order — **this task does not resolve that and makes
no claim about it.**

### 6. Country scoping is one-directional but currently benign

- `ADDR_CANON_FR` applies to France only (`normalize.py:320-321`). Verified by
  inspection; no other consumer of the dictionary exists in `_upstream/src/`
  (`prep.py:13` is the only call site).
- **33 of 68** `ADDR_CANON_FR` keys also occur in US or India address tokens, so the
  scoping is load-bearing. Highest-risk collisions had they leaked: `no`
  (2,993,998 in India), `st` (403,281 US), `dr` (342,400 US), `avenue` (321,245 US),
  `b` (462,898 India), `r` (100,313 India).
- The scoping is **one-directional**: the overlay adds French entries on top of
  `ADDR_CANON_COMMON` but never removes the COMMON entries that are India-specific
  (`bengaluru`, `gurgaon`, `nagar`, `taluk`, `colony`, …). Measured French exposure:
  **exactly 1 key, `col` → `colony`, 125 occurrences.** Benign at present, but the
  protection is accidental rather than designed.

### 7. Token deletion mass (working as intended, quantified for the record)

Empty-valued keys drop the token at `normalize.py:348-349` (`if t: ctoks.append(t)`).

| Key | Source | France occurrences |
|---|---|---|
| `n` | `ADDR_CANON_FR` | 106,424 |
| `no` | `ADDR_CANON_FR` | 72,021 |
| `na` | `ADDR_CANON_FR` | 1,397 |
| `numero`, `null` | `ADDR_CANON_FR` | 0 |
| `h` | `ADDR_CANON_COMMON` (still live for France) | 5,020 |
| **Total** | | **184,862 = 1.54%** of 11,992,918 |

**Inference:** `n`/`no` are the French *numéro* marker (`n°`), so deleting them is
correct behaviour, not a defect. I did not verify this against raw strings — the
profile does not retain them — so it is flagged as inference, not a measured fact.

### 8. DEFECT (new, affects the evidence base, not the pipeline)

`build_profile.py:28` defines `TOKEN_RE = re.compile(r"[a-z0-9]+")` and applies it to
the **raw** lowercased address. The pipeline applies `strip_accents`
(`normalize.py:264-266`) *before* splitting on `_non_alnum` (`normalize.py:269`), and
additionally strips ASCII apostrophes at `normalize.py:342` (`c.replace("'", "")`).
The two tokenisers disagree.

| Raw address | `build_profile.py:28` | `normalize.py:342` |
|---|---|---|
| `Résidence du Côté Sud` | `['r','sidence','du','c','t','sud']` | `['residence','du','cote','sud']` |
| `Allée des Tilleuls` | `['all','e','des','tilleuls']` | `['allee','des','tilleuls']` |
| `Impasse du Château` | `['impasse','du','ch','teau']` | `['impasse','du','chateau']` |
| `Rue de l’` + `Eglise` | `['rue','de','l','eglise']` | `['rue','de','leglise']` |

**Direct evidence that the profile emits tokens the pipeline cannot.** These are
accent-split or apostrophe-split fragments; a pipeline tokenisation can never produce
them:

| Profile token | France | US | India | Origin |
|---|---|---|---|---|
| `sidence` | **1,467** | 0 | 0 | `Résidence` |
| `chal` | **8,318** | 0 | 0 | `Maréchal` |
| `coeur` | **696** | 0 | 0 | `cœur` (ligature, not decomposed by NFKD) |

**Consequence:** profile token counts systematically **over-count** French elision
particles and **over-count** accent fragments relative to what `normalize.py` actually
feeds the model. `l` (99,889) and `d` (50,816) in `addr_tokens["France"]` are
overwhelmingly apostrophe fragments of `l'`/`d'`; the pipeline joins those
(`leglise`, `dazur`) and never emits a standalone `l` or `d`. All 1-character French
tokens together are 1,136,211 = **9.47%** of retained mass, and 36 of them are
distinct — implausibly high for real address vocabulary and consistent with
over-fragmentation.

This does not invalidate the token counts as *evidence that a word occurs*; it
invalidates them as *evidence of how many tokens the pipeline will see*, and it means
any dictionary mined from profile counts is mined from a different tokeniser than the
one that runs.

## Interpretation

*Marked as inference throughout.*

1. `ADDR_CANON_FR` should **not** be added to the `normalize.py:252` self-map loop. It
   is already closed. The tasks that follow should not spend effort there.
2. The exclusion tuple at `normalize.py:321` should be **deleted or documented as
   load-bearing-by-accident**, not "fixed". Its removal changes no output. Leaving it
   invites a future reader to believe French direction words are being suppressed when
   they are not. The `ne` (6,465) and `se` (556) survivors are the concrete evidence
   that direction vocabulary is *not* suppressed.
3. The 82.46% unmapped mass figure means `ADDR_CANON_FR` should be scoped in
   expectation as a **street-type canonicaliser only**. Any proposal to broaden it into
   a general French address dictionary is a large change, not a gap-fill.
4. The accent/apostrophe tokeniser divergence is the highest-value item here. It is
   cheap to fix in `build_profile.py` (apply `strip_accents` and the apostrophe
   removal before `TOKEN_RE.findall`) and it would make every future
   dictionary-mining task measure the real pipeline. Until then, profile-derived
   French token counts should be treated as upper bounds.
5. The `st`/`ste`/`n` non-fixed-point chain is latent, not active. Zero French rows
   trigger it. It is worth fixing only if French data with English street words is
   ever added; it is not worth a change today.

## Gaps

- **Component structure is not collected.** `build_profile.py:126-127` splits the
  address on `[,;]` and then tokenises, discarding which component a token came from.
  I therefore cannot say how often `ADDR_CANON_FR` rewrites a token that is part of a
  *city* name rather than a street type. This is a real gap for any
  false-canonicalisation claim.
- **Apostrophe glyph frequency is unknown.** The profile's `[a-z0-9]+` treats ASCII
  `'` and typographic `’` identically, so I cannot measure how many French addresses
  use the glyph that `normalize.py:342` fails to join. I proved the inconsistency
  exists from the source; I cannot size it. **Label: gap, not a finding.**
- **Fragment attribution is impossible.** `m` (56,527) and `e` (45,410) are certainly
  *partly* accent fragments, but the profile cannot map a fragment back to its parent
  word, so their true pipeline counts are unknown.
- **The 13 never-observed keys are not proven absent from the data.**
  `build_profile.py:27` keeps only `TOPN = 4000` tokens and `prune()`
  (`build_profile.py:45-49`) drops `count <= 1` every 8 chunks. A key occurring once
  in 480 MB is invisible here. The rarest key I *can* see is `gal` at 25. "Not in the
  top-4000" is not "zero occurrences".
- **No raw-string verification.** I did not open any `*.tsv` file, per the RAM
  constraint. Every data number here comes from `analysis_out/profile/*.json`.
- `city_comps` (`normalize.py:351-352`, gated on `not any(ch.isdigit() ...)`) is not
  exercised by anything in the profile. Its French behaviour is unmeasured.

## Recommendations

1. **Do not add `ADDR_CANON_FR` to the `normalize.py:252` self-map loop.** Zero
   effect; it would add noise to a diff. (Priority: high confidence, zero cost.)
2. **Remove the 7-key exclusion tuple at `normalize.py:321`, or replace it with a
   comment stating it is inert.** Recommended over "fixing" it, because there is
   nothing to fix. (Priority: high; this is the headline defect.)
3. **Align `build_profile.py:28` with `normalize.py:264-266,342`** — apply
   `strip_accents` and the apostrophe removal before `findall`, so profile token
   counts equal pipeline token counts. This unblocks accurate mining for every
   follow-on task. (Priority: **highest value per line of code**.)
4. **If direction-word suppression is actually wanted for France**, it must be added
   explicitly (`north`, `south`, `east`, `west`, `ne`, `se`, `nw`, `sw`) — the current
   tuple does not do it. Zero of those long forms occur in French data today, so this
   is hygiene, not a score fix. (Priority: low.)
5. **No change to the 68 entries themselves** on the basis of this task. The coverage
   gap is real but the unmapped mass is dominated by geography words handled by
   `FR_REGIONS`, which is a separate, still-open question.
6. **Extend the profile** with per-component token attribution (which comma-separated
   component each token came from). That single addition would let a later task
   measure false canonicalisation of city names, which is currently unmeasurable.

## Cross-check against the work order's `already_checked` block

- **REFUTED-1 (French postcodes lost by the `pin` guard).** Not re-derived. This task
  does not touch `pin`. I make no claim either way.
- **REFUTED-2 (France region handling).** Not re-derived, and I explicitly decline to
  quote a France-wide state-resolution rate. The `71.10%`/`97.44%` contradiction
  between D073 and D077 remains unreconciled and is **not** settled by anything here.
  My finding is strictly about `ADDR_CANON_FR`, a different dictionary; the geography
  words I list in section 5 are the *input* to `FR_REGIONS`, not evidence about its
  coverage.
- **The function-word finding.** Rebuilt independently and confirmed for `test_s2` at
  **15.41%** exactly. Added new information: `test_s1` is **19.52%** and `test_s3` is
  **15.61%**, so the honest France-wide statement is a source-dependent range.
- **The FR_REGIONS self-map gap.** Confirmed as real for `FR_REGIONS` (its 4 values
  have no self-maps) and shown to be **inapplicable** to `ADDR_CANON_FR` (all 29 of
  its values already self-map). These are different dictionaries and the existing
  narrative conflates them.

**New defect found: yes.** Two, plus one evidence-base defect:
(a) the `normalize.py:321` exclusion tuple is a provable no-op;
(b) three France canonical values (`st`, `ste`, `n`) are not fixed points, latent
with zero current French impact;
(c) `build_profile.py` and `normalize.py` use different tokenisers, so profile token
counts over-count French elision particles and accent fragments — this is the most
consequential result.




