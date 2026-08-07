#!/usr/bin/env python3
"""
Build QGIS review layers + a ranked annotation spreadsheet for trial-to-paddock matches.

Inspecting `<stub>_filt.gpkg` alone cannot tell you whether the RIGHT polygon was picked —
the trial location is not in the file. This writes, per AOI, layers that sit alongside the
existing ones with matching filenames:

  <stub>_trials.gpkg   trial points, attributed with the match and its risk flags
  <stub>_chosen.gpkg   the ONE polygon selected for each trial (so the choice is visible)

and one `review_sites.csv` for annotation, **ranked worst-first** by an automatic risk score.
Ranking is the point: reviewing ~2,000 sites in file order is a slog with no natural
stopping rule, whereas worst-first means the bad matches surface early and you can stop when
the flags go quiet.

    python3 make_review_layers.py --sites .../aois.csv.sites.csv \
        --polydir .../samgeo/full --outdir .../review --chm-dir .../canopy_height

Risk flags (all cheap, all computed from geometry + the canopy height model — no imagery):
  not_contained     the point falls outside every polygon; nearest was used
  edge_close        point within 20 m of the boundary, so the match could flip
  treed             >20 % of the polygon is canopy >1 m — the "it picked a tree patch" case
  tiny              polygon < 5 ha, small for broadacre
  bigger_neighbour  an adjacent polygon is >3x larger — the "it picked the little polygon
                    marking the trial rather than the surrounding paddock" case
  sliver            compactness > 6, i.e. long and thin

Verdict/notes columns are left empty for the human. `verdict` is deliberately free text with
a suggested vocabulary rather than a dropdown, so an unanticipated failure mode can be named
rather than forced into a bucket.
"""
import argparse
import os

import numpy as np
import pandas as pd

from extract_paddock import match_polygon

SUGGESTED_VERDICTS = "good | wrong_polygon | treed | too_small | too_big | no_paddock | unsure"


