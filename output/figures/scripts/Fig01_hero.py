#!/usr/bin/env python3
"""Fig 1 (HERO) -- Pipeline overview + example output.

Top: pipeline schematic (Sentinel-2 -> SAM segmentation -> paddock mask -> spectral-index
classifier -> presence gate -> Cereal yield calibration).
Bottom: real classified output over a 12km x 12km window inside the Riverina 100km
regional block (map100/consensus_crops.gpkg, the 2024 layer), coloured by class, with
abstained/no-consensus paddocks shown in a distinct neutral colour, not left blank.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import geopandas as gpd
from shapely.geometry import box

OUTDIR = "/home/147/cb8590/Projects/paddock-species/output/figures"
CONSENSUS = "/scratch/xe2/cb8590/paddock-species-data/derived/map100/consensus_crops.gpkg"

CLASS_COLORS = {"Canola": "#f2c134", "Cereal": "#8c6d31", "Legume": "#4472c4", "abstained": "#bbbbbb"}

fig = plt.figure(figsize=(7.2, 6.4))
gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 2.0], hspace=0.15)

# --- top: pipeline schematic ---
ax0 = fig.add_subplot(gs[0])
stages = ["Sentinel-2\ntime series", "SAM\nsegmentation", "Paddock\nmask",
          "Spectral-index\nclassifier", "Presence\ngate", "Cereal yield\ncalibration"]
n = len(stages)
box_w, box_h, gap = 0.14, 0.5, 0.026
x0 = 0.02
for i, label in enumerate(stages):
    x = x0 + i * (box_w + gap)
    ax0.add_patch(FancyBboxPatch((x, 0.25), box_w, box_h, boxstyle="round,pad=0.01,rounding_size=0.02",
                                  linewidth=1.2, edgecolor="#333333", facecolor="#eef2f7"))
    ax0.text(x + box_w / 2, 0.25 + box_h / 2, label, ha="center", va="center", fontsize=7.2)
    if i < n - 1:
        xa = x + box_w
        ax0.add_patch(FancyArrowPatch((xa, 0.25 + box_h / 2), (xa + gap, 0.25 + box_h / 2),
                                       arrowstyle="-|>", mutation_scale=10, color="#333333",
                                       linewidth=1.2))
ax0.set_xlim(0, 1)
ax0.set_ylim(0, 1)
ax0.set_axis_off()
ax0.set_title("(a) Pipeline overview", fontsize=10, loc="left")

# --- bottom: real output map panel ---
ax1 = fig.add_subplot(gs[1])
gdf = gpd.read_file(CONSENSUS, columns=["crop_2024", "conf_2024"])
b = gdf.total_bounds
cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
half = 6000  # 12km x 12km window
window = box(cx - half, cy - half, cx + half, cy + half)
sub = gdf[gdf.geometry.centroid.within(window)].copy()
sub["class"] = sub["crop_2024"].fillna("abstained")

for cls, color in CLASS_COLORS.items():
    part = sub[sub["class"] == cls]
    if len(part):
        part.plot(ax=ax1, color=color, edgecolor="white", linewidth=0.15, label=cls)

ax1.set_xlim(cx - half, cx + half)
ax1.set_ylim(cy - half, cy + half)
ax1.set_axis_off()
ax1.set_title("(b) Example output: 12km x 12km window, Riverina NSW, 2024", fontsize=10, loc="left")

# scale bar (2km)
sb_x0 = cx - half + 0.06 * 2 * half
sb_y = cy - half + 0.06 * 2 * half
ax1.plot([sb_x0, sb_x0 + 2000], [sb_y, sb_y], color="black", linewidth=2)
ax1.text(sb_x0 + 1000, sb_y + 0.02 * 2 * half, "2 km", ha="center", fontsize=7)

handles = [mpatches.Patch(color=c, label=("Unclassified (abstained)" if k == "abstained" else k))
           for k, c in CLASS_COLORS.items()]
ax1.legend(handles=handles, loc="lower right", fontsize=7, frameon=True,
           facecolor="white", framealpha=0.85, edgecolor="none")

fig.suptitle("A national, field-verified, paddock-scale crop-species map of Australia",
             fontsize=11, y=0.985)
fig.tight_layout(rect=[0, 0, 1, 0.97])
os.makedirs(OUTDIR, exist_ok=True)
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(OUTDIR, f"Fig01_hero.{ext}"), dpi=300)
plt.close(fig)
print(f"-> Fig01_hero.png/.pdf ({len(sub)} polygons in window: "
      f"{sub['class'].value_counts().to_dict()})")
