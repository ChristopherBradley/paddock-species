#!/usr/bin/env python3
"""
Re-run ONLY the trial->paddock matching under the fixed rules, and write a GeoPackage that
shows what changed — so the fix can be inspected in QGIS before anything is re-extracted.

WHY THIS IS CHEAP. Which polygon a trial gets is a function of the polygons, the trial point
and the matcher parameters alone; none of it touches the datacube. So the corrected assignment
can be produced from the existing `_filt.gpkg` files in minutes, while a full re-extraction of
the time series costs tens of CPU-hours. Verify the geometry first, re-extract second.

WHAT THE FIX IS. The upgrade rule may no longer move a trial onto a polygon that a DIFFERENT
crop has already claimed in the same AOI and year. Measured 2026-08-08, that rule was the main
generator of the project's largest label problem: 72.3 % of upgraded matches landed on a
polygon another trial also used, and 41.9 % of upgraded trials shared with a different crop
against 30.6 % of non-upgraded ones. Where that happens the two trials get an IDENTICAL
paddock-median series under contradictory labels, and canola on such a polygon reads 482 CFI
lower [95 % CI 348, 551] than canola on an unshared one.

WHAT TO LOOK AT IN QGIS. Layer `chosen` is the new assignment, `chosen_old` the previous one,
`trials` the points. Filter `changed = 1` to see only what moved — that is the whole review
set, and it is small. `conflict_9class` marks trials still sharing a polygon with a different
crop, which the matcher cannot fix on its own and which the 3-group collapse resolves for 69 %
of cases.

NOTE the `cfi_peak` column is carried over from the PREVIOUS extraction and is therefore STALE
wherever `changed = 1` — those trials need re-extraction before their CFI means anything. It
is kept only so unchanged trials stay comparable with the old heatmaps.

Output carries TrialCodes and coordinates, so it is written as *_SENSITIVE.gpkg.
"""
import argparse
import glob
import hashlib
import os

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from extract_paddock import match_polygon

GROUP = {"Canola": "Canola", "Wheat": "Cereal", "Barley": "Cereal", "Oat": "Cereal",
         "Chickpea": "Legume", "Faba Bean": "Legume", "Field Pea": "Legume",
         "Lentil": "Legume", "Lupin": "Legume"}


