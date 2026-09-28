"""Fodors–Zagats proxy benchmark for the Amazon ML 2026 strategy.

The public benchmark supplies sampled pair labels, not a complete negative table.
This harness therefore keeps three states separate: known positives, known
negatives, and unknown cross-table pairs. It tests retrieval recall, lexical
features, and model ranking. It does not claim a leaderboard-equivalent score.
"""
from __future__ import annotations

import argparse
import csv
import json
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import numpy as np
from rapidfuzz import fuzz
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_fscore_support
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

STOP = {"a", "an", "and", "the", "of", "for", "with", "to", "in", "on", "by"}


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKC", "" if value is None else str(value))
    text = text.casefold().replace("&", " and ")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = "".join(ch if ch.isalnum() else " " for ch in text)
    return " ".join(text.split())


def grams(value: str, n: int = 3) -> set[str]:
    # A blank value yields no grams: without this guard "" padded to "  " has
    # length 2 <= n and would return {"  "}, making blank-vs-blank ngram
    # similarity 1.0 for two records that share no content. The strip() covers
    # whitespace-only input too, which `if not value` alone would miss.
    compact = value.replace(" ", "")
    if not compact.strip():
        return set()
    padded = f" {compact} "
    return {padded} if len(padded) <= n else {padded[i : i + n] for i in range(len(padded) - n + 1)}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def tokens(value: str) -> set[str]:
    return {t for t in value.split() if t not in STOP and len(t) >= 2}


@dataclass(frozen=True)
class FZ:
    root: Path
    left: list[dict[str, str]]
    right: list[dict[str, str]]
    train: list[dict[str, str]]
    valid: list[dict[str, str]]
    test: list[dict[str, str]]

    def labels(self, split: str) -> dict[tuple[str, str], int]:
        # Parse strictly. Treating any non-"true" value as a negative would
        # silently convert a typo or blank cell into a wrong label.
        out: dict[tuple[str, str], int] = {}
        for r in getattr(self, split):
            raw = str(r["matching"]).strip().casefold()
            if raw in {"1", "true"}:
                value = 1
            elif raw in {"0", "false"}:
                value = 0
            else:
                raise ValueError(f"unrecognised matching label {r['matching']!r} in split {split!r}")
            out[(str(r["source_id"]), str(r["target_id"]))] = value
        return out

    def positives(self, split: str) -> set[tuple[str, str]]:
        return {p for p, y in self.labels(split).items() if y == 1}


def load_fz(root: Path) -> FZ:
    def table(path: Path) -> list[dict[str, str]]:
        return read_csv(path)
    return FZ(root, table(root / "record_descriptions/1_fodors.csv"), table(root / "record_descriptions/2_zagats.csv"), read_csv(root / "gs_train.csv"), read_csv(root / "gs_val.csv"), read_csv(root / "gs_test.csv"))


def make_indexes(data: FZ) -> tuple[list[str], list[str], dict[str, list[int]], dict[str, list[int]], dict[str, list[int]]]:
    names = [norm(r["name"]) for r in data.right]
    addresses = [norm(f"{r.get('addr', '')} {r.get('city', '')}") for r in data.right]
    name_tokens: dict[str, list[int]] = defaultdict(list)
    name_grams: dict[str, list[int]] = defaultdict(list)
    address_tokens: dict[str, list[int]] = defaultdict(list)
    for i, (name, address) in enumerate(zip(names, addresses)):
        for token in tokens(name):
            name_tokens[token].append(i)
        for gram in grams(name):
            name_grams[gram].append(i)
        for token in tokens(address):
            address_tokens[token].append(i)
    return names, addresses, name_tokens, name_grams, address_tokens


