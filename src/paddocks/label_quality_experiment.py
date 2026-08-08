#!/usr/bin/env python3
"""
Does the co-located-trial label problem explain the species model's failure, and does the
3-group collapse fix it?

THE PROBLEM, measured before this script was written. NVT sites run several crop trials side
by side in one field. SAM segments that field as ONE polygon, so every trial at the site gets
an IDENTICAL paddock-median time series while carrying a DIFFERENT crop label:
  * 31.8 % of the 2,477 training trials sit on a polygon shared, in the same year, with a
    trial of a different crop. 381 trials share EXACT coordinates with a different-crop trial.
  * Per crop, the share of trials within 200 m of a different-crop trial tracks that crop's F1
    at spearman -0.854 (p=0.003) — canola is the least co-located (24 %) and the best scoring
    (0.81); lentil is the most co-located (89 %) and the worst (0.07).
This is not noise. Identical features with contradictory labels put a hard ceiling on
accuracy, and it is concentrated exactly where the model fails.

WHY THE 3-GROUP COLLAPSE IS MORE THAN A CONVENIENCE. Trials co-located at a site are usually
the same agronomic group — pulse variety trials sit together, cereal trials sit together — so
collapsing to Canola / Cereal / Legume RESOLVES 540 of the 788 conflicts (69 %) rather than
merely hiding them. Only 59 polygon-groups remain genuinely cross-group.

DESIGN. Every arm is scored on the SAME test rows, and that test set is restricted to CLEAN
trials, because a dirty test label is not a yardstick — scoring against labels we already know
are contradictory would measure agreement with the corruption. So the training set varies and
the evaluation does not.

Nine-class and three-class scores are NOT comparable to each other (chance is 0.111 vs 0.333),
so the 9-class arms are ALSO scored with their predictions collapsed to 3 groups. That puts
both on the identical task and makes "is 3 classes better?" a paired question rather than a
comparison of two different scales.

Aggregate output only — no TrialCodes — so the report is committable.
"""
import argparse
import glob
import hashlib
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train_species import BANDS, build_features  # noqa: E402

GROUP = {"Canola": "Canola", "Wheat": "Cereal", "Barley": "Cereal", "Oat": "Cereal",
         "Chickpea": "Legume", "Faba Bean": "Legume", "Field Pea": "Legume",
         "Lentil": "Legume", "Lupin": "Legume"}
CLEAN_M = 200.0          # a different-crop trial nearer than this is inside the same paddock
BOOT = 2000


def macro_f1(y, pred, classes):
    from sklearn.metrics import f1_score
    return f1_score(y, pred, average="macro", labels=classes, zero_division=0)


def ci(v, lo=2.5, hi=97.5):
    v = np.asarray(v, float)
    v = v[~np.isnan(v)]
    return (float(np.percentile(v, lo)), float(np.percentile(v, hi))) if len(v) else (np.nan,)*2


def fmt(p, lohi, signed=False):
    s = "{:+.3f}" if signed else "{:.3f}"
    return f"**{s.format(p)}** [{s.format(lohi[0])}, {s.format(lohi[1])}]"


