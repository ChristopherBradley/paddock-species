#!/usr/bin/env python3
"""
compare_maps.py -- compare two national crop-type maps, e.g. the retired 3 km 2024 map against
the adopted 9 km 2024 map. Any pair of `crops`-schema GeoPackages works.

Two parts.
  NATIONAL  Per-map totals read straight from the GeoPackage's SQLite tables (no geometry):
            polygon count, classified share by count and by area, area by class, abstain reasons,
            median classified polygon size, and the legume share by argmax against the
            area-weighted mean predicted probability.
  WINDOWS   Geometric agreement on a random sample of tile windows. Each map's polygons whose
            centroid falls in the window are matched to the other map by best IoU
            (bench/geometry_decision.py's best_iou), in both directions. Reports the share matched
            at IoU >= 0.5, the median best IoU, polygon density, and class agreement on matched
            pairs where both polygons are classified.

Read the two maps' differences as model AND geometry together: the retired 3 km map used the
three-index classifier and was never de-duplicated across tile overlaps, the adopted 9 km map
uses the nine-index classifier and (merged file) is de-duplicated.

Aggregate only. No site-level or GRDC record is read or written.

    python3 compare_maps.py \
        --a .../national2024/national_2024_crops.gpkg --a-name "3 km (retired)" \
        --b .../national2024_9km/national_2024_crops_merged.gpkg --b-name "9 km (adopted)" \
        --aois .../national2024_9km/aois.csv --n-windows 300 \
        --out-md ../../output/MAP_COMPARISON_3KM_VS_9KM_2024.md --out-json .../compare/map_compare.json
"""
import argparse
import json
import os
import sqlite3
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "bench"))
from geometry_decision import best_iou  # noqa: E402

CLASSES = ["Canola", "Cereal", "Legume"]
def is_cls(extra=()):
    """SQL for "classified". `extra` lists abstain reasons that still carry a class, e.g.
    no_crop_shape: the 9 km run predicts every class and only flags a shape-gate failure."""
    s = "abstain_reason = '' OR abstain_reason IS NULL"
    if extra:
        s += " OR abstain_reason IN (" + ", ".join(f"'{r}'" for r in extra) + ")"
    return f"({s})"


def national(path, layer, extra=()):
    IS_CLS = is_cls(extra)
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    q = lambda s: con.execute(s).fetchall()  # noqa: E731
    n, area = q(f"SELECT COUNT(*), SUM(area_ha) FROM {layer}")[0]
    nc, ac = q(f"SELECT COUNT(*), SUM(area_ha) FROM {layer} WHERE {IS_CLS}")[0]
    by_cls = {p: {"n": k, "ha": a} for p, k, a in
              q(f"SELECT pred, COUNT(*), SUM(area_ha) FROM {layer} WHERE {IS_CLS} GROUP BY pred")}
    abst = {r: {"n": k, "ha": a} for r, k, a in
            q(f"SELECT abstain_reason, COUNT(*), SUM(area_ha) FROM {layer} WHERE NOT {IS_CLS} "
              f"GROUP BY abstain_reason")}
    pc, pe, pl = q(f"SELECT SUM(p_canola*area_ha), SUM(p_cereal*area_ha), SUM(p_legume*area_ha) "
                   f"FROM {layer} WHERE {IS_CLS}")[0]
    med = float(np.median([r[0] for r in q(f"SELECT area_ha FROM {layer} WHERE {IS_CLS}")]))
    srs = q(f"SELECT srs_id FROM gpkg_geometry_columns WHERE table_name='{layer}'")[0][0]
    tot_p = pc + pe + pl
    return dict(path=path, srs=int(srs), n=n, area_ha=area, n_cls=nc, area_cls_ha=ac,
                pct_cls_n=100 * nc / n, pct_cls_area=100 * ac / area, median_cls_ha=med,
                by_class=by_cls, abstain=abst,
                share_argmax={c: 100 * by_cls.get(c, {"ha": 0})["ha"] / ac for c in CLASSES},
                share_meanp={"Canola": 100 * pc / tot_p, "Cereal": 100 * pe / tot_p,
                             "Legume": 100 * pl / tot_p})


def window_boxes(aois_csv, n, seed, epsg):
    A = pd.read_csv(aois_csv)
    S = A.sample(n=min(n, len(A)), random_state=seed)
    x, y = Transformer.from_crs(4326, epsg, always_xy=True).transform(S.lon.values, S.lat.values)
    return [(s, (xi - h, yi - h, xi + h, yi + h)) for s, xi, yi, h in zip(S.stub, x, y, S.half_m)]


