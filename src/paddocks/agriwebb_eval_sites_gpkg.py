#!/usr/bin/env python3
"""Per-site AgriWebb crop-holdout gpkg: true label, group4 (retired) and group3 (current)
predictions, for the colleague discussion. Mirrors the NVT eval_sites gpkg
(`eval_sites_temporal_spatial_SENSITIVE.gpkg`) in structure and handling.

Reuses the group4_map.joblib bundle directly (verified: reproduces HOLDOUT_AGRIWEBB.md's
confusion matrix and 39.4%-called-Grazing figure exactly) and the seed-0 group3 predictions
already written by agriwebb_holdout_group3.py.
"""
import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train_species import build_features  # noqa: E402
from eval_predictions import load  # noqa: E402

D = "/scratch/xe2/cb8590/paddock-species-data/derived"
VAL_SITES = f"{D}/agriwebb/val/agriwebb_val_sites_SENSITIVE.csv"
GROUP3_PREDS = f"{D}/agriwebb/val/agriwebb_group3_predictions_SENSITIVE.csv"
OUT = f"{D}/agriwebb/val/agriwebb_eval_sites_SENSITIVE.gpkg"


def group4_predictions():
    bundle = joblib.load(f"{D}/models/group4_map.joblib")
    model, columns = bundle["model"], bundle["columns"]
    ts = load([f"{D}/agriwebb/ts_idx/r*_ts_SENSITIVE.csv",
               f"{D}/agriwebb/ts_idx/val_*_ts_SENSITIVE.csv"])
    value_cols = [c for c in ts.columns if c.endswith("_pad_median")]
    val = pd.read_csv(VAL_SITES).drop_duplicates("TrialCode")
    n = ts.groupby("TrialCode").size()
    ts = ts[ts.TrialCode.isin(set(n[n >= 10].index))]
    Fx = build_features(ts, value_cols, False, val).reindex(columns=columns)
    y_true = val.set_index("TrialCode").reindex(Fx.index)["crop"]
    ok = y_true.notna()
    Fx = Fx.loc[ok]
    pred = model.predict(Fx.values)
    return pd.DataFrame({"TrialCode": Fx.index, "pred_group4": pred})


def main():
    val = pd.read_csv(VAL_SITES)
    g3 = pd.read_csv(GROUP3_PREDS).rename(columns={"true": "group3_true", "pred_seed0": "pred_group3"})
    g4 = group4_predictions()

    df = val.merge(g3[["TrialCode", "group3_true", "pred_group3"]], on="TrialCode", how="inner")
    df = df.merge(g4, on="TrialCode", how="left")
    assert (df["crop"] == df["group3_true"]).all()

    df["correct_group3"] = df["crop"] == df["pred_group3"]
    df["correct_group4"] = df["crop"] == df["pred_group4"]

    def status(row):
        if row["correct_group3"] and row["correct_group4"]:
            return "correct_both"
        if row["correct_group3"] and not row["correct_group4"]:
            return "fixed_by_group3"
        if not row["correct_group3"] and row["correct_group4"]:
            return "broken_by_group3"
        return "wrong_both"
    df["status"] = df.apply(status, axis=1)
    df["was_called_grazing"] = df["pred_group4"] == "Grazing"

    print(df["status"].value_counts())
    print("of those, called Grazing under group4:",
          df.loc[df["status"] == "fixed_by_group3", "was_called_grazing"].sum(),
          "of", (df["status"] == "fixed_by_group3").sum())

    gdf = gpd.GeoDataFrame(
        df.drop(columns=["group3_true"]),
        geometry=[Point(xy) for xy in zip(df["lon"], df["lat"])], crs="EPSG:4326"
    ).to_crs("EPSG:3577").drop(columns=["lon", "lat"])

    gdf.to_file(OUT, driver="GPKG", layer="agriwebb_eval_sites_104")
    print(f"wrote {OUT} ({len(gdf)} sites)")


if __name__ == "__main__":
    main()
