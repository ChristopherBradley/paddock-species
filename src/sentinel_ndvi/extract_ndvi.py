#!/usr/bin/env python3
"""
Stage 2 (gadi/DEA): extract a Sentinel-2 index time series for each candidate NVT trial,
to confirm the surrounding paddock actually grew the trial crop.

Runs on NCI gadi inside the DEA module environment:
    module use /g/data/v10/public/modules/modulefiles
    module load dea/20231204
    python3 extract_ndvi.py --chunk <chunk.csv> --outdir <dir> [--window-m 200]

Input chunk CSV columns (subset of derived/nvt_trials_labeled.csv):
    TrialCode, Year, crop, lat, lon, sow, harv

Output: one long-form CSV per chunk in <outdir>, one row per trial per clear date:
    TrialCode, crop, sow, time,
    n_clear_px, n_px_total, n_px_window, n_tree_masked_px,
    ndvi_win_mean, ndvi_win_std, ndvi_corner,
    ndyi_win_mean, ndyi_corner,            # legacy, superseded by CFI
    cfi_win_mean, cfi_corner,              # Canola Flower Index — the discriminator
    red/green/blue/nir_win_mean            # raw bands, so new indices need no re-extraction

TREE MASKING (on by default, --chm-dir '' to disable). The 200 m window is centred on a
paddock CORNER, so it routinely catches tree lines, paddock trees and roadside vegetation.
Those pixels are green year-round and never flower, diluting the flowering signal. Any 10 m
pixel overlapping a >1 m canopy pixel (Global Canopy Height v2, 1 m) is dropped, along with
one ring of neighbours to absorb geolocation offset between the two products.
`n_px_total` is the count of USABLE (non-tree) pixels, so the downstream clear-fraction
filter compares like with like; `n_px_window` and `n_tree_masked_px` record what was removed.

`n_clear_px / n_px_total` is the clear fraction; partially-cloudy scenes are kept here
and filtered downstream in phenology_check.py (see --min-clear-frac).
Failures are recorded (status=FAILED) — never fabricated.
"""
import argparse
import os
import signal
import sys
import threading
import time
import traceback

import numpy as np
import pandas as pd
import xarray as xr

# DEA Sentinel-2 Analysis Ready Data (surface reflectance), all three platforms
PRODUCTS = ["ga_s2am_ard_3", "ga_s2bm_ard_3", "ga_s2cm_ard_3"]
BANDS = ["nbart_blue", "nbart_green", "nbart_red", "nbart_nir_1", "oa_fmask"]
NODATA = -999
FMASK_CLEAR = 1  # 0 nodata,1 valid,2 cloud,3 shadow,4 snow,5 water
REFL_SCALE = 10000.0  # DEA nbart int16 DN -> 0-1 surface reflectance


class TrialTimeout(Exception):
    """A single trial exceeded --trial-timeout."""


def _on_alarm(signum, frame):
    raise TrialTimeout("exceeded --trial-timeout")


# SIGALRM alone is NOT a sufficient watchdog here. Python runs signal handlers only when
# the interpreter regains control, and C libraries (curl, libpq, GDAL) restart their poll
# loops on EINTR — so a hang inside them swallows the alarm entirely. That is exactly how
# jobs sat blocked for 4 h on 2026-08-06/07 with the alarm armed and never firing.
# This thread is the hard backstop: the GIL is released during blocking I/O, so it still
# runs while the main thread is stuck, and it force-exits the process.
_last_progress = time.time()
_progress_lock = threading.Lock()


def _mark_progress():
    global _last_progress
    with _progress_lock:
        _last_progress = time.time()


def _start_watchdog(limit_s, chunk_name):
    def run():
        while True:
            time.sleep(15)
            with _progress_lock:
                idle = time.time() - _last_progress
            if idle > limit_s:
                print(f"WATCHDOG {chunk_name}: no trial completed in {idle:.0f}s "
                      f"(limit {limit_s}s) — main thread is stuck in native code. "
                      f"Force-exiting; per-trial results already on disk. Rerun to resume.",
                      file=sys.stderr, flush=True)
                os._exit(75)  # results are appended+closed per trial, so nothing is lost
    threading.Thread(target=run, daemon=True).start()


