# D070 — audit current FR_REGIONS

*Ground truth for the follow-up tasks. Source of record: `_upstream/src/normalize.py` at git
`8445b7f` (verified pristine, see Provenance). This file replaces an earlier draft of the same
name that was structurally out of order and contained two arithmetic errors, both corrected
below and listed in Provenance.*

## Headline

`FR_REGIONS` (`normalize.py:243-249`) holds **14 entries over 4 distinct canonical values**
(`hdf`, `idf`, `naq`, `pdl`), against 52/52 for `US_STATES` and 49/37 for `IN_STATES`. The
structural audit is mostly **clean**: no empty values, no empty keys, **zero overlap** with
either other state map, and **exhaustively correct** country scoping (all six profile files
satisfy `sum(country_rows.values()) == rows` exactly). Two defects are real: the **missing
self-map** at line 252 (`CONFIRMED` as code, **zero** measurable effect, independently
re-confirmed), and a **NEW** order-dependence defect nobody has looked for — line 334 assigns
`state = smap[ck]` with **no `break`**, so a matched component is not just consumed, it
**overwrites** any earlier match, and `'Paris, Hauts-de-France'` resolves `hdf` while
`'Hauts-de-France, Paris'` resolves `idf`.

**The single most important number for the tasks that follow:** on test s2/s3 French addresses
state a **departement** as often as a region — `229,735 / 703,378 = 0.3266` departement tokens
per France row (an upper bound on 32.66% of France s2 rows). The 9 departement keys are
load-bearing, not decoration, so the "obvious" fix of thinning `FR_REGIONS` to 18 regions would
be a large regression.

## Findings

### F1 — Static contents, quoted verbatim from source

`normalize.py:243-249`:

```python
FR_REGIONS = {
    "hauts de france": "hdf", "nord": "hdf", "pas de calais": "hdf", "somme": "hdf",
    "aisne": "hdf", "oise": "hdf",
    "nouvelle aquitaine": "naq", "gironde": "naq", "landes": "naq",
    "pays de la loire": "pdl", "loire atlantique": "pdl", "vendee": "pdl",
    "ile de france": "idf", "paris": "idf",
}
```

`normalize.py:250-254`, which is where the self-map defect lives:

```python
STATE_MAPS = {"US": US_STATES, "India": IN_STATES, "France": FR_REGIONS}
# abbreviations are canonical themselves
for _m in (US_STATES, IN_STATES):
    for _v in list(_m.values()):
        _m.setdefault(_v, _v)
```

Measured two independent ways that agree exactly: (a) `ast.literal_eval` of the module-level
assignments, which sees the dicts *as written*; (b) `importlib` loading the real module with a
stubbed `polars`, which sees the dicts *after* the line-252 loop has mutated them.

| Property | `FR_REGIONS` | `US_STATES` | `IN_STATES` | How measured |
|---|---|---|---|---|
| Entries, as written | **14** | 52 | 49 | `len()` of AST literal |
| Distinct canonical values | **4** | 52 | 37 | `len(set(values))` |
| Distinct values, listed | `hdf, idf, naq, pdl` | — | — | `sorted(set(...))` |
| Self-maps as written (value is also a key) | **0** | 0 | 0 | `[v for v in values if v in d]` |
| Entries **after** the line-252 loop | **14** | 104 | 86 | `len()` post-import |
| Self-maps after the loop | **0** | 104 | 86 | post-import |
| Empty-string values | **0** | 0 | 0 | `[v for v in values if not v]` |
| Empty / whitespace-only keys | **0** | 0 | 0 | `[k for k in keys if not k.strip()]` |

**F1a — No empty values.** Worth stating because the *address* canon maps are the opposite:
`ADDR_CANON_COMMON` (lines 196-197) maps `number, no, nos, num, h, hno, house, door, plot,
flat, shop, null, na, none, nil` to `""`, and `ADDR_CANON_FR` (line 213) maps `no, n, numero,
null, na` to `""`. `FR_REGIONS` has no such entries, so any French component that matches
always sets a non-empty `state`.

