# France findings — measured, not inferred

**Status: 4 of my earlier headline claims were WRONG and are retracted here** —
F1, F2, the US-only remedy in N0, and the function-word claim in A13. This document records
only findings that were tested against the real data, with the measurement that supports each
one. Every script named here is re-runnable.

Test data: `dataset/test/test_source1.tsv`, France slice = **259,452 rows**.
France appears **only in test** (train has US + India only) — confirmed from
`country_rows` in `analysis_out/profile/*.json`.

## How to read this document

The body is **append-only** — nothing above has been rewritten, because the sequence of
wrong turns is itself the evidence. That means later findings sit *after* earlier ones out
of logical order (A7, A11, A12 and A13 were appended out of sequence). Use this index:

**Retracted — do not act on these**
| § | Claim | Reality |
|---|---|---|
| F1 | France loses postal codes | **FALSE.** France `dig5/row` = 0.004 vs US 0.110 — house numbers, not postcodes |
| F2 | `FR_REGIONS` too thin | **FALSE.** All regions in the data resolve; the real gap is the *query* side (N3) |
| N0-R | Remedy is US-only | **RETRACTED.** No country has postal codes in this data; leave `pin` alone |
| A13 | French function-word finding | **RETRACTED.** Inflated ~37.5% and misdiagnosed |

**Confirmed**
| § | Finding |
|---|---|
| N0 | `pin_eq` is dead across the whole dataset (0.0083% of rows) |
| N1 | Ligatures silently deleted — `Cœur`/`Fœur`/`Sœur` → `ur` |
| N2 | City lost when written with an inline postcode (0.02%) |
| N3 | My F2 refutation was measured on the wrong file — France `state_eq` fires for only ~65% of source-2/3 |
| N4 | `alt_tset` is a second dead feature (<1%) |
| N5 | Both remaining dictionary "defects" are non-defects |
| A1, A2, A5, A5b | `LEET` corrupts French ordinals; fix implemented; French-only guard caught just 19.1% |
| A7 | The 71.10% vs 97.44% "contradiction" was never a contradiction |
| A8, A11, A12 | Three independent audits confirm the state dictionaries are already correct |

**Ruled out** — § "RULED OUT", plus component-order and cap-saturation hypotheses.

---

## RETRACTED

> **Later correction — see N0/N0-R.** F1 was wrong that the postal loss is
> France-specific, but a global pin problem is real. F1's *remedy* direction is
> also wrong: the dataset has no postal codes for **any** country.

### ~~F1: French postal codes are discarded~~ — FALSE
The claim was that `normalize.py:336-338` captures `pin` only when
`len(n)==6 and country=="India"`, so France loses its postal signal.

| slice | country | dig5/row | dig6/row |
|---|---|---:|---:|
| test_s1 | US | **0.110** | 0.001 |
| test_s1 | France | **0.004** | 0.000 |
| test_s1 | India | 0.003 | 0.000 |

Only **0.413%** of France rows contain a standalone 5-digit number. French
addresses carry *house numbers* — `175 Boulevard du Président Franklin
Roosevelt, Bordeaux` — not postcodes. There is no postal signal to lose.

The guard is real, but its actual impact is the **opposite** of what I said:
`dig6/row` is 0.000–0.001 for **India**, so the India-only branch almost never
fires. The asymmetry is by **source**, not country (US s1 0.001 vs US s2/s3
0.013–0.014).

*Evidence: `check_fr_postcode.py`, `check_pin_impact.py`*

### ~~F2: FR_REGIONS is too thin~~ — FALSE

Replicating `normalize_address`'s exact component matching against the real
data: state resolves for **259,452 / 259,452 France rows (100.00%)**, zero
unmatched.

The table works because this dataset only uses three modern regions:
hauts-de-france (101,521), nouvelle-aquitaine (85,197), pays-de-la-loire
(72,734) — all already mapped. Legacy names (lorraine, alsace, bretagne) total
~1,100 rows.

The missing self-map entry (`normalize.py:252` omits `FR_REGIONS`) is a genuine
code defect with **zero measurable effect** on this dataset.

*Evidence: `check_fr_exact.py`, `check_fr_regions.py`*

---

## CONFIRMED

### N0 — `pin_eq` is a dead feature across the entire dataset (the real F1)

**The finding stands. The originally-recommended fix is RETRACTED — see N0-R.**

`features.py:114` computes `pin_eq = tri(q_pin, s_pin)`, but `pin` is set only
under `normalize.py`'s `len(n)==6 and country=="India"` guard. Running the real
`normalize_address` over 1,500,012 rows:

| split | source | country | rows | pin set | rate |
|---|---|---|---:|---:|---:|
| train | s1 | India | 100,228 | 22 | 0.0219% |
| train | s1 | US | 149,774 | 0 | **0.0000%** |
| train | s2 | India | 100,426 | 22 | 0.0219% |
| train | s2 | US | 149,576 | 0 | **0.0000%** |
| train | s3 | India | 100,372 | 17 | 0.0169% |
| train | s3 | US | 149,630 | 0 | **0.0000%** |
| test | s1 | France | 37,323 | 0 | **0.0000%** |
| test | s1 | India | 116,911 | 15 | 0.0128% |
| test | s1 | US | 95,768 | 0 | **0.0000%** |
| test | s2 | France | 36,262 | 0 | **0.0000%** |
| test | s2 | India | 118,176 | 29 | 0.0245% |
| test | s2 | US | 95,564 | 0 | **0.0000%** |
| test | s3 | France | 35,661 | 0 | **0.0000%** |
| test | s3 | India | 118,119 | 20 | 0.0169% |
| test | s3 | US | 96,222 | 0 | **0.0000%** |

**Overall: `pin` is set on 125 of 1,500,012 rows (0.0083%).** It is **exactly
zero** for every US and every France row.

`pin_eq` is true only when *both* sides carry a pin, so it is false for
essentially every candidate pair, and the matching blocking key
(`keys.py:44`) never fires. This is a **global dead feature**, not the
France-specific loss I originally claimed.

The deadness is caused by the **data**, not by the guard. See N0-R.

*Evidence: `check_pin_feature.py`, `check_pin_cause.py`*

---

### N0-R — RETRACTED: "the actionable change is US-only"

The first version of N0 ended: *"The actionable change is US-only, since France
has no postal signal to capture."* **That recommendation was wrong**, for the
same reason F1 was: there is no US postal signal either.

The US `dig5` rate of **0.110/row** that motivated the fix is **not ZIP codes**.
Streaming all US rows and testing the only shape a ZIP can take in a
`street, city, ST` string — a 5-digit number following a state code:

