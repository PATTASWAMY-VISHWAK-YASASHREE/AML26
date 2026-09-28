# D095 — Ground-truth audit of `indic_token_dict.json`

**Task:** establish ground truth for the `indic_token_dict` table.
**Status:** complete. No change proposals (explicitly out of scope for D095).
**Path verified:** `_upstream/src/resources/indic_token_dict.json` — **EXISTS**, 47,788 bytes,
1,365 lines, 1,363 entries, no trailing newline. The work-order path is correct; the audit
below is valid.

---

# HEADLINE

**The table is not inert, but its *marginal* value is bounded by a number the profile cannot
measure — and for the scored country (France) the value is exactly zero.**

Three facts, in order of importance:

1. **The table is keyed 100% on native Brahmic script, never on Latin.**
   All 1,363 keys are pure codepoints in `U+0900-U+0D7F` across **9 scripts**. Zero keys
   contain a Latin letter, a digit, or ZWNJ/ZWJ. It therefore *cannot* fire on any
   transliterated-Latin text. It is a `Indic -> Latin` table and nothing else.

2. **Its entire output vocabulary already exists natively in the India data.**
   The table has **167 distinct Latin values** (169 distinct word-atoms after splitting the 4
   multi-word ones). **166 of those 169 atoms already appear as raw ASCII tokens in India's
   top-4000 `name_tokens`** (`analysis_out/profile/train_s1.json`), covering
   **2,212,001 / 2,955,338 = 74.85%** of the name-token occurrences listed.
   Consequence: the table **introduces no new vocabulary**. It can only *convert* rows that are
   already in Brahmic script, into a bucket the data is already in. Its entire contribution is
   the size of the Brahmic-script subset of India — **and that is a declared GAP (see section 6).**

3. **For France the value is 0, and this is provable, not inferred.** France has no rows in
   train, the table has no Latin keys, and France's rows are Latin French. The table cannot
   match a single French token. It is also **not country-scoped** (section 5) so it is loaded and
   evaluated on the France hot path for nothing.

> **Answering the work order's question 1 directly:**
> *How many DISTINCT tokens does it actually affect in the India data, out of how many India
> tokens?* -> **0 of the 8,000 listed (4,000 name + 4,000 addr), by construction — and that 0 is
> a MEASUREMENT ARTIFACT, not evidence of inertness.** `build_profile.py:28` tokenises with
> `TOKEN_RE = re.compile(r"[a-z0-9]+")`, which matches **zero characters** of a Brahmic string.
> Every token the profile can list is pure ASCII; every key in this table is pure Brahmic. The
> two sets are disjoint *by construction of the profile*, so this table is structurally
> **invisible** to every profile field the fleet has. Reading "0 tokens affected" as "inert"
> would be exactly the kind of plausible-but-wrong conclusion the fleet brief warns about.

---

# 1. Path verification

```
PS> Test-Path '_upstream\src\resources\indic_token_dict.json'
True
PS> Get-ChildItem '_upstream\src\resources'
Name                     Length
----                     ------
indic_token_dict.json    47788
```

It is the **only** file in `src/resources`. `_upstream/` was not modified (read-only
constraint honoured).

---

# 2. Entry count and value cardinality

Measured by parsing the file as UTF-8 (`ConvertFrom-Json`):

| Quantity | Value |
|---|---|
| Entries (key->value pairs) | **1,363** |
| Distinct keys | **1,363** (no duplicate keys) |
| Distinct values (canonical targets) | **167** |
| Distinct word-atoms in values (values split on space) | **169** |
| Empty or null values | **0** |
| Self-maps (key == value) | **0** |
| Values containing uppercase | **0** |
| Values not matching `^[a-z ]+$` | **0** |
| Keys containing a Latin letter | **0** |
| Keys containing a digit | **0** |
| Keys containing ZWNJ (U+200C) / ZWJ (U+200D) | **0** |
| Values containing a space | **4** |

**Arithmetic check on 169 vs 167:** the 4 multi-word values contribute 2 atoms each instead of
1, so they add 4 atoms; two of those atoms (`new`, `delhi`) were not already counted as
standalone values, and two (`andhra`, `pradesh`) were. Net `167 + 2 = 169`. The 4 values:

```
পশ্চিমবঙ্গ => west bengal
दिल्ली => new delhi
தமிழ்நாடு => tamil nadu
ఆంధ్రప్రదేశ్ => andhra pradesh
```

## 2a. "Missing self-maps" is a vacuous defect class here

