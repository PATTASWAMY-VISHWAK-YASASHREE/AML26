# D075 — mine evidence to extend US_STATES for US

## Headline

`US_STATES` needs **no extension**: 47 of its 52 keys carry real evidence, and the two
abbreviations that do appear in US addresses (`del` 10,711 and `penn` 3,084) are worth
adding but are **LIKELY, not CONFIRMED**. The far bigger finding is elsewhere and is
**new**: the US address corpus is written in **two mutually exclusive dialects** —
sources 1 and 2 write the 2-letter state code, source 3 writes the full state name — and
a second, larger defect sits in `ADDR_CANON_COMMON`, which canonicalises only ordinals
1–5 and therefore leaves **396,959 ordinal occurrences (77.67% of all numeric ordinals)
un-normalised**, at 33.11 per 1,000 US address rows.

## Findings

All counts are aggregated over the six profiles
`train_s1..3`, `test_s1..3`, from the `addr_tokens["US"]` / `name_tokens["US"]` fields.
US rows across all six files = **11,990,643** (`by_country.US.rows`:
1,323,633 + 3,016,817 + 3,170,056 + 663,106 + 1,871,330 + 1,945,701).

### F1 — `US_STATES` coverage is already near-complete (CONFIRMED)

`US_STATES` (normalize.py:216–229) holds 52 entries. Measured on the profile:

| group | n | evidence |
|---|---|---|
| single-word names present | 36 / 38 | e.g. `texas` 480,985; `ohio` 307,283; `illinois` 273,325 |
| names with **zero** evidence, all 6 files | 2 | `hawaii` 0, `mississippi` 0 |
| multi-word names (unmeasurable — see Gaps) | 14 | profile stores tokens, not components |
| codes with **zero** evidence, all 6 files | 7 | `hi` `mi` `ms` `nv` `nh` `nj` `pr` all 0 |

Only 5 of 52 keys have zero support for *both* name and code:
`hawaii`, `mississippi`, `new hampshire`, `new jersey`, `puerto rico`.
Note `michigan` 7,822 and `nevada` 3,472 appear as **names** while `mi` and `nv` are
0 — those two states are written out in full and never abbreviated in this corpus.

### F2 — The corpus has two incompatible US state dialects (NEW, CONFIRMED)

This is a previously unreported structural fact, and it is an exact clean split by source:

### F3 — Ordinal canonicalisation stops at "fifth" (NEW, CONFIRMED, largest quantified gap)

`ADDR_CANON_COMMON` (normalize.py:184) maps exactly five pairs:
`first→1st, second→2nd, third→3rd, fourth→4th, fifth→5th`. Nothing beyond.

On US `addr_tokens`, tokens matching `^\d+(st|nd|rd|th)$`:

| file | ordinal occurrences | n<=5 (canonicalised) | n>=6 (not) | % uncovered |
|---|---|---|---|---|
| train_s1 | 86,006 | 17,550 | 68,456 | 79.59% |
| train_s2 | 113,327 | 26,226 | 87,101 | 76.86% |
| train_s3 | 121,063 | 27,492 | 93,571 | 77.29% |
| test_s1 | 43,297 | 8,867 | 34,430 | 79.52% |
| test_s2 | 70,982 | 16,408 | 54,574 | 76.88% |
| test_s3 | 76,437 | 17,610 | 58,827 | 76.96% |
| **ALL** | **511,112** | **114,153** | **396,959** | **77.67%** |

Cross-check: 68,456+87,101+93,571+34,430+54,574+58,827 = **396,959** — the per-file sum
equals the aggregate exactly. Rate: 396,959 / 11,990,643 x 1000 = **33.11 uncanonicalised
ordinals per 1,000 US address rows**.

The spelled forms are also stranded, and the asymmetry is the actual bug: `first`
(15,800) folds to `1st` so "First Ave" and "1st Ave" unify, but `sixth` (9,900) and
`6th` do **not** unify — one stays `sixth`, the other `6th`. Present spelled forms:
`first` 15,800, `second` 15,184, `third` 14,029, `fourth` 13,704, `fifth` 11,551,
`sixth` 9,900, `seventh` 9,382, `eighth` 7,850, `ninth` 6,565, `tenth` 6,237,
`eleventh` 5,359, `twelfth` 5,356, `fourteenth` 4,596, `thirteenth` 4,281,
`fifteenth` 4,065, `twentieth` 3,044. (`sixteenth`...`nineteenth` are 0.)