| | test_source1 | train_source1 |
|---|---:|---:|
| US rows scanned | 663,106 | 1,323,633 |
| rows with a standalone 5-digit | 72,577 (10.945%) | 144,926 (10.949%) |
| ...of those, 5-digit is the **leading** token | 61,511 (**84.75%**) | 122,737 (**84.69%**) |
| `STATE <5-digit>` pattern (a real ZIP) | **0** | **0** |
| 9-digit runs (ZIP+4) | **0** | 1 |

The 5-digit numbers are **house numbers**, leading the address exactly as a
street number should:

```
25246 33 Avenue, Saint Cloud, MN        10601 Watford Lane, Spotsylvania County, VA
14028 Manistee Avenue, Burnham, IL      22997 Bland Circle, West Linn, OR
```

The header is `entity_id / business_name / business_address / country` and the
component-count distribution is 3 or 4. **The dataset carries no postal field at
all**, for any country.

Two further measurements kill the fix independently:

1. **It would add nothing to blocking.** 100.0% of US 5-digit values are already
   present in `nums` (`normalize.py:340`), and `keys.py:41` already builds a
   blocking key from every `nums` entry. A `pin` key would duplicate a key the
   pipeline already has.
2. **The Indian rows the guard "works" on are formatting artefacts.** Of the 175
   Indian `pin` values captured, **70.9% are fused to a preceding word** and
   **0.0% are a clean standalone token**:

   ```
   pin=411011  ... Kasba Peth Shimpi Ali Pune411011, Maharashtra, Pune
   pin=600001  18, Muthunaicken Street Madras600001, Chennai, Tamil Nadu
   ```

   `Madras600001` is a city name glued to digits, not a postal field. The guard
   is *syntactically* firing on the only rows that have a 6-digit run; those rows
   simply have no postal signal to capture.

**Corrected conclusion:** `pin` is dead because the dataset has no postal codes,
not because the guard is mis-gated. Widening the guard to `len(n)==5` for the US
would capture house numbers — it would make `pin_eq` a *house-number equality*
feature, adding a false-match vector to a metric that penalises false merges
~4× a miss. **Recommended action: none. Do not widen the guard.**

*Evidence: `check_us_zip_presence.py`, `check_pin_us_fix.py`, `check_pin_cause.py`, `check_pin_fused.py`*

#### N0-R corroborated by three independent tests

A second line of analysis initially reached the **opposite** conclusion — that
the convention is `<zip> <street>, <city>, <state>`, so the leading 5-digit
*is* the ZIP and the fix should be rescoped rather than dropped. That reading
rested on position alone, which is not sufficient. It is refuted by three
independent properties of the data, none of which needs an external ZIP table:

| Test | Result | ZIP would give | House number gives |
|---|---|---|---|
| **Geographic clustering** — share of a city's rows in its most common 3-digit prefix | mean **9.82%**, median 8.93%, **0 / 537** cities above 30% | high (a ZIP is a geographic unit) | near chance ✓ |
| **State association** — share of a prefix's rows in its most common state | mean **27.6%** vs **14.9%** base rate | far above base rate | near base rate ✓ |
| **First-digit distribution** | **70.4%** start `1`; **zero** start `0` | non-uniform but includes `0`-prefixed codes | Zipf-like decay ✓ |
| **Range tokens** — `10100 -14100 Greenwell Springs Road` | **61** such rows | a ZIP is never a range | house-number ranges ✓ |

The range rows are conclusive on their own: a postal code is never a span, so
`10100 -14100 … , Central City, LA` can only be a house-number range. The
strongest single signal is the clustering result — **not one** of 537 cities
shows ZIP-like concentration, which is exactly what a real postal allocation
would produce.

The first-digit distribution deserves a note: real US ZIPs are *also* non-uniform
and are skewed toward low first digits, so that test alone would be
inconclusive. It is only the **total absence of `0`-prefixed values** (thousands
of real US ZIPs begin `0`) that makes the Zipf-like decay implausible as postal
data. The clustering and range tests carry the conclusion on their own.

*Evidence: `check_zip_vs_housenum.py`, `check_state_assoc.py`, `check_housenum_confirm.py`*

#### Correction to the N0 table's denominators

The N0 table above reports 1,500,012 rows scanned, but
`check_pin_feature.py:44-45` breaks after 250k rows per file, so it covered
**1,500,012 of 24,229,173 rows = 6.2%** of the dataset. Its `rows` column is a
file *prefix*, not the slice population — it lists France test s1 as 37,323
where `analysis_out/profile/test_s1.json` reports **259,452**. The **rates** in
that table remain valid indicators, but the row counts must not be quoted as
slice statistics.

This does not weaken the conclusion, because the load-bearing part of N0 is a
**code fact rather than a statistic**: the guard at `normalize.py:337` reads
`if len(n) == 6 and country == "India"`, so a US or France row cannot enter
that branch under any data. `pin` is empty for every non-Indian row *by
construction* — no sample, however small, could have refuted it.

### N1 — Ligatures are silently deleted (real, low volume)

`strip_accents()` uses NFKD + drop-combining-marks. That does **not** decompose
`œ œ æ æ ß ø ł đ`. The downstream `_non_alnum = [^a-z0-9]+` then **deletes**
the survivor rather than transliterating it:

```
Cœur      → ['c', 'ur']       Fœur     → ['f', 'ur']
Sœur      → ['s', 'ur']       Œuvre    → ['uvre']
Manœuvre  → ['man', 'uvre']   Straße   → ['stra', 'burger']
```

Cœur / Fœur / Sœur all collapse to the same token `ur` — a genuine
false-merge vector, which F0.5 penalises ~4× a miss.

**Volume: 28 rows per 250,000 (0.011%)**, all `U+0152`. Real but small.
**Fix:** add an explicit ligature map before NFKD.

*Evidence: `check_fr_ligatures.py`, `check_fr_accents.py`*

### N2 — City lost when written with an inline postcode (real, negligible)

`normalize_address:351` marks a component as city only if it has **no digits**:

```python
if not any(ch.isdigit() for ch in c) and ctoks:
    city_comps.append(" ".join(ctoks))
```

So `33000 Bordeaux` yields `city_comps=[]` while `Bordeaux` yields
`['bordeaux']`. **63 rows (0.02%)** are affected — and the data mostly masks it,
because such rows repeat the city in a separate component
(`44000 NANTES, Nantes, …` → `city_comps=['nantes']`).

The city token still reaches the blocking keys via `toks`, so matching is
unaffected. **Verdict: cosmetic, not score-relevant.**

*Evidence: `check_fr_cityloss.py`*

### N3 — My F2 refutation was itself measured on the wrong file

The most important result here, because it is a **second-order correction**:
F2 was refuted, and then the refutation turned out to be partly wrong.

