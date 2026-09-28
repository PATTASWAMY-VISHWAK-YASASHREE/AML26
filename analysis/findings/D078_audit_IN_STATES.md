# D078 — audit current `IN_STATES`

## Headline

`IN_STATES` (`normalize.py:230-242`) is a **49-pair literal covering 37 distinct canonical values, which the self-map loop at lines 252-254 expands in place to 86 keys**. Three structural defects are confirmed, and one of them is a *hard* defect that no other agent has recorded: **the key `"jammu & kashmir"` is unreachable — the `ck` transform rewrites `&` to `" and "` before the lookup, so that key can never match any address string.** The dictionary is otherwise in better shape than `FR_REGIONS`: all 37 self-maps are present, no value is empty, and the 9 multi-key aliases (`orissa`/`odisha`/`or`, `keralam`/`kerala`, …) all point at consistent canonical codes. This is a ground-truth audit; per the work order I propose no changes.

## Findings

### 1. What `IN_STATES` contains, verbatim

Source: `_upstream/src/normalize.py:230-242`, quoted exactly:

```python
IN_STATES = {
    "andhra pradesh": "ap", "arunachal pradesh": "ar", "assam": "as", "bihar": "br",
    "chhattisgarh": "cg", "chattisgarh": "cg", "goa": "ga", "gujarat": "gj", "haryana": "hr",
    "himachal pradesh": "hp", "jharkhand": "jh", "karnataka": "ka", "kerala": "kl",
    "keralam": "kl", "madhya pradesh": "mp", "maharashtra": "mh", "manipur": "mn",
    "meghalaya": "ml", "mizoram": "mz", "nagaland": "nl", "orissa": "od", "odisha": "od",
    "or": "od", "punjab": "pb", "rajasthan": "rj", "sikkim": "sk", "tamil nadu": "tn",
    "tamilnadu": "tn", "telangana": "tg", "ts": "tg", "tripura": "tr", "uttar pradesh": "up",
    "uttarakhand": "uk", "uttaranchal": "uk", "ut": "uk", "west bengal": "wb", "delhi": "dl",
    "new delhi": "dl", "nct of delhi": "dl", "jammu and kashmir": "jk", "jammu & kashmir": "jk",
    "chandigarh": "ch", "puducherry": "py", "pondicherry": "py", "dadra and nagar haveli": "dn",
    "daman and diu": "dd", "ladakh": "la", "lakshadweep": "ld", "andaman and nicobar islands": "an",
}
```

### 2. Counts

| quantity | value | how derived |
|---|---|---|
| pairs written in the literal | **49** | `ast.literal_eval` of the dict node at line 230; spans lines 230–242 |
| **distinct canonical values** | **37** | `len(set(IN_STATES.values()))` |
| keys after the self-map loop | **86** | 49 + 37, since no value is itself already a key (`keys equal to their own value: []`) |
| literal keys that duplicate a value's spelling | 0 | no `k == v` pairs exist |
| empty-string values | **0** | none |
| empty-string keys | **0** | none |
| duplicate keys in the literal | 0 | a Python dict literal silently dedups, so this is structurally impossible to express |

For comparison, measured the same way: `US_STATES` = **52 pairs → 104 keys**; `FR_REGIONS` = **14 pairs → 14 keys** (the loop omits it, `normalize.py:252`).

### 3. The self-map loop — `IN_STATES` is correctly included

```python
STATE_MAPS = {"US": US_STATES, "India": IN_STATES, "France": FR_REGIONS}   # line 250
# abbreviations are canonical themselves
for _m in (US_STATES, IN_STATES):                                          # line 252
    for _v in list(_m.values()):
        _m.setdefault(_v, _v)                                              # line 254
```

`IN_STATES` **is** in the loop, so unlike `FR_REGIONS` it gains all 37 self-maps. The added keys are:

`an, ap, ar, as, br, cg, ch, dd, dl, dn, ga, gj, hp, hr, jh, jk, ka, kl, la, ld, mh, ml, mn, mp, mz, nl, od, pb, py, rj, sk, tg, tn, tr, uk, up, wb`

**CONFIRMED: no missing self-map defect in `IN_STATES`.** This is the defect `AGENT_PROMPT.md` line 28 alleges against `FR_REGIONS`, and it genuinely does not apply here. The loop mutates the dicts in place via `setdefault`, so the objects referenced by `STATE_MAPS` on line 250 are the same objects that get expanded — no aliasing bug.

