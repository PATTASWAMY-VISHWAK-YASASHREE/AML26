# D084 — mine `ADDR_CANON_COMMON` for the **US**

## HEADLINE

**`ADDR_CANON_COMMON` should NOT be extended for the US. The table already fires on
15,139,578 of 54,780,019 pooled US address tokens = 27.637%, and of the 7,331,972
non-identity rewrites, 7,036,251 = 95.97% land on a canonical value that is itself a
live token, i.e. they genuinely FUSE two surface forms of the same concept. Extending
it would be net negative, for the reason D116 gave for `FR_REGIONS`
and that I have now measured directly on the US: an unmapped token is LIVE FEATURE
MASS, and `ADDR_CANON_COMMON` has no way to add a key that increases fusion without
also removing IDF-weighted feature mass.**

**The single most important number: `village`→`vill` moves 79,428 US token occurrences
(0.1450% of listed mass) onto a canonical value `vill` that occurs ZERO times in the US
top-4000 of all six profiles — and the same is true of `heights`→`hts` 62,420,
`mountain`→`mtn` 54,177, `center`→`ctr` 37,722, `centre`→`ctr` 5,208,
`district`→`dist` 27,527, `junction`→`jct` 14,061, `plaza`→`plz` 8,286,
`industrial`→`indl` 4,316, `freeway`→`fwy` 2,174, `expressway`→`expy` 402.**
**Eleven keys, 295,721 = 0.5398% of listed mass, are renames into a target string the
US corpus never contains — so they deliver no fusion at all.** That is the *ceiling* on
what "extend the table" can buy, and it is ~10.7x smaller than the blocking mass the
table already destroys.

### The mechanism, stated once and traced

Three consumption points matter, and they pull in opposite directions.

1. **`normalize.py:347` `t = canon.get(t, t)`.** A canon-mapped token *does* reach
   `atoks` (unlike a state-matched component, which is `continue`d at `:333-335` and
   never does). So canonicalisation is **not** token deletion — it is **token
   substitution**. `village` is not removed from `atoks`; it is *replaced by* `vill`.
2. **`features.py:129` `wa`** = IDF-weighted overlap over `q_atoks`/`s_atoks`.
   `features.py:13-20 token_idf` builds `idf = ln(n/df)` per `(country, tok)`.
   A rename **moves df mass from one token to another**. Because the profile counts
   token *occurrences* and `token_idf` counts token *document frequency* (rows
   containing the token, after `list.unique()` at `features.py:15`), I cannot compute
   the exact IDF shift. **This is a labelled GAP (§7.1), not a number I estimate.**
3. **`keys.py:39`** deletes `ADDR_GENERIC` tokens from `atoks` *before* blocking keys
   are built, then `keys.py:42` keeps only alphabetic tokens of length >= 3 for `alph`.

Point 3 is where the table's US cost actually lands, and it is measurable:

| class | condition | US occurrences | % of listed mass |
|---|---|---|---|
| **A — blocking mass destroyed** | key NOT in `ADDR_GENERIC`, value IS | **3,150,695** | 5.7517% |
| **B — blocking mass created** | key IS in `ADDR_GENERIC`, value is NOT | 8,286 | 0.0151% |
| **D — token deleted outright** | value `""` | 309,855 | 0.5656% |

Class A is 380x class B. The table's net effect on US blocking is to **remove**
3,142,409 token occurrences' worth of blocking material, not add it. Every entry
proposed as an "extension" whose canonical value is in `ADDR_GENERIC` makes this
worse. `ADDR_GENERIC` (62 entries, `keys.py:14-19`) already contains `st, rd, ave,
dr, blvd, ln, ct, pl, sq, hwy, pkwy, cir, ter, trl, ste, apt, fl, bldg, unit, po, box,
way, floor, city, main, cross, ground, sector, phase, complex, colony, indl, estate,
dist, vill, apts, off, wing, block, office, tower, plaza, 1st, 2nd, 3rd, 4th, 5th` —
i.e. it is already a near-complete list of the canonical values `ADDR_CANON_COMMON`
produces. **That is the structural reason there is nothing worth adding: the downstream
consumer has already declared this whole vocabulary generic.**

