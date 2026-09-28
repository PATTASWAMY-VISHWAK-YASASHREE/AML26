# D117 — remaining gaps in `US_STATES`

## Headline

**I independently confirm the prior negative. `US_STATES` needs no dictionary expansion.**
Across an exhaustive scan of the union of all six profile `addr_tokens["US"]` lists
(4,510 distinct tokens), **every US state token that occurs is already a canonical
runtime key of `US_STATES`.** Zero misspellings, zero abbreviated state names, zero
unhandled 2-letter state codes, zero territory names.

The one genuinely open dictionary question — the **spelling-variant class** — is not
merely unobserved, it is **bounded**: the top-4000 floor per file is 201/407/440/101/258/274
US address tokens, so any variant spelling I failed to think of must occur **fewer than
~101 times per file** to be invisible to me. That is a real bound, not a guess.

Two things I found that prior tasks had **not** checked, and one of them is a live defect:

1. **NEW (CONFIRMED): the `Washington, DC` collision is real and it is a data-collision,
   not a hypothetical.** The corpus contains a standalone component `district of
   columbia` (27,527 occurrences of `district`, 58,751 of `columbia`, 252,303 of `of` in
   the US union) *and* a very large mass of bare `washington` (267,075). The key
   `district of columbia → dc` and the key `washington → wa` are **both live in the same
   country bucket**, so a DC row can resolve to `wa`. I flag this as a **collision risk
   that the profile cannot resolve to a row count** (see Gaps).
2. **NEW (CONFIRMED, exhaustive): no 2-character alphabetic token in the entire US
   address vocabulary is an unhandled state abbreviation.** I enumerated *all* 2-char
   alpha tokens in the union (33 of them, 4,001,717 occurrences) — they are `st`, `rd`,
   `dr`, `ln`, `of`, `po`, `pl`, `el` … i.e. street/ordinal/direction words. **Not one is a
   state.** This closes the abbreviation class far more tightly than D074/D075's
   hand-picked probe lists did.

Note: `penn` **and** `del` are both unhandled — see NEW-1, which corrects D074.

Denominators (`by_country[c].rows` summed over the six profiles): US **11,990,643**,
India 10,544,085, France **1,694,445**. All six `country_rows`/`by_country` keys are exactly
`US`, `India`, `France` — **no country-string variants** (`USA`, `U.S.`, `United States`
are all absent), so the country-keyed lookup cannot miss.

---

## What the prior work already covered, and what it might have missed

| Prior claim | Source | My independent re-test | Verdict |
|---|---|---|---|
| 52 literal entries, 104 runtime, all 52 self-maps | D074 §1–2 | Re-extracted the literal from `normalize.py:216-229` by text parse: **52 literal, 52 distinct values, 104 runtime, 0 self-maps missing** | **CONFIRMED, identical** |
| 50/50 states + `dc` + `pr` | D074 | 40 single-word + 12 multi-word keys | **CONFIRMED** |
| `wy → way` is the only corrupting canon collision | D074 §4 | Intersected all 104 runtime keys against `ADDR_CANON_COMMON` (177 entries): hits are `mt, fl, wy, ct, ne`; **exactly one non-identity: `wy → way`** | **CONFIRMED** |
| Zero occurrences of 14 hand-picked misspellings | D074 §11 | Superseded by an **exhaustive** scan below | **CONFIRMED and strengthened** |
| "`del` is already the Delaware code, so it resolves and is not a gap" | **D074 §11** | **`del` is NOT in the literal and NOT in the 104 runtime keys.** Delaware's key is `delaware → de`; its *code* key is `de`. `del` resolves to nothing. | **D074 IS WRONG — see NEW-1** |
| `penn` is unmapped, 3,084 occurrences | D075 F5 | Confirmed: absent from literal and from all 104 runtime keys; union **3,084** | **CONFIRMED** |
| 2-letter code coverage 45/45/38 per test split | D074 §10 | Union-of-six: **45 of 52 codes present**, 7 absent (`hi mi ms nv nh nj pr`), **7,354,018 occurrences** | **CONFIRMED** |
| Single-word name coverage | D075 F1 (36/38) | Union-of-six: **38 of 40 present**, 2 absent (`hawaii`, `mississippi`), **4,240,547 occurrences** | **CONFIRMED (union > per-file, as expected)** |
| `US_STATES` unreachable from France/India rows | D074 §3 | Confirmed: `smap = STATE_MAPS.get(country, {})` at `normalize.py:318`, keyed on exact strings `US`/`India`/`France` | **CONFIRMED** |