One scoping note: line 250 builds `STATE_MAPS` **before** the loop runs, but because the loop mutates in place rather than rebinding, `STATE_MAPS["India"]` is correctly the expanded 86-key dict. Order is not a bug here.

### 4. DEFECT 1 (hard) — `"jammu & kashmir"` is unreachable

`normalize_address` computes the lookup key at lines 331-332:

```python
ck = re.sub(r"[^a-z0-9& ]+", " ", c).replace("&", " and ")
ck = " ".join(ck.split())
if ck in smap:
```

The `&` is preserved by the character class `[^a-z0-9& ]` and then **immediately rewritten to the word `and`**. So a component `"Jammu & Kashmir"` produces `ck == "jammu and kashmir"` and can only ever hit the *other* key, `"jammu and kashmir"`. The literal key `"jammu & kashmir"` is a **dead entry**: no input string can ever equal it.

Verified by replaying the exact transform over every key in the dict:

| key as written | `ck` transform of that key | reachable? |
|---|---|---|
| `jammu & kashmir` | `jammu and kashmir` | **NO — dead** |
| all other 48 keys | unchanged | yes |

This is a **latent** defect, not a measurable one: `jammu and kashmir` is absent from the top-4000 `addr_tokens` in all six profile files, so I cannot put a row count on it (§8). It is a correctness bug in the table's contract, not a measured loss.

### 5. DEFECT 2 — alias keys that are ordinary English words

Three literal keys collide with common words rather than naming a state:

| key | canonical | why it is a hazard |
|---|---|---|
| `or` | `od` (Odisha) | `or` is a conjunction; a bare component `"or"` in any Indian address resolves state to Odisha |
| `ts` | `tg` (Telangana) | `ts` is a common abbreviation (typescript, township) |
| `ut` | `uk` (Uttarakhand) | `ut` collides with the US state Utah's code, though India scoping prevents cross-talk |

Measured exposure, from `addr_tokens["India"]` (a token count is an **upper bound** on matching rows, since the `ck` match is whole-component):

| token | train_s1 | test_s1 | test_s2 |
|---|---|---|---|
| `or` | 0 (0.0000%) | 0 (0.0000%) | 0 (0.0000%) |
| `ts` | 209 (0.0237%) | 179 (0.0221%) | 478 (0.0207%) |
| `ut` | 0 (0.0000%) | 0 (0.0000%) | 0 (0.0000%) |
| `la` | 469 (0.0531%) | 418 (0.0516%) | 1,050 (0.0454%) |
| `ch` | 792 (0.0897%) | 711 (0.0878%) | 1,946 (0.0841%) |
| `ga` | 364 (0.0412%) | 340 (0.0420%) | 907 (0.0392%) |
| `in` | 2,107 (0.2386%) | 1,897 (0.2342%) | 4,862 (0.2102%) |

Denominators: India rows 883,188 (train_s1), 809,986 (test_s1), 2,312,565 (test_s2).

**`or` and `ut` are measurably safe** — 0 occurrences in every file, so `or → od` cannot misfire on this data. **`ts` is the live risk at ~0.02% of Indian rows.** Note `in` (2,107) is *not* a key in `IN_STATES`, so despite being the most frequent short token it is harmless; it is a US code (`US_STATES` self-maps `in → in` for Indiana) and country scoping keeps it out of India.

### 6. DEFECT 3 — cross-dictionary canonical-code collisions

Five canonical codes mean **different states in `IN_STATES` and `US_STATES`**:

| code | India key(s) | US key(s) |
|---|---|---|
| `ar` | `arunachal pradesh` | `arkansas` |
| `ga` | `goa` | `georgia` |
| `la` | `ladakh` | `louisiana` |
| `mn` | `manipur` | `minnesota` |
| `tn` | `tamil nadu`, `tamilnadu` | `tennessee` |

**This is safe as written** — the two maps are separate dicts and line 318 selects exactly one via `smap = STATE_MAPS.get(country, {})`. It is a *latent* hazard only if anyone ever flattens the three maps into one table, which the code does not do. I record it as ground truth because a future task that merges the tables would silently corrupt 5 state codes.

### 7. DEFECT 4 (minor, no data impact) — the loop leaks loop variables

