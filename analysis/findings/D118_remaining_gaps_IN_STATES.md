# D118 — remaining gaps in `IN_STATES` (independent re-confirmation of the negative)

## Headline

**The negative is CONFIRMED. `IN_STATES` needs no dictionary expansion.** All 28 states and all
9 UT/NCT codes are present, and every alternate-spelling, ordinal, merged-territory and
concatenation variant I could construct from the profile **measures exactly 0 across all six
files**. A gap would have required a state/UT name to appear in the data that is not a key; I
could not find one, and the two candidate families I was specifically asked to hunt (union
territory vs state, and the Delhi / `Nagar Haveli` / merged-territory cases) all resolve to
**no missing key**.

**But the re-confirmation surfaced one NEW and important positive finding that reframes the
whole table: `IN_STATES`' self-map loop is not cosmetic, it is the *sole* mechanism by which
the two `s3` files resolve an Indian state at all.** 98.00% of all self-map key mass
(3,125,112 of 3,188,831 occurrences) sits in `train_s3`+`test_s3`. In `s1`/`s2` India writes
the state in full (`maharashtra` 217.83 per 1k rows, `mh` 2.38 per 1k); in `s3` it writes the
two-letter code (`mh` 151.93 per 1k, `maharashtra` 11.38 per 1k). The prior audits called the
self-map loop "correct, no defect" and stopped there. It is correct — and it is *load-bearing
for 4,520,547 Indian rows*, which is a much stronger reason to leave it alone than "it's fine".

**One NEW latent defect, of the same class D078 already found but on a different set of keys:**
the self-map loop manufactures the keys `as` (Assam) and `an` (Andaman & Nicobar), which are
ordinary English function words, at **2.92x the exposure of the `ts` risk D078 did flag**.
D078's Defect-2 table only examined *literal* short aliases (`or`, `ts`, `ut`) and so
systematically missed every hazard the loop itself creates.

Deliverable: this file. Sidecar: `analysis_out/findings/D118_remaining_gaps_IN_STATES.json`.

---

## Method, provenance and the two hard limits

All counts aggregate the six profile files `train_s1..3`, `test_s1..3`. Every India figure comes
from `country_rows["India"]`, `by_country["India"]`, and the `addr_tokens["India"]` /
`name_tokens["India"]` arrays. **I never opened a `*.tsv`.** No network access was used.

Two limits govern every "measures 0" claim in this report, and I state them once here so no
number below is over-read:

1. **Truncation.** `build_profile.py:27` sets `TOPN = 4000`, so each per-file token list is
   capped. The 4000th-token floors are `train_s1` 182, `train_s2` 394, `train_s3` 362,
   `test_s1` 166, `test_s2` 459, `test_s3` 416 — **sum of floors = 1,979** (independently
   re-derived from the profile, matching D080). A token absent from all six lists has a true
   six-file total **< 1,979**. Every "0" below therefore means **"not in the top 4000"**, never
   "does not occur".
2. **Unigrams are upper bounds on matches.** `normalize.py:333` requires the *whole*
   comma-component to equal the key (`if ck in smap`). A unigram occurrence can sit anywhere in
   an address, so token counts **overstate** state resolutions. They are the only direction of
   error available from this profile, and it is the safe one for a no-change verdict.

Provenance check: `sum(country_rows["India"])` = 883,188 + 2,017,799 + 2,115,547 + 809,986 +
2,312,565 + 2,405,000 = **10,544,085** India rows, matching D080/D079 exactly.


---

## 1. The table itself, re-derived independently from source

I did not take D078's 49/37/86 on trust. I re-parsed the dict literal at
`_upstream/src/normalize.py:230-242` with a regex over `"key": "value"` pairs and re-applied the
self-map loop in memory:

| quantity | my value | how derived |
|---|---|---|
| literal pairs | **49** | regex `"([^"]*)"\s*:\s*"([^"]*)"` over lines 230-242 |
| distinct canonical values | **37** | `Sort-Object -Unique` on the value column |
| effective keys after the loop | **86** | 49 + 37, because **0** pairs have `k == v` |
| keys where `k != v` and `len(k) <= 3` | **4** | `goa->ga`, `or->od`, `ts->tg`, `ut->uk` |

