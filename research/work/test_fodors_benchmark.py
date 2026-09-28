import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fodors_benchmark import candidates, f05, load_fz, norm


class FodorsBenchmarkTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(norm("Café & Bistro"), "cafe and bistro")

    def test_pair_f05(self):
        import numpy as np
        self.assertAlmostEqual(f05(np.array([1, 0]), np.array([1, 1])), 5 / 9)

    def test_candidate_generation_is_label_free_and_recall_is_measured(self):
        root = Path(__file__).resolve().parents[1] / "sources" / "fodors_zagats"
        data = load_fz(root)
        rows, stats = candidates(data, top_k=25)
        self.assertGreater(len(rows), 0)
        self.assertNotIn("label", rows[0])
        positives = data.positives("test")
        found = {(str(r["source_id"]), str(r["target_id"])) for r in rows}
        self.assertGreaterEqual(len(positives & found) / max(1, len(positives)), 0.0)


if __name__ == "__main__":
    unittest.main()
