# P033 — [France] train_s3: digit structure and address-number behaviour

**Status: COMPLETE. The France slice of `train_s3` is EMPTY, exactly as the work order predicted.**
**The work order's *premise* is refuted; the *secondary* substance (the s3 state-representation
shift) is real, measured, and 3.21× larger than D118 recorded.**

**Agent:** c02 · **Family:** A-profile · **Primary input:** `analysis_out/profile/train_s3.json`
(cross-checked against `train_s1`, `train_s2`, `test_s1..3`; France supplement from test files)
**Code read:** `_upstream/src/{normalize,keys,features,build_features,decoy_postfilter,crossfit}.py`
**No raw `*.tsv` was opened. No network access. Read-only on `_upstream/` and the dataset.**

> **Filename note.** `analysis_out/tasks/P033.json` names the deliverable
> `P033_France_train_s3_numeric.md`. My work order names
> `P033_France_train_s3_digits.md` as the EXACT required filename. I follow the work order
> and flag the mismatch rather than silently picking one.

---

## 1. HEADLINE 1 — THE FRANCE SLICE OF `train_s3` IS EMPTY. SHARE = EXACTLY 0.

`build_profile.py:61-62` builds `country_rows` as a `Counter`; line 142 emits
`dict(country_rows)`. A country with zero rows produces **no key at all**, not a zero entry.

| Quantity | Value |
|---|---|
| `train_s3.json` → `rows` | **5,285,603** |
| `train_s3.json` → `country_rows["US"]` | 3,170,056 |
| `train_s3.json` → `country_rows["India"]` | 2,115,547 |
| 3,170,056 + 2,115,547 | **5,285,603 — equals `rows`, to the row** |
| `country_rows` keys present | `US`, `India` — **no `France`** |
| `by_country` keys present | `US`, `India` — **no `France`** |
| `addr_tokens` / `name_tokens` keys | **no `France`** |
| **France rows in `train_s3`** | **0** |
| **France share of `train_s3`** | **0 / 5,285,603 = 0.000000% — exactly 0** |

The parts summing to `rows` to the row is the denominator check the brief demands: the
country breakdown is **complete**, so France is **absent**, not hiding inside a bucket.
The same holds for `train_s1` (2,206,821 = 1,323,633 US + 883,188 India) and `train_s2`
(5,034,616 = 3,016,817 US + 2,017,799 India). **All 12,527,040 train rows are US or India.**
Cross-check in code: `crossfit.py:112` iterates `for c in ("US","India")`; `decoy_postfilter.py:17-18`
names France explicitly as a country with **no training labels**.

### 1.1 Every France rate in this work order is UNDEFINED, not 0%

The order asks for France `dig5`/row, `dig6`/row, total digit density, the share of addresses
with no digits, and the share beginning with a house number. **Every one of them is
`f(France) / rows(France)` with `rows(France) = 0` — that is 0/0, UNDEFINED.**

I am explicitly **declining to publish "France dig5 = 0" or "France digit rate = 0%"** as
measured values. Such a figure asserts that 0 France rows lacked a standalone 5-digit number,
when the truth is that **no France rows were observed at all**. Reading a zero-denominator
artifact as a rate is *precisely* the error behind the retracted "100% of France rows resolve a
state" figure, which was a `test_source1`-only denominator (259,452 rows = **15.3119%** of
1,694,445 France test rows) presented as a France-wide rate.

> ### ⚠️ THE TRAP
> **Any France rate computed over a train-file France denominator is meaningless.**
> If you are handed a France *train* statistic, check the denominator first. A train file
> cannot produce one. France digit / postcode / state rates must be quoted from
> `test_s1/s2/s3`, never from a train file, and always with the sub-file named.

---

## 2. HEADLINE 2 (THE REAL SUBSTANCE) — s3 INVERTS THE STATE REPRESENTATION, AND IT DOES SO IN **OPPOSITE** DIRECTIONS FOR THE TWO COUNTRIES

This is what I was asked to quantify, and it is **larger and stranger than recorded**.
D118 measured the **India** direction only. The s3 shift is **bidirectional and
country-opposite**.

### 2.1 India: s1/s2 write the state in FULL, s3 writes the 2-LETTER CODE

`addr_tokens["India"]`: 36 self-map codes (`ap`…`an`) vs 29 unambiguous state head-words.
Rates are token **occurrences per 1,000 India rows** (build_profile counts occurrences, never rows).