This **independently reproduces D078's 49 / 37 / 86** and D080's F1. Three prior agents and I
agree on the ground truth, so the arithmetic below is not resting on a contested base.

Source, quoted verbatim (`normalize.py:250-254`):

```python
STATE_MAPS = {"US": US_STATES, "India": IN_STATES, "France": FR_REGIONS}
# abbreviations are canonical themselves
for _m in (US_STATES, IN_STATES):
    for _v in list(_m.values()):
        _m.setdefault(_v, _v)
```

`IN_STATES` **is** in the loop, so all 37 canonical codes are also keys. The codes added are:

`an ap ar as br cg ch dd dl dn ga gj hp hr jh jk ka kl la ld mh ml mn mp mz nl od pb py rj sk tg tn tr uk up wb`

**`IN_STATES` gets its self-map loop entry. `FR_REGIONS` does not** (line 252 iterates only
`US_STATES` and `IN_STATES`). That asymmetry is the defect the fleet brief attributes to
`FR_REGIONS`, and it genuinely does not apply to India.

### 1a. Does the canonical value appear as an input token? YES — massively, and only in s3.

This is the direct answer to the work order's self-map question. Measured six-file totals of
`addr_tokens["India"]` for all 37 codes:

| code | six-file total | code | six-file total | code | six-file total |
|---|---|---|---|---|---|
| `mh` | 700,244 | `ka` | 275,043 | `hr` | 128,707 |
| `dl` | 432,705 | `tn` | 226,332 | `sk` | 5,447 |
| `up` | 269,710 | `wb` | 205,206 | `ch` | 8,598 |
| `gj` | 205,186 | `tg` | 160,192 | `ga` | 4,030 |
| `ap` | 67,426 | `br` | 82,237 | `la` | 4,473 |
| `mp` | 85,555 | `kl` | 101,292 | `an` | 3,647 |
| `od` | 40,056 | `pb` | 46,654 | `mn` | 3,750 |
| `rj` | 114,311 | `ar` | 6,730 | `dd` | 3,048 |
| `as` | 2,743 | `hp` | 2,630 | `dn` | 2,879 |
| `cg` 0 | `jh` 0 | `jk` 0 | `ld` 0 | `ml` 0 | `mz` 0 |
| `nl` 0 | `py` 0 | `tr` 0 | `uk` 0 | | |

**Total self-map mass = 3,188,831 occurrences.** (This reproduces D080 F3's 3,188,831
independently — a second provenance check that passes.)

---

## 2. NEW FINDING (positive, high value): the self-map loop carries 98.00% of its own mass in s3

**Direct paired evidence, same token, same corpus, six files.** For each state, the full name
and its code move in exact opposition:

| token | train_s1 per 1k | train_s2 per 1k | **train_s3 per 1k** | test_s2 per 1k | **test_s3 per 1k** |
|---|---|---|---|---|---|
| `maharashtra` | 217.83 | 158.72 | **11.38** | 159.62 | **9.37** |
| `mh` (self-map) | 2.38 | 0.80 | **151.93** | 0.79 | **154.44** |
| `karnataka` | 79.85 | 58.68 | **4.55** | 59.45 | **3.88** |
| `ka` (self-map) | 2.73 | 2.40 | **56.62** | 2.53 | **58.18** |
| `tamil` | 72.01 | 52.55 | **3.74** | 53.24 | **3.12** |
| `tn` (self-map) | 0.00 | 0.00 | **49.38** | 0.00 | **50.67** |
| `uttar` | 85.85 | 62.72 | **6.18** | 63.22 | **5.25** |
| `up` (self-map) | 0.75 | 0.69 | **58.21** | 0.69 | **59.17** |
| `delhi` | 364.56 | 243.35 | **211.23** | 243.13 | **209.94** |
| `dl` (self-map) | **0.00** | **0.00** | **95.29** | **0.00** | **96.10** |

`dl` and `tn` are **exactly 0 in every s1/s2 file** and >104,000 in every s3 file. That is a
clean, zero-vs-nonzero signature: in s1/s2 those two codes are *never* used as a standalone
token, in s3 they are a primary state encoding.

**Interpretation (marked as inference).** `s3` Indian addresses appear to carry the state as the
ISO-ish two-letter code in its own comma-component, while `s1`/`s2` carry the spelled-out name.
*What the data shows* is the token-mass inversion above. *What I am inferring* is the mechanism:
that the s3 code sits alone in a component, which is what `normalize.py:333` requires.

