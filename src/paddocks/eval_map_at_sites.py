#!/usr/bin/env python
"""
eval_map_at_sites.py -- score a predicted-polygon product at labelled trial sites.

For each site (lat/lon/Year/crop) take the polygon that contains it; when two tiles' views
contain it, prefer the tile whose lattice square holds the site (the merge's ownership rule),
else the largest. Report per-class precision/recall/F1 and macro F1 over the group3 classes,
the abstention and no-polygon rates, and how the polygon's area compares with the trial
paddock area in the label set. Per-site output is SENSITIVE (kept under derived/); the JSON
summary is aggregate only.
"""
import argparse
import glob
import json
import os
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from merge_tile_boundaries import Lattice     # noqa: E402
from train_species import GROUP               # noqa: E402

CLASSES = ["Canola", "Cereal", "Legume"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", required=True, help="sites_SENSITIVE.csv from bench/site_tiles.py")
    ap.add_argument("--pred", required=True, nargs="+", help="predict_tile.py GeoPackage(s) or globs")
    ap.add_argument("--layer", default="paddocks")
    ap.add_argument("--aois", required=True, help="aois.csv of the product's lattice (ownership)")
    ap.add_argument("--year", type=int, default=None, help="restrict to one year of sites")
    ap.add_argument("--name", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-sites", required=True, help="per-site CSV, must be *_SENSITIVE.csv")
    a = ap.parse_args()
    assert "SENSITIVE" in a.out_sites
    S = pd.read_csv(a.sites)
    if a.year:
        S = S[S.Year == a.year]
    S = S[S.crop.isin(GROUP)].copy()
    S["label3"] = S.crop.map(GROUP)
    files = sorted({f for p in a.pred for f in glob.glob(p)})
    if not files:
        raise SystemExit("no prediction files")
    P = pd.concat([gpd.read_file(f, layer=a.layer) for f in files], ignore_index=True)
    P = gpd.GeoDataFrame(P, geometry="geometry", crs="EPSG:3577")
    P["abstain_reason"] = P.abstain_reason.fillna("")
    # A site is matched only to polygons of its own year. Every product stub embeds the year
    # (nlum_2023_r..., nlum9_2024_r...); without this a pooled run over two years'
    # predictions matched 92 of 360 sites to the other year's polygon (2026-09-09).
    P["poly_year"] = pd.to_numeric(P.stub.str.extract(r"_(\d{4})_")[0], errors="coerce")
    lat = Lattice(a.aois)
    pts = gpd.GeoDataFrame(S, geometry=gpd.points_from_xy(S.x, S.y), crs="EPSG:3577")
    tree = shapely.STRtree(P.geometry.values)
    rows = []
    for i, r in pts.iterrows():
        cand = tree.query(r.geometry, predicate="within")
        cand = [i for i in cand if np.isnan(P.poly_year.iat[i]) or int(P.poly_year.iat[i]) == int(r.Year)]
        rec = dict(TrialCode=r.TrialCode, Year=int(r.Year), crop=r.crop, label3=r.label3, label_area_ha=r.get("area_ha"))
        if len(cand) == 0:
            rec.update(found=False, pred=None, abstain_reason="no_polygon", poly_area_ha=np.nan, stub=None, n_views=0)
        else:
            c = P.iloc[cand].copy()
            kk = lat.k_from_xy(np.array([r.x]), np.array([r.y])); site_k = (int(kk[0][0]), int(kk[1][0]))
            c["owner"] = [lat.stub_k.get(s) == site_k for s in c.stub]
            c = c.sort_values(["owner", "area_ha"], ascending=[False, False])
            b = c.iloc[0]
            rec.update(found=True, pred=b.pred if isinstance(b.pred, str) else None, abstain_reason=b.abstain_reason or "",
                       poly_area_ha=float(b.area_ha), stub=b.stub, n_views=int(len(c)), owner=bool(b.owner),
                       p_canola=b.get("p_canola"), p_cereal=b.get("p_cereal"), p_legume=b.get("p_legume"))
        rows.append(rec)
    R = pd.DataFrame(rows)
    R.to_csv(a.out_sites, index=False)
    scored = R[R.found & (R.abstain_reason == "") & R.pred.notna()]
    summ = dict(name=a.name, n_sites=int(len(R)), n_found=int(R.found.sum()), n_scored=int(len(scored)),
                no_polygon=int((~R.found).sum()), abstained=int((R.found & (R.abstain_reason != "")).sum()),
                abstain_reasons=R[R.found].abstain_reason.replace("", "classified").value_counts().to_dict(),
                by_class={})
    y, yh = scored.label3.values, scored.pred.values
    for k in CLASSES:
        tp = int(((y == k) & (yh == k)).sum()); fp = int(((y != k) & (yh == k)).sum()); fn = int(((y == k) & (yh != k)).sum())
        pr = tp / (tp + fp) if tp + fp else 0.0; rc = tp / (tp + fn) if tp + fn else 0.0
        summ["by_class"][k] = dict(n=int((y == k).sum()), precision=round(pr, 3), recall=round(rc, 3),
                                   f1=round(2 * pr * rc / (pr + rc), 3) if pr + rc else 0.0)
    summ["macro_f1"] = round(float(np.mean([v["f1"] for v in summ["by_class"].values()])), 3)
    summ["accuracy"] = round(float((y == yh).mean()), 3) if len(scored) else None
    summ["balanced_accuracy"] = round(float(np.mean([summ["by_class"][k]["recall"] for k in CLASSES])), 3)
    # "coverage-adjusted" recall: sites with no polygon or an abstention count as misses
    allr = R[R.label3.notna()]
    summ["recall_all_sites_by_class"] = {k: round(float(((allr.label3 == k) & (allr.pred == k) & (allr.abstain_reason == "")).sum() / max((allr.label3 == k).sum(), 1)), 3) for k in CLASSES}
    conf = pd.crosstab(scored.label3, scored.pred).reindex(index=CLASSES, columns=CLASSES, fill_value=0)
    summ["confusion_rows_true_cols_pred"] = conf.values.tolist()
    ok = R[R.found & R.label_area_ha.notna() & (R.label_area_ha > 0)]
    lr = np.log(ok.poly_area_ha / ok.label_area_ha)
    summ["area_vs_label"] = dict(n=int(len(ok)), median_log_ratio=round(float(lr.median()), 3), median_abs_log_ratio=round(float(lr.abs().median()), 3),
                                 within_factor_2=round(float((lr.abs() <= np.log(2)).mean()), 3), within_factor_1_5=round(float((lr.abs() <= np.log(1.5)).mean()), 3),
                                 poly_median_ha=round(float(ok.poly_area_ha.median()), 1), label_median_ha=round(float(ok.label_area_ha.median()), 1))
    summ["multi_view_sites"] = int((R.n_views > 1).sum())
    with open(a.out_json, "w") as f:
        json.dump(summ, f, indent=2)
    print(json.dumps(summ, indent=2))


if __name__ == "__main__":
    main()
