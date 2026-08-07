#!/usr/bin/env python3
"""
Group trial sites into segmentation AOIs, sized to the trials they actually contain.

The benchmark AOI was a fixed 0.1 deg box (~11 km) because that is what PaddockTS uses.
That is wasteful here: the median 0.1 deg cell holds only **2** trials, and both the
datacube read and SAM scale with area, so most of that box is segmented for nothing.
This sizes each AOI to its trials' bounding box plus a margin, which is the single
biggest cost lever in the pipeline (an 11 km box is ~13x the area of a 3 km one).

Segmentation is season-specific, so the unit is (cell, year), not (cell).

    python3 make_aois.py --trials .../nvt_trials_labeled.csv --out .../aois.csv \
        --crops Canola Wheat --margin-m 1500

Writes two files:
  * <out>            — one row per AOI: stub, lat, lon, half_m, start, end, n_trials
  * <out>.sites.csv  — one row per trial, with the AOI stub it belongs to

Both contain site coordinates ⇒ SENSITIVE, keep on /scratch, never commit.
"""
import argparse
import os

import numpy as np
import pandas as pd

# Degrees per metre at the equator; longitude is corrected by cos(lat) at use.
M_PER_DEG = 111_320.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--crops", nargs="*", default=None, help="default: all crops")
    ap.add_argument("--years", nargs="*", type=int, default=None)
    ap.add_argument("--cell-deg", type=float, default=0.1,
                    help="grouping cell; trials in the same cell+year share one AOI")
    ap.add_argument("--margin-m", type=float, default=1500.0,
                    help="margin around the trial bounding box. Must exceed the largest "
                         "plausible paddock radius or a trial's paddock gets clipped.")
    ap.add_argument("--max-half-m", type=float, default=5500.0,
                    help="cap on AOI half-width, so one stray cell cannot blow up the cost")
    args = ap.parse_args()

    d = pd.read_csv(args.trials)
    if args.crops:
        d = d[d.crop.isin(args.crops)]
    if args.years:
        d = d[d.Year.isin(args.years)]
    if d.empty:
        raise SystemExit("no trials left after filtering")

    d = d.copy()
    d["gx"] = (d.lon / args.cell_deg).round().astype(int)
    d["gy"] = (d.lat / args.cell_deg).round().astype(int)

    rows, site_rows = [], []
    for (year, gx, gy), g in d.groupby(["Year", "gx", "gy"]):
        lat_c = float(g.lat.mean())
        lon_c = float(g.lon.mean())
        # Half-width that covers every trial in the group, plus the margin. Longitude
        # degrees shrink with latitude, so convert with cos(lat) rather than assuming square.
        dy_m = (g.lat.max() - g.lat.min()) / 2 * M_PER_DEG
        dx_m = (g.lon.max() - g.lon.min()) / 2 * M_PER_DEG * np.cos(np.radians(lat_c))
        half_m = min(max(dy_m, dx_m) + args.margin_m, args.max_half_m)
        stub = f"aoi_{year}_{gx:+05d}_{gy:+05d}".replace("+", "p").replace("-", "m")
        rows.append({
            "stub": stub, "lat": round(lat_c, 6), "lon": round(lon_c, 6),
            "half_m": round(float(half_m)),
            # A full calendar year: the Fourier-of-NDWI composite needs the whole season,
            # and this matches the benchmarked configuration.
            "start": f"{year}-01-01", "end": f"{year}-12-31",
            "year": int(year), "n_trials": len(g),
        })
        for _, r in g.iterrows():
            site_rows.append({**r.to_dict(), "aoi_stub": stub})

    aois = pd.DataFrame(rows).sort_values(["year", "stub"])
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    aois.to_csv(args.out, index=False)
    pd.DataFrame(site_rows).to_csv(args.out + ".sites.csv", index=False)

    area = (2 * aois.half_m / 1000.0) ** 2
    ref = 11.0 ** 2      # the benchmarked 0.1 deg box
    print(f"{len(d)} trials -> {len(aois)} AOIs ({aois.n_trials.median():.0f} trials each, "
          f"max {aois.n_trials.max()})")
    print(f"AOI width km: median {2*aois.half_m.median()/1000:.1f}, "
          f"p90 {2*aois.half_m.quantile(.9)/1000:.1f}, max {2*aois.half_m.max()/1000:.1f}")
    print(f"total area {area.sum():.0f} km^2 vs {len(aois)*ref:.0f} km^2 for fixed 11 km boxes "
          f"=> {len(aois)*ref/area.sum():.1f}x less area to segment")
    print(f"-> {args.out}")
    print(f"-> {args.out}.sites.csv")


if __name__ == "__main__":
    main()
