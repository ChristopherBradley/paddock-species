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

# The default target is the THREE-GROUP split, on the user's instruction (2026-08-08): these
# are the distinctions they actually need, and separating wheat from barley from oat was never
# working (F1 0.22, 0.00). It is also the better-posed problem, not merely the easier one —
# co-located trials at an NVT site are usually of the same agronomic group, so collapsing
# resolves 540 of the 788 same-polygon label conflicts (69 %) rather than hiding them.
# Measured: macro F1 0.78-0.82 on groups against 0.38 on species.
GROUP = {"Canola": "Canola", "Wheat": "Cereal", "Barley": "Cereal", "Oat": "Cereal",
         "Chickpea": "Legume", "Faba Bean": "Legume", "Field Pea": "Legume",
         "Lentil": "Legume", "Lupin": "Legume"}

# The fourth class, added 2026-08-24. `NONCROP_CLASS.md` measured what a three-way softmax does
# with a paddock that is none of its classes — 100 % of 125 pasture paddocks called a crop, 79 %
# Cereal, at a median confidence of 0.999 — and showed that thresholding the softmax cannot fix
# it, because every threshold that rejects pasture discards as much real crop. The only remedy
# left was a real negative class with real labels, which AgriWebb's dated, farmer-entered
# grazing records now supply. `Grazing` is deliberately its own label rather than a catch-all
# "NotCrop": the training negatives are grazed pasture specifically, and calling the class what
# the evidence actually says stops a fallow, a vineyard or a plantation being read as covered
# by it. See `GRAZING_CLASS.md`.
GROUP4 = dict(GROUP, Grazing="Grazing")


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


def build_features(ts, value_cols, with_geo, lab, bin_step=None):
    """`bin_step` in days; None keeps the module default.

    The default of 20 days is a compromise nobody has yet tested: Sentinel-2's revisit is 5 days
    with three satellites flying, so a narrower bin resolves the flowering peak more sharply,
    but it also leaves more bins empty on a cloudy paddock and every empty bin is a NaN the
    booster has to route around. Which way that trades is an empirical question about THIS
    dataset, so it is a flag rather than a constant.
    """
    step = BIN_STEP if bin_step is None else bin_step
    ts = ts.copy()
    ts["doy"] = pd.to_datetime(ts.time).dt.dayofyear
    edges = np.arange(BIN_START, BIN_END + step, step)
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
        have = [b for b in bins if f"{c}_{b}" in F.columns]
        if not have:
            continue
        A = F[[f"{c}_{b}" for b in have]].values
        F[f"{c}__p10"] = np.nanpercentile(A, 10, axis=1)
        F[f"{c}__p90"] = np.nanpercentile(A, 90, axis=1)
        F[f"{c}__amp"] = F[f"{c}__p90"] - F[f"{c}__p10"]
        with np.errstate(invalid="ignore"):
            idx = np.where(np.isnan(A).all(axis=1), np.nan, np.nanargmax(
                np.where(np.isnan(A), -np.inf, A), axis=1))
        # Index into the bins that ACTUALLY have a column, not into the full bin list. On the
        # training set all 13 bins are populated and the two are the same list, so this never
        # mattered; over a single tile a whole DOY bin can be absent (no clear scene anywhere
        # in it), and then the argmax position and the bin label part company — every peak
        # would be reported one or more bins too early. Peak timing is the single most
        # discriminating feature for canola, so that is not a small error.
        F[f"{c}__peak_doy"] = [np.nan if np.isnan(i) else int(have[int(i)]) for i in idx]

    if with_geo:
        g = lab.set_index("TrialCode")[["lat", "lon", "Year"]]
        F = F.join(g)
    return F