The work order asks for missing self-maps. **The class is structurally impossible in this
table, not merely unpopulated.** Keys are drawn from `U+0900-U+0D7F`; values match
`^[a-z ]+$`. The two sets are disjoint by construction, so a self-map cannot be written. The
measured `selfmaps = 0` is therefore *correct by design*, not a gap. Do not raise it.

## 2b. Key script blocks (the table is 9 near-parallel copies of one vocabulary)

| Block | Codepoint range | Keys | Distinct values covered |
|---|---|---|---|
| Devanagari | U+0900-U+097F | 161 | 156 / 167 |
| Gurmukhi | U+0A00-U+0A7F | 158 | 150 / 167 |
| Gujarati | U+0A80-U+0AFF | 152 | 148 / 167 |
| Telugu | U+0C00-U+0C7F | 152 | 148 / 167 |
| Malayalam | U+0D00-U+0D7F | 150 | 147 / 167 |
| Kannada | U+0C80-U+0CFF | 149 | 148 / 167 |
| Tamil | U+0B80-U+0BFF | 148 | 148 / 167 |
| Oriya | U+0B00-U+0B7F | 147 | 145 / 167 |
| Bengali | U+0980-U+09FF | 146 | 146 / 167 |
| **Total** | | **1,363** | — |

`161+158+152+152+150+149+148+147+146 = 1,363` (checks)

**This is the single most important structural fact about the table.** It is not 1,363
independent translations. It is **one 167-word closed vocabulary expressed in 9 scripts**,
each script covering 145-156 of the same 167 targets. The dictionary is a *translation layer
for a fixed, small, legal/brand word list* — not open-domain transliteration. Any Indic token
outside those 167 concepts does **not** reach this table at all; it falls through to the
rule-based `romanize()`.


---

# 3. How the table is actually used (source quotes)

All quotes are from `_upstream/src/`.

**`normalize.py:17-18`** — the gate and the matcher:
```python
INDIC_RE = re.compile(r"[ऀ-ൿ]")
INDIC_TOKEN_RE = re.compile(r"[ऀ-ൿ‌‍]+")
```
`ऀ` is U+0900 and `ൿ` is U+0D7F, so the class is exactly `U+0900-U+0D7F`, plus ZWNJ/ZWJ
inside `INDIC_TOKEN_RE`.

**`normalize.py:81-86`** — the load (the only reference to the resource path in the repo):
```python
def _load_dict():
    global _DICT
    if _DICT is None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "indic_token_dict.json")
        _DICT = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    return _DICT
```

**`normalize.py:89-103`** — the whole consumer. Note the early return at line 91:
```python
def translit_text(s: str) -> str:
    """Replace every Indic-script token by its Latin equivalent."""
    if not s or not INDIC_RE.search(s):
        return s
    d = _load_dict()

    def rep(m):
        t = m.group(0).replace("‌", "").replace("‍", "")
        if t in d:
            return d[t]
        t2 = m.group(0)
        if t2 in d:
            return d[t2]
        return romanize(t)
    return INDIC_TOKEN_RE.sub(rep, s)
```

Three behavioural consequences, all measurable from the code:

- **The dictionary is only consulted when the raw string contains a codepoint in
  `U+0900-U+0D7F`** (line 91). Latin text returns at line 92 before the dict is even loaded.
  This is the entire "is it live" mechanism.
- **ZWNJ/ZWJ double lookup is dead weight.** Line 96 strips ZWNJ/ZWJ and looks up; lines 99-101
  retry with the raw form. But **0 of the 1,363 keys contain ZWNJ or ZWJ** (measured), so the
  second lookup at line 100-101 can never hit. Not a defect — simply unreachable.
- **Every miss falls through to the rule-based `romanize()`** (line 102), which is the real
  coverage mechanism for open-vocabulary Indic text. The learned table only overrides the
  1,363 tokens it happens to contain.

**Call sites — both unconditional, both country-blind:**
```python
normalize.py:287    s = translit_text(raw or "")          # normalize_name
normalize.py:316    s = translit_text(raw or "")          # normalize_address(raw, country)
```
`normalize_address` receives `country` (line 314) and **does not pass it to `translit_text`**.

## 3a. Ordering: the table runs BEFORE the canonical token maps — this is correct

`normalize_name` (line 287) transliterates first, then `_name_tokens` (line 281) applies
`NAME_CANON`. So the table emits a *surface* Latin word and `NAME_CANON` canonicalises it.
Verified consistent end-to-end, e.g. the table's `"limited" -> "limited"` and
`normalize.py:111` `"limited": "ltd"` both land on `ltd`; `"private" -> "private"` and
`normalize.py:110` `"private": "pvt"` both land on `pvt`. No ordering defect.