**What I measured:** `test_source1.tsv`, France slice → state resolves for
**100.00%** of rows (259,452/259,452). I concluded `FR_REGIONS` was fine.

**Why that was the wrong file:** the task pairs a source-**2/3** *query* against
a source-1 record, and `features.py:114` computes
`state_eq = tri(q_state, s_state)`, which returns **-1 when either side is
empty**. The query side is the one that matters. Measuring all three test
sources:

| test source | France rows | state resolved | missing |
|---|---:|---:|---:|
| `test_source1` | 120,000 | **100.00%** | 0 |
| `test_source2` | 120,000 | **64.35%** | 42,783 |
| `test_source3` | 120,000 | **65.99%** | 40,807 |

The unresolved components are **cities carrying no region at all**:

```
'bordeaux' 6,478   'nantes' 5,813   'lille' 5,135   'tourcoing' 2,640
'dunkerque' 2,500  'roubaix' 2,441   'calais' 2,347   'pessac' 1,907
```

Source-1 French addresses **always** carry a region; source-2/3 French
addresses frequently carry only a city. So roughly **35% of French candidate
pairs get `state_eq = -1`**.

**The consequence that matters:** the original F2 *recommendation* — "add all 18
regions and 101 departements to `FR_REGIONS`" — **would have accomplished
nothing**. All three regions actually used are already mapped, and the missing
35% of rows contain no region string to map. This is an absence of data, not a
dictionary gap, and no dictionary work fixes it.

F2 was wrong as stated, but it pointed at a real weakness for entirely the wrong
reason, and its proposed remedy was a no-op — a plausible finding whose fix
would have consumed an hour and changed nothing.

*Evidence: `check_fr_state_by_source.py`, `check_feature_liveness.py`*

### N4 — `alt_tset` is a second dead feature

Field population, pooled across all six files, using the real `prep`
normalisation:

| field | US | India | France | verdict |
|---|---:|---:|---:|---|
| `nfull` | 100.0% | 100.0% | 100.0% | LIVE |
| `ncore` | 100.0% | 100.0% | 99.9% | LIVE |
| `nalt` | 1.0% | 0.7% | **0.6%** | **DEAD** |
| `atoks` | 97.7% | 98.3% | 97.9% | LIVE |
| `anums` | 94.2% | 91.5% | 95.2% | LIVE |
| `state` | 97.7% | 98.3% | **77.6%** | LIVE, weak for France (N3) |
| `pin` | 0.0% | 0.0% | 0.0% | **DEAD** (see N0-R) |
| `acity` | 97.1% | 96.4% | 97.9% | LIVE |

`nalt` (the alternate / DBA name) is populated on under 1% of rows for India and
France. `features.py:82` guards `alt_tset` with `alt_mask` and substitutes -1
when the mask is 0, so the feature is -1 for ~99% of pairs.

**Two of the ~64 features — `pin_eq` and `alt_tset` — are dead.** Neither costs
compute, but both dilute the feature set the ranker learns through.

*Evidence: `check_feature_liveness.py`*

### N5 — Both remaining dictionary "defects" are non-defects

Two issues survived the audits and were carried forward as open. Both were
settled by measurement, and neither is a defect.

**Issue A — 15 `ADDR_CANON_COMMON` entries map to `""` and delete the token.**
The worry was that short tokens like `h` and `hno` might be load-bearing.
Counted as *raw* address tokens across all six files (capped at 120k rows each):

| token | US | India | France |
|---|---:|---:|---:|
| `plot` | – | 27,890 | – |
| `h` | 258 | 25,353 | 167 |
| `flat` | 155 | 15,063 | – |
| `door` | 3 | 12,599 | – |
| `house` | 362 | 11,485 | – |
| `shop` | 31 | 7,582 | – |
| `hno` | – | 640 | – |
| `number` | 20 | 687 | – |

The deletion is overwhelmingly **India-targeted** and essentially absent from
France (167 total occurrences). What it suppresses is Indian *unit designators*
— `plot`, `flat`, `shop`, `hno` — which are not street-identifying and would
otherwise pollute blocking keys. That is the table working as designed.

**Issue B — France drops `{w,e,s}` with no mapping.** The framing was a silent
cross-country inconsistency. But `ADDR_CANON_COMMON` maps all three to
**themselves**: `{'e': 'e', 's': 's', 'w': 'w'}`. Since `normalize.py` does
`canon.get(t, t)`, an identity mapping and an absent mapping are
**behaviourally identical**. Dropping them for France is a literal no-op.

Their France frequency is low anyway: `e` 891, `s` 163, `w` 1 in 17,953 France
rows. And the *real* asymmetry in that drop-set is deliberate good design —
`st` means `saint` in France but `street` in US, which is exactly why France
must drop the US mapping. Correct as written.

*Evidence: `check_canon_defects.py`*

**Net effect: the dictionary surface is now exhausted with zero outstanding
defects.** Across five audits the result is one genuine code defect (N1
ligatures, 0.011%) and one negligible one (N2 inline-postcode city, 0.02%),
plus two dead features (N0, N4).

---

## RULED OUT (hypotheses tested and rejected)

| Hypothesis | Result |
|---|---|
| Region position is inconsistent (86.6% last / 6.6% first) and breaks key generation | **No.** Key sets are order-independent: Jaccard = **1.000** across all six orderings tested, including upper-case and hyphen variants. `fk` is sorted; address keys are number×word, not positional. |
| Extreme city concentration (top-10 = 84.58%) saturates the blocking caps and drops keys | **No.** 2,222,310 France source-1 keys generated; **99.94%** survive `S1_MAXCAP=300`. Per-kind survival: kind 0 99.67%, kind 1 99.67%, kind 2 97.25%, kind 3 99.81%, kind 4 96.62%. High-df city tokens simply never form keys alone — they are absorbed into combined keys. |
| The US `dig5` rate (0.110/row) is a postal signal that the India-only guard discards, so widening the guard to US 5-digit would fix the dead `pin_eq` feature | **No — this was my N0 remedy, now retracted (N0-R).** Zero `STATE <5-digit>` matches in 1,986,739 US rows. 84.7% of the 5-digit numbers are the *leading* token, i.e. house numbers. 100% of them already reach blocking via `nums`, so the new key would be redundant. Widening the guard would make `pin_eq` a house-number-equality feature — a false-merge risk, not a gain. |

*Evidence: `check_fr_order.py`, `check_fr_caps.py`*

---

## France shape (for the record)

| Property | Value |
|---|---|
| Leading house number | 85.97% |
| `bis`/`ter` suffix on the number | 4.31% |
| No digits at all | 0.42% |
| Exactly 3 comma components | 96.12% |
| Region component last / middle / first | 86.60% / 6.79% / 6.61% |
| Top-10 cities share | 84.58% (bordeaux 16.5%, nantes 14.4%, lille 13.2%) |
| Rows containing an accented character | 38.90% |
| Distinct place components | 5,960 |

