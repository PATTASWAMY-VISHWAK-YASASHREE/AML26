# SUBMISSION CONTRACT - mechanically checkable checklist

**Task:** `task_0004` (compliance/contracts audit)
**Date:** 2026-09-27
**Authoritative validator:** `amazon_ml_2026_research/student_resource/utils/validate_submission.py`
sha256 `D96E3B26A6F05FB832D33AFEFAF407095B98A4E4AF0FD9512523B6557F80F42A` (14,849 bytes)
**Verdict:** every claim below is backed by file+line AND, where marked [RUN], by an actual
execution of the real validator.

> **Scope caveat (preserve this).** No network access was used. The live Amazon portal and the real
> scorer were **not** reached. Everything below is verified against the *local* student_resource copy
> only. `amazon_ml_challenge_2026_verified_handoff.md` states the technical contract is
> "provenance not portal-verified" (L7, L11). A PASS here means "passes the local validator", not
> "accepted by Amazon".

---

## 0. HEADLINE - the singular/plural ambiguity is RESOLVED

**Use the PLURAL forms. The brief's singular table is wrong.**

```
source1_entity_id<TAB>matched_entity_ids
source1_entity_id<TAB>candidate_entity_ids
```

Exactly one TAB between the two fields, lowercase, no quotes, no trailing spaces.

### Evidence

| # | Source | Line(s) | Content |
|---|---|---|---|
| E1 | `utils/validate_submission.py` | **48** | `MATCHING_HEADER = ["source1_entity_id", "matched_entity_ids"]` |
| E2 | `utils/validate_submission.py` | **49** | `CANDIDATE_HEADER = ["source1_entity_id", "candidate_entity_ids"]` |
| E3 | `utils/validate_submission.py` | **124-129** | `if cols != expected_header:` -> hard **error**, `return None`. Exact list equality, no aliasing, no fallback. |
| E4 | `utils/validate_submission.py` | **123** | `cols = [c.strip().lower() for c in header.rstrip("\n").split(DELIM)]` - case-insensitive after strip |
| E5 | `utils/validate_submission.py` | **262** | matching file is validated against `MATCHING_HEADER` |
| E6 | `utils/validate_submission.py` | **271** | candidate file is validated against `CANDIDATE_HEADER` |
| E7 | `README.md` | **79-80, 85-88** | column table + example use `matched_entity_ids` |
| E8 | `README.md` | **114-115, 120-123** | column table + example use `candidate_entity_ids` |
| E9 | `README.md` | **33-34** | the **training label file** uses `source1_entity_id` / `matched_entity_ids` |
| E10 | `README.md` | **183, 185** | Constraints prose uses the **plural** `matched_entity_ids` |
| E11 | handoff `.md` | **15, 17-18** | "exact headers `source1_entity_id` and `matched_entity_ids`" / "`candidate_entity_ids`" |
| E12 | handoff `.md` | L37 | brief instructs: "The validator and sample are authoritative. Do not guess the header." |
| E13 | `dataset/train/train_ground_truth.tsv` | bytes 0-37 | **actual file bytes**: `source1_entity_id` TAB `matched_entity_ids` LF - the org's own label schema is plural |

**SAMPLE OUTPUT FILE: DOES NOT EXIST.** `student_resource/` contains only `dataset/`, `utils/`,
`README.md` and `Documentation_template.md` (full recursive listing performed). There is **no**
`output/`, `sample_submission/`, or `sample*.tsv` anywhere under `student_resource/`. So the sample
could not corroborate directly - but the **training ground-truth file (E13), which is the same schema
the submission mirrors, is present and is plural.** No guessing was required.

**[RUN] - decisive execution.** A synthetic 3-S1 fixture was built and the real validator was run
against both spellings:

```
PLURAL   -> PASS - no blocking issues found. Safe to submit.             exit=0
SINGULAR -> FAIL - 1 issue(s) to fix before submitting:
  1. matching_SINGULAR.tsv: unexpected header ['source1_entity_id', 'matched_entity_id'].
     Expected exactly ['source1_entity_id', 'matched_entity_ids'] (tab-separated).   exit=1
```

