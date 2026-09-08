#!/usr/bin/env python
"""
cross_year_check.py -- does another year's map hold the paddock whole where this year's is cut?

Segmentation is independent per year but the tile lattice and raster footprints are identical, so
a paddock cut at tile A's raster edge in year Y1 is cut at the same line in Y2 -- UNLESS tile B
captured it in Y2 (and failed to in Y1). For each classified polygon of Y1 this reports the best
IoU match in Y2, broken down by boundary_action, and for Y1's residual cut polygons whether a Y2
polygon covers >= --cover of it AND extends >= --beyond ha past Y1's raster footprint edge.
Aggregate only.
"""
import argparse
import json

import numpy as np
import pandas as pd
import shapely

from boundary_seam_audit import footprint, load


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--y1", required=True)
    ap.add_argument("--y2", required=True)
    ap.add_argument("--audit-y1", required=True, help="audit CSV for --y1 (truncated flags)")
    ap.add_argument("--samgeo-dir", required=True)
    ap.add_argument("--cover", type=float, default=0.8)
    ap.add_argument("--beyond", type=float, default=1.0)
    ap.add_argument("--summary", required=True)
    args = ap.parse_args()
    d1, G1 = load(args.y1, "crops")
    d2, G2 = load(args.y2, "crops")
    au = pd.read_csv(args.audit_y1).set_index("fid")
    d1 = d1.join(au[["truncated", "cut_len_m", "beyond_cut"]], on="fid")
    tree = shapely.STRtree(G2)
    feet = {}
    best_iou = np.zeros(len(d1)); repair = np.zeros(len(d1), dtype=bool); cover_best = np.zeros(len(d1))
    for i, g in enumerate(G1):
        cand = tree.query(g, predicate="intersects")
        if len(cand) == 0:
            continue
        inter = np.array([g.intersection(G2[j]).area for j in cand])
        iou = inter / np.array([g.union(G2[j]).area for j in cand])
        best_iou[i] = iou.max()
        cov = inter / g.area
        k = int(np.argmax(cov)); cover_best[i] = cov[k]
        if d1.truncated.values[i] and cov[k] >= args.cover:
            s = d1.stub.values[i]
            if s not in feet:
                feet[s] = footprint(args.samgeo_dir, s)
            beyond = G2[cand[k]].difference(feet[s]).area / 1e4 if feet[s] is not None else 0
            repair[i] = beyond >= args.beyond
    d1["best_iou"] = best_iou; d1["cover_best"] = cover_best; d1["whole_in_other_year"] = repair
    ba = d1.boundary_action.fillna("untouched") if "boundary_action" in d1 else pd.Series(["untouched"] * len(d1))
    d1["cat"] = np.where(d1.truncated & d1.beyond_cut.eq("none"), "residual_cut_" + ba, ba)
    cls = d1[d1.classified]
    out = dict(y1=args.y1, y2=args.y2, n_y1_classified=int(len(cls)),
               median_best_iou_by_cat={k: round(float(v), 3) for k, v in cls.groupby("cat").best_iou.median().items()},
               n_by_cat=cls.cat.value_counts().to_dict(),
               share_iou_ge_0_7_by_cat={k: round(float(v), 3) for k, v in cls.groupby("cat").best_iou.apply(lambda s: (s >= 0.7).mean()).items()})
    R = cls[cls.truncated & cls.beyond_cut.eq("none")]
    out["residual_cuts_classified"] = int(len(R))
    out["residual_cuts_whole_in_other_year"] = int(R.whole_in_other_year.sum())
    out["residual_cuts_whole_in_other_year_pct"] = round(100 * float(R.whole_in_other_year.mean()), 1) if len(R) else None
    out["residual_cuts_whole_by_action"] = R.groupby("cat").whole_in_other_year.mean().round(3).to_dict()
    with open(args.summary, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
