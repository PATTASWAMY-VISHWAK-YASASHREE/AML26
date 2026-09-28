# D074 — audit current US_STATES

## Headline

`US_STATES` (`_upstream/src/normalize.py:216-229`) is **structurally perfect as a dictionary**:
**52 literal entries, 52 distinct canonical values, zero duplicate values, zero empty keys, zero
empty values, zero non-lowercase keys, zero whitespace anomalies, zero non-string values, zero
self-maps in the literal**, and full coverage — all 50 state postal codes present, the only two
values outside the 50-code reference set being `dc` and `pr`. **The known "missing self-maps"
defect does NOT apply to `US_STATES`**: the loop at `normalize.py:252` does include it and lifts it
to **104 runtime entries with all 52 self-maps present**, versus `FR_REGIONS` which stays at 14
runtime entries with 4 codes lacking self-maps.

The defects that do exist are **matching-semantics defects in `normalize_address`, not
dictionary-content defects**, and the worst of them is new: a **city component that happens to
equal a single-word state name is silently consumed as the state and deleted from the token
stream**. `500 Peachtree St, Washington, Georgia 30303` returns `state='wa'` (wrong — the row is
Georgia), emits `['500','peachtree','st','georgia','30303']` with **`washington` deleted**, and
**still fails to capture `ga`** because of defect A. One input, three simultaneous errors.

## Findings

### 1. Ground truth — literal contents (`normalize.py:216-229`, read-only)

Extracted by `exec` of the file text truncated immediately before `STATE_MAPS = {` (i.e. the
pre-loop literal), with `polars` stubbed in memory. No file in `_upstream/` was written.

| Property | Value |
|---|---|
| Literal entry count | **52** |
| Distinct canonical values | **52** |
| Duplicate values | **0** |
| Empty / whitespace-only keys | **0** |
| Empty / whitespace-only values | **0** |
| Non-string values | **0** |
| Keys not lowercase | **0** |
| Whitespace anomalies (`"  "`, untrimmed) | **0** |
| Self-maps already in the literal | **0** |
| Keys altered by the `ck` cleaner `re.sub(r"[^a-z0-9& ]+"," ",k)` | **0** (all 52 round-trip) |

**Coverage.** Against a reference set of the 50 state postal codes: `missing_states = []`,
`extra_codes = ['dc','pr']`. So `50 - 0 = 50` states present, plus DC and Puerto Rico.

**Shape.** 52 keys = **40 single-word** state names + **12 multi-word** keys. The 12 multi-word
keys (`district of columbia`, `new hampshire`, `new jersey`, `new mexico`, `new york`,
`north carolina`, `north dakota`, `puerto rico`, `rhode island`, `south carolina`,
`south dakota`, `west virginia`) can **never** appear as a single profile token, because
`build_profile.py:28` defines `TOKEN_RE = [a-z0-9]+`. Their absence from `addr_tokens` is a
**tokenisation artifact, not a data gap**.

### 2. Self-maps: present at runtime for `US_STATES`, absent for `FR_REGIONS`

Source (`normalize.py:250-254`), quoted verbatim:

```python
STATE_MAPS = {"US": US_STATES, "India": IN_STATES, "France": FR_REGIONS}
# abbreviations are canonical themselves
for _m in (US_STATES, IN_STATES):
    for _v in list(_m.values()):
        _m.setdefault(_v, _v)
```

| | `US_STATES` | `IN_STATES` | `FR_REGIONS` |
|---|---|---|---|
| Literal entries | 52 | 49 | 14 |
| Runtime entries | **104** | 86 | 14 (loop omits it) |
| Codes lacking a self-map | **`[]`** | `[]` | `['hdf','idf','naq','pdl']` |

`STATE_MAPS["US"] is US_STATES` → `True`, so the self-maps are visible through the lookup at
`normalize.py:318`. **This establishes ground truth: the self-map defect belongs to
`FR_REGIONS` only.** I do not re-derive the work order's already-covered claim about its
downstream effect.

### 3. Cross-dictionary overlap and country scoping

| Check | Result |
|---|---|
| `US_STATES` keys ∩ `IN_STATES` keys (literal) | **`[]`** — none |
| `US_STATES` values ∩ `IN_STATES` values | `['ar','ga','la','mn','tn']` |
| `US_STATES` keys ∩ `FR_REGIONS` keys | **`[]`** |
| `US_STATES` values ∩ `FR_REGIONS` values | **`[]`** |
| `STATE_MAPS` keyed by country (`normalize.py:318`) | yes — `smap = STATE_MAPS.get(country, {})` |