def read_box(path, layer, box, pad, extra=()):
    x0, y0, x1, y1 = box
    g = gpd.read_file(path, layer=layer, bbox=(x0 - pad, y0 - pad, x1 + pad, y1 + pad))
    g["cls"] = g.pred.where(g.abstain_reason.fillna("").isin([""] + list(extra)), None)
    return g


def windows(a, b, aois, n, seed, pad=600.0, extra=()):
    boxes = window_boxes(aois, n, seed, a["srs"])
    to_b = Transformer.from_crs(a["srs"], b["srs"], always_xy=True)
    rows, pairs = [], []
    for stub, box in boxes:
        bx = to_b.transform_bounds(*box)
        A = read_box(a["path"], a["layer"], box, pad, extra)
        B = read_box(b["path"], b["layer"], bx, pad, extra)
        if B.crs != A.crs:
            B = B.to_crs(A.crs)
        win = shapely.box(*box)
        Ain = A[A.geometry.centroid.within(win)].reset_index(drop=True)
        Bin = B[B.geometry.centroid.within(win)].reset_index(drop=True)
        iab, jab = best_iou(Ain, B)
        iba, _ = best_iou(Bin, A)
        km2 = win.area / 1e6
        rows.append(dict(stub=stub, km2=km2, nA=len(Ain), nB=len(Bin),
                         nA_cls=int(Ain.cls.notna().sum()), nB_cls=int(Bin.cls.notna().sum()),
                         A_matched=int((iab >= 0.5).sum()), B_matched=int((iba >= 0.5).sum()),
                         A_cls_matched=int(((iab >= 0.5) & Ain.cls.notna().values).sum()),
                         A_area=float(Ain.area_ha.sum()), A_area_matched=float(Ain.area_ha[iab >= 0.5].sum()),
                         B_area=float(Bin.area_ha.sum()), B_area_matched=float(Bin.area_ha[iba >= 0.5].sum()),
                         iou_ab=iab.tolist(), iou_ba=iba.tolist()))
        for k in np.flatnonzero(iab >= 0.5):
            pairs.append((Ain.cls.iat[k], B.cls.iat[jab[k]]))
    W = pd.DataFrame(rows)
    P = pd.DataFrame(pairs, columns=["a", "b"])
    both = P.dropna()
    iab = np.concatenate([np.asarray(v) for v in W.iou_ab]) if len(W) else np.array([])
    iba = np.concatenate([np.asarray(v) for v in W.iou_ba]) if len(W) else np.array([])
    return dict(
        n_windows=len(W), km2=float(W.km2.sum()),
        density_a=float(W.nA.sum() / W.km2.sum()), density_b=float(W.nB.sum() / W.km2.sum()),
        cls_density_a=float(W.nA_cls.sum() / W.km2.sum()), cls_density_b=float(W.nB_cls.sum() / W.km2.sum()),
        pct_a_matched=100 * W.A_matched.sum() / max(W.nA.sum(), 1),
        pct_b_matched=100 * W.B_matched.sum() / max(W.nB.sum(), 1),
        pct_a_cls_matched=100 * W.A_cls_matched.sum() / max(W.nA_cls.sum(), 1),
        pct_a_area_matched=100 * W.A_area_matched.sum() / max(W.A_area.sum(), 1e-9),
        pct_b_area_matched=100 * W.B_area_matched.sum() / max(W.B_area.sum(), 1e-9),
        median_iou_ab=float(np.median(iab)) if len(iab) else float("nan"),
        median_iou_ba=float(np.median(iba)) if len(iba) else float("nan"),
        n_pairs_both_cls=int(len(both)),
        pct_class_agree=100 * float((both.a == both.b).mean()) if len(both) else float("nan"),
        confusion=pd.crosstab(both.a, both.b).to_dict() if len(both) else {})


def fmt(x, d=1):
    return f"{x:,.{d}f}"


