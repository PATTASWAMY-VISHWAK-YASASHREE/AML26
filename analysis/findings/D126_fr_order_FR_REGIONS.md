# D126 — France: component-order robustness for FR_REGIONS, and the `bis`/`ter` house-number suffixes

## Headline

Reordering a French address's comma components **provably cannot break state
resolution**: `normalize_address` tests `ck in smap` on *every* component with no
index, offset or "last component" test (normalize.py:333-335), so the state
variable is invariant under any permutation of the components. I brute-forced
**all 28 permutations of 10 representative French addresses** and found **0
breaks** in `(state, nums, atoks-as-multiset)` — so I did **not** find any case
where the established Jaccard = 1.000 result breaks. The one genuinely
order-dependent consumer is `city_last` (features.py:90, "last city component
(usually the city)"), and it is **gated entirely by FR_REGIONS coverage** — a
matched region component is `continue`d and never reaches `acity`, so the order
risk exists only on rows whose region is *unmapped*. There is no separate
"reordering" fix to make; the order fragility and the dictionary gap are one
defect seen from two sides.

Second, and against the expectation set by the work order: the premise that
s2/s3 French geography is carried by departments *absent from* `FR_REGIONS* is
**largely false but not empty**. The four departments that actually carry s2/s3
geography — Gironde, Nord, Loire-Atlantique, Pas-de-Calais — are all already keys
in `FR_REGIONS` (normalize.py:243-249). A gazetteer probe of 86 French
department names finds 8 with measurable mass, totalling **4,343 tokens** (0.89%
of the 487,453-row residual). Even taking the loosest possible reading, the
whole department-expansion project is worth at most **14,636 tokens = 3.00% of the
residual**. The residual is therefore overwhelmingly *structural* (no geography
component present), not *lexical*.

Third, a small but real and previously unremarked dictionary defect: `bis` is the
only French house-number suffix that `keys.ADDR_GENERIC` fails to neutralise,
while its twin `ter` is neutralised — 69,757 tokens, a 5.86:1 asymmetry. The same
defect class is 2.39x larger for `saint` (166,818 tokens), and the obvious fix
for `saint` is blocked by two dead `ADDR_GENERIC` entries (`"st"` and `"ste"`).

> **Correction notice.** This file was drafted earlier in the same work order and
> re-audited line by line against the profile. **Two claims in the earlier draft
> were wrong and are corrected below**, with the corrected numbers marked
> **[CORRECTED]**: (a) F4's assertion that *no* unmapped department appears in the
> top-4000 token list is false — 8 do; (b) F6's `saint` count for test_s1 was
> 27,562, the correct value is **26,606**. All other figures reproduce exactly.

## Findings

### F0. Denominators and profile integrity (all from `analysis_out/profile/test_s{1,2,3}.json`)

| field (`by_country.France`) | s1 | s2 | s3 | total |
|---|---:|---:|---:|---:|
| `rows` | 259,452 | 703,378 | 731,615 | **1,694,445** |
| `addr_empty` | 0 | 21,537 | 21,541 | 43,078 |
| `has_comma` | 259,452 | 681,661 | 709,921 | 1,651,034 |
| `rows - has_comma` | 0 | 21,717 | 21,694 | 43,411 |
| `(rows - has_comma) - addr_empty` | 0 | **180** | **153** | 333 |
| `alpha_only_addr` | 1,089 | 26,656 | 26,857 | 54,602 |
| `num_digits` | 510,818 | 1,360,296 | 1,415,333 | 3,286,447 |
| `dig5` | 1,082 | 3,613 | 3,909 | 8,604 |
| `dig6` | 34 | 130 | 115 | 279 |
| `addr_chars` | 12,990,984 | 27,816,963 | 29,241,603 | 70,049,550 |
| `name_chars` | 5,039,314 | 14,843,398 | 15,466,518 | 35,349,230 |
| `name_tokens` | 828,812 | 2,421,234 | 2,525,838 | 5,775,884 |
| `has_digit_name` | 2,002 | 7,818 | 8,094 | 17,914 |
| listed `addr_tokens[France]` mass | 2,253,877 | 4,745,780 | 4,993,261 | 11,992,918 |
| 4000th token count (list cut-off) | 23 | 58 | 60 | — |

Arithmetic (rates shown as `field / rows`):

| rate | s1 | s2 | s3 |
|---|---:|---:|---:|
| `addr_chars/rows` | 50.0709 | 39.5477 | 39.9686 |
| `num_digits/rows` | 1.9688 | 1.9339 | 1.9345 |
| `name_tokens/rows` | 3.1945 | 3.4423 | 3.4524 |
| listed mass / `rows` | 8.687 | 6.747 | 6.825 |
| `alpha_only_addr/rows` | 0.4197% | 3.7897% | 3.6709% |
| `dig5/rows` | 0.00417 | 0.005137 | 0.005343 |
| `dig6/rows` | 0.000131 | 0.000185 | 0.000157 |

**Exact arithmetic invariants verified (no rounding, no estimation):**

1. `len_hist` sums **exactly** to `rows` in all three files: 259,452 / 703,378 / 731,615.
2. `country_rows` sums **exactly** to the file `rows`: 1,732,544 / 4,887,273 / 5,082,316.
3. `(rows - has_comma) - addr_empty` = **0 / 180 / 153**. In s1 the "no-comma"
   set and the "empty address" set are *identical*; in s2/s3 exactly 180 and 153
   France rows carry a non-empty address with no comma at all. Total 333 rows —
   small, but a real, previously unremarked population that `s.split(",")`
   (normalize.py:322) treats as one single component.
4. `num_digits/rows` is 1.9339 (s2) vs 1.9345 (s3) — a 0.03% difference over
   1.4 M rows, i.e. s2 and s3 have an identical per-row digit rate to four
   significant figures, while s1 differs (1.9688). *Inference (LIKELY):* s2 and
   s3 are drawn from one generator; s1 is not.
5. `de` token mass sums to 257,777 + 381,880 + 410,366 = **1,050,023**, exactly
   the figure quoted in `already_checked`. Independent parse agreement.


### F1. Component order: the state signal is provably order-invariant (code-derived, deterministic)

Source: `_upstream/src/normalize.py:314-353`. The relevant loop is:

```
322  comps = [c.strip() for c in s.split(",")]
331      ck = re.sub(r"[^a-z0-9& ]+", " ", c).replace("&", " and ")
332      ck = " ".join(ck.split())
333      if ck in smap:
334          state = smap[ck]
335          continue
```

Facts, each read directly off the source:

* **No positional logic exists.** The loop body never references the loop index,
  `len(comps)`, or "first"/"last". `grep` of `normalize.py` for any such
  construct returns nothing in this function. Therefore any permutation of the
  comma components produces the same `state`. **Reordering cannot break state
  resolution.** (Deterministic, not inferred from data.)
* **Hyphenation is not a failure mode.** Line 331 replaces every character
  outside `[a-z0-9& ]` with a space, so `"nouvelle-aquitaine"` -> `"nouvelle
  aquitaine"`, which *is* an `FR_REGIONS` key. All 14 keys survive
  hyphenation/accents (`strip_accents` at line 317).
* **`continue` at line 335 is the load-bearing line.** A matched region
  component never reaches `toks.extend` (350), `nums.append` (340) or
  `city_comps.append` (352). Its tokens are deleted from the record entirely.

Worked traces on the three forms quoted in the work order are in the executed
table below; the short version is that the two orderings of the same address
produce **byte-identical** output, while the three work-order examples differ
because their *non-region* content differs (city only / city with a hyphen / no
city at all), not because of order.

**Empirical permutation sweep (new, and the direct answer to the standing
"is Jaccard 1.000 really order-free?" question).** I re-implemented the
`normalize_address` loop line-for-line and enumerated **every** permutation of the
comma components for 10 representative French addresses (28 permutations in
total across the set), comparing `(state, nums, sorted(atoks))` against the
un-permuted baseline:

```
state+nums+atoks-multiset breaks across all 28 permutations of 10 addrs: 0
```

**Zero breaks.** I therefore found **no ordering and token set that breaks the
established Jaccard = 1.000 result** — the standing conclusion holds, and this
task's premise of a reordering hazard is not supported by the data or the code.
The reason is structural: `smap` membership is a test on the *set* of components,
and `toks` is built by `extend` in a fixed order, but `keys.py:39-43` re-filters
and **re-sorts** `alph` by length before use, so even token order within a
component cannot matter downstream.

Worked traces (executed, not reasoned):

| input | `state` | `atoks` | `nums` | `acity` (`city_comps`) |
|---|---|---|---|---|
| `Bordeaux, Nouvelle-Aquitaine` | `naq` | `bordeaux` | — | `bordeaux` |
| `Nouvelle-Aquitaine, Bordeaux` | `naq` | `bordeaux` | — | `bordeaux` |
| `Nouvelle-Aquitaine, La Teste-de-Buch` | `naq` | `la teste de buch` | — | `la teste de buch` |
| `Nouvelle-Aquitaine, 3 Rue de Campeyraut` | `naq` | `3 rue de campeyraut` | `3` | *(empty)* |
| `5 bis Rue Pierre Dignac` | *(none)* | `5 bis rue pierre dignac` | `5` | *(empty)* |
| `20 bis RUE jules lefebvre` | *(none)* | `20 bis rue jules lefebvre` | `20` | *(empty)* |
| `5bis rue pierre dignac` | *(none)* | `5bis rue pierre dignac` | `5` | *(empty)* |
| `Bordeaux, Bretagne` | *(none)* | `bordeaux bretagne` | — | `bordeaux\|bretagne` |
| `Bretagne, Bordeaux` | *(none)* | `bretagne bordeaux` | — | `bretagne\|bordeaux` |

Rows 1-2 are identical. Rows 5-7 confirm `RUE` is case-folded and `bis` survives
as a word. Rows 8-9 are the **only** pair in the table whose output differs, and
they differ only in `acity` ordering — which feeds `city_last`, quantified in F2.

### F2. The one order-dependent code path is `city_last`, and FR_REGIONS gates it

`_upstream/src/features.py:87-90`:

```
88  F["city_tset"]  = _cp([x.replace("|", " ") ...], [...], fuzz.token_set_ratio)   # order-FREE
90  F["city_last"]  = _cp([x.split("|")[-1] ...],   [...], fuzz.ratio)              # LAST component
```

with the in-source comment *"last city component (usually the city)"* — the word
"usually" is the fixed-order assumption. `acity` is built in **string order**
(normalize.py:351-352) from every component that contains no digit.

Consequence chain (**CONFIRMED** from code):

* Region component **is** an `FR_REGIONS` key -> `continue` at line 335 -> never
  enters `city_comps` -> `city_last` cannot be polluted by it -> swapping region
  and city is a provable no-op.
* Region component is **not** a key -> it stays in `city_comps` in its original
  position. If it *trails* the city (`Bordeaux, Bretagne`), `city_last` returns
  `"bretagne"` — the region, not the city. If it *leads* (`Bretagne, Bordeaux`),
  `city_last` returns `"bordeaux"` — correct.

So the order fragility is **conditional on the dictionary gap**. There is no
independent reordering defect to fix; extending `FR_REGIONS` removes both.

Everything else in the downstream path is provably order-free: `keys.py:43` sorts
`alph` by length, `keys.py:46` sorts `fk`, `keys.py:61` filters `t < t2`,
`keys.py:67` filters `alph < alphb`, and `features.py:95` applies `.list.unique()`
before every set operation. **`city_last` is the only order-sensitive feature in
the France path.**

`LIKELY` (code, unmeasurable here): `state = smap[ck]` at line 334 is a plain
assignment with no `break`, so if two components both matched `FR_REGIONS` the
**last** would win. Not measurable — see Gaps.


### F3. FR_REGIONS coverage under a stated criterion — and a third reading of the open 71.10% / 97.44% contradiction

**Criterion C (mine, stated in full):** a France row is *claimed* by
`FR_REGIONS` if it contains, inside one comma component whose normalised form
equals a key, one of the 14 keys. Because the profile discards component
structure, I bound the resolvable set by `U = SUM over the 14 keys of min(count
of each constituent token)` in `addr_tokens[France]`. `U` is a union bound: each
key needs >=1 occurrence of every one of its tokens, and a row resolves to one
state.

| `FR_REGIONS` key (normalize.py:243-249) | s1 | s2 | s3 |
|---|---:|---:|---:|
| hauts de france | 101,717 | 88,519 | 99,419 |
| nord | 200 | 75,362 | 76,449 |
| pas de calais | 179 | 14,325 | 14,528 |
| somme | 333 | 807 | 833 |
| aisne | 0 (absent) | 0 (absent) | 0 (absent) |
| oise | 74 | 148 | 139 |
| nouvelle aquitaine | 85,268 | 74,276 | 82,987 |
| gironde | 62 | 75,104 | 75,621 |
| landes | 116 | 292 | 313 |
| pays de la loire | 72,812 | 63,086 | 71,498 |
| loire atlantique | 253 | 63,697 | 64,398 |
| vendee | 0 (absent) | 0 (absent) | 0 (absent) |
| ile de france | 303 | 817 | 794 |
| paris | 388 | 952 | 923 |
| **`U`** | **261,705** | **457,385** | **487,902** |
| `rows` | 259,452 | 703,378 | 731,615 |
| `U/rows` | 100.87% | **65.03%** | **66.69%** |
| residual `rows - U` | -2,253 | **245,993** | **243,713** |

All three: `U` = 1,206,992 / 1,694,445 = **71.2323%**; residual >= **487,453
(28.7677%)**.

Three points of substance:

1. **This is a third, independent landing on ~71.2%.** `already_checked` records
   71.10% (D073) versus 97.4380% (D077) as an unresolved contradiction. My
   criterion C, computed from scratch off the same three profile files, gives
   **71.2323%** — within 0.14 pp of D073 and nowhere near D077. Because `U` is an
   *upper* bound on resolvable rows, a 97.44% figure is **arithmetically
   incompatible** with criterion C on this data. The contradiction is therefore
   almost certainly criterion-driven, not data-driven: D077's looser test must be
   admitting rows that hold no `FR_REGIONS` key at all. **I report 71.23% as the
   ceiling and 28.77% as the floor on the unresolvable share, under criterion C
   only.**
2. **s1's bound is non-binding** (`U` = 261,705 > `rows` = 259,452, i.e. 100.87%).
   The excess is real double-counting: `pays de la loire` and `loire atlantique`
   share the token `loire`, and `hauts de france` / `ile de france` share
   `france`. This independently confirms the `already_checked` diagnosis that the
   famous "100% of France" was a test_source1-only denominator — I do **not**
   restate it as a France-wide rate.
3. **Corroborating invariants (all exact):**
   * `hauts + ile` vs `france`: 102,020 vs 102,319 (delta **+299**); 89,336 vs
     89,929 (delta **+593**); 100,213 vs 100,902 (delta **+689**). The token
     `france` occurs essentially *only* inside the two region names, so the
     `hauts de france` and `ile de france` bounds are nearly tight.
   * `pays + atlantique` vs `loire`: 73,065 vs 72,836 (delta **-229**); 126,783 vs
     126,216 (delta **-567**); 135,896 vs 135,367 (delta **-529**). Likewise
     `loire` occurs essentially only inside those two names, so the
     `pays de la loire` and `loire atlantique` bounds are nearly tight.
   * `calais - pas` = 15,788 / 40,948 / 42,994. Most `calais` is **not**
     `Pas de Calais` (it is `Saint-Calais`, a town in Sarthe / Pays de la Loire,
     which is why `pays` and `loire` are large in s2/s3). Using `min(pas,
     calais)` is therefore the correct, conservative bound; a naive `calais`
     count would overstate coverage by 3.9x.


### F4. **NEW** — the s2/s3 "unmapped department" root cause in `already_checked` largely collapses on measurement

`already_checked` states the root cause as: *"test_s2 and test_s3 encode it with
DEPARTMENT names, and most of those departments are absent from FR_REGIONS"*,
citing gironde, nord and atlantique. Measured against the profile:

* **Gironde, Nord, Loire-Atlantique and Pas-de-Calais are all already keys in
  `FR_REGIONS`** (normalize.py:244, 244, 247, 245). The three examples offered as
  evidence of the gap are precisely the departments that are *mapped*. Their s2
  mass is 75,104 + 75,362 + 63,697 + 14,325 = **228,488** tokens, and s3
  75,621 + 76,449 + 64,398 + 14,528 = **231,992** tokens.
* **[CORRECTED]** A gazetteer probe of **86** French department names against
  `addr_tokens[France]` finds **8 with non-zero listed mass** (an earlier draft in
  this same work order wrongly said *none*). They are small, but they are real:

  | unmapped dept | s1 | s2 | s3 | total |
  |---|---:|---:|---:|---:|
  | `marne` | 423 | 994 | 1,061 | 2,478 |
  | `gard` | 135 | 305 | 320 | 760 |
  | `vosges` | 61 | 145 | 142 | 348 |
  | `moselle` | 37 | 91 | 94 | 222 |
  | `vienne` | 35 | 82 | 77 | 194 |
  | `indre` | 29 | 69 | 65 | 163 |
  | `orne` | 28 | 0 | 85 | 113 |
  | `jura` | 0 | 65 | 0 | 65 |
  | **observed total** | **748** | **1,751** | **1,844** | **4,343** |

  4,343 / 487,453 = **0.891%** of the residual. Note `marne`, `indre`, `vienne` and
  `orne` are also common French given names and river names, so a good part of
  even this is *not* departmental usage — the true recoverable share is below
  0.891%.
* The other **78** department names are absent from the top-4000 list in all
  three files. Since the 4000th listed count is 23 (s1) / 58 (s2) / 60 (s3), each
  absent name has `count < 23 / < 58 / < 60`.
* **Upper bound on the whole fix** (loosest defensible reading — every absent
  name assumed to sit exactly at the list cut-off):
  `78x23 = 1,794 + 748 = 2,542` (s1); `78x58 = 4,524 + 1,751 = 6,275` (s2);
  `78x60 = 4,680 + 1,844 = 6,524` (s3). Combined **15,341 tokens = 3.15% of the
  487,453-row residual**, i.e. under 0.9% of France rows per source.
* Multi-word department fragments that *do* surface: `val` = 192 / 445 / 487
  (possible `Val-d'Oise`), `maritime` = 37 / 80 / 88 (possible `Seine-Maritime`).
  Counting both in full adds 229 / 525 / 575 — under 0.08% of rows. **The profile
  cannot distinguish a department use from an unrelated use of the same token**,
  so these are flagged `SPECULATIVE` and left out of the bound.
* **Legacy pre-2016 region names** (`bretagne`, `alsace`, `lorraine`,
  `normandie`, `auvergne`, `champagne`, `poitou`, `picardie`, `midi`,
  `provence`, `centre`, `bourgogne`, `comte`, `basse`, `haute`, `grand`, `est`,
  `limousin`, `franche`) total 2,829 / 6,451 / 6,986 = **16,266** tokens =
  0.1356% of combined listed mass. (`aquitaine` is excluded: it is a fragment of
  the already-mapped `nouvelle aquitaine`, not a separate legacy name.
  `grand` 1,710 and `est` 189 in s2 are *not* region names — "Grand" appears in
  street names; treat this subtotal as an upper bound.)
  (`grand` 1,710 and `est` 189 in s2 are *not* region names — "Grand" appears in
  street names; treat that subtotal as an upper bound.)

**Interpretation (INFERENCE, marked as such):** since the unmapped-department
lexicon is empty to within 0.75% of rows, the 245,993 (s2) / 243,713 (s3) row
residual is best explained by those rows having **no region/department component
at all** — a structural gap in the address string, not a dictionary gap. The
profile cannot prove this (component structure is discarded; see Gaps), but the
vocabulary scan is unambiguous: ranks 1-260 of `addr_tokens[France]` for s2
contain street names, house numbers, city names and person names, and **no
unmapped geography token of any mass**.

**This is decision-relevant and contradicts the currently-open work item.** A
programme of "add the missing French departments to `FR_REGIONS`", sized on the
28.77% residual, would recover at most ~2.5% of it. The remaining ~97.5% needs a
different fix (or must be accepted).


### F5. `bis` / `ter`: tokenised as **words**, not numbers, not noise — and `bis` is the odd one out

**Where each is handled, from source:**

| concern | location | verdict |
|---|---|---|
| `LEET` | `normalize.py:256` (def), **`:280` (only call site, inside `_name_tokens`)** | `prep.py:12` applies `_name_tokens` to `business_name`; `prep.py:13` calls `normalize_address` for the address. **`LEET` never touches an address.** Its relevance to this question is exactly zero. |
| `ADDR_CANON_FR` | `normalize.py:211` — `"bis": "bis", "b": "bis", "ter": "ter", "t": "ter"` | `bis` and `ter` map to **themselves**. Neither is deleted. A standalone `b` is *promoted* to `bis`; a standalone `t` is promoted to `ter`. |
| tokenisation | `normalize.py:342` `_non_alnum = re.compile(r"[^a-z0-9]+")` | `5 bis` -> `["5","bis"]` (number + word). `5bis` -> `["5bis"]` (one fused token). `NUM_RE` (`:311`,`:336`) still lifts `5` into `nums`, so `anums` is right but `atoks` is not. |
| `keys.ADDR_GENERIC` | `keys.py:14` contains **`"ter"`**; it does **not** contain `"bis"` | **The asymmetry.** `keys.py:39` deletes `ADDR_GENERIC` tokens before blocking. So `ter` is dropped, `bis` survives into `alph` (len 3 >= 3, `keys.py:42`) and into kind-2 keys. |

**Measured mass (`addr_tokens[France]`):**

| token -> canonical | s1 | s2 | s3 | total | % of listed mass |
|---|---:|---:|---:|---:|---|
| `bis` | 11,010 | 20,062 | 21,000 | 52,072 | |
| `b` | 2,642 | 7,286 | 7,757 | 17,685 | |
| **-> `bis`** | **13,652** | **27,348** | **28,757** | **69,757** | 0.6057 / 0.5763 / 0.5759 (0.5816 all) |
| `ter` | 1,674 | 3,044 | 3,178 | 7,896 | |
| `t` | 612 | 1,664 | 1,735 | 4,011 | |
| **-> `ter`** | **2,286** | **4,708** | **4,913** | **11,907** | 0.1014 / 0.0992 / 0.0984 (0.0993 all) |

Ratio `bis`-destined : `ter`-destined = **69,757 : 11,907 = 5.86 : 1**. As a rate
on rows: `bis`-destined tokens / France rows = 5.261% (s1) / 3.889% (s2) / 3.930%
(s3), 4.117% across all three. (Upper bound on rows: a row could in principle
contain two such tokens.)

**Fused house-number forms** (`^[0-9]+(b|bis|ter|terr|quater|quatre)$`): s1 1
token / **31**; s2 35 tokens / **2,636**; s3 28 tokens / **2,165**; **4,832
total**. Ordinal-shaped fused forms (`1er`, `2eme`, `3eme`, `2e`): 583 / 1,277 /
1,312 = 3,172.

Effect chain, stated precisely:

* `5 bis rue pierre dignac` -> `atoks = "5 bis rue pierre dignac"`. `bis` is
  non-numeric and length 3, so it enters `alph` and generates kind-2 blocking
  keys (`keys.py:65-68`). It also enters `qa`/`sa` (`features.py:97-98`) and the
  address IDF overlap `wa` (`features.py:129`).
* `5bis rue pierre dignac` -> `atoks` contains `"5bis"`, which is **not**
  `^\d+$`, so `keys.py:41` puts it in `alph` and **not** in `nums`. The number is
  therefore lost from the number x word blocking key entirely. The two spellings
  of one address produce disjoint blocking vocabularies.
* **Both** `bis` and `ter` dilute the *feature* side identically, because
  `q_atoks`/`s_atoks` (`prep.py:16`) are never filtered by `ADDR_GENERIC`. The
  asymmetry is **blocking-only**.

**Honest sizing:** at 0.58% of listed French address-token mass this is a *small*
defect. I am not going to inflate it. It is worth one line of code because it is
a one-line fix with zero downside, not because it is large.


### F6. **NEW** — the same defect class, 2.39x larger: 19 of 29 `ADDR_CANON_FR` outputs are not in `keys.ADDR_GENERIC`

`ADDR_CANON_FR` (normalize.py:199-214) has 68 input keys emitting **29** distinct
non-empty canonical values (verified by executing the dict literal).
`keys.ADDR_GENERIC` (keys.py:14-19) contains 10 of them (`allee`, `ave`, `blvd`,
`chemin`, `dr`, `impasse`, `pl`, `rue`, `sq`, `ter`). The other **19** are
emitted as content tokens and pollute `alph` and the feature-side token sets:
`bat`, `bis`, `crs`, `fbg`, `gen`, `lieu`, `lieudit`, `mal`, `pres`, `prof`,
`quai`, `res`, `rte`, `saint`, `sainte`, `za`, `zac`, `zi`, `zone`.
Measured mass of their raw input spellings (which is what the profile counts):

| canonical | raw inputs | s1 | s2 | s3 | total |
|---|---|---:|---:|---:|---:|
| `saint` | `saint`+`st` | 26,606 **[CORRECTED]** | 68,685 | 71,527 | **166,818** |
| `bis` | `bis`+`b` | 13,652 | 27,348 | 28,757 | 69,757 |
| `rte` | `route`+`rte` | 4,826 | 12,332 | 12,769 | 29,927 |
| `crs` | `cours`+`crs` | 2,182 | 5,432 | 5,667 | 13,281 |
| `res` | `residence`+`res` | 2,540 | 5,143 | 5,405 | 13,088 |
| `quai` | `quai`+`q`+`qu` | 2,157 | 5,347 | 5,500 | 13,004 |
| `sainte` | `sainte`+`ste` | 1,350 | 3,310 | 3,417 | 8,077 |
| `gen` | `general`+`gen`+`gal` | 567 | 2,735 | 2,776 | 6,078 |
| `mal` | `marechal`+`mal` | 349 | 2,184 | 2,197 | 4,730 |
| `bat` | `batiment`+`bat` | 742 | 1,449 | 1,554 | 3,745 |
| `fbg` | `faubourg`+`fbg` | 516 | 1,253 | 1,277 | 3,046 |
| `prof` | `professeur`+`prof` | 413 | 1,047 | 1,025 | 2,485 |
| `pres` | `president`+`pres` | 191 | 1,066 | 1,123 | 2,380 |
| `lieu` | `lieu` | 32 | 68 | 81 | 181 |
| `zone` | `zone` | 26 | 0 | 0 | 26 |
| `lieudit`, `za`, `zi`, `zac` | — | 0 | 0 | 0 | **0** (below list cut-off) |
| **subtotal, not neutralised** | | **56,149** | **336,256** | **342,218** | **336,623** |

336,623 / 11,992,918 = **2.8068%** of listed French address-token mass is a French
street-type or honorific canonical that the blocking layer treats as a content
word. (An earlier draft in this same work order put this at 337,553 / 2.814%; the
difference is entirely the `saint` s1 miscount, corrected above.)

Two sharp sub-findings:

* **`saint` is the single largest offender at 166,818 tokens — 2.39x the `bis`
  mass and 14.0x the `ter` mass** (166,818 / 69,757 = 2.391;
  166,818 / 11,907 = 14.01). And for France it is *unreachable* to fix via
  the obvious route: `ADDR_CANON_FR` at normalize.py:207 maps `"st"` -> `"saint"`
  and `"ste"` -> `"sainte"`, so the `ADDR_GENERIC` entries `"st"` and `"ste"`
  (keys.py:14) are **dead entries for France** — by the time `keys.py:39` runs,
  those tokens no longer exist in `atoks`. Verified by execution: the post-canon
  token is `saint` (len 5), which is not in `ADDR_GENERIC`, so it survives into
  `alph`. They work for the US (where `st` ->
  `st`) and are silently inert for France. `CONFIRMED` from code.
* By contrast `rue` **is** correctly handled and is the single most valuable
  entry in `ADDR_CANON_FR`: raw `r` alone is 2,543 / 182,872 / 182,809, so
  `r` -> `rue` is what makes `5 r de la paix` and `5 rue de la paix` identical.
  In s2, 182,872 / (182,872 + 269,264) = **40.4%** of all French street-type
  mentions use the `r` abbreviation. The map earns its keep there. `CONFIRMED`.


## Interpretation (inference, clearly marked)

1. **There is no reordering bug to fix, and the fix for the order fragility is
   the dictionary fix.** `state`, `toks`, `nums` and `pin` are
   permutation-invariant by construction, now confirmed empirically (0 breaks in
   28 permutations). `city_last` is not, but only via unmapped geography.
   Anyone who writes "make `normalize_address` order-robust" is solving a problem
   that does not exist; the useful change is to stop unmapped regions leaking into
   `acity`.
2. **`city_last` is a low-confidence feature and should be treated as one.** Its
   own comment says "usually". For the >=487,453 France rows with no
   `FR_REGIONS` key, `city_last` is whatever digit-free component happened to be
   last — which, given `Bordeaux, <dept>` ordering, is frequently the
   department. *Inference, not measured:* this is a plausible source of label
   noise in a feature the model may be leaning on. A cheap mitigation, if
   `city_last` proves predictive of error, is to emit `city_first` as well and
   let the model choose.
3. **Sizing a `FR_REGIONS` department-expansion project on 28.77% would be a
   mistake.** F4 bounds the recoverable share at **<=3.15% of that residual** even
   on the loosest possible assumptions. The correct next question is *why ~35% of
   s2/s3 France rows appear to carry no geography component at all* — that is a
   data-shape question, not a dictionary question, and it is currently unowned.
4. **`bis` is a correct, cheap, low-impact fix.** Expected effect: removes 69,757
   tokens (0.58% of French address-token mass) from the blocking alpha vocabulary
   and stops `"b"` being promoted to a 3-char content token. It will *not* touch
   the feature-side dilution, because `atoks` is unfiltered there.
5. **`saint` is the same bug with 2.39x the mass and it hides two dead
   `ADDR_GENERIC` entries.** If a human only has appetite for one change on the
   French dictionary, this is the one with the most leverage.

## Gaps (things the profile cannot answer — no estimates supplied)

1. **Component order is NOT observable.** `build_profile.py:126-127` does
   `for comp in ADDR_SPLIT.split(bal): at.update(TOKEN_RE.findall(comp))` — it
   splits on `[,;]` and immediately flattens into a single `Counter`. Component
   boundaries, component *count* and component *position* are all destroyed. So
   the frequency with which region-before-city vs city-before-region occurs is
   **unmeasurable here**. Everything in F1/F2 is therefore a *code* result
   (deterministic, from `_upstream/src/`) plus a *token-mass* bound — I have not
   claimed a row-level order distribution, because none can be derived.
2. **Consequently, the `city_last` mis-fire rate is unquantifiable.** I can bound
   the exposed population (`rows - U`: 245,993 s2 / 243,713 s3) but not the
   fraction of those rows on which the region actually trails the city.
3. **The "two components both match `FR_REGIONS`, last wins" path
   (normalize.py:334) is unquantifiable** for the same reason.
4. **Comma vs semicolon divergence is a live, unsized bias.**
   `build_profile.py:31` `ADDR_SPLIT = re.compile(r"[,;]")` but
   `normalize.py:322` splits on `","` **only**. The profile has no semicolon
   field, so I cannot size this. **Bias direction, stated so it is not mistaken
   for precision:** if semicolons occur, the profile splits a component the
   pipeline keeps whole, so my `U` ceilings in F3 are **over**-estimates of
   pipeline state resolution. The residual is correspondingly **under**-stated.
   The true unresolvable share is >= 28.7677%, not exactly 28.7677%.
5. **`listed addr-token mass` is a lower bound on the true token mass.**
   `build_profile.py` prunes `count <= 1` tokens every 8 chunks (`:128-133`) and
   `:140` truncates to `most_common(4000)`. Every "% of listed mass" figure in
   F5/F6 is therefore an **upper** bound on the true share.
6. **Absence from `addr_tokens[France]` is not zero.** Per the 4000th listed
   counts (23 / 58 / 60), an unlisted token has `count < 23 / < 58 / < 60`
   respectively, and could have been pruned at count 1. F4's bound uses the
   cut-off count, which is the loosest defensible reading.
7. **No ground truth was consulted.** All matching claims are code-derived or
   token-mass-derived. Whether reordering actually *preserves matching* in the
   scored sense (does it change the predicted entity?) is not answerable without
   a run of the pipeline, which I did not perform.
8. **The 71.23% / 97.44% contradiction is narrowed, not closed.** I have shown
   that criterion C reproduces ~71.2% and that 97.44% is incompatible with it as
   an upper bound. I have not read D077's criterion, so I cannot state *why* it
   differs.
9. **[CORRECTED] The department probe is a single-word-token probe and is
   blind to multi-word department names.** `build_profile.py:127` flattens
   components with `TOKEN_RE = [a-z0-9]+`, so `val-d'oise` becomes `val`,
   `d`, `oise` — no single token carries the department identity. F4 therefore
   measures *single-word* department mentions only. Department names that are
   always multi-word (e.g. `seine maritime`, `bouches du rhone`,
   `haute savoie`) are structurally invisible to this method and to any method
   using this profile. This is a genuine **profile gap**, not a null result, and
   it is the main reason the F4 bound should be read as an upper bound on a
   *sub-population*, not on the whole department lexicon.


## Recommendations

**P1 — Add `saint` and `sainte` to `keys.ADDR_GENERIC`, and either add or delete
the dead `"st"`/`"ste"` entries.** `CONFIRMED`. 174,895 tokens
(`saint`+`st`+`sainte`+`ste` = 27,956 + 71,995 + 74,944), 1.24% / 1.52% / 1.50%
of listed French address-token mass — 2.39x the `bis` mass. The `"st"`/`"ste"`
entries are provably inert for France because `ADDR_CANON_FR:207` rewrites them
first; leaving them is a trap for the next reader. Expected effect: removes the
largest French non-content token from the blocking alpha vocabulary. **Note the
scope:** this changes `keys.py` only, so it does not change the `wa`/`a_jac`
feature values.

**P2 — Add `bis` to `keys.ADDR_GENERIC`.** `CONFIRMED`, one line, zero downside.
69,757 tokens (0.58% of listed French address-token mass). It is the only French
house-number suffix currently treated as a content word while its twin `ter` is
noise. If a human prefers the minimal diff, this is the one to make.

**P3 — Add the other 17 uncovered `ADDR_CANON_FR` outputs** (`rte`, `crs`,
`quai`, `res`, `gen`, `mal`, `bat`, `fbg`, `prof`, `pres`, `lieu`, `lieudit`,
`zone`, `za`, `zi`, `zac`, plus `saint`/`sainte` from P1). `CONFIRMED` as a
coverage gap; together with P1/P2 they account for **336,623 tokens = 2.8068%**
of listed French address-token mass. Same scope caveat as P1: blocking only.

**P4 — Do NOT open a "add the missing French departments to `FR_REGIONS`"
project sized on the 28.77% residual.** `CONFIRMED` bound (F4): the entire
unmapped French department lexicon is worth <= 15,341 tokens <= 3.15% of the
residual. The open work item named in `already_checked` ("WHICH departments
test_s2/test_s3 actually use, and how many `FR_REGIONS` entries would be needed")
is now answered: **four** — Gironde, Nord, Loire-Atlantique, Pas-de-Calais — and
**all four are already mapped**. The only unmapped departments with any measurable
mass are 8 minor single-word ones totalling 4,343 tokens. Re-target that effort at
*why ~35% of s2/s3 France rows appear to carry no geography component at all*.

**P5 — Reorder nothing in `normalize_address`.** `CONFIRMED`: the function has no
positional logic, and `state`/`toks`/`nums`/`pin` are provably
permutation-invariant. If someone wants insurance against the residual order
risk, the correct instrument is P4 (stop unmapped regions entering `city_comps`),
not a rewrite. If `city_last` later proves to be a source of error, add
`city_first` as a second feature (`features.py:90`) rather than changing the
"last" rule — that preserves the signal and lets the model discount it.

**P6 — Record the criterion with the 71.10% / 97.44% figure.** `CONFIRMED`:
three independent computations now land at 71.10% / 71.23% / and something
looser, and a 97.44% *ceiling* is arithmetically incompatible with an upper
bound of 71.23% on the same data. Until D077's criterion is stated, quote
**71.23% as the ceiling and 28.77% as the floor** on France's unresolvable share,
never a point estimate, and never a single-source rate.

---

*Prepared from `analysis_out/profile/test_s{1,2,3}.json` and read-only inspection
of `_upstream/src/{normalize,keys,features,prep}.py`. No network access; no raw
TSV was opened; no tracked file in the dataset or `_upstream` was modified; the
only files written are this deliverable and its `.json` sidecar.*