| file | India rows | self-map **code** occ | code /1k | state **word** occ | word /1k | code:word |
|---|---|---|---|---|---|---|
| `train_s1` | 883,188 | 11,089 | 12.56 | 540,052 | 611.48 | 0.021 |
| `train_s2` | 2,017,799 | 19,558 | 9.69 | 910,115 | 451.04 | 0.021 |
| **`train_s3`** | **2,115,547** | **1,449,612** | **685.22** | **109,730** | **51.87** | **13.21** |
| `test_s1` | 809,986 | 10,175 | 12.56 | 495,614 | 611.88 | 0.021 |
| `test_s2` | 2,312,565 | 22,897 | 9.90 | 1,050,557 | 454.28 | 0.022 |
| **`test_s3`** | **2,405,000** | **1,675,500** | **696.67** | **111,759** | **46.47** | **14.99** |

Spot checks, `train_s3` India: `mh` = **321,405** (151.93/1k) vs `maharashtra` = **24,074**
(11.38/1k). In `train_s1`: `mh` = 2,099 (2.38/1k) vs `maharashtra` = **192,382** (217.83/1k).
`dl` and `tn` are **not in the top 4000** in any s1/s2 file (India floors: s1 = 182, s2 = 394)
and are **201,584** and **104,459** in `train_s3`. **The inversion is CONFIRMED on my own
numbers, independently of D118.** Kinds present: 17/36 (s1), 16/36 (s2), **27/36 (s3)**.

### 2.2 US: s1/s2 write the state as a 2-LETTER CODE, s3 writes it in FULL — **the reverse**

This is the part D118 does not cover, and it is unambiguous. 51 US self-map codes vs 40 full
state names (`alabama`…`wyoming`, all literal `US_STATES` keys).

| file | US rows | self-map **code** occ | code /1k | state **word** occ | word /1k | code:word |
|---|---|---|---|---|---|---|
| `train_s1` | 1,323,633 | 1,359,620 | 1,027.19 | 38,124 | 28.80 | 35.66 |
| `train_s2` | 3,016,817 | 3,002,591 | 995.28 | 80,883 | 26.81 | 37.13 |
| **`train_s3`** | **3,170,056** | **280,424** | **88.46** | **2,494,884** | **787.02** | **0.112** |
| `test_s1` | 663,106 | 680,728 | 1,026.57 | 19,188 | 28.94 | 35.48 |
| `test_s2` | 1,873,330 | 1,876,297 | 1,002.65 | 50,448 | 26.96 | 37.19 |
| **`test_s3`** | **1,945,701** | **154,358** | **79.33** | **1,557,020** | **800.24** | **0.099** |

Cleanest single token pair, `train_s3` US: `texas` = **294,385** (92.86/1k) against
`tx` = **15,282** (4.82/1k). In `train_s1` it is inverted ~40×: `tx` = 133,224 (100.65/1k)
against `texas` = **713** (0.54/1k). Corroborated by `ny`/`new` (`ny` 77.32 → 3.66 per 1k;
`new` 10.30 → 88.07 per 1k, i.e. s3 writes "New York") and `ca`/`california`
(28.25 → 1.32 and 0.43 → 26.36 per 1k).

**Conclusion (CONFIRMED):** `s3` writes **Indian** states as bare 2-letter codes and **US**
states as full names. Source 3 is not "shorter addresses" — it is a *different geography
encoding* whose direction depends on the country. A "s3 is compressed" intuition is
wrong for the US.

### 2.3 CORRECTION TO D118's headline — 98.00% is an India-only statistic

D118's "98.00% of self-map key mass (3,125,112 of 3,188,831) is in s3" is **correct but
scoped to `IN_STATES` only, and the scope was not stated as a limit.** `US_STATES` gets the
*same* loop (`normalize.py:252-254` iterates `for _m in (US_STATES, IN_STATES)`) and runs
the **other way**.

| map | total self-map occ (6 files) | occ in `s3` files | s3 share |
|---|---|---|---|
| `IN_STATES` | 3,188,831 | 3,125,112 | **98.00%** |
| `US_STATES` | 7,354,018 | 434,782 | **5.91%** |
| **combined** | **10,542,849** | **3,559,894** | **33.77%** |

The pooled 33.77% is a meaningless average of two opposite effects.

