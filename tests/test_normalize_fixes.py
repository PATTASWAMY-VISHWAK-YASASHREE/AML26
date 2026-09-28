"""Tests for the normalize.py preprocessing fixes applied in run_src/src.

Two fixes are covered:
  1. FR_REGIONS added to the canonical self-map, so a French address already
     carrying a canonical region code resolves to a state.
  2. The LEET rule is now gated by _should_leet(), so real leetspeak is still
     folded but ordinary alphanumeric business names are not corrupted.

Every case below is taken from the measured damage in check_prep_risks.py or
from a real French address in the test set.

Run: & .venv\\Scripts\\python.exe test_normalize_fixes.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "run_src", "src"))
import normalize as N  # noqa: E402

fails = []


def eq(label, got, want):
    if got != want:
        fails.append(f"{label}: got {got!r} want {want!r}")


def toks(name):
    return N._name_tokens(name)


# --- fix 1: FR_REGIONS self-map ------------------------------------------
for code in ("hdf", "idf", "naq", "pdl"):
    eq(f"FR self-map contains {code!r}", code in N.FR_REGIONS, True)

# a French address carrying the canonical code now resolves
for probe, want in (("175 Boulevard Roosevelt, hdf", "hdf"),
                    ("12 Rue de la Paix, idf", "idf"),
                    ("3 Rue Victor Hugo, naq", "naq")):
    _, _, st, _, _ = N.normalize_address(probe, "France")
    eq(f"state for {probe!r}", st, want)

# long-form regions must keep working (regression guard)
for probe, want in (("175 Bd Roosevelt, Hauts-de-France", "hdf"),
                    ("12 Rue de la Paix, Ile de France", "idf"),
                    ("5 Cours Mirabeau, Bordeaux, Nouvelle-Aquitaine", "naq")):
    _, _, st, _, _ = N.normalize_address(probe, "France")
    eq(f"long-form state for {probe!r}", st, want)

# US/India self-maps must be unaffected
eq("US self-map still present", "ny" in N.US_STATES, True)
eq("India self-map still present", "mh" in N.IN_STATES, True)

# --- fix 2: LEET must not corrupt ordinary names -------------------------
# These are the exact false rewrites measured on real data.
eq("24hr preserved", "24hr" in toks("24hr Auto Repair"), True)
eq("1st preserved", "1st" in toks("1st National Bank"), True)
eq("3rd preserved", "3rd" in toks("3rd Street Cafe"), True)
eq("3eme preserved", "3eme" in toks("3eme Republique"), True)
eq("4x4 preserved", "4x4" in toks("4x4 Offroad"), True)
eq("15kg preserved", "15kg" in toks("15kg Bulk Store"), True)
eq("7th preserved", "7th" in toks("7th Avenue Deli"), True)
eq("4l preserved", "4l" in toks("4L Trading Co"), True)

# --- fix 2: but genuine leetspeak must STILL be folded -------------------
# A false rewrite is only acceptable if we did not disable real normalisation.
# Expected outputs follow LEET exactly (1->l, 0->o, 3->e, 4->a): note that
# s3rv1ce yields "servlce", not "service", because 1 maps to l -- that is the
# pre-existing table's behaviour and this fix deliberately does not change it.
eq("b4rb4r folded", "barbar" in toks("B4RB4R Cafe"), True)
eq("s3rv1ce folded", "servlce" in toks("S3rv1ce Co"), True)
eq("m0b1l folded", "mobll" in toks("M0b1l Repair"), True)

# plain digits and pure-alpha tokens are untouched
eq("pure digits untouched", toks("123 456"), ["123", "456"])
eq("pure alpha untouched", toks("Acme"), ["acme"])

# the gate itself
eq("gate: 24hr", N._should_leet("24hr"), False)
eq("gate: 1st", N._should_leet("1st"), False)
eq("gate: b4rb4r", N._should_leet("b4rb4r"), True)
eq("gate: 123", N._should_leet("123"), False)
eq("gate: acme", N._should_leet("acme"), False)
eq("gate: empty", N._should_leet(""), False)

# --- the pipeline's headline behaviour must be unchanged -----------------
# normalize_name still returns 5 values and still strips legal forms from core
out = N.normalize_name("B+ Retail Inc")
eq("normalize_name arity", len(out), 5)
eq("core drops legal form", out[1], ["b", "retail"])
eq("is_dba false", out[4], 0)
eq("dba detected", N.normalize_name("Foo Inc DBA Bar Ltd")[4], 1)
eq("domain detected", N.normalize_name("wilfordhancock.com")[3], 1)

# transpiling must not crash on non-Latin input
full, core, alt, dom, dba = N.normalize_name("\u0930\u093e\u092e \u092e\u093e\u0930\u094d\u0915\u0947\u091f\u093f\u0902\u0917")
eq("devanagari translit produces tokens", len(full) > 0, True)

if fails:
    print("FAIL")
    for f in fails:
        print("  " + f)
    raise SystemExit(1)
print("all normalize-fix tests passed")
