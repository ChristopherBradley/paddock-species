#!/usr/bin/env python3
"""
Fit the deployable yield regressor — the missing sibling of `fit_map_model.py`
(output/YIELD_FEASIBILITY.md #1). Unlike `train_yield.py`, which VALIDATES with held-out years
and sites, this fits on every usable row: the paddock being predicted at map time is never in
the training set anyway, and withholding rows only makes the shipped model worse.

Ships one crop at a time. Default target is `Cereal` (Wheat+Barley+Oat pooled through GROUP in
train_species.py, matching what the crop-type classifier itself predicts), because the
classifier's `Cereal` polygons are the ones this model has to score at inference time — training
on Wheat+Barley alone (as `output/YIELD_FEASIBILITY.md` first framed it) would leave Oat
paddocks scored by an out-of-distribution model. See `output/YIELD_cereal_pooled.md` for the
measured cost of pooling against wheat and barley scored separately.

Canola is intentionally NOT supported here: `YIELD_FEASIBILITY.md` found optical-only canola
yield (R2 0.27) does not beat guessing the year and state (R2 0.29) — shipping it would be worse
than leaving the column empty, which `predict_tile.py`'s abstain path already knows how to do.

    python3 fit_yield_model.py --indices "$D/samgeo/ts_v2/*_SENSITIVE.csv" \
        --labeled $D/nvt_trials_labeled.csv --keep $D/keep_arms/keep_reviewed_SENSITIVE.csv \
        --yields "$XLSX" --crop Cereal --group --out $D/models/cereal_yield.joblib
"""
import argparse
import glob
import json
import os

import numpy as np
import pandas as pd

from train_species import GROUP, build_features
from train_yield import load_yield


def load(pats, min_clear_frac=0.5):
    files = sorted({f for p in pats for f in glob.glob(p)})
    if not files:
        raise SystemExit(f"no files matched {pats}")
    t = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    t = t.drop_duplicates(["TrialCode", "time"])
    return t[t.n_clear_px / t.n_px_paddock.clip(lower=1) >= min_clear_frac]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indices", nargs="+", required=True)
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--keep", required=True)
    ap.add_argument("--yields", required=True, help="NVT xlsx")
    ap.add_argument("--crop", default="Cereal",
                    help="value of the (grouped, if --group) crop column to train on")
    ap.add_argument("--group", action="store_true",
                    help="map species to the classifier's 3-group label (GROUP in "
                         "train_species.py) before selecting --crop")
    ap.add_argument("--min-obs", type=int, default=10)
    ap.add_argument("--bin-step", type=int, default=None,
                    help="DOY bin width; must match the classifier this model rides "
                         "alongside in predict_tile.py")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--calibration-factor", type=float, default=1.0,
                    help="multiplicative NVT-trial-yield -> ABS-commercial-yield offset. "
                         "NVT single-site yield is a replicated variety trial under trial "
                         "management and consistently reads above the ABS regional average "
                         "(YIELD_FEASIBILITY.md #4). predict_tile.py writes both the raw "
                         "(NVT-equivalent) yield_tha and yield_tha_calibrated = yield_tha * "
                         "this factor, never only the calibrated one. Default 1.0 = no "
                         "calibration applied.")
    ap.add_argument("--calibration-note", default="",
                    help="how --calibration-factor was derived, stored in the bundle for audit")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import joblib
    from sklearn.ensemble import HistGradientBoostingRegressor

    ts = load(args.indices)
    value_cols = [c for c in ts.columns if c.endswith("_pad_median")]
    lab = pd.read_csv(args.labeled).drop_duplicates("TrialCode")
    keep = set(pd.read_csv(args.keep).TrialCode)
    ts = ts[ts.TrialCode.isin(keep)]
    n = ts.groupby("TrialCode").size()
    ts = ts[ts.TrialCode.isin(set(n[n >= args.min_obs].index))]
    print(f"indices: {ts.TrialCode.nunique()} paddocks, {len(value_cols)} value columns")

    F = build_features(ts, value_cols, False, lab, args.bin_step)
    meta = lab.set_index("TrialCode").reindex(F.index)[["crop", "Year", "site", "state"]].copy()
    if args.group:
        meta["species"] = meta["crop"]
        meta["crop"] = meta["crop"].map(GROUP)

    Y = load_yield(args.yields)
    F = F.join(Y[["yield_tha"]])

    sel = (meta.crop == args.crop) & F.yield_tha.notna()
    F, meta = F[sel], meta[sel]
    if len(F) < 60:
        raise SystemExit(f"only {len(F)} usable {args.crop} trials with a yield label — "
                          f"too few to fit")

    feat_cols = [c for c in F.columns if c != "yield_tha"]
    Ffeat = F[feat_cols]
    # Same reasoning as fit_map_model.py: an all-NaN column carries nothing, but it must be
    # DECLARED in `columns` or a tile that does have it would shift the matrix.
    Ffeat = Ffeat.loc[:, Ffeat.notna().any()]
    y = F.yield_tha.values

    reg = HistGradientBoostingRegressor(random_state=args.seed)
    reg.fit(Ffeat.values, y)
    print(f"fitted on {Ffeat.shape[0]} {args.crop} paddocks x {Ffeat.shape[1]} features, "
          f"yield median {np.median(y):.2f} t/ha")
    if "species" in meta.columns:
        print(meta["species"].value_counts().to_string())

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    bundle = {
        "model": reg,
        "columns": list(Ffeat.columns),
        "value_cols": value_cols,
        "kind": "indices",
        "crop": args.crop,
        "n_train": int(Ffeat.shape[0]),
        "train_years": sorted(int(v) for v in meta.Year.dropna().unique()),
        "yield_median": float(np.median(y)),
        "yield_sd": float(np.std(y)),
        "species_counts": ({k: int(v) for k, v in meta["species"].value_counts().items()}
                           if "species" in meta.columns else {}),
        "min_obs": args.min_obs,
        "min_clear_frac": 0.5,
        "bin_step": args.bin_step,
        "seed": args.seed,
        "calibration_factor": args.calibration_factor,
        "calibration_note": args.calibration_note,
    }
    joblib.dump(bundle, args.out)
    side = os.path.splitext(args.out)[0] + ".json"
    with open(side, "w") as fh:
        json.dump({k: v for k, v in bundle.items() if k != "model"}, fh, indent=2)
    print(f"-> {args.out}\n-> {side}")


if __name__ == "__main__":
    main()
