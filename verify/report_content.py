"""Report content: research vs. upstream comparison, findings and fixes."""
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, Spacer

from report_base import (ACCENT, BAND, CRIT, HIGH, MED, MUTED, OKC, RULE, S, WARN, W,
                         bullets, callout, code, esc, finding, tbl)


def build(F):
    # ---------------------------------------------------------------- cover
    F.append(Spacer(1, 6 * mm))
    F.append(Paragraph("Entity Resolution: published research vs. the upstream pipeline",
                       S["title"]))
    F.append(Paragraph("Gap analysis, prioritised findings and concrete fixes for "
                       "<b>Ruthwik000/amazonsummerML</b> as adapted in "
                       "<font face='Courier'>colab_upstream_cell.txt</font>", S["sub"]))
    F.append(Spacer(1, 5 * mm))
    F.append(tbl(
        ["Field", "Detail"],
        [["Scope", "Methodology comparison only. No challenge dataset, ground truth, leaderboard or "
                   "third-party solution to this challenge was searched for or used."],
         ["Under review", "Ruthwik000/amazonsummerML @ 8445b7f (read-only clone in _upstream/), "
                          "22 source files, run_all.sh drives 12 steps."],
         ["Research corpus", "SIGMOD Programming Contests 2021/2022, ESWC 2024, NAACL 2024, VLDB 2021, "
                             "plus record-linkage literature. Full survey: "
                             "RESEARCH_entity_resolution_methodology.md."],
         ["Verdict", "Upstream is already competition-grade. The highest-return work is <b>not</b> a "
                     "better model - it is France coverage, validation honesty, and packaging."]],
        [30 * mm, W - 30 * mm]))
    F.append(Spacer(1, 6 * mm))

    F.append(callout(
        "REVISED EDITION - every finding in this report has now been re-tested",
        "The first edition shipped with <b>untested</b> findings. Given that its two top-ranked "
        "findings both turned out to be false on measurement, the remaining six were re-checked "
        "against the code and data rather than republished as-is. <b>Four of eight findings are now "
        "withdrawn or partly withdrawn:</b> "
        "<b>F1</b> (France postal codes) and <b>F2</b> (FR_REGIONS) are false; <b>F6</b> is half "
        "wrong - mutual exclusion <i>does</i> exist at "
        "<font face='Courier'>crossfit.py:37-44</font>, only the missing per-entity cap stands; "
        "<b>F8</b> Gaps 3 and 4 are both resolved, Gap 3 never was a bug. "
        "<b>F3, F4, F5 and F7</b> are confirmed and unchanged. "
        "The full measured record, including three further France hypotheses that were also ruled "
        "out, is in <font face='Courier'>FRANCE_FINDINGS.md</font>. "
        "<b>Standing lesson: a claim ships with the script that produced it, or it does not "
        "ship.</b>",
        CRIT, WARN))

    F.append(callout(
        "Severity has been re-ranked, and the ranking changed",
        "In the first edition F1 and F2 were rated CRITICAL on the reasoning that they affected "
        "France, the only scored country, at a cost of a line each. Both are false, so that entire "
        "justification collapses. <b>The highest-confidence remaining work is F8 Gap 1</b> - "
        "packaging and the methodology document - which is a reporting requirement, not a modelling "
        "one. F6's per-entity cap is the only live modelling change with a clear mechanism behind "
        "it. Read the priority table in section 6 as superseding the original ordering.",
        CRIT, MUTED))

    F.append(callout(
        "Correction to a working assumption carried in earlier notes",
        "Earlier notes stated that &quot;a smaller candidate set ranks higher, beyond the model "
        "score.&quot; <b>The brief does not say that.</b> It says candidate_pairs.tsv "
        "&quot;<i>is not scored on the leaderboard</i>&quot; and is used &quot;to analyse blocking "
        "quality (recall ceiling, reduction ratio) and to verify your pipeline.&quot; The only "
        "leaderboard-scored artefact is matching_results.tsv. <b>Consequence:</b> shrinking the "
        "candidate set buys no leaderboard points; it only moves the recall ceiling you are reviewed "
        "on. A research sub-agent was briefed with this wrong premise and repeated it - that claim is "
        "retracted here and re-derived from the primary sources below.",
        CRIT, MUTED))

    # ----------------------------------------------- 1. what upstream does
    F.append(PageBreak())
    F.append(Paragraph("1. What the upstream pipeline actually does", S["h1"]))
    F.append(Paragraph(
        "The design under review is stated precisely first, with file and line references. This matters "
        "because most findings below are about <i>which population a number applies to</i>, not about "
        "gross architectural errors.", S["body"]))
    F.extend(bullets([
        "<b>Blocking (retrieval).</b> Composite keys over 5 kinds - name x address, name-pair, "
        "address-number x address-word, full sorted name, single name token - hashed to u64 and scoped "
        "by country. Scored by summed IDF of shared keys, top 50 kept, plus a relative floor "
        "(rel=0.2). <i>src/keys.py</i>, <i>src/blocking.py:20-39</i>, <i>src/run_blocking.py:8</i>.",
        "<b>Stage 1 - learned candidate ranker.</b> Two LightGBM models, each trained on one half of "
        "the queries and scoring the other half, giving every training pair an out-of-fold score. "
        "<i>src/crossfit.py:60-100</i>.",
        "<b>Stage 2 - acceptance model.</b> LightGBM over each query's best candidate with cluster "
        "context and query-to-query similarity; threshold tuned for macro F0.5 on V. "
        "<i>src/crossfit.py:110-161</i>.",
        "<b>Assembly.</b> matching_results.tsv = accepted pairs; candidate_pairs.tsv = exactly the set "
        "stage 2 scores, filtered at P1_MIN = 0.02. <i>src/make_submission.py:68-77</i>.",
    ]))
    F.append(Paragraph(
        "Reported funnel: <b>30.5</b> candidates per Source-1 entity after retrieval, <b>3.97</b> after "
        "the learned ranker (6.9M pairs). A full run is quoted at 3-4 hours on 2 cores with peak under "
        "6 GB, because every step is chunked per country or per query range. This is well engineered, "
        "and the two-stage retrieve-then-rank shape is the same one the literature converges on.",
        S["body"]))
    F.append(tbl(
        ["Stage", "Cand. / S1", "Role", "Reference"],
        [["Raw key retrieval", "30.5", "Recall ceiling", "run_blocking.py:27"],
         ["Learned ranker (stage 1)", "3.97", "What stage 2 scores = candidate_pairs.tsv",
          "make_submission.py:74"],
         ["Stage 2 + threshold THR", "accepted", "matching_results.tsv", "make_submission.py:68"]],
        [40 * mm, 22 * mm, 64 * mm, 50 * mm], mono_cols=(3,)))
    F.append(Paragraph(
        "Table 1 - The candidate funnel as instrumented in the upstream code.", S["cap"]))

    # ------------------------------------------------- 2. research corpus
    F.append(Paragraph("2. The research corpus, and what each source actually claims", S["h1"]))
    F.append(Paragraph(
        "The SIGMOD Programming Contests are the two most valuable sources, because one of them scores "
        "blocking almost exactly the way this challenge reviews it. Confidence tags are carried through "
        "from the underlying survey, which marks each claim [VERIFIED] / [INFERENCE] / [THIN] / [GAP].",
        S["body"]))
    F.append(tbl(
        ["Source", "What it contributes", "Bearing on this task"],
        [["<b>SIGMOD 2022</b> - Blocking System for ER (Chu Data Lab / DBGroup UNIMORE); winner "
          "Brinkmann &amp; Peeters, U. Mannheim",
          "Task was <i>only</i> blocking. Ranked on <b>average recall at a hard candidate-set cap</b>, "
          "ties broken by runtime. 1M rows/dataset, 1M + 2M pair budgets, 35 min CPU-only.",
          "Closest structural analogue in public competition. Confirms candidate size is a genuine "
          "engineering constraint, but <b>not</b> a leaderboard score."],
         ["<b>SC-Block</b> (ESWC 2024), Brinkmann, Shraga, Bizer - arXiv:2303.03132",
          "Supervised contrastive learning places records in an embedding space, then ANN retrieval. "
          "Smaller candidate sets than 8 baselines; pipelines 1.5-2x faster, 8x on a large benchmark "
          "(2.5h -&gt; 18min against 5 min training). Benchmarks at <b>99.5% pair completeness</b>.",
          "The learned-retriever upgrade path. Its operating point is far more generous than this task "
          "needs."],
         ["<b>PLMs for Entity Blocking</b> (NAACL 2024), Wang &amp; Zhang - 2024.naacl-long.483",
          "Evaluates SOTA blockers <i>and</i> neural-IR models, studying in-distribution vs "
          "<b>out-of-distribution</b> generalisation - explicitly called out as under-studied yet "
          "important in real applications.",
          "Directly on point for the unseen-third-country risk. Reads as a caution, not a recipe."],
         ["<b>Ditto</b> (VLDB 2021), Li, Li, Suhara, Doan, Tan - arXiv:2004.00584",
          "PLM fine-tuned as sequence-pair classification. Up to +29% F1 over prior SOTA, +9.8% more "
          "from input highlighting, long-value summarisation and augmentation. <b>Reaches prior SOTA "
          "with at most half the labelled data.</b> 789K x 412K company records, F1 96.5%.",
          "Precedent for a company-record matcher, and for label efficiency mattering. Needs an "
          "MIT/Apache model under 8B - permitted, but costly."],
         ["<b>Bias in error estimation</b> (BMC Bioinformatics 2006), Varma &amp; Simon - "
          "doi:10.1186/1471-2105-7-91",
          "CV error for the optimally-tuned classifier was substantially biased; on null datasets the "
          "tuned SVM estimate was &lt;30% true error <b>38% of the time</b>, with test performance no "
          "better than chance. Nested CV &quot;gives an estimate very close to that obtained on the "
          "independent testing set.&quot;",
          "The direct justification for finding <b>F3</b>. Threshold choice is a tuning step by any "
          "reasonable definition."],
         ["<b>Self-map audit</b> of this repo - audit_normalize.py",
          "Counts parsed from the real normaliser, not recalled. FR_REGIONS: 14 entries, <b>4 distinct "
          "values</b>. US_STATES: 52/52. IN_STATES: 49/37.",
          "Quantifies <b>F1</b> and <b>F2</b>."]],
        [38 * mm, 70 * mm, 68 * mm]))
    F.append(Paragraph("Table 2 - Primary sources and what each actually claims.", S["cap"]))

    # ------------------------------------------------------- 3. gap matrix
    F.append(Paragraph("3. Gap matrix: upstream vs. the literature", S["h1"]))
    F.append(tbl(
        ["Technique from the literature", "Upstream status", "Verdict"],
        [["Two-stage retrieve-then-rank over all attributes",
          "Present and well built (30.5 -&gt; 3.97)", "<b>Already done.</b> No action."],
         ["Learned / embedding retriever (SC-Block class)",
          "Absent - retrieval is IDF over hashed keys",
          "Real gap, but see F7 - <b>not the first move</b>."],
         ["Country-agnostic normalisation with fallbacks for an unseen country",
          "Structurally safe (country-scoped keys, .get fallback); France tables "
          "<b>verified sufficient</b> on this dataset",
          "<b>No gap.</b> F1/F2 were refuted on measurement; six further audits agree. "
          "Do not extend the tables."],
         ["Abstention-aware thresholding for singletons",
          "Single global THR tuned on V", "Partially present; see F5 and F6."],
         ["Nested / cross-fitted threshold selection",
          "V is used for early stopping, thresholding <i>and</i> reporting",
          "<b>Gap - F3.</b> Affects reported honesty, not the submission."],
         ["Set-level constraints: cluster-size cap, mutual exclusion",
          "Mutual exclusion <b>present</b> (crossfit.py:37-44 anti-join); per-entity list "
          "<b>uncapped</b>",
          "<b>Partial gap - F6.</b> Only the cap is missing. The exclusion half was a "
          "misreading."],
         ["Metric-exact local scorer including singleton semantics",
          "Present; verified against sklearn fbeta_score over 400 randomised cases",
          "<b>Already done.</b> Keep it."],
         ["Fellegi-Sunter / m-u match weights as calibrated features",
          "Not present (raw similarity features instead)",
          "Optional; the learned ranker largely subsumes it. Low priority."],
         ["Candidate recall@budget measured explicitly",
          "Funnel sizes reported, but no recall-ceiling measurement",
          "Gap - F5. Cheap to add on V."]],
        [56 * mm, 66 * mm, 54 * mm]))
    F.append(Paragraph(
        "Table 3 - Most high-value literature techniques are already in place, or are gaps with unclear "
        "payoff. The two exceptions are France coverage and validation honesty.", S["cap"]))

    # --------------------------------------------------------- 4. findings
    F.append(PageBreak())
    F.append(Paragraph("4. Findings and fixes, in priority order", S["h1"]))
    F.append(Paragraph(
        "Severity reflects effect on the private-leaderboard score for the <i>French</i> test set, "
        "divided by cost. <b>This ordering is the revised one.</b> In the first edition F1 and F2 "
        "dominated the list on the reasoning that they were cheap and France-specific; both were then "
        "measured and found false, so the top of the ranking has changed. Items marked "
        "<font face='Courier'>RESOLVED</font> or <font face='Courier'>REFUTED</font> are retained for "
        "auditability, not as work items.", S["body"]))

    F.extend(finding("F1", MUTED, CRIT, "[REFUTED - DO NOT ACT ON THIS] France postal codes are never captured", [
        ("Status", "<b>This finding is FALSE and has been withdrawn.</b> It was produced by reading "
                   "<font face='Courier'>normalize.py</font> without measuring the data. The original "
                   "text is retained below only so the error is auditable."),
        ("Where", "<font face='Courier'>src/normalize.py:336-338</font>"),
        ("Evidence", "<font face='Courier'>if len(n) == 6 and country == \"India\": pin = n</font><br/>"
                     "A parse of the normaliser confirms <font face='Courier'>pin</font> is assigned in "
                     "exactly one place, under an India-only guard. Verified by grep across prep.py and "
                     "normalize.py."),
        ("Consequence", "US ZIP codes (5 digits) and French codes postaux (5 digits) are never stored in "
                        "<font face='Courier'>pin</font>. That field feeds a blocking key "
                        "(<font face='Courier'>keys.py:44</font>) and a ranker feature. Both are "
                        "therefore <b>constant/dead for France</b> - and France is the entire scored "
                        "test set. The strongest cheap locality signal in a French address is simply not "
                        "being used."),
        ("Fix", "Widen the guard. Capture 5-digit codes for US and France in addition to the existing "
                "6-digit Indian PIN. Optionally also capture the 2-character French departement forms "
                "(2A, 2B) which do not parse as integers."),
        ("Effort", "~1 line plus regression tests."),
        ("Risk", "Low, but re-run blocking: adding a new key kind changes the candidate set and "
                 "invalidates cached stage-1 outputs. Do it before any long run, not after."),
    ]))

    F.extend(finding("F2", MUTED, CRIT, "[REFUTED - DO NOT ACT ON THIS] FR_REGIONS covers 4 of 18 regions and is excluded from the abbreviation self-map", [
        ("Status", "<b>This finding is FALSE as a data-quality claim and has been withdrawn.</b> "
                   "Replicating <font face='Courier'>normalize_address</font>'s exact component matching, "
                   "state resolves for <b>100.00%</b> of France rows (259,452/259,452, zero unmatched). "
                   "The table is sufficient because this dataset uses only three modern regions. The "
                   "self-map defect at line 252 is real code but has no measurable effect here. The "
                   "original text is retained below only for audit."),
        ("Where", "<font face='Courier'>src/normalize.py:243-254</font>"),
        ("Evidence", "FR_REGIONS has 14 entries mapping to only <b>4 distinct values</b> (hdf, naq, pdl, "
                     "idf) - versus US_STATES 52/52 and IN_STATES 49/37. It omits Bretagne, Normandie, "
                     "Grand Est, Occitanie, AuRA, PACA, Centre-Val de Loire, Bourgogne-Franche-Comte "
                     "and Corse, plus 90 of 101 departements."),
        ("Second defect", "The self-map loop reads "
                          "<font face='Courier'>for _m in (US_STATES, IN_STATES):</font> at line 252 - "
                          "<b>FR_REGIONS is not in the tuple</b>. An already-abbreviated value such as "
                          "<font face='Courier'>idf</font> is therefore not recognised as a state and "
                          "falls through into the address token list, adding noise."),
        ("Fix", "Populate all 18 regions and the 101 departement codes; add FR_REGIONS to the self-map "
                "loop. This is a pure data-table edit with no structural change."),
        ("Why it matters", "The <font face='Courier'>state</font> feature and the state match in "
                           "stage 2 are close to useless for France as written, so the model falls back "
                           "on weaker string similarity for a third of the scored rows."),
        ("Effort", "Data entry, ~1 hour. Highest certainty-to-effort ratio in this report."),
    ]))

    F.extend(finding("F3", ACCENT, HIGH, "V is used for early stopping, threshold selection AND reporting - val_f05 is optimistic", [
        ("Where", "<font face='Courier'>src/crossfit.py:84</font> (early stop on V), "
                  "<font face='Courier'>153-156</font> (threshold sweep on V), "
                  "<font face='Courier'>161</font> (reports best_thr[0])"),
        ("Evidence", "The same V split (3% of Source-1 entities) serves three roles at once. A "
                     "controlled simulation in this workspace put single-step optimism at roughly "
                     "<b>+2.4%</b>."),
        ("Literature", "Varma &amp; Simon: CV error for the optimally-tuned classifier is substantially "
                       "biased, and on null data the tuned estimate was &lt;30% true error 38% of the "
                       "time. Their prescription is that <i>all</i> steps including parameter tuning be "
                       "repeated inside each CV loop."),
        ("Important nuance", "Tuning the shipped threshold on V is <b>legitimate</b> - that is what a "
                             "validation set is for. Only the <i>reported</i> number is compromised. "
                             "This is a reporting-integrity fix, not a submission change."),
        ("Fix", "Split V in two by hash: V-tune for early stopping and threshold selection, V-report "
                "untouched for the headline figure, and report both. Then add a second independent "
                "holdout - the current design has none."),
        ("Effect on score", "None on the submission. Large effect on how credible the methodology "
                            "document is in review - and the package <i>is</i> reviewed before final "
                            "rankings are confirmed."),
    ]))

    F.extend(finding("F4", ACCENT, HIGH, "The Vkeys evaluation population is narrower than the test-time population", [
        ("Where", "<font face='Courier'>src/crossfit.py:124</font>"),
        ("Evidence", "<font face='Courier'>Vkeys = best.join(qV, on=\"rid\").join(s1V, on=\"s1\")</font> "
                     "restricts <b>both</b> the query and the Source-1 side to V."),
        ("Consequence", "The macro F0.5 estimate is computed over a sub-population in which cross-links "
                        "between V and non-V entities cannot appear. At test time any query may match "
                        "any Source-1 entity, so the real macro average is taken over a broader - and "
                        "on these grounds slightly different - population."),
        ("Fix", "Evaluate V queries against <i>all</i> their candidate Source-1 entities, not only those "
                "whose s1 is in V. The gold-truth join already uses the full truth, so this is a change "
                "to the prediction filter, not to the scorer."),
        ("Effort", "Small, but it requires care to keep the scorer macro semantics intact."),
    ]))

    F.extend(finding("F5", ACCENT, MED, "Candidate set is top-1 per query with a very loose floor - measure the recall ceiling before touching it", [
        ("Where", "<font face='Courier'>src/make_submission.py:74</font>"),
        ("Evidence", "<font face='Courier'>cand = best.filter(pl.col(\"p1\") &gt;= P1_MIN)</font> - "
                     "<font face='Courier'>best</font> is stage 2's input, one candidate per query, so "
                     "the candidate set is exactly {best candidate : p1 &gt;= 0.02}."),
        ("Contract check", "This is <b>correct against the brief</b>: candidates must be the last stage's "
                           "input, and every ID in matching_results.tsv must appear in it. Since "
                           "<font face='Courier'>acc</font> filters a subset of <font face='Courier'>cand"
                           "</font> on the same P1_MIN (line 68), the subset invariant holds. No bug here."),
        ("The real issue", "Recall ceiling is capped at top-1 by construction. The SIGMOD 2022 winners "
                           "instead kept a <i>ranked</i> list and filled to an explicit pair budget, "
                           "which decouples 'what the model scores' from 'what the reviewer audits'."),
        ("Fix", "Measure the recall ceiling on V as a function of k and of the p1 floor, then emit a "
                "ranked top-k (k = 3-5) above a higher floor. Because candidate_pairs.tsv is "
                "<b>not leaderboard-scored</b>, this costs no score and raises the recall ceiling "
                "visible in review."),
        ("Local fallback evidence", "The measured cap/recall tradeoff on the local pipeline was 4.89 "
                                   "cand/S1 at 0.4108 gold recall (cap 5) rising to 9.63 at 0.4652 "
                                   "(cap 10). Upstream's learned ranker reaches 3.97, a materially "
                                   "better point on the same curve."),
    ]))

    F.extend(finding("F6", MUTED, MED, "[PARTLY REFUTED] Per-entity cap is a real gap; the mutual-exclusion half is an open question", [
        ("Status", "<b>Half of this finding is wrong.</b> The original text asserted there is "
                   "<i>no mutual exclusion</i>. There is: <font face='Courier'>home_table()</font> at "
                   "<font face='Courier'>crossfit.py:37-44</font> anti-joins each priority tier "
                   "against the tiers already assigned (<font face='Courier'>r.join(seen, on=\"rid\", "
                   "how=\"anti\")</font>), so a query is assigned to exactly one home partition and "
                   "cannot be scored twice. The <b>per-entity cap</b> half stands and is worth acting on."),
        ("Where", "<font face='Courier'>src/make_submission.py:69-70</font> (cap absent) and "
                  "<font face='Courier'>src/crossfit.py:37-44</font> (exclusion present)"),
        ("Still valid - no cap", "<font face='Courier'>s1.join(acc.group_by(\"s1\").agg("
                                 "pl.col(\"entity_id\").sort().str.join(\",\").alias("
                                 "\"matched_entity_ids\")))</font> - every accepted ID is concatenated "
                                 "with no cap."),
        ("Why it costs precision", "With F0.5, a false merge costs roughly 4x a missed link, and "
                                   "singletons score 0.0 for <i>any</i> prediction. A chaining error that "
                                   "absorbs 10 wrong records into one entity costs far more than one that "
                                   "absorbs 2. A per-entity cap of the k best by p2 bounds that damage "
                                   "directly."),
        ("Still open", "Whether one S2/S3 record may be claimed by two different S1 entities. The brief "
                       "rejects duplicates <i>within</i> a list but is less explicit about cross-entity "
                       "claims. <b>Verify against utils/validate_submission.py</b> before assuming it is "
                       "either allowed or forbidden."),
        ("Fix", "Cap matched_entity_ids per S1 at the top k by p2. Treat cross-entity collision "
                "resolution as a separate, separate-lookup question - do not bundle it with the cap."),
        ("Effort", "~5 lines, plus a decision on the collision question."),
    ]))

    F.extend(finding("F7", MUTED, BAND, "A learned / embedding retriever is a real gap but explicitly NOT the next move", [
        ("The technique", "SC-Block and the SIGMOD 2022 winner: fine-tune a small distilled Transformer "
                          "with a supervised contrastive loss, embed records, retrieve by approximate "
                          "nearest neighbour (FAISS), rerank with a symbol-level similarity such as "
                          "Jaccard, and fill to a pair budget."),
        ("Reported", "Smaller candidate sets than eight baselines; pipelines 1.5-2x faster, 8x on a "
                     "large benchmark (2.5h -&gt; 18 min) against 5 min of training."),
        ("Why not now", "Three reasons. (1) <b>Out-of-distribution risk:</b> the NAACL 2024 study shows "
                        "SOTA blockers' generalisation to unseen data is under-studied and a real "
                        "concern - a contrastive retriever trained on US+India faces precisely that, on "
                        "the only country that scores. (2) <b>Wrong operating point:</b> SC-Block "
                        "benchmarks at 99.5% pair completeness, far more generous than a "
                        "precision-weighted metric needs. (3) <b>Prohibited ingredient:</b> the 2022 "
                        "winner's pretraining set came from Common Crawl via schema.org - disqualifying "
                        "here."),
        ("Revisit only if", "F1-F6 are done <b>and</b> a second-country holdout exists to measure the "
                            "OOD drop honestly. Without that holdout you cannot tell an improvement from "
                            "a regression."),
        ("Verdict", "High cost, uncertain payoff, and it would consume the effort that F1 and F2 - a "
                    "few lines each - return with high confidence."),
    ]))

    F.extend(finding("F8", ACCENT, MED, "Packaging and reproducibility gaps that can cost the submission outright", [
        ("Brief requirement", "The final package is "
                              "<font face='Courier'>&lt;team&gt;_submission.zip</font> containing "
                              "<font face='Courier'>output/</font> (both TSVs), "
                              "<font face='Courier'>code/business_entity_resolution/</font> with "
                              "<font face='Courier'>src/</font>, <i>README.md</i> and pinned "
                              "<font face='Courier'>requirements.txt</font>, plus a filled "
                              "<font face='Courier'>Documentation_template.md</font>."),
        ("Gap 1", "The upstream repo has <font face='Courier'>src/</font> at top level and no "
                  "Documentation_template.md. It needs restructuring to the required path, and the "
                  "methodology document has to be written - the brief has no page limit and explicitly "
                  "prioritises depth."),
        ("Gap 2", "During the challenge the portal takes <b>matching_results.tsv only</b>; the zip is "
                  "the end-of-challenge package. Confirm which the portal expects per upload rather "
                  "than assuming."),
        ("Gap 3 - RESOLVED", "<i>Originally reported here:</i> the cell ran "
                             "<font face='Courier'>pip install -r requirements.txt</font> before cloning, "
                             "so a clean run would not find the file. <b>Re-checked, and this is not a "
                             "bug.</b> The clone is unconditional, in its own step "
                             "(<font face='Courier'>colab_upstream_cell.txt:50-53</font>, "
                             "<font face='Courier'>subprocess.run([\"git\", \"clone\", ...], "
                             "check=True)</font>), and the install line falls back to explicit package "
                             "names when the requirements file is absent. Withdrawn."),
        ("Gap 4 - RESOLVED", "check_cell.py originally compared only script names, step order and GT "
                             "placement. It now performs a <b>full argument-level diff</b> against "
                             "<font face='Courier'>run_all.sh</font> (12/12 exact match), so a silent "
                             "flag drift cannot ship."),
        ("Still open", "Gaps 1 and 2 only. Gap 1 is real packaging work and the largest remaining item; "
                       "Gap 2 is a one-question check against the upload portal."),
    ]))

    # ------------------------------------------------------- 5. do not do
    F.append(PageBreak())
    F.append(Paragraph("5. What not to do", S["h1"]))
    F.append(tbl(
        ["Tempting move", "Why it is wrong here"],
        [["Port the SIGMOD 2022 winner end to end, including its Common Crawl pretraining",
          "External data augmentation is <b>explicitly prohibited</b>; the penalty is immediate "
          "disqualification. Transfer the idea, not the corpus."],
         ["Shrink candidate_pairs.tsv to chase a smaller number",
          "It is not leaderboard-scored. You would trade away the recall ceiling for a metric that does "
          "not exist, and the ceiling is what gets reviewed."],
         ["Hard-code {US, India} or filter out unknown countries",
          "The brief calls country an open set and warns against exactly this. Upstream is already "
          "correct (country-scoped keys, <font face='Courier'>STATE_MAPS.get</font>); fix the "
          "<i>data</i> in F2, not the code path."],
         ["Quote the 0.98612 val_f05 as a headline in the methodology document",
          "It is the tuned-on-V figure (F3). Quoting it invites exactly the audit it will not survive, "
          "in a package reviewed before final rankings are confirmed."],
         ["Use a geocoding or business-registry API to enrich addresses",
          "Prohibited. The absence of a general-purpose geocoder from upstream is correct and must be "
          "preserved."],
         ["Keep designing against the 'smaller candidate set ranks higher' premise",
          "Retracted - a misreading of the brief (cover callout). It has already propagated into one "
          "research sub-agent's output; do not rely on that output without re-checking it."]],
        [56 * mm, 120 * mm]))
    F.append(Paragraph("Table 5 - Traps, each traced to a specific source line or brief clause.",
                       S["cap"]))

    # --------------------------------------------------------- 6. roadmap
    F.append(Paragraph("6. Recommended order of work", S["h1"]))
    F.append(tbl(
        ["#", "Action", "Findings", "Cost", "Affects score?"],
        [["1", "Restructure the repo to the required package layout; write the methodology doc",
          "F8", "Hours", "<b>Submission validity</b>"],
         ["2", "Cap matched_entity_ids per S1 at the top k by p2 (mutual exclusion already exists)",
          "F6", "~5 lines", "<b>Yes</b> - precision"],
         ["3", "Split V into tune/report halves; add a second untouched holdout", "F3, F4", "Small",
          "No - reporting honesty"],
         ["4", "Measure candidate recall ceiling on V for k = 1..5; emit a ranked top-k", "F5", "Small",
          "No (review only)"],
         ["5", "Confirm with the portal whether the zip or matching_results.tsv is uploaded per attempt",
          "F8 G2", "Minutes", "Submission validity"],
         ["6", "Only then consider a learned retriever, and only with a second-country holdout", "F7",
          "Days", "Unknown - measure first"],
         ["-", "<font face='Courier'>[REFUTED]</font> Widen the postal-code guard", "F1", "-", "<b>No - do not do</b>"],
         ["-", "<font face='Courier'>[REFUTED]</font> Complete FR_REGIONS / add to self-map loop", "F2", "-",
          "<b>No - do not do</b>"],
         ["-", "<font face='Courier'>[RESOLVED]</font> Reorder clone before pip install", "F8 G3", "-", "Done - was never a bug"]],
        [7 * mm, 78 * mm, 19 * mm, 21 * mm, 51 * mm]))
    F.append(Paragraph(
        "Table 6 - Sequencing, revised after re-measurement. The first edition opened with two "
        "one-line France fixes; both are now known to be no-ops, so <b>the highest-confidence remaining "
        "work is packaging and the methodology document</b>, which the brief requires and which is "
        "reviewed before final rankings are confirmed. The only live modelling change with a clear "
        "mechanism behind it is the F6 per-entity cap. Items 3-4 protect the submission's credibility; "
        "item 6 stays last until there is a second-country holdout to measure an OOD drop honestly.",
        S["cap"]))

    F.append(callout(
        "Bottom line",
        "The upstream pipeline is genuinely good engineering, and most of what the literature recommends "
        "is already in it. <b>The revised conclusion is the opposite of the first edition's on France.</b> "
        "That edition argued the gap was concentrated in France - specifically its postal code and "
        "region table - and rated both CRITICAL. Both were then measured and found to be no-ops: France "
        "carries house numbers rather than postcodes, and its three regions in use are all already "
        "mapped. Six further France-specific audits returned the same verdict, including an independent "
        "convergence showing that completing <font face='Courier'>FR_REGIONS</font> would actively "
        "<i>delete</i> live IDF feature mass. "
        "<b>What actually remains is smaller and less glamorous:</b> cap the per-entity output list, stop "
        "grading the validation set on itself, and produce the packaging and methodology the brief "
        "requires. That is a better use of the remaining time than any model change - and it is what the "
        "evidence supports, which is not the same as what the first edition claimed.",
        MED, ACCENT))

    F.append(Paragraph("7. Verification commands used in this review", S["h1"]))
    F.append(code([
        "# The scripts that REFUTE F1 and F2 (these are the ones that matter now)",
        ".venv-pdf\\Scripts\\python.exe check_fr_postcode.py     # F1: France dig5/row = 0.004",
        ".venv-pdf\\Scripts\\python.exe check_fr_exact.py       # F2: 259452/259452 resolve = 100%",
        ".venv-pdf\\Scripts\\python.exe check_pin_impact.py    # F1: India dig6/row ~ 0.000",
        ".venv-pdf\\Scripts\\python.exe check_fr_regions.py    # F2: which regions actually occur",
        "",
        "# F6: confirm mutual exclusion exists (it does - crossfit.py:37-44)",
        "Select-String -Path _upstream\\src\\crossfit.py -Pattern 'anti'",
        "",
        "# F8 Gap 3: confirm the clone is unconditional, so pip ordering is a non-issue",
        "Select-String -Path colab_upstream_cell.txt -Pattern 'clone'",
        "",
        "# Metric correctness, already verified in the first edition",
        ".venv-pdf\\Scripts\\python.exe verify_upstream_metric.py  # 400 cases vs sklearn",
    ]))
    F.append(Paragraph(
        "Full methodology survey with per-claim confidence tags: "
        "<font face='Courier'>RESEARCH_entity_resolution_methodology.md</font>. The upstream tree was "
        "left read-only throughout; <font face='Courier'>git status</font> clean at 8445b7f.",
        S["cap"]))
