# D071 — mine evidence to extend FR_REGIONS for US

## Headline

**`US_STATES` needs no extension: zero new entries are justified by this data.** All 52
postal codes are already canonical, 38 of the 40 single-word state names written in the
table occur in the profile, and the only two that do not (`hawaii` 0, `mississippi` 0) are
absent because the dataset contains neither state. Mining instead turned up a defect
**one dictionary downstream and larger than the FR_REGIONS question**: the sub-national
civic designators `county, township, town, columbia, state, canton, borough, ward` are
handled by **no dictionary anywhere in `_upstream/src/`** — not `US_STATES`, not
`ADDR_CANON_COMMON`, not `keys.ADDR_GENERIC` — and they reach the blocking key `alph` list
**679,393 times = 1.240% of all 54,780,019 listed US address-token occurrences**. They are
raw function words with near-zero IDF, so they consume scarce `alph` slots (capped at 9
by `keys.py:22`) in the largest country in the corpus.

I also **refute two numbers in the earlier draft of this same file** (kept in
*Corrections*, below): its headline "534,803 French occurrences" overstates by including a
token (`les`) it never listed and, more importantly, its claim that 138,508 US occurrences
of 14 `ADDR_CANON_COMMON` outputs "reach the alph blocking list" is wrong by 57,874 —
**11 of those 14 outputs are shorter than 3 characters and are discarded by the
`str.len_chars() >= 3` filter at `keys.py:42` before they can ever occupy a slot.**

Every figure below is computed from `analysis_out/profile/{train,test}_s{1,2,3}.json` plus
the literal dictionaries in `_upstream/src/normalize.py` and `_upstream/src/keys.py`.
No raw TSV was opened. No network access. `_upstream/` verified pristine at `8445b7f`.

## Findings

### F0 — Arithmetic invariants: 66 checks, 0 failures

`build_profile.py` collects `by_country[c]` as independent totals, so several exact
identities must hold. All hold on 6 files x 3 countries:

| Identity | Field(s) | Result |
|---|---|---|
| `rows == sum(country_rows.values())` | `rows`, `country_rows` | 6/6 pass |
| `by_country[c].rows == country_rows[c]` | `rows`, `country_rows` | 18/18 pass |
| `sum(len_hist.values()) == by_country[c].rows` | `len_hist`, `rows` | 18/18 pass |
| `num_digits >= rows - addr_empty - alpha_only_addr` | `num_digits`, `addr_empty`, `alpha_only_addr` | 18/18 pass |
| `5*dig5 + 6*dig6 <= num_digits` | `dig5`, `dig6`, `num_digits` | 18/18 pass |

The fourth identity **defines a quantity the profile does not name**:
`rows - addr_empty - alpha_only_addr` = rows whose address contains at least one digit.
Measured: US source-1 is `1,323,632 / 1,323,633` (train) and `663,105 / 663,106` (test) —
exactly **one** digit-free US source-1 row per file. India and France are far from
saturation.

Denominator used throughout: `sum(addr_tokens["US"] counts)` over all 6 files =
**54,780,019** listed US address-token occurrences; France = **11,992,918**. Both are
**lower bounds** on true occurrences (see Gaps 1).

### F1 — `US_STATES`: measured, and there is no gap to close (negative result)

| Property | Value | How measured |
|---|---|---|
| Entries as written (`normalize.py:216-229`) | **52** | parse of the module source |
| Distinct canonical values | **52** | `len(set(values))` — one per state/DC/PR |
| Entries after the self-map loop (`:252-254`) | 104 | replicated as `setdefault(v, v)` |
| Single-word keys **as written** | **40** | no space in key |
| Multi-word keys | **12** | `district of columbia, new hampshire, new jersey, new mexico, new york, north carolina, north dakota, puerto rico, rhode island, south carolina, south dakota, west virginia` |
| Single-word names with count 0 | **2**: `hawaii`, `mississippi` | counted in `addr_tokens["US"]` |
| Two-letter alpha tokens in US address vocab | 78 | regex `^[a-z]{2}$` |
| — of which are postal codes | **45** | membership in `set(US_STATES.values())` |
| — of which are already canonical | **45 of 45** | no gap |

