# P015 — [France] train_s3: shape, null rates, length distribution

**Status: COMPLETE (headline is negative, and the premise is confirmed invalid).**
**Agent:** b04c · **Family:** A-profile · **Profile input:** `analysis_out/profile/train_s3.json`
**Source of every number below:** the compact profile JSON. No raw TSV was opened.

---

## 1. HEADLINE — THE FRANCE SLICE IN train_s3 IS EMPTY

**There is no `France` key anywhere in `train_s3.json`.**

```
$ j.country_rows  ->  keys: US, India
$ j.by_country    ->  keys: US, India
$ j.name_tokens   ->  keys: US, India
$ j.addr_tokens   ->  keys: US, India
```

The field and the arithmetic:

| Quantity | Value |
|---|---|
| `train_s3.json` → `rows` (whole file) | **5,285,603** |
| `country_rows["US"]` | 3,170,056 |
| `country_rows["India"]` | 2,115,547 |
| `country_rows` keys present | `US`, `India` — **no `France`** |
| Sum of `country_rows` | 3,170,056 + 2,115,547 = **5,285,603 = `rows` exactly** |
| **France rows in train_s3** | **0** |
| **France share of train_s3** | **0 / 5,285,603 = 0.000000% — exactly 0** |

The sum closing on `rows` to the row is the denominator check the brief requires: the
country breakdown is complete, so France is not hiding inside it.

**Why absence means zero and not "not collected":** `build_profile.py:81-92` does
`country_rows[c] += 1` and `stats[c] = {...}` for **every** row unconditionally, on the
raw `country` column. A country with even one row would therefore get a key. The keys are
`dict(country_rows)` (line 139) / `stats` (line 138), so a zero-row country produces
**absence, not a zero entry**. Absence is the signature of zero rows.

## 2. CONSEQUENCE — EVERY FRANCE RATE IN THIS WORK ORDER IS 0/0, NOT 0%

The work order asks, per France: row count, empty-name rate, empty-address rate, mean name
length, mean address length, the name-length histogram, digit-in-name rate, comma-in-address
rate, and entity_id prefix validity. **None is computable.** Each is `f(France)/rows(France)`
with `rows(France) = 0`. They are **undefined (0/0), not 0%.**

I am explicitly declining to report them as "0%". "0% France empty-name rate in train_s3"
would be a fabricated figure: it asserts that zero France rows lacked names, whereas the
truth is that no France rows were observed. Same class of error as the retracted
"100% of France rows resolve a state" figure, in the opposite direction.

> ### ⚠️ THE TRAP, STATED PLAINLY
> **Any France rate computed against a train-file France denominator is meaningless.**
> That is exactly the error that produced the retracted figure earlier in this project.
> If you are handed "100%" (or "0%", or "50%") for any France **train** statistic, check
> the denominator first. If it came from a train file, it is a zero-denominator artifact.

## 3. WHY THIS IS THE EXPECTED AND CORRECT ANSWER (not a data gap)

France has **zero training rows in any of the three train files** — measured, not inferred.
Every file's `country_rows` sum closes exactly on its own `rows`, so no breakdown is partial:

| Profile file | `rows` | `country_rows` keys | France |
|---|---|---|---|
| `train_s1.json` | 2,206,821 | `US`, `India` | **absent** |
| `train_s2.json` | 5,034,616 | `India`, `US` | **absent** |
| `train_s3.json` | 5,285,603 | `US`, `India` | **absent** |
| `test_s1.json` | 1,732,544 | `US`, `France`, `India` | 259,452 |
| `test_s2.json` | 4,887,273 | `India`, `France`, `US` | 703,378 |
| `test_s3.json` | 5,082,316 | `India`, `France`, `US` | 731,615 |

Total train rows: 2,206,821 + 5,034,616 + 5,285,603 = **12,527,040, of which France = 0**.
Total France test rows: 259,452 + 703,378 + 731,615 = **1,694,445**.

The codebase already encodes this. Two independent confirmations, read from the pinned
clone at 8445b7f (read-only):

- `_upstream/src/crossfit.py:112` — `for c in ("US", "India"):` iterates the country list
  literally. **France is never trained on.** Same list again at `crossfit.py:122`.
- `_upstream/src/decoy_postfilter.py:17-18` — *"the country has no training labels
  (e.g. France in the test set)"*, which is why France gets a wider decoy-offset rule.

So "France has no training rows" is a **designed property of the challenge**, not a data
defect and not a profiling gap.

## 4. THE SUBSTANTIVE CONTENT OF train_s3 — STATE-REPRESENTATION ASYMMETRY (India)

The one real difference in this file is that **train_s3 writes Indian states as TWO-LETTER
CODES, while train_s1/s2 write them in full.** All figures below are from
`by_country.India.rows` as the denominator, using `addr_tokens.India` — which the profile
builder defines as `[token, count]` pairs of **token occurrences** (`build_profile.py:127`,
`140`), never rows.

