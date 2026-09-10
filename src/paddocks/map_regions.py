#!/usr/bin/env python3
"""
Pick demonstration regions for a wall-to-wall map, and lay the production tile grid over them.

WHY NLUM PICKS THE REGIONS AND NOT A HUMAN. "Somewhere with a lot of canola" has to be defined
before it can be defended, and NLUM's own expected areas are trustworthy at aggregate scale
(summing probability x pixel area reproduces the national statistics to within a few percent —
`NATIONAL_INFERENCE_BENCHMARK.md` §1). So a region is chosen as a block whose NLUM canola
probability is high AND which also carries cereal and legume, because a block that is purely
one crop demonstrates nothing about a classifier whose whole difficulty is telling them apart.
NLUM is the sampling frame here, never the label and never the yardstick.

REGIONS ARE FORCED APART, one per state and a minimum separation besides. Three blocks from the
same district would share a season, a soil and a rainfall decile, and three maps that agree
would be one result reported three times.

THE TILE IS 3 km AND THAT IS NOT A COST KNOB. `samgeo`'s fixed 512 px window makes tile size a
segmentation hyperparameter, not a partition of the same work: 9 km tiles returned 23 % fewer
and 29 % larger polygons on identical ground (`TILE_SIZE_BENCHMARK.md`). So a demonstration
region is tiled at the production size and the region is whatever an integer grid of those
covers — a 4x4 grid is 12 x 12 km, which contains the 10 x 10 km asked for rather than
approximating it by shrinking the tile.

    python3 map_regions.py --nlum-dir DIR --out regions.csv --aois-out aois.csv \
        --years 2020 2021 2022 2023 2024 --n 3
"""
import argparse
import os

import numpy as np
import pandas as pd

ALBERS = "EPSG:3577"
CANOLA = "NLUM_v7_probSurf_2021_334_10_W_OILSEEDS.tif"
CEREAL = "NLUM_v7_probSurf_2021_331_5_W_CER.tif"
LEGUME = "NLUM_v7_probSurf_2021_338_8_W_LEGUMES.tif"
# Rough state boxes, only ever used to name and spread the demonstration regions apart.
# Nothing downstream reads them as an authority on where a border is.
STATES = [("WA", 112.0, 129.0, -36.0, -26.0), ("SA", 129.0, 141.0, -38.5, -30.0),
          ("QLD", 138.0, 154.0, -29.5, -20.0)]