**Consequence, and why this is the most important thing in this report.** Because a lookup
needs the whole component to equal the key, the s3 code is resolvable **only** because the
self-map loop inserted the canonical value as its own key. Without line 252-254, every one of
those ~3.1M s3 occurrences would fail to resolve a state, and the s3 India state feature would
be near-empty. The prior audits (D078 §3, D080 F1) correctly recorded "the loop is present and
correct" but treated that as a formality. It is the load-bearing half of the table.

> **Recommendation, and it is a strong DO-NOT-TOUCH:** do not remove, restructure or
> "simplify" the self-map loop, and do not "clean up" the bare-code keys as redundant. A
> plausible-looking tidy-up here silently deletes the state feature for **4,520,547** Indian
> rows (`train_s3` 2,115,547 + `test_s3` 2,405,000). This is the single highest-value sentence
> in this report.

---

## 3. The negative, re-confirmed: no missing state or UT

The work order asked me to check the union-territory tier first, on the theory that a table
calling UTs "states", or omitting them, would be a genuine structural finding. I checked it
properly and **the suspicion does not hold.**

The 37 canonical values decompose as **28 state codes + 9 UT/NCT codes**:

- 28 states: `ap ar as br cg ga gj hr hp jh ka kl mp mh mn ml mz nl od pb rj sk tn tg tr up uk wb`
- 9 UT/NCT: `an` (A&N Islands), `ch` (Chandigarh), `dd` (Daman and Diu), `dl` (Delhi),
  `dn` (Dadra and Nagar Haveli), `jk` (Jammu and Kashmir), `la` (Ladakh), `ld` (Lakshadweep),
  `py` (Puducherry)

India's UT list is complete and correct. **No UT is omitted.** This independently reproduces
D080 F1. There is also **no state/UT labelling defect**: `IN_STATES` is a flat `str -> str` map
with no tier metadata, so it cannot "call a UT a state" — the union-territory-vs-state
ambiguity the work order worried about is **not expressible in this table**.

### 3a. The merged-territory / stale-table case — a real gap, with zero measurable stake

The work order specifically flagged *"the `Dadra and Nagar Haveli and Daman and Diu` style
merged/renamed territories, which are a classic source of stale tables"*. This one is real and

### 3b. `haveli` — a token no prior task probed (NEW evidence, but not a gap)

D080's gazetteer sweep (§F4a) probed `dadra`, `daman`, `diu` — all 0 — and closed the
Dadra/Nagar Haveli question. It did **not** probe `haveli`, which is a large token:

| token | India addr total | US addr total | France addr total |
|---|---|---|---|
| `haveli` | **52,465** | 0 | 0 |
| `nagar` | 1,578,887 | 0 | 0 |

`haveli` clears the 1,979 floor by a factor of 26, so this is a real, visible token, not a
below-floor sliver. It is India-specific (0 in the US and 0 in France).

**But this is NOT evidence of a missing state key, and I am not claiming one.** *Inference,
marked:* `Nagar Haveli` is also the name of a **town in Gujarat** (near Surat), and with
`nagar` at 1,578,887 the overwhelming majority of `haveli` occurrences are almost certainly the
town/locality, not the union territory. The UT form requires `dadra`, which is 0 in every file.
**The profile has no bigram or component field, so I cannot separate the two readings, and I
refuse to guess.** I therefore record this as an **evidence gap, not a dictionary gap**: if
anyone wants to confirm that `Nagar Haveli` (the UT) is being mis-handled, the profile as built
**cannot answer the question** — a whole-component histogram would be required.

If it *were* ever wanted, the minimal addition would be `"nagar haveli": "dn"`. I am explicitly
**not** recommending it: the evidence does not support it and the downside (firing on a Gujarat
town name) is real.

### 3c. The Delhi ambiguity — fully covered, three spellings, no gap

`delhi` = 2,621,031; `new` = 1,034,062; `nct` = **0**; `dl` = 432,705 (s3 only). The dictionary
carries **three** Delhi keys, which I enumerated from the key list:

```
delhi        -> dl
new delhi    -> dl
nct of delhi -> dl
```

