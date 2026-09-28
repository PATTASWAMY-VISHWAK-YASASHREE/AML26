"""Run the whole pipeline under a deliberately tiny memory limit.

The Colab failure was `could not allocate block of size 256.0 KiB
(5.5 GiB/5.5 GiB used)` inside stage_candidates, so the closest local proxy is
to squeeze the same workload into a buffer pool far smaller than it needs. With
the per-channel rewrite plus an explicit spill budget this must still complete
and still produce a valid submission - a kernel-level OOM instead would mean the
pipeline is still not out-of-core.
"""
from __future__ import annotations

import sys
import tempfile
import random
from pathlib import Path

import er_pipeline as P

STREETS = ["main st", "high st", "oak ave", "park rd", "elm st", "lake dr"]
HDR = "entity_id\tbusiness_name\tbusiness_address\tcountry\n"
N_S1, N_T = 900, 2600


def build(ds: Path) -> dict[str, list[str]]:
    rng = random.Random(11)
    truths: dict[str, list[str]] = {}
    s1, s2, s3 = [], [], []
    n2 = n3 = 0
    for i in range(N_S1):
        sid = f"S1-{i:05d}"
        # a small name pool forces heavy key collisions, which is what blew up
        # the single-query version
        name = rng.choice(["acme", "globex", "initech", "umbrella", "stark", "soylent"]) \
            + " " + rng.choice(["cafe", "mart", "works", "clinic", "depot"]) \
            + " " + rng.choice(["inc", "llc", "ltd", ""])
        city = rng.choice(["springfield", "fairview", "georgetown", "madison"])
        addr = f"{rng.randint(1, 40)} {rng.choice(STREETS)} {city}"
        s1.append((sid, name, addr))
        mids = []
        for _ in range(rng.randint(0, 3)):
            n2 += 1
            t = name.replace("inc", "incorporated") if rng.random() < .4 else name
            s2.append((f"S2-{n2:05d}", t, addr if rng.random() < .6 else addr.replace("st", "street")))
            mids.append(f"S2-{n2:05d}")
        for _ in range(rng.randint(0, 2)):
            n3 += 1
            t = name.replace("llc", "l l c") if rng.random() < .3 else name
            s3.append((f"S3-{n3:05d}", t, addr))
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
    return truths


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="er_tight_"))
    ds = base / "dataset"
    truths = build(ds)

    # Far tighter than the data needs: the whole point is to force spilling.
    P.CFG.update(threads=2, memory_limit="256MB", temp_directory_size="8GB",
                 train_sample_pct=100, candidate_sample_rows=2000000,
                 max_candidates=30, max_token_df=5000)
    print(f"dataset: {N_S1} S1 / {len(truths)} gt rows; memory_limit="
          f"{P.CFG['memory_limit']} (deliberately far too small)")

    summary = P.run(work_dir=str(base), dataset_dir=str(ds))

    out = base / "output"
    m = (out / "matching_results.tsv").read_text(encoding="utf-8").splitlines()
    c = (out / "candidate_pairs.tsv").read_text(encoding="utf-8").splitlines()
    assert m[0] == "source1_entity_id\tmatched_entity_ids"
    assert c[0] == "source1_entity_id\tcandidate_entity_ids"
    assert len(m) - 1 == N_S1 and len(c) - 1 == N_S1

    pred = {}
    for line in m[1:]:
        sid, _, cell = line.partition("\t")
        pred[sid] = {v for v in cell.split(",") if v}
    triples = [(s, t, True, t in pred.get(s, set())) for s in truths for t in truths[s]]
    score = P.macro_f05(triples, set(truths))

    spill = list((base / "er_work" / "tmp").glob("*.tmp"))
    print(f"\ncompleted under a 256MB budget")
    print(f"  blocking recall : {summary['blocking_recall']}")
    print(f"  macro F_0.5      : {score:.4f}")
    print(f"  rows written    : {len(m) - 1} / {N_S1}")
    print(f"  spill files left: {len(spill)}")
    assert (base / "submission.zip").exists()
    print("  OK - no OOM, valid submission produced")
    return 0


if __name__ == "__main__":
    sys.exit(main())
