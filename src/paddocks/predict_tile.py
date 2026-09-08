#!/usr/bin/env python3
"""
Wall-to-wall inference: classify EVERY segmented polygon in a tile, not just the ones a trial
sits in. This is the step between "we have a validated classifier" and "we have a map".

    python3 predict_tile.py --aois region.csv --polydir DIR --model group4.joblib \
        --out DIR/predictions.gpkg

WHY THIS IS NOT `extract_paddock.py` IN A LOOP, AND WHY THAT MATTERS FOR THE NATIONAL BILL.
`extract_paddock.py` is point-driven: one datacube read per trial, padded around one polygon.
Over a tile with 300 polygons that is 300 overlapping reads of the same scenes, and the
Sentinel-2 read is already the dominant cost of the whole pipeline (`TILE_SIZE_BENCHMARK.md`:
scene-cache locality, not tile size, is what moves per-tile cost, by 4.0x). Here the tile is
read ONCE and every polygon is a zonal statistic over that one cube, so the read amortises over
the polygons instead of multiplying by them.

THE FEATURES MUST BE IDENTICAL TO TRAINING, and "identical" is a stronger claim than "the same
formula". Four things are replicated deliberately, and each of them was a real choice upstream:
  * the polygon is eroded by 10 m before averaging, so boundary pixels mixed with road and tree
    line do not re-import the contamination the erosion exists to remove;
  * the same 1 m canopy mask is applied, because canopy is green all year and never flowers, so
    it flattens the exact peak the classifier reads;
  * the paddock MEDIAN, not the mean — a tree line or a header trail moves the mean;
  * dates with less than half the paddock's pixels clear are dropped, matching the
    `n_clear_px / n_px_paddock >= 0.5` filter every training row passed through.
Anything computed differently here would be a distribution shift the validation never saw.

WHAT IS EMITTED. One row per polygon with the predicted class, the probability of EVERY class,
and the quality fields (`area_ha`, `compactness`, `n_obs`, `n_clear_frac`, `treed_frac`,
`n_feat_present`, `touches_grid`, `dist_to_grid_m`). The probabilities are not decoration: every
operating-point result in this project — canola at 5 % FPR, the precision/recall trade — is
unrecoverable from a hard label, and a national product cannot be hand-reviewed, so the fields
the hand review used have to travel with the data instead. `touches_grid`/`dist_to_grid_m` flag
whether a polygon sits near its own tile's edge — a candidate for a tile-grid cut, not a filter;
every polygon ships regardless of its value (see `--grid-touch-tol-m`).
"""
import argparse
import glob
import os
import time

import numpy as np
import pandas as pd

FMASK_CLEAR = 1
NODATA = -999
REFL_SCALE = 10000.0
ALL_BANDS = ["nbart_blue", "nbart_green", "nbart_red", "nbart_red_edge_1", "nbart_red_edge_2",
             "nbart_red_edge_3", "nbart_nir_1", "nbart_nir_2", "nbart_swir_2", "nbart_swir_3"]
IDX_BANDS = ["nbart_red", "nbart_green", "nbart_blue", "nbart_nir_1"]
PRODUCTS = ["ga_s2am_ard_3", "ga_s2bm_ard_3", "ga_s2cm_ard_3"]


def zonal_medians(ds, labels, n_poly, value_cols, kind):
    """(n_poly, n_time, n_value) medians per polygon per date, over clear pixels only.

    `labels` is a rasterised polygon-index array (-1 = no polygon). Pixels are gathered once
    per polygon and then reused across every band and date, which is what keeps this cheap:
    the alternative — a boolean mask per polygon per band per date — rebuilds the same index
    set a few hundred times over.

    The index families are computed PER PIXEL and then medianed, exactly as
    `extract_paddock.py` does. This is not interchangeable with computing the index from the
    median reflectance: CFI is non-linear in reflectance, so median(CFI) != CFI(median), and
    the index files carry a signal a band file cannot reconstruct.
    """
    nt = ds.sizes["time"]
    clear = (ds["oa_fmask"].values == FMASK_CLEAR)                      # (t, y, x)

    def band(name):
        v = ds[name].values.astype("float32")
        return np.where((v == NODATA) | ~clear, np.nan, v) / REFL_SCALE

    if kind == "indices":
        red, green, blue, nir = (band(b) for b in IDX_BANDS)
        with np.errstate(invalid="ignore", divide="ignore"):
            planes = {
                "ndvi_pad_median": (nir - red) / (nir + red),
                "ndyi_pad_median": (green - blue) / (green + blue),
                "cfi_pad_median": ((nir - red) / (nir + red)) *
                                  ((red + green) + (green - blue)),
            }
    else:
        planes = {b.replace("nbart_", ""): band(b) for b in ALL_BANDS}
    stack = np.stack([planes[c] for c in value_cols], axis=-1)          # (t, y, x, v)

    out = np.full((n_poly, nt, len(value_cols)), np.nan, np.float32)
    n_clear = np.zeros((n_poly, nt), np.int32)
    n_px = np.zeros(n_poly, np.int32)
    flat = labels.ravel()
    order = np.argsort(flat, kind="stable")
    sflat = flat[order]
    starts = np.searchsorted(sflat, np.arange(n_poly), "left")
    ends = np.searchsorted(sflat, np.arange(n_poly), "right")
    S = stack.reshape(nt, -1, len(value_cols))
    C = clear.reshape(nt, -1)
    import warnings
    for i in range(n_poly):
        px = order[starts[i]:ends[i]]
        if px.size == 0:
            continue
        n_px[i] = px.size
        n_clear[i] = C[:, px].sum(axis=1)
        with np.errstate(invalid="ignore"), warnings.catch_warnings():
            # A polygon-date with no clear pixel is an expected, meaningful outcome — it stays
            # NaN and is dropped downstream by the clear-fraction and min-obs filters. The
            # warning would fire once per cloudy date per polygon and bury everything else.
            warnings.simplefilter("ignore", RuntimeWarning)
            out[i] = np.nanmedian(S[:, px, :], axis=1)
    return out, n_clear, n_px


