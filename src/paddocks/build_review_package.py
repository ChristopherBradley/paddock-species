#!/usr/bin/env python3
"""
Build a single QGIS GeoPackage for reviewing every chosen paddock by hand, and ingest the
verdicts back out again.

TRIAGE FIRST, THEN REVIEW. The user judged 36 polygons good or bad (loaded from --seed-verdicts). A first pass concluded
that no geometric rule could reproduce those verdicts, on the strength of this pair:

    Example C (2021)   5.9 ha  -> GOOD
    Example D (2022)   6.0 ha  -> BAD  (wrong paddock)

(codes in `memory/WORKED_EXAMPLES_SENSITIVE.md`; same site, adjacent years)

That conclusion was wrong, and only because the pair was tested on AREA and COMPACTNESS alone.
The two are trivially separable by a signal that was never checked: the trial point is INSIDE
the 2021 polygon and 137 m OUTSIDE the 2022 one. The confusion came from `match_rule`, which
reads "contains+upgraded_2.0to6ha" — the "contains" describes the polygon the point fell in
BEFORE the upgrade moved the match to a neighbour, so a rule string that says "contains" can
end up attached to a polygon the point is nowhere near. All 259 upgraded matches are like
this, and the upgrade reaches up to 148 m, far enough to cross a road into the next field.

**Lesson: "no rule can separate these" is only ever a statement about the features tried.**

The composite triage below therefore catches 17/17 of the judged-bad polygons while wrongly
flagging 2/19 of the good ones — but on three thresholds fitted to 36 points, so it is
in-sample and its true miss rate is unknown. It ORDERS the queue; it does not replace the
human, and `review_batch = validation` exists to measure what it misses.

REVIEW BY POLYGON, NOT BY TRIAL. 3,222 trials share only 1,992 distinct polygons, because the
same paddock recurs across seasons and co-located trials share one. Judging the polygon once
and propagating to its trials removes 38 % of the work for free.

QGIS WORKFLOW
  1. Open the .gpkg; layer `review` is one row per distinct polygon, `trials` the points.
  2. Toggle editing on `review` and fill `verdict` with: good | bad | redraw
     (`reason` is free text — "wrong paddock", "whole region", "trial site only", ...)
  3. To redraw: set verdict = redraw, then digitise the correct paddock into the
     `manual_polygons` layer, copying `poly_id` across so the two can be matched up.
  4. Save, then run this script with `ingest` to produce the corrected training set.

`review_order` sorts likely-bad and high-trial-count polygons first, so stopping early still
buys the most. Verdicts already given are pre-filled.

Output carries TrialCodes and coordinates, so it is written as *_SENSITIVE.gpkg.
"""
import argparse
import hashlib
import os

import geopandas as gpd
import numpy as np
import pandas as pd

# Verdicts already given are loaded from a *_SENSITIVE csv, NOT hardcoded here. TrialCodes are
# NDA data and this file is tracked in git — an earlier revision embedded the 36 codes inline
# and the pre-commit scan caught them. Anything keyed by TrialCode belongs on /scratch.
GROUP = {"Canola": "Canola", "Wheat": "Cereal", "Barley": "Cereal", "Oat": "Cereal",
         "Chickpea": "Legume", "Faba Bean": "Legume", "Field Pea": "Legume",
         "Lentil": "Legume", "Lupin": "Legume"}


