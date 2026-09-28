"""Challenge-faithful scoring and output policy utilities."""
from __future__ import annotations

import math
from typing import Mapping

from amazon_contract import parse_id_list


def entity_f05(gold: object, pred: object) -> float:
    gold_set = set(gold) if gold is not None else set()
    pred_set = set(pred) if pred is not None else set()
    if not gold_set and not pred_set:
        return 1.0
    tp = len(gold_set & pred_set)
    fp = len(pred_set - gold_set)
    fn = len(gold_set - pred_set)
    den = 5 * tp + 4 * fp + fn
    return 5 * tp / den if den else 0.0


def macro_f05(truth: Mapping[str, object], pred: Mapping[str, object]) -> float:
    values = [entity_f05(truth[e], pred.get(e) or set()) for e in truth]
    return sum(values) / len(values) if values else 0.0


def choose_from_candidates(candidate_ids: str, scores: Mapping[str, float], threshold: float) -> list[str]:
    candidates = parse_id_list(candidate_ids)
    # Deduplicate while preserving first-occurrence order
    seen: set[str] = set()
    unique_candidates: list[str] = []
    for x in candidates:
        if x not in seen:
            seen.add(x)
            unique_candidates.append(x)
    if not math.isfinite(threshold):
        raise ValueError(f"threshold must be finite, got {threshold!r}")
    unscored = [x for x in unique_candidates if x not in scores or not math.isfinite(scores[x])]
    if unscored:
        raise ValueError(f"{len(unscored)} candidate(s) without a finite score, e.g. {unscored[:3]}")
    return [x for x in unique_candidates if scores[x] >= threshold]
