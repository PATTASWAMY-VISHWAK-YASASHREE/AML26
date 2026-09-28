# D121 — Remaining gaps in `LEET` after the France-postcode and France-region hypotheses died

**Task type:** re-audit for *residual* defects. Two structural claims from the work order
are confirmed (dead keys, country-blindness); **one NEW defect class is found**; one
long-standing blanket claim in the fleet brief is **contradicted**.

**Sources:** `_upstream/src/normalize.py`, `keys.py`, `features.py` (read-only); the six
profile JSONs in `analysis_out/profile/`. No raw `*.tsv` opened. No network.

---

## Headline

1. **NEW DEFECT N4 — keys `3` and `7` are 100 % harmful and 0 % useful.** The fleet brief
   states *"Every LEET key is LOAD-BEARING."* That was only ever established for keys `1`
   and `4`. Extending the per-key test to all eight digit keys shows `3->e` and `7->t` fire
   on **3 types / 878 occurrences, of which 878 (100 %) are corruptions and 0 are correct
   expansions**. They are the only two entries in the table with a strictly negative
   sign. Every other key has a damage share between 0 % and 65.3 %.
2. **A tight, fully-decisive discriminator exists and D090 only ever ran it on France.**
   Applying the *ratio-anomaly* test (mixed count / plain-form count) to **all 284 mixed
   types** rather than France's 24 isolates **exactly** the known defect set and nothing
   else. The 274 non-anomalous types occupy a ratio band of **median 0.009, p25 0.006,
   p75 0.013, max 0.019** — with an empty gap before the first anomaly at **0.119**.
   This is strong evidence that **no fourth corruption class hides in the un-flagged tail**.
3. **CLEAN BILL OF HEALTH for the unit / model-code / version / grade / fraction shapes the
   work order asked about.** `24hr` is the *only* member of its family in the whole
   dataset; the entire address-side mixed-token mass (2,620,773 occurrences) contains
   **zero** `24h`/`7kg`/`30min`/`A4`/`4K`/`1080p`/`v2`/`2k`/`1of2` forms outside the
   ordinal and street-slot families. **The defects are exactly three classes and they are
   already all known.**

---

## 1. Reproduction of the denominator

I recomputed the mixed-token universe from scratch and it reproduces D087 exactly.

Trigger condition is `normalize.py:279` — a name token must contain **both** a letter and a
digit. Applying the `LEET` map to every such token in `name_tokens` across all six files:

| Country | mixed types | mixed occurrences |
|---|---|---|
| US | 133 | 90,100 |
| India | 127 | 80,735 |
| France | 24 | 5,307 |
| **total** | **284** | **176,142** |

Identical to D087 §4 (284 / 176,142). Independent agreement on the denominator.

---

## 2. NEW DEFECT N4 — keys `3` and `7` are pure loss

For each of the eight digit keys, split the observed mixed mass into **load-bearing**
(correct leet, must keep working) and **damage** (corrupted). Corrupt set =
`{3eme, 3e, 7eme, 1er, 1ere, 1st(US), 1st(India), 24hr}`.

| key | load-bearing types | load-bearing occ | damage types | **damage occ** | **damage share** |
|---|---|---|---|---|---|
| `0` | 110 | 71,527 | 0 | 0 | **0.0 %** |
| `1` | 85 | 47,775 | 4 | 1,293 | 2.7 % |
| **`3`** | **2** | **869** | **2** | **869** | **100.0 %** |
| `4` | 2 | 5,600 | 1 | 3,657 | 65.3 % |
| `5` | 54 | 33,541 | 0 | 0 | **0.0 %** |
| `6` | 13 | 7,373 | 0 | 0 | **0.0 %** |
| **`7`** | **1** | **9** | **1** | **9** | **100.0 %** |
| `8` | 16 | 9,195 | 0 | 0 | **0.0 %** |
| | | | | **5,828** | ✓ sums to the established total |

Arithmetic: `869 + 9 = 878`; `1293 + 869 + 3657 + 9 = 5,828` ✓ matches the D087/D090 total.