def build(args):
    g = gpd.read_file(args.chosen_gpkg, layer="chosen").to_crs("EPSG:3577")
    g["poly_id"] = [hashlib.md5(w).hexdigest()[:12] for w in g.geometry.to_wkb()]
    g["compactness"] = g.geometry.length / np.sqrt(g.geometry.area)
    g["group"] = g.crop.map(GROUP)

    # Distance from the trial point to its FINAL polygon. This is the signal that was missed
    # first time round: `match_rule` says "contains" for a match that was subsequently
    # UPGRADED to a neighbour, so the rule string describes the pre-upgrade polygon while the
    # geometry is the post-upgrade one. Every one of the 259 upgraded matches has its trial
    # point outside the polygon it ended up with, and the upgrade reaches up to 148 m — far
    # enough to cross a road into the next field, which is exactly the Example D failure.
    pt = gpd.GeoSeries(gpd.points_from_xy(g.lon, g.lat), crs="EPSG:4326").to_crs("EPSG:3577")
    g["dist_m"] = [0.0 if gm.contains(p) else gm.distance(p)
                   for gm, p in zip(g.geometry, pt)]

    agg = g.groupby("poly_id").agg(
        n_trials=("TrialCode", "size"),
        trial_codes=("TrialCode", lambda s: ",".join(sorted(s))),
        crops=("crop", lambda s: ",".join(sorted(set(s)))),
        n_crops=("crop", "nunique"),
        groups=("group", lambda s: ",".join(sorted(set(s)))),
        n_groups=("group", "nunique"),
        years=("Year", lambda s: ",".join(str(v) for v in sorted(set(s)))),
        site=("site", "first"), state=("state", "first"),
        paddock_ha=("paddock_ha", "first"), compactness=("compactness", "first"),
        match_rule=("match_rule_new", "first"),
        # Best case across the polygon's trials: if even the CLOSEST trial point is far
        # outside, the polygon is unlikely to be any of their fields.
        dist_m=("dist_m", "min"),
    )
    geom = g.drop_duplicates("poly_id").set_index("poly_id").geometry
    R = gpd.GeoDataFrame(agg.join(geom), geometry="geometry", crs="EPSG:3577").reset_index()

    # Composite triage. On the 36 judged polygons this catches 17/17 bad while wrongly
    # flagging 2/19 good, because the three failure modes the user named are each detectable
    # by a DIFFERENT signal and no single one covers them:
    #   * "wrong paddock" / "trial site only" -> the point is outside the chosen polygon
    #   * "whole region"                      -> the polygon is enormous (347-1048 ha)
    #   * "overlapping paddock"               -> another crop's trial shares the polygon
    # An area-only rule was tried first and could not work: Examples C (good) and
    # D (bad) are 0.1 ha apart at the same site. Distance separates them cleanly
    # (0 m vs 137 m) — the first attempt simply never tested it.
    #
    # STILL NOT A CLASSIFIER: three thresholds fitted to 36 points, so 17/17 is in-sample and
    # the true miss rate is unknown. That is what `review_batch = validation` exists to
    # measure — review those too, or the "presumed OK" pile is an untested assumption.
    # Path to the Fourier-NDWI composite SAM actually segmented, so a reviewer can load the
    # evidence behind a polygon straight from the attribute table rather than hunting for an
    # AOI stub. One AOI serves several trials, so this is the first trial's — they share it.
    if args.tif_csv and os.path.exists(args.tif_csv):
        t2 = pd.read_csv(args.tif_csv).drop_duplicates("TrialCode").set_index("TrialCode")
        first = g.drop_duplicates("poly_id").set_index("poly_id").TrialCode
        R["ndwi_tif"] = R.poly_id.map(first).map(t2.ndwi).fillna("")
        R["filt_gpkg"] = R.poly_id.map(first).map(t2.filt).fillna("")

    R["conflict"] = R.n_crops > 1
    # 3 ha, not 2: the one polygon the validation batch caught as bad (a trial site with the
    # surrounding paddock missed) is 2.8 ha, so a 2 ha cut let it through. 3 ha catches it for
    # +40 polygons of extra review — cheap insurance given the mode it represents.
    R["triage_flag"] = ((R.dist_m > 25) | (R.paddock_ha < 3)
                        | (R.paddock_ha > 300) | R.conflict)
    R["flag_reason"] = (
        pd.Series(np.where(R.dist_m > 25, "point_outside;", ""), index=R.index)
        + np.where(R.paddock_ha < 3, "too_small;", "")
        + np.where(R.paddock_ha > 300, "too_big;", "")
        + np.where(R.conflict, "crop_conflict;", ""))
    R["verdict"] = ""
    R["reason"] = ""

    seed = {}
    if args.seed_verdicts and os.path.exists(args.seed_verdicts):
        sv = pd.read_csv(args.seed_verdicts).fillna("")
        seed = {r.TrialCode: (r.verdict, r.reason) for r in sv.itertuples()}
    tc2poly = dict(zip(g.TrialCode, g.poly_id))
    n_seed = 0
    for tc, (v, why) in seed.items():
        pid = tc2poly.get(tc)
        if pid is None:
            continue
        m = R.poly_id == pid
        # A polygon shared by trials with opposing verdicts must not silently take one of them.
        if R.loc[m, "verdict"].iloc[0] not in ("", v):
            R.loc[m, "verdict"] = "CONFLICTED_SEED"
            R.loc[m, "reason"] = "two trials on this polygon were judged differently"
            continue
        R.loc[m, "verdict"] = v
        R.loc[m, "reason"] = why
        n_seed += 1

    # A random sample of UNFLAGGED polygons, so the triage's miss rate can be estimated
    # instead of assumed. Without it, "presumed OK" is a claim with no evidence behind it.
    rng = np.random.default_rng(0)
    unflagged = R.index[(~R.triage_flag) & R.verdict.eq("")]
    val = set(rng.choice(unflagged, min(args.validation_n, len(unflagged)), replace=False))
    R["review_batch"] = np.where(R.triage_flag, "flagged",
                         np.where(R.index.isin(val), "validation", "unflagged"))

    R["review_order"] = (R.verdict.eq("").astype(int) * 1_000_000
                         - R.triage_flag.astype(int) * 100_000
                         - R.review_batch.eq("validation").astype(int) * 50_000
                         - R.n_trials * 100
                         + np.arange(len(R)))
    R = R.sort_values("review_order").reset_index(drop=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    if os.path.exists(args.out):
        os.remove(args.out)
    R.to_crs("EPSG:4326").to_file(args.out, layer="review", driver="GPKG")

    pts = g.to_crs("EPSG:4326").copy()
    pts["geometry"] = gpd.points_from_xy(pts.lon, pts.lat)
    if args.tif_csv and os.path.exists(args.tif_csv):
        t3 = pd.read_csv(args.tif_csv).drop_duplicates("TrialCode").set_index("TrialCode")
        pts["ndwi_tif"] = pts.TrialCode.map(t3.ndwi).fillna("")
    keep = ["TrialCode", "crop", "group", "Year", "state", "site", "poly_id", "paddock_ha",
            "match_rule_new", "share_n", "conflict_9class", "conflict_3class", "dist_m",
            "ndwi_tif"]
    pts[[c for c in keep if c in pts.columns] + ["geometry"]].to_file(
        args.out, layer="trials", driver="GPKG")

    # Empty layer for hand-digitised replacements. Written with one dummy row then truncated,
    # because GPKG needs a schema to exist before QGIS will let you draw into it.
    man = gpd.GeoDataFrame({"poly_id": ["EXAMPLE_DELETE_ME"], "note": [""]},
                           geometry=[R.geometry.iloc[0]], crs="EPSG:3577")
    man.to_crs("EPSG:4326").to_file(args.out, layer="manual_polygons", driver="GPKG")

    print(f"{len(g)} trials -> {len(R)} distinct polygons to review "
          f"({100*(1-len(R)/len(g)):.0f}% less work than per-trial)")
    print(f"  pre-filled from your verdicts: {n_seed}")
    print(f"  triage-flagged (review first): {int(R.triage_flag.sum())}")
    for reason in ["point_outside", "too_small", "too_big", "crop_conflict"]:
        print(f"      {reason:14s} {int(R.flag_reason.str.contains(reason).sum()):5d}")
    print(f"  validation sample (unflagged) : "
          f"{int((R.review_batch=='validation').sum())}")
    print(f"  remaining unflagged           : {int((R.review_batch=='unflagged').sum())}")
    print(f"\n-> {args.out}  (layers: review, trials, manual_polygons)")
    print("   Fill `verdict` with good | bad | redraw, then run: "
          f"{os.path.basename(__file__)} ingest")


def refresh(args):
    """Re-copy the review-layer verdicts onto the trials layer, in place.

    The verdict lives on the POLYGON (one judgement covers all its trials) but is most usable
    on the POINTS: QGIS scales point markers with zoom while polygons keep their true extent,
    so at a state-wide zoom the polygons vanish to slivers and the points stay readable. That
    means the attribute has to be duplicated onto the trials layer — and a duplicate goes
    stale the moment the review layer is edited, which is why this is a re-runnable command
    rather than something done once at build time.

    Only the trials layer is rewritten. The review layer, with your edits, is read and left
    exactly as it is.
    """
    R = gpd.read_file(args.out, layer="review")
    T = gpd.read_file(args.out, layer="trials")
    cols = ["verdict", "reason", "review_batch", "triage_flag", "flag_reason"]
    have = [c for c in cols if c in R.columns]
    idx = R.set_index("poly_id")
    for c in have:
        T[c] = T.poly_id.map(idx[c])
    T["verdict"] = T.verdict.fillna("")
    T.to_file(args.out, layer="trials", driver="GPKG")
    n = int((T.verdict.astype(str).str.len() > 0).sum())
    print(f"trials layer refreshed: {len(T)} points, {n} carrying a verdict")
    print(f"  columns added: {', '.join(have)}")
    print(f"  {T.verdict.value_counts().to_dict()}")


def ingest(args):
    R = gpd.read_file(args.out, layer="review")
    done = R[R.verdict.isin(["good", "bad", "redraw"])]
    print(f"{len(done)}/{len(R)} polygons judged ({100*len(done)/len(R):.1f}%)")
    print(done.verdict.value_counts().to_string())
    try:
        man = gpd.read_file(args.out, layer="manual_polygons")
        man = man[man.poly_id != "EXAMPLE_DELETE_ME"]
        print(f"hand-drawn replacements: {len(man)}")
    except Exception:
        man = None

    rows = []
    for r in R.itertuples():
        for tc in str(r.trial_codes).split(","):
            rows.append({"TrialCode": tc, "poly_id": r.poly_id, "verdict": r.verdict,
                         "reason": r.reason, "paddock_ha": r.paddock_ha})
    T = pd.DataFrame(rows)
    T["usable"] = T.verdict.eq("good") | (T.verdict.eq("redraw") & T.poly_id.isin(
        set(man.poly_id) if man is not None else set()))
    T.to_csv(args.trials_out, index=False)
    print(f"\n{int(T.usable.sum())}/{len(T)} trials usable")
    print(f"-> {args.trials_out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["build", "refresh", "ingest"],
                    help="build: create the package (OVERWRITES, discarding any review edits). "
                         "refresh: copy verdicts onto the trials layer, edits preserved. "
                         "ingest: turn verdicts into a training filter.")
    ap.add_argument("--chosen-gpkg")
    ap.add_argument("--out", required=True)
    ap.add_argument("--trials-out")
    ap.add_argument("--seed-verdicts", help="csv of TrialCode,verdict,reason already judged")
    ap.add_argument("--tif-csv", help="trial_to_tif csv from link_tifs_by_trial.py")
    ap.add_argument("--validation-n", type=int, default=150,
                    help="unflagged polygons to sample for measuring the triage miss rate")
    args = ap.parse_args()
    if args.mode == "build":
        build(args)
    elif args.mode == "refresh":
        refresh(args)
    else:
        ingest(args)


if __name__ == "__main__":
    main()