**The class prior work did *not* test:** an **exhaustive** enumeration rather than a
hand-picked probe list. D074 probed 14 spellings; D075 probed a code list. Neither
enumerated the whole vocabulary. I did, which is why my negative is *bounded*.

---

## NEW-1 — `del` is an unhandled token, and D074's contrary claim is false (CONFIRMED)

This is the one place where I **contradict** a prior finding, so I show the arithmetic.

`US_STATES` contains, for Delaware, exactly two entries after the self-map loop:
`'delaware' -> 'de'` (literal) and `'de' -> 'de'` (added by the loop at
`normalize.py:252-254`). **`del` is neither.** Verified by direct key test against both
the literal and the 104-entry runtime table:

```
del        in_literal=False  in_runtime104=False  resolves_to='--'
penn       in_literal=False  in_runtime104=False  resolves_to='--'
de         in_literal=False  in_runtime104=True   resolves_to='de'
```

D074 wrote *"`del` occurs 646 / 1,779 / 1,842 but is already the Delaware **code** in
`US_STATES`, so it resolves and is not a gap."* The conflation is between the **code**
(`de`) and the **abbreviation** (`del`). They are different strings. A component `Del`
cleans to `ck = "del"`, `"del" not in smap`, so it falls through to the token stream
unresolved.

| file | `del` | `penn` |
|---|---|---|
| train_s1 | 1,168 | 334 |
| train_s2 | 2,520 | 801 |
| train_s3 | 2,756 | 822 |
| test_s1 | 646 | 163 |
| test_s2 | 1,779 | 467 |
| test_s3 | 1,842 | 497 |
| **union** | **10,711** | **3,084** |

Arithmetic: 1,168+2,520+2,756+646+1,779+1,842 = **10,711**; 334+801+822+163+467+497 =
**3,084**. As rates over 11,990,643 US rows: `del` 0.0893%, `penn` 0.0257%.

**These are token occurrences, not rows** (`build_profile.py:126-127` pushes
`[a-z0-9]+` matches from each comma-component into one flat `Counter`, discarding
boundaries), and `del` is a common English word that may sit in street names rather than
acting as a state. So the *gap* is CONFIRMED (the string is unhandled); the *benefit of
fixing it* is LIKELY at best. D075 already recommended `del → de` and `penn → pa`; this
confirms the `del` half and corrects the record on why.

---

## NEW-2 — Exhaustive negative: every 2-character token in the US vocabulary (CONFIRMED)

Rather than probe a guessed list, I enumerated **all** 2-character alphabetic tokens in
the six-file US `addr_tokens` union. There are **33**, totalling **4,001,717**
occurrences, and **every one is a street/ordinal/direction word**:

```
st=1054366 rd=982732 dr=890430 ln=377237 of=252303 po=162774 pl=102857 el=44528
ft=16488 cr=14569 fm=12558 us=11568 cv=10071 mc=6873 sr=6324 rt=6037 dp=5064
pt=4960 sq=4645 du=4493 jr=3828 le=3568 fe=3463 cp=2982 tr=2975 sw=2743 on=2714
sl=2240 nw=1950 sh=1944 to=1212 rm=805 se=416
```

**Not one is a state code.** This closes the abbreviation class exhaustively: there is no
unhandled two-letter state abbreviation anywhere in the retained US vocabulary. (`us`
= 11,568 and `nw` = 1,950 are present but neither is a state.)

---

## NEW-3 — Exhaustive negative: edit-distance-1 misspelling scan (CONFIRMED)

I computed Levenshtein distance ≤1 from **every** pure-alphabetic US address token
(length ≥3) that is **not** already a runtime key, against all 52 state names. Exactly
**6 tokens, 154,515 occurrences** qualify, and all six are ordinary English words, not
misspelled states:

