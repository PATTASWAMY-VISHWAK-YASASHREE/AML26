"""Leakage-safe proxy benchmark for the Amazon ML 2026 entity-resolution strategy.

The benchmark intentionally uses only the supplied public DeepMatcher/Magellan
proxy archives. It tests the algorithmic seams, not the challenge's private
score or the semantic similarity of product records to business records.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
from rapidfuzz import fuzz
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_fscore_support
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


# ---------- deterministic text and record normalization ----------

_WS = re.compile(r"\s+")
_NONWORD = re.compile(r"[^a-z0-9]+")
_ADDRESS_TOKENS = re.compile(r"[a-z0-9]+")


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", "" if value is None else str(value))
    text = text.casefold().replace("&", " and ")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = "".join(ch if ch.isalnum() else " " for ch in text)
    return _WS.sub(" ", text).strip()


def char_ngrams(value: str, n: int = 3) -> set[str]:
    # A blank value yields no grams: otherwise "" padded to "  " has length
    # 2 <= n and returns {"  "}, making blank-vs-blank ngram similarity 1.0.
    if not value:
        return set()
    compact = f" {value.replace(' ', '')} "
    if len(compact) <= n:
        return {compact}
    return {compact[i : i + n] for i in range(len(compact) - n + 1)}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def stable_key(*parts: str) -> str:
    return hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest()[:12]


# ---------- schema adapter ----------

@dataclass(frozen=True)
class ProxyDataset:
    name: str
    left: list[dict[str, str]]
    right: list[dict[str, str]]
    train: list[dict[str, str]]
    valid: list[dict[str, str]]
    test: list[dict[str, str]]
    left_name: str
    right_name: str
    address_field: str | None

    @property
    def all_pairs(self) -> list[dict[str, str]]:
        return self.train + self.valid + self.test


def load_deepmatcher(directory: Path, name: str, left_name: str, right_name: str, address_field: str | None) -> ProxyDataset:
    def table(path: Path) -> list[dict[str, str]]:
        rows = read_csv(path)
        for row in rows:
            row["id"] = str(row["id"])
        return rows

    def labels(path: Path) -> list[dict[str, str]]:
        rows = read_csv(path)
        return [
            {
                "left_id": str(row["ltable_id"]),
                "right_id": str(row["rtable_id"]),
                "label": int(row["label"]),
            }
            for row in rows
        ]

    return ProxyDataset(
        name=name,
        left=table(directory / "tableA.csv"),
        right=table(directory / "tableB.csv"),
        train=labels(directory / "train.csv"),
        valid=labels(directory / "valid.csv"),
        test=labels(directory / "test.csv"),
        left_name=left_name,
        right_name=right_name,
        address_field=address_field,
    )


# ---------- blocking ----------

# NOTE: the former blocking_keys() helper was never called by this module and
# has been removed.


def add_name_fields(rows: list[dict[str, str]], field: str) -> list[dict[str, str]]:
    return [{**row, "_name_field": field} for row in rows]


def build_candidates(data: ProxyDataset, split: str, max_per_left: int = 50, inject_positives: bool = True) -> list[dict[str, object]]:
    left_rows = add_name_fields(data.left, data.left_name)
    right_rows = add_name_fields(data.right, data.right_name)
    # LEAKAGE NOTE: injecting label==1 pairs for the split under test makes
    # blocking recall on that split 1.0 by construction. The test pool is
    # therefore built WITHOUT labels (inject_positives=False) and the labels
    # are applied afterwards, for scoring only.
    labeled = getattr(data, split) if inject_positives else []
    # Hard same-name/address neighbors, plus a fixed random negative sample.
    # This is a proxy test harness, not a production blocking implementation.
    by_left: dict[str, list[dict[str, object]]] = defaultdict(list)
    lmap = {r["id"]: r for r in left_rows}
    rmap = {r["id"]: r for r in right_rows}
    # Precompute normalized right names once (inverted index) instead of
    # re-normalizing every right record for every left record.
    right_norm_name = {r["id"]: normalize_text(r.get(data.right_name, "")) for r in right_rows}
    for item in labeled:
        if int(item["label"]) == 1:
            by_left[item["left_id"]].append({"right_id": item["right_id"], "label": 1, "origin": "positive"})
    for left in left_rows:
        candidates = by_left[left["id"]]
        taken: set[str] = {str(c["right_id"]) for c in candidates}
        lname = normalize_text(left.get(data.left_name, ""))
        for right in right_rows:
            rname = right_norm_name[right["id"]]
            same = bool(lname and rname and (fuzz.token_set_ratio(lname, rname) >= 95))
            # Skip right ids already taken (e.g. an injected positive) so a
            # positive is never appended a second time as a hard negative.
            if same and right["id"] not in taken and len(candidates) < max_per_left:
                candidates.append({"right_id": right["id"], "label": 0, "origin": "hard_negative"})
                taken.add(right["id"])
        # deterministic negatives by hash, not labels from test
        if not candidates:
            digest = stable_key(data.name, split, left["id"])
            rid = right_rows[int(digest, 16) % len(right_rows)]["id"]
            if rid not in taken:
                candidates.append({"right_id": rid, "label": 0, "origin": "random_negative"})
                taken.add(rid)
        by_left[left["id"]] = candidates[:max_per_left]
    rows: list[dict[str, object]] = []
    for left in left_rows:
        seen: set[str] = set()
        for cand in by_left[left["id"]]:
            rid = str(cand["right_id"])
            if rid in seen or rid not in rmap:
                continue
            seen.add(rid)
            left_row, right_row = lmap[left["id"]], rmap[rid]
            rows.append({
                "left_id": left["id"],
                "right_id": rid,
                "label": int(cand["label"]),
                "origin": cand["origin"],
                "left": left_row,
                "right": right_row,
            })
    return rows


# ---------- features and models ----------

def field_similarity(a: object, b: object) -> dict[str, float]:
    sa, sb = normalize_text(a), normalize_text(b)
    ta, tb = set(sa.split()), set(sb.split())
    ga, gb = char_ngrams(sa), char_ngrams(sb)
    inter = ga & gb
    union = ga | gb
    return {
        "exact": float(bool(sa and sa == sb)),
        "fuzz_ratio": fuzz.ratio(sa, sb) / 100.0 if sa and sb else 0.0,
        "token_sort": fuzz.token_sort_ratio(sa, sb) / 100.0 if sa and sb else 0.0,
        "token_set": fuzz.token_set_ratio(sa, sb) / 100.0 if sa and sb else 0.0,
        "jaccard": len(ta & tb) / len(ta | tb) if ta | tb else 0.0,
        "ngram": len(inter) / len(union) if union else 0.0,
        "len_ratio": min(len(sa), len(sb)) / max(len(sa), len(sb)) if sa and sb else 0.0,
    }


def pair_features(row: Mapping[str, object], data: ProxyDataset) -> dict[str, float]:
    left, right = row["left"], row["right"]
    name_l = field_similarity(left.get(data.left_name), right.get(data.right_name))
    features = {f"name_{k}": v for k, v in name_l.items()}
    address_field = data.address_field
    if address_field:
        address_l = field_similarity(left.get(address_field), right.get(address_field))
        features.update({f"address_{k}": v for k, v in address_l.items()})
    else:
        features.update({f"address_{k}": v for k, v in field_similarity("", "").items()})
    features["name_address_mean"] = (name_l["token_set"] + features.get("address_token_set", 0.0)) / 2
    features["name_address_min"] = min(name_l["token_set"], features.get("address_token_set", 0.0))
    # NOTE: "origin" (and the former is_hard_negative feature derived from it)
    # is a label-driven provenance field, not an inference-time signal. Exposing
    # it let the model key off how a row was labelled, so it is deliberately
    # excluded from the feature matrix.
    return features


def build_xy(rows: list[dict[str, object]], data: ProxyDataset) -> tuple[np.ndarray, np.ndarray]:
    feature_rows = [pair_features(r, data) for r in rows]
    names = sorted(feature_rows[0]) if feature_rows else []
    x = np.array([[r.get(k, 0.0) for k in names] for r in feature_rows], dtype=float)
    y = np.array([int(r["label"]) for r in rows], dtype=int)
    return x, y


def evaluate_pairwise(y: np.ndarray, score: np.ndarray, threshold: float) -> dict[str, float]:
    pred = (score >= threshold).astype(int)
    p, r, f, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    ap = float(average_precision_score(y, score)) if len(np.unique(y)) > 1 else 0.0
    return {"precision": float(p), "recall": float(r), "f1": float(f), "ap": ap, "n": int(len(y)), "positives": int(y.sum())}


def macro_f05_by_source(truth: Mapping[str, Mapping[str, set[str]]], pred: Mapping[str, Mapping[str, set[str]]], s1_ids: Sequence[str], sources: Sequence[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    vals = []
    for source in sources:
        tp = fp = fn = 0
        for sid in s1_ids:
            g = set(truth.get(sid, {}).get(source, set()))
            p = set(pred.get(sid, {}).get(source, set()))
            tp += len(g & p)
            fp += len(p - g)
            fn += len(g - p)
        den = 5 * tp + 4 * fp + fn
        value = 5 * tp / den if den else 0.0
        out[source] = value
        vals.append(value)
    out["macro"] = sum(vals) / len(vals) if vals else 0.0
    return out


def run_dataset(data: ProxyDataset, seed: int = 7) -> dict[str, object]:
    train = build_candidates(data, "train")
    valid = build_candidates(data, "valid")
    # Keep only the actual test pair labels as an evaluation sample; never use
    # them for model fitting or threshold tuning.
    test_truth = {(r["left_id"], r["right_id"]): int(r["label"]) for r in data.test}
    test = build_candidates(data, "test", inject_positives=False)
    for row in test:
        key = (row["left_id"], row["right_id"])
        # Labels are used for scoring only, never injected into the pool.
        row["label"] = test_truth.get(key, 0)
    xtr, ytr = build_xy(train, data)
    xva, yva = build_xy(valid, data)
    xte, yte = build_xy(test, data)
    # Select threshold on validation only.
    models = {
        "logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, class_weight="balanced", random_state=seed)),
        "hist_gbdt": HistGradientBoostingClassifier(max_iter=180, learning_rate=0.06, max_leaf_nodes=15, l2_regularization=1.0, random_state=seed),
    }
    results: dict[str, object] = {"dataset": data.name, "rows": {"train": len(train), "valid": len(valid), "test": len(test)}, "models": {}}
    for model_name, model in models.items():
        model.fit(xtr, ytr)
        sv = model.predict_proba(xva)[:, 1]
        st = model.predict_proba(xte)[:, 1]
        best = max((evaluate_pairwise(yva, sv, t)["f1"], t) for t in np.linspace(0.05, 0.95, 91))
        threshold = best[1]
        results["models"][model_name] = {
            "train": evaluate_pairwise(ytr, model.predict_proba(xtr)[:, 1], threshold),
            "valid": evaluate_pairwise(yva, sv, threshold),
            "test": evaluate_pairwise(yte, st, threshold),
            "threshold": float(threshold),
        }
    # Use a transparent exact/fuzzy rule for decision-level smoke test.
    decisions = defaultdict(lambda: defaultdict(set))
    for row in test:
        l, rr = row["left"], row["right"]
        ns = field_similarity(l.get(data.left_name), rr.get(data.right_name))
        as_ = field_similarity(l.get(data.address_field) if data.address_field else "", rr.get(data.address_field) if data.address_field else "")
        score = max(ns["token_set"], 0.5 * ns["fuzz_ratio"] + 0.5 * as_["token_set"])
        if score >= 0.92 and (as_["exact"] or as_["token_set"] >= 0.8 or ns["exact"]):
            decisions[row["left_id"]][data.right_name].add(row["right_id"])
    truth = defaultdict(lambda: defaultdict(set))
    for r in data.test:
        if int(r["label"]) == 1:
            truth[r["left_id"]][data.right_name].add(r["right_id"])
    left_ids = sorted({r["id"] for r in data.left})
    results["decision_smoke_macro_f05"] = macro_f05_by_source(truth, decisions, left_ids, [data.right_name])
    results["feature_names"] = sorted(pair_features(train[0], data)) if train else []
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=RESULTS / "proxy_results.json")
    args = parser.parse_args()
    datasets = {
        "amazon_google": ProxyDataset("amazon_google", [], [], [], [], [], "title", "title", "manufacturer"),
        "dblp_acm": ProxyDataset("dblp_acm", [], [], [], [], [], "title", "title", "venue"),
        "walmart_amazon": ProxyDataset("walmart_amazon", [], [], [], [], [], "title", "title", "category"),
        "dirty_walmart_amazon": ProxyDataset("dirty_walmart_amazon", [], [], [], [], [], "title", "title", "category"),
    }
    # Locate extracted archives, accepting either direct or exp_data layout.
    missing: list[str] = []
    for name, proxy in list(datasets.items()):
        candidates = [
            args.data_root / name / "exp_data",
            args.data_root / f"{name}_exp_data" / "exp_data",
            args.data_root,
        ]
        directory = next((path for path in candidates if (path / "tableA.csv").exists()), candidates[0])
        if not (directory / "tableA.csv").exists():
            missing.append(f"{name} (searched {', '.join(str(c) for c in candidates)})")
            continue
        left_field, right_field, address = {
            "amazon_google": ("title", "title", "manufacturer"),
            "dblp_acm": ("title", "title", "venue"),
            "walmart_amazon": ("title", "title", "category"),
            "dirty_walmart_amazon": ("title", "title", "category"),
        }[name]
        loaded = load_deepmatcher(directory, name, left_field, right_field, address)
        datasets[name] = loaded
    output = {"seed": 7, "datasets": {}}
    for name, data in datasets.items():
        if data.left:
            output["datasets"][name] = run_dataset(data)
    # Fail loudly: silently writing {"datasets": {}} and exiting 0 hides a
    # mis-rooted --data-root as a successful run.
    if missing:
        raise SystemExit("ERROR: could not locate tableA.csv for:\n  " + "\n  ".join(missing))
    if not output["datasets"]:
        raise SystemExit("ERROR: no dataset was evaluated; check --data-root")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
