#!/usr/bin/env python3
"""Fig 7 — multi-year regional evidence (100 km Riverina, 2017-2025), with a reserved
national panel left explicitly blank pending the national multi-year run (E8 in
PAPER_PLAN.md). Regional numbers from output/ABS_COMPARISON_100km.md's year-by-year
table (shipped, amplitude-gate config) -- do NOT fill the national panel with invented
numbers when the national run completes; regenerate this script's second axis instead.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUTDIR = "/home/147/cb8590/Projects/paddock-species/output/figures"

years = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
classified_pct = [59.0, 52.5, 73.4, 77.8, 73.8, 69.4, 76.6, 76.8, 78.5]
ndvi_amp = [0.46, 0.42, 0.56, 0.60, 0.57, 0.52, 0.56, 0.60, 0.62]
weak_years = {2017, 2018}

fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))

ax = axes[0]
colors = ["#d9534f" if y in weak_years else "#4472c4" for y in years]
ax.bar([str(y) for y in years], classified_pct, color=colors)
ax2 = ax.twinx()
ax2.plot([str(y) for y in years], ndvi_amp, color="black", marker="o", markersize=3,
         linewidth=1, label="mean ndvi_amp")
ax.set_ylabel("classified share (%)")
ax2.set_ylabel("mean ndvi_amp")
ax.set_title("(a) Regional (100 km Riverina), 2017-2025\nred = flagged weak years (S2B start / drought)")
ax.tick_params(axis="x", labelsize=7, rotation=45)
ax.spines[["top"]].set_visible(False)

ax = axes[1]
ax.axis("off")
ax.text(0.5, 0.55, "[PENDING]", ha="center", va="center", fontsize=16, color="#888",
        fontweight="bold")
ax.text(0.5, 0.40, "National 2017-2025 multi-year run\nnot yet executed (E8, PAPER_PLAN.md)",
        ha="center", va="center", fontsize=8, color="#888")
ax.set_title("(b) National — reserved panel")
for spine in ax.spines.values():
    spine.set_visible(True)
    spine.set_color("#ccc")
    spine.set_linestyle("--")

fig.tight_layout()
os.makedirs(OUTDIR, exist_ok=True)
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(OUTDIR, f"Fig07_multiyear_regional.{ext}"), dpi=300)
plt.close(fig)
print("-> Fig07_multiyear_regional.png/.pdf (panel b intentionally blank -- PENDING E8)")