**Conclusion.** The singular spelling in the brief's PDF table is an extraction/typo artifact. Three
independent lines of evidence (validator constants E1/E2, the org's own ground-truth file E13, and
the brief's *own* constraints prose E10) all say plural. `README.md` L182 states "Submissions that
fail validation will not be evaluated" - a singular header is a hard reject.

> **DISCREPANCY - flag to the team.** The local validator is **14,849 bytes**. The handoff (L25)
> describes the public mirror as **13,687 bytes** and states at L33 that it "treats a missing
> `candidate_pairs.tsv` as a warning". The local copy is **stricter** (it makes a missing candidate
> file a hard error, L275-279). So the local validator is a *newer/different revision* than the
> community copy the handoff audited. Satisfying the local validator therefore does **not** guarantee
> satisfying the portal's. Re-confirm if/when the official validator surfaces.

---

## 1. Headers - exact byte-level contract

- [ ] **1.1** `output/matching_results.tsv` line 1 is exactly `source1_entity_id` TAB
      `matched_entity_ids` (12 + 1 + 17 = 30 chars + terminator).
      *Source: validator L48, L124, L262. [RUN] verified True on the real file.*
- [ ] **1.2** `output/candidate_pairs.tsv` line 1 is exactly `source1_entity_id` TAB
      `candidate_entity_ids` (12 + 1 + 18 = 31 chars + terminator).
      *Source: validator L49, L124, L271. [RUN] verified True on the real file.*
- [ ] **1.3** A header row **is present** in both files, and it is the **only** header. It is
      required, not optional: the validator reads line 1 as the header unconditionally
      (`header = f.readline()`, L112) and errors on mismatch; `read_ids()` skips one header (L58).
      A headerless file fails 1.1/1.2 - its first data row gets compared against the expected header.
- [ ] **1.4** Header case is **forgiving but don't rely on it**: comparison lowercases (L123), so
      `SOURCE1_ENTITY_ID` TAB `MATCHED_ENTITY_IDS` [RUN] -> PASS. That is validator leniency, not a
      guaranteed scorer leniency. **Write lowercase.**
- [ ] **1.5** **No UTF-8 BOM.** Python's `open(encoding="utf-8")` does not strip BOM, so the BOM
      glues onto field 0. [RUN] with a real BOM -> FAIL
      `unexpected header ['\ufeffsource1_entity_id', ...]`.
- [ ] **1.6** No leading/trailing whitespace around header cells (it would be stripped, L123, but do
      not rely on it).

## 2. Rows, delimiter, quoting, terminator, encoding

- [ ] **2.1** **Delimiter is a single TAB** (0x09), never a comma. *Source: L46 `DELIM = "\t"`.*
      [RUN] a comma-separated `.tsv` -> FAIL "header has no TAB but contains commas" (L116-122).
- [ ] **2.2** **Exactly two tab-separated fields per data row.** A third column -> FAIL
      "malformed row (too many tab-separated columns)" (L147-156). [RUN] confirmed.
- [ ] **2.3** A data row with **no tab at all** -> FAIL "malformed row (no tab)" (L134-140).
      [RUN] confirmed.
- [ ] **2.4** **ID lists are comma-separated with NO quoting.** The ID list separator is `,` (L159),
      not a tab. The parser does **not** implement CSV quoting - it does `line.partition("\t")` then
      `rest.split(",")` (L132, L159). A CSV-quoted field is therefore read as literal junk IDs.
      [RUN] `"S2-1,S3-1"` -> FAIL `contains IDs without an S2-/S3- prefix: "S2-1` (the quote
      character survives into the ID). *Source: README L82 "ID lists separated by commas with no
      quoting".*
- [ ] **2.5** **No double-quote character anywhere** in either file. [RUN] the real `output/` files
      contain 0 double-quote bytes.
- [ ] **2.6** **Line terminator: LF or CRLF are both accepted** by the validator (it `rstrip("\n")`
      at L123/L159 and `.strip()`s each token at L159, absorbing `\r`).
      [RUN] a fully-CRLF file -> PASS. **Ship LF** (matches the dataset and the polars writer).
- [ ] **2.7** **No blank lines** inside the file. `read_ids` skips blanks (L59) and the row loop
      tolerates a blank line only because it has no tab and no content (L134-135). Emit none.