def state_of(lon, lat):
    for s, x0, x1, y0, y1 in STATES:
        if x0 <= lon < x1 and y0 <= lat < y1:
            return s
    if 141.0 <= lon < 154.0 and -39.5 <= lat < -28.0:
        # The Vic/NSW border is the Murray, not a parallel: a box put the Riverina (lon 147.2,
        # lat -34.7) in Victoria, which is ~150 km wrong. Approximate the river as a line from
        # -34.0 at the SA corner to -36.0 near Albury; south of it is Victoria.
        return "VIC" if lat < -34.0 - 2.0 * (lon - 141.0) / 7.0 else "NSW"
    return "??"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nlum-dir", required=True)
    ap.add_argument("--out", required=True, help="regions csv (one row per region)")
    ap.add_argument("--aois-out", required=True, help="tile AOI csv for the segmentation")
    ap.add_argument("--years", nargs="+", type=int,
                    default=[2020, 2021, 2022, 2023, 2024])
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--grid", type=int, default=4, help="tiles per side")
    ap.add_argument("--half-m", type=float, default=1500.0, help="tile half-width; 3 km tiles")
    ap.add_argument("--min-cereal", type=float, default=0.15)
    ap.add_argument("--min-legume", type=float, default=0.02)
    ap.add_argument("--min-sep-km", type=float, default=150.0)
    ap.add_argument("--centre", nargs=2, type=float, metavar=("LON", "LAT"),
                    help="pin the region here instead of letting NLUM choose. The NLUM search "
                         "exists so that 'somewhere with a lot of canola' is defensible rather "
                         "than hand-picked, and that principle still holds for choosing a NEW "
                         "region. It does not hold for CONTINUING one: re-scoring at a larger "
                         "block size moves the winning cell, and a time series that changes "
                         "location between runs is not a time series. Use this to extend a "
                         "region that NLUM already picked, and record which run picked it.")
    ap.add_argument("--region-name", default=None, help="name for --centre; defaults to state")
    ap.add_argument("--offset-seed", type=int, default=None,
                    help="PROTOTYPE, opt-in (default off, reproduces exactly today's fixed grid "
                         "when omitted). Draws an independent (dx, dy) per year, uniform over "
                         "[-half_m, half_m) in both axes -- one full tile width, so every "
                         "possible grid alignment is reachable -- and shifts that year's whole "
                         "tile grid by it before laying out cells. Purpose: on the FIXED grid "
                         "every year cuts a boundary-straddling paddock at the exact same place "
                         "(PIPELINE_ARCHITECTURE_AND_TILING.md section 5, 6.99-10.25% of "
                         "national polygons within 10-15m of a grid line, every year identically "
                         "-- there is no year in which the paddock is ever whole, so no amount of "
                         "cross-year voting can recover it). An independent offset per year makes "
                         "the cut fall in a DIFFERENT place each year, so a given paddock is only "
                         "cut in the minority of years and whole in the rest -- recoverable by "
                         "consensus, if polygon_stability.py's matching also stops assuming the "
                         "same (region, cell) label is the same ground across years (it does not, "
                         "once this is set -- see --spatial-match there).")
    args = ap.parse_args()

    import rasterio
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    from pyproj import Transformer

    block = 2 * args.half_m * args.grid          # the region edge, in metres

    if args.centre:
        # A PINNED REGION NEEDS NO SEARCH, AND THEREFORE NO NATIONAL REPROJECTION. Coarsening
        # three 250 m national rasters to the block size takes ~15 minutes and exists only to
        # RANK candidate blocks. When the block is already chosen, the NLUM probabilities are
        # provenance, not a decision, so read them from a small window at the centre instead.
        lon, lat = args.centre
        fwd = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)
        x, y = fwd.transform(lon, lat)

        def at_centre(fname):
            """Mean NLUM probability over the block, read as a window.

            The window comes from the block's CORNERS transformed into the raster's own CRS,
            never from `block / transform.a`: NLUM is stored in degrees, so dividing metres by a
            degree-valued pixel size asks for a 46-million-pixel window and a 3.8 PiB
            allocation. Units have to be converted, not assumed."""
            with rasterio.open(os.path.join(args.nlum_dir, fname)) as src:
                to_src = Transformer.from_crs(ALBERS, src.crs, always_xy=True)
                xs, ys = zip(*[to_src.transform(x + dx, y + dy)
                               for dx in (-block / 2, block / 2)
                               for dy in (-block / 2, block / 2)])
                w = rasterio.windows.from_bounds(min(xs), min(ys), max(xs), max(ys),
                                                 transform=src.transform)
                a = src.read(1, window=w, boundless=True, fill_value=0).astype(np.float32)
                a = np.where(a == src.nodata, 0.0, a) / 1e4
            return float(a.mean())

        st = state_of(lon, lat)
        picked = [{"region": args.region_name or f"{st.lower()}_c", "state": st,
                   "x": x, "y": y, "lon": round(lon, 6), "lat": round(lat, 6),
                   "canola_prob": round(at_centre(CANOLA), 4),
                   "cereal_prob": round(at_centre(CEREAL), 4),
                   "legume_prob": round(at_centre(LEGUME), 4),
                   "edge_km": block / 1000}]
        R = pd.DataFrame(picked).drop(columns=["x", "y"])
        R.to_csv(args.out, index=False)
        print(f"pinned region -> {args.out}")
        print(R.to_string(index=False))
        write_aois(args, picked, Transformer.from_crs(ALBERS, "EPSG:4326", always_xy=True))
        return

    with rasterio.open(os.path.join(args.nlum_dir, CANOLA)) as s:
        tr, W, H = calculate_default_transform(s.crs, ALBERS, s.width, s.height,
                                               *s.bounds, resolution=block)

    def coarse(fname):
        with rasterio.open(os.path.join(args.nlum_dir, fname)) as s:
            a = s.read(1).astype(np.float32)
            a = np.where(a == s.nodata, 0.0, a) / 1e4
            out = np.zeros((H, W), np.float32)
            reproject(a, out, src_transform=s.transform, src_crs=s.crs,
                      dst_transform=tr, dst_crs=ALBERS, resampling=Resampling.average)
        return out

    can, cer, leg = coarse(CANOLA), coarse(CEREAL), coarse(LEGUME)
    print(f"region grid {W}x{H} at {block/1000:g} km blocks")

    elig = (cer >= args.min_cereal) & (leg >= args.min_legume)
    print(f"blocks with cereal >={args.min_cereal} and legume >={args.min_legume}: "
          f"{int(elig.sum()):,}")
    score = np.where(elig, can, -1.0)

    to_wgs = Transformer.from_crs(ALBERS, "EPSG:4326", always_xy=True)

    order = np.argsort(score, axis=None)[::-1]
    picked, seen_states = [], set()
    for flat in order:
        if len(picked) >= args.n:
            break
        r, c = np.unravel_index(flat, score.shape)
        if score[r, c] <= 0:
            break
        x = tr.c + (c + 0.5) * tr.a
        y = tr.f + (r + 0.5) * tr.e
        if any(np.hypot(x - p["x"], y - p["y"]) < args.min_sep_km * 1000 for p in picked):
            continue
        lon, lat = to_wgs.transform(x, y)
        st = state_of(lon, lat)
        # One region per state, so three maps are three independent demonstrations rather
        # than one district reported three times.
        if st in seen_states:
            continue
        seen_states.add(st)
        picked.append({"region": f"{st.lower()}_{len(picked)}", "state": st,
                       "x": x, "y": y, "lon": round(lon, 6), "lat": round(lat, 6),
                       "canola_prob": round(float(can[r, c]), 4),
                       "cereal_prob": round(float(cer[r, c]), 4),
                       "legume_prob": round(float(leg[r, c]), 4),
                       "edge_km": block / 1000})
    if not picked:
        raise SystemExit("no eligible blocks — loosen --min-cereal/--min-legume")
    R = pd.DataFrame(picked).drop(columns=["x", "y"])
    R.to_csv(args.out, index=False)
    print(f"\n{len(R)} regions -> {args.out}")
    print(R.to_string(index=False))
    write_aois(args, picked, to_wgs)


