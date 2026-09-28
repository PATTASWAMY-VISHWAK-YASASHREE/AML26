"""Quick check of the F1 hypothesis against the streamed profile."""
import json
import os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "analysis_out", "profile")

for fn in sorted(os.listdir(P)):
    if not fn.endswith(".json"):
        continue
    d = json.load(open(os.path.join(P, fn), encoding="utf-8"))
    print(f"\n=== {fn}  rows={d['rows']:,}  countries={list(d['country_rows'])}")
    for c, s in d["by_country"].items():
        r = max(s["rows"], 1)
        d5 = s["dig5"] / r
        d6 = s["dig6"] / r
        alpha = s["alpha_only_addr"] / r
        ne = s["name_empty"] / r
        ae = s["addr_empty"] / r
        print(f"  {c:8s} rows={s['rows']:>9,} dig5/row={d5:6.3f} dig6/row={d6:6.3f} "
              f"alpha_only={alpha:6.2%} name_empty={ne:5.2%} addr_empty={ae:5.2%}")
