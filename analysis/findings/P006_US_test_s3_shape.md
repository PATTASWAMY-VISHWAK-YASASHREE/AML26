# P006 — [US] test_s3: shape, null rates, length distribution

> **REVISION 2 — two headline claims from revision 1 are RETRACTED below.**
> Both were measured against the raw file and are false. Sections 6 and 9 are
> new; everything else stands. See §6 and §9 for the numbers and the scripts
> (`check_null_placeholder.py`, `check_us_state.py`) that produced them.

Source of record: `analysis_out/profile/test_s3.json` (`split=test`, `source=3`).
No raw `*.tsv` was opened. Every number below is a named profile field or
arithmetic on named fields. Field semantics were pinned by reading
`build_profile.py` (lines 79–136) before quoting anything. `_upstream/src/normalize.py`
was read read-only and imported read-only to demonstrate mechanism on **synthetic
strings only** (`p006_mech.py`).

## Headline

The US slice of `test_source3` is **1,945,701 rows, 38.2837% of the 5,082,316-row
file**, and it is clean on every integrity axis the profiler collects: **zero**
empty names, **zero** malformed `entity_id` prefixes, and a name-length histogram
that sums *exactly* to the row count. It is more than large enough to conclude
from (every rate below is pinned to ±0.034pp at 95%).

This slice closes the P001–P006 shape series (train_s1, train_s2, train_s3,
test_s1, test_s2, test_s3). The useful results are:

1. **RETRACTED — the `null` placeholder does NOT double the null rate.**
   Revision 1 claimed a literal `null` leaves a row with "no usable address" and
   that the effective US null rate is 5.6470% rather than 2.8430%. **False.**
   Streaming all 1,945,701 US rows: **zero** rows have `null` as their entire
   address. It is always a single *component* of an otherwise complete address,
   and **100.00% of those rows (72,639) still yield a usable address** from the
   real normalizer. The profiler's `addr_empty = 2.8430%` is **correct as
   published**; there is no 2× understatement. See §6.
2. **`test_s3` US writes states as full names; `test_s2` uses abbreviations.**
   The full-name-to-abbreviation token ratio is **12.66 in test_s3** but
   **0.04 in test_s2**. Confirmed in revision 1 and still correct. The concern
   it raised — that this might break state extraction — is now **measured and
   refuted**: state resolves for **100.0000% of non-empty US rows**, zero
   exceptions. See §7 and §9.
3. **Refutation (new, not previously tested): the state-spelling convention does
   not cause a train/test distribution shift.** US source 3 is full-name
   dominant in **both** `train_s3` (11.23) and `test_s3` (12.66), so train and
   test agree. Worth stating explicitly, because the source-2-vs-3 split looks
   alarming until you check both sides.


## Findings

### 1. Shape and share of file

| Quantity | Value | Field / arithmetic |
|---|---|---|
| Rows in file | 5,082,316 | `rows` |
| US rows | 1,945,701 | `by_country.US.rows` |
| India rows | 2,405,000 | `country_rows.India` |
| France rows | 731,615 | `country_rows.France` |
| **US share of file** | **38.2837%** | 1,945,701 / 5,082,316 = 0.382837 |
| India share | 47.3209% | 2,405,000 / 5,082,316 = 0.473209 |
| France share | 14.3953% | 731,615 / 5,082,316 = 0.143953 |
| Countries present | `US`, `India`, `France` | `country_rows` keys |
| Columns | `entity_id, business_name, business_address, country` | `cols` |

**Invariant 1 (holds):** `country_rows` sums to `rows` —
2,405,000 + 731,615 + 1,945,701 = 5,082,316. No country is hidden, and the
three `by_country[*].rows` values independently agree with `country_rows`.

### 2. Null / integrity rates (all ÷ `by_country.US.rows` = 1,945,701)

| Field | Count | Rate | Arithmetic |
|---|---|---|---|
| `name_empty` | **0** | **0.0000%** | exact zero |
| `addr_empty` | 55,317 | **2.8430%** | 55317/1945701 = 0.028430 |
| `prefix_bad` | **0** | **0.0000%** | exact zero |
| `has_comma` | 1,890,384 | 97.1570% | 1890384/1945701 |
| `has_digit_name` | 118,172 | **6.0735%** | 118172/1945701 = 0.060735 |
| `alpha_only_addr` | 82,467 | 4.2384% | 82467/1945701 = 0.042384 |