def write_aois(args, picked, to_wgs):
    """Lay the production tile grid over each picked region and write the AOI csv."""
    rows = []
    g, hm = args.grid, args.half_m
    for p in picked:
        # Tile centres on an integer grid about the block centre, in Albers metres, so every
        # tile is a true 3 km square and the grid does not shear with latitude.
        offs = (np.arange(g) - (g - 1) / 2) * 2 * hm
        for yr in args.years:
            # --offset-seed: shift THIS YEAR's whole grid by an independent (ox, oy) before
            # laying out cells, so different years cut a boundary-straddling paddock in
            # different places. rng is seeded per-year (not once for the whole run) so adding a
            # year to --years never perturbs the offsets already used for the others.
            ox = oy = 0.0
            if args.offset_seed is not None:
                rng = np.random.default_rng(args.offset_seed + yr)
                ox, oy = rng.uniform(-hm, hm, size=2)
            for i, dy in enumerate(offs):
                for j, dx in enumerate(offs):
                    lon, lat = to_wgs.transform(p["x"] + ox + dx, p["y"] + oy - dy)
                    rows.append({"stub": f"{p['region']}_{yr}_r{i}c{j}",
                                 "lat": round(lat, 6), "lon": round(lon, 6),
                                 "half_m": int(hm), "grid_r": i, "grid_c": j,
                                 "start": f"{yr}-01-01", "end": f"{yr}-12-31",
                                 "year": yr, "region": p["region"], "n_trials": 0})
    A = pd.DataFrame(rows)
    # Sorted by region, year, then GRID POSITION, so a segmentation job walks tiles that share
    # Sentinel-2 scenes back to back. Scene-cache locality is worth 4.0x on pre-segment
    # (TILE_SIZE_BENCHMARK.md) and costs nothing but this sort.
    #
    # Sort on `grid_r`/`grid_c`, never on `stub`: the stub sorts lexically, so on any grid wider
    # than ten tiles `r10` lands between `r1` and `r2` and the walk jumps across the region on
    # every step. Harmless on the 4x4 demo grid, and a 4x cost error on a 34x34 one.
    A = A.sort_values(["region", "year", "grid_r", "grid_c"]).reset_index(drop=True)
    A.to_csv(args.aois_out, index=False)
    print(f"\n{len(A)} tile-years ({g}x{g} grid x {len(args.years)} years x {len(picked)} "
          f"region(s)) -> {args.aois_out}")


if __name__ == "__main__":
    main()