### F4 — `LEET` leetspeak table: two dead keys, one unmapped digit, two unreachable keys

`LEET` (normalize.py:256) = `0→o 1→l 3→e 4→a 5→s 6→g 7→t 8→b @→a $→s`.
Gate at normalize.py:279 only translates a token that is **both** alpha and digit, so the
`@` and `$` entries are **unreachable**: `_non_alnum = [^a-z0-9]+` (line 269) splits on
them before `translate` ever runs, so no surviving token can contain `@` or `$`.
Dead code, zero effect.

Digit frequency inside mixed alpha+digit US `name_tokens`
(133 distinct types, 90,100 occurrences):

| digit | occurrences | in `LEET`? |
|---|---|---|
| 0 | 34,401 | yes |
| 1 | 28,895 | yes |
| 2 | 3,657 | **no** |
| 3 | 0 | yes (dead key) |
| 4 | 3,657 | yes |
| 5 | 14,302 | yes |
| 6 | 4,933 | yes |
| 7 | 0 | yes (dead key) |
| 8 | 3,912 | yes |
| 9 | 0 | no |

The only mixed token containing an unmapped digit is **`24hr` (3,657)**, which is a
legitimate abbreviation, not leetspeak. So the missing `2→z` mapping has **no measured
cost**. Examples of genuine leetspeak the table *does* handle: `c0m` 2,855,
### F5 — Ranked candidate table for extending the dictionaries

Counts are aggregated US `addr_tokens`. Nothing here rises to CONFIRMED; the two
non-zero candidates are LIKELY and the rest have **zero** support.

| candidate | count | target | verdict | reasoning |
|---|---|---|---|---|
| `del` | 10,711 | `de`/Delaware | **LIKELY** | real token, classic Del. abbreviation; not in `US_STATES` |
| `penn` | 3,084 | `pa`/Pennsylvania | **LIKELY** | real token, "Penn" abbrev; not in `US_STATES` |
| `sixth`...`fifteenth`, `twentieth` | 136,903 | ordinals | **CONFIRMED** (see F3) | present, stranded by canon |
| `wisc` `calif` `fla` `mass` `wash` `ariz` `colo` `conn` `mich` `minn` `miss` `mont` `nebr` `okla` `tenn` `wyo` `kan` | 0 each | various | **SPECULATIVE / reject** | zero occurrences — adding is inert |

I explicitly tested the classic state abbreviations and **none** of them occur. The
"unhandled state abbreviation" hypothesis is **refuted by the data**; `del` and `penn`
are the only survivors and they are the only two worth a line each.

### F6 — No territory or region gap for US

`guam` 0, `samoa` 0, `mariana` 0, `virgin` 0, `islands` 0, `zone` 0, `territory` 0,
`united` 0, `states` 0, `zip` 0, `postal` 0, `code` 0, `parish` 0. The hits for
`marshall` (9,430) and `canal` (7,451) are Marshall, WI / Canal Fulton — towns, not
territories. Administrative granularity is carried by `county` 281,125,
`township` 157,227, `cdp` 116,500, `borough` 17,520, `commonwealth` 3,603 — none of which
is a state, so none belongs in `US_STATES`.

## Interpretation

*Inference, clearly marked as such.*

1. **`US_STATES` is not the bottleneck; the ordinal table is.** F1 shows the state table
   already covers what the data contains. F3 shows 396,959 stranded ordinal tokens — an
   order of magnitude more affected tokens than the `del`/`penn` candidates combined
   (13,795). Prioritise F3.
2. **F3 is a matching-quality bug, not a cosmetic one.** "6th St" and "Sixth St" are the
   same address written two ways, and the scorer compares normalised tokens, so these
   rows fail to pair. Extending the table to 1–20 plus the spelled forms is a pure
   addition with no false-merge risk (ordinals are unambiguous in address context).
