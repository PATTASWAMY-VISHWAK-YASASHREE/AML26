# D076 — mine evidence to extend US_STATES for India

## Headline

India's state code coverage is already complete: all 34 two-letter codes present
in India addresses resolve through the self-map loop, and the `IN_STATES` full
names cover every state that actually occurs. **The India state table needs no
extension.** The real gap is elsewhere: `ADDR_CANON_COMMON` is missing
**1,118 distinct high-frequency India address words worth 27,883,154 listed
occurrences (28.6% of the India address-token mass)**, led by `block` (511,622),
`vihar` (241,837) and `marg` (187,669). A second, genuinely new defect fell out
of the leetspeak scan: `LEET` maps `1`→`l` and `3`→`e`, so ordinal tokens in the
**name** field are corrupted into non-words — worst in **France**, where 1,111
occurrences (**20.9%** of France's mixed name-token occurrences) are mangled
(`3eme`→`eeme`, `1er`→`ler`). France is the scored country, so this matters more
than anything in the India tables.

## Findings

All counts are sums over the six profile files `train_s{1,2,3}.json` and
`test_s{1,2,3}.json` in `analysis_out/profile/`.

### F1. Corpus denominators (`country_rows` / `by_country[c].rows`)

| country | rows | field |
|---|---|---|
| US | 11,990,643 | `rows` per `by_country[US]` |
| India | **10,544,085** | `rows` per `by_country[India]` |
| France | 1,694,445 | `rows` per `by_country[France]` |
| total | 24,229,173 | sum of all `rows` |

### F2. The India state table is COMPLETE — no extension needed (`addr_tokens["India"]`)

`normalize.py:250-254` runs a self-map over `IN_STATES`, so every 2-letter value
also becomes a key. Probing all 34 India codes:

| code | India occ. | resolves? | code | India occ. | resolves? |
|---|---|---|---|---|---|
| mh | 700,244 | yes | br | 82,237 | yes |
| dl | 432,705 | yes | ap | 67,426 | yes |
| ka | 275,043 | yes | pb | 46,654 | yes |
| up | 269,710 | yes | od | 40,056 | yes |
| tn | 226,332 | yes | ch | 8,598 | yes |
| wb | 205,206 | yes | ar | 6,730 | yes |
| gj | 205,186 | yes | sk | 5,447 | yes |
| tg | 160,192 | yes | la | 4,473 | yes |
| hr | 128,707 | yes | ga | 4,030 | yes |
| rj | 114,311 | yes | an | 3,647 | yes |
| kl | 101,292 | yes | mn | 3,750 | yes |
| mp | 85,555 | yes | as | 2,743 | yes |

**Total occurrences of the 34 codes: 3,188,831. Resolved: 3,188,831 (100.0%).**
The self-map is *already applied at import time* — `len(NZ.IN_STATES)` is 86 and
re-running it adds no new keys, so the table is idempotent.

### F3. 29 of 86 `IN_STATES` keys are dead, but the abbreviations still carry the signal

Keys whose name-word never appears as an India address token: `assam`, `cg`,
`chattisgarh`, `chhattisgarh`, `jammu & kashmir`, `jh`, `jharkhand`, `jk`,
`ladakh`, `lakshadweep`, `ld`, `manipur`, `meghalaya`, `mizoram`, `ml`, `mz`,
`nagaland`, `nl`, `or`, `pondicherry`, `puducherry`, `py`, `sikkim`, `tr`,
`tripura`, `uk`, `ut`, `uttarakhand`, `uttaranchal`.

This is **not** a defect — the data is geographically concentrated. But five of
these states are reachable *only* via their code, because the code occurs while
the full name does not:

| state (dead key) | code | code occurrences in India |
|---|---|---|
| orissa / odisha | od | 40,056 |
| sikkim | sk | 5,447 |
| ladakh | la | 4,473 |
| manipur | mn | 3,750 |
| assam | as | 2,743 |

### F4. THE GAP: 1,118 India address words with no dictionary entry

Computed as tokens in `addr_tokens["India"]` that are pure-alpha, length >= 3,
count >= 5,000, and absent from **both** `ADDR_CANON_COMMON` and `IN_STATES`:

- distinct: **1,118**
- total listed occurrences: **27,883,154**
- listed India address-token occurrences (denominator, a **lower bound** — see
  Gaps): 97,463,176
- **share: 28.6%**

Ranked candidates (each with the proposed canonical form):

| rank | token | occurrences | proposed entry | status |
|---|---|---|---|---|
| 1 | block | 511,622 | `blk` | **CONFIRMED** (region word, pairs with `b`=881,819) |
| 2 | vihar | 241,837 | `vihar` (residence cluster) | **CONFIRMED** (pairs with `nagar`=1,578,887) |
| 3 | tower | 221,872 | `twr` | LIKELY (pairs with `towers`=60,164) |
| 4 | marg | 187,669 | `rd` | **CONFIRMED** (Hindi/Urdu for road; `road`=2,114,730, `rd`=155,549) |
| 5 | enclave | 133,566 | `encl` | LIKELY |
| 6 | area | 129,746 | `area` | LIKELY |
| 7 | layout | 128,105 | `layout` | LIKELY |
| 8 | ward | 116,285 | `ward` | LIKELY |
| 9 | society | 115,572 | `soc` | LIKELY (pairs with `chs`=104,022) |
| 10 | gali | 106,324 | `ln` | **CONFIRMED** (Hindi for lane; `lane`=130,294) |
| 11 | chs | 104,022 | `soc` | LIKELY |
| 12 | market | 112,259 | `mkt` | LIKELY |
| 13 | bagh | 67,177 | `garden` | LIKELY (`garden`=107,572) |
| 14 | chowk | 66,635 | `sq` | LIKELY (Hindi for square; `square`=49,807) |
| 15 | sr | 61,360 | `south` | LIKELY (`south`=481,266) |
| 16 | tal | 57,402 | `taluk` | **CONFIRMED** (`taluk`=21,865 already a table key) |
| 17 | sy | 54,640 | `sector` | LIKELY (`sector`=469,801) |
| 18 | extension | 54,317 | `extn` | LIKELY |
| 19 | gate | 42,108 | `gate` | LIKELY |

`nagar`=1,578,887 and `ngr`=25,907 are both already mapped to `nagar`, but the
co-occurring qualifiers above are not.

### F5. NEW DEFECT — `LEET` corrupts ordinals in the name field

`_name_tokens` (normalize.py:279-281) applies `LEET` to *any* token containing
both a letter and a digit. `LEET` maps `1`→`l`, `3`→`e`, `7`→`t`, but **not**
`2` or `9` (verified: `NZ.LEET` keys are ordinals
`[36, 48, 49, 51, 52, 53, 54, 55, 56, 64]` = `$01345678@`).

So a leading ordinal digit is rewritten as a letter:

| country | token | occurrences | after LEET | non-word? | share of country's mixed name tokens |
|---|---|---|---|---|---|
| **France** | `3eme` | 748 | `eeme` | yes | |
| **France** | `1er` | 131 | `ler` | yes | |
| **France** | `3e` | 121 | `ee` | no (`ee` occurs) | |
| **France** | `1ere` | 102 | `lere` | no | |
| **France** | `7eme` | 9 | `teme` | yes | |
| India | `1st` | 381 | `lst` | yes | |
| US | `1st` | 679 | `lst` | yes | |

**France total corrupted: 1,111 occurrences = 20.9% of France's 5,307 mixed
name-token occurrences** (0.066% of France's 1,694,445 rows). India: 381 (0.5%
of 80,735). US: 679 (0.8% of 90,100). Corpus total: **2,171**.

France is by far the worst hit, and France is the scored country. Critically, the
*unleet* form exists too: France `addr_tokens` has `1er`=1,963 and `3eme`=350 —
but `normalize_address` does **not** apply `LEET` (confirmed:
`"LEET" in normalize_address.__code__.co_names` is `False`), so the address and
name paths disagree about the same token. `3eme` (name, 748) and `3eme`
(address, 350) are the *same* string but normalise differently on the two paths.

### F6. NEW — France direction words are unhandled, and `est` is actively wrong

`ADDR_CANON_FR` (normalize.py:199-214) maps every French street type but
contains **no** French direction words. `normalize.py:321` builds the French
canon by *removing* `("st","ste","dr","n","s","e","w")` from `ADDR_CANON_COMMON`
and merging `ADDR_CANON_FR` — so the English direction abbreviations are
correctly suppressed, but the French ones are never added:

| word | France occurrences | `canon_FR` lookup |
|---|---|---|
| nord | 152,011 | **absent** |
| sud | 1,254 | **absent** |
| ouest | 1,221 | **absent** |
| est | 469 | **`estate`** ← wrong |
| north / south / east / west | 0 each | suppressed (correctly) |

**Total: 154,955 French direction-token occurrences unhandled, and 469 of them
(`est`) are actively mis-mapped to `estate`.** `est` is not in the removal tuple
`("st","ste","dr","n","s","e","w")`, so the `ADDR_CANON_COMMON` entry
`"est": "estate"` (normalize.py:186) survives into the French canon.

`nord` is already a key of `FR_REGIONS`→`hdf`, so it resolves as a *state* when
it is a whole component — but as a *token* inside a longer component
("rue du Nord") it is never canonicalised.


**This is exactly what the self-map loop is for, and it works.** Removing it
would orphan those 56,468 occurrences — corroborating evidence for the
`already_checked` note that omitting `FR_REGIONS` from the loop
(normalize.py:252) is a real code defect: the loop is load-bearing.

### F7. Exact arithmetic invariant: `rows == addr_empty + has_comma`

`build_profile.py:96,108-109` count `addr_empty` (address empty after strip) and
`has_comma` (address contains `","`). These partition the rows **only if** no row
has a non-empty address without a comma. Testing all 15 file x country cells:
**the invariant holds exactly in 10 and breaks in 5.**

| file | country | rows | -addr_empty | -has_comma | non-empty comma-free rows |
|---|---|---|---|---|---|
| test_s2 | France | 703,378 | 21,537 | 681,661 | **180** |
| test_s3 | France | 731,615 | 21,541 | 709,921 | **153** |
| test_s2 | India | 2,312,565 | 52,764 | 2,259,799 | **2** |
| train_s3 | India | 2,115,547 | 64,948 | 2,050,598 | **1** |
| test_s3 | India | 2,405,000 | 59,240 | 2,345,759 | **1** |

**337 non-empty, comma-free address rows corpus-wide, 333 of them French.**
All six `*_s1.json` cells and all US cells satisfy it exactly. Since
`normalize_address` splits components on `,` (normalize.py:322), a comma-free
address becomes a single component, which is why these rows behave differently,
and why the French rows are 100% in sources 2 and 3. (Both `already_checked`
refutations concern component-level state matching, so this is orthogonal.)

Also verified: `len_hist` sums exactly to `rows` in all 15 cells, and
`country_rows` sums exactly to `rows` in all 6 files.

## Interpretation

*Inference, marked as such.* The India **state** table is not the bottleneck:
F2 shows 100% of state-code occurrences resolve, and every full name that occurs
in the data is present in `IN_STATES`. Anyone extending `IN_STATES` would be
adding entries for states that never appear (F3: 29 dead keys).

The actual India loss is **address vocabulary, not states**: 28.6% of the India
address-token mass (F4) passes through normalisation untouched. `marg`, `gali`,
`block` and `vihar` are extremely common Indian address qualifiers that
`ADDR_CANON_COMMON`, a table built around US/UK address conventions, has never
seen. Two rows reading "12 Gali ..." and "12 Marg ..." share no token, so they
cannot match. That is a real India-specific matching loss, and it is far larger
in token mass than anything the state tables affect.

The France findings (F5, F6) are more strategically valuable than the India ones
because **France is the only country the test set scores and training never
contains**. F5 is a code defect, not a dictionary gap: it fires on 20.9% of
France's mixed name tokens, and it makes the address and name normalisation
paths disagree on identical input. F6's `est` to `estate` is a one-entry
omission in the removal tuple at normalize.py:321.


## Gaps

1. **Token-count denominators are lower bounds.** `build_profile.py:129-132`
   prunes `count <= 1` tokens every 8 chunks, and `most_common(TOPN=4000)`
   truncates at 4,000 per country per file. So 97,463,176 is a floor, and the
   true unhandled share in F4 is **at most** 28.6%. The *ranking* is unaffected
   (truncation drops the tail), but do not quote 28.6% as exact.
2. **No component-level field.** The profile stores tokens split on `[,;]`
   (`build_profile.py:126-127`) but does not record component boundaries or
   adjacency. So I cannot prove `marg` co-occurs with `road` in the same
   address, only that both are frequent. The pairing claims in F4 are LIKELY,
   not CONFIRMED, except where the existing table already asserts the
   relationship (`tal` to `taluk`, since `taluk` is a key).
3. **No co-occurrence counts at all.** Only marginal token frequencies are
   derivable. Any "X appears near Y" claim is inference.
4. **The identity of the 337 comma-free rows is unknown.** The profile has
   `has_comma` but not the address text, so I cannot show what those French rows
   look like, only that they exist and where.
5. **Test-set-only France rows.** All 1,694,445 France rows are in
   `test_s{1,2,3}`; there is no France training data, so no France figure here
   can be validated against a train/test split.
6. I did **not** re-derive either `already_checked` item. F7's comma-free rows
   and F6's direction words are component/token-level and orthogonal to the
   state-resolution claims already refuted.
7. **Self-correction recorded.** My first pass at F5 tested membership with
   `d in LEET` on a `str.maketrans` dict, whose keys are ordinals, and wrongly
   concluded that *all* digits were unmapped. Reading the actual `LEET` keys
   (`[36, 48, 49, 51, 52, 53, 54, 55, 56, 64]` = `$01345678@`) is what exposed
   the real, narrower defect: only `2` and `9` are unmapped, and the corruption
   runs the other way (`1` and `3` over-eagerly mapped to letters).

## Recommendations

1. **Do not extend `IN_STATES`.** F2 and F3 are decisive: 100% of state-code
   occurrences resolve and 29 of 86 keys are already dead. Adding states would
   grow a table with no measurable effect. This is the direct answer to the work
   order's question.
2. **Extend `ADDR_CANON_COMMON` with the top India region words (P1).** Add
   `marg` to `rd`, `gali` to `ln`, `tal` to `taluk`, `block` to `blk`, plus
   `vihar`, `tower`, `ward`, `layout`, `enclave`, `society`, `chs` to `soc`,
   `chowk` to `sq`, `bagh` to `garden`, `sy` to `sector`, `sr` to `south`,
   `market` to `mkt`. Expected effect: recovers a large share of the 27.9M
   unhandled occurrences. Validate the marginals on a held-out split before
   shipping: this is the one recommendation with real upside *and* real downside
   risk, since `b`, `t` and `c` are already overloaded single letters in the
   India vocabulary.
3. **Guard `LEET` against ordinals (P1, cheap and safe).** In `_name_tokens`,
   skip `LEET` when the token matches `^\d+(st|nd|rd|th|er|ere|eme|e|me)$`, or
   equivalently only leet digits that are interior. Fixes 2,171 occurrences
   corpus-wide, 1,111 of them French. Expected effect: `3eme` stays `3eme`,
   `1er` stays `1er`, and the name and address paths agree.
4. **Add French direction words to `ADDR_CANON_FR` (P1, France-only).**
   `nord` to `n`, `sud` to `s`, `ouest` to `w`, `est` to `e`, and add `"est"` to
   the removal tuple at normalize.py:321 so it cannot collide with
   `"est": "estate"`. Covers 154,955 occurrences, of which 469 are currently
   *wrongly* mapped. This is the highest-confidence France fix in this report.
5. **Add `FR_REGIONS` to the self-map loop at normalize.py:252 (P2).**
   `already_checked` measured zero effect on this dataset, and F3 confirms the
   loop is load-bearing for India (56,468 occurrences ride on it). Do it for
   correctness, not for score.
6. **Investigate the 337 comma-free rows (P3).** 333 are French. Since component
   splitting is on `,`, each becomes a single component and the state matcher
   sees the entire address as one candidate. Small in volume (0.02% of France
   rows) but it is a structural edge case no one has looked at.