**The complete set of name-side tokens in the dataset containing `3` or `7`:**

| country | token | -> LEET output | occ | verdict |
|---|---|---|---|---|
| France | `3eme` | `eeme` | 748 | CORRUPT |
| France | `3e` | `ee` | 121 | CORRUPT |
| France | `7eme` | `teme` | 9 | CORRUPT |

That is the **entire** set — three types, no others, in any country, in any of the six files.
Per-file confirmation that nothing hides in one slice: `3eme` = 120/311/317 and `3e` =
21/47/53 across test_s1/s2/s3; `7eme` = 9 in test_s1 only.

**Consequence.** `3->e` and `7->t` are **not load-bearing at all on this dataset**. Unlike
key `1` (which carries `de1hi` 1,674, `denta1` 1,652, `techno1ogies` 1,288 and 82 other
types) and key `4` (which carries `4l` 1,943), keys `3` and `7` carry **nothing but the
damage they cause**. Deleting those two entries would remove 878 corrupted occurrences at
**zero measured regression cost**.

**Confidence and the limit on it — this is a floor, not a census.** `name_tokens` is the
top 4000 per country per file (`build_profile.py:27,140`). Realised coverage of true
name-token mass, `sum(listed) / by_country[c].name_tokens`:

| file | US | India | France |
|---|---|---|---|
| train_s1 | 87.89 % | 90.40 % | — |
| train_s2 | 82.47 % | 83.03 % | — |
| train_s3 | 82.13 % | 84.10 % | — |
| test_s1 | 87.96 % | 90.42 % | 91.98 % |
| test_s2 | 83.33 % | 83.93 % | 90.23 % |
| test_s3 | 83.07 % | 85.05 % | 89.61 % |

So **8–18 % of name-token mass is outside the top-4000 cut** and is not measurable here. A
correct leet expansion using `3` or `7` (e.g. a hypothetical `c3o` -> `ceo`) could sit in
that tail. The honest claim is: **in the top-4000 window, `3` and `7` are 100 % harmful;
in the full corpus they are harmful on every occurrence measured, and the tail is
unmeasured.** Classification: **CONFIRMED for the measured window, with the tail named as a
gap.** This is a *targeted-table* claim, not a licence to delete keys on the strength of a
truncated list — which is exactly the trap the brief's own top-4000 warning describes.

> The brief's blanket sentence "Every LEET key is LOAD-BEARING" should be **narrowed**:
> keys `0`, `5`, `6`, `8` are load-bearing with zero damage; key `1` is load-bearing with
> 2.7 % damage; key `4` is load-bearing with 65.3 % damage; **keys `3` and `7` are not
> load-bearing at all in the measured window.**

---

## 3. The ratio-anomaly discriminator, run on all 284 types (new coverage)

D090 applied a ratio test — mixed count / plain-form count — but **only to France's 24
types**. I applied it to all 284 across all three countries. Criterion, fully traceable: for
mixed token `m` with LEET output `o` in country `c`, `ratio = n(c,m) / n(c,o)`, both counts
summed over the six `name_tokens` lists. A high ratio means the "leet" form outnumbers the
word it claims to expand to, which is the signature of a non-leet token.

**Result: exactly 10 types breach the threshold, and they are precisely the known set.**

| country | mixed | -> out | mixed n | plain n | ratio |
|---|---|---|---|---|---|
| US | `24hr` | `2ahr` | 3,657 | 0 | **INF** |
| France | `4l` | `al` | 1,943 | 645 | 3.012 |
| France | `3eme` | `eeme` | 748 | 0 | **INF** |
| US | `1st` | `lst` | 679 | 0 | **INF** |
| India | `1st` | `lst` | 381 | 0 | **INF** |
| India | `2nd` | `2nd` | 253 | 253 | 1.000 |
| France | `1er` | `ler` | 131 | 0 | **INF** |
| France | `3e` | `ee` | 121 | 1,017 | 0.119 |
| France | `1ere` | `lere` | 102 | 9 | 11.333 |
| France | `7eme` | `teme` | 9 | 0 | **INF** |

