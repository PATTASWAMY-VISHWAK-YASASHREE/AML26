# D083 — Ground truth for `ADDR_CANON_COMMON` in `_upstream/src/normalize.py`

**Status:** COMPLETE (baseline only — no changes proposed).
**Scope:** `_upstream/src/normalize.py` lines 153–198 (the dict), 199–214 (`ADDR_CANON_FR`), 314–353 (`normalize_address`).
**Data:** `analysis_out/profile/{test_s1,test_s2,test_s3}.json`, fields `addr_tokens[country]` and `name_tokens[country]` (semantics defined at `build_profile.py:126–141`; top 4000 per country per file).
**Constraints honoured:** no raw TSV opened, no network, `_upstream/` and the dataset untouched, only this `.md` + its `.json` sidecar written.

---

## HEADLINE

`ADDR_CANON_COMMON` holds **177 entries mapping to 81 distinct canonical values** (80 non-empty; the 81st is `""`). It is **structurally sound** — the two defects everyone expects (missing self-maps, empty mappings) are **both absent in effect** — but it carries **four measurable defects** and **one structural gap**:

| # | Defect | Class | Measured mass (test s1+s2+s3) |
|---|---|---|---|
| D1 | `apartment`→`apt` but `apartments`→`apts` — one concept, two features | concept split | **127,071** token occurrences (India) |
| D2 | `mount`→`mt` but `mountain`→`mtn` | concept split | **20,426** (US) |
| D3 | `cross`→`cross` but `crossing`→`xing` | concept split | **9,230** (India 4,668 + US 4,562) |
| D4 | `est`→`estate` applies to **France**, where `est` is the French word for *east* | country scoping | **469** (France) |
| G1 | The France drop-list is a **key**-level filter, not a **value**-level one: 9 sibling keys still emit the 7 dropped values | structural gap | **0 — latent, not measurable** |

**The single most important number: France fires only 31–32 of the 177 keys — 628,736 canon hits over 11,992,918 address-token slots = 5.24%, against India 29.49% and US 27.62%.** `ADDR_CANON_COMMON` is, in practice, a US+India dictionary with a thin French fringe; for France the real vocabulary lives in `ADDR_CANON_FR`. The second most actionable number: **`appt` (5,113) and `appartement` (4,307) are both unmapped in France while `apt` (1,872) is mapped — the map handles the least frequent of the three surface forms of the same French word.**

**Nothing here contradicts any settled fleet finding.** The self-map question is answered *differently* from `FR_REGIONS` (§2.1) and that difference is load-bearing.

---


## 1. The dictionary, quoted from source

`_upstream/src/normalize.py:153–198` (verbatim, complete):

