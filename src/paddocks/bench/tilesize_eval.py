#!/usr/bin/env python
"""
tilesize_eval.py -- do bigger tiles / more overlap give the same paddocks with fewer edge artefacts?

For each SAM arm directory (<stub>_filt.gpkg + <stub>.tif, EPSG:6933) and the production 3 km
reference, inside the block INTERIOR (the 18 km block shrunk by --margin m, so the big tiles'
own outer edges do not count):
  density      polygons per km2 and median ha (centroid inside the interior)
  agreement    for each production polygon, best IoU with the arm's polygons: median, share >= 0.5 / 0.7;
               and the reverse (arm -> production)
  band ratio   polygon density and median area in a 500 m band around the arm's own lattice lines
               vs. away from them (an artefact-free map has ratio ~1)
  cut share    polygons with >= 100 m of boundary within 30 m of their own raster edge
For overlap arms and the 3 km reference the merge (merge_tile_boundaries.py) is run through a
segmentation-only harness (uniform class), and the same metrics are recomputed on its output.
Aggregate only.
"""
import argparse
import glob
import json
import os
import sqlite3
import subprocess
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
from merge_tile_boundaries import Lattice  # noqa: E402
from boundary_seam_audit import footprint  # noqa: E402

D = "/scratch/xe2/cb8590/paddock-species-data/derived"
ATTR = ["stub", "poly_idx", "pred", "abstain_reason", "area_ha", "compactness", "ndvi_amp", "confidence",
        "p_canola", "p_cereal", "p_legume", "n_obs", "clear_frac", "treed_frac", "n_feat_present", "year"]


def load_arm(d, stubs):
    parts = []
    for s in stubs:
        f = f"{d}/{s}_filt.gpkg"
        if not os.path.exists(f):
            continue
        g = gpd.read_file(f).to_crs(3577)
        g["stub"] = s; g["poly_idx"] = np.arange(len(g))
        parts.append(g)
    if not parts:
        return None
    return gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs="EPSG:3577")


def pseudo_crops(g, path):
    """Segmentation-only harness: every polygon 'Cereal', so the merge rules act on geometry."""
    h = g.copy()
    h["pred"] = "Cereal"; h["abstain_reason"] = ""; h["area_ha"] = h.geometry.area / 1e4
    h["compactness"] = h.geometry.length / np.sqrt(h.geometry.area)
    for c, v in [("ndvi_amp", 0.5), ("confidence", 1.0), ("p_canola", 0.0), ("p_cereal", 1.0), ("p_legume", 0.0),
                 ("n_obs", 50), ("clear_frac", 1.0), ("treed_frac", 0.0), ("n_feat_present", 153), ("year", 2024)]:
        h[c] = v
    h = h[ATTR + ["geometry"]]
    if os.path.exists(path):
        os.remove(path)
    h.to_file(path, layer="crops", driver="GPKG")
    return path


def load_gpkg(path):
    con = sqlite3.connect(path)
    from merge_tile_boundaries import blob_to_geom
    rows = con.execute("select stub, geom from crops").fetchall()
    return gpd.GeoDataFrame({"stub": [r[0] for r in rows]}, geometry=[blob_to_geom(r[1]) for r in rows], crs="EPSG:3577")


