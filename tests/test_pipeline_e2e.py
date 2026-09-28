"""End-to-end smoke test of er_pipeline.run() on a tiny synthetic dataset.

Exercises every stage end to end - normalize, tokens, ground truth, candidate
blocking, features, the fit/tune split in stage_train, output writing and the
DuckDB-backed validate_outputs - and then scores the written submission with
the challenge metric so the whole path is proven, not just the units.
"""
from __future__ import annotations

import random
import sys
import tempfile
from pathlib import Path

import er_pipeline as P

STREETS = ["main st", "high st", "oak ave", "park rd", "elm st", "lake dr"]
CITIES = [("springfield", "IL"), ("fairview", "OH"), ("georgetown", "TX"),
          ("madison", "WI"), ("clinton", "IA")]


def main() -> int:
    rng = random.Random(7)
    base = Path(tempfile.mkdtemp(prefix="er_e2e_"))
    ds = base / "dataset"
    for split in ("train", "test"):
        (ds / split).mkdir(parents=True, exist_ok=True)

    n_s1 = 300
    # Each S1 entity gets 0-2 true S2/S3 twins with perturbed fields, so both
    # genuine matches and true singletons (scored 1.0 when left empty) occur.
    truths: dict[str, list[str]] = {}
    s1_rows, s2_rows, s3_rows = [], [], []
    n2 = n3 = 0
    for i in range(n_s1):
        sid = f"S1-{i:05d}"
        name = f"{rng.choice(['acme', 'globex', 'initech', 'umbrella', 'stark'])} " \
               f"{rng.choice(['cafe', 'mart', 'works', 'clinic', 'depot'])} " \
               f"{rng.choice(['inc', 'llc', 'ltd', ''])}".strip()
        city, state = rng.choice(CITIES)
        addr = f"{rng.randint(1, 999)} {rng.choice(STREETS)} {city} {state}"
        s1_rows.append((sid, name, addr, state == "IA" and "US" or "US"))
        mids: list[str] = []
        for src, count in (("S2", 2), ("S3", 1)):
            for _ in range(rng.randint(0, count)):
                n2 += 1
                nid = f"S2-{n2:05d}" if src == "S2" else f"S3-{n3:05d}"
                if src == "S3":
                    n3 += 1
                if src == "S2":
                    nid = f"S2-{n2:05d}"
                # perturb so only fuzzy/exact keys can recover the link
                pert = name.replace("inc", "incorporated") if rng.random() < .3 else name
                addr2 = addr if rng.random() < .5 else addr.replace("st", "street")
                if src == "S2":
                    s2_rows.append((nid, pert, addr2, "US"))
                else:
                    s3_rows.append((nid, pert, addr2, "US"))
                mids.append(nid)
        truths[sid] = mids

    for split, (rows2, rows3) in (("train", (s2_rows, s3_rows)),
                                  ("test", (s2_rows, s3_rows))):
        for src, rows in ((1, s1_rows), (2, rows2), (3, rows3)):
            p = ds / split / f"{split}_source{src}.tsv"
            p.write_text("entity_id\tbusiness_name\tbusiness_address\tcountry\n"
                         + "".join("\t".join(r) + "\n" for r in rows), encoding="utf-8")
    (ds / "train" / "train_ground_truth.tsv").write_text(
        "source1_entity_id\tmatched_entity_ids\n"
        + "".join(f"{k}\t{','.join(v)}\n" for k, v in truths.items()), encoding="utf-8")

    P.CFG.update({"memory_limit": "2GB", "train_sample_pct": 100,
                  "candidate_sample_rows": 200000, "max_candidates": 20})
    print(f"synthetic dataset at {ds}")
    summary = P.run(work_dir=str(base), dataset_dir=str(ds))

    out = base / "output"
    matching = (out / "matching_results.tsv").read_text(encoding="utf-8").splitlines()
    candidates = (out / "candidate_pairs.tsv").read_text(encoding="utf-8").splitlines()
    print(f"\nmatching_results.tsv  {len(matching) - 1} data rows (expected {n_s1})")
    print(f"candidate_pairs.tsv   {len(candidates) - 1} data rows (expected {n_s1})")
    assert matching[0] == "source1_entity_id\tmatched_entity_ids", matching[0]
    assert candidates[0] == "source1_entity_id\tcandidate_entity_ids", candidates[0]
    assert len(matching) - 1 == n_s1, "one row per S1 entity is required"
    assert len(candidates) - 1 == n_s1, "one row per S1 entity is required"

    # Score the written submission with the official metric.
    pred = {}
    for line in matching[1:]:
        sid, _, cell = line.partition("\t")
        pred[sid] = {v for v in cell.split(",") if v}
    triples, entities = [], set(truths)
    for sid in truths:
        for t in truths[sid]:
            triples.append((sid, t, True, t in pred.get(sid, set())))
    score = P.macro_f05(triples, entities)
    print(f"blocking recall (train): {summary['blocking_recall']}")
    print(f"threshold: {summary['threshold']:.4f}")
    print(f"macro F_0.5 on the synthetic test labels: {score:.4f}")
    print(f"zip produced: {(base / 'submission.zip').exists()}")
    assert (base / "submission.zip").exists(), "submission.zip must be produced"
    assert 0.0 <= score <= 1.0

    # --- cache invalidation -------------------------------------------------
    # Re-running with an unchanged config must reuse the parquet; changing a
    # knob must invalidate it, otherwise the reported recall/threshold/weights
    # silently describe a mixture of two configurations.
    meta = base / "er_work" / "norm" / "test_cand.parquet.meta.json"
    assert meta.exists(), "stage artifacts must carry a fingerprint sidecar"
    first = meta.read_text(encoding="utf-8")
    P.run(work_dir=str(base), dataset_dir=str(ds))
    assert meta.read_text(encoding="utf-8") == first, \
        "an unchanged config should reuse the cached stage"
    print("cache: unchanged config reused the stage (fingerprint stable)")

    P.CFG["max_candidates"] = 5
    P.run(work_dir=str(base), dataset_dir=str(ds))
    assert meta.read_text(encoding="utf-8") != first, \
        "changing max_candidates must invalidate the cached candidate stage"
    print("cache: max_candidates change invalidated the stage (fingerprint changed)")

    print(f"\nOK  artifacts under {base}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