`4l` is already adjudicated **not a defect** by D087 §4e (it converges with India's
`a1 -> al`, 272); `2nd` is the control (contains `2`, which is not a LEET key, so it is
untouched). The remaining 8 rows are the 5,828 known corruptions.

**The gap that makes this decisive.** The other 274 types sit in an extremely tight band:

| n | min | p25 | median | p75 | max |
|---|---|---|---|---|---|
| 274 | 0.000 | 0.006 | **0.009** | 0.013 | **0.019** |

Highest clean ratio **0.019**; lowest anomaly **0.119** — a **6.3x empty gap** with no type
in it. Only four clean types are below 0.0005, and all four are explained: `1imited`
(1,255 / 3,642,767), `l1c` (1,119 / 2,306,237), `1td` (241 / 1,675,238), `5ci` (27 / 63,630)
— all round to 0.000 and all have enormous plain denominators.

**Inference, marked as such:** because the clean population is this tightly clustered and the
gap is empty, a fourth corruption class of comparable mass would have had to show a ratio
outside a 0.000–0.019 band. None does. **I therefore find no evidence of an uncatalogued
defect in the measured window.** The 8–18 % unmeasured tail remains the honest caveat.

---

## 4. The shape classes the work order asked about — all clean

I searched both `name_tokens` and `addr_tokens` (2,620,773 mixed address occurrences across
351 types — the untreated side) for each named family.

| family | pattern | name-side result | address-side result |
|---|---|---|---|
| units | `^\d+(h\|hr\|min\|kg\|g\|ml\|cm\|l\|m\|s\|y)$` | **4 types: `24hr` 3,657 (known), `4l` 1,943 (adjudicated OK), `0m` 403, `5s` 238** | 0 |
| model codes | `^[a-z]{1,3}\d{1,4}$` / `^\d{1,4}[a-z]{1,3}$` | all correct leet (`denta1`, `capita1`, `physica1`…) | dominated by ordinals + Indian street slots |
| versions | `^v\d` / `\d+d$` | 0 | 4 types, `2d` 3,146 / `1d` 2,975 (India street slots) |
| resolutions | `4K`, `1080p` | **0 — not in the top 4000, any country, either column** | 0 |
| year suffixes | `^\d+[xk]$` | **0** | 0 |
| fractions | `^\d+of\d+$` | **0** | 0 |
| grades | `^[a-z]\d{1,2}$` | 40 types, all genuine leet | 40 types, all correct |

**Reading of each verdict.** `24hr` is a real unit and is corrupt — but it is already known,
and it is the **only** token in the dataset with two or more digits (`types = 1`). There is
no `24h`, no `7kg`, no `30min`: the unit family D087 identified is a **family of exactly
one member**, so a `^\d+(hr?)$`-style guard is sufficient and general. Model codes, version
strings, resolutions, year suffixes, fractions and grades produce **no new defect** — the
alphanumeric grade tokens in India (`a1` 16,283, `b1` 13,325, `a2` 11,135, `b2` 9,346, `a4`
4,294) are leet for genuine leet (`a1 -> al` 272 is confirmed correct by D087 §4e) and live
on the address side where LEET never fires.

**On digits `2` and `9`, which are unmapped:** only 2 of 284 name types contain them
(`24hr` 3,657 and `2nd` 253). Leaving them unmapped is correct and should not change.

---

## 5. NEW measurement — the address-side English-ordinal family is 1,513x the name side

D087 §4c sampled only `1st` and `2nd` on the address side. I enumerated the family
exhaustively with `^\d+(st|nd|rd|th)$` over `addr_tokens`, all six files:

**184 types, 1,986,432 occurrences** — India 1,475,320 (47 types) / US 511,112 (137 types).
This is **75.8 % of all 2,620,773 mixed address occurrences**. Top of the list:
`2nd` 324,528 · `1st` 305,356 · `3rd` 226,631 · `4th` 146,972 · `5th` 92,741 · `6th` 62,806 ·
`7th` 55,678 · `8th` 38,445 · `9th` 35,193 · `10th` 26,781 · `11th` 20,597.

