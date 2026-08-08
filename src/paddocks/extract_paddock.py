#!/usr/bin/env python3
"""
Paddock-median CFI time series per trial — the estimator that should replace the 200 m
corner window.

Extracts BOTH estimators from the SAME scenes in one pass:
  * `*_pad_median` / `*_pad_mean` — over the trial's paddock polygon, eroded by one pixel
  * `*_win_mean`                  — the 200 m window centred on the trial GPS (the baseline)

Computing them together is deliberate. If the two were extracted in separate runs they could
see different date sets (cloud filtering, scene availability) and any difference in
discriminating power would confound aggregation with sampling. Paired on identical dates,
the only thing that varies is the spatial support — which is the thing under test.

    python3 extract_paddock.py --sites .../aois.csv.sites.csv \
        --polydir .../samgeo/pilot --out .../paddock_ts_SENSITIVE.csv

Output carries TrialCode ⇒ SENSITIVE. Appended per trial, so a walltime kill keeps its work.

MATCHING A TRIAL TO A PADDOCK. The trial GPS marks a paddock *corner* and sits ~17-24 m from
the boundary — about two pixels — so containment is marginal and cannot be assumed. Rules,
in order, recorded per trial in `match_rule` so any result can be re-cut by match quality:
  contains          — a polygon contains the point (the good case)
  nearest_<=Nm      — no container; nearest polygon within --max-dist-m (its edge distance)
  none              — no polygon within tolerance; trial is skipped

TREES. Canopy pixels are green all year and never flower, so they pull the aggregate toward
"perennial" and flatten the very peak this measures. Eroding the polygon by 10 m removes the
boundary tree line but not a scattered paddock tree or an internal timber strip, so the same
1 m canopy mask the 200 m window uses is applied here too — a Sentinel pixel is dropped if
any overlapping 1 m canopy pixel is >1 m tall, plus its neighbours for co-registration slop.
Over most chosen paddocks this changes almost nothing (tree fraction is ~0 by construction of
the compactness filter); it matters for the treed tail, and it must be applied to EVERY crop
group or the group comparison confounds spatial support with tree contamination.
`chm_covered` records whether canopy tiles actually covered the paddock — no data is not the
same as no trees, and must never be read as the latter.
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "sentinel_ndvi"))

FMASK_CLEAR = 1
NODATA = -999
REFL_SCALE = 10000.0
BANDS = ["nbart_red", "nbart_green", "nbart_blue", "nbart_nir_1", "oa_fmask"]
# The 10 bands Presto consumes (S2 L2A minus coastal aerosol and cirrus), which is also a
# superset of anything a random forest would want. Storing the BANDS and not just derived
# indices is the lesson from Stage 2: that pass stored indices only, and changing the index
# then cost a full re-extraction. Bands are the raw material; indices are a view over them.
ALL_BANDS = ["nbart_blue", "nbart_green", "nbart_red", "nbart_red_edge_1", "nbart_red_edge_2",
             "nbart_red_edge_3", "nbart_nir_1", "nbart_nir_2", "nbart_swir_2", "nbart_swir_3"]
PRODUCTS = ["ga_s2am_ard_3", "ga_s2bm_ard_3", "ga_s2cm_ard_3"]


def indices_from(ds, keep):
    """NDVI/NDYI/CFI as (time, y, x) arrays, masked to clear pixels inside `keep`."""
    m = (ds["oa_fmask"] == FMASK_CLEAR) & keep

    def b(n):
        v = ds[n].where((ds[n] != NODATA) & m).astype("float32") / REFL_SCALE
        return v

    red, green, blue, nir = b("nbart_red"), b("nbart_green"), b("nbart_blue"), b("nbart_nir_1")
    ndvi = (nir - red) / (nir + red)
    ndyi = (green - blue) / (green + blue)
    # PaddockTS Code/indices_etc/indices.py: CFI = NDVI * ((Red + Green) + (Green - Blue))
    # Linear in reflectance, so it is scale-dependent: ours is 0-1, PaddockTS raw DN.
    cfi = ndvi * ((red + green) + (green - blue))
    return {"ndvi": ndvi, "ndyi": ndyi, "cfi": cfi}


def match_polygon(poly, pt, max_dist_m, min_paddock_ha=10.0, upgrade_ratio=3.0,
                  upgrade_search_m=150.0, max_upgrade_compactness=6.0,
                  claimed=None, crop=None):
    """(geometry, rule, edge_distance_m) for the trial point, or (None, 'none', nan).

    Plain "containing polygon, else nearest" is not enough. Reviewing the pilot in imagery
    showed a recurring failure: the trial point sits in a narrow ROAD VERGE or LANEWAY strip
    between fields, so the match is a ~2 ha sliver while the actual cropped paddock — tens of
    hectares — is immediately adjacent. Measured at 4 % of matched pilot trials (median 2.2 ha
    chosen against 40.2 ha available). Taking the median over a road verge is worse than the
    200 m window this whole exercise is meant to improve on.

    So a match smaller than `min_paddock_ha` is UPGRADED to a substantially larger neighbour
    (`upgrade_ratio`x) whose boundary lies within `upgrade_search_m`. The recorded rule name
    always says what happened so any upgrade can be audited or undone downstream.

    THE UPGRADE TARGET MUST ITSELF BE PADDOCK-SHAPED (`max_upgrade_compactness`). Bigger is
    not automatically better: where SAM under-segments it emits huge amorphous blobs spanning
    several fields plus timber, and upgrading into one would mix crops — the exact failure
    that disqualified Fields of The World. Compactness separates the two cases cleanly, on
    the user's own two worked examples (2026-08-07):
    (codes in `memory/WORKED_EXAMPLES_SENSITIVE.md`; NDA data must not enter a tracked file):
      * Example A — chosen 5.1 ha strip, target 51.6 ha at compactness 5.4 ⇒ upgrade, correct.
      * Example B — chosen 11.6 ha, neighbour 351.9 ha at compactness 7.2, which the user
        identified as spanning neighbouring paddocks and forest ⇒ blocked, correct.
    The 10 ha default likewise sits between those two chosen areas: it catches the 5.1 ha
    strip while leaving the acceptable 11.6 ha match alone.

    UPGRADING IS BLOCKED ONTO A POLYGON ANOTHER CROP HAS ALREADY CLAIMED (`claimed`: a dict of
    polygon index -> crop, for trials already matched in this AOI and year). Measured
    2026-08-08, this rule was a primary generator of the project's largest label problem:
    72.3 % of upgraded matches landed on a polygon also used by another trial, and 41.9 % of
    upgraded trials ended up sharing with a DIFFERENT crop against 30.6 % of non-upgraded
    ones. That matters because NVT co-locates several crop trials in one field, so upgrading
    two of them out of their own small plots and into the surrounding paddock gives them an
    identical time series under contradictory labels. Canola on such a polygon reads 482 CFI
    lower [95 % CI 348, 551] than canola on an unshared one — the median is averaging canola
    with its neighbour. Keeping the smaller original polygon is the lesser evil: it is at
    least the trial's own ground.
    """
    hit = poly[poly.contains(pt)]
    if len(hit):
        i = hit.index[0]
        rule, edge = "contains", float(pt.distance(poly.geometry.loc[i].exterior))
    else:
        d = poly.distance(pt)
        if not len(d) or d.min() > max_dist_m:
            return None, "none", float("nan")
        i = d.idxmin()
        rule, edge = f"nearest_{d.min():.0f}m", float(d.min())

    area_ha = poly.geometry.loc[i].area / 1e4
    if area_ha < min_paddock_ha:
        near = poly[poly.distance(pt) <= upgrade_search_m].copy()
        if len(near):
            near["_ha"] = near.geometry.area / 1e4
            near["_comp"] = near.geometry.length / np.sqrt(near.geometry.area)
            # Only paddock-shaped candidates are eligible; take the largest of those, not the
            # largest overall, so a neighbouring blob cannot win on size alone.
            ok = near[(near._comp <= max_upgrade_compactness) &
                      (near._ha >= upgrade_ratio * max(area_ha, 0.01))].copy()
            if claimed:
                # Only a DIFFERENT crop's claim blocks the upgrade. Two trials of the same crop
                # sharing a paddock duplicates a sample but does not contradict a label, and
                # under NVT protocol the surrounding paddock is that same crop anyway.
                ok = ok[[claimed.get(j, crop) == crop for j in ok.index]]
            if len(ok):
                # NEAREST eligible paddock, not the largest. The trial sits on the edge of
                # the field it belongs to, so "the big paddock immediately alongside" is the
                # right target; picking the largest within the search radius can reach past
                # it to an unrelated field (Example A: 51.6 ha at 41 m is correct, the
                # 96.7 ha at 98 m is a different paddock).
                ok["_d"] = ok.distance(pt)
                j = ok._d.idxmin()
                g = ok.geometry.loc[j]
                return (g, f"{rule}+upgraded_{area_ha:.1f}to{ok._ha.loc[j]:.0f}ha",
                        float(pt.distance(g)))
    return poly.geometry.loc[i], rule, edge


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", required=True, help="sites csv with an aoi_stub column")
    ap.add_argument("--polydir", required=True, help="dir of <stub>_filt.gpkg")
    ap.add_argument("--out", required=True)
    ap.add_argument("--window-m", type=float, default=200.0, help="baseline window")
    ap.add_argument("--erode-m", type=float, default=10.0,
                    help="shrink the paddock by this before averaging, so edge pixels mixed "
                         "with road/tree do not re-import the contamination we are removing")
    ap.add_argument("--max-dist-m", type=float, default=50.0)
    # These default to None so `match_polygon`'s own tuned defaults apply. They were plain
    # numbers before, which silently overrode the tuning: the user's 5.0 -> 10.0 ruling was
    # applied to the function but not to the flag, so every run kept matching at 5.0 and
    # Example A's 5.1 ha strip was never upgraded as they had directed. A default
    # duplicated in two places is a default that will drift — keep exactly one copy.
    ap.add_argument("--min-paddock-ha", type=float, default=None,
                    help="below this, try to upgrade to a larger adjacent polygon "
                         "(default: match_polygon's tuned value)")
    ap.add_argument("--upgrade-ratio", type=float, default=None,
                    help="only upgrade when the neighbour is this many times larger")
    ap.add_argument("--no-upgrade", action="store_true", help="disable the upgrade rule")
    ap.add_argument("--chm-dir", default="/scratch/xe2/cb8590/Global_Canopy_Height_v2",
                    help="1 m canopy height tiles; see --no-tree-mask to disable")
    ap.add_argument("--no-tree-mask", action="store_true")
    ap.add_argument("--all-bands", action="store_true",
                    help="store the paddock median of all 10 Sentinel-2 bands instead of "
                         "only the three indices — the input a multi-band model needs")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    os.environ.setdefault("PROJ_NETWORK", "OFF")
    import datacube
    import geopandas as gpd
    import xarray as xr
    from rasterio.features import geometry_mask
    from shapely.geometry import Point

    sites = pd.read_csv(args.sites)
    if args.limit:
        sites = sites.head(args.limit)
    dc = datacube.Datacube(app="extract_paddock")

    # Only pass what was explicitly set, so unset flags fall through to the tuned defaults.
    match_kw = {}
    if args.no_upgrade:
        match_kw["min_paddock_ha"] = 0.0
    elif args.min_paddock_ha is not None:
        match_kw["min_paddock_ha"] = args.min_paddock_ha
    if args.upgrade_ratio is not None:
        match_kw["upgrade_ratio"] = args.upgrade_ratio
    print(f"matcher: {match_kw or 'tuned defaults'}")

    masker = None
    if not args.no_tree_mask:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "sentinel_ndvi"))
        from tree_mask import TreeMasker
        masker = TreeMasker(args.chm_dir)

    done = set()
    if os.path.exists(args.out):        # resume: skip trials already written
        done = set(pd.read_csv(args.out, usecols=["TrialCode"]).TrialCode.unique())
        print(f"resuming: {len(done)} trials already done")

    poly_cache = {}
    # Which polygon each already-matched trial took, per (AOI, year), so the upgrade rule can
    # refuse to move a trial onto ground another crop has claimed. Sorting by AOI and year
    # keeps co-located trials adjacent, so the claims are populated before their neighbours
    # are matched rather than after.
    claims = {}
    sites = sites.sort_values(["aoi_stub", "Year"]) if "Year" in sites.columns \
        else sites.sort_values("aoi_stub")
    n_ok = n_skip = 0
    for _, r in sites.iterrows():
        if r["TrialCode"] in done:
            continue
        stub = r["aoi_stub"]
        if stub not in poly_cache:
            p = os.path.join(args.polydir, f"{stub}_filt.gpkg")
            poly_cache[stub] = (gpd.read_file(p).to_crs("EPSG:3577")
                                if os.path.exists(p) else None)
        poly = poly_cache[stub]
        if poly is None or not len(poly):
            print(f"{r['TrialCode']}: no polygons for {stub}", flush=True)
            n_skip += 1
            continue

        pt = gpd.GeoSeries([Point(float(r["lon"]), float(r["lat"]))],
                           crs="EPSG:4326").to_crs("EPSG:3577").iloc[0]
        ckey = (stub, r.get("Year"))
        geom, rule, edge_m = match_polygon(poly, pt, args.max_dist_m,
                                           claimed=claims.get(ckey), crop=r.get("crop"),
                                           **match_kw)
        if geom is not None:
            # Record the claim by polygon index, which is what the upgrade filter looks up.
            hit = poly.index[poly.geometry.geom_equals(geom)]
            if len(hit):
                claims.setdefault(ckey, {})[hit[0]] = r.get("crop")
        if geom is None:
            print(f"{r['TrialCode']}: no polygon within {args.max_dist_m} m", flush=True)
            n_skip += 1
            continue
        paddock_ha = geom.area / 1e4
        eroded = geom.buffer(-args.erode_m)
        # A paddock narrower than 2x the erosion vanishes. Fall back to the raw polygon and
        # say so, rather than silently dropping the trial or averaging an empty mask.
        if eroded.is_empty or eroded.area <= 0:
            eroded, rule = geom, rule + "+noerode"

        t0 = (pd.to_datetime(r["sow"]) - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
        t1 = (pd.to_datetime(r["harv"]) + pd.Timedelta(days=30)).strftime("%Y-%m-%d")
        b = eroded.bounds
        pad = args.window_m       # ensure the 200 m baseline window fits inside the read
        measurements = (ALL_BANDS + ["oa_fmask"]) if args.all_bands else BANDS
        ds = dc.load(product=PRODUCTS,
                     x=(min(b[0], pt.x - pad), max(b[2], pt.x + pad)),
                     y=(min(b[1], pt.y - pad), max(b[3], pt.y + pad)),
                     crs="EPSG:3577", time=(t0, t1), measurements=measurements,
                     output_crs="EPSG:3577", resolution=(-10, 10), group_by="solar_day")
        if ds.sizes.get("time", 0) == 0:
            n_skip += 1
            continue

        tr = ds.geobox.transform
        shape = (ds.sizes["y"], ds.sizes["x"])
        pad_mask = ~geometry_mask([eroded], out_shape=shape, transform=tr, invert=False)
        xs, ys = ds.x.values, ds.y.values
        win = ((np.abs(xs - pt.x) <= args.window_m / 2)[None, :] &
               (np.abs(ys - pt.y) <= args.window_m / 2)[:, None])
        if pad_mask.sum() == 0:
            n_skip += 1
            continue

        # Tree mask, applied to BOTH supports so the paddock-vs-window comparison is not
        # quietly changed by it. pad_deg is sized to the read, not to a fixed radius: a
        # 1,300 ha paddock spans several kilometres and a fixed 440 m pad would miss the
        # canopy tile covering its far end.
        tree_stats = {"chm_covered": False, "n_masked_px": 0}
        if masker is not None:
            bb = ds.geobox.extent.boundingbox
            pad_deg = max((bb.right - bb.left), (bb.top - bb.bottom)) / 111_320.0 + 0.004
            tree, tree_stats = masker.mask_for_geobox(
                ds.geobox, float(r["lon"]), float(r["lat"]), pad_deg=pad_deg)
            # Count the trees removed from THIS paddock, not from the whole read — the read
            # is padded well past the polygon, so the scene-wide count says nothing about
            # how contaminated the paddock was.
            tree_stats["n_masked_px"] = int((pad_mask & tree).sum())
            pad_mask &= ~tree
            win &= ~tree
            if pad_mask.sum() == 0:      # whole paddock read as canopy — do not average it
                print(f"{r['TrialCode']}: paddock fully tree-masked, skipped", flush=True)
                n_skip += 1
                continue

        pad_da = xr.DataArray(pad_mask, dims=("y", "x"), coords={"y": ds.y, "x": ds.x})
        win_da = xr.DataArray(win, dims=("y", "x"), coords={"y": ds.y, "x": ds.x})
        if not args.all_bands:
            ip = indices_from(ds, pad_da)
            iw = indices_from(ds, win_da)

        clear = ((ds["oa_fmask"] == FMASK_CLEAR) & pad_da).sum(dim=("x", "y"))
        cols = {
            "TrialCode": r["TrialCode"], "crop": r["crop"],
            "sow": pd.to_datetime(r["sow"]).date().isoformat(),
            "time": pd.to_datetime(ds["time"].values),
            "match_rule": rule, "edge_dist_m": round(edge_m, 1),
            "paddock_ha": round(paddock_ha, 2),
            "n_px_paddock": int(pad_mask.sum()), "n_px_window": int(win.sum()),
            "n_clear_px": clear.values.astype(int),
            "chm_covered": bool(tree_stats["chm_covered"]),
            "n_tree_px": int(tree_stats["n_masked_px"]),
        }
        if args.all_bands:
            m = (ds["oa_fmask"] == FMASK_CLEAR) & pad_da
            for b in ALL_BANDS:
                v = ds[b].where((ds[b] != NODATA) & m).astype("float32") / REFL_SCALE
                # Median only. The mean of a paddock is what a tree line or a header trail
                # moves; the median is what the whole exercise settled on, and storing both
                # would double a file that already has 10 bands x ~48 dates per trial.
                cols[b.replace("nbart_", "")] = v.median(dim=("x", "y")).values
        else:
            for name in ("ndvi", "ndyi", "cfi"):
                cols[f"{name}_pad_median"] = ip[name].median(dim=("x", "y")).values
                cols[f"{name}_pad_mean"] = ip[name].mean(dim=("x", "y")).values
                cols[f"{name}_win_mean"] = iw[name].mean(dim=("x", "y")).values
        out = pd.DataFrame(cols)
        out = out[out["n_clear_px"] > 0]
        if out.empty:
            n_skip += 1
            continue
        out.to_csv(args.out, mode="a", header=not os.path.exists(args.out), index=False)
        n_ok += 1
        print(f"{r['TrialCode']}: {len(out)} obs, {paddock_ha:.0f} ha, {rule}", flush=True)

    print(f"\ndone: {n_ok} trials extracted, {n_skip} skipped -> {args.out}")


if __name__ == "__main__":
    main()
