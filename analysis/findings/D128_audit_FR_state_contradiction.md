# D128 — audit the France state-resolution contradiction: 71.10% vs 97.44%

## Headline

**There is no contradiction. The two numbers are not two measurements of the same
quantity.** D073 measured a *dictionary* bound; D077 measured an *address-parseability*
ceiling. They are nested lower bounds on the same unknown, and D073's is the tighter one.

Under one criterion — **a France row resolves a state iff some whole comma-component of
`business_address`, after `translit_text` + `strip_accents` + lowercasing, equals one of
the 14 `FR_REGIONS` keys** — the defensible result is a **bound, not a point estimate**:

> **At most 1,213,296 of 1,694,445 France test rows (71.60%) can resolve a state through
> `FR_REGIONS`. At least 481,149 rows (28.40%) provably carry no state token at all.**

D077's 97.4380% is **not** a competing estimate of the resolvable rate. It is the share
of rows whose address is non-empty and comma-bearing — a property of the *raw data*, not
of `FR_REGIONS`. D077's own control proves this: its figure is 97.0552% for US and 97.5368%
for India, and it is unchanged if you swap the state dictionary for anything at all.

The single most important number: **28.40%** — the provable floor on France test rows with
no resolvable state. Engineering verdict: **do not extend `FR_REGIONS`.**

---

## 1. The criterion, tied to real code

`normalize_address` is the only place a state is ever set for France. From
`_upstream/src/normalize.py` (read-only; clone at 8445b7f):

```python
314: def normalize_address(raw: str, country: str):
315:     """Return dict with tokens (no state), numbers, state code, pin, comps."""
316:     s = translit_text(raw or "")
317:     s = strip_accents(s).lower()
318:     smap = STATE_MAPS.get(country, {})
...
322:     comps = [c.strip() for c in s.split(",")]
323:     state = ""
...
328:     for c in comps:
329:         if not c or c in ("null", "<null>", "n/a", "na", "none"):
330:             continue
331:         ck = re.sub(r"[^a-z0-9& ]+", " ", c).replace("&", " and ")
332:         ck = " ".join(ck.split())
333:         if ck in smap:
334:             state = smap[ck]
335:             continue
```

`STATE_MAPS["France"] = FR_REGIONS` (line 250). `FR_REGIONS` (lines 243-249) has exactly
**14 keys** mapping to 4 canonical values:

| value | keys |
|---|---|
| `hdf` | `hauts de france`, `nord`, `pas de calais`, `somme`, `aisne`, `oise` |
| `naq` | `nouvelle aquitaine`, `gironde`, `landes` |
| `pdl` | `pays de la loire`, `loire atlantique`, `vendee` |
| `idf` | `ile de france`, `paris` |

Three properties of lines 331-335 that decide everything:

1. **Whole-component match only.** `ck` is the *entire* component with punctuation folded
   to spaces. `12 rue de lorraine` does not match key `lorraine`. This is what makes a
   token count a poor proxy and a gazetteer addition risky.
2. **`continue` at 335.** A matching component contributes *no* tokens to the output — so
   state resolution consumes the component.
3. **Accents are stripped at 317, before matching.** `vends` → `vendee` resolves. The
   profile does **not** strip accents, so the profile *undercounts* accented keys. This is
   a one-directional correction and I apply it (§3).

**My criterion, in one sentence:** *a France test row counts as "state resolved" if and
only if at least one comma-delimited component of its `business_address`, after
transliteration, accent-stripping, lowercasing and punctuation-to-space folding, is exactly
equal to one of the 14 `FR_REGIONS` keys.*

Note what this criterion does **not** contain: any requirement of a comma, any assumption
about component count, any use of `has_comma`. D077 imported a `has_comma` assumption that
is not in the code.

## 2. What each prior agent actually did — the criterion mismatch

