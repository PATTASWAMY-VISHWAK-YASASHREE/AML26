"""Check the Colab cell's Drive path resolution against both real layouts.

The dataset root is /content/drive/MyDrive/student_resource. Two shapes occur in
practice and both must resolve, because a wrong root here means the pipeline
either cannot find the TSVs or silently reads the wrong ones:
  A) <root>/dataset/train/train_source1.tsv      (the documented layout)
  B) <root>/<anything>/dataset/train/...          (extra nesting, e.g. a
     folder uploaded inside another folder)
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# ---- verbatim copy of the resolver shipped in the Colab cell ---------------
def resolve(base: Path) -> Path:
    if (base / "dataset" / "train" / "train_source1.tsv").exists():
        return base
    for p in base.rglob("train_source1.tsv"):
        return p.parent.parent.parent
    raise FileNotFoundError(f"No train_source1.tsv under {base}")


def make(root: Path, *parts: str) -> Path:
    """Create a fake dataset at root/parts/... and return the Drive folder."""
    d = root.joinpath(*parts, "dataset", "train")
    d.mkdir(parents=True, exist_ok=True)
    (d / "train_source1.tsv").write_text("entity_id\tbusiness_name\t"
                                          "business_address\tcountry\n", encoding="utf-8")
    return root


def main() -> int:
    failures = []

    # Layout A: the folder from the Drive link
    with tempfile.TemporaryDirectory() as td:
        drive_folder = make(Path(td) / "MyDrive" / "student_resource")
        got = resolve(drive_folder)
        ok = got == drive_folder
        print(f"[{'PASS' if ok else 'FAIL'}] layout A: {got}")
        if not ok:
            failures.append(f"A resolved to {got}, expected {drive_folder}")

    # Layout B: an extra level of nesting inside student_resource
    with tempfile.TemporaryDirectory() as td:
        drive_folder = Path(td) / "MyDrive" / "student_resource"
        make(drive_folder, "ML_Challenge")
        got = resolve(drive_folder)
        ok = (got / "dataset" / "train" / "train_source1.tsv").exists()
        print(f"[{'PASS' if ok else 'FAIL'}] layout B: {got}")
        if not ok:
            failures.append(f"B resolved to {got}, no dataset there")

    # Layout C: genuinely empty folder must raise, not silently return
    with tempfile.TemporaryDirectory() as td:
        empty = Path(td) / "MyDrive" / "student_resource"
        empty.mkdir(parents=True)
        try:
            resolve(empty)
            print("[FAIL] layout C: empty folder did not raise")
            failures.append("C did not raise on an empty folder")
        except FileNotFoundError as exc:
            print(f"[PASS] layout C: empty folder raises -> {str(exc)[:60]}...")

    if failures:
        raise SystemExit("FAILURES: " + "; ".join(failures))
    print("\nall Drive path layouts resolve correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())