3. **F2 has a direct modelling consequence.** A blocker or feature that keys on the state
   *string* behaves completely differently on source 3 than on sources 1–2. If any
   learned component assumes a single US convention, it has effectively trained on one
   dialect and been scored on another. This is worth more attention than any single
   dictionary line, and it is invisible in the aggregate view — only the per-file split
   exposes it.
4. **F4 is a clean "no change needed".** `LEET` handles 100% of the leetspeak that
   actually appears. The only unmapped digit occurs in a non-leetspeak token.
5. **The `already_checked` refutations are not contradicted.** My evidence concerns US
   state handling only; I found nothing bearing on the France pin guard or the
   `FR_REGIONS` self-map loop, and I make no claim about either.

## Gaps

1. **Multi-word state keys are unmeasurable from this profile.** `build_profile.py` sets
   `TOKEN_RE = [a-z0-9]+` (line 28) and `ADDR_SPLIT = [,;]` (line 31), so a component
   `"New York"` is recorded as two separate tokens `new` (519,714) and `york` (384,608).
   There is **no bigram, component, or per-component field**. The 14 multi-word
   `US_STATES` keys — `new york`, `north carolina`, `district of columbia`,
   `west virginia`, `puerto rico`, etc. — therefore **cannot be audited at all** from
   this profile. I have not estimated them. This is the single most important gap.
2. **A `D.C.`-style defect is suspected but unquantified.** normalize.py:331 computes
   `ck = re.sub(r"[^a-z0-9& ]+", " ", c)`, which turns `"D.C."` into `"d c"` **with a
   space**, while `smap` holds `"dc"`. A dotted abbreviation would therefore fail to
   match. The profile has `dc` 35,681 but cannot tell dotted from undotted, because the
   token regex discards the dots. **Unresolvable without a component-level field.**
3. **Prefix truncation.** Each file keeps only the top 4,000 tokens; the rank-4000 count
   is 201 / 407 / 440 / 101 / 258 / 274. A token absent from all six lists has fewer than
   **101** occurrences in every file. So "0 occurrences" in F1/F5 means "< 101 per file",
   not literally zero.
4. **Hapax pruning.** `prune()` (line 45) deletes `count == 1` tokens every 8 chunks, so
   all singleton tokens are lost system-wide. Truly rare variants are invisible.
5. **No row-level co-occurrence.** The profile has no field joining a state token to the
   row it came from, so I cannot verify that `del` actually appears as a standalone
   address component rather than inside a street name — which is exactly what F5 needs to
   promote `del`/`penn` from LIKELY to CONFIRMED.
6. **No cross-source linkage field**, so F2's dialect split cannot be attributed to a
   specific generator process with evidence.

## Recommendations

1. **Extend `ADDR_CANON_COMMON` ordinals from 5 to 20** (highest priority; F3).
   Add `sixth→6th` ... `twentieth→20th`. Expected effect: closes 77.67% of the ordinal
   gap, ~33 fewer normalisation defects per 1,000 US address rows. Low risk.
2. **Add `"del": "de"` and `"penn": "pa"` to `US_STATES`** (F5, LIKELY). Expected effect:
   small but free — 13,795 additional address components normalise. Do not add the
   seventeen zero-count abbreviations; they are inert clutter.
3. **Do not extend `US_STATES` for territory/region names** (F6). No change needed.
4. **No change to `LEET`** (F4). Optionally delete the unreachable `@` and `$` keys and
   the dead `3`/`7` keys for clarity — cosmetic only, zero behavioural effect.
5. **Investigate F2 outside the dictionary** (highest *value*, not a dictionary edit).
   Before tuning any US state feature, confirm whether it was fitted on sources 1–2
   (codes) and applied to source 3 (names), or vice versa.
6. **Add a component-level field to `build_profile.py`** to close Gaps 1, 2 and 5 — a
   `comp_tokens` counter keyed on the whole comma-component would make the 14 multi-word
   state keys and the `del`/`penn` candidates directly measurable.
7. **Treat the aggregate code/name ratio ~1.44 as an artefact** (F2) and do not tune on
   it; always slice by source.

