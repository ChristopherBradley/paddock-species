#!/usr/bin/env python
"""
cut_continuity.py -- does the field continue past a polygon's raster-edge cut? (image test)

A polygon whose boundary runs along its own tile's raster edge is EITHER a view cut by the raster
window OR a whole paddock whose real fence/road happens to lie within 30 m of that edge. The
composite of the NEIGHBOURING tile covers both sides of the cut, so it can tell them apart:
compare the 3-band Fourier-of-NDWI values in a strip 15-60 m INSIDE the polygon along the cut
with a strip 15-60 m OUTSIDE it beyond the raster edge, both sampled from the SAME neighbour
composite (each tile's composite has its own percentile stretch, so never mix tiles).

    score = mean over bands of |mu_in - mu_out| / sqrt((sd_in^2 + sd_out^2) / 2)

Low score: same field continues (genuine cut). High score: a real boundary.

Calibration sets, all from the merge's own outputs:
  same_field    -- fragments the merge unioned (M1 'merge' pairs): the ground beyond fragment A's cut
                   IS the same paddock (the other view), so these are known genuine cuts.
  real_boundary -- interior polygons (> 500 m from any raster edge): their actual boundary, inside
                   vs outside strips from their own composite, known real boundaries.
Then the residual truncated polygons of the merged file are scored and classified by a threshold
placed between the two calibration distributions. Aggregate only.
"""
import argparse
import json
import os

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
import shapely
from pyproj import Transformer

from merge_tile_boundaries import Lattice
from boundary_seam_audit import footprint, load

_TO6933 = Transformer.from_crs("EPSG:3577", "EPSG:6933", always_xy=True).transform


def strip_stats(tif, geom3577):
    """Mean/sd per band of composite pixels under geom (EPSG:3577 -> raster CRS). None if < 6 px."""
    if geom3577.is_empty:
        return None
    g = shapely.ops.transform(_TO6933, geom3577)
    with rasterio.open(tif) as src:
        b = g.bounds
        win = src.window(b[0], b[1], b[2], b[3]).round_offsets().round_lengths()
        if win.width < 1 or win.height < 1:
            return None
        try:
            win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
        except rasterio.errors.WindowError:
            return None
        if win.width < 1 or win.height < 1:
            return None
        arr = src.read(window=win).astype(float)
        tr = src.window_transform(win)
    mask = rasterize([(g, 1)], out_shape=arr.shape[1:], transform=tr, fill=0, dtype="uint8").astype(bool)
    if mask.sum() < 6:
        return None
    v = arr[:, mask]
    return v.mean(1), v.std(1), int(mask.sum())


def score(stat_in, stat_out):
    mi, si, _ = stat_in
    mo, so, _ = stat_out
    return float(np.mean(np.abs(mi - mo) / np.sqrt((si ** 2 + so ** 2) / 2 + 1e-6)))


def cut_score(g, stubA, feet, samgeo_dir, lat, inv, tol=30, near=15, far=60):
    """Score the cut of polygon g (tile A) using each neighbour whose raster covers beyond the cut.
    Returns (score, n_in, n_out) pixel-weighted over neighbours, or None."""
    fA = feet[stubA]
    edge = fA.exterior
    cutzone = edge.buffer(far)
    inside = g.intersection(cutzone).difference(edge.buffer(near))
    outside = g.buffer(far).difference(g.buffer(near)).difference(fA)
    if inside.is_empty or outside.is_empty:
        return None
    kx, ky = lat.stub_k[stubA]
    acc = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if (dx, dy) == (0, 0):
                continue
            nb = inv.get((kx + dx, ky + dy))
            if nb is None or nb not in feet or feet[nb] is None:
                continue
            fB = feet[nb].buffer(-tol)
            o = outside.intersection(fB)
            if o.is_empty or o.area < 600:
                continue
            i = inside.intersection(fB).intersection(o.buffer(far + near + 40))
            if i.is_empty or i.area < 600:
                continue
            tif = f"{samgeo_dir}/{nb}.tif"
            si, so = strip_stats(tif, i), strip_stats(tif, o)
            if si is None or so is None:
                continue
            acc.append((score(si, so), si[2], so[2]))
    if not acc:
        return None
    w = np.array([min(a[1], a[2]) for a in acc], dtype=float)
    return float(np.average([a[0] for a in acc], weights=w)), int(sum(a[1] for a in acc)), int(sum(a[2] for a in acc))


