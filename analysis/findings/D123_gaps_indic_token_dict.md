# D123 — Remaining gaps in `indic_token_dict`, after the France hypotheses died

**Status:** complete. One NEW structural defect found (single-script state coverage).
**Path:** `_upstream/src/resources/indic_token_dict.json` — 47,788 bytes, **1,363 entries**,
**167 distinct values**, 0 Latin keys, 0 digit keys, 0 keys containing whitespace.
**Reference:** D095 (audit) is my ground truth. **D096 does not exist** — `analysis_out/findings/`
contains no `D096_*` file, only `analysis_out/tasks/D096.json`. I did not wait for it.

---

# HEADLINE

**The dictionary is correct. It is not dead weight, and it is not broken. But it is
*asymmetric*, and the asymmetry is the one real thing still wrong with it.**

`indic_token_dict.json` fans its vocabulary out across **9 scripts for brand/legal words**
and across **exactly 1 script for Indian state and region words**. A Gujarati-script
"Gujarat" is in the table (9 keys). A Bengali-script "Maharashtra" is **not** — only the
Devanagari spelling is. The whole point of the table is script robustness, and it is absent
precisely where script robustness matters most, because an address is the one field most
likely to be written in a regional script rather than Devanagari.

**The single most important number: 16 of the 167 values (9.58%) have exactly ONE key.
All 16 are Indian state/region words.**

---

# 1. The one NEW defect: 16 single-script values, all of them states

## 1a. The key-count distribution is bimodal, and the split is not random

Grouping the 1,363 entries by their canonical value:

| keys per value | # values | entries contributed |
|---|---|---|
| **1** | **16** | **16** |
| 3 | 2 | 6 |
| 4 | 1 | 4 |
| 5 | 3 | 15 |
| 6 | 1 | 6 |
| 7 | 1 | 7 |
| 8 | 2 | 16 |
| **9** | **129** | **1,161** |
| 10 | 7 | 70 |
| 11 | 2 | 22 |
| 13 | 2 | 26 |
| 14 | 1 | 14 |
| **Total** | **167** | **1,363** |

Arithmetic: `16 + 6 + 4 + 15 + 6 + 7 + 16 + 1161 + 70 + 22 + 26 + 14 = 1363`. Checks.

**129 of 167 values (77.2%) have the full 9-script fan-out.** That is D095's "one 167-word
vocabulary in 9 scripts" and it holds for the brand/legal vocabulary. The remaining 16 do not.

## 1b. The 16 single-key values — the entire state sub-vocabulary

```
andhra pradesh  U+0C06 (Telugu)      maharashtra   U+092E (Devanagari)
bihar           U+092B (Devanagari)  new delhi     U+0926 (Devanagari)
haryana         U+0939 (Devanagari)  orissa        U+0B13 (Oriya)
karnataka       U+0C95 (Telugu)      pradesh       U+092A (Devanagari)
kerala          U+0D15 (Malayalam)   punjab        U+0A2A (Gujarati)
madhya          U+092E (Devanagari)  rajasthan     U+0930 (Devanagari)
                                    telangana     U+0C24 (Telugu)
                                    tamil nadu    U+0BA4 (Tamil)
                                    uttar         U+0909 (Devanagari)
                                    west bengal   U+09AA (Bengali)
```

**These 16 are exactly the state/region words, and nothing else.** `gujarat` is the
instructive contrast: it is the *only* state name with the full 9-key fan-out
(`गुजरात ಗುಜರಾತ్ గుజరాత్ குஜராத் ગુજરાત গুজরাট ഗുജറാത്ത് ਗੁਜਰਾਤੰ ଗୁଜରାଟ`), because it appeared
in the source-1 *name* alignment branch, not only the address branch.

**Why this happens — the learner, not the table.** `learn_translit.py` has two branches:

- **Name branch** (`:41-48`): aligns native tokens to Latin tokens for *business names*.
  A name is the same word in all 9 scripts, so each concept accumulates 9 keys.
- **Address branch** (`:50-67`): only fires when the source-1 address component is an
  `IN_STATES` key (`:51`, `:55`) and the native address component contains Indic (`:59`).
  It therefore records **only the script that actually appeared in that address**, once.