- [ ] **2.8** **Encoding is UTF-8, plain text.** A `UnicodeDecodeError` is caught and reported as a
      hard failure (L342-352). [RUN] Latin-1 bytes -> FAIL "A file is not valid UTF-8 text".
      Not a `.gz`/`.xlsx`/`.parquet` renamed to `.tsv`.
- [ ] **2.9** A trailing newline is not required; the writer produces one. Not a rejection criterion.

## 3. Exactly-once coverage of every test S1 entity

The required S1 set is read from `dataset/test/test_source1.tsv` (L231-235), first column,
header skipped. **The test set contains 1,732,544 S1 entities** ([RUN], streamed: 1,732,544 data
rows, 1,732,544 unique IDs).

- [ ] **3.1** `output/matching_results.tsv` has **exactly 1,732,544 data rows** (1,732,545 lines
      including the header) - or, more robustly, exactly 1,732,544 data rows, zero missing, zero extra.
- [ ] **3.2** **Every** test S1 `entity_id` appears **exactly once**. Missing -> FAIL "required S1
      entity(ies) missing" (L204-208). [RUN] confirmed.
- [ ] **3.3** **No extra S1 rows.** An ID not in the test set -> FAIL "row(s) using an S1 ID that is
      not in the test set" (L209-212). [RUN] confirmed.
- [ ] **3.4** **No duplicate `source1_entity_id` rows.** -> FAIL "duplicate source1_entity_id row(s)"
      (L180-184, detected L143-144). [RUN] confirmed.
- [ ] **3.5** **Singletons MUST still get a row, with an empty second field.** A singleton row is
      literally `S1-12345` TAB LF - tab present, nothing after it. This is NOT an omission; omitting
      the row fails 3.2. [RUN] an all-empty 3-row file -> PASS.
- [ ] **3.6** **All 1,732,544 requirements apply to `candidate_pairs.tsv` identically.** The same
      `validate_id_list_file()` enforces them (L270-273). `required - seen` and `seen - required`
      are checked for the candidate file too.
- [ ] **3.7** No duplicate IDs **within** one list -> FAIL "repeated ID inside a {col} list"
      (L185-189, L165-166). [RUN] confirmed.
- [ ] **3.8** Only `S2-`/`S3-` IDs in the list. An `S1-` ID -> FAIL "self-matches"
      (L190-194, L170-171). [RUN] confirmed. Any other prefix -> FAIL "without an S2-/S3- prefix"
      (L195-198, L172-173).
- [ ] **3.9** [RUN] **single cheapest proof of 3.1-3.6**: three-way lockstep diff. Compare the S1
      column of both output files against `test_source1.tsv`, row for row. Result on the real
      `output/`: `1,732,544` rows, **0** rows differing, **0** missing, **0** extra, in both files.

---

## 4. The metric

- [ ] **4.1** Metric is **F-beta with beta = 0.5**, `F = (1.25*P*R)/(0.25*P + R)`.
      **Source: `README.md` L190-196 (the brief), NOT the validator.** The validator explicitly never
      computes a score (`README` L145; validator docstring L9 "never computes your score").
      Confirmed by inspection: the validator contains no precision/recall/F-beta code at all.
- [ ] **4.2** It is a **macro average over per-S1-entity F**, averaged across **all** S1 entities in
      the evaluation set. *Source: README L198.*
- [ ] **4.3** **True-empty (singleton) S1 entities are INCLUDED** in the average and are worth a full
      point: **1.0** if you predict an empty list, **0.0** if you predict any match. *Source: README L200.*
- [ ] **4.4** Consequence, operationally: predicting "no match" for *everything* is not free - it scores
      1.0 on every true singleton and 0.0 on every true match. Over-merging is punished twice
      (precision loss + singleton zero). *Source: README L200, L202, L262.*
- [ ] **4.5** Worked example to reproduce in your own harness - *Source: README L204-209*:
      pred `[S2-00047, S2-00193, S3-00812]`, truth `[S2-00047, S3-00812]` ->
      P=2/3, R=1.0, F0.5 = (1.25*0.667*1.0)/(0.25*0.667+1.0) = **0.714**.
- [ ] **4.6** Public/private split is applied **during scoring**; you submit the **full** test set in
      both cases. Do not build a portal-detection on subset size. *Source: README L211-217.*