Full state names resolve at scale and already work: `texas` 480,985; `york` 384,608;
`virginia` 307,461; `ohio` 307,283; `illinois` 273,325; `washington` 267,075;
`carolina` 354,636; `new` 519,714.

**Conclusion: no new `US_STATES` entry is supported by this data.** The 2 zero-count names
are the *only* absent states, and both are genuinely absent from the corpus, so adding
them would be unevidenced. Note the post-self-map view is 92 single-word keys with 9 at
count 0 (`hawaii, mississippi` plus the 7 codes `hi, mi, ms, nv, nh, nj, pr` that only
exist after the `:252` loop); the table is already **wider** than this dataset needs.

Multi-word keys are **not testable from this profile** (see Gaps 2), but every constituent
token is present at volume (`new` 519,714, `york` 384,608, `carolina` 354,636,
`dakota` 33,508, `columbia` 58,751, `island` 48,250), so they are not at risk.

### F2 — NEW DEFECT: civic designators are handled by no dictionary at all

This is the largest unhandled mass I found, and it is absent from every table.

`normalize_address` (`normalize.py:341-350`) applies `canon.get(t, t)`; `canon` is
`ADDR_CANON_COMMON` for US. `keys.token_lists` (`keys.py:39-43`) then keeps a token if
`~is_in(ADDR_GENERIC)`, and promotes it to `alph` if it is not all-digits **and
`len_chars() >= 3`**, sorted by length descending, `head(9)`.

For a token to reach `alph` it must therefore be: not a `US_STATES` key, not a key of
`ADDR_CANON_COMMON`/`ADDR_CANON_FR`, not in `ADDR_GENERIC`, and `len >= 3`. Measured
against the US address vocabulary:

| Token | US occurrences | In `US_STATES`? | In `ADDR_CANON_COMMON`? | In `ADDR_GENERIC`? | Reaches `alph`? |
|---|---|---|---|---|---|
| `county` | **281,125** | no | no | no | **yes** |
| `township` | **157,227** | no | no | no | **yes** |
| `town` | **104,576** | no | no | no | **yes** |
| `columbia` | **58,751** | no | no | no | **yes** |
| `state` | **38,177** | no | no | no | **yes** |
| `canton` | **18,546** | no | no | no | **yes** |
| `borough` | **17,520** | no | no | no | **yes** |
| `ward` | **3,471** | no | no | no | **yes** |
| **TOTAL** | **679,393** | | | | **1.240% of 54,780,019** |

`parish` 0, `municipality` 0, `precinct` 0, `suburb` 0 — US only. The same scan on France
returns **`commune` 502 and nothing else**, so this defect is US-specific.

Arithmetic: `281,125 + 157,227 + 104,576 + 58,751 + 38,177 + 18,546 + 17,520 + 3,471 =
679,393`; `679,393 / 54,780,019 = 1.240%`.

**Interpretation (inference):** these are administrative-division designators, not street
names. `county` and `township` are constant within any given address component and carry
near-zero discriminative power, yet they are long enough (6-9 chars) to win `alph` slots
under the `sort_by(len, descending=True)` rule at `keys.py:43` — the same slots that would
otherwise hold the distinctive street name. This is the single highest-value US dictionary
addition found in this task.

### F3 — `ADDR_GENERIC` is out of sync with `ADDR_CANON`: the canon-output leak

`ADDR_GENERIC` (`keys.py:14-19`) has 62 entries. `ADDR_CANON_COMMON` has 80 distinct
outputs, `ADDR_CANON_FR` 29. A canon output leaks into `alph` iff `len >= 3`, not
all-digits, and absent from `ADDR_GENERIC`.

**US** (via `ADDR_CANON_COMMON`), 9 leaking outputs, mass **223,154 = 0.407%**:

| Output | Folds from | Mass |
|---|---|---|
| `hts` | `heights` 62,420 | 62,420 |
| `mtn` | `mountain` 54,177 | 54,177 |
| `ctr` | `center` 37,722 + `centre` 5,208 | 42,930 |
| `rte` | `route` 11,386 + `rte` 7,114 + `rt` 6,037 | 24,537 |
| `xing` | `crossing` 12,074 + `xing` 2,093 | 14,167 |
| `jct` | `junction` 14,061 | 14,061 |
| `plz` | `plaza` 8,286 | 8,286 |
| `fwy` | `freeway` 2,174 | 2,174 |
| `expy` | `expressway` 402 | 402 |

**France** (effective canon = `ADDR_CANON_COMMON` minus `{st,ste,dr,n,s,e,w}` per
`normalize.py:321`, then `** ADDR_CANON_FR`), 16 leaking outputs, mass **337,590 =
2.815%** — six times the US rate, in the only country the test set scores:

`saint` 166,818 (`saint` 141,364 + `st` 25,454) · `bis` 69,757 (`bis` 52,072 + `b` 17,685) ·
`rte` 29,927 · `crs` 13,281 · `res` 13,088 · `quai` 13,004 · `sainte` 8,077 · `gen` 6,078 ·
`mal` 4,730 · `bat` 3,745 · `fbg` 3,046 · `prof` 2,485 · `pres` 2,380 · `ctr` 967 ·
`lieu` 181 · `zone` 26.

The `st -> saint` path deserves emphasis: `normalize.py:321` **excludes `st` from the
`""`-suppression set for France**, and `ADDR_CANON_FR:207` then maps `st -> saint`
(5 chars). So the token `st`, which carries no French street information, becomes `saint`
and *does* reach `alph`. Measured: `st` occurs 25,454 times in French addresses.

The France rate is **2.815% vs 0.407% for the US** — French addresses are proportionally
far noisier in the blocking key.

### F4 — Ordinals: `ADDR_GENERIC` covers only `1st`-`5th`

`ADDR_CANON_COMMON:184` maps `first..fifth` to `1st..5th`; `ADDR_GENERIC:18-19` lists
exactly those five literals. Tokens matching `^\d{1,3}(st|nd|rd|th)$`:

| | distinct tokens | occurrences | of which **not** in `ADDR_GENERIC` |
|---|---|---|---|
| US | 137 | 511,112 | **132 tokens, 419,608 occ** |
| France | **0** | **0** | **0** |

`419,608 / 54,780,019 = 0.766%` of listed US address-token occurrences. Top offenders are
all `6th`+: `6th` 14,645, `7th` 13,907, `8th` 12,129, `9th` 11,051, `16th` 10,722,
`10th` 10,460, `12th` 9,299, `11th` 9,185, `17th` 8,833. France has **zero** ordinals, so
this fix is US-only and does not help the scored country.

### F5 — Leetspeak: applied on the name side only

`LEET` (`normalize.py:256`) is a genuine ordinal-keyed `str.maketrans`
(`0->o, 1->l, 3->e, 4->a, 5->s, 6->g, 7->t, 8->b, @->a, $->s`) and is applied in
`_name_tokens` (`normalize.py:279-280`) **only** when a token has both an alpha and a
digit character. `normalize_address` contains **no `translate` call** — verified by
reading `normalize.py:314-353` — so the address channel never de-leets.

| Country | name: mixed alpha+digit tokens | occurrences | % of listed name tokens | addr: mixed tokens (LEET never applied) |
|---|---|---|---|---|
| US | 133 | 90,100 | 0.2495% of 36,110,533 | 145 tokens, 519,989 occ |
| India | 127 | 80,735 | 0.2769% of 29,151,826 | 160 tokens, 2,087,204 occ |
| France | **24** | **5,307** | **0.1019% of 5,210,495** | 46 tokens, 13,580 occ |

Leetspeak is **not a French problem** (0.10% of French name tokens vs 0.25% US).

Two measured failure shapes:

1. **Unmapped digits `2` and `9`.** Outputs still containing a digit: US `24hr -> 2ahr`
   **3,657 occurrences**; India `2nd` 253. Every other mapped digit resolves cleanly
   (`c0m -> com` 2,855; `5ervices -> services` 2,707; `6lobal/gl0bal/g1obal -> global`
   2,027; `denta1 -> dental` 1,652).
2. **Phantom tokens** — LEET produces a clean word that occurs **0 times** in the same
   country's raw name vocabulary: US `1st -> lst` 679; India `1st -> lst` 381; France
   `3eme -> eeme` 748, `1er -> ler` 131, `7eme -> teme` 9 (**888 total**).
   France's `1er` is the French *premier* and `3eme`/`7eme` are the French ordinal
   suffixes, so LEET actively corrupts correct French input.

**Digits inside otherwise-alphabetic words are the actual leetspeak signal in the address
channel** (519,989 US occurrences), and that channel is where LEET is *not* applied.

### F6 — Abbreviation-table evidence: every state abbreviation is already handled

Mining `(short, long)` pairs where `short` is a strict prefix of a known dictionary

### F7 — Four token collisions between `ADDR_CANON_COMMON` outputs and `US_STATES`

| Token | Canonical in both | Raw US occurrences | France |
|---|---|---|---|
| `ct` | `court -> ct` and `connecticut -> ct` | 324,465 | 0 |
| `fl` | `floor -> fl` and `florida -> fl` | 89,108 | 0 |
| `mt` | `mount -> mt` and `montana -> mt` | 74,552 | 0 |
| `ne` | `northeast -> ne` and `nebraska -> ne` | 33,301 | 6,465 |

Total **521,426** raw US occurrences. This is a design collision, not a bug:
`normalize_address` checks `ck in smap` on the whole comma-component (`normalize.py:333`)
*before* tokenising, so a component `"CT"` resolves to Connecticut and a component
`"12 Court Ct"` tokenises `court -> ct` normally. The two paths do not meet.
**No change recommended**; recorded so the next reviewer does not "fix" it.

### F8 — 15 of 62 `ADDR_GENERIC` entries are dead

Entries that are not the output of any canon map: `and, block, des, floor, lane, ltd, off,
office, plaza, pvt, road, street, the, tower, wing`. All 15 are `ADDR_CANON_COMMON`
**keys** whose value is different (`street -> st`, `road -> rd`, `lane -> ln`,
`floor -> fl`, `plaza -> plz`), or pure noise words that never appear as canon outputs.
They are harmless: `canon.get(t, t)` is the identity for a token not in the map, so
`street` still cannot appear in `atoks` (it becomes `st`), and words like `and`/`the` are
simply never produced. **No change recommended.**

### Corrections to the earlier draft of this file

Two numbers in the previous version of this deliverable do not reproduce, and I am
withdrawing them rather than carrying them forward:

1. **"241,653 occurrences of the 11 counted French boilerplate tokens."** The 11 listed
   tokens sum to **237,968**. The 3,685 discrepancy is **exactly** the count of `les`, a
   12th token that was added to the sum but never listed. Corrected figure: **237,968**.
2. **"138,508 measured occurrences reach the alph blocking list" for 14
   `ADDR_CANON_COMMON` outputs (`mt, ne, ft, rte, pt, xing, ctr, n, s, e, w, sw, nw, se`).**
   Only **`rte`, `xing`, `ctr`** survive the `len_chars() >= 3` filter at `keys.py:42`.
   The other **11** (`mt, ne, ft, pt, n, s, e, w, sw, nw, se`) are 1-2 characters and are
   discarded *before* the `alph` `head(9)`, so they never occupy a slot. The true
   alph-reaching mass for those three is **24,537 + 14,167 + 42,930 = 81,634**, not
   138,508 — an overstatement of 57,874.

The earlier draft's ordinal figure (**419,608**, 132 distinct tokens) **does** reproduce
exactly, as do its 54,780,019 denominator and its 2-of-40-vs-9-of-92 `US_STATES` framing.

## Interpretation

