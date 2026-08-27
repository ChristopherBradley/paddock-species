#!/usr/bin/env python3
"""
Render the wall-to-wall predictions as small multiples — one row per region, one column per
year — plus the per-year class areas behind them.

WHY THE YEARS SIT SIDE BY SIDE. A single-year map is unfalsifiable by eye: every polygon gets a
colour and nothing in the picture says whether the colour is right. Across years the same
paddocks are visible rotating, and rotation is a real agronomic constraint — canola is typically
grown one year in three or four on a given paddock, and a paddock that reads Canola five years
running is either irrigation, an error, or a model keying on something static like soil colour.
So the multi-year panel is the cheapest available check on a map with no ground truth in it,
and the rotation statistics under it are the numeric version of the same check.

CONFIDENCE IS DRAWN, NOT HIDDEN. Low-confidence polygons are rendered translucent, so a map that
looks decisive because the argmax is always something is visibly distinguishable from one that
is actually decisive.
"""
import argparse
import os

import numpy as np
import pandas as pd

COLORS = {"Canola": "#f2c200", "Cereal": "#c98b52", "Legume": "#4f9d4f",
          "Grazing": "#7fb3d5", "Other": "#bdbdbd", "Crop": "#c98b52"}


def md_table(df, index=True):
    """Markdown table without pandas' `to_markdown`, which needs `tabulate`.

    `tabulate` is not installed in the project environment, and adding a dependency to make a
    report render is a worse trade than eight lines here.
    """
    d = df.reset_index() if index else df
    cols = [str(c) for c in d.columns]
    out = ["| " + " | ".join(cols) + " |",
           "|" + "---|" * len(cols)]
    for _, r in d.iterrows():
        out.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", nargs="+", required=True, help="prediction GeoPackage(s)")
    ap.add_argument("--regions", required=True, help="regions.csv from map_regions.py")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--report", help="markdown summary (aggregate only — committable)")
    ap.add_argument("--half-m", type=float, default=1500.0,
                    help="tile half-width used to build the regions, for the "
                         "coverage denominator")
    ap.add_argument("--grid", type=int, default=4,
                    help="tiles per side, for the coverage denominator")
    ap.add_argument("--min-conf", type=float, default=0.5,
                    help="below this a polygon is drawn translucent, not dropped")
    args = ap.parse_args()

    import geopandas as gpd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    P = pd.concat([gpd.read_file(f) for f in args.pred], ignore_index=True)
    P = gpd.GeoDataFrame(P, geometry="geometry", crs="EPSG:3577")
    P["region"] = P.stub.str.rsplit("_", n=2).str[0]
    R = pd.read_csv(args.regions)
    regions = [r for r in R.region if r in set(P.region)]
    years = sorted(P.year.unique())
    classes = [c for c in ["Canola", "Cereal", "Legume", "Grazing", "Crop", "Other"]
               if c in set(P.pred)]
    os.makedirs(args.outdir, exist_ok=True)

    fig, axes = plt.subplots(len(regions), len(years),
                             figsize=(2.5 * len(years) + 1.2, 2.6 * len(regions) + 1.0),
                             squeeze=False)
    for i, reg in enumerate(regions):
        pr = P[P.region == reg]
        # One extent per ROW, from the region's full multi-year footprint, so the eye compares
        # the same ground across years instead of a differently-cropped view each column.
        bx = pr.total_bounds
        for j, yr in enumerate(years):
            ax = axes[i][j]
            g = pr[pr.year == yr]
            if len(g):
                hi, lo = g[g.confidence >= args.min_conf], g[g.confidence < args.min_conf]
                for sub, alpha in [(hi, 0.95), (lo, 0.35)]:
                    if len(sub):
                        sub.plot(ax=ax, color=[COLORS.get(c, "#999") for c in sub.pred],
                                 edgecolor="white", linewidth=0.12, alpha=alpha)
            ax.set_xlim(bx[0], bx[2])
            ax.set_ylim(bx[1], bx[3])
            ax.set_xticks([])
            ax.set_yticks([])
            if i == 0:
                ax.set_title(str(yr), fontsize=11)
            if j == 0:
                st = R.set_index("region").state.get(reg, "")
                ax.set_ylabel(f"{reg}\n{st}", fontsize=9)
            if len(g):
                ax.text(0.02, 0.02, f"{len(g)}", transform=ax.transAxes, fontsize=7,
                        color="#444")
    fig.legend(handles=[Patch(facecolor=COLORS[c], label=c) for c in classes],
               loc="lower center", ncol=len(classes), frameon=False, fontsize=9)
    fig.suptitle("Predicted crop group per paddock — 12 x 12 km demonstration regions\n"
                 "faded = model confidence below "
                 f"{args.min_conf:.0%}; polygon count per panel bottom-left", fontsize=11)
    fig.tight_layout(rect=[0, 0.05, 1, 0.94])
    png = os.path.join(args.outdir, "species_maps_by_year.png")
    fig.savefig(png, dpi=170)
    plt.close(fig)
    print(f"-> {png}")

    # Rotation: how many distinct classes each polygon takes across the years it was scored.
    # Polygons are matched across years by representative point, since segmentation is
    # re-run per year and the boundaries are not identical objects between runs.
    rot = []
    for reg in regions:
        pr = P[P.region == reg].copy()
        pt = pr.geometry.representative_point()
        # 200 m grid: coarse enough that a re-segmented paddock lands in the same cell,
        # fine enough that two neighbouring paddocks do not.
        pr["cell"] = (np.floor(pt.x / 200).astype(int).astype(str) + "_" +
                      np.floor(pt.y / 200).astype(int).astype(str))
        g = pr.groupby("cell").agg(n_years=("year", "nunique"),
                                   n_classes=("pred", "nunique"),
                                   canola_years=("pred", lambda s: int((s == "Canola").sum())))
        g = g[g.n_years >= max(3, len(years) - 1)]
        if len(g):
            rot.append({"region": reg, "n_tracked": len(g),
                        "median_classes": float(g.n_classes.median()),
                        "single_class_pct": float((g.n_classes == 1).mean()),
                        "canola_every_year_pct": float((g.canola_years >= g.n_years).mean()),
                        "canola_1_to_3_years_pct": float(
                            g.canola_years.between(1, max(1, len(years) // 2)).mean())})
    ROT = pd.DataFrame(rot)

    area = (P.groupby(["region", "year", "pred"]).area_ha.sum().unstack(fill_value=0)
            .round(0).astype(int))
    share = area.div(area.sum(axis=1), axis=0)

    TILE_HA = (2 * args.half_m / 100.0) ** 2          # 3 km tile = 900 ha
    args_grid = args.grid
    cov_region_ha = TILE_HA * args_grid ** 2
    COV = P.groupby(["region", "year"]).agg(
        polygons=("pred", "size"), classified_ha=("area_ha", "sum"),
        median_ha=("area_ha", "median"), over_300ha=("area_ha", lambda s: int((s > 300).sum())),
        median_obs=("n_obs", "median"), median_conf=("confidence", "median"))
    COV["coverage"] = (COV.classified_ha / cov_region_ha).round(3)
    COV["classified_ha"] = COV.classified_ha.round(0).astype(int)
    COV["median_ha"] = COV.median_ha.round(1)

    if args.report:
        with open(args.report, "w") as f:
            f.write("# Sample wall-to-wall species maps\n\n")
            f.write("Aggregate only — no site-level records, no trial codes.\n\n")
            f.write("## Regions\n\n" + md_table(R, index=False) + "\n\n")
            f.write(f"Each region is a {len(years)}-year run over a 4x4 grid of the 3 km "
                    "production tile, i.e. 12 x 12 km of ground. Tile size is held at 3 km "
                    "because `samgeo`'s fixed 512 px window makes it a segmentation "
                    "hyperparameter rather than a partition of the same work.\n\n")
            # Coverage is a limitation, not a footnote. A map that classifies half a region
            # and leaves the rest white is a different product from one that classifies all of
            # it, and the white is not empty ground — it is ground the segmentation did not
            # resolve into paddocks, or paddocks with too few clear observations to score.
            f.write("## Coverage, and what the white space is\n\n")
            f.write(f"Each region is {len(years) and ''}{cov_region_ha:,.0f} ha "
                    f"({args_grid}x{args_grid} tiles x {TILE_HA:,.0f} ha). `coverage` is the "
                    "share of that area inside a classified polygon. The remainder is ground "
                    "SAM did not resolve into a paddock above the 5 ha floor, or paddocks with "
                    "fewer than 10 clear observations — **not** ground with no crop on it.\n\n")
            f.write(md_table(COV) + "\n\n")
            f.write(f"**{int((P.area_ha > 300).sum())} of {len(P)} polygons "
                    f"({(P.area_ha > 300).mean():.1%}) exceed 300 ha** — the tile-scale blobs "
                    "SAM returns where there are no field boundaries to find. They are kept, "
                    "with `area_ha` and `compactness` on every row, because a national product "
                    "cannot be hand-reviewed and the fields the review used have to travel "
                    "with the data.\n\n")
            f.write("## Predicted area by class (hectares)\n\n")
            f.write(md_table(area) + "\n\n")
            f.write("## Predicted share by class\n\n")
            f.write(md_table(share.round(3)) + "\n\n")
            if len(ROT):
                f.write("## Rotation check\n\n")
                f.write("Polygons are matched across years on a 200 m grid of their "
                        "representative point, because segmentation is re-run per year and the "
                        "boundaries are not the same objects between runs. A paddock that "
                        "reads the same class every year is either perennial, irrigated, or "
                        "the model keying on something static.\n\n")
                f.write(md_table(ROT.round(3), index=False) + "\n\n")
            # The only external check available on ground with no field data in it. NLUM is a
            # 2020-21 land-use prior, so it cannot adjudicate any single year — but a map whose
            # multi-year mean canola share sits far from NLUM's expectation for the same block
            # is saying something that needs an explanation, and one that matches is at least
            # not contradicted by the one independent source there is.
            f.write("## Against NLUM's expectation for the same ground\n\n")
            f.write("NLUM is a 2020-21 prior and cannot adjudicate a single season. It is here "
                    "because it is the only independent statement about this ground, and a "
                    "multi-year mean that lands far from it needs an explanation.\n\n")
            f.write("| region | NLUM canola | mapped canola (mean over years) | "
                    "NLUM cereal | mapped cereal | NLUM legume | mapped legume |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            for _, r in R.iterrows():
                if r.region not in set(share.index.get_level_values("region")):
                    continue
                s = share.loc[r.region].mean()
                f.write(f"| {r.region} | {r.canola_prob:.3f} | "
                        f"{s.get('Canola', 0):.3f} | {r.cereal_prob:.3f} | "
                        f"{s.get('Cereal', 0):.3f} | {r.legume_prob:.3f} | "
                        f"{s.get('Legume', 0):.3f} |\n")
            f.write("\nNLUM's probabilities are shares of ALL land in the block including "
                    "non-agricultural; the mapped shares are of segmented paddocks only, so "
                    "the two columns are not expected to be equal. The comparison that means "
                    "something is their RATIO between crops.\n\n")
            f.write("## Confidence\n\n")
            c = P.groupby("pred").confidence.describe()[["count", "25%", "50%", "75%"]]
            f.write(md_table(c.round(3)) + "\n")
        print(f"-> {args.report}")

    print(share.round(3).to_string())
    if len(ROT):
        print(ROT.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
