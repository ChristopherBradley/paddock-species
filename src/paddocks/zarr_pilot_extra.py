#!/usr/bin/env python3
"""
ZARR PERSISTENCE PILOT -- benchmark scaffolding only, NOT production code.

Measures the MARGINAL cost of extending predict_tile.py's per-tile pipeline to ALSO persist
the raw per-scene, per-paddock time series (all ALL_BANDS reflectance bands + 9 spectral
indices) to a .zarr store, on top of the production baseline measured separately by running
predict_tile.py UNMODIFIED with --timings (see output/ZARR_BENCHMARK.md for the full writeup).

Does not import from or modify predict_tile.py's main()/CLI -- only reuses its zonal_medians()
function and band-name constants directly, so the aggregation formula is byte-identical to
production, not a re-derivation of it.

For each tile, in one process (so the two reads share warm OS/GDAL caches and the comparison
isolates the band-count effect rather than run-to-run network variance):
  1. dc.load with IDX_BANDS + fmask only (4+1 bands) -- reproduces exactly what the SHIPPED
     model (group3_map.joblib, kind="indices") reads today. Timed as `read_idx_s`.
  2. dc.load with ALL_BANDS + fmask (10+1 bands) -- what persisting raw reflectance requires.
     Timed as `read_all_s`. `read_extra_s = read_all_s - read_idx_s` is the real marginal read
     cost of the colleague's ask, isolated from everything else.
  3. Rasterise labels with the SAME 10m erosion + tree-mask logic predict_tile.py's main() uses
     (copied here, not imported, since that logic lives inside main() rather than a importable
     function) -- timed but NOT counted as "extra": a real implementation computes this once and
     reuses it for both the classifier's zonal_medians call and this one, so it is shared
     infrastructure the persistence feature does not add.
  4. Calls predict_tile.py's own zonal_medians() (imported, unmodified) twice on the ALL_BANDS
     cube: kind="indices" (NDVI/NDYI/CFI, per-pixel-then-median -- byte-identical to what the
     classifier already computes) and kind="bands" (raw reflectance, medianed per scene, one
     value per polygon/date/band). Both timed.
  5. Derives the 6 Sharma et al. (2026) Table S2 formulas (ndre2/vi2/vi3/vdvi/vci/evi2_sharma)
     from the ALREADY band-medianed (n_poly, n_time, n_band) array -- index-of-median, exactly
     matching how train_species.py's add_indices() already treats these 6 (it runs on binned
     band medians, never on a per-pixel array). Formulas copied verbatim from add_indices().
  6. Assembles a (paddock, time) xarray Dataset -- 10 raw bands + 9 indices, float32 -- and
     writes it to its own .zarr store (one store per tile, per the brief's "consider one .zarr
     per tile" question). Timed as `zarr_write_s`.

`extra_s = read_extra_s + zonal_bands_s + sharma6_s + zarr_write_s` is the number that answers
the brief's question: the marginal wall-clock cost of persistence on top of what predict_tile.py
already pays today. Rasterisation/erosion/tree-mask time is measured for context but excluded
from `extra_s` since it is not incremental.

Writes one CSV row per tile to --out-csv. Reads real composites/polygons from a national run's
existing samgeo/ dir; writes only to its own --zarr-dir. Does not touch any production output.
"""
import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from predict_tile import (ALL_BANDS, IDX_BANDS, PRODUCTS, FMASK_CLEAR, NODATA, REFL_SCALE,
                           zonal_medians)

BAND_NAMES = [b.replace("nbart_", "") for b in ALL_BANDS]   # e.g. "nbart_red" -> "red"


def sharma6(bandvals, names):
    """The 6 Sharma et al. (2026) Table S2 formulas NOT already covered by zonal_medians's
    "indices" kind (NDVI/NDYI/CFI), applied to an (n_poly, n_time, n_band) MEDIANED array --
    index-of-median, not median-of-index. Formulas copied verbatim from train_species.py's
    add_indices() (lines ~175-190), just re-targeted from DOY-binned wide columns to this
    array's band axis so they run once per (polygon, scene) instead of once per (trial, bin).
    """
    idx = {n: bandvals[..., names.index(n)] for n in names}
    red, green, blue = idx["red"], idx["green"], idx["blue"]
    nir, re1, re2 = idx["nir_1"], idx["red_edge_1"], idx["red_edge_2"]
    out = {}
    with np.errstate(invalid="ignore", divide="ignore"):
        out["ndre2"] = np.where(np.abs(nir + re2) < 1e-6, np.nan, (nir - re2) / (nir + re2))
        out["vi2"] = (re2 + red) - (re1 - blue)
        out["vi3"] = (re1 + green) - (blue + red)
        vdvi_denom = 2 * green + red + blue
        out["vdvi"] = np.where(np.abs(vdvi_denom) < 1e-6, np.nan,
                                (2 * green - red - blue) / vdvi_denom)
        r_ng = 0.38 * (nir - green) + green
        vci_denom = (r_ng - blue) ** 2
        out["vci"] = np.where(np.abs(vci_denom) < 1e-6, np.nan, (r_ng - red) ** 2 / vci_denom)
        evi2s_denom = nir + red + 1.0
        out["evi2_sharma"] = np.where(np.abs(evi2s_denom) < 1e-6, np.nan,
                                       2.4 * (nir - red) / evi2s_denom)
    return out


