# P032 - [France] train_s2: digit structure and address-number behaviour

**Status: COMPLETE. The France slice of `train_s2` is EMPTY; the `pin` thread is CLOSED.**
**Agent:** c01 | **Family:** A-profile | **Profile input:** `analysis_out/profile/train_s2.json`
(plus `train_s1/s3`, `test_s1/s2/s3` for the cross-source contrast and the France supplement)
**Source of every number below:** the compact profile JSON. **No raw TSV was opened.**

> **Filename note.** `analysis_out/tasks/P032.json` names the deliverable
> `P032_France_train_s2_numeric.md`. My work order names
> `P032_France_train_s2_digits.md` as the EXACT required filename. I follow the work
> order. Flagging the mismatch rather than silently picking one.

---

## 1. HEADLINE - THE FRANCE SLICE OF train_s2 IS EMPTY

**There is no `France` key in `train_s2.json`.** `build_profile.py:62` builds
`country_rows` as a `Counter`; line 142 emits `dict(country_rows)`. A country with
zero rows produces **no key at all**, not a zero entry.

| Quantity | Value |
|---|---|
| `train_s2.json` -> `rows` | **5,034,616** |
| `country_rows["US"]` | 3,016,817 |
| `country_rows["India"]` | 2,017,799 |
| 3,016,817 + 2,017,799 | **5,034,616 - equals `rows`, exactly** |
| `country_rows` keys present | `US`, `India` - **no `France`** |
| `by_country` keys present | `US`, `India` - **no `France`** |
| **France rows in train_s2** | **0** |
| **France share of train_s2** | **0 / 5,034,616 = 0.000000% - exactly 0** |

The parts summing to `rows` to the row is the denominator check the brief demands:
the country breakdown is **complete**, so France is **absent**, not hiding inside a
bucket. This holds for **all three train files**: `train_s1` (2,206,821) and
`train_s3` (5,285,603) also contain only `US` and `India`.

### 1.1 Every France rate in this work order is UNDEFINED, not 0%

The order asks for the France digit-in-name rate, standalone 5-digit and 6-digit
counts, digit distribution, and what the numbers represent. **Every one is
`f(France) / rows(France)` with `rows(France) = 0` - that is 0/0, UNDEFINED.**

I am explicitly **declining to publish "France dig5 = 0" or "France digit rate =
0%"** as measured values. Such a figure asserts that 0 France rows lacked a
standalone 5-digit number, when the truth is that **no France rows were observed at
all**. Reading a zero-denominator artifact as a rate is the exact error behind the
retracted "100% of France rows resolve a state" figure.

> ### THE TRAP
> **Any France rate computed over a train-file France denominator is meaningless.**
> If you are handed a France *train* statistic, check the denominator first.
> A train file cannot produce one. France `state`-resolve / digit / postcode rates
> must be quoted from `test_s1/s2/s3`, never from a train file.

France does exist - **only in the test files** (`test_s1` 259,452 / `test_s2`
703,378 / `test_s3` 731,615). Section 5 gives a clearly-labelled test-side
supplement so the "what are the numbers" question is not left blank, but it is
**not** a train_s2 measurement and must never be labelled as one.

## 2. VERDICT ON `pin` - DEAD CODE EVERYWHERE EXCEPT ~0.02% OF INDIA

`normalize.py:336-340`:
```python
for n in NUM_RE.findall(c):          # NUM_RE = r"\d+", on the RAW component
    if len(n) == 6 and country == "India":
        pin = n
    n2 = n.lstrip("0") or "0"
    nums.append(n2)                  # <-- OUTSIDE the guard: every number, every country
```

**(a) Never populated for US or France - by construction.** The guard requires
`country == "India"`, so `pin == ""` for **100%** of US and France rows. France
`dig6` does exist in test (130 occurrences in test_s2) and is **structurally
ineligible** to become a `pin`. This is a design choice, not a bug - see (c).

**(b) Essentially never populated for India either.** India `dig6`, train_s2:
**459** occurrences over **2,017,799** rows = **0.000227/row = 0.0227%** - and
`dig6` counts **occurrences, not rows**, so **<= 459 rows (0.0227% of India,
0.0091% of all 5,034,616 train_s2 rows)** can have a non-empty `pin`. Indian PIN
codes are 6 digits, yet essentially no Indian address in this dataset carries one.

**(c) And where it does fire it is redundant.** `pin` reaches only two consumers:
- `prep.py:17` -> `keys.py:44,58`: `"pin"+pin` becomes one **kind-0 (NA)** key.
- `features.py:100,114` -> `pin_eq`, one ternary feature - already established as
  **0.0% of rows** (fleet brief).

