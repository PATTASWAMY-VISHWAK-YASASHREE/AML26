"""Does France's extreme city concentration saturate the blocking caps in keys.py?

keys.py drops any key whose Source-1 document frequency exceeds S1_MAXCAP=300,
and query-side per-kind caps are CAPS={0:50,1:50,2:30,3:50,4:20} (300 for
name-only queries). France's top-10 cities cover 84.58% of its rows, so a city
token used as (or inside) a blocking key would blow straight through those caps
and be DROPPED ENTIRELY - silently destroying the key rather than just widening it.

This measures France Source-1 document frequency per candidate key type, using
the real make_keys logic against the real test data for France only.
"""
import sys
from collections import Counter

import polars as pl

sys.path.insert(0, "_upstream/src")
import keys as K  # noqa: E402
import normalize as N  # noqa: E402

TEST1 = ("amazon_ml_2026_research/student_resource/dataset/test/test_source1.tsv")
LIMIT = 400_000

print(f"caps: S1_MAXCAP={K.S1_MAXCAP}  CAPS={K.CAPS}  CAPS_NOADDR={K.CAPS_NOADDR}")
print("  (a key whose Source-1 df exceeds these is DROPPED, not widened)\n")

# normalise the France slice of source 1, streaming
rows = {"rid": [], "country": [], "ncore": [], "nalt": [],
        "atoks": [], "pin": [], "nnum": []}
n = 0
with open(TEST1, encoding="utf-8", errors="replace", newline="") as fh:
    import csv
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    next(rd)
    for rec in rd:
        if len(rec) < 4 or rec[3].strip() != "France":
            continue
        n += 1
        full, core, alt, _fd, _db = N.normalize_name(rec[1])
        atoks, anums, _st, pin, _cc = N.normalize_address(rec[2], "France")
        rows["rid"].append(n)
        rows["country"].append("France")
        rows["ncore"].append(" ".join(core))
        rows["nalt"].append(" ".join(alt))
        rows["atoks"].append(" ".join(atoks))
        rows["pin"].append(pin)
        rows["nnum"].append(" ".join(anums))
        if n >= LIMIT:
            break

print(f"France source-1 rows normalised: {n:,}")
df = pl.DataFrame(rows).with_columns(pl.col("rid").cast(pl.UInt32))
for c in ("ncore", "nalt", "atoks", "pin", "nnum"):
    df = df.with_columns(pl.col(c).cast(pl.Utf8))

# replicate build_s1_index's df computation
k1 = K.make_keys_chunked(df)
kdf = k1.group_by("key").agg(pl.len().alias("df"),
                             pl.col("kind").first()).sort("df", descending=True)
print(f"distinct blocking keys generated: {kdf.height:,}")

print("\n--- how many keys survive each cap ---")
for kind, cap in sorted(K.CAPS.items()):
    kk = kdf.filter(pl.col("kind") == kind)
    tot = kk.height
    kept = kk.filter(pl.col("df") <= cap).height
    print(f"  kind {kind}: {tot:>9,} keys, cap {cap:>3} -> kept {kept:>9,} "
          f"({kept/max(tot,1):6.2%}), DROPPED {tot - kept:,}")

# the S1_MAXCAP gate applied inside build_s1_index
print(f"\n--- the S1_MAXCAP={K.S1_MAXCAP} gate (applied to ALL kinds) ---")
kept = kdf.filter(pl.col("df") <= K.S1_MAXCAP).height
print(f"  keys kept {kept:,} of {kdf.height:,} ({kept/max(kdf.height,1):.2%})")

print("\n--- what the biggest surviving blocks actually are ---")
for r in kdf.filter(pl.col("df") <= K.S1_MAXCAP).head(12).iter_rows(named=True):
    print(f"  df={r['df']:>7,}  kind={r['kind']}")

print("\n--- city token document frequency (the collision risk) ---")
city = Counter()
for a in rows["atoks"]:
    pass
# city is what normalize_address put in city_comps; recompute cheaply for top tokens
tok = Counter()
for a in rows["atoks"]:
    tok.update(a.split())
print("  most frequent France source-1 address tokens and their df:")
for t, c in tok.most_common(15):
    over = "  <-- EXCEEDS every cap" if c > max(K.CAPS.values()) else (
        "  <-- exceeds kind-2/3/4 caps" if c > 30 else "")
    print(f"    {c:>7,}  {t}{over}")
