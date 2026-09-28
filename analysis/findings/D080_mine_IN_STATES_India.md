# D080 — mine evidence to extend `IN_STATES` for India

## Headline

**`IN_STATES` needs no extension for India, and the profile cannot demonstrate a need either way for most of it.** All 28 states and all 9 UT/NCT codes of India are already keys (37 distinct canonical values, 86 effective keys after the self-map loop), and every legacy/alternate spelling the dictionary bothers with — `orissa`, `chattisgarh`, `keralam`, `uttaranchal`, `pondicherry`, `ts`, `ut`, `or`, `nct of delhi` — is already there. Mining the full visible India address vocabulary (4,574 distinct unigrams) for anything state-shaped that is *not* already a key returns **zero candidates above the 1,979-occurrence truncation floor**. `IN_STATES` keys that are measurable already carry **8,937,976 India address-token occurrences = 9.17% of the 97,463,176 visible India address-token mass**. The 42 of 86 keys with no measurable unigram are reported as a **gap**, not estimated.

**The one NEW defect I found is in `LEET`, not in `IN_STATES`:** `LEET["@"]` and `LEET["$"]` (`normalize.py:256`) are **structurally unreachable dead entries**, because `normalize.py:269`'s `_non_alnum = [^a-z0-9]+` splitter guarantees every token reaching `normalize.py:279` is `[a-z0-9]+` only.

## Findings

### F0 — Provenance and invariants

All counts aggregate the six profiles `train_s1..3`, `test_s1..3`. Every India figure comes from `country_rows["India"]`, `by_country["India"]`, and `addr_tokens["India"]` / `name_tokens["India"]`.

Two internal-consistency checks run on all six files, both hold 6/6 — this is my provenance check that the profile is self-consistent:

- `rows == sum(country_rows.values())` — 6/6.
- `by_country[c]["rows"] == sum(by_country[c]["len_hist"].values())` — 6/6 files x 3 countries (18/18).

| quantity | value | source |
|---|---|---|
| India rows, all six files | **10,544,085** | `sum(country_rows["India"])`, verified against `sum(by_country["India"]["rows"])` |
| India address rows with >=1 comma | 10,309,283 (97.7731%) | `rows - (rows - has_comma)` |
| India address rows empty | 234,798 (2.2269%) | `by_country["India"]["addr_empty"]` |
| **non-empty India addresses with NO comma (= single component)** | **4 (0.0000380%)** | `(rows - has_comma) - addr_empty` = 234,802 - 234,798 |
| India visible address-token mass | **97,463,176** | `sum` of `addr_tokens["India"]`, 6 files x top-4000 => **lower bound** |
| tokens per India address row | 9.24 | 97,463,176 / 10,544,085 |

### F1 — `IN_STATES` is already complete for the Indian state/UT tier (CONFIRMED, code-only, no data needed)

Re-derived by `ast.literal_eval` of the dict node at `normalize.py:230-242`, then the self-map loop at `normalize.py:252-254` applied in memory:

- **49** literal pairs -> **37** distinct canonical values -> **86** effective keys.
- `k == v` pairs: `[]` (no value is already a key, so the loop adds exactly 37).

The 37 canonical values are the complete Indian administrative tier: the 28 state codes `ap ar as br cg ga gj hr hp jh ka kl mp mh mn ml mz nl od pb rj sk tn tg tr up uk wb`, plus 9 UT/NCT codes `an ch dd dl dn jk la ld py`. **Nothing at state or UT level is missing.** This matches the D078 ground truth I was given (49 pairs / 37 values / 86 keys) and re-derives it independently.

**Consequence: no `IN_STATES` addition can be justified by "a state is missing".** The only legitimate extension categories are spelling variants, district-level geography, and abbreviation forms — each tested below.

### F2 — What is measurable and what is not (the truncation floor)

`build_profile.py:27` sets `TOPN = 4000`, so each per-file list is capped. The floor is the 4000th (last) token count in each list:

| file | last `addr_tokens["India"]` token | floor |
|---|---|---|
| train_s1 | `nawab` | 182 |
| train_s2 | `ngar` | 394 |
| train_s3 | `1502` | 362 |
| test_s1 | `mushahari` | 166 |
| test_s2 | `aruna` | 459 |
| test_s3 | `19b` | 416 |