Country scoping is **sound**: `US_STATES` is unreachable from a France or India row. The
`ar/ga/la/mn/tn` value overlap between US and India is benign for the same reason.

Data-level confirmation that the risk is contained: US single-word state names appearing in the
**France** token stream are only `maine` (114 / 244 / 287) and `texas` (38 / 90 / 88) in
test_s1/s2/s3; **zero** US state names appear in the **India** token stream in any split.

### 4. Defect C (CONFIRMED) — `ADDR_CANON_COMMON` hijacks the `wy` state code

`US_STATES` values that are also keys of `ADDR_CANON_COMMON`: `ct→ct`, `fl→fl`, `mt→mt`,
`ne→ne` (harmless identity) and **`wy→way`** (corrupting). `ADDR_CANON_COMMON:176` reads
`"way": "way", "wy": "way",`. So whenever the state is *not* captured as a state, the token `wy`
is rewritten to `way`.

Measured with the real `normalize_address`:

| Input | country | `state` | `toks` |
|---|---|---|---|
| `12 Elm St, wy` | US | `'wy'` | `['12','elm','st']` |
| `12 Elm St, wy 10001` | US | **`''`** | `['12','elm','st','way','10001']` |

Occurrence counts (`addr_tokens["US"]`): `wy` = 1,336 / 3,675 / **absent**; `way` = 15,385 /
41,996 / 43,822. "Absent" means at or below the top-4000 floor (101 / 258 / 274), **not** zero —
`build_profile.py:27` caps at `TOPN = 4000` and `prune()` (lines 45-49) drops `count <= 1` every
8 chunks.

### 5. Defect A (CONFIRMED) — whole-component exact match (`normalize.py:331-335`)

```python
ck = re.sub(r"[^a-z0-9& ]+", " ", c).replace("&", " and ")
ck = " ".join(ck.split())
if ck in smap:
    state = smap[ck]
    continue
```

The test is on the **entire** component, so any component carrying extra material fails. Verified
against the real function:

| Input | country | `state` | `toks` |
|---|---|---|---|
| `175 Boulevard, Miami, FL` | US | `'fl'` | `['175','blvd','miami']` |
| `175 Boulevard, Miami, FL 33101` | US | **`''`** | `['175','blvd','miami','fl','33101']` |
| `500 Peachtree St, Atlanta, Georgia` | US | `'ga'` | `['500','peachtree','st','atlanta']` |
| `500 Peachtree St, Atlanta, Georgia 30303` | US | **`''`** | `['500','peachtree','st','atlanta','georgia','30303']` |
| `123 Main St, Springfield, Illinois 62704` | US | **`''`** | `['123','main','st','springfield','illinois','62704']` |
| `123 Main St, Springfield, IL 62704` | US | **`''`** | `['123','main','st','springfield','il','62704']` |

So defect A hits **both** 2-letter codes **and** full state names. Exposure is large:
`dig5 / rows` for US = 0.1098 (72,802/663,106) / 0.1097 (205,296/1,871,330) / 0.1101
(214,300/1,945,701) in test_s1/s2/s3.

**`dig5` counts occurrences, not rows** (`build_profile.py:115`: `s["dig5"] += len(DIG5.findall(bal))`),
so 0.1098 is *five-digit numbers per row*, **not** "11% of rows carry a ZIP". The fraction of
rows is ≤ 0.1098 and cannot be recovered from the profile. I flag this because it is the easiest
number in this report to over-claim.

The `ck` cleaner also destroys punctuated forms: `N.Y.` → `n y`, `D.C.` → `d c`,
`Mass.`/`Penn.`/`Fla.`/`Tenn.` → `mass`/`penn`/`fla`/`tenn` (none match). By contrast
`West-Virginia` → `west virginia` **does** match, so the failure is *interior* punctuation, not
trailing periods.

### 6. Defect B (CONFIRMED) — bare-word components are consumed as states **and deleted**

A matched component is `continue`d, so its tokens are **never emitted**. Any component consisting
only of a word that doubles as a state code or state name is swallowed.

