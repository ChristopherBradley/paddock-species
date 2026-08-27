#!/usr/bin/env python3
"""
Benchmark ONE Sentinel-1 AOI from Microsoft Planetary Computer, to size the full run.

WHY MPC AND NOT THE DATACUBE. There is no Sentinel-1 in the DEA index — 0 SAR products of 120
— and the NCI backscatter collection at `/g/data/dz56/backscatter` is permission-denied for
this account (member of xe2, ka08, not dz56). MPC's `sentinel-1-rtc` collection is
terrain-corrected and analysis-ready, which is what a paddock median needs; the GRD collection
would require RTC processing first.

WHERE IT CAN RUN. gadi compute nodes have no outbound internet; the login node and `copyq` do.
So the download and the extraction must be separate stages — pull to /scratch on copyq, then
compute paddock medians on `normal`. That is the same two-stage shape as the existing
segmentation pipeline, for the same reason.

NDA NOTE. This sends an AOI BOUNDING BOX to Microsoft. It carries no TrialCode, crop, date or
yield — the trial-level records the NDA covers stay local. Flagged rather than assumed; this
script deliberately touches ONE box so the decision to run all 1,362 stays with the user.

Prints wall time, scene count and array size, which are the three numbers needed to decide
whether the full extraction is worth its SUs.
"""
import argparse
import time

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aois", required=True)
    ap.add_argument("--row", type=int, default=0, help="which AOI row to benchmark")
    ap.add_argument("--months", type=int, default=3,
                    help="months of the flowering season to pull for the benchmark")
    args = ap.parse_args()

    import pandas as pd
    from pystac_client import Client
    from odc.stac import load
    from planetary_computer import sign_url
    from shapely.geometry import box

    a = pd.read_csv(args.aois).iloc[args.row]
    # half_m is metres; convert to degrees for the STAC intersects query.
    dlat = a.half_m / 111_320.0
    dlon = a.half_m / (111_320.0 * np.cos(np.radians(a.lat)))
    geom = box(a.lon - dlon, a.lat - dlat, a.lon + dlon, a.lat + dlat)
    # The flowering window this project established, not the whole year: the benchmark should
    # measure the query the pipeline would actually issue.
    start = f"{int(a.year)}-07-01"
    end = f"{int(a.year)}-10-01" if args.months == 3 else f"{int(a.year)}-12-31"
    print(f"AOI stub={a.stub}  half_m={a.half_m:.0f}  year={int(a.year)}  "
          f"trials={a.n_trials}")
    print(f"box {2*a.half_m/1000:.1f} km, window {start}..{end}")

    t0 = time.time()
    client = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    items = client.search(collections=["sentinel-1-rtc"], intersects=geom,
                          datetime=f"{start}/{end}").item_collection()
    t_search = time.time() - t0
    print(f"\nsearch: {len(items)} scenes in {t_search:.1f} s")
    if not len(items):
        print("NO SCENES — check the collection name or the date window")
        return

    t1 = time.time()
    data = load(items, geopolygon=geom, measurements=["vv", "vh"], groupby="solar_day",
                patch_url=sign_url, chunks={"x": 2048, "y": 2048},
                output_crs="epsg:3577", resolution=10).compute()
    t_load = time.time() - t1
    nbytes = sum(v.nbytes for v in data.data_vars.values())
    print(f"load: {dict(data.sizes)} in {t_load:.1f} s")
    print(f"      {nbytes/1e6:.1f} MB in memory, "
          f"{100*float(np.isfinite(data.vv).mean()):.1f} % finite vv")
    print(f"\nTOTAL {time.time()-t0:.1f} s for one AOI-season")
    n_aoi = 1362
    print(f"EXTRAPOLATION over {n_aoi} AOIs: "
          f"{(time.time()-t0)*n_aoi/3600:.1f} h wall, {nbytes*n_aoi/1e9:.0f} GB")
    print("copyq bills walltime x 1 CPU, so that is roughly the SU cost of stage 1.")


if __name__ == "__main__":
    main()
