# D088 — Mining `LEET` for the **US**: full mixed-token census, per-digit damage ranking, and the `1st` name/address asymmetry

**Task type:** evidence mining. The fix is already written (`patch_upstream/src/normalize.py:296-298`,
applied at `:322`); this report's job is to say whether the **US** needs anything the written guard
does not already do, and to quantify what is at stake.

**Sources read:** `_upstream/src/normalize.py`, `keys.py`, `features.py` (read-only);
`patch_upstream/src/normalize.py` (read-only); `build_profile.py`; the six profile JSONs in
`analysis_out/profile/`. No raw `*.tsv` opened. No network. All computation in PowerShell.

---

## Headline

1. **The written guard is already complete for the US. Do not widen it.** I enumerated the
   **entire US mixed-token population — 133 types / 90,100 occurrences** (exactly reproducing
   D087 §4 and D121 §1). The guard matches **exactly 2 of those 133 types, 4,336 occurrences**:
   `24hr` 3,657 and `1st` 679. **Zero** US types are wrongly exempted, and the other 131 types
   (85,764 occ) must keep translating. **No fourth US class exists, and no fifth guard
   alternative is warranted.** Confidence: CONFIRMED in the measured window.
2. **US contributes 4,336 of 5,828 corrupted occurrences = 74.4%** — the largest of the three
   countries by 3.9x over France. `24hr` alone is **84.3%** of all US LEET damage.
3. **Per-digit US damage is starkly bimodal, and this is the risk quantification the work order
   asked for.** In the US window, digits `0, 5, 6, 8` are **0.0% damaged**; `1` is **2.3%**;
   and **`4` is 100.0% damaged (3,657 of 3,657) with ZERO load-bearing US occurrences.**
   Digits `3` and `7` have **no US occurrences at all**. Any future table edit touching key `4`
   in the US context is deleting damage and nothing else — but key `4` is *not* globally
   removable, because France's `4l` (1,943) depends on it. **Country-blind code, country-
   asymmetric data.**
4. **NEW FINDING (N5, US-specific, name/address asymmetry — CONFIRMED, and the largest
   *unmeasured-risk* item):** `ADDR_CANON_COMMON` maps `first→1st` (normalize.py:184) but
   **`NAME_CANON` has no such entry.** So on the address side `first` and `1st` *converge* to
   `1st`; on the name side they do not. Combined with LEET, the US name column produces
   **three mutually non-matching spellings of the same ordinal** where it should produce one.
   See §4 — this is a *mismatch* defect the guard does **not** fix, and it is larger than the
   `1st` corruption itself.

---

## 0. Reproduction of the denominators (independence check)

Recomputed from scratch in PowerShell, not copied from D087/D121. **Both agree exactly.**

| population | my measurement | D087 §4 / D121 §1 |
|---|---|---|
| US name mixed types / occ | **133 / 90,100** | 133 / 90,100 ✓ |
| India name mixed types / occ | 127 / 80,735 | 127 / 80,735 ✓ |
| France name mixed types / occ | 24 / 5,307 | 24 / 5,307 ✓ |
| **all three** | **284 / 176,142** | 284 / 176,142 ✓ |

Trigger replicated from `normalize.py:279` — token contains **both** a letter and a digit.
Method: aggregate `name_tokens[US]` across all six files (5,065 distinct types in the union of
the six top-4000 windows), then filter.

> **PowerShell gotcha, recorded because it silently produced wrong answers and I nearly shipped
> them.** A `@{}` hashtable keyed on a token like `'149'` **auto-coerces the key to `Int64`**,
> and `-cmatch` then silently returns `$false` on it. My first three family scans reported
> *"0 US name-side types for every family"*, which is obviously wrong given `24hr` is in hand.
> Fix: prefix every key with `'_'` and strip it on read. Every number in this report uses the
> prefixed form. Anyone re-running these scans must do the same or they will get zeros.

