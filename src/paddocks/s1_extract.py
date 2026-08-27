#!/usr/bin/env python3
"""
Stage 2 of Sentinel-1: paddock-median VV/VH time series from the downloaded RTC cubes.

Runs on `normal` (no internet needed — stage 1 already pulled everything to /scratch).

DELIBERATELY MIRRORS THE S2 PIPELINE so the two feature sets describe the same ground:
  * the SAME chosen polygon per trial, taken from the review package by `poly_id`
  * the SAME 10 m erosion, so a boundary pixel mixing the neighbouring field is excluded
  * a MEDIAN over the polygon, not a mean — speckle is multiplicative and heavy-tailed, so a
    mean is dragged by bright scatterers in a way a median is not. This matters more for SAR
    than it did for optical.

THREE MEASUREMENTS, because the ratio is the informative one. VV and VH both scale with
incidence angle and moisture; VH/VV largely does not, and it is the channel that responds to
canopy STRUCTURE — which is the whole reason to want S1 here. Cereals (vertical stems) and
pulses (broad leaves, bushy) differ in depolarisation in a way CFI cannot see, and Legume is
the class this project cannot separate.

dB, not linear power. Backscatter is log-normal; a median in dB is the median in linear space
too, but every downstream mean, difference and gradient behaves far better in dB.

Output matches the S2 time-series schema (`TrialCode,time,...`) so `train_species.py` can read
it with the existing `--indices`-style loader.

SENSITIVE: keyed by TrialCode.
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--s1dir", required=True, help="directory of <stub>_s1.nc from stage 1")
    ap.add_argument("--review-gpkg", required=True)
    ap.add_argument("--review-sites", nargs="+", required=True,
                    help="review_sites.csv file(s), for the TrialCode -> aoi_stub map")
    ap.add_argument("--reviewed", required=True, help="reviewed_trials_SENSITIVE.csv")
    ap.add_argument("--out", required=True)
    ap.add_argument("--erode-m", type=float, default=10.0)
    ap.add_argument("--min-px", type=int, default=10)
    args = ap.parse_args()

    import geopandas as gpd
    import xarray as xr
    from rasterio.features import geometry_mask
    from rasterio.transform import from_origin

    rev = pd.read_csv(args.reviewed)
    good = set(rev.loc[rev.usable.astype(bool), "TrialCode"])
    T = gpd.read_file(args.review_gpkg, layer="trials").to_crs("EPSG:3577")
    R = gpd.read_file(args.review_gpkg, layer="review").to_crs("EPSG:3577")
    geom_by_poly = dict(zip(R.poly_id, R.geometry))
    rs = pd.concat((pd.read_csv(f) for f in args.review_sites), ignore_index=True)
    stub_of = dict(zip(rs.TrialCode, rs.aoi_stub))

    T = T[T.TrialCode.isin(good)].copy()
    T["stub"] = T.TrialCode.map(stub_of)
    T = T[T.stub.notna()]
    print(f"{len(T)} reviewed-good trials across {T.stub.nunique()} AOIs")

    rows, n_missing, n_empty = [], 0, 0
    for stub, grp in T.groupby("stub"):
        f = os.path.join(args.s1dir, f"{stub}_s1.nc")
        if not os.path.exists(f):
            # An AOI recorded as having no scenes is a COVERAGE finding, not a gap in this
            # stage; either way its trials simply get no S1 rows and the booster sees NaN.
            n_missing += 1
            continue
        try:
            ds = xr.open_dataset(f)
        except Exception as e:
            print(f"  unreadable {stub}: {e}")
            n_missing += 1
            continue
        xs, ys = ds.x.values, ds.y.values
        if len(xs) < 2 or len(ys) < 2:
            n_empty += 1
            continue
        res = float(abs(xs[1] - xs[0]))
        tr = from_origin(xs[0] - res / 2, ys[0] + res / 2, res, res)
        shape = (len(ys), len(xs))
        vv = ds["vv"].values
        vh = ds["vh"].values
        times = pd.to_datetime(ds.time.values)

        for r in grp.itertuples():
            g = geom_by_poly.get(r.poly_id)
            if g is None:
                continue
            e = g.buffer(-args.erode_m)
            if e.is_empty or e.area <= 0:
                e = g
            m = ~geometry_mask([e], out_shape=shape, transform=tr, invert=False)
            if m.sum() < args.min_px:
                continue
            for i, t in enumerate(times):
                a, b = vv[i][m], vh[i][m]
                ok = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
                if ok.sum() < args.min_px:
                    continue
                # dB after masking non-positive linear values: RTC can emit zeros in layover
                # and shadow, and log(0) would poison the median for the whole paddock.
                vv_db = 10 * np.log10(a[ok])
                vh_db = 10 * np.log10(b[ok])
                rows.append({
                    "TrialCode": r.TrialCode, "time": t,
                    "vv_pad_median": float(np.median(vv_db)),
                    "vh_pad_median": float(np.median(vh_db)),
                    "vhvv_pad_median": float(np.median(vh_db - vv_db)),
                    "n_px_paddock": int(m.sum()), "n_clear_px": int(ok.sum()),
                    "paddock_ha": float(g.area / 1e4),
                })
        ds.close()

    out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"\n{len(out)} trial-dates for {out.TrialCode.nunique() if len(out) else 0} trials")
    print(f"  AOIs with no S1 file: {n_missing}, empty cubes: {n_empty}")
    if len(out):
        print(f"  scenes per trial: median "
              f"{out.groupby('TrialCode').size().median():.0f}")
        print(out[["vv_pad_median", "vh_pad_median", "vhvv_pad_median"]].describe().round(2)
              .loc[["mean", "min", "max"]].to_string())
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