Against this, the **name**-side occurrences of the same regex are **3 country-token entries
/ 1,313 occurrences**: `1st` = 679 (US) + 381 (India) and `2nd` = 253 (India). I checked
`3rd`, `4th`, `5th`, `6th`, `7th`, `8th`, `9th`, `10th`, `11th` explicitly on the name
side: **all zero, every country, all six files.**

This sharpens D087's "not in the top 4000" observation into a positive statement about the
measured window: **the name-side English ordinal family has exactly two distinct literals
(`1st`, `2nd`), and exactly one of them is corrupt**, because `2nd` contains the unmapped
digit `2`. Only `1st -> lst` needs a guard. A `^\d+(st|nd|rd|th)$` guard is correct in
shape and costs nothing measurable; `^\d+st$` would be equally sufficient here but is
needlessly narrow if the tail behaves like the window.

**The asymmetry is the finding.** 1,986,432 address occurrences of ordinals are preserved
verbatim; 1,060 name occurrences are destroyed. `normalize.py:342-349` routes address
tokens to `canon.get(t, t)` with no `translate`, so this is structural, not incidental.
Ratio: **1,874 : 1** measured against the 1,060 destroyed occurrences, or **1,513 : 1**
against all 1,313 name-side occurrences. The same literal `1st` therefore yields `lst` in
`ncore` and `1st` in `atoks`, and the two columns index separate IDF tables
(`features.py:128-129`) and separate key namespaces (`keys.py:33` name vs `keys.py:39-43`
address), so the address side can never rescue the name side.


---

## 6. Cross-country: is any class country-specific?

**No — and this is the load-bearing design constraint.** The three corruption classes span
all three countries:

| class | France | US | India |
|---|---|---|---|
| French ordinals `3eme`/`3e`/`1er`/`1ere`/`7eme` | **1,111** | 0 | 0 |
| English ordinal `1st -> lst` | 0 | **679** | **381** |
| `24hr -> 2ahr` | 0 | **3,657** | 0 |

Corrupted mass: **US 4,336 (74.4 %)**, France 1,111 (19.1 %), India 381 (6.5 %).
`4,336 + 1,111 + 381 = 5,828` ✓.

The scored country is France, and France is the **smallest** of the three contributors to
this defect. A France-scoped guard would fix 19.1 %. D087 already established this and I
reproduce it exactly.

The structural reason no country-scoped guard exists: **`normalize_name(raw)` takes no
country parameter** (`normalize.py:285`) and `prep.py:12` supplies none, so country is not
in scope anywhere on the LEET path. A country guard is not implementable without changing a
public signature. This is a code fact, re-verified here, not an inference.

---

## 7. Mechanism — how the corruption costs matches (traced, not assumed)

Guarding against the profile-flattening trap: I traced each corrupted token to the code
that consumes it, so no claim below rests on a flattened count.

- `normalize.py:280` corrupts the token inside `_name_tokens`; `normalize.py:306` puts the
  corrupted token into `core`; nothing downstream reverses it.
- `keys.py:33-34` builds `nt` from `ncore`. The filter is `len_chars >= 2` only, so
  `eeme`, `lst`, `2ahr`, `teme` **all become live blocking keys** as garbage strings.
- `keys.py:39-43` builds `alph` from `atoks` (raw address tokens, untranslated).
- `keys.py:60` forms the kind-0 key as `th ^ (ah // 2)` — an XOR of a name-token hash and
  an address-token hash. Since `lst != 1st`, that key **cannot form** for a business whose
  name carries `1st` and whose address also carries `1st`.
- `features.py:128-129` computes `wn` from `q_ncore`/`s_ncore` against `name_idf` and `wa`
  from `q_atoks`/`s_atoks` against `addr_idf` — **separate tables**, so the preserved
  address token cannot offset the corrupted name token.

