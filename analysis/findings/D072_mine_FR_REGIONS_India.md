# D072 — mine evidence to extend FR_REGIONS for India

## Headline

`IN_STATES` — India's actual region/state table — needs **no extension**: every one of the 14
states and 4 union territories that actually appear in this dataset is already a key
(`normalize.py:230-242`). The real defect is one level down, in `ADDR_CANON_COMMON`: the
**drop family** (`value == ""`, i.e. "delete this structural token") is internally inconsistent.
`hno` is dropped but its far more common sibling **`hn` is not** — **146,010 occurrences**,
and the dictionary contains `h` and `hno` but not `hn`, so `"Hn 12, Model Town, Pune"` keeps a
spurious `hn` token while `"H.No 12, ..."` does not. That is a **NEW defect** found in this task
and confirmed by executing the real `normalize_address`.

**Scope correction.** The work-order title says "extend `FR_REGIONS` for India". `FR_REGIONS`
(`normalize.py:243`) is the **France** table; India's is `IN_STATES` (`normalize.py:230`), wired
in via `STATE_MAPS` at `normalize.py:250`. I audited `IN_STATES`, `ADDR_CANON_COMMON`,
`ADDR_CANON_FR`, `NAME_CANON` and `LEET` against the India slice. The `IN_STATES` half of the
question is answerable and the answer is "no change"; the dictionary half is where the evidence is.

## Findings

All counts are **sums of `addr_tokens["India"]` over the six profile files**
(`train_s1..3`, `test_s1..3`). Denominator: **`by_country["India"].rows` summed = 10,544,085**
(`country_rows["India"]`, identical in all six files). Dictionary membership was established by
`ast.literal_eval` on the module-level assignments in `_upstream/src/normalize.py`, and confirmed
by importing the real module with a stubbed `polars` and calling `normalize_address` directly.

### F1 — `hn` is unhandled while `hno` is deleted (CONFIRMED — new defect, highest priority)

`ADDR_CANON_COMMON` maps these fifteen keys to `""` (delete the token):

```
door, flat, h, hno, house, na, nil, no, none, nos, null, num, number, plot, shop
```

`hn` is **not** among them. Measured, `addr_tokens["India"]`:

| token | occurrences | per 1k India rows | in `ADDR_CANON_COMMON` | effect |
|---|---|---|---|---|
| `hno` | 19,527 | 1.852 | yes → `""` | deleted |
| **`hn`** | **146,010** | **13.848** | **no** | **kept as a token** |
| `house` | 372,704 | 35.345 | yes → `""` | deleted |
| `h` | — | — | yes → `""` | deleted |

Arithmetic: `146,010 / 10,544,085 × 1000 = 13.848` per 1,000 India rows.
`146,010 / 19,527 = 7.48` — **`hn` is 7.5× more frequent than the spelling the table handles.**

Per file (`addr_tokens["India"]`): `hn` = tr_s1 502, tr_s2 35,024, tr_s3 34,004,
te_s1 446, te_s2 38,111, te_s3 37,923 — present in **6 of 6** files.

**Live confirmation** against the real function (`normalize_address(..., "India")`):

```
'Hn 12, Model Town, Pune, Maharashtra'    -> toks=['hn','12','model','town','pune']  state='mh'
'H.No 12, Model Town, Pune, Maharashtra'  -> toks=['12','model','town','pune']        state='mh'
```

Identical meaning, different token stream. Two records for the same business cannot match on
address tokens. This is the mechanical definition of an entity-resolution miss.

Why CONFIRMED rather than LIKELY: the *frequency* and the *inconsistency* are both profile facts.
The gloss "`hn` means house number" is my own inference (**LIKELY**), but the defect does not
depend on it — any reader of the table sees `h`, `hno`, `house` handled and `hn` not.

Across the whole drop family the unhandled short forms are:

| short form | occurrences | long form (handled) | long count |
|---|---|---|---|
| **`hn`** | **146,010** | `hno` | 19,527 |
| `flt` | 9,038 | `flat` | 470,374 |
| `plt` | 7,276 | `plot` | 909,864 |
| `shp` | 1,033 | `shop` | 234,082 |
| **total** | **163,357** | | |

`hn` alone is **89.4%** of that total (`146,010 / 163,357`). The other three are real but an
order of magnitude smaller.


### F2 — `block`/`blk`: neither form is a key (CONFIRMED)

| form | occurrences | in `ADDR_CANON_COMMON` | in `ADDR_CANON_FR` |
|---|---|---|---|
| `block` | 511,622 | **no** | no |
| `blk` | 28,265 | **no** | no |
| sum | **539,887** | | |

Rate: `539,887 / 10,544,085 × 1000 = 51.20` per 1,000 India rows. Present in **6 of 6** files
(`block`: 39,081 / 109,932 / 95,008 / 35,657 / 125,323 / 106,621).

