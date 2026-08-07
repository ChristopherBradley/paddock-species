#!/usr/bin/env python3
"""
Species classifier from paddock-median Sentinel-2 time series — the baseline that says
whether a 10 m species map is reachable, and with what.

Runs on either input, so the pipeline can be tested before the bands land:
  * `--bands`   10-band paddock medians (`extract_paddock.py --all-bands`)
  * `--indices` the 3-index files, as the CFI-only reference point

FEATURES. Each trial becomes a fixed-length vector: every band binned onto calendar
day-of-year, plus indices derived from those binned bands, plus whole-season summaries.
Calendar DOY and not days-after-sowing, because measured on this dataset flowering aligns
tighter on the calendar (IQR 26 d vs 30 d). Gaps stay NaN and are handled natively by the
histogram booster rather than imputed, so a cloudy fortnight is not silently invented.

VALIDATION is the point of this script, not the accuracy number. Two splits, because a
related Australian study found spatial and temporal transfer behave very differently and this
project committed to testing both:
  * temporal — train on early seasons, predict later ones (the "will it work next year" test)
  * spatial  — GroupKFold on SITE, so no location is in both train and test (the "will it work
    over the fence" test). Grouping on site is essential: the same paddock recurs across years
    and a random split would let the model memorise locations and report a fantasy score.

Geography (lat/lon/year) is EXCLUDED by default and reported separately under `--with-geo`.
Chickpea is effectively a Queensland crop, so a model given coordinates can score well while
learning where crops are grown rather than what they look like. Both numbers are useful; only
one of them is evidence about the imagery.

Aggregate output only — no TrialCodes — so the report is committable.
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd

BIN_START, BIN_END, BIN_STEP = 90, 350, 20
BANDS = ["blue", "green", "red", "red_edge_1", "red_edge_2", "red_edge_3",
         "nir_1", "nir_2", "swir_2", "swir_3"]


def family(col):
    """Feature -> its band/index family, for summing importance.

    Splitting on the first underscore would merge `red_edge_1_290` into `red`, which is the
    one grouping that matters here: whether the red-edge bands (unavailable to the 3-index
    baseline) carry signal is the question this table exists to answer.
    """
    base = col.split("__")[0]                       # season summaries: `nir_1__amp`
    parts = base.rsplit("_", 1)
    return parts[0] if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 3 else base


def safe_ratio(a, b):
    d = a + b
    return np.where(np.abs(d) < 1e-6, np.nan, (a - b) / np.where(np.abs(d) < 1e-6, 1, d))


def add_indices(F, bins):
    """Normalised-difference indices per DOY bin, from the binned band medians.

    Derived here rather than at extraction so a new index costs a re-run of this script and
    not 38 CPU-hours of datacube reads — the mistake Stage 2 made when it stored indices but
    not the bands behind them.
    """
    for b in bins:
        def g(name):
            return F.get(f"{name}_{b}", pd.Series(np.nan, index=F.index)).values
        red, green, blue = g("red"), g("green"), g("blue")
        nir, re1, re3 = g("nir_1"), g("red_edge_1"), g("red_edge_3")
        sw2, sw3 = g("swir_2"), g("swir_3")
        F[f"ndvi_{b}"] = safe_ratio(nir, red)
        F[f"ndyi_{b}"] = safe_ratio(green, blue)
        # CFI (Tian et al. 2022), the canola flowering index this project already validated
        F[f"cfi_{b}"] = safe_ratio(nir, red) * ((red + green) + (green - blue))
        F[f"ndre_{b}"] = safe_ratio(nir, re1)        # chlorophyll / N status
        F[f"ndwi_{b}"] = safe_ratio(green, nir)      # canopy water
        F[f"nbr_{b}"] = safe_ratio(nir, sw3)         # senescence / residue
        F[f"psri_{b}"] = np.where(np.abs(re3) < 1e-6, np.nan, (red - blue) / re3)
        F[f"swir_ratio_{b}"] = np.where(np.abs(sw3) < 1e-6, np.nan, sw2 / sw3)
    return F


def build_features(ts, value_cols, with_geo, lab):
    ts = ts.copy()
    ts["doy"] = pd.to_datetime(ts.time).dt.dayofyear
    edges = np.arange(BIN_START, BIN_END + BIN_STEP, BIN_STEP)
    ts["bin"] = pd.cut(ts.doy, edges, labels=[str(e) for e in edges[:-1]], right=False)
    ts = ts.dropna(subset=["bin"])

    piv = ts.pivot_table(index="TrialCode", columns="bin", values=value_cols,
                         aggfunc="median", observed=True)
    piv.columns = [f"{a}_{b}" for a, b in piv.columns]
    F = piv

    bins = [str(e) for e in edges[:-1]]
    if set(BANDS).issubset(value_cols):
        F = add_indices(F, bins)

    # Whole-season shape, which the bins alone lose: how high it got, how much it moved, and
    # WHEN it peaked. Peak timing is the single most discriminating thing about canola.
    for c in value_cols:
        cols = [f"{c}_{b}" for b in bins if f"{c}_{b}" in F.columns]
        if not cols:
            continue
        A = F[cols].values
        F[f"{c}__p10"] = np.nanpercentile(A, 10, axis=1)
        F[f"{c}__p90"] = np.nanpercentile(A, 90, axis=1)
        F[f"{c}__amp"] = F[f"{c}__p90"] - F[f"{c}__p10"]
        with np.errstate(invalid="ignore"):
            idx = np.where(np.isnan(A).all(axis=1), np.nan, np.nanargmax(
                np.where(np.isnan(A), -np.inf, A), axis=1))
        F[f"{c}__peak_doy"] = [np.nan if np.isnan(i) else int(bins[int(i)]) for i in idx]

    if with_geo:
        g = lab.set_index("TrialCode")[["lat", "lon", "Year"]]
        F = F.join(g)
    return F


def evaluate(name, Xtr, ytr, Xte, yte, model, classes, f):
    from sklearn.metrics import (balanced_accuracy_score, classification_report,
                                 confusion_matrix, f1_score)
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    proba = model.predict_proba(Xte)
    macro = f1_score(yte, pred, average="macro")
    bal = balanced_accuracy_score(yte, pred)
    f.write(f"\n### {name}\n\n")
    f.write(f"- train {len(ytr)}, test {len(yte)}\n")
    f.write(f"- **macro F1 {macro:.3f}, balanced accuracy {bal:.3f}** "
            f"(chance {1/len(classes):.3f})\n\n")

    # Canola at a 5 % false-positive budget: the operating point Stage 2 actually needs, and
    # the number directly comparable with the CFI-threshold result.
    if "Canola" in list(model.classes_):
        ci = list(model.classes_).index("Canola")
        p = proba[:, ci]
        pos, neg = p[yte == "Canola"], p[yte != "Canola"]
        if len(pos) > 4 and len(neg) > 4:
            t = np.quantile(neg, 0.95)
            f.write(f"- **canola detected at 5 % FPR: {(pos > t).mean():.1%}** "
                    f"(n={len(pos)})\n\n")

    rep = classification_report(yte, pred, output_dict=True, zero_division=0)
    f.write("| crop | precision | recall | F1 | n |\n|---|---|---|---|---|\n")
    for c in classes:
        if c in rep:
            r = rep[c]
            f.write(f"| {c} | {r['precision']:.2f} | {r['recall']:.2f} | "
                    f"{r['f1-score']:.2f} | {int(r['support'])} |\n")
    cm = confusion_matrix(yte, pred, labels=classes)
    f.write("\nConfusion (row = truth, col = predicted):\n\n| |" +
            "|".join(c[:6] for c in classes) + "|\n|" + "---|" * (len(classes) + 1) + "\n")
    for i, c in enumerate(classes):
        f.write(f"| **{c[:9]}** |" + "|".join(str(v) for v in cm[i]) + "|\n")
    return {"split": name, "macro_f1": macro, "bal_acc": bal}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bands", nargs="*", default=[], help="glob(s) of 10-band time series")
    ap.add_argument("--indices", nargs="*", default=[], help="glob(s) of 3-index time series")
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--keep", help="cfi_heatmap_ALL_rows csv: restrict to quality-filtered "
                                   "trials (strongly recommended)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--with-geo", action="store_true")
    ap.add_argument("--min-obs", type=int, default=10)
    ap.add_argument("--model", choices=["hgb", "rf"], default="hgb")
    ap.add_argument("--select-k", type=int, default=0,
                    help="keep only the K best features (ANOVA F), selected INSIDE each "
                         "training fold. Use to test whether a richer feature set loses to a "
                         "smaller one because of capacity rather than information content.")
    args = ap.parse_args()

    from sklearn.ensemble import (HistGradientBoostingClassifier,
                                  RandomForestClassifier)
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.impute import SimpleImputer

    def load(pats):
        files = sorted({f for p in pats for f in glob.glob(p)})
        if not files:
            raise SystemExit(f"no files matched {pats}")
        t = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
        t = t.drop_duplicates(["TrialCode", "time"])
        return t[t.n_clear_px / t.n_px_paddock.clip(lower=1) >= 0.5]

    sources = []
    if args.bands:
        tb = load(args.bands)
        sources.append(("bands", tb, [b for b in BANDS if b in tb.columns]))
    if args.indices:
        ti = load(args.indices)
        sources.append(("indices", ti,
                        [c for c in ti.columns if c.endswith("_pad_median")]))
    if not sources:
        raise SystemExit("give --bands and/or --indices")
    for name, t, cols in sources:
        print(f"{name}: {t.TrialCode.nunique()} trials, {len(cols)} value columns")
    ts = sources[0][1]
    value_cols = sources[0][2]

    lab = pd.read_csv(args.labeled).drop_duplicates("TrialCode")
    if args.keep:
        keep = set(pd.read_csv(args.keep).TrialCode)
        ts = ts[ts.TrialCode.isin(keep)]
        print(f"quality filter: {ts.TrialCode.nunique()} trials kept")

    n = ts.groupby("TrialCode").size()
    keep_obs = set(n[n >= args.min_obs].index)

    # Bands and indices are NOT interchangeable inputs, and combining them is not redundant.
    # CFI is non-linear in reflectance, so the median of per-pixel CFI (what the index files
    # hold) is not CFI computed from the median reflectance (what a band file can reconstruct).
    # The index files therefore carry a signal the band files cannot express, which is the
    # most likely reason a 10-band model scored WORSE on canola than a 3-index one.
    parts = []
    for name, t, cols in sources:
        if args.keep:
            t = t[t.TrialCode.isin(keep)]
        t = t[t.TrialCode.isin(keep_obs)]
        f = build_features(t, cols, False, lab)
        if len(sources) > 1:
            f = f.add_suffix(f"@{name}")
        parts.append(f)
    F = parts[0] if len(parts) == 1 else parts[0].join(parts[1:], how="inner")
    if args.with_geo:
        F = F.join(lab.set_index("TrialCode")[["lat", "lon", "Year"]])
    meta = lab.set_index("TrialCode").loc[F.index, ["crop", "Year", "site", "state"]]
    # A feature that is NaN for every trial carries nothing and only slows the fit.
    F = F.loc[:, F.notna().any()]
    X, y = F.values, meta.crop.values
    classes = sorted(pd.Series(y).value_counts().index.tolist())
    print(f"feature matrix {X.shape}, {len(classes)} classes")

    def mk():
        if args.model == "rf":
            clf = RandomForestClassifier(n_estimators=500, min_samples_leaf=2,
                                         class_weight="balanced_subsample",
                                         n_jobs=-1, random_state=0)
        else:
            clf = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.06,
                                                 class_weight="balanced", random_state=0)
        if args.select_k:
            from sklearn.feature_selection import SelectKBest, f_classif
            # Selection sits INSIDE the pipeline so it is refit on each training fold only.
            # Choosing features once on the full matrix would leak the test set into the
            # choice and inflate every score that follows.
            # Note this also forces imputation, costing the booster its native NaN handling —
            # so compare --select-k runs only against other --select-k runs.
            return make_pipeline(SimpleImputer(strategy="median"),
                                 SelectKBest(f_classif, k=min(args.select_k, X.shape[1])), clf)
        if args.model == "rf":
            return make_pipeline(SimpleImputer(strategy="median"), clf)
        return clf

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    results = []
    with open(args.out, "w") as f:
        f.write("# Species classifier baseline — paddock-median Sentinel-2\n\n")
        f.write(f"- input: **{'10 bands' if args.bands else '3 indices'}** "
                f"({len(value_cols)} columns), {X.shape[0]} paddocks, "
                f"{X.shape[1]} features, {len(classes)} classes\n")
        f.write(f"- model: {'random forest' if args.model=='rf' else 'hist gradient boosting'}"
                f", class-balanced; geography "
                f"{'INCLUDED' if args.with_geo else 'excluded'}\n")
        f.write(f"- class counts: " +
                ", ".join(f"{c} {int((y==c).sum())}" for c in classes) + "\n")

        # Temporal transfer
        tr = meta.Year <= 2022
        results.append(evaluate(f"Temporal transfer — train <=2022, test 2023-24",
                                X[tr.values], y[tr.values], X[~tr.values], y[~tr.values],
                                mk(), classes, f))

        # Spatial transfer, grouped on site
        gkf = GroupKFold(n_splits=5)
        groups = meta.site.fillna(meta.index.to_series()).values
        preds = np.empty(len(y), dtype=object)
        for tri, tei in gkf.split(X, y, groups):
            m = mk()
            m.fit(X[tri], y[tri])
            preds[tei] = m.predict(X[tei])
        from sklearn.metrics import (balanced_accuracy_score, classification_report,
                                     confusion_matrix, f1_score)
        macro = f1_score(y, preds.astype(str), average="macro")
        bal = balanced_accuracy_score(y, preds.astype(str))
        f.write("\n### Spatial transfer — 5-fold GroupKFold on site\n\n")
        f.write(f"- **macro F1 {macro:.3f}, balanced accuracy {bal:.3f}**\n\n")
        rep = classification_report(y, preds.astype(str), output_dict=True, zero_division=0)
        f.write("| crop | precision | recall | F1 | n |\n|---|---|---|---|---|\n")
        for c in classes:
            if c in rep:
                r = rep[c]
                f.write(f"| {c} | {r['precision']:.2f} | {r['recall']:.2f} | "
                        f"{r['f1-score']:.2f} | {int(r['support'])} |\n")
        cm = confusion_matrix(y, preds.astype(str), labels=classes)
        f.write("\nConfusion (row = truth, col = predicted):\n\n| |" +
                "|".join(c[:6] for c in classes) + "|\n|" + "---|" * (len(classes) + 1) + "\n")
        for i, c in enumerate(classes):
            f.write(f"| **{c[:9]}** |" + "|".join(str(v) for v in cm[i]) + "|\n")
        results.append({"split": "spatial (GroupKFold on site)",
                        "macro_f1": macro, "bal_acc": bal})

        # Which bands and which times carry the signal — the question that decides whether
        # more bands were worth extracting.
        #
        # Measured OUT OF SAMPLE, on the temporal test set with a model that never saw it.
        # An in-sample permutation on a boosted model returns mostly negative importances
        # (shuffling a feature it overfit can raise accuracy), which is not a weak signal but
        # a broken measurement — the first version of this did exactly that.
        try:
            from sklearn.inspection import permutation_importance
            m = mk()
            m.fit(X[tr.values], y[tr.values])
            imp = permutation_importance(m, X[~tr.values], y[~tr.values], n_repeats=10,
                                         scoring="f1_macro", random_state=0,
                                         n_jobs=-1).importances_mean
            I = pd.Series(imp, index=F.columns)
            fam = I.groupby(I.index.map(family)).sum().sort_values(ascending=False)
            f.write("\n### Where the signal is\n\n")
            f.write("Permutation importance on the 2023-24 holdout, macro-F1 scoring, "
                    "summed within each family. Negative means the feature was not used "
                    "and shuffling it happened to help.\n\n")
            f.write("| feature family | importance |\n|---|---|\n")
            for k, v in fam.head(16).items():
                f.write(f"| `{k}` | {v:+.4f} |\n")
            f.write("\nTop individual features: " +
                    ", ".join(f"`{i}`" for i in I.sort_values(ascending=False).head(12).index)
                    + "\n")
        except Exception as e:                       # importance is a bonus, not the result
            f.write(f"\n(importance skipped: {e})\n")

        f.write("\n### Summary\n\n| split | macro F1 | balanced accuracy |\n|---|---|---|\n")
        for r in results:
            f.write(f"| {r['split']} | {r['macro_f1']:.3f} | {r['bal_acc']:.3f} |\n")

    for r in results:
        print(f"{r['split']:55s} macroF1 {r['macro_f1']:.3f}  balAcc {r['bal_acc']:.3f}")
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
