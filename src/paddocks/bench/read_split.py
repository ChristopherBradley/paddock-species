#!/usr/bin/env python
"""
read_split.py -- where does each stage's time go, on the same tiles?

Per tile: presegment-style load (green, nir, fmask; EPSG:6933; whole year) -> Fourier composite;
predict-style load (10 bands + fmask; EPSG:3577; DOY 90-350) -> zonal medians on the tile's
polygons. Writes one row per tile. The 'fused' saving of reading the bands once for both stages
is bounded above by the presegment read time (the 10-band read must happen anyway).
"""
import argparse
import os
import sys
import time

import geopandas as gpd
import numpy as np
import pandas as pd

os.environ.setdefault("PROJ_NETWORK", "OFF")
os.environ.setdefault("DATACUBE_CONFIG_PATH", "/g/data/v10/public/modules/dea/20231204/datacube.conf")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import predict_tile as pt        # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--aois", required=True)
ap.add_argument("--polydir", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
import datacube
import hdstats
from datacube.utils import geometry
from rasterio.features import rasterize
dc = datacube.Datacube(app="read_split")
rows = []
for r in pd.read_csv(a.aois).to_dict("records"):
    pt_ = geometry.point(r["lon"], r["lat"], geometry.CRS("EPSG:4326")).to_crs(geometry.CRS("EPSG:3577"))
    cx, cy = pt_.points[0]; h = float(r["half_m"]); year = int(r["year"])
    row = dict(stub=r["stub"], half_m=h)
    # presegment read + composite
    t = time.time()
    ds = dc.load(product=pt.PRODUCTS, x=(cx - h, cx + h), y=(cy - h, cy + h), crs="EPSG:3577", time=(r["start"], r["end"]),
                 measurements=["nbart_green", "nbart_nir_1", "oa_fmask"], output_crs="EPSG:6933", resolution=(-10, 10),
                 group_by="solar_day", skip_broken_datasets=True)
    row["preseg_read_s"] = round(time.time() - t, 1); row["preseg_scenes"] = int(ds.sizes["time"]); row["preseg_px"] = int(ds.sizes["x"] * ds.sizes["y"])
    t = time.time()
    clear = ds["oa_fmask"] == 1
    g = ds["nbart_green"].where((ds["nbart_green"] != -999) & clear).astype("float32")
    nir = ds["nbart_nir_1"].where((ds["nbart_nir_1"] != -999) & clear).astype("float32")
    ndwi = ((g - nir) / (g + nir)).transpose("y", "x", "time").values
    mean = np.nanmean(ndwi, axis=2, keepdims=True); ndwi = np.where(np.isnan(ndwi), np.where(np.isnan(mean), 0.0, mean), ndwi)
    f = hdstats.fourier_mean(ndwi.astype(np.float32))
    row["fourier_s"] = round(time.time() - t, 1)
    del ds, g, nir, ndwi, f
    # predict read + zonal
    poly = gpd.read_file(f"{a.polydir}/{r['stub']}_filt.gpkg").to_crs(3577)
    b = poly.total_bounds
    t = time.time()
    ds = dc.load(product=pt.PRODUCTS, x=(b[0], b[2]), y=(b[1], b[3]), crs="EPSG:3577", time=(f"{year}-03-30", f"{year}-12-16"),
                 measurements=pt.ALL_BANDS + ["oa_fmask"], output_crs="EPSG:3577", resolution=(-10, 10), group_by="solar_day",
                 skip_broken_datasets=True)
    row["pred_read_s"] = round(time.time() - t, 1); row["pred_scenes"] = int(ds.sizes["time"]); row["pred_px"] = int(ds.sizes["x"] * ds.sizes["y"])
    row["n_poly"] = len(poly)
    t = time.time()
    shape = (ds.sizes["y"], ds.sizes["x"])
    labels = rasterize(((g_, i) for i, g_ in enumerate(poly.geometry.buffer(-10))), out_shape=shape, transform=ds.geobox.transform, fill=-1, dtype="int32")
    pt.zonal_medians(ds, labels, len(poly), [b.replace("nbart_", "") for b in pt.ALL_BANDS], "bands")
    row["zonal_s"] = round(time.time() - t, 1)
    row["total_separate_s"] = round(row["preseg_read_s"] + row["fourier_s"] + row["pred_read_s"] + row["zonal_s"], 1)
    row["total_fused_s"] = round(row["fourier_s"] + row["pred_read_s"] + row["zonal_s"], 1)
    rows.append(row); print(row, flush=True)
    pd.DataFrame(rows).to_csv(a.out, index=False)
    del ds