def tree_fraction(masker, geom_3577):
    """Fraction of a polygon covered by canopy >height_min, from the 1 m CHM tiles.

    Computed on the CHM's own 1 m grid rather than resampled to Sentinel 10 m: a tree line
    along a fence is often narrower than a Sentinel pixel, and resampling first would either
    lose it or smear it across the whole cell. Returns NaN when no tile covers the polygon —
    "no canopy data" must not be reported as "no trees".
    """
    import rasterio
    from rasterio.features import geometry_mask
    import geopandas as gpd

    ll = gpd.GeoSeries([geom_3577], crs="EPSG:3577").to_crs("EPSG:4326").iloc[0]
    w, s, e, n = ll.bounds
    files = masker.tiles_for_bounds(w, s, e, n)
    inside = tree = 0
    for f in files:
        with rasterio.open(f) as src:
            g = gpd.GeoSeries([geom_3577], crs="EPSG:3577").to_crs(src.crs).iloc[0]
            try:
                win = src.window(*g.bounds).round_offsets().round_lengths()
                if win.width <= 0 or win.height <= 0:
                    continue
                arr = src.read(1, window=win)
                if arr.size == 0:
                    continue
                m = ~geometry_mask([g], out_shape=arr.shape,
                                   transform=src.window_transform(win), invert=False)
                inside += int(m.sum())
                tree += int(((arr > masker.height_min) & m).sum())
            except Exception:
                continue
    return (tree / inside) if inside else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", required=True)
    ap.add_argument("--polydir", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--chm-dir", help="canopy height tiles; omit to skip the treed flag")
    ap.add_argument("--max-dist-m", type=float, default=50.0)
    ap.add_argument("--erode-m", type=float, default=10.0)
    # None = defer to match_polygon's tuned defaults, exactly as extract_paddock.py does.
    # Restating the numbers here is how review and extraction silently drifted apart before.
    ap.add_argument("--min-paddock-ha", type=float, default=None)
    ap.add_argument("--upgrade-ratio", type=float, default=None)
    ap.add_argument("--no-upgrade", action="store_true")
    # Calibrated to the observed distribution, not to intuition: across the 169 matched pilot
    # trials tree fraction maxes at 0.036 (median 0.000), so an absolute "this is a forest"
    # threshold like 0.20 never fires and the flag is dead. 0.02 surfaces the worst few
    # percent, which is what a review queue needs.
    ap.add_argument("--tree-frac-flag", type=float, default=0.02)
    ap.add_argument("--no-layers", action="store_true", help="spreadsheet only")
    args = ap.parse_args()

    os.environ.setdefault("PROJ_NETWORK", "OFF")
    import geopandas as gpd
    from shapely.geometry import Point

    sites = pd.read_csv(args.sites)
    os.makedirs(args.outdir, exist_ok=True)

    match_kw = {}
    if args.no_upgrade:
        match_kw["min_paddock_ha"] = 0.0
    elif args.min_paddock_ha is not None:
        match_kw["min_paddock_ha"] = args.min_paddock_ha
    if args.upgrade_ratio is not None:
        match_kw["upgrade_ratio"] = args.upgrade_ratio

    masker = None
    if args.chm_dir:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "sentinel_ndvi"))
        from tree_mask import TreeMasker
        masker = TreeMasker(args.chm_dir)

    rows = []
    for stub, grp in sites.groupby("aoi_stub"):
        p = os.path.join(args.polydir, f"{stub}_filt.gpkg")
        if not os.path.exists(p):
            for _, r in grp.iterrows():
                rows.append({"TrialCode": r["TrialCode"], "aoi_stub": stub,
                             "crop": r["crop"], "Year": r.get("Year"),
                             "match_rule": "no_aoi_polygons"})
            continue
        poly = gpd.read_file(p).to_crs("EPSG:3577")
        poly["area_ha"] = poly.area / 1e4
        poly["compactness"] = poly.length / np.sqrt(poly.area)

        pts, chosen, recs = [], [], []
        for _, r in grp.iterrows():
            pt = gpd.GeoSeries([Point(float(r["lon"]), float(r["lat"]))],
                               crs="EPSG:4326").to_crs("EPSG:3577").iloc[0]
            # Shared with extract_paddock.py on purpose: if review used its own copy of the
            # matching rule the two would drift, and you would be annotating a polygon that
            # is not the one the time series was extracted from.
            g, rule, edge = match_polygon(poly, pt, args.max_dist_m, **match_kw)
            if g is None:
                recs.append({"TrialCode": r["TrialCode"], "aoi_stub": stub,
                             "crop": r["crop"], "Year": r.get("Year"),
                             "match_rule": "none"})
                continue
            area = g.area / 1e4
            i = poly.geometry.geom_equals(g).idxmax()   # row index of the chosen polygon

            # "Should it have picked the surrounding paddock?" — compare against the largest
            # polygon whose boundary is within 50 m, i.e. a plausible alternative.
            near = poly[poly.distance(pt) <= 250]
            bigger = near.area_ha.max() if len(near) else area
            tree_frac = tree_fraction(masker, g) if masker is not None else np.nan

            rec = {
                "TrialCode": r["TrialCode"], "aoi_stub": stub, "crop": r["crop"],
                "Year": r.get("Year"), "match_rule": rule,
                "edge_dist_m": round(edge, 1), "area_ha": round(float(area), 1),
                "compactness": round(float(poly.compactness.loc[i]), 2),
                "n_polys_within_250m": int(len(near)),
                "largest_near_ha": round(float(bigger), 1),
                "bigger_neighbour_ratio": round(float(bigger / max(area, 0.01)), 2),
                "tree_frac": None if np.isnan(tree_frac) else round(float(tree_frac), 3),
            }
            recs.append(rec)
            pts.append({**rec, "geometry": pt})
            chosen.append({"TrialCode": r["TrialCode"], "area_ha": rec["area_ha"],
                           "match_rule": rule, "geometry": g})

        rows.extend(recs)
        if not args.no_layers and pts:
            gpd.GeoDataFrame(pts, crs="EPSG:3577").to_file(
                os.path.join(args.outdir, f"{stub}_trials.gpkg"), driver="GPKG")
            gpd.GeoDataFrame(chosen, crs="EPSG:3577").to_file(
                os.path.join(args.outdir, f"{stub}_chosen.gpkg"), driver="GPKG")

    df = pd.DataFrame(rows)
    for c in ["edge_dist_m", "area_ha", "bigger_neighbour_ratio", "tree_frac", "compactness"]:
        if c not in df:
            df[c] = np.nan

    flags = pd.DataFrame(index=df.index)
    flags["not_contained"] = ~df.match_rule.fillna("").str.startswith("contains")
    flags["edge_close"] = df.edge_dist_m < 20
    flags["treed"] = df.tree_frac > args.tree_frac_flag
    flags["tiny"] = df.area_ha < 5
    flags["bigger_neighbour"] = df.bigger_neighbour_ratio > 3
    flags["sliver"] = df.compactness > 6
    df["flags"] = flags.apply(lambda r: ",".join(sorted(flags.columns[r.values])), axis=1)
    # Weighted so the failure modes seen in QGIS (wrong polygon, tree patch) sort highest.
    w = {"not_contained": 3, "treed": 3, "bigger_neighbour": 2,
         "tiny": 2, "edge_close": 1, "sliver": 1}
    df["risk"] = sum(flags[c].astype(int) * v for c, v in w.items())
    df["verdict"] = ""
    df["better_polygon_note"] = ""
    df["notes"] = ""

    df = df.sort_values(["risk", "TrialCode"], ascending=[False, True])
    out = os.path.join(args.outdir, "review_sites.csv")
    df.to_csv(out, index=False)

    print(f"{len(df)} trials -> {out}")
    print(f"suggested verdict vocabulary: {SUGGESTED_VERDICTS}\n")
    print("flag counts (a trial can carry several):")
    for c in flags.columns:
        print(f"  {c:20s} {int(flags[c].sum()):5d}  ({flags[c].mean():.1%})")
    tf = df.tree_frac.dropna()
    if len(tf):
        print(f"\ntree_frac over matched polygons: median {tf.median():.3f}, "
              f"p90 {tf.quantile(.9):.3f}, max {tf.max():.3f} "
              f"({int(df.tree_frac.isna().sum())} unmatched/no-CHM)")
    print(f"\nrisk score: {(df.risk == 0).sum()} clean, {(df.risk > 0).sum()} flagged, "
          f"{(df.risk >= 3).sum()} high (review these first)")


if __name__ == "__main__":
    main()
