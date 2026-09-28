"""Render analysis_out/profile2/blocking_recall.json as a table."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from postprocess import sanity_check_metrics  # noqa: E402

P = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "analysis_out", "profile2", "blocking_recall.json")
d = json.load(open(P, encoding="utf-8"))

# Fail loudly on impossible metrics.  A recall above 1.0 is an accounting bug,
# not a result -- this check exists because one run reported 4.39.
flat = {}
for _k, _v in d["per_key"].items():
    for _kk, _vv in _v.items():
        flat[f"{_k}.{_kk}"] = _vv
flat.update(d["union"])
_bad = sanity_check_metrics(flat)
if _bad:
    print("IMPOSSIBLE METRICS -- these are accounting bugs, not findings:")
    for _b in _bad:
        print("  " + _b)
    raise SystemExit(1)
print("metric sanity check: all values within valid bounds")

print(f"S1 sample          : {d['s1_sample']:,}"
      + (f"  (requested {d['s1_sample_requested']:,})"
         if "s1_sample_requested" in d else ""))
print(f"true edges in sample: {d['true_edges']:,}")
print(f"singletons in sample: {d['singletons_in_sample']:,} "
      f"({100 * d['singleton_rate']:.2f}%)")
print()
hdr = f"{'blocking key':16s} {'edge_recall':>12s} {'mean_cands':>11s} " \
      f"{'ent_w_cand':>10s} {'sing_FM_risk':>12s}"
print(hdr)
print("-" * len(hdr))
for k, v in d["per_key"].items():
    print(f"{k:16s} {v['edge_recall']:12.4f} {v['mean_cands_per_entity']:11.1f} "
          f"{v['entities_with_cand_rate']:10.4f} "
          f"{v['singleton_false_merge_risk']:12,d}")
u = d["union"]
print("-" * len(hdr))
print(f"{'UNION':16s} {u['edge_recall']:12.4f} {u['mean_cands_per_entity']:11.1f}")
print()
print(f"union median cands : {u['median_cands']:,}")
print(f"union p90 cands    : {u['p90_cands']:,}")
print(f"union max observed : {u['max_cands_observed']:,}")
print(f"hit CAND_CAP={2000}: {u['entities_hitting_cap']:,}")
print()
print("per country:")
for c, v in d["per_country"].items():
    print(f"  {c:6s} entities={v['entities']:6,}  true_edges={v['true_edges']:7,}  "
          f"union_recall={v['union_edge_recall']}  "
          f"mean_cands={v['mean_union_cands']}")