def score_extra(model, Xtr, ytr, Xte, yte, Xex, ex_meta, classes, f):
    """What the classifier does with paddocks that belong to NONE of its classes.

    The model has only ever seen NVT trial paddocks, so every class it can emit is a crop.
    Deployed nationally it meets a landscape that is ~87 % grazing, and a softmax over crops
    cannot abstain. This measures the size of that failure instead of assuming it.

    Both sides are scored by the SAME model fitted on <=2022, so the crop rows (2023-24) and
    the pasture rows are equally out-of-sample. Scoring pasture with a model refitted on
    everything, against crop numbers from a held-out split, would compare two different
    models and the gap between them would not be attributable to the class being absent.

    The confidence comparison is the point. A max-probability threshold is the cheapest
    possible open-set fix, and it is only worth anything if pasture sits lower than crop —
    so both distributions are reported, along with what a threshold would actually cost.
    """
    model.fit(Xtr, ytr)
    pex = model.predict(Xex)
    conf_ex = model.predict_proba(Xex).max(axis=1)
    conf_crop = model.predict_proba(Xte).max(axis=1)
    ok_crop = model.predict(Xte) == yte

    f.write("\n### Out-of-class behaviour — paddocks that are none of these classes\n\n")
    f.write(f"- {len(pex)} non-crop paddocks scored by the <=2022 model; "
            f"**every one is forced into a crop class**\n\n")
    f.write("| predicted | n | share |\n|---|---|---|\n")
    vc = pd.Series(pex).value_counts()
    for c in classes:
        f.write(f"| {c} | {int(vc.get(c, 0))} | {vc.get(c, 0)/len(pex):.1%} |\n")

    if ex_meta is not None and "stratum" in ex_meta.columns:
        f.write("\nBy stratum (`hard` = pasture inside cropping country, "
                "`easy` = rangeland):\n\n| stratum | n | mean max-prob |\n|---|---|---|\n")
        for s, g in ex_meta.assign(conf=conf_ex).groupby("stratum"):
            f.write(f"| {s} | {len(g)} | {g.conf.mean():.3f} |\n")

    f.write(f"\n**Confidence.** Pasture median max-prob {np.median(conf_ex):.3f} "
            f"against {np.median(conf_crop):.3f} on real crop paddocks the model also "
            f"never saw.\n\n")
    f.write("| max-prob threshold | pasture rejected | crop kept | crop correct of kept |\n")
    f.write("|---|---|---|---|\n")
    for t in [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]:
        kept = conf_crop >= t
        f.write(f"| {t:.2f} | {(conf_ex < t).mean():.1%} | {kept.mean():.1%} | "
                f"{(ok_crop[kept].mean() if kept.any() else float('nan')):.1%} |\n")
    return {"split": "out-of-class (non-crop paddocks)", "n": len(pex),
            "median_conf_noncrop": float(np.median(conf_ex)),
            "median_conf_crop": float(np.median(conf_crop))}


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
                    f"(n={len(pos)})\n")
            # Threshold-free summaries, for the canola map. Average precision is the one to
            # quote against an imbalanced positive class — ROC AUC flatters it, because the
            # negatives dominate and most of the ROC curve covers thresholds no map would use.
            from sklearn.metrics import average_precision_score, roc_auc_score
            yb = (yte == "Canola").astype(int)
            base = yb.mean()
            f.write(f"- **average precision {average_precision_score(yb, p):.3f}** "
                    f"(baseline = prevalence {base:.3f}), "
                    f"ROC AUC {roc_auc_score(yb, p):.3f}\n\n")
        else:
            f.write("\n")

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


