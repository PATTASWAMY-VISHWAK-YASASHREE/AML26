# D073 — mine evidence to extend FR_REGIONS for France

## Headline

**The inherited claim "state resolves for 100.00% of France rows" is an artefact of testing only `test_source1`, which is 15.31% of French rows. It is false for the other two test files.** Using a sound upper bound on `normalize_address`'s exact-component matching, at most **1,213,296 of 1,694,445** France rows (71.60%) can resolve a state, and **at least 481,149 rows (28.40%) provably cannot**. But the fix with real value is small: a maximal French region/department gazetteer recovers at most **10,307 rows (0.608%)** of that gap. The 28.40% residual is *not* a dictionary defect — it is the ~35% of French rows in s2/s3 that carry no region component at all.

The most valuable new finding is not in `FR_REGIONS` at all: **the `LEET` table silently corrupts 1,111 French ordinal tokens** (`3eme`→`eeme`, `1er`→`ler`), and French addresses are city-dominated to an extreme degree (top-3 cities = 43.3% of all French rows).

## Findings

### 1. Method, and why it is an upper bound

`normalize_address` (`_upstream/src/normalize.py:328-335`) resolves a state **only on an exact whole-comma-component match**:

```python
comps = [c.strip() for c in s.split(",")]
...
    ck = re.sub(r"[^a-z0-9& ]+", " ", c).replace("&", " and ")
    ck = " ".join(ck.split())
    if ck in smap:          # smap == FR_REGIONS for France
        state = smap[ck]; continue
```

So a row resolves **iff** some comma component equals a key after accent-stripping and punctuation→space.

`build_profile.py` splits the address on `[,;]` (`ADDR_SPLIT`, line 31) before counting tokens, so the profile's `addr_tokens` are the token multiset of those same components. For a multi-token key, the number of rows that can *contain* it is at most the **minimum** of its token counts. Summing over all 14 `FR_REGIONS` keys gives a union bound `UB`. Overlap between keys only inflates `UB`, so:

> resolvable ≤ min(UB, rows)  and  unresolved ≥ max(rows − UB, 0)

Source: `by_country["France"]["rows"]` and `addr_tokens["France"]`.

### 2. Two soundness corrections applied (this is why the numbers differ from the prior run)

The naive version of this bound is **not** sound, for two reasons I found by reading `build_profile.py`:

| issue | detail | fix |
|---|---|---|
| **Top-4000 truncation** | `build_profile.py:140` keeps only `most_common(4000)`. A key token absent from the list has count ≤ the rank-4000 cutoff (23 / 58 / 60 for s1/s2/s3), **not 0**. | substitute the cutoff for absent tokens |
| **Accent loss** | `TOKEN_RE = [a-z0-9]+` (line 28) is applied to the *lowercased* address with **no** `strip_accents`. `île-de-france` yields profile token `le` (the `î` is silently dropped), while `normalize_address` sees `ile`. So the profile **undercounts** accented keys. | for the key token `ile`, substitute `max(count(ile), count(le))` |

`le` is a valid upper stand-in for `ile` because `count(le)` ≥ the number of rows actually spelled with a circumflex. Measured: `ile`/`le` = 303/1,992 (s1), 817/4,882 (s2), 794/5,050 (s3).

### 3. The bound — and the refutation

| file | France rows | naive UB | naive unres. | **sound UB** | **provably unresolved** | **% unres.** |
|---|---|---|---|---|---|---|
| `test_s1.json` | 259,452 | 261,705 | 0 | 263,440 | 0 (bound vacuous) | 0.00% |
| `test_s2.json` | 703,378 | 457,385 | 245,993 | 461,566 | **241,812** | **34.38%** |
| `test_s3.json` | 731,615 | 487,902 | 243,713 | 492,278 | **239,337** | **32.71%** |
| **TOTAL** | **1,694,445** | — | 489,706 | — | **≥ 481,149** | **≥ 28.40%** |

`test_s1` contributes 0 because `UB` (263,440) exceeds `rows` (259,452) — the bound is *vacuous* there, which is precisely why it cannot detect anything.

**Arithmetic check on the inherited block:** `101,521 + 85,197 + 72,734 = 259,452`, exactly the `test_s1` France row count. Those three figures are the s1 `hauts`/`nouvelle`/`pays` token counts. **The prior agent's region breakdown and its 100% figure are both s1-only.** s1 is `259,452 / 1,694,445 = 15.31%` of French rows. The 84.69% that the claim never touched does not support it.

