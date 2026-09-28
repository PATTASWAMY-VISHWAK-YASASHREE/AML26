"""Measure the two preprocessing defects named in AGENT_PROMPT.md, on real data.

D1  normalize.py captures `pin` only when len(n)==6 and country=="India", so a
    US ZIP (5 digits) is never captured. Question: does that actually lose
    information, or is the number still recoverable from `anums`?

D2  the "abbreviations are canonical themselves" self-map loop covers
    (US_STATES, IN_STATES) but not FR_REGIONS, so a French address that already
    carries the canonical code ("hdf", "naq", ...) is not recognised as a state.

Read-only. Streams a bounded sample of the real TSVs.
"""
from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "run_src", "src"))
import normalize as N  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "amazon_ml_2026_research", "student_resource", "dataset")
SAMPLE = 200_000


def rows(split, src, limit=SAMPLE):
    p = os.path.join(DATA, split, f"{split}_source{src}.tsv")
    with open(p, "r", encoding="utf-8", errors="replace", newline="") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(rd, None)
        for i, rec in enumerate(rd):
            if i >= limit:
                return
            if len(rec) >= 4:
                yield rec[1], rec[2], rec[3].strip()


def main():
    print("=" * 70)
    print("D1: is a 5-digit US ZIP recoverable after normalize_address?")
    print("=" * 70)
    for split, src in (("train", 1), ("test", 1)):
        stats = {"US": [0, 0, 0], "India": [0, 0, 0], "France": [0, 0, 0]}
        for name, addr, ctry in rows(split, src):
            if ctry not in stats:
                continue
            toks, nums, st, pin, comps = N.normalize_address(addr, ctry)
            s = stats[ctry]
            s[0] += 1
            if pin:
                s[1] += 1
            # would a bare 5-digit token have survived into anums anyway?
            if any(len(t) == 5 and t.isdigit() for t in nums):
                s[2] += 1
        for c, (n, gotpin, in_anums) in stats.items():
            if not n:
                continue
            print(f"  {split}_s{src} {c:6s} rows={n:7,}  pin_set={gotpin:7,} "
                  f"({100 * gotpin / n:5.2f}%)  5-digit present in anums="
                  f"{in_anums:7,} ({100 * in_anums / n:5.1f}%)")

    print()
    print("=" * 70)
    print("D2: is FR_REGIONS reachable as a self-map?")
    print("=" * 70)
    fr = N.FR_REGIONS
    print(f"  FR_REGIONS entries        : {len(fr)}")
    print(f"  distinct canonical values: {sorted(set(fr.values()))}")
    for v in sorted(set(fr.values())):
        print(f"    {v!r} in FR_REGIONS (self-map present)? {v in fr}")
    print("  self-map loop covers     : (US_STATES, IN_STATES)  <- FR_REGIONS absent")
    # demonstrate: an address already carrying the canonical code
    for probe in ("175 Boulevard Roosevelt, hdf", "12 Rue de la Paix, idf",
                  "3 Rue Victor Hugo, naq"):
        toks, nums, st, pin, comps = N.normalize_address(probe, "France")
        print(f"  probe {probe!r:45s} -> state={st!r}")
    # and a long-form region, for contrast
    for probe in ("175 Bd Roosevelt, Hauts-de-France",
                  "12 Rue de la Paix, Ile de France"):
        toks, nums, st, pin, comps = N.normalize_address(probe, "France")
        print(f"  probe {probe!r:45s} -> state={st!r}")


if __name__ == "__main__":
    main()