def rasterize_labels(ds, poly, erode_m, chm_dir, no_tree_mask):
    """Copy of predict_tile.py main()'s labels block (erosion + rasterize + tree mask), so the
    pilot's `labels` array is identical to what production would hand to zonal_medians(). Not
    imported because this logic lives inline in main(), not as its own function.
    """
    import geopandas as gpd
    from rasterio.features import rasterize

    tr = ds.geobox.transform
    shape = (ds.sizes["y"], ds.sizes["x"])
    eroded = poly.geometry.buffer(-erode_m)
    eroded = gpd.GeoSeries([g if (not g.is_empty and g.area > 0) else r
                             for g, r in zip(eroded, poly.geometry)], crs=poly.crs)
    labels = rasterize(((g, i) for i, g in enumerate(eroded)), out_shape=shape,
                        transform=tr, fill=-1, dtype="int32", all_touched=False)
    treed_ok = False
    if not no_tree_mask:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "..", "sentinel_ndvi"))
        from tree_mask import TreeMasker
        masker = TreeMasker(chm_dir)
        bb = ds.geobox.extent.boundingbox
        pad_deg = max(bb.right - bb.left, bb.top - bb.bottom) / 111_320.0 + 0.004
        cen = poly.to_crs("EPSG:4326").geometry.unary_union.centroid
        tree, tstats = masker.mask_for_geobox(ds.geobox, cen.x, cen.y, pad_deg=pad_deg)
        if tstats.get("chm_covered"):
            labels = np.where(tree, -1, labels)
            treed_ok = True
    return labels, treed_ok


