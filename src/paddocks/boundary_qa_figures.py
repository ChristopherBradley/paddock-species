#!/usr/bin/env python
"""
boundary_qa_figures.py -- before/after QA windows for merge_tile_boundaries.py.

Each row of the figure is one window: [S2 composite | before | after]. Polygons are filled by
class (Canola yellow, Cereal orange, Legume green, abstained grey). The 3 km lattice is drawn as
white dashed lines and every tile's actual RASTER footprint (the EPSG:6933 bounding box of the
rotated lattice square, ~345 m wider than the square on every side) as a thin yellow outline, so
the overlap band between neighbouring tiles is visible. In the "before" panel polygons whose
centroid lies outside their own tile's lattice square ("away" views) get a white dashed edge; in
the "after" panel union products are outlined magenta, twins that absorbed a duplicate cyan,
rescued away polygons white dotted, and class conflicts are hatched.

Examples come from a CSV with columns name,x,y,half_m[,note] in EPSG:3577.
"""
import argparse
import os

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
import shapely
from pyproj import Transformer

from merge_tile_boundaries import Lattice

CLS_COLOR = {"Canola": "#ffd400", "Cereal": "#e8772e", "Legume": "#2fbf4f"}
ABST = "#b0b0b0"


def tiles_in_window(lat, inv, bounds):
    kx0, ky0 = lat.k_from_xy(np.array([bounds[0]]), np.array([bounds[1]]))
    kx1, ky1 = lat.k_from_xy(np.array([bounds[2]]), np.array([bounds[3]]))
    out = []
    for kx in range(int(kx0[0]) - 1, int(kx1[0]) + 2):
        for ky in range(int(ky0[0]) - 1, int(ky1[0]) + 2):
            if (kx, ky) in inv:
                out.append(inv[(kx, ky)])
    return out


def raster_footprint(samgeo_dir, stub):
    p = f"{samgeo_dir}/{stub}.tif"
    if not os.path.exists(p):
        return None
    with rasterio.open(p) as src:
        b, crs = src.bounds, src.crs
    xs, ys = np.linspace(b.left, b.right, 25), np.linspace(b.bottom, b.top, 25)
    ring = ([(x, b.bottom) for x in xs] + [(b.right, y) for y in ys] +
            [(x, b.top) for x in xs[::-1]] + [(b.left, y) for y in ys[::-1]])
    T = Transformer.from_crs(crs, "EPSG:3577", always_xy=True)
    return shapely.Polygon([T.transform(x, y) for x, y in ring])


def rgb_window(samgeo_dir, stubs, bounds, res=10.0):
    minx, miny, maxx, maxy = bounds
    w, h = int(round((maxx - minx) / res)), int(round((maxy - miny) / res))
    dst = np.zeros((3, h, w), np.uint8)
    tr = from_origin(minx, maxy, res, res)
    for s in stubs:
        p = f"{samgeo_dir}/{s}.tif"
        if not os.path.exists(p):
            continue
        tmp = np.zeros_like(dst)
        with rasterio.open(p) as src:
            reproject(rasterio.band(src, [1, 2, 3]), tmp, dst_transform=tr, dst_crs="EPSG:3577",
                      resampling=Resampling.nearest, dst_nodata=0)
        m = (dst.sum(0) == 0) & (tmp.sum(0) > 0)
        dst[:, m] = tmp[:, m]
    return dst