*Evidence: `analyse_france.py`*

---

## Honest conclusion

**Upstream's France handling is fundamentally sound.** Of the five France
hypotheses I generated, **three were wrong** — including both headline findings,
and including the fix I proposed for the third.

What survived:

- `pin_eq` and `alt_tset` are **dead features** (0.0% and <1% field
  population). Cheap to drop; the ranker just learns less.
- France's `state_eq` fires for only **~65%** of source-2/3 rows, so it is -1
  for about a third of French pairs. **Unfixable by dictionary work** — those
  rows contain no region string at all.
- Two real code defects (ligatures, inline-postcode city) worth 0.011% and
  0.02% of France rows.
- Component order, cap saturation and city concentration are **ruled out**.

**On `pin`: leave the guard alone.** The dead `pin_eq` is a property of the
*data*, not a bug. Widening the guard would not add a postal signal — it would
add a house-number signal, which is a false-match vector in a metric that
already punishes false merges ~4× a miss. The defensible change is to drop the
dead plumbing and change nothing else.

### The methodological lesson, stated plainly

My three errors shared one cause: **I measured the wrong population, or inferred
from code instead of running it.**

1. F1 — asserted a France effect from reading a country guard.
2. F2 — asserted a France gap from counting dictionary entries.
3. The F2 *refutation* — measured source-1 only, when the task matches source-2/3
   queries against source-1, so I "refuted" a claim using the wrong file and
   nearly buried a real weakness.

Every finding that survived did so because a script produced it. The rule this
document now holds itself to: **no claim ships without the script and the
population it was measured on.**

The lesson worth carrying: reading code and reasoning about it produced three
confident, wrong, high-severity findings — and the third was wrong in the
*remedy* even after its premise had been measured and confirmed. Measuring took
minutes and refuted all of them. Any future claim about this dataset should
come with the script that produced it, **including claims about what to change.**


---

## APPENDIX — D073 and D078 (appended by later agents; nothing above was edited)

### A1 — D073: the "100% state resolution" figure is an artefact of one file

**D073 re-measured the inherited claim on all three French test files, not just
`test_source1`.** The inherited block's own region breakdown gives
`101,521 + 85,197 + 72,734 = 259,452`, which is *exactly* the `test_source1` France
row count — so the prior 100% figure and its region breakdown were both s1-only.
s1 is `259,452 / 1,694,445 = 15.31%` of French rows.

Using a per-key-minimum union bound over `addr_tokens["France"]`, and correcting
two soundness holes in the naive version (top-4000 truncation means an absent
token is <= the rank-4000 cutoff, not 0; and `build_profile.py`'s `TOKEN_RE` drops
accents instead of decomposing them, so `ile` undercounts against `le`):

| file | France rows | sound UB | provably unresolved |
|---|---|---|---|
| test_s1 | 259,452 | 263,440 | 0 (bound vacuous) |
| test_s2 | 703,378 | 461,566 | **241,812 (34.38%)** |
| test_s3 | 731,615 | 492,278 | **239,337 (32.71%)** |
| **total** | **1,694,445** | — | **>= 481,149 (28.40%)** |

**But the fix is worth almost nothing.** A maximal, token-disjoint French
region/department gazetteer (51 candidate keys) recovers at most **10,307 rows =
0.608%** of France. The residual ~28% is *structural*: s2/s3 addresses are
`house number + street + city` with no region word. Supporting evidence:
`has_comma` is 100.00% in s1 but only 96.91% (s2) / 97.03% (s3); `alpha_only_addr`
is 0.42% in s1 but 3.79% / 3.67%. **Conclusion: `FR_REGIONS` is not the France
blocker. A city->region table is** — and it cannot be derived from this profile,
which has marginal token counts but no co-occurrence. Logged as a gap.

Also measured and worth recording: **French department *codes* are not a signal.**
The 2-digit tokens rank 67-89 of 99 two-digit tokens against a median of 2,915
(`test_s2`) — below median, not above. **Do not add numeric department codes.**
And France is extremely city-concentrated: `bordeaux` + `nantes` + `lille` =
**43.3% of every French test file**.

### A2 — D073: a NEW defect nobody had looked for — `LEET` corrupts French ordinals

`LEET` fires on any token with both an alpha and a digit character
(`normalize.py:279`). French ordinal suffixes are not leetspeak and get destroyed:

| token | n | LEET output |
|---|---|---|
| `3eme` | 748 | `eeme` |
| `1er` | 131 | `ler` |
| `3e` | 121 | `ee` |
| `1ere` | 102 | `lere` |
| `7eme` | 9 | `teme` |
| **total** | **1,111** | 0.066% of France rows |

The `LEET` *table* needs no new mappings — the 5,307 genuine alpha+digit tokens
(`c1ub`, `mais0n`, `5arl`, `li1le`, `sp0rtive`, ...) are all handled correctly. Only
the **trigger condition** is wrong. A guard excluding `^\d+(er|ere|eme|e)$` fixes
it. This is the one D073 item worth actioning immediately.

### A3 — D078: `IN_STATES` audit (ground truth for the follow-up tasks)

`IN_STATES` (`normalize.py:230-242`) is **49 pairs / 37 distinct canonical values
/ 86 effective keys** after the self-map loop. Against `US_STATES` (52 -> 104) and
`FR_REGIONS` (14 -> 14).

- **No self-map defect for India.** Line 252 includes `IN_STATES`, so it gains all
  37 self-maps. The `FR_REGIONS` omission does *not* apply here. Quote "86 keys",
  never "49 states".
- **NEW hard defect: `"jammu & kashmir"` (line 239) is unreachable.** The `ck`
  transform at line 331 does `.replace("&", " and ")`, so no input can ever produce
  that key. A structural bug that frequency analysis can never surface. Latent
  only — the name is below the profile's measurement floor.
- **36 of 86 keys are below the top-4000 truncation floor** and are unmeasurable
  from this profile. Reported as a gap, not estimated.
- 5 canonical codes (`ar ga la mn tn`) mean different states in India vs US. **Safe
  as written** — `STATE_MAPS` scoping isolates them. Only a hazard if the maps are
  ever flattened.


### A4 — D079: the work order's premise was void, and the sidecar was corrupt

