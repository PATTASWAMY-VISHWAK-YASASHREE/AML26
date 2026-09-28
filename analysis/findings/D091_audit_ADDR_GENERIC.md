# D091 - Ground truth for `ADDR_GENERIC` (and how it relates to the other two address tables)

**Task:** D091 (family B-dictionary). **Status:** GROUND TRUTH ESTABLISHED. No changes proposed.
**Sources read:** `_upstream/src/keys.py`, `_upstream/src/normalize.py`, `_upstream/src/prep.py`,
`_upstream/src/features.py`, `_upstream/src/blocking.py`, `build_profile.py`,
`analysis_out/profile/test_s{1,2,3}.json`.

---

## HEADLINE

`ADDR_GENERIC` is a **62-element list, not a dict**, it lives in **`_upstream/src/keys.py:14-19`**
(the work order's location is CORRECT - it is *not* in normalize.py), and it is used at exactly
**one** call site: `keys.py:39`.

The three address tables are **not three variants of one thing** - they are **three different
stages of one pipeline**, and only one of them is the odd one out:

| Table | File / lines | Type | Stage | Used? |
|---|---|---|---|---|
| `ADDR_CANON_COMMON` | normalize.py:153-198 | dict, 177 entries | normalise (rewrite) | yes, normalize.py:319,321 |
| `ADDR_CANON_FR` | normalize.py:199-214 | dict, 68 entries | normalise (rewrite) | yes, normalize.py:321 |
| `ADDR_GENERIC` | **keys.py:14-19** | **list, 62 entries** | **blocking-key stoplist (delete)** | yes, keys.py:39 |

**`ADDR_GENERIC` is NOT dead code.** It is a post-canonisation stoplist and it fires hard.

**The real defect is an ordering bug, not a coverage bug:** the stoplist is hand-maintained as
though it were applied *before* canonicalisation, but it is applied *after*
(`normalize.py:347` `t = canon.get(t, t)` runs in `prep.py:13` and writes `atoks`;
`keys.py:39` filters that already-canonicalised string). So any stoplist entry that canon
*renames* is dead on arrival, and any canon *output* that is not in the stoplist leaks into the
blocking keys. Both sides of this are measured below.

---

## 1. Exact contents and counts (verified by parsing the source, not by eye)

Quoted, `keys.py:14-19`:

```python
ADDR_GENERIC = ["st", "rd", "ave", "dr", "blvd", "ln", "ct", "pl", "sq", "hwy", "pkwy", "cir", "ter", "trl",
                "ste", "apt", "fl", "bldg", "unit", "po", "box", "rue", "near", "opposite", "main", "cross",
                "ground", "and", "des", "the", "city", "way", "floor", "nagar", "road", "sector", "phase",
                "complex", "colony", "indl", "estate", "dist", "vill", "apts", "chemin", "allee", "impasse",
                "lane", "street", "off", "wing", "block", "office", "tower", "plaza", "pvt", "ltd", "1st",
                "2nd", "3rd", "4th", "5th"]
```

| Property | Value |
|---|---|
| Entry count | **62** |
| Distinct entries | **62** (no duplicates) |
| Uppercase entries | none (all lowercase, matches canon keyspace) |
| Empty / null entries | **none** - it is a list, so "empty value" is not representable |
| Canonical *values* | **N/A - the list has no values.** All 62 entries are stoplist *keys*. |

> **Answer to the work order's "distinct canonical values" question: not applicable.**
> That phrasing presumes a `key -> value` mapping. `ADDR_GENERIC` has no values; it is consumed
> by `pl.element().is_in(ADDR_GENERIC)` (`keys.py:39`), a membership test only. I am flagging
> this rather than inventing a number.

The other two, for contrast, are real dicts:

| Property | `ADDR_CANON_COMMON` | `ADDR_CANON_FR` |
|---|---|---|
| Entries | **177** | **68** |
| Distinct values | **81** | **30** |
| Empty-valued keys (token deleted) | 15 - `na, door, nil, hno, house, nos, no, none, num, flat, null, h, number, shop, plot` | 5 - `no, null, n, na, numero` |
| Keys lacking a self-map | 114 | 39 |
| FR keys shadowing a COMMON key | 23 - `rte, no, null, n, blvd, na, sq, ste, bld, ter, boul, avn, ave, place, square, dr, avenue, route, boulevard, st, av, pl, bd` | - |

---

## 2. Are all three actually used? - YES, all three. Call sites quoted.

```
keys.py:14:         ADDR_GENERIC = [...]
keys.py:39:         toks = (pl.col("atoks")...filter(~pl.element().is_in(ADDR_GENERIC) & ...))
normalize.py:153:   ADDR_CANON_COMMON = {
normalize.py:199:   ADDR_CANON_FR = {
normalize.py:319:   canon = dict(ADDR_CANON_COMMON)
normalize.py:321:   canon = {**{k: v for k, v in ADDR_CANON_COMMON.items() if k not in ("st","ste","dr","n","s","e","w")}, **ADDR_CANON_FR}
```

Full call path, in execution order:

1. `prep.py:13` `toks, nums, st, pin, cc = N.normalize_address(a, c)`
2. `normalize.py:319-321` builds `canon`; `normalize.py:347` `t = canon.get(t, t)` **rewrites every address token**
3. `prep.py:16` `out["atoks"].append(" ".join(toks))` - the **post-canon** token string is persisted to parquet
4. `keys.py:39` filters that post-canon string against `ADDR_GENERIC` - **this is the only consumer**
5. `blocking.py:11,30` call `make_keys` / `make_keys_chunked`

**Difference between the three, stated plainly:** the two `ADDR_CANON_*` dicts are
*normalisation* (many spellings -> one canonical form, applied to every address, and they can
**delete** a token by mapping it to `""`). `ADDR_GENERIC` is *blocking-time noise suppression*
(one fixed list of already-canonical forms -> dropped, and it can only **delete**). They are not
overlapping tables and neither is a superset of the other; they are sequential filters on the same
field. `ADDR_GENERIC` operating on canon *output* is the whole story of the defect below.

**Blast radius - important and often assumed wrongly:** `ADDR_GENERIC` affects **blocking keys
only**. It is *not* referenced in `features.py` at all; `features.py:129` computes
`_weighted_overlap(... "q_atoks", "s_atoks", addr_idf, "wa")` on the **raw post-canon `atoks`**,
unstripped. So the leak below does **not** touch the IDF features - it touches candidate
generation only. `blocking.py:31` also tests `atoks == ""` for the `CAPS_NOADDR` path, which is
also pre-`ADDR_GENERIC`, so the "no address" branch does not see the stoplist effect either.

---

## 3. Country scoping - `ADDR_GENERIC` is NOT scoped. This is a genuine asymmetry.

`keys.py:39` tests membership against one global list with **no `country` predicate anywhere**.
Contrast `normalize.py:319-321`, which is explicitly country-scoped: France drops
`("st","ste","dr","n","s","e","w")` from COMMON and layers `ADDR_CANON_FR` on top.

Consequence: the French street words in `ADDR_GENERIC` - `rue`, `chemin`, `allee`, `impasse`
(`keys.py:15,17`) - are dropped from **US and Indian** blocking keys too. Conversely the US/UK
words `street`, `lane`, `block`, `office`, `tower`, `plaza` are dropped from **French** keys.
This is the same one-list-for-all-countries design as `NAME_STOP` (`normalize.py:144-149`),
which likewise has no country scoping, so it is at least consistent with house style - but it is
still a real, measurable cross-country contamination.

Measured: French `rue` occurrences in the US/India test corpora. **GAP - not collected.** The
profile's `addr_tokens` is top-4000 per country per file and does not record cross-country
token origin, so I cannot size this from the profile and will not guess. Flagged as a gap.

---

## 4. STRUCTURAL DEFECTS (measured)

The profile stores **raw, pre-canon** address tokens (`build_profile.py:113,126-127`:
`bal = ba.lower()` then `TOKEN_RE.findall` per component - no `canon.get` anywhere). So every
number below applies the real `canon` transform from `normalize.py:321/347` to the profile tokens
first, then tests `ADDR_GENERIC` membership exactly as `keys.py:39` would. Denominator is stated
on every line and is the **top-4000 listed token mass per country across test_s1+s2+s3** - the
tail is truncated (`build_profile.py:27,140`), so these are **lower bounds on absolute mass** and
**exact rates only within the listed set**.

### D0 (context) - how much `ADDR_GENERIC` actually fires

Post-canon address-token mass across all three test files, classified by fate. Same denominator
discipline as above (top-4000 listed mass; lower bound on absolute mass):

| Country | Listed mass | Removed by `ADDR_GENERIC` | Removed by empty canon | Survives into keys |
|---|---|---|---|---|
| US | 20,533,409 | 5,029,788 (24.50%) | 118,742 (0.58%) | 15,384,879 (74.93%) |
| France | 11,992,918 | 1,770,731 (14.76%) | 184,862 (1.54%) | 10,037,325 (83.69%) |
| India | 51,134,252 | 7,852,293 (15.36%) | 4,927,131 (9.64%) | 38,354,828 (75.01%) |

`ADDR_GENERIC` removes roughly an eighth to a quarter of all address-token mass depending on
country, so it is emphatically load-bearing. Note France has the *lowest* removal rate despite
having the most French street vocabulary in the list, because that vocabulary is a small share of
French address mass and the list never sees canon's French *outputs*.
### D1 (CONFIRMED, real) - 5 of 62 stoplist entries are dead on arrival because canon renames them first

`ADDR_GENERIC` is checked against canon *output*, but 5 of its own entries are canon *keys* that
get rewritten to something else before the check:

| Stoplist entry | canon rewrite | Net effect |
|---|---|---|
| `floor` | `floor -> fl` (normalize.py:174) | dead, but `fl` is in the list, so covered |
| `road` | `road -> rd` (normalize.py:155) | dead, but `rd` is in the list, so covered |
| `lane` | `lane -> ln` (normalize.py:159) | dead, but `ln` is in the list, so covered |
| `street` | `street -> st` (normalize.py:154) | dead, but `st` is in the list, so covered |
| **`plaza`** | **`plaza -> plz`** (normalize.py:177) | **UNCOVERED - `plz` is not in `ADDR_GENERIC`** |

The first four are harmless redundancy. **`plaza` is the one real hole in the stoplist itself**:
`plaza` is removed from the list's effective coverage by the rewrite, and the replacement `plz` is
not listed, so plaza traffic enters the blocking keys under a new name. **CONFIRMED** by parsing.

### D2 (CONFIRMED, real, large) - canon *outputs* missing from `ADDR_GENERIC` leak into blocking keys

37 (US/India) and 57 (France) canonical forms that `ADDR_CANON_*` can produce are absent from the
stoplist. Non-city, non-country noise among them:

- **`plz`** (plaza) - the D1 hole, measured **61,183** listed occurrences in India test files.
- **direction words** `n, s, e, w, ne, nw, se, sw` (normalize.py:171-173). These are canonicalised
  but never stoplisted. India is hit hardest: `west 479,074` + `s 308,923` (from `south 251,318`)
  + `e 210,416` (from `east 147,218` + `e`) + `north 204,278` (from `n 126,990`). US: `north 170,197`
  + `west 56,704` + `n 45,885` + `south 29,310` + `east 23,048`.
- **US street-type abbreviations** `pt` (point, 24,882), `ft` (fort, 30,871), `mt` (27,617),
  `hts` (heights, 23,567), `ctr` (centre).
- **French `saint` / `sainte`** (normalize.py:207). This is the *converse* of the France key-drop:
  for France, `st -> saint` and `ste -> sainte`, and **neither `saint` nor `sainte` is in
  `ADDR_GENERIC`** - while the entries `st` and `ste` in the list are precisely the ones France
  no longer produces. Measured: `saint 141,364` + `st 25,454` = **166,818** listed France test
  occurrences, plus `sainte` below the cut. `saint` is a genuine French place-name morpheme, so
  for France this leak is arguably *desirable*; for the US it would not be. As written it is
  accidental, not designed.
- **`bis`, `bat`, `pres`, `prof`, `gen`, `mal`, `quai`, `crs`, `fbg`, `zone`, `za`, `zi`, `zac`,
  `res`, `lieu`, `lieudit`** (France only, normalize.py:205-212). `bis` alone is **52,072**.

Aggregate leak, canon-rewritten tokens landing outside `ADDR_GENERIC`:

| File | US | France | India |
|---|---|---|---|
| test_s1 | 59,843 (of 3,189,237 listed = 1.88%) | 58,310 (of 2,253,877 = 2.59%) | 643,093 (of 8,617,430 = 7.46%) |
| test_s2 | 179,270 (of 8,135,308 = 2.20%) | 141,579 (of 4,745,780 = 2.98%) | 1,354,501 (of 21,702,626 = 6.24%) |
| test_s3 | 333,694 (of 9,208,864 = 3.62%) | 147,583 (of 4,993,261 = 2.96%) | 1,582,320 (of 20,814,196 = 7.60%) |

**Caveat, stated plainly:** this leak total *includes* the India/US **city-name** canon entries
(`mumbai 647,363`, `bangalore 428,707`, `gurgaon 96,243`, `kolkata`, `chennai`, `kochi`,
`pune`, `mysore`, `visakhapatnam`, `ahmedabad`, `calicut`, `orissa`, `kerala`). Those are
**intentional and correct** - they are identity-bearing, not noise, and *should* reach the keys.
They dominate the India column. The **noise-only** subset is the direction words, `plz`, `pt`,
`ft`, `mt`, `hts`, `ctr`, and the French morphemes listed above.

### D3 (CONFIRMED, real, new) - 15 stoplist entries have no canon rule at all and are silently effective everywhere

Exactly **15** of the 62 entries are not a key in `ADDR_CANON_COMMON` **or** `ADDR_CANON_FR`:

`and, des, the, off, wing, block, office, tower, pvt, ltd, 1st, 2nd, 3rd, 4th, 5th`

canon never rewrites them (`normalize.py:347` `canon.get(t, t)` returns `t` unchanged), so
`keys.py:39` removes them in all three countries. Consequences:

- **Function words** - `and`, `des`, `the` sit in the *address* stoplist. `des` is the French
  plural article; per the work order's already-settled finding, `de/la/du/des/le/les` are absent
  from `ADDR_CANON_FR`, and `des` here is dropped only for **blocking**, not for features, because
  `features.py` never consults this list. So the D081 finding (French function words dilute IDF)
  is **not** mitigated by this list. Do not double-count a fix.
- **`1st`..`5th` are safe**, and deliberately so: canon produces them from
  `first/second/third/fourth/fifth` (normalize.py:184), and pure-digit strings are *not* filtered
  by `keys.py:39` - but `1st` is not `^\d+$` (`keys.py:41`), so it correctly falls into the
  `alph` bucket (`keys.py:42`) and is then removed. No interaction with the `MAX_ALPHA` sort.

### D3b (CONFIRMED, real) - the four French street words are France-scoped in canon but GLOBAL in the stoplist

`rue`, `chemin`, `allee`, `impasse` (`keys.py:15,17`) **are** keys in `ADDR_CANON_FR`
(`normalize.py:200,202,204,203`), each mapping to itself, but they are **absent from
`ADDR_CANON_COMMON`**. So they are identity-preserving in France and untouched everywhere else -
yet `ADDR_GENERIC` deletes them for **US and Indian** rows too, because `keys.py:39` has no
`country` predicate. This is the cross-country contamination of section 3, isolated to a
4-token set. **GAP - unquantified:** top-4000 truncation plus no cross-country token provenance
in the profile, so I cannot state the occurrence count and will not invent one.

### D4 (CONFIRMED, real) - `st`/`ste` are inert for France, by design of the FR key-drop

Because `normalize.py:321` removes `st`, `ste`, `dr`, `n`, `s`, `e`, `w` from COMMON for France,
the `ADDR_GENERIC` entries `st` and `ste` **can never match a French row**. They are inert for
France while being live for US/India. This is the concrete answer to the work order's question
about whether `ADDR_GENERIC` gets similar treatment to the France canon key-drop: **it does not
get its own scoping, and the FR key-drop actively hollows out two of its entries.**

`dr` is *not* inert for France: `ADDR_CANON_FR` re-adds it as `docteur -> dr` (normalize.py:208),
so `dr` matches French `dr` and `docteur` alike.

---

## 5. What I am NOT claiming

- I did **not** re-derive US_STATES / IN_STATES / FR_REGIONS coverage, the France postcode claim,
  `pin_eq` / `alt_tset`, or France blocking caps. All ruled out by the brief.
- I did **not** measure whether the D2 leak changes recall/score. The profile carries no key-level
  or recall data. **This is a gap, and it is the gap that matters:** D2 is proven to change the
  *contents of the blocking keys*, but I cannot show from the profile that it changes the metric.
  A direction word or `plz` in a key is a selectivity/dilution issue, not obviously a recall loss.
- The cross-country contamination in section 3 is **unquantified** (top-4000 truncation + no
  cross-country token provenance in the profile).
- I am **not proposing changes** - out of scope for D091, which is the ground-truth task the
  follow-on tasks depend on.

---

## 6. Handoff to the follow-on tasks

The ground truth, in one line each:

- `ADDR_GENERIC` = **62 unique lowercase strings**, list not dict, `keys.py:14-19`, **one call site** `keys.py:39`, **no country scoping**, **no self-map concept**, **no empty values possible**, **no duplicates**.
- It runs **after** canon, so it is a stoplist over canon *outputs*. Correct maintenance rule:
  **every key of `ADDR_CANON_COMMON`/`ADDR_CANON_FR` should have its canonical value in
  `ADDR_GENERIC`** if it is meant to be suppressed. That invariant is violated by 37 forms
  (US/India) / 57 forms (France), of which the identity-bearing ones are the city aliases and are
  *correctly* absent.
- The single self-inflicted hole is **`plaza -> plz`** (61,183 India occurrences).
- The single largest *defensible* addition is the **direction words** `n/s/e/w/ne/nw/se/sw`, which
  are pure noise and are already canonicalised.
- The French `saint`/`sainte` case is a **design decision that has not been made**, not a bug to
  be patched blind.

*Written by analysis agent a04, D091.*


