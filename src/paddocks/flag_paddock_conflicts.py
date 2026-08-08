#!/usr/bin/env python3
"""
Flag trials whose paddock is shared with another trial — the label-corruption filter.

WHAT THIS CATCHES, and why no existing flag caught it. NVT sites run several crop trials side
by side in one field. SAM segments that field as ONE polygon, so every trial at the site gets
an IDENTICAL paddock-median time series while carrying a DIFFERENT crop label. The model is
then trained on identical features with contradictory targets, which is not noise but a hard
ceiling: where four crops share one polygon, no classifier can exceed 25 % on those rows.

None of the earlier quality flags see this, because each is a property of ONE trial's polygon
(size, compactness, tree fraction, observation count) and this is a property of the RELATION
between trials. `separability_diagnosis.py` likewise tested only per-trial and per-panel
drivers — cloud gap, match rule, paddock size, compactness — and so reported "no evidence that
data quality is the lever" while this went unmeasured.

Measured on the 2,477-trial training set (2026-08-08):
  * 31.8 % sit on a polygon shared, in the same year, with a different-crop trial.
  * Canola on such a polygon has median CFI 1489 against 1971 for canola on an unshared
    polygon — a gap of +482 [95 % CI +348, +551], measured WITHIN canola so no class-mix
    confound. The paddock median is averaging canola with a neighbouring crop.
  * The upgrade rule is a major generator: 72.3 % of upgraded matches land on a polygon also
    used by another trial, and upgrades from an origin under 2 ha score AUC 0.749 against
    0.832 for non-upgraded matches.
  * Collapsing to Canola / Cereal / Legume resolves 540 of the 788 conflicts (69 %), because
    co-located trials are usually of the same agronomic group — pulse trials sit together,
    cereal trials sit together. Only 59 polygon-groups are genuinely cross-group.

Emits one row per trial so downstream code can filter without recomputing geometry, plus a
`usable_9class` / `usable_3class` recommendation. Two levels are offered deliberately: the
3-class column is far less restrictive and is the one to use if the model targets groups.

Output carries TrialCodes, so it is written as *_SENSITIVE.csv.
"""
import argparse
import hashlib

import geopandas as gpd
import pandas as pd

GROUP = {"Canola": "Canola", "Wheat": "Cereal", "Barley": "Cereal", "Oat": "Cereal",
         "Chickpea": "Legume", "Faba Bean": "Legume", "Field Pea": "Legume",
         "Lentil": "Legume", "Lupin": "Legume"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chosen-gpkg", required=True,
                    help="cfi_heatmap_ALL gpkg (layer `paddocks`): the polygon each trial got")
    ap.add_argument("--labeled", help="nvt_trials_labeled.csv, for the co-location distance")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    G = gpd.read_file(args.chosen_gpkg, layer="paddocks").drop_duplicates(subset=["TrialCode"])
    G["group"] = G.crop.map(GROUP)

    # Identity by exact geometry. Two trials given the SAME polygon necessarily have the same
    # time series; near-duplicate polygons are a separate (milder) problem and are not flagged
    # here, so this is a lower bound on the damage rather than a generous estimate.
    G["gkey"] = [hashlib.md5(w).hexdigest() for w in G.geometry.to_wkb()]
    # Scoped to the year: the same paddock legitimately recurs across seasons under rotation,
    # and flagging that would discard the repeat-site structure the spatial CV depends on.
    G["ykey"] = G.gkey + "_" + G.Year.astype(str)

    g = G.groupby("ykey")
    G["share_n"] = g.TrialCode.transform("size")
    G["n_crops"] = g.crop.transform("nunique")
    G["n_groups"] = g["group"].transform("nunique")
    G["shared"] = G.share_n > 1
    G["conflict_9class"] = G.shared & (G.n_crops > 1)
    G["conflict_3class"] = G.shared & (G.n_groups > 1)
    G["usable_9class"] = ~G.conflict_9class
    G["usable_3class"] = ~G.conflict_3class

    cols = ["TrialCode", "crop", "group", "Year", "state", "panel", "paddock_ha", "match_rule",
            "share_n", "n_crops", "n_groups", "shared",
            "conflict_9class", "conflict_3class", "usable_9class", "usable_3class"]
    if args.labeled:
        lab = pd.read_csv(args.labeled).drop_duplicates("TrialCode").set_index("TrialCode")
        G = G.join(lab[["nearest_diffcrop_same_year_m"]], on="TrialCode")
        cols.append("nearest_diffcrop_same_year_m")

    out = pd.DataFrame(G[cols]).sort_values(["conflict_9class", "share_n"], ascending=False)
    out.to_csv(args.out, index=False)

    n = len(out)
    print(f"{n} trials")
    print(f"  shared polygon (same year) : {int(out.shared.sum()):5d} ({100*out.shared.mean():.1f}%)")
    print(f"  conflicting, 9-class       : {int(out.conflict_9class.sum()):5d} "
          f"({100*out.conflict_9class.mean():.1f}%)")
    print(f"  conflicting, 3-group       : {int(out.conflict_3class.sum()):5d} "
          f"({100*out.conflict_3class.mean():.1f}%)")
    print(f"  -> collapsing to 3 groups resolves "
          f"{int(out.conflict_9class.sum() - out.conflict_3class.sum())} conflicts")
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