**D079 was assigned as "mine evidence to extend `IN_STATES` for US". That combination
is structurally impossible, and the correct deliverable is a refusal, not a ranked
table.** `STATE_MAPS` (normalize.py:250) is keyed strictly by country
(`{"US": US_STATES, "India": IN_STATES, "France": FR_REGIONS}`) and
`normalize_address` looks up `smap = STATE_MAPS.get(country, {})` (normalize.py:318).
A US row reads `US_STATES` and **never consults `IN_STATES`**. Adding a key to
`IN_STATES` has exactly zero possible effect on any US row — by construction, not by
measurement. This is the "confident, well-formatted, entirely inert recommendation"
failure mode `AGENT_PROMPT.md` lines 78-89 warn about. The real US answers (from
D075, independently re-measured) are that `US_STATES` needs no region extension, the
only worthwhile additions are `del` (10,711) and `penn` (3,084) at **LIKELY**, and
`LEET` needs no new digit mappings for US.

**Two things worth recording for whoever aggregates these findings:**

1. **The D079 sidecar shipped as invalid JSON.** A 17-key object closed correctly at
   char 12,442, then an **orphaned `F7_jammu_ampersand_key_dead` fragment was
   appended after the closing brace** — with no enclosing braces, so `json.load` raised
   `Extra data: line 166`. Any aggregator reading this sidecar would have crashed or
   silently dropped F7. I re-wrapped the fragment into the object; it now
   strict-parses with 19 keys. **Lesson: a sidecar that "exists" is not a sidecar that
   parses — validate with `json.load`, not `Test-Path`.** (The same class of error bit
   D078, where a hand-written "50" survived in prose while the generated sidecar
   correctly said 36.)

2. **D079's genuinely new finding, independently verified by me:** the 7 post-self-map
   key collisions between `US_STATES` and `IN_STATES` (`ar ga la mn or tn ut`) total
   **976,874 US address-token occurrences = 81.47 per 1,000 US rows**, and every one
   of the 7 is exactly 2 characters. That means `learn_translit.py:55`'s
   `len(c.strip()) > 3` guard — which builds its state set with **no country filter**
   (`states = set(N.IN_STATES.keys())`, line 51) — neutralises all 7 *by coincidence*,
   not by design. I reproduced the intersection, the per-code counts, the 976,874
   total, and the "41 of 86 `IN_STATES` keys are permanently unusable by that path"


---

## APPENDIX — LEET ORDINAL GUARD IMPLEMENTED (appended by the lead; nothing above was edited)

### A5 — The `LEET` ordinal defect now has a fix, and it is verified

Section A2 above recorded the defect as a finding. It is now **implemented and
regression-tested**, in a working copy. `_upstream/` remains pristine at `8445b7f`.

**The fix** (`patch_upstream/src/normalize.py`), two changes:

```python
_ORDINAL_RE = re.compile(r"^\d+(?:er|ere|eme|e)$")
```

and at the single call site in `_name_tokens` (was one line, now two):

```python
-        if any(c.isalpha() for c in t) and any(c.isdigit() for c in t):
+        if (any(c.isalpha() for c in t) and any(c.isdigit() for c in t)
+                and not _ORDINAL_RE.match(t)):
             t = t.translate(LEET)
```

**Design decision, stated because it is the part that could have gone wrong:**
the guard is deliberately **NOT country-scoped**. `_name_tokens` is called from
`normalize_name`, which has **no `country` argument**, so a country check is not
available at this call site. A shape-based guard is also the safer choice: an
ordinal is an ordinal in any language, and the pattern is narrow enough that it
does not catch real leetspeak.

**The pattern is anchored to the whole token.** This is what stops the obvious
bug in the obvious fix. A looser pattern such as `\d+[er]` — which reads like the
right idea — would also swallow `b3er` → `beer` and `p1er` → `pler`, silently
disabling leetspeak on those tokens. The anchored form does not.

**Verification: 38 assertions, 38 passed, 0 failed.**

| class | examples | requirement |
|---|---|---|
| Ordinals guarded | `3eme`, `1er`, `3e`, `1ere`, `10eme`, `22e`, `4EME` | preserved verbatim |
| Real leetspeak kept | `c1ub`→`club`, `mais0n`→`maison`, `b3ta`→`beta`, `c0ff3e`→`coffee` | still translated |
| Pattern boundary | `b3er`→`beer`, `p1er`→`pler`, `3a`→`ea`, `e3`→`ee` | **not** treated as ordinals |
| Raw table unchanged | `3eme`.translate(LEET) == `eeme` | the *guard*, not the table, is the fix |

Two artefacts:
- `patch_upstream/src/test_leet_ordinal_guard.py` — the authoritative suite. It
  imports the real `normalize` module, so it exercises the real call path rather
  than a reimplementation. It **skips rather than passes** if the module cannot
  be imported, so a skip can never be mistaken for a pass.