### 2.4 THE NUMBER THAT MATTERS — exposure is **10,044,348**, not 3,125,112

The stake is the mass sitting in files that **write 2-letter codes**, because those are the
files where a state-lookup failure has **no blocking-key fallback** (§3).

| | occ |
|---|---|
| India `s3` (codes) | 3,125,112 |
| US `s1`+`s2`+`test_s1`+`test_s2` (codes) | 6,919,236 |
| **Total mass in code-writing files** | **10,044,348** |
| Total self-map mass, all files | 10,542,849 |
| **Share in code-writing files** | **95.27%** |

(6,919,236 = 1,359,620 + 3,002,591 + 680,728 + 1,876,297. 10,044,348 + 498,501 = 10,542,849,
where the residual 498,501 = US `s3` 434,782 + India s1/s2/test_s1/test_s2 63,719.)

D118 sized the risk at the India half. **The true exposure is 3.21× larger** (10,044,348 ÷
3,125,112 = 3.2141). A
"tidy up the redundant bare-code keys" refactor of `normalize.py:252-254` would silently
delete the state feature for **10,044,348 address occurrences** across **both** countries.

---

## 3. FINDING CANDIDATE (CONFIRMED, structural) — s3/s1-s2 state resolution is a **field-only** path with **no blocking-key fallback**, and the two directions fail differently

`keys.py:39-43`:
```python
toks = (pl.col("atoks").str.split(" ").list.eval(pl.element().filter(~pl.element().is_in(ADDR_GENERIC) & (pl.element() != ""))) ...)
nums = toks.list.eval(pl.element().filter(pl.element().str.contains(r"^\d+$"))).list.head(MAX_NUM)
alph = (toks.list.eval(pl.element().filter(~pl.element().str.contains(r"^\d+$") & (pl.element().str.len_chars() >= 3)))
        .list.eval(...sort_by(len,desc)...).list.head(MAX_ALPHA))
```

**All 36 `IN_STATES` and all 51 `US_STATES` canonical values are exactly 2 characters**
(verified programmatically against the dict literals at `normalize.py:216-242`: zero codes
with `len < 3`). `keys.py:42` requires `str.len_chars() >= 3` to enter `alph`; `keys.py:41`
requires `^\d+$` to enter `nums`. A 2-letter code satisfies **neither**. I also confirmed
**no** state code collides with any of the 62 `ADDR_GENERIC` entries (`keys.py:14-19`), so
nothing is rescued by the earlier filter — the `len >= 3` gate is the sole blocker.

**So: a 2-letter state token can never become a blocking key of any kind (0, 1, 2, 3 or 4).**
The only surviving carrier is the `state` field, which reaches the model solely through
`state_eq` (`features.py:114`, `tri("q_state","s_state")`) — a 3-way {-1,0,1} feature, **not**
a retrieval route.

**This cuts BOTH ways, and the profile cannot see it.** `normalize.py:333-335` requires the
*whole comma-component* to equal the key:
```python
if ck in smap:
    state = smap[ck]
    continue          # <-- component is CONSUMED, never appended to `toks`
```
On success the component is **removed from `atoks` entirely** — the code never reaches
`keys.py` at all, and blocking was never meant to carry it. On failure the component falls
through into `toks`… and is then killed by `len >= 3`. Either way no blocking key exists.
**INFERENCE (marked as such):** s3 Indian state resolution therefore rests **entirely** on the
`state` field with **zero** blocking redundancy, whereas `train_s1`/`train_s2` — which write
`maharashtra`, a 10-character token — *would* retain a length-≥3 blocking token even if the
dictionary missed. That is a genuine **structural asymmetry between s3 and s1/s2**.

Label: **CONFIRMED as a code-path asymmetry; its scoring impact is NOT measurable from this
profile** (`build_profile.py` flattens components via `ADDR_SPLIT`, so I cannot count how many
`mh` occurrences sit in a standalone component versus inside a longer one). **No change
recommended:** the dictionary is correct, the corpus is closed, and adding a code-based
blocking key would add mass with no measured recall problem to solve.

### 3.1 The asymmetry runs the other way for the US — s3 US is the *robust* case

`train_s3` US writes `texas` (5 chars), a length-≥3 token that **would** survive `keys.py:42`
if the state lookup failed. So US s3 has a blocking fallback that India s3 lacks.
**India s3 is the brittle case; US s3 is the safe one.** Recorded so a future refactor does not
"normalise" the US side and throw the fallback away.