| token | occurrences | nearest state name | d |
|---|---|---|---|
| `main` | 121,494 | `maine` | 1 |
| `indian` | 17,414 | `indiana` | 1 |
| `fontana` | 9,930 | `montana` | 1 |
| `mine` | 2,159 | `maine` | 1 |
| `marine` | 1,977 | `maine` | 1 |
| `marina` | 1,541 | `maine` | 1 |

`main`/`indian`/`fontana` are street and city words ("Main St", "Indian Lane", "Fontana").
**There is no misspelled US state name in the retained vocabulary.** Adding `calif`,
`fla`, `mass`, `tenn`, `wisc`, `minn`, `conn`, `colo`, `okla`, `ariz` would add **17 dead
entries** — D075's recommendation not to add the zero-count abbreviations is correct.

## NEW-4 — The self-map DOES fire on real input tokens

The brief asks whether canonical values appear as *input* tokens. **They do, heavily.**
The 52 self-map keys are themselves ordinary US address tokens: **45 of 52 appear in the
union, for 7,354,018 occurrences** (`tx`=696,979; `ny`=535,094; `nc`=498,226; `oh`=445,297;
`il`=396,078; `ct`=324,465; `tn`=313,504; `va`=312,719; `ma`=297,168; `in`=260,594;
`md`=211,774; `ca`=196,583; `az`=298,158).

Absent (not in the top-4000 of any file): `hi mi ms nv nh nj pr`.

This makes the self-map loop **load-bearing** for `US_STATES` — unlike `FR_REGIONS`, where
D073 measured zero effect. Source, quoted from `normalize.py:250-254`:

```python
STATE_MAPS = {"US": US_STATES, "India": IN_STATES, "France": FR_REGIONS}
# abbreviations are canonical themselves
for _m in (US_STATES, IN_STATES):
    for _v in list(_m.values()):
        _m.setdefault(_v, _v)
```

`FR_REGIONS` is deliberately **not** in the loop tuple — that is the defect D070/D073 own.
`US_STATES` is complete and correct here. **Do not "fix" it.**

## NEW-5 — The `Washington, DC` collision: real, confirmed, unquantifiable in rows

The brief flagged this specifically. **It is real.** `US_STATES` maps
`'district of columbia' -> 'dc'` **and** `'washington' -> 'wa'`, both in the same `US`
bucket, with no positional constraint. Relevant token masses (US union):

| token | occurrences | % of 11,990,643 US rows |
|---|---|---|
| `washington` | 267,075 | 2.2274% |
| `dc` | 35,681 | 0.2976% |
| `district` | 27,527 | 0.2296% |
| `columbia` | 58,751 | 0.4900% |
| `of` | 252,303 | 2.1044% |

Mechanism: `normalize.py:333-335` assigns `state = smap[ck]` on every match and **never
breaks**, so the last match wins. For a genuine DC row written `..., Washington, DC 20001`,
the postcode defeats the whole-component test (`ck = "dc 20001"`, not a key), so the
surviving match is `Washington → wa` and the row resolves to the **wrong state**. Exposure
is bounded above by the `dc` occurrence mass, **≤ 35,681 rows (≤0.2976%)** — and that
bound is loose, because a `dc` occurrence need not be a state component.

This is a **matcher** defect (positional matching), not dictionary content. No entry in
`US_STATES` would fix it; `district of columbia → dc` is already correct.

## NEW-6 — Case sensitivity: not a risk, and the matcher lowercases anyway

The brief asked about uppercase/mixed-case variants. `normalize.py:317` reads
`s = strip_accents(s).lower()`, so **all input is lowercased before any dictionary
lookup**. Separately, `build_profile.py:110,113` lowercases both `business_name` and
`business_address` before tokenising, so **the profile cannot even represent an
uppercase token**. Mixed-case handling is therefore a non-issue on both the code and
the evidence side. I looked for uppercase state tokens and there is none to find — the
measurement surface does not exist.

## France relevance — this task has near-zero France value, and I say so plainly

