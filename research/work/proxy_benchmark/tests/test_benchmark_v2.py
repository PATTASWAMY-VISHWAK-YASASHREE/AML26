import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark_v2 import char_ngrams, f05, generate_candidates, load_dataset, normalize_text, retrieval_stats, similarity


class BenchmarkV2Tests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalize_text("  Élan & Café, Ltd. "), "elan and cafe ltd")
        self.assertEqual(normalize_text("Ｎo．１２３"), "no 123")

    def test_ngrams(self):
        self.assertEqual(char_ngrams("abc"), {" ab", "abc", "bc "})
        # A blank value yields NO grams, not {"  "}. Padding "" to "  " has length
        # 2 <= n, so without the blank guard it would return {"  "} and make the
        # blank-vs-blank ngram Jaccard 1.0 -- a spurious "identical" signal.
        self.assertEqual(char_ngrams(""), set())
        self.assertEqual(similarity("", "")["ngram"], 0.0)
        self.assertEqual(similarity("", "abc")["ngram"], 0.0)

    def test_similarity(self):
        self.assertEqual(similarity("Acme Ltd", "Acme Ltd")["exact"], 1.0)
        self.assertEqual(similarity("", "")["exact"], 0.0)
        self.assertGreaterEqual(similarity("Acme Cafe", "Acme Café")["token_set"], 0.88)

    def test_f05(self):
        import numpy as np
        self.assertAlmostEqual(f05(np.array([1, 0]), np.array([1, 1])), 5 / 9)

    def test_label_free_retrieval_recall_is_measured(self):
        root = Path(__file__).resolve().parents[3] / "sources" / "proxy_downloads"
        data = load_dataset(root, "amazon_google", "title", "manufacturer")
        candidates = generate_candidates(data, top_k=10, secondary_k=5)
        stats = retrieval_stats(data, candidates, "test", 10, 5)
        self.assertGreater(stats["candidate_rows"], 0)
        self.assertGreaterEqual(stats["positive_pair_recall"], 0.0)
        self.assertLessEqual(stats["positive_pair_recall"], 1.0)


if __name__ == "__main__":
    unittest.main()
