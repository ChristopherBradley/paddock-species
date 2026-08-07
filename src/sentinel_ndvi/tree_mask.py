#!/usr/bin/env python3
"""
Tree masking for the Stage-2 Sentinel-2 windows, from the 1 m Global Canopy Height v2.

Why: the 200 m window sits on a paddock CORNER, so it routinely includes tree lines,
scattered paddock trees and roadside vegetation. Those pixels are green all year, never
flower, and drag the window mean toward "perennial" — diluting exactly the flowering
signal Stage 2 depends on.

Rule (as specified): a 10 m Sentinel pixel is dropped if ANY overlapping 1 m canopy pixel
is taller than --tree-height-min, and additionally every pixel ADJACENT to such a pixel is
dropped, because the canopy product and Sentinel-2 do not co-register perfectly.

The source is 2,842 quadkey tiles in EPSG:3857 (Web Mercator), uint8 height in metres.
Tiles are windowed-read, so cost is a few hundred KB per trial rather than the 394 GB total.

    from tree_mask import TreeMasker
    tm = TreeMasker("/scratch/xe2/cb8590/Global_Canopy_Height_v2")
    mask = tm.mask_for_geobox(geobox)      # True = drop this Sentinel pixel
"""
import glob
import math
import os

import numpy as np


def lonlat_to_tile(lon, lat, z):
    """Slippy-map tile x/y containing lon/lat at zoom z."""
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    lat_r = math.radians(max(min(lat, 85.05112878), -85.05112878))
    y = int((1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n)
    return min(max(x, 0), n - 1), min(max(y, 0), n - 1)


def tile_to_quadkey(x, y, z):
    """Bing quadkey string for a tile — this is what the .tif files are named."""
    qk = []
    for i in range(z, 0, -1):
        digit = 0
        bit = 1 << (i - 1)
        if x & bit:
            digit += 1
        if y & bit:
            digit += 2
        qk.append(str(digit))
    return "".join(qk)


class TreeMasker:
    def __init__(self, chm_dir, height_min=1.0, dilate=1):
        self.dir = chm_dir
        self.height_min = height_min
        self.dilate = dilate
        self.zoom = None
        self._have = set()
        for p in glob.glob(os.path.join(chm_dir, "*.tif")):
            qk = os.path.splitext(os.path.basename(p))[0]
            if qk.isdigit():
                self._have.add(qk)
                if self.zoom is None:
                    self.zoom = len(qk)
        if not self._have:
            raise SystemExit(f"no quadkey .tif tiles found in {chm_dir}")

    def tiles_for_bounds(self, west, south, east, north):
        """Every tile touching a lon/lat box (a window can straddle tile edges)."""
        x0, y0 = lonlat_to_tile(west, north, self.zoom)
        x1, y1 = lonlat_to_tile(east, south, self.zoom)
        out = []
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                qk = tile_to_quadkey(x, y, self.zoom)
                if qk in self._have:
                    out.append(os.path.join(self.dir, qk + ".tif"))
        return out

    def mask_for_geobox(self, geobox, lon, lat, pad_deg=0.004):
        """Boolean array on the Sentinel grid: True = drop (tree, or adjacent to tree).

        Returns (mask, stats). stats reports whether canopy data actually covered the
        window — a window with no tile is NOT the same as a window with no trees, and
        must not be silently treated as tree-free.
        """
        import rasterio
        from rasterio.warp import Resampling, reproject

        files = self.tiles_for_bounds(lon - pad_deg, lat - pad_deg,
                                      lon + pad_deg, lat + pad_deg)
        h, w = geobox.shape
        dst_crs = geobox.crs.crs_str if hasattr(geobox.crs, "crs_str") else str(geobox.crs)
        acc = np.zeros((h, w), dtype=np.uint8)
        covered = False

        for f in files:
            with rasterio.open(f) as src:
                # Reproject the tile's tree flag straight onto the Sentinel grid, taking the
                # MAX over contributing 1 m pixels — that is exactly "any tree in this cell".
                try:
                    win = src.window(*_bounds_in(src.crs, geobox, pad=40))
                    win = win.round_offsets().round_lengths()
                    if win.width <= 0 or win.height <= 0:
                        continue
                    arr = src.read(1, window=win)
                    if arr.size == 0:
                        continue
                    tree = (arr > self.height_min).astype(np.uint8)
                    out = np.zeros((h, w), dtype=np.uint8)
                    reproject(source=tree, destination=out,
                              src_transform=src.window_transform(win), src_crs=src.crs,
                              dst_transform=geobox.transform, dst_crs=dst_crs,
                              resampling=Resampling.max)
                    acc |= out
                    covered = True
                except Exception:
                    continue

        mask = acc.astype(bool)
        n_tree = int(mask.sum())
        if self.dilate > 0 and n_tree:
            mask = _dilate(mask, self.dilate)
        return mask, {"chm_tiles": len(files), "chm_covered": covered,
                      "n_tree_px": n_tree, "n_masked_px": int(mask.sum())}


def _bounds_in(dst_crs, geobox, pad=0.0):
    """Geobox bounds expressed in another CRS, with a metre pad."""
    from rasterio.warp import transform_bounds
    b = geobox.extent.boundingbox
    src_crs = geobox.crs.crs_str if hasattr(geobox.crs, "crs_str") else str(geobox.crs)
    return transform_bounds(src_crs, dst_crs,
                            b.left - pad, b.bottom - pad, b.right + pad, b.top + pad)


def _dilate(mask, n):
    """Binary dilation by n cells (3x3 structuring element), numpy-only."""
    out = mask.copy()
    for _ in range(n):
        p = np.pad(out, 1, mode="constant", constant_values=False)
        out = (p[:-2, :-2] | p[:-2, 1:-1] | p[:-2, 2:] |
               p[1:-1, :-2] | p[1:-1, 1:-1] | p[1:-1, 2:] |
               p[2:, :-2] | p[2:, 1:-1] | p[2:, 2:])
    return out
