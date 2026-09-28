"""Verify every number in the P005 deliverable against the profile JSON.

Low-memory: one profile file at a time, and only the scalar/stat keys are
touched (the 4000-entry token lists are never read). READ-ONLY.
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PROF = os.path.join(ROOT, "analysis_out", "profile")
FILES = ["train_s1", "train_s2", "train_s3", "test_s1", "test_s2", "test_s3"]
STATS = ["rows", "name_empty", "addr_empty", "name_chars", "addr_chars",
         "name_tokens", "num_digits", "has_digit_name", "has_comma",
         "prefix_bad", "dig5", "dig6", "alpha_only_addr"]

allstats = {}
for f in FILES:
    with open(os.path.join(PROF, f + ".json"), encoding="utf-8") as fh:
        p = json.load(fh)
    allstats[f] = {"rows": p["rows"], "cols": p["cols"],
                   "country_rows": p["country_rows"],
                   "by_country": {c: {k: s[k] for k in STATS}
                                  for c, s in p["by_country"].items()}}
    allstats[f]["len_hist"] = {c: s.get("len_hist", {})
                               for c, s in p["by_country"].items()}

print("=== file totals and country sums ===")
for f in FILES:
    d = allstats[f]
    tot = sum(d["country_rows"].values())
    print(f"  {f:8s} rows={d['rows']:>10,}  sum(country_rows)={tot:>10,}  "
          f"match={tot == d['rows']}  countries={sorted(d['country_rows'])}")
    print(f"           cols={d['cols']}")

print("\n=== COMMA IDENTITY:  has_comma  vs  rows - addr_empty ===")
print(f"  {'file':8s} {'country':7s} {'rows':>10s} {'nonempty':>10s} "
      f"{'has_comma':>10s} {'comma-less':>11s} {'pct':>9s}")
pool = {}
for f in FILES:
    for c, s in sorted(allstats[f]["by_country"].items()):
        ne = s["rows"] - s["addr_empty"]
        miss = ne - s["has_comma"]
        pct = 100.0 * miss / s["rows"]
        pool.setdefault(c, [0, 0])
        pool[c][0] += s["rows"]
        pool[c][1] += miss
        flag = "" if miss == 0 else "   <== BREAKS"
        print(f"  {f:8s} {c:7s} {s['rows']:>10,} {ne:>10,} {s['has_comma']:>10,} "
              f"{miss:>11,} {pct:>8.4f}%{flag}")
print("\n  pooled comma-less by country:")
for c, (r, m) in sorted(pool.items()):
    print(f"    {c:7s} {m:>7,} of {r:>12,}  = {100.0*m/r:.5f}%")

print("\n=== P005 slice: US in test_s2 ===")
us = allstats["test_s2"]["by_country"]["US"]
rows = us["rows"]
for k in STATS:
    if k == "rows":
        continue
    print(f"  {k:15s} {us[k]:>12,}   per-row {us[k]/rows:>10.5f}")
print(f"  addr_empty_pct      {100*us['addr_empty']/rows:.4f}")
print(f"  has_comma_pct       {100*us['has_comma']/rows:.4f}")
print(f"  has_digit_name_pct  {100*us['has_digit_name']/rows:.4f}")
print(f"  alpha_only_pct      {100*us['alpha_only_addr']/rows:.4f}")
print(f"  alpha_of_nonempty   {100*us['alpha_only_addr']/(rows-us['addr_empty']):.4f}"
      f"  (empty excluded by build_profile.py:117)")
print(f"  mean name chars     {us['name_chars']/rows:.4f}")
print(f"  mean addr all       {us['addr_chars']/rows:.4f}")
print(f"  mean addr nonempty  {us['addr_chars']/(rows-us['addr_empty']):.4f}")
print(f"  name_tokens/row     {us['name_tokens']/rows:.4f}")
print(f"  num_digits/row      {us['num_digits']/rows:.4f}")
print(f"  digit share addr    {100*us['num_digits']/us['addr_chars']:.4f}%")
print(f"  us share of file    {100*rows/allstats['test_s2']['rows']:.4f}%")

print("\n=== P005 len_hist (US, test_s2) ===")
lh = allstats["test_s2"]["len_hist"]["US"]
tot = 0
cum = 0
for k in sorted(lh, key=lambda x: int(x)):
    v = lh[k]
    tot += v
    cum += v
    print(f"  {k:>3}-{int(k)+9:<3} {v:>10,}  {100*v/rows:>8.4f}%   cum {100*cum/rows:>8.4f}%")
print(f"  SUM {tot:,}  == rows {rows:,}  -> {tot == rows}")
lo = sum(v for k, v in lh.items() if int(k) <= 10)
le39 = sum(v for k, v in lh.items() if int(k) <= 30)
ge50 = sum(v for k, v in lh.items() if int(k) >= 50)
print(f"  <=9 chars   {lo:>10,}  {100*lo/rows:.4f}%")
print(f"  <=39 chars  {le39:>10,}  {100*le39/rows:.4f}%")
print(f"  >=50 chars  {ge50:>10,}  {100*ge50/rows:.4f}%")

print("\n=== France in test_s2 / test_s3 (for the state bound) ===")
for f in ("test_s1", "test_s2", "test_s3"):
    fr = allstats[f]["by_country"].get("France")
    if not fr:
        print(f"  {f}: France ABSENT")
        continue
    ne = fr["rows"] - fr["addr_empty"]
    miss = ne - fr["has_comma"]
    print(f"  {f}: rows={fr['rows']:,} non-empty={ne:,} comma-less={miss:,} "
          f"-> state bound {100*(fr['rows']-miss)/fr['rows']:.4f}%")
    print(f"        dig5={fr['dig5']:,} ({fr['dig5']/fr['rows']:.5f}/row)  "
          f"dig6={fr['dig6']:,} ({fr['dig6']/fr['rows']:.5f}/row)  "
          f"alpha_only={fr['alpha_only_addr']:,} ({100*fr['alpha_only_addr']/fr['rows']:.4f}%)")

print("\n=== binormal consistency bound for the US test_s2 histogram ===")
bmin = sum(int(k) * v for k, v in lh.items())
bmax = sum((int(k) + 9) * v for k, v in lh.items())
print(f"  name_chars must lie in [{bmin:,} , {bmax:,}]")
print(f"  measured name_chars = {us['name_chars']:,}  inside = "
      f"{bmin <= us['name_chars'] <= bmax}")
print(f"  implied mean offset above bucket floor = "
      f"{(us['name_chars']-bmin)/rows:+.4f} chars")