def candidates(data: FZ, top_k: int = 50) -> tuple[list[dict[str, object]], dict[str, object]]:
    names, addresses, name_tokens, name_grams, address_tokens = make_indexes(data)
    exact_name: dict[str, list[int]] = defaultdict(list)
    exact_address: dict[str, list[int]] = defaultdict(list)
    for i, (name, address) in enumerate(zip(names, addresses)):
        if name:
            exact_name[name].append(i)
        if address:
            exact_address[address].append(i)
    rows: list[dict[str, object]] = []
    route_counts: dict[str, int] = defaultdict(int)
    for left in data.left:
        name = norm(left["name"])
        address = norm(f"{left.get('addr', '')} {left.get('city', '')}")
        found: dict[int, set[str]] = defaultdict(set)
        for i in exact_name.get(name, ()):
            found[i].add("name_exact")
        for i in exact_address.get(address, ()):
            found[i].add("address_exact")
        for token in tokens(name):
            # Hoist the posting lookup and the cap test out of the inner loop;
            # both are invariant per token.
            posting = name_tokens.get(token, ())
            if len(posting) > 300:
                continue
            for i in posting:
                found[i].add("name_token")
        for token in tokens(address):
            posting = address_tokens.get(token, ())
            if len(posting) > 300:
                continue
            for i in posting:
                found[i].add("address_token")
        for gram in grams(name):
            posting = name_grams.get(gram, ())
            if len(posting) > 600:
                continue
            for i in posting:
                found[i].add("name_ngram")
        # Evidence is a bounded 0..1 route-agreement signal so that the
        # 0.65/0.35 similarity weights actually apply. The previous
        # len(routes) * 2.0 term was on a 2..10 scale and swamped the blend.
        max_routes = max((len(r) for r in found.values()), default=1) or 1
        ranked: list[tuple[float, int]] = []
        for i, routes in found.items():
            ns = fuzz.WRatio(name, names[i]) if name and names[i] else 0.0
            ass = fuzz.token_set_ratio(address, addresses[i]) if address and addresses[i] else 0.0
            evidence = len(routes) / max_routes
            ranked.append((0.65 * ns + 0.35 * ass + evidence, i))
        ranked.sort(key=lambda x: (-x[0], int(data.right[x[1]]["subject_id"])))
        for score, i in ranked[:top_k]:
            route_counts[",".join(sorted(found[i]))] += 1
            rows.append({"source_id": left["subject_id"], "target_id": data.right[i]["subject_id"], "left": left, "right": data.right[i], "retrieval_score": float(score), "routes": sorted(found[i])})
    stats = {"candidate_rows": len(rows), "left_rows": len(data.left), "right_rows": len(data.right), "mean_per_left": len(rows) / max(1, len(data.left)), "cartesian_pairs": len(data.left) * len(data.right), "route_counts": dict(route_counts)}
    return rows, stats


def similarity(a: object, b: object) -> dict[str, float]:
    sa, sb = norm(a), norm(b)
    ta, tb = set(sa.split()), set(sb.split())
    ga, gb = grams(sa), grams(sb)
    return {"exact": float(bool(sa and sa == sb)), "ratio": fuzz.ratio(sa, sb) / 100 if sa and sb else 0.0, "token_sort": fuzz.token_sort_ratio(sa, sb) / 100 if sa and sb else 0.0, "token_set": fuzz.token_set_ratio(sa, sb) / 100 if sa and sb else 0.0, "jaccard": len(ta & tb) / len(ta | tb) if ta | tb else 0.0, "ngram": len(ga & gb) / len(ga | gb) if ga | gb else 0.0}


def row_features(row: Mapping[str, object]) -> dict[str, float]:
    left, right = row["left"], row["right"]
    n = similarity(left.get("name"), right.get("name"))
    a = similarity(f"{left.get('addr', '')} {left.get('city', '')}", f"{right.get('addr', '')} {right.get('city', '')}")
    out = {f"name_{k}": v for k, v in n.items()}
    out.update({f"address_{k}": v for k, v in a.items()})
    out["name_address_mean"] = (n["token_set"] + a["token_set"]) / 2
    out["name_address_min"] = min(n["token_set"], a["token_set"])
    out["retrieval_score"] = float(row.get("retrieval_score", 0.0))
    return out


# NOTE: The public labels are a SAMPLE of pairs, not a complete truth table.
# Emitting one row per labelled pair fabricates positives/negatives that
# retrieval never produces, so the pair model was being trained and scored on
# rows no deployment candidate list could contain. Model metrics are therefore
# restricted to pairs that retrieval actually retrieved; recall of the
# positives we fail to retrieve is reported separately by run(). Scoring is
# "retrieved-only" and must not be read as an end-to-end candidate-set score.
def all_labeled_rows(data: FZ, split: str, candidate_keys: set[tuple[str, str]]) -> list[dict[str, object]]:
    lm = {r["subject_id"]: r for r in data.left}
    rm = {r["subject_id"]: r for r in data.right}
    return [
        {"source_id": s, "target_id": t, "left": lm[s], "right": rm[t], "label": y, "retrieval_score": 0.0, "routes": []}
        for (s, t), y in data.labels(split).items()
        if (s, t) in candidate_keys
    ]


