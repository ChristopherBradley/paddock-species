#!/usr/bin/env python3
"""Fig 2 -- Study area map.

National 2024 mapped-tile coverage (grey), the 100km x 100km Riverina, NSW block used
for the nine-year (2017-2025) regional test (outlined), and the SA2s used for ABS
composition validation (coloured by state).

The 132-SA2 "well-covered" (>=50% box coverage) subset is re-derived here from the same
markdown table `abs_compare.py` already wrote to output/ABS_COMPARISON_NATIONAL.md (the
"cover" column) -- not re-run against the raw pipeline, since that table already IS the
matched result. Country outline is the SA2 layer itself, dissolved -- this project has no
separate coastline file and the ABS statistical boundary is accurate enough for a study-area
schematic.
"""
import os
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

OUTDIR = "/home/147/cb8590/Projects/paddock-species/output/figures"
SA2_SHP = "/scratch/xe2/cb8590/paddock-species-data/derived/abs/SA2_2021_AUST_GDA2020.shp"
NATIONAL_AOIS = "/scratch/xe2/cb8590/paddock-species-data/derived/national2024/aois.csv"
MAP100_REGIONS = "/scratch/xe2/cb8590/paddock-species-data/derived/map100/regions.csv"
ABS_NATIONAL_MD = "/home/147/cb8590/Projects/paddock-species/output/ABS_COMPARISON_NATIONAL.md"
CRS_ALBERS = "EPSG:3577"

# --- parse the SA2/state/cover table straight out of the already-published report ---
with open(ABS_NATIONAL_MD) as f:
    text = f.read()
row_re = re.compile(
    r"^\| ([^|]+?) \| ([^|]+?) \| \d{4} \| (\d+) % \| [\d,]+ \| [\d,]+ \| [\d.]+ % \| [\d.]+ % \| [\d.]+ % \| [+-][\d.]+ \|$",
    re.MULTILINE,
)
rows = [(m.group(1).strip(), m.group(2).strip(), int(m.group(3))) for m in row_re.finditer(text)]
df = pd.DataFrame(rows, columns=["SA2_NAME21", "STE_NAME21", "cover"])
well_covered = df[df["cover"] >= 50][["SA2_NAME21", "STE_NAME21"]].drop_duplicates()
print(f"parsed {len(df)} SA2 rows from ABS_COMPARISON_NATIONAL.md, {len(well_covered)} well-covered (>=50%)")

# --- SA2 boundaries ---
sa2 = gpd.read_file(SA2_SHP).to_crs(CRS_ALBERS)
# Dissolve BEFORE simplifying: simplifying each SA2 independently first leaves internal
# edges that no longer align, which dissolve() then renders as spurious internal seams.
country = sa2.dissolve().geometry.iloc[0].simplify(1000)
val_sa2 = sa2.merge(well_covered, on=["SA2_NAME21", "STE_NAME21"], how="inner")
val_sa2["geometry"] = val_sa2["geometry"].simplify(500)
print(f"matched {len(val_sa2)} of {len(well_covered)} well-covered SA2 names to the shapefile")

# --- national mapped-tile coverage ---
aois = pd.read_csv(NATIONAL_AOIS, usecols=["lat", "lon"])
aois_gdf = gpd.GeoDataFrame(
    geometry=[Point(xy) for xy in zip(aois["lon"], aois["lat"])], crs="EPSG:4326"
).to_crs(CRS_ALBERS)

# --- Riverina 100km regional box ---
reg = pd.read_csv(MAP100_REGIONS).iloc[0]
center = gpd.GeoSeries([Point(reg["lon"], reg["lat"])], crs="EPSG:4326").to_crs(CRS_ALBERS).iloc[0]
half = reg["edge_km"] * 1000 / 2
riverina_box = center.buffer(half, cap_style=3)

# --- plot ---
fig, ax = plt.subplots(figsize=(7.2, 7.2))
ax.scatter(aois_gdf.geometry.x, aois_gdf.geometry.y, s=0.6, color="#bbbbbb",
           alpha=0.5, linewidths=0, label="2024 national mapped tiles", zorder=1)
gpd.GeoSeries([country], crs=CRS_ALBERS).boundary.plot(ax=ax, color="black", linewidth=0.6, zorder=2)

states = sorted(val_sa2["STE_NAME21"].unique())
palette = plt.cm.tab10(range(len(states)))
for s, c in zip(states, palette):
    sub = val_sa2[val_sa2["STE_NAME21"] == s]
    sub.plot(ax=ax, color=c, edgecolor="none", alpha=0.85, zorder=3, label=s)

gpd.GeoSeries([riverina_box], crs=CRS_ALBERS).boundary.plot(
    ax=ax, color="#c0392b", linewidth=1.6, zorder=4
)

ax.set_axis_off()
ax.set_title(f"Study area: national 2024 coverage, {len(val_sa2)} ABS validation SA2s,\n"
             "and the 100km x 100km Riverina (NSW) regional test block", fontsize=10)

# scale bar (200 km) -- top-left, clear of the bottom-left legend
xmin, xmax = ax.get_xlim()
ymin, ymax = ax.get_ylim()
sb_x0 = xmin + 0.04 * (xmax - xmin)
sb_y = ymax - 0.05 * (ymax - ymin)
ax.plot([sb_x0, sb_x0 + 200_000], [sb_y, sb_y], color="black", linewidth=2, zorder=5)
ax.text(sb_x0 + 100_000, sb_y + 0.02 * (ymax - ymin), "200 km", ha="center", fontsize=7)
# north arrow
na_x = xmax - 0.06 * (xmax - xmin)
na_y0 = ymax - 0.12 * (ymax - ymin)
ax.annotate("N", xy=(na_x, na_y0 + 0.06 * (ymax - ymin)), xytext=(na_x, na_y0),
            arrowprops=dict(arrowstyle="-|>", color="black", linewidth=1.2),
            ha="center", fontsize=8, fontweight="bold")

handles = [mpatches.Patch(color="#bbbbbb", label="2024 national mapped tiles")]
handles += [mpatches.Patch(color=c, label=s) for s, c in zip(states, palette)]
handles += [plt.Line2D([0], [0], color="#c0392b", linewidth=1.6, label="Riverina 100km regional block")]
ax.legend(handles=handles, loc="lower left", fontsize=6.5, frameon=False, ncol=2,
          bbox_to_anchor=(0.0, -0.02))

fig.tight_layout()
os.makedirs(OUTDIR, exist_ok=True)
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(OUTDIR, f"Fig02_study_area.{ext}"), dpi=300)
plt.close(fig)
print("-> Fig02_study_area.png/.pdf")