```python
153 | ADDR_CANON_COMMON = {
154 |     "street": "st", "st": "st", "str": "st", "strt": "st",
155 |     "road": "rd", "rd": "rd",
156 |     "avenue": "ave", "ave": "ave", "av": "ave", "aven": "ave", "avn": "ave",
157 |     "drive": "dr", "dr": "dr", "drv": "dr",
158 |     "boulevard": "blvd", "blvd": "blvd", "boul": "blvd", "bd": "blvd", "bvd": "blvd",
159 |     "lane": "ln", "ln": "ln",
160 |     "court": "ct", "ct": "ct", "crt": "ct",
161 |     "place": "pl", "pl": "pl", "plc": "pl",
162 |     "square": "sq", "sq": "sq",
163 |     "highway": "hwy", "hwy": "hwy", "hiway": "hwy",
164 |     "parkway": "pkwy", "pkwy": "pkwy", "pky": "pkwy",
165 |     "circle": "cir", "cir": "cir", "circ": "cir",
166 |     "terrace": "ter", "ter": "ter", "terr": "ter",
167 |     "trail": "trl", "trl": "trl",
168 |     "point": "pt", "pt": "pt",
169 |     "mount": "mt", "mt": "mt", "mountain": "mtn", "mtn": "mtn",
170 |     "fort": "ft", "ft": "ft",
171 |     "north": "n", "n": "n", "south": "s", "s": "s", "so": "s", "east": "e", "e": "e",
172 |     "west": "w", "w": "w", "northeast": "ne", "ne": "ne", "northwest": "nw", "nw": "nw",
173 |     "southeast": "se", "se": "se", "southwest": "sw", "sw": "sw",
174 |     "suite": "ste", "ste": "ste", "apartment": "apt", "apt": "apt", "floor": "fl", "fl": "fl",
175 |     "flr": "fl", "building": "bldg", "bldg": "bldg", "bld": "bldg", "unit": "unit",
176 |     "way": "way", "wy": "way", "expressway": "expy", "expy": "expy", "freeway": "fwy",
177 |     "fwy": "fwy", "route": "rte", "rte": "rte", "rt": "rte", "plaza": "plz", "plz": "plz",
178 |     "center": "ctr", "centre": "ctr", "ctr": "ctr", "heights": "hts", "hts": "hts",
179 |     "junction": "jct", "jct": "jct", "crossing": "xing", "xing": "xing",
180 |     "near": "near", "nr": "near", "opp": "opposite", "opposite": "opposite",
181 |     "cross": "cross", "main": "main", "nagar": "nagar", "ngr": "nagar",
182 |     "sector": "sector", "sec": "sector", "phase": "phase", "ph": "phase",
183 |     "ground": "ground", "grd": "ground", "gf": "ground",
184 |     "first": "1st", "second": "2nd", "third": "3rd", "fourth": "4th", "fifth": "5th",
185 |     "apartments": "apts", "apts": "apts", "complex": "complex", "cmplx": "complex",
186 |     "industrial": "indl", "indl": "indl", "estate": "estate", "est": "estate",
187 |     "colony": "colony", "col": "colony", "post": "po", "po": "po", "box": "box",
188 |     "district": "dist", "dist": "dist", "dt": "dist", "taluk": "taluk", "tq": "taluk",
189 |     "village": "vill", "vill": "vill", "vil": "vill", "city": "city",
190 |     "bengaluru": "bangalore", "bangalore": "bangalore", "bombay": "mumbai", "mumbai": "mumbai",
191 |     "gurugram": "gurgaon", "gurgaon": "gurgaon", "trivandrum": "thiruvananthapuram",
192 |     "calcutta": "kolkata", "madras": "chennai", "poona": "pune", "odisha": "orissa",
193 |     "keralam": "kerala", "ahmadabad": "ahmedabad", "vishakhapatnam": "visakhapatnam",
194 |     "vizag": "visakhapatnam", "mysuru": "mysore", "mangaluru": "mangalore", "cochin": "kochi",
195 |     "belagavi": "belgaum", "kozhikode": "calicut", "calicut": "calicut",
196 |     "number": "", "no": "", "nos": "", "num": "", "h": "", "hno": "", "house": "", "door": "",
197 |     "plot": "", "flat": "", "shop": "", "null": "", "na": "", "none": "", "nil": "",
198 | }
```

**Counts (parsed mechanically from the source text, regex `"([^"]*)"\s*:\s*"([^"]*)"` over lines 154–197):**
- entries: **177**
- distinct keys: **177** (no duplicate key)
- distinct canonical values: **81**, of which **1 is the empty string** (produced by 15 keys) → **80 non-empty canonical values**
- keys mapped to the empty string: **15**
- canonical values that are **not** themselves keys: **18** (`""` plus 17 non-empty — see §2.1)

### 1.1 How it is consumed

```python
314 | def normalize_address(raw: str, country: str):
315 |     """Return dict with tokens (no state), numbers, state code, pin, comps."""
316 |     s = translit_text(raw or "")
317 |     s = strip_accents(s).lower()
318 |     smap = STATE_MAPS.get(country, {})
319 |     canon = dict(ADDR_CANON_COMMON)
320 |     if country == "France":
321 |         canon = {**{k: v for k, v in ADDR_CANON_COMMON.items() if k not in ("st", "ste", "dr", "n", "s", "e", "w")}, **ADDR_CANON_FR}
...
342 |         for t in _non_alnum.split(c.replace("'", "")):
345 |             if t.isdigit():
346 |                 t = t.lstrip("0") or "0"
347 |             t = canon.get(t, t)
348 |             if t:
349 |                 ctoks.append(t)
```

Three properties follow directly from lines 342–349 and underpin every claim below:

