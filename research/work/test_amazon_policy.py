import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from amazon_policy import choose_from_candidates, entity_f05, macro_f05


class AmazonPolicyTests(unittest.TestCase):
    def test_true_singleton_empty_prediction_scores_one(self):
        self.assertEqual(entity_f05(set(), set()), 1.0)

    def test_false_singleton_merge_scores_zero(self):
        self.assertEqual(entity_f05(set(), {"S2-1"}), 0.0)

    def test_one_to_many_is_not_capped(self):
        self.assertEqual(choose_from_candidates("S2-1,S2-2,S3-1", {"S2-1": .99, "S2-2": .97, "S3-1": .2}, .9), ["S2-1", "S2-2"])

    def test_macro_average_includes_singletons(self):
        value = macro_f05({"a": set(), "b": {"x"}}, {"a": set(), "b": {"x"}})
        self.assertEqual(value, 1.0)


if __name__ == "__main__":
    unittest.main()