def load(pats):
    files = sorted({f for p in pats for f in glob.glob(p)})
    if not files:
        raise SystemExit(f"no files matched {pats}")
    t = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    t = t.drop_duplicates(["TrialCode", "time"])
    return t[t.n_clear_px / t.n_px_paddock.clip(lower=1) >= 0.5]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indices", nargs="*", required=True)
    ap.add_argument("--bands", nargs="*", default=[])
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--keep", required=True)
    ap.add_argument("--chosen-gpkg", required=True,
                    help="cfi_heatmap_ALL gpkg, for the polygon actually assigned to each trial")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-obs", type=int, default=10)
    ap.add_argument("--max-iter", type=int, default=400)
    ap.add_argument("--boot", type=int, default=BOOT)
    args = ap.parse_args()

    import geopandas as gpd
    from sklearn.ensemble import HistGradientBoostingClassifier

    lab = pd.read_csv(args.labeled).drop_duplicates("TrialCode")
    keep = set(pd.read_csv(args.keep).TrialCode)

    ti = load(args.indices)
    idx_cols = [c for c in ti.columns if c.endswith("_pad_median")]
    t = ti[ti.TrialCode.isin(keep)]
    n = t.groupby("TrialCode").size()
    t = t[t.TrialCode.isin(set(n[n >= args.min_obs].index))]
    F = build_features(t, idx_cols, False, lab)
    F = F.loc[:, F.notna().any()]
    common = F.index.intersection(lab.set_index("TrialCode").index)
    F = F.loc[common]
    meta = lab.set_index("TrialCode").loc[common,
                                          ["crop", "Year", "site", "nearest_diffcrop_same_year_m"]]

    # Which trials actually landed on a polygon shared with a conflicting crop label.
    G = gpd.read_file(args.chosen_gpkg, layer="paddocks").drop_duplicates(subset=["TrialCode"])
    G["gkey"] = [hashlib.md5(w).hexdigest() for w in G.geometry.to_wkb()]
    G["ykey"] = G.gkey + "_" + G.Year.astype(str)
    g = G.groupby("ykey")
    G["n_share"] = g.TrialCode.transform("size")
    G["n_crop"] = g.crop.transform("nunique")
    conf = set(G[(G.n_share > 1) & (G.n_crop > 1)].TrialCode)

    meta["conflict"] = meta.index.isin(conf)
    meta["colocated"] = meta.nearest_diffcrop_same_year_m < CLEAN_M
    y9 = meta.crop.values
    y3 = pd.Series(y9, index=meta.index).map(GROUP).values
    X = F.values
    cls9 = sorted(set(y9))
    cls3 = ["Canola", "Cereal", "Legume"]

    tr_mask = (meta.Year <= 2022).values
    # Test on CLEAN rows only: a contradictory label is not a yardstick.
    te_mask = (~tr_mask) & (~meta.colocated.values) & (~meta.conflict.values)
    print(f"n={len(meta)}  train pool={int(tr_mask.sum())}  clean test={int(te_mask.sum())}")
    print(f"  conflict {meta.conflict.mean():.1%}  colocated {meta.colocated.mean():.1%}")

    def mk():
        return HistGradientBoostingClassifier(max_iter=args.max_iter, learning_rate=0.06,
                                              class_weight="balanced", random_state=0)

    rng = np.random.default_rng(0)
    pool = np.where(tr_mask)[0]
    arms = {
        "all": pool,
        "drop conflicting": pool[~meta.conflict.values[pool]],
        "drop co-located": pool[~meta.colocated.values[pool]],
    }
    # Size-matched random control: the filters remove data as well as noise, and without this
    # any gain could just be a smaller-training-set effect pointing the other way.
    nmin = min(len(v) for v in arms.values())
    arms["random subsample (control)"] = rng.choice(pool, nmin, replace=False)
    for k, v in arms.items():
        print(f"  arm {k:28s} n_train={len(v)}")

    te = np.where(te_mask)[0]
    yte9, yte3 = y9[te], y3[te]
    preds = {}
    for name, idx in arms.items():
        for task, yy, cc in [("9class", y9, cls9), ("3class", y3, cls3)]:
            m = mk()
            m.fit(X[idx], yy[idx])
            p = m.predict(X[te])
            preds[(name, task)] = p
            print(f"  {name:28s} {task}: macroF1 "
                  f"{macro_f1(yte9 if task=='9class' else yte3, p, cc):.3f}", flush=True)

    # 9-class predictions collapsed to 3 groups, so both tasks are scored identically.
    for name in arms:
        preds[(name, "9->3")] = pd.Series(preds[(name, "9class")]).map(GROUP).values

    draws = [rng.integers(0, len(te), len(te)) for _ in range(args.boot)]
    def boot(name, task):
        yy = yte9 if task == "9class" else yte3
        cc = cls9 if task == "9class" else cls3
        return [macro_f1(yy[i], preds[(name, task)][i], cc) for i in draws]

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        f.write("# Do co-located trial labels explain the species model's failure?\n\n")
        f.write(f"Every arm is trained on a different subset of the SAME pre-2023 pool and "
                f"scored on the SAME {len(te)} clean 2023-24 trials "
                f"(co-location >= {CLEAN_M:.0f} m AND not on a conflicting shared polygon), "
                f"so only the training data varies. {args.boot} bootstrap resamples of the "
                f"test set, paired across arms.\n\n")
        f.write(f"Training pool {int(tr_mask.sum())}; of the full {len(meta)} kept trials, "
                f"**{meta.conflict.mean():.1%} sit on a polygon shared with a different-crop "
                f"trial in the same year** and {meta.colocated.mean():.1%} lie within "
                f"{CLEAN_M:.0f} m of a different-crop trial.\n\n")

        f.write("## 1. Nine classes\n\n| training set | n | macro F1 (9 class) |\n|---|---|---|\n")
        b0 = boot("all", "9class")
        for name, idx in arms.items():
            b = boot(name, "9class")
            f.write(f"| {name} | {len(idx)} | "
                    f"{fmt(macro_f1(yte9, preds[(name,'9class')], cls9), ci(b))} |\n")
        f.write("\n| vs `all` | paired difference | verdict |\n|---|---|---|\n")
        for name in arms:
            if name == "all":
                continue
            d = np.asarray(boot(name, "9class")) - np.asarray(b0)
            lo, hi = ci(d)
            f.write(f"| {name} | {fmt(float(np.mean(d)), (lo, hi), signed=True)} | "
                    f"{'real' if (lo > 0 or hi < 0) else 'indistinguishable'} |\n")

        f.write("\n## 2. Three groups — Canola / Cereal / Legume\n\n")
        f.write("`9->3` collapses a nine-class model's predictions; `3class` trains on the "
                "three groups directly. Both are scored on the identical three-group task, so "
                "the comparison is paired and fair.\n\n")
        f.write("| training set | n | 9->3 collapsed | 3-class native |\n|---|---|---|---|\n")
        for name, idx in arms.items():
            f.write(f"| {name} | {len(idx)} | "
                    f"{fmt(macro_f1(yte3, preds[(name,'9->3')], cls3), ci(boot(name,'9->3')))} | "
                    f"{fmt(macro_f1(yte3, preds[(name,'3class')], cls3), ci(boot(name,'3class')))} |\n")
        f.write("\n| training set | native 3-class - collapsed 9-class | verdict |\n|---|---|---|\n")
        for name in arms:
            d = np.asarray(boot(name, "3class")) - np.asarray(boot(name, "9->3"))
            lo, hi = ci(d)
            f.write(f"| {name} | {fmt(float(np.mean(d)), (lo, hi), signed=True)} | "
                    f"{'real' if (lo > 0 or hi < 0) else 'indistinguishable'} |\n")

        # The comparison the control was BUILT for: cleaned vs random at IDENTICAL training
        # size. Against `all` the cleaned arms are confounded with having less data; against
        # the control they are not, and this is the only pair that isolates the cleaning.
        f.write("\n### Cleaning vs a random subsample of the same size\n\n")
        f.write("`drop co-located` and `random subsample` both train on "
                f"{len(arms['drop co-located'])} rows, so this pair isolates the effect of "
                "WHICH rows were removed from the effect of how many.\n\n")
        f.write("| task | drop co-located - random subsample | verdict |\n|---|---|---|\n")
        for task in ("9class", "9->3", "3class"):
            d = (np.asarray(boot("drop co-located", task))
                 - np.asarray(boot("random subsample (control)", task)))
            lo, hi = ci(d)
            f.write(f"| {task} | {fmt(float(np.mean(d)), (lo, hi), signed=True)} | "
                    f"{'real' if (lo > 0 or hi < 0) else 'indistinguishable'} |\n")

        f.write("\n## 3. Per-class, on the clean test set\n\n")
        from sklearn.metrics import f1_score
        for task, yy, cc in [("9class", yte9, cls9), ("3class", yte3, cls3)]:
            f.write(f"\n### {task}\n\n| class | n | " + " | ".join(arms) + " |\n")
            f.write("|---|---|" + "---|" * len(arms) + "\n")
            for c in cc:
                row = f"| {c} | {int((yy == c).sum())} "
                for name in arms:
                    v = f1_score(yy, preds[(name, task)], labels=[c], average="macro",
                                 zero_division=0)
                    row += f"| {v:.2f} "
                f.write(row + "|\n")

    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
