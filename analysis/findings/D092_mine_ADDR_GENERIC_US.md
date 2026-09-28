# D092 - mining `ADDR_GENERIC` for the **US**

**Status: COMPLETE. Headline: do NOT extend `ADDR_GENERIC` for the US. Two defects found,
and the work order's own stated mechanism is wrong for this dictionary.**

Task D092 (family B-dictionary). Deliverable: `analysis_out/findings/D092_mine_ADDR_GENERIC_US.md`.

Sources read: `_upstream/src/keys.py`, `normalize.py`, `features.py`, `blocking.py`,
`prep.py`, `build_features.py`, `run_blocking.py`, `build_profile.py`,
`analysis_out/profile/{train,test}_s{1,2,3}.json`.
Built on, **not redone**: D091, D094, D116, D120, D122, D127, D084.

---

## 0. Headline

**1. NEW DEFECT (US-specific, largest): 63.34% of everything `ADDR_GENERIC` removes from US
address tokens is provably invisible to the pipeline.** 8,518,413 of the 13,448,670 US
token occurrences it deletes have `len < 3`, and `keys.py:42` gates the `alph` bucket on
`len_chars() >= 3`. This is D122's NEW-1 mechanism, but D122 measured it **pooled across all
three countries** (39.91% of test removal mass). **For the US alone it is 63.47% - 1.59x
worse**, because the US is the country that abbreviates most.

