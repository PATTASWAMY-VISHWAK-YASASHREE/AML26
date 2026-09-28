# P031 — [France] train_s1: digit structure and address-number behaviour

**Status: COMPLETE. Headline is negative for the stated premise; the pin thread is CLOSED.**
**Agent:** b10 · **Family:** A-profile · **Profile input:** `analysis_out/profile/train_s1.json`
(plus `train_s2/s3`, `test_s1/s2/s3` for the cross-source contrast)
**Source of every number below:** the compact profile JSON. **No raw TSV was opened.**

> **Filename note.** `analysis_out/tasks/P031.json` names the deliverable
> `P031_France_train_s1_numeric.md`. My work order instructs
> `P031_France_train_s1_digits.md` as the EXACT required name. I follow the work
> order. Flagging the mismatch rather than silently picking one.

---

## 1. HEADLINE — THE FRANCE SLICE OF train_s1 IS EMPTY

**There is no `France` key in `train_s1.json`.** `build_profile.py:62` builds
`country_rows` as a `Counter` and line 142 emits `dict(country_rows)` — a country
with zero rows produces **no key at all**, not a zero entry.

| Quantity | Value |
|---|---|
| `train_s1.json` → `rows` | **2,206,821** |
| `country_rows["US"]` | 1,323,633 |
| `country_rows["India"]` | 883,188 |
| 1,323,633 + 883,188 | **2,206,821 = `rows`, exactly** |
| `country_rows` keys present | `US`, `India` — **no `France`** |
| **France rows in train_s1** | **0** |
| **France share of train_s1** | **0 / 2,206,821 = 0.000000% — exactly 0** |

The sum closing on `rows` to the row is the denominator check the brief demands:
the country breakdown is complete, so France is **absent**, not hiding inside a
bucket. Confirmed identically for `train_s2` (5,034,616) and `train_s3` (5,285,603).

### 1.1 Every France rate in this work order is UNDEFINED, not 0%

The order asks for France digit-in-name rate, standalone 5-digit and 6-digit
counts, digit distribution, and what the numbers represent. **Every one of these
is `f(France) / rows(France)` with `rows(France) = 0` — that is 0/0, UNDEFINED.**

I am explicitly **declining** to publish "France dig5 = 0" or "France digit rate =
0%" as *measured* values. Such a figure asserts that 0 France rows lacked a
standalone 5-digit number, when the truth is that **no France rows were observed
at all**. Reading a zero-denominator artifact as a rate is the exact error that
produced the retracted "100% of France rows resolve a state" figure.

> ### ⚠️ THE TRAP
> **Any France rate computed against a train-file France denominator is meaningless.**
> If you are handed a France train statistic, check the denominator first. A train
> file cannot produce one.

## 2. THE REAL SUBSTANCE: `pin` IS DEAD CODE EVERYWHERE

The pin question was left open by the REFUTED-1 correction. I traced the full
consumer chain in `_upstream/src/` and it resolves cleanly.

**The guard** — `normalize.py:336-340`:
```python
for n in NUM_RE.findall(c):
    if len(n) == 6 and country == "India":
        pin = n
    n2 = n.lstrip("0") or "0"
    nums.append(n2)          # <-- OUTSIDE the guard: every number, every country
```

**`pin` feeds exactly two places**, both of which I measured:

1. `prep.py:17` → `pin` column → `keys.py:44,58`: the string `"pin"+pin` becomes
   one extra blocking key in the kind-0 (name×address) family.
2. `features.py:100,114` → `pin_eq`, one ternary feature. Already established
   (fleet brief) as **0.0% of rows**.

**But every number — any length, any country — is appended to `nums` regardless**
(`normalize.py:340`), and `nums` independently reaches:
- `prep.py:16` → `anums` → `features.py:98-99` → `qm`/`sm`/`qm1`/`sm1` →
  **`num1_eq`, `m_inter`, `m_cont`**;
- `atoks` (`normalize.py:345-346`, `t.isdigit()`) → `keys.py:39-41`, where
  `nums` = tokens matching `^\d+$` → **`kind-2` (AA) blocking keys** (`keys.py:63,65`).

So a 5-digit or 6-digit number in **any** country is **already** a model feature
**and** already a blocking key, with or without the `pin` guard.

### 2.1 Verdict, stated plainly

