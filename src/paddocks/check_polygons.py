#!/usr/bin/env python3
"""
Overlay candidate paddock polygons on Sentinel-2 imagery, per trial site.

Used to judge a boundary source (Fields of The World, SAMGeo, anything else) by eye and by
number before committing to it for paddock-median extraction. Writes, per site:
  * a 2-panel PNG — S2 RGB with polygons, and the polygon that contains the trial point;
  * the containing polygon's area and how much of the 200 m window it covers.

    python3 check_polygons.py --polygons ftw_yorke2020.gpkg \
        --sites sites_yorke2020.csv --outdir .../figures/ftw --n 4

The number that matters is whether a polygon actually CONTAINS the trial point: the trial
GPS marks a paddock corner, so a boundary source can look plausible overall and still put
the trial on the wrong side of a line.
"""
import argparse
import os

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--polygons", required=True)
    ap.add_argument("--sites", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--window-m", type=float, default=200.0)
    ap.add_argument("--label", default="FTW")
    args = ap.parse_args()

    os.environ.setdefault("PROJ_NETWORK", "OFF")
    import datacube
    import geopandas as gpd
    from shapely.geometry import Point
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "sentinel_ndvi"))
    from extract_ndvi import FMASK_CLEAR, NODATA, REFL_SCALE, load_trial

    poly = gpd.read_file(args.polygons).to_crs("EPSG:3577")
    sites = pd.read_csv(args.sites).head(args.n)
    dc = datacube.Datacube(app="check_polygons")
    os.makedirs(args.outdir, exist_ok=True)

    rows = []
    for _, r in sites.iterrows():
        t0 = (pd.to_datetime(r["sow"]) + pd.Timedelta(days=110)).strftime("%Y-%m-%d")
        t1 = (pd.to_datetime(r["sow"]) + pd.Timedelta(days=200)).strftime("%Y-%m-%d")
        ds = load_trial(dc, float(r["lat"]), float(r["lon"]), t0, t1, args.window_m)
        if ds.sizes.get("time", 0) == 0:
            continue
        clear = (ds["oa_fmask"] == FMASK_CLEAR).sum(dim=("x", "y"))
        sc = ds.isel(time=int(clear.argmax()))
        m = sc["oa_fmask"] == FMASK_CLEAR

        def band(n):
            return (sc[n].where((sc[n] != NODATA) & m).astype("float32") / REFL_SCALE).values

        rgb = np.dstack([band("nbart_red"), band("nbart_green"), band("nbart_blue")])
        rgb = np.clip(rgb / np.nanpercentile(rgb, 98), 0, 1)
        gb = ds.geobox
        b = gb.extent.boundingbox
        extent = [b.left, b.right, b.bottom, b.top]

        pt = gpd.GeoSeries([Point(float(r["lon"]), float(r["lat"]))],
                           crs="EPSG:4326").to_crs("EPSG:3577").iloc[0]
        near = poly[poly.intersects(pt.buffer(args.window_m))]
        containing = poly[poly.contains(pt)]

        fig, ax = plt.subplots(1, 2, figsize=(11, 5.4))
        for a in ax:
            a.imshow(rgb, extent=extent, origin="upper")
            a.set_xticks([]); a.set_yticks([])
        if len(near):
            near.boundary.plot(ax=ax[0], color="#FF00FF", lw=1.6)
        ax[0].plot(pt.x, pt.y, "o", ms=9, mfc="yellow", mec="black", mew=1.4)
        ax[0].set_title(f"{args.label}: {len(near)} polygons near site")
        if len(containing):
            containing.boundary.plot(ax=ax[1], color="cyan", lw=2.4)
            area_ha = containing.geometry.area.iloc[0] / 1e4
            ttl = f"containing paddock: {area_ha:.1f} ha"
        else:
            area_ha = np.nan
            ttl = "NO polygon contains the trial point"
        ax[1].plot(pt.x, pt.y, "o", ms=9, mfc="yellow", mec="black", mew=1.4)
        ax[1].set_title(ttl)
        ax[0].set_xlim(extent[0], extent[1]); ax[0].set_ylim(extent[2], extent[3])
        ax[1].set_xlim(extent[0], extent[1]); ax[1].set_ylim(extent[2], extent[3])
        fig.suptitle(f"{r['TrialCode']} ({r['crop']}, {r['Year']})", weight="bold")
        fig.tight_layout()
        png = os.path.join(args.outdir, f"{args.label.lower()}_{r['TrialCode']}_SENSITIVE.png")
        fig.savefig(png, dpi=140); plt.close(fig)
        rows.append({"TrialCode": r["TrialCode"], "crop": r["crop"],
                     "n_near": len(near), "contains": len(containing) > 0,
                     "area_ha": area_ha})
        print(f"{r['TrialCode']}: {len(near)} near, contains={len(containing)>0}, "
              f"area={area_ha:.1f} ha")

    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(os.path.join(args.outdir, f"{args.label.lower()}_polygon_check_SENSITIVE.csv"),
                  index=False)
        print(f"\ncontaining polygon found for {df.contains.sum()}/{len(df)} sites")
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
