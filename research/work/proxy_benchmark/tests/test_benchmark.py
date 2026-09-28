import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark import (  # noqa: E402
    build_candidates,
    char_ngrams,
    field_similarity,
    load_deepmatcher,
    macro_f05_by_source,
    normalize_text,
)


class ProxyBenchmarkTests(unittest.TestCase):
    def test_normalization_is_deterministic_and_unicode_aware(self):
        self.assertEqual(normalize_text("  Élan & Café, Ltd. "), "elan and cafe ltd")
        self.assertEqual(normalize_text("Ｎo．１２３"), "no 123")

    def test_ngrams_have_stable_known_size(self):
        self.assertEqual(char_ngrams("abc"), {" ab", "abc", "bc "})
        # A blank value yields NO grams, not {"  "}. Padding "" to "  " has length
        # 2 <= n, so without the blank guard it would return {"  "} and make the
        # blank-vs-blank ngram similarity 1.0 -- a spurious "identical" signal.
        self.assertEqual(char_ngrams(""), set())
        self.assertEqual(field_similarity("", "")["ngram"], 0.0)
        self.assertEqual(field_similarity("", "abc")["ngram"], 0.0)

    def test_similarity_endpoints(self):
        self.assertEqual(field_similarity("Acme Ltd", "Acme Ltd")["exact"], 1.0)
        self.assertEqual(field_similarity("", "")["exact"], 0.0)
        self.assertGreaterEqual(field_similarity("Acme Cafe", "Acme Café")["token_set"], 0.88)

    def test_macro_f05_exact_known_case(self):
        truth = {"a": {"s2": {"x"}}, "b": {"s2": set()}}
        pred = {"a": {"s2": {"x"}}, "b": {"s2": set()}}
        out = macro_f05_by_source(truth, pred, ["a", "b"], ["s2"])
        self.assertAlmostEqual(out["s2"], 1.0)
        self.assertAlmostEqual(out["macro"], 1.0)

    def test_macro_f05_counts_false_singleton_link(self):
        truth = {"a": {"s2": {"x"}}, "b": {"s2": set()}}
        pred = {"a": {"s2": {"x"}}, "b": {"s2": {"y"}}}
        out = macro_f05_by_source(truth, pred, ["a", "b"], ["s2"])
        self.assertAlmostEqual(out["s2"], 5 / 9)

    def test_blocking_preserves_positive_pairs(self):
        data_path = Path(__file__).resolve().parents[3] / "sources" / "proxy_downloads"
        data = load_deepmatcher(data_path, "amazon_google", "title", "title", "manufacturer")
        candidates = build_candidates(data, "test", max_per_left=20)
        truth = {(r["left_id"], r["right_id"]) for r in data.test if r["label"] == "1"}
        found = {(str(r["left_id"]), str(r["right_id"])) for r in candidates}
        self.assertTrue(truth.issubset(found))


if __name__ == "__main__":
    unittest.main()