Per-file US mixed breakdown (shows the top-4000 truncation is not uniform across files):

| file | US rows | name_tokens | mixed types | mixed occ | guard-exempt types | guard-exempt occ |
|---|---|---|---|---|---|---|
| train_s1 | 1,323,633 | 4,617,935 | 1 | 425 | 1 | 425 |
| train_s2 | 3,016,817 | 10,713,782 | 119 | 27,009 | 2 | 1,089 |
| train_s3 | 3,170,056 | 11,522,038 | 124 | 30,696 | 2 | 1,136 |
| test_s1 | 663,106 | 2,311,785 | 1 | 218 | 1 | 218 |
| test_s2 | 1,871,330 | 6,843,339 | 106 | 14,953 | 2 | 690 |
| test_s3 | 1,945,701 | 7,243,924 | 113 | 16,799 | 2 | 778 |
| **total** | **11,990,643** | **43,252,803** | **133** | **90,100** | **2** | **4,336** |

The `train_s1` / `test_s1` rows showing **1 mixed type** are a truncation artefact, not a data
fact: those two files have the smallest US `name_tokens` denominators, so their top-4000 window
is proportionally shallow and only `24hr` (3,657, very high count) survives the cut. The union
across files recovers all 133. This is direct evidence that **single-file reads are unsafe for
this question** and is worth flagging to anyone auditing another country.

---

## 1. Full US mixed-token census — 133 types, each classified

Classification key, per work order item 1:
**(a) genuine leetspeak — must keep translating**; **(b) real token — guard should exempt**;
**(c) genuinely ambiguous — flagged, not forced.**

### 1a. The 131 types that must KEEP translating (85,764 occ)

Every one of these is a real English word spelled with a leet digit, and **all 131 have a
plain-form counterpart already present in the US name-token list**, so they merge correctly.
The 20 largest:

| token | → | occ | plain form occ | ratio | verdict |
|---|---|---|---|---|---|
| `c0m` | com | 2,855 | 403,355 | 0.007 | (a) genuine leet |
| `5ervices` | services | 2,707 | 257,069 | 0.011 | (a) |
| `ass0ciates` | associates | 1,817 | 266,314 | 0.007 | (a) — also `NAME_CANON`→`assoc` |
| `denta1` | dental | 1,652 | 106,308 | 0.016 | (a) |
| `hea1th` | health | 1,576 | 203,854 | 0.008 | (a) |
| `fami1y` | family | 1,395 | 99,491 | 0.014 | (a) |
| `5ervice` | service | 1,357 | 129,953 | 0.010 | (a) → `NAME_CANON`→`services` |
| `0f` | of | 1,345 | 308,735 | 0.004 | (a) — see §1c, the one arguable case |
| `6roup` | group | 1,179 | 438,519 | 0.003 | (a) |
| `l1c` | llc | 1,119 | 2,306,237 | 0.000 | (a) → `NAME_STOP`, dropped from core |
| `c1inic` | clinic | 1,042 | 157,602 | 0.007 | (a) |
| `c0rp` | corp | 1,022 | 471,416 | 0.002 | (a) → `NAME_CANON`→`corp`→`NAME_STOP` |
| `capita1` | capital | 1,013 | 82,771 | 0.012 | (a) |
| `visi0n` | vision | 945 | 55,424 | 0.017 | (a) |
| `r0cky` | rocky | 859 | 55,109 | 0.016 | (a) |
| `chir0practic` | chiropractic | 853 | 52,919 | 0.016 | (a) |
| `m0untain` | mountain | 850 | 58,186 | 0.015 | (a) |
| `5ummit` | summit | 826 | 97,174 | 0.009 | (a) |
| `at1antic` | atlantic | 823 | 59,907 | 0.014 | (a) |
| `physica1` | physical | 818 | 54,878 | 0.015 | (a) |

