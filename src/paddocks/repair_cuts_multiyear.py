#!/usr/bin/env python
"""
repair_cuts_multiyear.py -- extend raster-edge-cut polygons with another year's whole view.

The tile lattice and raster footprints are identical every year, so a paddock that tile A cuts at
its raster edge is cut at the same line every year -- but whether tile B captured it (so the merge
could union the two views) varies year to year with SAM. When year Y's merged map still holds a
cut view of a paddock and a DONOR year's merged map holds it whole, the whole view's part beyond
the cut is grafted on.

A polygon is repaired only if ALL of:
  cut      -- >= --min-cut m of its boundary lies within --tol m of its own tile's raster edge;
  image    -- the neighbour composite says the field continues past the cut (cut_continuity score
              <= --thr), unless --no-image-test;
  donor    -- one donor polygon covers >= --cover of it, and the part of that donor beyond the
              polygon, outside other kept polygons of year Y, touching the cut, is >= --min-add ha
              and <= --max-add-ratio x the polygon's area;
  shape    -- the result is one polygon, <= --max-area-ha and compactness <= --max-compactness.
Attributes are kept (the class was decided on the paddock's larger part); area_ha/compactness are
recomputed; boundary_action='repaired', repair_from=<donor>, repair_added_ha written.

`validate` re-cuts year Y's own M1 union polygons at their larger fragment's raster edge (a known
whole paddock, known cut line) and repairs them from the donor, scoring IoU against the truth.
Aggregate only.
"""
import argparse
import json
import shutil
import sqlite3

import numpy as np
import pandas as pd
import shapely
from shapely.ops import unary_union

from merge_tile_boundaries import Lattice, geom_to_blob, register_gpkg_functions
from boundary_seam_audit import footprint, load
from cut_continuity import cut_score


def cut_len(g, fp, tol):
    return g.boundary.intersection(fp.exterior.buffer(tol)).length