The argument that this is an *asymmetric omission* rather than policy: of the address-structure
noun families in the India vocabulary, 14 of 15 carry **both** the long and the short form as
keys — `street`/`st`, `road`/`rd`, `avenue`/`ave`, `lane`/`ln`, `drive`/`dr`, `sector`/`sec`,
`colony`/`col`, `nagar`/`ngr`, `village`/`vill`, `building`/`bldg`, `floor`/`fl`,
`apartment`/`apt`, `phase`/`ph`, `district`/`dist`, `taluk`/`tq`. `block`/`blk` is the sole
family where **neither** is present. CONFIRMED.

### F3 — `society`/`soc` is a second fully-unhandled family (CONFIRMED)

| form | occurrences | per 1k | in `ADDR_CANON_COMMON` |
|---|---|---|---|
| `society` | 115,572 | 10.961 | **no** |
| `soc` | 51,842 | 4.917 | **no** |
| sum | **167,414** | 15.878 | |

Same 6-of-6 presence. Note the near-synonym `chs` (**104,022**, per 1k 9.865) is also unhandled —
`chs` is a "co-operative housing society" abbreviation (**LIKELY**, my gloss). Together
`society`+`soc`+`chs` = **271,436** occurrences of housing-society vocabulary that no entry touches.

### F4 — `distt` is unhandled while `dist` is handled (CONFIRMED, low value)

`dist` = 56,836 (a key → `dist`); `distt` = 10,743 (not a key). `distt` is the common Indian
spelling of "district" (**LIKELY**). Same failure shape as F1 but far smaller; grouped with F2/F3
as a family-consistency issue rather than promoted on its own.

### F5 — `IN_STATES` needs no extension (CONFIRMED non-defect)

`IN_STATES` as written holds 49 entries over **37 distinct canonical codes**; after the
self-map loop at `normalize.py:252-254` (which **does** include `IN_STATES`) it has 86 keys.
Checked every state that actually occurs in the data:

| state | code | is a key? | token count(s) |
|---|---|---|---|
| maharashtra | mh | yes | 1,104,757 |
| delhi | dl | yes | 2,621,031 |
| uttar pradesh | up | yes | 443,572 + 783,159 |
| karnataka | ka | yes | 410,672 |
| tamil nadu | tn | yes | 366,913 + 366,795 |
| gujarat | gj | yes | 335,446 |
| telangana | tg | yes | 283,530 |
| haryana | hr | yes | 218,443 |
| rajasthan | rj | yes | 188,237 |
| kerala | kl | yes | 181,552 |
| bihar | br | yes | 141,819 |
| madhya pradesh | mp | yes | 130,403 + 783,159 |
| andhra pradesh | ap | yes | 215,298 + 783,159 |
| west bengal | wb | yes | 921,804 + 331,662 |
| punjab | pb | yes | 85,621 |
| odisha / orissa | od | yes (both) | 40,791 / 57,491 |

