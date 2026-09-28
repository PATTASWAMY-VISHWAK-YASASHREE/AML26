"""Ground-truth graph analysis (roadmap section 7) -- streaming, bounded RAM.

Answers, from train_ground_truth.tsv alone:
  * cluster-size distribution over an S1 row plus all its matched S2/S3 records
  * composition: S1->S2 only vs S1->S3 only vs both
  * degree distribution per source, including the anomalous high-degree tail
  * label integrity: unknown ids, self-matches, dups within a list, bad prefixes
  * whether one S2/S3 record is claimed by many S1 rows (shared alias rather
    than clean 1:1 duplication)

Memory discipline: an id->S1 map for 12.5M records in Python strings is too
large on a 0.36 GB box, so ids are verified against a sorted int64 hash array
per source (8 bytes/row) instead of a dict.
"""
from __future__ import annotations

import csv
import json
import os
import re
import time
from collections import Counter

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "amazon_ml_2026_research", "student_resource", "dataset")
OUT = os.path.join(ROOT, "analysis_out", "profile2")
os.makedirs(OUT, exist_ok=True)

ID_SPLIT_RE = re.compile(r"^(S[123])-")


def log(*a):
    print(*a, flush=True)


def build_id_hashes(split: str, src: int) -> np.ndarray:
    """Sorted int64 hashes of every entity_id in one source file."""
    path = os.path.join(DATA, split, f"{split}_source{src}.tsv")
    ids = []
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(rd, None)
        for rec in rd:
            if rec:
                ids.append(hash(rec[0].strip()))
    a = np.array(ids, dtype=np.int64)
    del ids
    a.sort()
    return a


def main() -> None:
    t0 = time.time()
    log("building id hash arrays (train) ...")
    H = {s: build_id_hashes("train", s) for s in (1, 2, 3)}
    for s, a in H.items():
        log(f"  S{s}: {a.size:,} ids")

    gt = os.path.join(DATA, "train", "train_ground_truth.tsv")
    cluster_hist: Counter = Counter()
    pair_hist: Counter = Counter()
    s2_per_s1: Counter = Counter()
    s3_per_s1: Counter = Counter()
    total_per_s1: Counter = Counter()
    deg_s2: Counter = Counter()
    deg_s3: Counter = Counter()
    n_rows = n_empty = n_bad_prefix = n_self_match = 0
    n_unknown_id = n_unknown_2 = n_unknown_3 = n_dup = n_mismatch = 0

    with open(gt, "r", encoding="utf-8", errors="replace", newline="") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(rd, None)
        for rec in rd:
            if not rec:
                continue
            n_rows += 1
            s1 = rec[0].strip()
            m = ID_SPLIT_RE.match(s1)
            if not m or m.group(1) != "S1":
                n_bad_prefix += 1
            vals = rec[1].split(",") if len(rec) > 1 and rec[1].strip() else []
            vals = [v.strip() for v in vals if v.strip()]
            if not vals:
                n_empty += 1
                total_per_s1[0] += 1
                continue
            c2 = c3 = 0
            seen = set()
            for v in vals:
                if v in seen:
                    n_dup += 1
                seen.add(v)
                if v == s1:
                    n_self_match += 1
                mm = ID_SPLIT_RE.match(v)
                tag = mm.group(1) if mm else "??"
                if tag not in ("S2", "S3"):
                    n_mismatch += 1
                    continue
                h = hash(v)
                arr = H[2] if tag == "S2" else H[3]
                i = int(np.searchsorted(arr, h))
                if i >= arr.size or int(arr[i]) != h:
                    if tag == "S2":
                        n_unknown_2 += 1
                    else:
                        n_unknown_3 += 1
                    n_unknown_id += 1
                    continue
                if tag == "S2":
                    c2 += 1
                    deg_s2[h] += 1
                else:
                    c3 += 1
                    deg_s3[h] += 1
            if c2 and c3:
                pair_hist["S2_and_S3"] += 1
            elif c2:
                pair_hist["S2_only"] += 1
            elif c3:
                pair_hist["S3_only"] += 1
            else:
                pair_hist["none_resolved"] += 1
            s2_per_s1[c2] += 1
            s3_per_s1[c3] += 1
            k = c2 + c3
            total_per_s1[k] += 1
            cluster_hist[str(k) if k <= 12 else "13+"] += 1


    def pct(v, q):
        return v[int(q * (len(v) - 1))] if v else None

    d2 = sorted(deg_s2.values(), reverse=True)
    d3 = sorted(deg_s3.values(), reverse=True)
    rep2 = sum(1 for v in deg_s2.values() if v > 1)
    rep3 = sum(1 for v in deg_s3.values() if v > 1)

    res = {
        "rows": n_rows,
        "singletons": n_empty,
        "singleton_rate": round(n_empty / n_rows, 6) if n_rows else None,
        "bad_prefix_rows": n_bad_prefix,
        "self_matches": n_self_match,
        "mismatched_source_ids": n_mismatch,
        "unknown_ids": n_unknown_id,
        "unknown_S2": n_unknown_2,
        "unknown_S3": n_unknown_3,
        "dups_within_list": n_dup,
        "composition": dict(pair_hist),
        "s2_per_s1": {str(k): v for k, v in sorted(s2_per_s1.items())},
        "s3_per_s1": {str(k): v for k, v in sorted(s3_per_s1.items())},
        "total_per_s1": {str(k): v for k, v in sorted(total_per_s1.items())},
        "cluster_hist": dict(cluster_hist),
        "multi_claimed_S2": {
            "distinct_claimed": len(deg_s2),
            "claimed_by_gt_1_rows": rep2,
            "rate": round(rep2 / max(1, len(deg_s2)), 6),
            "top_claims": sorted(deg_s2.values(), reverse=True)[:20],
        },
        "multi_claimed_S3": {
            "distinct_claimed": len(deg_s3),
            "claimed_by_gt_1_rows": rep3,
            "rate": round(rep3 / max(1, len(deg_s3)), 6),
            "top_claims": sorted(deg_s3.values(), reverse=True)[:20],
        },
        "degree_S2": {"p50": pct(d2, .5), "p90": pct(d2, .9),
                      "p99": pct(d2, .99), "max": d2[0] if d2 else None},
        "degree_S3": {"p50": pct(d3, .5), "p90": pct(d3, .9),
                      "p99": pct(d3, .99), "max": d3[0] if d3 else None},
        "elapsed_s": round(time.time() - t0, 1),
    }
    op = os.path.join(OUT, "gt_graph.json")
    with open(op, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    slim = {k: v for k, v in res.items()
            if k not in ("s2_per_s1", "s3_per_s1", "total_per_s1",
                         "cluster_hist")}
    log(json.dumps(slim, indent=1))
    log(f"-> {op}")


if __name__ == "__main__":
    main()

