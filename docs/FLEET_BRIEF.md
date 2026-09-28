
# ─────────────────────────────────────────────────────────────────────────────
# FLEET OPERATING BRIEF — read this before your work order.
# Working dir: C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)
# ─────────────────────────────────────────────────────────────────────────────

## The single most important lesson of this project

**Code inspection produced several WRONG high-confidence claims. Direct measurement
on the correct source population is mandatory.**

Concretely: an early review claimed "France loses postal codes" (FALSE — no country
in this dataset has a postal field; US 5-digit values are house numbers) and "FR_REGIONS
is too thin" (FALSE as a dictionary-gap claim). Both were plausible, both were wrong.
A third agent then produced a "100% of France rows resolve a state" figure that was
really a test_source1-only denominator covering 15.31% of French rows.

So: read code to form a hypothesis, then MEASURE it. Never ship a code-reading
conclusion as a finding. When you measure, state the DENOMINATOR and check that it
is the population you think it is — a number that sums exactly to one sub-file's row
count is the classic tell that you scoped it wrong.

## Hard constraints

- **READ-ONLY on `amazon_ml_2026_research/` and on `_upstream/`.** Never modify, move
  or delete anything there. `_upstream` is a pristine git clone at 8445b7f.
- **Read ONLY `analysis_out/profile/*.json`** for data. Each is 575–865 KB.
  **NEVER open the raw `*.tsv` files.** This machine has ~0.6 GB free RAM and a
  480 MB scan was already OOM-killed. It will kill you too.
- You MAY read `_upstream/src/*.py` to check what a dictionary actually does.
- You may write **exactly two files**: the `.md` deliverable named in your work
  order, and a `.json` sidecar in `analysis_out/findings/`.
- **No network access whatsoever.** The competition prohibits external data lookup,
  with immediate disqualification as the penalty. Everything must come from the data.