1. **Single lookup, no cascade.** Line 347 is `canon.get(t, t)` — one pass. A canonical *value* is never re-fed through the map. So `suite → ste` stays `ste` in France even though `ste → sainte` exists in `ADDR_CANON_FR`.
2. **Empty string = token deletion.** Line 348 (`if t:`) drops falsy results, so all 15 empty mappings delete the token entirely.
3. **Identity fallback.** `canon.get(t, t)` means a token that is *not* a key survives unchanged. This is the single most important structural fact in this task — see §2.1.


## 2. Structural defects — the two that are NOT there

### 2.1 Missing self-maps: **NOT A DEFECT** (and this is the key contrast with the settled `FR_REGIONS` finding)

**18 canonical values are not keys:** `""`, `1st`, `2nd`, `3rd`, `4th`, `5th`, `ahmedabad`, `belgaum`, `chennai`, `kerala`, `kochi`, `kolkata`, `mangalore`, `mysore`, `orissa`, `pune`, `thiruvananthapuram`, `visakhapatnam`.

There is **no self-map loop** for this dictionary, unlike the state dictionaries:

```python
251 | # abbreviations are canonical themselves
252 | for _m in (US_STATES, IN_STATES):
253 |     for _v in list(_m.values()):
254 |         _m.setdefault(_v, _v)
```

**But none is needed here.** `ADDR_CANON_COMMON` is consumed through `canon.get(t, t)` (line 347), whose fallback *is* the self-map. Verified: `1st` occurs 157,535 times in India `addr_tokens` and `2nd` 167,919 times; both are absent from the key set, both are emitted unchanged, which is exactly the intent of `"first": "1st"` (line 184). **Zero behavioural effect.**

This is categorically different from `FR_REGIONS`, which is consumed through a *membership* test:

```python
333 |         if ck in smap:
334 |             state = smap[ck]
```

There is no fallback, so a missing self-map genuinely loses the match. **Do not port the `FR_REGIONS` self-map verdict (line 252 omits `FR_REGIONS`) onto `ADDR_CANON_COMMON`** — the two consumption sites have different semantics. The settled note that the `FR_REGIONS` self-map omission has zero effect on this dataset is unaffected either way.

### 2.2 Empty values: **CONFIRMED HARMLESS**, 15 entries

`"number", "no", "nos", "num", "h", "hno", "house", "door", "plot", "flat", "shop", "null", "na", "none", "nil"` → `""` (lines 196–197).