**F1b — Zero overlap, in all seven directions tested.** All four cross-dictionary set

### F2 — Country scoping is exhaustively correct

`STATE_MAPS` is keyed by the exact strings `"US"`, `"India"`, `"France"`; post-import
`STATE_MAPS["France"] is FR_REGIONS` is `True`. `normalize_address` line 318 resolves
`smap = STATE_MAPS.get(country, {})` from the row's own `country` value, so an unrecognised
country falls through to `{}` rather than to another country's map.

Profile field `country_rows` gives the exact set of country strings present, and `rows` gives
the file total. The invariant `sum(country_rows.values()) == rows` holds in all six files, so
no row is unaccounted for and no country string exists outside the `STATE_MAPS` key set:

| File | `country_rows` keys | `sum(country_rows.values())` | `rows` | Equal |
|---|---|---|---|---|
| test_s1 | `['France','India','US']` | 1,732,544 | 1,732,544 | yes |
| test_s2 | `['France','India','US']` | 4,887,273 | 4,887,273 | yes |
| test_s3 | `['France','India','US']` | 5,082,316 | 5,082,316 | yes |
| train_s1 | `['India','US']` | 2,206,821 | 2,206,821 | yes |
| train_s2 | `['India','US']` | 5,034,616 | 5,034,616 | yes |
| train_s3 | `['India','US']` | 5,285,603 | 5,285,603 | yes |

France is test-only, as expected: zero France rows in all three train files. **No defect.**

I also confirmed the scoping is *load-bearing* end to end, not just at the dictionary:
`run_blocking.py:14,16,23` and `build_features.py:107-113` both iterate countries and filter
with `pl.col("country") == country`, so every candidate pair is country-homogeneous. Therefore
`state_eq` (`features.py:114`) never compares a French code against a US or Indian code, and
the 3-letter French values cannot collide with the 2-letter US/IN values in a pair. This is
inference from the call sites, not a profile field.

### F3 — NEW DEFECT: three administrative levels share one flat namespace

The 14 keys are not 14 regions. Classified by French administrative level:

| Level | Count | Keys |
|---|---|---|
| **Region** (18 exist nationally) | **4** | `hauts de france`, `nouvelle aquitaine`, `pays de la loire`, `ile de france` |
| **Departement** | **9** | `nord`, `pas de calais`, `somme`, `aisne`, `oise`, `gironde`, `landes`, `loire atlantique`, `vendee` |
| **City / commune** | **1** | `paris` |

So **10 of 14 entries (71.4%) are not regions**, and only 4 of 18 regions (22.2%) are present.
The identifier `FR_REGIONS` is therefore actively misleading. `CONFIRMED` as a structural
defect: the dictionary is level-inconsistent, which is what makes it unsafe to extend (you
cannot tell from the name whether a new key should be a region, a departement or a city).

### F4 — NEW DEFECT: a matched component *overwrites* the state (order dependence)

