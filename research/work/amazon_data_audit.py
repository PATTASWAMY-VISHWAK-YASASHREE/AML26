"""Streaming, low-memory feature extraction for the official Amazon ER data.

The input is intentionally processed in bounded chunks. No full table is loaded.
This module is a data-audit helper, not a final matcher.
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


def tokens(value: str | None) -> set[str]:
    return {x for x in norm(value).split() if x not in STOP and len(x) >= 2}


def sim(a: str | None, b: str | None) -> dict[str, float]:
    na, nb = norm(a), norm(b)
    ta, tb = tokens(a), tokens(b)
    ga = {na[i : i + 3] for i in range(max(0, len(na) - 2))}
    gb = {nb[i : i + 3] for i in range(max(0, len(nb) - 2))}
    return {
        "exact": float(bool(na and na == nb)),
        "ratio": fuzz.ratio(na, nb) / 100 if na and nb else 0.0,
        "token_set": fuzz.token_set_ratio(na, nb) / 100 if na and nb else 0.0,
        "jaccard": len(ta & tb) / len(ta | tb) if ta | tb else 0.0,
        "ngram": len(ga & gb) / len(ga | gb) if ga | gb else 0.0,
    }


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    # int() truncates the index and biases every quantile low; round instead and
    # clamp BOTH ends of the index range.
    index = round(q * (len(ordered) - 1))
    return ordered[min(max(index, 0), len(ordered) - 1)]


def audit(train_root: Path, sample_mod: int = 211) -> dict[str, object]:
    if sample_mod < 1:
        raise ValueError(f"--sample-mod must be >= 1, got {sample_mod}")
    gt_path = train_root / "train_ground_truth.tsv"
    sample_rows: list[tuple[str, list[str]]] = []
    s1_ids: set[str] = set()
    target_ids: dict[str, set[str]] = {"S2": set(), "S3": set()}
    unknown_prefixes: Counter[str] = Counter()
    with gt_path.open(encoding="utf-8", newline="") as handle:
        for i, row in enumerate(csv.DictReader(handle, delimiter="\t")):
            if i % sample_mod:
                continue
            # The ground truth stores "S2-1,S2-2"; unstripped tokens keep their
            # leading space and silently never match a source file.
            ids = [x.strip() for x in (row["matched_entity_ids"] or "").split(",") if x.strip()]
            sample_rows.append((row["source1_entity_id"], ids))
            s1_ids.add(row["source1_entity_id"])
            for target_id in ids:
                prefix = target_id.split("-", 1)[0]
                if prefix in target_ids:
                    target_ids[prefix].add(target_id)
                else:
                    # setdefault-style: an unexpected prefix must not raise KeyError
                    # (e.g. a self-match to S1), and is reported instead.
                    unknown_prefixes[prefix] += 1

    sources: dict[str, dict[str, str]] = {}
    with (train_root / "train_source1.tsv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["entity_id"] in s1_ids:
                sources[row["entity_id"]] = row
    targets: dict[str, dict[str, dict[str, str]]] = {"S2": {}, "S3": {}}
    for prefix, filename in (("S2", "train_source2.tsv"), ("S3", "train_source3.tsv")):
        with (train_root / filename).open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                if row["entity_id"] in target_ids[prefix]:
                    targets[prefix][row["entity_id"]] = row

    metrics: dict[str, list[float]] = {"name_exact": [], "name_ratio": [], "name_token_set": [], "name_jaccard": [], "name_ngram": [], "address_exact": [], "address_ratio": [], "address_token_set": [], "address_jaccard": [], "address_ngram": []}
    country_agree = 0
    links = 0
    target_empty_address = 0
    for source_id, gold_ids in sample_rows:
        source = sources.get(source_id)
        if not source:
            continue
        for target_id in gold_ids:
            target = targets.get(target_id.split("-", 1)[0], {}).get(target_id)
            if not target:
                continue
            ns = sim(source["business_name"], target["business_name"])
            aa = sim(source["business_address"], target["business_address"])
            for prefix, values in (("name", ns), ("address", aa)):
                for key, value in values.items():
                    metrics[f"{prefix}_{key}"].append(value)
            country_agree += int(source["country"] == target["country"])
            target_empty_address += int(not bool(target["business_address"]))
            links += 1
    summary: dict[str, object] = {
        "sample_sources": len(sample_rows),
        "sample_links": links,
        "country_agreement": country_agree / max(1, links),
        "target_empty_address": target_empty_address,
        "unknown_target_prefixes": dict(unknown_prefixes),
    }
    for key, values in metrics.items():
        # fmean over an empty sequence raises StatisticsError; report 0.0 instead.
        summary[key] = {
            "mean": statistics.fmean(values) if values else 0.0,
            "p10": quantile(values, 0.1),
            "p50": quantile(values, 0.5),
            "p90": quantile(values, 0.9),
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-root", type=Path, required=True)
    parser.add_argument("--sample-mod", type=int, default=211)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.sample_mod < 1:
        parser.error(f"--sample-mod must be >= 1, got {args.sample_mod}")
    result = audit(args.train_root, args.sample_mod)
    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
