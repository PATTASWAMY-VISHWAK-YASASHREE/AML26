"""End-to-end checks of the official utils/validate_submission.py behaviour.

Builds a miniature test-set directory plus deliberately broken submissions and
asserts the validator's exit code and messages. The 3-column case is the one
that previously slipped through: `line.partition(DELIM)` consumed only the first
tab, so `S1-1<TAB>S2-1<TAB>S2-2` became a single bogus id "S2-1\tS2-2" that
still passed the S2-/S3- prefix test, and the script printed PASS.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

VALIDATOR = (Path(__file__).parent / "amazon_ml_2026_research" / "student_resource"
             / "utils" / "validate_submission.py")

HDR = "entity_id\tbusiness_name\tbusiness_address\tcountry\n"


def make_testdir(root: Path, s1: list[str]) -> Path:
    d = root / "dataset" / "test"
    d.mkdir(parents=True, exist_ok=True)
    rows = "".join(f"{i}\tBiz {i}\t1 Main St, Springfield\tUS\n" for i in s1)
    (d / "test_source1.tsv").write_text(HDR + rows, encoding="utf-8")
    (d / "test_source2.tsv").write_text(HDR + rows, encoding="utf-8")
    (d / "test_source3.tsv").write_text(HDR, encoding="utf-8")
    return d


def run(test_dir: Path, out: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR),
         "--matching", str(out / "matching_results.tsv"),
         "--candidate", str(out / "candidate_pairs.tsv"),
         "--test-dir", str(test_dir)],
        capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def report(label: str, ok: bool, rc: int, text: str, failures: list[str],
           needle: str) -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {label} (rc={rc})")
    if not ok:
        failures.append(label)
        print(text)


def main() -> None:
    S1 = ["S1-1", "S1-2"]
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)

        # --- 1. three-column row must be rejected (the original hole) ----------
        d = make_testdir(base / "a", S1)
        out = base / "a" / "out"; out.mkdir()
        (out / "matching_results.tsv").write_text(
            "source1_entity_id\tmatched_entity_ids\nS1-1\tS2-1\tS2-2\nS1-2\t\n", encoding="utf-8")
        (out / "candidate_pairs.tsv").write_text(
            "source1_entity_id\tcandidate_entity_ids\nS1-1\tS2-1,S2-2\nS1-2\t\n", encoding="utf-8")
        rc, text = run(d, out)
        report("3-column row rejected", rc == 1 and "too many tab-separated columns" in text,
               rc, text, failures, "3-column")

        # --- 2. empty / header-only test source1 must not report PASS --------
        d2 = make_testdir(base / "b", [])
        out2 = base / "b" / "out"; out2.mkdir()
        (out2 / "matching_results.tsv").write_text(
            "source1_entity_id\tmatched_entity_ids\n", encoding="utf-8")
        (out2 / "candidate_pairs.tsv").write_text(
            "source1_entity_id\tcandidate_entity_ids\n", encoding="utf-8")
        rc, text = run(d2, out2)
        report("empty test set rejected", rc == 1 and "no Source 1 entities" in text,
               rc, text, failures, "empty test set")

        # --- 3. missing candidate_pairs.tsv must not report PASS -------------
        d3 = make_testdir(base / "c", S1)
        out3 = base / "c" / "out"; out3.mkdir()
        (out3 / "matching_results.tsv").write_text(
            "source1_entity_id\tmatched_entity_ids\nS1-1\tS2-1\nS1-2\t\n", encoding="utf-8")
        rc, text = run(d3, out3)
        report("missing candidate_pairs rejected",
               rc == 1 and "candidate_pairs.tsv" in text and "PASS" not in text,
               rc, text, failures, "missing candidate_pairs")

        # --- 4. a genuinely valid submission still passes --------------------
        d4 = make_testdir(base / "d", S1)
        out4 = base / "d" / "out"; out4.mkdir()
        (out4 / "matching_results.tsv").write_text(
            "source1_entity_id\tmatched_entity_ids\nS1-1\tS2-1\nS1-2\t\n", encoding="utf-8")
        (out4 / "candidate_pairs.tsv").write_text(
            "source1_entity_id\tcandidate_entity_ids\nS1-1\tS2-1\nS1-2\t\n", encoding="utf-8")
        rc, text = run(d4, out4)
        report("valid submission accepted", rc == 0 and "PASS" in text,
               rc, text, failures, "valid submission")

    if failures:
        raise SystemExit("FAILURES: " + "; ".join(failures))
    print("\nall official-validator checks passed")


if __name__ == "__main__":
    main()