**All present states are already mapped.** Ten of the 37 codes — `cg`, `jh`, `jk`, `ld`, `ml`,
`mz`, `nl`, `py`, `tr`, `uk` — have **zero** occurrences in `addr_tokens["India"]`, and their
full names are absent too (`chhattisgarh` 0, `jharkhand` 0, `uttarakhand` 0, `assam` 0,

### F6 — `LEET` omits `2` and `9` (CONFIRMED code defect, negligible measured effect)

`normalize.py:256` defines `LEET` with ten pairs; the digit coverage is `0,1,3,4,5,6,7,8`.
**`2` and `9` are absent.** `_name_tokens` (`normalize.py:279-280`) applies `LEET` to any token
containing both a letter and a digit, so an untranslated `2`/`9` survives into the token stream.

Measured over `name_tokens`, all three countries:

| country | LEET-eligible tokens (alpha+digit) | occurrences | of which contain `2`/`9` | occurrences | % of eligible |
|---|---|---|---|---|---|
| India | 127 | 80,735 | 1 (`2nd`) | 253 | 0.313% |
| US | 133 | 90,100 | 1 (`24hr`) | 3,657 | 4.059% |
| France | 24 | 5,307 | **0** | **0** | 0.000% |

**This is a real code defect with essentially no measurable payoff.** The only affected tokens
are `2nd` (253, India) and `24hr` (3,657, US), neither of which any sensible `2→z` mapping would
change. Documented so it is not rediscovered as a "fix", and because France — the scored
country — has **exactly zero** affected tokens.

For contrast, `LEET` *is* doing real work: `5ervices`→`services` (5,407), `c0m`→`com` (2,873),
`8rothers`→`brothers` (2,386), `de1hi`→`delhi` (1,674) — all India `name_tokens`.

### F7 — `ADDR_CANON_COMMON` covers under a third of India address tokens (CONFIRMED context)

| quantity | value | source |
|---|---|---|
| India address token occurrences (top-4000 union, 6 files) | 97,463,176 | `addr_tokens["India"]` |
| …that are keys of `ADDR_CANON_COMMON` | 28,704,311 | same, intersected with the dict |
| **coverage** | **29.45%** | `28,704,311 / 97,463,176` |
| distinct India address tokens | 4,574 | same |
| …of which are keys | 126 | same |

This is context, **not** a defect claim: 70% of token occurrences are proper nouns (street,
colony, person and place names) that a structural dictionary should not touch. It is reported so
nobody reads a 29% figure as a quality score.

## Interpretation

*Clearly marked as inference; the measurements above are what the data shows.*

1. **F1 is the highest-value change in this report.** The pipeline is otherwise careful about
   deleting structural noise — it deletes `hno`, `h`, `house`, `no`, `num`, `plot`, `flat`,
   `shop` — but `hn` slips through at 146,010 occurrences. Because `hn` is a *constant* token
   appearing in many Indian addresses, it mostly adds a shared token rather than breaking every
   comparison, so the expected effect is **modest and positive rather than dramatic**: it mainly
   helps when one source writes `Hn 12` and the other writes `H.No 12`. Treat it as cheap and safe,

## Gaps

1. **The profile does not record per-component tokens — the single biggest limitation.**
   `build_profile.py:126-127` splits the address on `[,;]` and then updates a single flat
   `Counter`, so component identity is discarded. But `normalize_address:333` tests
   `if ck in smap` on a **whole component**, and the token loop at `342-349` runs per component.
   I can therefore report `hn` = 146,010 *tokens* but **cannot** report how many are the
   standalone component `"Hn 12"`. Every F1–F4 frequency is a token count, not a component count.
   This is why F1's frequency is strong while its match-rate effect is an estimate. Fix: add a
   field recording the token list of each comma-component.

2. **No field records the mapping actually applied.** Every "unhandled" claim here is
   established by evaluating the dictionary literal against the profile — sound and direct, but
   it is not an observation of pipeline output. I additionally executed the real
   `normalize_address` on 7 constructed India strings to confirm the mechanism (results in F1);
   that is a demonstration, not a corpus measurement.

3. **Semantic glosses are mine, not profile fields.** "`hn` = house number", "`soc`/`chs` =
   co-operative housing society", "`distt` = district", and the Hindi/Urdu words (`marg`, `gali`,
   `vihar`, `enclave`, `mohalla`, `peth`, `haveli`, `wadi`, `layout`, `kunj`) are my own knowledge,
   marked **LIKELY**. Confirming them needs row-level samples, which the RAM constraint forbids.
   The F1–F4 *defects* do not depend on these glosses.

4. **No n-gram or co-occurrence field exists.** I cannot tell whether `marg` and `road` ever
   co-occur in the same address, which is the condition under which folding `marg`→`rd` would
   merge anything. Any expected effect for the Hindi/Urdu vocabulary is therefore qualitative
   only, which is why I did not put it in the recommendations.

5. **The 253 `2nd` / 3,657 `24hr` occurrences cannot be classified** as leet versus legitimate
   from token bags alone. Hence F6 is CONFIRMED as a code fact but only LIKELY as a defect.

6. `build_profile.py` **prunes hapax tokens** (`prune()`, every 8 chunks, drops `count <= 1`) and
   keeps only the **top 4000** per country per file. So a token that exists but is rare, or falls
   outside the top 4000 in a given file, is invisible. Absence of a token from my tables is
   therefore *not* proof it never occurs. All my figures are lower bounds.

## Recommendations

1. **Add `"hn": ""` to `ADDR_CANON_COMMON`. CONFIRMED. Do this first.** One line, matches the
   table's own treatment of `h`/`hno`/`house`, and covers 146,010 occurrences — 89.4% of all
   unhandled drop-family short forms. Lowest-risk, highest-evidence change in this report.

2. **Add `flt`, `plt`, `shp` to the same drop family. CONFIRMED, low priority.** 9,038 + 7,276 +
   1,033 = 17,347 occurrences. Same one-line-per-entry shape as (1); bundle them.

