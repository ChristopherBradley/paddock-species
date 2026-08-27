#!/usr/bin/env python3
"""
Stage 1 of Sentinel-1: pull RTC backscatter per AOI from Microsoft Planetary Computer.

RUN THIS ON `copyq`, NOT `normal`. gadi compute nodes have no outbound internet; copyq and the
login node do. That forces the same two-stage split the S2 pipeline already uses — download to
/scratch here, compute paddock medians on `normal` in stage 2 (`s1_extract.py`).

WHY MPC. There is no Sentinel-1 in the DEA datacube (0 SAR products of 120) and
`/g/data/dz56/backscatter` is permission-denied for this account. MPC's `sentinel-1-rtc` is
already terrain-corrected, which a paddock median needs and which the GRD collection would
require a processing chain to reach.

MEASURED, not assumed (`s1_benchmark.py`, 8 AOIs sampled per year):

    scenes in the 3-month flowering window   median 7-11 across 2017-2024
    one AOI-season                           ~14 s, ~7 MB
    2,390 AOIs                               ~9 h wall, ~18 GB

**Coverage is not uniform.** Sentinel-1B failed in Dec 2021, and 4 of the 24 AOI-seasons
sampled from 2022-2024 returned fewer than 3 scenes — one returned 0. Those trials will carry
NaN S1 features, which the gradient booster handles natively; do NOT fill them, and do check
the per-year missing rate before reading anything into a 2023 result.

NDA NOTE. This sends an AOI BOUNDING BOX to Microsoft — no TrialCode, crop, date or yield.
The trial-level records the NDA covers never leave NCI.

Resumable: an AOI whose output already exists is skipped, so a walltime kill costs only the
AOI in flight.
"""
import argparse
import os
import time

import numpy as np
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aois", nargs="+", required=True, help="aois_*.csv file(s)")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--start-month", type=int, default=4, help="season start (inclusive)")
    ap.add_argument("--end-month", type=int, default=12, help="season end (exclusive)")
    ap.add_argument("--limit", type=int, default=0, help="stop after N AOIs (0 = all)")
    ap.add_argument("--shard", default="0/1",
                    help="I/N — take every Nth AOI starting at I, so N copyq jobs can run in "
                         "parallel without a shared chunk file and without racing each other "
                         "for the same output. Striding rather than blocking keeps each "
                         "shard's mix of years and box sizes representative, so they finish "
                         "at about the same time.")
    args = ap.parse_args()
    shard_i, shard_n = (int(v) for v in args.shard.split("/"))

    from pystac_client import Client
    from odc.stac import load
    from planetary_computer import sign_url
    from shapely.geometry import box

    os.makedirs(args.outdir, exist_ok=True)
    a = pd.concat((pd.read_csv(f) for f in args.aois), ignore_index=True) \
        .drop_duplicates("stub").sort_values("stub").reset_index(drop=True)
    total = len(a)
    a = a.iloc[shard_i::shard_n]
    print(f"{total} AOIs -> shard {shard_i}/{shard_n} = {len(a)}")
    client = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")

    done = fail = skip = 0
    t00 = time.time()
    for i, r in a.iterrows():
        out = os.path.join(args.outdir, f"{r.stub}_s1.nc")
        if os.path.exists(out):
            skip += 1
            continue
        if args.limit and done >= args.limit:
            break
        dlat = r.half_m / 111_320.0
        dlon = r.half_m / (111_320.0 * np.cos(np.radians(r.lat)))
        geom = box(r.lon - dlon, r.lat - dlat, r.lon + dlon, r.lat + dlat)
        y = int(r.year)
        window = f"{y}-{args.start_month:02d}-01/{y}-{args.end_month:02d}-01"
        try:
            items = client.search(collections=["sentinel-1-rtc"], intersects=geom,
                                  datetime=window).item_collection()
            if not len(items):
                # Recorded as an EMPTY file, not skipped: "no scenes" is a finding about S1
                # coverage that stage 2 needs to distinguish from "not downloaded yet".
                open(out + ".empty", "w").close()
                print(f"  {r.stub}: 0 scenes")
                done += 1
                continue
            ds = load(items, geopolygon=geom, measurements=["vv", "vh"],
                      groupby="solar_day", patch_url=sign_url,
                      chunks={"x": 2048, "y": 2048}, output_crs="epsg:3577",
                      resolution=10).compute()
            ds.to_netcdf(out)
            done += 1
            if done % 20 == 0:
                el = time.time() - t00
                print(f"[{done}] {r.stub} {len(items)} scenes | {el/done:.1f} s/AOI, "
                      f"{el/3600:.2f} h elapsed", flush=True)
        except Exception as e:                      # one bad AOI must not end the run
            fail += 1
            print(f"  FAIL {r.stub}: {type(e).__name__}: {e}", flush=True)

    print(f"\ndownloaded {done}, skipped {skip}, failed {fail} in "
          f"{(time.time()-t00)/3600:.2f} h -> {args.outdir}")


if __name__ == "__main__":
    main()
