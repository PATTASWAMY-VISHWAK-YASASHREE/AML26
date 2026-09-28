"""Entity-level policy smoke tests for zero, one, and many matches.

The Fodors–Zagats public labels are sampled pair labels and are not a complete
entity truth table. These tests validate policy mechanics only; they do not
pretend to be a competition score.
"""
from __future__ import annotations

from typing import Iterable, Mapping


def macro_set_f05(
    truth: Mapping[str, set[str]],
    pred: Mapping[str, set[str]],
    empty_fn: float = 1.0,
) -> dict[str, float | int]:
    """Entity-level F0.5 over TP/FP/FN.

    F0.5 = 5*TP / (5*TP + 4*FP + FN) -- FN carries the extra weight because
    beta<1 weights recall. ``empty_fn`` scores an entity whose gold set is
    empty and which is correctly predicted empty; the contract is 1.0.
    """
    per: list[float] = []
    for entity, gold in truth.items():
        got = set(pred.get(entity, set()))
        if not gold and not got:
            score = empty_fn
        else:
            tp = len(gold & got); fp = len(got - gold); fn = len(gold - got)
            den = 5 * tp + 4 * fp + fn
            score = 5 * tp / den if den else 0.0
        per.append(score)
    return {"macro_f05": sum(per) / len(per) if per else 0.0, "entities": len(per), "empty_entities": sum(not g for g in truth.values())}


def choose_matches(candidates: Iterable[tuple[str, float]], threshold: float, max_per_entity: int | None = None) -> set[str]:
    if max_per_entity is not None:
        if max_per_entity < 0:
            raise ValueError(f"max_per_entity must be non-negative, got {max_per_entity}")
    chosen = [(target, score) for target, score in candidates if score >= threshold]
    chosen.sort(key=lambda x: (-x[1], x[0]))
    if max_per_entity is not None:
        chosen = chosen[:max_per_entity]
    return {target for target, _ in chosen}


# NOTE: deliberately NOT named test_* -- pytest collects test_* callables and a
# non-None return value is a collection error in pytest 8.x. This is a fixture
# builder consumed by test_policy_fixtures.py, not a test.
def fixture_zero_one_many() -> dict[str, object]:
    truth = {"empty": set(), "one": {"a"}, "many": {"a", "b"}}
    scores = {
        "empty": [("a", 0.10)],
        "one": [("a", 0.98), ("b", 0.20)],
        "many": [("a", 0.99), ("b", 0.97), ("c", 0.80)],
    }
    pred = {entity: choose_matches(values, 0.9) for entity, values in scores.items()}
    return {"truth": truth, "pred": pred, "metric": macro_set_f05(truth, pred), "one_to_many_without_cap": pred["many"]}


# NOTE: same naming caveat as above -- not collected by pytest.
def fixture_capped() -> dict[str, object]:
    """Exercise the max_per_entity cap path and its negative-value guard."""
    candidates = [("a", 0.99), ("b", 0.97), ("c", 0.80)]
    capped = choose_matches(candidates, 0.9, max_per_entity=1)
    try:
        choose_matches(candidates, 0.9, max_per_entity=-1)
    except ValueError:
        rejected = True
    else:
        rejected = False
    return {"capped": capped, "negative_max_rejected": rejected}
