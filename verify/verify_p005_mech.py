"""Demonstrate the comma-less-address mechanism on the REAL normalizer.

_imports_ _upstream/src/normalize.py read-only; no file is written and no
dataset row is touched. Every input string below is synthetic.
"""
import os
import sys

# Never leave a __pycache__ inside the read-only _upstream clone: _upstream/src
# is tracked in git and must stay pristine. Import with bytecode writing off.
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "_upstream", "src"))
import normalize as N  # noqa: E402

print("=== region self-map loop (normalize.py:252) ===")
for name, m in (("US_STATES", N.US_STATES), ("IN_STATES", N.IN_STATES),
                ("FR_REGIONS", N.FR_REGIONS)):
    canon = set(m.values())
    selfmapped = sum(1 for v in canon if v in m)
    print(f"  {name:10s} entries={len(m):>3d}  distinct canonical values={len(canon):>3d}"
          f"  canonicals self-mapped={selfmapped:>3d}")
print("  -> FR_REGIONS is omitted from the loop at line 252 (only US and India).")

print("\n=== pin guard (normalize.py:337): len(n)==6 and country=='India' ===")
for addr, ctry in [("75001 Paris", "France"), ("10001 New York", "US"),
                   ("400001 Mumbai", "India"), ("110001 Delhi", "India")]:
    _, nums, state, pin, _ = N.normalize_address(addr, ctry)
    print(f"  {addr:16s} {ctry:7s} -> pin={pin!r:10s} nums={nums} state={state!r}")

print("\n=== single-component (comma-less) address: state AND city loss ===")
CASES = [
    "175 Boulevard du President Franklin Roosevelt",  # digit-bearing street
    "rue de la Paix",                                # digit-free, not a region
    "ile de france",                                 # IS a region key
    "Bordeaux",                                      # bare city
    "Bordeaux, Nouvelle-Aquitaine",                   # two-component control
]
for a in CASES:
    toks, nums, state, pin, comps = N.normalize_address(a, "France")
    print(f"  {a:46s}")
    print(f"      -> state={state!r:8s} city_comps={comps}  nums={nums}")

print("\n  Line 333 tests `ck in smap` on a WHOLE component. With no comma there")
print("  is one component == the entire address, so a state is emitted only if the")
print("  whole string equals a region key. Line 351 then also requires the")
print("  component to be digit-free for it to reach city_comps.")