The corrupted strings are also **not** in `NAME_CANON` and **not** in `NAME_STOP`
(`normalize.py:306` drops only `NAME_STOP`), so each survives into the features as a unique
garbage token rather than being cleaned.

---

## 8. Verdict on the work order's three questions

1. **Which entries are never or almost never fired (dead weight)?** **`@` and `$` — 2 of 10
   entries — are unreachable dead code**, confirmed by D087 §D3 and re-verified here:
   `_non_alnum = re.compile(r"[^a-z0-9]+")` (`normalize.py:269`) splits on line 276 before
   `translate` runs on line 280, so the token is guaranteed `[a-z0-9]` only. Beyond those
   two, **no entry is dead weight**: every digit key fires on at least one observed token,
   the smallest being `7` (1 type, 9 occurrences). Keys `3` and `7` are *not* dead — they
   are worse than dead, they fire only to cause harm (§2).
2. **Which tokens appear that the dictionary does not handle but should?** **None found.**
   The three known classes are exhaustive in the measured window; the ratio test isolates
   them and nothing else (§3), and every shape family the work order named is empty or
   already correct (§4).
3. **Which entries could collide across countries?** **No cross-country collision exists
   in the data.** The corrupted *outputs* are mutually disjoint — `eeme`/`ee`/`ler`/`lere`/
   `teme` (French ordinals), `lst` (US + India, which is the *only* genuine cross-country
   convergence in the defect set and is desirable — the same fix covers both), `2ahr` (US
   only). No two countries' corruptions collide with each other or with a legitimate plain
   token: the `lst` output occurs **0** times as a plain name token in any country, so it
   does not shadow a real word. Of 43 output strings reached by more than one input
   spelling (52,901 occurrences), **not one contains a member whose plain form is absent** —
   the many-to-one merges are all genuine leet fan-in and all desirable.

---

## 9. Honest summary

**`LEET` is not broken beyond the three already-known classes, and I found no fourth
class.** The dictionary is a 10-entry character map with one call site, and its only real
failures are `3eme`/`3e`/`1er`/`1ere`/`7eme`/`1st`/`24hr`.

The one genuinely new result is **N4: keys `3` and `7` have a 100 % damage rate in the
measured window and no correct expansions at all** — which contradicts the blanket
"every LEET key is load-bearing" claim in the fleet brief and narrows it.

**The fix is still not in the table** (D087 §6 stands): the decision needs the whole token,
which a character map cannot express, and **96.7 % of mixed occurrences (170,314 /
176,142) are correct leet that must keep working.** Any change must be **token-anchored**
(`^...$`) and must **exempt rather than extend**, and it must be country-blind because
France contributes only 19.1 % of the damage.

## 10. Gaps and limits (stated so nothing here is over-read)

- **Top-4000 truncation.** 8–18 % of name-token mass is outside `name_tokens`. Every type
  list in this report is a **floor**. "Not in the top 4000" is never "does not occur."
  This is the specific limit on the N4 claim about keys `3` and `7`.
- **Token occurrences, not rows.** Every count here is a `name_tokens` / `addr_tokens`
  **token-occurrence** count. **No row count is quoted for any of them.**
- **Flattening.** `build_profile.py:111,127` applies `TOKEN_RE = [a-z0-9]+` to the raw
  lowercased string with **no accent stripping**, so every accented French word is chopped
  at its first accent (D090 §F4b). `1ère` appears as `1` + `re`, not as a token. Counts for
  accented forms are split across 2+ entries and are floors.
- **No raw TSV was read**, so `4l` (ratio 3.012, the one token D090 left `SPECULATIVE` and
  D087 adjudicated on convergence evidence alone) is **not independently re-litigated here**.
  I record D087's verdict and note it remains the least-evidenced item on the list.
- **Not collected:** the profile has no field that would let me count how many *rows*
  contain a given mixed token, nor the untruncated tail mass. Both are named as gaps
  rather than estimated.