def _transformer():
    from pyproj import Transformer
    return Transformer.from_crs("EPSG:4326", "EPSG:3577", always_xy=True)


def load_trial(dc, lat, lon, t0, t1, window_m):
    half = window_m / 2.0
    dlat = half / 111320.0
    dlon = half / (111320.0 * np.cos(np.radians(lat)))
    ds = dc.load(
        product=PRODUCTS,
        x=(lon - dlon, lon + dlon),
        y=(lat - dlat, lat + dlat),
        crs="EPSG:4326",
        time=(t0, t1),
        measurements=BANDS,
        output_crs="EPSG:3577",
        resolution=(-10, 10),
        group_by="solar_day",
    )
    return ds


def compute_indices(ds, tree_mask=None):
    """Return per-pixel index/band DataArrays (cloud-masked) plus the clear-pixel count.

    Reflectance is rescaled to 0-1. NDVI/NDYI are ratios so the scale cancels, but CFI is
    NOT a ratio — it is linear in reflectance, so its magnitude depends on this choice.
    PaddockTS applies the formula to raw DN; multiply CFI by REFL_SCALE to compare against
    values from that code. Separability and threshold *ranking* are unaffected either way,
    since the two differ by a constant factor.

    `tree_mask` (True = drop) is folded into the clear mask, so trees are excluded from
    every statistic AND from the clear-pixel count. That matters: if trees were dropped
    from the numerator only, a heavily-treed window would look permanently cloudy and be
    discarded downstream by the clear-fraction filter.
    """
    clear = ds["oa_fmask"] == FMASK_CLEAR
    if tree_mask is not None:
        keep = xr.DataArray(~tree_mask, dims=("y", "x"),
                            coords={"y": ds["y"], "x": ds["x"]})
        clear = clear & keep
    b = {}
    for name in ("nbart_blue", "nbart_green", "nbart_red", "nbart_nir_1"):
        arr = ds[name].where((ds[name] != NODATA) & clear)
        b[name] = arr.astype("float32") / REFL_SCALE
    red, green, blue, nir = (b["nbart_red"], b["nbart_green"],
                             b["nbart_blue"], b["nbart_nir_1"])
    ndvi = (nir - red) / (nir + red)
    ndyi = (green - blue) / (green + blue)
    # Canola Flower Index, Tian et al. 2022 (Remote Sensing), as implemented in
    # PaddockTS Code/indices_etc/indices.py:  CFI = NDVI * ((Red + Green) + (Green - Blue))
    # The NDVI factor is the point: it suppresses bare/senescent soil, which is bright in
    # the visible bands and was inflating the plain-NDYI yellowness signal on wheat sites.
    cfi = ndvi * ((red + green) + (green - blue))
    n_clear = clear.sum(dim=("x", "y"))
    return {"ndvi": ndvi, "ndyi": ndyi, "cfi": cfi,
            "red": red, "green": green, "blue": blue, "nir": nir}, n_clear