But the same 6-digit string is **already** in `nums` (line 340, unconditional), and
`nums` -> `prep.py:16` `anums` -> `features.py:98-99,113-114` -> `qm`/`sm`/
`m_inter`/`num1_eq`; and a standalone 6-digit token also survives `t.isdigit()`
(`normalize.py:345`) into `atoks` -> `keys.py:41` (`^\d+$`) -> **kind-2 (AA)
blocking keys**.

> ### **`pin` is a strictly redundant duplicate of `anums`. Dead code in all three
> countries: structurally for US/France, and at 0.02% coverage for India.**
> **The US source-1 "pin gap" therefore costs nothing. Close the thread.
> Leave the guard alone.**

## 3. US train_s2 - ARE THE 5-DIGIT VALUES ZIPs? NO. THEY ARE HOUSE NUMBERS.

The earlier positional claim ("the 'STATE 5-digit' pattern occurs zero times") is
**not reproducible from the profile** - it is a position pattern, and
`build_profile.py:126-127` destroys position. I use a counting argument instead,
which needs no position.

`train_s2` US has **323,824** standalone 5-digit numbers. The `addr_tokens`
top-4000 bag for US train_s2 has cutoff **407** and contains **zero** 5-digit pure
tokens (also zero 6-digit). So every 5-digit value occurs **<= 406** times,
requiring **>= ceil(323,824 / 406) = 798 distinct values** - a long tail.

A US ZIP field present in essentially every US address, with a strongly
concentrated real distribution, would saturate the top-4000 list. It contains
**none**.

> **CONFIRMED: US 5-digit values are house numbers. The US address has no ZIP field.**
> Consistent with the settled "no country has a postal field."

**Digit ladder, `train_s2` `addr_tokens`, pure-digit tokens** (token
**occurrences**, not rows; top-4000 bag only, so **lower bounds**):

| Length | US distinct / occ | India distinct / occ |
|---|---|---|
| 1 | 9 / 183,570 | 10 / 979,507 |
| 2 | 100 / 359,171 | 100 / 1,184,521 |
| 3 | 680 / 860,320 | 764 / 982,956 |
| 4 | 424 / 256,829 | **29 / 18,741** |
| **5** | **0 / 0** | **0 / 0** |
| **6** | **0 / 0** | **0 / 0** |

Both countries show a **hard cliff at 5** - the shape of a house/street-number
field, not a postcode. India's 4-digit band collapses to 29 distinct values while
US keeps 424: Indian numbers are overwhelmingly 1-2 digits, US numbers run to 3-4.

## 4. FULL train_s2 DIGIT STRUCTURE (the two countries that exist)

Rates = field / `rows`, per `build_profile.py` (totals across the slice, not averages).

| Metric | US (rows 3,016,817) | India (rows 2,017,799) | France |
|---|---|---|---|
| `dig5` / row | 323,824 -> **0.107340** (10.7340%) | 22,959 -> **0.011378** (1.1378%) | **UNDEFINED (0 rows)** |
| `dig6` / row | 42,026 -> **0.013931** (1.3931%) | 459 -> **0.000227** (0.0227%) | **UNDEFINED (0 rows)** |
| `num_digits` / row (ADDRESS only) | 11,317,142 -> **3.751352** | 8,234,897 -> **4.081128** | **UNDEFINED** |
| `alpha_only_addr` / row (**no digits at all**) | 184,605 -> **6.1192%** | 117,369 -> **5.8167%** | **UNDEFINED** |
| `has_digit_name` / row (**digit-in-name rate**) | 193,041 -> **6.3988%** | 62,595 -> **3.1021%** | **UNDEFINED** |
| `has_comma` / row | 2,905,696 -> **96.3166%** | 1,959,953 -> **97.1332%** | **UNDEFINED** |
| `addr_empty` / row | 111,121 -> 3.6834% | 57,846 -> 2.8668% | **UNDEFINED** |
| `addr_chars` / row | 95,123,286 -> 31.5310 | 137,606,434 -> **68.1963** | **UNDEFINED** |

`has_digit_name` counts rows whose **business_name** contains a digit; `num_digits`
counts digits in the **address only**. Indian addresses are 2.16x longer in
characters than US ones yet carry **more** digits per row (4.08 vs 3.75) - long,
wordy, and dominated by 1-2 digit numbers (section 3).

## 5. FRANCE SUPPLEMENT - from TEST files only, clearly labelled

> **This section is `test_s2`, NOT `train_s2`.** It exists only so the "what are the
> numbers" question is answered. It must not be cited as a train_s2 France figure.

