# D079 — mine evidence to extend IN_STATES for US

## Headline

**`IN_STATES` needs no extension for US, because `IN_STATES` is never consulted for a US
row.** `STATE_MAPS` (normalize.py:250) is keyed strictly by country —
`{"US": US_STATES, "India": IN_STATES, "France": FR_REGIONS}` — and `normalize_address`
looks up `smap = STATE_MAPS.get(country, {})` (normalize.py:318). A row with
`country == "US"` therefore reads `US_STATES` and can never read an `IN_STATES` key. The
work order's premise is therefore void as literally stated, and the correct answer to
"what should IN_STATES contain for US" is **nothing**.

That said, mining surfaced a **genuine, previously unremarked latent defect**: `US_STATES`
and `IN_STATES` share **7 identical keys that mean different states**
(`ar ga la mn or tn ut`), and those 7 keys carry **976,874 US address-token occurrences =
81.47 per 1,000 US address rows** in this corpus. It is harmless today only because
state lookup is country-scoped — and, separately, only because an accidental `len > 3`
guard in `learn_translit.py:55` happens to filter every one of the 7 out. Either
safeguard removed, and 81 per 1,000 US rows silently mis-resolve. Separately, the `LEET`
table omits `2` and `9`, which mangles 3,657 US name-token occurrences.

## Findings

All counts aggregate the six profiles `train_s1..3`, `test_s1..3` from
`addr_tokens[country]` / `name_tokens[country]`. Row totals from `country_rows`:
US **11,990,643**, India **10,544,085**, France **1,694,445**, total **24,229,173**.

Two exact arithmetic invariants were checked on all six files and both hold everywhere
(they are my provenance check that the profile is internally consistent):

- `rows == sum(country_rows.values())` — 6/6 files.
- `by_country[c]["rows"] == sum(by_country[c]["len_hist"].values())` — 6/6 files x 3 countries.

### F1 — `IN_STATES` is structurally unreachable from US rows (CONFIRMED, code-only)

| fact | source | consequence |
|---|---|---|
| `STATE_MAPS = {"US": US_STATES, "India": IN_STATES, "France": FR_REGIONS}` | normalize.py:250 | one map per country, no fallback |
| `smap = STATE_MAPS.get(country, {})` | normalize.py:318 | a US row reads `US_STATES` only |
| `if ck in smap: state = smap[ck]` | normalize.py:333-334 | single lookup, country-locked |
| `prep.py` passes the row's own country `c` | prep.py:13 | country is per-row |

Consequence: **no edit to `IN_STATES` can change any feature value for any US row.**
Its only live consumer outside `normalize_address` is `learn_translit.py:51`
(`states = set(N.IN_STATES.keys())`) — see F3.

### F2 — 7 keys collide across `US_STATES` and `IN_STATES` (NEW, CONFIRMED)