| Input | country | `state` | `toks` | token deleted |
|---|---|---|---|---|
| `12 High St, in` | US | `'in'` | `['12','high','st']` | `in` |
| `12 High St, or` | US | `'or'` | `['12','high','st']` | `or` |
| `12 High St, de` | US | `'de'` | `['12','high','st']` | `de` |
| `12 High St, la` | US | `'la'` | `['12','high','st']` | `la` |
| `12 High St, co` | US | `'co'` | `['12','high','st']` | `co` |
| `12 High St, md` | US | `'md'` | `['12','high','st']` | `md` |
| `12 High St, pa` | US | `'pa'` | `['12','high','st']` | `pa` |
| `12 High St, me` | US | `'me'` | `['12','high','st']` | `me` |

`city_comps` is also emptied, so the deletion propagates into the city field.

### 7. Defect D (**NEW**) — a *city* named after a state is eaten, producing a wrong state

The 40 single-word state names include very common US city names. Any address whose **city
component** is one of them is mis-read as the state, and the city token is destroyed:

| Input | country | `state` | `toks` | `city` |
|---|---|---|---|---|
| `100 Main St, Washington` | US | **`'wa'`** | `['100','main','st']` | **`[]`** |
| `100 Main St, Georgia` | US | **`'ga'`** | `['100','main','st']` | **`[]`** |
| `100 Main St, Texas` | US | **`'tx'`** | `['100','main','st']` | **`[]`** |
| `100 Main St, Virginia` | US | **`'va'`** | `['100','main','st']` | **`[]`** |
| `100 Main St, Oklahoma` | US | **`'ok'`** | `['100','main','st']` | **`[]`** |
| `100 Main St, Indiana` | US | **`'in'`** | `['100','main','st']` | **`[]`** |
| `1 A St, Paris, Texas` | US | `'tx'` | `['1','a','st','paris']` | `['paris']` |

The compound case is the damaging one — three errors from one row:

```
'500 Peachtree St, Washington, Georgia 30303'  ->  state='wa'   (row is Georgia)
toks  = ['500','peachtree','st','georgia','30303']   ('washington' deleted)
city  = []                                                 ('washington' deleted from city too)
```

Compare the correct behaviour: `'500 Peachtree St, Atlanta, Georgia'` → `state='ga'`, city
`['atlanta']`. **Appending one ZIP to a Georgia address flips the resolved state from `ga` to
`wa` and destroys the city field.** A postcode can change the resolved state to a different, wrong
one — strictly worse than a missing state, and a failure mode not described in the work order.

Data exposure (city-like subset of the 40 single-word names, `addr_tokens["US"]`):

| Measurement | test_s1 | test_s2 | test_s3 |
|---|---|---|---|
| Occurrences of the 19 checked city-like names | 16,317 | 42,731 | 831,109 |
| `washington` alone | 6,830 | 18,051 | 76,647 |
| `texas` alone | 343 | 898 | 183,097 |
| `virginia` alone | 2,248 | 5,953 | 109,625 |
| `indiana` alone | 306 | 806 | 68,790 |
| `oklahoma` alone | absent (≤101) | 271 | 31,397 |

These are **token occurrences, not misfire counts** — `build_profile.py:126-127` splits the
address on `[,;]` and pushes `[a-z0-9]+` matches into one flat `Counter`, discarding component
boundaries. An occurrence of `washington` may be the state, the city, or a street name. **The
profile cannot tell them apart and I do not convert these into a row count.**

### 8. Defect E (**NEW**) — no `break`: the **last** matching component wins, position-dependent

The loop assigns `state = smap[ck]` on every match and never breaks, so with two matching
components the later one silently overwrites the earlier:

| Input | country | `state` |
|---|---|---|
| `1 A St, Washington, Texas` | US | **`'tx'`** |
| `1 A St, Texas, Washington` | US | **`'wa'`** |
| `1 A St, Virginia, West Virginia` | US | `'wv'` |
| `1 A St, New Delhi, Delhi` | India | `'dl'` |
| `1 A St, Orissa, Odisha` | India | `'od'` |

Reordering two components flips the resolved state. Under a canonical convention the state is the
**last** component, so last-wins is defensible — but it is currently **coincidental, not
enforced**: nothing in the code asserts position, and defect D's "city first, state last" rows
resolve correctly *only* because the real state happens to come last.

### 9. Defect F (**NEW**) — punctuated `D.C.` yields a confidently **wrong** state

```
'100 Main St, Washington, D.C.'  -> state='wa'   toks=['100','main','st','d','c']  city=['d c']
'100 Main St, Washington, DC'    -> state='dc'   toks=['100','main','st']
```

