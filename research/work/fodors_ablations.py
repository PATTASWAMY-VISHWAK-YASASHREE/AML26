"""Label-free blocking ablations on the Fodors–Zagats public proxy."""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from fodors_benchmark import grams, load_fz, norm, tokens


def indexes(data):
    left = data.left
    right = data.right
    names = [norm(r["name"]) for r in right]
    addresses = [norm(f"{r.get('addr', '')} {r.get('city', '')}") for r in right]
    exact_name = defaultdict(set)
    exact_address = defaultdict(set)
    name_token = defaultdict(set)
    address_token = defaultdict(set)
    name_gram = defaultdict(set)
    for i, (name, address) in enumerate(zip(names, addresses)):
        if name:
            exact_name[name].add(i)
        if address:
            exact_address[address].add(i)
        for token in tokens(name):
            name_token[token].add(i)
        for token in tokens(address):
            address_token[token].add(i)
        for gram in grams(name):
            name_gram[gram].add(i)
    return names, addresses, exact_name, exact_address, name_token, address_token, name_gram


def generate(data, method: str, top_k: int | None = None, rare_df: int = 20, gram_count: int = 1) -> tuple[set[tuple[str, str]], dict[str, float | int]]:
    names, addresses, exact_name, exact_address, name_token, address_token, name_gram = indexes(data)
    # Rare filtering is loop-invariant; computing it inside the per-record loop
    # rebuilt the whole dict on every left record. Compute at most once here.
    nt, at = name_token, address_token
    if method.startswith("rare_"):
        nt = {k: v for k, v in name_token.items() if len(v) <= rare_df}
        at = {k: v for k, v in address_token.items() if len(v) <= rare_df}
    out: set[tuple[str, str]] = set()
    per_left: list[int] = []
    for l in data.left:
        name = norm(l["name"])
        address = norm(f"{l.get('addr', '')} {l.get('city', '')}")
        found: set[int] = set()
        if method == "name_exact":
            found |= exact_name.get(name, set())
        elif method == "address_exact":
            found |= exact_address.get(address, set())
        elif method == "name_or_address_exact":
            found |= exact_name.get(name, set()) | exact_address.get(address, set())
        elif method in {"name_token", "rare_name_token", "address_token", "rare_address_token", "name_token_or_address_token", "rare_name_or_address_token", "full_grams"}:
            if method in {"name_token", "rare_name_token", "name_token_or_address_token", "rare_name_or_address_token", "full_grams"}:
                for token in tokens(name):
                    found |= nt.get(token, set())
            if method in {"address_token", "rare_address_token", "name_token_or_address_token", "rare_name_or_address_token", "full_grams"}:
                for token in tokens(address):
                    found |= at.get(token, set())
            if method == "full_grams":
                counts: Counter[int] = Counter()
                for gram in grams(name):
                    counts.update(name_gram.get(gram, set()))
                found |= {i for i, count in counts.items() if count >= gram_count}
            if method in {"name_token_or_address_token", "rare_name_or_address_token", "full_grams"}:
                found |= exact_name.get(name, set()) | exact_address.get(address, set())
        else:
            raise ValueError(method)
        if top_k is not None and len(found) > top_k:
            assert top_k > 0, f"top_k must be positive, got {top_k}"
            # deterministic evidence ranking for capped ablations
            found = set(sorted(found, key=lambda i: (-(fuzz_score(name, names[i], address, addresses[i])), int(data.right[i]["subject_id"])))[:top_k])
        per_left.append(len(found))
        out.update((l["subject_id"], data.right[i]["subject_id"]) for i in found)
    vals = per_left or [0]
    stats = {
        "candidate_rows": len(out),
        "mean_per_left": sum(vals) / len(vals),
        "median_per_left": statistics.median(vals),
        "p95_per_left": sorted(vals)[int(0.95 * (len(vals) - 1))],
        "max_per_left": max(vals),
        "cartesian_pairs": len(data.left) * len(data.right),
    }
    return out, stats


def fuzz_score(a: str, b: str, c: str, d: str) -> float:
    from rapidfuzz import fuzz
    n = fuzz.WRatio(a, b) if a and b else 0
    ad = fuzz.token_set_ratio(c, d) if c and d else 0
    return 0.65 * n + 0.35 * ad


def main() -> None:
    p = argparse.ArgumentParser(); p.add_argument("--data-root", type=Path, required=True); p.add_argument("--out", type=Path, required=True); args = p.parse_args()
    data = load_fz(args.data_root)
    positives = data.positives("train") | data.positives("valid") | data.positives("test")
    # NOTE: "full_union" was a byte-identical duplicate of "full_grams" (both
    # branches matched the same four conditions), so it is dropped here.
    methods = ["name_exact", "address_exact", "name_or_address_exact", "name_token", "rare_name_token", "address_token", "rare_address_token", "name_token_or_address_token", "rare_name_or_address_token", "full_grams"]
    result = {"dataset": "Fodors-Zagats", "positive_pairs": len(positives), "methods": {}}
    for method in methods:
        found, stats = generate(data, method)
        result["methods"][method] = {**stats, "positive_recalled": len(found & positives), "positive_recall": len(found & positives) / max(1, len(positives))}
    result["oracle_cartesian"] = {"positive_recall": 1.0, "cartesian_pairs": len(data.left) * len(data.right)}
    args.out.parent.mkdir(parents=True, exist_ok=True); args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"); print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
