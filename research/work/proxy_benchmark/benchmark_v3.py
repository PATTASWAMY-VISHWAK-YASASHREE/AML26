"""Label-free retrieval and pair-model proxy benchmark.

This version is deliberately conservative: candidate generation uses record text
only, while labels are used only to calculate retrieval recall and model metrics.
The DeepMatcher files are pair-labelled proxies, not the private Amazon challenge
and not a claim of equivalent business-entity accuracy.
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

STOP = {"a", "an", "and", "the", "of", "for", "with", "to", "in", "on", "by", "pc"}


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKC", "" if value is None else str(value))
    text = text.casefold().replace("&", " and ")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = "".join(ch if ch.isalnum() else " " for ch in text)
    return " ".join(text.split())


def grams(value: str, n: int = 3) -> set[str]:
    # Blank input yields no grams: otherwise "" padded to "  " has length 2 <= n
    # and returns {"  "}, making blank-vs-blank ngram similarity 1.0. Same guard
    # as grams() in fodors_benchmark / char_ngrams() in benchmark{,_v2}.
    if not value:
        return set()
    compact = f" {value.replace(' ', '')} "
    return {compact} if len(compact) <= n else {compact[i : i + n] for i in range(len(compact) - n + 1)}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def stable_int(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:12], 16)


@dataclass(frozen=True)
class Proxy:
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
        return {pair for pair, label in self.labels(split).items() if label == 1}


def load_proxy(directory: Path, name: str, name_field: str, secondary_field: str) -> Proxy:
    def table(path: Path) -> list[dict[str, str]]:
        rows = read_csv(path)
        for row in rows:
            row["id"] = str(row["id"])
        return rows

    def labels(path: Path) -> list[dict[str, str]]:
        return [{"left_id": str(x["ltable_id"]), "right_id": str(x["rtable_id"]), "label": int(x["label"])} for x in read_csv(path)]

    return Proxy(name, table(directory / "tableA.csv"), table(directory / "tableB.csv"), labels(directory / "train.csv"), labels(directory / "valid.csv"), labels(directory / "test.csv"), name_field, secondary_field)


def _tokens(value: str) -> set[str]:
    return {x for x in value.split() if x not in STOP and len(x) >= 2}


def _postings(values: list[str]) -> list[dict[str, list[int]]]:
    name_tokens: dict[str, list[int]] = defaultdict(list)
    name_grams: dict[str, list[int]] = defaultdict(list)
    secondary_tokens: dict[str, list[int]] = defaultdict(list)
    for idx, value in enumerate(values):
        for token in _tokens(value):
            name_tokens[token].append(idx)
        for gram in grams(value):
            name_grams[gram].append(idx)
    return [name_tokens, name_grams, secondary_tokens]


def generate_candidates(data: Proxy, top_k: int = 30) -> list[dict[str, object]]:
    right_ids = [r["id"] for r in data.right]
    names = [norm(r.get(data.name_field, "")) for r in data.right]
    secondary = [norm(r.get(data.secondary_field, "")) for r in data.right]
    # Inverted index from normalized value -> row indices, so the exact-match
    # blocks are O(1) lookups instead of rescanning the whole right table for
    # every left record (previously O(n_left * n_right)).
    exact_name_idx: dict[str, list[int]] = defaultdict(list)
    exact_secondary_idx: dict[str, list[int]] = defaultdict(list)
    for idx, value in enumerate(names):
        if value:
            exact_name_idx[value].append(idx)
    for idx, value in enumerate(secondary):
        if value:
            exact_secondary_idx[value].append(idx)
    name_tokens, name_grams, _ = _postings(names)
    secondary_tokens: dict[str, list[int]] = defaultdict(list)
    for idx, value in enumerate(secondary):
        for token in _tokens(value):
            secondary_tokens[token].append(idx)

    # Deterministic per-right-record tie-break, precomputed. Sorting calls this
    # key once per shortlisted candidate per query, so hashing it inline costs a
    # sha256 per comparison instead of a handful per record.
    tie_break = [stable_int(rid) for rid in right_ids]

    # The deterministic posting sample depends only on (dataset, right_id, key),
    # never on the query, so each distinct key is sampled once and reused instead
    # of re-sorting the same posting lists once per left record.
    sample_cache: dict[tuple[str, str], list[int]] = {}

    def sampled(kind: str, key: str, posting: list[int], cap: int) -> list[int]:
        cache_key = (kind, key)
        hit = sample_cache.get(cache_key)
        if hit is None:
            if len(posting) <= cap:
                hit = list(posting)
            else:
                hit = sorted(posting, key=lambda i: stable_int(f"{data.name}:{right_ids[i]}:{key}"))[:cap]
            sample_cache[cache_key] = hit
        return hit

    rows: list[dict[str, object]] = []
    for left in data.left:
        query = norm(left.get(data.name_field, ""))
        sec_query = norm(left.get(data.secondary_field, ""))
        qtokens, qgrams = _tokens(query), grams(query)
        scores: dict[int, float] = defaultdict(float)
        routes: dict[int, set[str]] = defaultdict(set)

        # Exact blocks are never capped.
        for idx in exact_name_idx.get(query, ()):
            scores[idx] = max(scores[idx], 100.0)
            routes[idx].add("name_exact")
        for idx in exact_secondary_idx.get(sec_query, ()):
            scores[idx] = max(scores[idx], 95.0)
            routes[idx].add("secondary_exact")

        # Token and character evidence. Large postings are sampled deterministically
        # to avoid common-word candidate explosions.
        for token in qtokens:
            for idx in sampled("name_token", token, name_tokens.get(token, ()), 600):
                scores[idx] += 3.0
                routes[idx].add("name_token")
        for gram in qgrams:
            for idx in sampled("name_ngram", gram, name_grams.get(gram, ()), 1200):
                scores[idx] += 0.35
                routes[idx].add("name_ngram")
        for token in _tokens(sec_query):
            for idx in sampled("secondary_token", token, secondary_tokens.get(token, ()), 600):
                scores[idx] += 1.5
                routes[idx].add("secondary_token")

        # Rank the shortlist using the same local string metrics used by the model.
        ranked: list[tuple[float, int]] = []
        for idx, evidence in scores.items():
            name_score = fuzz.WRatio(query, names[idx]) if query and names[idx] else 0.0
            sec_score = fuzz.token_set_ratio(sec_query, secondary[idx]) if sec_query and secondary[idx] else 0.0
            combined = max(name_score, 0.7 * name_score + 0.3 * sec_score)
            ranked.append((combined + min(evidence, 20.0) / 20.0, idx))
        ranked.sort(key=lambda item: (-item[0], tie_break[item[1]]))
        for score, idx in ranked[:top_k]:
            rows.append({
                "left_id": left["id"],
                "right_id": right_ids[idx],
                "left": left,
                "right": data.right[idx],
                "retrieval_score": float(score),
                "routes": sorted(routes.get(idx, set())),
            })
    return rows


def sim(a: object, b: object) -> dict[str, float]:
    sa, sb = norm(a), norm(b)
    ta, tb = set(sa.split()), set(sb.split())
    ga, gb = grams(sa), grams(sb)
    return {
        "exact": float(bool(sa and sa == sb)),
        "ratio": fuzz.ratio(sa, sb) / 100 if sa and sb else 0.0,
        "token_sort": fuzz.token_sort_ratio(sa, sb) / 100 if sa and sb else 0.0,
        "token_set": fuzz.token_set_ratio(sa, sb) / 100 if sa and sb else 0.0,
        "jaccard": len(ta & tb) / len(ta | tb) if ta | tb else 0.0,
        "ngram": len(ga & gb) / len(ga | gb) if ga | gb else 0.0,
    }


def feature_row(row: Mapping[str, object], data: Proxy) -> dict[str, float]:
    left, right = row["left"], row["right"]
    n, s = sim(left.get(data.name_field), right.get(data.name_field)), sim(left.get(data.secondary_field), right.get(data.secondary_field))
    out = {f"name_{k}": v for k, v in n.items()}
    out.update({f"secondary_{k}": v for k, v in s.items()})
    out["name_secondary_mean"] = (n["token_set"] + s["token_set"]) / 2
    out["name_secondary_min"] = min(n["token_set"], s["token_set"])
    out["retrieval_score"] = float(row.get("retrieval_score", 0.0))
    out["candidate_exact_name"] = float(bool(row.get("routes") and "name_exact" in row["routes"]))
    out["candidate_exact_secondary"] = float(bool(row.get("routes") and "secondary_exact" in row["routes"]))
    return out


def all_label_rows(data: Proxy, split: str, candidates: list[dict[str, object]] | None = None) -> list[dict[str, object]]:
    """Labelled rows carrying the SAME retrieval fields seen at inference.

    Previously these rows hardcoded retrieval_score 0.0 and routes [], so the
    model trained on features that could never occur at inference. The real
    retrieval values are looked up from the candidate pool.
    """
    lm = {r["id"]: r for r in data.left}
    rm = {r["id"]: r for r in data.right}
    retrieval: dict[tuple[str, str], tuple[float, list[str]]] = {}
    if candidates:
        for c in candidates:
            retrieval[(str(c["left_id"]), str(c["right_id"]))] = (float(c.get("retrieval_score", 0.0)), list(c.get("routes", ())))
    rows = []
    for (lid, rid), label in data.labels(split).items():
        if lid in lm and rid in rm:
            score, routes = retrieval.get((lid, rid), (0.0, []))
            rows.append({"left_id": lid, "right_id": rid, "left": lm[lid], "right": rm[rid], "label": label, "retrieval_score": score, "routes": routes})
    return rows


def xy(rows: list[dict[str, object]], data: Proxy) -> tuple[np.ndarray, np.ndarray, list[str]]:
    fs = [feature_row(row, data) for row in rows]
    names = sorted(fs[0]) if fs else []
    x = np.asarray([[f.get(name, 0.0) for name in names] for f in fs], dtype=float)
    y = np.asarray([int(row["label"]) for row in rows], dtype=int)
    return x, y, names


def f05(y: np.ndarray, pred: np.ndarray) -> float:
    tp = int(np.sum((y == 1) & (pred == 1)))
    fp = int(np.sum((y == 0) & (pred == 1)))
    fn = int(np.sum((y == 1) & (pred == 0)))
    den = 5 * tp + 4 * fp + fn
    return 5 * tp / den if den else 0.0


def pair_metrics(y: np.ndarray, score: np.ndarray, threshold: float) -> dict[str, float]:
    pred = (score >= threshold).astype(int)
    p, r, f, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    return {"precision": float(p), "recall": float(r), "f1": float(f), "f05": f05(y, pred), "ap": float(average_precision_score(y, score)) if len(np.unique(y)) > 1 else 0.0, "n": int(len(y)), "positives": int(y.sum()), "threshold": float(threshold)}


def select_threshold(y: np.ndarray, score: np.ndarray) -> tuple[float, dict[str, float]]:
    choices = [(f05(y, (score >= t).astype(int)), float(t)) for t in np.unique(np.r_[0.0, 1.0, score])]
    _, best_t = max(choices, key=lambda x: (x[0], x[1]))
    return best_t, pair_metrics(y, score, best_t)


def set_f05(truth: Mapping[str, set[str]], pred: Mapping[str, set[str]], ids: list[str]) -> dict[str, float | int]:
    tp = fp = fn = 0
    for sid in ids:
        g, p = set(truth.get(sid, set())), set(pred.get(sid, set()))
        tp += len(g & p); fp += len(p - g); fn += len(g - p)
    den = 5 * tp + 4 * fp + fn
    return {"tp": tp, "fp": fp, "fn": fn, "f05": 5 * tp / den if den else 0.0}


def truth_sets(data: Proxy, split: str) -> dict[str, set[str]]:
    return truth_sets_from_labels(data.labels(split))


def truth_sets_from_labels(labels: Mapping[tuple[str, str], int]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for (lid, rid), label in labels.items():
        if label == 1:
            out[lid].add(rid)
    return dict(out)


def evaluate_candidates(data: Proxy, candidates: list[dict[str, object]], split: str, threshold: float, scores: dict[tuple[str, str], float], labels: Mapping[tuple[str, str], int] | None = None) -> dict[str, float | int]:
    pred: dict[str, set[str]] = defaultdict(set)
    for row in candidates:
        key = (str(row["left_id"]), str(row["right_id"]))
        if scores.get(key, 0.0) >= threshold:
            pred[key[0]].add(key[1])
    label_map = data.labels(split) if labels is None else labels
    return set_f05(truth_sets_from_labels(label_map), pred, [r["id"] for r in data.left])


def run(data: Proxy, seed: int = 7) -> dict[str, object]:
    candidates = generate_candidates(data, top_k=30)
    candidate_keys = {(str(x["left_id"]), str(x["right_id"])) for x in candidates}
    # Hoist the label dicts out of the loops; data.labels() rebuilt the entire
    # dict on every call and was previously invoked once per candidate row.
    label_maps = {s: data.labels(s) for s in ("train", "valid", "test")}
    train_rows, valid_rows, test_rows = (all_label_rows(data, s, candidates) for s in ("train", "valid", "test"))
    xtr, ytr, feature_names = xy(train_rows, data)
    xva, yva, _ = xy(valid_rows, data)
    xte, yte, _ = xy(test_rows, data)
    models = {
        "logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=300, class_weight="balanced", random_state=seed)),
        "hist_gbdt": HistGradientBoostingClassifier(max_iter=80, learning_rate=0.07, max_leaf_nodes=15, l2_regularization=1.0, random_state=seed),
    }
    result: dict[str, object] = {"dataset": data.name, "rows": {"left": len(data.left), "right": len(data.right), "candidate_rows": len(candidates)}, "labels": {s: len(label_maps[s]) for s in ("train", "valid", "test")}, "retrieval": {}, "models": {}, "feature_names": feature_names}
    for split in ("train", "valid", "test"):
        positives = {k for k, v in label_maps[split].items() if v == 1}
        result["retrieval"][split] = {"positive_pairs": len(positives), "recalled_positive_pairs": len(positives & candidate_keys), "positive_pair_recall": len(positives & candidate_keys) / max(1, len(positives)), "candidate_rows": len(candidates), "candidate_fraction_of_cartesian": len(candidates) / max(1, len(data.left) * len(data.right))}
    for model_name, model in models.items():
        model.fit(xtr, ytr)
        sv, st = model.predict_proba(xva)[:, 1], model.predict_proba(xte)[:, 1]
        threshold, selected = select_threshold(yva, sv)
        result["models"][model_name] = {"valid_selected": selected, "train_pair": pair_metrics(ytr, model.predict_proba(xtr)[:, 1], threshold), "valid_pair": pair_metrics(yva, sv, threshold), "test_pair": pair_metrics(yte, st, threshold), "threshold": threshold}
        # End-to-end candidate-level evaluation scores EVERY candidate and
        # treats an unlabelled pair as label 0. Restricting the pool to
        # labelled pairs discarded false positives, so these were not truly
        # end-to-end numbers.
        def score_all(rows: list[dict[str, object]], labels: Mapping[tuple[str, str], int]) -> tuple[dict[tuple[str, str], float], list[dict[str, object]]]:
            if not rows:
                return {}, []
            x_all = np.asarray([[feature_row(row, data).get(n, 0.0) for n in feature_names] for row in rows], dtype=float)
            probs = model.predict_proba(x_all)[:, 1]
            scored = [{**r, "label": int(labels.get((str(r["left_id"]), str(r["right_id"])), 0))} for r in rows]
            return {(str(r["left_id"]), str(r["right_id"])): float(p) for r, p in zip(rows, probs)}, scored

        valid_scores, valid_scored = score_all(candidates, label_maps["valid"])
        test_scores, test_scored = score_all(candidates, label_maps["test"])
        result["models"][model_name]["valid_candidate_set"] = evaluate_candidates(data, valid_scored, "valid", threshold, valid_scores, label_maps["valid"])
        result["models"][model_name]["test_candidate_set"] = evaluate_candidates(data, test_scored, "test", threshold, test_scores, label_maps["test"])
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    specs = {"amazon_google": ("title", "manufacturer"), "dblp_acm": ("title", "venue"), "walmart_amazon": ("title", "category"), "dirty_walmart_amazon": ("title", "category")}
    found: dict[str, Proxy] = {}
    missing: list[str] = []
    for name, (field, secondary) in specs.items():
        choices = [args.data_root / name / "exp_data", args.data_root / f"{name}_exp_data" / "exp_data", args.data_root]
        directory = next((p for p in choices if (p / "tableA.csv").exists()), choices[0])
        if (directory / "tableA.csv").exists():
            found[name] = load_proxy(directory, name, field, secondary)
        else:
            missing.append(f"{name} (searched {', '.join(str(c) for c in choices)})")
    # Warn per missing dataset and fail if none were found; previously a
    # mis-rooted --data-root still wrote a successful-looking JSON.
    for entry in missing:
        print(f"WARNING: no tableA.csv for {entry}")
    if not found:
        raise SystemExit("ERROR: no dataset was found; check --data-root")
    output = {"seed": 7, "datasets": {name: run(data) for name, data in found.items()}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