def report(a, b, W, args):
    L = [f"# National map comparison: {args.a_name} vs {args.b_name}", "",
         f"Generated by `src/paddocks/compare_maps.py`. Aggregate only.", "",
         f"- A = {args.a_name}: `{a['path']}` (layer `{a['layer']}`)",
         f"- B = {args.b_name}: `{b['path']}` (layer `{b['layer']}`)",
         "- classified = empty `abstain_reason`" + (f" or one of {args.count_as_classified} (still carries a class)"
                                                  if args.count_as_classified else ""), "",
         "Differences mix model and geometry. The retired 3 km map used the three-index classifier and "
         "was never de-duplicated across tile overlaps, so its counts include polygons duplicated in "
         "the ~350 m overlap bands. Read the window matching, not the raw counts, for geometry.", "",
         "## 1. National totals", "",
         f"| | {args.a_name} | {args.b_name} |", "|---|---:|---:|",
         f"| polygons | {a['n']:,} | {b['n']:,} |",
         f"| classified polygons | {a['n_cls']:,} ({fmt(a['pct_cls_n'])}%) | {b['n_cls']:,} ({fmt(b['pct_cls_n'])}%) |",
         f"| total polygon area (ha) | {fmt(a['area_ha'], 0)} | {fmt(b['area_ha'], 0)} |",
         f"| classified area (ha) | {fmt(a['area_cls_ha'], 0)} ({fmt(a['pct_cls_area'])}%) | {fmt(b['area_cls_ha'], 0)} ({fmt(b['pct_cls_area'])}%) |",
         f"| median classified polygon (ha) | {fmt(a['median_cls_ha'])} | {fmt(b['median_cls_ha'])} |"]
    for c in CLASSES:
        ca, cb = a["by_class"].get(c, {"n": 0, "ha": 0}), b["by_class"].get(c, {"n": 0, "ha": 0})
        L.append(f"| {c.lower()} area (ha), share of classified | {fmt(ca['ha'], 0)} ({fmt(a['share_argmax'][c])}%) "
                 f"| {fmt(cb['ha'], 0)} ({fmt(b['share_argmax'][c])}%) |")
    for c in CLASSES:
        L.append(f"| {c.lower()} share by area-weighted mean probability | {fmt(a['share_meanp'][c])}% | {fmt(b['share_meanp'][c])}% |")
    reasons = sorted(set(a["abstain"]) | set(b["abstain"]))
    L += ["", "Abstain reasons (polygons):", "", f"| reason | {args.a_name} | {args.b_name} |", "|---|---:|---:|"]
    for r in reasons:
        L.append(f"| `{r}` | {a['abstain'].get(r, {'n': 0})['n']:,} | {b['abstain'].get(r, {'n': 0})['n']:,} |")
    L += ["", f"## 2. Window matching ({W['n_windows']} random tile windows, {fmt(W['km2'], 0)} km², seed {args.seed})", "",
          "A polygon counts in a window when its centroid falls inside it. Each is matched to the other map's "
          "best-overlapping polygon by IoU, candidates read with a 600 m margin.", "",
          f"| | {args.a_name} | {args.b_name} |", "|---|---:|---:|",
          f"| polygons per km² | {fmt(W['density_a'], 2)} | {fmt(W['density_b'], 2)} |",
          f"| classified polygons per km² | {fmt(W['cls_density_a'], 2)} | {fmt(W['cls_density_b'], 2)} |",
          f"| matched in the other map at IoU >= 0.5 (count) | {fmt(W['pct_a_matched'])}% | {fmt(W['pct_b_matched'])}% |",
          f"| matched at IoU >= 0.5 (area) | {fmt(W['pct_a_area_matched'])}% | {fmt(W['pct_b_area_matched'])}% |",
          f"| median best IoU | {W['median_iou_ab']:.2f} | {W['median_iou_ba']:.2f} |", "",
          f"Class agreement on {W['n_pairs_both_cls']:,} matched pairs (IoU >= 0.5) where both polygons are classified: "
          f"**{fmt(W['pct_class_agree'])}%**.", "", f"Rows = {args.a_name}, columns = {args.b_name}:", ""]
    conf = pd.DataFrame(W["confusion"]).T if W["confusion"] else pd.DataFrame()
    if len(conf):
        conf = pd.DataFrame(W["confusion"]).fillna(0).astype(int)
        L += ["| | " + " | ".join(conf.columns) + " |", "|---|" + "---:|" * len(conf.columns)]
        for r, row in conf.iterrows():
            L.append(f"| {r} | " + " | ".join(f"{v:,}" for v in row.values) + " |")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True); ap.add_argument("--a-layer", default="crops"); ap.add_argument("--a-name", default="A")
    ap.add_argument("--b", required=True); ap.add_argument("--b-layer", default="crops"); ap.add_argument("--b-name", default="B")
    ap.add_argument("--aois", required=True, help="aois.csv whose tiles define the sample windows")
    ap.add_argument("--n-windows", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--count-as-classified", nargs="*", default=[],
                    help="abstain reasons that still carry a class and count as classified, e.g. no_crop_shape")
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--out-json", required=True)
    args = ap.parse_args()
    a = national(args.a, args.a_layer, args.count_as_classified); a["layer"] = args.a_layer
    b = national(args.b, args.b_layer, args.count_as_classified); b["layer"] = args.b_layer
    print("national totals done", flush=True)
    W = windows(a, b, args.aois, args.n_windows, args.seed, extra=args.count_as_classified)
    os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
    json.dump(dict(a=a, b=b, windows=W), open(args.out_json, "w"), indent=1, default=str)
    open(args.out_md, "w").write(report(a, b, W, args))
    print(f"wrote {args.out_md}")


if __name__ == "__main__":
    main()
