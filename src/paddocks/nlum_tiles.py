#!/usr/bin/env python3
"""
Turn an NLUM commodity probability surface into the thing that actually sets the compute bill:
a count of segmentation tiles.

WHY TILES AND NOT AREA. Every cost in this pipeline is per-AOI-per-year — one datacube read,
one Fourier composite, one SAM pass, one feature extraction. So "how much would a national run
cost" is not answered by km2, it is answered by how many tiles the mask touches, which depends
on the tile size as much as on the threshold.

WHY THE THRESHOLD IS THE WHOLE DECISION. NLUM values are probability x 10000 that a 250 m
pixel grows the commodity. Thresholding at >1 keeps any pixel with a >0.01 % chance, which for
canola selects 12x more land than NLUM itself believes is planted with canola (compare the
mask area against sum(prob)*area, which this script prints as the "expected" area). Every one
of those tiles is segmented, downloaded and classified at full price to find nothing.

Resampling with Resampling.max onto a grid whose cell IS the tile is what makes the count
exact: a tile survives iff at least one NLUM pixel inside it clears the threshold, which is
precisely the rule a real run would apply.

Not sensitive — NLUM is public and this writes no trial records.
"""
import argparse

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

ALBERS = "EPSG:3577"  # equal-area, so a tile is the same size everywhere in Australia


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raster", required=True, nargs="+",
                    help="NLUM probability GeoTIFF(s). Several are UNIONED: a tile survives if "
                         "ANY of them clears the threshold there. That is the right rule for a "
                         "3-class product — the run has to visit a tile that grows any of the "
                         "three — and it is nearly free, because 96.4 %% of the union is already "
                         "inside the cereal mask (NATIONAL_INFERENCE_BENCHMARK_V2.md)")
    ap.add_argument("--threshold", type=float, default=1.0,
                    help="keep pixels with value > this (out of 10000)")
    ap.add_argument("--half-m", type=float, default=1500.0,
                    help="AOI half-width; tile edge is 2x this. 1500 matches the trial AOIs")
    ap.add_argument("--sample", type=int, default=0,
                    help="write this many randomly-chosen tiles as an AOI csv for benchmarking")
    ap.add_argument("--cluster", type=int, default=0, metavar="G",
                    help="sample CLUSTERS of GxG contiguous tiles instead of scattered ones, "
                         "and read --sample as the number of clusters. USE THIS FOR ANY COST "
                         "MEASUREMENT. Scattered tiles overstate the per-tile cost by 4.0x "
                         "(TILE_SIZE_BENCHMARK.md): the bill is driven by Sentinel-2 scene-read "
                         "locality, and a real national run would walk the mask in spatial "
                         "order, not jump across the continent between tiles. A scattered "
                         "sample measures a run nobody would perform.")
    ap.add_argument("--all", action="store_true",
                    help="write EVERY masked tile, not a sample — i.e. the production run")
    ap.add_argument("--block", type=int, default=32,
                    help="tiles are emitted in blocks of BLOCK x BLOCK, blocks in row-major "
                         "order and tiles row-major inside each block. This is the 4.0x "
                         "scene-locality saving (TILE_SIZE_BENCHMARK.md) made explicit at "
                         "national scale: a Sentinel-2 granule is ~100 km, about 33 tiles, so a "
                         "job that walks a BLOCK re-reads each granule once, while a job that "
                         "walks a ROW crosses a new granule every 33 tiles and never returns. "
                         "Row-major over the whole continent would be a 4,000 km stripe.")
    ap.add_argument("--year", type=int, default=2021)
    ap.add_argument("--out", help="AOI csv path, required with --sample")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    edge = 2 * args.half_m
    mask_max = prob_avg = dst_tr = W = H = None
    for path in args.raster:
        with rasterio.open(path) as src:
            nod = src.nodata
            if dst_tr is None:
                # The grid is defined ONCE, by the first raster, and every later raster is
                # reprojected onto it. Letting each raster pick its own grid would union masks
                # that are not pixel-aligned, and the union would be wrong at every edge.
                dst_tr, W, H = calculate_default_transform(
                    src.crs, ALBERS, src.width, src.height, *src.bounds, resolution=edge)
                mask_max = np.zeros((H, W), np.uint8)
                prob_avg = np.zeros((H, W), np.float32)
            # Two reprojections, because two different questions. `max` answers "does this tile
            # contain any qualifying pixel" (the tile count). `average` over the probability
            # answers "how much crop does NLUM think is in it" (the expected area), and
            # averaging a mask would silently answer neither.
            one = np.zeros((H, W), np.uint8)
            avg = np.zeros((H, W), np.float32)
            src_arr = src.read(1)
            valid = src_arr != nod
            reproject(np.where(valid & (src_arr > args.threshold), 1, 0).astype(np.uint8),
                      one, src_transform=src.transform, src_crs=src.crs,
                      dst_transform=dst_tr, dst_crs=ALBERS, resampling=Resampling.max)
            reproject(np.where(valid, src_arr, 0).astype(np.float32) / 1e4,
                      avg, src_transform=src.transform, src_crs=src.crs,
                      dst_transform=dst_tr, dst_crs=ALBERS, resampling=Resampling.average)
            mask_max |= one
            prob_avg += avg      # expected area is additive across commodities
            print(f"  {path.split('/')[-1]}: {int(one.sum()):,} tiles")

    tile_km2 = (edge / 1000.0) ** 2
    n_tiles = int(mask_max.sum())
    mask_km2 = n_tiles * tile_km2
    expected_km2 = float(prob_avg.sum()) * tile_km2

    print(f"rasters   : {len(args.raster)} unioned")
    print(f"threshold : > {args.threshold:g} / 10000")
    print(f"tile      : {edge/1000:g} km edge = {tile_km2:g} km2")
    print(f"\nTILES TO PROCESS : {n_tiles:,}  ({mask_km2:,.0f} km2)")
    print(f"NLUM expected crop area : {expected_km2:,.0f} km2 ({expected_km2/10000:.2f} Mha)")
    print(f"INFLATION : {mask_km2/max(expected_km2,1e-9):.1f}x more land segmented than planted")

    if args.all:
        if not args.out:
            raise SystemExit("--all needs --out")
        import pandas as pd
        from pyproj import Transformer
        to_wgs = Transformer.from_crs(ALBERS, "EPSG:4326", always_xy=True)
        ys, xs = np.nonzero(mask_max)
        x = dst_tr.c + (xs + 0.5) * dst_tr.a
        y = dst_tr.f + (ys + 0.5) * dst_tr.e
        lon, lat = to_wgs.transform(x, y)
        A = pd.DataFrame({"stub": [f"nlum_{args.year}_r{r}_c{c}" for r, c in zip(ys, xs)],
                          "lat": np.round(lat, 6), "lon": np.round(lon, 6),
                          "half_m": int(args.half_m),
                          "start": f"{args.year}-01-01", "end": f"{args.year}-12-31",
                          "year": args.year, "n_trials": 0,
                          "grid_r": ys, "grid_c": xs,
                          "block_r": ys // args.block, "block_c": xs // args.block})
        A = A.sort_values(["block_r", "block_c", "grid_r", "grid_c"]).reset_index(drop=True)
        A.to_csv(args.out, index=False)
        nb = A.groupby(["block_r", "block_c"]).ngroups
        print(f"\nwrote ALL {len(A):,} tiles -> {args.out}")
        print(f"{nb:,} blocks of {args.block}x{args.block}, median "
              f"{int(A.groupby(['block_r','block_c']).size().median())} tiles per block")
        return

    if args.sample:
        if not args.out:
            raise SystemExit("--sample needs --out")
        ys, xs = np.nonzero(mask_max)
        rng = np.random.default_rng(args.seed)
        pick = rng.choice(len(ys), size=min(args.sample, len(ys)), replace=False)
        import pandas as pd
        from pyproj import Transformer
        to_wgs = Transformer.from_crs(ALBERS, "EPSG:4326", always_xy=True)

        if args.cluster:
            g = args.cluster
            cells, seen = [], set()
            for k, i in enumerate(pick):
                r0, c0 = ys[i] - g // 2, xs[i] - g // 2
                for dr in range(g):
                    for dc in range(g):
                        r, c = r0 + dr, c0 + dc
                        # Only tiles that are themselves in the mask. Padding a cluster out
                        # with tiles a real run would never visit would price work that
                        # would never be done.
                        if 0 <= r < H and 0 <= c < W and mask_max[r, c] and (r, c) not in seen:
                            seen.add((r, c))
                            cells.append((r, c, k))
            print(f"\n{len(pick)} clusters of up to {g}x{g} -> {len(cells)} tiles "
                  f"({len(cells)/max(len(pick),1):.1f} per cluster; a cluster loses tiles "
                  f"where the mask does not fill the block)")
        else:
            cells = [(ys[i], xs[i], k) for k, i in enumerate(pick)]

        rows = []
        for r, c, k in cells:
            x = dst_tr.c + (c + 0.5) * dst_tr.a
            y = dst_tr.f + (r + 0.5) * dst_tr.e
            lon, lat = to_wgs.transform(x, y)
            rows.append({"stub": f"nlum_{args.year}_r{r}_c{c}",
                         "lat": round(lat, 6), "lon": round(lon, 6),
                         "half_m": int(args.half_m),
                         "start": f"{args.year}-01-01", "end": f"{args.year}-12-31",
                         "year": args.year, "n_trials": 0, "cluster": k})
        # Sorted so a job walks a cluster contiguously — the whole point of clustering.
        pd.DataFrame(rows).sort_values(["cluster", "stub"]).to_csv(args.out, index=False)
        print(f"sampled {len(rows)} tiles -> {args.out}")


if __name__ == "__main__":
    main()