The address path is the reverse and also correct: `normalize_address:333` tests the whole
component against `STATE_MAPS` **before** per-token canonicalisation at line 347, so the
table's state outputs (`gujarat`, `maharashtra`, `west bengal`, ...) match `IN_STATES`
directly. `normalize.py:190-192` then rewrites the `ADDR_CANON_COMMON` aliases
(`bombay -> mumbai`, `calcutta -> kolkata`, `madras -> chennai`, `odisha -> orissa`) only if the
component is *not* a bare state, which is the right order.

---

# 4. Overlaps

## 4a. With the other dictionaries in `normalize.py` — no conflict

The table's values are 167 surface Latin words. Checked against `NAME_CANON`
(`normalize.py:109-142`), `ADDR_CANON_COMMON` (`153-198`), `IN_STATES` (`230-242`).
Every intersection converges on the same canonical token. Examples:

- `shiv -> shiva`; `NAME_CANON:135` has both `"shiv": "shiva"` and `"shiva": "shiva"`. Same.
- `jay -> jai`; `NAME_CANON:133` has both `"jay": "jai"` and `"jai": "jai"`. Same.
- `lakshmi -> laxmi`; `NAME_CANON:134` has both. Same.
- `gujarat -> gujarat`; `IN_STATES:232` `"gujarat": "gj"`. Same.
- `bombay -> bombay`; `ADDR_CANON_COMMON:190` `"bombay": "mumbai"`. Same (Latin `Bombay` takes
  the identical path).

**No collision, no shadowing, no ordering bug found.** The one redundancy is that ~6 of the
167 values duplicate work `NAME_CANON` already does (`shiv`, `jay`, `lakshmi`, `shree`, `sree`,
`jai`). Harmless — the dict output is *more* surface-specific than `NAME_CANON`'s, so it
dominates correctly.

## 4b. Within the table — deliberate many-to-one, not a defect

- **`om` <- 14 keys**, one per script: `ॐ ಓಂ ओम ఓం ওம ഒം ഓം ఓമ్ ଓମ୍ ଓଁ ૐ ఓમ ੴ ਓਮ`.
  Correct script fan-out of one concept, not a defect.
- **`ss` <- 9 keys** (one per script), **`llp` <- 9**, **`ltd` <- 3**, **`pvt` <- 3**.

## 4c. NEW STRUCTURAL DEFECT (minor, behaviourally benign): affix-fragment keys

Three keys are **bare word-fragments**, not words:

```
लि  => "ltd"      લਿ => "ltd"      ਲਿ => "ltd"
प्रा => "pvt"      પ્રા => "pvt"      ੍પ੍ਰા => "pvt"
```

`लि` is a prefix of `लिमिटेड` (limited); `प्रा` is a prefix of `प्राइवेट` (private). These are
**positional-alignment artefacts of the learner**, not translations — see `learn_translit.py:45`
(`if len(a) == len(b)`) and `:41-48`. Any Latin source-1 name whose native-script counterpart
has the *same token count* will align the fragments positionally and, at the `n >= 2` threshold
(`learn_translit.py:71`), a wrong pair that recurs twice wins.

**Why it is benign:** `ltd` and `pvt` are both fixed points downstream —
`NAME_CANON:111` `"ltd": "ltd"` and `NAME_CANON:110` `"pvt": "pvt"` — and the full forms
`limited -> NAME_CANON -> ltd` and `private -> NAME_CANON -> pvt` reach the same tokens. So the
fragments cannot desynchronise the name stream. **Recorded as a real but harmless defect; it
should not generate a change on its own.**

## 4d. NEW STRUCTURAL DEFECT: inconsistent multi-word decomposition of state names

The 4 two-word values are *not* decomposed consistently with the rest of the table:

- Single-token whole-name entries: `पश्चिम बंगाल`-as-one-word -> `west bengal`,
  `தமிழ்நாடு` -> `tamil nadu`, `ఆంధ్రప్రదేశ్` -> `andhra pradesh`, `दिल्ली` -> `new delhi`.
- Split per-token entries: `मध्य -> madhya` and `प्रदेश -> pradesh` are **two separate
  single-word entries** (each frequency 1), not one `madhya pradesh` entry. Same for
  `उत्तर -> uttar` / `प्रदेश -> pradesh`.

Because `INDIC_TOKEN_RE` breaks on whitespace, a space-separated native state name is matched
token-by-token and reassembles correctly (`"madhya" + " " + "pradesh"` = `madhya pradesh`,
which `IN_STATES:234` matches -> `mp`). So this is **cosmetically inconsistent but functionally
correct**. Logged for completeness only.

---

