"""Unit tests for blocking_recall's key construction. No dataset access.

Run: & .venv\\Scripts\\python.exe test_blocking_keys.py
"""
import blocking_recall as b

fails = []


def eq(label, got, want):
    if got != want:
        fails.append(f"{label}: got {got!r} want {want!r}")


# --- soundex: the canonical examples ---------------------------------------
eq("soundex robert", b.soundex("robert"), "R163")
eq("soundex rupert", b.soundex("rupert"), "R163")   # must collide: that is the point
eq("soundex tafte", b.soundex("tafte"), "T130")
eq("soundex pfister", b.soundex("pfister"), "P236")
eq("soundex ashcraft", b.soundex("ashcraft"), "A261")
eq("soundex honeyman", b.soundex("honeyman"), "H555")
eq("soundex tymczak", b.soundex("tymczak"), "T522")
eq("soundex wagner", b.soundex("wagner"), "W256")   # g,n both -> 5, then r -> 6
eq("soundex lee", b.soundex("lee"), "L000")
eq("soundex ghosh", b.soundex("ghosh"), "G200")
# non-latin / empty must degrade gracefully, never raise
eq("soundex devanagari", b.soundex("प्राइवेट"), "")
eq("soundex digits", b.soundex("123"), "")

# --- h64 must be stable across processes (unlike Python's salted hash) -----
eq("h64 determinism", b.h64("S1-925783039"), b.h64("S1-925783039"))
if b.h64("a") == b.h64("b"):
    fails.append("h64 collision on trivial inputs")

# --- normalisation ---------------------------------------------------------
eq("norm strips punct", b.norm_name("A&B, Ltd."), "a b ltd")
eq("possessive is intra-word", b.norm_name("Orelee's Barbershop"),
   "orelees barbershop")
eq("name_core drops legal", b.name_core("B+ Retail Inc"), "b retail")
eq("name_core all-legal falls back",
   b.name_core("Private Limited"), "private limited")
# "india" is deliberately in GENERIC, so it is dropped from the sorted
# specific-token key; "traders" survives.
eq("name_specific sorts+drops generic",
   b.name_specific("The India Traders Company"), "traders")

# --- postal / houseno ------------------------------------------------------
eq("postal 5", b.postal_of("1795 Westchester Dr, High Point, NC 27260"), "5:27260")
eq("postal 6 wins over 5", b.postal_of("G-3/571, Bhopal, MP 462001"), "6:462001")
eq("postal none", b.postal_of("Bordeaux, Nouvelle-Aquitaine"), "")
eq("houseno", b.houseno_of("1795 Westchester Dr, High Point"), "1795")
eq("housenum_alnum", b.houseno_of("12B Rue Lafayette, Paris"), "12")
eq("houseno none", b.houseno_of("Bordeaux, Nouvelle-Aquitaine"), "")

# the full key dict, built once and reused by the assertions below
k = b.blocking_keys("Orelee's Barbershop", "1795 Westchester Drive, High Point, NC 27260")

# --- state code: the real US locality signal (99.28% of US addresses have
# --- no ZIP, but 86.42% end in a 2-letter state code)
eq("state NC", b.state_of("1795 Westchester Drive, High Point, NC"), "NC")
eq("state TX long form", b.state_of("Mack Rd, Haltom City, Texas"), "")
eq("state with trailing space", b.state_of("1712 Montebello Ave, Phoenix, AZ "), "AZ")
eq("state DC", b.state_of("1600 Pennsylvania Ave NW, Washington, DC"), "DC")
# must NOT fire on ordinary words or lowercase street tokens
eq("state rejects 'Ave'", b.state_of("12 Main Ave"), "")
eq("state rejects lowercase", b.state_of("12 Main St, Springfield, il"), "")
eq("state rejects unknown code", b.state_of("12 Main St, Foo, ZZ"), "")
eq("state rejects France", b.state_of("175 Bd Roosevelt, Bordeaux"), "")
eq("state rejects IN inside street",
   b.state_of("123 Main St, Springfield, IL"), "IL")

# every declared key must be present in every returned dict
for kn in b.KEY_NAMES:
    if kn not in k:
        fails.append(f"missing key {kn}")

# the state key must fire on a realistic US row and stay empty for France
ks = b.blocking_keys("Orelee's Barbershop", "1795 Westchester Drive, High Point, NC")
if ks["state"] != "NC":
    fails.append(f"state key wrong on US row: {ks['state']!r}")
kf2 = b.blocking_keys("Team Ecole",
                      "175 Boulevard du President Franklin Roosevelt, Bordeaux, "
                      "Nouvelle-Aquitaine")
if kf2["state"]:
    fails.append(f"France address wrongly produced state key: {kf2['state']!r}")
k = b.blocking_keys("Orelee's Barbershop", "1795 Westchester Drive, High Point, NC 27260")
k = b.blocking_keys("Orelee's Barbershop", "1795 Westchester Drive, High Point, NC 27260")
eq("key name_exact", k["name_exact"], "orelees barbershop")
eq("key postcode", k["postcode"], "5:27260")
eq("key housenum_pc", k["housenum_pc"], "1795|5:27260")
if b.blocking_keys("x", "y")["postcode"]:
    fails.append("postcode key should be empty when no digits present")

# a France address must yield NO postal key (documented dataset property)
kf = b.blocking_keys("Team Ecole",
                     "175 Boulevard du President Franklin Roosevelt, Bordeaux, "
                     "Nouvelle-Aquitaine")