*Inference, clearly marked as such — I cannot measure any downstream leaderboard effect
from the profile.*

1. **The FR_REGIONS question, applied to the US, is a dead end.** `US_STATES` is already

## Gaps

1. **Token counts are lower bounds.** `build_profile.py:127-141` splits on `[,;]`, applies
   `TOKEN_RE = [a-z0-9]+`, and keeps only `most_common(4000)` per country per file, after
   pruning hapaxes every 8 chunks (`:45-48,128-133`). Any token outside the top 4,000 in a
   given file is invisible. This is why `hts`, `mtn`, `ctr`, `jct`, `plz`, `fwy`, `expy`
   all show **raw count 0** in the US vocabulary while their *canon outputs* are huge:
   `heights` 62,420 and `mountain` 54,177 are present, `hts`/`mtn` are not. I report the
   canon-output mass because that is what actually reaches `alph`, but the 0-count entries
   are real absences from the profile, not absences from the data.
2. **Multi-word state keys are untestable here.** `build_profile.py` discards the comma
   component structure (it flattens via `at.update(TOKEN_RE.findall(comp))` at `:126-127`).
   So I cannot measure whether `"New York"` appears as a contiguous component and therefore
   cannot compute a state-resolution rate for the US, for France, or for India. This is the
   same structural gap that blocks the D070 follow-ups. It is a **profile** limitation, not
   a claim about the pipeline.
3. **The `alph` `head(9)` effect is unquantified.** I can measure how many occurrences
   *are eligible*, but not how many rows actually lose a distinctive token to a generic
   one, because that needs the per-row token order. Treat 679,393 as an eligibility count,
   not a damage count.
4. **`has_digit_name` is a row count, not a histogram**, so leetspeak volume could not be
   cross-checked against it numerically.
5. **France has 0 rows in all three train files**, so no French figure can be validated on
   held-out French data.
6. **Token identity within a row is unknown.** `county` 281,125 occurrences do not tell me
   how many distinct rows contain it; a row with `"County Road 12"` contributes 2.

## Recommendations

Priority order. The "expected effect" column is a reasoned inference; the occurrence
figures are measurements.

1. **P1 — add the civic designators to `keys.ADDR_GENERIC`:**
   `county, township, town, columbia, state, canton, borough, ward`.
   **679,393 US occurrences = 1.240% of listed US address-token mass** — the largest single
   unhandled mass found in this task, and handled by no dictionary today.
   `CONFIRMED` for every count and for the absence from all three tables; `LIKELY` that
   all eight are non-identifying in a blocking key (a district name adjacent to the street
   name is the identifying part, not the designator word). Expected effect: frees `alph`
   slots that currently go to length-sorted boilerplate.
2. **P2 — add the 15 leaking French outputs to `keys.ADDR_GENERIC`:**
   `saint, sainte, bis, rte, crs, res, quai, gen, mal, bat, fbg, prof, pres, ctr, lieu, zone`.
   **337,590 French occurrences = 2.815% of the 11,992,918 listed French address tokens**,
   in the only country the test set scores. `saint` alone is 166,818. `CONFIRMED` counts
   and `CONFIRMED` absence from `ADDR_GENERIC`; `LIKELY` that they are non-identifying
   (`saint` is the French near-equivalent of "St", which the US list *does* suppress as
   `st`). This is the highest-value change for the actual score.
3. **P3 — add the 9 leaking US outputs to `keys.ADDR_GENERIC`:**
   `hts, mtn, ctr, rte, xing, jct, plz, fwy, expy`. **223,154 = 0.407%.** `CONFIRMED`.
   Note `hts` (62,420) and `mtn` (54,177) are the two largest and are entirely absent
   from the raw vocabulary (Gaps 1), so enumerating canon outputs — not raw tokens — is
   the only way to find them.
