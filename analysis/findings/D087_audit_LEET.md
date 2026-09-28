# D087 — Ground-truth audit of the `LEET` table in `_upstream/src/normalize.py`

**Task type:** ground-truth establishment. No changes proposed — this is the factual
baseline the fix tasks consume.

**Sources read:** `_upstream/src/normalize.py` (read-only), `_upstream/src/prep.py`,
`_upstream/src/keys.py`, and the six profile JSONs in `analysis_out/profile/`.
No raw `*.tsv` opened. No network.

---

## Headline

`LEET` is **not a token dictionary**. It is a **single character-to-character
`str.maketrans` table of 10 entries with 8 distinct canonical values**, defined in one
line at `_upstream/src/normalize.py:256`, and applied at **exactly one call site**
(`normalize.py:280`) **per whole name token**, name field only, with **no country in
scope**. It cannot be fixed inside the table: the confirmed French-ordinal defect
requires knowing the *whole token*, which a character-level table structurally cannot
express. **The fix belongs at the call site, in `_name_tokens`.**

Two NEW defects found, both missed by the ordinal guard proposed in the brief:

| # | Defect | Mass (all 6 profile files) | Caught by `^\d+(e|er|ere|eme)$`? |
|---|---|---|---|
| **N1** | `24hr` -> `2ahr` (US; "24hr" is 24-hours, not leet) | **3,657** | **NO** |
| **N2** | `1st` -> `lst` (US 679 + India 381; English ordinal) | **1,060** | **NO** |
| D1 | French ordinals `3eme/1er/3e/1ere/7eme` | 1,111 | yes |
| D3 | `@` and `$` keys are **unreachable dead code** | 2 of 10 entries | n/a |

**The brief's proposed guard catches 1,111 of the 5,828 corrupted occurrences (19.1%).
It misses `24hr` and `1st` entirely** — together 4,717 occurrences, **4.25x** the French
ordinal mass. A guard scoped only to French ordinals would leave the single largest
corruption in the whole table unfixed.

---

## 1. Exact contents of `LEET` — exhaustive

Single source line, `_upstream/src/normalize.py:256`:

```python
LEET = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "6": "g", "7": "t", "8": "b", "@": "a", "$": "s"})
```

| Property | Value |
|---|---|
| Entry count | **10** |
| Distinct canonical values | **8** — `a, b, e, g, l, o, s, t` |
| Key classes | 8 digits (`0,1,3,4,5,6,7,8`) + 2 symbols (`@`,`$`) |
| Keys absent | **`2`** and **`9`** (deliberate or not, they are unmapped) |
| Any key that is a letter? | **No** — no key is an ordinary character, so no key can shadow a real word |
| Any value that is itself a key? | **No** — values are all letters, keys are all digits/symbols, so the table is **non-recursive** (one pass, no chaining) |
| Self-maps (`k -> k`) | **None present, none needed** — no key equals its value |
| Value collisions (many->one) | **2**: `4->a` and `@->a`; `5->s` and `$->s` |
| Empty-string values | **None.** Every value is a 1-char string. A `""` value in `maketrans` would be a deletion; none is present |
| Overlap with `ADDR_CANON_COMMON` | **None, and structurally impossible** — see §5 |

**Digits 2 and 9 are unmapped.** This is *not* a defect on current evidence: across all
6 files only **2** of 284 mixed token types contain `2` or `9` (`24hr` 3,657 and `2nd`
253), and both are corrupted for a *different* reason (§4).

---

## 2. Where and how `LEET` is applied — full call path

Repo-wide search for `LEET|translate(|maketrans` over all 19 `.py` files in `_upstream`
returns **exactly two hits**, both in `normalize.py`:

```
_upstream\src\normalize.py:256: LEET = str.maketrans({...})
_upstream\src\normalize.py:280: t = t.translate(LEET)
```

The call path, with source lines:

