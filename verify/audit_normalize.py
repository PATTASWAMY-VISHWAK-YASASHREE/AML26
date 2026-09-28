"""Audit normaliser coverage per country, to ground the report's France findings."""
import ast
import pathlib

src = pathlib.Path("_upstream/src/normalize.py").read_text(encoding="utf-8")
tree = ast.parse(src)

WANT = ("US_STATES", "IN_STATES", "FR_REGIONS", "ADDR_CANON_COMMON", "ADDR_CANON_FR", "LEET")
for node in tree.body:
    if not isinstance(node, ast.Assign):
        continue
    name = getattr(node.targets[0], "id", "")
    if name not in WANT:
        continue
    try:
        d = ast.literal_eval(node.value)
    except Exception as exc:  # pragma: no cover
        print(f"{name:20s} ERROR {exc}")
        continue
    if hasattr(d, "values"):
        print(f"{name:20s} entries={len(d):4d} distinct_values={len(set(d.values())):4d}")
    else:
        print(f"{name:20s} entries={len(d):4d}")

# French postal-code capture: the pin branch is India-only.
line = next((i + 1 for i, l in enumerate(src.splitlines()) if 'country == "India"' in l and "pin = n" in l), None)
print("pin capture guard at line:", line)

# Is FR_REGIONS included in the abbreviation self-map loop?
loop = next((i + 1 for i, l in enumerate(src.splitlines()) if "for _m in (" in l), None)
print("self-map loop at line:", loop)
print("self-map covers FR_REGIONS:", bool(loop and "FR_REGIONS" in src.splitlines()[loop - 1]))