**Sum of floors = 1,979.** A token absent from all six lists has a true six-file total of **< 1,979**. (`build_profile.py:45-48` also prunes `count <= 1` every 8 chunks, so the true floor is somewhat higher than 1,979; 1,979 is the arithmetic bound I can actually defend.)

Partitioning the 86 effective keys into 35 single-word non-code + 14 multiword + 37 codes (= 86):

| class | n | measurable mass | below floor / structurally unmeasurable |
|---|---|---|---|
| canonical codes (the 37 self-maps) | 37 | **27 present, 3,188,831 occ** | **10 below floor**: `cg jh jk ld ml mz nl py tr uk` |
| single-word name keys | 35 | **17 present, 5,749,145 occ** | **18 below floor**: `assam chattisgarh chhattisgarh jharkhand ladakh lakshadweep manipur meghalaya mizoram nagaland or pondicherry puducherry sikkim tripura ut uttarakhand uttaranchal` |
| multiword keys (contain a space) | 14 | n/a — **cannot ever be a single unigram**, so their 0 is structural, not a measurement | 14 |
| **total** | **86** | **44 of 86 keys measurable, 8,937,976 occ** | **42 of 86 with no measurable unigram** |

This is a different grain from the D078 figure of "36 of 86 below the floor". Mine is 28 zero-occurrence keys measured directly (18 name + 10 code) **plus** 14 multiword keys that are structurally unmeasurable as unigrams. Both are arithmetically correct at their own grain; cite 42-of-86 only if you also count the multiword keys.

### F3 — Measured mass already captured by `IN_STATES` keys in India

| group | occurrence | rate |
|---|---|---|
| 37 canonical code keys | 3,188,831 | 302.43 per 1,000 India address rows (3,188,831 / 10,544,085 x 1000) |
| 17 single-word name keys | 5,749,145 | 545.30 per 1,000 rows |
| **total** | **8,937,976** | **9.17% of the 97,463,176 visible India addr-token mass** |

Top single-word name keys (`addr_tokens["India"]`, six files): `delhi` 2,621,031 | `maharashtra` 1,104,757 | `karnataka` 410,672 | `gujarat` 335,446 | `telangana` 283,530 | `haryana` 218,443 | `rajasthan` 188,237 | `kerala` 181,552 | `bihar` 141,819 | `punjab` 85,621 | `keralam` 67,682 | `orissa` 57,491 | `odisha` 40,791 | `tamilnadu` 4,567 | `chandigarh` 4,436 | `ts` 2,187 | `goa` 883.

**These are unigram counts, so they are UPPER BOUNDS on state matches, not match counts** (see Gaps). The direction of the error is known and stated: a unigram occurrence can sit anywhere in an address, whereas `normalize.py:333` requires the *whole* comma-component to equal the key.

### F4 — Mining result: NO unhandled state-shaped token exists above the floor (the direct answer to the question)

Three independent sweeps over the visible India address vocabulary, all returning nothing actionable:

**(a) Gazetteer sweep.** I probed, from my own knowledge (no network, no external file), every Indian state, UT, and the common legacy spellings. Result: **every state/UT name is either already a key or measures 0.** Legacy/alternate spellings measured 0 across all six files: `chhattisgarh`, `chattisgarh`, `himachal`, `arunachal`, `uttarakhand`, `uttaranchal`, `pondicherry`, `puducherry`, `coorg`, `nct`, `dadra`, `daman`, `diu`, `jammu`, `kashmir`, `andaman`, `nicobar`, `islands`, `ladakh`, `lakshadweep`, `manipur`, `meghalaya`, `mizoram`, `nagaland`, `sikkim`, `tripura`, `jharkhand`, `assam`. All are below the 1,979 floor, so this is a **negative result at the resolution limit, not a proof of zero.**

**(b) Fuzzy sweep.** Every India addr unigram with count >= 2,000, not already handled by any dictionary, compared at cutoff 0.85 against the state-name word set: **16 hits, all false positives.** Highest is `punjabi` 9,706 ~ `punjab` (a demonym, not a state string), `nagari` 6,326 ~ `nagar`, `gola` 3,798 ~ `goa`, `naidu` 3,383 ~ `nadu`, `aman` 2,912 ~ `daman`. **None is a state-name variant.**