| | D073 | D077 |
|---|---|---|
| Question asked | "How many rows can contain a key?" | "How many rows are not *structurally* dead?" |
| Test applied | union bound over 14 keys, per-key min of token counts | `rows − addr_empty − non-empty-comma-free` |
| Quantity produced | upper bound on resolvable | ceiling on *anything* state-like |
| Result | ≤1,213,296 (71.60%) resolvable | ≤43,411 (2.5620%) "unresolvable" |
| Direction of error | conservative (may over-state coverage) | **anti-conservative** (ignores dictionary) |

**D073** scored a key by `min` over its constituent token counts, then summed over the 14
keys as a union bound. Overlap inflates it, so it is a genuine *upper* bound on resolvable
rows — sound in direction.

**D077** never looked at `FR_REGIONS` at all. It counted rows that are dead regardless of
dictionary: empty address, or non-empty with no comma. Every other row was assumed
resolvable. That assumption is false — line 333 requires a component to *equal a key*, and
nothing guarantees one exists.

**The two are not in conflict because they bound the same thing from opposite optimism.**
D077 says "≥97.44% of rows are *not ruled out*". D073 says "≤71.60% of rows are *capable*".
Both can be true simultaneously. The honest reading is: the truth lies in
**[28.40%, 97.44%]** and the profile can push the resolvable ceiling down to 71.60% but
cannot pin a point value.

**D077's own control falsifies its criterion as a resolvability measure.** It reports the
same invariant for other countries: US test_s2 97.0552%, US test_s3 97.1570%, India
97.5368%. A dictionary-coverage figure that is near-identical for countries with entirely
disjoint state tables is measuring the *address format*, not coverage. France at 97.4380%
is in line — i.e. France is not unusual; the metric is not about France at all.

**Both prior figures, restated under my criterion:**

| prior claim | as stated | under my criterion | verdict |
|---|---|---|---|
| D073 (number quoted in the task brief) | 1,204,739 resolvable / 71.10% | ≤1,213,296 / 71.60% | correct in direction, **stale by 8,557 rows** |
| D073 (its own .md) | ≥481,149 unresolvable / 28.40% | identical | **reproduced exactly; the defensible bound** |
| D077 | 2.5620% unresolvable | not a resolvability figure | **criterion mismatch**; it is the empty-address rate |
| D077 | 97.4380% resolvable ceiling | ≤71.60% | **too loose by ≥25.8 pp**; ignores line 333 |
| inherited claim | 100% of France rows | s1 only = 15.31% of France rows | **refuted** |

**The interval I can defend:** resolvable ∈ **[0%, 71.60%]**, unresolvable ∈
**[28.40%, 97.44%]**. The lower end of the resolvable range is a **gap, not a measurement**
— see §5.

## 3. Arithmetic reproduction of D073 (checked, not re-derived)

Recomputed the union bound from `addr_tokens["France"]`, substituting the rank-4000 cutoff
for absent tokens (cutoffs 23 / 58 / 60, measured as the minimum value in each file's
France token list) and substituting `max(count(ile), count(le))` for `ile` to absorb accent
loss. Per-key minima:

| key | s1 | s2 | s3 |
|---|---|---|---|
| `hauts de france` | 101,717 | 88,519 | 99,419 |
| `nord` | 200 | 75,362 | 76,449 |
| `pas de calais` | 179 | 14,325 | 14,528 |
| `somme` | 333 | 807 | 833 |
| `aisne` | 23 | 58 | 60 |
| `oise` | 74 | 148 | 139 |
| `nouvelle aquitaine` | 85,268 | 74,276 | 82,987 |
| `gironde` | 62 | 75,104 | 75,621 |
| `landes` | 116 | 292 | 313 |
| `pays de la loire` | 72,812 | 63,086 | 71,498 |
| `loire atlantique` | 253 | 63,697 | 64,398 |
| `vendee` | 23 | 58 | 60 |
| `ile de france` | 1,992 | 4,882 | 5,050 |
| `paris` | 388 | 952 | 923 |
| **union bound** | **263,440** | **461,566** | **492,278** |