`D.C.` cleans to `d c`, which is not a key, so the state is lost — but the preceding component
`Washington` still matches and emits `wa`. The generalisable statement: **when a real state
component fails to match, defect D converts the failure from an empty state into a wrong state.**

### 10. Vocabulary exposure in US addresses (profile fields named)

`by_country["US"].rows` = 663,106 / 1,871,330 / 1,945,701.
`rows == sum(country_rows.values())` holds exactly in all three test profiles
(663,106 + 259,452 + 809,986 = 1,732,544 = `rows` for test_s1), confirming internal consistency.
`has_comma / rows` = 1.0000 / 0.9706 / 0.9716 — essentially every US address is comma-structured,
so the component logic always has ≥2 components to work with.

| Measurement | test_s1 | test_s2 | test_s3 |
|---|---|---|---|
| Code tokens present in top-4000 | 45 / 52 | 45 / 52 | **38 / 52** |
| Occurrences of those code tokens | 680,728 | 1,876,297 | 154,358 |
| Single-word state names present | 32 / 40 | 32 / 40 | 38 / 40 |
| Occurrences of those name tokens | 19,188 | 50,448 | 1,557,020 |
| `dig5 / rows` | 0.1098 | 0.1097 | 0.1101 |
| `dig6 / rows` | 0.0012 | 0.0143 | 0.0138 |
| top-4000 floor count | 101 | 258 | 274 |

Codes absent from the top-4000: test_s1 and test_s2 both `hi, mi, ms, nh, nj, nv, pr`; test_s3
`ak, ga, hi, id, mi, ms, nh, nj, nv, pr, ri, sc, sd, wy`. **Absent means count ≤ floor, not zero.**

**Correction to a pre-existing draft of this task:** that draft's table claimed "45 of 52" code
tokens present for *all three* test splits. Recount against `addr_tokens["US"]` gives
**45 / 45 / 38**; test_s3 has 14 absent codes, not 7. Its occurrence figure for test_s3 (154,358)
was correct, so the error was in the type count only. Flagged because the other two splits being
45/52 invites a false pattern.

### 11. Dictionary gaps probed

`penn` occurs 163 / 467 / 497 times in `addr_tokens["US"]` across test_s1/s2/s3 and is **not** a
`US_STATES` key. `del` occurs 646 / 1,779 / 1,842 but is already the Delaware **code** in
`US_STATES`, so it resolves and is not a gap. Probes returning **zero in all three profiles**:
`calif`, `fla`, `mass`, `tenn`, `tex`, `ariz`, `colo`, `conn`, `wisc`, `minn`, `miss`, `mont`,
`okla`. The five US territories absent from `US_STATES` (`guam`, `american samoa`,
`us virgin islands`, `northern mariana islands`, `us minor outlying islands`) are also absent
from `addr_tokens["US"]` in every test split.

### 12. `NAME_CANON` interaction

Measured precisely: the intersection of `US_STATES` **literal keys** with `NAME_CANON` keys is
**`[]`** — no full state name is claimed. At **runtime** the 52 self-maps make the codes keys too,
and then the intersection is `co, de, la, md, pa` (all identity mappings). `NAME_CANON` is applied
to business *names* (`normalize.py:281`) and `ADDR_CANON_COMMON` to *addresses*
(`normalize.py:347`), so the two never meet. **Not a defect.**

## Interpretation

The following is **inference**, separated from the measurements above.

1. **The dictionary is not the bottleneck; the matcher is.** `US_STATES` covers 50/50 + DC + PR
   with clean, lowercase, self-mapping values. Adding states would fix nothing the data shows as
   broken.
2. **Defects A, B, D and E interact, and the interaction is worse than any of them alone.** A
   postcode appended to a Georgia address that also contains the city `Washington` yields the
   wrong state `wa` *and* deletes the city. A last-wins overwrite with no positional check means
   the outcome depends on field order. **I would prioritise D over A**: A loses a field, D
   corrupts one and destroys another.
3. **Defect D is the one I would most want a human to check**, because it is the only defect here
   that can make a *correct-looking* state value appear where the truth is a different state, and
   because `washington` / `texas` / `virginia` / `indiana` are among the highest-frequency tokens
   measured here (up to 183,097 occurrences for `texas` in test_s3).