**(c) Geography-suffix sweep.** 167 India addr tokens ending in `pur / pradesh / garh / nagar / bad / gram / circle / zone / region / taluk / mandi / district / block / ward / sector`, count >= 1,500. The top 167 are **overwhelmingly cities and localities** — `hyderabad` 477,654, `ahmedabad` 257,841, `jaipur` 207,060, `nagpur` 96,788, `kanpur` 63,370, `raigarh` 33,395, `gandhinagar` 39,609. **Not one is a state.** Adding these to `IN_STATES` would be actively wrong.

**Verdict: `IN_STATES` has zero CONFIRMED extension candidates for India.** This is a positive "no change needed" result, stated as such.

### F5 — NEW DEFECT: `LEET["@"]` and `LEET["$"]` are unreachable dead entries (CONFIRMED, code + simulation)

```python
LEET = str.maketrans({"0":"o","1":"l","3":"e","4":"a","5":"s","6":"g","7":"t","8":"b","@":"a","$":"s"})   # normalize.py:256
_non_alnum = re.compile(r"[^a-z0-9]+")                                                            # normalize.py:269
...
for t in _non_alnum.split(s):                                                                     # normalize.py:276
    if any(c.isalpha() for c in t) and any(c.isdigit() for c in t):                                # normalize.py:279
        t = t.translate(LEET)                                                                     # normalize.py:280
```

`_non_alnum.split` can only ever emit tokens matching `^[a-z0-9]+$`. Therefore `'@'` and `'$'` can never be a character of a token, so `LEET["@"]` and `LEET["$"]` can never fire. I proved this by executing a byte-exact replica of `_name_tokens` over a sweep of `aXc` for every ASCII alphanumeric `X`:

```
'S@shi Enterprises'  -> ['s', 'shi', 'enterprises']      # split, not translated
'Shiv$ Traders'      -> ['shiv', 'traders']             # '$' deleted by the split
'5olutions Inc'      -> ['solutions', 'inc']            # '5' IS translated
'c0m pvt ltd'        -> ['com', 'pvt', 'ltd']           # '0' IS translated
tokens containing '@' or '$' reachable via _name_tokens: NONE
```

Only `0 1 3 4 5 6 7 8` can ever fire. **Severity: cosmetic.** The intent of those two entries is to catch `S@shi`, and the surrounding split silently destroys the signal before `LEET` sees it — so the correct fix is a pre-split substitution, not a bigger `LEET` table. No behavioural change is lost by deleting them; the finding matters because it shows the leet table was written against a mental model of the code that the code does not implement.

### F6 — CONFIRMED NON-DEFECT: `odisha` and `keralam` sit in two dictionaries at once, and the ordering makes `IN_STATES` win

These are the **only** two strings that are both an effective `IN_STATES` key and an `ADDR_CANON_COMMON` key (measured by set intersection, not asserted):

| string | `IN_STATES` | `ADDR_CANON_COMMON` | India addr occurrences |
|---|---|---|---|
| `odisha` | `-> od` | `-> orissa` | 40,791 |
| `keralam` | `-> kl` | `-> kerala` | 67,682 |
| `orissa` (canon target) | `-> od` | absent | 57,491 |
| `kerala` (canon target) | `-> kl` | absent | 181,552 |

Order of operations in `normalize_address` resolves it correctly:

- `normalize.py:333-335` — `if ck in smap: state = smap[ck]; continue`. The component is consumed as a state and **never reaches** the token loop.
- `normalize.py:342-349` — the `canon.get(t, t)` pass runs only for components that were *not* a state key.

So a standalone `Odisha` component yields `state='od'`; a non-standalone `odisha` (e.g. inside `odisha 500001`) falls through to `ADDR_CANON_COMMON` and yields the address token `orissa`. **Both routes land on the same canonical value (`od`), and the fallback route lands on the same token as a literal `orissa` component would.** This is a well-designed redundancy, not a defect. Same for `keralam`/`kerala` -> `kl`. Recording it because the duplicate membership looks alarming on a first read.

### F7 — D078 refinement: `"jammu & kashmir"` is a dead key, but the net user-facing loss is zero