Nothing in `learn_translit.py` iterates over scripts. The 9-way fan-out in the name branch
is an *emergent* property of the data (the same word really is written 9 ways); the 1-way
coverage in the address branch is an *emergent* property too. The asymmetry is a property of
the training pairs, not a design choice and not a bug in the table as shipped.

**So I am recording this as a genuine coverage gap, `LIKELY` material, and explicitly NOT
as a code defect.** The table is faithful to what it was taught.

## 1c. Why I cannot size the impact — declared GAP

`build_profile.py:28` `TOKEN_RE = re.compile(r"[a-z0-9]+")` matches **zero characters** of a
Brahmic string, and `build_profile.py:110-111` applies it to the **raw, untransliterated**
name. So every Brahmic token is invisible to every profile field. **I cannot state how many
India rows carry a non-Devanagari-script state name, and I will not estimate it.**

What the profile *can* show is that the affected Latin surface is large and already present
in India `train_s1` `addr_tokens` (occurrence counts):

```
maharashtra 192,382   pradesh 116,200   west 123,775    bengal 57,198
uttar  75,822        tamil 63,594      nadu 63,587      gujarat 58,151
telangana 56,251      haryana 36,972    karnataka 70,523  kerala 35,828
rajasthan 32,625      bihar 23,752      madhya 22,660    andhra 18,368
orissa 13,984         punjab 13,984     delhi 321,971 (name 8,795)
```

These are **raw** counts on the untransliterated field (`build_profile.py:127`), so they are
the *destination* the table converts into, not evidence of what the table converted. They
establish that the single-script gap is not in some rare corner of the vocabulary — the
missing second script for `maharashtra` would target a token worth 192,382 listed occurrences.

---

# 2. Collisions: definitively NONE, and the mechanism is not first-match

The work order asks whether overlapping keys resolve arbitrarily in `romanize`. **They cannot
collide at all, and the reason is stronger than "first-match is fine".**

`normalize.py:18` `INDIC_TOKEN_RE = re.compile(r"[ऀ-ൿ‌‍]+")` is used with `.sub()` at
`normalize.py:103`. The `+` is **greedy**, so the regex emits **maximal runs** of Brahmic
codepoints. `rep()` then does an **exact whole-run hash lookup**:

```python
def rep(m):
    t = m.group(0).replace("‌","").replace("‍","")
    if t in d: return d[t]        # exact match on the ENTIRE run
    t2 = m.group(0)
    if t2 in d: return d[t2]
    return romanize(t)
```

`romanize()` (`normalize.py:40`) **never consults the dictionary at all** — it is a pure
code-point loop. So there is no prefix scan, no longest-match, no first-match ambiguity, and
no key can shadow another. **The work order's "is it first-match or longest-match" question
does not apply: it is a single exact dict lookup on a maximally-munched run.**

**Consequence, and it is a real one.** 140 of the 1,363 keys are a proper substring of
another key, so those 140 fire **only when they appear standalone**, never inside a longer
word. Of the 140, **131 map to a value that disagrees with at least one of their
superstrings** (e.g. `सन`→`sun` vs `सन्राइज़`→`sunrise`; `टेक`→`tech` vs
`टेक्नोलॉजी`→`technology`). This looks alarming and is **completely harmless**: maximal munch
means the two can never be candidates for the same input span, so they cannot disagree on any
row. I state this explicitly because the raw number (131 "collisions") would otherwise read
as a serious defect.

**Cross-country collision: impossible, definitively.** All 1,363 keys are pure
`U+0900-U+0D7F`; the gate at `normalize.py:91` is `if not s or not INDIC_RE.search(s): return s`,
which is per-*string*, not per-country. A US or France row must therefore contain a literal
Brahmic codepoint for any of this to fire. **There is no mechanism by which this table can
touch a US or France row.** This is stronger than D095's "value is 0 for France": it is 0 for
the **US too**, and for every non-India country, by construction rather than by measurement.

---

# 3. France cost: negligible. Do not inflate it.

The table is not country-scoped, so it is on the France hot path. Cost:

- `_load_dict()` is called at `normalize.py:93`, **after** the `INDIC_RE.search` gate at
  `:91`. A run containing no Brahmic anywhere never loads the 47,788-byte JSON at all.