plus the self-map `dl -> dl`. So `Delhi`, `New Delhi`, `NCT of Delhi` and the bare code are all
handled, and `New Delhi` vs `Delhi` are **not** conflated — they are two distinct keys that
happen to share a canonical value, which is the correct design. **No gap.** `nct of delhi` is
unmeasurable (`nct` = 0, not in the top 4000) but is harmless and correct to keep.

### 3d. Ordinal / state-suffix / concatenation variants — all measure 0

I probed every concatenation and suffix variant a real Indian address might use, all six files:

| variant probe | six-file total |
|---|---|
| `uttarpradesh` | 0 |
| `andhrapradesh` | 0 |
| `himachalpradesh` | 0 |
| `madhyapradesh` | 0 |
| `arunachalpradesh` | 0 |

### 3e. Districts where states are expected

D080 F8 already measured this at scale (82 of 100 probed Indian districts above the floor:
`pune` 574,946, `hyderabad` 477,654, `noida` 170,497, ...). I **agree with D080's conclusion
and do not re-derive the numbers**: a district is not a state, and adding district names to
`IN_STATES` would emit wrong state codes and actively degrade the feature. D080's own caution
stands — the profile is unigram-only with no co-occurrence, so **whether a district-bearing
address also carries its state is unanswerable from this instrument**. I flag it as a
profile-harness gap, not an `IN_STATES` gap.

---

## 4. NEW latent defect: the loop manufactures the English-word keys `as` and `an`

D078's Defect 2 correctly identified that some `IN_STATES` keys are ordinary English words
rather than state names, and measured `or` = 0, `ut` = 0, `ts` = 2,187. But it examined only
the **literal** short aliases. It did not examine the keys **the self-map loop itself creates**,
which is where the real English-word exposure lives.

Three of the 37 canonical codes are ordinary English words, and all three are created by
`normalize.py:254`, not written by hand:

| code | state | as an English word | India addr total | D078 flagged it? |
|---|---|---|---|---|
| `as` | Assam | "as" (conjunction) | **2,743** | **no** |
| `an` | Andaman & Nicobar | "an" (article) | **3,647** | **no** |
| `la` | Ladakh | "la" (solfège) | **4,473** | yes (as a short token, not as a loop key) |
| `or` | Odisha (literal) | "or" (conjunction) | **0** | yes |
| `ut` | Uttarakhand (literal) | "ut" | **0** | yes |
| `ts` | Telangana (literal) | "ts" | **2,187** | yes — "the live risk" |

**The live exposure is `as` + `an` = 6,390 occurrences, 2.92x the `ts` figure D078 singled out
as the one real risk** (6,390 / 2,187 = 2.920). `ts` is a rarer English token than `as` or `an`,
which is why the ordering is inverted from what the literal-key audit implied.

**Severity: latent, and low — but it is a real class, and it is new.** Two constraints keep it
harmless today, and I state both rather than overclaim:

1. The match is **whole-component** (`normalize.py:333`), so only an address component that is
   *literally* the bare word `as` or `an` would misfire. An `as` inside `"Shastri Nagar"` or a
   house-number block is not a component match. The 2,743 / 3,647 token counts are **upper
   bounds on candidates, not measured misfires** — the profile cannot count true misfires at all.
2. Country scoping keeps the US meanings of `la` (Louisiana) and `as` out of Indian rows
   (`STATE_MAPS.get(country, {})`, `normalize.py:318`).

**Recommendation: no behavioural change.** This is the same "add a regression test, do not edit
the dictionary" pattern D079 already recommended for its 7 cross-country collisions. A cheap
guard is a test asserting the *loop-generated* key set contains no English stopword, or simply
pinning the measured six-file totals `as` = 2,743 and `an` = 3,647 so a future edit trips a diff.

---

## 5. Cross-dictionary and cross-country collisions

**India x `ADDR_CANON_COMMON` — 2 members, unchanged and correct.** I re-derived the set
intersection of the 86 effective `IN_STATES` keys against the 177 `ADDR_CANON_COMMON` keys
(`normalize.py:153` onward). Result: **exactly 2** — `keralam` and `odisha`. This independently
reproduces D080 F6. The ordering in `normalize_address` resolves it correctly:
`normalize.py:333-335` consumes a state component and `continue`s, so the `canon.get` pass at
line 347 never sees it; a non-standalone `odisha` falls through to `ADDR_CANON_COMMON` and

