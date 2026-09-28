import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark_v3 import f05, generate_candidates, load_proxy, norm, set_f05, sim


class BenchmarkV3Tests(unittest.TestCase):
    def test_norm(self):
        self.assertEqual(norm("Élan & Café"), "elan and cafe")

    def test_similarity(self):
        self.assertEqual(sim("x", "x")["exact"], 1.0)
        self.assertEqual(sim("", "")["exact"], 0.0)

    def test_f05(self):
        import numpy as np
        self.assertAlmostEqual(f05(np.array([1, 0]), np.array([1, 1])), 5 / 9)

    def test_set_f05_singleton(self):
        out = set_f05({"a": {"x"}, "b": set()}, {"a": {"x"}, "b": {"y"}}, ["a", "b"])
        self.assertEqual(out["tp"], 1)
        self.assertEqual(out["fp"], 1)
        self.assertAlmostEqual(out["f05"], 5 / 9)

    def test_candidate_generation_is_label_free(self):
        root = Path(__file__).resolve().parents[3] / "sources" / "proxy_downloads"
        data = load_proxy(root, "amazon_google", "title", "manufacturer")
        candidates = generate_candidates(data, top_k=5)
        self.assertGreater(len(candidates), 0)
        self.assertTrue(all("label" not in row for row in candidates))


if __name__ == "__main__":
    unittest.main()
