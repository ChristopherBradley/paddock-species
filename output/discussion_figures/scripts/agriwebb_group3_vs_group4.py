#!/usr/bin/env python3
"""AgriWebb independent holdout: retired group4 (with Grazing) vs current group3.

For the colleague validation-methodology discussion ONLY -- not a manuscript figure (the user
does not want AgriWebb results in the paper). Numbers copied verbatim from
output/HOLDOUT_AGRIWEBB.md (group4, 104 sites) and output/HOLDOUT_AGRIWEBB_group3.md (group3,
same 104 sites, seed 0 -- identical across seeds 0-4).
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUTDIR = "/home/147/cb8590/Projects/paddock-species/output/discussion_figures"
COLORS = {"group4 (retired, with Grazing)": "#a6a6a6", "group3 (current, shipped)": "#4472c4"}

classes = ["macro F1\n(3 classes)", "Canola\nF1", "Cereal\nF1", "Legume\nF1\n(n=5, noisy)"]
group4 = [0.468, 0.55, 0.67, 0.18]
group3 = [0.5917, 0.64, 0.85, 0.29]

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3), gridspec_kw={"width_ratios": [2.2, 1]})

ax = axes[0]
x = np.arange(len(classes))
w = 0.35
b1 = ax.bar(x - w / 2, group4, w, label="group4 (retired, with Grazing)", color=COLORS["group4 (retired, with Grazing)"])
b2 = ax.bar(x + w / 2, group3, w, label="group3 (current, shipped)", color=COLORS["group3 (current, shipped)"])
for bars in (b1, b2):
    for bar in bars:
        h = bar.get_height()
        ax.annotate(f"{h:.2f}", (bar.get_x() + bar.get_width() / 2, h), textcoords="offset points",
                    xytext=(0, 3), ha="center", fontsize=8)
ax.set_xticks(x)
ax.set_xticklabels(classes, fontsize=8.5)
ax.set_ylabel("F1")
ax.set_ylim(0, 1.0)
ax.set_title("(a) Independent AgriWebb holdout, 104 farmer-recorded\ncrop paddocks — never trained on, either model", fontsize=9.5)
ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.spines[["top", "right"]].set_visible(False)

ax = axes[1]
pct = [39.4, 0.0]
bars = ax.bar(["group4\n(retired)", "group3\n(current)"], pct,
              color=[COLORS["group4 (retired, with Grazing)"], COLORS["group3 (current, shipped)"]])
for bar, v in zip(bars, pct):
    ax.annotate(f"{v:.1f}%", (bar.get_x() + bar.get_width() / 2, v), textcoords="offset points",
                xytext=(0, 3), ha="center", fontsize=9, fontweight="bold")
ax.set_ylabel("% of known-cropped paddocks\ncalled \"Grazing\"")
ax.set_ylim(0, 50)
ax.set_title("(b) The failure group3 removes\nby construction (no Grazing class)", fontsize=9.5)
ax.spines[["top", "right"]].set_visible(False)

fig.suptitle("Dropping the retired Grazing class fixes the AgriWebb holdout, not just the internal metric\n"
             "(site-level: 29/104 flip from wrong to correct, 27 of those were specifically mis-called Grazing; only 2/104 newly wrong)",
             fontsize=9, y=1.03)
fig.tight_layout()
os.makedirs(OUTDIR, exist_ok=True)
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(OUTDIR, f"agriwebb_group3_vs_group4.{ext}"), dpi=300, bbox_inches="tight")
plt.close(fig)
print("-> agriwebb_group3_vs_group4.png/.pdf")