4. **P4 — generalise the ordinal rule instead of enumerating.** `ADDR_GENERIC:18-19` lists
   `1st`-`5th`; the data has **132 distinct unsupported ordinal tokens worth 419,608 US
   occurrences**. Replacing the five literals with a `^\d{1,3}(st|nd|rd|th)$` membership
   test removes all of them in one change and is robust to tokens above the 4,000 cut.
   `CONFIRMED`. France has 0 ordinals, so this is US-only and will not move the French
   score.
5. **P5 — do NOT extend `US_STATES`, and do NOT add abbreviation entries.** F1 and F6
   measured no gap: 45 of 45 postal codes already canonical, 38 of 40 state names present,
   and every state abbreviation pair is already handled. Adding entries would be
   unevidenced. This is the explicit negative result of the task.
6. **P6 — exempt `LEET` from the two shapes it breaks** rather than extending the table:
   skip translation when the leading character has no mapping (`2`, `9`), and exempt the
   French ordinal suffixes. Measured tokens that currently become strings occurring **0**
   times in the corpus: `24hr -> 2ahr` 3,657 (US), `1st -> lst` 679 (US) + 381 (India),
   `3eme -> eeme` 748 + `1er -> ler` 131 + `7eme -> teme` 9 (France) = **5,606 occurrences**.
   `CONFIRMED` counts; the fix design is a judgement call. Lower priority than P1-P3
   because the name channel is a smaller share of the blocking key than the address
   channel.
7. **P7 — no change to the 15 dead `ADDR_GENERIC` entries (F8) or the four
   `ADDR_CANON`/`US_STATES` collisions (F7).** Both are harmless by construction; F7's
   two code paths never meet. Recorded to prevent a future "cleanup" from breaking them.
8. **P8 — add a component-level field to the next profile build**, alongside
   `build_profile.py:126-127`. It is the single missing measurement that blocks the
   state-resolution question for all three countries, and it is a one-line change.

   wider than the corpus requires. Effort spent extending it is wasted; effort spent
   making the *sub-national* layer (`county`, `township`, `town`) suppressible is not.
2. **The US defect is size, not coverage.** 679,393 occurrences of pure administrative
   boilerplate reach `alph`, versus 223,154 of un-suppressed street-type outputs. The
   bigger problem is not that `hts` is missing from `ADDR_GENERIC`; it is that nothing at
   all knows what `county` is.
3. **France is simultaneously the noisiest and the most fixable.** 2.815% leak rate vs
   0.407% for the US, and every affected token is in the *address* channel where the fix
   is a one-line `ADDR_GENERIC` addition rather than a normalisation change. France also
   has the smallest leetspeak contamination (0.10%), so the cheap fix is the whole fix
   there.
4. **`alph` is a length-sorted, capacity-9 slot** (`keys.py:22,43`), so long generic tokens
   are the most damaging. This is why `township` (9 chars) outranks `ward` (4) as a
   priority despite being 45x rarer.

concept, both frequent, excluding pairs that already agree under canon, returned 118 US
and 133 FR candidates. **All the state-relevant ones are false positives** — verified
individually:

| Pair | Occurrences | Already handled? |
|---|---|---|
| `oh ~ ohio` | 445,297 / 307,283 | **yes** — `oh` is a `US_STATES` key after the `:252` self-map |
| `il ~ illinois` | 396,078 / 273,325 | **yes** — same |
| `ma ~ maine/maryland/massachusetts` | 297,168 / 43,709-206,116 | **yes** — same |
| `in ~ indiana` | 260,594 / 181,306 | **yes** — same |
| `wa ~ washington` | 222,793 / 267,075 | **yes** — same |
| `ca ~ california` | 196,583 / 139,681 | **yes** — same |
| `wi ~ wisconsin` | 165,081 / 118,034 | **yes** — same |

`st ~ ste` (1,054,366 / 11,831) and `ct ~ ctr` (324,465 / 0) are **not** abbreviation
pairs: `st`->`st` (street) and `ste`->`ste` (suite) are distinct concepts, and `ctr`
(centre) never appears as a raw US token. `park ~ parkway` (183,782 / 34,378) is
`park -> parkway`, both real words, not an abbreviation. **No abbreviation entry is
justified by this data.**

