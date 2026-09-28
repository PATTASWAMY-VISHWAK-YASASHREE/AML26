"""Leakage-safe proxy benchmark for the Amazon ML 2026 entity-resolution strategy.

The public DeepMatcher/Magellan archives are pair-labelled product/bibliographic
records. They test retrieval, normalization, pair models, and threshold selection;
they are not a numerical estimate of the private Amazon challenge score. Candidate
generation never reads labels; labels are used only for evaluation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
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

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", "" if value is None else str(value))
    text = text.casefold().replace("&", " and ")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = "".join(ch if ch.isalnum() else " " for ch in text)
    return " ".join(text.split())


def char_ngrams(value: str, n: int = 3) -> set[str]:
    # A blank value yields no grams: otherwise "" padded to "  " has length
    # 2 <= n and returns {"  "}, making blank-vs-blank ngram Jaccard 1.0.
    if not value:
        return set()
    compact = f" {value.replace(' ', '')} "
    if len(compact) <= n:
        return {compact}
    return {compact[i : i + n] for i in range(len(compact) - n + 1)}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


@dataclass(frozen=True)
class ProxyDataset:
    name: str
    left: list[dict[str, str]]
    right: list[dict[str, str]]
    train: list[dict[str, str]]
    valid: list[dict[str, str]]
    test: list[dict[str, str]]
    name_field: str
    secondary_field: str

    def labels(self, split: str) -> dict[tuple[str, str], int]:
        return {(str(x["left_id"]), str(x["right_id"])): int(x["label"]) for x in getattr(self, split)}

    def positives(self, split: str) -> set[tuple[str, str]]:
        return {p for p, y in self.labels(split).items() if y == 1}


def load_dataset(directory: Path, name: str, name_field: str, secondary_field: str) -> ProxyDataset:
    def table(path: Path) -> list[dict[str, str]]:
        rows = read_csv(path)
        for row in rows:
            row["id"] = str(row["id"])
        return rows

    def labels(path: Path) -> list[dict[str, str]]:
        return [{"left_id": str(x["ltable_id"]), "right_id": str(x["rtable_id"]), "label": int(x["label"])} for x in read_csv(path)]

    return ProxyDataset(name, table(directory / "tableA.csv"), table(directory / "tableB.csv"), labels(directory / "train.csv"), labels(directory / "valid.csv"), labels(directory / "test.csv"), name_field, secondary_field)


def generate_candidates(data: ProxyDataset, top_k: int = 8, secondary_k: int = 4) -> list[dict[str, object]]:
    right_ids = [row["id"] for row in data.right]
    right_by_id = {row["id"]: row for row in data.right}
    # O(1) id->index map; the previous right_ids.index(rid) was a linear scan
    # inside a nested loop.
    index_of = {rid: i for i, rid in enumerate(right_ids)}
    names = [normalize_text(row.get(data.name_field, "")) for row in data.right]
    secondary = [normalize_text(row.get(data.secondary_field, "")) for row in data.right]
    exact_names: dict[str, list[str]] = defaultdict(list)
    exact_secondary: dict[str, list[str]] = defaultdict(list)
    for rid, name, sec in zip(right_ids, names, secondary):
        if name:
            exact_names[name].append(rid)
        if sec:
            exact_secondary[sec].append(rid)

    rows: list[dict[str, object]] = []
    # Exact blocks are label-free and fast; the proxy run records their recall
    # rather than spending minutes on all-pairs fuzzy matching.
    def rank_block(query: str, sec_query: str, block: list[str]) -> list[tuple[float, str]]:
        ranked: list[tuple[float, str]] = []
        for rid in block:
            idx = index_of[rid]
            score = fuzz.WRatio(query, names[idx]) if query else 0.0
            if sec_query:
                score = max(score, fuzz.token_set_ratio(sec_query, secondary[idx]))
            ranked.append((float(score), rid))
        ranked.sort(key=lambda x: (-x[0], int(x[1]) if x[1].isdigit() else int(hashlib.sha256(x[1].encode()).hexdigest()[:8], 16)))
        return ranked

    for left in data.left:
        query = normalize_text(left.get(data.name_field, ""))
        sec_query = normalize_text(left.get(data.secondary_field, ""))
        # Rank name and secondary blocks SEPARATELY so secondary_k reserves its
        # own quota; merging them first meant top_k alone decided the cut.
        name_ranked = rank_block(query, sec_query, list(exact_names.get(query, ())))
        sec_ranked = rank_block(query, sec_query, [r for r in exact_secondary.get(sec_query, ()) if r not in exact_names.get(query, ())])
        chosen = name_ranked[:top_k] + sec_ranked[:secondary_k]
        for score, rid in chosen:
            rows.append({"left_id": left["id"], "right_id": rid, "left": left, "right": right_by_id[rid], "retrieval_score": score})
    return rows


def retrieval_stats(data: ProxyDataset, candidates: list[dict[str, object]], split: str, top_k: int, secondary_k: int) -> dict[str, float | int]:
    found = {(str(x["left_id"]), str(x["right_id"])) for x in candidates}
    positives = data.positives(split)
    recalled = positives & found
    counts: dict[str, int] = defaultdict(int)
    # Seed every left id at 0 so median/p95/max include rows that produced no
    # candidates, which previously they silently excluded.
    for row in data.left:
        counts[str(row["id"])] = 0
    for row in candidates:
        counts[str(row["left_id"])] += 1
    values = list(counts.values()) or [0]
    return {"candidate_rows": len(candidates), "left_rows": len(data.left), "mean_candidates_per_left": len(candidates) / max(1, len(data.left)), "median_candidates_per_left": float(np.median(values)), "p95_candidates_per_left": float(np.percentile(values, 95)), "max_candidates_per_left": int(max(values)), "positive_pairs": len(positives), "positive_pairs_recalled": len(recalled), "positive_pair_recall": len(recalled) / max(1, len(positives)), "top_k": top_k, "secondary_k": secondary_k}


def similarity(a: object, b: object) -> dict[str, float]:
    sa, sb = normalize_text(a), normalize_text(b)
    ta, tb = set(sa.split()), set(sb.split())
    ga, gb = char_ngrams(sa), char_ngrams(sb)
    return {"exact": float(bool(sa and sa == sb)), "ratio": fuzz.ratio(sa, sb) / 100 if sa and sb else 0.0, "token_sort": fuzz.token_sort_ratio(sa, sb) / 100 if sa and sb else 0.0, "token_set": fuzz.token_set_ratio(sa, sb) / 100 if sa and sb else 0.0, "jaccard": len(ta & tb) / len(ta | tb) if ta | tb else 0.0, "ngram": len(ga & gb) / len(ga | gb) if ga | gb else 0.0}


def features(row: Mapping[str, object], data: ProxyDataset) -> dict[str, float]:
    left, right = row["left"], row["right"]
    n = similarity(left.get(data.name_field), right.get(data.name_field))
    s = similarity(left.get(data.secondary_field), right.get(data.secondary_field))
    out = {f"name_{k}": v for k, v in n.items()}
    out.update({f"secondary_{k}": v for k, v in s.items()})
    out["name_secondary_mean"] = (n["token_set"] + s["token_set"]) / 2
    out["name_secondary_min"] = min(n["token_set"], s["token_set"])
    out["retrieval_score"] = float(row.get("retrieval_score", 0.0))
    return out


def xy(candidates: list[dict[str, object]], labels: Mapping[tuple[str, str], int], data: ProxyDataset) -> tuple[np.ndarray, np.ndarray, list[str]]:
    rows = [x for x in candidates if (str(x["left_id"]), str(x["right_id"])) in labels]
    fs = [features(x, data) for x in rows]
    names = sorted(fs[0]) if fs else []
    x = np.asarray([[f.get(n, 0.0) for n in names] for f in fs], dtype=float)
    y = np.asarray([labels[(str(r["left_id"]), str(r["right_id"]))] for r in rows], dtype=int)
    return x, y, names


def f05(y: np.ndarray, pred: np.ndarray) -> float:
    tp = int(np.sum((y == 1) & (pred == 1)))
    fp = int(np.sum((y == 0) & (pred == 1)))
    fn = int(np.sum((y == 1) & (pred == 0)))
    return 5 * tp / (5 * tp + 4 * fp + fn) if (5 * tp + 4 * fp + fn) else 0.0


def metrics(y: np.ndarray, score: np.ndarray, threshold: float) -> dict[str, float]:
    pred = (score >= threshold).astype(int)
    p, r, f, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    return {"precision": float(p), "recall": float(r), "f1": float(f), "f05": f05(y, pred), "ap": float(average_precision_score(y, score)) if len(np.unique(y)) > 1 else 0.0, "n": int(len(y)), "positives": int(y.sum()), "threshold": float(threshold)}


def choose_threshold(y: np.ndarray, score: np.ndarray) -> tuple[float, dict[str, float]]:
    candidates = np.unique(np.r_[0.0, 1.0, score])
    choices = [(f05(y, (score >= t).astype(int)), float(t)) for t in candidates]
    best_f, best_t = max(choices, key=lambda x: (x[0], x[1]))
    return best_t, metrics(y, score, best_t)


def run(data: ProxyDataset, seed: int = 7) -> dict[str, object]:
    # Keep the proxy run bounded; retrieval recall is reported explicitly.
    candidates = generate_candidates(data, top_k=8, secondary_k=4)
    train_labels, valid_labels, test_labels = data.labels("train"), data.labels("valid"), data.labels("test")
    xtr, ytr, feature_names = xy(candidates, train_labels, data)
    xva, yva, _ = xy(candidates, valid_labels, data)
    xte, yte, _ = xy(candidates, test_labels, data)
    models = {"logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=120, class_weight="balanced", random_state=seed)), "hist_gbdt": HistGradientBoostingClassifier(max_iter=30, learning_rate=0.1, max_leaf_nodes=7, l2_regularization=1.0, random_state=seed)}
    out: dict[str, object] = {"dataset": data.name, "rows": {"left": len(data.left), "right": len(data.right), "candidate_rows": len(candidates)}, "label_counts": {"train": len(train_labels), "valid": len(valid_labels), "test": len(test_labels)}, "retrieval": {s: retrieval_stats(data, candidates, s, 8, 4) for s in ("train", "valid", "test")}, "models": {}, "feature_names": feature_names}
    # model.fit dies with a confusing sklearn error when the training split has
    # no rows or a single class; record an explicit "unevaluable" status.
    if len(ytr) == 0 or len(np.unique(ytr)) < 2:
        out["models"]["_status"] = "unevaluable: training candidates contain fewer than two classes"
        return out
    for name, model in models.items():
        model.fit(xtr, ytr)
        sv, st = model.predict_proba(xva)[:, 1], model.predict_proba(xte)[:, 1]
        if len(yva) == 0 or len(np.unique(yva)) < 2:
            out["models"][name] = {"status": "unevaluable: validation candidates contain fewer than two classes"}
            continue
        t, vm = choose_threshold(yva, sv)
        # NOTE: the former "valid" key was byte-identical to "valid_selected"
        # (both are the validation metrics at the same selected threshold).
        # Keep one clearly named key.
        out["models"][name] = {"valid_selected": vm, "train": metrics(ytr, model.predict_proba(xtr)[:, 1], t), "test_labeled_candidates": metrics(yte, st, t)}
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=RESULTS / "proxy_results.json")
    args = parser.parse_args()
    specs = {"amazon_google": ("title", "manufacturer"), "dblp_acm": ("title", "venue"), "walmart_amazon": ("title", "category"), "dirty_walmart_amazon": ("title", "category")}
    datasets: dict[str, ProxyDataset] = {}
    missing: list[str] = []
    for name, (field, secondary) in specs.items():
        # NOTE: the bare --data-root fallback is removed. It could resolve all
        # four dataset specs to the same directory, benchmarking identical
        # tables four times and reporting it as four datasets.
        choices = [args.data_root / name / "exp_data", args.data_root / f"{name}_exp_data" / "exp_data"]
        directory = next((p for p in choices if (p / "tableA.csv").exists()), choices[0])
        if (directory / "tableA.csv").exists():
            datasets[name] = load_dataset(directory, name, field, secondary)
        else:
            missing.append(f"{name} (searched {', '.join(str(c) for c in choices)})")
    if missing:
        print("WARNING: no tableA.csv for:\n  " + "\n  ".join(missing))
    if not datasets:
        raise SystemExit("ERROR: no dataset was evaluated; check --data-root")
    result = {"seed": 7, "datasets": {name: run(data) for name, data in datasets.items()}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