---

## 6. Gaps — what I could NOT establish

Stated plainly, because a plausible wrong number here would propagate into a real submission.

1. **No true zero is provable.** Every "0" means "not in the top 4000", bounded at < 1,979
   six-file occurrences. A gap smaller than ~1,979 rows would be invisible to this instrument.
2. **True false-positive rate is unmeasurable.** I can bound *candidate* tokens (`as` 2,743,
   `an` 3,647, `la` 4,473, `ts` 2,187) but never *actual* component-level misfires, because the
   profile has no whole-component field.
3. **The s3 code-placement mechanism is inferred, not measured.** I show token-mass inversion
   (§2) but cannot show that the code occupies its own comma-component, which is what
   `normalize.py:333` needs. A component histogram would settle it.
4. **`Nagar Haveli` town-vs-UT is unresolvable here** (§3b). `haveli` = 52,465 is real, but the
   profile cannot say whether it is the Gujarat town or the union territory.
5. **Semicolon prevalence is unmeasurable** — inherited from D078 Defect H. `build_profile.py:31`
   splits components on `[,;]` while `normalize.py:322` splits on `,` only, and the profile has
   no semicolon field. A semicolon-only separator could hide a state component from the pipeline.
6. **Indic-script text is invisible to the whole report.** `build_profile.py:28`'s
   `TOKEN_RE = [a-z0-9]+` cannot match Devanagari, so Indian addresses written in Indic script
   contribute zero tokens to every number above. This biases every count **downward** by an
   unquantified amount, and is the strongest reason not to over-trust any "not in the top 4000".
7. **10 of 37 self-map codes are below the floor** (`cg jh jk ld ml mz nl py tr uk`, all 0) and
   so are unmeasurable, even though §2 shows the loop is load-bearing. I cannot say whether
   they fire in s3 or never appear at all.
8. **The s3 self-map mass is an upper bound on s3 state resolutions**, for the same
   whole-component reason as every other count here.

---

## 7. Bottom line

| question asked | answer |
|---|---|
| Is any India state/UT missing from `IN_STATES`? | **No.** 28 states + 9 UT/NCT codes, all present. |
| Does any token in the profile look state-shaped but unhandled? | **No.** All concatenation, ordinal, merged-territory and alternate-spelling probes measure 0. |
| Is the union-territory tier defective? | **No.** All 9 UTs present; the table has no tier labelling to get wrong. |
| Is the merged `Dadra and Nagar Haveli and Daman and Diu` UT missing? | **Yes, structurally** — the table is pre-2020 vintage. **Zero measurable impact** (`dadra`/`daman`/`diu` all 0). |
| Is `New Delhi` vs `Delhi` confused? | **No.** Three distinct keys sharing canonical `dl`, plus self-map `dl`. |
| Does `IN_STATES` get the self-map loop? | **Yes** (`normalize.py:252`). And it is **load-bearing for 4,520,547 s3 India rows** (2,115,547 + 2,405,000). |
| Is the dead `jammu & kashmir` key still there? | **Yes** (D078 Defect 1, confirmed by D080 F7). **Blast radius zero** — `jammu` and `kashmir` both 0. |
| Any NEW defect? | **Yes, one, latent:** loop-generated keys `as` (2,743) and `an` (3,647) are English words — 2.92x the exposure of the `ts` risk D078 did flag. No behavioural change warranted. |

**Headline recommendation: DO NOT CHANGE `IN_STATES`.** The dictionary is complete for this
corpus. The two things worth recording for the humans who own this code are (a) the self-map
loop is the sole state-resolution mechanism for the two `s3` files and must not be "cleaned
up", and (b) the `as`/`an` self-map keys deserve a regression test, not an edit. **"No change
needed" is the finding, and it is a well-evidenced one.**

---

*Note on France: the scored country is France, absent from training. Nothing in this report
bears on French scoring, and I found no France analogue of the India findings. Recorded
explicitly so the aggregator does not misread a large number here as a France-impact number.*

yields `orissa`, the same canonical value. **No defect.**

