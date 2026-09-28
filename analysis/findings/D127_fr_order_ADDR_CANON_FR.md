# D127 — France: component-order robustness for ADDR_CANON_FR

## Headline

**Component order is NOT a defect: `normalize_address` is provably order-independent for state resolution, confirmed by executing the real `normalize.py`.** The work order's main premise is refuted. The genuine France-specific risk is elsewhere and worse: **`bis` and `ter` are handled asymmetrically, in the direction that keeps the noise.** `ter` is silently deleted by `ADDR_GENERIC` while `bis` survives into blocking keys and the IDF table — a 5.86x asymmetry (`bis` 69,757 vs `ter` 11,907 occurrences across the three test files). Separately, **4,832 French address tokens are *fused* number+suffix forms (`5bis`, `12b`, `13bis`) the address path never splits**, and for those the house number is dropped from the blocking keys entirely.

## Findings

### 1. Component order does not affect state resolution — REFUTES the work-order premise

`normalize.py:322` splits on `,` into `comps`; `:328-335` loops over **every** component testing `if ck in smap`, with **no positional index anywhere** — no `comps[0]`, no `comps[-1]`, no "assume the last field is the region".

Executed against the real, unmodified module (`polars` stubbed; `_upstream` read-only):

| Input | `state` | `city_comps` |
|---|---|---|
| `Bordeaux, Nouvelle-Aquitaine` | `naq` | `['bordeaux']` |
| `Nouvelle-Aquitaine, Bordeaux` | `naq` | `['bordeaux']` |
| `Lille, Hauts-de-France` | `hdf` | `['lille']` |
| `Hauts-de-France, Lille` | `hdf` | `['lille']` |
| `La Teste-de-Buch, Nouvelle-Aquitaine` | `naq` | `['la teste de buch']` |

**Reordering preserves matching.** Both orderings of the work order's own examples resolve to `naq`. The whole-component match at `:333` is inherently order-free: it asks "does this component *equal* a region name", never "is the region in position N".

Corroborating profile evidence that order is genuinely mixed (field `addr_tokens["France"]`):

| token | s1 | s2 | s3 |
|---|---|---|---|
| `hauts` | 101,717 | 88,519 | 99,419 |
| `france` | 102,319 | 89,929 | 100,902 |
| `nouvelle` | 85,311 | 74,392 | 83,099 |
| `aquitaine` | 85,268 | 74,276 | 82,987 |
| `pays` | 72,812 | 63,086 | 71,498 |

### 2. The one genuine order sensitivity: `city_last` — a pre-existing, non-France issue

`normalize.py:351-352` appends to `city_comps` in encounter order and `features.py:90` takes `x.split("|")[-1]` — the **last** component. With ≥2 digit-free non-region components the feature *is* order-dependent:

| Input | `city_comps` | `city_last` |
|---|---|---|
| `Bordeaux, La Teste-de-Buch` | `['bordeaux', 'la teste de buch']` | `'la teste de buch'` |
| `La Teste-de-Buch, Bordeaux` | `['la teste de buch', 'bordeaux']` | `'bordeaux'` |
| `Bordeaux, Rhone, 12 Rue X` | `['bordeaux', 'rhone']` | `'rhone'` |
| `Rhone, Bordeaux, 12 Rue X` | `['rhone', 'bordeaux']` | `'bordeaux'` |

The single-component case is safe: a *recognised* region is `continue`d at `:335` and never enters `city_comps`, so the usual 2-component French address has one city component and `city_last` is stable. This is **inference** from code, not a measured rate.

### 3. `bis` vs `ter`: real, confirmed, asymmetric

`ADDR_CANON_FR` (`normalize.py:211`) maps both: `"bis"→"bis"`, `"b"→"bis"`, `"ter"→"ter"`, `"t"→"ter"`. But `keys.py:14-19` `ADDR_GENERIC` contains `"ter"` (inherited from the US *terrace* sense, `normalize.py:166`) and **not** `"bis"`. Executed, real code:

```
bis -> canon 'bis'  in_ADDR_GENERIC=False -> survives into keys.py alph: True
b   -> canon 'bis'  in_ADDR_GENERIC=False -> survives (as 'bis'): True
ter -> canon 'ter'  in_ADDR_GENERIC=True  -> survives into keys.py alph: False
t   -> canon 'ter'  in_ADDR_GENERIC=True  -> survives (as 'ter'): False
```

Two semantically identical French suffixes get **opposite** treatment.

Measured exposure (`addr_tokens["France"]`, 3 test files):

| token | s1 | s2 | s3 | total | per 1,000 France rows |
|---|---|---|---|---|---|
| `bis` | 11,010 | 20,062 | 21,000 | **52,072** | |
| `b` | 2,642 | 7,286 | 7,757 | **17,685** | |
| **bis-family** | | | | **69,757** | **41.17** |
| `ter` | 1,674 | 3,044 | 3,178 | **7,896** | |
| `t` | 612 | 1,664 | 1,735 | **4,011** | |
| **ter-family** | | | | **11,907** | **7.03** |

Arithmetic: bis-family 52,072+17,685 = 69,757; ter-family 7,896+4,011 = 11,907; ratio **5.86x**. France test rows = 1,694,445, so 69,757/1,694,445 = 41.17 per 1,000. Listed France address-token mass (3 files) = 2,253,877+4,745,780+4,993,261 = 11,992,918, so `bis`-family is **0.58%** of French address token mass, `ter`-family **0.10%**.

**Consequence (inference):** ~0.58% of every French address token stream is a suffix carrying no location information, yet it gets a full IDF entry and can generate kind-2 address blocking keys (`keys.py:63-69`). Attached to a house number it also creates a spurious number×word pair.


### 4. Fused number+suffix tokens: the house number is LOST

`normalize.py:342` splits on `_non_alnum = [^a-z0-9]+` (`:269`). Digits and letters are both alphanumeric, so **`5bis` is never split**. Confirmed by execution:

```
5 bis Rue Pierre Dignac  toks=['5', 'bis', 'rue', 'pierre', 'dignac']  nums=['5']
5bis Rue Pierre Dignac   toks=['5bis', 'rue', 'pierre', 'dignac']      nums=['5']
12b Rue Victor Hugo      toks=['12b', 'rue', 'victor', 'hugo']         nums=['12']
```

`ADDR_CANON_FR.get("5bis")` is `None`. The damage: `keys.py:41` derives the blocking `nums` list **from the token string** by `^\d+$`, *not* from `normalize_address`'s `nums` field:

```
5 bis Rue Pierre Dignac   normalize_address.nums=['5']  keys.py-derived nums=['5']  number_lost=False
5bis Rue Pierre Dignac    normalize_address.nums=['5']  keys.py-derived nums=[]     number_lost=True
```

For the fused form the house number reaches the *features* (`features.py:99` `qm1`/`sm1` read `anums`) but is **absent from the blocking keys** (`keys.py:41-43`). Number and blocking signal disagree.

Measured, France address tokens, 3 test files — 46 distinct fused digit+letter tokens, **13,580 occurrences**:

| class | s1 | s2 | s3 | total |
|---|---|---|---|---|
| all fused digit+letter | 1,610 | 6,122 | 5,848 | **13,580** |
| of which `Nbis`/`Nb` | 31 | 2,636 | 2,165 | **4,832** |
| of which len≥3 → becomes an `alph` token | 1,554 | 5,274 | 4,998 | **11,826** |

Largest offenders: `cour2` (657/1,563/1,652), `chem1` (207/443/452), `1er` (343/795/825), `2eme`, `3eme`, `espl1`, `chau1`. The 4,832 `Nbis`/`Nb` forms are **0.29% of France test rows** but are the sharpest case, because a real house number is destroyed. The fused share is heavily s2/s3-weighted: fused/(fused+split `bis`) = **3.55% in s1 vs 14.84% in s2 and 12.71% in s3**.

