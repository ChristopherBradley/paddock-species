#!/usr/bin/env python3
"""
Fit the classifier that a map run will actually use, and save it with everything needed to
reproduce its input.

WHY THIS IS NOT `train_species.py`. That script exists to VALIDATE — it holds years and sites
out, and every number it reports is from a model that was deliberately denied part of the data.
A map wants the opposite: every usable row, because the paddock being predicted is not in the
training set anyway and withholding 2023-24 only makes the map worse. Keeping the two apart
means no reported score ever comes from a model that saw its own test set.

WHAT IS SAVED, AND WHY THE COLUMN LIST MATTERS MOST. A boosted tree takes an unnamed array, so
a feature matrix built at prediction time with a different column ORDER produces confident
nonsense rather than an error. The pickle therefore carries `columns` and `predict_tile.py`
reindexes onto it, which also turns a DOY bin that happened to be empty over a tile into NaN —
the value the booster is built to handle — instead of silently shifting every column by one.

    python3 fit_map_model.py --indices "$D/samgeo/ts_v2/*_SENSITIVE.csv" \
        "$D/agriwebb/ts_idx/neg_*_SENSITIVE.csv" \
        --labeled $D/labels_combined_SENSITIVE.csv --keep $D/keep_group4_SENSITIVE.csv \
        --target group4 --out $D/models/group4.joblib
"""
import argparse
import glob
import json
import os

import numpy as np
import pandas as pd

from train_species import GROUP, GROUP4, build_features


def load(pats, min_clear_frac=0.5):
    files = sorted({f for p in pats for f in glob.glob(p)})
    if not files:
        raise SystemExit(f"no files matched {pats}")
    t = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    t = t.drop_duplicates(["TrialCode", "time"])
    return t[t.n_clear_px / t.n_px_paddock.clip(lower=1) >= min_clear_frac]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indices", nargs="*", default=[])
    ap.add_argument("--bands", nargs="*", default=[])
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--keep", required=True)
    ap.add_argument("--target", choices=["group3", "group4", "canola", "crop2"],
                    default="group4")
    ap.add_argument("--min-obs", type=int, default=10)
    ap.add_argument("--bin-step", type=int, default=None,
                    help="DOY bin width; must match the arm this model came from. "
                         "Stored in the bundle so prediction cannot silently use "
                         "a different one.")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import joblib
    from sklearn.ensemble import HistGradientBoostingClassifier

    if args.bands:
        ts = load(args.bands)
        value_cols = [b for b in ["blue", "green", "red", "red_edge_1", "red_edge_2",
                                  "red_edge_3", "nir_1", "nir_2", "swir_2", "swir_3"]
                      if b in ts.columns]
        kind = "bands"
    else:
        ts = load(args.indices)
        value_cols = [c for c in ts.columns if c.endswith("_pad_median")]
        kind = "indices"
    lab = pd.read_csv(args.labeled).drop_duplicates("TrialCode")
    keep = set(pd.read_csv(args.keep).TrialCode)
    ts = ts[ts.TrialCode.isin(keep)]
    n = ts.groupby("TrialCode").size()
    ts = ts[ts.TrialCode.isin(set(n[n >= args.min_obs].index))]
    print(f"{kind}: {ts.TrialCode.nunique()} paddocks, {len(value_cols)} value columns")

    F = build_features(ts, value_cols, False, lab, args.bin_step)
    meta = lab.set_index("TrialCode").reindex(F.index)
    F = F.loc[meta.crop.notna()]
    meta = meta.loc[F.index]

    if args.target == "group4":
        y = meta.crop.map(GROUP4).values
    elif args.target == "group3":
        y = meta.crop.map(GROUP).values
    elif args.target == "crop2":
        y = np.where(meta.crop.values == "Grazing", "Grazing", "Crop")
    else:
        y = np.where(meta.crop.values == "Canola", "Canola", "Other")
    ok = pd.notna(y)
    if not ok.all():
        print(f"dropping {int((~ok).sum())} rows with an unmapped crop: "
              f"{sorted(set(meta.crop[~ok]))}")
        F, y, meta = F[ok], y[ok], meta[ok]

    # A feature that is NaN for every training row carries nothing, but it must still be
    # DECLARED in `columns` or a tile that does have it would shift the matrix. So drop it
    # here and record the surviving list as the contract.
    F = F.loc[:, F.notna().any()]
    clf = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.06,
                                         class_weight="balanced", random_state=args.seed)
    clf.fit(F.values, y)
    print(f"fitted on {F.shape[0]} paddocks x {F.shape[1]} features, "
          f"classes {list(clf.classes_)}")
    print(pd.Series(y).value_counts().to_string())

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    bundle = {
        "model": clf,
        "columns": list(F.columns),
        "value_cols": value_cols,
        "kind": kind,
        "target": args.target,
        "classes": list(clf.classes_),
        "n_train": int(F.shape[0]),
        "train_years": sorted(int(v) for v in meta.Year.dropna().unique()),
        "class_counts": {k: int(v) for k, v in pd.Series(y).value_counts().items()},
        "label_sources": ({k: int(v) for k, v in meta.label_src.value_counts().items()}
                          if "label_src" in meta.columns else {}),
        "min_obs": args.min_obs,
        "min_clear_frac": 0.5,
        "bin_step": args.bin_step,
        "seed": args.seed,
    }
    joblib.dump(bundle, args.out)
    side = os.path.splitext(args.out)[0] + ".json"
    with open(side, "w") as fh:
        json.dump({k: v for k, v in bundle.items() if k != "model"}, fh, indent=2)
    print(f"-> {args.out}\n-> {side}")


if __name__ == "__main__":
    main()
