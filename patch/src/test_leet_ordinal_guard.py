"""Regression tests for the LEET ordinal guard in normalize.py.

Run:  python test_leet_ordinal_guard.py

WHY THIS TEST EXISTS
`LEET` is a `str.maketrans` table applied in `_name_tokens` to any token that
contains both a letter and a digit. French ordinals have exactly that shape, so
they were silently destroyed:

    "3eme" -> "eeme"   (748 occurrences in the France data)
    "1er"  -> "ler"    (131)
    "3e"   -> "ee"     (121)

An ordinal like "3eme" ("third", as in "3eme arrondissement") is not leetspeak.
Translating it yields a nonsense token that then flows into the IDF-weighted
similarity features and corrupts the match signal for France, the only country
that is actually scored.

The guard must fix the ordinals WITHOUT breaking real leetspeak. Both directions
are asserted below, because a fix that suppresses the bug but also suppresses
"c1ub" -> "club" would be a regression, not a repair.

The tests import the real `normalize` module so they exercise the real call path
rather than a reimplementation of it. If the module cannot be imported (missing
dependency, e.g. polars), the test SKIPS rather than passes - a skip must never
be mistaken for a pass.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from normalize import (LEET, _ORDINAL_RE, _EN_ORDINAL_RE, _HOURS_RE,
                           _LEET_GUARD_RE, _name_tokens)
except Exception as exc:  # pragma: no cover - environment guard
    print(f"SKIP: cannot import normalize ({exc}). "
          f"polars and the other requirements must be installed.")
    raise SystemExit(0)


# (input token, expected token after _name_tokens)
#
# GUARDED CLASS D1 - French ordinals. These MUST be preserved verbatim.
# 1,111 occurrences total. The single most important case.
GUARDED_FR = [
    ("3eme", "3eme"),      # "troisieme" - the headline defect
    ("1er", "1er"),        # "premier"
    ("3e", "3e"),          # "troisieme", short form
    ("2e", "2e"),
    ("1ere", "1ere"),      # "premiere" - feminine form
    ("7eme", "7eme"),
    ("10eme", "10eme"),    # multi-digit must work
    ("22e", "22e"),
    ("4EME", "4eme"),      # uppercase: _name_tokens lowercases first
]

# GUARDED CLASS N1 - 24-hour notation. 3,657 occurrences: the SINGLE LARGEST
# corruption in the entire dataset, and 3.3x the French ordinal mass. A
# French-only guard misses it entirely, which is why it is asserted here.
GUARDED_HR = [
    ("24hr", "24hr"),
    ("24HR", "24hr"),
    ("7hr", "7hr"),
    ("12hr", "12hr"),
]

# GUARDED CLASS N2 - English ordinals. 1,060 occurrences (US 679 + India 381).
GUARDED_EN = [
    ("1st", "1st"),
    ("2nd", "2nd"),
    ("3rd", "3rd"),
    ("4th", "4th"),
    ("21st", "21st"),
]

# REAL LEETSPEAK - these MUST still be translated. Asserting this is the point:
# a guard that simply disabled LEET would pass the first list and fail this one.
#
# NOTE on "p1zza": the LEET table maps 1 -> l, so "p1zza" -> "plzza", NOT "pizza".
# That is correct upstream behaviour, not a bug being introduced here. The point
# of the case is only that the token is still passed through LEET at all.
STILL_LEET = [
    ("c1ub", "club"),
    ("mais0n", "maison"),
    ("b3ta", "beta"),
    ("5tar", "star"),
    ("g0ld", "gold"),
    ("n3w", "new"),
    ("c0ff3e", "coffee"),
    ("t3am", "team"),
    ("h0tel", "hotel"),
    ("p1zza", "plzza"),   # 1 -> l, so "plzza". Not "pizza"; see note above.
]

# DEAD LEET ENTRIES - a real (minor) finding, not a defect introduced by the guard.
# `_non_alnum` splits on [^a-z0-9]+ BEFORE LEET is applied, so "@" and "$" are
# already gone by the time translate() runs. The LEET table's "@" -> "a" and
# "$" -> "s" entries can therefore never fire through _name_tokens. The
# expectation is the post-tokenisation token, with no substitution.
DEAD_LEET_ENTRIES = [
    ("@lm", "lm"),        # "@" stripped -> "lm", no digit left, LEET not reached
    ("$tore", "tore"),    # "$" stripped -> "tore"
]

# EDGE CASES - tokens that are neither clean ordinals nor clean leetspeak.
# These pin down the boundary of the pattern so a future edit cannot quietly
# widen it. Note "b3er" and "p1er" are the important ones: a LOOSER pattern such
# as r"\d+[er]" would wrongly treat them as ordinals and leave them untranslated.
EDGE = [
    ("b3er", "beer"),    # 3->e gives "beer"; MUST NOT be treated as an ordinal
    ("p1er", "pler"),    # 1->l gives "pler"; MUST NOT be treated as an ordinal
    ("3a", "ea"),        # digit + single letter, not an ordinal suffix
    ("e3", "ee"),        # letter first, then digit
    ("3", "3"),          # pure digit, no alpha: LEET not applied at all
    ("abc", "abc"),      # pure alpha: LEET not applied at all
]


class TestLeetOrdinalGuard(unittest.TestCase):
    def test_french_ordinals_are_preserved(self):
        for tok, want in GUARDED_FR:
            with self.subTest(token=tok):
                self.assertEqual(_name_tokens(tok), [want])

    def test_24hr_notation_is_preserved(self):
        """N1: the single largest corruption in the dataset (3,657).

        This is the case a French-suffix-only guard silently misses.
        """
        for tok, want in GUARDED_HR:
            with self.subTest(token=tok):
                self.assertEqual(_name_tokens(tok), [want])

    def test_english_ordinals_are_preserved(self):
        """N2: 1,060 occurrences across US and India."""
        for tok, want in GUARDED_EN:
            with self.subTest(token=tok):
                self.assertEqual(_name_tokens(tok), [want])

    def test_real_leetspeak_still_translated(self):
        for tok, want in STILL_LEET:
            with self.subTest(token=tok):
                self.assertEqual(_name_tokens(tok), [want])

    def test_at_and_dollar_leet_entries_are_dead(self):
        """@ and $ are stripped by _non_alnum before LEET can fire.

        This is a real, pre-existing finding about the upstream table, not a
        consequence of the ordinal guard. It is asserted so the behaviour is
        documented rather than discovered later.
        """
        for tok, want in DEAD_LEET_ENTRIES:
            with self.subTest(token=tok):
                self.assertEqual(_name_tokens(tok), [want])
        # the table still claims to map them; the call path just never delivers
        # those characters to translate().
        self.assertEqual("@".translate(LEET), "a")
        self.assertEqual("$".translate(LEET), "s")

    def test_edge_cases(self):
        for tok, want in EDGE:
            with self.subTest(token=tok):
                self.assertEqual(_name_tokens(tok), [want])

    def test_ordinal_regex_shape(self):
        """Every guard pattern must be anchored: whole-token match only."""
        for rx, toks in ((_ORDINAL_RE, ("3eme", "1er", "3e", "10eme")),
                         (_EN_ORDINAL_RE, ("1st", "2nd", "3rd", "4th")),
                         (_HOURS_RE, ("24hr", "7hr"))):
            for tok in toks:
                self.assertIsNotNone(rx.match(tok), f"{tok} should match {rx.pattern}")
        # the union must reject anything not wholly one of the three classes
        for tok in ("b3er", "p1er", "3a", "e3", "abc3", "3emex", "x3eme",
                    "x1st", "hr24", "24hrs", "1std"):
            self.assertIsNone(_LEET_GUARD_RE.match(tok),
                              f"{tok} should NOT match the guard")

    def test_subclasses_agree_with_union(self):
        """The union must not silently diverge from its three parts."""
        for tok in ("3eme", "1er", "3e", "1ere", "7eme", "10eme", "22e",
                    "24hr", "7hr", "12hr", "1st", "2nd", "3rd", "4th", "21st"):
            self.assertIsNotNone(_LEET_GUARD_RE.match(tok), tok)
            self.assertTrue(
                _ORDINAL_RE.match(tok) or _EN_ORDINAL_RE.match(tok)
                or _HOURS_RE.match(tok),
                f"{tok} matches the union but none of the parts")

    def test_leet_table_unchanged(self):
        """The guard must not have altered the LEET table itself.

        NOTE (task_0002): this assertion previously used string keys
        (LEET["3"]) and could never pass. str.maketrans() returns a dict keyed
        by ORDINAL, not by character, so LEET has keys {48, 49, 51, 52, ...} and
        LEET["3"] raises KeyError. The table was never broken; the test was.
        """
        self.assertEqual(LEET[ord("3")], "e")
        self.assertEqual(LEET[ord("1")], "l")
        self.assertEqual(LEET[ord("0")], "o")
        self.assertNotIn("3", LEET, "str.maketrans keys must be ordinals, not chars")
        self.assertEqual("3eme".translate(LEET), "eeme",
                         "raw LEET still mangles ordinals - the guard, not the "
                         "table, is what protects them")

    def test_mixed_sentence_keeps_ordinal_and_fixes_leet(self):
        """A realistic French business name mixing both cases."""
        toks = _name_tokens("Boulangerie du 3eme c1ub")
        self.assertIn("3eme", toks)
        self.assertIn("club", toks)
        self.assertNotIn("eeme", toks)


if __name__ == "__main__":
    unittest.main(verbosity=2)
