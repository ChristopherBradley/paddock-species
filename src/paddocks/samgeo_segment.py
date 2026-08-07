#!/usr/bin/env python3
"""
SAMGeo paddock segmentation for an AOI — the second arm of the boundary-source benchmark.

Follows PaddockTS (`01_pre-segment.py` + `02_SAMGeo_paddocks.py`): build a 3-band image
from the Fourier transform of an NDWI time series, segment it with SAM (vit_h), polygonise,
then filter on area and perimeter:area. Timed per stage so the cost can be compared against
simply downloading Fields of The World polygons.

    python3 samgeo_segment.py --lat -33.9 --lon 137.9 --buffer 0.05 \
        --start 2020-01-01 --end 2020-12-31 \
        --outdir /scratch/.../derived/samgeo --stub yorke2020

Run via PBS (needs no internet: SAM checkpoint is on /g/data, PROJ_NETWORK is off).

NOTE ON AREA UNITS: PaddockTS computes `area_ha = pol.area/1000`. In an equal-area CRS
`.area` is m², so hectares are `/10000` — that expression is 10x too large, which makes the
shipped --min-area-ha 10 / --max-area-ha 1500 filter behave like 1 ha / 150 ha. This script
uses the correct conversion, so its area thresholds are not interchangeable with theirs.
"""
import argparse
import os
import time

import numpy as np