Remaining 111 types (occ 48,479) are the same pattern at lower mass — `va1ley`→`valley`,
`regi0nal`/`regiona1`→`regional`, `piedm0nt`, `cardi0logy`/`cardio1ogy`, `dermat0logy`,
`si1ver`, `uro1ogy`, `0rthopedic`, `crysta1`, `wi1liams`, `superi0r`, `se1ect`, `behavi0ral`,
`onco1ogy`, and so on. **Full list is machine-readable in the sidecar** (`us_mixed_tokens`),
because inlining 133 rows would triple this document's length for no analytical gain.

Two structural facts about this block, both worth stating because they bound the risk:

- **Every one of the 131 has a plain-form counterpart.** The 131 ratios occupy a band of
  **min 0.00049, median 0.0105, max 0.0189** — a tight, entirely-below-0.02 cluster, matching
  D121's all-country band (median 0.009, max 0.019) exactly. There is no second cluster.
- **The US is 95.2% clean by mass in this column**: 85,764 / 90,100 = 95.19% load-bearing.

### 1b. The 2 types the guard already exempts (4,336 occ) — both CONFIRMED corrupt

| token | → | occ | plain form | class |
|---|---|---|---|---|
| `24hr` | `2ahr` | **3,657** | **0 — does not exist** | (b) real token: 24-hours notation |
| `1st` | `lst` | **679** | **0 — does not exist** | (b) real token: English ordinal |

Both have **zero** plain-form counterpart anywhere in the US name column, which is the
strongest single indicator of corruption available in this profile (see §3).

### 1c. Category (c) — genuinely ambiguous, reported rather than forced

**`0f` → `of` (1,345 occ). CONFIRMED as correct leet, but the only one I would call arguable.**

- It is the single-token **`^\d+[a-z]$` shape** in the US mixed population (1 type, 1,345 occ).
- The word is `of` — a pure function word, in `NAME_STOP` (normalize.py:147), so the token is
  **dropped from `core` regardless** of whether LEET fires. The translation is behaviourally
  inert.
- Danger if it were ever exempted: `0f` would survive as a distinct token, entering
  `keys.py:33`'s `nt` list (length ≥ 2 passes), creating a spurious blocking key. That is
  strictly worse than the current behaviour.
- **Verdict: leave it translating. No guard alternative should match `^\d+[a-z]$`,** because
  that shape also matches the `1a`/`2b`/`3a`-style address suite designators (8,877 US addr
  occ, §2) and would begin eating legitimate leet the moment the shape is relaxed. This is a
  concrete reason the guard's 3 alternatives are the right *number*.

**`c0` → `co` (582 occ) and `dd5` → `dds` (542 occ)** are the only two `^[a-z]{1,3}[0-9]{1,2}$`
---

## 2. Per-digit US damage ranking (work order item 3) — the risk quantification

Method: for each LEET key, split the US mixed mass into **load-bearing** (correct leet, must
keep working) and **damage** (one of the 2 confirmed corrupt types), counting a type under
every digit it contains. A type containing two keys would be double-counted — **measured: zero
US mixed types contain a repeated leet key**, consistent with D087 §3.

| key | load-bearing types | load-bearing occ | damage types | damage occ | **US damage share** | rank |
|---|---|---|---|---|---|---|
| **`4`** | **0** | **0** | 1 | **3,657** | **100.0 %** | **1 (worst)** |
| `1` | 46 | 28,216 | 1 | 679 | **2.3 %** | 2 |
| `0` | 53 | 34,401 | 0 | 0 | 0.0 % | 3 (tied) |
| `5` | 19 | 14,302 | 0 | 0 | 0.0 % | 3 (tied) |
| `6` | 7 | 4,933 | 0 | 0 | 0.0 % | 3 (tied) |
| `8` | 6 | 3,912 | 0 | 0 | 0.0 % | 3 (tied) |
| `3` | 0 | 0 | 0 | 0 | **n/a — no US occurrences** | — |
| `7` | 0 | 0 | 0 | 0 | **n/a — no US occurrences** | — |