D078's hard defect is **correct and I confirm it**: `normalize.py:331` does `.replace("&", " and ")` *before* the `ck in smap` lookup, so the key `"jammu & kashmir"` (`normalize.py:239`) can never match any input string.

What I add is the **severity correction**: `"jammu and kashmir"` is a key on the *same line, one token earlier*, and the `&`->`" and "` transform means the input `"Jammu & Kashmir"` produces `ck = "jammu and kashmir"`, which **does** match. So the dead key costs nothing:

- Input `"Jammu & Kashmir"` -> `ck = "jammu and kashmir"` -> `jk`. PASS
- The `"jammu & kashmir"` key is never consulted. Dead but redundant.

And the measurable stake is nil anyway: `jammu` = 0 and `kashmir` = 0 in `addr_tokens["India"]` across all six files (below the 1,979 floor). **This does not retract D078's finding — the key is genuinely unreachable — it narrows its blast radius from "a state is lost" to "a redundant line is dead."** The other three `&` keys are unaffected either way, because `ck` converts them to their `and` twins: `dadra and nagar haveli`, `daman and diu`, `andaman and nicobar islands`.

### F8 — The India analogue of the France s2/s3 department gap: districts are present at scale, `IN_STATES` maps none of them

The `already_checked` block warns that France's "region handling is fine" is **not settled** because test_s2/s3 encode geography with departments rather than regions. I ran the equivalent test on India rather than assuming the parallel.

**India's addresses are heavily district-level.** Of 100 major Indian districts I probed, **82 measured above the 1,979 floor**:

`pune` 574,946 | `hyderabad` 477,654 | `howrah` 232,678 | `gurgaon` 184,772 | `noida` 170,497 | `coimbatore` 120,122 | `ernakulam` 108,468 | `indore` 107,909 | `nagpur` 96,788 | `faridabad` 75,204 | `nashik` 68,224 | `kanpur` 63,370 | `thiruvananthapuram` 59,960 | `bhopal` 50,675 | `kozhikode` 47,197 | `malappuram` 42,717 | `thrissur` 41,700 | `varanasi` 39,912 | `ludhiana` 36,346 | `kanchipuram` 33,476 | `kolhapur` 33,085 | `madurai` 29,497 | `allahabad` 27,014 | `daskroi` 24,013 | `gorakhpur` 23,361 ... down to `asansol` 3,745, `bankura` 4,105, `ratlam` 4,076, `medinipur` 4,984, `malda` 4,776.

Subdivision vocabulary is unhandled at scale too: `parganas` 73,085 | `region` 70,887 | `dist` 56,836 | `district` 35,210 | `circle` 33,391 | `mandi` 24,851 | `daskroi` 24,013 | `taluk` 21,865 | `zone` 18,181 | `ward` 116,285 | `block` 511,622.

**`IN_STATES` contains none of these, and should not** — a district is not a state, and adding them would emit wrong state codes. But this is the same *shape* of problem as the France department gap, and it is the honest "anything nobody has asked about" result for India:

- **What the data shows:** Indian addresses carry a large, unhandled district/subdivision vocabulary.
- **What I cannot show (see Gaps):** whether a district-bearing address also carries its state. The profile is unigram-only with no co-occurrence, so I **cannot** claim Indian state resolution is impaired the way the France s2/s3 numbers claim French region resolution is. **I am explicitly not asserting a defect here.**

### F9 — The India `pin` signal is effectively dead (NEW, measured)

`normalize.py:337` captures `pin` only when `len(n) == 6 and country == "India"`. Measured across all six files, India:

| field | total | rate |
|---|---|---|
| `by_country["India"]["dig6"]` (standalone 6-digit, lookaround-guarded) | **2,237** | **0.2122 per 1,000 rows** = 0.0212% |
| `by_country["India"]["dig5"]` (standalone 5-digit) | 100,265 | 9.51 per 1,000 rows |
| `by_country["India"]["num_digits"]` (all address digits) | 46,008,263 | 4.363 per row |
| `by_country["India"]["alpha_only_addr"]` | 655,039 | 6.21% => **93.79% of India rows contain at least one digit** |

