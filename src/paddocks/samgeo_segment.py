#!/usr/bin/env python3
"""
SAMGeo paddock segmentation — split into two stages so each runs on the cheapest queue.

Follows PaddockTS (`01_pre-segment.py` + `02_SAMGeo_paddocks.py`): build a 3-band image from
the Fourier transform of an NDWI time series, segment it with SAM (vit_h), polygonise, then
filter on area and shape.

WHY TWO STAGES. Measured on the 11 km benchmark AOI: pre-segment 133 s, SAM model load 49 s,
segment 29 s, polygonise 3 s — GPU utilisation 21 %. So ~62 % of the runtime is a datacube
read that needs no GPU at all, and the model load is a fixed per-job cost paid once per AOI
if you run them one at a time. `gpuvolta` bills 12 CPUs per GPU whatever you request, so any
non-GPU second spent in a GPU job is billed at the full GPU rate. Splitting lets stage 1 run
as many small cheap `normal` jobs and stage 2 batch many AOIs behind a single model load.

    # stage 1 (normal queue, no GPU) — build the Fourier-NDWI composites
    python3 samgeo_segment.py presegment --aois aois.csv --outdir DIR

    # stage 2 (gpuvolta) — one model load, many AOIs
    python3 samgeo_segment.py segment --aois aois.csv --outdir DIR

    # single AOI, both stages (the original one-shot path, kept for spot checks)
    python3 samgeo_segment.py all --lat <LAT> --lon <LON> --half-m 5500 \
        --start 2020-01-01 --end 2020-12-31 --outdir DIR --stub yorke2020

Both stages are idempotent: an AOI whose output already exists is skipped, so a job killed at
walltime resumes rather than restarting. Timings are appended per AOI (not buffered to the
end) so a killed job still leaves usable benchmark data — the Stage-2 lesson.

KNOWN FAILURE, NOT OURS: the DEA archive contains occasional ZERO-BYTE tiles (seen on the
1,362-AOI run: `ga_s2bm_oa_3-2-1_54HWH_2022-01-23_final_fmask.tif`, 0 bytes, dated Jul 2022).
dc.load then raises "not recognized as a supported file format" and the whole AOI fails,
reproducibly. Per-AOI exception handling keeps the rest of the batch alive; the fix for the
affected AOI is to narrow --start/--end past the bad date, which costs nothing when the bad
scene is outside the flowering window. Worth reporting to the NCI/DEA helpdesk.

NOTE ON AREA UNITS: PaddockTS computes `area_ha = pol.area/1000`. In an equal-area CRS
`.area` is m², so hectares are `/10000` — that expression is 10x too large, which makes the
shipped --min-area-ha 10 / --max-area-ha 1500 filter behave like 1 ha / 150 ha. This script
uses the correct conversion, so its area thresholds are not interchangeable with theirs.
"""
import argparse
import csv
import json
import os
import time

import numpy as np

# Sentinel-2 fmask: 1 = clear land.
FMASK_CLEAR = 1


def aoi_paths(outdir, stub):
    j = os.path.join
    return dict(tif=j(outdir, stub + ".tif"),
                mask=j(outdir, stub + "_segment.tif"),
                gpkg=j(outdir, stub + "_segment.gpkg"),
                filt=j(outdir, stub + "_filt.gpkg"))