`prefix_bad = 0` is non-vacuous: `build_profile.py:94` evaluates
`eid.startswith(f"S{src}-")` per row with `src=3`, so 0/1,945,701 means the
`S3-` prefix is a valid partition key for **100%** of US rows in this file.
**No prefix repair is needed.**

### 3. Lengths

| Quantity | Value | Arithmetic |
|---|---|---|
| Mean name length | **24.6192** chars | `name_chars` 47,901,505 / 1,945,701 |
| Mean address length (all rows) | **38.8379** chars | `addr_chars` 75,566,854 / 1,945,701 |
| Mean address length (non-empty only) | 39.9743 | 75,566,854 / 1,890,384 |
| Mean name tokens/row | 3.7230 | `name_tokens` 7,243,924 / 1,945,701 |
| Address digits/row | 4.0601 | `num_digits` 7,899,714 / 1,945,701 |
| Address digit share of address chars | 10.4539% | 7,899,714 / 75,566,854 |
| `dig5` | 214,300 | 0.11014 occurrences/row |
| `dig6` | 26,760 | 0.01375 occurrences/row |

The two mean-address figures differ by exactly the null rate, because
`build_profile.py:102-103` adds `len(bn)`/`len(ba)` of the **stripped** string
and `len("") == 0`. `num_digits` counts digits in the **address only** (line
114); the digit-in-name signal is the separate `has_digit_name` field.

`dig5`/`dig6` are *occurrence* counts (`len(findall(...))`, lines 115–116), not
row counts, so they are reported as occurrences/row and never as row rates.

### 4. Name-length histogram (`len_hist`, bucketed by `len//10*10`)

| Name length | Rows | % of US rows | cumulative |
|---|---|---|---|
| 0–9 | 60,401 | 3.1043% | 3.1043% |
| 10–19 | 546,045 | 28.0642% | 31.1685% |
| 20–29 | 797,043 | 40.9643% | 72.1328% |
| 30–39 | 423,139 | 21.7474% | 93.8802% |
| 40–49 | 100,651 | 5.1730% | 99.0532% |
| 50–59 | 16,279 | 0.8367% | 99.8899% |
| 60–69 | 1,978 | 0.1017% | 99.9915% |
| 70–79 | 153 | 0.0079% | 99.9994% |
| 80–89 | 12 | 0.0006% | 100.0000% |
| **Total** | **1,945,701** | **100.0000%** | |

**Invariant 2 (holds, exactly):** `len_hist` sums to `rows`,
1,945,701 = 1,945,701. Because `name_empty = 0`, all 60,401 rows in the 0–9
bucket hold names of length 1–9, not empty strings.

**Consistency check on the histogram.** Summing the per-bucket minimum and
maximum possible `name_chars` (floor `10k`, ceiling `10k+9`) gives a bound of
[39,065,820 , 56,577,129] and the measured `name_chars` = 47,901,505 falls inside
it, implying a mean offset of +4.5411 chars above each bucket floor. Histogram
and character total are mutually consistent.

### 5. Is the slice large enough to conclude from? — Yes

n = 1,945,701. 95% binomial half-widths:

| Field | Rate | 95% CI half-width | Rows equivalent |
|---|---|---|---|
| `addr_empty` | 2.8430% | ±0.0234pp | ±454 |
| `has_digit_name` | 6.0735% | ±0.0336pp | ±652 |
| `has_comma` | 97.1570% | ±0.0234pp | ±454 |
| `alpha_only_addr` | 4.2384% | ±0.0283pp | ±550 |

The smallest effects discussed below (153 rows = 0.0079pp) are **~3× smaller
than the sampling error on `addr_empty`**, which is why they are only detectable
as *exact integer* discrepancies against structural identities rather than as
rate differences. The `null` finding is a different kind of claim — it is an
exact token count, not a rate difference, so sampling error does not apply to it.

### 6. RETRACTED — the `null` placeholder does NOT double the null rate

> **This section previously read "NEW FINDING — the literal `null` placeholder
> doubles the apparent null rate", claiming an effective US null rate of
> **5.6470%** against the published 2.8430%, and recommending that every
> published US/India null rate be restated. That claim is FALSE and is
> withdrawn. Recommendation 2 in the Recommendations section is withdrawn with
> it.**

The reasoning that produced it was sound but rested on an unverified premise:
that the `null` token marks a row whose address is *absent*. Revision 1 read the
token count out of `addr_tokens` and never checked what the surrounding string
actually looked like.

