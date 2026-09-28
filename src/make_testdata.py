"""Generate a synthetic three-source entity-resolution fixture with real linkage.

The fixture is designed to exercise a matcher, so every source2/source3 row is
*derived from its parent source1 record* (index ``i // N_DUP``) and therefore
really shares business_name / address / country with it.  Only formatting-level
noise (case, punctuation, street abbreviations, legal-suffix expansion) is
applied, so a normalising matcher can recover the planted links.

Outputs (into --out):
    source1.tsv, source2.tsv, source3.tsv   one row per record
    ground_truth.tsv                        planted (s1_id, s2_id) / (s1_id, s3_id) pairs
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

N_SRC = 40        # source1 records
N_DUP = 3         # duplicates each source1 record gets in source2 and source3

STREET = ["peets coffee", "main st", "oak ave", "high st", "riverside dr", "union pl", "market st", "park ln"]
CITY = [("peekskill", "us"), ("yonkers", "us"), ("cleveland", "us"), ("akron", "us"), ("utica", "us")]
CTRY = ["United States", "Canada", "United Kingdom", "Germany", "Australia"]
SUFFIX = ["co", "inc", "llc", "ltd"]
# Trailing legal-suffix token -> its expanded form.  Expanding only the final
# token leaves names such as "peets coffee" intact.
SUFFIX_FULL = {"co": "company", "inc": "incorporated", "llc": "limited liability company", "ltd": "limited"}
OWNER = ["acme", "northwind", "blue ridge", "harbor", "summit", "keystone", "lakeside", "ironwood"]
STREET_FULL = {"st": "street", "ave": "avenue", "dr": "drive", "pl": "place", "ln": "lane"}


def suffix_form(rng: random.Random, style: int) -> str:
    """Render a name tail.  ``style`` controls how aggressively it is expanded."""
    s = rng.choice(SUFFIX)
    if style == 0:
        return s
    if style == 1:
        return SUFFIX_FULL[s]
    # style 2: suffix dropped entirely (a common real-world variant)
    return ""


def biz_name(rng: random.Random, style: int) -> str:
    owner = rng.choice(OWNER)
    tail = suffix_form(rng, style)
    return f"{owner} {tail}".strip()


def addr(rng: random.Random) -> str:
    """Build a street address.  Takes only the rng: the record index is unused.

    Only a genuine trailing abbreviation is expanded, so a stem that merely ends
    in a lookalike token (e.g. "peets coffee") is left untouched.
    """
    street = rng.choice(STREET)
    parts = street.split()
    kind = parts[-1]
    stem = " ".join(parts[:-1])
    kind = STREET_FULL.get(kind, kind)
    return f"{rng.randint(1, 999)} {stem} {kind}"


def make_record(rng: random.Random, style: int) -> tuple[str, str, str, str]:
    """Return (business_name, address, city, country) for one synthetic entity."""
    city, _ = rng.choice(CITY)
    return biz_name(rng, style), addr(rng), city.title(), rng.choice(CTRY)


def s1_id(i: int) -> str:
    return f"S1-{200000 + i}"


def s2_id(i: int, k: int) -> str:
    return f"S2-{100000 + i * N_DUP + k}"


def s3_id(i: int, k: int) -> str:
    return f"S3-{300000 + i * N_DUP + k}"


def write_tsv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.write_text("\t".join(header) + "\n" + "".join("\t".join(r) + "\n" for r in rows), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("testdata"), help="output directory")
    ap.add_argument("--seed", type=int, default=20260926, help="RNG seed (output is deterministic)")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    # Source1: one record per planted entity.
    src1: list[list[str]] = []
    for i in range(N_SRC):
        name, address, city, country = make_record(rng, style=0)
        src1.append([s1_id(i), name, address, city, country])

    # Source2/3: derived from the parent source1 row (i // N_DUP), never drawn
    # independently -- this is what makes the planted ground truth real.
    src2: list[list[str]] = []
    src3: list[list[str]] = []
    truth: list[list[str]] = []
    for n in range(N_SRC * N_DUP):
        i = n // N_DUP          # parent source1 index
        k = n % N_DUP           # which duplicate of that parent
        parent = src1[i]
        for style, store, idfn in ((1, src2, s2_id), (2, src3, s3_id)):
            # Reuse the parent's identity fields; only vary the presentation.
            name, address, city, country = parent[1], parent[2], parent[3], parent[4]
            if style == 1:
                # expand/keep the trailing legal suffix, keep the address readable
                head, _, tail = name.rpartition(" ")
                name = f"{head} {SUFFIX_FULL[tail]}" if tail in SUFFIX_FULL else name
                if k == 2:
                    address = address.lower()          # case noise
                    city = city.upper()
            else:
                # drop the legal suffix entirely, and strip a street abbreviation
                name = name.rpartition(" ")[0]
                address = address.replace(" Street", " St").replace(" Avenue", " Ave")
            store.append([idfn(i, k), name, address, city, country])
            truth.append([parent[0], idfn(i, k)])

    args.out.mkdir(parents=True, exist_ok=True)
    header = ["id", "business_name", "address", "city", "country"]
    write_tsv(args.out / "source1.tsv", header, src1)
    write_tsv(args.out / "source2.tsv", header, src2)
    write_tsv(args.out / "source3.tsv", header, src3)
    write_tsv(args.out / "ground_truth.tsv", ["s1_id", "dup_id"], truth)
    print(f"wrote {len(src1)} source1 / {len(src2)} source2 / {len(src3)} source3 rows and "
          f"{len(truth)} ground-truth pairs to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
