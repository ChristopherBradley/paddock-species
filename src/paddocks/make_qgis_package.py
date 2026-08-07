#!/usr/bin/env python3
"""
Consolidate a review shortlist into ONE QGIS project's worth of layers.

The per-AOI layers (`<stub>_trials.gpkg`, `<stub>_chosen.gpkg`) are named after the AOI, not
the trial, so a shortlist of TrialCodes gives no clue which file to open — and a shortlist
spanning 20 AOIs would mean opening 40 files. This writes a single GeoPackage with three
layers covering every trial on the list, so the whole review is one drag-and-drop:

  trials     the trial points, attributed with verdict, note, flags, and the AOI they came
             from (so the per-AOI files are still findable if you want the full context)
  chosen     the polygon the algorithm picked for each trial, same attributes
  candidates every other polygon within --context-m of a listed trial — what it could have
             picked instead, which is the thing you are usually judging

    python3 make_qgis_package.py --review .../review_sites.csv --polydir .../samgeo/full \
        --sites .../aois.csv.sites.csv --out .../review_shortlist.gpkg \
        --trials-from .../verdicts_w1.csv

Layers carry a `label` column ("TrialCode | verdict | area ha") for QGIS labelling, so the
map is readable without opening the attribute table.
"""
import argparse
import os

import numpy as np
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", required=True, help="review_sites.csv (flags, aoi_stub)")
    ap.add_argument("--sites", required=True, help="sites csv with lat/lon")
    ap.add_argument("--polydir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--trials-from", nargs="*",
                    help="verdict CSVs; restrict to these trials and carry their verdicts")
    ap.add_argument("--trials", nargs="*", help="explicit TrialCodes")
    ap.add_argument("--only-unusable", action="store_true",
                    help="keep only trials whose verdict is not good/trial_plot")
    ap.add_argument("--good", type=int, default=0,
                    help="also include this many trials judged good, so the package shows "
                         "what a correct match looks like and not only the failures")
    ap.add_argument("--unreviewed", type=int, default=0,
                    help="also include this many never-reviewed trials, sampled at random")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--context-m", type=float, default=600.0)
    args = ap.parse_args()

    os.environ.setdefault("PROJ_NETWORK", "OFF")
    import geopandas as gpd
    from shapely.geometry import Point

    rev = pd.read_csv(args.review)
    # review_sites.csv ships EMPTY annotation columns for the human reviewer; they collide
    # with the reviewer files on merge and silently become verdict_x/verdict_y.
    rev = rev.drop(columns=[c for c in ("verdict", "note", "better_polygon_note",
                                        "claude_verdict", "claude_note")
                            if c in rev.columns])
    OKV = ["good", "trial_plot"]
    if args.trials_from:
        verd = pd.concat([pd.read_csv(f) for f in args.trials_from],
                         ignore_index=True).drop_duplicates("TrialCode")
        rev = rev.merge(verd, on="TrialCode", how="left")
    else:
        rev["verdict"] = np.nan
    # `status` is what you colour by in QGIS. Three values, because "not yet looked at" is a
    # genuinely different thing from "looked at and fine" — collapsing them would make an
    # unreviewed match look endorsed.
    rev["status"] = np.where(rev.verdict.isna(), "unreviewed",
                             np.where(rev.verdict.isin(OKV), "good", "bad"))

    rng = np.random.default_rng(args.seed)

    def take(df, n):
        return df if n >= len(df) else df.iloc[rng.choice(len(df), n, replace=False)]

    if args.trials:
        rev = rev[rev.TrialCode.isin(args.trials)]
    else:
        keep = [rev[rev.status == "bad"]]
        if not args.only_unusable:
            keep.append(take(rev[rev.status == "good"], args.good))
            keep.append(take(rev[rev.status == "unreviewed"], args.unreviewed))
        rev = pd.concat(keep)
    if rev.empty:
        raise SystemExit("no trials selected")
    print("selected: " + ", ".join(f"{k} {v}" for k, v in
                                   rev.status.value_counts().items()))

    sites = pd.read_csv(args.sites).drop_duplicates("TrialCode").set_index("TrialCode")
    pt_rows, ch_rows, cand_rows = [], [], []
    cache = {}
    for _, r in rev.iterrows():
        code = r["TrialCode"]
        if code not in sites.index:
            continue
        s = sites.loc[code]
        pt = gpd.GeoSeries([Point(float(s.lon), float(s.lat))],
                           crs="EPSG:4326").to_crs("EPSG:3577").iloc[0]
        stub = r["aoi_stub"]
        if stub not in cache:
            p = os.path.join(args.polydir, f"{stub}_filt.gpkg")
            cache[stub] = gpd.read_file(p).to_crs("EPSG:3577") if os.path.exists(p) else None
        poly = cache[stub]

        verdict = "" if pd.isna(r.get("verdict")) else str(r.get("verdict"))
        base = {"TrialCode": code, "crop": r.get("crop", ""), "aoi_stub": stub,
                "status": r["status"],
                "match_rule": r.get("match_rule", ""), "flags": r.get("flags", ""),
                "verdict": verdict, "note": str(r.get("note", "") or ""),
                "area_ha": r.get("area_ha", np.nan),
                "source_gpkg": os.path.join(args.polydir, f"{stub}_filt.gpkg")}
        base["label"] = f"{code} | {verdict or 'unreviewed'} | {base['area_ha']} ha"
        pt_rows.append({**base, "geometry": pt})

        if poly is None or not len(poly):
            continue
        near = poly[poly.distance(pt) <= args.context_m]
        # The chosen polygon: recomputed the same way extraction does, via the shared matcher.
        from extract_paddock import match_polygon
        g, rule, _ = match_polygon(poly, pt, 50.0)
        for _, q in near.iterrows():
            is_chosen = g is not None and q.geometry.equals(g)
            row = {**base, "poly_area_ha": round(q.geometry.area / 1e4, 1),
                   "compactness": round(q.geometry.length / np.sqrt(q.geometry.area), 2),
                   "geometry": q.geometry}
            (ch_rows if is_chosen else cand_rows).append(row)

    if not os.path.dirname(args.out) == "":
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    written = []
    for name, rows in (("trials", pt_rows), ("chosen", ch_rows), ("candidates", cand_rows)):
        if not rows:
            continue
        gpd.GeoDataFrame(rows, crs="EPSG:3577").to_file(args.out, layer=name, driver="GPKG")
        written.append(f"{name} ({len(rows)})")
    print(f"-> {args.out}")
    print("   layers: " + ", ".join(written))
    print(f"   {rev.TrialCode.nunique()} trials")


if __name__ == "__main__":
    main()