def save_confusion(Xtr, ytr, Xte, yte, model, classes, png, target):
    """Confusion matrix as a heatmap — the archival record of what species-level got to.

    Row-normalised, because the classes are wildly imbalanced (wheat 835, lentil 81) and a
    raw-count image just shows which class is common. Counts are printed inside the cells so
    nothing is hidden by the normalisation.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import confusion_matrix, f1_score

    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    cm = confusion_matrix(yte, pred, labels=classes)
    row = cm.sum(1, keepdims=True)
    frac = np.divide(cm, row, out=np.zeros_like(cm, float), where=row > 0)

    n = len(classes)
    fig, ax = plt.subplots(figsize=(1.05 * n + 3.2, 1.0 * n + 2.4))
    im = ax.imshow(frac, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(n), classes, rotation=45, ha="right")
    ax.set_yticks(range(n), classes)
    ax.set_xlabel("predicted")
    ax.set_ylabel("true")
    macro = f1_score(yte, pred, average="macro", labels=classes, zero_division=0)
    ax.set_title(f"{target}: temporal transfer (train <=2022, test 2023-24)\n"
                 f"macro F1 {macro:.3f}, chance {1/n:.3f} — row-normalised, counts in cells",
                 fontsize=10)
    for i in range(n):
        for j in range(n):
            if cm[i, j]:
                ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=8,
                        color="white" if frac[i, j] > 0.5 else "black")
    fig.colorbar(im, ax=ax, label="fraction of true class", fraction=0.046)
    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(png)), exist_ok=True)
    fig.savefig(png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"confusion heatmap -> {png}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bands", nargs="*", default=[], help="glob(s) of 10-band time series")
    ap.add_argument("--indices", nargs="*", default=[], help="glob(s) of 3-index time series")
    ap.add_argument("--s1", nargs="*", default=[],
                    help="glob(s) of Sentinel-1 paddock series (s1_extract.py). Joined LEFT, "
                         "not inner: S1B's 2021 failure leaves some 2022-24 paddocks with no "
                         "usable scenes, and those must become NaN features rather than "
                         "vanish from the training set — dropping them would silently change "
                         "the sample between the with-S1 and without-S1 arms and make the "
                         "comparison meaningless.")
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--score-extra", nargs="*", default=[],
                    help="glob(s) of time series for paddocks with NO class label (the "
                         "grazing negatives). Never trained on — only scored, to measure "
                         "what the model does with inputs outside its label space")
    ap.add_argument("--extra-meta", help="csv keyed by TrialCode carrying a `stratum` column "
                                         "for the --score-extra rows")
    ap.add_argument("--features-csv", help="per-trial precomputed features keyed by TrialCode "
                                           "(e.g. presto_embeddings_SENSITIVE.csv)")
    ap.add_argument("--features-only", action="store_true",
                    help="use ONLY --features-csv columns, dropping the built features")
    ap.add_argument("--test-keep", help="csv of TrialCodes that MAY be scored on. Training is "
                    "unaffected. Without this, an arm using a cleaner --keep also gets a "
                    "cleaner TEST set, so 'cleaning helps' cannot be separated from 'cleaning "
                    "made the exam easier'. Point every arm at the same file and the "
                    "comparison isolates the training data, which is the actual question.")
    ap.add_argument("--keep", help="cfi_heatmap_ALL_rows csv: restrict to quality-filtered "
                                   "trials (strongly recommended)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--with-geo", action="store_true")
    ap.add_argument("--min-obs", type=int, default=10)
    ap.add_argument("--bin-step", type=int, default=BIN_STEP,
                    help=f"DOY bin width in days (default {BIN_STEP}). Narrower resolves the "
                         "flowering peak more sharply and leaves more bins empty on a cloudy "
                         "paddock; which way that trades has never been measured here")
    ap.add_argument("--model", choices=["hgb", "rf"], default="hgb")
    ap.add_argument("--seed", type=int, default=0,
                    help="model random_state. Vary it to separate a real feature effect "
                         "from boosting noise: the S1 gain moved from +0.044 to +0.029 "
                         "when 68 trials were added, which is only interpretable against "
                         "a measured seed spread.")
    ap.add_argument("--target", choices=["group3", "group4", "species", "canola", "crop2"],
                    default="group3",
                    help="group3 (default): Canola/Cereal/Legume, the distinctions actually "
                         "needed and the ones that survive the co-located-label problem. "
                         "group4: those three plus Grazing — the target a national map needs, "
                         "since 87 %% of NLUM's agricultural land is grazing and a three-way "
                         "softmax cannot abstain. "
                         "crop2: binary Crop vs Grazing, the first stage of the two-stage "
                         "alternative to group4 — same rows, so the two are comparable. "
                         "species: all 9 crops, kept for the record — see --confusion-png. "
                         "canola: binary Canola vs Other — the publishable 10 m map, and the "
                         "only target whose negative class needs no within-group separability.")
    ap.add_argument("--importance-repeats", type=int, default=10,
                    help="permutation-importance repeats; 0 skips it. This is the dominant "
                         "cost of the whole script — it refits nothing but scores the model "
                         "n_features x n_repeats times, and with n_jobs=-1 it silently scales "
                         "with the cores available, so a run that took 10 min on a login node "
                         "took >90 min on a 4-CPU PBS job.")
    ap.add_argument("--confusion-png", help="write the temporal-split confusion matrix as a "
                                            "heatmap figure (row-normalised)")
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
    if args.s1:
        t1 = load(args.s1)
        sources.append(("s1", t1,
                        [c for c in t1.columns if c.endswith("_pad_median")]))
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
    parts, s1_parts = [], []
    for name, t, cols in sources:
        if args.keep:
            t = t[t.TrialCode.isin(keep)]
        t = t[t.TrialCode.isin(keep_obs)]
        f = build_features(t, cols, False, lab, args.bin_step)
        if len(sources) > 1:
            f = f.add_suffix(f"@{name}")
        (s1_parts if name == "s1" else parts).append(f)
    if not parts:
        # S1 alone. There is no optical block to hang the LEFT join off, so the first
        # backscatter block becomes the base; the no-coverage-keeps-its-row argument below
        # does not apply, because with nothing else in the row there is nothing to keep.
        parts, s1_parts = s1_parts[:1], s1_parts[1:]
    F = parts[0] if len(parts) == 1 else parts[0].join(parts[1:], how="inner")
    for f in s1_parts:
        # LEFT, so a paddock with no S1 coverage keeps its optical features and gets NaN for
        # backscatter. The booster handles NaN natively; an inner join would delete the row.
        F = F.join(f, how="left")
        print(f"S1 joined: {int(f.index.isin(F.index).sum())} of {len(F)} rows have "
              f"backscatter ({100*F[f.columns[0]].notna().mean():.0f} % non-null)")
    # Precomputed per-trial features (Presto embeddings) go through the SAME splits, model and
    # metrics as the hand-built ones — otherwise "Presto scores X" and "our features score Y"
    # are two different experiments and the difference between them is not attributable.
    if args.features_csv:
        E = pd.read_csv(args.features_csv).drop_duplicates("TrialCode").set_index("TrialCode")
        if args.features_only:
            F = E.reindex(F.index.intersection(E.index))
        else:
            F = F.join(E, how="inner")
        print(f"features csv: {E.shape[1]} columns -> matrix {F.shape}")
    if args.with_geo:
        F = F.join(lab.set_index("TrialCode")[["lat", "lon", "Year"]])
    meta = lab.set_index("TrialCode").loc[F.index, ["crop", "Year", "site", "state"]]
    # A feature that is NaN for every trial carries nothing and only slows the fit.
    F = F.loc[:, F.notna().any()]
    X = F.values
    if args.target == "group3":
        y = meta.crop.map(GROUP).values
    elif args.target == "group4":
        y = meta.crop.map(GROUP4).values
    elif args.target == "crop2":
        # Stage 1 of the two-stage alternative. Run on the SAME rows as group4 so the two
        # designs are compared on one row universe: a two-stage pipeline that quietly sees a
        # different sample is not an alternative, it is a different experiment.
        y = np.where(meta.crop.values == "Grazing", "Grazing", "Crop")
    elif args.target == "canola":
        # Binary against EVERYTHING else, not against wheat. Measured on this dataset, lentil,
        # faba bean, field pea and lupin all sit ABOVE wheat on peak CFI, so a canola-vs-wheat
        # evaluation flatters the index by ~8 pp and is not the number to publish.
        y = np.where(meta.crop.values == "Canola", "Canola", "Other")
    else:
        y = meta.crop.values
    if args.target in ("group3", "group4") and pd.isna(y).any():
        raise SystemExit(f"unmapped crops: {sorted(set(meta.crop[pd.isna(y)]))}")
    classes = sorted(pd.Series(y).value_counts().index.tolist())
    print(f"feature matrix {X.shape}, {len(classes)} classes")

    def mk():
        if args.model == "rf":
            clf = RandomForestClassifier(n_estimators=500, min_samples_leaf=2,
                                         class_weight="balanced_subsample",
                                         n_jobs=-1, random_state=args.seed)
        else:
            clf = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.06,
                                                 class_weight="balanced", random_state=args.seed)
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

        # A fixed yardstick, when asked for: the test rows are the SAME for every arm, so a
        # score difference can only come from what each arm trained on.
        scorable = (meta.index.isin(set(pd.read_csv(args.test_keep).TrialCode))
                    if args.test_keep else np.ones(len(meta), bool))
        if args.test_keep:
            f.write(f"- **fixed test set**: scoring restricted to {int(scorable.sum())} of "
                    f"{len(meta)} rows listed in `{os.path.basename(args.test_keep)}`\n")

        # Temporal transfer
        tr = (meta.Year <= 2022).values
        te = ~tr & scorable
        results.append(evaluate(f"Temporal transfer — train <=2022, test 2023-24",
                                X[tr], y[tr], X[te], y[te], mk(), classes, f))

        if args.confusion_png:
            save_confusion(X[tr], y[tr], X[te], y[te],
                           mk(), classes, args.confusion_png, args.target)

        if args.score_extra:
            tex = load(args.score_extra)
            nx = tex.groupby("TrialCode").size()
            tex = tex[tex.TrialCode.isin(set(nx[nx >= args.min_obs].index))]
            # Reindexed onto the TRAINING matrix's columns, so a DOY bin that happens to be
            # empty for these paddocks becomes NaN rather than silently shifting every
            # downstream column by one and scoring the model on misaligned features.
            Fx = build_features(tex, value_cols, False, lab,
                                args.bin_step).reindex(columns=F.columns)
            exm = None
            if args.extra_meta:
                exm = (pd.read_csv(args.extra_meta).drop_duplicates("TrialCode")
                       .set_index("TrialCode").reindex(Fx.index))
            print(f"score-extra: {len(Fx)} unlabelled paddocks, "
                  f"{Fx.notna().any().sum()} of {F.shape[1]} features present")
            results.append(score_extra(mk(), X[tr], y[tr], X[te], y[te],
                                       Fx.values, exm, classes, f))

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
        # Folds are built from each arm's own rows — that is the training difference under
        # test — but the SCORE is read off the common subset only.
        ys, ps = y[scorable], preds.astype(str)[scorable]
        macro = f1_score(ys, ps, average="macro")
        bal = balanced_accuracy_score(ys, ps)
        f.write("\n### Spatial transfer — 5-fold GroupKFold on site\n\n")
        f.write(f"- **macro F1 {macro:.3f}, balanced accuracy {bal:.3f}**"
                f"{f' (scored on {len(ys)} fixed rows)' if args.test_keep else ''}\n\n")
        rep = classification_report(ys, ps, output_dict=True, zero_division=0)
        f.write("| crop | precision | recall | F1 | n |\n|---|---|---|---|---|\n")
        for c in classes:
            if c in rep:
                r = rep[c]
                f.write(f"| {c} | {r['precision']:.2f} | {r['recall']:.2f} | "
                        f"{r['f1-score']:.2f} | {int(r['support'])} |\n")
        cm = confusion_matrix(ys, ps, labels=classes)
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
            if not args.importance_repeats:
                raise RuntimeError("skipped by --importance-repeats 0")
            from sklearn.inspection import permutation_importance
            m = mk()
            # `tr` is already a numpy array (line above builds it with `.values`), so asking
            # for `.values` again raises AttributeError — which the except below swallowed as
            # "(importance skipped: ...)". Every run that printed that line was reporting a
            # bug, not a deliberate skip.
            m.fit(X[tr], y[tr])
            imp = permutation_importance(m, X[~tr], y[~tr],
                                         n_repeats=args.importance_repeats,
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
            # The out-of-class rows have no macro F1 and cannot: the paddocks carry no label
            # to be right or wrong about. They report confidence instead, in their own section.
            if "macro_f1" in r:
                f.write(f"| {r['split']} | {r['macro_f1']:.3f} | {r['bal_acc']:.3f} |\n")

    for r in results:
        if "macro_f1" not in r:
            print(f"{r['split']:55s} n {r['n']}  median max-prob "
                  f"{r['median_conf_noncrop']:.3f} vs crop {r['median_conf_crop']:.3f}")
            continue
        print(f"{r['split']:55s} macroF1 {r['macro_f1']:.3f}  balAcc {r['bal_acc']:.3f}")
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