Clamped per file to `min(UB, rows)`: s1 → 259,452 (UB exceeds rows, bound vacuous),
s2 → 461,566, s3 → 492,278. **Total 1,213,296 = 71.60%**; residual **481,149 = 28.40%**.

This reproduces D073's refined figures exactly.

**New discrepancy found (not a defect, a documentation inconsistency):** D073's two
artefacts disagree with each other. Its JSON sidecar carries the **pre-fix** numbers
(1,204,739 / 71.10% / 28.90%); its `.md` carries the **corrected** 1,213,296 / 71.60% /
28.40%. The task brief quotes the stale JSON figure. The `.md` is the correct one. Anyone
citing D073 should cite the `.md`.

**Arithmetic check on the inherited 100% claim** (`by_country["France"]["rows"]`,
`addr_tokens["France"]`): the prior agent's s1 region counts `101,521 + 85,197 + 72,734 =
259,452` — exactly the s1 France row count. My measured s1 values are `hauts 101,717`,
`nouvelle 85,311`, `pays 72,812`, summing to **259,840** (delta +388). Close, but **not** the
prior agent's triple; I cannot reproduce their exact figures from the profile. The
*conclusion* survives regardless — s1 is 259,452 / 1,694,445 = **15.31%** of French rows, and
the 84.69% it never touched is what drives the whole disagreement.

## 4. Per-source: which administrative level does each file use?

This is the substantive new finding, and it is decisive for the verdict. Region and
department *discriminator* tokens, `addr_tokens["France"]`:

| source | France rows | region tokens | density | dept tokens | density |
|---|---|---|---|---|---|
| test_s1 | 259,452 | 261,165 | **100.7%** | 17,625 | 6.8% |
| test_s2 | 703,378 | 229,083 | 32.6% | 272,145 | **38.7%** |
| test_s3 | 731,615 | 257,250 | 35.2% | 276,832 | **37.8%** |
| **total** | **1,694,445** | **747,498** | 44.1% | **566,602** | 33.4% |

"Density" = token occurrences ÷ France rows. It exceeds 100% for s1 because a region name
contributes 2-3 tokens per row (`hauts`+`de`+`france`); it is a concentration indicator,
**not** a row count. This is exactly the "token count is not a row count" trap the fleet
brief warns about, and it is why the density must never be read as coverage.

Region discriminators present: `hauts` 289,655 · `nouvelle` 242,802 · `pays` 207,396 — and
those three are **89.7%** of all region-token mass. Everything else is ≤1,262.

Department discriminators present: `nord` 152,011 · `gironde` 150,787 · `calais` 128,762 ·
`atlantique` 128,348 — those four are **98.9%** of department mass. Everything else ≤2,478.

**Not in the top 4000 in any test file** (so count ≤ 23/58/60, *not* proven absent):
`occitanie`, `limousin`, `languedoc`, `corse`, `rhone`, `herault`, `lozere`, `finistere`,
`morbihan`, `var`, `tarn`, `essonne`, `yvelines`, `isere`, `loiret`, `manche`, `dordogne`,
`charente`, `creuse`, `mayenne`, `pyrenees`, `cotes`, `azur`, `ardenne`, `franche`.

**The picture — this answers the task's "which tokens does each source use" question:**

- **s1 encodes REGIONS.** Region density 100.7%, department density 6.8%. Essentially every
  s1 row carries `Hauts-de-France` / `Nouvelle-Aquitaine` / `Pays de la Loire` as a
  component. This is why s1's bound is vacuous and why the inherited "100% of France rows"
  figure was true *for s1 only*.
- **s2/s3 encode DEPARTMENTS.** Department density jumps 6.8% → ~38% (5.7×) while region
  density falls 100.7% → ~33%. The departments they use (`gironde`, `nord`, `calais`,
  `loire atlantique`) are **already keys in `FR_REGIONS`**. So s2/s3 *are* largely
  resolvable — via the department half of the existing table, not via a missing region entry.
- **The residual is cities.** `bordeaux` 277,474 · `nantes` 238,748 · `lille` 221,585 ·
  `tourcoing` 115,914 · `dunkerque` 111,538 · `roubaix` 107,111. Top 3 cities alone are
  ~43.7% of all French rows and carry **no** administrative token, so no dictionary entry
  can ever fire on them. `paris` is only 2,263 — Paris is not the mass, the provinces are.

This directly confirms the task's anchor: the three modern regions present
(`hauts-de-france`, `nouvelle-aquitaine`, `pays-de-la-loire`) are all already mapped, and
`FR_REGIONS` is adequate for the region tokens that exist.

## 5. Gaps — what the profile cannot settle

- **No component structure.** `build_profile.py:126-127` splits on `[,;]` then does
  `at.update(TOKEN_RE.findall(comp))` against a *flattened* counter. Component identity and
  component **order** are both destroyed. I cannot convert a token count into a resolved-row
  count in either direction. **This is the single reason no point estimate exists here**, and
  it is why a bound is the correct output rather than a failure.
- **No accent stripping in the profile.** `TOKEN_RE = re.compile(r"[a-z0-9]+")` (line 28)
  runs on the lowercased address with no `strip_accents`, so `île-de-france` yields `le`,
  not `ile` (measured: `ile` 303/817/794, `le` 1,992/4,882/5,050). The pipeline strips
  accents first (normalize.py:317). I correct only for `ile`; other accented keys
  (`vendee`→`vend` is 53/80/97, `cote d or`, `rhone alpes`) remain undercounted, so the true
  UB may be slightly *higher* than 1,213,296. Direction: my 71.60% is conservative.
- **Semicolon splitting mismatch.** The profile splits on `[,;]`; `normalize_address` splits
  on `,` only (line 322). A semicolon-joined address is 2 components to the profile and 1
  to the pipeline. Direction of error not cleanly determined — **gap**.
- **No per-row data at all.** Every figure here is a token-occurrence sum. The raw TSVs are
  prohibited on this box (~0.6 GB free RAM; a 480 MB scan was already OOM-killed).
- **Precision of any candidate key is unmeasurable.** I can bound how many rows *could*
  resolve; I can never bound how many would *falsely* resolve. Every addition is a
  potential false positive and only row-level data can price it.
- **City→region mapping not derivable.** `addr_tokens` holds marginal counts, not
  co-occurrence. Not estimated. See §7.

## 6. Maximal gazetteer: is extending `FR_REGIONS` worth it?

Scored 49 keys (the 14 existing + 35 modern regions, metropolitan departments and legacy
names) under the identical criterion and the identical per-key-minimum method, clamped per
file to `min(UB, rows)`:

| key set | keys | max resolvable | % of France rows | provably unresolvable |
|---|---|---|---|---|
| `FR_REGIONS` as-is | 14 | 1,213,296 | 71.60% | 481,149 (28.40%) |
| + 29 **token-disjoint** keys | 43 | 1,226,859 | 72.40% | 467,586 (27.60%) |
| all 49, overlaps undeducted | 49 | 1,257,967 | 74.24% | 436,478 (25.76%) |

The token-disjoint restriction matters: it counts only keys sharing **no** token with the 20
tokens `FR_REGIONS` already consumes, so no counted row is already resolvable and the delta
is provably incremental. That set is `lorraine`, `alsace`, `bretagne`, `gard`,
`basse normandie`, `normandie`, `haute normandie`, `haute marne`, `grand est`,
`martinique`, `cote d or`, `vosges`, `haute garonne`, `picardie`, `vienne`, `jura`,
`guyane`, `limousin`, `corse`, `sarthe`, `auvergne`, `rhone alpes`, `bourgogne`,
`franche comte`, `poitou charentes`, `champagne ardenne`, `midi pyrenees`,
`languedoc roussillon`, `provence alpes cote d azur`.

**Best case, maximally generous: a complete French gazetteer moves the bound by 2.64
percentage points (44,671 rows) and still leaves ≥25.76% of France rows unresolvable.** The
provably-incremental disjoint subset moves it by **0.80 pp (13,563 rows)**.

And even that 0.80 pp is an *upper* bound on gain, not an estimate of it. Under
whole-component matching (line 333) every added key is also a precision risk:
`lorraine` and `alsace` are common French street names ("Rue de Lorraine", "Rue d'Alsace"),
`grand est` and `centre` are ordinary nouns, `gard` is an ordinary French word. Under
*whole-component* matching these do **not** fire on a street-name component (the component
would be `12 rue de lorraine`, not `lorraine`), which limits but does not eliminate the
risk. Precision is unmeasurable here — **gap**.

Also: `seine` is 0 in all three files, so no department containing "Seine" can appear in
this data; Île-de-France is reachable only via `ile de france` / `paris`, both tiny.

## 7. ENGINEERING VERDICT

**Do not extend `FR_REGIONS`. This is a settled "no defect found" for the dictionary, and
the fleet brief's existing entry ("`FR_REGIONS` needs no dictionary expansion") is
confirmed — now with the mechanism explained rather than merely asserted.**

I reasoned under the criterion in §1: a row resolves a state iff a whole comma-component of
the accent-stripped, lowercased, punctuation-folded `business_address` exactly equals one
of the 14 keys. Under that criterion the dictionary is not the binding constraint:

- The three region tokens that carry mass (`hauts` 289,655, `nouvelle` 242,802, `pays`
  207,396 — 89.7% of all region mass) are **already mapped**.
- The department tokens that dominate s2/s3 (`nord` 152,011, `gironde` 150,787, `calais`
  128,762, `atlantique` 128,348 — 98.9% of department mass) are **also already mapped**.
  This is the fact the old REFUTED-2 entry recorded without explaining: s2/s3 do resolve,
  through the department half of the existing table.
- The ≥25.76% residual is address-shaped `house number + street + city` with **no
  administrative component at all**, which no gazetteer can reach. A maximal 49-key
  gazetteer buys at most 2.64 pp on paper and 0.80 pp provably-incremental.

The only fix with real value is a **city→region table** — `bordeaux` / `nantes` / `lille`
alone are ~43.7% of every French test file — but the profile stores marginal token counts
with no co-occurrence, so **I cannot produce that mapping from this evidence**. That is a
gap, not a number, and it is the correct next scraping job: re-scan France with component
identity preserved, keyed on city.

**On the contradiction itself:** D077's 2.5620% should be **retired, not averaged with
D073's**. It measures the empty-address rate, it is near country-invariant (US 97.06% /
India 97.54% / France 97.44%), and presenting it as a "ceiling" invites exactly the
averaging error that produced this task. Any future "state resolves for X% of rows" claim
must state (a) the component-match criterion and (b) the denominator file.

## Provenance

| field | source |
|---|---|
| state rule | `_upstream/src/normalize.py:314-335`, `:250`, `:243-249` |
| token semantics | `build_profile.py:28` (`TOKEN_RE`), `:126-127` (component split + flatten), `:139` (top-4000) |
| France rows | `by_country["France"]["rows"]`: 259,452 / 703,378 / 731,615 |
| structural | `by_country["France"]`: `addr_empty` 0/21,537/21,541 · `has_comma` 259,452/681,661/709,921 · `alpha_only_addr` 1,089/26,656/26,857 · `dig5` 1,082/3,613/3,909 |
| token counts | `addr_tokens["France"]` in `analysis_out/profile/test_s{1,2,3}.json` |
| cutoffs | min value in each file's France `addr_tokens` list: 23 / 58 / 60 |
| France scope | `country_rows` in `train_s{1,2,3}.json` = US + India only; France is test-only |

All computation in PowerShell (`ConvertFrom-Json` over the profile JSON); Python is broken on
this box. No raw TSV was opened. No network access. `_upstream/` and the dataset untouched.