- Python is currently BROKEN on this box (the Python313 install has no `Lib\`).
  Use PowerShell for any computation. Do not waste turns trying to run `python`.

## Evidence standard

- Every figure traceable to a **named profile field**, with the arithmetic shown.
- If a field you need was not collected, **label it a gap**. Never invent a
  plausible-looking number. A plausible wrong number is worse than an admitted gap,
  because this output feeds real changes to a competition submission.
- Separate **what the data shows** from **what you are inferring**. Mark inferences.
- Propose entries as `CONFIRMED` / `LIKELY` / `SPECULATIVE`.
- If the profile contradicts a claim, **say so plainly**. Do not smooth it over.
- **"No defect found" is a valid and useful result.** Do not manufacture a
  recommendation to look productive.

## Read these before quoting any profile field

`build_profile.py` defines the exact semantics. Several fields are easy to
misread and one agent got a wrong conclusion by skipping this:

- `num_digits` counts digits in the **ADDRESS only**, not the name.
- `dig5` / `dig6` are **lookaround-guarded** — a digit inside a longer digit run
  does not count.
- All per-country stats are **totals across the whole slice**; derive rates by
  dividing by `rows`.
- `name_tokens` / `addr_tokens` are the **top 4000** per country. A token missing
  from them is not proof it is absent — the tail is truncated. Say "not in the top
  4000", never "does not occur".

## Already settled — do not re-derive any of this

- No country has a postal field. The `pin` guard should be left alone.
- `pin_eq` is dead (0.0% of rows). `alt_tset` is dead (nalt 0.6–1.0%).
- `US_STATES`, `IN_STATES`, `FR_REGIONS` mappings need **no** dictionary expansion.
- France blocking caps are **healthy**: 99.94% of 2,222,310 keys survive S1_MAXCAP=300.
- Address component **order** is not a problem (measured in D126, D127).
- The ligature deletion defect (`Cœur/Fœur/Sœur → ur`) and the inline-postcode city
  loss are confirmed but **negligible for scoring**.
- `ADDR_CANON_COMMON` empty mappings and the France `w/e/s` differences are
  behaviourally harmless / intentional.
- **Actionable and real:** `LEET` corrupts three classes of legitimate token —
  French ordinals (`3eme → eeme`, 1,111), **`24hr → 2ahr` (3,657 — the single
  largest corruption in the dataset)**, and English ordinals (`1st → lst`, 1,060).
  Genuine leetspeak still works (`c1ub → club`, `mais0n → maison`).
  **D087: a France-only guard fixes just 19.1% of this. The `24hr` and `1st` cases
  are US/India defects. Any guard on this shared code path must cover all three
  countries, must be token-anchored (`^…$`, or `b3er`/`p1er` get swallowed), and
  must EXEMPT rather than extend — 96.7% of mixed occurrences are correct leet.**

- **⚠️ RETRACTED — the French function-word finding was WRONG. Do not repeat it.**
  An earlier narrative claimed `ADDR_CANON_FR` lacks `de/la/du/des/le/les`, that
  these are 15.41% of test_s2 address-token mass (France ~42× the US rate), and
  that they "dilute IDF weighting for every French pair". **D119 measured this and
  it is overstated by ~37.5% and misdiagnosed as to mechanism:**
  - `normalize.py:333-335` matches a whole comma-component and then `continue`s, so
    the `de`/`la` inside `"Pays de la Loire"`, `"Hauts de France"`, `"Pas de Calais"`
    and `"Ile de France"` **never reach `atoks` at all**. The profile cannot see
    this because it flattens components. Real visible mass: **1,229,094 = 10.25%**;
    test_s2 moves **15.41% → 10.68%**.
  - The "dilutes IDF" mechanism is **self-cancelling**: `idf = ln(n/df)` with
    `n = 1,694,445` gives `idf(de) ≥ 0.4785` against a ceiling of 14.343 — already
    discounted ~28×.
  - The "pollutes blocking" mechanism **does not exist**: `keys.py:42` needs
    `len ≥ 3`, so `de/la/du/le` never become blocking keys; `des` is already in
    `ADDR_GENERIC`; `les` (3,685) exceeds `S1_MAXCAP=300`.

  **`ADDR_CANON_FR` has no material gap for this dataset.** See D119.

`FRANCE_FINDINGS.md` is shared and may be edited concurrently. **Append only**;
never rewrite a section you were not assigned.

## Write your files EARLY, and write a SKELETON before you investigate

Two agents in this project have now lost an entire run to a **timeout**, not an
auth error:

- An early run completed all its analysis and died on an auth error. It survived only
  because its files were already on disk.
- **run_00052 (D089) timed out having written NOTHING.** It was re-dispatched from
  scratch, losing ~15 minutes of work.

So the rule is stronger than "write early":

1. **In your first few tool calls, create a skeleton `.md` at your exact declared
   path** containing your task id, title, and a one-line placeholder headline.
   Update it in place as you learn more. A skeleton on disk beats a perfect answer
   in a dead session.
2. **Order your work cheapest-and-highest-value first**, so the headline lands
   before the budget runs out. If you can settle the main question cheaply, stop and
   bank it rather than chasing a long tail.
3. **A `.md` with a clear partial-deliverable note is an acceptable outcome.** The
   `.json` sidecar comes last and can be sacrificed. Say in the file that it is
   partial — a labelled partial result is useful; a silently incomplete one is not.

## Long runs are the main risk to this fleet, not auth

The runtime enforces a **concurrency cap of 2** (dispatch 10, but only 2 run at a
time; the rest queue). Individual runs also have a wall-clock limit. Two failure
modes have been observed and they are NOT the same:

| symptom | cause | what to do |
|---|---|---|
| fails in 1–2s, `Unauthorized` | expired/racing credential | re-authenticate, re-dispatch |
| runs 15–35 min, then "operation timed out", **no files written** | exceeded the run budget | re-dispatch with the write-early discipline above |

**Always write the skeleton first.** It converts the second failure mode from
"total loss" into "partial result".

## Validate your sidecar, and check your arithmetic

Three sidecars have shipped broken, and one shipped broken in a way only a human
check could catch:

- **D079** — an orphaned fragment appended AFTER the closing brace.
- **D127** — `bis_ter_asymmetry.arithmetic` never closed, so `fused_number_suffix`
  nested inside it with a duplicated tail dangling after the root object.
- **D073** — parsed perfectly, but the sidecar carried **stale numbers** that
  contradicted its own `.md` (1,204,739/71.10% vs the corrected 1,213,296/71.60%).
- **D120** — valid JSON, every field individually correct, but a derived **TOTAL
  disagreed with its own components** (headline said 6,192; the correct sum was
  5,192). **Parsing alone can never catch this.** It was found only by recomputing
  every arithmetic expression in the document from its stated inputs.

So, before you finish:

```powershell
# 1. does it parse?
try { $null=Get-Content $p -Raw|ConvertFrom-Json -ErrorAction Stop; 'OK' } catch { "INVALID: $($_.Exception.Message)" }

# 2. fleet-wide parse + arithmetic cross-check
powershell -NoProfile -ExecutionPolicy Bypass -File .\validate_sidecars.ps1

# 3. the one that actually matters: re-derive EVERY number in your .md
#    from its stated inputs, by hand, and diff against what you printed.
```

Step 3 is cheap and it is the only check that catches the D120 class. Do it.

**Also make sure every number in your sidecar MATCHES your `.md`.** If you revise a
figure, revise it in BOTH files, or state in the sidecar that the `.md` supersedes
it. A downstream aggregator reading only the sidecar will otherwise propagate a
number you have already retracted.

## Write your `.md` to the EXACT declared path

Three agents (D116, D117, D118) invented self-descriptive filenames
(`remaining_gaps_*.md`) where the work order declared `gaps_*.md`. The work was
fine, but linkage broke and the reconciler had to be patched to tolerate it. Copy
the `deliverable` field from your work order verbatim.

`FRANCE_FINDINGS.md` is shared and may be edited concurrently. **Append only**;
never rewrite a section you were not assigned.


## Report back

Reply with a 5-line summary: task id, headline, the single most important number,
whether you found any NEW defect, and your deliverable path.
