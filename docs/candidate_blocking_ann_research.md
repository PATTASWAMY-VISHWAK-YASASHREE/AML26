# Candidate Blocking and ANN Retrieval for a Small Entity-Resolution Corpus

## Scope and decision

This note targets the stated setting: `S1` reference records, searchable `S2`/`S3` records, fields `entity_id`, `business_name`, `business_address`, and `country`; test adds France; the metric is macro per-`S1` F0.5 over empty, singleton, and multi-match truth sets; no external lookup is allowed at inference.

**Recommendation:** for a genuinely small target corpus, make the **full cross-source Cartesian product the correctness reference and, while it fits the local time/memory budget, the default candidate generator**. Do not introduce ANN, learned blocking, or hard country blocks merely because entity resolution is usually large-scale. Use a deterministic union of sparse inverted-index and character-n-gram candidate channels for the production subset. Measure the oracle F0.5 ceiling and per-`S1` **full-set** recall at every retrieval budget; choose the smallest budget that preserves the required recall. HNSW/FAISS/Pinecone are scale escape hatches, not the first design choice here.

This follows the blocking/filtering distinction in the primary survey by Papadakis et al. and Christen's indexing survey: blocking restricts comparisons, while filtering returns pairs satisfying a known similarity predicate [1, 2].

## 1. Why exact exhaustive retrieval is the right baseline

Let `Q = |S1|` and `B = |S2| + |S3|`. Exhaustive retrieval creates exactly `Q*B` cross-source pairs. Measure that count first, rather than relying on a corpus-size folklore cutoff.

- If `Q*B` is small enough to score in one batch (for this task, a practical engineering starting point is at most about **5 million pairs**, then adjusted after measurement), score all of them. This eliminates a second layer of approximation and gives a clean recall ceiling of 1.0 with respect to the searchable corpus.
- If the pair count is too large for the pair classifier, exhaustive **retrieval** can still remain possible with vectorized exact similarities. FAISS `IndexFlatIP`/`IndexFlatL2` performs exhaustive search and is the exact baseline; FAISS explicitly documents flat indexes as exact brute-force search [3, 4]. Use normalized vectors and inner product for cosine, or L2 for squared Euclidean distance.
- Keep an exact top-k result for a realistic query sample. It is required ground truth for any later ANN recall measurement.

The 5-million threshold is a suggested operational starting point, not a literature result. Record actual wall time, peak memory, and the largest query; revise the cutoff. The task has no latency constraint, so the real stopping rule is feasibility plus candidate recall, not query milliseconds.

The literature repeatedly identifies all-pairs comparison as the quadratic baseline that blocking is designed to avoid [1, 2, 5]. That efficiency argument is weak when the Cartesian product is already small enough to run.

## 2. Production candidate cascade

All records are indexed on the searchable side (`S2` and `S3` together), while every `S1` is queried against that index. Never exclude an unseen country; country may be a feature, not a hard block.

### 2.1 Deterministic normalization

1. Parse IDs as strings and preserve missing/empty values explicitly.
2. Normalize Unicode consistently (for example, NFKC or NFKD plus a documented case-folding/accent policy), lowercase, replace punctuation with spaces, collapse whitespace, and normalize numeric tokens.
3. Produce both:
   - a **compact comparison string** (for example, alphanumeric characters only), used for character shingles and edit-distance deletion neighborhoods; and
   - an ordered **token list** (including numeric tokens), used for token overlap and inverted indexes.
4. Keep the normalizer version in the retrieval manifest. Unicode policy should be selected from training-only data, frozen before outer validation, and applied unchanged to France.

The address and name should have separate normalizers/indices; punctuation, unit designators, and word order should not be globally rewritten without evidence.

### 2.2 Channel A: exact keys and token inverted indexes

Build these deterministic posting maps over `S2 ∪ S3`:

| Posting key | Query key(s) from `S1` | Purpose |
|---|---|---|
| `N_EQ` | full normalized name | exact legal-form/entity spelling |
| `N_TOK_ALL` | all non-empty name tokens | reordered names, legal suffix/noise changes |
| `N_TOK_RARE` | 2–3 lowest-DF name tokens | strong, low-volume shared tokens |
| `N_PREFIX` | first 3 and last 3 alphanumeric characters of compact name | suffix/prefix errors, order changes |
| `A_EQ` | full normalized address | exact relocation/format variants |
| `A_TOK_RARE` | 2–3 lowest-DF nonnumeric address tokens | renamed street/building variants |
| `NUM_POSTAL` | postal/PIN token | high-value structured address signal |
| `NUM_STREET` | house number + one rare street token | tolerant to address formatting/order |

Implementation rules:

- Use a token-frequency cutoff learned from the current fold's searchable corpus, not labels. Suggested first sweep: drop tokens with document frequency above **20%** from the `RARE` channels, but retain them in full-token overlap scoring.
- Score posting candidates with additive exact evidence (e.g. weighted token Jaccard/Dice/overlap, exact-name flag, exact-address flag, and numeric conflicts). This is ranking evidence, not truth.
- Union postings across channels and deduplicate by target ID. Keep a bit mask showing which channels found each candidate; this supports ablation and debugging.
- Prefer exact posting lookup over a single full-name block. A common n-gram such as `^in` can dominate the pair count while adding no discriminative value.

Christen describes standard blocking as an inverted index from generated blocking key values to record identifiers, and multi-key approaches as a way to reduce sensitivity to a particular key [2].

### 2.3 Channel B: character n-gram overlap

Generate character q-grams as a **set**, not a bag:

- name: `q=3` and `q=4` (start here);
- compact address: `q=3` and `q=4`;
- optionally word 2-grams and 3-grams for name tokens, with a padding marker if word boundaries matter.

For a name or address, count shared q-grams per candidate and retain candidates satisfying any of:

- one shared 4-gram (very high recall, potentially noisy);
- at least two shared 3-grams;
- q-gram Dice/Jaccard above a threshold validated on fold-internal data.

Do **not** use a single shared 3-gram as the only criterion. A union channel is acceptable because the final classifier is cheap relative to missing a true edge, but a single common 3-gram can create a large low-quality tail.

The primary ER survey describes q-gram blocking as more noise-tolerant than exact standard blocking but less selective; combining q-grams reduces candidate count at some possible recall cost [1]. Xiao et al. provide a more formal exact-similarity-join foundation: for token sets `x,y` with overlap `O(x,y)`, Jaccard threshold `t` implies

`O(x,y) >= ceil(t * (|x| + |y|) / (1 + t))`.

This overlap constraint motivates an inverted index whose postings can be counted and, if desired, prefix-filtered [6]. The same counting implementation works for character shingles.

### 2.4 Channel C: MinHash LSH (optional)

MinHash estimates set Jaccard similarity; LSH banding turns a threshold-shaped retrieval rule into buckets. Broder introduced the resemblance/containment framework [7], and Charikar formalized min-wise independent LSH for set similarity [8].

For signatures split into `b` bands of `r` rows, ideal collision probability is

`P(s) = 1 - (1 - s^r)^b`.

For conservative small-corpus retrieval, test these exact settings on character 3-gram and 4-gram sets:

- **A:** `num_perm=128`, `b=32`, `r=4`: `P(0.5)=0.873`, `P(0.6)=0.988`.
- **B:** `num_perm=256`, `b=64`, `r=4`: `P(0.5)=0.984`, `P(0.4)=0.810`.
- **C:** deliberately aggressive `num_perm=128`, `b=37`, `r=3` (111 of 128 permutations used): `P(0.5)=0.993`, but many false collisions at `P(0.3)=0.637`.