Arithmetic check: `34,401 + 28,216 + 0 + 0 + 14,302 + 4,933 + 0 + 3,912 + 3,657 + 679 = 90,100` ✓
equals the US mixed total. Load-bearing `85,764` + damage `4,336` = `90,100` ✓.

**This table is the answer to "how risky is any future table edit", and the answer is
sharply country-dependent:**

- **US-only view:** deleting key `4` would remove 3,657 corruptions and **0** regressions.
  Deleting key `1` would save 679 and cost 28,216 across 46 types. Keys `0/5/6/8` are pure
  upside and must not be touched.
- **Global view (the constraint that actually binds):** key `4` is **not** deletable, because
  France's `4l` (1,943) is its sole remaining dependent. Key `3` and key `7` have no US mass
  at all, so D121's "100% harmful" finding about them is **entirely a France finding**
  (869 + 9 = 878, all French ordinals). Nothing in the US data bears on the `3`/`7` decision.
- **Therefore: the US ranking cannot be used to justify any table edit.** It ranks the damage;
  it does not authorise the edit. The call-site guard (D087 §6) remains the only correct fix,
  and it is already written.

### Does any US class need a guard shape beyond the current three alternatives? (item 4)

**No. Measured, not assumed.** The written guard is:

```python
_LEET_GUARD_RE = re.compile(r"^(?:\d+(?:er|ere|eme|e)|\d+(?:st|nd|rd|th)|\d+hr)$")
```

Applied to the 133 US mixed types it matches **2** (4,336 occ) and misses 131 (85,764 occ).
Its three alternatives break down over the US population as:

| alternative | US types matched | US occ | note |
|---|---|---|---|
| `\d+(?:er\|ere\|eme\|e)` | **0** | **0** | French-only; contributes nothing to the US |
| `\d+(?:st\|nd\|rd\|th)` | 1 (`1st`) | 679 | needed for the US |
| `\d+hr` | 1 (`24hr`) | 3,657 | needed for the US; single member of its family |

So the guard's US-relevant content is exactly two alternatives, and **the French-suffix
alternative is dead weight in the US window** — kept only because it is required for France's
1,111, and because `normalize_name` has no `country` parameter so the alternatives cannot be
country-selected anyway.

For completeness I ran every shape family the work order named against the US mixed population
in **both** columns. Name side is where LEET fires; address side is where it never fires.

| family | pattern | US **name** result | US **address** result |
|---|---|---|---|
| units | `^\d+(h\|hr\|min\|kg\|g\|ml\|cm\|l\|m\|s\|y)$` | 1 type `24hr` 3,657 (known) | 0 |
| model codes, digit-lead | `^[0-9]{1,4}[a-z]{1,3}$` | 9 types 9,590 (8 genuine leet + `1st`) | 145 types 519,989 (all ordinals) |
| model codes, alpha-lead | `^[a-z]{1,3}[0-9]{1,4}$` | 2 types 1,124 (`c0`, `dd5`) | 0 |
| versions | `^v[0-9]` / `^[0-9]d$` | **0 / 0** | **0 / 0** |
| resolutions | `^[0-9]{3,4}p$`, `^4k$` | **0** | **0** |
| year suffixes | `^[0-9]+[xk]$` | **0** | **0** |
| fractions | `^[0-9]+of[0-9]+$` | **0** | **0** |
| grades | `^[a-z][0-9]{1,2}$` | 1 type `c0` 582 (correct) | 0 |
| suite / unit designators | `^[0-9]+[a-z]$` | 1 type `0f` 1,345 (correct) | **8 types 8,877** |
| two-or-more-digits | `^[0-9][0-9]` | **1 type `24hr` 3,657** | 108 types 342,968 |
| digit-lead, any alpha tail | `^[0-9]+[a-z]+$` | 36 types 28,866 | 145 types 519,989 |