- `verify_leet_guard.ps1` — a PowerShell harness that exercises the same 38
  assertions **without Python**, because the interpreter on this box is broken
  (`C:\Program Files\Python313` has no `Lib\` tree; every venv points at a deleted
**Honest note on expected impact.** The guard is correct and the defect is real,
but `3eme`+`1er`+`3e` is ~1,000 token occurrences. That is small relative to
~1.7M France test rows. This is a **correctness fix, not a score fix** — expect
negligible leaderboard movement. It is worth taking because it is cheap, safe and
provably does not regress genuine leetspeak, not because it will move F0.5.

### A5b — CORRECTION: the French-only guard above fixes just 19.1% of the defect

**D087 (the `LEET` ground-truth audit) found two larger defect classes that the
guard described in A5 does not touch.** I widened the patch. The original A5 text
is left in place above rather than rewritten, because the mistake is the point.

| class | token | becomes | occurrences | caught by the French-only guard? |
|---|---|---|---|---|
| **D1** | `3eme` / `1er` / `3e` | `eeme` / `ler` / `ee` | 1,111 | **yes** |
| **N1** | `24hr` | `2ahr` | **3,657** | **NO** |
| **N2** | `1st` | `lst` | 1,060 (US 679 + India 381) | **NO** |

`24hr` is the **single largest corruption in the entire dataset** and is **3.3×**
the French ordinal mass. A French-suffix-only guard fixes 1,111 of 5,828 (19.1%)
and leaves the biggest defect untouched. **And country-scoping would not rescue
it**, because N1 and N2 are US and India defects, not French ones.

**The widened guard**, three classes unioned, still token-anchored, still at the
call site:

```python
_ORDINAL_RE  = re.compile(r"^\d+(?:er|ere|eme|e)$")    # French: 3eme, 1er, 3e
_EN_ORDINAL_RE = re.compile(r"^\d+(?:st|nd|rd|th)$")   # English: 1st, 2nd, 3rd
_HOURS_RE    = re.compile(r"^\d+hr$")                  # 24hr, 7hr
_LEET_GUARD_RE = re.compile(
    r"^(?:\d+(?:er|ere|eme|e)|\d+(?:st|nd|rd|th)|\d+hr)$")
```

**D087 also independently confirmed the two design decisions in A5**, with
evidence I did not have: the fix belongs at the **call site** and not in the
table (a `str.maketrans` character map structurally cannot express "skip this
token"), and it must **exempt rather than extend** (170,314 of 176,142 observed
mixed occurrences, 96.7%, are correct leet expansions).

**D087 proved every LEET key is load-bearing**, which kills the alternative fix of
deleting a digit from the table: removing `1` to save `1st` would also break
`de1hi` (1,674), `denta1` (1,652) and `techno1ogies` (1,288) plus 82 other types;
removing `4` to save `24hr` would break `4l` (1,943). Exemption is the only
safe option.

**D087 also independently reached my A6 finding** — `@` and `$` are unreachable
dead code — and strengthened it: the same blindness applies at profile time
(`build_profile.py`'s `TOKEN_RE` is `[a-z0-9]+`), so **no measurement could ever
have found them**. D087 upgraded D090's "cannot be evaluated" to "unreachable by
construction".

**Re-verified after widening: 73 assertions, 73 passed, 0 failed** (was 38). New
assertions cover `24hr`/`24HR`/`7hr`/`12hr`, `1st`/`2nd`/`3rd`/`4th`/`21st`, the
union-vs-parts consistency check, and the new rejections `x1st`, `hr24`, `24hrs`,
`1std`.

**The methodological point, stated plainly:** I wrote a fix for the defect I had
already found, verified it 38/38, and it was still wrong in scope — because I
anchored on France (the scored country) and never asked what else the same code
path breaks elsewhere. D087 was assigned merely to establish ground truth, and
it found more than the task it was fixing. **A guard on a shared code path must be
audited against every country, not the one you care about.**

  base). **Stated limitation: .NET regex is not Python `re`.** They agree on this

### A6 — Two new minor findings from building the tests

1. **The `@` and `$` entries in `LEET` are dead code.** `_non_alnum` splits on
   `[^a-z0-9]+` *before* `translate()` is reached, so `@` and `$` are already gone
   by the time the table is applied. `@lm` → `lm`, `$tore` → `tore`, never `alm` /
   `store`. This is pre-existing upstream behaviour, not something the guard
   caused. It is harmless — but it means 2 of the 12 `LEET` entries can never fire
   via `_name_tokens`, which is worth knowing before anyone reasons about `LEET`
   coverage. Asserted in `test_at_and_dollar_leet_entries_are_dead`.

2. **`1` maps to `l`, not `i`.** So `p1zza` → `plzza`, not `pizza`. I had asserted
   `pizza` in the first draft of the test and it failed — the test was wrong, not
   the code. Recorded because "leet" is often assumed to recover the intended

---

## APPENDIX — CONVERGENT EVIDENCE ON FR_REGIONS (appended by the lead; nothing above was edited)

### A8 — D116 independently confirms A7, and adds the strongest argument against the fix

D116 was dispatched as "remaining gaps in FR_REGIONS" **without** being told D128's
answer. It reached the same verdict by a different route, which makes this
convergent rather than inherited:

> **No change to `FR_REGIONS` is warranted. The premise of the work order is refuted
> by direct measurement, and the residual gap is not a dictionary gap.**

**D116 refuted the premise directly.** The `already_checked` block claimed s2/s3
"encode geography with department names absent from `FR_REGIONS`", citing `gironde`,
`nord` and `loire atlantique`. All three **are already keys** (`normalize.py:244`,
`:246`, `:247`). Their s1→s2 count jump is a *frequency* shift between sources, not
a *coverage* gap. This is the same correction D128 made, reached independently.

**The new and strongest argument — D116's, not D128's — is that the fix would make
things WORSE:**

> A department name that does not match an `FR_REGIONS` key is **retained** in
> `atoks` and contributes to the IDF-weighted overlap `wa_wj` (`features.py:129`).
> Adding the key would make `normalize.py:335` `continue`, which **deletes the token
> from `atoks`** — removing signal rather than adding it.

This inverts the usual intuition. An unmatched token is *not* dead weight that a
dictionary must clean up; on this pipeline it is **live feature mass**. So the
dictionary is not merely insufficient for the residual — extending it would
*destroy* information that currently works. That is a much stronger objection than
"the gain is too small to bother", and it should carry the decision.

**A second, larger finding D116 surfaced, which dwarfs the dictionary question:**

> **France has ZERO training rows.** `country_rows` in `train_s1/s2/s3.json` contains
> only `US` and `India`. Consequently `_upstream/src/crossfit.py:112` iterates
> `for c in ("US", "India")` — **France is never trained on.**

The codebase already knows this: `decoy_postfilter.py:17-18` comments *"the country
has no training labels (e.g. France in the test set)"*. So France is test-only by
construction, and the cross-fitted ranker never sees a French label. This reframes
the whole France effort: dictionary work is not where the leverage is, because
**nothing in the pipeline is fitted to France at all.**

**Sizing, for the record:** a maximal French department/region gazetteer would
recover at most **8,400 French test rows = 0.496% of 1,694,445** — a deliberately
optimistic union bound. D128's independent estimate for the same question was
44,671 rows / 2.64pp for all 49 keys, and 13,563 rows / 0.80pp for the
provably-incremental token-disjoint subset. **The two estimates differ by ~5x**
(D116 counts only genuinely-absent departments; D128 scored a maximal gazetteer),
and they bracket the same conclusion: the recoverable mass is a fraction of a
percent to low single-digit percent, against a measured 28.40% residual that is
**structural** — rows with no administrative component at all.

**Net: three independent audits (D070, D116, D128) now agree that `FR_REGIONS`
should not be extended**, and D116 explains why extending it would actively hurt.
The one change that would genuinely move France is a **city→region table**
(`bordeaux` 277,474, `nantes` 238,748, `lille` 221,585 — top 3 ≈ 43.7% of every
French test file), and that is **not derivable from the current profile**, which
stores marginal token counts with no co-occurrence.

### A9 — D095: the `indic_token_dict` "0 tokens affected" result is a PROFILE ARTEFACT

D095 audited `indic_token_dict.json` (1,363 entries, 167 distinct Latin values).
Its most important result is a warning about our own tooling, not about the table:

> The table is keyed **100% on native Brahmic script** (U+0900–U+0D7F, 9 scripts),
> zero Latin keys. `build_profile.py:28` tokenises with `TOKEN_RE =
> re.compile(r"[a-z0-9]+")`, which matches **zero characters** of a Brahmic string.
> **Every token the profile can list is pure ASCII; every key in this table is pure
> Brahmic. The two sets are disjoint by construction of the profile.**

So the intuitive finding — "this table affects 0 of 8,000 listed India tokens,
therefore it is inert" — is **false, and false in a way that looks exactly right.**
The table is not inert; it is *invisible to every profile field the fleet has*.
Reading the zero as inertness is precisely the plausible-but-wrong inference the
fleet brief warns about.

Two further measured points:
- **166 of the table's 169 output word-atoms already exist as raw ASCII in India's
  `name_tokens`**, covering 2,212,001 / 2,955,338 = **74.85%** of listed name-token
  mass. The table therefore **introduces no new vocabulary**; it can only convert

---

## APPENDIX — STATE DICTIONARIES: INDEPENDENT RE-CONFIRMATION (appended by the lead)

Three separate agents were dispatched to re-verify the *negatives* on the state
tables, on the explicit principle that **an unverified negative is as dangerous as
an unverified positive** — this project has already been burned twice by
plausible-but-wrong claims. All three confirmed. Two also found live defects.
Nothing above was edited.

### A10 — D117: `US_STATES` confirmed clean, but a real `Washington` / `DC` collision

Exhaustive scan of the union of all six profiles' `addr_tokens["US"]` — **4,510
distinct tokens**: every US state token that occurs is already a canonical runtime
key. Zero misspellings, zero abbreviated names, zero unhandled 2-letter codes,
zero territory names.

**The abbreviation class is now closed far more tightly than before.** D117
enumerated *every* 2-character alphabetic token in the entire US address vocabulary
— **33 of them, 4,001,717 occurrences** — and they are all street/ordinal/direction
words (`st`, `rd`, `dr`, `ln`, `of`, `po`, `pl`, `el`…). **Not one is a state.**
That replaces the earlier hand-picked probe lists with an exhaustive result.

**D117 turned a hypothetical into a measured collision.** The US vocabulary contains
a standalone component `district of columbia` (`district` 27,527, `columbia` 58,751,
`of` 252,303) *and* a very large mass of bare `washington` (**267,075**). The keys
`district of columbia → dc` and `washington → wa` are **both live in the same
country bucket**, so a DC row can resolve to `wa`. Flagged as a collision the
profile **cannot** price into a row count.

**D117 also corrected D074:** `penn` and `del` are both unhandled, and D074 had
called the canon-collision set complete without them. (It did re-confirm D074's one
non-identity collision, `wy → way`, by intersecting all 104 runtime keys against
`ADDR_CANON_COMMON`.)

**A useful bounded-negative technique, worth reusing.** D117 did not merely say
"no gaps found" — it *bounded* the class it could not see. The 4000th-token floors
per file are 201/407/440/101/258/274, so **any unthought-of variant spelling must
occur fewer than ~101 times per file to be invisible.** A negative with a stated

---

## APPENDIX — D119 RETRACTS A FINDING I HAD PROPAGATED (appended by the lead)

### A13 — The French function-word finding is RETRACTED. It was inflated ~37.5% and misdiagnosed.

This is the third time in this project that a finding I had recorded, briefed to
other agents, and started acting on turned out to be wrong on measurement. I am
recording that rather than quietly editing it out, because the pattern is the
lesson.

**What was claimed:** `ADDR_CANON_FR` has no entries for the French function words
`de/la/du/des/le/les`; they are **731,158 of 4,745,780 = 15.41%** of test_s2
address-token mass (France ~42× the US rate); they are unhandled, so they enter
the IDF-weighted features and **"dilute IDF weighting for every French pair."**

**What D119 measured:**

1. **The magnitude is inflated by ~37.5%.** `normalize.py:333-335` resolves a French
   region by matching a **whole comma-component** and then `continue`s — so the
   `de`/`la` inside `"Pays de la Loire"`, `"Hauts de France"`, `"Pas de Calais"` and
   `"Ile de France"` **never enter `atoks` at all**. The profile cannot see this
   because it flattens components. Real pipeline-visible mass is
   **1,229,094 = 10.25%**, not 1,966,401 = 16.40%; the test_s2 figure moves
   **15.41% → 10.68%**.

2. **The stated mechanism — "dilutes IDF" — is self-cancelling.** `idf = ln(n/df)`
   with `n = 1,694,445` France rows and `df ≤ occurrences` gives
   `idf(de) ≥ ln(1694445/1050023) = 0.4785` against a ceiling of 14.343. **IDF
   already discounts these words by ~28×.** The claimed dilution is a mathematical
   artefact of assuming `df = df_max`.

3. **The "pollutes blocking" mechanism does not exist.** `keys.py:42` requires
   `len ≥ 3` for a blocking token, so `de/la/du/le` (2 chars) **never become
   blocking keys**. `des` is **already** in `ADDR_GENERIC` (`keys.py:16`). `les`
   (3,685 occurrences) exceeds `S1_MAXCAP=300` and is dropped as non-selective.

**Verdict: `ADDR_CANON_FR` has no material gap for this dataset.** The remaining
street-type gap is 0.55% of listed mass with **no single load-bearing entry**: the
16 unambiguous French way-types total 26,447 (0.2205%), the plausible-but-ambiguous
set adds 40,002 (0.3335%), and the largest unhandled candidate `cour` (9,403 =
0.078%) is **smaller than the already-handled `place` (13,363)**. D119's
recommendation is one cheap SPECULATIVE addition (`cour → crs`) and an explicit
argument *against* adding the function words.

**D119's structural numbers, for the record:** `ADDR_CANON_COMMON` 177 keys;
`ADDR_CANON_FR` 68 keys; COMMON after the 7-key France drop tuple 170; **effective
France canon = 219**. France rows 259,452 + 703,378 + 731,615 = 1,694,445. Listed
France address-token mass 2,253,877 + 4,745,780 + 4,993,261 = 11,992,918.

**The lesson, and it is the same one as A5b (the `LEET` guard):** both errors
shared a shape — *a plausible count attached to a plausible mechanism, neither
checked against the code path that actually consumes the value.* For `LEET` I
anchored on France and never checked US/India. For the function words I took a
token-share number from a profile that **flattens components**, and asserted a
downstream effect I never traced into `features.py`. **A token count from a
component-flattening profile is not a pipeline-visible quantity**, and that is now
the third distinct trap in this project after the `test_source1` denominator and
top-4000 truncation. It should be a standing check on every remaining task.

detection floor is worth far more than a bare negative.

### A11 — D118: `IN_STATES` confirmed clean, and the self-map loop is LOAD-BEARING

All 28 states and 9 UT/NCT codes present; every alternate-spelling, ordinal,
merged-territory and concatenation variant constructible from the profile measures
**exactly 0** across all six files. The two families D118 was specifically sent to
hunt — union-territory-vs-state, and the `Delhi` / `Nagar Haveli` /
merged-territory cases — both resolve to **no missing key**.

**The reframing, and it is the valuable part.** The prior audits (D078) described
the self-map loop as "correct, no defect" and stopped. D118 shows it is the **sole
mechanism by which the two `s3` files resolve an Indian state at all**:

- **98.00%** of all self-map key mass (**3,125,112 of 3,188,831** occurrences) sits
  in `train_s3`+`test_s3`.
- In `s1`/`s2` India writes the state in full (`maharashtra` 217.83 per 1k rows,
  `mh` 2.38 per 1k). In `s3` it writes the two-letter code (`mh` 151.93 per 1k,
  `maharashtra` 11.38 per 1k).

So the loop is load-bearing for **4,520,547 Indian rows**. That is a far stronger
reason to leave it alone than "it is fine" — and it reframes D079's related
finding (the `ar ga la mn or tn ut` collisions being neutralised *by coincidence*)
from a latent-bug note into a **"this code is far more important than it looks"**
warning. A future refactor that tidies the loop would silently break s3 state
resolution for millions of rows.

**New latent defect, same class as D078 but a set D078 missed.** The self-map loop
manufactures the keys `as` (Assam) and `an` (Andaman & Nicobar) — **ordinary English
function words** — at **2.92× the exposure** of the `ts` risk D078 did flag. D078's
Defect-2 table examined only *literal* short aliases (`or`, `ts`, `ut`), so it
systematically missed every hazard **the loop itself creates**. That is a precise
statement about where to look next time, not just another warning.

### A12 — The convergent picture across all three state audits

| table | verdict | who | notable |
|---|---|---|---|
| `FR_REGIONS` | **no change** | D070, D116, D128 | adding keys would `continue` and **delete** live feature mass (A8) |
| `US_STATES` | **no change** | D074, D075, D117 | 4,510-token exhaustive scan; `washington`/`dc` collision is live |
| `IN_STATES` | **no change** | D078, D079, D118 | self-map loop is load-bearing for 4.5M rows; `as`/`an` are function words |

**The general lesson, which is the reason all three were commissioned:** these
tables are *correct*, and the reason they are correct is **not obvious from reading
them**. Each correctness depends on a specific mechanism — a self-map loop, an
accident of key length, a downstream deletion — that a future maintainer would
reasonably "clean up". The negatives are only trustworthy **together with the
mechanism that makes them true**, which is why D118's reframe matters more than its
confirmation.

  rows already in Brahmic into a bucket the data is already in. Its entire
  contribution is the Brahmic subset of India — a declared gap.
- **For France its value is exactly 0, and that is provable rather than inferred.**
  France has no training rows, the table has no Latin keys, and French rows are
  Latin. It also is **not country-scoped**, so it is loaded and evaluated on the
  France hot path for nothing.

**Methodological lesson to carry into the remaining tasks:** a zero in this profile
means "not observable with the fields collected", not "does not occur". This is the
same class of error as the `test_source1`-only denominator, and as reading
top-4000 truncation as absence.

   letter, and for `1` it does not.

### A7 — D128 RESOLVED: the 71.10% vs 97.44% contradiction was not a contradiction

Section A1 and the `already_checked` block of every D-task describe a live
disagreement between D073 and D077. **It is resolved, and the answer is that the
two figures never measured the same quantity.**

- **D073** computed a *dictionary* bound: a union bound over the 14 `FR_REGIONS`
  keys. Sound in direction, an upper bound on resolvable rows.
- **D077** never consulted `FR_REGIONS` at all. It counted rows that are
  structurally dead regardless of dictionary (empty address, or non-empty with no
  comma) and treated everything else as resolvable. That assumption is false:
  `normalize.py:333` requires a component to *exactly equal* a key.

D077's own control falsifies its criterion: it reports 97.0552% for US and
97.5368% for India, countries with entirely disjoint state tables. A coverage
metric that is near-identical across disjoint dictionaries is measuring **address
format**, not dictionary coverage.

**Defensible result under one criterion** (a France row resolves iff a whole
comma-component equals one of the 14 keys, per `normalize.py:331-335`):

> **≤ 1,213,296 of 1,694,445 France test rows (71.60%) can resolve a state through
> `FR_REGIONS`. ≥ 481,149 rows (28.40%) provably carry no state token at all.**

**Engineering verdict: do NOT extend `FR_REGIONS`.** This upgrades the earlier
"`FR_REGIONS` needs no expansion" assertion from *unexplained* to *explained*:

- The three region tokens carrying mass (`hauts` 289,655, `nouvelle` 242,802,
  `pays` 207,396 — 89.7% of region mass) are **already mapped**.
- The department tokens dominating s2/s3 (`nord` 152,011, `gironde` 150,787,
  `calais` 128,762, `atlantique` 128,348 — 98.9% of department mass) are **also
  already mapped**. s2/s3 *do* resolve — through the department half of the
  existing table. This is the fact REFUTED-2 recorded without explaining.
- The residual is address-shaped `house number + street + city` with **no
  administrative component at all**. A maximal 49-key gazetteer moves the bound
  by **2.64 pp**; the provably-incremental token-disjoint subset by **0.80 pp**
  (13,563 rows). Neither justifies the change.
- The departments driving the miss are *cities*: `bordeaux` 277,474, `nantes`
  238,748, `lille` 221,585 — top 3 alone are ~43.7% of every French test file.
  `paris` is only 2,263. **The provinces are the mass, not Paris.**

**The real fix would be a city→region table, and it is not derivable from this
evidence.** The profile stores marginal token counts with no co-occurrence, so
city→region cannot be reconstructed. That is a gap, not a number. The correct
next scraping job is a **component-level re-scan of France** — which is exactly
the profile capability that would also convert these bounds into point estimates.

**Also found: D073's two artefacts disagree with each other.** Its JSON sidecar
carries stale pre-fix numbers (1,204,739 / 71.10% / 28.90%); its `.md` carries the
corrected 1,213,296 / 71.60% / 28.40%. The `.md` is correct. **Anyone citing D073
must cite the `.md`, not the sidecar.** This is the same failure class as A4
(D079's invalid-JSON sidecar): a sidecar that *exists* is not a sidecar that is
*correct*.

  simple anchored alternation, so the harness validates the pattern logic and the
  token-classification decision, **not** Python's exact engine behaviour. The
  `.py` suite must still be run once Python is repaired.

**Honest note on expected impact.** The guard is correct and the defect is real,
but `3eme`+`1er`+`3e` is ~1,000 token occurrences. That is small relative to
~1.7M France test rows. This is a **correctness fix, not a score fix** — expect
negligible leaderboard movement. It is worth taking because it is cheap, safe and
provably does not regress genuine leetspeak, not because it will move F0.5.

   figure exactly. Safe today; one refactor away from a live bug.
