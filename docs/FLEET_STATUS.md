# FLEET STATUS AND HANDOFF — read this first

**Written:** 2026-09-27 · **Working dir:** `C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)`

> **If you only read two things:** §1 (the fleet is blocked on credits, here's the
> config fix that was needed) and **§7 (France has ZERO training rows — this
> reframes the entire project and is not a dictionary finding).**


---

## 1. THE FLEET IS CURRENTLY BLOCKED. Credits are exhausted.

**Every sub-agent run now fails within 1–7 seconds with:**

```
Insufficient balance. Your Cline Credits balance is $0.01
```

A minimal probe (`spawn_agent`, one line, no tools) returns the same error and
consumes **0 input / 0 output tokens** — the request is rejected *before* any
inference happens. This is a **billing limit, not a configuration problem.**

### The model configuration WAS wrong, and I fixed it

You were right that "nothing else will work." The cause was in
`C:\Users\pvish\.cline\data\settings\providers.json` line 3:

```diff
-  "lastUsedProvider": "openai-codex",
+  "lastUsedProvider": "cline",
```

`openai-codex` was the active provider, while the Space Bunny Alpha model lives
under the `cline` provider key. Verified after the change:

| field | value |
|---|---|
| `lastUsedProvider` | `cline` |
| `providers.cline.settings.model` | **`stealth/space-bunny-alpha`** |
| `providers.cline.settings.reasoning` | enabled, effort `xhigh` |
| token source | `oauth` (has a refresh token; it auto-refreshed mid-session) |

**That pin is correct and should stay.** But the `cline` provider bills against
Cline Credits, and the balance is exhausted. Fixing the model selection got the
fleet working — it then ran ~20 successful tasks — until the credit ran out.

**To resume: top up Cline Credits.** No other change is needed. Do not switch
providers; `openai-codex` is the one you told me not to use.

---

## 2. Where the work stands

| | |
|---|---|
| Roster | **128** tasks (task IDs are now **immutable**) |
| Delivered | **47** |
| Outstanding | **81**, all queued in `analysis_out/dispatch_plan.json` |
| Orphan deliverables | 5 (work done, work orders lost in an earlier renumbering — **not** re-dispatched) |
| Sidecar validity | **53 / 53 valid, 0 invalid** |
| `.md` deliverables | 52 |
| `_upstream/` clone | **pristine at `8445b7f`**, 0 tracked files modified |

### State files to trust

| file | purpose |
|---|---|
| `analysis_out/roster_manifest.json` | frozen roster + per-task DELIVERED/OUTSTANDING, hash-locked |
| `analysis_out/dispatch_plan.json` | the 81 outstanding tasks in 9 batches of ≤10 |
| `FLEET_BRIEF.md` | **the brief every agent reads first.** Constraints, evidence standard, settled findings, 3 retractions |
| `FRANCE_FINDINGS.md` | 800+ lines, append-only, sections A1–A13 |

### The three scripts that matter

```powershell
# reconcile + replan  (run this first after any top-up)
powershell -NoProfile -ExecutionPolicy Bypass -File .\freeze_roster.ps1

# validate every sidecar: parse + arithmetic cross-check
powershell -NoProfile -ExecutionPolicy Bypass -File .\validate_sidecars.ps1

# verify the LEET fix without Python (73 assertions)
powershell -NoProfile -ExecutionPolicy Bypass -File .\verify_leet_guard.ps1
```


---

## Python interpreter — RESOLVED. Use this one.

```powershell
$py = 'C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)\.venv\Scripts\python.exe'
```

- **Python 3.11.15** — the exact version `_upstream/requirements.txt` says it was
  tested with.
- All five pinned requirements installed and verified: `polars 1.44.2`,
  `pyarrow 25.0.1`, `numpy 2.4.4`, `lightgbm 4.7.0`, `rapidfuzz 3.14.6`.