**Measured** (`check_null_placeholder.py`, streaming all 1,945,701 US rows of
`test_source3.tsv`, feeding each one to the real `normalize_address`):

| Quantity | Count | % of US rows |
|---|---:|---:|
| US rows scanned | 1,945,701 | 100.0000% |
| rows whose **entire address** is a null-ish literal | **0** | **0.0000%** |
| rows merely **containing** a null-ish component | 72,639 | 3.7333% |
| …of those, still yield non-empty `atoks` from the real normalizer | **72,639** | **100.0000%** |
| …of those, `atoks` came back empty | **0** | 0.0000% |

Sample rows (each keeps a street, a city and a state):

```
'868-872 Howell Rd, NULL, Hillsboro, Tennessee'
'314 Hillsdale Road, <NULL>, Columbia, Missouri'
'Anodver, Minnesota, 150th Ave, null'
'N/A, Charles City, 4805 Cattail Road, Virginia'
'33254 Vine Saint, Ohio, Eastlake, <NULL>'
```

**So `addr_empty = 55,317 (2.8430%)` is correct as published.** The `null`
placeholder is a *spurious component inside a populated address*, dropped
cleanly at `normalize.py:329`, not a missing address. There is no 2×
understatement, and no null rate needs restating.

The three observations from revision 1 that are **independent of the retracted
claim** and remain correct:

1. **Source 1 has no placeholder at all** — `null` = 0 in train_s1 and test_s1
   for every country, and both source-1 files have `addr_empty = 0` exactly.
   Source-1 addresses are always populated.
2. **France has exactly zero `null` tokens in all three test files.** The
   artefact belongs to the US/India generators. **The scored country is
   unaffected.**
3. **The placeholder is still absorbed correctly by the pipeline.**
   `normalize.py:329` skips any component equal to `null`/`<null>`/`n/a`/`na`/
   `none`; the table above shows `atoks` is never empty *because* of it and
   never polluted by it. `q_addr_empty` fires only for genuinely blank
   addresses. **The model is fine; the earlier measurement was not.**


### 7. NEW FINDING — US source 3 spells states in full, source 2 abbreviates

Comparing the top `addr_tokens` per file for the US slice makes the convention
change unmistakable:

| Rank | test_s2 US | count | | test_s3 US | count |
|---|---|---|---|---|---|
| 1 | `st` | 199,073 | | `st` | 199,668 |
| 2 | `rd` | 188,400 | | `rd` | 188,187 |
| 3 | **`tx`** | 182,000 | | **`texas`** | 183,097 |
| 4 | `dr` | 170,193 | | `dr` | 170,782 |
| 6 | **`ny`** | 139,340 | | **`new`** + **`york`** | 172,950 / 141,564 |
| 9 | **`nc`** | 131,272 | | **`carolina`** | 135,451 |
| 12 | **`oh`** | 115,700 | | **`ohio`** | 116,365 |

Aggregated over the whole corpus (full-name tokens vs abbreviation tokens):

| File | Country | full-name tokens | abbrev tokens | ratio |
|---|---|---|---|---|
| train_s1 | US | 48,923 | 1,245,542 | 0.04 |
| train_s2 | US | 102,838 | 2,751,481 | 0.04 |
| **train_s3** | **US** | **3,002,450** | **267,244** | **11.23** |
| test_s1 | US | 24,545 | 624,005 | 0.04 |
| test_s2 | US | 63,087 | 1,720,661 | 0.04 |
| **test_s3** | **US** | **1,871,526** | **147,824** | **12.66** |
| test_s1/2/3 | France | 670 / 1,583 / 1,703 | 377,681 / 565,531 / 607,066 | ≈0.00 |

The full-name set is the 39 single-word state names plus the seven sub-tokens
the profiler produces by splitting two-word names on the space (`carolina`,
`dakota`, `hampshire`, `jersey`, `mexico`, `york`, `island`); the abbreviation
set is the 53 two-letter keys. Both sets are defined in `build_p006_json.py`, so
these figures are reproducible rather than hand-counted.

**Refutation of an obvious worry (new, not previously tested).** The split looks
like a train/test distribution shift at first glance. It is not: US source 3 is
full-name dominant in **both** train (11.23) and test (12.66), and US sources
1–2 are abbreviation-dominant in both. Train and test agree within each source,
so **no train/test correction is warranted for this cause**. *This is why the
ratio is reported for all six files rather than only for the assigned slice.*