- For France specifically the per-row cost is **one regex scan of a short Latin string**,
  returning `s` at `:92`. No dict lookup, no allocation, no `romanize()`.

France test rows: `259,452 + 703,378 + 731,615 = 1,694,445`, i.e. **3,388,890 regex searches**
(`1,694,445 × 2`, name + address). At ordinary Python regex speed for a 20–40 char string that
is **well under one second, once, for the entire France test set.**

**Verdict: negligible. A country-scoping guard would be churn, not a fix.** I am not
recommending one. (`STATE_MAPS` at `normalize.py:250` *is* country-scoped; `translit_text` is
simply not given the country to scope with. That is untidy, not expensive.)

---

# 4. The 4 multi-word values: safe, and they are load-bearing

The 4 values containing a space, with their single key each:

```
পশ্চিমবঙ্গ  (U+09AA..U+0997, Bengali)   =>  west bengal
दिल्ली      (U+0926..U+0940, Devanagari) =>  new delhi
தமிழ்நாடு  (U+0BA4..U+0BC1, Tamil)      =>  tamil nadu
ఆంధ్రప్రదేశ్ (U+0C06..U+0C4D, Telugu)     =>  andhra pradesh
```

**All 4 are keys of `IN_STATES`** (`normalize.py:231-242`): `andhra pradesh`→`ap`,
`new delhi`→`dl`, `tamil nadu`→`tn`, `west bengal`→`wb`. The space is **required** for
them to resolve, because `IN_STATES` is itself keyed on the space-joined form.

**The space does not break anything downstream.** I traced both consumers:
- `normalize_address:331` `ck = re.sub(r"[^a-z0-9& ]+", " ", c)` — the character class
  **includes the space** (it is the only non-alphanumeric character preserved), so
  `"west bengal"` survives as a component. `:332` normalises whitespace, `:333`
  `if ck in smap` matches, `:334` sets the state, `:335` `continue`s. Correct.
- `normalize_name:276` `_non_alnum.split(s)` splits on `[^a-z0-9]+`, so a name-borne
  `"west bengal"` becomes two tokens `west`, `bengal`. Also correct.
- `keys.py:33,39,46` all `.str.split(" ")` on space-joined columns, so no blocking key can
  contain a space either.

**Verdict: no defect. The 4 multi-word values are the correct shape and are the *only*
things that make the Brahmic state branch work at all.**

D095 §4d ("inconsistent multi-word decomposition") also checks out. I re-derived the
split-token entries `मध्य`→`madhya`, `प्रदेश`→`pradesh`, `उत्तर`→`uttar`
(`U+092E U+0927 U+094D U+092F`, `U+092A U+094D U+0930 U+0926 U+0947 U+0936`,
`U+0909 U+0924 U+094D U+0924 U+0930`) and confirmed a space-separated
`"मध्य प्रदेश"` reassembles to `madhya pradesh` → `IN_STATES` → `mp`. Correct.
*(Self-correction: my first check of these three appeared to show them MISSING. That was my
own transcription — I typed the word with a trailing matra instead of `मध्य`. The dictionary
is right and D095 is right; I record the error rather than quietly dropping it.)*

---

# 5. Can the table be rebuilt to cover the Latin side? NO — and that is the point

The work order asks whether the Brahmic-only keying is a deliberate design choice or an
artefact. **It is deliberate, and the learner makes extending it incoherent.**

`learn_translit.py:44-48`:
```python
a, b = lat_tokens(n1), nat_tokens(n2)
if len(a) == len(b):
    for x, y in zip(b, a):     # x = NATIVE token  -> dict KEY
        cnt[x][y] += 1         # y = Latin  token  -> dict VALUE
```
The **key is always the native token and the value is always the Latin token**, by
construction of the `zip` at `:46`. `:42` (`if not re.search(IND, n2): continue`) additionally
*discards* every pair whose source-2 name has no Brahmic. There is no code path, and no
parameter, that could emit a Latin key.

**So "extend the dictionary to the Latin side" is a category error, not a task.** The Latin
side is already the job of `NAME_CANON` (`normalize.py:109-142`), `ADDR_CANON_COMMON`
(`:153-198`), `ADDR_CANON_FR` (`:199-214`), `LEET` (`:255`) and `STATE_MAPS` (`:250`) — all
hand-built Latin→canonical tables. Re-keying this file on Latin would duplicate them in a
second, learned, and strictly worse place. **I am not proposing it.**

