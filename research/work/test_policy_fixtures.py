import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from policy_fixtures import fixture_capped, fixture_zero_one_many, macro_set_f05


class PolicyFixtureTests(unittest.TestCase):
    def test_zero_one_many_policy(self):
        result = fixture_zero_one_many()
        self.assertEqual(result["pred"]["empty"], set())
        self.assertEqual(result["pred"]["one"], {"a"})
        self.assertEqual(result["pred"]["many"], {"a", "b"})
        self.assertGreater(result["metric"]["macro_f05"], 0.6)

    def test_empty_truth_policy_is_explicit(self):
        result = macro_set_f05({"x": set()}, {"x": set()}, empty_fn=0.5)
        self.assertEqual(result["macro_f05"], 0.5)

    def test_empty_truth_defaults_to_one(self):
        result = macro_set_f05({"x": set()}, {"x": set()})
        self.assertEqual(result["macro_f05"], 1.0)

    def test_max_per_entity_cap_and_negative_guard(self):
        result = fixture_capped()
        self.assertEqual(result["capped"], {"a"})
        self.assertTrue(result["negative_max_rejected"])


if __name__ == "__main__":
    unittest.main()
