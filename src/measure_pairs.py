"""Measure the REAL per-country pair count that build_features test will process.

build_features filters test_cand_<country>.parquet with `bscore >= 0.3 * btop`, so that
filtered count - not the candidate file size - is what drives the feature parquet size
and therefore the disk peak.  This streams the 6 narrow columns and only ever holds an
aggregate, so it is safe with ~500 MB free RAM.

usage: python measure_pairs.py
"""
import os

import polars as pl

B = r"C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)"
W = os.path.join(B, "work_test")
S1 = {"India": 809986, "US": 663106, "France": 259452}

tot_cand = tot_pairs = 0
rows = []
for c in ("India", "US", "France"):
    p = os.path.join(W, f"test_cand_{c}.parquet")
    if not os.path.isfile(p):
        print(f"{c}: MISSING {p}")
        continue
    lf = pl.scan_parquet(p)
    cand = lf.select(pl.len()).collect(engine="streaming").item()
    pairs = (lf.filter(pl.col("bscore") >= 0.3 * pl.col("btop"))
               .select(pl.len()).collect(engine="streaming").item())
    mb = os.path.getsize(p) / 2 ** 20
    rows.append((c, S1[c], cand, pairs, mb))
    tot_cand += cand
    tot_pairs += pairs
    print(f"{c:<8} S1={S1[c]:>9}  candidates={cand:>10,}  pairs_after_0.3btop={pairs:>10,}  "
          f"cand_file={mb:7.1f}MB  pairs/S1={pairs/S1[c]:6.2f}")

print(f"\nTOTAL candidates={tot_cand:,}  pairs={tot_pairs:,}")
print(f"README claimed 30.5 candidates per S1 and ~53M test pairs.")
print(f"actual: {tot_cand/1732544:.2f} candidates/S1, {tot_pairs/1e6:.1f}M pairs after the filter")

# feature parquet size = pairs * bytes_per_pair, calibrated on the 7.40 GB upstream figure
bpp = 7.40 * 2 ** 30 / 52_800_000
print(f"\nusing the upstream 7.40GB/52.8M = {bpp:.0f} B/pair:")
gt = 0
for c, s1, cand, pairs, mb in rows:
    est = pairs * bpp / 2 ** 20
    gt += est
    print(f"  {c:<8} feature parquet ~= {est:7.0f} MB")
print(f"  {'TOTAL':<8} feature parquet ~= {gt:7.0f} MB  (upstream says 7.40 GB = 7,573 MB)")