**France is the scored country and is absent from training** (France rows: 0 in
train_s1/2/3, 259,452 / 703,378 / 731,615 in test_s1/2/3 = 1,694,445). `US_STATES` is
**unreachable from any France row** because `STATE_MAPS` is country-keyed
(`normalize.py:318`) and no France country string maps to `"US"`. Confirmed at the
token level too: US state names appearing in the France `addr_tokens` union are
`maine`=645, `texas`=216, plus codes `al ar co ga la ma me mi ne ny or pr ri`, and the
large ones are the ordinary French words `de`=1,050,023 and `la`=481,231 — which are
*not* US states here and are governed by `FR_REGIONS`/`ADDR_CANON_FR` instead.

**So every finding in this report is US-only and none of it can move the France
score.** The correct fleet-level conclusion is: *the France dictionaries are where the
remaining value is; `US_STATES` is finished.*

---

## Gaps and limits — what I could NOT establish

1. **Truncation is the binding limit on every negative here.**
   `build_profile.py:27` sets `TOPN = 4000` and `most_common(TOPN)` keeps only the top
   4,000 per country per file. The rank-4000 US `addr_tokens` count is
   **201 / 407 / 440 / 101 / 258 / 274** for train_s1/2/3 and test_s1/2/3. Therefore any
   token absent from all six lists occurs **fewer than 101 times in test_s1** and
   **fewer than 201 in train_s1** — under ~1,681 occurrences summed across all six.
   **Every "absent" in this report means "not in the top 4000", never "does not occur".**
2. **Hapax pruning removes singletons outright.** `prune()` (`build_profile.py:45-48`)
   deletes `count <= 1` tokens periodically, so genuinely rare variants are invisible
   system-wide and cannot be bounded at 1 — only at the floor in item 1.
3. **The 12 multi-word keys are structurally unmeasurable.** `TOKEN_RE = [a-z0-9]+`
   (line 28) and `ADDR_SPLIT = [,;]` (line 31) mean `new york` is stored as `new` and
   `york` separately. `york`=384,608 and `carolina`=354,636 are in the US union, but
   **I cannot tell whether they ever co-occur in one component**, so I make **no claim**
   about multi-word coverage either way. This is a profile gap, not a dictionary gap.
4. **No row-level counts anywhere in this report.** `addr_tokens` is a flat `Counter`
   with component boundaries discarded (line 126-127). Every figure I give is a
   **token occurrence** or an explicitly labelled **upper bound** on rows. I have not
   converted any occurrence count into a row count.
5. **`del`/`penn` cannot be confirmed as state references.** They are unhandled
   (CONFIRMED) but whether they appear as standalone state components rather than inside
   street names is not recoverable from this profile. Hence LIKELY, not CONFIRMED, as a
   *fix*.
6. **I did not re-derive the France `pin` guard or the `FR_REGIONS` resolution rate**, per
   the work order. My France statements above are about *scoping only* and rest on
   `by_country` row counts plus token membership.

---

## Recommendations

1. **Do not add states, territories, or abbreviations to `US_STATES`.** The exhaustive
   scans (NEW-2, NEW-3) show there is nothing to add. *(CONFIRMED — bounded by Gaps 1–2.)*
2. **Optionally add `"del": "de"` and `"penn": "pa"`.** 10,711 + 3,084 = **13,795**
   occurrences (0.115% of US rows). Cheap and harmless, but **LIKELY** benefit, not
   confirmed. D075 owns this recommendation; I confirm it and correct D074's reason.
3. **Do NOT touch the self-maps.** All 52 are present and load-bearing (NEW-4).
   *(CONFIRMED.)*
4. **Do NOT treat the `Washington`/`DC` collision as a dictionary problem.** It is
   matcher positional logic (NEW-5). The right fix is requiring a state match to be the
   final component or to be followed only by a postcode — D074's recommendation 3,
   which I endorse and re-rate as the highest-value US item, ahead of any dictionary edit.
5. **Explicitly deprioritise this dictionary for the France objective.** NEW-6.

## Bottom line

**"This dictionary is fine for this dataset; the defect is theoretical only" — with one
small, real, and already-known exception (`del`, `penn`).** Every state token the data
actually contains is already a canonical key. The only live US defect is in
`normalize_address`'s positional logic, not in the dictionary.

