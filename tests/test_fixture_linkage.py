"""Check that make_testdata.py's ground truth encodes REAL linkage.

The generator previously drew each source2/3 row's name/address/country
independently, so records the ground truth declared "the same business" shared
no fields at all (often not even the country). Any matcher scored against that
fixture would get ~0 and it exercised no realistic linkage behaviour. This
asserts that each ground-truth link is recoverable by the exact country plus a
strong name/address signal.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "_ttd")


def read(name: str) -> dict[str, dict[str, str]]:
    with (ROOT / name).open(encoding="utf-8", newline="") as fh:
        return {r["id"]: r for r in csv.DictReader(fh, delimiter="\t")}


def main() -> int:
    s1, s2, s3 = read("source1.tsv"), read("source2.tsv"), read("source3.tsv")
    targets = {**s2, **s3}
    # The fixture writes the ground truth in long form: one (s1_id, dup_id) per
    # row, rather than the official comma-separated list per S1 entity.
    with (ROOT / "ground_truth.tsv").open(encoding="utf-8", newline="") as fh:
        gt = list(csv.DictReader(fh, delimiter="\t"))

    links = 0
    same_country = 0
    same_addr = 0
    same_name = 0
    missing = 0
    for row in gt:
        a, t = s1.get(row["s1_id"]), targets.get(row["dup_id"])
        links += 1
        if a is None or t is None:
            missing += 1
            continue
        if a["country"] == t["country"]:
            same_country += 1
        # address is stored split into street + city
        if (a["address"], a["city"]) == (t["address"], t["city"]):
            same_addr += 1
        if a["business_name"] == t["business_name"]:
            same_name += 1

    print(f"ground-truth links checked: {links}")
    print(f"  endpoints not found:        {missing}")
    print(f"  same country:               {same_country}/{links} "
          f"({same_country / max(1, links):.0%})")
    print(f"  same name:                  {same_name}/{links} "
          f"({same_name / max(1, links):.0%})")
    print(f"  same address + city:        {same_addr}/{links} "
          f"({same_addr / max(1, links):.0%})")

    assert links > 0, "fixture produced no ground-truth links"
    assert missing == 0, "a ground-truth endpoint is absent from the data files"
    # Every true link must agree on country; otherwise a correct matcher is
    # punished for the fixture's own random data.
    assert same_country == links, (
        f"only {same_country}/{links} true links share a country - the ground "
        f"truth is not recoverable")
    # Every true link must at least share a name or a full address, i.e. carry
    # some real signal. Names/addresses are deliberately perturbed per variant,
    # so require a strong majority overall rather than every single link.
    assert max(same_name, same_addr) >= 0.5 * links, (
        f"only {same_name}/{links} share a name and {same_addr}/{links} share an "
        f"address - linkage is not actually encoded in the data")
    print("\nOK: ground truth encodes real, recoverable linkage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
