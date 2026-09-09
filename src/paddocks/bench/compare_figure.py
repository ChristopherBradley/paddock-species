#!/usr/bin/env python
"""
compare_figure.py -- [true colour | composite | left product | right product] per window.

Left and right are crops-schema GeoPackages (e.g. production after the merge, and a candidate
tiling after its merge); each has its own aois.csv (lattice) and samgeo dir (raster footprints).
Windows: CSV name,x,y,half_m[,note] in EPSG:3577.
"""
import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from merge_tile_boundaries import Lattice                                   # noqa: E402
from boundary_qa_figures import (CLS_COLOR, ABST, tiles_in_window, raster_footprint, rgb_window,
                                 draw_polys, draw_lattice, read_fid)        # noqa: E402
from truecolour import truecolour                                           # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--left", required=True); ap.add_argument("--left-aois", required=True); ap.add_argument("--left-samgeo", required=True)
    ap.add_argument("--right", required=True); ap.add_argument("--right-aois", required=True); ap.add_argument("--right-samgeo", required=True)
    ap.add_argument("--left-title", default="production 3 km, merged"); ap.add_argument("--right-title", default="candidate, merged")
    ap.add_argument("--windows", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--tc-cache", required=True); ap.add_argument("--labels", action="store_true"); ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    latL, latR = Lattice(a.left_aois), Lattice(a.right_aois)
    invL, invR = {v: k for k, v in latL.stub_k.items()}, {v: k for k, v in latR.stub_k.items()}
    W = pd.read_csv(a.windows)
    n = len(W)
    fig, axes = plt.subplots(n, 4, figsize=(17.5, 4.4 * n), squeeze=False)
    for i, e in W.iterrows():
        h = float(e.half_m); b = (e.x - h, e.y - h, e.x + h, e.y + h)
        tc, ext = truecolour(e.x, e.y, h, a.tc_cache, str(e["name"]))
        stubsL = tiles_in_window(latL, invL, b); stubsR = tiles_in_window(latR, invR, b)
        feetL = [raster_footprint(a.left_samgeo, s) for s in stubsL]; feetR = [raster_footprint(a.right_samgeo, s) for s in stubsR]
        rgb = rgb_window(a.left_samgeo, stubsL, b)
        gL, gR = read_fid(a.left, "crops", b), read_fid(a.right, "crops", b)
        panels = [("Sentinel-2 true colour (clearest spring scene)", None, None, None),
                  ("Fourier-NDWI composite SAM saw", None, None, None),
                  (a.left_title, gL, latL, feetL), (a.right_title, gR, latR, feetR)]
        for j, (ttl, g, lat, feet) in enumerate(panels):
            ax = axes[i][j]
            if j == 0:
                ax.imshow(tc, extent=ext, interpolation="nearest")
            else:
                ax.imshow(rgb.transpose(1, 2, 0), extent=(b[0], b[2], b[1], b[3]), interpolation="nearest")
            if g is not None:
                draw_polys(ax, g, lat, "after")
                draw_lattice(ax, lat, b, feet)
                if a.labels:
                    import shapely
                    win = shapely.box(*b)
                    for fid, gm in zip(g.fid, g.geometry):
                        c = gm.intersection(win).representative_point()
                        ax.text(c.x, c.y, str(fid), fontsize=5, color="white", ha="center", va="center")
                ttl = f"{ttl}: {len(g)} polygons"
            ax.set_xlim(b[0], b[2]); ax.set_ylim(b[1], b[3]); ax.set_xticks([]); ax.set_yticks([])
            ax.set_title((f"{e['name']} " if j == 0 else "") + ttl, fontsize=8, loc="left")
        if "note" in W and isinstance(e.get("note"), str):
            axes[i][0].text(0.01, 0.02, e["note"], transform=axes[i][0].transAxes, fontsize=7, color="white",
                            va="bottom", bbox=dict(fc="black", alpha=0.5, lw=0))
    handles = [Patch(fc=c, alpha=0.5, label=k) for k, c in CLS_COLOR.items()] + [
        Patch(fc=ABST, alpha=0.4, label="abstained"), Line2D([], [], color="white", ls="--", label="lattice"),
        Line2D([], [], color="#ffff66", label="tile raster footprint"), Line2D([], [], color="#ff00ff", lw=1.8, label="union of two views"),
        Line2D([], [], color="#00e5ff", lw=1.5, label="absorbed a duplicate"), Patch(fc="none", hatch="///", label="class conflict")]
    fig.legend(handles=handles, loc="lower center", ncol=8, fontsize=8, frameon=False)
    if a.title:
        fig.suptitle(a.title, fontsize=11)
    fig.tight_layout(rect=(0, 0.03, 1, 0.985)); fig.savefig(a.out, dpi=a.dpi, facecolor="#202020"); print("wrote", a.out)


if __name__ == "__main__":
    main()