These probabilities follow the standard ideal MinHash/banding model; actual collision rates should be checked against exact sets. Use the same fixed seed/hash family in every fold and inference run. Pin explicit `(b, r)` rather than relying on a library optimizer. Verify every collision against exact q-gram Jaccard and retain only exact-Jaccard `>= t` (or keep the collision as a candidate if the objective is high recall). MinHash LSH has both false positives and false negatives; it cannot enforce the exact threshold itself [9].

Because the target corpus is small, MinHash LSH is a **diagnostic or scaling fallback**, not a better default than exact overlap counting.

### 2.5 Channel D: deletion neighborhoods (only for short strings)

A `d`-deletion neighborhood contains a string and all strings obtained by deleting up to `d` characters. For short canonical fields, strings within a stated edit-distance threshold can share a deletion signature; the generated neighbor must still be verified with the exact metric. Mishra et al. use deletion neighborhoods for edit-distance string similarity search and report major speedups, with space traded for query time [10].

Practical limits:

- Apply only to normalized names, legal-form words, or compact short address components.
- Suggested first sweep: `d=1` for names of length 8–32 characters; `d=2` only for strings of length at most 16.
- Stop expanding when the number of variants exceeds a fixed cap (for example 2,000) or the string exceeds the configured length.
- Do not apply to long free-form addresses; deletion variants grow rapidly and the key space becomes noisy.
- Bucket by `(field, source_family, deletion_variant, edit_radius)`; do not conflate name and address variants.
- Always verify with the same Levenshtein/Damerau metric used by the classifier.

This channel is also not necessary when exhaustive normalized Levenshtein scoring is already affordable. Its advantage appears only for short strings and larger searchable dictionaries.

### 2.6 Sorted neighborhood (secondary)

Sort `S2 ∪ S3 ∪ S1` by a frozen canonical blocking key and compare records within a window. Run at least two passes:

1. normalized name;
2. compact address (or `name | address` when a combined lexical key is stable).

Suggested first sweep `w ∈ {5, 10, 20, 50}`; choose by fold-internal full-set recall and candidate count. Hernández and Stolfo introduced the merge/purge formulation and sorted-neighborhood approach [11]. The primary survey notes robustness to errors near the end of keys but also a difficult, size-dependent window choice [1].

Sorted-neighborhood is not mutually exclusive with inverted indexes: union its candidates with Channels A–C.

### 2.7 Do not use country equality as a hard block

Training countries are US and India; France is unseen. Exact-country blocks can silently remove the relevant test candidates. Country equality, inequality, and missingness can be generic pair features, while all retrieval channels remain global. A two-pass strategy is acceptable only if every pass has a global fallback and the fallback is included in the final recall report.

## 3. Ranking, deduplication, and candidate budgets

### 3.1 Union first, cap last

For every `S1`, union candidates from all enabled channels, then rank with a deterministic composite retrieval score. A transparent starting score is:

`0.40 * name_char_dice + 0.25 * name_token_dice + 0.20 * address_char_dice + 0.10 * address_token_dice + 0.05 * structured_numeric_score`

where missing fields contribute zero only after a missingness flag is retained for the classifier. This weighting is an experiment seed, not a literature constant; fit/choose it on training folds.

Deterministic finalization:

1. score descending with a fixed rounding precision (e.g. 12 decimals);
2. target ID ascending as the tie-break;
3. source (`S2`, then `S3`) as an earlier stable key if desired;
4. deduplicate by `(S1_id, S2_or_S3_id)`;
5. write the final `candidate_pairs.tsv` sorted by the same tuple.

Store the source/channel bit mask and component scores in an internal audit table. The final model receives exactly the persisted candidate rows and may only accept/reject them.

### 3.2 Budget sweep

Evaluate the uncapped union first, then:

- per-`S1`, **per-source** caps `{50, 100, 250, 500, 1000}`;
- and optional global caps `{100, 250, 500, 1000, 2500}`.

Per-source caps are necessary because one large source can crowd out the other. A cap of 100 is not automatically safe: if an entity has multiple true targets, missing even one candidate is harmful. Increase a cap when a target's **full truth set** is not covered; candidate recall and the official metric matter more than compactness.

