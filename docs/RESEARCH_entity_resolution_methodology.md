# Entity Resolution Methodology Survey — Multi-Source Business Record Linkage with an Unseen Test Country

**Scope note / compliance.** This is a survey of *general, published* ER/record-linkage methodology. I did **not** search for, fetch, or use the Amazon ML Challenge 2026 dataset, its ground truth, leaderboard, or any third-party write-up of it. Search terms deliberately excluded the challenge name. Everything below is from public literature, public documentation, or public competition pages for *other* challenges.

**How to read the confidence tags.**

- **[VERIFIED]** — I read the primary source directly and am quoting/paraphrasing its actual text.
- **[MY INFERENCE]** — my reasoning from a verified source, not a claim the source makes.
- **[THIN]** — evidence is weak, indirect, or I could not reach the source.
- **[GAP]** — I searched and could not find it; the survey is silent on it, not the literature.

---

## 0. The 8 most transferable techniques, and why each fits this task shape

| # | Technique | Why it fits *this specific* task |
|---|---|---|
| 1 | **Two-stage retrieve-then-rank, with a *learned or embedding-based* retriever over all attributes** | Candidate-set size is *explicitly scored* (smaller ranks higher). So recall@budget is a first-class objective, not an engineering detail. [VERIFIED] Papadakis et al. define the exact metrics to optimise (PC/PQ/RR). [VERIFIED] DeepER's LSH-on-tuple-embeddings is the canonical "use all attributes, not just a few" retriever. |
| 2 | **Deduplicated-union blocking via a long list of strict rules, plus skew control** | Three noisy sources, no shared key. Splink's guidance — many *tight* rules beat few *loose* rules — is directly transferable, and its quantified comparison-budget guidance (~20M pairs on DuckDB) gives a concrete budget. [VERIFIED] |
| 3 | **Fellegi–Sunter / log2(m/u) match weights as calibrated, explainable features** | With β=0.5 the metric is precision-dominated, so you need *ranking* that's well calibrated at the top. Match weights give a monotone, additive, auditable score, and `match weight → match probability` is a known, published mapping. [VERIFIED] |
| 4 | **Abstention-aware thresholding: predict "no match" for most reference entities** | Singletons are in the denominator and *any* prediction on a singleton scores 0.0. So the optimal operating point is "emit nothing unless evidence is strong" — a per-entity abstention problem, not a global threshold. [VERIFIED — Lipton et al. derive the optimal threshold for exactly this shape of metric.] |
| 5 | **Cross-fitted / nested threshold selection** | Choosing a threshold on the same scores you evaluate is the single easiest way to silently inflate a macro metric. Varma & Simon's numbers show how bad it gets. [VERIFIED] |
| 6 | **Set-level (cluster) post-processing with consistency constraints, not just pairwise links** | Cross-source pairwise links can be mutually contradictory; clustering repairs these. Also lets you *cap cluster size*, which directly serves the "smaller candidate set ranks higher" incentive. [VERIFIED] |
| 7 | **Country-agnostic normalisation + zero-shot/unsupervised fallbacks** | The test country is unseen. The literature's answer is twofold: (a) script-agnostic romanisation/normalisation, and (b) components that need *no* labels for the new country. ZeroER and Sudowoodo both demonstrate label-free operation. [VERIFIED] |
| 8 | **F-beta-aware evaluation harness that reproduces the leaderboard metric exactly, including singleton scoring** | Nobody's off-the-shelf F0.5 is your metric. If your local metric differs even slightly from the scorer's, every threshold decision is made on noise. [MY INFERENCE, built on the verified metric definition] |

**The single most important framing point** [MY INFERENCE]: your task is *not* "maximise pairwise F1". It is a **per-entity retrieval problem with an abstention option**, scored by a precision-weighted F with abstention counted as perfect. The three sources should be treated as: reference entities as *queries*, and other-source records as *the corpus to rank*. Everything in §1–§2 follows from that reframe.

---


## 1. Blocking / candidate generation that scales, and how the trade-off is reported

### 1.1 The standard metrics — use these, they are exactly the right ones

[VERIFIED] Papadakis, Skoutas, Thanos & Palpanas, *"A Survey of Blocking and Filtering Techniques for Entity Resolution"*, arXiv:1905.06167 / ACM CSUR (doi 10.1145/3377455), define the trade-off formally. Exact text from the paper:

> (1) Pair Completeness (PC) corresponds to recall... `PC(B) = |D(B)| / |D(E)| ∈ [0,1]`
> (2) Pairs Quality (PQ) corresponds to precision... `PQ(B) = |D(B)| / ||B|| ∈ [0,1]`
> (3) Reduction Ratio (RR) measures the reduction in the number of pairwise comparisons in B with respect to the brute-force approach: `RR(B,E) = 1 − ||B||/||E|| ∈ [0,1]`

Critically, and this is a point most implementers miss, the paper states:

> Note that PC provides an **optimistic** estimation of recall, presuming the existence of an oracle, while PQ provides a **pessimistic** estimation of precision, treating as false positives the repeated comparisons between duplicates.

[MY INFERENCE] For your task, add a **fourth** metric the literature doesn't name but your scorer effectively imposes: **mean candidate-set size per reference entity** (plus a coverage curve — recall@1/3/5). Because "smaller candidate set ranks higher beyond the model score", the objective is a *Pareto frontier* over (mean |candidates|, recall@k), not a single number. Report the whole curve.