# 5. Country scoping — the table is NOT country-scoped

- `STATE_MAPS` *is* country-scoped (`normalize.py:250`:
  `STATE_MAPS = {"US": US_STATES, "India": IN_STATES, "France": FR_REGIONS}`), but
  `translit_text` is not, and it is called with **no country argument** from both
  `normalize_name:287` and `normalize_address:316`.
- The table is therefore loaded once and evaluated on **every row of every country**, while
  every one of its 1,363 keys is an India-specific transliteration learned exclusively from
  India train S2/S3 pairs (`learn_translit.py:11` `IND = r"[ऀ-ൿ]"`; `:37` filters S2/S3 on `IND`).
- **Not a live defect for France**: `INDIC_RE.search` at `normalize.py:91` cannot fire on Latin
  French text, so the cost is one regex scan per row and nothing else. But it is a genuine
  design gap and it is the reason the table is on the hot path for the scored country at all.
- **France has zero rows in train.** Measured: `analysis_out/profile/train_s1.json`,
  `train_s2.json`, `train_s3.json` each contain only the `US` and `India` keys under
  `by_country`; `France` appears only in `test_s1/2/3.json`. So the table is a pure
  India-train artefact applied to a country the model is scored on.

---

# 6. GAP — the one number that decides this table's value, and it was not collected

**The profile cannot measure the Brahmic-script share of India, at all.** This is structural,
not an oversight in my analysis:

- `build_profile.py:28` — `TOKEN_RE = re.compile(r"[a-z0-9]+")`.
- `build_profile.py:110-111` — `bnl = bn.lower()` then `bnt = TOKEN_RE.findall(bnl)`.
  This runs on the **raw** string. There is **no transliteration step** in `build_profile.py`
  at all (grep for `indic|devanagari|script|nonascii|unicode|0900` in `build_profile.py`
  returns nothing).
- Therefore a name written entirely in Devanagari contributes its full length to
  `name_chars` (line 102) and **exactly zero** to `name_tokens` (line 112), and it is
  **invisible in both `name_tokens` and `addr_tokens`**.

Consequence: **I cannot state how many India rows this table actually fires on, and I will
not estimate it.** Per the evidence standard this is labelled a gap, not filled with a
plausible number.

**What I can say about it, with evidence:**

- **The table is provably not dead.** `learn_translit.py:42` (`if not re.search(IND, n2): continue`)
  means an entry is only ever written for a token observed in a real train S2/S3 name that
  actually contained Brahmic script. `learn_translit.py:70-72` requires the winning
  translation to have `n >= 2` observations. **1,363 entries each backed by >=2 real
  observations is proof that Brahmic-script text exists in India train s2/s3 at volume.**
- **Its open-vocabulary coverage is nil.** Because the value set is a closed 167-word list
  (section 2b), any Indic token outside that list bypasses the table entirely and hits
  `romanize()` (`normalize.py:102`). So the table is a *high-precision patch on a 167-word
  legal/brand vocabulary*, not a transliteration engine.

**The best available indirect bound — clearly an INFERENCE, not a measurement.**
`name_chars / name_tokens` per row (both from `by_country`):

| split | country | name_chars/row | name_tokens/row | chars per ASCII token |
|---|---|---|---|---|
| train_s1 | US | 22.465 | 3.489 | 6.44 |
| train_s1 | India | 26.386 | 3.702 | 7.13 |
| train_s2 | India | 27.420 | 2.893 | 9.48 |
| train_s2 | US | 23.554 | 3.551 | 6.63 |
| train_s3 | India | 27.038 | 3.324 | 8.13 |
| train_s3 | US | 23.977 | 3.635 | 6.60 |
| test_s1 | France | 19.423 | 3.194 | 6.08 |
| test_s1 | India | 26.375 | 3.701 | 7.13 |

Arithmetic: e.g. India train_s1 `26.386 / 3.702 = 7.13`; US train_s1 `22.465 / 3.489 = 6.44`.

India's s1 ratio (7.13) is essentially US's (6.44) and *higher* than France's (6.08), and
India s1 `name_tokens/row` (3.702) is **higher** than US s1 (3.489) — a large Devanagari
subset would push this *down*, since Devanagari rows contribute 0 tokens. India s2 (9.48) and
s3 (8.13) run higher than US (6.63, 6.60), which is *directionally consistent* with a
Brahmic subset in S2/S3 — but Indian transliterated names are also simply longer, and the
two explanations are not separable from these fields. **I therefore bound it only as
"not a large majority of s1, plausibly non-trivial in s2/s3", and mark it an inference.**
Closing this gap needs one new profile field (e.g. `rows_with_indic_name`,
`rows_with_indic_addr`, counting `U+0900-U+0D7F` in the raw field) — a streaming counter,
`csv`-based, same cost as the existing pass.