Per-file France row totals (`country_rows["France"]`): s1 259,452 · s2 703,378 · s3 731,615.

### 4. What a maximal gazetteer would actually recover — small

I scored a 51-key candidate gazetteer (all 18 modern regions, 96 metropolitan departments, plus pre-2016 legacy names) using the same per-key-minimum bound, restricted to keys whose constituent tokens are **disjoint** from the 20 tokens already used by `FR_REGIONS`, so no counted row is already resolvable.

| key | UB rows | % of FR rows | status |
|---|---|---|---|
| `lorraine` | 1,948 | 0.115% | LIKELY — region, but "Rue de Lorraine" is a common street name |
| `alsace` | 1,813 | 0.107% | LIKELY — same ambiguity |
| `bretagne` | 1,262 | 0.074% | CONFIRMED — unambiguous region token |
| `val de marne` | 1,124 | 0.066% | CONFIRMED — department |
| `centre val de loire` | 960 | 0.057% | LIKELY — `centre` alone = 343, a generic noun |
| `gard` | 760 | 0.045% | LIKELY — department, but also an ordinary French word |
| `basse normandie` / `normandie` | 756 each | 0.045% | CONFIRMED (overlapping; not additive) |
| `maine et loire` | 645 | 0.038% | CONFIRMED |
| `haute normandie` / `haute marne` / `haute loire` | 543 each | 0.032% | CONFIRMED |
| `grand est` | 469 | 0.028% | LIKELY — `grand` = 1,710, a common street word |
| `martinique` | 414 | 0.024% | CONFIRMED |
| `cote d or` | 349 | 0.021% | CONFIRMED |
| `vosges` | 348 | 0.021% | CONFIRMED |
| `haute garonne` | 257 | 0.015% | CONFIRMED |
| `picardie` | 215 | 0.013% | CONFIRMED |
| `vienne`, `jura`, `guyane`, `limousin`, `corse`, `sarthe` | 141–194 | ≤0.011% | SPECULATIVE — single-token, collision-prone, **and the 141 figure is a truncation artefact, not a real frequency** |

**Total clean-gazetteer recovery ≤ 10,307 rows = 0.608% of France rows.** Even the maximally generous figure — summing all 37 candidates with overlaps undeducted — is **16,589 rows (0.979%)**, and **1,692 of those are pure measurement artefact**: 12 keys have an absent token, so each inherits the cutoff substitute (23+58+60 = 141). Their true frequency is somewhere in 0–141; I cannot distinguish, so I flag them SPECULATIVE rather than quoting 141 as a count.

**Two keys already in `FR_REGIONS` are dead:** `aisne` and `vendee` are both absent from the top-4000 `addr_tokens` in all three test files. True count is 0–23 / 0–58 / 0–60 respectively. The inherited "~1,100 rows of legacy names" is therefore *not* legacy region names in any volume — it is an unmeasured residue.

`seine` = 0 in all three files ⇒ **no department containing "Seine" can appear in this data.** Île-de-France is reachable only via `ile de france` / `paris`.

**Zero-value candidates — do NOT add:** `corse`, `occitanie`, `var`, `rhone`, `alpes`, `herault`, `dordogne`, `charente`, `creuse`, `mayenne`, `tarn`, `essonne`, `yvelines`, `isere`, `loiret`, `manche`, `cotes d armor`, `finistere`, `morbihan` are all absent from the top-4000. So are the multi-token keys `champagne ardenne`, `midi pyrenees`, `seine et marne`, `seine saint denis`, `hauts de seine`, `franche comte`, `provence alpes cote d azur`, `languedoc roussillon`, `charente maritime`, `deux sevres`, `poitou charentes` — one constituent token is always absent.

### 5. NEW DEFECT — `LEET` corrupts French ordinals

`LEET` (`normalize.py:256`) is applied by `_name_tokens` (line 279) to **every** token containing both an alpha and a digit character. That includes French ordinal suffixes, which are not leetspeak:

| token | occurrences | LEET output | reading |
|---|---|---|---|
| `3eme` | 748 | `eeme` | *troisième* |
| `1er` | 131 | `ler` | *premier* |
| `3e` | 121 | `ee` | *troisième* (short form) |
| `1ere` | 102 | `lere` | *première* |
| `7eme` | 9 | `teme` | *septième* |
| **total** | **1,111** | | **0.066% of France rows** |