4. **The France-side analogue of defect B exists and is France-relevant.** `FR_REGIONS` maps
   `paris → idf`, so a French address with a standalone `Paris` component loses its city:
   `'5 Rue Lafayette, Paris'` → `state='idf'`, `toks=['5','rue','lafayette']`, `city=[]`. This is
   the identical mechanism. **`paris` occurs 388 / 952 / 923 times in `addr_tokens["France"]`.**
   I am **not** claiming a row count — `paris` in the token stream is not proof of a standalone
   `Paris` component. Flagged because `FR_REGIONS` conclusions belong to D070/D073, while the
   mechanism is what this task establishes.
5. **Country scoping is correct and should not be touched.** `STATE_MAPS` is country-keyed; the
   only US state names leaking into France's token stream (`maine`, `texas`) cannot match, and no
   US state name appears in India's stream at all.

## Gaps

- **Row-level misfire counts for defects A, B, D and E are NOT measurable from the profile.**
  `build_profile.py:126-127` splits on `[,;]`, applies `TOKEN_RE = [a-z0-9]+` per component, and
  updates a single flat `Counter`. Component boundaries are discarded, so the profile cannot
  distinguish a standalone `fl` component (state captured) from `fl` inside `Miami FL 33101`
  (state lost), nor `washington` as city from `washington` as state. **I have deliberately not
  multiplied the token counts above into a row count.**
- **`dig5`/`dig6` are occurrence totals, not row counts.** The share of US rows affected by defect
  A is bounded above by `dig5/rows` but is not equal to it, and the true row share is unavailable.
- **The 12 multi-word state names cannot be validated at all** from `addr_tokens`; they are
  structurally invisible to that field.
- **"Absent" never means "zero occurrences"** (`TOPN = 4000`, `prune()` dropping `count <= 1`).
  No rate computed from an absent token is valid, and I have not computed one.
- **I did not test whether French or Indian addresses contain a component matching a `US_STATES`
  key at the component level.** The token-level check in section 3 is the closest available proxy.
  The inference that they cannot match rests on the country-keyed lookup, not on measurement.
- **I did not examine `features.py` / `keys.py`.** Whether any of these defects change the final
  submission is therefore **unproven**; this task audited the dictionary and matcher only.
- **Not re-derived, per the work order:** the France `pin` guard and the `FR_REGIONS` resolution
  rate. For the record my numbers are consistent with both refutations — France `dig5/row` =
  0.0042 / 0.0051 / 0.0053 versus US 0.1098 / 0.1097 / 0.1101, and `FR_REGIONS` self-maps are
  absent (4 codes) with no key or value overlap against `US_STATES`.

## Recommendations

This task was explicitly told to establish ground truth and **not** propose dictionary changes.
Items 1-2 are the only dictionary statements; the rest are matcher changes.

1. **Do not add states to `US_STATES`.** 50/50 + DC + PR, clean, self-mapping. **The dictionary is
   not the bottleneck.** *(CONFIRMED)*
2. **The only dictionary item worth considering: `penn → pa`**, 163/467/497 occurrences,
   currently unmapped. *(LIKELY — `penn` is a standard Pennsylvania abbreviation, but the profile
   cannot show the surrounding component, so I cannot prove it is being used as a state.)* The five
   missing territories: **no action — they are absent from every test split (SPECULATIVE at best).**
3. **Fix defect D first — never treat a state-name match as authoritative without a positional
   check.** Require a state match to be the **final** component, or to be followed only by a
   postcode. Expected effect: stops city-named-after-a-state from producing a wrong state and
   from being deleted from `toks`/`city_comps`. **Confidence: CONFIRMED behaviour; row-level
   effect SPECULATIVE (profile gap above).**
4. **Fix defect A — after the whole-component test fails, also try a trailing `<code|name>
   <5-digit>` pattern.** Expected effect: recovers the state for part of the US rows carrying a
   `dig5`. **Confidence: CONFIRMED that the miss occurs; SPECULATIVE on the recovered count.**
5. **Make last-wins explicit (defect E) by breaking on the first positional match, or asserting
   the matched component is last.** Removes order-dependence. **CONFIRMED behaviour.**
6. **Fix the `wy → way` collision (defect C)** — either drop `"wy": "way"` from
   `ADDR_CANON_COMMON` or resolve a state code before the canon fallback. Low volume
   (1,336 occurrences in test_s1) but it corrupts a token rather than merely losing a field.
   **CONFIRMED.**
7. **Explicitly NOT recommended: touching `US_STATES` self-maps.** They are already complete
   (52/52 at runtime, 104 entries). "Fixing" `FR_REGIONS` on the assumption that it mirrors
   `US_STATES` is a separate change owned by D070, and the work order states its omission has zero
   measurable effect on this dataset.
