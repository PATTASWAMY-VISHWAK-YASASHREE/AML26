"""P006 mechanism probe: run the REAL upstream normalize.py on synthetic strings.

READ-ONLY on _upstream/. No raw TSV is touched. Confirms whether the literal
"null" placeholder that the profile counts in addr_tokens is actually absorbed
by normalize_address, and whether it trips the features.py q_addr_empty gate.
"""
import sys

# Do NOT let the import of _upstream/src/normalize.py drop a __pycache__ into
# the pristine upstream clone - AGENT_PROMPT requires _upstream/ stay untouched.
sys.dont_write_bytecode = True
sys.path.insert(0, "_upstream/src")
import normalize as N  # noqa: E402

EMPTY = ""


def show(s, country="US"):
    toks, nums, st, pin, cc = N.normalize_address(s, country)
    atoks = " ".join(toks)
    print("  %-34r -> atoks=%-30r q_addr_empty=%d state=%r"
          % (s, atoks, int(atoks == EMPTY), st))


print("=== dictionary sizes (ground truth for D0xx family) ===")
for nm, m in (("US_STATES", N.US_STATES), ("IN_STATES", N.IN_STATES),
              ("FR_REGIONS", N.FR_REGIONS)):
    print("  %-10s entries=%3d distinct_values=%2d %s"
          % (nm, len(m), len(set(m.values())), sorted(set(m.values()))))

print()
print("=== A. whole-address null placeholders (US) ===")
for s in ["null", "null, null", "null, null, null", "", "   ",
          "N/A", "None", "<null>", "n/a", "none", "NULL", "Null"]:
    show(s)

print()
print("=== B. null inside a multi-component address ===")
for s in ["null, null, null", "123 Main St, null, TX 78701",
          "null, Austin, Texas 78701", "123 Main St, Austin, Texas 78701"]:
    show(s)

print()
print("=== C. France: same probe ===")
for s in ["null", "12 rue de la Paix, null, 75001", "12 rue de la Paix"]:
    show(s, "France")

print()
print("=== D. state-name form: does a ZIP in the state component break it? ===")
for s in ["123 Main St, Austin, Texas", "123 Main St, Austin, Texas 78701",
          "123 Main St, Austin, Texas, 78701", "123 Main St, Austin, TX",
          "123 Main St, Austin, TX 78701", "123 Main St, Austin, TX, 78701",
          "1600 Pennsylvania Ave, Washington, DC 20500",
          "123 Road, Raleigh, North Carolina 27601",
          "123 Road, Raleigh, North Carolina, 27601"]:
    show(s)

print()
print("=== E. canon maps: is a bare 'null'/'na' token mapped to ''? ===")
print("  ADDR_CANON_COMMON['null'] =", repr(N.ADDR_CANON_COMMON.get("null")))
print("  ADDR_CANON_COMMON['na']   =", repr(N.ADDR_CANON_COMMON.get("na")))
print("  ADDR_CANON_FR['null']     =", repr(N.ADDR_CANON_FR.get("null")))
print("  US_STATES has 'texas'->", N.US_STATES.get("texas"),
      " 'tx'->", N.US_STATES.get("tx"))
print("  US_STATES has 'north carolina'->", N.US_STATES.get("north carolina"),
      " 'nc'->", N.US_STATES.get("nc"))