I partitioned the 49 `IN_STATES` keys (`normalize.py:230-242`) into **49 full-name keys**
and the **37 distinct canonical codes** they map to. The two sets are **disjoint**
(`Compare-Object -IncludeEqual` returns empty), so code mass and full-name mass partition
cleanly and can be summed without double-counting.

| File | India rows | 2-letter CODE mass | FULL-NAME mass | code/1k rows | full/1k rows | code share of resolvable state mass |
|---|---|---|---|---|---|---|
| `train_s1` | 883,188 | 11,089 | 857,493 | 12.56 | 970.91 | **1.28%** |
| `train_s2` | 2,017,799 | 19,558 | 1,373,764 | 9.69 | 680.82 | **1.40%** |
| **`train_s3`** | **2,115,547** | **1,449,612** | **546,661** | **685.22** | **258.40** | **72.62%** |
| `test_s3` | 2,405,000 | 1,675,500 | 605,241 | 696.67 | 251.66 | 73.46% |

The single clearest pair, `mh` vs `maharashtra` (per 1k India rows, token occurrences):

| File | `mh` | `maharashtra` |
|---|---|---|
| `train_s1` | **2.38** | **217.83** |
| `train_s2` | 0.80 | 158.72 |
| **`train_s3`** | **151.93** | **11.38** |

`mh` jumps **63.8×** from s1 to s3; `maharashtra` collapses **19.1×**. This independently
reproduces the D118 figures (151.93 / 11.38 in s3, 2.38 / 217.83 in s1) from the same
profile field.

**Code mass is almost entirely an s3 phenomenon.** Summing the 37 codes over all six
profiles gives 3,188,831 occurrences, of which train_s3 + test_s3 hold
**3,125,112 = 98.00%** (train_s3 45.46%, test_s3 52.54%; s1 0.35%, s2 0.61%, test_s1 0.32%,
test_s2 0.72%). India rows in train_s3 + test_s3 = 2,115,547 + 2,405,000 = **4,520,547**,
matching the D118 row count.

### The self-map loop is what makes s3 resolve a state at all

`normalize.py:252-254` — three lines, quoted from the pinned clone:

```python
251: # abbreviations are canonical themselves
252: for _m in (US_STATES, IN_STATES):
253:     for _v in list(_m.values()):
254:         _m.setdefault(_v, _v)
```

Read with `STATE_MAPS = {"US": US_STATES, "India": IN_STATES, "France": FR_REGIONS}`
(`normalize.py:250`) and the component matcher at `normalize.py:333-335`:

```python
333:         if ck in smap:
334:             state = smap[ck]
335:             continue
```

Without line 254 the 37 codes are **not keys** of `IN_STATES`, so a `mh` component would
miss `ck in smap`, fall through to the token loop, and be emitted as a bare blocking/
feature token with `state = ""`. The loop is therefore **load-bearing for the ~4.52M
Indian rows in s3**, and near-inert for s1/s2 (1.28% / 1.40% code share).

`FR_REGIONS` is **not** in the loop tuple at line 252. That is the already-settled
"zero measurable effect" item in my work order — all 14 canonical values (`hdf`, `naq`,
`pdl`, `idf`) occur 0 times as input, because s3-style abbreviation is an India/US
convention here. I make no new claim about it.

## 5. FULL SHAPE STATISTICS — FOR THE TWO COUNTRIES THAT EXIST

Since the France cell is empty, here are the requested statistics for the populations that
are actually in `train_s3`, so the shape of the file is on record. Every rate is
`field / by_country.<c>.rows`.

| Statistic | US | India |
|---|---|---|
| `rows` | 3,170,056 | 2,115,547 |
| share of file (`rows/5,285,603`) | 59.9753% | 40.0247% |
| `name_empty` | **0** (0.0000%) | **0** (0.0000%) |
| `addr_empty` | 110,968 (**3.5005%**) | 64,948 (**3.0700%**) |
| mean name length (`name_chars/rows`) | **23.9772** chars | **27.0376** chars |
| mean address length (`addr_chars/rows`) | **38.4452** chars | **59.1055** chars |
| `has_digit_name` | 199,652 (**6.2981%**) | 71,195 (**3.3653%**) |
| `has_comma` | 3,059,088 (**96.4995%**) | 2,050,598 (**96.9299%**) |
| `prefix_bad` (entity_id not starting `S3-`) | **0** | **0** |
| `alpha_only_addr` | 164,957 (5.2036%) | 145,433 (6.8745%) |
| `dig5` / row (guarded) | 0.10780 | 0.01055 |
| `dig6` / row (guarded) | 0.01335 | 0.00019 |
| `name_tokens` (occurrences) | 11,522,038 | 7,032,501 |
| `num_digits` (ADDRESS digits only) | 12,614,249 | 7,979,194 |

**Name-length histogram** (`len_hist`, key = `len(name)//10*10`, so "20" = 20-29 chars).
Both sum exactly to `rows` — verified, `len_hist_sum == rows` is `True` for both.

