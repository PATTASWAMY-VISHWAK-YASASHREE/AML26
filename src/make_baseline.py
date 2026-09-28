"""Minimal viable VALID baseline submission (task_0003 fallback, tier 0).

Streams test_source1.tsv line by line - never loads a dataframe, never touches
test_source2/3.tsv. Peak RSS ~50 MB, runtime ~30 s on this box.

Writes BOTH required files so the official validator does not fail on the
"candidate_pairs.tsv not found" error (validate_submission.py:274-284).

usage:  python make_baseline.py <student_resource_dir> <out_dir>
"""
import sys
from pathlib import Path


def main() -> int:
    sr = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        r"C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)"
        r"\amazon_ml_2026_research\student_resource")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(
        r"C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)\output")
    out.mkdir(parents=True, exist_ok=True)

    src = sr / "dataset" / "test" / "test_source1.tsv"
    seen = set()
    n_dup = 0
    with src.open(encoding="utf-8") as f, \
         (out / "matching_results.tsv").open("w", encoding="utf-8", newline="") as m, \
         (out / "candidate_pairs.tsv").open("w", encoding="utf-8", newline="") as c:
        next(f)                                            # skip header
        m.write("source1_entity_id\tmatched_entity_ids\n")   # TAB separated
        c.write("source1_entity_id\tcandidate_entity_ids\n")
        for line in f:
            if not line.strip():
                continue
            s1 = line.split("\t", 1)[0].strip()
            if s1 in seen:                                  # validator: no dup S1 rows
                n_dup += 1
                continue
            seen.add(s1)
            m.write(f"{s1}\t\n")                           # empty = scored singleton
            c.write(f"{s1}\t\n")

    print(f"rows written : {len(seen)}")
    print(f"duplicates skipped : {n_dup}")
    print(f"expected     : 1732544 (all S1- prefixed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