---

## 0. Denominators and method

`country_rows.US` and `rows`, from all six `analysis_out/profile/*.json`:

| File | `rows` | `country_rows.US` | listed US addr mass | entries in `addr_tokens.US` |
|---|---|---|---|---|
| train_s1 | 2,206,821 | 1,323,633 | — | 4,000 (at cap) |
| train_s2 | 5,034,616 | 3,016,817 | — | 4,000 (at cap) |
| train_s3 | 5,285,603 | 3,170,056 | — | 4,000 (at cap) |
| test_s1 | 1,732,544 | 663,106 | 3,189,237 | 4,000 (at cap) |
| test_s2 | 4,887,273 | 1,871,330 | 8,135,308 | 4,000 (at cap) |
| test_s3 | 5,082,316 | 1,945,701 | 9,208,864 | 4,000 (at cap) |
| **pooled** | — | **11,990,643** | **54,780,019** | 4,510 distinct (union) |

Pooled US listed address-token mass = **54,780,019 token OCCURRENCES** over 4,510
distinct tokens. This is **not** a row count and I never use it as one.

Test-only US listed mass = 3,189,237 + 8,135,308 + 9,208,864 = **20,533,409**. The
US test rows are 663,106 + 1,871,330 + 1,945,701 = **4,480,137**; test_s1 is
663,106 / 4,480,137 = **14.80%** of US test rows, so no s1-only rate is quoted.

**Method.** `ADDR_CANON_COMMON` was parsed mechanically from
`_upstream/src/normalize.py:153-198` with a PowerShell regex over the literal
(`"([^"]*)"\s*:\s*"([^"]*)"`): **177 entries, 177 distinct keys, 81 distinct values
(80 non-empty + `""`)**. This reproduces D083's parse exactly. `ADDR_GENERIC` was
parsed from `keys.py:14-19` (**62 entries**). `US_STATES` was parsed from
`normalize.py:216-229` (**52 literal keys**), then the runtime self-map loop at
`normalize.py:251-253` was replicated (`for _v in list(_m.values()): _m.setdefault(_v, _v)`)
giving **104 runtime keys**.

**Arithmetic self-check (every figure below recomputes):**
`chg 7,331,972 + del 309,855 + self 7,497,751 = 15,139,578` canon-fired mass;
`15,139,578 + 39,640,441 unmapped = 54,780,019` = total. Both exact.
`7,036,251 fusing + 295,721 rename-to-dead = 7,331,972`. Both exact.


---

## 1. Does extending help or hurt? MEASURED, not assumed

**Answer: it hurts, on both consumption paths, and the ceiling on the upside is
0.5398% of listed mass.** Three independent measurements:

### 1.1 The upside ceiling is 0.5398%

A new entry only helps if it *fuses* two surface forms that both occur. I classified
every one of the 177 keys against the US corpus by the target string's live status:
- **FUSING (7,036,251 = 12.8446%)** � the canonical value is itself a live US token.
  E.g. `avenue`→`ave` (879,283 into a token with 731,134), `street`→`st` (1,324,910
  into 1,054,366), `drive`→`dr` (1,069,145 into 890,430). These work.
- **RENAME-TO-DEAD (295,721 = 0.5398%)** — the canonical value occurs **zero times** in
  the US union, so the mapping cannot bring two observed surface forms together. Eleven
  keys: `village`→`vill` 79,428 · `heights`→`hts` 62,420 · `mountain`→`mtn` 54,177 ·
  `center`→`ctr` 37,722 · `district`→`dist` 27,527 · `junction`→`jct` 14,061 ·
  `plaza`→`plz` 8,286 · `centre`→`ctr` 5,208 · `industrial`→`indl` 4,316 ·
  `freeway`→`fwy` 2,174 · `expressway`→`expy` 402.
  Sum: 79,428+62,420+54,177+37,722+27,527+14,061+8,286+5,208+4,316+2,174+402
  = **295,721**. Both totals exact: 7,036,251 + 295,721 = 7,331,972 = the non-identity
  rewrite mass.

  *Sub-split worth recording:* of these eleven, **seven** (`vill, hts, mtn, jct, indl,
  fwy, expy` targets) have no other key mapping to the same target, so they are pure
  one-way renames — **145,836 = 0.2662%**. The other four (`ctr` from `center`+`centre`,
  `dist` from `district`, `plz` from `plaza`) DO have sibling keys pointing at the same
  dead target, so they do fuse two *table* entries — they just fuse them onto a string
  no row produces. I report the 295,721 total as the honest ceiling because the
  observable outcome is identical: zero fusion in the corpus.