def metrics(g, prod, interior, lat, feet, band_m=500):
    c = g.geometry.centroid
    inside = c.within(interior)
    gi = g[inside]
    A = interior.area / 1e6
    res = dict(n=int(len(gi)), per_km2=round(len(gi) / A, 3), median_ha=round(float(gi.geometry.area.median() / 1e4), 1) if len(gi) else None)
    # agreement with production (both restricted to the interior)
    pi = prod[prod.geometry.centroid.within(interior)]
    if len(gi) and len(pi):
        tree = shapely.STRtree(gi.geometry.values)
        def best(src, tgt_tree, tgt):
            out = np.zeros(len(src))
            for k, geom in enumerate(src.geometry.values):
                cand = tgt_tree.query(geom, predicate="intersects")
                if len(cand):
                    inter = shapely.area(shapely.intersection(tgt[cand], geom))
                    out[k] = (inter / (geom.area + shapely.area(tgt[cand]) - inter)).max()
            return out
        b1 = best(pi, tree, gi.geometry.values)
        b2 = best(gi, shapely.STRtree(pi.geometry.values), pi.geometry.values)
        res.update(prod_to_arm_iou_median=round(float(np.median(b1)), 3), prod_matched_ge05=round(float((b1 >= 0.5).mean()), 3),
                   prod_matched_ge07=round(float((b1 >= 0.7).mean()), 3), arm_to_prod_iou_median=round(float(np.median(b2)), 3),
                   arm_matched_ge05=round(float((b2 >= 0.5).mean()), 3))
    # band vs interior density along the arm's own lattice lines
    if lat is not None and len(gi):
        b = gi.geometry.bounds
        d = lat.dist_to_any_line(b.minx.values, b.miny.values, b.maxx.values, b.maxy.values)
        cx, cy = c[inside].x.values, c[inside].y.values
        dc = lat.dist_to_any_line(cx, cx, cy, cy)
        # band area: fraction of interior within band_m of a line, by Monte Carlo
        rng = np.random.default_rng(0); minx, miny, maxx, maxy = interior.bounds
        px = rng.uniform(minx, maxx, 20000); py = rng.uniform(miny, maxy, 20000)
        pts_in = shapely.contains_xy(interior, px, py)
        pd_ = lat.dist_to_any_line(px[pts_in], px[pts_in], py[pts_in], py[pts_in])
        band_frac = float((pd_ <= band_m).mean())
        nb, ni = int((dc <= band_m).sum()), int((dc > band_m).sum())
        dens_b = nb / (A * band_frac) if band_frac else np.nan
        dens_i = ni / (A * (1 - band_frac)) if band_frac < 1 else np.nan
        ab = gi.geometry.area.values[dc <= band_m]; ai = gi.geometry.area.values[dc > band_m]
        res.update(band_frac_of_area=round(band_frac, 3), band_density_ratio=round(dens_b / dens_i, 3) if dens_i else None,
                   band_median_ha=round(float(np.median(ab)) / 1e4, 1) if len(ab) else None,
                   interior_median_ha=round(float(np.median(ai)) / 1e4, 1) if len(ai) else None,
                   touch10=int((d <= 10).sum()))
    # cut share against own raster edge
    if feet:
        cut = 0
        for s, geom in zip(gi.stub.values, gi.geometry.values):
            fp = feet.get(s)
            if fp is not None and geom.boundary.intersection(fp.exterior.buffer(30)).length >= 100:
                cut += 1
        res["cut_share"] = round(cut / len(gi), 3) if len(gi) else None
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--margin", type=float, default=1000.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    B = a.bench
    ch = pd.read_csv(f"{B}/aois/ch36.csv")
    lat24 = Lattice(f"{D}/national2024/aois.csv")
    cores = [shapely.box(*lat24.core_bounds(*lat24.stub_k[s])) for s in ch.stub]
    block = shapely.unary_union(cores)
    interior = block.buffer(-a.margin)
    prod = load_arm(f"{D}/national2024/samgeo", ch.stub.tolist())
    feet_prod = {s: footprint(f"{D}/national2024/samgeo", s) for s in ch.stub}
    out = {"block_km2": round(block.area / 1e6, 1), "interior_km2": round(interior.area / 1e6, 1)}
    out["prod_3km"] = metrics(prod, prod, interior, lat24, feet_prod)
    os.makedirs(f"{B}/polys", exist_ok=True)
    pseudo_crops(prod, f"{B}/polys/prod_3km.gpkg")
    arms = {
        "ts_ov1750": ("ov1750", None), "ts_ov2000": ("ov2000", None),
        "ts_p9_default": ("p9", None), "ts_p9_s352": ("p9", None), "ts_p9_s768": ("p9", None),
        "ts_p9_s768_pps42": ("p9", None), "ts_p9_nobatch_pps40": ("p9", None),
        "ts_p18_default": ("p18", None), "ts_p18_s768": ("p18", None),
    }
    merged_inputs = {"prod_3km": (prod, f"{D}/national2024/aois.csv", f"{D}/national2024/samgeo")}
    for arm, (aoi, _) in arms.items():
        d = f"{B}/{arm}"
        if not os.path.isdir(d):
            continue
        stubs = pd.read_csv(f"{B}/aois/{aoi}.csv").stub.tolist()
        g = load_arm(d, stubs)
        if g is None:
            continue
        latA = Lattice(f"{B}/aois/{aoi}.csv") if len(stubs) > 1 else None
        feet = {s: footprint(d, s) for s in stubs}
        tim = glob.glob(f"{d}/timings_segment_*.csv")
        t = pd.concat([pd.read_csv(f) for f in tim]) if tim else None
        m = metrics(g, prod, interior, latA, feet)
        if t is not None:
            ok = t[t.status == "OK"]
            area_km2 = sum(feet[s].area for s in stubs if feet.get(s) is not None) / 1e6
            m.update(segment_s_total=round(float(ok.segment_s.sum()), 1), polygonise_s_total=round(float(ok.polygonise_s.sum()), 1),
                     n_raw=int(ok.n_raw.sum()), n_keep=int(ok.n_keep.sum()), raster_km2=round(area_km2, 1),
                     segment_s_per_km2=round(float(ok.segment_s.sum()) / area_km2, 3))
        out[arm] = m
        os.makedirs(f"{B}/polys", exist_ok=True)
        pseudo_crops(g, f"{B}/polys/{arm}.gpkg")          # for figures
        if arm.startswith("ts_ov"):
            merged_inputs[arm] = (g, f"{B}/aois/{aoi}.csv", d)
    # merge harness
    for name, (g, aois, samdir) in merged_inputs.items():
        wd = f"{B}/merge_{name}"; os.makedirs(wd, exist_ok=True)
        inp = pseudo_crops(g, f"{wd}/in.gpkg"); outp = f"{wd}/out.gpkg"
        if os.path.exists(outp):
            os.remove(outp)
        r = subprocess.run([sys.executable, os.path.dirname(os.path.abspath(__file__)) + "/../merge_tile_boundaries.py",
                            "--in", inp, "--out", outp, "--aois", aois, "--samgeo-dir", samdir, "--away-csv", f"{wd}/away.csv",
                            "--pairs-csv", f"{wd}/pairs.csv", "--summary", f"{wd}/summary.json"], capture_output=True, text=True)
        if r.returncode != 0:
            out[f"merged_{name}"] = {"error": r.stderr[-800:]}
            continue
        sm = json.load(open(f"{wd}/summary.json"))
        gm = load_gpkg(outp)
        latM = Lattice(aois)
        feet = {s: footprint(samdir, s) for s in gm.stub.unique()}
        mm = metrics(gm, prod, interior, latM, feet)
        mm.update(n_before=sm["n_polygons"], n_after=sm["n_polygons_after"], overlap_ha_before=sm["overlap_ha_before"],
                  overlap_ha_after=sm["overlap_ha_after"], n_raster_cut_ge_100=sm.get("n_raster_cut_ge_100"),
                  away_pct=sm["pct_away_of_all"])
        out[f"merged_{name}"] = mm
    with open(a.out, "w") as f:
        json.dump(out, f, indent=2, default=str)
    for k, v in out.items():
        print(k, v)


if __name__ == "__main__":
    main()
