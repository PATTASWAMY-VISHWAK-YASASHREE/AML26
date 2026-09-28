"""Compute the P006 figures from analysis_out/profile/test_s3.json.

Read-only. Mirrors p004_figures.py for the P006 work order ([US] test_s3), and
extends it with the cross-file tables P005 established as the comparison basis
(comma identity, dig5/dig6 by source). Every printed number is a profile field
or arithmetic on one.
"""
import json
import math

SPLITS = ("train_s1", "train_s2", "train_s3", "test_s1", "test_s2", "test_s3")
L = lambda n: json.load(open("analysis_out/profile/%s.json" % n, encoding="utf-8"))

p = L("test_s3")
us = p["by_country"]["US"]
N = us["rows"]
hist = {int(k): v for k, v in us["len_hist"].items()}

print(f"file rows            {p['rows']:,}")
print(f"US rows              {N:,}")
print(f"country_rows         {p['country_rows']}")
print(f"country sum check    {sum(p['country_rows'].values()):,} == {p['rows']:,} -> "
      f"{sum(p['country_rows'].values()) == p['rows']}")
print(f"US share of file     {N / p['rows']:.6%}")

print("\n--- null / integrity (denominator = US rows) ---")
for f in ("name_empty", "addr_empty", "prefix_bad", "has_comma",
          "has_digit_name", "alpha_only_addr"):
    print(f"  {f:16s} {us[f]:>9,}  {us[f] / N:10.6%}")
for f in ("dig5", "dig6", "num_digits"):
    print(f"  {f + ' (occ)':16s} {us[f]:>9,}  {us[f] / N:10.6f} per row")

print("\n--- lengths ---")
print(f"  name_chars total   {us['name_chars']:,}")
print(f"  mean name chars    {us['name_chars'] / N:.4f}")
print(f"  addr_chars total   {us['addr_chars']:,}")
print(f"  mean addr (all)    {us['addr_chars'] / N:.4f}")
print(f"  mean addr (nonemp) {us['addr_chars'] / (N - us['addr_empty']):.4f}")
print(f"  name_tokens total  {us['name_tokens']:,}")
print(f"  name tokens/name   {us['name_tokens'] / N:.4f}")
print(f"  addr digit share   {us['num_digits'] / us['addr_chars']:.4%}")

print("\n--- name length histogram ---")
tot = sum(hist.values())
cum = 0
for b in sorted(hist):
    cum += hist[b]
    print(f"  {b:>3}-{b + 9:<3} {hist[b]:>9,}  {hist[b] / N:8.4%}  cum {cum / N:8.4%}")
print(f"  SUM                {tot:,}  == US rows {N:,} -> {tot == N}")

lo = sum(b * v for b, v in hist.items())
hi = sum((b + 9) * v for b, v in hist.items())
print(f"\n  bucket-implied name_chars range [{lo:,}, {hi:,}]")
print(f"  measured name_chars {us['name_chars']:,} inside -> "
      f"{lo <= us['name_chars'] <= hi}")
print(f"  implied mean offset above bucket floor: "
      f"{(us['name_chars'] - lo) / N:.3f} chars")

print("\n--- statistical power: 95% binomial Wald half-width (pp) ---")
for f in ("addr_empty", "has_digit_name", "dig5", "dig6", "alpha_only_addr"):
    pp = us[f] / N
    hw = 1.96 * math.sqrt(pp * (1 - pp) / N) * 100
    print(f"  {f:16s} p={pp:9.6%}  +/-{hw:.4f}pp  (+/-{hw / 100 * N:,.0f} rows)")

print("\n--- comma identity across all six files: has_comma == rows - addr_empty ---")
pool = {}
for name in SPLITS:
    d = L(name)
    for c, s in d["by_country"].items():
        deficit = (s["rows"] - s["addr_empty"]) - s["has_comma"]
        pool.setdefault(c, [0, 0])
        pool[c][0] += deficit
        pool[c][1] += s["rows"]
        if deficit:
            print(f"  {name:9s} {c:7s} rows={s['rows']:>9,} non-empty={s['rows'] - s['addr_empty']:>9,} "
                  f"has_comma={s['has_comma']:>9,} comma_less={deficit:>5} "
                  f"({100 * deficit / s['rows']:.4f}%)")
print("  (only country-slices with a non-zero deficit are listed above)")
for c in ("US", "India", "France"):
    d, r = pool[c]
    print(f"  POOLED {c:7s} comma_less={d:>6,} of {r:>12,} rows = {100 * d / r:.6f}%")

print("\n--- US dig5 / dig6 by source (for the pin-gate question) ---")
for name in SPLITS:
    s = L(name)["by_country"]["US"]
    print(f"  {name:9s} dig5/row={s['dig5'] / s['rows']:.6f}  "
          f"dig6={s['dig6']:>7,}  dig6/row={s['dig6'] / s['rows']:.6f}")

print("\n--- cross-country digit density in test_s3 ---")
for c, s in p["by_country"].items():
    print(f"  {c:7s} dig5/row={s['dig5'] / s['rows']:.6f}  "
          f"dig6/row={s['dig6'] / s['rows']:.6f}  "
          f"alpha_only={s['alpha_only_addr']:>7,} ({s['alpha_only_addr'] / s['rows']:.4%})")