def log_timing(outdir, stage, row):
    """Append one row per AOI so a walltime kill still leaves benchmark data behind."""
    path = os.path.join(outdir, f"timings_{stage}.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)


def build_image(lat, lon, half_m, start, end, out_tif, resolution=10):
    """3-band Fourier-of-NDWI GeoTIFF, per PaddockTS 01_pre-segment.py."""
    import datacube
    import hdstats
    import rasterio
    from datacube.utils import geometry
    from rasterio.transform import from_bounds

    dc = datacube.Datacube(app="samgeo_presegment")
    # Query in Albers metres so the AOI is a true square of known size, rather than a
    # degree box whose ground width changes with latitude.
    pt = geometry.point(lon, lat, geometry.CRS("EPSG:4326")).to_crs(geometry.CRS("EPSG:3577"))
    cx, cy = pt.points[0]
    ds = dc.load(
        product=["ga_s2am_ard_3", "ga_s2bm_ard_3", "ga_s2cm_ard_3"],
        x=(cx - half_m, cx + half_m), y=(cy - half_m, cy + half_m), crs="EPSG:3577",
        time=(start, end),
        measurements=["nbart_green", "nbart_nir_1", "oa_fmask"],
        output_crs="EPSG:6933",           # equal-area, as PaddockTS uses
        resolution=(-resolution, resolution),
        group_by="solar_day",
    )
    if ds.sizes.get("time", 0) == 0:
        raise RuntimeError("no Sentinel-2 scenes for this AOI/time range")
    clear = ds["oa_fmask"] == FMASK_CLEAR
    g = ds["nbart_green"].where((ds["nbart_green"] != -999) & clear).astype("float32")
    nir = ds["nbart_nir_1"].where((ds["nbart_nir_1"] != -999) & clear).astype("float32")
    ndwi = ((g - nir) / (g + nir)).transpose("y", "x", "time").values
    # hdstats wants a dense (y, x, t) cube; gaps are filled with the per-pixel mean so the
    # transform sees a continuous series rather than NaNs.
    mean = np.nanmean(ndwi, axis=2, keepdims=True)
    ndwi = np.where(np.isnan(ndwi), np.where(np.isnan(mean), 0.0, mean), ndwi)

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
    return int(ds.sizes["time"]), img.shape


def sam_kwargs(args):
    """SamAutomaticMaskGenerator settings, or None for the library defaults.

    The original runs passed `sam_kwargs=None`, i.e. points_per_side=32 over the whole AOI.
    That is the direct cause of the dominant review failure mode: at 32 prompt points across a
    ~3 km tile, adjacent fields of similar wetness get merged into one mask, which surfaces as
    "whole region, not a paddock" (222 flagged polygons over 300 ha, up to 1,048 ha) and as
    co-located trials of different crops landing on one polygon. Raising the sampling density
    is the first thing to try, and it costs GPU time roughly quadratically.
    """
    kw = {k: v for k, v in {
        "points_per_side": args.points_per_side,
        "pred_iou_thresh": args.pred_iou_thresh,
        "stability_score_thresh": args.stability_score_thresh,
        "crop_n_layers": args.crop_n_layers,
        "min_mask_region_area": args.min_mask_region_area,
    }.items() if v is not None}
    return kw or None


def filter_polygons(gpkg, filt, min_area_ha, max_area_ha, max_compactness):
    """Area + shape filter. Returns (n_raw, n_kept, median_ha)."""
    import geopandas as gpd

    pol = gpd.read_file(gpkg)
    if "value" in pol.columns:
        pol = pol.drop(columns="value")
    pol["area_ha"] = pol.area / 10000.0            # correct m^2 -> ha
    # Shape filter uses a DIMENSIONLESS compactness, P/sqrt(A) (square = 4.0, circle = 3.54).
    # PaddockTS filters on length/(area/1000), which is not dimensionless and is only
    # meaningful alongside its 10x-inflated area — correcting the area alone silently
    # rejects everything, which is exactly what happened on the first run here.
    pol["compactness"] = pol.length / np.sqrt(pol.area)
    keep = pol[(pol.area_ha >= min_area_ha) & (pol.area_ha <= max_area_ha) &
               (pol.compactness <= max_compactness)]
    keep.to_file(filt, driver="GPKG")
    med = float(keep.area_ha.median()) if len(keep) else float("nan")
    return len(pol), len(keep), med


def read_aois(path):
    import pandas as pd
    return pd.read_csv(path).to_dict("records")


def do_presegment(args):
    os.makedirs(args.outdir, exist_ok=True)
    aois = read_aois(args.aois)
    done = skipped = failed = 0
    for a in aois:
        p = aoi_paths(args.outdir, a["stub"])
        if os.path.exists(p["tif"]) and not args.force:
            skipped += 1
            continue
        t = time.time()
        try:
            n_scenes, shape = build_image(float(a["lat"]), float(a["lon"]), float(a["half_m"]),
                                          a["start"], a["end"], p["tif"])
        except Exception as e:                      # one bad AOI must not kill the batch
            print(f"FAILED {a['stub']}: {e}", flush=True)
            log_timing(args.outdir, "presegment",
                       {"stub": a["stub"], "half_m": a["half_m"], "status": "FAILED",
                        "seconds": round(time.time() - t, 1), "n_scenes": "", "px": ""})
            failed += 1
            continue
        dt = time.time() - t
        log_timing(args.outdir, "presegment",
                   {"stub": a["stub"], "half_m": a["half_m"], "status": "OK",
                    "seconds": round(dt, 1), "n_scenes": n_scenes,
                    "px": shape[0] * shape[1]})
        print(f"{a['stub']}: {dt:.0f}s, {n_scenes} scenes, {shape[0]}x{shape[1]}", flush=True)
        done += 1
    print(f"presegment: {done} built, {skipped} skipped, {failed} failed")


def do_segment(args):
    os.makedirs(args.outdir, exist_ok=True)
    aois = read_aois(args.aois)
    todo = [a for a in aois
            if os.path.exists(aoi_paths(args.outdir, a["stub"])["tif"])
            and (args.force or not os.path.exists(aoi_paths(args.outdir, a["stub"])["filt"]))]
    missing = [a for a in aois if not os.path.exists(aoi_paths(args.outdir, a["stub"])["tif"])]
    if missing:
        print(f"WARNING: {len(missing)} AOIs have no pre-segment .tif — run presegment first")
    if not todo:
        print("nothing to segment")
        return

    import torch
    from samgeo import SamGeo
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    # The whole point of batching: this is paid once, not once per AOI.
    t = time.time()
    sam = SamGeo(model_type="vit_h", checkpoint=args.checkpoint, sam_kwargs=sam_kwargs(args))
    load_s = time.time() - t
    print(f"SAM on {dev}, model load {load_s:.0f}s, {len(todo)} AOIs to segment", flush=True)
    print(f"sam_kwargs={sam_kwargs(args)}", flush=True)

    for i, a in enumerate(todo, 1):
        p = aoi_paths(args.outdir, a["stub"])
        t = time.time()
        try:
            sam.generate(p["tif"], p["mask"], batch=True, foreground=True,
                         erosion_kernel=(3, 3), mask_multiplier=255)
            seg_s = time.time() - t
            t2 = time.time()
            sam.tiff_to_gpkg(p["mask"], p["gpkg"], simplify_tolerance=None)
            poly_s = time.time() - t2
            n_raw, n_keep, med = filter_polygons(p["gpkg"], p["filt"], args.min_area_ha,
                                                 args.max_area_ha, args.max_compactness)
        except Exception as e:
            print(f"FAILED {a['stub']}: {e}", flush=True)
            log_timing(args.outdir, "segment",
                       {"stub": a["stub"], "half_m": a["half_m"], "status": "FAILED",
                        "device": dev, "model_load_s": round(load_s, 1), "segment_s": "",
                        "polygonise_s": "", "n_raw": "", "n_keep": "", "median_ha": ""})
            continue
        log_timing(args.outdir, "segment",
                   {"stub": a["stub"], "half_m": a["half_m"], "status": "OK",
                    "device": dev, "model_load_s": round(load_s, 1),
                    "segment_s": round(seg_s, 1), "polygonise_s": round(poly_s, 1),
                    "n_raw": n_raw, "n_keep": n_keep, "median_ha": round(med, 1)})
        print(f"[{i}/{len(todo)}] {a['stub']}: segment {seg_s:.0f}s, "
              f"{n_raw} -> {n_keep} polygons, median {med:.1f} ha", flush=True)


def do_all(args):
    """Single AOI, both stages — the original one-shot path, for spot checks."""
    os.makedirs(args.outdir, exist_ok=True)
    p = aoi_paths(args.outdir, args.stub)
    timings = {}
    t = time.time()
    n_scenes, shape = build_image(args.lat, args.lon, args.half_m, args.start, args.end,
                                  p["tif"])
    timings["pre_segment_s"] = time.time() - t
    print(f"[1] pre-segment: {timings['pre_segment_s']:.0f}s -> {p['tif']} {shape}", flush=True)

    import torch
    from samgeo import SamGeo
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[2] SAM on {dev}", flush=True)
    t = time.time()
    sam = SamGeo(model_type="vit_h", checkpoint=args.checkpoint, sam_kwargs=None)
    timings["model_load_s"] = time.time() - t
    t = time.time()
    sam.generate(p["tif"], p["mask"], batch=True, foreground=True, erosion_kernel=(3, 3),
                 mask_multiplier=255)
    timings["segment_s"] = time.time() - t
    print(f"[2] segment: {timings['segment_s']:.0f}s", flush=True)
    t = time.time()
    sam.tiff_to_gpkg(p["mask"], p["gpkg"], simplify_tolerance=None)
    timings["polygonise_s"] = time.time() - t
    print(f"[3] polygonise: {timings['polygonise_s']:.0f}s", flush=True)

    n_raw, n_keep, med = filter_polygons(p["gpkg"], p["filt"], args.min_area_ha,
                                         args.max_area_ha, args.max_compactness)
    print(f"\npolygons: {n_raw} raw -> {n_keep} after filter")
    print(f"area_ha: median {med:.1f}")
    for k, v in timings.items():
        print(f"  {k:16s} {v:8.0f}s")
    print(f"  {'TOTAL':16s} {sum(timings.values()):8.0f}s   device={dev}, "
          f"scenes={n_scenes}, half_m={args.half_m:.0f}")
    with open(os.path.join(args.outdir, args.stub + "_timings.json"), "w") as fh:
        json.dump({**timings, "device": dev, "n_scenes": n_scenes, "n_polygons_raw": n_raw,
                   "n_polygons_filt": n_keep, "image_shape": list(shape)}, fh, indent=2)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_filter_args(p):
        p.add_argument("--min-area-ha", type=float, default=1.0)
        p.add_argument("--max-area-ha", type=float, default=1500.0)
        p.add_argument("--max-compactness", type=float, default=8.0,
                       help="max P/sqrt(A); square=4.0, circle=3.54. Dimensionless, unlike "
                            "PaddockTS's perimeter:area which depends on its area units")
        p.add_argument("--checkpoint",
                       default="/g/data/xe2/John/Data/PadSeg/sam_vit_h_4b8939.pth")
        # All default to None so the library defaults are used and existing runs reproduce
        # exactly. Only a value explicitly passed enters sam_kwargs.
        p.add_argument("--points-per-side", type=int, default=None,
                       help="SAM prompt grid density (library default 32). Higher splits "
                            "merged fields; cost grows ~quadratically")
        p.add_argument("--pred-iou-thresh", type=float, default=None,
                       help="library default 0.88; lower admits more, weaker masks")
        p.add_argument("--stability-score-thresh", type=float, default=None,
                       help="library default 0.95; lower admits more, weaker masks")
        p.add_argument("--crop-n-layers", type=int, default=None,
                       help="library default 0; 1 re-runs on crops, catching small fields")
        p.add_argument("--min-mask-region-area", type=int, default=None)

    p1 = sub.add_parser("presegment", help="stage 1: Fourier-NDWI composites (no GPU)")
    p1.add_argument("--aois", required=True)
    p1.add_argument("--outdir", required=True)
    p1.add_argument("--force", action="store_true")
    p1.set_defaults(func=do_presegment)

    p2 = sub.add_parser("segment", help="stage 2: SAM over many AOIs, one model load")
    p2.add_argument("--aois", required=True)
    p2.add_argument("--outdir", required=True)
    p2.add_argument("--force", action="store_true")
    add_filter_args(p2)
    p2.set_defaults(func=do_segment)

    p3 = sub.add_parser("all", help="single AOI, both stages")
    p3.add_argument("--lat", type=float, required=True)
    p3.add_argument("--lon", type=float, required=True)
    p3.add_argument("--half-m", type=float, default=5500.0, help="AOI half-width, metres")
    p3.add_argument("--start", default="2020-01-01")
    p3.add_argument("--end", default="2020-12-31")
    p3.add_argument("--outdir", required=True)
    p3.add_argument("--stub", required=True)
    add_filter_args(p3)
    p3.set_defaults(func=do_all)

    args = ap.parse_args()
    os.environ.setdefault("PROJ_NETWORK", "OFF")
    args.func(args)


if __name__ == "__main__":
    main()
