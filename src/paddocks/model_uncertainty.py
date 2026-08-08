#!/usr/bin/env python3
"""
Confidence intervals on the species-model comparisons — the missing half of `train_species.py`.

WHY THIS EXISTS. Five configurations were run overnight and they land within 0.03 macro F1 of
each other (indices 0.316, bands 0.301, combined 0.302, and the two --select-k runs 0.287 /
0.319). Conclusions were then drawn from that ordering: "ten bands alone do not beat three
indices". But macro F1 here averages nine per-class F1s, four of which rest on 22-30 test
samples, so its sampling error is large and entirely unquantified. A 0.015 gap between two
configs may be nothing at all. This project already learned the neighbouring lesson once —
a partial-extraction run was read as a feature experiment when it was a sample-size
experiment — and this is the same error wearing a different hat.

WHAT IT MEASURES, and why each piece is separate:

  1. PAIRED bootstrap over the temporal test set. Each resample is applied to EVERY config's
     saved predictions, so the difference between two configs is computed on identical rows.
     This matters more than it sounds: the configs share a test set, so their errors are
     strongly correlated, and comparing two independent CIs would overstate the uncertainty
     on their difference by a wide margin. The paired difference is the number that decides
     whether a comparison is real; a marginal CI on each config is not.

  2. CLUSTER bootstrap over the spatial folds, resampling SITES rather than rows. The same
     paddock recurs across years, so rows are not independent — resampling rows would treat
     one site's four seasons as four pieces of evidence and report an interval that is too
     narrow. Same reasoning that put GroupKFold on site in the first place.

  3. SEED spread, from refitting with several random_state values. This is a different noise
     source from test-set sampling and the two do not substitute for each other: a gap that
     is stable across resampled test sets but flips sign across seeds is still not a result.

  4. The CFI-THRESHOLD baseline (max CFI in DOY 200-300, thresholded at 5 % FPR) scored on
     the same test rows, so the headline "+31 pp from modelling the whole seasonal shape"
     gets a paired interval rather than a bare difference of two point estimates.

Aggregate output only — no TrialCodes — so the report is committable.
"""
import argparse
import glob
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train_species import BANDS, build_features  # noqa: E402

FLOWER = (200, 300)      # calendar DOY window holding the canola peak, as in the diagnosis
BOOT = 2000
SEEDS = [0, 1, 2, 3, 4]


def macro_f1(y, pred, classes):
    from sklearn.metrics import f1_score
    return f1_score(y, pred, average="macro", labels=classes, zero_division=0)


def canola_at_fpr(y, p, fpr=0.05):
    """Sensitivity for canola at a fixed false-positive budget.

    The threshold is recomputed inside every bootstrap resample rather than fixed once on the
    full test set, because choosing it is part of the estimator — freezing it would report the
    variability of the sensitivity alone and hide the variability of the operating point.
    """
    pos, neg = p[y == "Canola"], p[y != "Canola"]
    if len(pos) < 5 or len(neg) < 5:
        return np.nan
    return float((pos > np.quantile(neg, 1 - fpr)).mean())


def canola_at_fpr_per_season(y, p, season, fpr=0.05):
    """Same, but with the threshold fitted separately within each season.

    This project measured that pooling seasons destroys CFI separation — the pooled Youden J
    (0.318) fell BELOW every individual season (0.400-0.778), because the absolute CFI level
    shifts between seasons so one threshold cannot serve all. Scoring the CFI baseline with a
    single pooled threshold would therefore handicap it against its own established method and
    inflate the model's apparent advantage. The model gets no such per-season help, so this is
    the conservative comparison, not the flattering one.

    Both this and the model's operating point are chosen ON the test set, so they are
    oracle-thresholded alike — the comparison is fair, but neither number is a deployable
    out-of-sample threshold.
    """
    hits = tot = 0
    for s in np.unique(season):
        m = season == s
        ys, ps = y[m], p[m]
        pos, neg = ps[ys == "Canola"], ps[ys != "Canola"]
        if len(pos) < 1 or len(neg) < 5:
            continue
        hits += int((pos > np.quantile(neg, 1 - fpr)).sum())
        tot += len(pos)
    return float(hits / tot) if tot else np.nan


def ci(v, lo=2.5, hi=97.5):
    v = np.asarray(v, dtype=float)
    v = v[~np.isnan(v)]
    if not len(v):
        return (np.nan, np.nan)
    return float(np.percentile(v, lo)), float(np.percentile(v, hi))


def fmt(point, lohi, pct=False, signed=False):
    lo, hi = lohi
    s = "{:+.1f}" if (pct and signed) else "{:.1f}" if pct else "{:+.3f}" if signed else "{:.3f}"
    m = 100 if pct else 1
    return f"**{s.format(point * m)}** [{s.format(lo * m)}, {s.format(hi * m)}]"