### 5. LEET does not reach addresses

`LEET` (`normalize.py:256`) is referenced **only** at `:280` inside `_name_tokens`, the **name** path; it never appears in the `normalize_address` body (`:314-353`). Verified: `_name_tokens("5bis")` → `['sbis']` (digit 5 → `s`) while `normalize_address("5bis rue x","France")` → `['5bis','rue','x']`. The `bis` question is **not** a LEET issue — and the name path would actively *corrupt* `5bis` → `sbis`.

### 6. Reproduced the open geography contradiction — and sharpened it

The unresolved 71.10% (D073) vs 97.44% (D077) dispute. I recomputed the union bound independently (rows containing key K ≤ min over K's tokens of that token's occurrence) and got **exactly** the D073 figure:

| source | France rows | sum of per-key bounds | union upper bound | % |
|---|---|---|---|---|
| s1 | 259,452 | 261,705 | 259,452 (capped) | **100.00%** |
| s2 | 703,378 | 457,385 | 457,385 | **65.03%** |
| s3 | 731,615 | 487,902 | 487,902 | **66.69%** |
| **all** | **1,694,445** | | **1,204,739** | **71.10%** |

**Because this is an upper bound, D077's 97.44% is not merely a different criterion — it exceeds a rigorous ceiling.** No resolution criterion over these 14 keys can resolve more than 1,204,739 of 1,694,445 French rows. I hold **D077's 97.44% refuted** and D073's 71.10% the correct *upper bound* (truth is ≤71.10%).

Also a **correction to the work order's premise**: it says s2/s3 "encode geography with DEPARTMENT names". Only half true — s2/s3 contain **both**. `hauts`=88,519 and `nouvelle`/`aquitaine`≈74,3xx are region names at s1-scale volume *alongside* `nord`=75,362 and `gironde`=75,104. And `loire` decomposes: s2 `loire`=126,216 vs `pays`=63,086, so ~50.5% of s2 `loire` comes from `Loire-Atlantique`, not `Pays de la Loire`. Likewise `calais`=55,273 vs `pas`=14,325 in s2 — most `calais` is the **city** Calais, not `Pas-de-Calais`. Any fix must be per-source.

### 7. Arithmetic invariants (both hold exactly)

- `sum(len_hist.values()) == rows` for France in s1/s2/s3 — all `True`.
- `sum(country_rows.values()) == rows` for s1/s2/s3 — `1,732,544 / 4,887,273 / 5,082,316`, all `True`.


## Interpretation *(inference)*

1. **The order question is closed, and closed positively.** The pipeline was written order-agnostically on purpose. Any proposal to "fix" component order would solve a non-problem and risks *introducing* order-sensitivity into a currently order-free state path. The one real order dependence (`city_last`, `features.py:90`) is a last-wins convention predating France and affecting all countries equally; it is *exposed* by France's multi-word city names (`La Teste-de-Buch`), not caused by them.
2. **The real France risk is suffix handling, asymmetric in the wrong direction.** `ter` is silently dropped, `bis` silently promoted. Both are noise; neither should reach the IDF table. `CONFIRMED`: profile counts and executed code agree.
3. **The fused form is the more serious of the two**, because it does not merely add noise — it *removes signal*. A `5bis` address keeps its number for features but loses it for blocking, so two representations of the same business disagree about what they are keyed on. `CONFIRMED`, and concentrated in s2/s3, i.e. the sources the competition scores.
4. The France region gap is real and s2/s3-weighted; D073's 71.10% should be treated as a ceiling.

## Gaps

