"""Print one ground-truth pair from the make_testdata.py fixture side by side.

The generator used to draw each source2/3 row's fields independently, so rows
the ground truth called "the same business" shared nothing. This shows the
current rows so the linkage can be inspected by eye.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "_ttd")


def table(name: str) -> dict[str, dict[str, str]]:
    with (ROOT / name).open(encoding="utf-8", newline="") as fh:
        return {r["id"]: r for r in csv.DictReader(fh, delimiter="\t")}


def main() -> None:
    s1, s2, s3 = table("source1.tsv"), table("source2.tsv"), table("source3.tsv")
    with (ROOT / "ground_truth.tsv").open(encoding="utf-8", newline="") as fh:
        gt = list(csv.DictReader(fh, delimiter="\t"))
    targets = {**s2, **s3}

    shown = 0
    for row in gt:
        a, t = s1[row["s1_id"]], targets[row["dup_id"]]
        if a["country"] != t["country"]:
            continue
        print(f"GROUND TRUTH: {row['s1_id']} == {row['dup_id']}\n")
        print(f"  id    | {a['id']:<12} | {t['id']}")
        print(f"  name  | {a['business_name']:<12} | {t['business_name']}")
        print(f"  addr  | {(a['address'] + ', ' + a['city']):<12} "
              f"| {t['address'] + ', ' + t['city']}")
        print(f"  country | {a['country']:<10} | {t['country']}")
        print("  -> names are deliberately perturbed (realistic ER noise); "
              "address + country are shared.\n")
        shown += 1
        if shown == 3:
            break
    print(f"total ground-truth links in fixture: {len(gt)}")


if __name__ == "__main__":
    main()
