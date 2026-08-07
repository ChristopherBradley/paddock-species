#!/usr/bin/env python3
"""
Compare two or more paddock-boundary sources over the SAME wide AOI, side by side.

`check_polygons.py` crops to the 200 m extraction window, which is deliberately tight — but
too tight to judge whether a containing polygon is one paddock or several merged. At 200 m
a 57 ha polygon and a 339 ha polygon look identical: you see one boundary line either way.
This script plots a few km of context so the containing polygon can be seen whole.

    python3 compare_boundaries.py --lat <LAT> --lon <LON> \
        --start 2020-08-15 --end 2020-09-30 --context-m 3000 \
        --source SAMGeo=/scratch/.../yorke_arth_2020_filt.gpkg \
        --source FTW=/scratch/.../ftw_yorke2020_SENSITIVE.gpkg \
        --site-csv /scratch/.../sites_arth.csv \
        --out /scratch/.../figures/boundary_comparison_SENSITIVE.png

Run on a gadi login node (small dc.load, no internet needed).
"""
import argparse
import os

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402

FMASK_CLEAR = 1
NODATA = -999
REFL_SCALE = 10000.0


def clearest_rgb(dc, lat, lon, start, end, half_m):
    """RGB of the least-cloudy scene over a square AOI, plus its extent in EPSG:3577."""
    import datacube
    from datacube.utils import geometry

    # Work in Australian Albers so the AOI is a true square in metres.
    pt = geometry.point(lon, lat, geometry.CRS("EPSG:4326")).to_crs(geometry.CRS("EPSG:3577"))
    ds = dc.load(
        product=["ga_s2am_ard_3", "ga_s2bm_ard_3", "ga_s2cm_ard_3"],
        x=(pt.points[0][0] - half_m, pt.points[0][0] + half_m),
        y=(pt.points[0][1] - half_m, pt.points[0][1] + half_m),
        crs="EPSG:3577",
        time=(start, end),
        measurements=["nbart_red", "nbart_green", "nbart_blue", "oa_fmask"],
        output_crs="EPSG:3577",
        resolution=(-10, 10),
        group_by="solar_day",
    )
    if ds.sizes.get("time", 0) == 0:
        raise SystemExit("no Sentinel-2 scenes for this AOI/time range")
    clear = (ds["oa_fmask"] == FMASK_CLEAR).sum(dim=("x", "y"))
    sc = ds.isel(time=int(clear.argmax()))
    m = sc["oa_fmask"] == FMASK_CLEAR
    bands = [(sc[n].where((sc[n] != NODATA) & m).astype("float32") / REFL_SCALE).values
             for n in ("nbart_red", "nbart_green", "nbart_blue")]
    rgb = np.clip(np.dstack(bands) / np.nanpercentile(np.dstack(bands), 98), 0, 1)
    b = ds.geobox.extent.boundingbox
    date = str(sc.time.values)[:10]
    frac = float(clear.max()) / (ds.sizes["x"] * ds.sizes["y"])
    return rgb, [b.left, b.right, b.bottom, b.top], date, frac


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--context-m", type=float, default=3000.0, help="AOI width in metres")
    ap.add_argument("--source", action="append", required=True,
                    help="LABEL=path.gpkg, repeatable")
    ap.add_argument("--site-csv", help="optional; marks every site inside the AOI")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    os.environ.setdefault("PROJ_NETWORK", "OFF")
    import datacube
    import geopandas as gpd
    from shapely.geometry import Point, box

    dc = datacube.Datacube(app="compare_boundaries")
    half = args.context_m / 2.0
    rgb, extent, date, frac = clearest_rgb(dc, args.lat, args.lon, args.start, args.end, half)
    print(f"scene {date} ({frac:.0%} clear), AOI {args.context_m:.0f} m")

    aoi = box(extent[0], extent[2], extent[1], extent[3])
    pt = gpd.GeoSeries([Point(args.lon, args.lat)], crs="EPSG:4326").to_crs("EPSG:3577").iloc[0]

    sites = None
    if args.site_csv:
        s = pd.read_csv(args.site_csv)
        sites = gpd.GeoDataFrame(
            s, geometry=gpd.points_from_xy(s.lon, s.lat), crs="EPSG:4326").to_crs("EPSG:3577")
        sites = sites[sites.within(aoi)]

    srcs = [t.split("=", 1) for t in args.source]
    fig, axes = plt.subplots(1, len(srcs), figsize=(6.2 * len(srcs), 6.6), squeeze=False)
    for ax, (label, path) in zip(axes[0], srcs):
        pol = gpd.read_file(path).to_crs("EPSG:3577")
        vis = pol[pol.intersects(aoi)]
        containing = pol[pol.contains(pt)]
        ax.imshow(rgb, extent=extent, origin="upper")
        if len(vis):
            vis.boundary.plot(ax=ax, color="#FF00FF", lw=1.1)
        if len(containing):
            containing.boundary.plot(ax=ax, color="cyan", lw=3.0)
            area = containing.geometry.area.iloc[0] / 1e4
            sub = f"containing paddock {area:.0f} ha"
        else:
            sub = "NO containing polygon"
        if sites is not None and len(sites):
            ax.plot(sites.geometry.x, sites.geometry.y, "o", ms=7,
                    mfc="yellow", mec="black", mew=1.2, ls="none")
        # Polygon counts are for the plotted AOI only, so they compare like with like.
        ax.set_title(f"{label}: {len(vis)} polygons in AOI\n{sub}", fontsize=11)
        ax.set_xlim(extent[0], extent[1]); ax.set_ylim(extent[2], extent[3])
        ax.set_xticks([]); ax.set_yticks([])
        med = vis.geometry.area.median() / 1e4 if len(vis) else float("nan")
        print(f"{label:8s} {len(vis):4d} polygons in AOI, median {med:.1f} ha, "
              f"containing={'yes' if len(containing) else 'NO'}"
              + (f" ({containing.geometry.area.iloc[0]/1e4:.1f} ha)" if len(containing) else ""))

    fig.suptitle(f"Paddock boundary sources — S2 {date}, {args.context_m/1000:.1f} km AOI",
                 weight="bold", y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.94])   # leave room, else suptitle overlaps axis titles
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    fig.savefig(args.out, dpi=140)
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
