#!/usr/bin/env python3
"""Out-of-fold predictions for the "reviewed" arm's 543 fixed test trials, temporal + spatial,
across several seeds -- for (1) a per-site correct/incorrect gpkg and (2) a seed-stability
check on macro F1 / the confusion matrix.

Reuses train_species.py's exact feature-building code (`build_features`, `GROUP`) via import,
rather than reimplementing it, so the feature matrix here is guaranteed identical to the one
`GROUP3_reviewed.md`'s reported 0.821/0.823 came from -- not a close re-derivation.

Same inputs as `train_group3_reviewed.pbs`'s "reviewed" arm: --indices ts_v2/*_SENSITIVE.csv,
--keep keep_reviewed_SENSITIVE.csv, --test-keep testkeep_temporal_SENSITIVE.csv, target=group3.

    python3 eval_predictions.py --seeds 0 1 2 3 4 \
        --sites-out /scratch/.../keep_arms/eval_predictions_SENSITIVE.csv \
        --stability-out ../../output/EVAL_SEED_STABILITY.md
"""
import argparse
import glob
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train_species import build_features, GROUP  # noqa: E402

D = "/scratch/xe2/cb8590/paddock-species-data/derived"
INDICES_GLOB = f"{D}/samgeo/ts_v2/*_SENSITIVE.csv"
LABELED = f"{D}/nvt_trials_labeled.csv"
KEEP = f"{D}/keep_arms/keep_reviewed_SENSITIVE.csv"
TEST_KEEP = f"{D}/keep_arms/testkeep_temporal_SENSITIVE.csv"


def load(pats):
    files = sorted({f for p in pats for f in glob.glob(p)})
    if not files:
        raise SystemExit(f"no files matched {pats}")
    t = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    t = t.drop_duplicates(["TrialCode", "time"])
    return t[t.n_clear_px / t.n_px_paddock.clip(lower=1) >= 0.5]


def build_matrix():
    ts = load([INDICES_GLOB])
    value_cols = [c for c in ts.columns if c.endswith("_pad_median")]
    lab = pd.read_csv(LABELED).drop_duplicates("TrialCode")
    keep = set(pd.read_csv(KEEP).TrialCode)
    ts = ts[ts.TrialCode.isin(keep)]
    n = ts.groupby("TrialCode").size()
    keep_obs = set(n[n >= 10].index)
    ts = ts[ts.TrialCode.isin(keep) & ts.TrialCode.isin(keep_obs)]
    F = build_features(ts, value_cols, False, lab)
    meta = lab.set_index("TrialCode").loc[F.index, ["crop", "Year", "site", "state"]]
    F = F.loc[:, F.notna().any()]
    X = F.values
    y = meta.crop.map(GROUP).values
    if pd.isna(y).any():
        raise SystemExit(f"unmapped crops: {sorted(set(meta.crop[pd.isna(y)]))}")
    classes = sorted(pd.Series(y).value_counts().index.tolist())
    scorable = meta.index.isin(set(pd.read_csv(TEST_KEEP).TrialCode))
    print(f"feature matrix {X.shape}, {len(classes)} classes, "
          f"{scorable.sum()} scorable (fixed test) rows")
    return F, X, y, meta, classes, scorable


def run_seed(seed, X, y, meta, classes, scorable):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.model_selection import GroupKFold
    from sklearn.metrics import f1_score, balanced_accuracy_score, confusion_matrix, classification_report

    def mk():
        return HistGradientBoostingClassifier(max_iter=400, learning_rate=0.06,
                                              class_weight="balanced", random_state=seed)

    # Temporal
    tr = (meta.Year <= 2022).values
    te = ~tr & scorable
    m = mk()
    m.fit(X[tr], y[tr])
    pred_temporal_all = np.full(len(y), None, dtype=object)
    pred_temporal_all[te] = m.predict(X[te])
    macro_t = f1_score(y[te], pred_temporal_all[te].astype(str), average="macro")
    bal_t = balanced_accuracy_score(y[te], pred_temporal_all[te].astype(str))
    cm_t = confusion_matrix(y[te], pred_temporal_all[te].astype(str), labels=classes)
    rep_t = classification_report(y[te], pred_temporal_all[te].astype(str),
                                   output_dict=True, zero_division=0)

    # Spatial, 5-fold GroupKFold on site (deterministic split; seed only affects the model fit)
    gkf = GroupKFold(n_splits=5)
    groups = meta.site.fillna(meta.index.to_series()).values
    preds_spatial_all = np.empty(len(y), dtype=object)
    for tri, tei in gkf.split(X, y, groups):
        m = mk()
        m.fit(X[tri], y[tri])
        preds_spatial_all[tei] = m.predict(X[tei])
    ys, ps = y[scorable], preds_spatial_all.astype(str)[scorable]
    macro_s = f1_score(ys, ps, average="macro")
    bal_s = balanced_accuracy_score(ys, ps)
    cm_s = confusion_matrix(ys, ps, labels=classes)
    rep_s = classification_report(ys, ps, output_dict=True, zero_division=0)

    return {
        "seed": seed, "classes": classes,
        "macro_f1_temporal": macro_t, "bal_acc_temporal": bal_t,
        "cm_temporal": cm_t, "report_temporal": rep_t,
        "macro_f1_spatial": macro_s, "bal_acc_spatial": bal_s,
        "cm_spatial": cm_s, "report_spatial": rep_s,
        "pred_temporal_scorable": pred_temporal_all[scorable].astype(str),
        "pred_spatial_scorable": preds_spatial_all[scorable].astype(str),
        "trialcodes_scorable": meta.index[scorable].values,
        "true_scorable": y[scorable],
    }