## 4. DIGIT STRUCTURE OF `train_s3` (the literal question, for the two countries that exist)

All figures from `by_country[...].{num_digits,dig5,dig6,alpha_only_addr,addr_empty,has_comma}`.
Per `build_profile.py`: `num_digits` counts digits in the **ADDRESS only** (line 114, on `ba`);
`dig5`/`dig6` are **lookaround-guarded** (`(?<!\d)\d{5}(?!\d)`, lines 29-30, 115-116) so a
digit inside a longer run does not count; **every field is a total across the slice**, so rates
are derived by dividing by `rows`. `alpha_only_addr` (line 117-118) is the count of rows whose
address contains **no digit at all** — this is the "share of addresses with no digits" the
order asks for.

| Metric | `train_s3` US (rows 3,170,056) | `train_s3` India (rows 2,115,547) | `train_s3` **France** |
|---|---|---|---|
| `num_digits` | 12,614,249 → **3.9792**/row | 7,979,194 → **3.7717**/row | **UNDEFINED (0/0)** |
| `dig5` | 341,738 → **0.107802**/row | 22,317 → **0.010549**/row | **UNDEFINED (0/0)** |
| `dig6` | 42,321 → **0.013350**/row | 410 → **0.000194**/row | **UNDEFINED (0/0)** |
| `alpha_only_addr` (no digits) | 164,957 → **5.2036%** | 145,433 → **6.8745%** | **UNDEFINED (0/0)** |
| `addr_empty` | 110,968 → **3.5005%** | 64,948 → **3.0700%** | **UNDEFINED (0/0)** |
| `has_comma` | 3,059,088 → 96.4995% | 2,050,598 → 96.9299% | **UNDEFINED (0/0)** |
| `addr_chars`/row | 121,873,446 → **38.45** | 125,040,524 → **59.11** | **UNDEFINED (0/0)** |
| `has_digit_name` | 199,652 → 6.2981% | 71,195 → 3.3653% | **UNDEFINED (0/0)** |

### 4.1 Does the US-side pin asymmetry hold for `train_s3`? **YES — `s3` groups with `s2`, not `s1`.**

The order flags this as already covered and asks only that I state whether it holds for s3. It does.

| | US `train_s1` | US `train_s2` | US `train_s3` | s3/s1 ratio |
|---|---|---|---|---|
| `dig6`/row | **0.001251** | 0.013931 | **0.013350** | **10.671×** |
| `dig5`/row | 0.109844 | 0.107340 | **0.107802** | 0.981× |
| `dig5`/row (India) | 0.003021 | 0.011378 | **0.010549** | 3.492× |

**`train_s3` US `dig6`/row is 0.013350, i.e. 10.67× the `train_s1` value and within 4.2% of
`train_s2`'s 0.013931.** The source-1 six-digit deficit is a **source-1-only** artefact and
`s3` does **not** reproduce it. `dig5`/row is flat across all three US train sources
(0.1098 / 0.1073 / 0.1078), so the 5-digit house-number structure is **stable across sources**;
it is only the 6-digit/pin structure that shifts. This is a one-line confirmation, not a
re-derivation of the mechanism.

`pin` remains structurally ineligible for US rows by construction (`normalize.py:337`
requires `country == "India"`), so the 42,321 `dig6` occurrences in `train_s3` US are dead
regardless. `pin_eq` is already settled as dead (0.0% of rows) and I do not re-test it.

### 4.2 Pure-digit token ladder — where the digits actually live

`addr_tokens`, pure-digit tokens only (`^\d+$`), **token occurrences** (not rows), and only
the **top 4000 bag**, so these are **lower bounds**:

| Length | `train_s3` US kinds / occ | `train_s3` India kinds / occ |
|---|---|---|
| 1 | 10 / 303,604 | 10 / 928,554 |
| 2 | 100 / 416,680 | 100 / 1,150,128 |
| 3 | 676 / 1,016,608 | 807 / 987,378 |
| 4 | 454 / 300,876 | 36 / 21,338 |
| **5** | **0 / 0** | **0 / 0** |
| **6** | **0 / 0** | **0 / 0** |