**`A4`, `S20`, `X1`, `4K`, `1080p`, `v2`, `3d`, `5kg`, `30min`, `100g`, `2k`, `98`, `1of2`,
`ste 1b`, `apt 4a` — every one of the shapes the work order named is measurably ABSENT from
the US mixed population in both columns** (not "small": zero types, zero occurrences).
The two nearest real neighbours are `24hr` (a unit, already known and already guarded) and
`0f` (already argued in §1c as correct leet). This is a stronger negative result than D121's
"clean bill of health", because I ran it on the US specifically and on both columns.

---

## 3. Why `24hr` and `1st` are provably corrupt — the zero-plain-form test

This is a cleaner discriminator than D090's ratio test, and it is decisive on the US data.

**Test:** a mixed token is corrupt if its LEET output is **not present as a plain name token
anywhere in the same country's name column**. A genuine leetspeak token spells a word that
someone else also spells normally, so its output must exist. A corrupted token spells nothing.

| country | mixed types | types with **no** plain-form output | which |
|---|---|---|---|
| **US** | 133 | **2** | `24hr`→`2ahr` 3,657; `1st`→`lst` 679 |
| India | 127 | (2nd is the known control) | per D121 |
| France | 24 | per D087/D121 | the 5 ordinals |

- US `2ahr` as a plain name token: **0**. US `lst` as a plain name token: **0**.
- Both US address-side: `2ahr` = **0**, `lst` = **0**.
- The other **131 US types all pass**, with ratios clustered in 0.00049–0.0189.

**This closes the search.** The gap between the highest clean ratio (**0.0189**) and the
corrupt set (both members of which sit at *infinite* ratio, denominator 0) is not a 6.3x empty
band as in D121 — for the US it is a **degenerate** one, because the two defects have *zero*
denominator rather than merely a high ratio. **No US corruption class can hide in that gap.**

---

## 4. NEW FINDING N5 — the `first`/`1st` name-side divergence (US, and it is a MISMATCH defect)

This is the item the work order asked me to push hardest on, and pushing on it turned up
something the three prior audits did not name. **I am not re-litigating D087's `1st`
asymmetry — I am reporting an additional, larger asymmetry underneath it.**

### 4a. The code asymmetry

- `ADDR_CANON_COMMON` (normalize.py:184) contains
  `"first": "1st", "second": "2nd", "third": "3rd", "fourth": "4th", "fifth": "5th"`.
  This is consulted at normalize.py:347 inside **`normalize_address`**.
- **`NAME_CANON` (normalize.py:109-142) contains no ordinal entry at all.** I read all 34
  lines; there is no `first`, `second`, `third`, `1st`, or `2nd`. It is consulted at
  normalize.py:281 inside **`_name_tokens`**.

So the *same* canonicalisation exists on one side of the pipeline and is absent on the other.

### 4b. What that does to the US data — three spellings where there should be one

Measured in the US top-4000 windows (`name_tokens` / `addr_tokens`, six files):

| literal | US **name** occ | US **address** occ | name-side fate | address-side fate |
|---|---|---|---|---|
| `first` | **61,068** | 15,800 | stays `first` (no canon, no leet) | → **`1st`** (canon line 184) |
| `1st` | **679** | **16,478** | → `lst` (LEET) | stays `1st` |
| `lst` | 0 | 0 | — | — |

Address side: `first` and `1st` **converge** — both become `1st`. Address-side `1st` mass is
therefore 15,800 + 16,478 = **32,278**.

Name side: they **diverge three ways** — `first` (61,068), `lst` (679, garbage), and after the
guard is applied, `1st` (679, correct). Even *with the guard in place*, a US business named
`1st Choice Realty` and one named `First Choice Realty` produce name tokens `1st` and `first`
— **still two different tokens.** The guard fixes the corruption; it does **not** fix the
divergence. **The guard is necessary but not sufficient.**

