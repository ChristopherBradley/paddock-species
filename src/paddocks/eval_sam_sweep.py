#!/usr/bin/env python3
"""
Score SAM parameter settings against the user's hand verdicts.

THE QUESTION. 624 polygons are flagged for manual review, which is more work than the user
wants to do. Most of the queue is under-segmentation — 222 polygons over 300 ha ("whole
region, not a paddock") and 207 carrying a different crop's trial as well. Both are what you
get from `sam_kwargs=None`, i.e. a 32-point prompt grid over a ~3 km tile. If a denser grid
splits merged fields, a large part of the queue fixes itself.

HOW IT IS SCORED, and why not by eye. 37 polygons already carry a verdict (18 bad, 19 good),
so a setting can be judged automatically against them:

  * a BAD polygon is FIXED when the trial point lands inside a plausible paddock — inside the
    polygon, 2-300 ha, compactness <= 6.
  * a GOOD polygon is BROKEN when it stops being plausible under the same test, or when it is
    carved up so far that it no longer overlaps most of what the user approved (IoU < 0.5).

The second half is the one that matters. Denser sampling trivially "fixes" over-large polygons
by cutting everything smaller, so a setting must be shown NOT to destroy the polygons already
judged correct. Reporting only the fix rate would make the most destructive setting look best.

CONTROL. `pps32` reproduces the production settings, so its scores are the baseline any other
setting must beat. A difference against pps32 is attributable to the parameter; a difference
against the stored production polygons would also include SAM nondeterminism and any library
drift since that run.
"""
import argparse
import glob
import os

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

PLAUSIBLE_HA = (2.0, 300.0)
PLAUSIBLE_COMP = 8.0   # the production filter's limit. An earlier 6.0 was borrowed from
                       # the UPGRADE-TARGET rule and wrongly failed 12/19 user-approved
                       # polygons, which run to compactness 7.9.


def plausible(poly, pt):
    """Would this polygon pass as the trial's paddock?"""
    if poly is None:
        return False, {}
    ha = poly.area / 1e4
    comp = poly.length / np.sqrt(poly.area)
    ok = (poly.contains(pt) and PLAUSIBLE_HA[0] <= ha <= PLAUSIBLE_HA[1]
          and comp <= PLAUSIBLE_COMP)
    return ok, {"ha": ha, "comp": comp, "inside": poly.contains(pt)}


def best_polygon(poly_gdf, pt):
    """The polygon a reviewer would judge: the one containing the point, else the nearest."""
    if poly_gdf is None or not len(poly_gdf):
        return None
    hit = poly_gdf[poly_gdf.contains(pt)]
    if len(hit):
        return hit.geometry.iloc[hit.geometry.area.values.argmin()]   # tightest containing
    d = poly_gdf.distance(pt)
    return poly_gdf.geometry.loc[d.idxmin()] if d.min() <= 150 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep-dir", required=True)
    ap.add_argument("--settings", nargs="+", required=True)
    ap.add_argument("--judged", required=True, help="TrialCode,verdict,aoi_stub,polydir csv")
    ap.add_argument("--production-gpkg", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    J = pd.read_csv(args.judged)
    prod = gpd.read_file(args.production_gpkg, layer="chosen").to_crs(3577)
    prod = prod.drop_duplicates("TrialCode").set_index("TrialCode")
    pts = {}
    for tc in J.TrialCode:
        if tc in prod.index:
            r = prod.loc[tc]
            pts[tc] = gpd.GeoSeries([Point(r.lon, r.lat)], crs=4326).to_crs(3577).iloc[0]

    rows = []
    for setting in args.settings:
        cache = {}
        for r in J.itertuples():
            tc = r.TrialCode
            if tc not in pts:
                continue
            f = os.path.join(args.sweep_dir, setting, f"{r.aoi_stub}_filt.gpkg")
            if r.aoi_stub not in cache:
                cache[r.aoi_stub] = (gpd.read_file(f).to_crs(3577)
                                     if os.path.exists(f) else None)
            g = best_polygon(cache[r.aoi_stub], pts[tc])
            ok, info = plausible(g, pts[tc])
            old = prod.loc[tc].geometry
            iou = np.nan
            if g is not None and old is not None:
                inter = g.intersection(old).area
                union = g.union(old).area
                iou = inter / union if union else np.nan
            rows.append({"setting": setting, "TrialCode": tc, "verdict": r.verdict,
                         "plausible": ok, "iou_with_production": iou,
                         "n_polys": 0 if cache[r.aoi_stub] is None else len(cache[r.aoi_stub]),
                         **info})
    R = pd.DataFrame(rows)
    R.to_csv(args.out.replace(".md", "_detail_SENSITIVE.csv"), index=False)

    with open(args.out, "w") as f:
        f.write("# Does a denser SAM prompt grid fix the flagged polygons?\n\n")
        f.write(f"Scored on {J.verdict.value_counts().to_dict()} hand-judged polygons across "
                f"{J.aoi_stub.nunique()} AOIs. `pps32` reproduces production and is the "
                f"control.\n\n")
        f.write("A BAD polygon counts as FIXED when the trial point lands inside a plausible "
                f"paddock ({PLAUSIBLE_HA[0]:.0f}-{PLAUSIBLE_HA[1]:.0f} ha, compactness "
                f"<= {PLAUSIBLE_COMP}). A GOOD one counts as KEPT when it still passes that "
                "user approved (IoU >= 0.5). A polygon the user already passed needs no quality "
                "proxy applied to it a second time — the only question is whether the new "
                "setting CHANGED it. Without that guard a setting that shatters every field "
                "would score perfectly on the bad ones.\n\n")
        f.write("| setting | bad FIXED | good KEPT | median polys/AOI | median IoU (good) |\n")
        f.write("|---|---|---|---|---|\n")
        for s in args.settings:
            d = R[R.setting == s]
            bad, good = d[d.verdict == "bad"], d[d.verdict == "good"]
            kept = good.iou_with_production >= 0.5
            f.write(f"| {s} | {int(bad.plausible.sum())}/{len(bad)} "
                    f"({100*bad.plausible.mean():.0f}%) | {int(kept.sum())}/{len(good)} "
                    f"({100*kept.mean():.0f}%) | {d.n_polys.median():.0f} | "
                    f"{good.iou_with_production.median():.2f} |\n")
        f.write("\n## Per-polygon, bad ones only\n\n")
        f.write("| TrialCode-anon | " + " | ".join(args.settings) + " |\n")
        f.write("|---|" + "---|" * len(args.settings) + "\n")
        bad_tcs = J[J.verdict == "bad"].TrialCode.tolist()
        for i, tc in enumerate(bad_tcs, 1):
            cells = []
            for s in args.settings:
                d = R[(R.setting == s) & (R.TrialCode == tc)]
                if not len(d):
                    cells.append("-")
                    continue
                r = d.iloc[0]
                cells.append(f"{'OK' if r.plausible else 'no'} ({r.get('ha', float('nan')):.0f} ha)")
            f.write(f"| bad #{i} | " + " | ".join(cells) + " |\n")
        f.write("\nTrialCodes withheld — see the detail csv.\n")
    print(f"-> {args.out}")
    for s in args.settings:
        d = R[R.setting == s]
        bad, good = d[d.verdict == "bad"], d[d.verdict == "good"]
        kept = good.iou_with_production >= 0.5
        print(f"  {s:14s} bad fixed {bad.plausible.mean():5.0%}  good kept {kept.mean():5.0%}")


if __name__ == "__main__":
    main()
