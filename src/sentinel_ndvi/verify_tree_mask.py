#!/usr/bin/env python3
"""
Visual verification of the tree mask, per trial site.

Produces, for each example trial:
  * a 4-panel PNG — Sentinel-2 RGB, canopy height, the derived 10 m tree mask, and the
    NDVI before/after masking — so the mask can be judged by eye against the imagery;
  * a GeoTIFF of the mask on the Sentinel grid (openable in QGIS alongside the S2 scene);
  * a GeoPackage of the 200 m window footprint and the masked cells as polygons.

    python3 verify_tree_mask.py \
        --chunk   /scratch/.../derived/chunks/chunk_000.csv \
        --outdir  /scratch/.../derived/figures/tree_mask \
        --n 4

Intermediate outputs are the point here: the mask changes every downstream number, so it
should be inspectable rather than taken on trust.
"""
import argparse
import os

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402

from extract_ndvi import BANDS, FMASK_CLEAR, NODATA, PRODUCTS, REFL_SCALE, load_trial  # noqa: E402
from tree_mask import TreeMasker         # noqa: E402


def pick_scene(ds):
    """The clearest scene in the stack — the best backdrop for judging the mask."""
    clear = (ds["oa_fmask"] == FMASK_CLEAR).sum(dim=("x", "y"))
    return int(clear.argmax())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--chm-dir", default="/scratch/xe2/cb8590/Global_Canopy_Height_v2")
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--window-m", type=float, default=200.0)
    ap.add_argument("--tree-height-min", type=float, default=1.0)
    ap.add_argument("--dilate", type=int, default=1)
    args = ap.parse_args()

    os.environ.setdefault("PROJ_NETWORK", "OFF")
    import datacube
    import rasterio
    from rasterio.features import shapes
    dc = datacube.Datacube(app="verify_tree_mask")
    tm = TreeMasker(args.chm_dir, args.tree_height_min, args.dilate)
    os.makedirs(args.outdir, exist_ok=True)

    trials = pd.read_csv(args.chunk).head(args.n)
    rows = []
    for _, r in trials.iterrows():
        t0 = (pd.to_datetime(r["sow"]) + pd.Timedelta(days=110)).strftime("%Y-%m-%d")
        t1 = (pd.to_datetime(r["sow"]) + pd.Timedelta(days=200)).strftime("%Y-%m-%d")
        ds = load_trial(dc, float(r["lat"]), float(r["lon"]), t0, t1, args.window_m)
        if ds.sizes.get("time", 0) == 0:
            print(f"{r['TrialCode']}: no scenes")
            continue
        gb = ds.geobox
        mask, st = tm.mask_for_geobox(gb, float(r["lon"]), float(r["lat"]))
        i = pick_scene(ds)
        sc = ds.isel(time=i)
        clear = sc["oa_fmask"] == FMASK_CLEAR

        def band(n):
            return (sc[n].where((sc[n] != NODATA) & clear).astype("float32") / REFL_SCALE).values

        red, green, blue, nir = band("nbart_red"), band("nbart_green"), band("nbart_blue"), band("nbart_nir_1")
        ndvi = (nir - red) / (nir + red)
        rgb = np.dstack([red, green, blue])
        rgb = np.clip(rgb / np.nanpercentile(rgb, 98), 0, 1)

        # canopy height on the same grid, for the middle panel
        chm = _chm_on_grid(tm, gb, float(r["lon"]), float(r["lat"]))

        pct = 100.0 * mask.sum() / mask.size
        fig, ax = plt.subplots(1, 4, figsize=(19, 5.2))
        ax[0].imshow(rgb); ax[0].set_title(f"S2 RGB  {str(sc.time.values)[:10]}")
        im1 = ax[1].imshow(chm, cmap="viridis"); ax[1].set_title("canopy height (m)")
        fig.colorbar(im1, ax=ax[1], fraction=0.046)
        ax[2].imshow(rgb)
        ax[2].imshow(np.ma.masked_where(~mask, mask), cmap=ListedColormap(["#FF00FF"]), alpha=0.55)
        ax[2].set_title(f"tree mask (>{args.tree_height_min} m, +{args.dilate} px)\n"
                        f"{mask.sum()}/{mask.size} px = {pct:.1f}% dropped")
        nd_m = np.where(mask, np.nan, ndvi)
        im3 = ax[3].imshow(nd_m, cmap="YlGn", vmin=0, vmax=1)
        ax[3].set_title(f"NDVI after masking\nmean {np.nanmean(ndvi):.3f} -> {np.nanmean(nd_m):.3f}")
        fig.colorbar(im3, ax=ax[3], fraction=0.046)
        for a in ax:
            a.set_xticks([]); a.set_yticks([])
        fig.suptitle(f"{r['TrialCode']}  ({r['crop']}, {r['Year']})", weight="bold")
        fig.tight_layout()
        png = os.path.join(args.outdir, f"treemask_{r['TrialCode']}_SENSITIVE.png")
        fig.savefig(png, dpi=140); plt.close(fig)

        # GeoTIFF of the mask, on the Sentinel grid, for QGIS
        tif = os.path.join(args.outdir, f"treemask_{r['TrialCode']}_SENSITIVE.tif")
        with rasterio.open(tif, "w", driver="GTiff", height=mask.shape[0], width=mask.shape[1],
                           count=1, dtype="uint8", crs=str(gb.crs), transform=gb.transform,
                           nodata=255, compress="deflate") as dst:
            dst.write(mask.astype("uint8"), 1)

        # GeoPackage of the masked cells, for overlaying on anything
        try:
            import geopandas as gpd
            from shapely.geometry import shape
            geoms = [shape(g) for g, v in shapes(mask.astype("uint8"), mask=mask,
                                                 transform=gb.transform) if v == 1]
            if geoms:
                gpkg = os.path.join(args.outdir, f"treemask_{r['TrialCode']}_SENSITIVE.gpkg")
                gpd.GeoDataFrame({"tree": [1] * len(geoms)}, geometry=geoms,
                                 crs=str(gb.crs)).to_file(gpkg, driver="GPKG")
        except Exception as e:  # geopandas optional
            print(f"  (gpkg skipped: {e})")

        rows.append({"TrialCode": r["TrialCode"], "crop": r["crop"], "pct_masked": pct,
                     "ndvi_before": float(np.nanmean(ndvi)), "ndvi_after": float(np.nanmean(nd_m)),
                     **st})
        print(f"{r['TrialCode']}: {pct:5.1f}% masked | NDVI {np.nanmean(ndvi):.3f} -> "
              f"{np.nanmean(nd_m):.3f} | {png}")

    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(os.path.join(args.outdir, "tree_mask_summary_SENSITIVE.csv"), index=False)
        print("\n" + df.to_string(index=False))