- [ ] **4.7** UNVERIFIED: the exact tie-breaking / 0-over-0 convention (e.g. what a true-singleton with
      a non-empty prediction yields when P is undefined) is **not stated** in any local file.
      README L200 fixes the *result* (0.0) but not the arithmetic guard. The live scorer was not
      reachable. Implement the README result literally in your offline harness.

## 5. `candidate_pairs.tsv` - scored? required? subset?

- [ ] **5.1** **NOT leaderboard-scored.** *Source: README L68-69 "This is the only file scored on the
      leaderboard"* and L109 "It is **not scored on the leaderboard**".*
- [ ] **5.2** **REQUIRED in the final submission zip**, even though it is not scored.
      *Source: validator L16-18 ("When absent ... the run **fails**: it is required in your final
      submission zip") and L275-279, which appends a hard **error**, not a warning.
      [RUN] deleting the candidate file -> FAIL "not found - candidate_pairs.tsv checks were skipped."
      NOTE the handoff (L33) says the *public* copy only warns. The local copy errors. See section 0.
- [ ] **5.3** For the **leaderboard upload during the challenge** you upload only
      `matching_results.tsv` to the Portal. *Source: README L221-223.* UNVERIFIED whether the Portal's
      upload widget *also* accepts/wants the candidate file.
- [ ] **5.4** **Final matches SHOULD be a subset of candidates - this is a WARNING, never a failure.**
      *Source: validator L281-293 (`warnings.append`, explicitly "we warn but never fail on it";
      L28 "warnings never fail the run").* [RUN] a match absent from the candidate set -> **PASS,
      exit 0**, warning only. *README L128-129 and handoff L18 both say "should be a subset" -
      advisory, not a gate.*
- [ ] **5.5** `candidate_pairs.tsv` must be the **LAST** blocking stage - the exact pair set the
      matcher actually scored at inference, not a raw earlier blocking pass. *Source: README L100-107.*
- [ ] **5.6** Empty `candidate_entity_ids` rows are **legal** (L161-164, L218 counts them; README L126).
- [ ] **5.7** It is used by organizers to audit **blocking recall ceiling and reduction ratio**.
      *Source: README L109-110, L149-152.*
- [ ] **5.8** Coding note: the current writer defines the candidate set as the stage-1 top-ranked S1
      candidate per record kept when `p1 >= P1_MIN` - i.e. already narrowed to the best pair.
      *Source: `_upstream/src/make_submission.py` L72-77.* Consistent with README L100-107 (it is the
      set the model actually scores), but confirm the blocking recall ceiling is acceptable - a
      1-candidate-per-record ceiling is a deliberate recall trade-off.

## 6. Unknown S2/S3 IDs - reject or score zero?

**The local validator and the brief directly contradict each other. Treat "reject" as the rule.**

- [ ] **6.1** By default the validator does **NOT** check ID existence (`--check-ids` is off, L322-329)
      and prints a warning saying so (L253-259). Without `--check-ids` an unknown S2/S3 ID causes
      **no error at all**.
- [ ] **6.2** With `--check-ids` and a complete `--test-dir`, an unknown ID is a hard **FAIL**:
      "references IDs not in the test Source-2/3 files" (L199-203, L174-175). [RUN] confirmed.
- [ ] **6.3** **The brief says REJECT.** *Source: README L183 - "IDs that do not exist in the test set,
      **will be rejected**"*; README L96 "ID lists must only contain Source 2 or Source 3 IDs that
      exist in the test set"; README L182 "Submissions that fail validation will not be evaluated."
- [ ] **6.4** **The validator's own docstring says the opposite**: L37-38 "a missing/garbage matched ID
      only lowers your score rather than being rejected by the scorer, so this check is a diagnostic,
      not a gate."
- [ ] **6.5** UNRESOLVED CONFLICT. The handoff (L37) flags the same conflict: "This conflicts with the
      brief's stronger wording that nonexistent IDs are rejected. Confirm with the official
      validator/scorer."
      **Operational ruling: emit only IDs you have actually seen in `test_source2.tsv` /
      `test_source3.tsv`.** This satisfies both readings. Always run with `--check-ids` before shipping.
- [ ] **6.6** Always pass `--check-ids` as the final gate. It is off by default only for memory reasons
      (L30-39, L322-328) - a few GB on the full set. On this machine **free RAM was only 616 MB of
      7,913 MB**; the full `--check-ids` run loads all S2/S3 IDs and was **not executed here** (it
      would very likely OOM). Run it on a machine with >=8 GB free, or verify ID provenance at
      generation time instead.
- [ ] **6.7** UNVERIFIED: whitespace, ordering and case handling of IDs by the *real scorer*. The
      validator `.strip()`s tokens (L159) and does **not** require sorted order (handoff L35).
      [RUN] `" S1-1 " TAB " S2-1 , S3-1 "` -> PASS. Do not rely on scorer-side leniency; the writer
      already sorts IDs (`make_submission.py` L69, L75).

---

## 7. Package / zip layout

*Source: README L147-178, L219-229; `Documentation_template.md` L63-67.*

- [ ] **7.1** A **single** zip, named `<team_name>_submission.zip`, with this layout:
  ```
  <team_name>_submission.zip
  |-- output/
  |   |-- matching_results.tsv
  |   `-- candidate_pairs.tsv
  |-- code/
  |   `-- business_entity_resolution/
  |       |-- src/             # all source
  |       |-- README.md        # exact run instructions, data -> blocking -> matching -> output
  |       `-- requirements.txt # pinned versions / environment
  `-- Documentation_template.md   # FILLED IN
  ```
  *Source: README L156-167.*
- [ ] **7.2** `output/matching_results.tsv` is **byte-identical** to the file uploaded to the
  leaderboard. *README L159 "same file you upload to the leaderboard".*
- [ ] **7.3** `code/business_entity_resolution/` is **self-contained and runnable** - "Anyone should be
  able to regenerate both output files from the training/test data using only what is in this folder."
  *README L171-175.* Test this from a clean clone.
- [ ] **7.4** `requirements.txt` must **pin** versions. *README L165, L173.*
- [ ] **7.5** The methodology document is the **filled-in `Documentation_template.md`**, dropped in at
  the zip root. `.md` is fine; a `.pdf` export is also fine; **no need to rename it**.
  *README L176-178.* **Do not ship the blank template.**
- [ ] **7.6** No page limit. *README L236, template L74.* Cover at minimum: methodology (L230-231),
  candidate generation/blocking (L232), model architecture + feature engineering (L233), any other
  relevant info (L234). The template's own sections also ask for: blocking keys + candidate-pair count
  + how true matches were not lost (template L30-32); features + model type + **threshold selection
  method** (L38-44); F0.5 macro + FP/FN error analysis (L50-52).
- [ ] **7.7** **Every team** must submit the package, not just finalists. *README L149, L228.*
- [ ] **7.8** UNVERIFIED - exact zip name/path, whether a top-level wrapping folder is allowed inside
  the zip, and the documentation page limit. Handoff L85 lists all three as unconfirmed. The layout
  above is from the brief, which shows no wrapping folder.
- [ ] **7.9** Current state: **no zip builder script exists in the workspace** (searched for
  `zip|package|submit|build_sub*.py` outside venvs/site-packages -> only two unrelated
  `check_*_zip_*.py` data-inspection scripts). This must be written.

## 8. Fair play & model licence

*Source: README L238-254, L186; handoff L21.*

- [ ] **8.1** NO external databases, APIs or services used to look up business identities or resolve
      entities. *README L242.*
- [ ] **8.2** NO commercial entity-resolution APIs or services. *README L244.*
- [ ] **8.3** NO government business-registration lookups / registries. *README L245.*
- [ ] **8.4** NO geocoding APIs to normalise addresses. *README L246.*
- [ ] **8.5** NO internet-derived data augmentation. *README L247.*
- [ ] **8.6** Consequence: penalty is **immediate disqualification**; all code and methodology are
      reviewed and verified. *README L249-252.*
- [ ] **8.7** The final **model** must be **MIT- or Apache-2.0-licensed** and **<= 8 billion
      parameters**. *README L186.*
- [ ] **8.8** UNRESOLVED SCOPE (handoff L21, L88) - do not self-resolve, ask the organizers:
  - Does the 8B / licence cap apply to **model weights only**, or to the whole stack including
    dependencies, embeddings and reranker models?
  - Are **classical / non-neural models** (LightGBM, XGBoost, logistic regression) permitted at all?
    `_upstream/src/make_submission.py` is a **two-stage LightGBM** pipeline (`import lightgbm as lgb`,
    L8) with **no neural model** - if "final model" is read strictly, item 8.7 may be **inapplicable**,
    or may still be read as requiring a disclosed model licence.
  - Are **locally cached / pre-trained encoders** allowed, and how is "parameter count" measured?
  - Is a generic public proxy dataset (e.g. FEBRL, DBLP-ACM) usable for **offline development** while
    still being barred from the submitted model? *Handoff L89.*
  - Current pipeline has no 8B-parameter model at all, so 8.7 is a documentation-disclosure item
    rather than a hard gate - **state the architecture and licences explicitly in the methodology doc
    so the reviewer can check it.**

## 9. The one command that gates everything

- [ ] **9.1** Run, from `student_resource/`, and require **`PASS` + exit code 0**:
  ```bash
  python utils/validate_submission.py \
      --matching   <abs>/output/matching_results.tsv \
      --candidate  <abs>/output/candidate_pairs.tsv \
      --test-dir   <abs>/dataset/test \
      --check-ids
  ```
  *Invocation form: validator L20-25, L298-341.* Exit 0 = safe, 1 = fix; **warnings never fail**
  (L28, L360-361, L367).
- [ ] **9.2** The validator checks the *files* only, and is a **subset of what the brief demands**: it
  never checks the metric, never checks the zip layout, never checks the model licence, and (by
  default) never checks ID existence. A PASS is **necessary, not sufficient**. Items 4, 7 and 8 are
  **not** covered by any script in this repo.

---

## 10. LIVE FINDING - the current `output/` files are structurally valid but semantically EMPTY

A streaming audit of `output/matching_results.tsv` and `output/candidate_pairs.tsv` (24,063,927 /
24,063,929 bytes, written 2026-09-27 13:09) against `dataset/test/test_source1.tsv` returned:

```
matching header : 'source1_entity_id<TAB>matched_entity_ids'      <- correct
candidate header: 'source1_entity_id<TAB>candidate_entity_ids'   <- correct
data rows in matching_results.tsv : 1732544                       <- correct
rows whose S1 differs from test_source1 order : 0                <- correct
rows not exactly 2 fields (matching) : 0                         <- correct
rows not exactly 2 fields (candidate) : 0                        <- correct
IDs without S2-/S3- prefix : 0                                  <- correct
rows with duplicate ID inside list : 0                            <- correct
rows where matched NOT subset of candidate : 0                    <- correct
CR(0x0D) bytes=0 ; double-quote bytes=0 ; UTF8-BOM=0              <- correct

*** empty matched_entity_ids (singletons predicted) : 1732544    <- ALL 1.73M rows empty
*** empty candidate_entity_ids                    : 1732544    <- ALL 1.73M rows empty
```

**Every single one of the 1,732,544 rows in BOTH files has an empty second field.**

- **Format: fully compliant.** These two files satisfy every item in sections 1-3.
- **Content: a total-miss run.** Zero predicted matches *and* zero candidates - the blocking stage
  produced nothing for any of the 1.73 M S1 entities. Under README L190-200 this scores **F0.5 equal
  to the fraction of true singletons only**, and since a business ER test set is not all singletons,
  effectively **~0** - while still burning a leaderboard submission.
- The byte sizes corroborate this: 24,063,927 B / 1,732,544 rows ~ 13.9 B/row, exactly
  `len("S1-714132312") + tab + LF` with **no** ID list. The writer
  (`_upstream/src/make_submission.py` L69-71, L75-77) is a `left` join plus `fill_null("")`, so an
  all-null join - every S1 unmatched, every S1 uncandidateed - produces exactly this file.
  **The format code is right; the upstream model artifacts/inputs did not run.**
- **Action for the team:** treat this as a **blocking** defect, not a formatting pass. Do not ship this
  zip. Re-run `_upstream/src/make_submission.py` with real work-dir artifacts and confirm the
  `"S1 with >=1 match"` counter (L79-80) is non-zero before packaging. Add a pre-packaging assertion
  that `matching_results.tsv` contains **at least one** non-empty second field.
- Note `_upstream/src/make_submission.py` and `patch_upstream/src/make_submission.py` are
  **byte-identical** (both sha256 `7288B6DF...C991653`), so the patch tree offers no fix.

---

## 11. UNVERIFIED - open questions that must not be guessed

1. Live portal / official scorer behaviour - **unreachable, no network.** All of sections 1-7
   reflects the *local* validator + brief only. (handoff L7, L11)
2. Local validator (14,849 B) vs the handoff's public mirror (13,687 B) - **different revisions**; the
   local one is stricter about a missing `candidate_pairs.tsv`. Which one the portal runs is unknown.
3. Unknown S2/S3 IDs: **reject** (README L183) vs **score zero** (validator L37). Unresolved (6.5).
4. Is `candidate_pairs.tsv` required for the **leaderboard upload**, the **final zip only**, or merely
   recommended? The brief settles the zip (required) but not the upload widget. (handoff L85)
5. Exact metric edge conventions (0-over-0 guards, tie-breaking) and whether the test France shift is
   exactly as described. (README L27, L190-200; handoff L86-87)
6. Scope of "MIT/Apache-2.0, <=8B parameters": weights vs whole stack; classical models allowed?
   (handoff L21, L88)
7. Exact zip name/path, whether a wrapping folder is permitted, documentation page limit. (handoff L85)
8. Scorer-side ID whitespace / ordering / case handling. (handoff L35, L86)
9. Whether any generic public proxy may be used for offline development. (handoff L89)
10. Team size (2-4 vs 3-4), registration deadline, timezone, graduation-year eligibility, cross-college
    teams. (handoff L84) - out of scope for this contract, listed for completeness.
11. Whether a genuine `sample_submission` exists on the portal; none exists locally, so the validator
    is the only authority available for header spelling.

---

## Appendix - evidence index (quick reference)

| Item | File | Lines |
|---|---|---|
| Exact matching header constant | `utils/validate_submission.py` | **48** |
| Exact candidate header constant | `utils/validate_submission.py` | **49** |
| Tab delimiter constant | `utils/validate_submission.py` | **46** |
| Header exact-equality gate | `utils/validate_submission.py` | **123-129** |
| CSV-instead-of-TSV guard | `utils/validate_submission.py` | **116-122** |
| 3-column / 2-column row gate | `utils/validate_submission.py` | **147-156** |
| No-tab row gate | `utils/validate_submission.py` | **134-140** |
| Comma split, strip, empty-list handling | `utils/validate_submission.py` | **158-164** |
| Prefix / self-match / unknown checks | `utils/validate_submission.py` | **169-175** |
| 7 aggregated error categories | `utils/validate_submission.py` | **177-216** |
| Required-S1 source = `test_source1.tsv` | `utils/validate_submission.py` | **231-245** |
| `--check-ids` default OFF + warning | `utils/validate_submission.py` | **247-259, 322-329** |
| matching/candidate wired to constants | `utils/validate_submission.py` | **261-273** |
| candidate file REQUIRED (hard error) | `utils/validate_submission.py` | **274-279** |
| Subset check = warning only | `utils/validate_submission.py` | **281-293** |
| UTF-8 failure path | `utils/validate_submission.py` | **342-352** |
| exit 0 = pass / 1 = fail | `utils/validate_submission.py` | **360-368** |
| "unknown ID only lowers score" docstring | `utils/validate_submission.py` | **30-39** |
| Column tables + examples (plural) | `README.md` | **77-88, 112-124** |
| Ground-truth schema (plural) | `README.md` | **33-34** |
| "no quoting" rule | `README.md` | **82** |
| Zip layout | `README.md` | **154-178** |
| Constraints (reject wording) | `README.md` | **180-186** |
| F0.5 formula | `README.md` | **190-196** |
| Macro-per-S1 | `README.md` | **198** |
| Singleton = 1.0 / 0.0 | `README.md` | **200** |
| Worked example (0.714) | `README.md` | **204-209** |
| Fair-play prohibitions | `README.md` | **238-254** |
| Pipeline writer (2 TSVs) | `_upstream/src/make_submission.py` | **66-80** |