```
prep.py:12   full, core, alt, dom, dba = N.normalize_name(n)     # <-- NO country passed
prep.py:13   toks, nums, st, pin, cc = N.normalize_address(a, c) # <-- country IS passed
   |
normalize.py:285  def normalize_name(raw: str):                  # signature has NO country
normalize.py:287      s = translit_text(raw or "")
normalize.py:288      s = strip_accents(s)
normalize.py:305      full = _name_tokens(main)
normalize.py:307      alt_core = [... _name_tokens(alt) ...] if alt else []
   |
normalize.py:272  def _name_tokens(s: str):
normalize.py:273      s = s.lower()...replace("&"," and ")...
normalize.py:276      for t in _non_alnum.split(s):              # _non_alnum = [^a-z0-9]+  (line 269)
normalize.py:279          if any(c.isalpha() for c in t) and any(c.isdigit() for c in t):
normalize.py:280              t = t.translate(LEET)              # <-- THE ONLY APPLICATION
normalize.py:281          toks.append(NAME_CANON.get(t, t))
```

Answering the work order's questions precisely:

- **Whole token or substring?** **Whole token, whole-token pass.** `str.translate` rewrites
  *every* character of the token, not a matched substring. There is no regex, no
  anchoring, no boundary logic.
- **Per-token or per-substring?** **Per-token.** One `translate` call per token from the
  `_non_alnum.split` at line 276.
- **Name only, or address too?** **Name only.** `normalize_address` (lines 314-353) never
  references `LEET`; its tokens go to `canon.get(t, t)` at line 347. Confirmed by the
  two-hit search above.
- **Before or after country is known?** This is the decisive structural fact.
  `normalize_address(raw, country)` takes a country (line 314) and uses it at lines
  318/321/337. **`normalize_name(raw)` does not take one at all (line 285)**, and
  `prep.py:12` does not supply one. **Country is therefore not in scope anywhere on the
  LEET path.** A country-scoped guard is not implementable without changing a public
  signature and a call site.
- **Trigger condition.** LEET fires only when the token contains **both** a letter and a
  digit (line 279). A pure-digit or pure-alpha token is never translated.

### Ordering relative to other transforms
`translate` runs **after** `strip_accents` (line 288) and **after** `.lower()` (line 273),
and **before** `NAME_CANON.get` (line 281) and before `NAME_STOP` filtering (line 306).
So a `NAME_CANON` entry keyed on `"3eme"` could never fire today — the token has already
become `"eeme"` by line 281. This matters for whoever designs the fix.

### Downstream blast radius
`ncore` is built from `core` (line 306) and feeds `keys.py:33-34`. `keys.py:42` filters
address tokens with `~str.contains(r"^\d+$")`, and name tokens enter `nt` unfiltered at
length >= 2 — so a corrupted name token like `eeme` becomes a live blocking key while the
same business's address side keeps the correct `3eme` (`normalize_address` lines 342-349).
Confirmed by the name/address asymmetry in §4d.

---

## 3. Per-token vs per-substring — why the guard must be written token-anchored

This matters for the fix, so it is measured rather than assumed.

**Measured: across all 284 mixed token types in all 6 profile files, ZERO contain a
repeated leet key.** No token contains `3` twice, `1` twice, etc. Consequence: in every
observed case `translate` rewrites **exactly one character**.

> types with a repeated leet key = 0, occurrences = 0

Two implications for the follow-on fix task:

1. A guard of the form `^\d+(e|er|ere|eme)$` (anchored on the **whole token**) is the
   correct shape. A substring/unanchored guard would be wrong in principle even though it
   happens to be indistinguishable on current data.
2. `translate` is a *single pass* — the values it writes (`o,l,e,a,s,g,t,b`) are not
   themselves keys, so a token can never cascade. Output length always equals input length.

---

## 4. The confirmed defect, precisely characterised

Denominator: `name_tokens[country]` in the six profile JSONs, restricted to tokens
containing at least one letter **and** at least one digit (the line-279 trigger). All six
files: **284 mixed types / 176,142 occurrences**.

| Country | mixed types | mixed occurrences |
|---|---|---|
| US | 133 | 90,100 |
| India | 127 | 80,735 |
| **France** | **24** | **5,307** |
| **total** | **284** | **176,142** |