Measured mass deleted (sum of the 3 test files' `addr_tokens[country]` counts for exactly these 15 keys):

| country | token slots (denominator) | deleted-token mass | rate |
|---|---|---|---|
| India | 8,617,430 + 21,702,626 + 20,814,196 = **51,134,252** | **4,927,131** | **9.64%** |
| US | 3,189,237 + 8,135,308 + 9,208,864 = **20,533,409** | **118,742** | **0.58%** |
| France | 2,253,877 + 4,745,780 + 4,993,261 = **11,992,918** | **78,438** | **0.65%** |

France also deletes `n` (106,424) through `ADDR_CANON_FR:213`, taking true French deletion mass to **184,862 = 1.54%**.

**Verdict: harmless, and the fleet's earlier ruling stands.** Arithmetic behind it: `h.no` tokenises to `h` + `no`, both deleted, so Indian "H.No. 12" collapses to the bare house number already captured in `nums`; `plot` (474,686), `flat` (245,475), `door` (275,553), `shop` (121,719) are the dwelling-type nouns that follow the number, and deleting them stops a ~1-million-occurrence constant from diluting IDF weights in `features.py`. Every one of the 15 is a *numbering or type* word carrying no locational identity.

**One item flagged for the follow-on tasks, not a finding:** `h` is the single most-massful alphabetic empty key (**487,371** India occurrences) and is the only one that is a bare token rather than a word ("Block H" → "block"). No evidence in the profile that it carries identity, so I make no recommendation.


## 3. Concept splits — two DIFFERENT surface tokens, DIFFERENT canonical values, same street type

### 3.1 D1 — `apartment`/`apartments` → `apt` vs `apts` — **CONFIRMED, largest defect**

```python
174 |  ... "apartment": "apt", "apt": "apt", ...
185 |     "apartments": "apts", "apts": "apts", ...
```

Singular and plural of the same word, two different canonical values, 11 lines apart. Measured, summing the 3 test files:

| surface | India | US | France | → canonical |
|---|---|---|---|---|
| `apartment` | 60,630 | 30,573 | 0 | `apt` |
| `apt` | 18,366 | 26,395 | 1,872 | `apt` |
| `apartments` | 35,906 | not in top 4000 | 0 | `apts` |
| `apts` | 12,169 | not in top 4000 | 0 | `apts` |
| **totals** | `apt` **78,996** / `apts` **48,075** | `apt` **56,968** | `apt` **1,872** | |

- **India: 127,071 token occurrences** of one building-type word are split across two features (`apt` 78,996 / `apts` 48,075). Two rows saying "Apartment 5B" and "Apartments 5B" produce disjoint address-token multisets.
- The plural forms do **not** appear in the US or France top 4000 — say "not in the top 4000", not "absent".

### 3.2 D2 — `mount`/`mountain` → `mt` vs `mtn` — **CONFIRMED**

```python
169 |     "mount": "mt", "mt": "mt", "mountain": "mtn", "mtn": "mtn",
```

US only (`addr_tokens[US]`, 3 test files): `mount` 18,939 + `mt` 27,617 = **46,556 → `mt`**; `mountain` **20,426 → `mtn`**. India `mount` 5,317; no `mountain` in the India top 4000. "Mount Vernon" and "Mountain View" become two unrelated features.

### 3.3 D3 — `cross`/`crossing` → `cross` vs `xing` — **CONFIRMED**

```python
179 |     "junction": "jct", "jct": "jct", "crossing": "xing", "xing": "xing",
181 |     "cross": "cross", ...
```

| surface | India | US | → canonical |
|---|---|---|---|
| `cross` | 112,540 | 4,396 | `cross` |
| `crossing` | 4,668 | 4,562 | `xing` |
| `xing` | not in top 4000 | 830 | `xing` |

India: 112,540 occurrences of `cross` and 4,668 of `crossing` are the same Indian address landmark in two features. US: 4,396 + 4,562 + 830 = 9,788. The cross-country mass of the *split* — occurrences forced away from their own language's dominant form — is 4,668 (India) + 4,562 (US) = **9,230**.

### 3.4 Same-shape families that are **NOT** defects (recorded so later tasks do not re-open them)

- `road`→`rd` vs `route`→`rte` — genuinely different street types. US `road` 448,002 + `rd` 378,562; India `road` 1,107,409 + `rd` 80,914. Correctly kept apart.
- `place`→`pl` vs `plaza`→`plz` — different types.
- `highway`→`hwy`, `expressway`→`expy`, `freeway`→`fwy` — borderline (US 42,099 / 146 / 885). Same concept family, three values, but each is a conventional distinct US street name; I record this as **SPECULATIVE / do not change** rather than a defect.
- `terrace`→`ter`, `square`→`sq`, `place`→`pl`, all 5 `avenue` spellings → `ave`, `center`/`centre`/`ctr` → `ctr` — correctly merged.

### 3.5 Country-scoped splits inside `ADDR_CANON_COMMON`

- **`bld` (line 175) is the only key whose meaning changes by country:** `"bld": "bldg"` in COMMON, but `ADDR_CANON_FR:201` has `"bld": "blvd"`. The `{**common, **fr}` merge at line 321 makes France the winner. Correct for French (`bld` = *boulevard* there); it fires 0 times in the France top 4000.
- **17 India-only city/state aliases sit in the "COMMON" table** (lines 190–195: `bengaluru`, `bombay`, `gurugram`, `trivandrum`, `calcutta`, `madras`, `poona`, `odisha`, `keralam`, `ahmadabad`, `vishakhapatnam`, `vizag`, `mysuru`, `mangaluru`, `cochin`, `belagavi`, `kozhikode`). Structurally a country-scoping defect — they are applied verbatim to US and French addresses. **Measured effect: zero.** Every one of the 17 has count 0 in `addr_tokens[US]` and `addr_tokens[France]` across all three test files. Sum of those 17 keys = **353,055** token occurrences rewritten in India (`bengaluru` 49,692 + `bombay` 35,834 + `gurugram` 23,693 + `trivandrum` 18,422 + `calcutta` 49,092 + `madras` 23,304 + `poona` 10,226 + `odisha` 22,014 + `keralam` 35,979 + `ahmadabad` 33,597 + `vishakhapatnam` 14,919 + `vizag` 1,146 + `mysuru` 2,307 + `mangaluru` 468 + `cochin` 6,341 + `belagavi` 1,100 + `kozhikode` 24,921), plus `calicut`→`calicut` 6,589, a redundant self-map.
- **`odisha`/`keralam` conflict with `IN_STATES`.** `ADDR_CANON_COMMON:192` maps `"odisha": "orissa"` and `:193` `"keralam": "kerala"`, while `IN_STATES:236` maps `"odisha": "od"`, `"orissa": "od"`, and `:237` `"keralam": "kl"`, `"kerala": "kl"`. Because line 333 tests the whole component *before* line 347 tokenises, a standalone `"Odisha"` component becomes `od`; the same word embedded in a longer component becomes the string `orissa`/`kerala`. Measured: `odisha` 22,014, `orissa` 29,133, `keralam` 35,979, `kerala` 92,647 occurrences in India `addr_tokens`. **The profile has no component-position field, so I cannot split those counts by standalone vs embedded — labelled GAP, not a measured defect.**
- **`plc` is a cross-dictionary contradiction:** `ADDR_CANON_COMMON:161` `"plc": "pl"` (public limited company read as *place*), while `NAME_CANON:115` `"plc": "plc"`. Measured: `plc` has count 0 in `addr_tokens` for all three countries and all three files — latent.


## 4. Country scoping: what dropping `("st","ste","dr","n","s","e","w")` for France actually does

```python
319 |     canon = dict(ADDR_CANON_COMMON)
320 |     if country == "France":
321 |         canon = {**{k: v for k, v in ADDR_CANON_COMMON.items() if k not in ("st", "ste", "dr", "n", "s", "e", "w")}, **ADDR_CANON_FR}
```

Line 321 removes **7 exact keys** and then overlays `ADDR_CANON_FR` (68 entries, which wins on conflicts). Traced key by key, with measured French occurrence counts (`addr_tokens[France]`, union of the 3 test files' top 4000):

| dropped key | COMMON value | `ADDR_CANON_FR` entry | French occurrences of the key | net effect in France |
|---|---|---|---|---|
| `st` | `st` | `"st": "saint"` (:207) | **25,454** | **REAL CHANGE** → `saint` |
| `ste` | `ste` | `"ste": "sainte"` (:207) | **591** | **REAL CHANGE** → `sainte` |
| `n` | `n` | `"n": ""` (:213) | **106,424** | **REAL CHANGE** → deleted |
| `dr` | `dr` | `"dr": "dr"` (:208) | 256 | none — same target |
| `s` | `s` | absent | 12,701 | **none — see below** |
| `e` | `e` | absent | 45,410 | **none — see below** |
| `w` | `w` | absent | 104 | **none — see below** |

**Answers to the three sub-questions:**

1. **Does it lose information?** Only in one narrow, currently-latent way. `s`, `e`, `w` were **identity** maps (`"s": "s"`, `"e": "e"`, `"w": "w"`, lines 171–172) and have no `ADDR_CANON_FR` entry, so removing them changes nothing — `canon.get(t, t)` at line 347 returns the same string. Confirmed by arithmetic: 12,701 + 45,410 + 104 = **58,215 French token occurrences behave identically with or without the drop.** The fleet's earlier "France `w/e/s` differences are harmless" ruling is **CONFIRMED** by this trace.

2. **Does it create a gap?** **Yes — a structural one, with zero measured effect.** The filter removes the seven *keys*, not the seven *values*. Nine sibling keys still point at the dropped values and therefore still fire in France:

   | key | value | still mapped in France? | occurrences in France top 4000 |
   |---|---|---|---|
   | `street`, `str`, `strt` | `st` | yes | **0 — not in the top 4000** |
   | `suite` | `ste` | yes | **0 — not in the top 4000** |
   | `north` | `n` | yes | **0 — not in the top 4000** |
   | `south`, `so` | `s` | yes | **0 — not in the top 4000** |
   | `east` | `e` | yes | **0 — not in the top 4000** |
   | `west` | `w` | yes | **0 — not in the top 4000** |

   Consequence if those tokens ever appear in a French address: `street` → `st` while `st` → `saint` (a concept split, same shape as §3); `suite` → `ste` while `ste` → `sainte`; and France would still emit the tokens `n`/`s`/`e`/`w` from the long forms even though the bare letters are meant to be suppressed. **I cannot claim this fires — none of the nine appears in the France top 4000.** Gap: the profile truncates at 4000 tokens per country per file.

3. **Anything else France loses?** Only `dr`, and not even that: `drive`→`dr` and `drv`→`dr` (line 157) survive, and `ADDR_CANON_FR:208` `"docteur": "dr"` agrees, so France's `dr` is coherent either way.

**Net: of the entire 7-key drop mechanism, exactly 3 keys change behaviour (`st` 25,454, `n` 106,424, `ste` 591). The other 4 are no-ops.**


## 5. Coverage: what fraction of the dictionary each country actually uses

Canon hits = sum over the 177 keys of their `addr_tokens[country]` count; denominator = total `addr_tokens[country]` slots (the sum of all token counts in that field, one test file). This is a *token* rate, not a row rate.

| country | s1 hits / slots | s2 hits / slots | s3 hits / slots | 3-file total | rate | distinct keys fired (of 177) |
|---|---|---|---|---|---|---|
| India | 2,502,632 / 8,617,430 | 6,447,423 / 21,702,626 | 6,130,139 / 20,814,196 | **15,080,194 / 51,134,252** | **29.49%** | 119 / 123 / 123 |
| US | 887,473 / 3,189,237 | 2,187,234 / 8,135,308 | 2,596,973 / 9,208,864 | **5,671,680 / 20,533,409** | **27.62%** | 83 / 85 / 92 |
| France | 79,144 / 2,253,877 | 270,459 / 4,745,780 | 279,133 / 4,993,261 | **628,736 / 11,992,918** | **5.24%** | **31 / 32 / 32** |

France's rate is **~5.6× lower** than the other two countries', and it is lower even though French addresses are *longer* in tokens per row than US ones. The reason is structural: the French vocabulary lives almost entirely in `ADDR_CANON_FR`, not in the "COMMON" table this task is auditing. **This is the framing for any follow-on expansion work: `ADDR_CANON_COMMON` is misnamed for France, not merely incomplete.**

The complete set of 32 `ADDR_CANON_COMMON` keys that fire in the France top 4000 (count = union of the 3 test files):

```
apt 1872 | av 57361 | ave 21614 | avenue 126497 | bd 25273 | blvd 6046 | boulevard 38275
centre 967 | col 125 | dr 256 | e 45410 | est 469 | fort 1923 | h 5020 | n 106424
na 1397 | ne 6465 | no 72021 | pl 12989 | place 13363 | point 938 | rd 641 | route 17932
rte 11995 | s 12701 | se 556 | sq 458 | square 4933 | st 25454 | ste 591 | ter 7896
village 770 | w 104
```


## 6. Street-type token vs CITY name vs BUSINESS-NAME token

### 6.1 City names — no collision found for France

The France top 4000 union contains **4,441 distinct tokens**. Of those, 32 are `ADDR_CANON_COMMON` keys (§5 list). Cross-referencing that list against the dominant French place tokens in the same field — `bordeaux` 277,474, `nantes` 238,748, `lille` 221,585, `tourcoing` 115,914, `dunkerque` 111,538, `roubaix` 107,111, `nazaire` 88,016, `pessac` 81,815, `teste`/`buch` 72,268/72,331, `rignac` 51,156, `pornic` 50,117, `herblain` 44,846, `merignac` 14,416 — **there is no overlap. No French city is deleted or rewritten by this dictionary.** The nearest calls are `fort` (1,923), `point` (938), `village` (770) and `col` (125), all of which are far more likely street-type uses; the profile carries no component-position field, so I cannot prove their role. **Labelled GAP.**

### 6.2 D4 — `est` → `estate` in France: a direction word rewritten as a land-use word

```python
186 |     "industrial": "indl", "indl": "indl", "estate": "estate", "est": "estate",
```

`est` is the French word for *east*. It is a correct Indian abbreviation for *estate* (India `est` 4,691 occurrences) and a wrong French one — `ADDR_CANON_FR` has no `est` entry, so line 321 leaves `"est": "estate"` in force for France. Measured: **469 occurrences** in `addr_tokens[France]` (s1 76, s2 189, s3 204).

The French direction vocabulary is therefore inconsistent three ways:

| French direction word | count (France top 4000) | handling |
|---|---|---|
| `est` (east) | 469 | **→ `estate`** (English land-use noun) |
| `sud` (south) | 1,254 | **unmapped** |
| `ouest` (west) | 1,221 | **unmapped** |
| `nord` (north) | 152,011 | not in either canon map; handled only at whole-component level by `FR_REGIONS:244` |
| `n` / `s` / `e` / `w` (English) | 106,424 / 12,701 / 45,410 / 104 | suppressed (`n` deleted, `s`/`e`/`w` pass through) |

Class **LIKELY** (the direction reading of `est` is an inference; the profile has no field that disambiguates it), magnitude small (469 / 11,992,918 = 0.004% of French address tokens).

### 6.3 Business names — no interference, but one cross-dictionary vocabulary split

`normalize_name` never touches `ADDR_CANON_COMMON`; it uses `NAME_CANON` at line 281 (`toks.append(NAME_CANON.get(t, t))`). So a street-type word inside a business name is **not** rewritten by this dictionary — there is no deletion hazard. Measured cross-usage in France `name_tokens`: `s` 136,182, `centre` 56,194, `e` 35,433, `st` 2,561, `h` 1,181 — large in names, irrelevant here, because the two dicts are applied to different fields.

**But the two dictionaries canonicalise the same concept to different strings, so the two fields can never meet:**

| token | `ADDR_CANON_COMMON` (address) | `NAME_CANON` (name) | line refs |
|---|---|---|---|
| `center` / `centre` / `ctr` | `ctr` | `center` | :178 vs :124 |
| `st` | `st` (US) / `saint` (FR) | `saint` | :154 vs :131 |
| `ste` | `ste` (US) / `sainte` (FR) | `sainte` | :174 vs :131 |
| `plc` | `pl` | `plc` | :161 vs :115 |

The `st`/`ste` divergence is clearly deliberate (address = *street*/*suite*, name = *Saint*/*Sainte*). The `center` one is the material one: a US address token is `ctr` (US `center` 14,120 + `centre` 1,999 = 16,119 occurrences) while the same word in the name is `center`, so an address written "Center St" and a name written "Center" share no token. **Recorded as a real cross-feature split; no recommendation.**


## 7. French street types present in the data that NEITHER table maps

Source: `addr_tokens[France]`, union of `test_s1/s2/s3` top 4000. **Every line below is "present in the top 4000"; the tail is truncated, so absence from this list is not proof of absence from the data.**

| token | count | status | note |
|---|---|---|---|
| `appartement` | 4,307 | **UNMAPPED** | the full French word |
| `appt` | 5,113 | **UNMAPPED** | the standard French abbreviation |
| `apt` | 1,872 | COMMON → `apt` | **the only one of the three that is handled** |
| `passage` | 3,167 | **UNMAPPED** | French street type |
| `pont` | 3,866 | **UNMAPPED** | "Pont" as street type (bridge) |
| `clos` | 3,588 | **UNMAPPED** | French street type |
| `cite` | 2,546 | **UNMAPPED** | "Cité" (unaccented in the profile) |
| `parc` | 4,244 | **UNMAPPED** | |
| `port` | 3,825 | **UNMAPPED** | "Port" as street type |
| `gare` | 1,735 | **UNMAPPED** | |
| `mail` | 1,731 | **UNMAPPED** | "Le Mail", a standard French street name |
| `lotissement` | 1,788 | **UNMAPPED** | |
| `hameau` | 1,067 | **UNMAPPED** | |
| `esplanade` | 878 | **UNMAPPED** | |
| `parvis` | 587 | **UNMAPPED** | |
| `villa` | 594 | **UNMAPPED** | |
| `promenade` | 536 | **UNMAPPED** | |
| `venelle` | 481 | **UNMAPPED** | |
| `sentier` | 618 | **UNMAPPED** | |
| `rond` | 411 | **UNMAPPED** | (as in *rond-point*; `rondpoint` = 0, `carrefour` = 0, `traverse` = 0) |
| `mont` | 577 | **UNMAPPED** | vs COMMON `mount`→`mt` |
| `montagne` | 385 | **UNMAPPED** | vs COMMON `mountain`→`mtn` |
| `sud` | 1,254 | **UNMAPPED** | direction, §6.2 |
| `ouest` | 1,221 | **UNMAPPED** | direction, §6.2 |

Upper bound on my (non-exhaustive) list: **44,519 token occurrences** unmapped, of which the apartment family alone is 9,420 (`appt` 5,113 + `appartement` 4,307) against 1,872 handled.

**The single cleanest gap in this whole task: France has three surface forms for "apartment" — `apt` (mapped, 1,872), `appt` (unmapped, 5,113) and `appartement` (unmapped, 4,307) — and the map handles the least frequent one.** It also compounds D1: `apt` and `apts` are already different features, and `appt`/`appartement` would add two more.

**Measurement caveat that matters here:** `build_profile.py:28` uses `TOKEN_RE = re.compile(r"[a-z0-9]+")` and does **not** strip accents, whereas `normalize.py:317` calls `strip_accents`. So accented French street types are fragmented in the profile (e.g. `résidence` appears as `r`+`sidence`; note the stray `sident` 3,106 in the raw France token list). My counts for accented words are therefore **lower bounds**, and some unmapped accented street types may be invisible rather than absent.

Already correctly handled by `ADDR_CANON_FR` (for completeness, these are **not** gaps): `rue`/`r`, `avenue`/`av`, `boulevard`/`bd`/`boul`, `chemin`/`ch`/`chem`/`che`, `impasse`/`imp` (21,102), `place`/`pl`, `route`/`rte`, `allee`/`all`/`al` (17,779), `square`/`sq`, `faubourg`/`fbg`/`fg`, `cours`/`crs`, `quai`/`q`/`qu`, `saint` (141,364), `sainte`, `general`/`gen`/`gal`, `docteur`/`dr`, `professeur`/`prof`, `marechal`/`mal`, `president`/`pres`, `residence`/`res` (4,748), `batiment`/`bat`, `bis`/`b`, `ter`/`t`, `lieu`, `lieudit`, `zone`/`za`/`zi`/`zac`, `no`/`n`/`numero`/`null`/`na`.


## 8. Explicit non-findings (recorded to stop re-derivation)

1. **No self-map defect.** §2.1 — 18 non-key canonical values, zero behavioural effect, because line 347's `canon.get(t, t)` fallback *is* the self-map.
2. **No empty-mapping defect.** §2.2 — 15 entries, 4,927,131 India / 118,742 US / 78,438 France deletions, all numbering or dwelling-type words.
3. **No France key-loss from `s`/`e`/`w`.** §4 — 58,215 occurrences, behaviourally identical either way. Fleet ruling CONFIRMED.
4. **No cross-country key collision between the two dicts** other than `bld` (`bldg` vs `blvd`, correct for France) and the 3 `st`/`ste`/`n` overrides, all intentional.
5. **No `plc` hazard in the data** — 0 occurrences in `addr_tokens` for all 3 countries × 3 files.
6. **No French city is rewritten** — §6.1, 32 keys vs 13 dominant place names, zero intersection.

## 9. Labelled GAPS (fields the profile does not collect)

- **Component position.** `addr_tokens` is a flat per-country `Counter` (`build_profile.py:126–127`); nothing marks a token as street / city / region. Every claim about "this token is a city name" or "this token is a street type" is an inference from token identity and frequency, not a measurement.
- **Top-4000 truncation** (`build_profile.py:27 TOPN = 4000`, plus `prune()` at lines 45–49 which drops count-1 tokens). Every zero in this document means "not in the top 4000 of the three test files", never "does not occur".
- **Accent fragmentation** — §7 caveat. `build_profile.py:28 TOKEN_RE` does not strip accents; `normalize.py:317` does.
- **No France rows in train.** `country_rows` in `train_s1/s2/s3` contains only `US` and `India`; France appears only in test, so every France figure here is test-only by construction.
- **Row-level rates are not available** for any count here; all rates above are token-level over `addr_tokens` totals, and the denominator is printed alongside every rate.

## 10. Method / reproducibility

All code claims are quoted from `_upstream/src/normalize.py` at the line numbers given. All data numbers come from `analysis_out/profile/{test_s1,test_s2,test_s3}.json`, fields `addr_tokens[country]`, `name_tokens[country]`, `country_rows`, with the denominator printed alongside every rate. The dictionary was parsed mechanically with a PowerShell regex over lines 154–197 (177 pairs, 177 distinct keys, 81 distinct values) rather than counted by eye. Python is broken on this box; no raw TSV was opened; nothing under `_upstream/` or the dataset was modified.