def boundary_score(g, stub, samgeo_dir, feet, near=15, far=60):
    """Real-boundary control: inside vs outside strips across the polygon's own boundary, own tile."""
    inside = g.difference(g.buffer(-far)).difference(g.difference(g.buffer(-near)))
    outside = g.buffer(far).difference(g.buffer(near))
    fB = feet[stub].buffer(-far)
    inside, outside = inside.intersection(fB), outside.intersection(fB)
    if inside.is_empty or outside.is_empty:
        return None
    tif = f"{samgeo_dir}/{stub}.tif"
    si, so = strip_stats(tif, inside), strip_stats(tif, outside)
    if si is None or so is None:
        return None
    return score(si, so)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--pairs-csv", required=True)
    ap.add_argument("--audit-after", required=True)
    ap.add_argument("--aois", required=True)
    ap.add_argument("--samgeo-dir", required=True)
    ap.add_argument("--n-calib", type=int, default=400)
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--summary", required=True)
    args = ap.parse_args()
    rng = np.random.default_rng(0)
    lat = Lattice(args.aois)
    inv = {v: k for k, v in lat.stub_k.items()}
    dB, GB = load(args.before, "crops")
    dA, GA = load(args.after, "crops")
    stubs = set(dB.stub) | set(dA.stub)
    feet = {}
    for s in stubs:
        kx, ky = lat.stub_k[s]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = inv.get((kx + dx, ky + dy))
                if n is not None and n not in feet:
                    feet[n] = footprint(args.samgeo_dir, n)
    fidB = {f: i for i, f in enumerate(dB.fid.values)}

    # --- calibration 1: known genuine cuts (fragments the merge unioned) ---
    P = pd.read_csv(args.pairs_csv)
    P = P[P.decision.eq("merge") & P.reason.eq("same_class")]
    rows = []
    idx = rng.permutation(len(P))
    for k in idx:
        r = P.iloc[k]
        for fa in (r.fid_a, r.fid_b):
            i = fidB.get(int(fa))
            if i is None:
                continue
            res = cut_score(GB[i], dB.stub.values[i], feet, args.samgeo_dir, lat, inv)
            if res is not None:
                rows.append(dict(set="same_field", fid=int(fa), score=res[0], n_in=res[1], n_out=res[2]))
        if sum(1 for x in rows if x["set"] == "same_field") >= args.n_calib:
            break
    # --- calibration 2: real boundaries of interior polygons ---
    au = pd.read_csv(args.audit_after).set_index("fid")
    interior = [i for i, (f, s) in enumerate(zip(dA.fid.values, dA.stub.values))
                if dA.classified.values[i] and feet.get(s) is not None
                and GA[i].distance(feet[s].exterior) > 500]
    for i in rng.permutation(interior)[: args.n_calib * 2]:
        sc = boundary_score(GA[i], dA.stub.values[i], args.samgeo_dir, feet)
        if sc is not None:
            rows.append(dict(set="real_boundary", fid=int(dA.fid.values[i]), score=sc))
        if sum(1 for x in rows if x["set"] == "real_boundary") >= args.n_calib:
            break
    # --- residual truncated polygons of the merged file ---
    for i, f in enumerate(dA.fid.values):
        if f not in au.index or not bool(au.loc[f, "truncated"]) or not dA.classified.values[i]:
            continue
        res = cut_score(GA[i], dA.stub.values[i], feet, args.samgeo_dir, lat, inv)
        if res is not None:
            rows.append(dict(set="residual", fid=int(f), score=res[0], n_in=res[1], n_out=res[2],
                             boundary_action=dA.boundary_action.values[i] if "boundary_action" in dA else None,
                             beyond_cut=au.loc[f, "beyond_cut"], cut_len_m=au.loc[f, "cut_len_m"],
                             area_ha=dA.area_ha.values[i]))
    df = pd.DataFrame(rows)
    df.to_csv(args.out_csv, index=False)
    sf, rb = df[df.set == "same_field"].score, df[df.set == "real_boundary"].score
    # threshold: equal-error point between the two calibration sets
    ths = np.linspace(0, 5, 501)
    err = [(float((sf > t).mean()) + float((rb <= t).mean())) / 2 for t in ths]
    thr = float(ths[int(np.argmin(err))])
    res = df[df.set == "residual"]
    summ = dict(
        n_same_field=int(len(sf)), n_real_boundary=int(len(rb)), n_residual=int(len(res)),
        same_field_quantiles={q: round(float(sf.quantile(q)), 3) for q in (0.1, 0.25, 0.5, 0.75, 0.9)},
        real_boundary_quantiles={q: round(float(rb.quantile(q)), 3) for q in (0.1, 0.25, 0.5, 0.75, 0.9)},
        threshold=thr, equal_error_rate=round(float(min(err)), 3),
        same_field_flagged_continuous=round(float((sf <= thr).mean()), 3),
        real_boundary_flagged_boundary=round(float((rb > thr).mean()), 3),
        residual_quantiles={q: round(float(res.score.quantile(q)), 3) for q in (0.1, 0.25, 0.5, 0.75, 0.9)} if len(res) else {},
        residual_genuine_cut_n=int((res.score <= thr).sum()), residual_genuine_cut_pct=round(100 * float((res.score <= thr).mean()), 1) if len(res) else None,
        residual_genuine_cut_area_ha=round(float(res[res.score <= thr].area_ha.sum()), 1) if len(res) else None,
        residual_genuine_by_action=res.groupby(res.boundary_action.fillna("untouched")).apply(lambda s: round(float((s.score <= thr).mean()), 3)).to_dict() if len(res) else {},
        residual_genuine_by_beyond=res.groupby("beyond_cut").apply(lambda s: round(float((s.score <= thr).mean()), 3)).to_dict() if len(res) else {},
    )
    with open(args.summary, "w") as f:
        json.dump(summ, f, indent=2, default=str)
    print(json.dumps(summ, indent=2, default=str))


if __name__ == "__main__":
    main()
