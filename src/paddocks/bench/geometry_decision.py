#!/usr/bin/env python
"""
geometry_decision.py -- production 3 km tiles vs candidate tilings, each predicted and merged.

For every arm with predictions (predict_tile.py output, layer 'paddocks'):
  1. write a crops-schema 'before' GeoPackage restricted to the block,
  2. run merge_tile_boundaries.py with the arm's own lattice and raster footprints,
  3. run boundary_seam_audit.py on the merged file,
  4. score the merged product inside the block interior: density, size, class shares and areas,
     residual overlap, raster-edge cut share, band density ratio, agreement with the merged
     production block (IoU-matched shares both ways, class agreement on matched pairs),
  5. cost per national year from this round's per-tile timings (normalbw CPU stages, fp16 SAM).
Also writes the windows where production and a candidate disagree most, for the figures.
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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE + "/..")
from merge_tile_boundaries import Lattice, blob_to_geom      # noqa: E402
from boundary_seam_audit import footprint                    # noqa: E402

D = "/scratch/xe2/cb8590/paddock-species-data/derived"
PY = sys.executable
ATTR = ["stub", "poly_idx", "pred", "abstain_reason", "area_ha", "compactness", "ndvi_amp", "confidence",
        "p_canola", "p_cereal", "p_legume", "n_obs", "clear_frac", "treed_frac", "n_feat_present", "year"]
N_TILES_3KM = 99465


def to_crops(g, path):
    h = g.copy()
    for c in ATTR:
        if c not in h:
            h[c] = np.nan
    h = h[ATTR + ["geometry"]]
    if os.path.exists(path):
        os.remove(path)
    h.to_file(path, layer="crops", driver="GPKG")


def load_crops(path):
    con = sqlite3.connect(path)
    cols = [r[1] for r in con.execute("PRAGMA table_info(crops)")]
    want = [c for c in ["fid", "stub", "pred", "abstain_reason", "area_ha", "boundary_action", "class_conflict",
                        "raster_cut_m", "clip_ha", "merge_n"] if c in cols]
    rows = con.execute(f"SELECT {', '.join(want)}, geom FROM crops").fetchall()
    g = gpd.GeoDataFrame([dict(zip(want, r[:-1])) for r in rows], geometry=[blob_to_geom(r[-1]) for r in rows], crs="EPSG:3577")
    g["abstain_reason"] = g["abstain_reason"].fillna("")
    g["classified"] = (g.abstain_reason == "") & g.pred.notna()
    return g


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-1500:])
    return r


def best_iou(src, tgt):
    if not len(src) or not len(tgt):
        return np.zeros(len(src)), np.full(len(src), -1)
    tree = shapely.STRtree(tgt.geometry.values)
    out, idx = np.zeros(len(src)), np.full(len(src), -1)
    T = tgt.geometry.values
    for k, g in enumerate(src.geometry.values):
        c = tree.query(g, predicate="intersects")
        if len(c):
            inter = shapely.area(shapely.intersection(T[c], g))
            iou = inter / (g.area + shapely.area(T[c]) - inter)
            j = int(np.argmax(iou)); out[k], idx[k] = iou[j], c[j]
    return out, idx


def score(g, prod, interior, lat, band_m=500):
    c = g.geometry.centroid
    gi = g[c.within(interior)].copy()
    A = interior.area / 1e6
    cls = gi[gi.classified]
    res = dict(n=int(len(gi)), n_classified=int(len(cls)), per_km2=round(len(gi) / A, 3),
               classified_per_km2=round(len(cls) / A, 3),
               median_ha=round(float(gi.geometry.area.median() / 1e4), 1) if len(gi) else None,
               classified_median_ha=round(float(cls.geometry.area.median() / 1e4), 1) if len(cls) else None,
               area_ha_by_class={k: round(float(v) / 1e4, 1) for k, v in cls.groupby("pred").geometry.apply(lambda s: s.area.sum()).items()},
               abstained_area_ha=round(float(gi[~gi.classified].geometry.area.sum() / 1e4), 1),
               classified_area_ha=round(float(cls.geometry.area.sum() / 1e4), 1),
               abstain_reasons=gi.abstain_reason.replace("", "classified").value_counts().to_dict())
    if "raster_cut_m" in gi:
        rc = pd.to_numeric(gi.raster_cut_m, errors="coerce").fillna(0)
        res["cut_share_classified"] = round(float((rc[gi.classified] >= 100).mean()), 3) if len(cls) else None
    if "class_conflict" in gi:
        res["class_conflicts"] = int(pd.to_numeric(gi.class_conflict, errors="coerce").fillna(0).sum())
    # overlap within the interior
    G = gi.geometry.values
    tree = shapely.STRtree(G); ii, jj = tree.query(G, predicate="intersects"); m = ii < jj
    inter = shapely.area(shapely.intersection(G[ii[m]], G[jj[m]]))
    res["overlap_ha"] = round(float(inter[inter > 0].sum() / 1e4), 1)
    res["overlap_pct_area"] = round(100 * float(inter[inter > 0].sum()) / max(float(shapely.area(G).sum()), 1), 2)
    # band ratio on own lattice
    if lat is not None:
        cx, cy = c[c.within(interior)].x.values, c[c.within(interior)].y.values
        dc = lat.dist_to_any_line(cx, cx, cy, cy)
        rng = np.random.default_rng(0); minx, miny, maxx, maxy = interior.bounds
        px, py = rng.uniform(minx, maxx, 20000), rng.uniform(miny, maxy, 20000)
        pin = shapely.contains_xy(interior, px, py)
        pdd = lat.dist_to_any_line(px[pin], px[pin], py[pin], py[pin])
        bf = float((pdd <= band_m).mean())
        nb, ni = int((dc <= band_m).sum()), int((dc > band_m).sum())
        res["band_density_ratio"] = round((nb / (A * bf)) / (ni / (A * (1 - bf))), 3) if (0 < bf < 1 and ni) else None
    # agreement with production (classified polygons both sides)
    pi = prod[prod.geometry.centroid.within(interior) & prod.classified]
    if len(cls) and len(pi):
        b1, k1 = best_iou(pi, cls); b2, k2 = best_iou(cls, pi)
        same = [(pi.pred.values[i] == cls.pred.values[k1[i]]) for i in range(len(pi)) if b1[i] >= 0.5]
        res.update(prod_matched_ge05=round(float((b1 >= 0.5).mean()), 3), prod_matched_ge07=round(float((b1 >= 0.7).mean()), 3),
                   prod_to_arm_iou_median=round(float(np.median(b1)), 3), arm_matched_ge05=round(float((b2 >= 0.5).mean()), 3),
                   arm_matched_ge07=round(float((b2 >= 0.7).mean()), 3), class_agreement_on_matches=round(float(np.mean(same)), 3) if same else None,
                   n_prod_unmatched=int((b1 < 0.5).sum()), n_arm_unmatched=int((b2 < 0.5).sum()))
    return res


def sam_wall_per_tile(B, arm_dir_name):
    """Wall seconds per tile of a SAM arm = (job elapsed - model load) / tiles, from the BENCH line
    the bench_sam.pbs job wrote. segment_s alone misses the composite read, polygonise, filter and
    GeoPackage write, which add 20-50 % (BENCH_KSU.md sec 2 priced by job SU, which includes them)."""
    import re
    LOGS = "/scratch/xe2/cb8590/paddock-species-logs"
    jobs = [l.split()[1].split(".")[0] for l in open(f"{B}/jobs.txt") if l.strip() and l.split()[0] in ("fx1", "fx2", "sam_grid_fp16")]
    for jid in jobs:
        for f in glob.glob(f"{LOGS}/{jid}.gadi-pbs.OU"):
            for line in open(f, errors="replace"):
                m = re.search(r"BENCH sam arm=(\S+) elapsed=(\d+)", line)
                if m and m.group(1).rstrip("/").endswith("/" + arm_dir_name):
                    fs = glob.glob(f"{B}/{arm_dir_name}/timings_segment_*.csv")
                    t = pd.concat([pd.read_csv(x) for x in fs])
                    return (float(m.group(2)) - float(t.model_load_s.iloc[0])) / len(t), int(len(t))
    return None


def per_tile_s(pattern, col):
    fs = glob.glob(pattern)
    if not fs:
        return None
    t = pd.concat([pd.read_csv(f) for f in fs]); t = t[t.status == "OK"] if "status" in t else t
    return float(t[col].median()), int(len(t))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--margin", type=float, default=1000.0)
    ap.add_argument("--merge-args", default="", help="extra merge_tile_boundaries.py flags, e.g. '--cover-min 0'")
    ap.add_argument("--suffix", default="", help="output sub-dir suffix per arm, e.g. _norescue")
    ap.add_argument("--only", default="", help="comma list of arms to run (default all)")
    a = ap.parse_args()
    B, O = a.bench, a.out_dir
    os.makedirs(O, exist_ok=True)
    ch = pd.read_csv(f"{B}/aois/ch36.csv")
    lat24 = Lattice(f"{D}/national2024/aois.csv")
    block = shapely.unary_union([shapely.box(*lat24.core_bounds(*lat24.stub_k[s])) for s in ch.stub])
    interior = block.buffer(-a.margin)

    # arms: name -> (predicted gpkg, aois, samgeo dir, lattice spacing m, tile half m)
    arms = {
        "prod_3km": (None, f"{D}/national2024/aois.csv", f"{D}/national2024/samgeo", 3000, 1500),
        "ov2000": (f"{B}/pred_fx_ov2000/pred.gpkg", f"{B}/aois/ov2000.csv", f"{B}/tiles", 3000, 2000),
        "ov2500": (f"{B}/pred_fx_ov2500/pred.gpkg", f"{B}/aois/ov2500.csv", f"{B}/tiles", 3000, 2500),
        "p9": (f"{B}/pred_fx_p9/pred.gpkg", f"{B}/aois/p9.csv", f"{B}/tiles", 9000, 4500),
        "p9ov1000": (f"{B}/pred_fx_p9ov1000/pred.gpkg", f"{B}/aois/p9ov1000.csv", f"{B}/tiles", 9000, 5000),
        "p9ov2000": (f"{B}/pred_fx_p9ov2000/pred.gpkg", f"{B}/aois/p9ov2000.csv", f"{B}/tiles", 9000, 5500),
        # the FINAL configuration: EPSG:3577 composites, half_m 4850 (350 m buffer), SAM+predict co-scheduled
        "p9_3577": (f"{B}/pred_p9_3577/p_*.gpkg", f"{B}/aois/p9_3577.csv", f"{B}/tiles_3577", 9000, 4850),
    }
    out = {"block_km2": round(block.area / 1e6, 1), "interior_km2": round(interior.area / 1e6, 1)}
    merged = {}
    for name, (pred, aois, samdir, E, half) in arms.items():
        if a.only and name not in a.only.split(","):
            continue
        wd = f"{O}/{name}{a.suffix}"; os.makedirs(wd, exist_ok=True)
        before = f"{wd}/before.gpkg"
        if name == "prod_3km":
            src = f"{B}/prod_block_before.gpkg"
            if not os.path.exists(src):
                raise SystemExit("run: clip production block first (prod_block_before.gpkg)")
            g = gpd.read_file(src)
        else:
            pfiles = sorted(glob.glob(pred))
            if not pfiles:
                print("skip", name, "(no predictions yet)"); continue
            g = gpd.GeoDataFrame(pd.concat([gpd.read_file(f, layer="paddocks") for f in pfiles], ignore_index=True), crs="EPSG:3577")
        to_crops(g, before)
        after = f"{wd}/after.gpkg"
        if os.path.exists(after):
            os.remove(after)
        run([PY, f"{HERE}/../merge_tile_boundaries.py", "--in", before, "--out", after, "--aois", aois, "--samgeo-dir", samdir,
             "--away-csv", f"{wd}/away.csv", "--pairs-csv", f"{wd}/pairs.csv", "--summary", f"{wd}/merge_summary.json"] + a.merge_args.split())
        run([PY, f"{HERE}/../boundary_seam_audit.py", "--gpkg", after, "--aois", aois, "--samgeo-dir", samdir,
             "--out-csv", f"{wd}/audit.csv", "--summary", f"{wd}/audit.json"])
        merged[name] = (load_crops(after), Lattice(aois), json.load(open(f"{wd}/merge_summary.json")), json.load(open(f"{wd}/audit.json")))
    if "prod_3km" not in merged:      # a partial run: score against the default-merged production block
        merged_prod = load_crops(f"{O}/prod_3km/after.gpkg")
        prod = merged_prod
    else:
        prod = merged["prod_3km"][0]
    for name, (g, lat, ms, au) in merged.items():
        r = score(g, prod, interior, lat)
        r.update(n_before=ms["n_polygons"], n_after=ms["n_polygons_after"], merge_overlap_ha_before=ms["overlap_ha_before"],
                 merge_overlap_ha_after=ms["overlap_ha_after"], away_pct=ms["pct_away_of_all"],
                 audit_truncated_classified=au.get("n_truncated_classified"), audit_beyond_cut=au.get("beyond_cut_counts_classified"),
                 audit_overlap_pct=au.get("overlap_pct_of_area"))
        # cost per national year (normalbw CPU stages 1.25 SU/h; gpuvolta 36 SU/h)
        E, half = arms[name][3], arms[name][4]
        n_tiles = N_TILES_3KM * (3000 / E) ** 2
        stub_prefix = {"prod_3km": "nlum_2024", "ov2000": "ov2000", "ov2500": "ov2500", "p9": "p9_", "p9ov1000": "p9ov1000", "p9ov2000": "p9ov2000", "p9_3577": "p9b_"}[name]
        seg = sam_wall_per_tile(B, f"fx_{name if name != 'prod_3km' else 'ch36'}") if name != "p9_3577" else None
        seg_gpu = per_tile_s(f"{B}/{'tiles_3577' if name == 'p9_3577' else 'fx_' + (name if name != 'prod_3km' else 'ch36')}/timings_segment_*.csv", "segment_s")
        ps = per_tile_s(f"{B}/tiles/timings_presegment_*.csv", "seconds") if name != "prod_3km" else per_tile_s(f"{B}/ps2021_bw8/timings_presegment_*.csv", "seconds")
        if name != "prod_3km":
            fs = glob.glob(f"{B}/{'tiles_3577' if name == 'p9_3577' else 'tiles'}/timings_presegment_*.csv")
            t = pd.concat([pd.read_csv(f) for f in fs]); t = t[(t.status == "OK") & t.stub.str.startswith(stub_prefix)]
            ps = (float(t.seconds.median()), int(len(t))) if len(t) else None
        pr = (per_tile_s(f"{B}/pred_p9_3577/timings_predict.csv", "total_s") if name == "p9_3577" else
              per_tile_s(f"{B}/pred_fx_{name}/*_timings.csv", "total_s") if name != "prod_3km" else per_tile_s(f"{B}/pred_fx_prod36/*_timings.csv", "total_s"))
        cost = {}
        if seg: cost["sam_s_per_tile"] = round(seg[0], 2); cost["sam_su_year"] = round(n_tiles * seg[0] / 3600 * 36)
        if seg_gpu: cost["sam_gpu_s_per_tile"] = round(seg_gpu[0], 2)
        if ps: cost["presegment_s_per_tile"] = round(ps[0], 1); cost["presegment_su_year"] = round(n_tiles * ps[0] / 3600 * 1.25)
        if pr: cost["predict_s_per_tile"] = round(pr[0], 1); cost["predict_su_year"] = round(n_tiles * pr[0] / 3600 * 1.25)
        if seg and ps and pr:
            cost["total_su_year"] = cost["sam_su_year"] + cost["presegment_su_year"] + cost["predict_su_year"]
        cost["n_tiles_national"] = int(n_tiles)
        r["cost"] = cost
        out[name] = r
        print(name, json.dumps(r, default=str)[:600])
    # disagreement windows: production polygons unmatched in each candidate, clustered
    for name, (g, lat, ms, au) in merged.items():
        if name == "prod_3km":
            continue
        pi = prod[prod.geometry.centroid.within(interior) & prod.classified]
        cls = g[g.classified]
        b1, _ = best_iou(pi, cls); b2, _ = best_iou(cls[cls.geometry.centroid.within(interior)], pi)
        un = pd.concat([pi[b1 < 0.5].geometry.centroid, cls[cls.geometry.centroid.within(interior)][b2 < 0.5].geometry.centroid])
        if not len(un):
            continue
        cell = 1500.0
        keys = pd.DataFrame({"kx": np.floor(un.x / cell), "ky": np.floor(un.y / cell)})
        top = keys.value_counts().head(6)
        rows = [dict(name=f"{name}_dis{i + 1}", x=round((k[0] + 0.5) * cell), y=round((k[1] + 0.5) * cell), half_m=800,
                     note=f"{n} unmatched polygons (IoU<0.5) in this 1.5 km cell") for i, (k, n) in enumerate(top.items())]
        pd.DataFrame(rows).to_csv(f"{O}/{name}{a.suffix}/disagree_windows.csv", index=False)
    jp = f"{O}/geometry_decision{a.suffix}.json"
    if a.only and os.path.exists(jp):      # a partial run adds/refreshes its arms, keeps the rest
        prev = json.load(open(jp)); prev.update(out); out = prev
    with open(jp, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print("wrote", f"{O}/geometry_decision.json")


if __name__ == "__main__":
    main()