**What the split exposes.** `US_STATES` contains both spellings — `'texas'→'tx'`
and `'tx'→'tx'` (line 217 and the self-map loop at lines 252–254) — so the
dictionary is *not* the problem. The problem is `normalize.py:333`, which
requires a **whole** comma-component to equal a region key. A trailing ZIP fused
into that component defeats it for **both** spellings:

| Input (real `normalize_address`, US) | `state` |
|---|---|
| `'123 Main St, Austin, Texas'` | `'tx'` |
| `'123 Main St, Austin, Texas 78701'` | **`''`** |
| `'123 Main St, Austin, Texas, 78701'` | `'tx'` |
| `'123 Main St, Austin, TX 78701'` | **`''`** |
| `'123 Road, Raleigh, North Carolina 27601'` | **`''`** |
| `'123 Road, Raleigh, North Carolina, 27601'` | `'nc'` |
| `'1600 Pennsylvania Ave, Washington, DC 20500'` | `'wa'` |

The same failure for the abbreviation form is what shows the full-name
convention is a *revealer* rather than the cause. This is the **same
whole-component assumption** P005 documented for France's comma-less rows, now
with a second independent trigger.

**Its prevalence in this file is measured, and it is zero — see §9.** Streaming
all 1,945,701 US rows, 0 rows lost their state to a fused ZIP, and state
resolves for 100.00% of non-empty rows. The mechanism above is real but does
not fire on source-3 US data.

### 8. Comma identity in this slice (carried forward from P005)

`has_comma == rows − addr_empty` holds exactly here: 1,945,701 − 55,317 =
1,890,384 = `has_comma`, **0 exceptions**. This is the sixth consecutive US file
where the identity is exact, and it is why the P005 France leak (180 rows in
test_s2, 153 in test_s3) could be detected as an integer discrepancy at all.
This slice adds no new France evidence and does not change P005's bounds.

### 9. NEW (revision 2) — state extraction is MEASURED at 100.00% of non-empty rows

Revision 1 flagged the whole-component assumption at `normalize.py:333` as a
"real robustness hole" but, having no `n_comps` field, could only show it on
synthetic strings and left prevalence as a gap. I closed that gap by streaming
the raw file (`check_us_state.py`, one row at a time, `state_of()` replicating
lines 328–335 and **cross-validated against the shipped `normalize_address` on
400 real address shapes — 0 mismatches**).

| Quantity | Count | % of US rows |
|---|---:|---:|
| US rows streamed | 1,945,701 | 100.0000% |
| **state resolved** | **1,890,384** | **97.1570%** |
| unresolved, but a state token **was** present | **0** | **0.0000%** |
| unresolved, no state token at all (= `addr_empty`) | 55,317 | 2.8430% |
| rows with a component containing a state token | 1,600,456 | 82.26% |
| …of those, a ZIP in that same component | 78,696 | 4.04% |
| **…of those, state NOT emitted** | **0** | **0.0000%** |
| rows contributing ≥1 city component | 1,890,384 | 97.1570% |

**`state` resolution is exactly 100.0000% of non-empty rows
(1,890,384 / 1,890,384, zero exceptions).** The ZIP-in-state-component
fragility shown in §7 costs **exactly 0 rows in this file**, because source 3
writes the state as a clean standalone component. So:

- `state_eq` (`features.py:114`) is a **live** feature for US, unlike the
  refuted `pin_eq`. No dictionary or parser change is needed.
- The fragility is **real but dormant here**, not absent. It remains a latent
  risk for any future layout that fuses a ZIP into the state component.

**The 6 never-emitted codes are a data fact, not a dictionary gap.** 46 of the
52 codes in `US_STATES` appear. The absent six are `hi, mi, ms, nh, nj, pr`. I
probed the raw addresses for each full name to find out why:

| Full name | US addresses containing it | Example | Why no state |
|---|---:|---|---|
| `michigan` | 1,302 | `'43 Michigan Ave, Bristol, Connecticut'` | street name; real state is CT |
| `mississippi` | 189 | — | street/river name only |
| `new hampshire` | 183 | — | street name only |
| `new jersey` | 151 | — | street name only |
| `hawaii` | 18 | `'Hawaii Ave, Alamogordo, New Mexico'` | street name; real state is NM |
| `puerto rico` | 3 | — | effectively absent |

