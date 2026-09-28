"""How much does degree-1 conflict resolution actually buy?

The constraint is real (verify_degree1.py: 0 conflicts in 3,746,510 ids), but
its value depends on how often a scorer actually emits a contested record.
This measures that on REAL train ground truth:

  * how many S2/S3 records are claimed by exactly one S1  (the normal case)
  * what a naive scorer that ALSO keeps the runner-up would cost, i.e. the
    ceiling on what conflict resolution can recover
  * the macro-F0.5 delta between the two, per country

Read-only, streaming, bounded memory.
"""
from __future__ import annotations

import csv
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "run_src", "src"))
from postprocess import f05_entity  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "amazon_ml_2026_research", "student_resource", "dataset")


def main():
    # record -> owning s1, streamed from the ground truth
    owner = {}
    dup_claim = 0
    n_edges = 0
    n_rows = 0
    n_sing = 0
    per_s1 = defaultdict(list)      # s1 -> list of match counts (for cluster size)
    gt_path = os.path.join(DATA, "train", "train_ground_truth.tsv")
    with open(gt_path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(rd, None)
        for rec in rd:
            if not rec:
                continue
            n_rows += 1
            s1 = rec[0].strip()
            vals = [v.strip() for v in
                    (rec[1].split(",") if len(rec) > 1 and rec[1].strip() else [])
                    if v.strip()]
            if not vals:
                n_sing += 1
                per_s1[s1].append(0)
                continue
            per_s1[s1].append(len(vals))
            for v in vals:
                n_edges += 1
                if v in owner and owner[v] != s1:
                    dup_claim += 1
                else:
                    owner[v] = s1

    print(f"gt rows            : {n_rows:,}")
    print(f"true edges         : {n_edges:,}")
    print(f"singletons         : {n_sing:,} ({100 * n_sing / n_rows:.2f}%)")
    print(f"distinct S2/S3 recs: {len(owner):,}")
    print(f"records claimed by >1 S1: {dup_claim}   <- the constraint")
    print()

    # What would a scorer cost by ALSO keeping the runner-up claim?
    # In the true labels this situation cannot arise, so we model it as:
    # a scorer with per-pair error rate eps emits, for each true edge, a
    # correct claim plus a wrong claim against a random other S1.
    print("Modelled cost of a scorer that emits one wrong claim per true edge")
    print("(p_wrong = probability the extra claim is attached to a true edge's")
    print(" record, i.e. how often it is a *guaranteed* false positive):")
    print()
    print("  p_wrong   macroF0.5 no-resolve   with-resolve   delta")
    hist = Counter()
    for s1, cnts in per_s1.items():
        hist[cnts[0]] += 1
    for pw in (0.0, 0.05, 0.10, 0.20, 0.30):
        before = 0.0
        after = 0.0
        for s1, cnts in per_s1.items():
            nt = cnts[0]
            n_pred = nt  # one claim per true edge
            if nt > 0 and pw > 0:
                # a wrong claim lands on some OTHER s1; on average it adds one
                # false positive to a random entity with nt>0
                n_pred += 1
            tp = nt
            before += f05_entity(n_pred, nt, tp)
            # with resolution the wrong claim is dropped: the contested record
            # goes to its true owner, so precision returns to 1.0
            after += f05_entity(nt, nt, tp)
        b = before / n_rows
        a = after / n_rows
        print(f"  {pw:5.2f}      {b:18.4f}   {a:14.4f}   {a - b:+.4f}")

    print()
    print("Upper bound on the gain: a resolved scorer is exactly the")
    print("perfect-precision scorer, so the delta column is the whole prize.")
    print(f"Entities with nt>0: {sum(v for k, v in hist.items() if k > 0):,}")
    print(f"Entities with nt=0: {hist.get(0, 0):,}")


if __name__ == "__main__":
    main()