def find_repair(g, stub, feet, donors, dtree, others, otree, args):
    """Return (added_geom, donor_idx, reason)."""
    cand = dtree.query(g, predicate="intersects")
    if len(cand) == 0:
        return None, None, "no_donor_overlap"
    cov = np.array([g.intersection(donors[j]).area for j in cand]) / g.area
    k = int(np.argmax(cov))
    if cov[k] < args.cover:
        return None, None, "donor_cover_below_min"
    d = donors[cand[k]]
    added = d.difference(g)
    oth = otree.query(added, predicate="intersects")
    if len(oth):
        added = added.difference(unary_union([others[j] for j in oth]))
    added = added.buffer(0)
    if added.is_empty:
        return None, cand[k], "nothing_to_add"
    # keep only parts that touch the cut
    cutzone = feet[stub].exterior.buffer(args.tol + 10)
    parts = [p for p in (added.geoms if added.geom_type == "MultiPolygon" else [added]) if p.intersects(cutzone) and p.area >= 2000]
    if not parts:
        return None, cand[k], "added_part_not_at_cut"
    added = unary_union(parts)
    if added.area / 1e4 < args.min_add:
        return None, cand[k], "added_below_min"
    if added.area > args.max_add_ratio * g.area:
        return None, cand[k], "added_over_ratio"
    u = unary_union([g, added]).buffer(0)
    if u.geom_type != "Polygon":
        return None, cand[k], "result_not_single_polygon"
    if u.area / 1e4 > args.max_area_ha:
        return None, cand[k], "result_over_max_area"
    if u.length / np.sqrt(u.area) > args.max_compactness:
        return None, cand[k], "result_over_max_compactness"
    return u, cand[k], "repaired"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["repair", "validate"])
    ap.add_argument("--in", dest="inp", required=True, help="year Y merged GeoPackage")
    ap.add_argument("--donor", required=True, action="append", help="donor merged GeoPackage(s)")
    ap.add_argument("--out", help="repaired GeoPackage (repair mode)")
    ap.add_argument("--aois", required=True)
    ap.add_argument("--samgeo-dir", required=True)
    ap.add_argument("--tol", type=float, default=30.0)
    ap.add_argument("--min-cut", type=float, default=100.0)
    ap.add_argument("--thr", type=float, default=0.61, help="cut_continuity threshold (calibrated)")
    ap.add_argument("--no-image-test", action="store_true")
    ap.add_argument("--cover", type=float, default=0.8)
    ap.add_argument("--min-add", type=float, default=1.0)
    ap.add_argument("--max-add-ratio", type=float, default=3.0)
    ap.add_argument("--max-area-ha", type=float, default=300.0)
    ap.add_argument("--max-compactness", type=float, default=8.0)
    ap.add_argument("--decisions-csv", required=True)
    ap.add_argument("--summary", required=True)
    args = ap.parse_args()
    lat = Lattice(args.aois)
    inv = {v: k for k, v in lat.stub_k.items()}
    d, G = load(args.inp, "crops")
    feet = {}
    for s in set(d.stub):
        kx, ky = lat.stub_k[s]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = inv.get((kx + dx, ky + dy))
                if n is not None and n not in feet:
                    feet[n] = footprint(args.samgeo_dir, n)
    donor_sets = []
    for path in args.donor:
        dd, GD = load(path, "crops")
        keep = dd.classified.values | (dd.abstain_reason.values == "no_crop_signal")
        donor_sets.append((path, GD[keep], shapely.STRtree(GD[keep])))
    others_tree = shapely.STRtree(G)

    recs = []
    if args.mode == "repair":
        targets = [i for i in range(len(d)) if d.classified.values[i]]
    else:
        ba = d.boundary_action.fillna("") if "boundary_action" in d else pd.Series([""] * len(d))
        targets = [i for i in range(len(d)) if ba.values[i] == "union"]
    new_geoms = {}
    for i in targets:
        g, s = G[i], d.stub.values[i]
        fp = feet.get(s)
        if fp is None:
            continue
        truth = None
        if args.mode == "validate":
            truth = g
            beyond = g.difference(fp).area / 1e4
            t = g.intersection(fp.buffer(-20)).buffer(0)
            if beyond < args.min_add or t.geom_type != "Polygon" or t.area < 1e4:
                continue
            g = t
        cl = cut_len(g, fp, args.tol)
        rec = dict(fid=int(d.fid.values[i]), stub=s, pred=d.pred.values[i], area_ha=round(g.area / 1e4, 2),
                   cut_len_m=round(cl, 1), score=np.nan, reason="", donor="", added_ha=0.0)
        if cl < args.min_cut:
            rec["reason"] = "not_cut"; recs.append(rec); continue
        if not args.no_image_test:
            sc = cut_score(g, s, feet, args.samgeo_dir, lat, inv, tol=args.tol)
            rec["score"] = round(sc[0], 3) if sc else np.nan
            if sc is None or sc[0] > args.thr:
                rec["reason"] = "image_says_boundary" if sc else "image_no_sample"; recs.append(rec); continue
        # exclude self from 'others'
        oth_idx = [j for j in others_tree.query(g.buffer(500), predicate="intersects") if j != i]
        others = G[oth_idx] if oth_idx else np.array([], dtype=object)
        otree = shapely.STRtree(others) if len(others) else shapely.STRtree(np.array([shapely.Point(0, 0).buffer(0)], dtype=object))
        best = None
        for path, GD, dtree in donor_sets:
            u, k, why = find_repair(g, s, feet, GD, dtree, others, otree, args)
            rec["reason"] = why
            if u is not None:
                best = (u, path); rec["donor"] = path; break
        if best is None:
            recs.append(rec); continue
        u, path = best
        rec["added_ha"] = round((u.area - g.area) / 1e4, 2)
        if args.mode == "validate":
            rec["iou_truth"] = round(u.intersection(truth).area / u.union(truth).area, 3)
            rec["iou_cut_truth"] = round(g.intersection(truth).area / g.union(truth).area, 3)
            rec["recovered_frac"] = round((u.area - g.area) / max(truth.area - g.area, 1), 3)
            rec["overshoot_ha"] = round(u.difference(truth).area / 1e4, 3)
        else:
            new_geoms[int(d.fid.values[i])] = (u, path)
        recs.append(rec)
    R = pd.DataFrame(recs)
    R.to_csv(args.decisions_csv, index=False)
    summ = dict(mode=args.mode, n_targets=int(len(R)), reasons=R.reason.value_counts().to_dict() if len(R) else {},
                n_repaired=int((R.reason == "repaired").sum()) if len(R) else 0,
                added_ha_total=round(float(R.added_ha.sum()), 1) if len(R) else 0.0,
                thresholds=dict(tol=args.tol, min_cut=args.min_cut, thr=args.thr, image_test=not args.no_image_test,
                                cover=args.cover, min_add=args.min_add, max_add_ratio=args.max_add_ratio))
    if args.mode == "validate" and len(R):
        V = R[R.reason == "repaired"]
        C = R[R.reason != "not_cut"]
        summ.update(n_known_cuts=int(len(C)), repaired_pct=round(100 * len(V) / max(len(C), 1), 1),
                    iou_cut_vs_truth_median=round(float(C.iou_cut_truth.median()), 3) if "iou_cut_truth" in C and C.iou_cut_truth.notna().any() else None,
                    iou_repaired_vs_truth_quantiles={q: round(float(V.iou_truth.quantile(q)), 3) for q in (0.1, 0.25, 0.5, 0.75, 0.9)} if len(V) else {},
                    iou_before_repair_quantiles={q: round(float(V.iou_cut_truth.quantile(q)), 3) for q in (0.1, 0.25, 0.5, 0.75, 0.9)} if len(V) else {},
                    recovered_frac_median=round(float(V.recovered_frac.median()), 3) if len(V) else None,
                    share_iou_ge_0_9=round(float((V.iou_truth >= 0.9).mean()), 3) if len(V) else None,
                    share_iou_le_0_7=round(float((V.iou_truth <= 0.7).mean()), 3) if len(V) else None,
                    overshoot_ha_median=round(float(V.overshoot_ha.median()), 3) if len(V) else None)
    if args.mode == "repair" and args.out:
        shutil.copyfile(args.inp, args.out)
        con = sqlite3.connect(args.out)
        register_gpkg_functions(con)
        existing = {r[1] for r in con.execute("PRAGMA table_info(crops)")}
        for c, t in [("boundary_action", "TEXT"), ("repair_from", "TEXT"), ("repair_added_ha", "REAL")]:
            if c not in existing:
                con.execute(f'ALTER TABLE crops ADD COLUMN "{c}" {t}')
        srs = con.execute("SELECT srs_id FROM gpkg_geometry_columns WHERE table_name='crops'").fetchone()[0]
        rows = []
        for fid, (u, path) in new_geoms.items():
            g0 = G[int(np.where(d.fid.values == fid)[0][0])]
            rows.append((geom_to_blob(u, srs), round(u.area / 1e4, 2), float(u.length / np.sqrt(u.area)),
                         "repaired", path, round((u.area - g0.area) / 1e4, 2), fid))
        con.executemany("UPDATE crops SET geom=?, area_ha=?, compactness=?, boundary_action=?, repair_from=?, "
                        "repair_added_ha=? WHERE fid=?", rows)
        con.commit(); con.close()
        summ["output"] = args.out
    with open(args.summary, "w") as f:
        json.dump(summ, f, indent=2, default=str)
    print(json.dumps(summ, indent=2, default=str))


if __name__ == "__main__":
    main()