def draw_polys(ax, g, lat, mode):
    if len(g) == 0:
        return
    for _, r in g.iterrows():
        pred = r.get("pred")
        classified = (r.get("abstain_reason") in ("", None)) and isinstance(pred, str)
        fc = CLS_COLOR.get(pred, ABST) if classified else ABST
        ec, lw, ls, hatch, alpha = "black", 0.6, "-", None, 0.45 if classified else 0.3
        if mode == "before" and r.get("_away"):
            ec, lw, ls = "white", 1.2, "--"
        if mode == "after":
            ba = r.get("boundary_action") or ""
            if ba == "repaired":
                ec, lw = "#00ff40", 2.2
            elif ba.startswith("union"):
                ec, lw = "#ff00ff", 1.8
            elif ba.startswith("absorbed"):
                ec, lw = "#00e5ff", 1.5
            elif ba.startswith("rescued"):
                ec, lw, ls = "white", 1.2, ":"
            elif ba == "clipped":
                ec, lw = "#ffa500", 1.2
            if r.get("class_conflict") == 1:
                hatch = "///"
        geoms = [r.geometry] if r.geometry.geom_type == "Polygon" else list(r.geometry.geoms)
        for gm in geoms:
            xy = np.asarray(gm.exterior.coords)
            ax.fill(xy[:, 0], xy[:, 1], fc=fc, ec="none", alpha=alpha, hatch=hatch)
            ax.plot(xy[:, 0], xy[:, 1], color=ec, lw=lw, ls=ls)
            for hole in gm.interiors:
                h = np.asarray(hole.coords)
                ax.fill(h[:, 0], h[:, 1], fc="white", ec="none", alpha=0.0)
                ax.plot(h[:, 0], h[:, 1], color=ec, lw=lw * 0.7, ls=ls)


def draw_lattice(ax, lat, bounds, feet):
    minx, miny, maxx, maxy = bounds
    vx, vy = lat.ox - lat.half, lat.oy - lat.half
    for x in np.arange(vx + np.floor((minx - vx) / lat.E) * lat.E, maxx + lat.E, lat.E):
        if minx <= x <= maxx:
            ax.axvline(x, color="white", ls="--", lw=1.0, alpha=0.9)
    for y in np.arange(vy + np.floor((miny - vy) / lat.E) * lat.E, maxy + lat.E, lat.E):
        if miny <= y <= maxy:
            ax.axhline(y, color="white", ls="--", lw=1.0, alpha=0.9)
    for fp in feet:
        if fp is None:
            continue
        xy = np.asarray(fp.exterior.coords)
        ax.plot(xy[:, 0], xy[:, 1], color="#ffff66", lw=0.8, alpha=0.9)


def read_fid(path, layer, bounds):
    """Read polygons in bbox with the GeoPackage fid as a column (so labels match the CSVs)."""
    import fiona
    from shapely.geometry import shape
    recs, geoms = [], []
    with fiona.open(path, layer=layer) as src:
        for ft in src.filter(bbox=bounds):
            d = dict(ft["properties"])
            d["fid"] = int(ft["id"])
            recs.append(d)
            geoms.append(shape(ft["geometry"]))
    g = gpd.GeoDataFrame(recs, geometry=geoms, crs="EPSG:3577")
    if "fid" not in g:
        g["fid"] = []
    return g