This is the unexplored territory `already_checked` pointed at ("French rows put region before
or after city inconsistently"), and it is a real code defect, not just a data quirk.
`normalize.py:331-335`:

```python
ck = re.sub(r"[^a-z0-9& ]+", " ", c).replace("&", " and ")
ck = " ".join(ck.split())
if ck in smap:
    state = smap[ck]
    continue          # <-- no break: loop continues, state can be overwritten
```

There is no `break` and no "first match wins" guard, so `state` is **last match wins**. The
`continue` also skips both `toks.extend(ctoks)` (line 350) and `city_comps.append` (line 352),
so a matched component is deleted from the address token stream *and* from the city list.
Executed against the real module:

| Address | country | `state` | `acity` |
|---|---|---|---|
| `10 rue de Rivoli, Paris, Hauts-de-France` | France | **`hdf`** | `[]` |
| `10 rue de Rivoli, Hauts-de-France, Paris` | France | **`idf`** | `[]` |
| `9 Rue T, Paris, Nord` | France | **`hdf`** | `[]` |
| `9 Rue T, Nord, Paris` | France | **`idf`** | `[]` |
| `9 Rue T, Washington, DC` | US | **`dc`** | `[]` |
| `9 Rue T, DC, Washington` | US | **`wa`** | `[]` |
| `9 Rue T, Delhi, Uttar Pradesh` | India | **`up`** | `[]` |
| `9 Rue T, Uttar Pradesh, Delhi` | India | **`dl`** | `[]` |

Two rows describing the same French business resolve to **two different states** purely from
comma order. The mechanism is not France-specific — `Washington`/`DC` and `Delhi`/`UP` show the

### F5 — The same `continue` destroys the city feature for French Paris rows

Line 335's `continue` is the mechanism behind F4's second half, and it is worth isolating
because it is a *loss* rather than a *flip*. `features.py:87-90` builds `city_tset` and
`city_last` from `q_acity`/`s_acity`, so a French row whose only city component is `paris`
compares against the empty string on both city features:

| Address | country | `state` | `toks` | `acity` |
|---|---|---|---|---|
| `12 avenue Foch, Paris` | France | `idf` | `['12','ave','foch']` | `[]` |
| `5 Main St, Paris, TX` | US | `tx` | `['5','main','st','paris']` | `['paris']` |
| `1 Rue du Nord, Calais, Hauts-de-France` | France | `hdf` | `['1','rue','du','nord','calais']` | `['calais']` |

The identical city string `paris` is a **retained feature** in a US row and a **deleted
feature** in a French row. Bounded by the same 388/952/923 tokens, i.e. **~0.13-0.15% of France
rows** (upper bound). Small, because most French Paris-area rows also carry `ile de france`,
which is consumed too. `CONFIRMED` as behaviour; the *semantic* claim that `paris -> idf` is
the right answer is `SPECULATIVE` (no French ground truth exists, see Gaps).

### F6 — s1 is region-stated, s2/s3 are departement-stated. The departement keys are load-bearing

This is the finding that must constrain everything the follow-up tasks propose. Probe tokens
from `addr_tokens["France"]`, divided by `by_country["France"]["rows"]`:

| Source | France rows | region-tok/row | departement-tok/row | ratio dept/region |
|---|---|---|---|---|
| test_s1 | 259,452 | **1.0015** (259,840) | **0.0047** (1,217) | 0.005 |
| test_s2 | 703,378 | 0.3213 (225,997) | **0.3266** (229,735) | 1.02 |
| test_s3 | 731,615 | 0.3472 (254,016) | **0.3175** (232,281) | 0.91 |

Arithmetic shown: region = `hauts + nouvelle + pays`; departement = `nord + gironde +
atlantique + pas + landes + somme + oise + aisne + vendee` (s1: `200+62+253+179+116+333+74+0+0
= 1,217`; s2: `75,362+75,104+63,697+14,325+292+807+148+0+0 = 229,735`; s3:
`76,449+75,621+64,398+14,528+313+833+139+0+0 = 232,281`).

Consequence: on s2/s3, **at most 32.66%** (s2) and **31.75%** (s3) of France rows carry a
departement that only resolves because of the 9 departement keys. On s1 the region keys carry
essentially everything (1.0015 region tokens per row). **Any change that deletes or renames
the departement keys is a large regression on two of the three test sources.**

Two per-key caveats I will not paper over: `pas` (for `pas de calais`) is also the ordinary
French word "step", so it is a loose upper bound — `calais` is 55,273 in s2 against `pas`
14,325, so most `calais` occurrences are the **city** Calais, not the departement. And `loire`
cannot be used for `loire atlantique` because `loire` also occurs in `pays de la loire`; I
therefore used `atlantique`, which is unambiguous.

### F7 — Per-key activity, and two dead entries

| Key | Value | Level | s1 | s2 | s3 | Verdict |
|---|---|---|---|---|---|---|
| hauts de france | hdf | region | 101,717 | 88,519 | 99,419 | active |
| nouvelle aquitaine | naq | region | 85,311 | 74,392 | 83,099 | active |
| pays de la loire | pdl | region | 72,812 | 63,086 | 71,498 | active |
| ile de france | idf | region | 303 | 817 | 794 | active, marginal (0.11-0.12% of rows) |
| nord | hdf | dept | 200 | 75,362 | 76,449 | active, **s2/s3 only** |

### F8 — The unmapped regions are measurable but small, and two are not confirmed

Regions *not* in `FR_REGIONS`, counted by their distinctive word (excluding the shared function
words `de`, `la`, `d'`) in `addr_tokens["France"]`:

| Unmapped region (word) | s1 | s2 | s3 | Status |
|---|---|---|---|---|
| lorraine | 334 | 825 | 789 | CONFIRMED non-zero |
| alsace | 311 | 744 | 758 | CONFIRMED non-zero |
| bretagne | 222 | 505 | 535 | CONFIRMED non-zero |
| normandie | 139 | 288 | 329 | CONFIRMED non-zero |
| bourgogne | 124 | 273 | 316 | CONFIRMED non-zero |
| auvergne | 89 | 213 | 218 | CONFIRMED non-zero |
| picardie | 38 | 79 | 98 | CONFIRMED non-zero |
| champagne | 35 | 82 | 78 | CONFIRMED non-zero |
| occitanie | 0 | 0 | 0 | <= 23/58/60, unproven |
| corse | 0 | 0 | 0 | <= 23/58/60, unproven |
| grand est (`grand` / `est`) | 704 / 76 | 1,710 / 189 | 1,848 / 204 | **LIKELY at most** - see below |
| PACA (`provence` / `cote` / `azur`) | 56 / 23 / 0 | 119 / 157 / 0 | 116 / 169 / 0 | **SPECULATIVE** - see below |

Upper bound on France rows carrying 1 or more unmapped-region word, summing all 20 probe words
listed above: **2,151 (s1) = 0.83%**, **5,184 (s2) = 0.74%**, **5,458 (s3) = 0.75%** of France
rows. Token counts are an upper bound on rows, since a row can carry several.

**Why `grand est` is not confirmed:** `grand`=704 and `est`=76 in s1 is a 9:1 ratio. A
co-occurring two-word region field would give a ratio near 1:1. `grand` is far more likely to
be street vocabulary (`Grand Rue`, `Grande Place`). Marked `LIKELY` at most, and excluded from
any headline claim. **Why PACA is speculative:** `provence`=56 and `cote`=23 in s1, i.e. at or
below the truncation floor of 23, so presence is not established at all in s1; s2/s3
`provence`=119/116 is real but `cote`=157/169 does not match `provence` closely enough to
assert co-occurrence. Both need a row-level check before anyone acts on them.

### F9 — Accent handling: a measurement trap in the profile, not a defect in the pipeline

`build_profile.py:28` tokenises with `TOKEN_RE = [a-z0-9]+` and **never strips accents**, while
`normalize.py:317` calls `strip_accents(s).lower()` *before* the component split. Verified
tokenizer behaviour:

| Input | `TOKEN_RE.findall` |
|---|---|
| `'ile-de-france'` | `['ile']` |
| `'Île-de-france'.lower()` | `['le', 'de', 'france']` |
| `'hauts-de-france'` | `['hauts', 'de', 'france']` |

So an accented `Île-de-France` contributes **no** `ile` token at all — the `Î` vanishes and the
word is silently re-attributed to the shared token `le`. The pipeline is *correct* here
(verified against the real module: `2 Bd A, Paris, Île-de-France` gives `state='idf'`). The
consequence is for measurement only, and it is quantifiable. Define
`excess = addr_tokens["France"]["france"] - addr_tokens["France"]["hauts"]`; since essentially
every `france` token is the second word of `Hauts-de-France`, `excess` is an **upper bound on
(accented Île-de-France rows + standalone `France`-component rows)**:

| Source | `france` | `hauts` | `excess` | of which unaccented `ile` | residual ceiling |
|---|---|---|---|---|---|
| test_s1 | 102,319 | 101,717 | 602 | 303 | <= 299 |
| test_s2 | 89,929 | 88,519 | 1,410 | 817 | <= 593 |
| test_s3 | 100,902 | 99,419 | 1,483 | 794 | <= 689 |

**Process rule: never use `ile` counts as evidence about Île-de-France, and never use `le`
counts at all** (`le` is also the ordinary French article, 1,992/4,882/5,050 — dominated by
article usage, not by `Île`). Region measurements must be made on whole components, which the
profile does not record.

### F10 — A related leak: a code written inline with the city never resolves

`normalize_address` splits on `,` only (line 322) and then requires the **entire** component to
equal a key (line 333). So a region sharing a comma-field with anything else never resolves:

| Address | `state` | `acity` |
|---|---|---|
| `7 Rue V, Paris IDF` | `''` | `['paris idf']` |
| `9 Rue T, HDF` | `''` | `['hdf']` |
| `5 Rue Z, Rennes, Bretagne` | `''` | `['rennes', 'bretagne']` |
| `12 Pays de la Loire` | `''` | `[]` (has a digit, so line 351 excludes it) |


### F11 — The missing self-map: a confirmed code defect with zero measurable effect

`normalize.py:252` iterates `(US_STATES, IN_STATES)` only, so `FR_REGIONS` gains no self-maps:
0 of its 4 values are also keys, against 104 for `US_STATES` and 86 for `IN_STATES` (F1). Had
`hdf`/`idf`/`naq`/`pdl` appeared as address components, those rows would silently fail to
resolve and the code would leak into `acity` instead (demonstrated in F10).

They do not appear. `addr_tokens["France"]` gives `hdf`=0, `idf`=0, `naq`=0, `pdl`=0 in **all
three** test sources, bounded by the 23/58/60 truncation floor.

This **agrees with** `already_checked` REFUTED-2 and I record the agreement explicitly rather
than claiming it as new. `CONFIRMED` as a code defect, measured effect **exactly zero** on this
dataset.


### F12 — I must flag an internal contradiction in `already_checked`, with numbers

`already_checked` REFUTED-2 asserts all three of the following:

* HDF 101,521 + NAQ 85,197 + PDL 72,734, and
* "state resolves for 100.00% of France rows (259,452 / 259,452, zero unmatched)", and
* "plus ~1,100 rows of legacy names".

The first two are an exact arithmetic identity, and I confirm it:
`101,521 + 85,197 + 72,734 = 259,452 = by_country["France"]["rows"]` for test_s1. But that sum
leaves a remainder of **exactly zero**, which requires that **zero** test_s1 France rows are
Ile-de-France-stated and zero are legacy-stated. That directly conflicts with the "~1,100
legacy rows" claim in the same block, and it sits awkwardly with the profile's own
`ile` = 303 occurrences in s1.

I cannot resolve this from the profile, and I will not smooth it over:

* If the three figures are **exact component counts**, then the 303 `ile` occurrences must be
  street-name usage (e.g. `rue de l'ile`) or rows that *also* carry one of the three regions —
  in which case the three counts are not a partition and the identity is a coincidence of
  overlapping upper bounds.
* If `ile` = 303 counts real Ile-de-France rows, then the three-way sum over-counts and at most
  303 rows carry a fourth region.
* `ile` = 303 is only an **upper bound** on IDF rows, so this is a bound conflict, not a
  demonstrated one.

**What is *not* affected:** the *conclusion* of REFUTED-2 — that `FR_REGIONS` resolves a state
for essentially all France rows, and that thinness is not the defect — survives this. My own
measurement is consistent with it: the three regions used account for 1.0015 tokens per s1
France row, and every departement in F6's probe list except the two dead keys is present. The
contradiction is confined to the exact partition arithmetic and the legacy-row count, both of
which are row-level quantities the profile cannot supply. Flagged, not reconciled.

## Interpretation

*Clearly marked as inference:*

1. The dictionary's real function in this pipeline is not "map French regions to codes" but
   "detect a trailing geographic component, delete it from the token stream, and record a
   state". The `continue` at line 335 is doing as much work as the mapping. That reframing
   explains why 9 departement keys outperform 14 region keys would: s2/s3 are
   departement-stated (F6).
2. Thinness is **not** the defect the earlier review assumed (REFUTED-2, which I independently
   re-confirm on the self-map question in F11). The real defects are (a) level-inconsistency
   (F3), which makes the dictionary unsafe to extend, and (b) the absence of a `break` at line
   334 (F4), which makes the resolved state depend on comma order.
3. F4 is the highest-value code finding in this audit because it is the only one that can make
   a correct, well-mapped address resolve to the *wrong* region. F5 and F11 can only lose

## Gaps

1. **No `state`-resolution field exists in the profile.** `by_country` collects `rows`,
   `name_empty`, `addr_empty`, `name_chars`, `addr_chars`, `name_tokens`, `num_digits`,
   `has_digit_name`, `has_comma`, `prefix_bad`, `dig5`, `dig6`, `alpha_only_addr`, `len_hist`
   (`build_profile.py:85-91`). There is no per-country count of resolved states, so
   `already_checked`'s "100.00% (259,452 / 259,452)" **cannot be re-derived from the profile at
   all**. I corroborated it only indirectly, via the exact-sum invariant in F12 and the
   token-density arithmetic in F6. I did not open the raw TSVs to measure it, per the RAM
   constraint.
2. **The profile records tokens, not components.** `addr_tokens` is a per-country `Counter` fed
   by `ADDR_SPLIT.split` then `TOKEN_RE.findall` (`build_profile.py:126-127`) — it keeps no
   record of which tokens were in the *same* comma-field. Therefore I cannot measure
   co-occurrence, cannot count rows matching a multi-word key, cannot separate the city
   `calais` from the key `pas de calais`, and cannot resolve F12. **Every "affected rows" figure
   in this report is a token-count upper bound and is labelled as one.** Resolving F4's true
   blast radius and F8's `grand est`/PACA status needs a component-level field, which is the
   single highest-value addition to `build_profile.py`.
3. **The `already_checked` contradiction (F12) is unresolved** and cannot be resolved from the
   profile.
4. **No French ground truth.** All three train files have zero France rows, so no label can
   confirm which of `hdf`/`idf`/`naq`/`pdl` is *correct* for a given row. Any claim that
   `paris -> idf` is semantically right is `SPECULATIVE`; I claim only that consuming the
   component is behaviourally destructive.
5. **Truncation floor.** `TOPN = 4000` with the 4,000th France token at **23 / 58 / 60**
   (s1/s2/s3, entries `casablanca` / `campanules` / `370`). Absence from `addr_tokens` proves
   `count <= 23/58/60`, never zero. This is why `aisne`, `vendee`, `occitanie`, `corse`,
   `azur`, `rhone`, `alpes`, `arde` and the four canonical codes are all reported as bounded,
   not zero.

## Recommendations

The work order asked for ground truth and explicitly **not** for changes, so these are recorded
as constraints on the follow-up tasks. **None should be applied on the strength of this audit
alone.**

1. **[P1] Do not "fix" `FR_REGIONS` by deleting the departement keys.** F6: s2/s3 are
   departement-stated at 0.3266 and 0.3175 tokens per France row, i.e. up to 32.66% / 31.75% of
   France rows. Expected effect of the naive "thin it to 18 regions" fix: **large regression on
   two of three test sources.** This is the highest-value warning in the report.
2. **[P1] Add a precedence rule at line 334** so a matched component cannot overwrite an earlier
   match (F4). Cheapest possible fix, and the only one that can fix *wrong* answers rather than
   just missing ones. **Measure before and after** — it changes the resolved state for any row
   carrying two mapped components, and I have bounded that at <=388/952/923 France rows.
3. **[P1] Add a component-level field to `build_profile.py`** (G2): the address field split on
   commas, stored as a component-level counter, or at minimum a per-country count of rows whose
   address contains 2 or more state-map keys. Without it, F4, F8 and F12 all stay unresolvable
   and the next agent will re-derive the same upper bounds.
4. **[P2] Move `paris` out of the state map** into a city list (F3, F5), so a city is never
   consumed at line 335 and never competes with a region for `state`. Behaviour change on
   ~0.13-0.15% of France rows; measure, do not assume.
5. **[P2] Rename or re-document the dictionary** to reflect that it is a mixed-level
   region + departement + city gazetteer (F3). Cost: a comment. Benefit: prevents the next
   reviewer from making mistake (1). Pure win, no behavioural change.
6. **[P2] Add the unmapped regions that are measurably present** — `bretagne`, `lorraine`,
   `alsace`, `normandie`, `auvergne`, `bourgogne`, `champagne`, `picardie` (F8), all
   `CONFIRMED` non-zero. `grand est` is `LIKELY` at most and PACA is `SPECULATIVE`; both need
   the component-level field from (3) first.
7. **[P3] Add the self-map loop entry** (`for _m in (US_STATES, IN_STATES, FR_REGIONS)`) (F11).
   Expected effect: **exactly zero on this dataset** — 0 occurrences of all four codes. Do it
   for symmetry and future-proofing only; do not claim a score change.
8. **[P3] Leave `aisne` and `vendee` alone** (F7a). They cost nothing measurable. Deleting them
   is a readability call, not a correctness one, and it would remove the only forward-looking
   coverage for HDF/PDL.
9. **[Process] Do not use `ile` or `le` counts as evidence about Ile-de-France** (F9), and do
   not cite the exact partition `101,521 + 85,197 + 72,734 = 259,452` without also citing the
   F12 contradiction.
10. **[Out of scope, flagged for the `ADDR_CANON_FR` owner]** `ADDR_CANON_FR:211` maps
    single-letter tokens `b` to `bis`, `t` to `ter`, `r` to `rue`, `q`/`qu` to `quai`,
    `all`/`al` to `allee`. Verified: `'9 Rue T, HDF'` yields `toks = ['9','rue','ter','hdf']`,
    i.e. the `T` was rewritten to `ter`. French addresses use bare `B`/`T`/`R`/`N` degrees

## Provenance

* **Read-only.** Opened `_upstream/src/normalize.py` (lines 88-262 and 314-353),
  `_upstream/src/prep.py`, `_upstream/src/features.py` (lines 70-130),
  `_upstream/src/blocking.py`, `_upstream/src/run_blocking.py`,
  `_upstream/src/build_features.py`, and `build_profile.py`. **No file under
  `amazon_ml_2026_research/student_resource/dataset/` was opened.** No network access.
* **`_upstream/` verified pristine.** `git log -1` = `8445b7f11a6f23f2b6adec254ef1dc3bb45507ad`
  ("Initial commit"); `git diff --stat` empty; the 18 tracked `src/__pycache__/*.cpython-310.pyc`
  files are untouched. Module inspection used `importlib` with a stubbed `polars` **and
  `python -B`**, so no bytecode cache was written; `git status --porcelain` is empty after all
  work.
* **Two independent measurement paths, in agreement.** Static facts were taken from
  `ast.literal_eval` on the module source (sees dicts as written) *and* from importing the real
  module (sees them after the line-252 mutation). Every count in F1 matched between the two.
* **Corrections to the earlier draft of this file**, for the record: (a) unmapped-region row
  bounds were stated as 2,020 / 4,561 / 4,919 — the correct sums of the listed probe words are
  **2,151 / 5,184 / 5,458**; (b) region-tok/row for s1 was stated as 2.006 — the correct figure
  on the stated token set (`hauts + nouvelle + pays`) is **1.0015**, since 2.006 implicitly
  counted `france`, `aquitaine` and `loire` as well, which double-counts `pays de la loire`
  (`loire` also appears in `loire atlantique`, where s2 `loire` = 126,216 against
  `atlantique` = 63,697); (c) the earlier draft's `pays`/`loire` ratio claims were unsound for
  the same reason; (d) its sections were out of order and its Gaps list was truncated
  mid-sentence.
* **Evidence discipline.** Every figure names its profile field or source line. Arithmetic is
  shown inline. Upper bounds and truncation bounds are labelled as such. No figure was
  estimated, extrapolated, or carried over from another country. Where a claim is `LIKELY` or
  `SPECULATIVE` it is marked inline so a human can discard it cheaply.
