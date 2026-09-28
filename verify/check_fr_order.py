"""Does French address component ORDER break anything? (was task P020)

The data has both 'Bordeaux, Nouvelle-Aquitaine' (region last) and
'Nouvelle-Aquitaine, La Teste-de-Buch' (region first). Test whether that
changes normalize_address output or the blocking keys.
"""
import csv
import sys
from collections import Counter

sys.path.insert(0, "_upstream/src")
import keys as K  # noqa: E402
import normalize as N  # noqa: E402

CASES = [
    ("region last",  "175 Rue du President Wilson, Bordeaux, Nouvelle-Aquitaine"),
    ("region first", "Nouvelle-Aquitaine, Bordeaux, 175 Rue du President Wilson"),
    ("mid",         "Bordeaux, Nouvelle-Aquitaine, 175 Rue du President Wilson"),
    ("city first",  "Lille, 329 Avenue de Dunkerque, Hauts-de-France"),
    ("region first2", "Nouvelle-Aquitaine, 3 Rue de Campeyraut, Bordeaux"),
    ("bis",         "Nouvelle-Aquitaine, La Teste-de-Buch, 5 bis Rue Pierre Dignac"),
    ("no city",     "175 Rue Exemple, 33000 Bordeaux, Nouvelle-Aquitaine"),
    ("dpt code",    "175 Rue Exemple, 33300 Bordeaux"),
    ("upper",       "175 RUE WILSON, BORDEAUX, NOUVELLE-AQUITAINE"),
    ("reordered",   "Nouvelle-Aquitaine, 175 Rue du President Wilson, Bordeaux"),
]

print("=== does normalize_address depend on component ORDER? ===\n")
for label, addr in CASES:
    toks, nums, st, pin, comps = N.normalize_address(addr, "France")
    print(f"{label:14s} {addr[:52]:52s}")
    print(f"{'':14s}   toks={toks}")
    print(f"{'':14s}   nums={nums} state={st!r} pin={pin!r} city_comps={comps}")

print("\n=== the same street written in two orders: are the keys identical? ===")
import polars as pl


def keys_for(addr):
    full, core, alt, _fd, _db = N.normalize_name("Test Business")
    atoks, anums, _st, _p, _c = N.normalize_address(addr, "France")
    row = {"rid": [1], "country": ["France"], "ncore": [" ".join(core)],
           "nalt": [" ".join(alt)], "atoks": [" ".join(atoks)], "pin": [""]}
    df = pl.DataFrame(row).with_columns(
        pl.col("rid").cast(pl.UInt32), pl.col("ncore").cast(pl.Utf8),
        pl.col("nalt").cast(pl.Utf8), pl.col("atoks").cast(pl.Utf8))
    return K.make_keys(df)


pairs = [
    ("a", "175 Rue Wilson, Bordeaux, Nouvelle-Aquitaine"),
    ("b", "Nouvelle-Aquitaine, Bordeaux, 175 Rue Wilson"),
    ("c", "Bordeaux, Nouvelle-Aquitaine, 175 Rue Wilson"),
    ("d", "175 Rue Wilson, Bordeaux"),
    ("e", "Bordeaux, 175 Rue Wilson"),
    ("f", "175 Rue Wilson, BORDEAUX, nouvelle aquitaine"),
]
sets = {k: set(keys_for(v)["key"].to_list()) for k, v in pairs}
for k, v in pairs:
    print(f"  {k}: {len(sets[k]):>3} keys  <- {v}")
print("\n  pairwise overlap of key sets (1.0 = order-independent):")
for i, (x, _) in enumerate(pairs):
    for y, _ in pairs[i + 1:]:
        a, b = sets[x], sets[y]
        j = len(a & b) / max(len(a | b), 1)
        flag = "" if j > 0.999 else "   <-- KEYS DIFFER"
        print(f"    {x} vs {y}: jaccard={j:.3f}{flag}")

print("\n=== city_comps classification: does order change which comp is 'city'? ===")
print("  normalize_address line 351: a component counts as city only if it has NO digits")
for addr in ["Bordeaux, Nouvelle-Aquitaine, 175 Rue Wilson",
             "175 Rue Wilson, Bordeaux, Nouvelle-Aquitaine"]:
    _t, _n, _s, _p, comps = N.normalize_address(addr, "France")
    print(f"    {addr[:48]:48s} -> city_comps={comps}")
