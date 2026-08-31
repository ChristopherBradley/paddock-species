#!/usr/bin/env python3
"""Fig 4 -- National 2024 crop-species map, full continent.

The classified GeoPackage has 1,346,582 polygons nationally (verified via `ogrinfo` COUNT(*)
on national_2024_crops.gpkg -- the OTHER national2024 file, national_2024_crops_classified.gpkg,
is a DERIVED 650,766-row subset containing only the classified rows with abstained polygons
already dropped, so it cannot show the abstain-rate story this figure needs).

At national extent every individual paddock polygon is far smaller than one printed pixel,
so plotting 1.3M polygon outlines would be both slow and visually meaningless. Centroids were
extracted once (via `ogr2ogr -dialect SQLite ... ST_Centroid`, 28s for all 1.3M rows -- see
fig_extract/national_2024_centroids.csv) and are rasterised here to a 3km grid, taking the
majority class per cell. This is a density/majority visualisation, not the polygon map itself.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import geopandas as gpd

OUTDIR = "/home/147/cb8590/Projects/paddock-species/output/figures"
CENTROIDS = "/scratch/xe2/cb8590/paddock-species-data/derived/national2024/fig_extract/national_2024_centroids.csv"
SA2_SHP = "/scratch/xe2/cb8590/paddock-species-data/derived/abs/SA2_2021_AUST_GDA2020.shp"
CRS_ALBERS = "EPSG:3577"
CELL_M = 3000

CLASS_COLORS = {"Cereal": "#8c6d31", "Canola": "#f2c134", "Legume": "#4472c4", "Abstained": "#bbbbbb"}
CATS = list(CLASS_COLORS)  # fixed order used as the category-code axis below

df = pd.read_csv(CENTROIDS)
df["cat"] = df["pred"].where(df["pred"].notna() & (df["pred"] != ""), "Abstained")
counts_overall = df["cat"].value_counts()
print("national totals:", counts_overall.to_dict(), "sum:", counts_overall.sum())

xmin, ymin, xmax, ymax = df.cx.min(), df.cy.min(), df.cx.max(), df.cy.max()
nx = int(np.ceil((xmax - xmin) / CELL_M))
ny = int(np.ceil((ymax - ymin) / CELL_M))
ix = np.clip(((df["cx"].to_numpy() - xmin) / CELL_M).astype(int), 0, nx - 1)
iy = np.clip(((df["cy"].to_numpy() - ymin) / CELL_M).astype(int), 0, ny - 1)
flat = iy * nx + ix

layers = np.zeros((len(CATS), ny * nx), dtype=np.int32)
cat_code = df["cat"].map({c: i for i, c in enumerate(CATS)}).to_numpy()
for i in range(len(CATS)):
    layers[i] = np.bincount(flat[cat_code == i], minlength=nx * ny)

total = layers.sum(axis=0)
dominant = layers.argmax(axis=0).astype(np.float32)
dominant[total == 0] = np.nan
grid = dominant.reshape(ny, nx)

fig, ax = plt.subplots(figsize=(7.2, 7.6))
cmap = matplotlib.colors.ListedColormap([CLASS_COLORS[c] for c in CATS])
ax.imshow(grid, origin="lower", extent=(xmin, xmax, ymin, ymax), cmap=cmap,
          vmin=-0.5, vmax=len(CATS) - 0.5, interpolation="none")

sa2 = gpd.read_file(SA2_SHP).to_crs(CRS_ALBERS)
country = sa2.dissolve().geometry.iloc[0].simplify(1000)
gpd.GeoSeries([country], crs=CRS_ALBERS).boundary.plot(ax=ax, color="black", linewidth=0.5, zorder=2)

ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)
ax.set_axis_off()
ax.set_title("National 2024 crop-species map (1,346,582 polygons, 3km majority-class grid)",
             fontsize=9.5)

sb_x0 = xmin + 0.04 * (xmax - xmin)
sb_y = ymax - 0.05 * (ymax - ymin)
ax.plot([sb_x0, sb_x0 + 200_000], [sb_y, sb_y], color="black", linewidth=2)
ax.text(sb_x0 + 100_000, sb_y + 0.02 * (ymax - ymin), "200 km", ha="center", fontsize=7)
na_x = xmax - 0.06 * (xmax - xmin)
na_y0 = ymax - 0.12 * (ymax - ymin)
ax.annotate("N", xy=(na_x, na_y0 + 0.06 * (ymax - ymin)), xytext=(na_x, na_y0),
            arrowprops=dict(arrowstyle="-|>", color="black", linewidth=1.2),
            ha="center", fontsize=8, fontweight="bold")

pct = (counts_overall / counts_overall.sum() * 100).round(1)
handles = [mpatches.Patch(color=CLASS_COLORS[c], label=f"{c} ({pct.get(c, 0):.1f}%)") for c in CATS]
ax.legend(handles=handles, loc="lower left", fontsize=7.5, frameon=False)

fig.tight_layout()
os.makedirs(OUTDIR, exist_ok=True)
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(OUTDIR, f"Fig04_national_map.{ext}"), dpi=300)
plt.close(fig)
print("-> Fig04_national_map.png/.pdf")