3. **Add `block`/`blk` → a single canonical. CONFIRMED.** 539,887 occurrences, 6/6 files, and the
   only 1-of-15 break in the table's long/short convention. Suggested: `{"block": "block",
   "blk": "block"}`. Direction of the fold (long vs short) is a **SPECULATIVE** choice — the
   profile cannot tell you which spelling the *other* source uses more often.

4. **Add `soc`/`society`/`chs`. CONFIRMED frequency, LIKELY as a group.** 271,436 occurrences.
   Mapping all three to one canonical is defensible on frequency alone; the claim that they mean
   the same thing is **LIKELY**, not CONFIRMED.

5. **Add `distt` → `dist`. CONFIRMED frequency, LIKELY gloss.** 10,743 occurrences.

6. **Do NOT extend `IN_STATES`. CONFIRMED non-defect.** Every state present in the data is
   already a key; ten codes and their full names have zero occurrences. Adding them would be
   unmeasurable. Documented so a future reader does not "complete" the table speculatively.

7. **Do NOT extend `LEET` to addresses. CONFIRMED non-defect**, recorded so it is not "fixed":
   it would corrupt `2nd`, `1st`, `b3`, `1a`, `2b` — 2,042,847 alpha+digit India address tokens.

8. **Treat `LEET`'s missing `2`/`9` as a documentation item, not a fix. CONFIRMED, no action.**
   253 occurrences in India, 3,657 in the US, **0 in France**. Not worth a code change or an
   experiment.

9. **Open a profile-schema ticket for per-component tokens (Gap 1).** Highest-leverage non-code
   change available. Without it, the whole family of "does this token resolve as a state/region"
   questions — which is what `normalize_address:333` actually asks — stays unanswerable for all
   three countries, and any future `IN_STATES`/`FR_REGIONS` work remains guesswork.

10. **State the France caveat in the PR.** None of recommendations 1–5 touch a single French row
    (all affected tokens measure 0 in `addr_tokens["France"]`). Since France is the only scored
    country, present this work as India hygiene with an expected score effect of **zero**, not as
    a leaderboard improvement.

## Provenance

* **Read-only respected.** Read only `analysis_out/profile/{train,test}_s{1,2,3}.json` and
  `_upstream/src/normalize.py`. **No file under
  `amazon_ml_2026_research/student_resource/dataset/` was opened.** No network access.
* **`_upstream/` verified pristine after all work:** `git log -1` = `8445b7f1`, `git status
  --porcelain` empty. The module was imported with `python -B` and
  `PYTHONDONTWRITEBYTECODE=1` and a stubbed `polars`, so **no `.pyc` was written**.
* **Dictionary facts taken two independent ways**, in agreement: `ast.literal_eval` on the
  module source (dicts as written) and importing the real module (dicts after the line-252
  self-map mutation, which does include `IN_STATES`).
* **Field semantics pinned by reading `build_profile.py` first:** `num_digits` sums digits over
  the **address only** (line 114); `dig5`/`dig6` are lookaround-guarded (lines 29-30, 115-116) so
  a digit inside a longer run does not count; `addr_tokens` is built per comma/semicolon component
  but **flattened into one Counter** (lines 126-127); counts are pruned at `count <= 1` and
  truncated to the top 4000.
* **Files written: 2** — this document and `D072_mine_FR_REGIONS_India.json`.


7. I did not open any file under
   `amazon_ml_2026_research/student_resource/dataset/`. Only the six profile JSONs
   (575–865 KB each, parsed one at a time) and `_upstream/src/normalize.py` were read.

   not as a score-changing fix.

2. **F2 and F3 are the same class of fix at larger scale** (`block`/`blk` 539,887;
   `society`/`soc`/`chs` 271,436). Folding the short form onto the long form lets a
   `Block 4` record match a `Blk 4` record. Note the *reverse* asymmetry also disappears: today
   `Block 4` yields token `block` and `Blk 4` yields `blk`, which can never match.

3. **F6 should not be actioned as a performance fix.** 253 + 3,657 occurrences, zero in France.
   Adding `2`/`9` to `LEET` is defensible as correctness-by-construction, but it will not move a
   metric and it carries a small risk: `9` in an address-adjacent name could collide. Low priority.

4. **None of F1–F4 touch France.** Every affected token has a France count of **0**
   (`hn`, `blk`, `block`, `flt`, `plt`, `shp`, `soc`, `chs`, `distt`, `rm`, `room`, `marg`,
   `gali`, `mohalla`, `layout`, `enclave`, `vihar` all measured 0 in `addr_tokens["France"]`).
   France has 1,694,445 rows across the three test files and 4,441 distinct address tokens, and
   its effective canon (`normalize.py:320-321` = `ADDR_CANON_COMMON` minus `st,ste,dr,n,s,e,w`,
   overlaid with `ADDR_CANON_FR`, 219 keys) already covers French structure. **Since France is
   the only scored country, the honest expected score effect of every recommendation in this
   report is zero.** They are India hygiene, and should be labelled as such in any PR.

`tripura` 0). Those states simply do not appear in this dataset. Adding them would be
unmeasurable speculation. **Do not extend `IN_STATES`.**

This is consistent with `already_checked` REFUTED-2, which reached the same conclusion for
France: the region table is not the problem. My evidence does **not** contradict REFUTED-1 or
REFUTED-2, and I did not re-derive either.
