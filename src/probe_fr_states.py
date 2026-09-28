"""Check the upstream France handling in normalize.py.

The test set introduces France, a country absent from training, so any
country-keyed lookup without a fallback is the highest-value bug class here.
Two things are checked:
  1. does an unseen country raise, or degrade safely?
  2. is France treated consistently with the countries that ARE in training?
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).parent / "_upstream" / "src"
sys.path.insert(0, str(SRC))
import normalize as N  # noqa: E402

failures: list[str] = []


def check(label, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}{(' :: ' + detail) if detail else ''}")
    if not ok:
        failures.append(label)


def main() -> int:
    print("state/region map sizes")
    for k, v in N.STATE_MAPS.items():
        print(f"    {k:8s} {len(v):4d} entries")

    # --- 1. unseen country must degrade, not raise -----------------------
    check("STATE_MAPS lookup uses .get with a default",
          "get(country" in (SRC / "normalize.py").read_text(encoding="utf-8"))

    # --- 2. abbreviation-as-key coverage --------------------------------
    # normalize.py runs `for _m in (US_STATES, IN_STATES)` to add each
    # abbreviation as a key mapping to itself. Is France in that loop?
    src = (SRC / "normalize.py").read_text(encoding="utf-8")
    loop = "for _m in (US_STATES, IN_STATES):" in src
    check("abbreviation self-map loop exists", loop)

    abbrevs = {"US": "ca", "India": "mh", "France": "idf"}
    print("\nis the abbreviation itself recognised as a region key?")
    for country, ab in abbrevs.items():
        has = ab in N.STATE_MAPS[country]
        print(f"    {country:8s} '{ab}' in map: {has}")
    us_ok = "ca" in N.STATE_MAPS["US"]
    fr_ok = "idf" in N.STATE_MAPS["France"]
    check("US abbreviations are self-mapped (baseline works)", us_ok)
    check("France abbreviations are ALSO self-mapped", fr_ok,
          "France excluded from the (US_STATES, IN_STATES) loop"
          if not fr_ok else "")

    # --- 3. does it change tokenisation? --------------------------------
    if N.STATE_MAPS and hasattr(N, "norm_address"):
        fn = getattr(N, "norm_address")
        for country, raw in (("US", "1 Main St, Springfield, CA 90210"),
                             ("France", "10 rue de rivia, Paris, idf 75001"),
                             ("France", "10 rue de rivia, Paris, ile de france 75001")):
            try:
                out = fn(raw, country)
                print(f"    {country:8s} {raw[:42]:44s} -> {out}")
            except Exception as exc:  # noqa: BLE001
                print(f"    {country:8s} {raw[:42]:44s} -> RAISED {type(exc).__name__}: {exc}")

    if failures:
        print("\nfindings:")
        for f in failures:
            print("  - " + f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