def conflict_flags(df):
    """Recompute sharing/conflict on whatever assignment `df` holds."""
    df = df.copy()
    df["gkey"] = [hashlib.md5(w).hexdigest() if w is not None else f"none{i}"
                  for i, w in enumerate(df.geometry.to_wkb())]
    df["ykey"] = df.gkey + "_" + df.Year.astype(str)
    g = df.groupby("ykey")
    df["share_n"] = g.TrialCode.transform("size")
    df["n_crops"] = g.crop.transform("nunique")
    df["n_groups"] = g["group"].transform("nunique")
    df["conflict_9class"] = (df.share_n > 1) & (df.n_crops > 1)
    df["conflict_3class"] = (df.share_n > 1) & (df.n_groups > 1)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", nargs="+", required=True,
                    help="PREFIX=GLOB=POLYDIR triples, e.g. cw=.../chunks/cw_*.csv=.../full")
    ap.add_argument("--old-gpkg", required=True, help="previous cfi_heatmap_ALL gpkg")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-dist-m", type=float, default=50.0)
    args = ap.parse_args()

    sites = []
    for spec in args.chunks:
        _, pat, polydir = spec.split("=", 2)
        files = sorted(glob.glob(pat))
        if not files:
            raise SystemExit(f"no chunk files matched {pat}")
        d = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
        d["polydir"] = polydir
        sites.append(d)
    S = pd.concat(sites, ignore_index=True).drop_duplicates("TrialCode")
    print(f"{len(S)} trials across {S.polydir.nunique()} polygon dirs")

    # Sorting so co-located trials are adjacent: the claim table must be populated before a
    # neighbour is matched, or the collision rule has nothing to block against.
    S = S.sort_values(["polydir", "aoi_stub", "Year", "TrialCode"])

    poly_cache, claims, rows = {}, {}, []
    for _, r in S.iterrows():
        stub, polydir = r["aoi_stub"], r["polydir"]
        ck = (polydir, stub)
        if ck not in poly_cache:
            p = os.path.join(polydir, f"{stub}_filt.gpkg")
            poly_cache[ck] = (gpd.read_file(p).to_crs("EPSG:3577")
                              if os.path.exists(p) else None)
            if len(poly_cache) % 200 == 0:
                print(f"  {len(poly_cache)} AOIs read", flush=True)
        poly = poly_cache[ck]
        if poly is None or not len(poly):
            continue
        pt = gpd.GeoSeries([Point(float(r["lon"]), float(r["lat"]))],
                           crs="EPSG:4326").to_crs("EPSG:3577").iloc[0]
        key = (stub, r["Year"])
        geom, rule, edge = match_polygon(poly, pt, args.max_dist_m,
                                         claimed=claims.get(key), crop=r["crop"])
        if geom is None:
            continue
        hit = poly.index[poly.geometry.geom_equals(geom)]
        if len(hit):
            claims.setdefault(key, {})[hit[0]] = r["crop"]
        rows.append({"TrialCode": r["TrialCode"], "crop": r["crop"],
                     "group": GROUP.get(r["crop"]), "Year": int(r["Year"]),
                     "state": r.get("state"), "site": r.get("site"),
                     "panel": f"{int(r['Year'])}_{r.get('state')}",
                     "lat": r["lat"], "lon": r["lon"],
                     "match_rule_new": rule, "edge_dist_m": edge,
                     "paddock_ha": geom.area / 1e4, "geometry": geom})

    new = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:3577")
    new = conflict_flags(new)
    print(f"\nmatched {len(new)} trials")

    old = gpd.read_file(args.old_gpkg, layer="paddocks").drop_duplicates(subset=["TrialCode"])
    old = old.to_crs("EPSG:3577")
    old["group"] = old.crop.map(GROUP)
    old = conflict_flags(old)
    o = old.set_index("TrialCode")
    new["match_rule_old"] = new.TrialCode.map(o.match_rule)
    new["paddock_ha_old"] = new.TrialCode.map(o.paddock_ha)
    new["cfi_peak"] = new.TrialCode.map(o.cfi_peak)          # STALE where changed=1
    new["gkey_old"] = new.TrialCode.map(o.gkey)
    # THREE states, not a boolean. A plain `gkey != gkey_old` marked every trial absent from
    # the previous run as "changed", because comparing against a missing value is always true
    # — 897 of them, against 28 real changes, so the file said 925 and the console said 28.
    # A trial that did not exist before has not changed; it is new.
    new["status"] = np.where(new.gkey_old.isna(), "new",
                     np.where(new.gkey != new.gkey_old, "changed", "unchanged"))
    new["changed"] = (new.status == "changed").astype(int)

    # Before/after must be computed on the SAME trials. The new run matches more trials than
    # the old gpkg holds, and a conflict flag depends on who else is in the population — so
    # flagging each set at its own size would compare different questions and overstate the
    # fix. Recompute BOTH on the intersection.
    common = sorted(set(new.TrialCode) & set(o.index))
    both = conflict_flags(new[new.TrialCode.isin(common)])
    old_c = conflict_flags(old[old.TrialCode.isin(common)])
    print(f"\n=== effect of the collision-aware upgrade ===")
    print(f"  compared on {len(common)} trials present in both runs")
    print(f"  trials whose polygon CHANGED: {int(both.changed.sum())} "
          f"({100*both.changed.mean():.1f}%)")
    print(f"  conflicting (9-class): old {int(old_c.conflict_9class.sum()):4d} "
          f"-> new {int(both.conflict_9class.sum()):4d}")
    print(f"  conflicting (3-group): old {int(old_c.conflict_3class.sum()):4d} "
          f"-> new {int(both.conflict_3class.sum()):4d}")
    print(f"  sharing any polygon:   old {int((old_c.share_n>1).sum()):4d} "
          f"-> new {int((both.share_n>1).sum()):4d}")
    print(f"  upgraded matches:      old "
          f"{int(o.loc[both.TrialCode].match_rule.str.contains('upgraded',na=False).sum()):4d}"
          f" -> new {int(both.match_rule_new.str.contains('upgraded',na=False).sum()):4d}")
    ch = both[both.changed == 1]
    if len(ch):
        print(f"  median area of changed trials: {ch.paddock_ha_old.median():.1f} ha "
              f"-> {ch.paddock_ha.median():.1f} ha")

    out = new.to_crs("EPSG:4326")
    keep = [c for c in out.columns if c not in ("gkey", "ykey", "gkey_old")]
    out[keep].to_file(args.out, layer="chosen", driver="GPKG")
    pts = out.copy()
    pts["geometry"] = gpd.points_from_xy(pts.lon, pts.lat)
    pts[keep].to_file(args.out, layer="trials", driver="GPKG")
    oc = old.to_crs("EPSG:4326")
    oc[[c for c in oc.columns if c not in ("gkey", "ykey")]].to_file(
        args.out, layer="chosen_old", driver="GPKG")
    print(f"\n-> {args.out}  (layers: chosen, chosen_old, trials)")


if __name__ == "__main__":
    main()