Source: `name_tokens["France"]`, tokens matching `^\d+(er|ere|eme|e)$`, summed over the three test files (truncated at top-4000, so 1,111 is a lower bound).

This is a real, previously-unrecorded defect: it is deterministic and lossy, so a business named *…3eme* and one named *…Eeme* collapse together, while a *…3ème* spelled without the digit matches neither.

**The leet table needs no new mappings.** 24 distinct France name tokens contain both alpha and digit, totalling **5,307 occurrences**; the existing `0→o 1→l 3→e 4→a 5→s 6→g 7→t 8→b` covers every genuine case correctly: `5arl→sarl` (637), `c1ub→club` (190), `amica1e→amicale` (136), `mais0n→maison` (118), `5asu→sasu` (85), `c0mite→comite` (75), `ass0ciation→association` (75), `rati0n→ration` (61), `tab1issements→tablissements` (56), `li1le→lille` (54), `fi1s→fils` (26), `sp0rtive→sportive` (25), `5portive→sportive` (26), `5ci→sci` (27). Purely numeric tokens like `41` (278) correctly stay digits, since they lack an alpha character.

### 6. What the 28.40% residual actually is

It is **not** a region-dictionary problem. Evidence that s2/s3 French addresses simply lack a region component:

- `has_comma` is **259,452 / 259,452 = 100.00%** in s1 but only **681,661 / 703,378 = 96.91%** (s2) and **709,921 / 731,615 = 97.03%** (s3). s1 always carries the extra comma that holds the region.
- `alpha_only_addr` (address has **no digit at all**) is **1,089 / 259,452 = 0.42%** in s1 but **26,656 / 703,378 = 3.79%** (s2) and **26,857 / 731,615 = 3.67%** (s3).
- s2/s3 are dominated by **department** names rather than region names, per the per-key minima: `gironde` 75,104 (s2) and 75,621 (s3) versus **62** in s1 — a ~1,214× jump. Likewise `loire atlantique` 63,697 (s2) versus 253 (s1), a 252× jump. The departments are already mapped; the *region* word is simply absent.

### 7. Abbreviation pairs — every mined pair is already handled

Probed short/long pairs with both counts above cutoff, `test_s2` `addr_tokens["France"]`:

| short | n | long | n | already in `ADDR_CANON_FR`? |
|---|---|---|---|---|
| `st` | 12,555 | `saint` | 56,130 | yes → `saint` (line 207) |
| `av` | 27,580 | `avenue` | 45,928 | yes → `ave` (line 200) |
| `ave` | 10,792 | `avenue` | 45,928 | yes |
| `bd` | 11,596 | `boulevard` | 14,029 | yes → `blvd` (line 201) |
| `blvd` | 3,000 | `boulevard` | 14,029 | yes |
| `all` | 24,216 | `allee` | 8,185 | yes → `allee` (line 204) |
| `imp` | 5,998 | `impasse` | 7,735 | yes → `impasse` (line 203) |
| `ch` | 5,734 | `chemin` | 5,535 | yes → `chemin` (line 202) |
| `rte` | 5,783 | `route` | 6,549 | yes → `rte` (line 204) |
| `pl` | 5,980 | `place` | 4,818 | yes → `pl` (line 203) |
| `res` | 3,255 | `residence` | 1,888 | yes → `res` (line 210) |
| `q` | 2,132 | `quai` | 2,982 | yes → `quai` (line 206) |
| `bat` | 688 | `batiment` | 761 | yes → `bat` (line 211) |
| `ste` | 239 | `sainte` | 3,071 | yes → `sainte` (line 207) |

**No new abbreviation entry is warranted for France.** `av` is the only one with real mass (27,580) and it is already mapped.

### 8. Department *codes* are not a signal — refuted

The 2-digit tokens that could be French department numbers are ordinary house numbers. Comparing each against the median of all 99 two-digit tokens present (`test_s2`, median 2,915): `33` ranks 24/99 at 2.16× median, but `77` ranks **67/99** (0.62×), `78` **70/99** (0.60×), `91` **82/99** (0.47×), `92` **83/99**, `95` **84/99**, `94` **85/99**, `93` **89/99**. Identical ordering in `test_s3`. A genuine department code would rank near the top; these rank near the bottom, below the median. **Do not add numeric department codes to any table.**

