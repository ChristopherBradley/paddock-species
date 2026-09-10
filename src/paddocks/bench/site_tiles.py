#!/usr/bin/env python
"""
site_tiles.py -- the 3 km tiles and 9 km parents that contain the 543 fixed test trials (2023-24).
Writes SENSITIVE per-site lookups and per-year AOI lists for both products under --out (derived only).
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
from pyproj import Transformer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
from merge_tile_boundaries import Lattice  # noqa: E402

D = "/scratch/xe2/cb8590/paddock-species-data/derived"
ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--half9", type=float, default=4850.0); a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
t = pd.read_csv(f"{D}/keep_arms/testkeep_temporal_SENSITIVE.csv")
L = pd.read_csv(f"{D}/labels_combined_sam_SENSITIVE.csv")[["TrialCode", "Year", "lat", "lon", "crop", "area_ha"]]
S = t[["TrialCode", "Year", "crop", "label", "paddock_ha"]].merge(L, on=["TrialCode", "Year", "crop"], how="left")
# the trial paddock area: labels_combined has area_ha for only 669 of 5148 rows (none of the test
# trials); the reviewed test set carries it as paddock_ha, so prefer that.
S["area_ha"] = S.paddock_ha.where(S.paddock_ha.notna(), S.area_ha)
assert S.lat.notna().all(), "unmatched test trials"
to_alb = Transformer.from_crs("EPSG:4326", "EPSG:3577", always_xy=True); to_ll = Transformer.from_crs("EPSG:3577", "EPSG:4326", always_xy=True)
S["x"], S["y"] = to_alb.transform(S.lon.values, S.lat.values)
lat24 = Lattice(f"{D}/national2024/aois.csv")
kx, ky = lat24.k_from_xy(S.x.values, S.y.values); inv = {v: k for k, v in lat24.stub_k.items()}
S["stub3_2024"] = [inv.get((int(a_), int(b_))) for a_, b_ in zip(kx, ky)]
A24 = pd.read_csv(f"{D}/national2024/aois.csv").set_index("stub")
S["grid_r"] = [A24.grid_r.get(s) if s else None for s in S.stub3_2024]; S["grid_c"] = [A24.grid_c.get(s) if s else None for s in S.stub3_2024]
S["R"], S["C"] = S.grid_r // 3, S.grid_c // 3
print("test sites", len(S), "| without a 2024 lattice tile:", int(S.stub3_2024.isna().sum()))
S = S[S.stub3_2024.notna()].copy()
xx, yy = to_alb.transform(A24.lon.values, A24.lat.values); A24["x"], A24["y"] = xx, yy; A24["R"], A24["C"] = A24.grid_r // 3, A24.grid_c // 3
for year in (2023, 2024):
    Ay = pd.read_csv(f"{D}/national{year}/aois.csv").set_index("stub")
    sy = S[S.Year == year]
    stubs3 = sorted({s.replace("2024", str(year)) for s in sy.stub3_2024})
    rows3 = Ay.loc[[s for s in stubs3 if s in Ay.index]].reset_index()
    seg = [os.path.exists(f"{D}/national{year}/samgeo/{s}_filt.gpkg") for s in rows3.stub]
    rows3.to_csv(f"{a.out}/aois3_{year}.csv", index=False)
    print(f"{year}: {len(sy)} sites -> {len(rows3)} 3 km tiles ({sum(seg)} segmented)")
    parents = []
    for (R, C), g in A24[A24.set_index(["R", "C"]).index.isin(list(zip(sy.R, sy.C)))].groupby(["R", "C"]):
        lon, lat = to_ll.transform(float(g.x.mean()), float(g.y.mean()))
        parents.append(dict(stub=f"nlum9_{year}_r{R}_c{C}", lat=lat, lon=lon, half_m=a.half9, start=f"{year}-01-01", end=f"{year}-12-31", year=year,
                            n_trials=int(((sy.R == R) & (sy.C == C)).sum()), grid_r=int(R), grid_c=int(C), block_r=int(g.block_r.iloc[0]), block_c=int(g.block_c.iloc[0]), n_children=len(g)))
    P = pd.DataFrame(parents).sort_values(["block_r", "block_c", "grid_r", "grid_c"]); P.to_csv(f"{a.out}/aois9_{year}.csv", index=False)
    print(f"{year}: {len(P)} 9 km parents (children per parent median {P.n_children.median():.0f})")
S["stub9"] = [f"nlum9_{y}_r{int(R)}_c{int(C)}" for y, R, C in zip(S.Year, S.R, S.C)]
S["stub3"] = [s.replace("2024", str(y)) for s, y in zip(S.stub3_2024, S.Year)]
S.to_csv(f"{a.out}/sites_SENSITIVE.csv", index=False); print("wrote", f"{a.out}/sites_SENSITIVE.csv")