The `train_s3` floors are **US 440, India 362**. A **hard cliff at length 5** in the listed bag.
That is *not* evidence of absence — `dig5` records 341,738 US occurrences — it means the
5-digit values are **too numerous and too dispersed** to survive a top-4000 cut. Lower bound on
distinct 5-digit values: `ceil(341738 / 440)` = **777** for US, `ceil(22317 / 362)` = **62** for
India. Shape of a house/street-number field, not a postcode — consistent with the settled
"no country has a postal field" conclusion. The `pin` guard should be left alone.

---


## 5. FRENCH-SHAPED FUSED NUMBER+SUFFIX FORMS — the real `bis` phenomenon is **test-only**; in `train_s3` it is an **India `1a`/`1b` flat-designation phenomenon**, not a French one

The order asks whether any French-shaped fused form (`5bis`, `12b`) exists in `train_s3` for US
or India. Answer: **no `bis` form at all in any train file; the 2-char fused forms that do exist
in `train_s3` are Indian, and they are 12× more frequent than the US ones.**

Regex `^\d+[a-z]{1,4}$` over `addr_tokens` (top-4000 bag; **occurrences**, not rows):

| file | country | fused kinds | total occ | of which **len 2** (blocked by `keys.py:42`) | of which **len ≥3** (survives as `alph`) |
|---|---|---|---|---|---|
| `train_s1` | US | 120 | 88,017 | 7 / 2,011 | 113 / 86,006 |
| `train_s1` | India | 85 | 192,672 | 33 / 26,554 | 52 / 166,118 |
| `train_s2` | US | 110 | 113,327 | 0 / 0 | 110 / 113,327 |
| `train_s2` | India | 88 | 374,034 | 31 / 51,732 | 57 / 322,302 |
| **`train_s3`** | **US** | **112** | **125,050** | **7 / 3,987** | **105 / 121,063** |
| **`train_s3`** | **India** | **87** | **307,654** | **33 / 49,331** | **54 / 258,323** |

Sum check `train_s3` India: 49,331 + 258,323 = 307,654 ✓. Sum check `train_s3` US:
3,987 + 121,063 = 125,050 ✓.

**`bis` — the French suffix — is ABSENT from every train file.** A `bis` substring search over
`addr_tokens` in all six train slices returns only proper nouns: `bismarck` 1,780 / `bishop` 594
(US `train_s3`), `bishrakh` 908 / `biswas` 577 / `bishnupur` 545 (India `train_s3`). **Zero
occurrences of `bis` as a bare token and zero of `\d+bis` in any train file, any country.**
The `<N>bis` form is **France-test-only**: `test_s2` has 10 such kinds / 765 occ
(`2bis` 104, `1bis` 92, `13bis` 89 …) and `test_s3` has 9 / 640 (`2bis` 92, `1bis` 89 …),
alongside a bare `bis` token at 20,062 (`test_s2`) and 21,000 (`test_s3`). `test_s1` France has
**0** — the form arrives with source 2, exactly like the department-vs-region shift.

**What the `train_s3` fused mass actually is.** Splitting by digits-before-suffix:
`1digit+suffix` vs `2digit+suffix` — `train_s3` India **262,207** occ (42 kinds) vs **45,447**
occ (45 kinds); `train_s3` US **43,572** (29 kinds) vs **80,519** (81 kinds). The Indian
1-digit forms are dominated by ordinals (`2nd` 53,858, `1st` 50,756, `3rd` 37,164 …) plus
**flat designations `1a` 7,350, `2a` 4,698, `1b` 3,378, `3a` 3,263, `2b` 2,961, `4a` 2,472,
`5a` 2,202, `3b` 2,056 …** — Indian society-block naming, not French `bis`.

