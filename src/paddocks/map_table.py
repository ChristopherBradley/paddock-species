#!/usr/bin/env python3
"""
Flatten a map run into ONE attribute table, so every later question is a pandas filter.

WHY THIS EXISTS. Reading the 30 prediction GeoPackages of the Riverina run costs 5-20 min
depending on how loaded the login node is, and every question asked of that map — does a
confidence filter recover the ABS composition, do stable paddocks classify better, what does the
excess land look like — is a filter over the same 247k rows. Paying the read once and writing a
40 MB parquet turns a 15-minute question into a 2-second one, which is the difference between
checking an idea and not bothering.

WHAT IT JOINS. Three sources that are keyed differently and are useless apart:
  * `pred/*.gpkg`   — one row per polygon-year: class, probabilities, ndvi_amp, observation counts
  * `stability_all.csv` — `paddock_id`, `n_years`, `median_iou`: the SAME polygon tracked across
    the nine annual segmentations. This is the project's only quality signal that owes nothing to
    the spectra, so it must be available beside the spectral ones.
  * SA2 boundaries + the tile grid — which region each polygon is in, and what fraction of that
    region the map actually covers, because a share compared against ABS is only meaningful where
    coverage is high (`abs_compare.py --aois`).

Geometry is dropped: the centroid is kept as x/y in Albers, which is enough to re-join to the
GeoPackages or to plot, and keeps the table small enough to load in a second.

    python3 map_table.py --pred '.../map100/pred/*.gpkg' --stability .../map100/stability_all.csv \
        --sa2 .../abs/SA2_2021_AUST_GDA2020.shp --aois .../map100/aois.csv \
        --out .../map100/attrs.parquet
"""
import argparse
import glob
import re


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True, help="glob of prediction gpkgs")
    ap.add_argument("--stability", help="stability_all.csv from polygon_stability.py")
    ap.add_argument("--sa2", help="SA2 shapefile")
    ap.add_argument("--aois", help="aois.csv — to measure how much of each SA2 is covered")
    ap.add_argument("--out", required=True, help=".parquet (falls back to .csv.gz by extension)")
    args = ap.parse_args()

    import geopandas as gpd
    import pandas as pd

    files = sorted(glob.glob(args.pred))
    if not files:
        raise SystemExit(f"no predictions matched {args.pred}")
    P = pd.concat([gpd.read_file(f) for f in files], ignore_index=True)
    P = gpd.GeoDataFrame(P, crs=gpd.read_file(files[0]).crs)
    print(f"{len(files)} files, {len(P):,} polygon-years, crs {P.crs}")

    pat = re.compile(r"^(?P<region>.+?)_(?P<year>\d{4})_(?P<cell>r\d+c\d+)$")
    meta = P.stub.str.extract(pat)
    P["region"], P["cell"] = meta["region"], meta["cell"]
    cen = P.geometry.centroid
    P["x"], P["y"] = cen.x, cen.y

    if args.stability:
        S = pd.read_csv(args.stability)[["region", "cell", "year", "idx", "paddock_id",
                                         "n_years", "median_iou"]]
        before = len(P)
        P = P.merge(S, left_on=["region", "cell", "year", "poly_idx"],
                    right_on=["region", "cell", "year", "idx"], how="left").drop(columns=["idx"])
        # A left join, deliberately: a polygon with no stability row is one the matcher never
        # saw (a tile with fewer than two years). Dropping it here would silently shrink the map.
        assert len(P) == before, f"stability join changed row count {before} -> {len(P)}"
        print(f"stability joined; {P.paddock_id.isna().sum():,} polygon-years without a match")

    if args.sa2:
        SA = gpd.read_file(args.sa2)[["SA2_CODE21", "SA2_NAME21", "STE_NAME21", "geometry"]]
        SA = SA.to_crs(P.crs)
        SA["sa2_ha"] = SA.area / 1e4
        C = gpd.GeoDataFrame(P[["region"]].copy(), geometry=cen, crs=P.crs)
        # Join on the CENTROID: a polygon straddling an SA2 boundary would otherwise be counted
        # in both, inflating every share it touches.
        J = gpd.sjoin(C, SA, how="left", predicate="within")
        J = J[~J.index.duplicated()]          # a centroid on a shared edge can match twice
        for c in ["SA2_CODE21", "SA2_NAME21", "STE_NAME21", "sa2_ha"]:
            P[c] = J[c].values
        print(f"{P.SA2_CODE21.notna().sum():,} polygon-years fell inside an SA2")

        if args.aois:
            from shapely.geometry import box
            from shapely.ops import unary_union
            from pyproj import Transformer
            A = pd.read_csv(args.aois).drop_duplicates(["region", "grid_r", "grid_c"])
            fwd = Transformer.from_crs("EPSG:4326", "EPSG:3577", always_xy=True)
            x, y = fwd.transform(A.lon.values, A.lat.values)
            foot = gpd.GeoDataFrame(geometry=[box(xi - h, yi - h, xi + h, yi + h)
                                              for xi, yi, h in zip(x, y, A.half_m.values)],
                                    crs="EPSG:3577").to_crs(SA.crs)
            foot = gpd.GeoDataFrame(geometry=[unary_union(foot.geometry.values)], crs=SA.crs)
            ov = gpd.overlay(SA, foot, how="intersection")
            ov["covered_ha"] = ov.area / 1e4
            cov = ov.groupby("SA2_CODE21").agg(covered_ha=("covered_ha", "sum"),
                                               sa2_ha=("sa2_ha", "first"))
            cov["cover_frac"] = cov.covered_ha / cov.sa2_ha
            P = P.merge(cov[["covered_ha", "cover_frac"]], left_on="SA2_CODE21",
                        right_index=True, how="left")
            print(f"footprint touches {len(cov)} SA2s, "
                  f"{int((cov.cover_frac >= 0.5).sum())} of them >= 50 % covered")

    T = pd.DataFrame(P.drop(columns="geometry"))
    if args.out.endswith(".parquet"):
        T.to_parquet(args.out, index=False)
    else:
        T.to_csv(args.out, index=False)
    print(f"{len(T):,} rows x {len(T.columns)} cols -> {args.out}")
    print("columns:", ", ".join(T.columns))


if __name__ == "__main__":
    main()