def build_image(lat, lon, buffer_deg, start, end, out_tif, resolution=10):
    """3-band Fourier-of-NDWI GeoTIFF, per PaddockTS 01_pre-segment.py."""
    import datacube
    import hdstats
    import rasterio
    from rasterio.transform import from_bounds

    dc = datacube.Datacube(app="samgeo_presegment")
    query = dict(
        y=(lat - buffer_deg, lat + buffer_deg),
        x=(lon - buffer_deg, lon + buffer_deg),
        crs="EPSG:4326",
        time=(start, end),
        measurements=["nbart_green", "nbart_nir_1", "oa_fmask"],
        output_crs="EPSG:6933",           # equal-area, as PaddockTS uses
        resolution=(-resolution, resolution),
        group_by="solar_day",
    )
    ds = dc.load(product=["ga_s2am_ard_3", "ga_s2bm_ard_3", "ga_s2cm_ard_3"], **query)
    if ds.sizes.get("time", 0) == 0:
        raise SystemExit("no Sentinel-2 scenes for this AOI/time range")
    clear = ds["oa_fmask"] == 1
    g = ds["nbart_green"].where((ds["nbart_green"] != -999) & clear).astype("float32")
    nir = ds["nbart_nir_1"].where((ds["nbart_nir_1"] != -999) & clear).astype("float32")
    ndwi = ((g - nir) / (g + nir)).transpose("y", "x", "time").values
    # hdstats wants a dense (y, x, t) cube; gaps are filled with the per-pixel mean so the
    # transform sees a continuous series rather than NaNs.
    mean = np.nanmean(ndwi, axis=2, keepdims=True)
    ndwi = np.where(np.isnan(ndwi), np.where(np.isnan(mean), 0.0, mean), ndwi)
    print(f"  NDWI cube {ndwi.shape} from {ds.sizes['time']} scenes", flush=True)

    f = hdstats.fourier_mean(ndwi.astype(np.float32))
    lo, hi = np.nanpercentile(f, 1), np.nanpercentile(f, 99)
    img = np.clip((f - lo) / max(hi - lo, 1e-9), 0, 1) * 255
    img = np.nan_to_num(img).astype("uint8")            # (y, x, 3)

    gb = ds.geobox
    b = gb.extent.boundingbox
    transform = from_bounds(b.left, b.bottom, b.right, b.top, img.shape[1], img.shape[0])
    with rasterio.open(out_tif, "w", driver="GTiff", height=img.shape[0], width=img.shape[1],
                       count=3, dtype="uint8", crs=str(gb.crs), transform=transform,
                       compress="deflate") as dst:
        for i in range(3):
            dst.write(img[:, :, i], i + 1)
    return out_tif, ds.sizes["time"], img.shape


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--buffer", type=float, default=0.05, help="AOI half-width, degrees")
    ap.add_argument("--start", default="2020-01-01")
    ap.add_argument("--end", default="2020-12-31")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--stub", required=True)
    ap.add_argument("--checkpoint", default="/g/data/xe2/John/Data/PadSeg/sam_vit_h_4b8939.pth")
    ap.add_argument("--min-area-ha", type=float, default=1.0)
    ap.add_argument("--max-area-ha", type=float, default=1500.0)
    ap.add_argument("--max-perim-area-ratio", type=float, default=30.0)
    args = ap.parse_args()

    os.environ.setdefault("PROJ_NETWORK", "OFF")
    os.makedirs(args.outdir, exist_ok=True)
    tif = os.path.join(args.outdir, args.stub + ".tif")
    mask = os.path.join(args.outdir, args.stub + "_segment.tif")
    gpkg = os.path.join(args.outdir, args.stub + "_segment.gpkg")
    filt = os.path.join(args.outdir, args.stub + "_filt.gpkg")
    timings = {}

    t = time.time()
    _, n_scenes, shape = build_image(args.lat, args.lon, args.buffer, args.start, args.end, tif)
    timings["pre_segment_s"] = time.time() - t
    print(f"[1] pre-segment: {timings['pre_segment_s']:.0f}s -> {tif} {shape}", flush=True)

    import torch
    from samgeo import SamGeo
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[2] SAM on {dev}", flush=True)

    t = time.time()
    sam = SamGeo(model_type="vit_h", checkpoint=args.checkpoint, sam_kwargs=None)
    timings["model_load_s"] = time.time() - t

    t = time.time()
    sam.generate(tif, mask, batch=True, foreground=True, erosion_kernel=(3, 3),
                 mask_multiplier=255)
    timings["segment_s"] = time.time() - t
    print(f"[2] segment: {timings['segment_s']:.0f}s", flush=True)

    t = time.time()
    sam.tiff_to_gpkg(mask, gpkg, simplify_tolerance=None)
    timings["polygonise_s"] = time.time() - t
    print(f"[3] polygonise: {timings['polygonise_s']:.0f}s", flush=True)

    import geopandas as gpd
    pol = gpd.read_file(gpkg)
    if "value" in pol.columns:
        pol = pol.drop(columns="value")
    pol["area_ha"] = pol.area / 10000.0            # correct m^2 -> ha (see module docstring)
    pol["perim_area"] = pol.length / pol["area_ha"]
    keep = pol[(pol.area_ha >= args.min_area_ha) & (pol.area_ha <= args.max_area_ha) &
               (pol.perim_area <= args.max_perim_area_ratio)]
    keep.to_file(filt, driver="GPKG")

    print(f"\npolygons: {len(pol)} raw -> {len(keep)} after filter")
    print(f"area_ha: median {keep.area_ha.median():.1f}, "
          f"p10 {keep.area_ha.quantile(.1):.1f}, p90 {keep.area_ha.quantile(.9):.1f}")
    total = sum(timings.values())
    for k, v in timings.items():
        print(f"  {k:16s} {v:8.0f}s")
    print(f"  {'TOTAL':16s} {total:8.0f}s   device={dev}, scenes={n_scenes}, "
          f"AOI={2*args.buffer:.3f}deg")
    import json
    with open(os.path.join(args.outdir, args.stub + "_timings.json"), "w") as fh:
        json.dump({**timings, "device": dev, "n_scenes": n_scenes,
                   "n_polygons_raw": len(pol), "n_polygons_filt": len(keep),
                   "image_shape": list(shape)}, fh, indent=2)


if __name__ == "__main__":
    main()
