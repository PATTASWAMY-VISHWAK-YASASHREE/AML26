"""Two more preprocessing risks visible in normalize.py, measured on real data.

R1  LEET maps digits to letters, but only for tokens containing BOTH letters and
    digits. "B2B" therefore becomes "bab" -- a false rewrite of a real and
    common business term. Check how often this fires and what it collides with.

R2  NAME_STOP contains the single letters "d", "l", "a". Transliteration can
    emit single-character tokens, and a legitimate one-letter brand token would
    then be dropped from the *core* name (the name used for matching).
"""
from __future__ import annotations

import csv
import os
import sys
from collections import Counter

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
    print("R1: LEET applied to mixed alnum tokens -- what does it rewrite?")
    print("=" * 70)
    fired = Counter()
    for split, src in (("train", 1), ("test", 1)):
        for name, addr, ctry in rows(split, src):
            raw = N.strip_accents(N.translit_text(name or "")).lower()
            for tok in N._non_alnum.split(raw):
                if tok and any(c.isalpha() for c in tok) and any(c.isdigit() for c in tok):
                    # Route through the REAL gate, not a bare translate(), so
                    # this measures what the pipeline actually does.
                    if N._should_leet(tok):
                        fired[(tok, tok.translate(N.LEET))] += 1
                    else:
                        fired[(tok, tok)] += 1
    total = sum(fired.values())
    print(f"  mixed alnum tokens seen: {total:,}")
    print(f"  distinct (before -> after): {len(fired):,}")
    unchanged = [(k, v) for k, v in fired.items() if k[0] == k[1]]
    changed = [(k, v) for k, v in fired.items() if k[0] != k[1]]
    print(f"  left unchanged by the gate : {len(unchanged):,} distinct, "
          f"{sum(v for _, v in unchanged):,} occurrences")
    print(f"  still rewritten by LEET    : {len(changed):,} distinct, "
          f"{sum(v for _, v in changed):,} occurrences")
    print("  most common REWRITES (before -> after):")
    for (b, a), v in sorted(changed, key=lambda kv: -kv[1])[:15]:
        print(f"    {b!r:14s} -> {a!r:14s} {v:,}")
    # collisions: two different originals mapping to the same output
    by_after = Counter()
    for (b, a), v in changed:
        by_after[a] += v
    print("  rewrite targets that are also real words (collision risk):")
    for a, v in by_after.most_common(12):
        print(f"    -> {a!r:14s} {v:,}")

    print()
    print("=" * 70)
    print("R2: single-letter tokens dropped from the core name")
    print("=" * 70)
    single = Counter()
    core_lost = 0
    rows_seen = 0
    for split, src in (("train", 1),):
        for name, addr, ctry in rows(split, src):
            rows_seen += 1
            full, core, alt, dom, dba = N.normalize_name(name)
            for t in full:
                if len(t) == 1:
                    single[(t, ctry)] += 1
            if full and not core:
                core_lost += 1
    print(f"  rows sampled: {rows_seen:,}")
    print(f"  rows whose CORE name became EMPTY: {core_lost:,} "
          f"({100 * core_lost / max(1, rows_seen):.2f}%)")
    print("  most common single-character tokens in the full name:")
    for (t, c), v in single.most_common(15):
        in_stop = t in N.NAME_STOP
        print(f"    {t!r:6s} {c:6s} {v:7,}  in NAME_STOP={in_stop}")
    print(f"  NAME_STOP single letters: "
          f"{sorted(t for t in N.NAME_STOP if len(t) == 1)}")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "analysis_out", "prep_risks.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"rows_sampled={rows_seen}\n")
        f.write(f"core_empty={core_lost}\n")
        f.write("single_char_tokens:\n")
        for (t, c), v in single.most_common(60):
            f.write(f"  {t}\t{c}\t{v}\tstop={t in N.NAME_STOP}\n")
    print(f"  wrote {out}")


if __name__ == "__main__":
    main()