[VERIFIED] The survey also gives the taxonomy you'll need: **Blocking** (restrict which pairs get compared) vs **Filtering** (cheap pre-comparison discard) vs **Block Processing** (refine blocks between blocking and matching). It frames the core tension: schema-agnostic blocking "disregard[s] any schema information, creating blocks of very high recall but low precision", and Block Processing then "significantly increas[es] precision at a negligible (if any) cost in recall."

### 1.2 Concrete scalable blocking recipes

**[VERIFIED] Union of many strict rules, deduplicated.** From Splink's blocking guide (https://moj-analytical-services.github.io/splink/topic_guides/blocking/blocking_rules.html):

> It's usually better to use a **longer list of strict blocking rules**, than a short list of loose blocking rules.
> ... There is a tension between these aims, because by choosing loose blocking rules which generate more comparisons, you have a greater chance of capturing all true matches. A single rule is unlikely to be able to achieve both aims.
> ... by specifying a variety of `blocking_rules_to_generate_predictions`, **even if each rule on its own is relatively tight, it becomes implausible that a truly matching record would not be captured by at least one of the rules.**

Splink's worked example is analogous to your data (block on first_name+surname, *plus* postcode as a second rule, so a typo in the name doesn't lose the match). For business records the natural rule set is: (normalised name token), (name first-char + postcode/region), (house number + street name), rare-token rarity, and fuzzy-string rules.

**[VERIFIED] Deduplicate the union, and measure each rule's marginal contribution.** From the Splink Blocking tutorial (https://moj-analytical-services.github.io/splink/demos/tutorials/03_Blocking.html):

> Since the same record comparison may be created by several blocking rules, and Splink automatically deduplicates these comparisons, we cannot simply total the number of comparisons generated by each rule individually. Splink provides a chart that shows the **marginal (additional) comparisons generated by each blocking rule, after deduplication**.

**[VERIFIED] Control skew explicitly, and know the numbers.** Same tutorial:

> For linkages in DuckDB on a standard laptop, we suggest using blocking rules that create no more than about **20 million comparisons**. For Spark and Athena, try starting with fewer than **100 million comparisons**, before scaling up.

and

> within each distinct value of (city, first initial), all possible pairwise comparisons will be generated. So for instance, if there are 15 distinct records with London,J then these records will result in n(n−1)/2 = 105 pairwise comparisons... In a larger dataset, we might observe 10,000 London,J records, which would then be responsible for **49,995,000 comparisons**.

[MY INFERENCE] For a *new* country, the likeliest skew bomb is not a common city name but a **placeholder address** (empty string, "NA", "-", a bare house-number token, a district name meaning "central"). Compute candidate counts per block value and hard-cap or exclude degenerate blocks (Splink: `n_largest_blocks`, `profile_columns`). If your test country has many low-quality addresses, this step alone is likely worth more than any model change.

**[VERIFIED] Sorted neighborhood** is the classic alternative; the survey places it in the schema-aware family. Progressive Sorted Neighborhood incrementally widens a window over a sorted list. [MY INFERENCE] SN requires the sort key to place true matches adjacent — exactly what fails across an address-format change in a new country. 
### 1.3 Learned / embedding two-stage retrieval (retrieve broadly, rank down)

Highest-leverage area for you, because candidate-set size is scored.

**[VERIFIED] DeepER (Ebraheem et al., PVLDB 2018, arXiv:1710.00597, doi 10.14778/3236187.3236198)** proposes LSH over *distributed representations of the whole tuple*:

> we propose a locality sensitive hashing (LSH) based blocking approach that uses distributed representations of tuples; **it takes all attributes of a tuple into consideration and produces much smaller blocks, compared with traditional methods that consider only a few attributes.**

That sentence is the whole argument for learned retrieval in your task: hand-picked keys only use the attributes you thought of; an embedding over the concatenated record uses all of them, including those that matter only in country #3.

**[VERIFIED] Non-Latin-script blocking is a known weak point.** A 2024 paper (Wang, Kong, Tao, Borthwick, Golac, Johnson, Hijazi, Deng, Zhang — "NLSHBlock", surfaced via the arXiv API under *entity matching* + *clustering*) introduces a new LSH framework "specifically designed for non-Latin script text", reporting improved results "particularly within the semi-supervised setting". Treat standard LSH on raw non-Latin codepoints as unreliable; normalise/romanise first (§6).

**[VERIFIED] Self-supervised representations beat task-specific pipelines and need no labels.** **Sudowoodo** (Li, Wang & Wang, arXiv:2207.04122):

> Contrastive learning enables Sudowoodo to learn similarity-aware data representations from a large corpus of data items... **without using any labels**. ... Sudowoodo also **outperforms previous best specialized blocking or matching solutions for EM**.

[MY INFERENCE] The "no labels" property is the key transferable part: train the *representation* on all three sources including the unseen country without any ground truth for that country, then fine-tune the *decision head* on the two labelled countries. That decouples "does this representation capture name+address structure in country 3" from "do I know what a match looks like in country 1".

### 1.4 Where the tooling actually stands