### 4a. France, all 24 types (every French mixed token, measured)

| input | LEET output | occ | verdict |
|---|---|---|---|
| `4l` | `al` | 1,943 | **not a defect** (see 4e) |
| `3eme` | `eeme` | 748 | **CORRUPT** |
| `5arl` | `sarl` | 637 | correct |
| `5as` | `sas` | 417 | correct |
| `c1ub` | `club` | 190 | correct |
| `amica1e` | `amicale` | 136 | correct |
| `1er` | `ler` | 131 | **CORRUPT** |
| `5a` | `sa` | 129 | correct |
| `3e` | `ee` | 121 | **CORRUPT** |
| `mais0n` | `maison` | 118 | correct |
| `1ere` | `lere` | 102 | **CORRUPT** |
| `uni0n` | `union` | 87 | correct |
| `5asu` | `sasu` | 85 | correct |
| `ass0ciation` | `association` | 75 | correct |
| `c0mite` | `comite` | 75 | correct |
| `rati0n` | `ration` | 61 | correct |
| `tab1issements` | `tablissements` | 56 | correct |
| `li1le` | `lille` | 54 | correct |
| `c0mit` | `comit` | 29 | correct |
| `5ci` | `sci` | 27 | correct |
| `fi1s` | `fils` | 26 | correct |
| `5portive` | `sportive` | 26 | correct |
| `sp0rtive` | `sportive` | 25 | correct |
| `7eme` | `teme` | 9 | **CORRUPT** |

Arithmetic: 748 + 131 + 121 + 102 + 9 = **1,111 corrupted**.
1,111 / 5,307 = **20.93%** of French mixed name tokens are corrupted.
This independently reproduces D090's 1,111 exactly, from the raw profile files.

### 4b. NEW DEFECT N1 — `24hr` -> `2ahr` (US, 3,657)

`24hr` is the standard abbreviation for *24 hours*. The `4` is a real digit, not a leet
stand-in, and `2` is not even a LEET key, so the token is mangled into `2ahr`, which is
not a word in any language in this dataset.

- `24hr` is the **2nd-largest** single mixed type in the entire dataset.
- It is the **only** mixed token of the form `^\d+[a-z]+` where the leading number is
  >= 10 (types = 1, occ = 3,657), so the family is exactly one token, not a class.
- The brief's `^\d+(e|er|ere|eme)$` guard **does not match it** — it ends in `hr`, not in
  an ordinal suffix.
- Address-side mass for `24hr` = **0**, so the fix is name-side only.

### 4c. NEW DEFECT N2 — `1st` -> `lst` (US 679 + India 381 = 1,060)

`1st` is the ordinary English ordinal. LEET maps `1->l`, producing `lst`. The same
pattern as the French ordinals, in two more countries.

- `1st` is an **English ordinal**, so the brief's French-suffix guard
  `^\d+(e|er|ere|eme)$` **does not match it**.
- `1st` is also the only non-French case of the broader English-ordinal family
  `^\d+(st|nd|rd|th)$` present in the top-4000: `3rd`, `4th`, `5th` are **not in the
  top-4000 name tokens** (absence from a truncated list is not proof of absence).
- `2nd` (India, 253) is the control: it contains `2`, which is **not** a LEET key, so
  `2nd -> 2nd`, unchanged and correct. This proves the corruption is caused specifically
  by the `1->l` key, not merely by the presence of a leading digit.
- **Address side is huge and safe**: `1st` = 305,356 (India) + 16,478 (US) address
  occurrences, all preserved verbatim because `normalize_address` never calls LEET. So the
  *same literal* is destroyed on the name side and preserved on the address side — the
  identical asymmetry D090 documented for `3eme`, at ~150x the mass.

### 4d. Name/address asymmetry, same literals