The one *legitimate* extension this file admits is the §1b gap: **add the 8 missing scripts
for the 16 single-key state values.** `SPECULATIVE` as a change, `CONFIRMED` as a gap,
and unmeasurable against the current profile either way — see the gap in §1c.

---

# 6. What is NOT wrong (so the fleet does not re-open it)

| Check | Result |
|---|---|
| Empty / null values | **0** |
| Keys with a Latin letter | **0** |
| Keys with a digit | **0** |
| Keys containing whitespace | **0** |
| Keys with ZWNJ U+200C / ZWJ U+200D | **0** → `normalize.py:100-101` second lookup is **unreachable dead code**, benign |
| Duplicate keys | **0** (1,363 entries = 1,363 distinct keys) |
| Cross-country collision | **impossible**, §2 |
| Key-vs-key shadowing | **impossible**, §2 (maximal munch + exact lookup) |
| Multi-word values breaking `split()` | **no**, §4 |
| Country-scoping cost on France | **negligible**, §3 |

Entries whose value is in `NAME_STOP` (`:144-149`) and is therefore dropped from `ncore`:
**15 of 1,363** — 9 × `llp`, 3 × `ltd`, 3 × `pvt`. These are exactly D095 §4c's affix
fragments (`लि`, `प्रा` and their 5 script siblings) plus the 9 legitimate `llp` spellings.
`llp`/`ltd`/`pvt` are legal-form noise by design (`NAME_STOP:145`), so this is **correct
behaviour, not a defect.** Note the fragments are *also* protected by maximal munch
(§2), which is a second, independent reason they cannot corrupt a longer word.

---

# 7. Verdict

**This dictionary is fine. Stating that plainly, as the work order invites.**

- **Dead weight: none found.** Zero empty values, zero malformed keys, zero unreachable
  *by construction* code paths other than the benign ZWNJ double-lookup. All 1,363 entries
  are well-formed and every one of them is reachable when its token occurs standalone.
- **Tokens the profile shows that this should handle but does not: none can be
  established.** The profile is structurally blind to this table (§1c). Any such list would
  be invented. **Declaring this a GAP rather than answering it is the correct output.**
- **Collisions across countries: impossible**, by construction (§2).
- **NEW defect found: 1** — the 16 single-script state values (§1). Coverage gap in the
  learned table, faithful to its training data, `LIKELY` material, **not** a code bug.
- **France: value exactly 0, cost negligible.** No change recommended.

**The honest headline for the fleet is the D095 measurement trap, restated because it still
governs this file:** the profile reports **0 of 8,000** India tokens affected. That zero is a
**measurement artefact**, not inertness — `build_profile.py:28` erases every Brahmic
character before any counter sees it. Do not let that zero be quoted as evidence that this
table does nothing. It demonstrably does something: 1,363 entries each backed by `n >= 2`
real train observations (`learn_translit.py:70-72`) is proof of Brahmic text at volume in
India train S2/S3.

**If anyone wants to close this file for good, the only thing needed is two counters in
`build_profile.py`: `rows_with_indic_name` and `rows_with_indic_addr`, counting
`U+0900-U+0D7F` in the raw field. Both are streaming `any()` tests, same cost as the
existing pass, ~4 lines. Without them this file can be audited for *correctness* (done, clean)
but never for *coverage* (still open).**

---

# 8. Constraints honoured

`_upstream/` and `amazon_ml_2026_research/` read-only, never modified. No raw `*.tsv` opened —
every data figure comes from `analysis_out/profile/*.json`. No network. PowerShell only
(Python is broken on this box). Two files written: this `.md` and
`analysis_out/findings/D123_gaps_indic_token_dict.json`.

**Not re-derived** (per `already_checked` and the fleet brief): the France-postcode/pin
hypothesis, `FR_REGIONS` thinness, `US_STATES`/`IN_STATES` expansion, the retracted French
function-word finding, `LEET`, `ADDR_CANON_FR`, `ADDR_GENERIC`, blocking caps, address
component order, the ligature defect, `pin_eq`, `alt_tset`.