So `mi` is missing not because Michigan is unrepresented but because
**"Michigan" in this corpus is a street name, never a state value** — 1,302
occurrences, all `Michigan Ave` / `Michigan St`, each paired with a different
real state. **No dictionary entry is warranted**; adding one would add a key
that correctly matches nothing.

**Methodological note, because it nearly misled this document too.** My first
run of `check_us_state.py` reported "1,684 recoverable rows" and 93.3052% state
resolution. That was **my bug, not a finding**: I extracted `US_STATES` with
`ast.literal_eval`, which sees only the 52-entry literal and misses the runtime
self-map added at `normalize.py:252-254`, so every abbreviated-state row failed
to match. Replaying that loop changed the answer to 97.1570%. This is the same
lesson as the retraction in §6, and the same one already recorded in
`FRANCE_FINDINGS.md`: a reimplementation of upstream logic that was never
cross-validated against the shipped code will confidently produce a wrong
headline number. The cross-validation is what makes the result trustworthy.


## Interpretation (inference, marked as such)

1. **RETRACTED — the `null` placeholder is not a profiler blind spot.** Revision 1
   argued it made every published US/India null rate understated by ~2×.
   Measurement refutes this: 0 rows have `null` as the whole address, and
   **100.00%** of rows containing a null-ish component keep a usable address.
   The `null` placeholder is a **generator artefact producing a spurious
   component**, dropped cleanly by `normalize.py:329`; `q_addr_empty` and the
   `addr_empty` rates are all correct. **The model sees nothing wrong, and
   neither does the profiler.**
2. **The placeholder is a US/India generator artefact and does not touch the
   scored country.** France has exactly zero `null` tokens in all three test
   files. Nothing here requires action on the competition's scored rows.
3. **The state-spelling split is a per-source convention, symmetric across train
   and test.** *Inference* from the token pattern — the profile contains no
   generator information — but the practical consequence is firm: there is no
   train/test shift to correct for here. Revision 2 strengthens this: the split
   is also **harmless**, since state extraction is 100.00% in source 3.
4. **The fused state+ZIP component is a real but DORMANT robustness hole.**
   P005 attributed France's shortfall to comma-less addresses; this slice shows
   a second trigger of the *same* whole-component assumption. *Inference:* any
   layout that fuses a ZIP into the state component, or drops a comma, loses the
   state signal. **But revision 2 measured its prevalence in US test_s3 at
   exactly 0 rows**, so it is latent here, not active. *Inference on scope:* I
   have not measured test_s1 or test_s2, where the abbreviation style coexists
   with ZIPs, so I cannot claim the hole is absent corpus-wide.
5. **`state_eq` is a live feature for US — the opposite of `pin_eq`.**
   `state` is populated for 100.00% of non-empty US rows, so the state signal is
   fully available to the model. *Inference on impact:* I did not read the
   feature builder or the model, so I can say the feature is not dead, but not
   how much weight it carries.

## Gaps

- ~~**No row-level `has_null_addr` boolean.**~~ **CLOSED in revision 2.** This gap
  was cited in support of the retracted §6 claim. Streaming the raw file
  (`check_null_placeholder.py`) shows **0** rows whose entire address is a
  null-ish literal, and **100.00%** of the 72,639 rows containing a null-ish
  *component* still yield a usable address. The field would only tell us how
  many rows carry a spurious component, which is a **data-quality note about the
  generator, not a null-rate correction**. Downgraded from HIGH to LOW.
- **No `n_comps` field.** `build_profile.py:126` splits on `[,;]` only to feed
  the token counter and **discards the component count**. This remains the
  largest blind spot in the profile. Revision 2 worked around it for *this*
  slice by streaming the raw file (§9), but any future component-structure
  question still needs a 90-second scan rather than a profile lookup.
- ~~**No `state` / `city` / `region` field — so state resolution is only a
  bound.**~~ **PARTIALLY CLOSED in revision 2.** State resolution is now a
  **direct measurement** over all 1,945,701 US rows (§9), not a bound: 100.00%
  of non-empty rows, cross-validated against the shipped function. The profile
  still lacks the field, so this required a raw scan; and the equivalent
  France figure remains P005's bound, untouched here.
- **The full-name/abbreviation ratio is a proxy, not a row count.** The profiler
  splits multi-word state names on the space, so `north carolina` becomes
  `north` + `carolina`, and only `carolina` is in the full-name set. The ratio
  **undercounts** full-name mentions. It is used only to establish that the two
  conventions differ by >10×, which it does unambiguously.