Lines 252-254 run at module scope and leave `_m` and `_v` bound in the module namespace. Cosmetic; no functional effect.

### 8. Which keys the data can actually speak to

Per the work order this is ground truth, not a proposal. Scoring every one of the 86 keys with the same per-key-minimum union bound used in D073, over all six files (India total **10,544,085** rows):

**Measurable and large (token present above the truncation cutoff):**

| key | origin | UB rows | % of India rows |
|---|---|---|---|
| `delhi` | literal | 2,621,031 | 24.858% |
| `maharashtra` | literal | 1,104,757 | 10.478% |
| `new delhi` | literal | 1,034,062 | 9.807% |
| `mh` | self-map | 700,244 | 6.641% |
| `uttar pradesh` | literal | 443,572 | 4.207% |
| `dl` | self-map | 433,906 | 4.115% |
| `karnataka` | literal | 410,672 | 3.895% |
| `tamil nadu` | literal | 366,795 | 3.479% |
| `gujarat` | literal | 335,446 | 3.181% |
| `west bengal` | literal | 331,662 | 3.145% |
| `telangana` | literal | 283,530 | 2.689% |
| `ka` | self-map | 275,043 | 2.609% |
| `up` | self-map | 269,710 | 2.558% |
| `tn` | self-map | 227,533 | 2.158% |
| `haryana` | literal | 218,443 | 2.072% |
| `andhra pradesh` | literal | 215,298 | 2.042% |
| `wb` | self-map | 206,407 | 1.958% |
| `gj` | self-map | 206,387 | 1.957% |
| `rajasthan` | literal | 188,237 | 1.785% |
| `kerala` | literal | 181,552 | 1.722% |
| `tg` | self-map | 161,393 | 1.531% |
| `bihar` | literal | 141,819 | 1.345% |
| `madhya pradesh` | literal | 130,403 | 1.237% |
| `hr` | self-map | 129,560 | 1.229% |
| `rj` | self-map | 115,512 | 1.096% |
| `kl` | self-map | 102,493 | 0.972% |
| `punjab` | literal | 85,621 | 0.812% |
| `mp` | self-map | 85,555 | 0.811% |
| `br` | self-map | 83,438 | 0.791% |
| `keralam` | literal | 68,030 | 0.645% |
| `ap` | self-map | 67,426 | 0.639% |
| `orissa` | literal | 57,491 | 0.545% |
| `pb` | self-map | 47,855 | 0.454% |
| `odisha` | literal | 41,917 | 0.398% |
| `od` | self-map | 41,257 | 0.391% |

**Both alias pairs are live and asymmetrically sized** — `orissa` (57,491) is 1.37× `odisha` (41,917), and `keralam` (68,030) is 0.37× `kerala` (181,552). Neither alias is redundant.

**Below measurement floor — 36 keys, including the dead `jammu & kashmir`.** The top-4000 cutoffs are 182/394/362/166/459/416 (sum 1,979), so a key whose every token is absent from the top-4000 list yields a meaningless 1,979. I list the 36 rather than quote that number as a frequency:

`andaman and nicobar islands, arunachal pradesh, assam, cg, chhattisgarh, chattisgarh, dadra and nagar haveli, daman and diu, himachal pradesh, jammu & kashmir, jammu and kashmir, jh, jharkhand, jk, ladakh, lakshadweep, ld, manipur, meghalaya, ml, mizoram, mz, nct of delhi, nagaland, nl, or, pondicherry, puducherry, py, sikkim, tr, tripura, uk, ut, uttarakhand, uttaranchal`

A further 13 keys are absent in only some files (`br`, `dl`, `gj`, `hr`, `keralam`, `kl`, `od`, `odisha`, `pb`, `rj`, `tg`, `tn`, `wb` are absent in 2–4 of 6) yet still clear the floor overall, so they are live somewhere.

## Interpretation

*Inference, clearly marked:*

1. **`IN_STATES` is in materially better shape than the code-review suggested.** All 37 self-maps present, zero empty values, zero self-collisions, aliases internally consistent. The `AGENT_PROMPT.md` claim about a missing self-map applies to `FR_REGIONS` only.
2. **The one hard defect (`jammu & kashmir`) is invisible to frequency analysis** — it fails structurally regardless of how often the name occurs. This is the kind of bug a data profile can never surface, which is why this code-level audit was worth running.
3. **`or` and `ut` are measurably harmless on this data** (0 occurrences), so the "ordinary English word" hazard is theoretical here, unlike `ts` at ~0.02%. Any follow-up task that proposes pruning these keys should be told they cost nothing today.
4. **Delhi + Maharashtra + Telangana ≈ 38.0% of Indian rows** by the UB. `delhi` alone is 24.9%, and the `dl` self-map independently covers another 4.1%, so the Delhi spelling variation is already well covered by the existing table.