### 4c. Why this is a mismatch defect, not a corruption defect

Same mechanism D087/D121 traced, now with the larger US number:

- Name keys are built from LEET/canon-processed `ncore` (`keys.py:33-34`); address keys from
  raw `atoks` (`keys.py:39-43`).
- The **kind-0 key at `keys.py:60` XORs the two** (`th ^ (ah // 2)`), so it can only form when
  a name token and an address token agree.
- IDF features are **separate tables**: `wn` over `ncore` vs `name_idf` (`features.py:128`),
  `wa` over `atoks` vs `addr_idf` (`features.py:129`). **The address side can never rescue the
  name side.**

Concretely, a US business whose name carries the ordinal and whose address carries it cannot
form the kind-0 key, because the name side is `first`/`lst` and the address side is `1st`.

**US-side exposure quantification:**

- Address-side `1st` mass that the name side cannot join: **32,278** occurrences.
- Name-side mass stranded on a spelling that does not match the address side:
  `first` **61,068** + `lst` **679** = **61,747** occurrences.
- Ratio: address-side is only **0.52x** the name-side stranded mass (32,278 / 61,747 = 0.52) — the
  asymmetry runs *opposite* to France's `3eme` case (where the address side dominates), because
  the US writes the ordinal as a **word** in names far more often than as a numeral.

**This is a bigger US number than the `1st` corruption itself (61,747 vs 679, a 91x ratio), and
the written guard does not touch it.** I am explicitly *not* proposing a `NAME_CANON` edit as
part of the LEET fix — that is a different table with its own risk surface, and `NAME_CANON`
is consulted at line 281, *after* `translate`, so an ordinal entry there would only ever see
already-leeted tokens. But it should be on someone's desk, and it is the single most
consequential thing I found.

**Cross-check against D084 (c03, `ADDR_CANON_COMMON` for the US), which independently supports
this.** D084 classified the canon keys whose canonical value occurs **zero** times in the US
corpus (the "no-fusion" class, ceiling 295,721 = 0.5398% of US listed address mass). The
ordinal key `first`->`1st` is **not** in that list — because `1st` *does* occur 16,478 times on
the US address side. So D084's measurement independently confirms that this particular canon
entry **is** fusing productively on the address side, which is exactly the half of the
pipeline that works. The defect is that its name-side counterpart does not exist. D084's
verdict — *do not extend `ADDR_CANON_COMMON` for the US* — is therefore **not in tension**
with mine: the table is not the problem here, the *missing mirror in `NAME_CANON`* is.

**Honest limits on N5.** (i) These are **token occurrences, never rows** — the number of US
*rows* whose name contains an ordinal is **not derivable** from this profile and I do not
quote one. (ii) `61,068` is a count of the literal `first` in the *raw* name column, not of
ordinal *meanings*; some fraction of US businesses named "First ..." use it as an ordinal and
some as a brand word ("First Choice", "First National" are overwhelmingly ordinal, but I did
not classify them and **cannot** from this profile). (iii) Whether adding `"first": "1st"` to
`NAME_CANON` would actually improve matches is **SPECULATIVE** — it could equally help or
hurt, and testing it needs a scored run, which is outside my remit. I flag the divergence as
**CONFIRMED**; I flag the *fix direction* as **SPECULATIVE**.

---

## 5. Answers to the work order's questions, ranked