def trial_timeseries(dc, row, window_m, masker=None):
    lat, lon = float(row["lat"]), float(row["lon"])
    t0 = (pd.to_datetime(row["sow"]) - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    t1 = (pd.to_datetime(row["harv"]) + pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    ds = load_trial(dc, lat, lon, t0, t1, window_m)
    if ds.sizes.get("time", 0) == 0:
        return pd.DataFrame()
    n_window = int(ds.sizes["x"] * ds.sizes["y"])
    tree_mask, n_masked = None, 0
    if masker is not None:
        tree_mask, _st = masker.mask_for_geobox(ds.geobox, lon, lat)
        n_masked = int(tree_mask.sum())
        if n_masked >= n_window:          # window is entirely tree — nothing to measure
            return pd.DataFrame()
    idx, n_clear = compute_indices(ds, tree_mask)
    cx, cy = _transformer().transform(lon, lat)
    cols = {
        "TrialCode": row["TrialCode"],
        "crop": row["crop"],
        # Carried through so downstream can define the flowering window per trial without
        # re-joining the (sensitive) labelled table. CFI peaks again during senescence, so
        # an unrestricted seasonal max picks the wrong event — the window is load-bearing.
        "sow": pd.to_datetime(row["sow"]).date().isoformat(),
        "time": pd.to_datetime(idx["ndvi"]["time"].values),
        "n_clear_px": n_clear.values.astype(int),
        # n_px_total is the count of USABLE (non-tree) pixels, so the downstream
        # clear-fraction filter compares like with like. Full window size and the number of
        # tree-masked pixels are kept separately for transparency.
        "n_px_total": n_window - n_masked,
        "n_px_window": n_window,
        "n_tree_masked_px": n_masked,
    }
    for name in ("ndvi", "ndyi", "cfi"):
        cols[f"{name}_win_mean"] = idx[name].mean(dim=("x", "y")).values
        cols[f"{name}_corner"] = idx[name].sel(x=cx, y=cy, method="nearest").values
    cols["ndvi_win_std"] = idx["ndvi"].std(dim=("x", "y")).values
    # Raw band means (0-1 reflectance) so any further index — NIRv, NDTI, a revised CFI —
    # can be derived later without re-running the extraction. Cheap insurance: this rerun
    # exists only because the first pass stored indices but not the bands behind them.
    for name in ("red", "green", "blue", "nir"):
        cols[f"{name}_win_mean"] = idx[name].mean(dim=("x", "y")).values
    out = pd.DataFrame(cols)
    # drop fully-cloudy dates
    return out[out["n_clear_px"] > 0].reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", required=True, help="CSV of trials to process")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--window-m", type=float, default=200.0)
    ap.add_argument("--trial-timeout", type=int, default=300,
                    help="seconds before a single trial is abandoned as FAILED "
                         "(normal is ~30 s; a blocked DEA index query hangs forever)")
    ap.add_argument("--max-consecutive-timeouts", type=int, default=5,
                    help="abort the job after this many timeouts in a row — the index DB "
                         "is down or its connection pool is exhausted, so continuing just "
                         "burns walltime and hammers a shared service")
    ap.add_argument("--chm-dir", default="/scratch/xe2/cb8590/Global_Canopy_Height_v2",
                    help="1 m Global Canopy Height v2 quadkey tiles; '' disables tree masking")
    ap.add_argument("--tree-height-min", type=float, default=1.0,
                    help="canopy height (m) above which a 1 m pixel counts as tree")
    ap.add_argument("--tree-dilate", type=int, default=1,
                    help="also drop N rings of pixels around each tree pixel, to absorb "
                         "geolocation offset between the canopy product and Sentinel-2")
    ap.add_argument("--stall-timeout", type=int, default=900,
                    help="force-exit if no trial completes in this many seconds (hard "
                         "backstop for hangs inside native code, which SIGALRM cannot "
                         "interrupt)")
    args = ap.parse_args()

    # PROJ grid downloads from cdn.proj.org hang forever on gadi compute nodes (no outbound
    # internet). extract_ndvi.pbs exports this too; set it here so interactive runs and any
    # other caller are protected regardless of how they were launched.
    os.environ.setdefault("PROJ_NETWORK", "OFF")

    signal.signal(signal.SIGALRM, _on_alarm)

    import datacube
    # Pre-flight: if the shared index is unreachable, say so in seconds instead of
    # discovering it one 300 s trial timeout at a time.
    signal.alarm(60)
    try:
        dc = datacube.Datacube(app="paddock_s2_extract")
        dc.list_products()
    except TrialTimeout:
        print("ABORT: DEA index did not respond within 60 s at startup — pool exhausted or "
              "down. Not starting; rerun to resume.", file=sys.stderr, flush=True)
        sys.exit(75)
    finally:
        signal.alarm(0)

    masker = None
    if args.chm_dir:
        from tree_mask import TreeMasker
        masker = TreeMasker(args.chm_dir, args.tree_height_min, args.tree_dilate)
        print(f"tree masking ON: >{args.tree_height_min} m, +{args.tree_dilate} px, "
              f"{len(masker._have)} tiles", flush=True)

    trials = pd.read_csv(args.chunk)
    os.makedirs(args.outdir, exist_ok=True)
    chunk_name = os.path.splitext(os.path.basename(args.chunk))[0]
    out_csv = os.path.join(args.outdir, f"{chunk_name}_ts.csv")
    log_csv = os.path.join(args.outdir, f"{chunk_name}_status.csv")

    # Results are appended per trial rather than held in memory and written at the end:
    # a walltime overrun or crash then costs only the trial in flight, not the whole chunk,
    # and the status file doubles as a live progress signal (PBS only stages .o/.e logs
    # back when the job exits). Re-running the same chunk resumes where it stopped.
    # Only OK/EMPTY count as done. FAILED is retried on resume — most failures here are
    # transient (a blocked index query timing out), and silently inheriting them would turn
    # an outage into permanent missing data. The status file is rewritten without those rows
    # so it never accumulates duplicates and stays a truthful count of trials completed
    # (extract_ndvi.sh uses that count to decide whether a chunk is finished).
    done = set()
    if os.path.exists(log_csv):
        prev = pd.read_csv(log_csv)
        keep = prev[prev["status"].isin(["OK", "EMPTY"])]
        done = set(keep["TrialCode"].astype(str))
        n_retry = len(prev) - len(keep)
        keep.to_csv(log_csv, index=False)
        print(f"resuming {chunk_name}: {len(done)} done, retrying {n_retry} previously FAILED",
              flush=True)

    def append(path, frame):
        frame.to_csv(path, mode="a", header=not os.path.exists(path), index=False)

    _mark_progress()
    _start_watchdog(args.stall_timeout, chunk_name)

    n_ok = n_empty = n_failed = 0
    consecutive_timeouts = 0
    aborted = False
    for _, row in trials.iterrows():
        tc = str(row["TrialCode"])
        if tc in done:
            continue
        try:
            signal.alarm(args.trial_timeout)      # watchdog: never block forever
            try:
                df = trial_timeseries(dc, row, args.window_m, masker)
            finally:
                signal.alarm(0)
            if df.empty:
                st, note, n_empty = "EMPTY", "", n_empty + 1
            else:
                append(out_csv, df)
                st, note, n_ok = "OK", f"{len(df)} obs", n_ok + 1
            consecutive_timeouts = 0
            print(f"{tc}: {st} {note}", flush=True)
        except TrialTimeout as e:
            st, note = "FAILED", f"TIMEOUT after {args.trial_timeout}s"
            n_failed += 1
            consecutive_timeouts += 1
            print(f"{tc}: FAILED {note}", file=sys.stderr, flush=True)
        except Exception as e:  # noqa: BLE001
            st, note, n_failed = "FAILED", repr(e), n_failed + 1
            consecutive_timeouts = 0
            print(f"{tc}: FAILED {e}", file=sys.stderr, flush=True)
            traceback.print_exc()
        append(log_csv, pd.DataFrame([(tc, st, note)],
                                     columns=["TrialCode", "status", "note"]))
        _mark_progress()

        if consecutive_timeouts >= args.max_consecutive_timeouts:
            print(f"ABORT {chunk_name}: {consecutive_timeouts} consecutive timeouts — the "
                  f"DEA index is unreachable or its connection pool is exhausted. Stopping "
                  f"rather than burning walltime; rerun to resume.", file=sys.stderr,
                  flush=True)
            aborted = True
            break

    print(f"{chunk_name}: OK={n_ok} EMPTY={n_empty} FAILED={n_failed}"
          f"{' ABORTED' if aborted else ''} -> {out_csv}")
    if aborted:
        sys.exit(75)  # EX_TEMPFAIL: transient, safe to resubmit


if __name__ == "__main__":
    main()
