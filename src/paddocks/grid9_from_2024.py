#!/usr/bin/env python
"""
grid9_from_2024.py -- a 9 km national tile grid from the 2024 3 km aois.csv (TILE_GEOMETRY_DECISION.md).

Each 9 km parent is the 3 x 3 block of 3 km children with grid_r // 3 and grid_c // 3 in common
(the same children the pipeline already knows); its centre is the mean of the children's centres
in EPSG:3577 (so a coastal parent with fewer than 9 children is centred on the children it has),
half_m 4500, dates and year copied. Stubs: nlum9_<year>_r<R>_c<C> with R, C the parent indices.
"""
import argparse

import numpy as np
import pandas as pd
from pyproj import Transformer

ap = argparse.ArgumentParser()
ap.add_argument("--aois-2024", required=True)
ap.add_argument("--year", type=int, default=2024)
ap.add_argument("--out", required=True)
a = ap.parse_args()
A = pd.read_csv(a.aois_2024)
to_alb = Transformer.from_crs("EPSG:4326", "EPSG:3577", always_xy=True)
to_ll = Transformer.from_crs("EPSG:3577", "EPSG:4326", always_xy=True)
x, y = to_alb.transform(A.lon.values, A.lat.values)
A["x"], A["y"] = x, y
A["R"], A["C"] = A.grid_r // 3, A.grid_c // 3
rows = []
for (R, C), g in A.groupby(["R", "C"]):
    lon, lat = to_ll.transform(float(g.x.mean()), float(g.y.mean()))
    rows.append(dict(stub=f"nlum9_{a.year}_r{R}_c{C}", lat=lat, lon=lon, half_m=4500,
                     start=f"{a.year}-01-01", end=f"{a.year}-12-31", year=a.year, n_trials=int(g.n_trials.sum()),
                     grid_r=int(R), grid_c=int(C), block_r=int(g.block_r.iloc[0]), block_c=int(g.block_c.iloc[0]),
                     n_children=len(g)))
out = pd.DataFrame(rows).sort_values(["block_r", "block_c", "grid_r", "grid_c"])
out.to_csv(a.out, index=False)
print(f"{len(out)} parents from {len(A)} children; children per parent: {out.n_children.value_counts().sort_index().to_dict()}")
