import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from amazon_contract import MATCHING_HEADER, validate_outputs, write_tsv


class _ExplodingRows(dict):
    """A rows mapping that fails *while* write_tsv is iterating it."""

    def items(self):
        yield "S1-1", ["S2-1"]
        raise RuntimeError("serialization failed")


class AmazonContractTests(unittest.TestCase):
    def test_valid_zero_one_many_and_subset(self):
        errors = validate_outputs(
            ["S1-1", "S1-2", "S1-3"],
            ["S2-1", "S2-2", "S3-1"],
            [("S1-1", "S2-1,S3-1"), ("S1-2", ""), ("S1-3", "S2-2")],
            [("S1-1", "S2-1,S3-1,S2-2"), ("S1-2", ""), ("S1-3", "S2-2")],
        )
        self.assertEqual(errors, [])

    def test_final_match_must_be_candidate(self):
        errors = validate_outputs(["S1-1"], ["S2-1"], [("S1-1", "S2-1")], [("S1-1", "")])
        self.assertTrue(any("absent from candidate_pairs" in x for x in errors))

    def test_duplicate_and_unknown_ids_rejected(self):
        errors = validate_outputs(["S1-1"], ["S2-1"], [("S1-1", "S2-1,S2-1,S9-1")], [("S1-1", "S2-1,S9-1")])
        self.assertGreaterEqual(len(errors), 2)

    def test_tsv_writer_preserves_empty_singletons(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "matching_results.tsv"
            write_tsv(path, ("source1_entity_id", "matched_entity_ids"), {"S1-1": [], "S1-2": ["S2-1"]})
            self.assertEqual(path.read_text(encoding="utf-8"), "source1_entity_id\tmatched_entity_ids\nS1-1\t\nS1-2\tS2-1\n")

    def test_tsv_writer_rejects_non_official_header(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "matching_results.tsv"
            with self.assertRaises(ValueError):
                write_tsv(path, ("entity_id", "matched_entity_ids"), {"S1-1": ["S2-1"]})
            self.assertFalse(path.exists())

    def test_tsv_writer_is_atomic_on_mid_write_failure(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "matching_results.tsv"
            with self.assertRaises(RuntimeError):
                write_tsv(path, MATCHING_HEADER, _ExplodingRows())
            # No half-written file at the official path, no temp file left behind.
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_tsv_writer_leaves_previous_file_intact_on_failure(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "matching_results.tsv"
            write_tsv(path, MATCHING_HEADER, {"S1-9": ["S2-9"]})
            before = path.read_text(encoding="utf-8")
            with self.assertRaises(RuntimeError):
                write_tsv(path, MATCHING_HEADER, _ExplodingRows())
            self.assertEqual(path.read_text(encoding="utf-8"), before)
            self.assertEqual([p.name for p in Path(d).iterdir()], ["matching_results.tsv"])

    def test_every_s1_row_required(self):
        errors = validate_outputs(["S1-1", "S1-2"], ["S2-1"], [("S1-1", "")], [("S1-1", "")])
        self.assertTrue(any("missing 1" in x for x in errors))


if __name__ == "__main__":
    unittest.main()