| Metric | France `test_s2` (rows 703,378) |
|---|---|
| `dig5` / row | 3,613 -> **0.005137** |
| `dig6` / row | 130 -> **0.000185** |
| `num_digits` / row | 1,360,296 -> **1.9339** |
| `alpha_only_addr` / row | 26,656 -> **3.7897%** |

France `num_digits`/row is **1.93 vs US 3.75 / India 4.08** - roughly **half** the
US density, consistent with French addresses leading with a short house number and
then a long street name.

**A nuance that qualifies - but does not overturn - "no country has a postal
field".** France's 5-digit pure tokens number exactly **10 distinct values**, and
they are **identical in all three test files**:

`59000 / 59100 / 59200 / 59800 / 44300 / 44000 / 44100 / 44600 / 33000 / 62100`

These are **department code x 1000** (59 = Nord/Lille, 44 = Loire-Atlantique/
Nantes, 33 = Gironde/Bordeaux, 62 = Pas-de-Calais/Calais) - postcode-shaped, landing
on exactly the cities the brief names as dominant. But they are only **10 values at
<= 220 occurrences each**, i.e. **0.5137% of France test_s2 rows** (3,613/703,378),
and they are **inline in the address string, not a dedicated column** - which is what
"no postal *field*" actually asserts. **INFERENCE, marked as such:** the French
address does carry a sparse, heavily-truncated postcode remnant. It is far too thin
to be a matching key and does not reopen the postcode thread. Flagging it because
it qualifies a settled statement.

## 6. THE FUSED NUMBER+SUFFIX CASE - `keys.py:41` DROPS THE HOUSE NUMBER

`_non_alnum = r"[^a-z0-9]+"` (`normalize.py:269`) splits on **non-alphanumeric**,
so a letter suffix is **not** a separator: `5bis`, `12b`, `1a` survive as **single
tokens**. Confirmed by D127. So:

- `keys.py:41` - `nums = toks.filter(^\d+$)` - **drops them.** `5bis` is not
  `^\d+$`, so it produces **no kind-2 (AA) blocking key**.
- **But they are NOT lost to the model.** `normalize.py:336` runs `NUM_RE = r"\d+"`
  on the **raw component, before tokenisation**, so `5bis` -> `"5"` -> `nums` ->
  `anums` -> `qm`/`sm`/`num1_eq` features. (`t.isdigit()` at line 345 is False for
  `5bis`, so the token survives unchanged in `atoks`; only `keys.py:41` rejects it.)

**So the defect is a BLOCKING-only loss, not a total loss.** Precise statement:
a fused house number retains its model features but loses its address-number
blocking key. This refines D127's framing.

**Quantified for `train_s2`** (`addr_tokens` top-4000, digit-leading tokens
`^\d+[a-z]{1,4}$`):

| Country | fused tokens | occ | ORDINAL (`st/nd/rd/th`) | HOUSE-NUM SUFFIX (`1a`,`2bis`,...) |
|---|---|---|---|---|
| US | 110 | 113,327 | **110 / 113,327 (100%)** | **0 / 0** |
| India | 88 | 374,034 | 30 / 303,940 | **57 / 69,612** |

India check: 30 + 57 + 1 (`100ft`) = **88** tokens; 303,940 + 69,612 + 482 =
**374,034** occ.

- **US: every fused form is a street ordinal** (`4th`, `16th`, `2st`, `3th`) - a
  street name, **not a house number**. Losing the blocking key costs **nothing**:
  the street word is still an `alph` token. US fused occ = 3.7565% of US rows.
- **India: 57 tokens / 69,612 occurrences = 3.4499% of India rows** are genuine
  house-number suffixes (`1a` 7,743 / `2a` 4,967 / `1b` 3,880 / `3a` 3,465 /
  `2b` 3,061 / `4a` 2,528 / `5a` 2,295 / `3b` 2,068). **This is a real,
  quantifiable blocking-key loss for Indian addresses.**
- **Note:** `1st`,`2nd`,`3rd`,`4th`,`5th` are additionally in `ADDR_GENERIC`
  (`keys.py:18`) and are dropped even earlier at `keys.py:39`. Ordinals `6th`+ are
  not in `ADDR_GENERIC` and are dropped by the `^\d+$` filter instead. Either
  way: no AA key.

**France:** 39 fused digit-leading tokens in `test_s2` (`1er` 795 / `2eme` 279 /
`3eme` 139 / `1b` 119 / `2bis` 104 / `6b` 99 / `2b` 99 / `5b` 97 / `1bis` 92 /
`13bis` 89 / `12b` 82 = 3,913 occ) - so the fused form **does** occur in French
addresses and France **would** be affected by the same blocking loss. **But France
has zero train rows, so this is a test-side observation only and cannot be sized
against any train denominator.**