**Why the default `python` still fails, and why that is not a problem.**
`python`, `py` and `python3` all resolve to the 0-byte WindowsApps alias stub or
to `C:\Program Files\Python313`, which has **no `Lib\` tree**. Several venvs on
this box (`auth\env`, `logic\env`, `newtool\tools`, `python-sdk-1\venv`, `New
folder (9)\.venv`) point at `AppData\Local\Programs\Python\Python3xx` bases that
have been **deleted**, so they fail with `No Python at ...`.

**Two venvs survive** because they are `uv`-managed and point at
`AppData\Roaming\uv\python\`, which still exists:
- `C:\Users\pvish\major101\.venv` → 3.11.15
- `C:\Users\pvish\Desktop\pokemon-workspace\.venv` → 3.12.13

The project `.venv` above was created from the `uv` 3.11.15 base, so it does not
depend on any deleted install. There is **no venv named "hermes"** on this box —
`.hermes`, `.hermes-bridge`, `ECC\.hermes`, `.agency-agents\integrations\hermes`
and `.local\state\hermes` all exist, but none contains a Python environment.

### Verify the environment any time

```powershell
& .\.venv\Scripts\python.exe env_report.py     # interpreter + all 5 requirements
```

### Note for the shell harness

The PowerShell tool **swallows Python's stderr**, so `python -c "..."` shows only
a truncated `Traceback`. Redirect through `cmd` to see real errors:

```powershell
cmd /c ".\.venv\Scripts\python.exe your_script.py > out.txt 2>&1"; Get-Content out.txt
```

A `NativeCommandError` from PowerShell is **not** evidence the script failed —
`test_leet_ordinal_guard.py` appeared to fail while actually reporting `OK`.

---

## 3. The one code change: LEET ordinal guard — VERIFIED IN REAL PYTHON

`_upstream/` was **not** modified. The fix lives in `patch_upstream/` (a copy).

**Defect:** `_name_tokens` applies `LEET` to any token containing both a letter and
a digit, destroying three classes of legitimate token:

| class | becomes | occurrences | caught by the original French-only guard? |
|---|---|---|---|
| French ordinals `3eme`/`1er`/`3e` | `eeme`/`ler`/`ee` | 1,111 | yes |
| **`24hr`** | **`2ahr`** | **3,657** | **NO** |
| English ordinals `1st` | `lst` | 1,060 (US 679 + India 381) | **NO** |

Total 5,828. A French-suffix-only guard fixed just **19.1%** — `24hr` is the
single largest corruption in the dataset and is a *US* defect.

**The fix** (2 lines changed + one regex, `patch_upstream/src/normalize.py`):

```python
_LEET_GUARD_RE = re.compile(
    r"^(?:\d+(?:er|ere|eme|e)|\d+(?:st|nd|rd|th)|\d+hr)$")
...
if (any(c.isalpha() for c in t) and any(c.isdigit() for c in t)
        and not _LEET_GUARD_RE.match(t)):
    t = t.translate(LEET)
