#!/usr/bin/env python3
"""
Split each AOI in a csv into an NxN grid of smaller AOIs covering EXACTLY the same ground.

WHY. The 9 km and 3 km benchmarks were run on different tiles in different landscapes — one
set included rangeland where SAM returns a single whole-tile blob — so the apparent per-km²
advantage of large tiles confounds tile size with where the tiles happen to be. Segmenting the
same ground at both sizes removes that: the only thing that varies is the tile edge.

The comparison this enables is not only cost. A 3 km tile has 1.33 km of edge per km² against
0.44 for a 9 km tile, so it truncates ~3x as many paddocks against a boundary; polygons per km²
and median polygon area are the measurements that show whether that matters.

    python3 subtile_aois.py --aois aois_bench9km.csv --n 3 --out aois_bench3km_matched.csv
"""
import argparse

import pandas as pd
from pyproj import Transformer

ALBERS = "EPSG:3577"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aois", required=True)
    ap.add_argument("--n", type=int, default=3, help="split each AOI into n x n")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    src = pd.read_csv(args.aois)
    to_alb = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)
    to_wgs = Transformer.from_crs(ALBERS, "EPSG:4326", always_xy=True)

    rows = []
    for _, r in src.iterrows():
        x, y = to_alb.transform(float(r.lon), float(r.lat))
        half = float(r.half_m) / args.n            # child half-width
        # Child centres on the parent's grid: offsets are odd multiples of the child half-width
        # about the parent centre, which tiles the parent exactly with no gap and no overlap.
        off = [(2 * i - (args.n - 1)) * half for i in range(args.n)]
        for iy, dy in enumerate(off):
            for ix, dx in enumerate(off):
                lon, lat = to_wgs.transform(x + dx, y + dy)
                rows.append({"stub": f"{r.stub}_s{iy}{ix}",
                             "lat": round(lat, 6), "lon": round(lon, 6),
                             "half_m": int(half), "start": r.start, "end": r.end,
                             "year": r.year, "n_trials": 0, "parent": r.stub})
    d = pd.DataFrame(rows)
    d.to_csv(args.out, index=False)
    print(f"{len(src)} AOIs at half_m={src.half_m.iloc[0]:g} -> {len(d)} sub-AOIs at "
          f"half_m={d.half_m.iloc[0]} ({args.n}x{args.n}) -> {args.out}")


if __name__ == "__main__":
    main()
