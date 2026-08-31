#!/usr/bin/env python3
"""Fig 5 — ABS composition validation and the area-inflation decomposition.

Panel (a): mapped vs ABS crop-share composition across the 6 well-covered SA2-years
(canola highlighted), from output/ABS_COMPARISON_NATIONAL.md / ABS_COMPARISON_100km.md.
Panel (b): ABS / diluted / mapped / absorbed decomposition by class, from
output/ABS_COMPARISON_100km.md "The share deficit and the area over-call are one result".

Numbers are copied verbatim from those already-validated report files (aggregate only,
no site-level records) — do not edit without updating the source report first.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUTDIR = "/home/147/cb8590/Projects/paddock-species/output/figures"
COLORS = {"Canola": "#f2c200", "Cereal": "#c98b52", "Legume": "#4f9d4f"}

# Panel (a): mapped vs ABS share, medians over the 6 well-covered SA2-years
# (ABS_COMPARISON_100km.md, "Cereal and legume shares")
classes = ["Canola", "Cereal", "Legume"]
mapped = [23.4, 70.0, 7.2]
abs_ref = [36.2, 59.6, 3.5]

# Panel (b): ABS / diluted / mapped / absorbed decomposition (ABS_COMPARISON_100km.md)
diluted = [22.9, 37.6, 2.2]
absorbed = [0.6, 32.4, 5.0]

fig, axes = plt.subplots(1, 2, figsize=(8.4, 4.0))

ax = axes[0]
x = np.arange(len(classes))
w = 0.35
ax.bar(x - w / 2, mapped, w, label="Mapped", color=[COLORS[c] for c in classes], alpha=0.9)
ax.bar(x + w / 2, abs_ref, w, label="ABS", color=[COLORS[c] for c in classes], alpha=0.4,
       hatch="//", edgecolor="white")
ax.set_xticks(x)
ax.set_xticklabels(classes)
ax.set_ylabel("share of crop-classified area (%)")
ax.set_title("(a) Mapped vs. ABS composition\n(6 well-covered SA2-years, median)")
ax.legend(frameon=False, fontsize=8)
ax.spines[["top", "right"]].set_visible(False)

ax = axes[1]
bottom = np.zeros(len(classes))
ax.bar(classes, diluted, label="diluted (ABS / over-call)", color=[COLORS[c] for c in classes],
       alpha=0.9)
ax.bar(classes, absorbed, bottom=diluted, label="absorbed (excess land)",
       color=[COLORS[c] for c in classes], alpha=0.35, hatch="xx", edgecolor="white")
for i, c in enumerate(classes):
    ax.text(i, diluted[i] + absorbed[i] + 0.8, f"+{absorbed[i]:.1f}", ha="center", fontsize=8)
ax.set_ylabel("share of mapped area (%)")
ax.set_title("(b) Area over-call by class\n(median ratio 1.59x, 100 km test)")
ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.spines[["top", "right"]].set_visible(False)

fig.suptitle("ABS validation: composition matches for Canola; the area over-call is a\n"
             "Cereal/Legume presence problem, not a classification problem", fontsize=10)
fig.tight_layout(rect=[0, 0, 1, 0.88])

os.makedirs(OUTDIR, exist_ok=True)
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(OUTDIR, f"Fig05_abs_validation.{ext}"), dpi=300)
plt.close(fig)
print("-> Fig05_abs_validation.png/.pdf")