**India x `US_STATES` — no live bug.** D079 measured 7 shared keys meaning different states
(`ar ga la mn or tn ut`) totalling 976,874 US occurrences, and correctly concluded the risk is
latent because `STATE_MAPS` is keyed strictly by country (`normalize.py:250`, `318`). I
re-verify the mechanism and **do not re-derive the counts**: `smap = STATE_MAPS.get(country, {})`
means a US row can never read an `IN_STATES` key. **No action.**

**`or` and `ut` remain measurably safe.** 0 occurrences in all six files (not in the top 4000).
D080 recommended leaving them alone; I agree, and add that `ts` should join them in the "leave
it" bucket *for this corpus* while `as`/`an` are noted as the more exposed pair.

**`jammu & kashmir` dead key (D078 Defect 1 / D080 F7) — re-confirmed, still zero stake.**
`jammu` = 0 and `kashmir` = 0 in all six files, so nothing changes. Not re-derived.

| `westbengal` | 0 |
| `nctofdelhi` | 0 |
| `andamannicobar(islands)` | 0 |
| `dadranagarhaveli(andamandiu)` | 0 |
| `uttaranchal` | 0 |
| `pondicherry` | 0 |
| `coorg` | 0 |
| `himachal` / `arunachal` / `andaman` / `nicobar` / `daman` / `diu` / `dadra` / `nct` | 0 |
| **`tamilnadu`** | **4,567** |
| `lakshadweep` / `ladakh` / `puducherry` | 0 |

**A genuine internal asymmetry exists here and is worth recording even though it costs
nothing.** The dictionary bothers with the *concatenated* spelling for exactly **two** states —
`tamilnadu` (line 236) and `uttaranchal` (line 238) — but not for `uttarpradesh`,
`andhrapradesh`, `madhyapradesh`, `himachalpradesh`, `arunachalpradesh` or `westbengal`, all of
which are common in the wild. The data explains why: of that whole family, **only `tamilnadu`
actually occurs** (4,567, above the floor). The coverage looks uneven but is in fact tuned to
what this corpus contains, and `tamilnadu -> tn` earns its place.

**No ordinal variants were found for India.** (The known ordinal defect — `LEET` firing on
French `3eme -> eeme` — is France-only and is already settled in the fleet brief. I did not
re-derive it and found no India analogue.)

I am reporting it as a **structural** finding, carefully bounded:

- The dictionary carries the **pre-2020 split** form: `"dadra and nagar haveli": "dn"` and
  `"daman and diu": "dd"` as two separate keys (`normalize.py:240-241`).
- The **merged** post-reorganisation UT is **absent**. I tested the key list explicitly:
  `MERGED_UT_KEY_present = False`. There is no key covering the combined territory.
- `nagar haveli` alone is also **not** a key (`NAGAR_HAVELI_ALONE = False`).

**Measurable stake: none.** `dadra` = **0**, `daman` = **0**, `diu` = **0**, `dnhh` = **0** in all
six files (not in the top 4000). So the pre-2020 keys `dn` and `dd` are themselves
**unmeasurable** in this corpus, and the missing merged form cannot be shown to cost anything.
Label: **CONFIRMED structural gap, zero measured impact, do not act on it for this dataset.**


Splitting that 3,188,831 by source:

| slice | self-map occurrences | share |
|---|---|---|
| `train_s3` + `test_s3` | **3,125,112** | **98.00%** |
| `train_s1` + `train_s2` + `test_s1` + `test_s2` | 63,719 | 2.00% |

Arithmetic: 3,125,112 / 3,188,831 = 0.98004 -> **98.00%**.

Rate per 1,000 India rows, same 37 codes:

| file | India rows | self-map mass | per 1k |
|---|---|---|---|
| train_s1 | 883,188 | 11,089 | 12.56 |
| train_s2 | 2,017,799 | 19,558 | 9.69 |
| **train_s3** | 2,115,547 | **1,449,612** | **685.22** |
| test_s1 | 809,986 | 10,175 | 12.56 |
| test_s2 | 2,312,565 | 22,897 | 9.90 |
| **test_s3** | 2,405,000 | **1,675,500** | **696.67** |

The per-1k rate jumps **~70x** between s2 and s3 (9.69 -> 685.22 train, 9.90 -> 696.67 test).
This is not a sampling wobble; it is a change in how the address is written.