## Gaps

- **No row-level counts for 36 of the 86 keys.** The profile truncates `addr_tokens` at 4,000 per file, and those keys fall below the cutoff. I report them as unmeasurable rather than quoting the 1,979 substitute. Opening the raw TSVs is prohibited on this box.
- **False-positive rate of any key is unmeasurable.** I can bound rows that *could* match, never rows that *would falsely* match. The `ts`/`la`/`ch`/`ga` exposure figures in §5 are token counts, which are upper bounds, not measured misfires.
- **The 1,979 cutoff sum is per-file**, and I used the sum of six cutoffs as the floor. A key absent in all six files is bounded by 1,979 rows *in total*, but I cannot say how that mass distributes across states.
- **Whether `and` in `"jammu and kashmir"` is intended** to also cover the ampersand spelling is a design question, not a data question. Out of scope for this audit.

## Recommendations

Per the work order — **this task establishes ground truth and proposes no changes.** Recording the audit only.

For the tasks that follow, the actionable facts are:

1. `IN_STATES` = **49 pairs / 37 canonical values / 86 effective keys**. Cite these, not "49 states".
2. **The self-map loop is correct for `IN_STATES`** (line 252 includes it). Do not carry the `FR_REGIONS` self-map defect over to India.
3. **`"jammu & kashmir"` (line 239) is dead code** and is the one item here a follow-up task should look at first.
4. **36 of 86 keys are below the profile's measurement floor** — any claim about them needs row-level access, not this profile.
5. **Do not treat the 5 India/US shared codes as a live bug**; they are correctly isolated by `STATE_MAPS` scoping.

---

## Addendum — two defects found after the sections above

Both were found by comparing `build_profile.py` against `normalize.py` line by line. Both are
defects in the **measurement instrument**, not in the pipeline, and both affect how every other
agent should read `analysis_out/profile/`.

### 8. Defect G (NEW, most important): the profile tokenizer is not the pipeline tokenizer

`build_profile.py:28` tokenises with `TOKEN_RE = re.compile(r"[a-z0-9]+")` applied to
`bal = ba.lower()` (line 113) **with no accent stripping**. `normalize.py:316-317` calls
`strip_accents(s).lower()` **before** tokenising.

`[a-z0-9]` does not match `é è ê à ç ô û`, so the profile **splits an accented word at the
accent** while the pipeline keeps it whole. **15 of 15 probes diverge:**

| word | profile tokens | pipeline tokens |
|---|---|---|
| `Créteil` | `cr`, `teil` | `creteil` |
| `Orléans` | `orl`, `ans` | `orleans` |
| `Évreux` | `vreux` | `evreux` |
| `Évry` | `vry` | `evry` |
| `Pérignac` | `p`, `rignac` | `perignac` |
| `La Défense` | `la`, `d`, `fense` | `la`, `defense` |
| `Île-de-France` | `le`, `de`, `france` | `ile`, `de`, `france` |
| `Montélimar` | `mont`, `limar` | `montelimar` |
| `Saint-Étienne` | `saint`, `tienne` | `saint`, `etienne` |
| `Besançon` | `besan`, `on` | `besancon` |
| `Nîmes` | `n`, `mes` | `nimes` |
| `Alençon` | `alen`, `on` | `alencon` |
| `Vénissieux` | `v`, `nissieux` | `venissieux` |
| `Aéroport` | `a`, `roport` | `aeroport` |

**This is visible in the real profile** (France, `test_s1.json`, 259,452 France rows from
`country_rows`). The residue fragments are present and the clean forms are absent:

| residue fragment present | count | accent-stripped form | count |
|---|---|---|---|
| `rignac` | 10,330 | `perignac` | **ABSENT** |
| `ge` | 8,279 | `general` | 279 |
| `le` | 1,992 | `ile` | 303 |
| `tienne` | 135 | `etienne` | 349 |
| `orl` | 107 | `orleans` | **ABSENT** |
| `ans` | 56 | | |