## 7. NEW FINDING - the **India** source-1 vs source-2/3 `dig5` asymmetry is 3.8x, not the US `dig6` one

The brief flagged a US-side asymmetry (`dig6` 0.001 in source-1 vs 0.013-0.014 in
source-2/3). **India has the same discontinuity at 5 digits, larger in relative
terms, and completely unflagged.**

| File | India rows | `dig5` | `dig5`/row |
|---|---|---|---|
| train_s1 | 883,188 | 2,668 | **0.003021** |
| **train_s2** | 2,017,799 | 22,959 | **0.011378** - **3.7663x s1** |
| train_s3 | 2,115,547 | 22,317 | **0.010549** - 3.4919x s1 |
| test_s1 | 809,986 | 2,305 | **0.002846** |
| test_s2 | 2,312,565 | 25,554 | **0.011050** - **3.8826x s1** |
| test_s3 | 2,405,000 | 24,462 | **0.010171** - 3.5738x s1 |

**Reproduced independently in train and test**, so it is a property of how the
sources were built, not a sampling fluke - the same signature as the US `dig6` gap
and the US `alpha_only_addr` gap (P031 section 7). Indian source-1 addresses
essentially never carry a standalone 5-digit number; source-2/3 Indian addresses
carry ~3.8x more.

**What the numbers are: GAP, not estimated.** I cannot determine from the profile
whether these are Indian survey/plot numbers, PIN fragments, or house numbers.
India train_s2 has 22,959 5-digit occurrences with a top-4000 cutoff of 394 and
**zero** 5-digit tokens, requiring **>= ceil(22,959 / 393) = 59 distinct values** -
a long tail, house-number-like, **not** a bounded PIN vocabulary (Indian PINs are
6-digit, and 6-digit tokens also fail to reach the cutoff). **INFERENCE:** more
likely survey/plot or house numbers than postcodes.

**Direction of impact (INFERENCE, marked as such):** source-1 is the blocking index
(`run_blocking.py:31`); s2/s3 are queries. A 5-digit number in a query row produces
a kind-2 key the index may not contain - **a query-side recall asymmetry**. I have
**not** measured whether the name-only key families (kinds 1, 3, 4) already cover
these rows, so this is a description, **not a recommended change**.

## 8. GAPS - stated, not estimated

- **"How many France addresses begin with a house number" - NOT MEASURABLE, and for
  train_s2 doubly so.** `build_profile.py:126-127` splits on `[,;]` then
  `TOKEN_RE.findall`s each component and `Counter.update`s it. **Position is
  destroyed**; `addr_tokens` is an unordered multiset. There is **no positional
  field in the profile at all.** Even for US/India, whether the number precedes or
  follows the street word is a **GAP**. Not estimated.
- **"Is the house number in a consistent position relative to the street word" -
  NOT MEASURABLE.** Same reason.
- **"Is the house number a reliable matching key or a noise source" - only
  partially answerable.** Cross-pair reliability needs pair-level data the profile
  does not contain. What I can say: the value is **high-entropy** (>= 798 distinct US
  values, section 3) and a kind-2 key is `num XOR (alph-hash // 8)` (`keys.py:65`),
  so it fires only when **both** the number and a >=3-char street word agree.
  **INFERENCE:** that makes it a *selective* key, not a noisy one - but this is a
  code-reading inference, **not a measurement**, and is flagged as such.
- **France train digit structure of any kind: permanent gap.** No train rows exist.
- `addr_tokens`/`name_tokens` are the **top 4000 per country AND periodically
  pruned** (`build_profile.py:45-48` drops `count <= 1` every 8 chunks), so all token
  counts are **lower bounds**. The ladders in sections 3 and 6 are lower bounds; the
  5-/6-digit zeros mean **"no value reached the cutoff," not "no value exists."**
- `dig5`/`dig6` are **lookaround-guarded** (`build_profile.py:29-30`), so a digit
  inside a longer run does not count. `dig6` counts **occurrences**, not rows.

## 9. WHAT I DID NOT DO

- Did not re-derive anything in the brief's ALREADY SETTLED list (no postal field;
  `pin_eq`/`alt_tset` dead; mapping completeness; FR blocking caps; component
  order; the RETRACTED French function-word finding).
- Did not invent a France train distribution, and did not publish any
  zero-denominator France rate.
- Did not modify `_upstream/` or the dataset. Both READ-ONLY throughout.