```

Three design points that could each have gone wrong:
- **Call site, not the table.** `str.maketrans` is a character map and structurally
  cannot express "skip this token". Confirmed independently by D087.
- **Not country-scoped.** `normalize_name` has no `country` parameter
  (normalize.py:285), so a country guard is impossible *and* would be the wrong
  shape — `24hr`/`1st` are US/India defects.
- **Token-anchored (`^…$`).** A looser `\d+[er]` would swallow `b3er`, `p1er`,
  `x1st` and silently disable genuine leetspeak.

**Verification — now run in real Python, three independent ways:**

| check | command | result |
|---|---|---|
| Authoritative unittest suite | `.\.venv\Scripts\python.exe patch_upstream\src\test_leet_ordinal_guard.py` | **10/10 tests OK** |
| Real-module integration (imports the actual `normalize.py`) | `.\.venv\Scripts\python.exe verify_leet_real_module.py` | **50/50 checks, exit 0** |
| Python-free .NET-regex harness | `.\verify_leet_guard.ps1` | **73/73** |

The earlier **`.NET-regex` caveat is now closed** — it existed only because Python
was unavailable. The guard is confirmed against the real pipeline code, so "the
harness validates the pattern but not Python's engine" no longer applies.
(`verify_leet_real_module.py` needed one correction: `4EME`→`4eme` and
`24HR`→`24hr` are correct lowercasing by `normalize.py:273`, and pure-digit or
pure-alpha tokens never enter the LEET branch at all. My first version of that
script mis-scored those four — the script was wrong, not the guard.)

**Independent external validation:** D088 enumerated the entire US mixed-token
population (133 types / 90,100 occurrences) and found the guard **wrongly exempts
0 of 131 legitimate US leet types**, and that no fourth US class exists. D087
separately proved **every LEET key is load-bearing** (removing `1` to save `1st`
would break `de1hi` 1,674, `denta1` 1,652, `techno1ogies` 1,288 + 82 types), so

---

## 4. Three retractions — the recurring failure mode of this project

Read these before trusting any earlier note. Full history in `FRANCE_FINDINGS.md`
(A1–A13) and `FLEET_BRIEF.md`.

1. **"France loses postal codes" — FALSE.** No country in this dataset has a
   postal field. French addresses carry house numbers
   ("175 Boulevard du President Franklin Roosevelt"). US 5-digit values are house
   numbers too.
2. **"FR_REGIONS is too thin" — REFUTED as a dictionary gap.** Three independent
   agents (D070, D116, D128) agree: **do not extend it.** A maximal 49-key
   gazetteer moves the bound by ≤2.64pp, and the provably-incremental token-disjoint
   subset by only 0.80pp. Worse, **D116 showed extending it would actively hurt**:
   an unmatched token is *live IDF feature mass* (`features.py:129`), and adding a
   key makes `normalize.py:335` `continue` and **delete** it.
3. **"French function words are 15.41% of test_s2 and dilute IDF" — RETRACTED by
   D119.** Overstated ~37.5% (real: **10.25%** pooled, **10.68%** for s2) because
   the profile flattens components and `normalize.py:333-335` `continue`s past
   matched region components so their `de`/`la` never reach `atoks`. The IDF
   mechanism is **self-cancelling** (`idf(de) ≥ 0.4785` vs a 14.343 ceiling).

**Two tooling traps that caused these**, now standing checks in the brief:
- A **`test_source1`-only denominator** presented as a France-wide rate. s1 is
  15.31% of French test rows.
- A **component-flattening profile** (`build_profile.py`) — a token count from it
  is *not* a pipeline-visible quantity. Trace to consuming code first.

---

## 5. The one change that would actually move France

A **city→region table**, not a dictionary extension:

- `bordeaux` 277,474 · `nantes` 238,748 · `lille` 221,585 — **top 3 ≈ 43.7% of
  every French test file**, and they carry no administrative token at all.
- `paris` is only 2,263. **The provinces are the mass, not Paris.**
- s1 encodes geography with region names; **s2/s3 use departments/city names**
  (dept density 6.8% → ~38%).

**This is not derivable from the current profile**, which stores marginal token
counts with no co-occurrence. The correct next instrumentation job is a
**component-level re-scan of France** — which would also convert the current
dictionary *bounds* into point estimates, and let a city→region mapping be built.

---

## 6. How to resume

```powershell
cd 'C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)'
powershell -NoProfile -ExecutionPolicy Bypass -File .\freeze_roster.ps1   # reconcile
```

Then dispatch `analysis_out/dispatch_plan.json` batch 1 (10 tasks), **10 at a
time** — the runtime only runs **2 concurrently**, the rest queue, so expect the
batch to drain over ~40–60 min.

Give every agent a role prompt that says **read `FLEET_BRIEF.md` first**, keeps it
short (the old teammate ballooned to 459K chars from inlining a task JSON), and
demands the **skeleton-file-first** discipline below.

### Two operational lessons that cost real work

| failure | symptom | fix now in the brief |
|---|---|---|
| **auth** | fails in 1–2s, `Unauthorized` | re-authenticate, re-dispatch |
| **timeout** | runs 15–35 min, then "operation timed out", **no files written** (cost run_00052 / D089 ~15 min) | write a skeleton `.md` in the first few tool calls, order work cheapest-and-highest-value first, accept a labelled partial deliverable |

And the data-integrity lesson: **parsing a sidecar is not enough.** Four shipped
broken — D079 (orphaned trailing fragment), D127 (unclosed object), D073
(parseable but *stale* numbers contradicting its own `.md`), and D120 (valid JSON,
every field correct, but a derived **TOTAL disagreed with its components**).
Only recomputing every arithmetic expression catches the last class.
`validate_sidecars.ps1` now does a parse check *and* a `total`-vs-sum
cross-check; it also needs a human to adjudicate, since percentages and
overlapping category sets legitimately don't sum.

deleting digits was never a valid alternative.

**Honest impact:** this is a **correctness fix, not a score fix.** ~5,828 token
occurrences against 1.7M France test rows. Do not expect measurable F0.5 movement.

**Still unrun: the full pipeline.** The blocker is now **RAM, not Python** — free
RAM is **0.54 GB** and a 480 MB scan was already OOM-killed on this box. Free disk
is ~4.5 GB, which is fine. Any end-to-end run needs Colab or a bigger machine.

---

## 7. The biggest finding, and it is not a dictionary finding

**France has ZERO training rows.** `country_rows` in `train_s1/s2/s3.json` contains
only `US` and `India`; there is no `France` key. Consequently
`_upstream/src/crossfit.py:112` iterates `for c in ("US", "India")` — the
cross-fitted LightGBM ranker is **fit without a single French label** and then
applied to 1,694,445 French test rows. The codebase already knows this:
`decoy_postfilter.py:17-18` comments *"the country has no training labels (e.g.
France in the test set)"*.

**This dwarfs every dictionary question.** For France the binding constraint is
missing labels, not missing entries. Two independent agents (D116, P013/P014/P015)
confirmed it.

**`python` is BROKEN on this box** — `C:\Program Files\Python313` has no `Lib\`
tree and every venv points at a deleted base interpreter. All tooling is
PowerShell. Repairing Python is worth doing before the Colab work.