93.79% of Indian addresses contain digits, `num_digits` averages 4.36 per row, and yet only **2,237 standalone 6-digit numbers exist in 10,544,085 Indian rows**. Consistently, **zero pure-digit 5- or 6-length tokens appear anywhere in the top-4000 of any of the six files** (the visible pure-digit tokens are L1 x10, L2 x100, L3 x522-807, L4 x29-36 per file — no L5, no L6 at all).

*Inference, marked as such:* the digits in Indian addresses in this corpus are house numbers, floor numbers, plot numbers and sectors — **not 6-digit PIN codes**. On this evidence the India `pin` feature is close to vestigial. I am **not** claiming the `len==6` guard is wrong for India; I am claiming the guard has almost nothing to capture for India either way. Contrast: US `dig6` runs 0.00120-0.01430 per row, and the US source-1 dip (0.00120 in test_s1, 0.00125 in train_s1 vs 0.01335-0.01430 in s2/s3) is the already-covered, already-delivered US finding, which I do not re-derive.

### F10 — Component structure is healthy for India (positive finding)

`normalize.py:333` can only resolve a state if the address has at least two comma-separated components. For India it always does: **234,802 of 10,544,085 India rows have no comma, and 234,798 of those are empty addresses — leaving exactly 4 non-empty single-component India addresses in the entire corpus (0.0000380%).** The component-lookup precondition is therefore effectively universal for India, which is the opposite of the France s2/s3 situation and is worth recording as a structural difference.

Caveat inherited from D078 Defect H: `build_profile.py:31` splits components on `[,;]` while `normalize.py:322` splits on `,` only, so a semicolon-only separator would hide a real component from the pipeline. There is **no semicolon field in the profile**, so semicolon prevalence is unmeasurable — see Gaps.

### F11 — Leetspeak mining for India

LEET is applied to **name** tokens only (`normalize.py:279-280`), never to address tokens (`normalize.py:342-349`).

**India LEET-eligible name tokens** (`name_tokens["India"]`, contains >=1 alpha and >=1 digit, per `normalize.py:279`): **127 distinct, 80,735 occurrences.** LEET is doing real work here and is working correctly:

| token | occ | LEET output | token | occ | LEET output |
|---|---|---|---|---|---|
| `5ervices` | 5,407 | `services` | `techn0logies` | 1,327 | `technologies` |
| `c0m` | 2,873 | `com` | `de1hi` | 1,674 | `delhi` |
| `8rothers` | 2,386 | `brothers` | `1imited` | 1,255 | `limited` |
| `br0thers` | 2,000 | `brothers` | `f0undation` | 1,734 | `foundation` |

**Digits `2` and `9` are absent from LEET.** For India the entire measured exposure is **one token: `2nd`, 253 occurrences** (`name_tokens["India"]`). All other 79,482 LEET-eligible occurrences use digits LEET already covers. `2nd` is an ordinal, not a leet spelling, so **extending LEET with `2`/`9` would gain nothing and would risk corrupting the 859,099 occurrences of the address token `2` and the 283,400 of `9`.** Recommend **do not extend** — a sharper, India-specific version of D079's US conclusion, where the exposure was the single token `24hr` at 3,657.

**India address tokens that would be leet-corrupted if LEET were extended to addresses: 160 distinct, 2,087,204 occurrences**, dominated by ordinals (`2nd` 324,528, `1st` 305,356, `3rd` 226,631, `4th` 146,972) and block labels (`b3` 105,589, `1a` 38,231, `a1` 16,283). `b3` -> `bg` would be actively wrong. **Do not extend LEET to addresses.**

### F12 — Abbreviation-pair mining: the risky keys, and why they are harmless

The 27 measurable canonical codes are all already keys. The **10 below-floor codes** are `cg jh jk ld ml mz nl py tr uk` — the Indian states/UTs with no measurable standalone code occurrence.

The one live class of risk is a 2-letter key that is also an English or common word. Only three qualify:

| key | meaning in `IN_STATES` | India occurrences |
|---|---|---|
| `as` | assam | 2,743 |
| `an` | andaman and nicobar | 3,647 |
| `or` | orissa (-> `od`) | **0** |
| `ut` | uttarakhand (-> `uk`) | **0** |
| **sum** | | **6,390** |