**[VERIFIED] `dedupe`** (https://docs.dedupe.io/) — "reads in human labeled data and comes up with the best rules for your dataset", including **blocking rules** and comparison weights. But **[VERIFIED] it has a hard scalability ceiling**: the MERAI paper (Kannangara et al., arXiv:2508.03767) reports "**Dedupe failed to scale beyond 2 million records due to memory constraints**", while their own pipeline reached 15.7M and beat both Dedupe and Splink on F1.

**[VERIFIED] `Splink`** (https://moj-analytical-services.github.io/splink/) is SQL-native (DuckDB/Spark/Postgres/Athena), does Fellegi–Sunter properly, and has excellent blocking/evaluation tooling. Its weakness for you: blocking is hand-written rules, not learned retrieval.

**[VERIFIED] Magellan** (https://github.com/anhaidgroup/magellan) — the current repo is effectively a **JS/TS stub** (0 stars, `package.json`, no Python `magellan` package on `main`). The Python MAGELLAN is historical; do not plan around it.

[MY INFERENCE] Practical build: **Splink or a DuckDB implementation for the scoring layer + blocking scaffolding**, plus a **custom learned retriever (embedding ANN or LSH) for stage 1**, plus a **custom clusterer with a size cap**. Don't make one library do all three.
## 2. Pairwise vs set-level (cluster) decisions

### 2.1 Why pairwise decisions are structurally insufficient

[VERIFIED] **ZeroER** (Wu, Chaba, Sawlani, Chu & Thirumuruganathan, SIGMOD 2020, arXiv:1908.06049, doi 10.1145/3318464.3389743) makes transitivity central to a *generative* model:

> ...we incorporate the **transitivity property into the generative model** in a novel way resulting in improved accuracy.

**Sudowoodo** (arXiv:2207.04122) frames the same idea as *consistency*: match decisions are not independent, and a set of mutually inconsistent pair decisions signals that the pairwise view is the wrong unit.

**[VERIFIED] Correlation clustering is the principled objective.** Lokhande, Wang, Singh & Yarkony (AAAI 2020, arXiv:1909.05460) model ER as correlation clustering / weighted set-packing, via an ILP with column generation:

> Traditional approaches tackle entity resolution with hierarchical clustering, which does not benefit from a formal optimization formulation. In contrast, we model entity resolution as correlation-clustering... we achieve state-of-the-art accuracy on two popular benchmark datasets.

Earlier ER-consistency work: Fisher & Wang, *"Unsupervised Measuring of Entity Resolution Consistency"*, ICDMW 2015 (doi 10.1109/icdmw.2015.162). [THIN — I retrieved the Crossref record (authors, venue, pages 218–221) but not the full text, so I am not characterising its findings.]

### 2.2 When set-level helps — specifically for you

[MY INFERENCE, grounded in the above + the metric definition]:

1. **Set-level decisions are the only way to enforce a *mutual-exclusion* constraint** that a precision-weighted metric rewards. If entity A cannot be linked to both B and C, then a top-2 candidate set containing both is *provably* wrong for at least one. Resolving this at the set level (competition/assignment) converts two half-right decisions into one clearly-right and one clean "no match". With β=0.5 that trade is strongly positive.
2. **Set-level decisions let you cap output size for free.** If the scorer prefers smaller candidate sets, you can enforce "at most k records per reference entity", resolved by best-score-wins. This is not expressible in a pairwise classifier at all.
3. **Transitivity gives extra evidence for free.** If A~B and B~C with high confidence, A~C is near-certain — extra positive evidence from *no* new comparisons, which matters because comparisons are your budget.

[VERIFIED] Splink's cluster-quality guide states the hard ceiling honestly:

> Blocking rules, necessary to make computations tractable, **can prevent record comparisons between some true matches ever being made**. Data limitations can place an upper bound on the level of quality achievable.

and flags large clusters as a review trigger: "if, for example, you already know that a large cluster (containing say 100 nodes) is suspicious for your deduplicated dataset."

[MY INFERENCE] **A cluster-size cap is a double win in your task**: it directly reduces candidate-set size (which is scored), and it blocks the chaining pathology (transitive closure over one mildly-wrong pair creates a giant wrong cluster, and every member is then wrong for you). A size-2 mistake puts 1 wrong record in your output; a size-10 cluster puts 9.
## 3. Cross-fitting, out-of-fold scoring, and nested validation

### 3.1 The core result

**[VERIFIED]** Varma & Simon, *"Bias in error estimation when using cross-validation for model selection"*, BMC Bioinformatics 7:91 (2006), doi 10.1186/1471-2105-7-91. The exact numbers are the argument:

> The CV error estimate for the classifier with the optimal parameters was found to be a **substantially biased estimate of the true error**... Even though there is no real difference between the two classes for the "null" datasets, the CV error estimate for the Shrunken Centroid with the optimal parameters was **less than 30% on 18.5%** of simulated training data-sets. For SVM with optimal parameters the estimated error rate was **less than 30% on 38%** of "null" data-sets. Performance of the optimized classifiers on the independent test set was **no better than chance**.

> **The nested CV procedure reduces the bias considerably and gives an estimate of the error that is very close to that obtained on the independent testing set.**

And the prescription:

> Proper use of CV for estimating true error of a classifier developed using a well defined algorithm requires that **all steps of the algorithm, including classifier parameter tuning, be repeated in each CV loop.**

[MY INFERENCE] Threshold selection is a *tuning step* by any reasonable definition. So picking your F0.5-optimal threshold on the same held-out set you report is exactly the Varma & Simon pathology, and it will overstate your score. With a small labelled set and a metric this threshold-sensitive, the overstatement can be several points.

### 3.2 The concrete recipe

[MY INFERENCE, implementing the Varma & Simon requirement]:

1. **Split by entity, not by pair.** Pairs sharing a reference entity are not independent; random pair-level CV leaks.
2. **Outer loop** = your honest estimate. Inside it, run *everything*: preprocessing, scorer, calibration, and **threshold selection**.
3. **Inner loop** = threshold selection on inner-validation scores only.
4. **Report the outer score.** Only that is defensible.
5. **For the final submission**, re-run the identical procedure on all labelled data to get the threshold to ship.

**Why this matters more here than in a normal task** [MY INFERENCE]: your metric is macro-averaged *per reference entity*, so it has high variance — one entity flipping from 0 to 1 moves the score a lot. Selecting a threshold on a noisy, high-variance estimate will both overfit and be unstable. Report a **bootstrap confidence interval over entities**, not a point estimate. If the CI is wide, your threshold choice is close to arbitrary, and you should say so.

[VERIFIED] A related trap: **parameter estimation is itself a fitted step.** Splink is explicit that EM estimates of `m` are computed on blocked data, that "Unlike blocking rules for prediction, it does not matter if Training Rules excludes some true matches — it just needs to generate examples of matches and non-matches", and that EM "seems to work best when the pairwise record comparisons are a mix of anywhere between around 0.1% and 99.9% true matches." [MY INFERENCE] So your `m` estimates must be produced *inside* the outer fold too, or your leakage is not just the threshold.
## 4. The unseen country: normalisation fallbacks, per-country parsing, what breaks

The least-covered area in the ER literature, and where careful engineering pays most. Here is what exists, and what does not.

### 4.1 What the literature actually supports

**[VERIFIED] Zero-shot transfer to unseen countries is demonstrated to work — for address parsing.** Yassine, Beauchemin, Laviolette & Lamontagne, *"Multinational Address Parsing: A Zero-Shot Evaluation"* (iJIST; arXiv:2112.04008):

> previous work on neural networks has only focused on parsing addresses from a single source country. This paper explores the possibility of **transferring the address parsing knowledge acquired by training deep learning models on some countries' addresses to others with no further training in a zero-shot transfer learning setting**. ... Both methods [attention, domain adversarial training] yield **state-of-the-art performance for most of the tested countries while giving good results to the remaining countries**.

[VERIFIED] This is the best precedent for your situation and the positive result is encouraging. But read the hedge: "**most** of the tested countries... **good** results to the remaining" is real degradation, not parity. [MY INFERENCE] The hedge also implicitly assumes script/locale transfer; if your third country uses a *different writing system* from countries 1 and 2, you are outside what this paper tested.

**[VERIFIED] Zero-shot / no-label matching specifically.** ZeroER (arXiv:1908.06049) claims: "On five benchmark ER datasets, we show that **ZeroER greatly outperforms existing unsupervised approaches and achieves comparable performance to supervised approaches**" — with *zero* labelled examples. Sudowoodo likewise learns representations with no labels. [MY INFERENCE] This is your safety net: since labels for the new country cannot exist (it is test), the *decision layer* must degrade to unsupervised rather than to a broken supervised model.

**[VERIFIED] Benchmarks systematically underestimate this difficulty.** Wang et al., *"Bridging the Gap between Reality and Ideality of Entity Matching"* (IJCAI 2022, arXiv:2205.05889) is directly on point:

> The assumptions made in the previous benchmark construction process are **not coincidental with the open environment**, which conceal the main challenges of the task and therefore **significantly overestimate the current progress of entity matching**.

They identify the specific unrealistic assumptions: **restricted entities, balanced labels, and single-modal records**. [MY INFERENCE] All three are things your challenge violates by design (unseen country = new entity population; real match rates ≠ 50%; three differently-noisy sources = multimodal). So treat *every* published accuracy number — including mine — as an upper bound for your test set.
### 4.2 What breaks, concretely

[MY INFERENCE, from the verified sources above — this table is my reasoning, not source claims]:

| Breaks | Because | Mitigation |
|---|---|---|
| **Address component parsing** | Address grammar is country-specific; a parser trained on countries 1–2 will mislabel components in country 3 | Use a script- and country-agnostic parser, or hand-rules for the new country. Prefer comparing *whole normalised address strings* over component-wise features where components are unreliable. |
| **Term-frequency (TF) adjustments** | Match weight uses `log2(m/u)`; `u` depends on the *value distribution of the corpus*. A new country has a different distribution, so **`u` learned on countries 1–2 is wrong for country 3** | Either estimate `u` per-country on the new country's own unlabelled data (random sampling suffices, no labels needed), or drop TF weighting for the new country. |
| **Fuzzy string comparators** | Levenshtein/Jaro-Winkler operate on codepoints; scripts without spaces, with combining marks, or right-to-left ordering distort them | Normalise (NFKC) and optionally romanise (§6) before fuzzy comparison. |
| **Address-derived blocking keys** | If the address format changes, an address-based key may become near-constant → massive skew → you blow your budget precisely on the hardest split | Anchor blocking primarily on **name**; use address as a secondary rule. Measure per-rule comparison counts *per country*. |
| **Any absolute score threshold** | The score→probability mapping shifts when the value distribution shifts | Re-estimate on the new country, or switch to a rank/count-based rule instead of an absolute score cut. Support: Lipton et al. (§5) show the optimal threshold depends on calibration. |

### 4.3 Normalisation fallbacks — build a ladder, not a single path

[MY INFERENCE, informed by [VERIFIED] ZeroER and the zero-shot address-parsing result — i.e. "always have a no-label fallback"]:

1. **Primary:** trained scorer from countries 1–2.
2. **Fallback A (label-free):** ZeroER- or Sudowoodo-style unsupervised model fit on the new country's own unlabelled data. [VERIFIED] these reach supervised-comparable accuracy.
3. **Fallback B (no model):** conservative high-precision rules (exact normalised name + matching postcode/region, or high fuzzy name + high fuzzy address) with a *high* threshold. [MY INFERENCE] under β=0.5, a rule that only fires on near-certain matches is metric-optimal even at poor recall.

**[VERIFIED] Supporting infrastructure.** **libpostal** (https://github.com/openvenues/libpostal) "is a C library for parsing/normalizing street addresses around the world using statistical NLP and open data", covering a wide set of countries, reporting "99.45% full parse accuracy" on held-out test data, and listing ~30 supported languages including non-Latin-script cases. It also warns: "If the address parser isn't working well for a particular country, language or style of address, chances are that some name variations or places being missed/mislabeled during training data creation." [MY INFERENCE] — for a genuinely new country the *cheap* fix may be adding address-format data, not retraining a model. Also worth considering [VERIFIED, doi 10.18653/v1/2024.findings-acl.362]: *GeoAgent*, using an LLM with geospatial tools for address standardization. And [VERIFIED] Splink's user base includes "The Shared Child Health Record project in Lao PDR [which] used Splink to de-duplicate pediatric records in a **non-Latin script context**" — real-world evidence that this approach deploys.
## 5. Threshold selection for a precision-weighted macro metric with singletons in the denominator

### 5.1 Get the metric exactly right first

**[VERIFIED]** Splink's edge-metrics guide (https://moj-analytical-services.github.io/splink/topic_guides/evaluation/edge_metrics.html) gives the general form:

> `F_β = (1+β²)·Precision·Recall / (β²·Precision + Recall)` ... For example, when Precision and Recall are equally weighted (β=1), we get F1 ... Other popular versions are **F2 (Recall twice as important than Precision) and F0.5 (Precision twice as important than Recall)**

⚠️ **[MY INFERENCE — correcting a likely misreading]** With β=0.5 the harmonic-mean weights are `β²=0.25` on precision and `1` on recall, so **precision is weighted 4× recall**. That matches the ~4× false-merge penalty in your task description. Splink's prose "twice as important" is a loose gloss, not the arithmetic. **Use the formula, not the prose.**

**[VERIFIED]** Splink also warns about a property that bites exactly here:

> **Warning:** F-score does not account for class imbalance in the data, and is **asymmetric** (i.e. it considers the prediction of matching records, but ignores how well the model correctly predicts non-matching records).

[MY INFERENCE] Your metric repairs that asymmetry by scoring singletons (empty = 1.0, any = 0.0) — so **abstention is part of the metric**. A plain pairwise F0.5 is *not* your metric and will pick a threshold that is too low.

### 5.2 The theoretical result you should actually use

**[VERIFIED]** Lipton, Elkan & Narayanaswamy, *"Thresholding Classifiers to Maximize F1 Score"* (arXiv:1402.1892) derive, for any classifier producing a real-valued output, **the relationship between the best achievable F-score and the threshold achieving it**:

> As a special case, **if the classifier outputs are well-calibrated conditional probabilities, then the optimal threshold is half the optimal F1 score.** As another special case, if the classifier is **completely uninformative**, then the optimal behavior is to **classify all examples as positive**.

Three consequences [MY INFERENCE]:
- The optimal threshold is a **derived quantity**, not a swept hyperparameter. If your scorer is calibrated, `t* ≈ F*_β / 2`. This gives a principled starting point and a self-consistency check.
- **"Classify everything positive" is optimal for an uninformative classifier.** Your singleton rule (empty = 1.0, any = 0.0) is the metric's structural answer to this pathology — which is exactly why the abstention option is load-bearing, and why an abstention-capable model beats a pure ranker.
- Everything hinges on **calibration**. Uncalibrated scores (typical for GBMs on class-imbalanced data, and *especially* after a distribution shift to a new country) invalidate the ½ rule. [VERIFIED] Splink's `match probability = 2^MW/(1+2^MW)` mapping is one way to get a calibrated score out of Fellegi–Sunter match weights. [VERIFIED, doi 10.1371/journal.pone.0118432] PR curves beat ROC curves on imbalanced data — a reason to recalibrate on the new country before trusting any absolute threshold.

### 5.3 The practical algorithm

[MY INFERENCE, assembling the verified pieces]:

1. Build the **exact** scorer metric, including: per-entity F0.5, empty prediction = 1.0, any prediction on a true singleton = 0.0.
2. Get **out-of-fold** scores for every candidate pair (the cross-fitting from §3).
3. For each candidate threshold, and **separately per country**, compute the metric.
4. Pick the threshold maximising the macro score — but **select it inside the inner CV loop** only.
5. **Prefer a per-entity output cap over a lower threshold** if the curve is flat: capping costs less macro-F than the extra false merges do, and it also satisfies the "smaller candidate set ranks higher" bonus.

## 6. Transliteration, abbreviations, DBA/trade names, leetspeak

The thinnest-evidence area. Being explicit about that.

**[VERIFIED] Transliteration — strong, directly useful tool.** Hermjakob, May & Knight, *"Out-of-the-box Universal Romanization Tool uroman"* (ACL 2018 demos, doi 10.18653/v1/P18-4003):

> a tool for converting text in myriads of languages and scripts such as Chinese, Arabic and Cyrillic into a common Latin-script representation... handles nearly all character sets, including some that are quite obscure such as Tibetan and Tifinagh. uroman converts digital numbers in various scripts to Western Arabic numerals. **Romanization enables the application of string-similarity metrics to texts from different scripts without the need and complexity of an intermediate phonetic representation.**

[MY INFERENCE] The clause "without the need and complexity of an intermediate phonetic representation" is the actionable bit for you: **romanise, then use ordinary string similarity.** You do not need a language-specific phonetic algorithm. Also: convert native digits to Western Arabic numerals — otherwise `١٢٣` and `123` are non-matches that silently poison both blocking and scoring.

**[VERIFIED] Transliteration variation is a named problem in a deployed, linguistically diverse system.** SGER (Chourasia, Kapoor & Patil, ACL 2026 Industry Track, arXiv:2605.23597, doi 10.18653/v1/2026.acl-industry.101), deployed at Dream11 serving 250M+ users on Indian identity data, frames its problem as:

> Variations in naming conventions, **inconsistent transliteration across scripts**, and frequent data entry errors make it difficult to unify user identities.

[MY INFERENCE] So "inconsistent transliteration" is a real, documented failure mode in exactly your kind of deployment. Practical consequence: **keep both the original script and the romanised form as features**, because two sources may romanise the same name differently. A single canonical form discards information.

**[VERIFIED] Abbreviations** — I found **no** ER-specific abbreviation-handling literature in the accessible indexes ([GAP]; arXiv `abs:"entity resolution" AND abs:"abbreviation"` returns 0 hits). Closest adjacent work is generic abbreviation/thesaurus mining (e.g. doi 10.1109/wi.2006.119) and leetspeak normalisation, which is studied in **toxicity/abuse detection, not ER** (e.g. doi 10.21428/594757db.cd61e1d6, doi 10.21928/uhdjst.v10n2y2026.pp134-152 — [VERIFIED] these exist and sit in the abuse-detection literature, [THIN] on their relevance to us). [MY INFERENCE] For your data: abbreviations and DBA markers are *domain knowledge*, and the right move is an explicit hand-built normalisation list plus a "strip known business-suffix tokens" rule — treat it as feature engineering, not a literature-following step. Do **not** use phonetic algorithms (Soundex/Metaphone) for business names: they were designed for surnames and will collapse distinct company names. [MY INFERENCE, standard practice.]

**[VERIFIED] Company/organisation name matching — genuinely relevant literature exists, focused on aliases.**
- **CompanyName2Vec** (Ziv, Gronau & Fire, arXiv:2201.04687) learns company-name semantics from an *unlabelled* job-ad corpus, "without relying on any information on the matched company besides its name", reporting "an average success rate of 89.3%". [MY INFERENCE] the job-ad-corpus idea transfers if you have any co-occurring business text; the "no labels needed" property is the appealing part.
- **Terrorizer** (arXiv:2403.12083), on patent assignees, describes exactly the alias problem:
  > multinational corporations which file patents under **a plethora of names, including alternate spellings of the same entity** and, eventually, **companies' subsidiaries**.
  and notes prior approaches "rel[ied] on labor-intensive **dictionary based or string matching** approaches". [MY INFERENCE] "dictionary based" is precisely the DBA/trade-name problem, and the paper's framing confirms it is *not* solved by better string similarity.
- **JEL** (JPMorgan Chase, arXiv:2411.02695, doi 10.1609/aaai.v35i17.17796) is entity *linking*, adjacent but reports a relevant caution: "several techniques exist for entity linking, they are **tuned for entities that exist in Wikipedia, and fail to generalize for the entities that are of interest to an enterprise**." [MY INFERENCE] Same failure mode as your unseen country, stated by practitioners.

**[THIN] Leetspeak specifically in ER**: no ER literature found. [MY INFERENCE] If your new country has a community that obfuscates business names in registries, treat it as (a) a character-level normalisation feature and (b) a reason *not* to hard-block on a strict transliteration. Note [VERIFIED] DeepER works on *character*-level LSTM encoders, which is structurally leetspeak-robust, whereas a token-level-only featuriser would not be.
## 7. Documented pitfalls

Each pitfall is [VERIFIED] as a source claim unless marked otherwise.

1. **Threshold-selected-then-evaluated bias.** Varma & Simon (doi 10.1186/1471-2105-7-91): CV error for a CV-tuned classifier was "a substantially biased estimate"; on null data, estimated error <30% on 18.5% (centroids) / 38% (SVM) of runs, with test performance "no better than chance". *All* tuning, including the threshold, must be inside the fold. → §3
2. **Conditional independence is false in practice.** Splink's training rationale: "The Fellegi-Sunter model assumes columns are independent conditional on match status, which is **rarely true in practice**." Consequence: match weights are not probabilities. [MY INFERENCE] they remain excellent *ranking* features. [VERIFIED] Also EM blocking bias: "This trick is vulnerable to the criticism that we may get a biased selection of matching records."
3. **EM needs a balanced-ish pair sample.** Splink: EM "seems to work best when the pairwise record comparisons are a mix of anywhere between around **0.1% and 99.9%** true matches. It works less efficiently if there is a huge imbalance." → don't run EM on unblocked data.
4. **Blocking silently caps achievable quality.** Splink: blocking rules "can prevent record comparisons between some true matches **ever being made**. Data limitations can place an upper bound on the level of quality achievable." → measure retriever recall against held-out known matches and report it.
5. **Skew destroys the budget.** Splink: 10,000 records sharing one block value ⇒ 49,995,000 comparisons. → §1.2.
6. **F-score is asymmetric and ignores imbalance.** Splink's explicit warning (§5.1). Never tune on a plain F0.5.
7. **Benchmarks overestimate real performance.** Wang et al. (arXiv:2205.05889): restricted-entity / balanced-label / single-modal assumptions are unrealistic and "significantly overestimate the current progress of entity matching." → all published numbers are upper bounds.
8. **Dedupe does not scale past ~2M records.** Kannangara et al. (arXiv:2508.03767): "Dedupe failed to scale beyond 2 million records due to memory constraints." → don't make dedupe your production path.
9. **Off-the-shelf tools leave accuracy on the table.** The same paper found their pipeline "outperforms both baseline systems in terms of matching accuracy, with consistently higher F1" — Dedupe and Splink were beaten even at moderate scale.
10. **Human review only surfaces problems if you look at clusters.** Splink: graph metrics "can also help us home in on problematic clusters, such as those containing inaccurate links (false positives)". Given the scorer prefers small candidate sets, a large-cluster check is a cheap FP detector.
11. **Naive string matching on company aliases is a dead end.** Terrorizer (arXiv:2403.12083): reliance on "dictionary based or string matching" left the problem "mostly unresolved" given alias/subsidiary sprawl.
12. **Magellan is not usable as a Python library today.** [VERIFIED] github.com/anhaidgroup/magellan `main` is a JS/TS stub (0 stars).
13. **Wikipedia-flavoured entity linking generalises badly to enterprise entities.** JEL (arXiv:2411.02695, JPMorgan Chase). [MY INFERENCE] same lesson as the unseen country, stated by practitioners.
14. **Fellegi–Sunter needs proper `m`/`u` estimation.** Splink's three-step rationale: estimate `λ` (probability two random records match), then `u` by **random sampling of pairs** ("two random records, they will almost certainly not be a match... this step is usually straightforward and reliable"), then `m` by EM on blocked data. [VERIFIED] EM needs multiple passes because blocking on a column forces it to be equal, so a second pass must block on something else. [VERIFIED] Splink's own failure anecdote is a good data-quality check: convergence problems are "often due to data quality issues e.g. **mr and mrs in first_name**".
## 8. What I could not find — read this before relying on a gap

- **[GAP] WSDM Cup 2020 Track 1 (entity matching).** `wsdmcup2020.github.io` returns 404 and has no Wayback snapshot; the Google Sites mirror requires sign-in. I could not retrieve the task description, metric, or any solution write-up. [VERIFIED] the WSDM Cup has produced entity-resolution tracks and that overview papers appear on arXiv (e.g. arXiv:1712.08081 for the 2017 Triple Scoring task), so look there — but **I have read no WSDM-2020-specific source.**
- **[GAP] Recruit RVL-CDMC cross-lingual ER challenge.** Multiple routes (Bing, OpenAlex title search, Crossref) returned nothing. The challenge is commonly cited in cross-lingual ER work, but **I have no verified URL and make no claims about its metric or winners.**
- **[GAP] IEEE Big Data ER competition.** No verified source found.
- **[GAP] Kaggle competitions of this exact shape.** No verified source found.
- **[GAP] A single source on DBA/trade-name normalisation for ER.** Adjacent evidence only (Terrorizer, CompanyName2Vec). This looks like a genuine hole in the literature, not a gap in my search.
- **[GAP] Out-of-fold / cross-fitting *as practised in ER*.** arXiv `abs:"entity resolution" AND abs:"out-of-fold"` → 0 hits. The method is standard statistics (Varma & Simon), but **ER papers do not appear to discuss it.** [MY INFERENCE] you get the benefit without inheriting ER-specific bad habits — but nobody has published ER-specific guidance.
- **[THIN] Fisher & Wang, "Unsupervised Measuring of Entity Resolution Consistency"** (ICDMW 2015, doi 10.1109/icdmw.2015.162) — record confirmed (authors, venue, pages 218–221) but **not** its findings. Read before citing.
- **[THIN] NLSHBlock** — authors and an abstract fragment recovered via an arXiv API listing, but no resolvable arXiv identifier (title search returns 0 hits, suggesting a non-arXiv venue). Attribution provisional.
- **[THIN] Leetspeak and abbreviations in ER** — no ER literature located; adjacent work is in abuse detection. See §6.

---

## 9. Full source list

**Surveys & theory**
- Papadakis, Skoutas, Thanos, Palpanas. *A Survey of Blocking and Filtering Techniques for Entity Resolution.* arXiv:1905.06167 / ACM CSUR doi 10.1145/3377455 — https://arxiv.org/abs/1905.06167 · full text https://ar5iv.labs.arxiv.org/html/1905.06167
- Fellegi & Sunter. *A Theory for Record Linkage.* JASA 1969. doi 10.1080/01621459.1969.10501049
- Christen. *Frameworks for entity matching: A comparison.* Data & Knowledge Engineering 2009. doi 10.1016/j.datak.2009.10.003
- Fisher & Wang. *Unsupervised Measuring of Entity Resolution Consistency.* ICDMW 2015. doi 10.1109/icdmw.2015.162 **[THIN]**
- Meta-blocking: Papadakis et al. TKDE 2013. doi 10.1109/TKDE.2013.54 · Supervised meta-blocking, PVLDB 2014. doi 10.14778/2733085.2733098
- *Record linkage* (overview, history, terminology, criticism) — https://en.wikipedia.org/wiki/Record_linkage

**Validation / thresholding**
- Varma & Simon. *Bias in error estimation when using cross-validation for model selection.* BMC Bioinformatics 7:91 (2006) — https://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-7-91
- Lipton, Elkan, Narayanaswamy. *Thresholding Classifiers to Maximize F1 Score.* arXiv:1402.1892 — https://arxiv.org/abs/1402.1892
- Saito & Rehmsmeier. *The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets.* PLOS ONE 2015. doi 10.1371/journal.pone.0118432

**Representations, retrieval, label-free learning**
- Ebraheem et al. *DeepER — Deep Entity Resolution.* arXiv:1710.00597 / PVLDB doi 10.14778/3236187.3236198
- Wu et al. *ZeroER: Entity Resolution using Zero Labeled Examples.* SIGMOD 2020. arXiv:1908.06049 · doi 10.1145/3318464.3389743
- Li, Wang & Wang. *Sudowoodo: Contrastive Self-supervised Learning for Multi-purpose Data Integration and Preparation.* arXiv:2207.04122
- Kannangara et al. *A Robust and Efficient Pipeline for Enterprise-Level Large-Scale Entity Resolution (MERAI).* arXiv:2508.03767
- Wang et al. *Bridging the Gap between Reality and Ideality of Entity Matching.* IJCAI 2022. arXiv:2205.05889
- *Pre-Trained Embeddings for Entity Resolution: An Experimental Analysis.* PVLDB doi 10.14778/3598581.3598594 (arXiv:2304.12329)
- *Improving the Efficiency and Effectiveness for BERT-based Entity Resolution.* AAAI 2021. doi 10.1609/aaai.v35i15.17562
- *Low-resource Deep Entity Resolution with Transfer and Active Learning.* ACL 2019. doi 10.18653/v1/p19-1586

**Clustering / set-level**
- Lokhande, Wang, Singh & Yarkony. *Accelerating Column Generation via Flexible Dual Optimal Inequalities with Application to Entity Resolution.* AAAI 2020. arXiv:1909.05460
- Raghavan et al. *Collective entity resolution in relational data.* SIGMOD 2007. doi 10.1145/1217299.1217304
- *Graph-based hierarchical record clustering for unsupervised entity resolution (GDWM).* arXiv:2112.06331

**International / non-Latin / addresses**
- Yassine, Beauchemin, Laviolette & Lamontagne. *Multinational Address Parsing: A Zero-Shot Evaluation.* arXiv:2112.04008
- Hermjakob, May & Knight. *Out-of-the-box Universal Romanization Tool uroman.* ACL 2018 — https://aclanthology.org/P18-4003/
- openvenues. *libpostal* — https://github.com/openvenues/libpostal
- *GeoAgent: To Empower LLMs using Geospatial Tools for Address Standardization.* ACL Findings 2024. doi 10.18653/v1/2024.findings-acl.362
- Chourasia, Kapoor & Patil. *Structure-Guided Entity Resolution* (SGER). ACL 2026 Industry Track. arXiv:2605.23597 · doi 10.18653/v1/2026.acl-industry.101

**Company / organisation names**
- Ziv, Gronau & Fire. *CompanyName2Vec: Company Entity Matching Based on Job Ads.* arXiv:2201.04687
- *Presenting Terrorizer: an algorithm for consolidating company names in patent assignees.* arXiv:2403.12083
- Ding et al. *JEL: Applying End-to-End Neural Entity Linking in JPMorgan Chase.* arXiv:2411.02695 · doi 10.1609/aaai.v35i17.17796

**Tooling & documentation**
- Splink — https://moj-analytical-services.github.io/splink/ — specifically: [What are Blocking Rules?](https://moj-analytical-services.github.io/splink/topic_guides/blocking/blocking_rules.html) · [Model Training Blocking Rules](https://moj-analytical-services.github.io/splink/topic_guides/blocking/model_training.html) · [Training rationale](https://moj-analytical-services.github.io/splink/topic_guides/training/training_rationale.html) · [The Fellegi-Sunter Model](https://moj-analytical-services.github.io/splink/topic_guides/theory/fellegi_sunter.html) · [Why do we need record linkage?](https://moj-analytical-services.github.io/splink/topic_guides/theory/record_linkage.html) · [Edge Metrics](https://moj-analytical-services.github.io/splink/topic_guides/evaluation/edge_metrics.html) · [Model evaluation](https://moj-analytical-services.github.io/splink/topic_guides/evaluation/model.html) · [Clusters overview](https://moj-analytical-services.github.io/splink/topic_guides/evaluation/clusters/overview.html) · [Feature engineering](https://moj-analytical-services.github.io/splink/topic_guides/data_preparation/feature_engineering.html) · [Run times & performance](https://moj-analytical-services.github.io/splink/topic_guides/performance/drivers_of_performance.html) · [Blocking tutorial](https://moj-analytical-services.github.io/splink/demos/tutorials/03_Blocking.html)
- Splink paper: Linacre, Lindsay, Manassis, Slade, Hepworth, Kennedy & Bond. *Splink: Free software for probabilistic record linkage at scale.* IJPDS 7(3) 2022. doi 10.23889/ijpds.v7i3.1794
- dedupe — https://docs.dedupe.io/ · https://github.com/dedupeio/dedupe
- anhaidgroup. *Magellan* — https://github.com/anhaidgroup/magellan **[VERIFIED: currently a JS/TS stub, not the historical Python library]**

---

## 10. If you only read five things

1. **Papadakis et al. blocking survey** (§1.1) — the PC/PQ/RR vocabulary and the recall-vs-selectivity framing. Everything in §1 hangs off it.
2. **Splink blocking rules + blocking tutorial** (§1.2) — the concrete "many tight rules, deduplicated, control skew, here is your comparison budget" recipe, with numbers.
3. **Varma & Simon 2006** (§3.1) — why threshold selection must be nested, with the numbers that make it convincing.
4. **Lipton et al. 2014** (§5.2) — the calibrated-threshold-is-half-the-F1 rule, and the "uninformative classifier should predict all positive" result that explains why your singleton rule exists.
5. **Wang et al. 2022, "Bridging the Gap between Reality and Ideality"** (§4.1) — the paper that says published ER numbers are optimistic because benchmarks are unrealistic, and names exactly which unrealistic assumptions your challenge violates.

---

---

---
