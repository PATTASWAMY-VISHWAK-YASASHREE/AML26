"""Exercise the real `normalize` module directly and print what it does.

This is the end-to-end proof that the LEET guard works inside the actual
pipeline code, not just in a reimplementation of its logic. It imports
`patch_upstream/src/normalize.py` unmodified.

Run:  .\\.venv\\Scripts\\python.exe verify_leet_real_module.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "patch_upstream" / "src"))

from normalize import LEET, _LEET_GUARD_RE, _name_tokens  # noqa: E402

# (token, mode) where mode is:
#   "keep"  - a legitimate token the guard must exempt, so it must survive
#             UNCHANGED apart from lowercasing (inputs are lowercased at
#             normalize.py:273, so "4EME" legitimately becomes "4eme")
#   "leet"  - genuine leetspeak, so translate() MUST fire and change the token
#   "noalnum" - pure-digit or pure-alpha: the LEET branch is never reached at
#             all (the condition needs BOTH a letter and a digit), so the token
#             is returned unchanged by a different route. These are neither
#             "guarded" nor "translated" and must not be scored as either.
CASES = [
    # --- D1 French ordinals, 1,111 occurrences
    ("3eme", "keep"), ("1er", "keep"), ("3e", "keep"), ("2e", "keep"),
    ("1ere", "keep"), ("7eme", "keep"), ("10eme", "keep"), ("22e", "keep"),
    ("4EME", "keep"),          # lowercased to "4eme" by normalize.py:273
    # --- N1 24-hour notation, 3,657 occurrences: the largest single defect
    ("24hr", "keep"), ("24HR", "keep"), ("7hr", "keep"), ("12hr", "keep"),
    # --- N2 English ordinals, 1,060 occurrences
    ("1st", "keep"), ("2nd", "keep"), ("3rd", "keep"), ("4th", "keep"),
    ("21st", "keep"),
    # --- genuine leetspeak: MUST still be translated (regression cases)
    ("c1ub", "leet"), ("mais0n", "leet"), ("b3ta", "leet"), ("5tar", "leet"),
    ("g0ld", "leet"), ("n3w", "leet"), ("c0ff3e", "leet"), ("t3am", "leet"),
    ("h0tel", "leet"), ("p1zza", "leet"),
    # --- dead LEET entries: stripped by _non_alnum before translate() runs
    ("@lm", "leet"), ("$tore", "leet"),
    # --- pattern boundary: must NOT be mistaken for ordinals, so still leeted
    ("b3er", "leet"), ("p1er", "leet"), ("3a", "leet"), ("e3", "leet"),
    # --- pure digit / pure alpha: the LEET branch is never entered
    ("3", "noalnum"), ("abc", "noalnum"),
]

print(f"guard pattern: {_LEET_GUARD_RE.pattern}")
print(f"raw LEET still mangles 3eme -> {'3eme'.translate(LEET)}")
print(f"  (so the GUARD, not the table, is what protects it)")
print()
print(f"{'token':<9} {'expected':<9} {'_name_tokens()':<14} {'result':}")
print("-" * 52)

fails = 0
for tok, mode in CASES:
    out = _name_tokens(tok)
    got = out[0] if out else ""
    low = tok.lower()
    if mode == "keep":
        ok, want = (got == low), low
    elif mode == "leet":
        ok, want = (got != low), "changed"
    else:  # noalnum
        ok, want = (got == low), low
    if not ok:
        fails += 1
    print(f"{tok:<9} {str(want):<9} {str(out):<14} {'PASS' if ok else 'FAIL'}")

print()
print(f"cases: {len(CASES)}   failures: {fails}")

# Rejection set: the guard must NOT match these, or it would disable real leetspeak
REJECTS = ["b3er", "p1er", "3a", "e3", "abc3", "3emex", "x3eme", "x1st",
           "hr24", "24hrs", "1std", "b1st", "de1hi", "denta1"]
print()
print("must be REJECTED by the guard (each would be a real leet token):")
bad = 0
for t in REJECTS:
    hit = _LEET_GUARD_RE.match(t) is not None
    if hit:
        bad += 1
    print(f"  {t:<9} matched={str(hit):<6} {'FAIL' if hit else 'PASS'}")

print()
total_fail = fails + bad
print(f"TOTAL: {len(CASES) + len(REJECTS)} checks, {total_fail} failures")
sys.exit(1 if total_fail else 0)