Derived by intersecting the two dicts *after* the self-map loop at normalize.py:252-254
has run (each map's values are re-inserted as keys), giving `US_STATES` 104 keys and
`IN_STATES` 86 keys. The intersection has exactly 7 members, all two characters:

| key | `US_STATES` means | `IN_STATES` means | US addr occ | India addr occ | US rate /1k |
|---|---|---|---|---|---|
| `tn` | tennessee | tamilnadu | 313,504 | 226,332 | 26.146 |
| `mn` | minnesota | manipur | 163,335 | 3,750 | 13.622 |
| `or` | oregon | orissa (`"or": "od"`) | 157,903 | 0 | 13.169 |
| `ar` | arkansas | arunachal pradesh | 143,938 | 6,730 | 12.004 |
| `ut` | utah | uttarakhand (`"ut": "uk"`) | 120,670 | 0 | 10.064 |
| `la` | louisiana | ladakh | 61,346 | 4,473 | 5.116 |
| `ga` | georgia | goa | 16,178 | 4,030 | 1.349 |
| **total** | | | **976,874** | **248,315** | **81.47** |

Arithmetic: 313,504 + 163,335 + 157,903 + 143,938 + 120,670 + 61,346 + 16,178 =
**976,874**. Rate: 976,874 / 11,990,643 x 1000 = **81.47 per 1,000 US address rows**.

`or` and `ut` are the sharpest: India writes `0` occurrences of either, so a merged map
would corrupt **278,573 pure-US rows** (`157,903 + 120,670`) with no offsetting benefit.
`or` and `ut` are also the only two collisions where the India side is a *hand-written*
2-char key rather than a self-mapped code — they are deliberate India-specific
abbreviations, i.e. the most likely to have been added later and the least likely to have
been collision-checked.

**Status: LIKELY-defect (latent).** Confirmed as a property of the dictionaries; *not*
confirmed as a live bug, because F1 shows lookup is country-scoped. I am not claiming a
current scoring defect.


### F3 — The one live `IN_STATES` consumer is country-blind, and is saved by luck

`learn_translit.py:51` builds a state-name set with **no country filter**, and applies it
to the Source-1 address `a1` (learn_translit.py:55), which is a mixed-country file:

```python
states = set(N.IN_STATES.keys())          # line 51 - no country argument
st = [c.strip().lower() for c in a1.split(",")
      if c.strip().lower() in states and len(c.strip()) > 3]   # line 55
```

Two measured facts about this path:

1. **The `len(c.strip()) > 3` guard happens to neutralise all 7 collisions.** All 7
   collision keys are exactly 2 characters, so `len > 3` is False for every one.
   Verified: `all(len(c) <= 3 for c in collisions)` -> `True`. The guard is clearly
   intended to skip 2-letter codes, not to prevent a collision — it is coincidental
   protection.
2. **41 of 86 `IN_STATES` keys (47.7%) are permanently unusable by this path**, because
   they are <= 3 characters. These are the 35 self-mapped codes plus `goa`, `or`, `ts`,
   `ut`. So `IN_STATES` is 48% dead weight *for transliteration learning*, and in
   particular `goa` (a real, frequent state) can never be learned while `gujarat` can.

**Zero measured leak into US.** For all 45 `IN_STATES` keys with `len > 3` — the only
ones this path can match — the US address-token count is **0** for every single key.
The 15 that occur at all, with their India counts, are: `delhi` 2,621,031;
`maharashtra` 1,104,757; `karnataka` 410,672; `gujarat` 335,446; `telangana` 283,530;
`haryana` 218,443; `rajasthan` 188,237; `kerala` 181,552; `bihar` 141,819;
`punjab` 85,621; `keralam` 67,682; `orissa` 57,491; `odisha` 40,791;
`tamilnadu` 4,567; `chandigarh` 4,436. France is 0 for all of them too. So the
country-blind `IN_STATES` set costs nothing measurable on this dataset — the leak is
**0 occurrences**, a clean no-defect result for the path that actually uses it.

### F4 — `LEET` omits `2` and `9` (NEW, CONFIRMED)

`LEET` (normalize.py:256) maps `0 1 3 4 5 6 7 8 @ $` but **not `2` and not `9`**.
Measured on `name_tokens["US"]`, tokens that are mixed alpha-digit (the exact condition
`_name_tokens` requires before applying `LEET`, normalize.py:279):

- **133 distinct tokens, 90,100 total occurrences.**
- Of these, **3,657 occurrences (4.06%) contain an unmapped digit**, and they are
  **all one token: `24hr` (3,657, digits {2,4})**. `24hr` -> LEET maps `4`->`a` and leaves
  `2`, yielding the nonsense token `2ahr`, which matches nothing.
- The other 86,443 occurrences (95.94%) use only mapped digits and are handled correctly:
  `c0m` 2,855; `5ervices` 2,707; `ass0ciates` 1,817; `denta1` 1,652; `hea1th` 1,576;
  `fami1y` 1,395; `0f` 1,345; `6roup` 1,179; `l1c` 1,119; `c1inic` 1,042; `c0rp` 1,022.

The rest of the leet corpus is clean and confirms `LEET` is doing real work: `visi0n` 945,
`r0cky` 859, `chir0practic` 853, `m0untain` 850, `harb0r` 803, `n0se` 793, `8lue` 758.

### F5 — Dead and mis-scoped entries, with US evidence

| entry | dict | US addr occ | note |
|---|---|---|---|
| `puerto rico` -> `pr` | `US_STATES` | `puerto` **0**, `rico` **0** | no evidence in any file; absent from India/France too |
| `calle` | not in `ADDR_CANON_COMMON` | **2,821** | Spanish street word, unhandled (see Rec 4) |
| `county` | not in `ADDR_CANON`, not a state | **281,125** | largest unhandled US address token found |
| `district` | in `ADDR_CANON_COMMON` -> `dist` | 27,527 | already handled; correctly not a state |
| `borough` | not in `ADDR_CANON` | 17,520 | Alaska-specific; low value |
| `canton` | not in `ADDR_CANON` | 18,546 | also French/Chinese; country-ambiguous |

**No Puerto Rico evidence exists in this dataset at all** — `puerto` 0, `rico` 0,
`estado` 0, `carretera` 0, `barrio` 0, `condominio` 0, `municipio` 0, `zona` 0,
`urb` 0 across all six files and all three countries. `"puerto rico": "pr"` in

### F6 — No IN/US abbreviation pair is supported by the data (no-defect result)

I searched for the pattern the work order asks for — short token and long token both
frequent, one plausibly an abbreviation of the other. Across the plausible US set
(`de/del`, `penn/pennsylvania`, `mass`, `conn`, `wash`, `ariz`, `colo`, `mich`, `minn`,
`wisc`, `fla`, `ill`, `kans`, `nebr`, `okla`, `oreg`, `penna`, `calif`, `cali`, `bama`,
`wyo`), **every abbreviation has a US address count of exactly 0** except `del` (10,711)
and `penn` (3,084). The full names are all present and substantial: `delaware` 41,742,
`pennsylvania` 47,713, `massachusetts` 206,116, `connecticut` 68,304,
`washington` 267,075, `arizona` 206,484, `colorado` 19,189, `michigan` 7,822,
`minnesota` 112,763, `wisconsin` 118,034, `florida` 5,791, `illinois` 273,325,
`kansas` 97,056, `nebraska` 21,040, `oklahoma` 82,572, `oregon` 115,199,
`california` 139,681, `alabama` 118,811, `wyoming` 13,043.

This independently corroborates D075's `del`/`penn` finding from a different direction and
adds that **no third abbreviation is worth adding**. Also confirmed: no `IN_STATES` vs
`US_STATES` long-name pair co-occurs — there is no cross-country state-name aliasing
visible in the corpus at all.

### F7 — A `jammu & kashmir` key is unreachable, but harmlessly so

`IN_STATES` has both `"jammu and kashmir": "jk"` and `"jammu & kashmir": "jk"`. The
`&` variant is dead: `normalize_address` builds `ck` via
`re.sub(r"[^a-z0-9& ]+", " ", c).replace("&", " and ")` (normalize.py:331), so
`"jammu & kashmir"` arrives at the lookup as `"jammu and kashmir"`. Verified: the
transformed string **is** in `IN_STATES`. So the `&` key never matches, and the `and`
key absorbs it correctly. **No defect** — noted only so a future reader does not "fix"
it by deleting the `and` form.

## Interpretation

*Inference, clearly marked as such.*

1. **The highest-value output of this task is the negative result plus the latent
   collision.** Anyone reading "extend `IN_STATES` for US" would naturally start adding
   US state names to the India map. That edit would be **actively harmful**: it would
   create same-map key ambiguity the moment the maps are ever combined, and today it
   has literally zero upside (F1).
2. **F2 is a booby trap, not a bug.** 7 keys, 81.47 US occurrences per 1,000 rows, all
   currently inert. The realistic trigger is a well-intentioned refactor — "let's just
   merge the state maps" or "let's make state lookup country-agnostic and let the data
   sort it out". That refactor would break US rows on 7 of the most common codes
   (`tn` alone is 313,504 occurrences) while looking like an improvement.
3. **F3 shows the safety is accidental.** `len > 3` in `learn_translit.py:55` is the only
   thing standing between the 7 collisions and a live mis-learn, and it is there to skip
   2-letter codes. It also silently disables 48% of `IN_STATES` including `goa`.
4. **F4 is small and cosmetic.** 3,657 occurrences of `24hr` is 0.031% of US name-token
   occurrences. Fixing `2`->`z` in `LEET` would help, but the risk of over-triggering on
   real digits (`2` in `24hr`, `24/7`, `7up`) exceeds the 4% benefit. I would **not**
   prioritise this.
5. **F5's `county` (281,125) is the real prize in this neighbourhood**, but it belongs to
   `ADDR_CANON_COMMON`, not to any state table — it is out of scope for D079 and is
   flagged for D086-D089.

`US_STATES` is unexercised. `pr` is also one of the 7 codes D075 reported as having zero
evidence, which is consistent: this corpus contains no Puerto Rico rows.

## Gaps

Stated explicitly rather than estimated.

- **Multi-word keys are unmeasurable in this profile.** `build_profile.py:126-127` splits
  addresses on `[,;]` and then tokenises with `TOKEN_RE = [a-z0-9]+`, so
  `"andhra pradesh"` is recorded only as the separate tokens `andhra` and `pradesh`. I
  cannot confirm or refute the presence of any multi-word `IN_STATES` key as a *unit*
  from `addr_tokens` — only as its constituent words. Consequently the 30 zero-evidence
  multi-word keys in F3 (`uttar pradesh`, `tamil nadu`, `west bengal`, `jammu and
  kashmir`, `andaman and nicobar islands`, `dadra and nagar haveli`, `daman and diu`, ...)
  are **unmeasured, not absent**. Their constituent words do appear in India
  (`pradesh` 783,159; `uttar` 443,572; `bengal` 331,662; `tamil` 366,913;
  `nadu` 366,795), which is *circumstantial* support that the phrases exist — I am
  labelling that LIKELY, not CONFIRMED.
- **No component-position data.** The profile has no field recording which token sits in
  which comma-separated component, and no per-row address strings. So I cannot measure
  how often a given state token appears in the *state position* versus elsewhere in the
  address. All state rates above are raw token frequencies and may overstate how often
  the token functions as a state.
- **No bigram or co-occurrence field.** F6's abbreviation pairs rest on independent
  unigram counts, not on the two tokens ever appearing in the same address. Every pair in
  F6 is therefore LIKELY at best, and the 15 zero-count abbreviations are the real
  evidence (absence, not unobserved co-occurrence).
- **No per-row entity linkage.** I cannot tell whether a `tn` token in a US row and a
  `tn` token in an India row belong to businesses that might be cross-matched. The
  collision exposure in F2 is a token-count exposure, not a demonstrated scoring error.
- **Train/test leakage between sources is not visible.** Per-source numbers for the
  collision codes differ enormously (`or` is 0 in India, `ut` is 0 in India), but the
  profile gives no way to tell whether the US `or` rows and India `orissa` rows could ever
  be compared by the model.
- **LEET is not applied to addresses at all** — `_name_tokens` applies it (normalize.py:280)
  but `normalize_address` (normalize.py:342-349) does not. Mixed alpha-digit address
  tokens number 519,989 occurrences across 145 distinct tokens, dominated by ordinals
  (`2nd` 19,721, `4th` 19,461, `3rd` 19,019, `5th` 16,825, `1st` 16,478). That ordinal
  gap is already covered by D075 (396,959 uncanonicalised ordinals); I am not re-deriving
  it. What is *not* covered: whether any of those 145 address tokens would be wrongly
  leeted if `LEET` were extended to addresses. Unmeasured.

## Recommendations

Scoped and prioritised. The headline recommendation is a **do not change**, and I will
state it as such rather than manufacture work.

1. **DO NOT add US state names to `IN_STATES`. Zero upside, real downside.** `IN_STATES`
   is not read for US rows (F1). Any such edit enlarges the F2 collision surface for no
   benefit. This is the direct answer to the work order's question.

2. **PRIORITY 1 — add a regression test pinning the 7 collisions, without changing
   behaviour.** F2 is latent. A cheap guard is a test that asserts
   `set(US_STATES) & set(IN_STATES) == set()` after the self-map loop, or at minimum
   asserts the 7 known members explicitly so a future edit to either dict trips it. No
   scoring change, pure insurance. If a merge is ever genuinely wanted, the 7 keys must be
   namespaced (`"us:tn"`) or the maps kept separate — that is a design decision for a
   human, not something to smuggle in via a dictionary edit.

3. **PRIORITY 2 — give `learn_translit.py` a country filter and say why.** Line 51 builds
   the state set from `IN_STATES` with no country argument, and line 55 scans the
   mixed-country `a1`. Measured leak today is **0** (F3), so this is not urgent — but the
   filter should be added *and commented with the collision table above*, so the next
   person to touch it understands that removing the `len > 3` guard is not safe. Also
   worth deciding deliberately: `goa` is unreachable to transliteration learning while
   `gujarat` is reachable.

4. **PRIORITY 3 — add `calle` to `ADDR_CANON_COMMON` (LIKELY, low value).** 2,821 US
   address occurrences, 0 in India and France, so it is safely country-scoped. Small,
   cheap, no risk. Note the ordering: `calle` must **not** be added to `ADDR_CANON_FR`,
   where it is not a French street word.

5. **SKIP — do not extend `LEET` with `2`/`9` (SPECULATIVE, net-negative expected).** The
   entire measured benefit is 3,657 occurrences of the single token `24hr` (F4), and
   mapping `2`->`z` would corrupt legitimate numeric tokens (`24`, 25,681 occurrences;
   `2`, 277,980; `7`, 35,097; `21`, 29,108) in a corpus where 519,989 address-token
   occurrences are already numeric. The risk exceeds the 4.06% benefit.

6. **NOT IN SCOPE, flagged for the owning task — `county` (281,125 US occurrences) is the
   largest unhandled US address token in this neighbourhood.** It is a county/subdivision
   word, not a state, so it belongs to `ADDR_CANON_COMMON` (D086-D089), not to any state
   table. Recording it here so the number is not lost.

7. **NO CHANGE — `puerto rico`: `pr` stays.** Zero evidence in all six files and all three
   countries. It is harmless and plausibly useful for a future split; removing it would
   only add risk. Likewise **no change to `IN_STATES` content at all** on US evidence:
   all 45 usable keys measure exactly 0 US occurrences.