def process_tile(dc, stub, lat, lon, half_m, year, polydir, erode_m, chm_dir, no_tree_mask,
                  zarr_dir, doy):
    import geopandas as gpd
    from pyproj import Transformer

    to_albers = Transformer.from_crs("EPSG:4326", "EPSG:3577", always_xy=True)
    p = os.path.join(polydir, f"{stub}_filt.gpkg")
    poly_all = gpd.read_file(p).to_crs("EPSG:3577")
    poly_all["area_ha"] = (poly_all.geometry.area / 1e4).round(2)
    poly = poly_all[poly_all.area_ha >= 5.0].reset_index(drop=True)   # same default min-area
    n_poly = len(poly)
    if n_poly == 0:
        return None

    b = poly.total_bounds
    date0 = (pd.Timestamp(year=year, month=1, day=1) +
             pd.Timedelta(days=doy[0] - 1)).strftime("%Y-%m-%d")
    date1 = (pd.Timestamp(year=year, month=1, day=1) +
             pd.Timedelta(days=doy[1] - 1)).strftime("%Y-%m-%d")

    # 1. IDX_BANDS-only read -- reproduces exactly what production reads today.
    t0 = time.time()
    ds_idx = dc.load(product=PRODUCTS, x=(b[0], b[2]), y=(b[1], b[3]), crs="EPSG:3577",
                      time=(date0, date1), measurements=IDX_BANDS + ["oa_fmask"],
                      output_crs="EPSG:3577", resolution=(-10, 10), group_by="solar_day")
    read_idx_s = time.time() - t0
    n_scenes = ds_idx.sizes.get("time", 0)
    if n_scenes == 0:
        return None
    del ds_idx   # only needed to measure read_idx_s; the ALL_BANDS read below is a superset

    # 2. ALL_BANDS read -- what raw-band persistence requires.
    t0 = time.time()
    ds = dc.load(product=PRODUCTS, x=(b[0], b[2]), y=(b[1], b[3]), crs="EPSG:3577",
                 time=(date0, date1), measurements=ALL_BANDS + ["oa_fmask"],
                 output_crs="EPSG:3577", resolution=(-10, 10), group_by="solar_day")
    read_all_s = time.time() - t0
    read_extra_s = read_all_s - read_idx_s

    # 3. Rasterise labels (shared infra, not "extra").
    t0 = time.time()
    labels, treed_ok = rasterize_labels(ds, poly, erode_m, chm_dir, no_tree_mask)
    rasterize_s = time.time() - t0

    # 4a. Indices zonal (byte-identical to what the classifier already computes).
    t0 = time.time()
    idx_vals, idx_nclear, idx_npx = zonal_medians(
        ds, labels, n_poly, ["ndvi_pad_median", "ndyi_pad_median", "cfi_pad_median"], "indices")
    zonal_indices_s = time.time() - t0

    # 4b. Raw band zonal -- the NEW work.
    t0 = time.time()
    band_vals, band_nclear, band_npx = zonal_medians(ds, labels, n_poly, BAND_NAMES, "bands")
    zonal_bands_s = time.time() - t0

    # 5. Sharma6 from the already-medianed band array -- cheap vectorised arithmetic.
    t0 = time.time()
    s6 = sharma6(band_vals, BAND_NAMES)
    sharma6_s = time.time() - t0

    # 6. Assemble (paddock, time) Dataset and write to its own .zarr store.
    import xarray as xr
    times = pd.to_datetime(ds["time"].values)
    data_vars = {}
    for j, name in enumerate(BAND_NAMES):
        data_vars[name] = (("paddock", "time"), band_vals[:, :, j].astype("float32"))
    data_vars["ndvi"] = (("paddock", "time"), idx_vals[:, :, 0].astype("float32"))
    data_vars["ndyi"] = (("paddock", "time"), idx_vals[:, :, 1].astype("float32"))
    data_vars["cfi"] = (("paddock", "time"), idx_vals[:, :, 2].astype("float32"))
    for name, arr in s6.items():
        data_vars[name] = (("paddock", "time"), arr.astype("float32"))
    ds_out = xr.Dataset(
        data_vars,
        coords={"paddock": np.arange(n_poly), "time": times,
                "stub": ("paddock", [stub] * n_poly)},
    )
    encoding = {v: {"chunks": (min(n_poly, 256), min(n_scenes, 128))} for v in data_vars}
    zpath = os.path.join(zarr_dir, f"{stub}.zarr")
    t0 = time.time()
    ds_out.to_zarr(zpath, mode="w", encoding=encoding, consolidated=True)
    zarr_write_s = time.time() - t0

    # zarr store size on disk (directory of chunk files -- du, not a single stat).
    zarr_bytes = sum(os.path.getsize(os.path.join(dp, f))
                      for dp, _, fnames in os.walk(zpath) for f in fnames)

    extra_s = read_extra_s + zonal_bands_s + sharma6_s + zarr_write_s

    return dict(stub=stub, n_poly=n_poly, n_scenes=n_scenes, treed_ok=treed_ok,
                read_idx_s=round(read_idx_s, 2), read_all_s=round(read_all_s, 2),
                read_extra_s=round(read_extra_s, 2), rasterize_s=round(rasterize_s, 2),
                zonal_indices_s=round(zonal_indices_s, 2),
                zonal_bands_s=round(zonal_bands_s, 2), sharma6_s=round(sharma6_s, 4),
                zarr_write_s=round(zarr_write_s, 2), extra_s=round(extra_s, 2),
                zarr_bytes=zarr_bytes, zarr_path=zpath)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aois", required=True)
    ap.add_argument("--polydir", required=True)
    ap.add_argument("--zarr-dir", required=True)
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--erode-m", type=float, default=10.0)
    ap.add_argument("--chm-dir", default="/scratch/xe2/cb8590/Global_Canopy_Height_v2")
    ap.add_argument("--no-tree-mask", action="store_true")
    ap.add_argument("--doy", nargs=2, type=int, default=[90, 350])
    args = ap.parse_args()

    os.environ.setdefault("PROJ_NETWORK", "OFF")
    os.makedirs(args.zarr_dir, exist_ok=True)
    import datacube
    dc = datacube.Datacube(app="zarr_pilot_extra")

    aois = pd.read_csv(args.aois)
    rows = []
    for _, a in aois.iterrows():
        print(f"{a['stub']}: starting", flush=True)
        r = process_tile(dc, a["stub"], a["lat"], a["lon"], a["half_m"], int(a["year"]),
                          args.polydir, args.erode_m, args.chm_dir, args.no_tree_mask,
                          args.zarr_dir, args.doy)
        if r is None:
            print(f"{a['stub']}: skipped (no polygons or no scenes)", flush=True)
            continue
        rows.append(r)
        print(f"{a['stub']}: n_poly={r['n_poly']} n_scenes={r['n_scenes']} "
              f"read_idx={r['read_idx_s']}s read_all={r['read_all_s']}s "
              f"read_extra={r['read_extra_s']}s zonal_bands={r['zonal_bands_s']}s "
              f"sharma6={r['sharma6_s']}s zarr_write={r['zarr_write_s']}s "
              f"EXTRA={r['extra_s']}s zarr_bytes={r['zarr_bytes']}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(args.out_csv, index=False)
    print(f"\n{len(df)} tiles -> {args.out_csv}")


if __name__ == "__main__":
    main()