def crosses_zero(lohi):
    lo, hi = lohi
    return not (lo > 0 or hi < 0)


def load(pats, min_clear=0.5):
    files = sorted({f for p in pats for f in glob.glob(p)})
    if not files:
        raise SystemExit(f"no files matched {pats}")
    t = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    t = t.drop_duplicates(["TrialCode", "time"])
    return t[t.n_clear_px / t.n_px_paddock.clip(lower=1) >= min_clear]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bands", nargs="*", required=True)
    ap.add_argument("--indices", nargs="*", required=True)
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--keep", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-obs", type=int, default=10)
    ap.add_argument("--boot", type=int, default=BOOT)
    # Both exist so the whole report can be smoke-tested end to end in ~1 min before
    # committing to 30 full fits; a crash in the write-up stage is otherwise very expensive.
    ap.add_argument("--seeds", type=int, default=len(SEEDS))
    ap.add_argument("--max-iter", type=int, default=400)
    ap.add_argument("--cache", help="npz of fitted predictions; reused when the trial set and "
                                    "feature shapes match, so the report can be refined "
                                    "without refitting")
    args = ap.parse_args()
    seeds = SEEDS[:args.seeds]

    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.model_selection import GroupKFold

    lab = pd.read_csv(args.labeled).drop_duplicates("TrialCode")
    keep = set(pd.read_csv(args.keep).TrialCode)

    tb, ti = load(args.bands), load(args.indices)
    band_cols = [b for b in BANDS if b in tb.columns]
    idx_cols = [c for c in ti.columns if c.endswith("_pad_median")]

    # Every config must be scored on IDENTICAL trials or the "paired" comparison is not paired.
    # The overnight runs differed by a row or two (2477 vs 2476), which is harmless for a point
    # estimate and fatal for a paired difference.
    feats = {}
    for name, t, cols in [("bands", tb, band_cols), ("indices", ti, idx_cols)]:
        t = t[t.TrialCode.isin(keep)]
        n = t.groupby("TrialCode").size()
        t = t[t.TrialCode.isin(set(n[n >= args.min_obs].index))]
        feats[name] = build_features(t, cols, False, lab)
    common = feats["bands"].index.intersection(feats["indices"].index)
    common = common.intersection(lab.set_index("TrialCode").index)
    print(f"common trial set: {len(common)}")

    X = {"indices": feats["indices"].loc[common],
         "bands": feats["bands"].loc[common],
         "combined": feats["bands"].loc[common].add_suffix("@bands").join(
             feats["indices"].loc[common].add_suffix("@indices"))}
    for k in X:
        X[k] = X[k].loc[:, X[k].notna().any()]
        print(f"{k}: {X[k].shape[1]} features")

    meta = lab.set_index("TrialCode").loc[common, ["crop", "Year", "site", "state"]]
    y = meta.crop.values
    classes = sorted(pd.Series(y).value_counts().index.tolist())
    tr = (meta.Year <= 2022).values

    # ---- CFI-threshold baseline on the same rows -------------------------------------------
    w = ti[ti.TrialCode.isin(common)].copy()
    w["doy"] = pd.to_datetime(w.time).dt.dayofyear
    w = w[(w.doy >= FLOWER[0]) & (w.doy <= FLOWER[1])]
    peak = w.groupby("TrialCode").cfi_pad_median.max().reindex(common)

    def mk(seed):
        return HistGradientBoostingClassifier(max_iter=args.max_iter, learning_rate=0.06,
                                              class_weight="balanced", random_state=seed)

    # ---- temporal: fit every config at every seed, keep the test-set probabilities ----------
    # Fits are cached because they are the whole cost of this script (~15 min) while the
    # report below is seconds — and refining the write-up should not mean refitting. The
    # cache is keyed on the trial set and feature shapes; anything upstream of that changing
    # invalidates it. Delete the file to force a refit.
    configs = ["indices", "bands", "combined"]
    key = (f"{len(common)}_{args.min_obs}_{args.max_iter}_{len(seeds)}_"
           + "_".join(str(X[c].shape[1]) for c in configs))
    proba, pred, oof = {}, {}, {}
    cached = False
    if args.cache and os.path.exists(args.cache):
        z = np.load(args.cache, allow_pickle=True)
        if str(z["key"]) == key:
            for c in configs:
                for s in seeds:
                    proba[(c, s)] = z[f"proba_{c}_{s}"]
                    pred[(c, s)] = z[f"pred_{c}_{s}"]
                oof[c] = z[f"oof_{c}"]
            cached = True
            print(f"loaded cached fits from {args.cache}")
        else:
            print(f"cache key mismatch ({z['key']} != {key}) — refitting")

    if not cached:
        for c in configs:
            Xa = X[c].values
            for s in seeds:
                m = mk(s)
                m.fit(Xa[tr], y[tr])
                proba[(c, s)] = m.predict_proba(Xa[~tr])[:, list(m.classes_).index("Canola")]
                pred[(c, s)] = m.predict(Xa[~tr])
                print(f"temporal {c} seed {s}: macroF1 "
                      f"{macro_f1(y[~tr], pred[(c, s)], classes):.3f}", flush=True)

    yte = y[~tr]
    cfi_te = peak.values[~tr]
    season_te = meta.Year.values[~tr]

    # ---- spatial: out-of-fold predictions, seed 0 ------------------------------------------
    groups = meta.site.fillna(meta.index.to_series()).values
    if not cached:
        for c in configs:
            Xa = X[c].values
            p = np.empty(len(y), dtype=object)
            for tri, tei in GroupKFold(n_splits=5).split(Xa, y, groups):
                m = mk(0)
                m.fit(Xa[tri], y[tri])
                p[tei] = m.predict(Xa[tei])
            oof[c] = p.astype(str)
            print(f"spatial {c}: macroF1 {macro_f1(y, oof[c], classes):.3f}", flush=True)
        if args.cache:
            np.savez(args.cache, key=key,
                     **{f"proba_{c}_{s}": proba[(c, s)] for c in configs for s in seeds},
                     **{f"pred_{c}_{s}": pred[(c, s)] for c in configs for s in seeds},
                     **{f"oof_{c}": oof[c] for c in configs})
            print(f"cached fits -> {args.cache}")

    # ---- bootstraps -------------------------------------------------------------------------
    rng = np.random.default_rng(0)
    n_te = len(yte)
    bt = {c: {"f1": [], "sens": []} for c in configs}
    bt["cfi_pooled"] = {"sens": []}
    bt["cfi_per_season"] = {"sens": []}
    for _ in range(args.boot):
        i = rng.integers(0, n_te, n_te)          # one resample, applied to every config
        for c in configs:
            bt[c]["f1"].append(macro_f1(yte[i], pred[(c, 0)][i], classes))
            bt[c]["sens"].append(canola_at_fpr(yte[i], proba[(c, 0)][i]))
        bt["cfi_pooled"]["sens"].append(canola_at_fpr(yte[i], cfi_te[i]))
        bt["cfi_per_season"]["sens"].append(
            canola_at_fpr_per_season(yte[i], cfi_te[i], season_te[i]))

    # Spatial: resample SITES, not rows.
    site_of = pd.Series(groups, index=np.arange(len(y)))
    by_site = {s: np.where(groups == s)[0] for s in pd.unique(groups)}
    sites = np.array(list(by_site.keys()))
    bs = {c: [] for c in configs}
    for _ in range(args.boot):
        pick = rng.integers(0, len(sites), len(sites))
        i = np.concatenate([by_site[sites[k]] for k in pick])
        for c in configs:
            bs[c].append(macro_f1(y[i], oof[c][i], classes))

    # ---- report -----------------------------------------------------------------------------
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        f.write("# How much of the model comparison is real?\n\n")
        f.write(f"Paired bootstrap, {args.boot} resamples, 95 % percentile intervals. "
                f"All configs scored on an **identical** trial set "
                f"(n={len(common)}, temporal test n={int((~tr).sum())}) so differences are "
                f"paired row-by-row.\n\n")
        f.write("Feature counts: " +
                ", ".join(f"{c} {X[c].shape[1]}" for c in configs) + ".\n\n")

        f.write("## 1. Each config on its own\n\n")
        f.write("| config | temporal macro F1 | canola @ 5 % FPR | spatial macro F1 |\n")
        f.write("|---|---|---|---|\n")
        for c in configs:
            f.write(f"| {c} | {fmt(macro_f1(yte, pred[(c,0)], classes), ci(bt[c]['f1']))} "
                    f"| {fmt(canola_at_fpr(yte, proba[(c,0)]), ci(bt[c]['sens']), pct=True)} "
                    f"| {fmt(macro_f1(y, oof[c], classes), ci(bs[c]))} |\n")
        f.write(f"| CFI threshold, pooled seasons | — | "
                f"{fmt(canola_at_fpr(yte, cfi_te), ci(bt['cfi_pooled']['sens']), pct=True)} "
                f"| — |\n")
        f.write(f"| CFI threshold, per season | — | "
                f"{fmt(canola_at_fpr_per_season(yte, cfi_te, season_te), ci(bt['cfi_per_season']['sens']), pct=True)} "
                f"| — |\n\n")
        f.write("The per-season CFI row is the baseline that matters: this project measured "
                "that one pooled threshold cannot serve multiple seasons, so the pooled row "
                "understates what thresholding CFI can do.\n\n")

        f.write("## 2. The comparisons the conclusions rest on (paired)\n\n")
        f.write("A difference whose interval spans zero is not evidence of an ordering.\n\n")
        f.write("| comparison | metric | paired difference | verdict |\n|---|---|---|---|\n")
        pairs = [("bands", "indices"), ("combined", "indices"), ("combined", "bands")]
        for a, b in pairs:
            for metric, key, pct in [("temporal macro F1", "f1", False),
                                     ("canola @ 5 % FPR", "sens", True)]:
                d = np.asarray(bt[a][key]) - np.asarray(bt[b][key])
                point = (macro_f1(yte, pred[(a,0)], classes) - macro_f1(yte, pred[(b,0)], classes)
                         if key == "f1" else
                         canola_at_fpr(yte, proba[(a,0)]) - canola_at_fpr(yte, proba[(b,0)]))
                v = "indistinguishable" if crosses_zero(ci(d)) else "real"
                f.write(f"| {a} - {b} | {metric} | {fmt(point, ci(d), pct=pct, signed=True)} "
                        f"| {v} |\n")
            d = np.asarray(bs[a]) - np.asarray(bs[b])
            point = macro_f1(y, oof[a], classes) - macro_f1(y, oof[b], classes)
            v = "indistinguishable" if crosses_zero(ci(d)) else "real"
            f.write(f"| {a} - {b} | spatial macro F1 | {fmt(point, ci(d), signed=True)} "
                    f"| {v} |\n")
        base = {"cfi_pooled": canola_at_fpr(yte, cfi_te),
                "cfi_per_season": canola_at_fpr_per_season(yte, cfi_te, season_te)}
        for bname in ("cfi_pooled", "cfi_per_season"):
            for c in configs:
                d = np.asarray(bt[c]["sens"]) - np.asarray(bt[bname]["sens"])
                point = canola_at_fpr(yte, proba[(c, 0)]) - base[bname]
                v = "indistinguishable" if crosses_zero(ci(d)) else "real"
                f.write(f"| {c} model - {bname.replace('_', ' ')} | canola @ 5 % FPR | "
                        f"{fmt(point, ci(d), pct=True, signed=True)} | {v} |\n")
        f.write("\n")

        f.write("## 3. Is any of the spread just the seed?\n\n")
        spread = max(float(np.std([macro_f1(yte, pred[(c, s)], classes) for s in seeds]))
                     for c in configs)
        f.write(f"Refits of each config on identical data at `random_state` "
                f"{', '.join(str(s) for s in seeds)}. Largest macro-F1 sd across seeds: "
                f"**{spread:.4f}**.\n\n")
        if spread < 1e-9:
            f.write("**Zero — the fits are bit-identical.** `HistGradientBoostingClassifier` "
                    "only consumes its seed for the early-stopping validation split, and "
                    "early stopping is off below 10,000 samples (we have "
                    f"{int(tr.sum())} training rows). So the seed is not a noise source here, "
                    "and none of the differences between the overnight runs can be waved away "
                    "as re-fit jitter — but equally, seeds cannot be used to estimate this "
                    "model's variance. Test-set sampling, in sections 1-2, is the noise that "
                    "matters.\n\n")
        else:
            f.write("| config | temporal macro F1 across seeds | canola @ 5 % FPR "
                    "across seeds |\n|---|---|---|\n")
            for c in configs:
                v = [macro_f1(yte, pred[(c, s)], classes) for s in seeds]
                w2 = [canola_at_fpr(yte, proba[(c, s)]) for s in seeds]
                f.write(f"| {c} | {np.mean(v):.3f} ± {np.std(v):.3f} "
                        f"(min {min(v):.3f}, max {max(v):.3f}) | "
                        f"{100*np.mean(w2):.1f} ± {100*np.std(w2):.1f} "
                        f"(min {100*min(w2):.1f}, max {100*max(w2):.1f}) |\n")
            f.write("\n")

        f.write("## 4. Per-class intervals on the temporal split\n\n")
        f.write("Where the macro average's uncertainty comes from — the minority classes. "
                "Same resamples across configs, so columns are comparable row-by-row.\n\n")
        f.write("| crop | n in test | " + " | ".join(configs) + " |\n")
        f.write("|---|---|" + "---|" * len(configs) + "\n")
        from sklearn.metrics import f1_score
        draws = [rng.integers(0, n_te, n_te) for _ in range(400)]
        for cl in classes:
            row = [f"| {cl} | {int((yte == cl).sum())} "]
            for c in configs:
                b = [f1_score(yte[i], pred[(c, 0)][i], labels=[cl], average="macro",
                              zero_division=0) for i in draws]
                pt = f1_score(yte, pred[(c,0)], labels=[cl], average="macro", zero_division=0)
                lo, hi = ci(b)
                row.append(f"| {pt:.2f} [{lo:.2f}, {hi:.2f}] ")
            f.write("".join(row) + "|\n")

    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