def mark_away(g, lat):
    if len(g) == 0:
        g["_away"] = []
        return g
    k = np.array([lat.stub_k.get(s, (np.nan, np.nan)) for s in g.stub], dtype=float)
    c = g.geometry.centroid
    hk = lat.k_from_xy(c.x.values, c.y.values)
    g["_away"] = (hk[0] != k[:, 0]) | (hk[1] != k[:, 1])
    return g


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--aois", required=True)
    ap.add_argument("--samgeo-dir", required=True, help="dir with <stub>.tif composites")
    ap.add_argument("--examples", required=True, help="CSV: name,x,y,half_m[,note]")
    ap.add_argument("--out", required=True, help="output PNG (one figure, one row per example)")
    ap.add_argument("--layer", default="crops")
    ap.add_argument("--labels", action="store_true", help="write fid next to each polygon")
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--title", default="")
    args = ap.parse_args()

    lat = Lattice(args.aois)
    inv = {v: k for k, v in lat.stub_k.items()}
    ex = pd.read_csv(args.examples)
    n = len(ex)
    fig, axes = plt.subplots(n, 3, figsize=(13.5, 4.4 * n), squeeze=False)
    for i, e in ex.iterrows():
        h = float(e.half_m)
        bounds = (e.x - h, e.y - h, e.x + h, e.y + h)
        stubs = tiles_in_window(lat, inv, bounds)
        feet = [raster_footprint(args.samgeo_dir, s) for s in stubs]
        rgb = rgb_window(args.samgeo_dir, stubs, bounds)
        gb = mark_away(read_fid(args.before, args.layer, bounds), lat)
        ga = read_fid(args.after, args.layer, bounds)
        for j, (ax, mode) in enumerate(zip(axes[i], ["image", "before", "after"])):
            ax.imshow(rgb.transpose(1, 2, 0), extent=(bounds[0], bounds[2], bounds[1], bounds[3]),
                      interpolation="nearest")
            if mode == "before":
                draw_polys(ax, gb, lat, "before")
            elif mode == "after":
                draw_polys(ax, ga, lat, "after")
            draw_lattice(ax, lat, bounds, feet)
            if args.labels and mode != "image":
                g = gb if mode == "before" else ga
                win = shapely.box(*bounds)
                for fid, gm in zip(g.fid, g.geometry):
                    c = gm.intersection(win).representative_point()
                    ax.text(c.x, c.y, str(fid), fontsize=5, color="white", ha="center", va="center")
            ax.set_xlim(bounds[0], bounds[2]); ax.set_ylim(bounds[1], bounds[3])
            ax.set_xticks([]); ax.set_yticks([])
            if mode == "image":
                ax.set_title(f"{e['name']}  ({e.x:.0f}, {e.y:.0f}) ±{h:.0f} m", fontsize=9, loc="left")
            elif mode == "before":
                ax.set_title(f"before: {len(gb)} polygons, {int(gb._away.sum()) if len(gb) else 0} away views",
                             fontsize=9, loc="left")
            else:
                ba = ga.boundary_action.fillna("") if "boundary_action" in ga else pd.Series([], dtype=str)
                ax.set_title(f"after: {len(ga)} polygons, {int(ba.str.startswith('union').sum())} unions, "
                             f"{int(ba.str.startswith('absorbed').sum())} absorbed, "
                             f"{int(ba.str.startswith('rescued').sum())} rescued, "
                             f"{int(ba.str.contains('clipped').sum())} clipped, "
                             f"{int((ba == 'repaired').sum())} repaired, "
                             f"{int((ga.class_conflict == 1).sum()) if 'class_conflict' in ga else 0} conflicts",
                             fontsize=8, loc="left")
        if "note" in ex and isinstance(e.get("note"), str):
            axes[i][0].text(0.01, 0.02, e["note"], transform=axes[i][0].transAxes, fontsize=7,
                            color="white", va="bottom", bbox=dict(fc="black", alpha=0.5, lw=0))
    handles = [Patch(fc=c, alpha=0.5, label=k) for k, c in CLS_COLOR.items()] + [
        Patch(fc=ABST, alpha=0.4, label="abstained"),
        Line2D([], [], color="white", ls="--", label="3 km lattice"),
        Line2D([], [], color="#ffff66", label="tile raster footprint"),
        Line2D([], [], color="white", ls="--", lw=1.2, label="before: away view"),
        Line2D([], [], color="#ff00ff", lw=1.8, label="after: union"),
        Line2D([], [], color="#00e5ff", lw=1.5, label="after: absorbed a duplicate"),
        Line2D([], [], color="white", ls=":", lw=1.2, label="after: rescued"),
        Line2D([], [], color="#ffa500", lw=1.2, label="after: sliver clipped (M2)"),
        Line2D([], [], color="#00ff40", lw=2.2, label="after: repaired from another view"),
        Patch(fc="none", hatch="///", label="class conflict"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=7, fontsize=8, frameon=False)
    if args.title:
        fig.suptitle(args.title, fontsize=11)
    fig.tight_layout(rect=(0, 0.03, 1, 0.985))
    fig.savefig(args.out, dpi=args.dpi, facecolor="#202020")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
