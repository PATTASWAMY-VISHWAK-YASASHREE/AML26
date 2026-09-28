"""Is test_s1 structurally different from every other source file?

P004 (US test_s1) shows addr_empty=0 and has_comma=rows for all three countries,
while train_s2/s3 and test_s2/s3 show a 2.9-3.7% US address-null rate. This
script tests whether test_s1 is a null-free, comma-complete outlier across the
whole corpus. Read-only; profile JSONs only.
"""
import glob
import json
import os

rows = []
for f in sorted(glob.glob("analysis_out/profile/*.json")):
    key = os.path.splitext(os.path.basename(f))[0]
    p = json.load(open(f, encoding="utf-8"))
    for c, s in p["by_country"].items():
        rows.append((key, c, s))

print("=== addr_empty rate by file x country ===")
print(f"{'file':10s} {'country':7s} {'rows':>10s} {'addr_empty':>11s} {'rate':>9s} "
      f"{'has_comma%':>11s} {'alpha_only%':>12s}")
for key, c, s in rows:
    n = s["rows"]
    print(f"{key:10s} {c:7s} {n:>10,} {s['addr_empty']:>11,} "
          f"{s['addr_empty'] / n:>8.4%} {s['has_comma'] / n:>10.4%} "
          f"{s['alpha_only_addr'] / n:>11.4%}")

print("\n=== per-file summary: is this file null-free and comma-complete? ===")
for f in sorted(glob.glob("analysis_out/profile/*.json")):
    key = os.path.splitext(os.path.basename(f))[0]
    p = json.load(open(f, encoding="utf-8"))
    tot_ae = sum(s["addr_empty"] for s in p["by_country"].values())
    tot_ne = sum(s["rows"] - s["addr_empty"] for s in p["by_country"].values())
    tot_hc = sum(s["has_comma"] for s in p["by_country"].values())
    tot = sum(s["rows"] for s in p["by_country"].values())
    print(f"  {key:10s} rows={tot:>10,}  addr_empty={tot_ae:>8,} "
          f"({tot_ae / tot:7.4%})  comma_less={tot_ne - tot_hc:>5,}  "
          f"null_free={tot_ae == 0}  comma_complete={tot_ne == tot_hc}")

print("\n=== US dig6/row by source: the source-1 asymmetry ===")
for key, c, s in rows:
    if c == "US":
        print(f"  {key:10s} dig5/row={s['dig5'] / s['rows']:.6f}  "
              f"dig6/row={s['dig6'] / s['rows']:.6f}  "
              f"dig6={s['dig6']:>7,}")
