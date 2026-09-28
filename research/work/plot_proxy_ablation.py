"""Create a compact recall-versus-candidate-size figure from proxy results."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

root = Path(__file__).resolve().parents[1]
data = json.loads((root / "work/fodors_ablations.json").read_text(encoding="utf-8"))
labels = ["Exact\nname", "Exact\naddress", "Name\ntoken", "Rare name\ntoken", "Rare addr\ntoken", "Rare name\nOR addr", "Full\ngrams"]
keys = ["name_exact", "address_exact", "name_token", "rare_name_token", "rare_address_token", "rare_name_or_address_token", "full_grams"]
# Single source of truth for the palette: each marker keeps its blocking family.
GROUPS = ["exact", "exact", "token", "token", "token", "token", "full"]
GROUP_COLORS = {"exact": "#b23a48", "token": "#2b6cb0", "full": "#718096"}
GROUP_LABELS = {"exact": "Exact blocks", "token": "Token / gram ablations", "full": "Full n-grams (all rows)"}
rows = [data["methods"][k] for k in keys]
x = [r["candidate_rows"] for r in rows]
y = [100 * r["positive_recall"] for r in rows]
positive_pairs = data["positive_pairs"]
colors = [GROUP_COLORS[g] for g in GROUPS]
# A log axis cannot represent 0; fail loudly rather than silently dropping a point.
nonpos = [lbl for lbl, xi in zip(labels, x) if xi <= 0]
if nonpos:
    raise SystemExit("error: candidate_rows must be > 0 for a log x-axis; offending methods: " + ", ".join(nonpos))
fig, ax = plt.subplots(figsize=(9.2, 5.1), constrained_layout=True)
ax.scatter(x, y, s=78, c=colors, alpha=.92, edgecolor="white", linewidth=1.2, label="Blocking ablation")
offsets = [(5, 7), (5, 7), (5, -16), (5, -28), (5, -28), (5, 18), (-48, 7)]
for xi, yi, label, off in zip(x, y, labels, offsets):
    ax.annotate(label, (xi, yi), xytext=off, textcoords="offset points", fontsize=8,
                arrowprops={"arrowstyle": "-", "color": "#718096", "lw": .6} if abs(off[0]) > 20 or abs(off[1]) > 20 else None)
ax.set_xscale("log")
# Derive limits from the data so a re-run outside the previously hard-coded
# window can never silently clip markers off the plot.  The pad is multiplicative
# because a log axis rejects non-positive limits.
ax.set_xlim(min(x) / 1.6, max(x) * 1.6)
ypad = (max(y) - min(y)) * 0.15 or 1.0
# Only the lower bound is clamped: recall cannot go below 0%, but the upper bound
# needs headroom so markers sitting at 100% are not clipped by the axes frame.
ax.set_ylim(max(0.0, min(y) - ypad), max(y) + ypad)
ax.set_xlabel("Candidate rows (log scale)")
ax.set_ylabel("Known-positive recall (%)")
ax.set_title("Fodors–Zagats blocking ablation")
ax.grid(True, which="both", alpha=.22)
# The scatter is multi-coloured, so a single collection label would render one
# misleading swatch; key each colour group explicitly instead.
group_order = [g for g in dict.fromkeys(GROUPS)]
handles = [Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor=GROUP_COLORS[g], markeredgecolor="white", label=GROUP_LABELS[g]) for g in group_order]
ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=8)
ax.text(.01, -.18, f"Known positives = {positive_pairs} union of supplied label files; not a complete truth table. Marker size is uniform.", transform=ax.transAxes, fontsize=8, color="#555")
out = root / "figures/fodors_blocking_ablation.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, dpi=220, facecolor="white")
print(out)