> ### **`pin` is a strictly redundant duplicate of `anums`. It is dead code in every country, for two independent reasons.**
>
> **(a) It is never populated for US or France** — the guard requires
> `country == "India"`. By construction `pin == ""` for 100% of US and France rows.
>
> **(b) It is essentially never populated for India either.** It fires only on a
> standalone 6-digit number. Measured India `dig6` across **all six** profile files:
>
> | File | India rows | `dig6` | `dig6`/row |
> |---|---|---|---|
> | train_s1 | 883,188 | 182 | 0.000206 |
> | train_s2 | 2,017,799 | 459 | 0.000227 |
> | train_s3 | 2,115,547 | 410 | 0.000194 |
> | test_s1 | 809,986 | 159 | 0.000196 |
> | test_s2 | 2,312,565 | 500 | 0.000216 |
> | test_s3 | 2,405,000 | 527 | 0.000219 |
> | **total** | **10,544,085** | **2,237** | **0.000212 (0.0212%)** |
>
> Indian PINs are 6 digits, yet only **0.0212%** of Indian addresses contain a
> standalone 6-digit number. The dataset's Indian addresses simply do not carry
> their PIN code. So `pin` is non-empty on ~2 rows in 10,000.
>
> **(c) And even where it does fire, it adds nothing** — the same 6-digit string is
> already in `anums` and already a blocking key via `nums`.

**Therefore the US-source-1 "pin gap" is a non-issue, and the entire pin thread
should be closed. Leave the guard alone.**


## 3. THE US-SIDE ASYMMETRY, QUANTIFIED PER SOURCE FILE

The brief flagged this as already-covered and told me not to merely re-derive it.
I measured it precisely anyway, because the *asymmetry is real* even though its
*pin interpretation is wrong* — and the measurement disambiguates the verdict.

**US `dig6`/row — the asymmetry is large and consistent:**

| File | rows | `dig6` | `dig6`/row |
|---|---|---|---|
| train_s1 | 1,323,633 | 1,656 | **0.001251** |
| train_s2 | 3,016,817 | 42,026 | **0.013931** |
| train_s3 | 3,170,056 | 42,321 | **0.013350** |
| test_s1 | 663,106 | 793 | **0.001196** |
| test_s2 | 1,871,330 | 26,757 | **0.014298** |
| test_s3 | 1,945,701 | 26,760 | **0.013753** |

**s2/s1 ratio = 11.13× (train), 11.96× (test).** Reproduced independently in train
and test, so it is a real property of how the sources were built.

**US `dig5`/row is FLAT across the same files** — 0.10984 / 0.10734 / 0.10780
(train) and 0.10979 / 0.10971 / 0.11014 (test). So the asymmetry is **isolated to
6 digits and does not touch 5 digits.** Since `pin` is the only consumer keyed on
6-digit length, and `pin` is redundant anyway (§2), **the asymmetry costs nothing.**

## 4. WHAT THE NUMBERS ACTUALLY ARE — VERIFYING THE "HOUSE NUMBERS, NOT ZIPs" CLAIM

The earlier finding said US 5-digit values are house numbers, not ZIPs. **I confirm
it, by a stronger route than the one recorded** (which used a positional pattern I
cannot measure — see §6).

The test is purely a counting argument, and it is decisive. `addr_tokens` is the top
4000 per country, and I read the actual cutoff:

| File / country | rank-4000 cutoff | **5-digit tokens ≥ cutoff** | 6-digit tokens ≥ cutoff |
|---|---|---|---|
| train_s1 US | 201 | **0** | **0** |
| train_s2 US | 407 | **0** | **0** |
| train_s3 US | 440 | **0** | **0** |
| test_s1 US | 101 | **0** | **0** |
| test_s2 US | 258 | **0** | **0** |
| test_s3 US | 274 | **0** | **0** |
| all India files | 166–459 | **0** | **0** |
| France (test_s1/2/3) | 23 / 58 / 60 | **10 / 10 / 10** | 0 |

**US has 145,393 standalone 5-digit numbers in train_s1, and not one 5-digit token
reaches 201 occurrences.** A US ZIP field would be present in essentially every US
address and is strongly concentrated (real US ZIP distributions put thousands of
addresses in the leading ZIPs). If US 5-digit values were ZIPs, the top-4000 list
would be saturated with them. It contains **zero**.

Working the arithmetic the long way: 145,393 occurrences with a per-value maximum
below 201 requires **≥ ⌈145,393 / 201⌉ = 724 distinct values** — a long tail, the
signature of house numbers, not a bounded postal vocabulary.

**CONFIRMED: US 5-digit values are house numbers. The US address has no ZIP field.**
This is consistent with the already-settled "no country has a postal field."

## 5. THE DIGIT LADDER (train_s1) — the two countries that actually exist

Occurrences of pure-digit address tokens **within the top-4000 bag**
(`addr_tokens`, TOKEN_RE = `[a-z0-9]+`; these are token occurrences, not rows):

| Length | US distinct / occurrences | India distinct / occurrences |
|---|---|---|
| 1 digit | 10 / **98,826** | 10 / **438,791** |
| 2 digit | 92 / **173,412** | 100 / **486,462** |
| 3 digit | 647 / **484,247** | 522 / **372,735** |
| 4 digit | 553 / **182,654** | 35 / **11,746** |
| **5 digit** | **0 / 0** | **0 / 0** |
| **6 digit** | **0 / 0** | **0 / 0** |