## 4. Required retrieval diagnostics

Compute these on every leakage-safe fold and pool by source, country, truth cardinality (`0`, `1`, `2+`), field missingness, and candidate count.

### 4.1 Pair and entity recall

Let `G_i` be the truth set for reference `i`, and `C_i` its candidate IDs.

- **Positive-edge recall:** `sum_i |G_i ∩ C_i| / sum_i |G_i|` (all truth sets are empty, so this is undefined only if the denominator is zero).
- **Full-set recall:** `mean_{i: |G_i|>0} [G_i ⊆ C_i]`.
- **Full-hit rate over all references:** `mean_i [G_i ⊆ C_i]`; this counts all singleton truths as one if retrieved.
- **Candidate-free references:** `mean_i [|C_i|=0]`.
- **Orphan true edges:** total `sum_i |G_i \ C_i|` and the worst affected entities.

Pair recall alone is insufficient: with truth size 3, retrieving 2 of 3 gives 0.667 edge recall but 0 full-set recall.

### 4.2 Efficiency and cost

- total unique candidate pairs;
- mean/median/p90/p99/max candidates per `S1` and per source;
- candidates per non-empty truth set;
- candidate generation and exact-similarity wall time;
- peak memory and temporary disk;
- reduction ratio `1 - |C| / (Q*B)` (the survey's RR definition) [1];
- train-time and test-time pair counts.

### 4.3 Ceilings and ablations

- **Exact candidate oracle F0.5:** use truth to choose the best possible set from each candidate list. This is diagnostic only, never an inference input.
- Oracle F0.5 with exhaustive candidates is 1.0 if the scorer and truth convention are correct.
- Leave-one-channel-in and cap curves: show both recall and average candidates.
- Break down misses by whether the pair shares a name token, q-gram, exact address, postal/number, or only a dense embedding.
- For France/unseen-country diagnostics, inject country-field label changes or country removal in a controlled perturbation test. This tests robustness without consulting external country data.

- The contest metric includes singleton/empty truth entities, but **candidate recall is only defined over non-empty truth sets**. Report empty/singleton slices separately: an empty truth set can never validate a retrieved edge, while a missed singleton is a direct loss.

Use grouped/entity-isolated folds. Tune retrieval parameters inside the training portion. Generate candidates with the same production procedure used on test; do not inject labeled positives into validation candidate lists.

## 5. ANN decision: exact Flat first, HNSW only if measured Flat is infeasible

### 5.1 FAISS exact retrieval

Use `IndexFlatIP` on L2-normalized embeddings for cosine. FAISS's own index guide labels `IndexFlatL2` and `IndexFlatIP` as exact brute-force methods [3]. This gives a correct reference and has no ANN recall loss. It is usually the best choice for a small target corpus.

If pair generation, not dense search, is the bottleneck, an approximate vector index does not solve the main problem; improve lexical filtering or batch scoring instead.

### 5.2 HNSW implementation settings

Only move to HNSW after measuring that exact Flat cannot meet the local run budget. A reproducible first sweep:

- metric: cosine (`space='cosine'`) on normalized vectors;
- `M ∈ {16, 32}`;
- `ef_construction ∈ {100, 200}`;
- `random_seed=100`; add target vectors in sorted target-ID order with `num_threads=1` during build;
- `ef_search ∈ {50, 100, 200, 400, 800}` and at least the requested `k`; use a larger exact top-k than the final cap;
- one target index containing both sources, with source preserved in metadata/IDs;
- **no deletion/update in the competition run**—rebuild from the frozen test target corpus.

These are explicit starting settings, not universal optima. hnswlib's primary API documents defaults `M=16`, `ef_construction=200`, `random_seed=100`, and describes `ef` as the query-time accuracy/speed trade-off [12]. Its parameter guide states `ef` cannot be below `k`; higher `ef` improves accuracy at a latency cost [13]. The HNSW paper is the canonical method source [14]. ANN-Benchmarks emphasizes that quality/performance must be evaluated across parameters and datasets rather than reported as a single configuration-free result [15].

Determinism caveat: fixed seed and insertion order do not prove cross-platform bit identity, especially with multithreaded builds. The reproducible artifact is the exact index binary, library version, parameters, and serialized candidate file.

### 5.3 ANN evaluation

For each `k ∈ {50, 100, 250, 500}`:

1. Build exact `k`-NN ground truth with Flat.
2. Report `ANN recall@k = |A_k ∩ E_k| / k`, plus the number of exact top-k neighbors recovered and the worst query.
3. Sweep `ef_search`; select the smallest value meeting the retrieval target.
4. Separately report **ER candidate recall**: of labeled true pairs/entities, how many did ANN return? ANN rank recall alone is insufficient.
5. Compare total end-to-end macro F0.5, not just vector recall.

Use no hard labels to build ANN. Do not claim recall on a held-out true edge that exact retrieval itself did not place in top-k; the vector model simply cannot recover it.

### 5.4 Pinecone

Pinecone is not recommended here:

- the competition prohibits external lookup at inference, and a managed service is an external dependency unless its use is explicitly permitted;
- network latency, cost, eventual consistency, and mutable service behavior weaken reproducibility;
- exact Flat/HNSW is locally available and tiny enough for exact search;
- tuning/guarantees differ by service tier and index architecture.

Pinecone's current query documentation exposes `scan_factor` and `max_candidates` only for dense-vector search on dedicated read nodes; its default `max_candidates` is 2,500 and can be raised to 100,000, while on-demand indexes accept but ignore the parameters [16]. That is a service-specific architecture, not a portable HNSW `M/efConstruction/efSearch` contract. If a later rules change permits it, freeze the index version and measure label-level candidate recall against local Flat results.

## 6. BK-tree: exact metric search, not ANN

A BK-tree is a metric-space index that uses the triangle inequality to prune distance evaluations. It can be exact for radius or nearest-neighbor search when the distance is a genuine metric; the original BK-tree is by Burkhard and Keller [17].

For this task:

- use a BK-tree only for **short normalized names** and a true integer metric such as Levenshtein or optimal-string-alignment Damerau-Levenshtein;
- it is not appropriate for a learned vector score, cosine on non-normalized vectors, or arbitrary weighted edit similarity;
- it can degrade when the data distribution is highly clustered, strings are long, or the radius is large;
- for a small corpus, exhaustive Levenshtein is usually simpler, deterministic, and fast enough.

Do not use a BK-tree merely because names are strings. Measure it against brute force and deletion neighborhoods.

## 7. Concrete implementation order

1. **Reference:** build and score the full `S1 × (S2∪S3)` matrix when feasible. Save pair count, runtime, peak memory, candidate hash, and oracle F0.5.
2. **Lexical union:** exact/token/rare-token/name/address/numeric indexes plus q=3,4 character overlap; run `d=1` deletion neighborhoods only for short names; add two sorted-neighborhood passes.
3. **Caps:** rank the union and evaluate `{50,100,250,500,1000}` per source and global. Inspect every full-set miss before reducing the budget.
4. **Dense exact baseline:** use TF-IDF/character TF-IDF and, if useful, a local encoder. Retrieve with exact cosine/Flat; measure whether it adds any full-set recall beyond lexical candidates.
5. **Scale escape hatch:** only if exact retrieval is infeasible, tune HNSW against Flat. Require both vector recall and label-level candidate recall to clear predefined targets.
6. **Freeze:** persist sorted `candidate_pairs.tsv`, retrieval config, normalization/hash versions, library versions, diagnostics, and SHA-256 hashes.

## References

1. G. Papadakis, D. Skoutas, E. Thanos, and T. Palpanas, “Blocking and Filtering Techniques for Entity Resolution: A Survey,” *ACM Computing Surveys*, 2020. DOI: https://doi.org/10.1145/3377455 (open author manuscript: https://arxiv.org/html/1905.06167v4).
2. P. Christen, “A Survey of Indexing Techniques for Scalable Record Linkage and Deduplication,” *IEEE TKDE* 24(9), 2012. DOI: https://doi.org/10.1109/TKDE.2011.127 (author PDF: https://users.cecs.anu.edu.au/~Peter.Christen/publications/christen2011indexing.pdf).
3. Meta FAISS, “Faiss indexes” (official repository wiki). https://github.com/facebookresearch/faiss/wiki/Faiss-indexes
4. Meta FAISS, “Guidelines to choose an index” (official repository wiki). https://github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index
5. P. Christen, *Data Matching: Concepts and Techniques for Record Linkage, Entity Resolution, and Duplicate Detection*, Springer, 2012. This monograph is the source for the quadratic all-pairs baseline. DOI: https://doi.org/10.1007/978-3-642-31164-2
6. C. Xiao, W. Wang, X. Lin, J. X. Yu, and G. Wang, “Efficient Similarity Joins for Near-Duplicate Detection,” *ACM TODS* 36(3), 2011. DOI: https://doi.org/10.1145/2000824.2000825
7. A. Z. Broder, “On the Resemblance and Containment of Documents,” 1997. DOI: https://doi.org/10.1109/SEQUEN.1997.666900
8. M. S. Charikar, “Similarity Estimation Techniques from Rounding Algorithms,” STOC 2002. DOI: https://doi.org/10.1145/509907.509965
9. datasketch, “MinHash LSH” (primary implementation documentation; states the exact banding probability and false-positive/false-negative behavior). https://ekzhu.com/datasketch/lsh.html
10. S. Mishra, T. Gandhi, A. Arora, and A. Bhattacharya, “Efficient Edit Distance Based String Similarity Search Using Deletion Neighborhoods,” EDBT/ICDT Workshops, 2013. DOI: https://doi.org/10.1145/2457317.2457387
11. M. A. Hernández and S. J. Stolfo, “The Merge/Purge Problem for Large Databases,” SIGMOD 1995. DOI: https://doi.org/10.1145/223784.223807
12. hnswlib, official repository README (primary implementation source). https://github.com/nmslib/hnswlib/blob/master/README.md
13. hnswlib, “Algorithm Parameters” (primary implementation documentation). https://github.com/nmslib/hnswlib/blob/master/ALGO_PARAMS.md
14. Y. A. Malkov and D. A. Yashunin, “Efficient and Robust Approximate Nearest Neighbor Search Using Hierarchical Navigable Small World Graphs,” *IEEE TPAMI* 42(4), 2020. DOI: https://doi.org/10.1109/TPAMI.2018.2889473 ; open manuscript: https://arxiv.org/pdf/1603.09320
15. M. Aumüller, E. Bernhardsson, and A. Faithfull, “ANN-Benchmarks: A Benchmarking Tool for Approximate Nearest Neighbor Algorithms,” *Information Systems* 87, 2020. DOI: https://doi.org/10.1016/j.is.2019.02.006 ; open paper: https://arxiv.org/abs/1807.05614
16. Pinecone, “Tune queries on dedicated read nodes” (official product documentation). https://docs.pinecone.io/guides/index-data/dedicated-read-nodes/tune-queries
17. W. A. Burkhard and R. M. Keller, “Some Approaches to Best-Match File Searching,” *Communications of the ACM* 16(4), 1973. DOI: https://doi.org/10.1145/362003.362025

## Source verification note

DOI metadata and titles were checked against Crossref on 2026-09-25. URLs for the author survey, FAISS wiki, hnswlib, datasketch documentation, and Pinecone documentation were fetched successfully on the same date. The `5M`-pair feasibility threshold, posting-frequency cutoff, q-gram settings, source caps, HNSW sweep, and composite lexical score are explicit engineering starting points to validate on this dataset; they are not claimed as universally optimal published constants.