- **No true-empty vs whitespace-only distinction.** The builder `.strip()`s
  before testing emptiness (lines 96–101), so `"   "` is already counted empty.
- **Token counters are top-4000 and pruned of hapax** (`prune`, line 45), so no
  vocabulary size, type-token ratio, or unique-business count is derivable.

- **REFUTED-1 (French postal codes discarded by the `pin` guard).** I did **not**
  re-derive it, and my evidence does **not** support it. US `dig5`/row here is
  0.11014, consistent with the ~0.110 figure for US source-2, so US rows are
  rich in 5-digit numbers. The pin guard is a real code defect whose impact is
  on **US source-1 / India**, not France.
- **REFUTED-2 (`FR_REGIONS` too thin ⇒ no usable state signal).** I did not
  re-derive the core claim and **agree** with it. Re-measured dictionary sizes
  on the real module (`p006_mech.py`): `FR_REGIONS` 14 entries / 4 values,
  `US_STATES` 104 / 52, `IN_STATES` 86 / 37. This slice adds no new France state
  evidence and does not improve on P005's 99.9744% / 99.9791% bounds.

## Recommendations

1. **MEDIUM (downgraded from HIGH) — Add `n_comps` to `build_profile.py`:**
   `n_comps = len([c for c in ba.split(',') if c.strip()])`. *Confidence:
   CONFIRMED* that it is a gap; one-line streaming counter at negligible cost.
   *Effect:* pure diagnostic. It is the only way to answer component-structure
   questions from the profile instead of re-streaming a 480 MB file. The
   `has_null_addr` half of revision 1's recommendation is **withdrawn** (see
   recommendation 2).
2. **~~HIGH — Restate every published US/India null rate as the effective
   figure (5.6470%, not 2.8430%).~~ WITHDRAWN — the premise is false.**
   Measured: **0** US rows have `null` as their entire address, and **100.00%**
   of the 72,639 rows containing a null-ish *component* still yield a usable
   address. The published `addr_empty` rates are **correct as they stand**;
   there is nothing to restate. Acting on the withdrawn version would have
   introduced a 2× error into every null-handling decision. *Confidence:
   CONFIRMED by measurement* (`check_null_placeholder.py`).
3. **NONE — Do not change `normalize.py` to handle the literal `null`.** It is
   already absorbed at line 329 and via `ADDR_CANON_COMMON`, and `q_addr_empty`
   fires correctly. There is no defect here, and a "fix" would be churn.
   *Confidence: CONFIRMED* (executed the real module on all 72,639 rows).
4. **NONE for this slice (downgraded from LOW) — do not add trailing-ZIP
   tolerance yet.** The mechanism is real (`'Austin, Texas 78701'` → `state=''`)
   but revision 2 **measured its prevalence at exactly 0 rows** in US test_s3:
   state resolves for 100.00% of non-empty rows, and 0 of the 78,696 rows with
   a ZIP in the state component lost their state. *Confidence: CONFIRMED for
   this slice.* Do this only if a follow-up scan of test_s1/test_s2 — where the
   abbreviation style coexists with ZIPs — shows real losses. It is insurance,
   not a fix, and **no leaderboard move should be expected**.
5. **NONE — No normalisation-dictionary entry is warranted from this slice.**
   `US_STATES` already carries both spellings of all 52 states, and the 6 codes
   never emitted (`hi, mi, ms, nh, nj, pr`) are absent because those names occur
   only as **street names** in this corpus (1,302 `Michigan Ave` rows and so
   on), not because the dictionary is missing them. Adding entries would create
   keys that correctly match nothing. *Confidence: CONFIRMED* by raw-address
   probe (§9).
6. **LOW — Record the state-spelling convention as a per-source fact** (source 3
   full names, sources 1–2 abbreviations, consistent across train and test) so
   future agents do not mistake it for a train/test distribution shift. **Also
   record that US state extraction is healthy** (100.00% of non-empty rows,
   §9) so nobody re-raises it as an open defect.
7. **LOW — Re-run `check_us_state.py` against test_s1 and test_s2.** This is the
   single open question from this work order. The harness is written and
   cross-validated; only the s1/s2 numbers are missing. Those files use the
   abbreviation style *and* carry ZIPs, so they are where the fused
   state+ZIP component (if it exists anywhere) would actually appear.
   *Confidence: harness CONFIRMED; the s1/s2 prevalence is unmeasured.*






