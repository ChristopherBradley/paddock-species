#!/usr/bin/env python
"""
make_aois.py -- AOI lists for the KSU / tile-size / overlap benchmark (output/BENCH_KSU.md).

One Riverina block on the production 3 km lattice, chosen so every tile has a 2024 composite,
segmentation and prediction (so production is the reference at zero cost):
  ch36        6x6 children (3 km, half 1500)            reference, nothing to run
  ov1750      same 36 centres, half 1750 (3.5 km tiles, 500 m overlap each side)
  ov2000      same 36 centres, half 2000 (4 km tiles, 1 km overlap)
  p9          4 parents of 9 km (half 4500)
  p18         1 tile of 18 km (half 9000)
  sam100      10x10 children, composites exist         SAM throughput arms
  ps2021_60   10x6 children relabelled to 2021          presegment queue arms (no composites exist)
  pr2022_40   8x5 children, 2022                        predict queue arms (segmented, unpredicted)
"""
import argparse
import os

import numpy as np
import pandas as pd
from pyproj import Transformer

D = "/scratch/xe2/cb8590/paddock-species-data/derived"
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--r0", type=int, default=930)
ap.add_argument("--c0", type=int, default=1182)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
A = pd.read_csv(f"{D}/national2024/aois.csv")
A = A[(A.grid_r.between(925, 950)) & (A.grid_c.between(1176, 1200))]
key = {(r, c): row for r, c, row in zip(A.grid_r, A.grid_c, A.to_dict("records"))}
S24, S22 = f"{D}/national2024/samgeo", f"{D}/national2022/samgeo"


def present(r, c, year):
    row = key.get((r, c))
    if row is None:
        return False
    stub = row["stub"] if year == 2024 else row["stub"].replace("2024", str(year))
    d = S24 if year == 2024 else S22
    return os.path.exists(f"{d}/{stub}.tif") and os.path.exists(f"{d}/{stub}_filt.gpkg")


# find a 10x10 block with everything present for 2024 and the 8x5 corner present for 2022
found = None
for r0 in range(a.r0, a.r0 + 10):
    for c0 in range(a.c0, a.c0 + 10):
        if all(present(r0 + i, c0 + j, 2024) for i in range(10) for j in range(10)) and \
           all(present(r0 + i, c0 + j, 2022) for i in range(8) for j in range(5)):
            found = (r0, c0); break
    if found:
        break
if not found:
    raise SystemExit("no fully present 10x10 block found; widen the search")
r0, c0 = found
print("block origin grid_r, grid_c =", r0, c0)
rows = lambda ri, ci: pd.DataFrame([key[(r0 + i, c0 + j)] for i in ri for j in ci])

ch36 = rows(range(6), range(6))
ch36.to_csv(f"{a.out}/ch36.csv", index=False)
for half in (1750, 2000):
    v = ch36.copy(); v["half_m"] = half
    v["stub"] = [f"ov{half}_2024_r{r}_c{c}" for r, c in zip(v.grid_r, v.grid_c)]
    v.to_csv(f"{a.out}/ov{half}.csv", index=False)
to_alb = Transformer.from_crs("EPSG:4326", "EPSG:3577", always_xy=True)
to_ll = Transformer.from_crs("EPSG:3577", "EPSG:4326", always_xy=True)


def parent(df, stub, half):
    x, y = to_alb.transform(df.lon.values, df.lat.values)
    lon, lat = to_ll.transform(float(x.mean()), float(y.mean()))
    return dict(stub=stub, lat=lat, lon=lon, half_m=half, start="2024-01-01", end="2024-12-31",
                year=2024, n_trials=0, grid_r=int(df.grid_r.min()), grid_c=int(df.grid_c.min()),
                block_r=int(df.block_r.iloc[0]), block_c=int(df.block_c.iloc[0]))


p9 = pd.DataFrame([parent(rows(range(3 * i, 3 * i + 3), range(3 * j, 3 * j + 3)),
                          f"p9_2024_r{r0 + 3 * i + 1}_c{c0 + 3 * j + 1}", 4500) for i in range(2) for j in range(2)])
p9.to_csv(f"{a.out}/p9.csv", index=False)
pd.DataFrame([parent(ch36, "p18_2024", 9000)]).to_csv(f"{a.out}/p18.csv", index=False)
rows(range(10), range(10)).to_csv(f"{a.out}/sam100.csv", index=False)
ps = rows(range(10), range(6)).copy()
ps["stub"] = ps.stub.str.replace("2024", "2021"); ps["start"] = "2021-01-01"; ps["end"] = "2021-12-31"; ps["year"] = 2021
ps.to_csv(f"{a.out}/ps2021_60.csv", index=False)
pr = rows(range(8), range(5)).copy()
pr["stub"] = pr.stub.str.replace("2024", "2022"); pr["start"] = "2022-01-01"; pr["end"] = "2022-12-31"; pr["year"] = 2022
pr.to_csv(f"{a.out}/pr2022_40.csv", index=False)
for f in ["ch36", "ov1750", "ov2000", "p9", "p18", "sam100", "ps2021_60", "pr2022_40"]:
    d = pd.read_csv(f"{a.out}/{f}.csv"); print(f"{f}: {len(d)} rows, half_m {sorted(d.half_m.unique())}, e.g. {d.stub.iloc[0]}")