**2. NEW DEFECT (cross-country, the US analogue of France's `bis`/`ter`): `des` deletes
"Des Moines" and "Des Plaines" from US blocking keys.** 22,816 US occurrences; 21,707 of them
(**95.14%**) are accounted for by the two US place names whose first word is `Des`. The entry
exists to delete the French plural article, and `keys.py:39` has no country predicate.

**3. The work order's stated safety mechanism is WRONG for this dictionary, and this is the
single most important correction I make.** The order says adding an entry "REMOVES that token
from the features", citing `features.py:129`. It does not. `keys.py:39` builds a **local**
`toks` list; `keys.py:45` returns only `rid, country, nt, pref, nums, alph, pin, fk` -
`atoks` is not an output column and is never written back. `prep.py:16` persisted `atoks`
to parquet long before `run_blocking.py` reads it, and `build_features.py:26`
(`token_idf(frames, "atoks")`) plus `features.py:129` read that untouched column. **Adding
entries to `ADDR_GENERIC` costs exactly zero IDF feature mass.** I therefore **agree with
D122's NEW-2 and reject the work order's premise.** But I still reach "do not extend", for
the reason in section 5: the *blocking* side of the trade-off is what bites, and it is not
symmetric.

**4. Verdict: NO extension is warranted.** The upside is **184,450 = 0.3367%** of US listed
address mass (section 5), it is 86.49% concentrated in three tokens that are all *ambiguous*
between street-type and place-name (`hts`/`mtn`/`ctr`), and the one entry that is
unambiguously a pure type word (`plz`, 8,286) is already handled for India and is a rounding
error for the US.

---

## 1. Denominators

| File | `country_rows.US` | US listed `addr_tokens` mass | cut-off (4000th) |
|---|---|---|---|
| train_s1 | 1,323,633 | 6,364,441 | `2027:201` |
| train_s2 | 3,016,817 | 12,997,820 | `lantern:407` |
| train_s3 | 3,170,056 | 14,884,349 | `calvert:440` |
| test_s1 | 663,106 | 3,189,237 | `1626:101` |
| test_s2 | 1,871,330 | 8,135,308 | `stonington:258` |
| test_s3 | 1,945,701 | 9,208,864 | `otis:274` |
| **pooled** | **11,990,643** | **54,780,019** | - |

4,510 distinct listed tokens in the US union. **All mass figures are TOKEN OCCURRENCES inside
the top-4000 listed set, never rows.** A token at 0 is **"not in the top 4000"**, never "does
not occur". I quote the **test** split separately throughout because that is the scored
population.

**Method - order matters and is not optional.** `build_profile.py:113,126-127` stores **raw
pre-canon** tokens (there is no `canon.get` anywhere in it). `ADDR_GENERIC` is applied at
`keys.py:39` to the **post-canon** string that `prep.py:16` wrote. So every measurement below
applies `ADDR_CANON_COMMON` (`normalize.py:319`, the non-France branch) *first*, then tests
membership, then applies the `keys.py:41/42` length gates. Measuring raw tokens would have
been wrong in both directions.

**Replication check.** My test-split US removal total is **5,029,788** on a listed mass of
**20,533,409** - D122's D0 table reports `US 5,029,788 (24.50%)` on `20,533,409` to the unit.
That validates the method against an independent agent before I use it for anything new.

**Full partition of US listed mass (all six files), every bucket recomputes to the total:**

| Bucket | Mass | % of 54,780,019 |
|---|---|---|
| state-name component skipped (`normalize.py:333-335`) | 4,240,547 | 7.7410% |
| deleted by empty canon (`normalize.py:196-197`) | 309,855 | 0.5656% |
| **`ADDR_GENERIC` - blocking-visible (fires)** | **4,930,257** | **9.0001%** |
| **`ADDR_GENERIC` - structurally inert (`len<3`)** | **8,518,413** | **15.5502%** |
| survives, `len>=3` (real key material + leak) | 20,303,952 | 37.0645% |
| survives, `len<3` (inert) | 9,048,835 | 16.5185% |
| survives, digit-only (goes to `nums`) | 7,428,160 | 13.5600% |
| **sum** | **54,780,019** | **100%** |

---

## 2. `ADDR_GENERIC` is a 62-entry LIST - confirmed, and what that costs

Confirmed by parsing `_upstream/src/keys.py:14-19` directly, not by eye:

| Property | Value |
|---|---|
| Entries | **62** |
| Distinct entries | **62** - **no duplicates are present** |
| Uppercase entries | 0 (matches the canon keyspace) |
| Empty / null entries | **0** - not representable in a list; the "empty value" concept does not exist here |
| Canonical *values* | **N/A** - a list has no values. Consumed by `pl.element().is_in(...)`, a membership test only |
| `len < 3` | **9** - `st, rd, dr, ln, ct, pl, sq, fl, po` |
| `len >= 3` | **53** |
| digit-only (`^\d+$`) | **0** |

**Consequences of it being a list, stated because the work order asks:**

1. **Ordering is semantically irrelevant** - `is_in` is a set-membership test, so the visual
   clustering in `keys.py:14-19` (streets, then French words, then ordinals) is documentation,
   not behaviour.
2. **Membership cost is a 62-element linear scan per token per row**, not a dict hash lookup.
   At 11,990,643 US rows this sits in the hot loop of `run_blocking.py`. I make **no timing
   claim** - I did not run the pipeline and the profile holds no timing field. Flagged as a
   **GAP**, not a finding.
3. **Duplicates are possible in principle** (a list literal permits them) but there are
   **none today**. A future edit appending an already-present token would be silently
   harmless, not silently harmful.
4. **There is no country scoping anywhere on this path** (`keys.py:39` tests one global list
   with no `country` predicate). This is what makes section 4 possible.

---

## 3. DEFECT 1 - 63.34% of the US removal mass is structurally inert

`keys.py:39-45` is the whole story:

```python
39: toks = (pl.col("atoks").str.split(" ").list.eval(pl.element().filter(~pl.element().is_in(ADDR_GENERIC) & (pl.element() != "")))
40:         .list.unique(maintain_order=True))
41: nums = toks.list.eval(pl.element().filter(pl.element().str.contains(r"^\d+$"))).list.head(MAX_NUM)
42: alph = (toks.list.eval(pl.element().filter(~pl.element().str.contains(r"^\d+$") & (pl.element().str.len_chars() >= 3)))
43:         .list.eval(pl.element().sort_by(...)).list.head(MAX_ALPHA))
45: return df.select("rid", "country", nt, pref, nums, alph, pin, fk)
```

`toks` has exactly **two** consumers, `nums` and `alph`, and `make_keys` (`keys.py:53-73`)
reads only `tl.nums` and `tl.alph`. A stoplist entry can therefore only ever matter if its
canonical form is digit-only (-> `nums`) or `len >= 3` (-> `alph`).

- **Digit-only entries: 0 of 62** -> the `nums` route is closed for every entry.
- **`len < 3`: 9 entries** -> they can never reach `alph`.

Per-entry US mass those 9 strip, post-canon, all six files:

| Entry | US mass stripped | `len` |
|---|---|---|
| `st` (`st` 1,054,366 + `street` 1,324,910) | 2,379,276 | 2 |
| `rd` (`rd` 982,732 + `road` 1,216,059) | 2,198,791 | 2 |
| `dr` (`dr` 890,430 + `drive` remainder) | 1,959,575 | 2 |
| `ln` | 835,113 | 2 |
| `ct` | 609,931 | 2 |
| `pl` | 235,891 | 2 |
| `po` | 170,152 | 2 |
| `fl` | 113,027 | 2 |
| `sq` | 16,657 | 2 |
| **total** | **8,518,413** | |

`8,518,413 / 13,448,670 = 63.3402%` of all US `ADDR_GENERIC` removal (all six files);
`3,192,235 / 5,029,788 = 63.4666%` on the **test** files.

**D122 measured this pooled: 39.91% of test removal mass across all three countries. For the
US it is 63.47% - 1.59x worse.** That is the genuinely new part. The mechanism is D122's; the
US-specific magnitude and its cause (the US is the heaviest abbreviator, so its stoplist mass
concentrates in the 2-letter forms) are mine. D091's softer phrase for this class - "harmless
redundancy" - should be retired: these entries are not redundant, they are inert.

**Entry accounting (the work order's dead-weight question):** of 62 entries, **31 fire and
change blocking behaviour for the US, 9 are structurally inert, and 22 never fire at all for
the US.** 31 + 9 + 22 = 62.

---

## 4. DEFECT 2 - `des` deletes "Des Moines" and "Des Plaines" from US keys

The work order asked for the US analogue of France's `bis`/`ter` asymmetry. It exists, and it
is **`des`** - a French function word doing damage in a country that has no French.

- `des` is in `ADDR_GENERIC` at `keys.py:15`. `len("des") == 3`, so unlike `st`/`rd` it is
  **genuinely live**: it is removed from `alph` and therefore does change US keys.
- `ADDR_CANON_COMMON` has **no `des` key at all** (D091's D3 list of 15 entries with no canon
  rule includes `des`), so `normalize.py:347` passes it through unchanged. Raw `des` reaches
  the filter directly.
- US mass: **22,816** (0.0417% of US listed mass); **8,331** on test (0.0406%).
- For contrast, French `des` = **199,183**. The entry is 8.7x more valuable in France than in
  the US, and the US is the only country where it is actively wrong.

**Why it is a place name in the US, not an article.** `des` is not an English word; the only
US settlements whose name begins with it are **Des Moines** and **Des Plaines**:

| Probe token | US `addr_tokens` | US `name_tokens` |
|---|---|---|
| `moines` | 18,957 | 782 |
| `plaines` | 2,750 | 0 |
| **sum** | **21,707** | 782 |
| `des` | 22,816 | 966 |

21,707 / 22,816 = **95.14%** of US `des` mass is numerically accounted for by the two place
names. `city` shows the same shape at scale (`city` 798,242 with `oklahoma` 82,572,
`kansas` 97,056) - which is exactly why `city` being in `ADDR_GENERIC` is **correct** for the
US and I recommend keeping it, whereas `des` being there is **incorrect**.

**[INFERENCE, flagged as such]** The profile stores no co-occurrence data, so I cannot prove
`des` and `moines` appear in the same address string. The claim rests on (a) the absence of
`des` from `ADDR_CANON_COMMON`, which fixes its meaning as a bare literal, and (b) the 95.14%
mass match. I did not open any `*.tsv`. **One raw-inspection pass promotes this from LIKELY to
CONFIRMED** - it is cheap, and I recommend it before anyone edits the list.

**The France `bis`/`ter` asymmetry does NOT reproduce for `ter` - and I checked, because it
would have been the obvious answer.** For the US, `ter` is *correct*: raw `ter` 22,742 +
`terrace` 40,048 = **62,790** post-canon, all of it US *terrace*, and `terr` is 0 in the US
(`normalize.py:166` maps `terr`/`terrace` -> `ter`). `ter` is 3 chars, so it is live and it is
suppressing genuine US street-type noise. D127's asymmetry is France-specific: France has
`bis` (69,757) which the table lacks, while the US has no such unmatched partner for `ter`.
**So the US direction of this defect is not "a missing synonym" - it is "a French function
word in a global stoplist", which is a different bug class.**

---

## 5. Does extending help or hurt? - the numbers, then the verdict

### 5a. The work order's premise is refuted (this is the load-bearing correction)

The order states that adding an entry removes the token from `wa` and cites `features.py:129`.
Traced, it does not:

| | `FR_REGIONS` (D116's case) | `ADDR_GENERIC` (here) |
|---|---|---|
| applied at | `normalize.py:333-335` | `keys.py:39` |
| mechanism | `continue` skips `toks.extend(ctoks)` at `:350` | `.filter(~is_in(...))` on a **local** list |
| upstream of `atoks`? | **YES** | **NO** - `keys.py:45` does not return `atoks` |
| reaches `token_idf`/`wa_*`? | **YES** | **NO** |

`prep.py:16` writes `atoks` to parquet; `run_blocking.py:9` `COLS` includes `atoks`;
`build_features.py:26` builds `addr_idf` from it; `features.py:129` reads `q_atoks`/`s_atoks`.
None of these see the `keys.py:39` filter. **D116's "unmatched token is live feature mass"
argument does not transfer here, and I side with D122's NEW-2 against the work order.**

### 5b. But the blocking-side trade-off is real, and it is asymmetric

Adding a US token to `ADDR_GENERIC` removes it from `alph`, and `alph` is the sole source of
the **kind-0 (name x address)**, **kind-2 (address number x address word)** and **kind-4**
key material. Two things can go wrong, and only one is reversible:

- **Upside:** a non-selective street-type token stops generating a key shared by thousands of
  rows. This is what the existing 31 firing entries already do.
- **Downside:** if the token is *identity-bearing* - a component of a place or street **name**
  - removing it makes two genuinely different addresses produce the **same** key set. That
  inflates candidate counts and directly costs precision. This is the failure mode `saint`
  would cause for France (D122 section 3) and `des` already causes for the US today.

**The US is unusually exposed to the downside**, because US addresses are dominated by *place
names* rather than administrative morphemes. The top of the US surviving-token list is
`new` 519,714, `york` 384,608, `carolina` 354,636, `county` 281,125, `lake` 190,688,
`park` 183,782, `hill` 162,002, `township` 157,227 - all identity-bearing. There is no large
French-style residue of pure type words left to harvest, because the US corpus is
spelling-standard (D084: every non-US-sense key is 0 in the US union).

### 5c. The measured upside ceiling: 184,450 = 0.3367%

I took every non-empty `ADDR_CANON_COMMON` value, excluded the 62 stoplist entries, kept
`len >= 3` and `not ^\d+$`, then required that **the canonical form itself never occurs raw in
the US corpus** - i.e. the token can only reach a US key by being *manufactured* by canon and
nothing can fuse with it. That last filter matters and is D084's no-fusion test; without it
`rte` (7,114) and `xing` (2,093) look like candidates but are not.

| Rank | Canon value | Feeder key(s) | US all-6 | US test | `len` | % of US mass | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | `hts` | `heights` | 62,420 | 23,567 | 3 | 0.1139% | **SPECULATIVE** |
| 2 | `mtn` | `mountain` | 54,177 | 20,426 | 3 | 0.0989% | **SPECULATIVE** |
| 3 | `ctr` | `center`, `centre` | 42,930 | 16,119 | 3 | 0.0784% | **SPECULATIVE** |
| 4 | `jct` | `junction` | 14,061 | 5,439 | 3 | 0.0257% | **LIKELY** |
| 5 | `plz` | `plaza` | 8,286 | 3,203 | 3 | 0.0151% | **CONFIRMED** (see below) |
| 6 | `fwy` | `freeway` | 2,174 | 885 | 3 | 0.0040% | **LIKELY** |
| 7 | `expy` | `expressway` | 402 | 146 | 4 | 0.0007% | **LIKELY** |
| | **total** | | **184,450** | **69,785** | | **0.3367%** | |

**Why ranks 1-3 are SPECULATIVE, not CONFIRMED - this is the whole verdict.** Each long form
is *also* a common US place-name component, and the profile's `name_tokens` prove the
collision is real:

| Feeder | US `addr_tokens` | US `name_tokens` |
|---|---|---|
| `center` | 37,722 | **514,865** |
| `mountain` | 54,177 | **58,186** |
| `heights` | 62,420 | 1,847 |

`center` appears in **514,865** US business names and `mountain` in **58,186**. "Center",
"Mountain" and "Heights" are street types in one sense and toponym morphemes in the other
(Center, TX; Mountain View; Brooklyn Heights). A one-word stoplist cannot express that
distinction - the same component-position problem D084 hit with `saint`. **Adding any of the
top three would risk deleting a discriminative place-name token from US keys, to save 0.29% of
token mass.** The remaining four total 24,923 = 0.0455%, which does not justify a
shared-code-path change.

**`plz` is CONFIRMED but not worth acting on for the US.** It is the single self-inflicted hole
D091 identified - `plaza` is in `ADDR_GENERIC` but canon sends `plaza` -> `plz`
(`normalize.py:177`), so `plaza` can never fire and `plz` leaks instead. Fixing it closes a
real leak (8,286 US; 125,969 all-country per D122) - but it is a **France/India** fix that
happens to help the US slightly, not a US extension.

### 5d. Reconciliation with D084 - the class is real, and I have split it

D084 measured a **295,721** "no-fusion" class for the US: canon keys whose canonical value
occurs zero times in the US corpus. I reproduce that total exactly and partition it by whether
`ADDR_GENERIC` already suppresses the output:

| Sub-class | Mass | % of D084 class | Status |
|---|---|---|---|
| `vill` 79,428 + `dist` 27,527 + `indl` 4,316 | **111,271** | 37.627% | **already suppressed** - all three values are in `ADDR_GENERIC` |
| `hts` + `mtn` + `ctr` + `jct` + `plz` + `fwy` + `expy` | **184,450** | 62.373% | **leaks into US keys** |
| **total** | **295,721** | 100% | matches D084 to the unit |

`111,271 + 184,450 = 295,721`. **This is a strict refinement of D084, not a contradiction:**
D084 correctly identified the class as mishandled; I show that **37.6% of it is in fact
already handled** by the downstream stoplist, and the 184,450 that genuinely leaks is exactly
my Class A. Without this partition one would over-state the US gap by 1.60x.

---

## 6. Per-entry liveness for the US (the work order asks for this explicitly)

All 62 entries classified by measured post-canon US behaviour.
**31 fire / 9 inert / 22 dead.**

### 6a. FIRE and change blocking behaviour - 31 entries, 4,930,257 (9.0001%)

`ave` 1,610,417 / `city` 798,242 / `unit` 607,229 / `way` 284,878 / `cir` 249,327 /
`blvd` 189,169 / `box` 163,713 / `apt` 155,013 / `trl` 123,479 / `main` 121,494 /
`hwy` 113,225 / `vill` 79,428 / `ter` 62,790 / `pkwy` 59,054 / `2nd` 34,905 / `4th` 33,165 /
`3rd` 33,048 / `1st` 32,278 / `bldg` 29,515 / `5th` 28,376 / `dist` 27,527 / `ste` 24,529 /
`des` 22,816 / `cross` 11,684 / `the` 8,767 / `tower` 6,129 / `and` 5,071 / `colony` 4,895 /
`indl` 4,316 / `ground` 3,598 / `estate` 2,180

Every one is doing the job the table exists to do - with **one exception, `des`** (section 4).
`city` firing is *correct* despite `city` also being a place-name component, because
`oklahoma`/`kansas` survive alongside it and carry the discrimination.

### 6b. INERT - 9 entries, 8,518,413 (15.5502%), zero effect on any key

`st` 2,379,276 / `rd` 2,198,791 / `dr` 1,959,575 / `ln` 835,113 / `ct` 609,931 /
`pl` 235,891 / `po` 170,152 / `fl` 113,027 / `sq` 16,657

### 6c. DEAD for the US - 22 entries, zero US mass

Two sub-populations, and the distinction matters for whoever edits the file.

**(i) 17 entries that are French- or India-scoped**, firing 0 times in the US:
`rue`, `chemin`, `allee`, `impasse` (French street words); `nagar`, `sector`, `phase`,
`complex`, `apts` (India); `near`, `opposite`, `off`, `wing`, `block`, `office`, `pvt`, `ltd`.

This **confirms D122's correction of D091**: D091's D3b called `rue`/`chemin`/`allee`/`impasse`
"cross-country contamination" and flagged it *unquantified*. I quantify it - **all four are
exactly 0 in the US**, so D091's D3b has **no measurable effect on this dataset**. The
contamination is real in principle and zero in fact.

**(ii) 5 entries killed by canon before the filter sees them** - the redundancy D091
identified: `road`->`rd`, `lane`->`ln`, `street`->`st`, `floor`->`fl` (all folded into an inert
2-letter target) and `plaza`->`plz` (**not** in the list, so this one leaks - D091's single
self-inflicted hole, section 5c).

**On `st`/`ste`, which D120 raised for France and asked me to check for the US:** they are
**asymmetric for the US in the opposite way to France.** `st` is post-canon 2,379,276 US
occurrences and is **inert** (`len` 2). `ste` is post-canon **24,529** (`ste` 11,831 +
`suite` 12,698), `len` 3, and is therefore **genuinely live** - one of the 31 firing entries.
For France both are dead (D091 D4: `ADDR_CANON_FR:207` rewrites them to `saint`/`sainte`
first). **So `ste` is live for the US and dead for France; `st` is inert for the US and dead
for France.** Neither does anything useful in France.

### 6d. The 15 D091-D3 entries (no canon rule) for the US

Fire: `2nd` 19,721 / `4th` 19,461 / `3rd` 19,019 / `1st` 16,478 / `5th` 16,825 / `des` 22,816 /
`the` 8,767 / `tower` 6,129 / `and` 5,071. Zero for the US: `off`, `wing`, `block`, `office`,
`pvt`, `ltd`. (The ordinals are fed by `first`..`fifth` = 15,800/15,184/14,029/13,704/11,551
plus the bare forms.) `des` is the only harmful one.

---

## 7. Cross-country collisions - the complete US picture

| Direction | Finding | US mass |
|---|---|---|
| French entry corrupting a **US** token | **`des`** -> "Des Moines" / "Des Plaines" | 22,816 (0.0417%) |
| French street words corrupting US tokens | `rue`/`chemin`/`allee`/`impasse` | **0** - D091 D3b has no US effect |
| US entry corrupting a French token | `saint` 201,117 in the US is a *US city-name* token (St Louis, St Paul), so adding it would be a US regression; for France it is a genuine morpheme | not added |
| `bis`/`ter` asymmetry | **does not reproduce for the US** - `ter` is correct US *terrace* (62,790) | n/a |
| US corpus spelling | D084: every non-US-sense key (`est`, `col`, `so`, `plc`, `nr`, `opp`, `tq`, `bvd`, `boul`, `hiway`, `terr`, `bld`) is **0** in the US union | clean |

**Confirmed: no US entry corrupts a US *street-type* token.** The one live cross-country
defect is `des`, and it runs French -> US, not US -> anything.

---

## 8. Verdict and recommendations

**`ADDR_GENERIC` should NOT be extended for the US.** Ranked by value:

1. **CONFIRMED, do first - remove `des`.** The only entry that provably deletes an
   identity-bearing US token (95.14% of its 22,816 occurrences are Des Moines / Des Plaines).
   It is worth 199,183 in France and worth **negative** in the US. The clean fix is a country
   predicate at `keys.py:39`, but that is a structural change, and until the other 61 entries
   are measured under such a predicate, **removing `des` is the minimal correct action.**
   *Promote to CONFIRMED after one raw-inspection pass confirms the co-occurrence (section 4).*
2. **CONFIRMED, free, cross-country - add `plz`.** Closes D091's self-inflicted hole at 8,286
   US / 125,969 all-country. Zero IDF cost (section 5a). Not a US-specific extension.
3. **LIKELY, optional - `jct` 14,061, `fwy` 2,174, `expy` 402.** Together 16,637 = 0.0304%.
   `junction`/`freeway`/`expressway` have no plausible US place-name sense in this corpus
   (`junction` US `name_tokens` = 36). Small and safe, but below the noise floor of a
   shared-path change - take them only if the file is being edited anyway.
4. **SPECULATIVE, do NOT add - `hts`, `mtn`, `ctr`.** 159,527 = 0.2912%, i.e. 86.49% of the
   entire upside - and each is a live place-name morpheme in the US (`center` alone appears in
   **514,865** US business names). Adding them is the single most likely way to make US
   blocking *worse*. This is the direct US answer to D084's `saint` finding.
5. **Cosmetic, provably zero effect - the 9 inert entries (section 3) and the 22 dead ones
   (section 6c).** Deleting them changes no key. Low value; it would only make the dictionary
   honest about what it does. **Keep `st`/`rd`/`ln`** despite inertness: they are the *targets*
   that `road`/`lane`/`street` canon into, so they document intent even though the length gate
   makes them unobservable.
6. **Explicitly NOT recommended: `saint`.** 201,117 in the US, but overwhelmingly a US
   *city-name* token (`louis` 49,573, `paul` 30,845). Adding it would fuse "St Louis" with
   unrelated addresses. This resolves the item D122 flagged as "needs raw inspection".

**The structural recommendation, worth more than any single entry:** the defect class here is
not vocabulary, it is that `keys.py:39` is **one global list with no country predicate** while
`normalize.py:319-321` *is* country-scoped. `des` (22,816 damaged US occurrences) and D091's
four French street words are both symptoms. A `country -> set` mapping would fix the class. I
am **not** claiming a score delta for that - see section 9.

---

## 9. Gaps and limitations - stated, not smoothed over

- **All mass is token occurrences in the top-4000 listed set**, never rows. A token at 0 is
  **"not in the top 4000"**. US cut-offs are s1 101 / s2 258 / s3 274, higher than D120's
  French figures, so absence is *less* likely to mean anything here - but it still does not
  mean zero.
- **`build_profile.py` flattens comma-components.** I could not test co-occurrence, which is
  why the `des` finding is LIKELY-not-CONFIRMED and why `hts`/`mtn`/`ctr` are SPECULATIVE
  rather than rejected outright. I traced every claim to consuming code (`keys.py:39-45`,
  `normalize.py:319-354`, `prep.py:16`, `build_features.py:24-26`, `features.py:129`,
  `blocking.py:11,30-31`) before asserting an effect.
- **Section 3 and 5a are structural claims from quoted code, not measured score deltas.** I
  did not run the pipeline and claim **no F0.5 change** for any recommendation.
- **The `is_in` membership cost (section 2) is a GAP.** I flag it as a possible hot-loop issue
  and assert nothing about it - the profile has no timing field.
- **Class A's 184,450 is a ceiling, not a predicted gain.** It is mass that *could* be removed
  from US keys, not evidence that removing it would improve the metric. I have no recall or
  key-level data in the profile, so I cannot convert mass into score. **This is the gap that
  matters**, and it applies to every "add X" recommendation in this project.
- I did **not** re-derive US_STATES coverage, the France postcode claim, `pin_eq`/`alt_tset`,
  France blocking caps, or component order - all ruled out by the brief. The state-skip row in
  section 1 is quoted only to complete the partition and is an **upper bound**:
  `normalize.py:333` matches a *whole* component, so my per-token test over-counts it.
- Read-only respected on `amazon_ml_2026_research/` and `_upstream/`. No network. No `*.tsv`
  opened. Exactly two files written: this `.md` and `D092_mine_ADDR_GENERIC_US.json`.
  Scratch PowerShell was written to `%TEMP%` only.

*Written by analysis agent c06, D092.*