## 6. GAPS — stated, not estimated

- **"How many France addresses BEGIN with a house number" — NOT MEASURABLE.**
  `build_profile.py:126-127` splits components then `TOKEN_RE.findall`s each one
  and `Counter.update`s them. **Position is destroyed.** `addr_tokens` is an
  unordered multiset; it cannot say whether a number precedes or follows the street
  word. There is no positional field in the profile. **GAP — not estimated.**
- **"Does the house number sit in a consistent position relative to the street
  word" — NOT MEASURABLE**, same reason.
- Consequently the earlier "'STATE 5-digit' pattern occurs zero times" claim is
  **not reproducible from the profile** — it is positional. I do not repeat it as
  evidence. §4 replaces it with a counting argument that does not need position.
- **France train digit structure of any kind: gap**, unfixable from the provided files.
- `addr_tokens`/`name_tokens` are the **top 4000 per country AND periodically
  pruned** (`prune()` drops `count <= 1` every 8 chunks), so token counts are
  **lower bounds**. The ladder in §5 is a lower bound; the 5-digit/6-digit zeros are
  "no value reached the cutoff," not "no value exists."

## 7. NEW DEFECT FOUND — the US source-1 digit asymmetry is far larger than the pin one

This is the one genuinely new result. It is **not** the pin thread (that is closed),
and it is **not** a France finding.

**US addresses containing NO digit at all** (`alpha_only_addr` / `rows`):

| File | rows | `alpha_only_addr` | rate |
|---|---|---|---|
| **train_s1** | 1,323,633 | **1** | **0.0001%** |
| train_s2 | 3,016,817 | 184,605 | **6.1192%** |
| train_s3 | 3,170,056 | 164,957 | **5.2036%** |
| **test_s1** | 663,106 | **1** | **0.0002%** |
| test_s2 | 1,871,330 | 93,584 | **5.0009%** |
| test_s3 | 1,945,701 | 82,467 | **4.2384%** |

**Exactly one digit-free US address in source-1, versus ~5–6% in sources 2/3** —
a ~**60,000×** gap, reproduced independently in train and test.

This is the same source-1 vs source-2/3 discontinuity as the `dig6` gap (§3), but
**five orders of magnitude larger**, and unlike `dig6` it is not confined to
6-digit values: `num_digits`/row is 4.1667 (train_s1) vs 3.7514 (train_s2).

**Why it matters (INFERENCE, marked as such):** source-1 is the blocking index
(`run_blocking.py:31` — `{split}_s1.parquet` is the index, `s2`+`s3` are the
queries). An index row with no address number generates **no `kind-2` (AA) key at
all** (`keys.py:63` explodes `nums`, which is empty). At 0.0001% that is a
non-issue for the index. But the **5–6% of source-2/3 rows that are digit-free
cannot be retrieved by an address-number key at all** — they depend entirely on the
name-only key families (kinds 1, 3, 4). Direction of impact: this is a
**recall** asymmetry in query-side retrieval, not a precision problem.

**This is a description, not a recommended change.** The brief's evidence standard
forbids manufacturing a recommendation to look productive, and I have not measured
whether `CAPS_NOADDR` (`keys.py:25`) already covers these rows adequately. I flag
it as measured and unexplained: **source-1 and source-2/3 US addresses were
apparently built by different pipelines**, and nothing in the code or the profile
documents that.

## 8. WHAT I DID NOT DO

- Did not re-derive anything in the brief's ALREADY SETTLED list (no postal field;
  `pin_eq`/`alt_tset` dead; mapping completeness; FR blocking caps; component
  order; the RETRACTED French function-word finding).
- Did not invent a France train distribution.
- Did not modify `_upstream/` or the dataset. Both READ-ONLY throughout.

Both countries show a smooth **decay past 4 digits and a hard cliff at 5** — the
shape of a house/street-number field, not a postcode. India's 4-digit band collapses
to 35 distinct values (11,746 occ) while US keeps 553 (182,654 occ): Indian numbers
are overwhelmingly 1–2 digits, US numbers run to 3–4.

**Derived per-country rates for train_s1** (rate = field / `rows`, per `build_profile.py`):

| Metric | US | India | France |
|---|---|---|---|
| rows | 1,323,633 | 883,188 | **0 — UNDEFINED** |
| `dig5` / row | **0.109838** | **0.003020** | undefined |
| `dig6` / row | **0.001251** | **0.000206** | undefined |
| `num_digits` / row (address only) | **4.1667** | **3.8571** | undefined |
| `alpha_only_addr` / row (no digits at all) | **0.0001%** (1 row) | **8.7225%** | undefined |
| `has_digit_name` / row (**digit-in-name rate**) | **2.6060%** | **0.1235%** | undefined |
