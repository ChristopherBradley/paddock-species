#!/usr/bin/env python
"""
boundary_seam_audit.py -- quantify tile-boundary artefacts in a (merged or unmerged) crop GeoPackage.

Two signatures are measured, both against the tiles' ACTUAL raster footprints (the EPSG:6933
bounding box of each rotated 3 km lattice square, read from <samgeo-dir>/<stub>.tif):

  truncation  -- boundary length a polygon shares with its OWN tile's raster edge (within --tol m;
                 SAM polygons stop 2 px = ~20 m inside the raster, so --tol 30).
                 A real paddock edge coincides with that specific rotated line only by chance, so
                 shared length >= --min-cut m is a view that was cut by the raster window.
  fill        -- for each truncated polygon, what the same file holds in a --probe m deep strip
                 just beyond the cut: same class / other class / abstained / nothing. A cut whose
                 far side is empty or a different class is the residual artefact a merge did not fix.

Plus the overlap census (pairwise cross-tile overlap area) and a per-polygon CSV so figures can be
drawn from the truncated cases. Aggregate only.
"""
import argparse
import json
import os
import sqlite3

import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer
import rasterio

from merge_tile_boundaries import Lattice, blob_to_geom

_T = Transformer.from_crs("EPSG:6933", "EPSG:3577", always_xy=True)


def footprint(samgeo_dir, stub):
    p = f"{samgeo_dir}/{stub}.tif"
    if not os.path.exists(p):
        return None
    with rasterio.open(p) as src:
        b = src.bounds
    xs, ys = np.linspace(b.left, b.right, 25), np.linspace(b.bottom, b.top, 25)
    ring = ([(x, b.bottom) for x in xs] + [(b.right, y) for y in ys] +
            [(x, b.top) for x in xs[::-1]] + [(b.left, y) for y in ys[::-1]])
    return shapely.Polygon([_T.transform(x, y) for x, y in ring])