- **Component order, count and boundaries are NOT recoverable from the profile.** `build_profile.py:126-127` does `for comp in ADDR_SPLIT.split(bal): at.update(TOKEN_RE.findall(comp))` — components are split, then their tokens **merged into one flat `Counter`**. Order is destroyed at source. Every order statement in §1-2 is therefore from **executing the code**, not from measured row data. I could not measure "what % of French rows put region first". **Hard gap** — not resolvable without re-running the builder with a positional field.
- `num_components` per row was never collected, so I cannot size how many French rows have ≥2 digit-free non-region components (the population exposed to `city_last` order-sensitivity). **Gap.**
- `ADDR_GENERIC` document frequencies are not in the profile, so I cannot compute the *IDF value* of `bis` or its key-collision rate. Occurrence counts only. **Gap.**
- Whether fused `5bis` and split `5 bis` ever co-occur for the *same* entity (i.e. whether this actually causes a missed match, as opposed to two independent spellings) is **not determinable** from unigram profiles. **Gap — the single most valuable follow-up.**
- Semicolons: `build_profile.py:31` splits on `[,;]` but `normalize.py:322` splits on `,` only. If semicolons occur in French addresses, profile and pipeline disagree about components. I could not detect semicolon frequency from the profile. **Gap, flagged as a possible profile/pipeline divergence.**

## Recommendations

1. **Add `"bis"` to `ADDR_GENERIC` in `keys.py:14-19`**, keeping `ter` there. *Rationale:* both are French house-number suffixes with zero location information; `ter` is already present via the US *terrace* sense, so this makes treatment symmetric rather than merely reversing the asymmetry. *Expected effect:* removes ~0.58% of French address token mass from the IDF table and from kind-2 blocking keys. `CONFIRMED`. Low risk, one line.
2. **Split fused digit+suffix tokens in `normalize_address` before the canon lookup** (e.g. `re.sub(r"(?<=\d)(?=[a-z])", " ", ...)` at `:342`). *Rationale:* 13,580 French tokens, of which 4,832 are the `Nbis`/`Nb` form, currently yield a blocking key set that disagrees with the feature set. *Expected effect:* restores the house number to `keys.py:41` and converts 11,826 junk `alph` tokens into real numbers. `CONFIRMED`. Medium risk — key counts change, so re-tune `CAPS` (`keys.py:23`) and re-measure blocking recall.
3. **Do NOT change the component loop at `normalize.py:328-353`.** It is correct and order-free. Recommend against "fixing" order.
4. **Treat D073's 71.10% as a ceiling; close the D077 dispute as resolved against 97.44%.** If the s2/s3 gap is fixed, build a per-source gazetteer: the target set is *not* "add the missing departments", because s2/s3 mix region and department names and `Loire-Atlantique`/`Pas-de-Calais` are already keyed.
5. **Re-run the profile builder with a positional field** (e.g. a `comp_index` histogram per country, or ordered first/last-component token pairs) so order questions stop being unanswerable. Cheap, and unblocks a whole class of work orders.

## Provenance

Fields used: `split, source, rows, country_rows, by_country[France].{rows,name_tokens,num_digits,has_digit_name,has_comma,prefix_bad,dig5,dig6,alpha_only_addr,len_hist}`, `addr_tokens["France"]`, `name_tokens["France"]`.

Code read (read-only): `_upstream/src/normalize.py` (199-214, 243-256, 264-353), `_upstream/src/keys.py` (14-19, 31-46), `_upstream/src/features.py` (9-10, 87-99), `build_profile.py` (28-32, 110-127).

Semantics confirmed against `build_profile.py`: `num_digits` sums digits over the **whole address**; `dig5`/`dig6` are lookaround-guarded standalone runs; `len_hist` is name-length bucketed by tens; `addr_tokens` merges all components into one flat counter.

No network access. Dataset and `_upstream` untouched. Temp scripts removed; only this file and its `.json` sidecar were written.

France totals across 3 test files: rows 1,694,445; `num_digits` 3,286,447 (1.93954/row); `dig5` 8,604; `dig6` 279; `alpha_only_addr` 54,602; `has_digit_name` 17,914; `addr_empty` 43,078.
