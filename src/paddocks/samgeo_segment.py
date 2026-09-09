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
dc.load then raises "not recognized as a supported file format". Originally documented here as
a per-AOI failure to work around manually (narrow --start/--end past the bad date); found
2026-09-07 that this is what silently stalled the LAST 753 tiles of the national2022 run for
its entire duration — every repair attempt failed 100% of its AOIs against this same file (plus
a second one, `50JNR` on the same date), and nothing distinguished it from a transient
connection error until the logs were read directly. `build_image` (below) now passes
`skip_broken_datasets=True` to dc.load, which skips only the broken dataset and keeps every
other scene, so a bad file anywhere in the year costs one scene, not the whole tile. Worth
reporting to the NCI/DEA helpdesk regardless — this class of failure has real time-waste cost
(see MEMORY.md, `dea-archive-corrupt-scenes-silently-fail-aoi.md`) and won't be caught by exit
status alone.

NOTE ON AREA UNITS: PaddockTS computes `area_ha = pol.area/1000`. In an equal-area CRS
`.area` is m², so hectares are `/10000` — that expression is 10x too large, which makes the
shipped --min-area-ha 10 / --max-area-ha 1500 filter behave like 1 ha / 150 ha. This script
uses the correct conversion, so its area thresholds are not interchangeable with theirs.
"""
import argparse
import contextlib
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
    """Append one row per AOI so a walltime kill still leaves benchmark data behind.

    ONE FILE PER JOB, NOT ONE FILE PER STAGE. Every job of a stage writes concurrently to the
    same directory, and an append from a separate process is only atomic below the pipe buffer.
    Sharing one file corrupted `timings_segment.csv` on the 2026-08-25 Riverina run: six GPU
    jobs interleaved mid-line and produced rows like `6.56.46.52.9...`.

    It is a telemetry bug, not a data one, and it is partial — 909 of 910 parsed rows survived,
    because most writes do land atomically. But the failure is silent and it grows with the
    number of concurrent writers, so at national scale (100,000 tiles, many more jobs) the
    benchmark this file exists to support would quietly stop being trustworthy. The
    segmentation outputs were never at risk: every tile writes its own GeoPackage.

    The job id keeps the writers apart; read a stage back with a glob."""
    job = os.environ.get("PBS_JOBID", str(os.getpid())).split(".")[0]
    if os.environ.get("BENCH_WORKER"):          # several workers share one PBS job: one file each
        job = f"{job}_{os.getpid()}"
    path = os.path.join(outdir, f"timings_{stage}_{job}.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)


# ONE DATACUBE CONNECTION PER PROCESS, NOT PER TILE.
#
# This used to be `datacube.Datacube(...)` inside build_image, i.e. a fresh Postgres connection
# for every AOI — 310 open/close cycles per job. With 320 jobs on the continent that exhausted
# the DEA connection pooler outright:
#
#     psycopg2.OperationalError: FATAL: no more connections allowed (max_client_conn)
#
# and because each AOI is wrapped in `except Exception`, every one of those failures printed
# FAILED and moved on while the JOB still exited 0. Measured on the first national attempt:
# **79 % of tiles failed and PBS reported success on every chunk.** The composites simply were
# not there, and nothing downstream would have noticed until the map had holes.
#
# The pool is shared with every other DEA user on gadi, so the fix is both correctness and
# courtesy: hold one connection for the life of the process, and back off rather than hammer
# when the pooler is full.
_DC = None


def _datacube():
    global _DC
    if _DC is None:
        import datacube
        _DC = datacube.Datacube(app="samgeo_presegment")
    return _DC


def _is_transient(e):
    """Pool exhaustion and dropped connections are worth waiting for; a bad AOI is not."""
    m = str(e).lower()
    return any(k in m for k in ("max_client_conn", "no more connections", "too many clients",
                                "connection reset", "server closed the connection",
                                "could not connect", "operationalerror", "timeout expired"))


def with_retry(fn, *a, tries=6, base=20.0, **kw):
    """Retry `fn` on transient datacube/database errors with exponential backoff + jitter.

    Backoff is jittered because the failure is CORRELATED across jobs — the pooler fills when
    everyone queries at once, so a fixed sleep would send the whole fleet back in lockstep and
    refill it instantly. 20 s doubling to ~10 min covers a pooler that is full because of a
    burst; anything longer than that is a real outage and should surface as a failure.
    """
    import random
    for i in range(tries):
        try:
            return fn(*a, **kw)
        except Exception as e:
            if i == tries - 1 or not _is_transient(e):
                raise
            wait = base * (2 ** i) * (0.5 + random.random())
            print(f"  transient datacube error ({type(e).__name__}), "
                  f"retry {i + 1}/{tries - 1} in {wait:.0f}s", flush=True)
            time.sleep(wait)


def build_image(lat, lon, half_m, start, end, out_tif, resolution=10):
    """3-band Fourier-of-NDWI GeoTIFF, per PaddockTS 01_pre-segment.py."""
    import datacube
    import hdstats
    import rasterio
    from datacube.utils import geometry
    from rasterio.transform import from_bounds

    dc = _datacube()
    # Query in Albers metres so the AOI is a true square of known size, rather than a
    # degree box whose ground width changes with latitude.
    pt = geometry.point(lon, lat, geometry.CRS("EPSG:4326")).to_crs(geometry.CRS("EPSG:3577"))
    cx, cy = pt.points[0]
    # skip_broken_datasets=True: without it, ONE corrupt scene anywhere in the time range (GA
    # occasionally ships a zero-byte ARD tile — see the module docstring) raises "not recognized
    # as a supported file format" and fails the ENTIRE AOI, discarding every other good scene.
    # Found 2026-09-07 re-running `repair` on national2022's last 753 tiles: all 4 repair jobs
    # reported 0/754 built, every failure tracing to the same two files (`54HWH`/`50JNR`, both
    # dated 2022-01-23, both 0 bytes on disk since Jul 2022) — a permanent archive defect, not
    # the transient connection issue this same tile subset hit on 2026-09-04. An earlier version
    # of this fix hand-rolled a find_datasets+exclude-and-retry loop, but it dropped x=/y=/crs=
    # from the retry's dc.load call, which loads the FULL ~100km scene extent rather than the
    # 3km AOI window when no spatial query is given — instant 4GB OOM on a single test tile.
    # datacube 1.8.17 already has the right primitive for this (confirmed via
    # inspect.signature): it skips only the broken dataset, keeping the query/windowing intact.
    ds = dc.load(
        product=["ga_s2am_ard_3", "ga_s2bm_ard_3", "ga_s2cm_ard_3"],
        x=(cx - half_m, cx + half_m), y=(cy - half_m, cy + half_m), crs="EPSG:3577",
        time=(start, end),
        measurements=["nbart_green", "nbart_nir_1", "oa_fmask"],
        output_crs="EPSG:6933",           # equal-area, as PaddockTS uses
        resolution=(-resolution, resolution),
        group_by="solar_day",
        skip_broken_datasets=True,
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
        "points_per_batch": getattr(args, "points_per_batch", None),
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
            n_scenes, shape = with_retry(
                build_image, float(a["lat"]), float(a["lon"]), float(a["half_m"]),
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

    # EXIT NON-ZERO ON A SYSTEMIC FAILURE. Wrapping each AOI in try/except is right for one bad
    # tile and wrong for a shared service falling over: on the first national submission every
    # job exited 0 with 84 % of its tiles FAILED, and nothing downstream could tell. The queue
    # said success, the composites were not there, and the map would have had holes.
    #
    # A few per cent of failures is normal (an AOI with no Sentinel-2 coverage, a corrupt scene).
    # Above `--max-fail-frac` it is not a tile problem, it is a run problem, and the job must say
    # so where PBS can see it.
    attempted = done + failed
    if attempted and failed / attempted > args.max_fail_frac:
        raise SystemExit(
            f"ABORT: {failed}/{attempted} AOIs failed ({100 * failed / attempted:.0f} %), above "
            f"--max-fail-frac {args.max_fail_frac:.0%}. This is a systemic fault, not bad tiles "
            f"— check for datacube connection errors and re-submit with fewer concurrent jobs.")


def _full_grid(n):
    import numpy as np
    g = (np.arange(n) + 0.5) / n
    return np.array([(x, y) for y in g for x in g])


def _install_image_only_prompts(mask_generator, n):
    """Wrap SamAutomaticMaskGenerator.generate so the prompt grid covers only the window's
    non-zero (image) extent, plus one grid cell of margin, in normalised coordinates."""
    import numpy as np
    base = _full_grid(n)
    orig = mask_generator.generate

    def generate(image, *a, **k):
        h, w = image.shape[:2]
        nz = np.asarray(image).reshape(h, w, -1).any(axis=2)
        rows, cols = np.where(nz.any(axis=1))[0], np.where(nz.any(axis=0))[0]
        if len(rows) == 0:
            return []
        y0, y1, x0, x1 = rows[0] / h, (rows[-1] + 1) / h, cols[0] / w, (cols[-1] + 1) / w
        keep = ((base[:, 0] >= x0 - 1 / n) & (base[:, 0] <= x1 + 1 / n) &
                (base[:, 1] >= y0 - 1 / n) & (base[:, 1] <= y1 + 1 / n))
        mask_generator.point_grids = [base[keep]]
        return orig(image, *a, **k)
    mask_generator.generate = generate


def do_segment(args):
    os.makedirs(args.outdir, exist_ok=True)
    aois = read_aois(args.aois)
    todo = [a for a in aois
            if os.path.exists(aoi_paths(args.outdir, a["stub"])["tif"])
            and (args.force or not os.path.exists(aoi_paths(args.outdir, a["stub"])["filt"]))]
    missing = [a for a in aois if not os.path.exists(aoi_paths(args.outdir, a["stub"])["tif"])]

    # A MISSING INPUT IS NOT A WARNING. This used to print one line and carry on, and that is
    # how the national run grew a Victoria-shaped hole: 56 chunks never ran presegment (they
    # were system-held over the 200-job queue ceiling and reaped), so this stage saw 310 of 310
    # composites absent, printed the warning, said "nothing to segment" and exited 0. PBS
    # recorded success, predict then ran over the same empty ground and also exited 0, and the
    # first sign of trouble would have been missing paddocks in a national map.
    #
    # The per-AOI try/except below is the right shape for one corrupt scene. It is the wrong
    # shape for "the stage that feeds me never ran", because that is not a property of any tile
    # — so it is checked once, up front, against the count that was ASKED for. Exit 0 has to
    # mean the work was done, not merely that nothing raised.
    if missing:
        frac = len(missing) / len(aois)
        print(f"WARNING: {len(missing)}/{len(aois)} AOIs have no pre-segment .tif "
              f"({frac:.0%})", flush=True)
        if frac > args.max_missing_frac:
            raise SystemExit(
                f"ABORT: {len(missing)}/{len(aois)} AOIs ({frac:.0%}) have no composite, above "
                f"--max-missing-frac {args.max_missing_frac:.0%}. Pre-segment did not run for "
                f"this list — check for system-held ({{Hold_Types = s}}) or reaped jobs and "
                f"re-submit with `run_national.sh repair` before segmenting.")
    if not todo:
        # Reached only when the missing fraction is small enough to tolerate, so every AOI that
        # HAS a composite already has its polygons. That is genuinely nothing to do.
        print("nothing to segment")
        return

    import torch
    from samgeo import SamGeo
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    # The whole point of batching: this is paid once, not once per AOI.
    t = time.time()
    kw = sam_kwargs(args)
    if getattr(args, "prompt_image_only", False):
        # samgeo reads every sample window with `bound` px of boundless (zero-filled) margin, so
        # a 3 km composite (351 x 316 px) sits in a 768 px canvas that is 81 % zero padding, and
        # SAM's points_per_side grid prompts the padding too (752 of 1,024 points decode nothing).
        # The generator is built with an explicit grid and the grid is rebuilt for every window
        # from the window's own non-zero extent (+ one grid cell), so it is right for any tile
        # size, for multi-window composites and for the padded edge windows of big tiles.
        n = args.points_per_side or 32
        kw = dict(kw or {})
        kw["points_per_side"] = None          # SAM insists on exactly one of the two
        kw["point_grids"] = [_full_grid(n)]
        print(f"prompt grid restricted to each window's image content ({n}x{n} base grid)", flush=True)
    sam = SamGeo(model_type="vit_h", checkpoint=args.checkpoint, sam_kwargs=kw)
    if getattr(args, "prompt_image_only", False):
        _install_image_only_prompts(sam.mask_generator, args.points_per_side or 32)
    load_s = time.time() - t
    print(f"SAM on {dev}, model load {load_s:.0f}s, {len(todo)} AOIs to segment", flush=True)
    print(f"sam_kwargs={ {k: (v if k != 'point_grids' else f'{len(v[0])} points') for k, v in (kw or {}).items()} }", flush=True)

    for i, a in enumerate(todo, 1):
        p = aoi_paths(args.outdir, a["stub"])
        t = time.time()
        try:
            gen_kw = dict(batch=not getattr(args, "no_batch", False), foreground=True,
                          erosion_kernel=(3, 3), mask_multiplier=255)
            if gen_kw["batch"]:
                # samgeo splits the composite into sample_size windows read with `bound` px of
                # context on every side and writes back only the centre (common.py:1095), so
                # seams INSIDE a tile are stitched with context; only the outer raster edge cuts.
                if getattr(args, "sample_size", None):
                    gen_kw["sample_size"] = (args.sample_size, args.sample_size)
                if getattr(args, "bound", None) is not None:
                    gen_kw["bound"] = args.bound
            else:
                gen_kw["unique"] = False     # binary + erosion, same downstream as the batch path
            ctx = (torch.autocast(device_type="cuda", dtype=torch.float16)
                   if getattr(args, "fp16", False) and dev == "cuda" else contextlib.nullcontext())
            with ctx:
                sam.generate(p["tif"], p["mask"], **gen_kw)
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
    p1.add_argument("--max-fail-frac", type=float, default=0.10,
                    help="abort the job (non-zero exit) if more than this fraction of AOIs fail. "
                         "A per-AOI try/except cannot tell a bad tile from a shared service that "
                         "has fallen over, and the first national submission exited 0 on every "
                         "chunk with 84 %% of tiles failed. This is the job-level check that "
                         "makes a systemic fault visible to PBS.")
    p1.set_defaults(func=do_presegment)

    p2 = sub.add_parser("segment", help="stage 2: SAM over many AOIs, one model load")
    p2.add_argument("--aois", required=True)
    p2.add_argument("--outdir", required=True)
    p2.add_argument("--force", action="store_true")
    # Benchmark knobs (output/BENCH_KSU.md). All default to the production behaviour.
    p2.add_argument("--sample-size", type=int, default=None,
                    help="samgeo batch window edge in px (library default 512)")
    p2.add_argument("--bound", type=int, default=None,
                    help="context read around each window, px (library default 128)")
    p2.add_argument("--no-batch", action="store_true",
                    help="one SAM pass over the whole composite (resized to 1024 px)")
    p2.add_argument("--points-per-batch", type=int, default=None,
                    help="prompts decoded per GPU batch (library default 64)")
    p2.add_argument("--fp16", action="store_true", help="torch.autocast float16 around generate")
    p2.add_argument("--prompt-image-only", action="store_true",
                    help="prompt only each window's image content, not samgeo's zero padding "
                         "(2.5x less GPU time on 3 km tiles, identical polygons; BENCH_KSU.md)")
    p2.add_argument("--max-missing-frac", type=float, default=0.10,
                    help="abort the job (non-zero exit) if more than this fraction of AOIs have "
                         "no pre-segment composite. Distinct from --max-fail-frac: that catches "
                         "a stage failing on its own items, this catches the stage BEFORE it "
                         "never having run. 56 chunks of the first national run were reaped off "
                         "the queue unstarted, and SAM reported success on every one of them.")
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
