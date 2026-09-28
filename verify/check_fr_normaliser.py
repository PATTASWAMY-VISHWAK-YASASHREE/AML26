"""Verify two France-specific hypotheses against the REAL normaliser.

H-A: accents are handled. strip_accents() uses NFKD + drop combining marks, and
     normalize_name/normalize_address both call it before tokenising, so
     38.9% accented French rows should fold cleanly. But NFKD does NOT decompose
     the ligature 'oe' (U+0153) or the 'æ' ligature, so verify those.

H-B: 'bis' handling. ADDR_CANON_FR maps bis->bis and b->bis, ter->ter, t->ter.
     But normalize_address strips non-alphanumerics and checks `if ck in smap`
     for STATE, while tokens go through canon.get(t, t). Is 'b' a real French
     street abbreviation or does it collide with something? Critically: ADDR_CANON_FR
     maps "b"->"bis" and ADDR_CANON_COMMON likely maps "b" differently, so a
     French address containing the token 'b' may be mangled.
"""
import sys
import unicodedata

sys.path.insert(0, "_upstream/src")
import normalize as N  # noqa: E402

print("=== H-A: accent handling ===")
tests = ["Société Générale", "Mérignac", "Lège-Cap-Ferret", "Côte-d'Azur",
         "Hôtel", "Nîmes", "Besançon", "Aix-en-Provence", "Œuvre", "Forêts",
         "Château-Thierry", "Rue de l'Église", "Créteil"]
for t in tests:
    folded = N.strip_accents(t)
    toks = N.normalize_name(t)[0]
    flag = "  <-- NOT fully folded" if any(ord(c) > 127 for c in folded) else ""
    print(f"  {t:24s} -> strip_accents: {folded:24s} name_toks: {toks}{flag}")

print("\n=== ligature check ===")
for ch, name in [("œ", "oe-ligature"), ("Œ", "OE-ligature"),
                 ("æ", "ae-ligature"), ("Æ", "AE-ligature"),
                 ("ß", "sharp-s"), ("ø", "o-stroke"), ("đ", "d-stroke")]:
    f = N.strip_accents(ch)
    print(f"  {name:14s} {ch!r} U+{ord(ch):04X} -> {f!r} "
          f"{'OK' if not any(ord(c) > 127 for c in f) else 'SURVIVES - collision risk'}")

print("\n=== H-B: 'bis' / 'b' / 'ter' token handling ===")
print("  ADDR_CANON_FR['b'] =", repr(N.ADDR_CANON_FR.get("b")))
print("  ADDR_CANON_FR['bis'] =", repr(N.ADDR_CANON_FR.get("bis")))
print("  ADDR_CANON_COMMON['b'] =", repr(N.ADDR_CANON_COMMON.get("b")))
print("  ADDR_CANON_COMMON['bis'] =", repr(N.ADDR_CANON_COMMON.get("bis")))
for addr in ["5 bis Rue Pierre Dignac", "20 bis RUE jules lefebvre",
             "3 ter Rue de la Paix", "B Rue Victor Hugo", "12 b avenue Foch"]:
    toks, nums, state, pin, comps = N.normalize_address(addr, "France")
    print(f"  {addr:32s} -> toks={toks} nums={nums} state={state!r} comps={comps}")

print("\n=== does 'b' collide with Belgium or a name initial? ===")
for addr in ["B 1000 Bruxelles", "B-1000 Bruxelles", "b rur saint germain"]:
    toks, nums, state, pin, comps = N.normalize_address(addr, "France")
    print(f"  {addr:32s} -> toks={toks} nums={nums} state={state!r}")
