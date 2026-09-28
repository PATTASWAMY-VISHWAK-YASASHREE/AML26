"""End-to-end smoke test for the Amazon-style TSV contract.

This does not pretend to be the Amazon dataset. It creates a tiny synthetic
fixture with zero, one, and many matches, runs the contract utilities, and
verifies the final-match subset invariant.
"""
from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from amazon_contract import CANDIDATE_HEADER, MATCHING_HEADER, validate_outputs, write_tsv


def read_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    """Return the header row and the data rows of a TSV file."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader)
        return header, [row for row in reader]


def main() -> int:
    s1 = ["S1-1", "S1-2", "S1-3", "S1-4", "S1-5"]
    targets = ["S2-1", "S2-2", "S3-1", "S3-2"]
    candidates = {
        "S1-1": ["S2-1", "S3-1"],
        "S1-2": [],
        "S1-3": ["S2-2", "S3-2"],
        "S1-4": ["S2-1"],
        "S1-5": ["S2-1"],
    }
    matches = {
        "S1-1": ["S2-1", "S3-1"],
        "S1-2": [],
        "S1-3": ["S2-2", "S3-2"],
        "S1-4": [],
        "S1-5": ["S2-1"],
    }
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write_tsv(root / "matching_results.tsv", MATCHING_HEADER, matches)
        write_tsv(root / "candidate_pairs.tsv", CANDIDATE_HEADER, candidates)
        matching_header, matching_rows = read_rows(root / "matching_results.tsv")
        candidate_header, candidate_rows = read_rows(root / "candidate_pairs.tsv")
        if matching_header != list(MATCHING_HEADER):
            print(f"FAIL: matching_results.tsv header is {matching_header}, expected {list(MATCHING_HEADER)}")
            return 1
        if candidate_header != list(CANDIDATE_HEADER):
            print(f"FAIL: candidate_pairs.tsv header is {candidate_header}, expected {list(CANDIDATE_HEADER)}")
            return 1
        errors = validate_outputs(s1, targets, matching_rows, candidate_rows)
        if errors:
            print("FAIL")
            print("\n".join(errors))
            return 1

        # Negative test, isolated to a single entity so the only defect is the one
        # under test: S1-1's final match (S2-2) is absent from its candidate list
        # (S2-1). Every other ID is valid and every S1 entity has a row.
        neg_errors = validate_outputs(["S1-1"], ["S2-1", "S2-2"], [("S1-1", "S2-2")], [("S1-1", "S2-1")])
        expected_neg = ["matching_results[S1-1]: 1 final IDs absent from candidate_pairs"]
        if neg_errors != expected_neg:
            print("FAIL: expected exactly the absent-from-candidate error")
            print(f"  expected: {expected_neg}")
            print(f"  actual:   {neg_errors}")
            return 1

        print("PASS: synthetic zero/one/many contract fixture")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