def _chm_on_grid(tm, geobox, lon, lat):
    """Canopy height (max over contributing 1 m pixels) on the Sentinel grid, for display."""
    import rasterio
    from rasterio.warp import Resampling, reproject
    from tree_mask import _bounds_in
    h, w = geobox.shape
    out_acc = np.zeros((h, w), dtype=np.uint8)
    for f in tm.tiles_for_bounds(lon - 0.004, lat - 0.004, lon + 0.004, lat + 0.004):
        with rasterio.open(f) as src:
            try:
                win = src.window(*_bounds_in(src.crs, geobox, pad=40))
                win = win.round_offsets().round_lengths()
                if win.width <= 0 or win.height <= 0:
                    continue
                arr = src.read(1, window=win)
                if arr.size == 0:
                    continue
                out = np.zeros((h, w), dtype=np.uint8)
                reproject(source=arr, destination=out,
                          src_transform=src.window_transform(win), src_crs=src.crs,
                          dst_transform=geobox.transform,
                          dst_crs=geobox.crs.crs_str if hasattr(geobox.crs, "crs_str") else str(geobox.crs),
                          resampling=Resampling.max)
                out_acc = np.maximum(out_acc, out)
            except Exception:
                continue
    return out_acc


if __name__ == "__main__":
    main()