def write_stability_report(all_results, out_path):
    classes = all_results[0]["classes"]
    lines = ["# Seed stability check — reviewed arm, group3 classifier", "",
             "Generated by `eval_predictions.py`. Aggregate only (macro F1, confusion "
             "matrices, per-class precision/recall) — no TrialCodes, matching this "
             "project's standing convention for committable classifier reports.", "",
             "Re-runs the identical \"reviewed\" arm (same features, same 543 fixed test "
             "rows, same `keep_reviewed_SENSITIVE.csv` training set) across several model "
             "seeds. `GroupKFold`'s fold assignment is deterministic (does not depend on "
             "seed) — only the `HistGradientBoostingClassifier`'s own randomness varies.",
             "", "## Macro F1 by seed", "",
             "| seed | temporal macro F1 | spatial macro F1 |", "|---|---|---|"]
    for r in all_results:
        lines.append(f"| {r['seed']} | {r['macro_f1_temporal']:.4f} | {r['macro_f1_spatial']:.4f} |")
    t_vals = [r["macro_f1_temporal"] for r in all_results]
    s_vals = [r["macro_f1_spatial"] for r in all_results]
    lines += ["",
              f"**Temporal**: mean {np.mean(t_vals):.4f}, sd {np.std(t_vals):.4f}, "
              f"range [{min(t_vals):.4f}, {max(t_vals):.4f}]",
              f"**Spatial**: mean {np.mean(s_vals):.4f}, sd {np.std(s_vals):.4f}, "
              f"range [{min(s_vals):.4f}, {max(s_vals):.4f}]",
              "",
              f"Previously reported (seed 0, `GROUP3_reviewed.md`): temporal 0.821, spatial 0.823.",
              ""]

    for split in ("temporal", "spatial"):
        lines.append(f"## Per-class F1 by seed — {split}")
        lines.append("")
        lines.append("| seed | " + " | ".join(classes) + " |")
        lines.append("|---|" + "---|" * len(classes))
        for r in all_results:
            rep = r[f"report_{split}"]
            row = [f"{rep.get(c, {}).get('f1-score', float('nan')):.3f}" for c in classes]
            lines.append(f"| {r['seed']} | " + " | ".join(row) + " |")
        lines.append("")

    for split in ("temporal", "spatial"):
        lines.append(f"## Confusion matrices by seed — {split} (row=truth, col=predicted)")
        lines.append("")
        for r in all_results:
            cm = r[f"cm_{split}"]
            lines.append(f"**seed {r['seed']}**")
            lines.append("")
            lines.append("| |" + "|".join(c[:6] for c in classes) + "|")
            lines.append("|" + "---|" * (len(classes) + 1))
            for i, c in enumerate(classes):
                lines.append(f"| **{c[:9]}** |" + "|".join(str(v) for v in cm[i]) + "|")
            lines.append("")

    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {out_path}")


def write_sites_csv(seed0_result, out_path):
    df = pd.DataFrame({
        "TrialCode": seed0_result["trialcodes_scorable"],
        "group3_true": seed0_result["true_scorable"],
        "pred_temporal": seed0_result["pred_temporal_scorable"],
        "pred_spatial": seed0_result["pred_spatial_scorable"],
    })
    df["correct_temporal"] = df["group3_true"] == df["pred_temporal"]
    df["correct_spatial"] = df["group3_true"] == df["pred_spatial"]
    df.to_csv(out_path, index=False)
    print(f"wrote {out_path} ({len(df)} rows)")
    print(f"temporal accuracy: {df['correct_temporal'].mean():.3f}, "
          f"spatial accuracy: {df['correct_spatial'].mean():.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    ap.add_argument("--sites-out", required=True,
                    help="per-TrialCode true/pred/correct CSV, seed 0 only (SENSITIVE)")
    ap.add_argument("--stability-out", required=True,
                    help="aggregate-only, no-TrialCodes seed-stability report (committable)")
    args = ap.parse_args()

    F, X, y, meta, classes, scorable = build_matrix()

    all_results = []
    for seed in args.seeds:
        print(f"=== seed {seed} ===")
        r = run_seed(seed, X, y, meta, classes, scorable)
        print(f"  temporal macro F1 {r['macro_f1_temporal']:.4f}, "
              f"spatial macro F1 {r['macro_f1_spatial']:.4f}")
        all_results.append(r)

    write_stability_report(all_results, args.stability_out)
    seed0 = next(r for r in all_results if r["seed"] == args.seeds[0])
    write_sites_csv(seed0, args.sites_out)


if __name__ == "__main__":
    main()