| # | question | answer | class |
|---|---|---|---|
| 1 | Which US LEET entries are dead weight? | **None that the guard doesn't already handle.** `@`/`$` are unreachable dead code (D087 D3), but that is not US-specific. | CONFIRMED |
| 2 | Which tokens appear that the dictionary does not handle but should? | **None.** The full 133-type US census yields exactly 2 defects, both already covered by the written guard. | CONFIRMED (window) |
| 3 | Which entries could collide across countries? | **No new collision.** The US corrupt outputs `2ahr` and `lst` are both absent as plain tokens in every country, so they shadow nothing. The only genuine cross-country convergence in the defect set is `1st` (US 679 + India 381), and that is *desirable* — one shape guard covers both. | CONFIRMED |
| 4 | Does any US class need a guard shape beyond the current 3? | **No.** Every shape family the work order named is empty in the US. Adding a 4th alternative can only add false exemptions. | CONFIRMED |
| 5 | Is the `1st` asymmetry real for the US? | **Yes, and larger than stated** — because `ADDR_CANON_COMMON` has `first→1st` and `NAME_CANON` does not, the US name side strands **61,747** occurrences against **32,278** address-side. See §4. | CONFIRMED (asymmetry) / SPECULATIVE (fix) |

**Bottom line for the implementer: change nothing.** The written guard
`_LEET_GUARD_RE` at `patch_upstream/src/normalize.py:296-298` covers 4,336 of 4,336 US
corrupted occurrences, exempts **0** of the 131 legitimate leet types, and is already
token-anchored and country-blind as the hard constraints require. Widening it is the only
remaining action available, and widening it is **not supported by any US evidence**.

---

## 6. Gaps and limits — stated, not estimated

- **Top-4000 truncation, and it bites unevenly.** `name_tokens`/`addr_tokens` are the top 4000
  per country per file (`build_profile.py:27,140`) with periodic hapax pruning
  (`build_profile.py:45-49,130-133`). **8–18% of name-token mass is outside the window**
  (D121's coverage table). My §0 per-file table shows this is not even uniform: two of six
  files expose only **1** US mixed type. **Every type list in this report is a floor, and every
  "0 types" result is a floor too** — it means "not in the measured window", never
  "does not occur". `A4`/`S20`/`v2`/`4K` etc. are absent *from the window*.
- **Token occurrences, not rows.** Every count here is a token-occurrence count from
  `name_tokens`/`addr_tokens`. **No row count is quoted for any finding**, and the per-row
  impact of the 4,336 US corruptions is **not derivable** from this profile. US row counts
  appear in §0 only as denominators for the truncation argument.
- **Profile flattening.** `build_profile.py:111,127` applies
  `TOKEN_RE = [a-z0-9]+` to the raw lowercased string with **no accent stripping**, and
  `addr_tokens` is computed **per comma-component** (`:126-127`) then summed. Component
  structure is not visible. `ADDR_CANON_COMMON` is likewise not applied by the profiler, so
  the 15,800 address-side `first` occurrences are the *raw* count — the post-canon figure
  (32,278) is my **inference** from reading normalize.py:347, and is marked as such.
- **No raw TSV was read** (hard constraint). Nothing here is verified against source rows.
- **Not collected, named as gaps rather than estimated:** (i) rows-per-token; (ii) the
  untruncated tail mass; (iii) which US name tokens containing `first` use it as an ordinal
  vs a brand word; (iv) any scored-run evidence for whether a `NAME_CANON` ordinal entry helps
  or hurts.
- **Not re-derived** (per work order and FLEET_BRIEF): postal/`pin`, `pin_eq`, `alt_tset`,
  `US_STATES`/`IN_STATES`/`FR_REGIONS` expansion, France blocking caps, address component
  order, the ligature defect, the retracted French function-word finding, D084's
  `ADDR_CANON_COMMON` verdict (read and cross-checked in §4c, not re-derived), and D087 §4e's
  adjudication that `4l` is not a defect.




types. Both are correct: `c0`→`co` is `NAME_CANON`→`co`→`NAME_STOP` (dropped), and `dd5`→`dds`
is literally in `NAME_CANON` (normalize.py:140). No action.

**`a1l` → `all` (692 occ)** deserves a note because it *looks* like a grade or a suite
designator. It is not: `all` has 54,275 plain occurrences and the ratio is 0.013, squarely in
the clean band. Correct leet for the common word "all". No action.