| Bin | US count | US % | India count | India % |
|---|---|---|---|---|
| 0-9 | 117,192 | 3.697% | 64,887 | 3.067% |
| 10-19 | 968,304 | 30.545% | 405,990 | 19.191% |
| 20-29 | 1,276,652 | 40.272% | 799,604 | 37.797% |
| 30-39 | 628,392 | 19.823% | 645,037 | 30.490% |
| 40-49 | 149,220 | 4.707% | 169,414 | 8.008% |
| 50-59 | 26,607 | 0.839% | 26,650 | 1.260% |
| 60-69 | 3,417 | 0.108% | 3,480 | 0.164% |
| 70-79 | 259 | 0.008% | 409 | 0.019% |
| 80-89 | 13 | 0.000% | 57 | 0.003% |
| 90-99 | 0 | 0.000% | 16 | 0.001% |
| 100-109 | 0 | 0.000% | 2 | 0.000% |
| 110-119 | 0 | 0.000% | 0 | 0.000% |
| 120-129 | 0 | 0.000% | 1 | 0.000% |
| **sum** | **3,170,056** | **100%** | **2,115,547** | **100%** |

**Reading the 0-9 bin correctly:** `name_empty = 0` for both countries, so bin "0" contains
only names of length 1-9 — it is a **length band, not an emptiness measure**. It is
numerically close to but *not equal to* `addr_empty` (US 117,192 vs 110,968; India 64,887
vs 64,948), and the two must not be conflated. The only exact reconciliation here is that
each `len_hist` sums to its own `rows`, verified `True` for both.

## 6. IS THE SLICE LARGE ENOUGH TO CONCLUDE FROM?

**The France-train question is undefined, not answered negatively.** There is no slice, so
there is no sample size and no confidence interval. No France train conclusion can be drawn
at any n, because n = 0.

For the populations that *are* present the sample sizes are overwhelming. Standard errors
on the headline rates: US digit-in-name 6.2981% at n=3,170,056 gives
`sqrt(0.062981*0.937019/3170056)` = **0.0136pp**; India's 3.3653% at n=2,115,547 gives
**0.0124pp**. The state-representation asymmetry is not a sampling question at all: the
72.62% vs 1.28% code share is a **57× separation** on occurrences in the millions.

## 7. NEW DEFECTS FOUND

**None.** `prefix_bad = 0` and `name_empty = 0` for both countries, both `len_hist` bin sets
reconcile exactly to `rows`, and the France-zero-train condition is already known and
already handled in code. Per the evidence standard, "no defect found" is the result; I am
not manufacturing a recommendation to look productive.

The self-map loop at `normalize.py:252-254` is correctly scoped for the data as it stands
(US + India both use abbreviations; France does not). I see no reason to change it.

## 8. GAPS AND LIMITS

- **Not measured / undefined:** every France-train statistic in the work order. A gap in
  the *data*, unfixable from the provided files. This is not a gap in effort.
- **Not measurable from the profile:** whether a state code resolves via the
  whole-component match at `normalize.py:333`. `build_profile.py:126-127` **flattens**
  address components (`ADDR_SPLIT = [,;]` then per-component `findall`), so the profile
  cannot tell whether `mh` appeared as a standalone component (resolves) or glued to a
  postcode inside one component (does not resolve). **Any per-file India state-resolution
  rate is therefore not computable from these artifacts** — the same limitation that made
  the France 71.10%/2.56% figures unreconcilable.
- **`name_tokens` / `addr_tokens` are TOP 4000 per country** and the counters are
  **periodically pruned** (`prune()`, `PRUNE_EVERY=8`, `build_profile.py:45-48`, `128-133`).
  Token counts are **lower bounds with a pruned tail**, and a token missing from the list
  means "**not in the top 4000**", never "does not occur". The code-vs-full-name split in
  §4 therefore *understates* both masses by an unknown amount — but since the missing
  tail is dominated by ordinary address words, not by state names, the 72.62% vs 1.28%
  separation is robust. *(This robustness is an INFERENCE, not a measurement.)*
- **`num_digits` counts digits in the ADDRESS only** (`build_profile.py:114`), not the name.
  I used the separate ROW counter `has_digit_name` (lines 106-107) for the digit-in-name
  figure. `dig5`/`dig6` are lookaround-guarded (`(?<!\d)\d{5}(?!\d)`, lines 29-30), so a
  digit inside a longer run does not count.
- I did not re-derive anything in the brief's ALREADY RULED OUT list, and I do not repeat
  the RETRACTED French function-word finding.

## 9. HOW TO REPRODUCE (PowerShell; Python is broken on this box)

```powershell
$b='analysis_out/profile'
$j = Get-Content "$b\train_s3.json" -Raw | ConvertFrom-Json
$j.rows                                   # 5285603
$j.country_rows | ConvertTo-Json -Compress  # {"US":3170056,"India":2115547}  <- no France
$j.by_country.PSObject.Properties.Name      # US, India
# addr_tokens.India is a JSON array of [token,count] pairs (not a property bag)
$d=@{}; foreach($p in $j.addr_tokens.India){ $d[[string]$p[0]]=[double]$p[1] }
$d['mh']          # 321405
$d['maharashtra'] # 24074
1000*$d['mh']/$j.by_country.India.rows          # 151.93 per 1k
```