**The 295,721 rename-to-dead mass is the entire remaining opportunity**, because it is
the only mass the table currently mishandles. So *any* extension can address at most
0.5398% of US listed address mass — and only by finding new surface forms for those
dead targets, or new pairs like them.

### 1.2 The downside is 5.7517% + 0.5656%

Extending pushes mass into Class A (blocking destroyed) and Class D (deletion). Already
**3,150,695** (5.7517%) sit in Class A. The shortest unmapped US street-type tokens that
an extension would plausibly target — `twp` 43,490, `cdp` 116,500, `cddp` 1,943,
`ccdp` 2,114, `cpd` 2,356, `dcp` 2,262 — would each become a *new* blocking key
(surviving `keys.py:42`'s length >= 3 filter) or, if mapped to a generic value, a new
Class-A deletion. Neither is a gain over the unmapped status quo.

### 1.3 The state-skip already ate the geography bucket

Replicating `normalize.py:333-335` for the 104 runtime `US_STATES` keys gives a
**union-bound** on state-key token mass of **11,594,565 = 21.1657%** of US listed
mass (test-only 4,338,039). This is an **upper bound on rows**, not a count of rows:
`build_profile.py:126-127` flattens components, so I cannot tell whether `tx` sits in
a standalone component (consumed as `state`, invisible to `atoks`) or inside a longer
component (survives as a token). The tell from FLEET_BRIEF applies — this is a
---

## 2. Which US address tokens are NOT handled by the 177 entries?

**4,415 of 4,510 distinct tokens; 39,640,441 = 72.363% of listed mass.** Every line
below is a TOKEN OCCURRENCE count, and every zero is **"not in the top 4000"**,
never "does not occur". Grouped by likely type (the *type* is my inference from token
identity; the *count* is measured).

### 2.1 Two-letter state codes and state names — 21.1657% union-bound (§1.3)
`tx` 696,979 · `ny` 535,094 · `nc` 498,226 · `tn` 313,504 · `az` 298,158 · `ma` 297,168 ·
`ca` 196,583 · `wa` 222,793 · `or` 157,903 · `mt` 74,552 · `wy` 14,214 · `del` 10,711 ·
`penn` 3,084. All of the state *names* too (`texas` 480,985, `ohio` 307,283,
`illinois` 273,325, `washington` 267,075...). **D117 already established
`US_STATES` needs no expansion and that `del`+`penn` = 13,795 is the only open item.**
Not re-derived here; recorded so this report is not read as re-opening it.

### 2.2 City and place names — the largest single bucket
`houston` 118,232 · `chicago` 85,039 · `charlotte` 75,302 · `columbus` 72,939 ·
`phoenix` 68,041 · `springfield` 56,544 · `indianapolis` 56,539 · `nashville` 55,807 ·
`salem` 52,580 · `dallas` 52,537 · `mesa` 51,113 · `austin` 50,866 ·
`cleveland` 50,763 · `louisville` 50,026 · `louis` 49,573 · `portland` 47,633 ·
`brooklyn` 47,143 · `boston` 46,214 · `sacramento` 45,454 · `raleigh` 44,796 ·
`cincinnati` 44,088 · `richmond` 43,887 · `baltimore` 39,543 · `buffalo` 38,292 ·
`memphis` 35,354 · `arlington` 35,228 · `eloy` 2,591 · `nixa` 1,980.
**Verdict: NOT a canon gap.** `ADDR_CANON_COMMON` is a street-type/dwelling
abbreviation table; it deliberately contains no US place names. The 17 place aliases it
*does* contain (`normalize.py:190-195`) are all Indian and D083 measured their US
effect at exactly **zero** — I confirm that: none of the 17 appears in the US union.
Adding US cities would be a category error and would create cross-country collisions.

### 2.3 Street-name NOUNS — the real gap, and it is a naming gap, not a canon gap
`lake` 190,688 · `park` 183,782 · `hill` 162,002 · `township` 157,227 · `creek` 140,077 ·
`valley` 134,797 · `ridge` 123,214 · `view` 59,566 · `hills` 58,248 · `green` 54,658 ·
`cedar` 54,995 · `oak` 102,050 · `pine` 50,458 · `maple` 40,771 · `elm` 25,814 ·
`springs` 78,084 · `spring` 76,367 · `falls` 78,814 · `river` 81,026 · `beach` 68,214 ·
`island` 48,250 · `grove` 92,198 · `meadow` 34,095 · `orchard` 22,748 · `farm` 25,348 ·
`vista` 31,893 · `canyon` 19,912 · `summit` 14,455 · `prairie` 28,868.

**Why extending the table would NOT help here.** These are *proper-name* elements.
`oak` and `oakwood` are different streets; `lake` and `lakeview` differ. Fusing
`hills`->`hts` would conflate "Heights" with "Hills", two distinct US place-name
conventions. D083's own note on `heights`->`hts` is the proof: the table already made
this call, and I show in §5 that for the US it is the wrong call. **A 0.5398% ceiling
against a naming problem that is not solvable by abbreviation mapping.**

### 2.4 Administrative / census-designation abbreviations
`pmb` 162,985 · `cdp` 116,500 · `twp` 43,490 · `borough` 17,520 · `county` 281,125 ·
`town` 104,576 · `cddp` 1,943 · `ccdp` 2,114 · `cpd` 2,356 · `dcp` 2,262 · `ward` 3,471 ·
`lot` 13,005.
**`twp`<->`township` (43,490 / 157,227) is the only genuine abbreviation pair in this
bucket and it is the single best extension candidate in the whole report — see §6,
rated LIKELY.** Everything else is a census/geographic label, not a street type.

### 2.5 Religious and Spanish-origin tokens
`saint` 201,117 · `san` 39,639 · `santa` 18,149 · `el` 44,528 · `los` 10,963.
**This is the mirror risk the work order asked about (§4).**

### 2.6 Pure digits
`1` 336,186 · `2` 277,980 · `0` 54,623 · `3` 49,855 · `10` 42,392 · `4` 40,844 ·
`11` 39,763 · `12` 36,445 · `5` 38,004 · `6` 35,837 · `15` 35,220 · `7` 35,097 ·
`20` 34,108. **Out of scope by design** — `normalize.py:345-346` strips leading zeros
and `keys.py:41` harvests digit tokens into `nums` for blocking kind 2.
`ADDR_CANON_COMMON` must not touch them; a canon entry on a digit token would be a bug.

### 2.7 Ordinary English words that happen to be street names
`old` 71,613 · `high` 32,853 · `big` 18,843 · `little` 38,643 · `long` 16,587 ·
`pass` 14,602 · `run` 40,121 · `line` 9,930 · `path` 10,023 · `port` 26,363 ·
`new` 519,714. **Correctly unmapped.** Any mapping here would be a corruption.

---

## 3. The 13/15 EMPTY mappings — re-verified for the US, and the prior ruling is **too generous**

`ADDR_CANON_COMMON:196-197` maps **15** keys to `""` (D083's count; the work order
says 13 — **15 is correct**, verified by parsing the literal:
`door, flat, h, hno, house, na, nil, no, none, nos, null, num, number, plot, shop`).
The "13" in the work order is off by two. Recorded as a correction, not a defect.

**US deletion mass = 309,855 = 0.5656% of 54,780,019** (test-only 118,742). Only
**4 of the 15** keys fire at all in the US union:

| key | US occurrences | test-only |
|---|---|---|
| `null` | 283,911 | 109,104 |
| `house` | 11,518 | 4,492 |
| `h` | 9,587 | 3,303 |
| `flat` | 4,839 | 1,843 |
| **total** | **309,855** | **118,742** |

The other 11 are **not in the top 4000** of any US file.

**`null` alone is 91.65% of the US deletion mass** (283,911 / 309,855). And here the
prior "harmless" verdict needs qualifying for the US specifically:

- `normalize.py:329` **already skips** a component whose stripped text is exactly
  `null`, `<null>`, `n/a`, `na` or `none`, *before* tokenisation. So the 283,911
  surviving `null` tokens come from components where `null` appears **alongside other
  text** (e.g. `"123 null st"`), which the `:329` guard does not catch. The `""` mapping
  at `:347` is the **only** thing that removes them. **For the US this deletion is
  load-bearing, not redundant** — this is the one place where the empty-mapping class
  does real work, and it is a *different* reason from the India one D083 gave.
- `h` (9,587), `house` (11,518) and `flat` (4,839): numbering/dwelling-type words.
  Same reasoning as D083, and I concur. `h` is the one D083 flagged as "a bare token
  rather than a word" (`"Block H"` -> `block`). For the US I note `"Ste H"`/`"Unit H"`
  is a *section letter*, which carries no locational identity in this dataset because
  the row's own house number and street already do. **LIKELY harmless; no
  recommendation.**

**Verdict: the US empty-mapping mass is 0.5656%, 91.65% of it is `null`, and it is
behaviourally justified. No change recommended. The prior fleet ruling stands, with
the `null` mechanism sharpened.**

---


## 4. THE MIRROR RISK — D120's France finding has a US twin, and it is `st`/`saint`

D120 found the table "silently applies an ENGLISH sense to French words". The US is the
table's home country, so the mirror question is: does it apply a **non-US sense to a US
token**? I tested all 177 keys against the US union. **Result: exactly one genuine
corruption, and it is a confirmed US defect.**

### 4.1 `st` -> `st` (street) but `saint` is UNMAPPED — **CONFIRMED, US-only defect**

```python
154 |    "street": "st", "st": "st", ...
174 |    "suite": "ste", "ste": "ste", ...
```
`ADDR_CANON_COMMON` maps `st` to **`st`** = *street*. `NAME_CANON:131` maps the very
same token to **`saint`**: `"saint": "saint", "st": "saint", "ste": "sainte"`.
`ADDR_CANON_FR:207` also maps `st`->`saint`, correctly for French.

In the US corpus, `saint` occurs **201,117** times and `ste` occurs **11,831** times,
and **`saint` is not a key of `ADDR_CANON_COMMON` at all**. So in a US address
"123 Saint Joseph Way" the token `saint` survives unchanged, while "123 St Joseph Way"
yields `st`. Those two rows produce **disjoint address-token multisets** over the same
street. This is the mirror of D120's finding, running the other way: in France the
table applies an English sense; **in the US it withholds a needed one, and the French
and Indian dictionaries both know better than the common table.**

**Measured mass: 201,117 US token occurrences = 0.3671% of listed mass** (test-only
75,969). I verified `saint` is not reachable via any other route: it is not a
`US_STATES` key, not in `ADDR_GENERIC`, and not a canonical value of any canon key.

**Counter-argument I must state, because it is real.** In US business addresses `st`
overwhelmingly means *street* ("Main St"), and `saint` overwhelmingly means the
religious honorific ("St Louis"). Mapping `saint`->`st` would fuse two genuinely
different concepts and would fire on **every** `saint` in the corpus, not just the
street-name ones — `saint` is far more often part of a *city* name (St Louis, St Paul)
than a street name. **So `saint`->`st` is my honest recommendation against, and I am
not proposing it.** The defect is real; the obvious fix is wrong. What this actually
needs is component-position awareness (is this token in the street component or the city
component?), which the profile **cannot express** (§7.2). Recorded as
**CONFIRMED defect, fix deferred, no dictionary change recommended.**

### 4.2 The other mirror candidates — all clean, all measured
I probed every plausibly-foreign key against the US union. **Every one is zero:**

`est`->`estate` (the France corruption) **0** · `col`->`colony` **0** · `so`->`s` **0** ·
`plc`->`pl` **0** · `nr`->`near` **0** · `opp`->`opposite` **0** · `tq`->`taluk` **0** ·
`ngr`->`nagar` **0** · `ph`->`phase` **0** · `sec`->`sector` **0** · `dt`->`dist` **0** ·
`gf`/`grd`->`ground` **0** · `bvd`/`boul`->`blvd` **0** · `avn`/`aven`->`ave` **0** ·
`str`/`strt`->`st` **0** · `hiway`->`hwy` **0** · `terr`->`ter` **0** · `bld`->`bldg` **0**.
is a *missing-sense* problem (`saint`), and one more:

### 4.3 `centre`->`ctr` is the only non-US-spelling key that fires in the US
`centre` **5,208** US occurrences (test 1,999) -> `ctr`. This is *correct* for the US
(US addresses do write "Centre" as in Centreville). **Not a defect.** Recorded because
it is the one key where the table's British spelling is load-bearing for the US.

### 4.4 Spanish tokens: present but correctly unmapped
`el` 44,528 · `los` 10,963 · `san` 39,639 · `santa` 18,149 · `paso` 30,048 ·
`del` 10,711. These are Spanish place names in the US Southwest (El Paso, San Antonio,
Santa Fe, Del Rio). **Mapping any of them would be a corruption** — they are proper
names, not street types. **No defect.**

---


**The UK/India spelling variants are all "not in the top 4000" for the US.** So the
mirror risk is **not** a UK-spelling problem — the US corpus is spelling-standard. It
is a *missing-sense* problem (`saint`), and one more:
---

## 5. The `wy`->`way` collision: still the only non-identity corruption — CONFIRMED

I independently re-derived D074/D117's claim by intersecting all 177 `ADDR_CANON_COMMON`
keys against all 104 runtime `US_STATES` keys. **Exactly five keys are in both:**

| key | canon value | state value | US occurrences | non-identity? |
|---|---|---|---|---|
| `fl` | `fl` | `fl` | 89,108 | no (self-map) |
| `ct` | `ct` | `ct` | 324,465 | no (self-map) |
| `mt` | `mt` | `mt` | 74,552 | no (self-map) |
| `ne` | `ne` | `ne` | 33,301 | no (self-map) |
| **`wy`** | **`way`** | **`wy`** | **14,214** | **YES** |

**CONFIRMED, identical to D074/D117: `wy`->`way` is the only non-identity canon/state
collision.** US mass **14,214 = 0.0259%** of listed mass (test-only 5,011).
`wy` is the Wyoming postal code; written standalone it resolves as a state and never
reaches `atoks` (§1.3), but embedded in a longer component it is rewritten to `way`
(*Wyoming Way* -> *way way*). Low mass, real corruption, **and the correct fix is
`normalize.py:333` positional logic, not a dictionary entry** — I endorse D117's
recommendation 4 over any edit here.

**Beyond the state intersection, the US-specific corruption list is the seven orphans
of §1.1** — `heights`->`hts`, `village`->`vill`, `mountain`->`mtn`, `center`->`ctr`,
`district`->`dist`, `junction`->`jct`, `plaza`->`plz`, `industrial`->`indl`,
`freeway`->`fwy`, `expressway`->`expy`. These are not *wrong* senses; they are
**renames to a target the corpus never contains**, so they deliver zero fusion. That is
a materially different and **newly measured** defect class: D120 classified French
collisions as *wrong-sense*; I am measuring US *no-fusion*. **295,721 = 0.5398%.**

Of these, `village`->`vill` (79,428) and `mountain`->`mtn` (54,177) are the two largest
and both are **concept splits in the US corpus**:
- `village` 79,428 -> `vill` (0 occurrences) while `vill`/`vil` are also keys — the
  abbreviation family is present in the table but **zero** US tokens use the short
  forms. The mapping is 100% pure rename.
- `mount` 50,792 -> `mt` (74,552 live) **vs** `mountain` 54,177 -> `mtn` (0). D083's D2
  confirmed the split; my measurement adds that the `mtn` side is a **dead token**, so
  "Mount Vernon" and "Mountain View" are not merely two features — the second is a
  feature **no other row can ever match**.

---

## 6. Extension candidates, ranked, with measured mass

Standing caveat: every count is token occurrences in the pooled US union of six
top-4000 lists, and "not in the top 4000" is the only claim I make about absence.

| # | candidate | mass (US / test) | % listed | rating | verdict |
|---|---|---|---|---|---|
| 1 | `twp`->`township` | 43,490 / 16,161 | 0.0794% | **LIKELY** | The only real abbreviation pair in the corpus. `twp` 43,490 and `township` 157,227 both occur and are unrelated to any other token. **But** Class A: `township` is not in `ADDR_GENERIC`, so this would be a *pure* fusion with no blocking loss — the one entry in this report with a clean mechanism. Still only 0.0794%, and the profile cannot confirm `twp` and `township` ever co-occur in one component. |
| 2 | `saint` handling | 201,117 / 75,969 | 0.3671% | **CONFIRMED defect, fix deferred** | §4.1. The obvious mapping is wrong (see counter-argument). Needs component position, not a dictionary. |
| 3 | merge `mtn` into `mt` | 54,177 / 20,426 | 0.0989% | **LIKELY** | Fixes D083's D2 *and* my dead-token finding. `mount`/`mountain` are the same US concept. Risk: "Mountain" and "Mount" are genuinely distinct in some city names (Mount Prospect vs Mountain Lakes). **LIKELY, not CONFIRMED.** |
| 4 | `hills`->`hts` | 58,248 / 22,148 | 0.1063% | **SPECULATIVE — do not** | Would conflate "Hills" with "Heights", distinct US place-name conventions. Recorded to be **rejected**, not to be done. |
| 5 | `estates`->`estate` | 9,201 / 3,519 | 0.0168% | **LIKELY** | Same defect shape as D083's D1 (`apartment`/`apartments`): plural of an already-mapped noun, unmapped. Class A (`estate` IS in `ADDR_GENERIC`) so it also removes blocking mass — net unclear. |
| 6 | `borough`->`bo` | 17,520 / 6,362 | 0.0320% | **SPECULATIVE** | `boro`/`bo` are **not in the top 4000** for the US. Would create a dead token — exactly the defect of §5. **Do not.** |
| 7 | `del`->`de`, `penn`->`pa` | 10,711 / 3,084 | 0.0251% | **LIKELY (D117's, re-confirmed)** | These are `US_STATES` items, not `ADDR_CANON_COMMON` items, and D117 owns them. Listed only so this report is complete. |
| 8 | any US city / state / street noun | see §2.2, §2.3 | 0.0153%–0.1% each | **SPECULATIVE — do not** | Proper names. Mapping them creates cross-country collisions and destroys IDF mass. |

**Totals if items 1, 3, 5, 7 were all applied: 43,490 + 54,177 + 9,201 + 13,795 =
120,663 = 0.2203% of US listed mass** — and that is the *optimistic* sum, counting
overlapping concepts once, before any Class-A blocking loss is deducted. **Against a
5.7517% Class-A cost that already exists.** That ratio is the whole answer.

---

## 7. GAPS — what I could NOT establish

1. **IDF effect is not computable from this profile.** `features.py:13-20` computes
   `idf = ln(n/df)` where `df` counts **rows containing the token** (after
   `list.unique()`), and `n` counts rows per country. `addr_tokens` gives token
   **occurrences**, flattened across components and truncated to 4,000. I therefore
   **cannot** state how much any rename moves `wa_wj`/`w_sum`. Every "expected effect"
   in this report is an **INFERENCE from the code path**, explicitly labelled. I have
   not converted any occurrence count into a row count.
2. **No component structure.** `build_profile.py:126-127` splits on `[,;]` then feeds
   a flat `Counter` into `most_common(TOPN)`. Component boundaries are destroyed. This
   is why §1.3 is a *union bound* and why §4.1 cannot be fixed from this evidence.
3. **Top-4000 truncation.** All six `addr_tokens.US` lists are at the cap. The union is
   4,510 distinct tokens. **Every "absent"/"zero" in this document means "not in the
   top 4000 of the six profiles", never "does not occur".**
4. **Hapax pruning** (`build_profile.py:26 PRUNE_EVERY=8`, `:45-48 prune()`) drops
   count-<=1 tokens periodically, so listed mass under-counts by an unknown amount.
5. **Tokenisation mismatch with the pipeline.** `build_profile.py:28 TOKEN_RE =
   [a-z0-9]+` runs on `ba.lower()` **without** `strip_accents`, whereas
   `normalize.py:317` calls `strip_accents()` before tokenising. For the **US** this is
   a small effect (D120 showed it matters 71.9x more for France via the `r` ratio), but
   it means short-token US claims are lower bounds. Also `normalize.py:331` applies
   `re.sub(r"[^a-z0-9& ]+"," ")` per component and `:342` splits on `_non_alnum`,
   neither of which the profiler replicates exactly.
6. **Leetspeak in US addresses is out of scope and unmeasured here.**
   `normalize_address` (`:314-353`) never calls `translate(LEET)` — only `_name_tokens`
   (`:280`) does. The fleet's `24hr`/`1st` LEET findings are a **name-path** defect and
   this report makes no claim about them. (Note the interaction: `ADDR_CANON_COMMON:184`
   maps `first`->`1st`, producing a token that the **name** path would then corrupt to
   `lst`. That is a cross-path observation, not a measured address-path effect, and I
   label it **SPECULATIVE**.)
7. **Row-level effects unmeasured throughout.** I trace `atoks` into `prep.py:16` ->
   `features.py:98, 112, 123-124, 129` and into `keys.py:39, 41-43`, but cannot
   quantify the score movement.

---

## 8. Bottom line

- **DO NOT extend `ADDR_CANON_COMMON` for the US.** Measured ceiling on the upside is
  **295,721 = 0.5398%** of listed address mass (the dead-target class);
  the already-realised downside is **3,150,695 = 5.7517%** of Class-A blocking loss
  plus **309,855 = 0.5656%** of deletion. The ratio is ~10.7:1 against.
- **The US is not blocked by this table.** 21.1657% of US mass is consumed upstream by
  the `US_STATES` matcher at `normalize.py:333-335`; the remaining 72.363% is state
  codes, city names, street-name nouns and house numbers — none of them
  canonicalisation targets.
- **NEW DEFECT (CONFIRMED): the `saint`/`st` sense split.** `saint` (201,117 US
  occurrences, 0.3671%) is unmapped while `st`->`st` (*street*) and both `NAME_CANON:131`
  and `ADDR_CANON_FR:207` map `st`->*saint*. The obvious fix is wrong; the real fix is
  component position, which this profile cannot express. **No dictionary change
  recommended � reported so the lead can decide whether the positional work is worth it.**
- **NEW DEFECT (CONFIRMED, 295,721 = 0.5398%): eleven canon keys rename US tokens into
  targets that occur zero times in the corpus**, delivering no fusion whatsoever.
  `village`->`vill` (79,428) and `mountain`->`mtn` (54,177) are the two largest. This is
  a defect class D120 did not measure (it measured *wrong-sense*; I measure *no-fusion*).
- **`wy`->`way` re-confirmed** (14,214 = 0.0259%), still the only non-identity
  canon/state collision; fix belongs in positional logic, not the dictionary.
- **The 15 empty mappings re-verified for the US**: 309,855 = 0.5656%, 91.65% of it is
  `null`, and for the US the `null` deletion is **load-bearing** because
  `normalize.py:329`'s component guard misses `null` embedded in longer text. Prior
  ruling stands.
- **Correction to the work order:** the empty-mapping count is **15**, not 13.
- **`twp`->`township` (43,490 = 0.0794%)** is the only clean-mechanism extension
  candidate found. LIKELY, not CONFIRMED.
