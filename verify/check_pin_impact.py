"""F1 was misattributed. Check where the pin bug ACTUALLY bites.

normalize.py captures `pin` only when len(n)==6 and country=="India".
The report claimed France is the victim. Test every country/split properly.
"""
import json
import os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analysis_out", "profile")
print(f"{'file':16s} {'country':8s} {'rows':>10s} {'dig5/row':>9s} {'dig6/row':>9s}  verdict")
print("-" * 78)
for fn in sorted(os.listdir(P)):
    if not fn.endswith(".json"):
        continue
    d = json.load(open(os.path.join(P, fn), encoding="utf-8"))
    for c, s in d["by_country"].items():
        r = max(s["rows"], 1)
        d5, d6 = s["dig5"] / r, s["dig6"] / r
        if d6 > 0.005:
            v = "pin already captured"
        elif d5 > 0.05:
            v = "*** 5-digit present, pin NOT captured ***"
        elif d5 > 0.001:
            v = "5-digit marginal"
        else:
            v = "no postal signal"
        print(f"{fn[:-5]:16s} {c:8s} {s['rows']:>10,} {d5:>9.3f} {d6:>9.3f}  {v}")