### 9. France is extremely city-concentrated

`addr_tokens["France"]`, excluding street/region/generic words:

| token | s1 | s2 | s3 |
|---|---|---|---|
| `bordeaux` | 43,634 (16.82%) | 114,608 (16.29%) | 119,232 (16.30%) |
| `nantes` | 37,624 (14.50%) | 98,429 (13.99%) | 102,695 (14.04%) |
| `lille` | 34,931 (13.46%) | 91,622 (13.03%) | 95,032 (12.99%) |
| **top-3 share** | **44.78%** | **43.32%** | **43.32%** |

`tourcoing` / `dunkerque` / `roubaix` add a further ~19.6% in every file. The profile also exposes **accent-truncated city fragments** — `rignac` (19,738 in s2) is *Mérignac*, `buch`/`teste` are *La Teste-de-Buch*, `nazaire` is *Saint-Nazaire*, `lege` is *Lège*. Same accent-loss artefact as §2, and a reason a raw substring gazetteer would over-match.

### 10. Corroborating France shape (`by_country["France"]`)

| field | s1 | s2 | s3 |
|---|---|---|---|
| rows | 259,452 | 703,378 | 731,615 |
| France share of file | 14.98% | 14.39% | 14.40% |
| `dig5` (standalone 5-digit) | 1,082 (0.0042/row) | 3,613 (0.0051/row) | 3,909 (0.0053/row) |
| `dig6` | 34 (0.0001/row) | 130 (0.0002/row) | 115 (0.0002/row) |
| `addr_empty` | 0 | 21,537 (3.06%) | 21,541 (2.94%) |
| `name_empty` | 0 | 0 | 0 |
| `prefix_bad` | 0 | 0 | 0 |

**This corroborates REFUTED-1 with numbers, on all three files, not just s1:** France `dig5`/row is 0.0042–0.0053, an order of magnitude below US 0.110. I did not re-derive the US side, as instructed.

## Interpretation

*Inference, clearly marked:*

1. **Do not treat the 28.40% as a `FR_REGIONS` bug.** A maximal gazetteer buys ≤0.608% of France rows. The remaining ~28% is *structural*: those addresses are `house number + street + city` with no region word. No dictionary fixes that. The only fixes are (a) derive region from the city, or (b) accept the missing state.
2. **A city→region table is the high-value asset** (`already_checked` flagged this). Bordeaux, Nantes and Lille alone are 43.3% of every French test file. But the profile gives marginal token counts, not city-region co-occurrence, so **I cannot produce the mapping from this evidence.** Flagged as a gap, not estimated.
3. **The `LEET` ordinal corruption is a safe, cheap fix** and is the only defect here I would action immediately.
4. **Adding `lorraine`/`alsace` is a precision risk, not a free win.** "Rue de Lorraine" and "Rue d'Alsace" are common French street names. Because `normalize_address` matches *whole components*, a row like `12 Rue de Lorraine, ...` would **not** fire (the component is `12 rue de lorraine`, not `lorraine`) — which limits, but does not eliminate, the risk. **I did not measure US `nord` collision frequency, so the precision side of `nord` is unquantified — gap.**

## Gaps

- **City→region mapping.** Not derivable from the profile: `addr_tokens` holds marginal counts, not co-occurrence. Not estimated.
- **Precision of any candidate key.** I can bound how many rows *could* resolve, never how many *would falsely* resolve. Every new entry is a potential false positive; measuring that needs row-level data.
- **True counts for 12 candidate keys** whose tokens fall below the top-4000 cutoff. I substituted the cutoff and labelled the result SPECULATIVE rather than reporting it as a frequency.
- **The ~1,100 "legacy region rows"** named in `already_checked` cannot be inspected: the profile stores per-token counts, not per-row addresses, and opening the raw TSVs is prohibited on this box.
- **Component order** (`"Bordeaux, Nouvelle-Aquitaine"` vs `"Nouvelle-Aquitaine, La Teste-de-Buch"`), raised in `already_checked`, is **not measurable here**: the profile splits components and discards their order, so order is unrecoverable without the raw files.
- **US `nord` / `lorraine` frequency** — not measured; needed before adding those keys.