**Consequence for `keys.py` — CONFIRMED, small, and shared with s1/s2 (not an s3 novelty).**
`1a` / `1b` / `2a` are **2 characters**. `keys.py:42` requires `len >= 3` for `alph`, and
`keys.py:41` requires `^\d+$` for `nums`, so a 2-char fused token satisfies **neither**:
the **house number is dropped from blocking `nums` entirely** (D127's finding) *and* the fused
token is dropped from `alph`. The `train_s3` India exposure is **49,331 occurrences = 23.32 per
1k India rows**; US is **3,987 = 1.26 per 1k**. Note `s1` India is *larger* (26,554 occ) and
`s2` is *larger still* (51,732 occ), so this is a **pre-existing, source-independent** issue and
**not** something `s3` introduced. `1a`/`2a`/`1b`/`2b` are the top items; the bulk of the
len-≥3 mass is `1st`–`9th`, which `ADDR_CANON_COMMON:184` already canonicalises.

**No action.** The magnitude is ~23/1k rows on one country, the affected forms are low-entropy
(`1a`, `1b` recur across thousands of unrelated addresses), and adding them as blocking keys
would mostly add collisions. Reported because the order asked and because the honest answer is
*the French form is not in train at all*.

---


## 6. IS THE HOUSE NUMBER A RELIABLE MATCHING KEY OR A NOISE SOURCE?

**Verdict: a genuinely reliable key for the ~94% of rows that have one, and a designed-in
noise source for exactly the rows the decoy post-filter targets.**

**What the data shows (train_s3).**
- Only **5.2036%** of US and **6.8745%** of India `train_s3` rows have a digit-free address
  (`alpha_only_addr`), so **~93–95% of rows carry a usable number** and `keys.py:41` puts the
  first three (`MAX_NUM = 3`) into `nums`, feeding the kind-2 address-number×word key.
- The numbers are **short and highly concentrated**: the pure-digit ladder (§4.2) is dominated
  by lengths 1–3. `train_s3` US has 676 distinct 3-digit values carrying 1,016,608 occurrences
  — a mean of ~1,504 rows per value. Indian numbers are shorter still (L1 928,554 + L2 1,150,128
  vs US 303,604 + 416,680).
- **Concentration is the problem, not presence.** `keys.py:23` sets `CAPS = {… 2: 30 …}` with
  `S1_MAXCAP = 300`, dropping keys whose Source-1 frequency exceeds the cap. A 1–3 digit
  number in a country this size clears the bar only when genuinely rare. **The cap is doing
  the discriminating**, so the number contributes a low-entropy signal that survives only in
  the tail.

**What I am inferring (marked INFERENCE).** `decoy_postfilter.py:5-9` states the generator
builds lookalike decoys by shifting the house number by a fixed **positive** offset
(+1,+2,+3,+4,+5,+7,+9,+11,+13,+21), and that **79.8%** of same-name US decoys carry one of
those offsets versus **0.126%** of true US pairs (0.299% India) for the strong offsets. If that
holds, the house number is **simultaneously the strongest available signal and the deliberate
decoy channel** — which is why a dedicated asymmetric post-filter exists. I did **not**
re-measure 79.8%/0.126%; they are quoted from the module docstring and **the profile cannot
verify them** (it holds no pair-level data).

**Practical reading:** house number is a **high-precision, low-recall** key. Trustworthy when it
*agrees*; near-worthless when it *disagrees by a small positive amount*. Treat a small positive
number delta as evidence of a decoy, not a typo. `num1_eq` (`features.py:114`) is a 3-way
feature, so a missing number is distinguishable from a mismatch.

**Position of the house number relative to the street word — GAP, not measured.** **The profile
discards it.** The address is lowercased, split on `[,;]` (lines 31, 126) and fed to a
`Counter` (line 127) — a bag of tokens with **no order and no component boundaries retained**.
It cannot distinguish "175 Boulevard …" from "… 175", and cannot count leading-number rows.
**This is a structural gap in the profile, not in the data**, and I am not estimating it.
D126/D127 measured component *order* and found it not a problem; that is a different claim and
I do not restate it as a measurement of this slice.

---

## 7. FRANCE SUPPLEMENT — from the TEST files only, clearly labelled

> **This section is `test_*`, NOT `train_*`.** It answers the "what are the digits" question
> for France at all. **It must never be cited as a `train_s3` France figure.**

| Metric | France `test_s1` (259,452) | France `test_s2` (703,378) | France `test_s3` (731,615) |
|---|---|---|---|
| `num_digits`/row | 510,818 → **1.9688** | 1,360,296 → **1.9339** | 1,415,333 → **1.9345** |
| `dig5`/row | 1,082 → **0.004170** | 3,613 → **0.005137** | 3,909 → **0.005343** |
| `dig6`/row | 34 → 0.000131 | 130 → 0.000185 | 115 → 0.000157 |
| `alpha_only_addr` (no digits) | 1,089 → **0.4197%** | 26,656 → **3.7897%** | 26,857 → **3.6709%** |
| `addr_empty` | 0 → 0.0000% | 21,537 → 3.0619% | 21,541 → 2.9443% |
| `has_comma` | 100.0000% | 96.9125% | 97.0348% |
| `has_digit_name` | 2,002 → 0.7716% | 7,818 → 1.1115% | 8,094 → 1.1063% |

France `num_digits`/row is **1.93–1.97 versus US 3.98 / India 3.77 in `train_s3`** — roughly
**half** the density, consistent with a short leading house number then a long French street
name. The **0.42%** no-digit figure quoted in the order is **`test_s1` only**; s2/s3 is
**3.67–3.79%**, about 9× higher. **Quoting "0.42% of France rows have no digits" without
naming `test_s1` repeats the denominator error this slice exists to prevent.** That s1/s2/s3
gap mirrors the US `alpha_only_addr` gap (0.0001% → 6.12% → 5.20%), so it is a **source
artefact, not a France fact**.

**France 2-char address tokens** (`test_s3`): bag 4,993,261 occ, 190 two-char kinds,
1,293,935 occ = **25.91%**, led by `de` 410,366, `la` 188,981, `du` 94,953, `no` 35,742,
`av` 27,570. Per D119 these function words are largely consumed by the whole-component
`continue` at `normalize.py:333-335` and are behaviourally harmless. **None is a state code** —
France has no 2-letter state representation, so **§3's asymmetry does not arise for France**.

---


## 8. GAPS — stated, not estimated

1. **Component ORDER and house-number position** — not in the profile at all
   (`build_profile.py:126-127` flattens to a `Counter`). No leading-number count is possible.
2. **Whether a state code sits in a standalone comma-component** — not measurable, same
   flattening. This is what bounds §3's magnitude claim.
3. **Pair-level decoy statistics (79.8% / 0.126% / 0.299%)** — quoted from
   `decoy_postfilter.py:5-9`, **not re-measured**; the profile holds no pair data.
4. **Values below the top-4000 cut** — floors: `train_s1` 182, `train_s2` 394, `train_s3` 362,
   `test_s1` 166, `test_s2` 459, `test_s3` 416. Every "absent" here means **"not in the top
   4000"**, never "does not occur".
5. **All token figures are OCCURRENCES, never rows.** A token appearing twice in one address
   counts twice.
6. **Row-level digit co-occurrence** (e.g. addresses with both a 5- and a 6-digit number) is not
   collected. `dig5`/`dig6` are independent totals and **must not be added**.

---

## 9. BOTTOM LINE

- **The France slice of `train_s3` is EMPTY: 0 of 5,285,603 rows, share exactly 0.** Every
  France rate over a train-file France denominator is **0/0 = UNDEFINED**; publishing it as
  "0%" is the retracted-figure error. This work order's premise is confirmed invalid.
- **The real substance is a bidirectional s3 geography-encoding shift.** India s1/s2 write the
  state in full, s3 writes a 2-letter code; **the US does the exact opposite** — s1/s2 write a
  2-letter code (1,027/1k rows) and s3 writes the full name (787/1k rows). D118 covered only
  the India direction.
- **The self-map loop (`normalize.py:252-254`) is load-bearing for 10,044,348 occurrences, not
  3,125,112** — 3.21× the recorded figure, because the US half runs the other way. Do not
  "tidy up the bare-code keys". **CONFIRMED, no action.**
- **A 2-letter state code can never be a blocking key** (`keys.py:42`, `len >= 3`), so state
  resolution is field-only. India s3 has no fallback; US s3 (`texas`, 5 chars) does.
  Structural asymmetry **CONFIRMED**; scoring impact **not measurable** here. **No action.**
- **The US `dig6`/row pin asymmetry holds for `s3`**: 0.013350 in `train_s3` vs 0.001251 in
  `train_s1` (10.67×), tracking `s2`. `dig5`/row is flat across all three US train sources.
- **The French `bis` fused form does not exist in any train file.** The `train_s3` fused mass is
  Indian `1a`/`1b` flat designations (49,331 len-2 occurrences = 23.32/1k rows) — a
  pre-existing `keys.py:41` issue, **larger in s1/s2 than in s3**, so not an s3 regression.
  **No action.**
- **"No defect found" is the honest result for the France slice.** The useful results here are
  the bidirectional state-encoding finding and the 3.21× correction to the self-map exposure.

**Deliverable:** this file. **Sidecar:** `analysis_out/findings/P033_France_train_s3_digits.json`.

---