6,390 / 97,463,176 = **0.0066% of visible India address-token mass**, and even that is a gross over-count: `normalize.py:333` requires the *whole* component to be exactly `as`/`an`/`or`, so only a strict subset of those 6,390 unigram occurrences is even reachable. **Quantified and dismissed: the `or -> od` and `ut -> uk` entries, which look like the most dangerous lines in the dictionary, measure literally zero Indian occurrences.**

The 7 `US_STATES`/`IN_STATES` key collisions (`ar ga la mn or tn ut`) remain latent exactly as D079 established; India-side mass for all 7 is 248,315 occurrences (D079's figure, not re-derived) and the `len > 3` guard at `learn_translit.py:55` still filters all 7. India occurrences: `la` 4,473 | `ar` 6,730 | `ga` 4,030 | `mn` 3,750 | `or` 0 | `ut` 0.

### F13 — Does my evidence bear on the `already_checked` block?

- **REFUTED-1 (France postcode loss): my evidence does NOT support it, and I can reproduce the refutation.** I measured `by_country["France"]["dig5"]` for completeness: test_s1 **0.0042** per row, test_s2 **0.0051**, test_s3 **0.0053**, against US 0.1097-0.1101 and India 0.0028-0.0114. The work order's quoted 0.004 and 0.005 match mine to the displayed precision. **REFUTED-1 stands as refuted; nothing here revives it.**
- **REFUTED-2 (FR_REGIONS, re-scoped): out of scope and untouched.** I did no French region analysis and quote no French resolution rate. The only cross-cutting thing I can add is F10's structural contrast: India's component structure is near-perfect (4 exceptions in 10.5M rows), so whatever is wrong with France s2/s3 is **not** a component-splitting problem — it is a vocabulary-coverage problem. That is consistent with, and independently corroborates, the department-gap root cause stated in the work order. **I do not reconcile the 71.10% vs 97.4380% contradiction; it is not mine to resolve and I have no French component data.**


## Interpretation

Everything in this section is **inference**, not measurement.

1. `IN_STATES` is complete at the state/UT tier and has no measurable gap in spelling variants. The India geography vocabulary is **city-and-district-heavy at the address-token level but state-complete at the state-lookup level**. My reading: an Indian address almost always names a state or carries its code, so `state` resolves; the unhandled information is *which city/district*, which the current pipeline leaves to raw address tokens. This is a **feature-enrichment** opportunity (F8), not a `state` defect.
2. The `state` feature for India is probably already well-populated — `mh` 700,244, `dl` 432,705, `ka` 275,043, `up` 269,710 alongside `maharashtra` 1,104,757, `delhi` 2,621,031, `karnataka` 410,672. The code and name forms co-exist in the same corpus at plausible ratios. But *plausible ratio* is not proof, because I cannot see which tokens share a row.
3. F9 suggests the India `pin` is nearly vestigial in this corpus. If true, dropping the `len==6 and country=="India"` guard would be safe **and also pointless** for India — there is nothing to recover. I would not spend a submission cycle on it.

## Gaps

Stated plainly, not estimated.

1. **No component structure, so no state-resolution rate is derivable.** `addr_tokens` is a unigram bag (`build_profile.py:126-127` splits on `[,;]` then `TOKEN_RE.findall`). Every count I quote for a state key is an **upper bound** on matchable rows, never a match count. I cannot produce a "state resolves for X% of India rows" figure, and I have not estimated one. This is the single largest limitation of this report and it is not closable with the shipped profile.
2. **42 of 86 `IN_STATES` keys are unmeasurable**, and I did not estimate them: 10 codes and 18 single-word names measure 0 (below the 1,979 floor), and 14 multiword keys are structurally unmeasurable as unigrams. For the multiword keys I can only report their **component words**, which are all individually present except the below-floor ones: `pradesh` 783,159 | `nagar` 1,578,887 | `haveli` 52,465 | `and` 70,487 | `of` 66,007 | `new` 1,034,062 | `delhi` 2,621,031 | `west` 921,804 | `bengal` 331,662 | `uttar` 443,572 | `madhya` 130,403 | `tamil` 366,913 | `nadu` 366,795 | `andhra` 215,298; and below floor: `arunachal` 0, `himachal` 0, `jammu` 0, `kashmir` 0, `dadra` 0, `daman` 0, `diu` 0, `andaman` 0, `nicobar` 0, `islands` 0, `nct` 0.
3. **No co-occurrence data, so F8 cannot be upgraded from "districts are present" to "districts displace states".** Whether a district-bearing Indian address also carries its state is unmeasurable here.
4. **Semicolon prevalence is unmeasurable.** `has_comma` (`build_profile.py:108`) records `,` only; no profile field counts `;`. D078's Defect H divergence therefore remains open, and it is the one mechanism that could break F10's "components are always >=2" result.
5. **Indic script is invisible to this entire report.** `build_profile.py:28`'s `TOKEN_RE = [a-z0-9]+` cannot match Devanagari, and `translit_text` is *not* applied by the profile builder. Indian addresses written in Indic script contribute **zero** tokens to every number above, and a transliterated state name would look identical to an unhandled one. This biases every count downward by an unquantified amount.
6. **Truncation is two-edged.** Counts are lower bounds (the top-4000 cap) *and* the `prune(count<=1)` at `build_profile.py:45-48` runs periodically, so the effective floor is above 1,979. My "measured 0" claims mean "below an unstated threshold", not "absent".
7. **Multi-source denominators are never mixed here.** Every India rate in this report uses the six-file sum, 10,544,085 rows, as its denominator. No single-source rate is quoted as an India-wide rate.

## Recommendations

Prioritised. The headline is a **do-not-change**, stated as such rather than manufacturing work.

1. **DO NOT add anything to `IN_STATES` for India.** All 28 states and 9 UT codes are present (F1); the mining sweeps found zero unhandled state-shaped token above the truncation floor (F4); the fuzzy sweep's 16 hits are all false positives (F4b). This is the direct answer to the work order. Any edit here enlarges the D079 collision surface for no measured gain.
2. **PRIORITY 1 — the one real (cosmetic) fix: delete `LEET["@"]` and `LEET["$"]`, or implement the intent properly.** F5 proves both are unreachable. If the intent was to catch `S@shi`, the fix is a pre-split `s.replace("@","a").replace("$","s")` at `normalize.py:273` alongside the existing `&`/`+`/`'` replacements — **not** a bigger `LEET` table. Zero behavioural risk either way; do it so the next reader is not misled.
3. **PRIORITY 2 — record F8 as an owned follow-up, and scope it correctly.** Indian district vocabulary is large and unhandled (`parganas` 73,085, `daskroi` 24,013, `taluk` 21,865, plus 82 of 100 probed districts above the floor). It belongs in a **district/city normalisation table or a `city` feature**, **never in `IN_STATES`**. Before anyone sizes it, the component-structure gap (Gaps 1) must be closed — a new profile field counting whole components, not unigrams. Do not size this fix from the numbers in this report.
4. **PRIORITY 3 — do NOT extend `LEET` with `2`/`9`, and do NOT apply `LEET` to addresses.** India evidence: the `2`/`9` exposure is one token, `2nd`, 253 occurrences (F11), against 859,099 occurrences of the address token `2` that a `2 -> z`-style mapping would endanger. Address-side exposure is 2,087,204 occurrences including `b3` 105,589, which would become `bg`. Both moves are net-negative on this corpus.
5. **NO CHANGE — `learn_translit.py`'s `len > 3` guard.** 41 of 86 `IN_STATES` keys are permanently unreachable to transliteration learning (len <= 3). Not my task and not measured here; flagged only because every key I propose (none) would inherit the same fate.
6. **NO CHANGE to the `or -> od` and `ut -> uk` entries, and no removal of the dead `"jammu & kashmir"` key.** F7/F12: both measure 0 Indian occurrences, and the `&` key's `"jammu and kashmir"` twin already covers the input. Removing them would be a churn-only edit. If anyone *does* remove `"jammu & kashmir"`, note that `"jammu and kashmir"` must stay.
7. **Close the profile gap that blocked this whole task, if one harness change is allowed.** `build_profile.py` should record, per country, a histogram of **whole normalised components** alongside the unigram bag. Every "does state X resolve" question in this project — France departments (REFUTED-2), India districts, anything else — is currently unanswerable without it, and this task's entire conclusion had to be built on upper bounds. That is an analysis-harness change, not an `_upstream/` change, and it is the highest-leverage thing on this list.