def load(gpkg, layer):
    con = sqlite3.connect(gpkg)
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({layer})")]
    want = [c for c in ["fid", "stub", "pred", "abstain_reason", "area_ha", "boundary_action",
                        "class_conflict", "merge_n"] if c in cols]
    rows, geoms = [], []
    for r in con.execute(f"SELECT {', '.join(want)}, geom FROM {layer}"):
        rows.append(r[:-1])
        geoms.append(blob_to_geom(r[-1]))
    con.close()
    df = pd.DataFrame(rows, columns=want)
    if "pred" not in df:
        df["pred"] = None
    if "abstain_reason" not in df:
        df["abstain_reason"] = ""
    df["abstain_reason"] = df["abstain_reason"].fillna("")
    df["classified"] = (df.abstain_reason == "") & df.pred.notna()
    return df, np.array(geoms, dtype=object)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gpkg", required=True)
    ap.add_argument("--layer", default="crops")
    ap.add_argument("--aois", required=True)
    ap.add_argument("--samgeo-dir", required=True)
    ap.add_argument("--tol", type=float, default=30.0,
                    help="SAM polygons stop ~2 px (20 m) inside the raster; 30 m catches the cut")
    ap.add_argument("--min-cut", type=float, default=100.0)
    ap.add_argument("--probe", type=float, default=60.0)
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--summary", required=True)
    args = ap.parse_args()

    lat = Lattice(args.aois)
    df, G = load(args.gpkg, args.layer)
    n = len(df)
    feet = {}
    for s in df.stub.unique():
        feet[s] = footprint(args.samgeo_dir, s)
    missing = sum(1 for v in feet.values() if v is None)
    edge_buf = {s: (f.exterior.buffer(args.tol) if f is not None else None) for s, f in feet.items()}

    # truncation: shared boundary length with own raster edge
    cut_len = np.zeros(n)
    for i, (s, g) in enumerate(zip(df.stub.values, G)):
        eb = edge_buf.get(s)
        if eb is None:
            cut_len[i] = np.nan
            continue
        if not g.intersects(eb):
            continue
        cut_len[i] = g.boundary.intersection(eb).length
    df["cut_len_m"] = np.round(cut_len, 1)
    df["truncated"] = df.cut_len_m >= args.min_cut

    # fill beyond the cut, from the same file
    tree = shapely.STRtree(G)
    fill_rows = []
    for i in np.where(df.truncated.values)[0]:
        s, g = df.stub.values[i], G[i]
        strip = g.buffer(args.probe).difference(g).difference(feet[s].buffer(-args.tol))
        if strip.is_empty or strip.area <= 0:
            fill_rows.append((i, 0.0, 0.0, 0.0, 0.0))
            continue
        cand = tree.query(strip, predicate="intersects")
        same = other = abst = 0.0
        for j in cand:
            if j == i:
                continue
            a = strip.intersection(G[j]).area
            if a <= 0:
                continue
            if not df.classified.values[j]:
                abst += a
            elif df.pred.values[j] == df.pred.values[i]:
                same += a
            else:
                other += a
        A = strip.area
        fill_rows.append((i, A / 1e4, min(same / A, 1), min(other / A, 1), min(abst / A, 1)))
    F = pd.DataFrame(fill_rows, columns=["i", "strip_ha", "fill_same", "fill_other", "fill_abst"]).set_index("i")
    for c in ["strip_ha", "fill_same", "fill_other", "fill_abst"]:
        df[c] = np.nan
        df.loc[F.index, c] = F[c].round(3)
    df["fill_none"] = (1 - df[["fill_same", "fill_other", "fill_abst"]].sum(axis=1)).round(3)
    df.loc[~df.truncated, "fill_none"] = np.nan

    def bucket(r):
        if not r.truncated:
            return ""
        v = {"same": r.fill_same, "other": r.fill_other, "abst": r.fill_abst, "none": r.fill_none}
        k = max(v, key=v.get)
        return k if v[k] >= 0.5 else "mixed"
    df["beyond_cut"] = df.apply(bucket, axis=1)

    # overlap census (cross-tile, pairwise)
    ii, jj = tree.query(G, predicate="intersects")
    m = (ii < jj) & (df.stub.values[ii] != df.stub.values[jj])
    ii, jj = ii[m], jj[m]
    inter = shapely.area(shapely.intersection(G[ii], G[jj]))
    k = inter > 0
    ii, jj, inter = ii[k], jj[k], inter[k]
    cls = df.classified.values
    total_area = float(shapely.area(G).sum() / 1e4)

    cen = shapely.centroid(G)
    cx, cy = shapely.get_x(cen), shapely.get_y(cen)
    df["cx"], df["cy"] = np.round(cx, 1), np.round(cy, 1)
    df.to_csv(args.out_csv, index=False)

    T = df[df.truncated]
    Tc = T[T.classified]
    summ = dict(
        gpkg=args.gpkg, n_polygons=n, n_classified=int(cls.sum()), total_area_ha=round(total_area, 1),
        classified_area_ha=round(float(shapely.area(G[cls]).sum() / 1e4), 1),
        tiles=len(feet), tiles_without_tif=missing,
        n_overlap_pairs=int(len(ii)), overlap_ha=round(float(inter.sum() / 1e4), 1),
        overlap_ha_classified=round(float(inter[cls[ii] & cls[jj]].sum() / 1e4), 1),
        overlap_pct_of_area=round(100 * float(inter.sum() / 1e4) / total_area, 2),
        n_truncated=int(len(T)), pct_truncated=round(100 * len(T) / n, 2),
        truncated_area_ha=round(float(T.area_ha.sum()), 1),
        n_truncated_classified=int(len(Tc)),
        pct_truncated_classified=round(100 * len(Tc) / max(cls.sum(), 1), 2),
        cut_len_median_m=round(float(T.cut_len_m.median()), 1) if len(T) else None,
        beyond_cut_counts=T.beyond_cut.value_counts().to_dict(),
        beyond_cut_counts_classified=Tc.beyond_cut.value_counts().to_dict(),
        beyond_cut_area_ha_classified={k: round(float(v), 1) for k, v in Tc.groupby("beyond_cut").area_ha.sum().items()},
        thresholds=dict(tol=args.tol, min_cut=args.min_cut, probe=args.probe),
    )
    if "boundary_action" in df:
        summ["truncated_by_action"] = T.boundary_action.fillna("untouched").value_counts().to_dict()
    with open(args.summary, "w") as f:
        json.dump(summ, f, indent=2)
    print(json.dumps(summ, indent=2))


if __name__ == "__main__":
    main()
