"""Verify the GENERATED Colab cell's embedded pipeline actually runs.

The cell is the artifact the user will paste, so testing er_pipeline.py directly
is not enough - a mistake in the triple-quote splicing or in the header/footer
would only show up when the embedded copy is extracted and executed. This pulls
the PIPELINE string out of the generated cell exactly as Colab would, proves it
is byte-identical to the tested module, then runs it end-to-end.
"""
from __future__ import annotations

import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent
CELL = (ROOT / "amazon_ml_colab_cell.py").read_text(encoding="utf-8")
Q3 = chr(39) * 3

HDR = "entity_id\tbusiness_name\tbusiness_address\tcountry\n"
STREETS = ["main st", "high st", "oak ave", "park rd"]
CITIES = ["springfield", "fairview", "georgetown", "madison"]


def extract_pipeline(cell: str) -> str:
    """Mirror exactly what the cell does: split on the raw triple-quote.

    The header ends with the marker followed by a newline, so that newline
    belongs to the header, not to the pipeline body.
    """
    marker = "PIPELINE = r" + Q3
    start = cell.index(marker) + len(marker)
    if cell[start] == "\n":
        start += 1
    end = cell.index(Q3, start)
    return cell[start:end]


def build(ds: Path, n: int = 250):
    rng = random.Random(5)
    truths, s1, s2, s3 = {}, [], [], []
    n2 = n3 = 0
    for i in range(n):
        sid = f"S1-{i:05d}"
        name = rng.choice(["acme", "globex", "initech", "soylent"]) + " " \
               + rng.choice(["cafe", "mart", "works", "clinic"]) + " " \
               + rng.choice(["inc", "llc", "ltd", ""])
        addr = f"{rng.randint(1, 40)} {rng.choice(STREETS)} {rng.choice(CITIES)}"
        s1.append((sid, name, addr))
        mids = []
        for _ in range(rng.randint(0, 3)):
            n2 += 1
            t = name.replace("inc", "incorporated") if rng.random() < .4 else name
            s2.append((f"S2-{n2:05d}", t, addr))
            mids.append(f"S2-{n2:05d}")
        for _ in range(rng.randint(0, 2)):
            n3 += 1
            s3.append((f"S3-{n3:05d}", name, addr))
            mids.append(f"S3-{n3:05d}")
        truths[sid] = mids
    for split in ("train", "test"):
        (ds / split).mkdir(parents=True, exist_ok=True)
        for src, rows in ((1, s1), (2, s2), (3, s3)):
            (ds / split / f"{split}_source{src}.tsv").write_text(
                HDR + "".join(f"{a}\t{b}\t{c}\tUS\n" for a, b, c in rows), encoding="utf-8")
    (ds / "train" / "train_ground_truth.tsv").write_text(
        "source1_entity_id\tmatched_entity_ids\n"
        + "".join(f"{k}\t{','.join(v)}\n" for k, v in truths.items()), encoding="utf-8")
    return truths, n


def main() -> int:
    pipeline = extract_pipeline(CELL)
    on_disk = (ROOT / "er_pipeline.py").read_text(encoding="utf-8")
    assert pipeline == on_disk, (
        "embedded pipeline differs from er_pipeline.py - the cell would not be "
        "the code that was tested")
    print("PASS embedded pipeline is byte-identical to er_pipeline.py")

    base = Path(tempfile.mkdtemp(prefix="cell_e2e_"))
    ds = base / "dataset"
    truths, n = build(ds)
    work = base / "content"
    work.mkdir()
    (work / "er_pipeline.py").write_text(pipeline, encoding="utf-8")

    driver = f'''
import sys
sys.path.insert(0, {str(work)!r})
import er_pipeline as ER
ER.CFG.update(threads=2, memory_limit="256MB", temp_directory_size="8GB",
              train_sample_pct=100, candidate_sample_rows=2000000)
s = ER.run(work_dir={str(work)!r}, dataset_dir={str(ds)!r})
print("RECALL", s["blocking_recall"])
print("N_S1", s["test_s1_entities"], "N_TGT", s["test_target_entities"])
'''
    (work / "_driver.py").write_text(driver, encoding="utf-8")
    proc = subprocess.run([sys.executable, str(work / "_driver.py")],
                          capture_output=True, text=True)
    out = proc.stdout + proc.stderr
    if proc.returncode != 0:
        print(out[-3000:])
        raise SystemExit("embedded pipeline failed to run")

    sys.path.insert(0, str(work))
    import er_pipeline  # noqa: E402
    lines = (work / "output" / "matching_results.tsv").read_text(
        encoding="utf-8").splitlines()
    assert lines[0] == "source1_entity_id\tmatched_entity_ids", lines[0]
    assert len(lines) - 1 == n, f"expected {n} rows, got {len(lines) - 1}"
    pred = {}
    for line in lines[1:]:
        sid, _, cell_ = line.partition("\t")
        pred[sid] = {v for v in cell_.split(",") if v}
    triples = [(s, t, True, t in pred.get(s, set())) for s in truths for t in truths[s]]
    score = er_pipeline.macro_f05(triples, set(truths))
    assert (work / "submission.zip").exists()

    for line in out.splitlines():
        if line.startswith(("RECALL", "N_S1", "[*] validation", "[*] test candidates")):
            print("   ", line)
    print(f"    macro F_0.5 = {score:.4f}, {len(lines) - 1} rows, zip written")
    print("\nPASS the generated cell's embedded pipeline runs end-to-end under 256MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