---

# 7. The vocabulary the table already occupies (74.85%)

Because the table introduces no new vocabulary, its value collapses to a conversion count.
For scale, the overlap of its 169 atoms with India's listed tokens
(`analysis_out/profile/train_s1.json`, top 4000 per `build_profile.py:27 TOPN = 4000`):

| set | listed tokens | atoms present | occurrences listed | occurrences covered | share |
|---|---|---|---|---|---|
| India `name_tokens` | 4,000 | **166 / 169** | 2,955,338 | 2,212,001 | **74.85%** |
| India `addr_tokens` | 4,000 | **121 / 169** | 9,395,284 | 1,896,499 | **20.19%** |

Arithmetic: `2,212,001 / 2,955,338 = 0.74854`; `1,896,499 / 9,395,284 = 0.20186`.

**This is not evidence that the table is working.** The counts are *raw* data counts
(`build_profile.py:125 nt.update(bnt)` on the untransliterated name), so `limited`
(521,781), `pvt` (121,461), `ltd` (145,941) and `delhi` (321,971) are Latin tokens that were
**already in the TSV**. The table is credited with the output vocabulary that the data
already had. Precisely: the table's marginal effect is bounded above by the Brahmic-row count
(GAP, section 6) and is *definitionally* zero for the 74.85% of listed name-token occurrences
that are already Latin in the source file.

The 3 atoms absent from India's top-4000 name tokens: `nadu`, `tamil`, `telangana`
(they live in addresses instead — `tamil` 63,594 and `telangana` 56,251 in `addr_tokens`).

**Caveat on "top 4000", stated per the fleet brief:** the list is doubly truncated. It is
`Counter.most_common(4000)` (`build_profile.py:140-141`) over counters that are **periodically
pruned of all count==1 tokens** (`build_profile.py:26 PRUNE_EVERY = 8`, `:45-48`, `:128-133`).
So it is not a complete frequency list. Absence of an atom from it is **"not in the top 4000"**,
never "does not occur". This does not affect the headline: the claim is about a *disjointness*
that is proved by the tokenizer, not about occurrence.

---

# 8. Verdict

| Question | Answer | Basis |
|---|---|---|
| Path in work order correct? | **Yes** | `Test-Path` -> `True`, 47,788 bytes |
| Entry count | **1,363** | parsed |
| Distinct canonical values | **167** (169 atoms) | parsed |
| Empty values | **0** | parsed |
| Missing self-maps | **0, and the class is vacuous** | keys and values are disjoint codepoint sets |
| Overlaps with `NAME_CANON`/`ADDR_CANON_COMMON`/`IN_STATES` | **none that conflict** | section 4a |
| Country scoping | **absent** — applied to US, India and France alike | `normalize.py:287, 316` |
| Keyed on script? | **Yes — native Brahmic, 9 scripts, 0 Latin keys** | section 2b |
| Distinct India tokens it can affect | **0 of 8,000 listed — a profile artifact, not inertness** | Headline |
| India rows it fires on | **GAP — not collected by the profile** | section 6 |
| Marginal value for **France** (the scored country) | **0, provable** | France absent from train; 0 Latin keys; `INDIC_RE` cannot fire on Latin |
| NEW defects found | 2, both benign: affix-fragment keys (4c), inconsistent multi-word state decomposition (4d) | — |

**"No defect found" is almost the right answer, and I am reporting that plainly.** The one
finding worth carrying forward is not a defect in the table at all — it is that **this table
cannot be audited for value with the artifacts the fleet currently has**, because
`build_profile.py:28` erases all Brahmic text before it is ever counted. Any later task that
proposes expanding or trimming this table should first add the two counter fields named in
section 6, or its recommendation will rest on numbers that cannot exist.

**No changes proposed — D095 is ground truth only, per the work order.**

---

# 9. Explicitly NOT re-derived

Per the work order's `already_checked` list, I did not touch: `US_STATES`, `IN_STATES`,
`FR_REGIONS` dictionary expansion; the France-postcode-loss claim; `pin_eq`; `alt_tset`;
France blocking caps; address component order; the ligature defect; `ADDR_CANON_COMMON` empty
mappings; the `LEET` French-ordinal defect.

**Constraints honoured:** `_upstream/` and `amazon_ml_2026_research/` were read only, never
modified. No raw `*.tsv` was opened — all data figures come from `analysis_out/profile/*.json`.
No network access. PowerShell only (Python is broken on this box).