| country | literal | name occ (corrupted) | addr occ (preserved) |
|---|---|---|---|
| France | `3eme` | 748 -> `eeme` | 350 |
| France | `1er` | 131 -> `ler` | 1,963 |
| US | `1st` | 679 -> `lst` | 16,478 |
| India | `1st` | 381 -> `lst` | 305,356 |
| India | `2nd` | 253 -> `2nd` (safe) | 324,528 |

For `1st` alone: 1,060 corrupted name occurrences against 321,834 preserved address
occurrences. Because `keys.py:33` builds name keys from the LEET-processed `ncore` while
`keys.py:39-43` builds address keys from unprocessed `atoks`, and the kind-0 key at
`keys.py:60` XORs the two, **a business whose name contains `1st` cannot match a business
whose address contains `1st`.** This is the mechanism by which the defect costs matches,
not just dirty tokens.

### 4e. `4l` -> `al` (France, 1,943) — resolved as NOT a defect

D090 left `4l` unresolved. It can now be settled from the profile:
`4l -> al` and India's `a1 -> al` (272) **converge on the same output**. `al` is an
ordinary token (Al / Albert). So `4l` behaves as a **correct** leet expansion of `al`,
not a corruption. It is the largest French mixed type but it is **not** part of the
1,111. Recorded here so the next task does not re-litigate it.

### 4f. Total corrupted mass

| class | occ | caught by `^\d+(e|er|ere|eme)$` |
|---|---|---|
| French ordinals (5 types) | 1,111 | yes |
| `1st` (2 countries) | 1,060 | **no** |
| `24hr` (US) | 3,657 | **no** |
| **total corrupted** | **5,828** | 1,111 (19.1%) |

Against the 176,142 mixed-occurrence denominator that is **3.31%** of all mixed name
tokens corrupted. The remainder (**170,314**, incl. `4l`) are correct leet expansions
and **must keep working** — `c1ub->club`, `mais0n->maison`, `5ervices->services`,
`de1hi->delhi` are the load-bearing cases.

### 4g. Canonical-value collisions among observed tokens

63 distinct output strings are produced by more than one input type. Almost all are
**desirable** many-to-one merges — that is the entire point of the table
(`5ervices`+`s0lutions`+`so1utions` -> `solutions`; `8rothers`+`br0thers` -> `brothers`).
These are the regression set the fix must not break. No collision produces a wrong word.

---

## 5. Empty values, self-maps, and overlap with `ADDR_CANON_COMMON`

- **Empty-string values: none.** All 10 values are single characters. (For contrast,
  `ADDR_CANON_COMMON` *does* carry 13 empty mappings — `"number": ""` ... lines 196-197 —
  which is a different mechanism: token deletion, consumed downstream at `keys.py:39`.)
- **Missing self-maps: none, and none are needed.** No LEET key equals its value, and
  the value space (`a,b,e,g,l,o,s,t`) is disjoint from the key space (digits + symbols),
  so the table is idempotent-safe and non-recursive. A "self-map" concept borrowed from
  the token-dictionary tables (`US_STATES` etc.) **does not transfer to `LEET`** — it is a
  character map, not a lookup dict.
- **Overlap with `ADDR_CANON_COMMON`: none, and it cannot exist.** `LEET` is only ever
  applied at line 280 inside `_name_tokens`; `ADDR_CANON_COMMON` is only ever consulted at
  line 347 inside `normalize_address`. The two tables sit on **disjoint code paths** and
  can never see the same token. Any audit that treats them as potentially interacting is
  wrong. (Note `ADDR_CANON_COMMON` does contain `first->1st`, `second->2nd`, `third->3rd`
  at line 184 — English ordinals as *address* values — but those are address-side and
  never meet LEET.)

### NEW DEFECT D3 — `@` and `$` are unreachable dead code (2 of 10 entries)

`_name_tokens` splits on `_non_alnum` at line 276, and `_non_alnum` is
`re.compile(r"[^a-z0-9]+")` (line 269). So by the time line 280 runs, the token is
guaranteed to contain **only `[a-z0-9]`**. A character-level table lookup for `@` or `$`
can therefore never hit.

Verified: a search for `[@$]` across `normalize.py` returns **only line 256** — no
earlier step maps `@` or `$` to a letter. Therefore:

- `@ -> a` and `$ -> s` are **provably dead** in the current pipeline.
- They are harmless (they cost nothing and corrupt nothing) but they are misleading: a
  maintainer reading the table believes symbol-leetspeak is handled. D090's gap note
  ("`@` and `$` cannot be evaluated") is **resolved here** — not merely unmeasurable, but
  *unreachable by construction*.
- The same blindness applies at profile time: `build_profile.py:28`
  `TOKEN_RE = re.compile(r"[a-z0-9]+")` discards symbols, so no measurement could ever
  have found them.

---

## 6. Where the fix belongs — the judgement the next task consumes

**Verdict: the CALL SITE (`_name_tokens`, `normalize.py:279-280`). Not the table.**

Justification, each tied to a source line:

1. **Not the table — structural.** `LEET` is `str.maketrans`, a character->character map
   (line 256). The defect needs the **whole token** to decide whether to fire
   (`3eme` must stay, but a digit inside `x3eme` is a different question). A character map
   has no context and cannot express "skip this token". The information required is
   strictly more than a per-character table can hold.
2. **Not the table — empirical.** Deleting a key does not work. Measured sole-dependency
   mass per key (tokens whose only leet key present is that digit):
   `0`=71,527, `1`=47,775, `5`=33,541, `8`=9,195, `6`=7,373, `4`=5,600, `3`=869, `7`=9.
   Removing `1` to save `1st` (1,060) would break `de1hi` (1,674), `denta1` (1,652),
   `techno1ogies` (1,288) and 82 other types. Removing `4` to save `24hr` (3,657) would
   break `4l` (1,943). **Every key is load-bearing.**
3. **Not country-scoped — impossible, and also wrong.** Country is not in scope on this
   path at all (signature line 285, call site `prep.py:12`). And a country guard would be
   the wrong shape anyway: N1 and N2 are **US and India** defects. A French-only guard
   fixes 1,111 of 5,828.
4. **Therefore: a guard predicate at the call site**, immediately before line 280, keyed
   on the whole token. Per §3 it must be token-anchored (`^...$`).

**Constraint on the fix, established here:** the guard must **exempt** rather than
**extend** — 170,314 of 176,142 observed mixed occurrences (96.7%) are correct leet
expansions. Any change must be a no-op on those, and `c1ub->club` / `mais0n->maison` are
the named regression cases. Also (§2 ordering) a `NAME_CANON` entry keyed `"3eme"` cannot
work today, because line 281 sees `"eeme"` — the guard must run *before* line 280 if a
`NAME_CANON` ordinal entry is also wanted.

---

## 7. Gaps — stated, not estimated

- **`addr_tokens` is also top-4000 and count>=2 per country** (`build_profile.py:126-127,
  141`). Address-side masses in §4d are **lower bounds**, and the top-4000 cap means a
  literal absent from `addr_tokens` is *not* proven absent.
- **~8-10% of name-token mass is outside the top-4000 cut.** All type-level lists here
  (284 types) are floors, not complete enumerations. The 284 / 176,142 figures are
  "observed within the top-4000", not "total in the data".
- **No profile field counts how many ROWS a given token type appears in** — only token
  occurrences. The per-row impact of the 5,828 corrupted occurrences is **not derivable**
  from the profile. Do not quote a row count for the ordinal defect.
- **No raw-data check was possible or attempted** (hard constraint). The `4l` resolution
  in §4e is inferred from output convergence with `a1->al`, not from a source-data read.
- **Country-level `rows` is absent for France in all three train files** (`by_country` has
  no `France` key). France is test-only, as D090 already established.

## 8. Not re-derived (already settled, per work order)

- No country has a postal field; the `pin` guard should be left alone.
- `pin_eq` / `alt_tset` are dead.
- `US_STATES` / `IN_STATES` / `FR_REGIONS` need no expansion.
- France blocking caps are healthy.
- Address component order is not a problem.
- Ligature deletion and inline-postcode losses are confirmed but negligible.