def xy(rows: list[dict[str, object]]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    fs = [row_features(r) for r in rows]
    names = sorted(fs[0]) if fs else []
    return np.asarray([[f.get(n, 0.0) for n in names] for f in fs], dtype=float), np.asarray([r["label"] for r in rows], dtype=int), names


def f05(y: np.ndarray, pred: np.ndarray) -> float:
    # F0.5 = 5*TP / (5*TP + 4*FP + FN). beta<1 weights recall, so the extra
    # weight belongs on FN, not FP. (5*tp + 1*fp + 4*fn would be F2.)
    tp = int(np.sum((y == 1) & (pred == 1))); fp = int(np.sum((y == 0) & (pred == 1))); fn = int(np.sum((y == 1) & (pred == 0)))
    den = 5 * tp + 4 * fp + fn
    return 5 * tp / den if den else 0.0


def pair_metrics(y: np.ndarray, score: np.ndarray, threshold: float) -> dict[str, float]:
    pred = (score >= threshold).astype(int)
    # Guard both metrics the same way: average="binary" needs both classes
    # present, exactly like average_precision_score does.
    two_class = len(np.unique(y)) > 1
    p, r, f = (precision_recall_fscore_support(y, pred, average="binary", zero_division=0)[:3] if two_class else (0.0, 0.0, 0.0))
    return {"precision": float(p), "recall": float(r), "f1": float(f), "f05": f05(y, pred), "ap": float(average_precision_score(y, score)) if two_class else 0.0, "n": int(len(y)), "positives": int(y.sum()), "threshold": float(threshold)}


def select_threshold(y: np.ndarray, score: np.ndarray) -> tuple[float, dict[str, float]]:
    choices = [(f05(y, (score >= t).astype(int)), float(t)) for t in np.unique(np.r_[0.0, 1.0, score])]
    best_f, best_t = max(choices, key=lambda x: (x[0], x[1]))
    return best_t, pair_metrics(y, score, best_t)


def run(data: FZ, seed: int = 17) -> dict[str, object]:
    candidate_rows, retrieval_stats = candidates(data)
    candidate_keys = {(str(r["source_id"]), str(r["target_id"])) for r in candidate_rows}
    train, valid, test = (all_labeled_rows(data, x, candidate_keys) for x in ("train", "valid", "test"))
    xtr, ytr, feature_names = xy(train); xva, yva, _ = xy(valid); xte, yte, _ = xy(test)
    models = {"logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=250, class_weight="balanced", random_state=seed)), "hist_gbdt": HistGradientBoostingClassifier(max_iter=80, learning_rate=0.07, max_leaf_nodes=7, l2_regularization=1.0, random_state=seed)}
    out: dict[str, object] = {"dataset": "Fodors-Zagats", "retrieval": retrieval_stats, "labels": {"train": len(data.train), "valid": len(data.valid), "test": len(data.test), "positive_total": len(data.positives("train")) + len(data.positives("valid")) + len(data.positives("test"))}, "models": {}, "feature_names": feature_names}
    for split in ("train", "valid", "test"):
        p = data.positives(split)
        out["retrieval"][f"{split}_positive_recall"] = len(p & candidate_keys) / max(1, len(p))
        out["retrieval"][f"{split}_positives"] = len(p)
        out["retrieval"][f"{split}_recalled"] = len(p & candidate_keys)
    for name, model in models.items():
        model.fit(xtr, ytr)
        sv, st = model.predict_proba(xva)[:, 1], model.predict_proba(xte)[:, 1]
        threshold, selected = select_threshold(yva, sv)
        out["models"][name] = {"valid_selected": selected, "train_pair": pair_metrics(ytr, model.predict_proba(xtr)[:, 1], threshold), "valid_pair": pair_metrics(yva, sv, threshold), "test_pair": pair_metrics(yte, st, threshold), "threshold": threshold}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--data-root", type=Path, required=True); parser.add_argument("--out", type=Path, required=True); args = parser.parse_args()
    result = run(load_fz(args.data_root))
    args.out.parent.mkdir(parents=True, exist_ok=True); args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"); print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