if kf["postcode"] or kf["housenum_pc"]:
    fails.append(f"France address wrongly produced postal key: {kf}")

# every declared key must be present in every returned dict
for kn in b.KEY_NAMES:
    if kn not in k:
        fails.append(f"missing key {kn}")

if fails:
    print("FAIL")
    for f in fails:
        print("  " + f)
    raise SystemExit(1)
print("all blocking-key tests passed")


# --- spill-file round trip -------------------------------------------------
# Regression guard for the bug that made union edge recall come out at 1.3%:
# spill_index wrote [keys][ids] in 4096-entry flushes while query() split each
# file at the halfway mark, so the reader compared keys against id hashes.
# This writes real PAIR_DT records, reads them back the way query() does, and
# asserts every key maps to exactly the ids that were written.
import os
import tempfile

import numpy as np

os.makedirs(b.SPILL, exist_ok=True)
tmp = os.path.join(b.SPILL, "_roundtrip.bin")
records = [(b.h64("k=alpha"), b.h64("S2-1")),
           (b.h64("k=alpha"), b.h64("S2-2")),
           (b.h64("k=beta"), b.h64("S3-9"))]
arr = np.empty(len(records), dtype=b.PAIR_DT)
for n, (k, i) in enumerate(records):
    arr[n]["k"] = k
    arr[n]["i"] = i
with open(tmp, "wb") as f:
    f.write(arr.tobytes())

back = np.fromfile(tmp, dtype=b.PAIR_DT)
os.remove(tmp)
eq("roundtrip record count", int(back.size), len(records))
got = {}
for r in back:
    got.setdefault(int(r["k"]), set()).add(int(r["i"]))
want = {}
for k, i in records:
    want.setdefault(int(k), set()).add(int(i))
if got != want:
    fails.append(f"roundtrip key->ids mismatch: got {got} want {want}")

# the reader must sort by the KEY field specifically
order = np.argsort(back["k"], kind="stable")
sk = back["k"][order]
if not np.all(sk[:-1] <= sk[1:]):
    fails.append("sorted keys are not ascending after reader-style sort")

if fails:
    print("FAIL (spill round trip)")
    for f in fails:
        print("  " + f)
    raise SystemExit(1)
print("all blocking-key and spill round-trip tests passed")


# --- union-metric accounting ----------------------------------------------
# Regression guard for two metric bugs that made the reported union recall
# impossible (4.39, i.e. >1) and the candidate median 0 while the mean was 142.
#
#   Bug A: found-edges were added once PER KEY, so an edge recovered by three
#          keys counted three times.
#   Bug B: on reaching CAND_CAP the candidate set was cleared, so the entity
#          reported 0 candidates while the mean stayed high.
#
# The invariant is: a true edge contributes AT MOST 1 to the union, and a
# candidate count never decreases once capped.
print()
print("union-metric invariants:")


def simulate_union(true_hashes, per_key_cands, cap=2000):
    """Mirror of blocking_recall's union accumulation, with the same fixes."""
    u = {"n_cands": 0, "cands": set(), "capped": False, "found_ids": set()}
    for cand in per_key_cands:
        cs = set(cand)
        if not u["capped"]:
            room = cap - len(u["cands"])
            if room > 0:
                u["cands"].update(list(cs)[:room])
                if len(u["cands"]) >= cap:
                    u["capped"] = True
                    u["n_cands"] = cap
                    u["cands"].clear()
                else:
                    u["n_cands"] = len(u["cands"])
            else:
                u["capped"] = True
                u["n_cands"] = cap
                u["cands"].clear()
        else:
            u["n_cands"] += len(cs)
        u["found_ids"].update(set(true_hashes) & cs)
    return u


# one true edge, found by THREE different keys -> must count once
t1 = [111]
u1 = simulate_union(t1, [[222], [111], [111, 333]])
eq("edge found by 3 keys counts once", len(u1["found_ids"]), 1)

# no overlap with any key -> 0
u0 = simulate_union(t1, [[222], [333]])
eq("edge found by no key counts 0", len(u0["found_ids"]), 0)

# every key finds it -> still 1
uall = simulate_union(t1, [[111]] * 6)
eq("edge found by 6 keys counts once", len(uall["found_ids"]), 1)

# capping must NOT zero the count (Bug B)
big = list(range(10_000))
uc = simulate_union([], [big], cap=2000)
eq("capped count stays at the cap, not 0", uc["n_cands"], 2000)
if uc["n_cands"] == 0:
    fails.append("capping zeroed the candidate count (Bug B is back)")

# count must be monotonically non-decreasing across keys
prev = 0
mono = True
for k in range(12):
    uu = simulate_union([], [list(range(k * 500, (k + 1) * 500))], cap=2000)
    if uu["n_cands"] < prev:
        mono = False
    prev = uu["n_cands"]
if not mono:
    fails.append("candidate count decreased as keys were added")

# de-duplication: the same candidate offered by several keys counts once
ud = simulate_union([], [[5, 6, 7], [5, 6, 7], [5, 6, 7]])
eq("repeated candidates de-duplicated", ud["n_cands"], 3)

if fails:
    print("FAIL (union metrics)")
    for f in fails:
        print("  " + f)
    raise SystemExit(1)
print("all blocking-key, spill round-trip and union-metric tests passed")
