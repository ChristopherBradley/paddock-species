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
`n_feat_present`). The probabilities are not decoration: every operating-point result in this
project — canola at 5 % FPR, the precision/recall trade — is unrecoverable from a hard label,
and a national product cannot be hand-reviewed, so the fields the hand review used have to
travel with the data instead.
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
    args = ap.parse_args()

    os.environ.setdefault("PROJ_NETWORK", "OFF")
    import datacube
    import geopandas as gpd
    import joblib
    from rasterio.features import rasterize
    from train_species import build_features

    B = joblib.load(args.model)
    clf, columns, value_cols, kind = B["model"], B["columns"], B["value_cols"], B["kind"]
    classes = list(clf.classes_)
    print(f"model: {B['target']}, {kind}, {len(columns)} features, classes {classes}")

    YB = joblib.load(args.yield_model) if args.yield_model else None
    if YB is not None:
        print(f"yield model: {YB['crop']}, {len(YB['columns'])} features, "
              f"trained on {YB['n_train']} paddocks, median {YB['yield_median']:.2f} t/ha")

    SG = joblib.load(args.crop_gate_shape) if args.crop_gate_shape else None
    if SG is not None:
        print(f"shape gate: {SG['thresholds']}, held-out recall "
              f"{SG['held_out_recall']:.1%} on {SG['n_train']} NVT trials "
              f"(output/PHENOLOGY_GATE.md — NOT validated against ABS area ratio)")

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

    measurements = ((ALL_BANDS if kind == "bands" else IDX_BANDS) + ["oa_fmask"])
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
        vals, n_clear, n_px = zonal_medians(ds, labels, n_poly, value_cols, kind)
        t_zonal = time.time() - t1

        # Long form, so the SAME `build_features` the model was trained with does the binning.
        # Rebuilding the pivot here would be a second implementation of the feature contract
        # and the two would drift.
        times = pd.to_datetime(ds["time"].values)
        keep_obs = (n_clear / np.maximum(n_px, 1)[:, None]) >= args.min_clear_frac
        pi, ti = np.nonzero(keep_obs)
        if pi.size == 0:
            print(f"{stub}: no polygon-dates clear enough", flush=True)
            continue
        long = pd.DataFrame({"TrialCode": pi, "time": times[ti]})
        for j, c in enumerate(value_cols):
            long[c] = vals[pi, ti, j]

        F_raw = build_features(long, value_cols, False, None, B.get("bin_step"))
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
        ndvi_col = next((c for c in value_cols if "ndvi" in c), None)
        if args.crop_gate_amp is not None and ndvi_col:
            q = long.groupby("TrialCode")[ndvi_col].quantile([0.1, 0.9]).unstack()
            amp = (q[0.9] - q[0.1])

        shape_pass = None
        if SG is not None and ndvi_col:
            shape_pass = shape_gate(long, ndvi_col, SG)

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
            fails_shape = ~shape_pass.reindex(F.index).fillna(False).values
            # Do not overwrite an existing reason (area/amplitude already explains the abstain).
            blank = g["abstain_reason"] == ""
            g.loc[blank & fails_shape, "abstain_reason"] = "no_crop_shape"
            pred = np.where(fails_shape, None, pred)
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
                Fy = F_raw.reindex(columns=YB["columns"]).loc[F.index]
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
