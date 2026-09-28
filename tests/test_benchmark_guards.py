"""Spot-check the semantic guards added to the benchmark modules.

Each of these was a silent-corruption bug: a blank field scored as a perfect
lexical match, or a malformed label quietly became a negative training label.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "amazon_ml_2026_research" / "work"))

import fodors_benchmark as F  # noqa: E402


def main() -> int:
    print("grams('')      ->", F.grams(""))
    print("grams('  ')    ->", F.grams("  "))
    print("grams('cafe')  ->", sorted(F.grams("cafe")))
    assert F.grams("") == set(), "blank value must yield no grams"
    assert F.grams("  ") == set(), "whitespace must yield no grams"

    blank = F.similarity("", "")
    print("ngram similarity of two blanks ->", blank["ngram"], "(was 1.0 before the fix)")
    assert blank["ngram"] == 0.0, "blank-vs-blank must not be a perfect match"

    real = F.similarity("acme cafe", "acme cafe")
    print("ngram similarity of two identical names ->", round(real["ngram"], 3))
    assert real["ngram"] == 1.0, "identical values must still score 1.0"

    # Malformed labels must raise, not silently become a negative.
    class Bad:
        train = [{"source_id": "1", "target_id": "2", "matching": "garbage"}]

    class Good:
        train = [{"source_id": "1", "target_id": "2", "matching": "true"},
                 {"source_id": "1", "target_id": "3", "matching": "false"},
                 {"source_id": "1", "target_id": "4", "matching": "1"},
                 {"source_id": "1", "target_id": "5", "matching": "0"}]

    try:
        F.FZ(None, [], [], Bad.train, [], []).labels("train")
    except ValueError as exc:
        print("garbage label raises ValueError:", exc)
    else:
        raise SystemExit("FAIL: a garbage label was silently accepted as a negative")

    labels = F.FZ(None, [], [], Good.train, [], []).labels("train")
    print("valid labels ->", labels)
    assert labels == {("1", "2"): 1, ("1", "3"): 0, ("1", "4"): 1, ("1", "5"): 0}

    # A correct singleton abstention must score 1.0 per the challenge contract.
    import policy_fixtures as PF
    truth = {"a": set(), "b": {"S2-1"}}
    pred = {"a": set(), "b": {"S2-1"}}
    r = PF.macro_set_f05(truth, pred)
    print("macro_set_f05 on a correct singleton ->", r)
    assert r["macro_f05"] == 1.0, f"a correct singleton must score 1.0, got {r}"

    print("\nall benchmark guard checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
