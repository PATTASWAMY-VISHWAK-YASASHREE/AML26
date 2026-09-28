"""Bounded, streaming profile of the official Amazon ER training data.

This deliberately keeps only a small systematic sample of source/target rows and
aggregate counters. It is safe to run on the full TSV files without loading them
into a dataframe.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import unicodedata
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz

STOP = {"a", "an", "and", "the", "of", "for", "with", "to", "in", "on", "by"}


def norm(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "").casefold().replace("&", " and ")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = "".join(c if c.isalnum() else " " for c in text)
    return " ".join(text.split())


def toks(value: str | None) -> set[str]:
    return {x for x in norm(value).split() if x not in STOP and len(x) >= 2}


def similarity(a: str | None, b: str | None) -> dict[str, float]:
    na, nb = norm(a), norm(b)
    ta, tb = toks(a), toks(b)
    ga = {na[i : i + 3] for i in range(max(0, len(na) - 2))}
    gb = {nb[i : i + 3] for i in range(max(0, len(nb) - 2))}
    return {
        "exact": float(bool(na and na == nb)),
        "ratio": fuzz.ratio(na, nb) / 100 if na and nb else 0.0,
        "token_set": fuzz.token_set_ratio(na, nb) / 100 if na and nb else 0.0,
        "jaccard": len(ta & tb) / len(ta | tb) if ta | tb else 0.0,
        "ngram": len(ga & gb) / len(ga | gb) if ga | gb else 0.0,
    }


def q(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    # sorted() copies; values.sort() would mutate the caller's list in place.
    ordered = sorted(values)
    # int() truncates the index and biases the quantile low; round instead.
    index = round(p * (len(ordered) - 1))
    return ordered[min(max(index, 0), len(ordered) - 1)]


def profile(root: Path, sample_mod: int) -> dict[str, object]:
    if sample_mod < 1:
        raise ValueError(f"sample_mod must be >= 1, got {sample_mod}")
    gt_path = root / "train_ground_truth.tsv"
    source_ids: set[str] = set()
    target_ids: dict[str, set[str]] = {"S2": set(), "S3": set()}
    sample_gold: list[tuple[str, list[str]]] = []
    cardinality = Counter()
    singleton_rows = 0
    total_rows = 0
    unknown_prefixes: Counter[str] = Counter()
    with gt_path.open(encoding="utf-8", newline="") as handle:
        for i, row in enumerate(csv.DictReader(handle, delimiter="\t")):
            total_rows += 1
            ids = [x.strip() for x in (row["matched_entity_ids"] or "").split(",") if x.strip()]
            cardinality[len(ids)] += 1
            singleton_rows += int(not ids)
            if i % sample_mod == 0:
                sample_gold.append((row["source1_entity_id"], ids))
                source_ids.add(row["source1_entity_id"])
                for target_id in ids:
                    prefix = target_id.split("-", 1)[0]
                    # A bare dict subscript aborts with an unhandled KeyError on an
                    # unexpected prefix (e.g. a self-match to S1, which the task
                    # statement explicitly warns about).
                    if prefix in target_ids:
                        target_ids[prefix].add(target_id)
                    else:
                        unknown_prefixes[prefix] += 1

    sources: dict[str, dict[str, str]] = {}
    with (root / "train_source1.tsv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["entity_id"] in source_ids:
                sources[row["entity_id"]] = row
    targets: dict[str, dict[str, dict[str, str]]] = {"S2": {}, "S3": {}}
    for prefix, filename in (("S2", "train_source2.tsv"), ("S3", "train_source3.tsv")):
        with (root / filename).open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                if row["entity_id"] in target_ids[prefix]:
                    targets[prefix][row["entity_id"]] = row

    metrics: dict[str, list[float]] = {}
    by_country: dict[str, dict[str, list[float]]] = {}
    country_agree = Counter()
    address_missing = Counter()
    positive_links = 0
    # Unresolved joins used to be dropped silently, shrinking the denominator of
    # every downstream statistic while the JSON still looked complete.
    unresolved_sources = 0
    unresolved_targets = 0
    for source_id, gold_ids in sample_gold:
        source = sources.get(source_id)
        if not source:
            unresolved_sources += 1
            continue
        for target_id in gold_ids:
            target = targets.get(target_id.split("-", 1)[0], {}).get(target_id)
            if not target:
                unresolved_targets += 1
                continue
            positive_links += 1
            country_agree[(source["country"], target["country"])] += 1
            # Reuse norm(): a whitespace-only address normalizes to "" and yields
            # 0.0 similarity, so bool() on the raw value overstated presence.
            address_missing["source"] += int(not norm(source["business_address"]))
            address_missing["target"] += int(not norm(target["business_address"]))
            ns = similarity(source["business_name"], target["business_name"])
            aa = similarity(source["business_address"], target["business_address"])
            for prefix, values in (("name", ns), ("address", aa)):
                bucket = by_country.setdefault(source["country"], {})
                for key, value in values.items():
                    metrics.setdefault(f"{prefix}_{key}", []).append(value)
                    bucket.setdefault(f"{prefix}_{key}", []).append(value)

    expected_links = sum(len(ids) for _, ids in sample_gold)
    summary: dict[str, object] = {
        "train_ground_truth_rows": total_rows,
        "singleton_rows": singleton_rows,
        "singleton_fraction": singleton_rows / max(1, total_rows),
        "cardinality": {str(k): v for k, v in sorted(cardinality.items())},
        "sample_sources": len(sample_gold),
        "sample_positive_links": positive_links,
        "expected_sample_positive_links": expected_links,
        "unresolved_sources": unresolved_sources,
        "unresolved_targets": unresolved_targets,
        "unresolved_total": unresolved_sources + unresolved_targets,
        "unknown_target_prefixes": dict(unknown_prefixes),
        "country_pairs": {f"{a}->{b}": n for (a, b), n in country_agree.items()},
        "address_missing": dict(address_missing),
    }
    for key, values in metrics.items():
        summary[key] = {
            "mean": statistics.fmean(values) if values else 0.0,
            "p10": q(values, 0.1),
            "p50": q(values, 0.5),
            "p90": q(values, 0.9),
        }
    for country, values in by_country.items():
        summary.setdefault("by_country", {})[country] = {
            key: {
                "mean": statistics.fmean(vals) if vals else 0.0,
                "p10": q(vals, 0.1),
                "p50": q(vals, 0.5),
                "p90": q(vals, 0.9),
            }
            for key, vals in values.items()
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--sample-mod", type=int, default=1009)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.sample_mod < 1:
        # 0 raises ZeroDivisionError; a negative value silently samples only row 0
        # and still prints as a successful run.
        parser.error(f"--sample-mod must be >= 1, got {args.sample_mod}")
    result = profile(args.root, args.sample_mod)
    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
