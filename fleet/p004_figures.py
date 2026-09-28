"""Compute the P004 figures from analysis_out/profile/test_s1.json.

Read-only. Every printed number is a profile field or arithmetic on one, so the
prose in the deliverable can be checked line by line against this output.
"""
import json

p = json.load(open("analysis_out/profile/test_s1.json", encoding="utf-8"))
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
    v = us[f]
    print(f"  {f:16s} {v:>9,}  {v / N:10.6%}")
for f in ("dig5", "dig6", "num_digits"):
    v = us[f]
    print(f"  {f + ' (occ)':16s} {v:>9,}  {v / N:10.6f} per row")

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

# bucket-implied bounds on the true name-length mean
lo = sum(b * v for b, v in hist.items())
hi = sum((b + 9) * v for b, v in hist.items())
print(f"\n  bucket-implied name_chars range [{lo:,}, {hi:,}]")
print(f"  measured name_chars {us['name_chars']:,} inside -> "
      f"{lo <= us['name_chars'] <= hi}")
print(f"  implied mean offset above bucket floor: "
      f"{(us['name_chars'] - lo) / N:.3f} chars")

print("\n--- statistical power: 95% binomial Wald half-width (pp) ---")
import math
for f in ("addr_empty", "has_digit_name", "dig5", "dig6", "alpha_only_addr"):
    pp = us[f] / N
    hw = 1.96 * math.sqrt(pp * (1 - pp) / N) * 100
    print(f"  {f:16s} p={pp:9.6%}  +/-{hw:.4f}pp  (+/-{hw / 100 * N:,.0f} rows)")

print("\n--- comma identity: has_comma == rows - addr_empty ---")
for c, s in p["by_country"].items():
    deficit = (s["rows"] - s["addr_empty"]) - s["has_comma"]
    print(f"  {c:7s} rows={s['rows']:>9,} nonempty={s['rows'] - s['addr_empty']:>9,} "
          f"has_comma={s['has_comma']:>9,} comma_less={deficit}")

print("\n--- cross-country digit density in test_s1 (for the pin-gate question) ---")
for c, s in p["by_country"].items():
    print(f"  {c:7s} dig5/row={s['dig5'] / s['rows']:.6f}  "
          f"dig6/row={s['dig6'] / s['rows']:.6f}  "
          f"alpha_only={s['alpha_only_addr']:>7,} ({s['alpha_only_addr'] / s['rows']:.4%})")