def sharma6_from_bands(bandvals, names):
    """The 6 Sharma et al. (2026) Table S2 indices, on an (n_poly, n_time, n_band) MEDIANED
    array — index-of-median, not median-of-index.

    Formulas copied verbatim from `train_species.py`'s `add_indices()`, re-targeted from its
    DOY-binned wide columns to this array's band axis so they run once per (polygon, scene).
    That is the same quantity `add_indices()` already produces in training (it only ever runs
    on binned band medians, never on a per-pixel array), so these columns mean the same thing
    here as they do to the classifier.

    NOTE THE ASYMMETRY, and see the store's own `index_semantics` attribute: NDVI/NDYI/CFI come
    from `zonal_medians(kind="indices")`, which is median-of-per-pixel-index, while these six
    are index-of-median. CFI is non-linear in reflectance so the two are genuinely different
    quantities. This mirrors production rather than inventing a convention for the archive.
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


def write_chunk_zarr(path, recs, model_desc):
    """One consolidated .zarr for a whole chunk of tiles, dims (paddock, time).

    WHY ONE STORE PER CHUNK, NOT PER TILE. `ZARR_BENCHMARK.md` measured the per-tile design at
    26-39 % of baseline on-disk storage against 8-24 % logical, because each store pays ~47
    fixed metadata files regardless of how few polygons the tile holds — and at national scale
    that is 99,465 stores / ~6.9 M files, which is a Lustre metadata problem independent of the
    byte count. A chunk store pays that fixed cost once per ~311 tiles instead, matching how
    `predict_tile.py` already writes exactly one GeoPackage per chunk.

    The time axis is the UNION of the chunk's tiles' scene dates; a paddock is NaN on any date
    its own tile was not observed. Tiles in a chunk are spatially contiguous (the AOI list is
    block-sorted for scene-cache locality), so they share most dates and the union stays close
    to a single tile's scene count — and the NaN padding compresses to almost nothing.

    Joins to the predictions GeoPackage on (stub, poly_idx).
    """
    import xarray as xr

    all_times = np.unique(np.concatenate([r["times"].values for r in recs]))
    tpos = {t: i for i, t in enumerate(all_times)}
    n_pad = sum(len(r["poly_idx"]) for r in recs)
    nt = len(all_times)
    varnames = sorted({v for r in recs for v in r["vars"]})

    data = {v: np.full((n_pad, nt), np.nan, "float32") for v in varnames}
    n_clear = np.zeros((n_pad, nt), "int32")
    n_px = np.zeros(n_pad, "int32")
    stub_co, pidx_co = np.empty(n_pad, object), np.empty(n_pad, "int32")

    p0 = 0
    for r in recs:
        n = len(r["poly_idx"])
        cols = np.array([tpos[t] for t in r["times"].values])
        for v, arr in r["vars"].items():
            data[v][p0:p0 + n, cols] = arr
        n_clear[p0:p0 + n, cols] = r["n_clear"]
        n_px[p0:p0 + n] = r["n_px"]
        stub_co[p0:p0 + n] = r["stub"]
        pidx_co[p0:p0 + n] = r["poly_idx"]
        p0 += n

    ds = xr.Dataset(
        {v: (("paddock", "time"), a) for v, a in data.items()}
        | {"n_clear": (("paddock", "time"), n_clear), "n_px": ("paddock", n_px)},
        coords={"paddock": np.arange(n_pad), "time": pd.to_datetime(all_times),
                "stub": ("paddock", stub_co.astype(str)),
                "poly_idx": ("paddock", pidx_co)},
        attrs={
            "title": "Per-paddock, per-scene Sentinel-2 medians (paddock-species)",
            "source_model": model_desc,
            "join": "join to the predictions GeoPackage on (stub, poly_idx)",
            "index_semantics": ("ndvi/ndyi/cfi are median-of-per-pixel-index (as the classifier "
                                "computes them); ndre2/vi2/vi3/vdvi/vci/evi2_sharma are "
                                "index-of-median, matching train_species.py add_indices()"),
            "nan_meaning": ("NaN = no clear pixel for that paddock on that date, OR the date "
                            "belongs to another tile in this chunk. n_clear distinguishes them: "
                            "n_clear == 0 with the date in the paddock's own tile means cloud."),
            "reflectance": "surface reflectance, scaled to 0-1 (raw DN / 10000)",
            "crs": "EPSG:3577 (polygons); values are zonal medians over eroded polygons",
        },
    )
    enc = {v: {"chunks": (min(n_pad, 512), min(nt, 128))} for v in list(data) + ["n_clear"]}
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    ds.to_zarr(path, mode="w", encoding=enc, consolidated=True)
    size = sum(os.path.getsize(os.path.join(dp, f))
               for dp, _, fs in os.walk(path) for f in fs)
    print(f"\nzarr: {n_pad} paddocks x {nt} scene-dates x {len(varnames)} variables "
          f"-> {path} ({size / 1e6:.1f} MB on disk)")
    return size


def shape_gate(long, ndvi_col, SG):
    """Peak-anchored green-up + post-harvest-senescence check, mirroring the DEPLOYABLE variant
    fitted in phenology_gate.py (see that module's docstring for why it is peak-anchored rather
    than sow/harv-anchored: no polygon here has a known planting or harvest date).

    Returns a bool Series indexed like `long`'s TrialCode groups (True = passes the gate).
    """
    thr = SG["thresholds"]
    pre_lo, pre_hi = SG["pre_window_days"]
    post_lo, post_hi = SG["post_window_days"]
    out = {}
    for tc, g in long.groupby("TrialCode"):
        d, v = g["time"], g[ndvi_col]
        if len(v) < 3 or not np.isfinite(v.max()) or v.max() <= 0:
            out[tc] = False
            continue
        peak = v.max()
        peak_date = d[v.idxmax()]
        pre = (d >= peak_date - pd.Timedelta(days=pre_lo)) & (d <= peak_date - pd.Timedelta(days=pre_hi))
        post = (d >= peak_date + pd.Timedelta(days=post_lo)) & (d <= peak_date + pd.Timedelta(days=post_hi))
        pre_val = v[pre].median() if pre.sum() >= 1 else np.nan
        post_val = v[post].median() if post.sum() >= 1 else np.nan
        greenup = (peak - pre_val) / peak if pd.notna(pre_val) else np.nan
        senesc = (peak - post_val) / peak if pd.notna(post_val) else np.nan
        out[tc] = bool(pd.notna(greenup) and greenup >= thr["greenup_rise"] and
                       pd.notna(senesc) and senesc >= thr["senescence_drop"])
    return pd.Series(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aois", required=True, help="csv with stub,lat,lon,half_m,start,end,year")
    ap.add_argument("--polydir", required=True, help="dir of <stub>_filt.gpkg")
    ap.add_argument("--max-missing-frac", type=float, default=0.10,
                    help="abort (non-zero exit) if more than this fraction of the AOIs have no "
                         "_filt.gpkg. Guards against predicting over ground that was never "
                         "segmented, which produces a partial map that looks complete and "
                         "exits 0 — 63 chunks of the first national run did exactly that.")
    ap.add_argument("--model", required=True, help="joblib from fit_map_model.py")
    ap.add_argument("--yield-model", default=None,
                    help="joblib from fit_yield_model.py. Adds a yield_tha column, filled only "
                         "for polygons whose predicted class matches the yield model's own "
                         "`crop` (e.g. a Cereal-yield model scores only pred == 'Cereal' rows).")
    ap.add_argument("--out", required=True, help="output GeoPackage")
    ap.add_argument("--erode-m", type=float, default=10.0)
    ap.add_argument("--min-obs", type=int, default=10)
    ap.add_argument("--min-clear-frac", type=float, default=0.5)
    ap.add_argument("--min-area-ha", type=float, default=5.0)
    # ---- the abstain path (output/PRESENCE_ONLY_LABELS.md) ----
    ap.add_argument("--max-area-ha", type=float, default=None,
                    help="SEGMENTABILITY AS A MASK. SAM returns a partition, and on ground with "
                         "no field boundaries — unimproved pasture — that partition is one blob "
                         "per tile. Measured: 63.9 %% of grazing paddocks land in a polygon over "
                         "300 ha against 5.8 %% of known crop paddocks. Setting this to 300 "
                         "turns that failure into a filter. It costs 22 %% of real crop "
                         "paddocks, so quote that with any coverage figure.")
    ap.add_argument("--crop-gate-amp", type=float, default=None,
                    help="CROP PRESENCE, NOT CROP ABSENCE. NDVI amplitude (p90-p10 of the "
                         "paddock median) below this and the polygon is left UNCLASSIFIED rather "
                         "than assigned a class. 0.35 is the Stage-2 operating point, fitted on "
                         "presence labels alone (held-out J = 0.535); 91.6 %% of known sown "
                         "crops clear it. Abstaining says 'no crop signature detected here', "
                         "which the labels support; naming a non-crop class is a claim they "
                         "do not.")
    ap.add_argument("--crop-gate-shape", default=None,
                    help="joblib from phenology_gate.py. A SEPARATE, STRICTER presence check: "
                         "peak-anchored green-up + post-harvest senescence, not just amplitude "
                         "(NEXT_STEPS.md #6.2 — amplitude alone cannot tell a real crop from "
                         "sown-but-not-harvested pasture, which greens up just as hard). NOT "
                         "validated against ABS area ratio yet, only against held-out NVT "
                         "presence recall (output/PHENOLOGY_GATE.md) — do not make this the "
                         "production default without that check. Stacks with --crop-gate-amp "
                         "if both are given; either failing sets abstain_reason.")
    ap.add_argument("--shape-gate-skip-classes", nargs="+", default=[],
                    help="EXPERIMENTAL, PHENOLOGY_GATE.md 'Next step' #2 (two-pass gating). "
                         "Predicted classes (e.g. Canola) exempted from --crop-gate-shape -- "
                         "they still need --crop-gate-amp, just not the stricter shape check. "
                         "Motivated by the shape gate's canola-specific recall shortfall "
                         "(83.4% vs cereal 95.1%/legume 95.5%, PHENOLOGY_GATE.md). No effect "
                         "unless --crop-gate-shape is also given.")
    ap.add_argument("--grid-touch-tol-m", type=float, default=10.0,
                    help="a polygon within this many metres of ITS OWN tile's edge is flagged "
                         "touches_grid=True (dist_to_grid_m carries the raw distance). Default "
                         "matches the 10m (one Sentinel-2 pixel) tolerance used throughout "
                         "PIPELINE_ARCHITECTURE_AND_TILING.md's boundary-split quantification "
                         "and polygon_stability.py's --grid-touch-tol-m. Computed against the "
                         "tile's INTENDED bounds (this row's lat/lon +/- half_m from --aois, "
                         "reprojected to EPSG:3577), not the downloaded composite's own bounds "
                         "-- the raster is padded some hundreds of metres past the true AOI "
                         "window, so measuring against it would flag the padding edge, not the "
                         "tile-to-tile abutment line a national mosaic actually cuts along. "
                         "Applies to EVERY polygon carried through, including abstained ones -- "
                         "this is a geometry fact about the tile, not a classification outcome.")
    ap.add_argument("--doy", nargs=2, type=int, default=[90, 350], metavar=("START", "END"),
                    help="read only this day-of-year window, overriding the AOI's start/end. "
                         "Defaults to the exact span `build_features` bins over, which is also "
                         "the span `extract_paddock.py` read for training (sow-30d to "
                         "harv+30d). Reading the whole calendar year instead costs ~28 %% more "
                         "datacube time for observations that are then binned away — and the "
                         "read is ~98 %% of this stage's runtime, so that is the whole bill.")
    ap.add_argument("--chm-dir", default="/scratch/xe2/cb8590/Global_Canopy_Height_v2")
    ap.add_argument("--no-tree-mask", action="store_true")
    ap.add_argument("--timings", help="append per-tile timings here (for the cost benchmark)")
    # ON BY DEFAULT (user decision 2026-09-08). The raw per-scene, per-paddock medians are
    # already computed in memory as the classifier's own intermediate -- `build_features` bins
    # them into DOY windows and the raw series is otherwise thrown away. Persisting it costs
    # only the write: `ZARR_BENCHMARK.md` measured 0.4-1.7 s/tile against a ~14 s/tile amortised
    # production baseline, and the two line items that dominated that benchmark's "extra" cost
    # (a second wider datacube read, and a 10-band zonal pass) are now BASELINE, because the
    # adopted shipped+sharma6 model reads ALL_BANDS for its own features.
    ap.add_argument("--no-zarr", action="store_true",
                    help="skip writing the per-scene paddock time series. The store is written "
                         "by default; this opts out.")
    ap.add_argument("--zarr-out", default=None,
                    help="path for the chunk's .zarr store (default: <out-dir>/../zarr/"
                         "<out-basename>.zarr)")
    args = ap.parse_args()

    os.environ.setdefault("PROJ_NETWORK", "OFF")
    import datacube
    import geopandas as gpd
    import joblib
    from pyproj import Transformer
    from rasterio.features import rasterize
    from train_species import build_features

    to_albers = Transformer.from_crs("EPSG:4326", "EPSG:3577", always_xy=True)

    B = joblib.load(args.model)
    clf, columns = B["model"], B["columns"]
    # `sources` (written by fit_map_model.py since 2026-09-08) lists every (kind, value_cols)
    # the model was fitted from -- the shipped+sharma6 classifier has two. Older single-source
    # bundles (group3_map.joblib, group4.joblib) carry only kind/value_cols; same thing, one entry.
    sources = [tuple(s) for s in (B.get("sources") or [(B["kind"], B["value_cols"])])]
    classes = list(clf.classes_)
    print(f"model: {B['target']}, sources {[k for k, _ in sources]}, {len(columns)} features, "
          f"classes {classes}")

    YB = joblib.load(args.yield_model) if args.yield_model else None
    if YB is not None:
        print(f"yield model: {YB['crop']}, {len(YB['columns'])} features, "
              f"trained on {YB['n_train']} paddocks, median {YB['yield_median']:.2f} t/ha")

    SG = joblib.load(args.crop_gate_shape) if args.crop_gate_shape else None
    if SG is not None:
        # phenology_gate.py's two save paths use different keys for the same number: the
        # --senescence-slack-pct ("loose") bundle writes held_out_recall_baseline, the plain
        # bundle writes held_out_recall. Log-line only -- read whichever is present rather than
        # crash on the print statement.
        recall = SG.get("held_out_recall", SG.get("held_out_recall_baseline"))
        print(f"shape gate: {SG['thresholds']}, held-out recall "
              f"{recall:.1%} on {SG['n_train']} NVT trials "
              f"(output/PHENOLOGY_GATE.md — NOT validated against ABS area ratio)")

    zarr_recs = []
    zarr_path = None
    if not args.no_zarr:
        # Fail NOW, not four hours into a chunk: a missing dependency on a default-on feature
        # must not surface after the datacube reads are already paid for.
        import zarr  # noqa: F401
        zarr_path = args.zarr_out or os.path.join(
            os.path.dirname(os.path.abspath(args.out)), "..", "zarr",
            os.path.splitext(os.path.basename(args.out))[0] + ".zarr")
        zarr_path = os.path.normpath(zarr_path)
        print(f"zarr: writing per-scene paddock time series to {zarr_path} "
              f"(disable with --no-zarr)")

    masker = None
    if not args.no_tree_mask:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "sentinel_ndvi"))
        from tree_mask import TreeMasker
        masker = TreeMasker(args.chm_dir)

    aois = pd.read_csv(args.aois)

    # CHECK THE INPUT EXISTS BEFORE SPENDING A SINGLE DATACUBE READ. `no polygons, skipped` in
    # the loop below is the correct response to one tile SAM could not segment, and it was the
    # wrong response to 307 of them: on the first national run 63 chunks were predicted over
    # ground that had never been segmented at all, each writing a plausible-looking GeoPackage
    # from the handful of tiles that did exist and exiting 0. `p316` classified 42 polygons from
    # 3 tiles of 310 in 2 min and reported "Done predict_tile".
    #
    # Up front rather than at the end, for two reasons: the job costs nothing when it aborts
    # early (the 63 wasted runs were ~0.15-0.35 SU each), and an output file that is never
    # created cannot be mistaken for a finished chunk by the `-s` guard in run_national.sh.
    have = sum(os.path.exists(os.path.join(args.polydir, f"{s}_filt.gpkg"))
               for s in aois["stub"])
    frac_missing = 1 - have / len(aois)
    if frac_missing > args.max_missing_frac:
        raise SystemExit(
            f"ABORT: only {have}/{len(aois)} tiles have a _filt.gpkg "
            f"({frac_missing:.0%} missing, above --max-missing-frac "
            f"{args.max_missing_frac:.0%}). The segmentation for this chunk did not run — "
            f"predicting now would write a partial map that looks complete. "
            f"Fix with `run_national.sh repair` / `repair-sam`, then re-predict.")
    if frac_missing:
        print(f"WARNING: {len(aois) - have}/{len(aois)} tiles have no polygons "
              f"({frac_missing:.0%})", flush=True)

    dc = datacube.Datacube(app="predict_tile")

    # ALL_BANDS is a superset of IDX_BANDS, so one read serves every source.
    measurements = ((ALL_BANDS if any(k == "bands" for k, _ in sources) else IDX_BANDS)
                    + ["oa_fmask"])
    out_parts = []

    for _, a in aois.iterrows():
        stub = a["stub"]
        p = os.path.join(args.polydir, f"{stub}_filt.gpkg")
        if not os.path.exists(p):
            print(f"{stub}: no polygons, skipped", flush=True)
            continue
        t0 = time.time()
        poly_all = gpd.read_file(p).to_crs("EPSG:3577")
        poly_all["area_ha"] = (poly_all.geometry.area / 1e4).round(2)
        # touches_grid / dist_to_grid_m: does THIS polygon sit within tolerance of ITS OWN
        # tile's edge, i.e. is it a candidate for having been cut by the tile grid rather than
        # by a real paddock boundary. Every polygon gets this (abstained ones too) — it is a
        # geometry fact about the tile, not a classification outcome, and it stays a plain
        # attribute here: nothing is filtered or merged across tiles on the strength of it.
        cx, cy = to_albers.transform(a["lon"], a["lat"])
        half_m = a["half_m"]
        pb = poly_all.geometry.bounds
        dx = np.minimum(np.abs(pb.minx - (cx - half_m)), np.abs(pb.maxx - (cx + half_m)))
        dy = np.minimum(np.abs(pb.miny - (cy - half_m)), np.abs(pb.maxy - (cy + half_m)))
        poly_all["dist_to_grid_m"] = np.minimum(dx, dy).round(1)
        poly_all["touches_grid"] = poly_all["dist_to_grid_m"] <= args.grid_touch_tol_m
        # EVERY polygon is carried to the output, with the reason it was not classified. A
        # polygon dropped here is white space on the map, and white space that cannot be
        # attributed to a cause is indistinguishable from ground with no crop on it — which is
        # exactly the confusion this whole reframe exists to remove.
        poly_all["abstain_reason"] = ""
        small = poly_all.area_ha < args.min_area_ha
        poly_all.loc[small, "abstain_reason"] = "area_below_min"
        if args.max_area_ha:
            big = poly_all.area_ha > args.max_area_ha
            poly_all.loc[big, "abstain_reason"] = "unsegmented_blob"
        poly = poly_all[poly_all.abstain_reason == ""].reset_index(drop=True)
        if poly.empty:
            print(f"{stub}: {len(poly_all)} polygons, none of usable size", flush=True)
            out_parts.append(poly_all.assign(stub=stub,
                                             year=int(a["year"]) if "year" in a else -1))
            continue

        b = poly.total_bounds
        year = int(a["year"]) if "year" in a else pd.to_datetime(a["start"]).year
        # Named `date0/date1`, not `t0/t1`: those are the wall-clock stamps this loop times
        # itself with, and shadowing them turned every tile into a TypeError.
        date0 = (pd.Timestamp(year=year, month=1, day=1) +
                 pd.Timedelta(days=args.doy[0] - 1)).strftime("%Y-%m-%d")
        date1 = (pd.Timestamp(year=year, month=1, day=1) +
                 pd.Timedelta(days=args.doy[1] - 1)).strftime("%Y-%m-%d")
        ds = dc.load(product=PRODUCTS, x=(b[0], b[2]), y=(b[1], b[3]), crs="EPSG:3577",
                     time=(date0, date1), measurements=measurements,
                     output_crs="EPSG:3577", resolution=(-10, 10), group_by="solar_day")
        if ds.sizes.get("time", 0) == 0:
            print(f"{stub}: no scenes", flush=True)
            continue
        t_read = time.time() - t0

        t1 = time.time()
        tr = ds.geobox.transform
        shape = (ds.sizes["y"], ds.sizes["x"])
        eroded = poly.geometry.buffer(-args.erode_m)
        # A polygon narrower than 2x the erosion vanishes; fall back to its raw shape rather
        # than dropping it silently, matching extract_paddock.py's `+noerode` case.
        eroded = gpd.GeoSeries([g if (not g.is_empty and g.area > 0) else r
                                for g, r in zip(eroded, poly.geometry)], crs=poly.crs)
        # `rasterize` paints later shapes over earlier ones, so a pixel shared by two touching
        # polygons is assigned to exactly one — no polygon can borrow another's pixels.
        labels = rasterize(((g, i) for i, g in enumerate(eroded)), out_shape=shape,
                           transform=tr, fill=-1, dtype="int32", all_touched=False)

        treed = np.zeros(len(poly), np.float32)
        if masker is not None:
            bb = ds.geobox.extent.boundingbox
            pad_deg = max(bb.right - bb.left, bb.top - bb.bottom) / 111_320.0 + 0.004
            cen = poly.to_crs("EPSG:4326").geometry.unary_union.centroid
            tree, tstats = masker.mask_for_geobox(ds.geobox, cen.x, cen.y, pad_deg=pad_deg)
            if tstats.get("chm_covered"):
                for i in range(len(poly)):
                    m = labels == i
                    tot = int(m.sum())
                    treed[i] = (int((m & tree).sum()) / tot) if tot else np.nan
                labels = np.where(tree, -1, labels)
            else:
                treed[:] = np.nan

        n_poly = len(poly)
        # ONE ZONAL PASS PER SOURCE, JOINED EXACTLY AS TRAINING JOINED THEM. A model fitted from
        # --indices AND --bands (the shipped+sharma6 classifier: NDVI/NDYI/CFI per-pixel-then-
        # median from IDX_BANDS, plus Sharma et al. 2026's six derived from ALL_BANDS medians)
        # carries columns suffixed "@indices"/"@bands" by train_species.py / fit_map_model.py.
        # Before 2026-09-08 this ran a single (kind, value_cols) pass and reindexed onto
        # `columns`: for a two-source model every column of the missing source came back NaN,
        # which HGB accepts without complaint, so the tile would have been classified from a
        # half-empty matrix with no error anywhere -- the "confident nonsense" fit_map_model.py's
        # docstring warns about. Per-source frames are kept UNSUFFIXED in `F_raw_plain` for the
        # yield model and the gates, which were trained on single-source column names.
        times = pd.to_datetime(ds["time"].values)
        parts_plain, long_gate, gate_cols = {}, None, None
        n_clear = n_px = pi0 = None
        raw_by_kind = {}
        for s_kind, s_cols in sources:
            vals, s_clear, s_px = zonal_medians(ds, labels, n_poly, s_cols, s_kind)
            raw_by_kind[s_kind] = (vals, s_cols)
            keep_obs = (s_clear / np.maximum(s_px, 1)[:, None]) >= args.min_clear_frac
            pi, ti = np.nonzero(keep_obs)
            if pi.size == 0:
                break
            if n_clear is None:
                n_clear, n_px, pi0 = s_clear, s_px, pi   # same fmask/labels for every source
            long_s = pd.DataFrame({"TrialCode": pi, "time": times[ti]})
            for j, c in enumerate(s_cols):
                long_s[c] = vals[pi, ti, j]
            if long_gate is None and any("ndvi" in c for c in s_cols):
                long_gate, gate_cols = long_s, s_cols
            # Long form, so the SAME `build_features` the model was trained with does the
            # binning. Rebuilding the pivot here would be a second implementation of the
            # feature contract and the two would drift.
            parts_plain[s_kind] = build_features(long_s, s_cols, False, None, B.get("bin_step"))
        t_zonal = time.time() - t1
        if len(parts_plain) < len(sources):
            print(f"{stub}: no polygon-dates clear enough", flush=True)
            continue
        pi = pi0
        frames = list(parts_plain.values())
        F_raw_plain = frames[0] if len(frames) == 1 else frames[0].join(frames[1:], how="inner")
        if len(sources) > 1:
            suffixed = [f.add_suffix(f"@{k}") for k, f in parts_plain.items()]
            F_raw = suffixed[0].join(suffixed[1:], how="inner")
        else:
            F_raw = F_raw_plain
        F = F_raw.reindex(columns=columns)
        n_obs = pd.Series(pi).value_counts()
        ok = F.index[F.index.map(n_obs).fillna(0) >= args.min_obs]
        F = F.loc[ok]
        if F.empty:
            print(f"{stub}: no polygon has {args.min_obs} clear observations", flush=True)
            poly["abstain_reason"] = "too_few_observations"
            out_parts.append(poly.assign(stub=stub, year=year))
            continue

        # NDVI amplitude per polygon, from the same long form the features are built from, so
        # the gate sees exactly the series the classifier does.
        amp = None
        ndvi_col = next((c for c in (gate_cols or []) if "ndvi" in c), None)
        if args.crop_gate_amp is not None and ndvi_col:
            q = long_gate.groupby("TrialCode")[ndvi_col].quantile([0.1, 0.9]).unstack()
            amp = (q[0.9] - q[0.1])

        shape_pass = None
        if SG is not None and ndvi_col:
            shape_pass = shape_gate(long_gate, ndvi_col, SG)

        proba = clf.predict_proba(F.values)
        pred = np.array(classes)[proba.argmax(axis=1)].astype(object)

        g = poly.loc[F.index].copy()
        # The polygon's row number in its own `_filt.gpkg`. Carried so the predictions can be
        # joined EXACTLY to `polygon_stability.py`'s table, which is keyed the same way — a
        # spatial re-join would be approximate on precisely the wobbling boundaries the
        # stability analysis is about.
        g["poly_idx"] = F.index.values
        g["stub"] = stub
        g["year"] = year
        g["area_ha"] = (g.geometry.area / 1e4).round(2)
        g["compactness"] = (g.geometry.length / np.sqrt(g.geometry.area)).round(3)
        if amp is not None:
            g["ndvi_amp"] = amp.reindex(F.index).round(3).values
            fails = g.ndvi_amp.fillna(0) < args.crop_gate_amp
            # The class probabilities are still written for an abstained polygon. They are what a
            # reviewer needs to see to judge whether the gate threw away something real, and
            # deleting them would make the gate unauditable.
            g.loc[fails, "abstain_reason"] = "no_crop_signal"
            pred = np.where(fails.values, None, pred)
        if shape_pass is not None:
            # `abstain_reason` always reflects the RAW shape-check outcome, regardless of
            # --shape-gate-skip-classes -- a skipped class's failure is still recorded and
            # therefore still filterable downstream. Only whether `pred` gets NULLED is
            # controlled by the skip list, via a separate boolean below.
            #
            # THE BUG THIS FIXES. Before 2026-09-07 these were the SAME boolean: an exempt
            # class's shape-gate failure was excluded from `fails_shape` before either the
            # abstain_reason write OR the pred-nulling, so it left literally no trace --
            # neither a null pred nor an abstain_reason to filter on later. That was fine for
            # Canola (permanently exempt, always shipped as classified, by design), but it
            # silently breaks "predict every class, mask out gate failures afterward" for any
            # OTHER class added to the skip list: there would be nothing left to mask against.
            fails_shape_raw = ~shape_pass.reindex(F.index).fillna(False).values
            # Do not overwrite an existing reason (area/amplitude already explains the abstain).
            blank = g["abstain_reason"] == ""
            g.loc[blank & fails_shape_raw, "abstain_reason"] = "no_crop_shape"
            fails_shape_null = fails_shape_raw
            if args.shape_gate_skip_classes:
                # Two-pass gating (PHENOLOGY_GATE.md 'Next step' #2): a polygon already
                # classified into an exempt class (by amplitude-gated argmax, above) keeps its
                # `pred` even when it fails the shape check -- `pred` still holds that class
                # here, since only fails/amp have touched it so far. The abstain_reason set
                # above still marks the failure, so a downstream reader can still filter it out;
                # only the class label itself is preserved rather than discarded.
                exempt = np.isin(pred.astype(object), args.shape_gate_skip_classes)
                fails_shape_null = fails_shape_raw & ~exempt
            pred = np.where(fails_shape_null, None, pred)
        g["pred"] = pred
        g["confidence"] = proba.max(axis=1).round(4)
        for k, c in enumerate(classes):
            g[f"p_{c.lower()}"] = proba[:, k].round(4)
        g["n_obs"] = [int(n_obs.get(i, 0)) for i in F.index]
        g["clear_frac"] = np.round(
            (n_clear[F.index].sum(1) / np.maximum(n_px[F.index] * n_clear.shape[1], 1)), 3)
        g["treed_frac"] = np.round(treed[F.index], 3)
        g["n_feat_present"] = F.notna().sum(axis=1).values
        if YB is not None:
            # Only polygons the classifier actually called YB['crop'] get scored — an abstained
            # polygon has pred None, which never matches, so it is left NaN rather than guessed.
            is_target = (pred == YB["crop"])
            g["yield_tha"] = np.nan
            g["yield_tha_calibrated"] = np.nan
            if is_target.any():
                # Unsuffixed: the yield model was fitted from a single source, so its column
                # names carry no "@source" tag even when the classifier's do.
                Fy = F_raw_plain.reindex(columns=YB["columns"]).loc[F.index]
                raw = YB["model"].predict(Fy.values[is_target])
                # Raw is NVT-trial-equivalent yield, not commercial paddock yield (trial plots
                # under trial management out-yield the field around them). `calibration_factor`
                # is the measured NVT->ABS offset — see fit_yield_model.py and
                # output/YIELD_CALIBRATION.md. Both columns ship; never only the calibrated one.
                g.loc[is_target, "yield_tha"] = np.round(raw, 2)
                g.loc[is_target, "yield_tha_calibrated"] = np.round(
                    raw * YB.get("calibration_factor", 1.0), 2)
        out_parts.append(g)

        # The polygons that never reached the model, carried through with their reason.
        missed = poly.drop(index=F.index)
        if len(missed):
            missed = missed.copy()
            missed["abstain_reason"] = "too_few_observations"
            out_parts.append(missed.assign(stub=stub, year=year))
        if len(poly_all) > len(poly):
            rest = poly_all[poly_all.abstain_reason != ""].copy()
            out_parts.append(rest.assign(stub=stub, year=year))

        if zarr_path is not None:
            # The raw (paddock, scene) medians the classifier just built its DOY bins from.
            # Every variable here is already in memory: nothing is re-read or re-aggregated.
            zvars = {}
            for s_kind, (vals, s_cols) in raw_by_kind.items():
                for j, c in enumerate(s_cols):
                    zvars[c.replace("_pad_median", "")] = vals[:, :, j].astype("float32")
            if "bands" in raw_by_kind:
                bvals, bcols = raw_by_kind["bands"]
                zvars.update({k: v.astype("float32")
                              for k, v in sharma6_from_bands(bvals, list(bcols)).items()})
            zarr_recs.append({"stub": stub, "times": times,
                              "poly_idx": np.arange(n_poly, dtype="int32"),
                              "n_clear": n_clear, "n_px": n_px, "vars": zvars})

        dt = time.time() - t0
        share = pd.Series(pred).value_counts(normalize=True)
        print(f"{stub}: {len(g)}/{n_poly} polygons, {ds.sizes['time']} scenes, {dt:.0f}s "
              f"(read {t_read:.0f}s, zonal {t_zonal:.0f}s) | " +
              ", ".join(f"{c} {share.get(c, 0):.0%}" for c in classes), flush=True)
        if args.timings:
            row = {"stub": stub, "year": g.year.iloc[0], "n_poly": n_poly,
                   "n_scored": len(g), "n_scenes": int(ds.sizes["time"]),
                   "px": shape[0] * shape[1], "read_s": round(t_read, 1),
                   "zonal_s": round(t_zonal, 1), "total_s": round(dt, 1)}
            pd.DataFrame([row]).to_csv(args.timings, mode="a", index=False,
                                       header=not os.path.exists(args.timings))

    if not out_parts:
        raise SystemExit("nothing predicted")
    import geopandas as gpd
    P = gpd.GeoDataFrame(pd.concat(out_parts, ignore_index=True), crs="EPSG:3577")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    P.to_file(args.out, layer="paddocks", driver="GPKG")
    print(f"\n{len(P)} polygons over {P.stub.nunique()} tiles -> {args.out}")
    if zarr_path is not None and zarr_recs:
        write_chunk_zarr(zarr_path, zarr_recs,
                         f"{args.model} ({', '.join(k for k, _ in sources)})")
    print(P.groupby(["year", "pred"], dropna=False).agg(n=("pred", "size"),
                                                        ha=("area_ha", "sum")).round(0).to_string())
    if "abstain_reason" in P:
        cls = P.abstain_reason.fillna("") == ""
        print(f"\nCOVERAGE: {int(cls.sum())} of {len(P)} polygons classified "
              f"({100 * cls.mean():.1f} %), {P.loc[cls, 'area_ha'].sum() / P.area_ha.sum() * 100:.1f} % by area")
        print(P[~cls].abstain_reason.value_counts().to_string())
    if "yield_tha" in P.columns:
        yv = P["yield_tha"].dropna()
        yc = P["yield_tha_calibrated"].dropna()
        print(f"\nYIELD ({YB['crop']}): {len(yv)} polygons scored, "
              f"raw (NVT-equivalent) mean {yv.mean():.2f} t/ha, median {yv.median():.2f} t/ha")
        print(f"  calibrated (x{YB.get('calibration_factor', 1.0):.4f}, ABS-offset): "
              f"mean {yc.mean():.2f} t/ha, median {yc.median():.2f} t/ha")


if __name__ == "__main__":
    main()
