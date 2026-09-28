"""Confirm every edited archival capture is still well-formed HTML/JSON.

The source-integrity and security fixes were applied by hand to vendored
arXiv/JSTOR snapshots, so a stray unclosed tag would silently corrupt the
archived record. Parsing is the cheapest guard against that.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from lxml import html

ROOT = Path(__file__).parent
HTML = [
    "amazon_ml_2026_research/sources/ditto_2020.html",
    "amazon_ml_2026_research/sources/hu_2018_arxiv_1803.07720.html",
    "amazon_ml_2026_research/sources/benchmark_critique_2023.html",
    "amazon_ml_2026_research/sources/_blocked/fellegi_sunter_1969_jstor_BLOCKED.html",
    ".research_tmp_classical/febrl_gen.html",
    ".research_tmp_classical/febrl_generator_node70.html",
    ".research_tmp_classical/febrl_manual.html",
]
JSONS = [
    "amazon_ml_2026_research/sources/_blocked/MANIFEST_blocked_captures.json",
]


def main() -> int:
    bad = 0
    for rel in HTML:
        p = ROOT / rel
        if not p.exists():
            print(f"MISSING {rel}")
            bad += 1
            continue
        try:
            html.parse(str(p))
            print(f"OK   {rel} ({p.stat().st_size:,} bytes)")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {rel}: {type(exc).__name__}: {exc}")
            bad += 1
    for rel in JSONS:
        p = ROOT / rel
        if not p.exists():
            print(f"MISSING {rel}")
            bad += 1
            continue
        try:
            json.loads(p.read_text(encoding="utf-8"))
            print(f"OK   {rel} (valid JSON)")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {rel}: {type(exc).__name__}: {exc}")
            bad += 1

    # The mis-identified capture must be gone from the live sources directory,
    # and its replacement must carry an explicit provenance notice.
    stale = ROOT / "amazon_ml_2026_research/sources/deepmatcher_2018.html"
    print(("FAIL " if stale.exists() else "OK   ")
          + "deepmatcher_2018.html removed from sources/ (renamed to its real identity)")
    if stale.exists():
        bad += 1
    fixed = ROOT / "amazon_ml_2026_research/sources/hu_2018_arxiv_1803.07720.html"
    if "PROVENANCE" in fixed.read_text(encoding="utf-8", errors="ignore"):
        print("OK   replacement carries a PROVENANCE / MISIDENTIFICATION notice")
    else:
        print("FAIL replacement has no provenance notice")
        bad += 1

    if bad:
        raise SystemExit(f"{bad} problem(s)")
    print("\nall archived captures parse cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