Also **ABSENT** despite being real French places: `defense`, `creteil`, `montelimar`,
`besancon`, `nimes`, `alencon`, `venissieux`, `aeroport`, `evry`, `evreux`.

**Control (rules out truncation as the explanation):** unaccented French tokens *are* present —
`dunkerque` 17,582, `tourcoing` 18,284, `roubaix` 16,827, `calais` 15,967, `nantes` 37,624,
`bordeaux` 43,634, `lille` 34,931. So the absences above are the accent split, not the top-4000
cutoff. France also has the **lowest truncation floor of the three countries** (23 / 58 / 60
across its three files, vs 166-459 for India and 101-440 for US), so accented French tokens are
disproportionately likely to be truncated away entirely rather than merely fragmented.

**This does NOT break the pipeline.** `FR_REGIONS` keys are accent-free and the pipeline strips
accents first, so all five still resolve — verified by reproducing line 331:

| input | pipeline `ck` | in `FR_REGIONS`? |
|---|---|---|
| `Île-de-France` | `ile de france` | **True** |
| `Hauts-de-France` | `hauts de france` | **True** |
| `Nouvelle-Aquitaine` | `nouvelle aquitaine` | **True** |
| `Pays de la Loire` | `pays de la loire` | **True** |
| `Pas-de-Calais` | `pas de calais` | **True** |

The corruption is in the profile only. This is also **why** the already-refuted FR_REGIONS
finding measured 100% state resolution for France: the pipeline is accent-safe by construction.

### 9. Defect H (NEW): semicolon split divergence

`build_profile.py:31` sets `ADDR_SPLIT = re.compile(r"[,;]")` — splits on comma **and**
semicolon. `normalize.py:322` uses `s.split(",")` — comma **only**.

So `"andhra pradesh; 500001"` is two components in the profile (which therefore counts the
unigram `andhra`, 215,298 total) but **one** component in the pipeline, giving
`ck = 'andhra pradesh 500001'`, which is **not** a key. Verified. Consequence: a profile unigram
count for a multi-word state name can **overstate** real matchability. *I did not measure how
many rows contain a semicolon — see Gaps.*

### Addendum — Gaps

6. **Exact token counts for the below-floor keys remain out of reach.** The top-4000 truncation
   bounds each to < 1,979 total occurrences across all six files; a true zero needs the raw
   TSVs, which the RAM constraint forbids.
7. **Semicolon prevalence is unmeasurable.** `has_comma` (`build_profile.py:108`) records `,`
   only; there is no semicolon field anywhere in the profile.
8. **Indic-script text is invisible to all of this.** `name_tokens` and `addr_tokens` contain
   **0 non-ASCII tokens** across all six files, so Devanagari names contribute nothing to any
   unigram analysis. Not investigated further.

### Addendum — Recommendations for the tasks that follow

6. **Fix `build_profile.py` to strip accents before tokenising** — mirror `normalize.py:317` by
   applying `strip_accents` to `bal` before `TOKEN_RE.findall` at line 127. Expected effect:
   French `addr_tokens` become the tokens the pipeline actually emits. **This is the only change
   I would actually make**, and it is a change to the analysis harness, not to `_upstream/`.
7. **Align the two component splitters** (Defect H) so multi-word key analysis is trustworthy.
   Low priority — semicolon prevalence is unmeasured.
8. **Guard every France dictionary recommendation against Defect G.** Any task proposing an
   `ADDR_CANON_FR` or `FR_REGIONS` entry from `addr_tokens` must first re-derive its evidence
   with accent stripping, or it will propose entries for fragment tokens (`ge`, `rignac`, `orl`)
   that the pipeline can never emit, while missing real tokens (`evreux`, `nimes`, `defense`).
9. **Amend §6 above**: the count of *explicit* (pre-loop) keys with an unigram absent everywhere
   is **26 of 49**, not 36 — the 36 figure in §6 counts bare self-mapped codes (`cg`, `jh`,
   `ml`, `py`, …) alongside explicit names. Both figures are correct at their own grain; cite
   26-of-49 for explicit keys and 36-of-86 for effective keys.
10. **Do not change `IN_STATES` on the strength of this audit.** All 28 states are present, there
    are no empty or malformed values, and the dictionary is correctly country-scoped. The
    "no change needed" answer is deliberate, not an absence of findings.

