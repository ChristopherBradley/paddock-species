#!/usr/bin/env python3
"""
Does tuning the gradient booster's hyperparameters beat the adopted settings?

The manuscript said the classifier ran at scikit-learn defaults. It does not: `train_species.py`
builds `HistGradientBoostingClassifier(max_iter=400, learning_rate=0.06, class_weight="balanced")`,
which is already two steps off default. So the open question is not "defaults vs tuned" but
"the two hand-picked values vs a searched grid", which is what this measures.

THE TEST SET IS NEVER USED TO CHOOSE ANYTHING. Tuning a model on the rows you then report it on
is the single easiest way to manufacture an improvement, so:
  * temporal — the grid is searched by GroupKFold on `site` INSIDE the <=2022 training rows only.
    The winner is refit on all training rows and scored ONCE on the fixed 543-row 2023-24 test
    set. The test rows never enter the search.
  * spatial  — NESTED GroupKFold. Each outer fold re-runs the whole search on its own training
    rows, so no fold's test paddocks influenced its own model's settings. A single search
    followed by a cross-validated score of the winner would leak, and is the mistake this
    design exists to avoid.

AND THE RESULT IS COMPARED AGAINST TEST-SET NOISE, not against zero. `HistGradientBoosting-
Classifier` is deterministic at this data size — it subsamples only when binning more than
200k rows, and early stopping is off — so refitting at a different `random_state` returns the
identical model and a seed spread of exactly 0.0000. That makes seed variation useless as a
yardstick here. The uncertainty that does matter is the test set: macro F1 is read off 543
trials, and a 0.005 difference between two models on 543 rows is well inside sampling noise.
So the comparison is a PAIRED BOOTSTRAP over the test rows — resample the 543 trials, score
both models on each resample, and report the distribution of the difference. If that interval
straddles zero, tuning did not beat the adopted settings, whatever the point estimates say.

    python3 tune_hyperparams.py --indices "$D/samgeo/ts_v2/*_SENSITIVE.csv" \
        --bands "$D/samgeo/bands_ts/*_SENSITIVE.csv" \
        --bands-keep-families ndre2 vi2 vi3 vdvi vci evi2_sharma \
        --labeled $D/nvt_trials_labeled.csv \
        --keep $D/keep_arms/keep_reviewed_SENSITIVE.csv \
        --test-keep $D/keep_arms/testkeep_temporal_SENSITIVE.csv \
        --out output/HYPERPARAMETER_TUNING.md

Aggregate output only — no TrialCodes — so the report is committable.
"""
import argparse
import glob
import itertools
import json
import os
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import f1_score, balanced_accuracy_score
from sklearn.model_selection import GroupKFold
from joblib import Parallel, delayed

from train_species import GROUP, build_features, family, BANDS

# The adopted settings, from train_species.py's mk(). Everything else is a scikit-learn default.
ADOPTED = {"max_iter": 400, "learning_rate": 0.06}
SKLEARN_DEFAULT = {"max_iter": 100, "learning_rate": 0.1}
FIXED = {"class_weight": "balanced", "random_state": 0}

GRID = {
    "learning_rate": [0.03, 0.06, 0.1, 0.2],
    "max_iter": [100, 200, 400, 800],
    "max_leaf_nodes": [15, 31, 63],
    "min_samples_leaf": [10, 20, 40],
    "l2_regularization": [0.0, 1.0],
}


def load_ts(pats):
    files = []
    for p in pats:
        files += sorted(glob.glob(p))
    if not files:
        raise SystemExit(f"no files matched {pats}")
    t = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    t = t.drop_duplicates(["TrialCode", "time"])
    return t[t.n_clear_px / t.n_px_paddock.clip(lower=1) >= 0.5]


def build_matrix(args):
    """The adopted 153-feature matrix, assembled exactly as train_species.py assembles it."""
    sources = []
    if args.bands:
        tb = load_ts(args.bands)
        sources.append(("bands", tb, [b for b in BANDS if b in tb.columns]))
    if args.indices:
        ti = load_ts(args.indices)
        sources.append(("indices", ti, [c for c in ti.columns if c.endswith("_pad_median")]))
    if not sources:
        raise SystemExit("give --bands and/or --indices")

    lab = pd.read_csv(args.labeled).drop_duplicates("TrialCode")
    keep = set(pd.read_csv(args.keep).TrialCode) if args.keep else None
    ts = sources[0][1]
    if keep is not None:
        ts = ts[ts.TrialCode.isin(keep)]
    n = ts.groupby("TrialCode").size()
    keep_obs = set(n[n >= args.min_obs].index)

    parts = []
    for name, t, cols in sources:
        if keep is not None:
            t = t[t.TrialCode.isin(keep)]
        t = t[t.TrialCode.isin(keep_obs)]
        f = build_features(t, cols, False, lab)
        if name == "bands" and args.bands_keep_families is not None:
            fams = set(args.bands_keep_families)
            f = f[[c for c in f.columns if family(c) in fams]]
        if len(sources) > 1:
            f = f.add_suffix(f"@{name}")
        parts.append(f)
    F = parts[0] if len(parts) == 1 else parts[0].join(parts[1:], how="inner")
    meta = lab.set_index("TrialCode").loc[F.index, ["crop", "Year", "site", "state"]]
    F = F.loc[:, F.notna().any()]
    y = meta.crop.map(GROUP).values
    if pd.isna(y).any():
        raise SystemExit("unmapped crops")
    return F.values, y, meta, list(F.columns)


def configs():
    keys = list(GRID)
    return [dict(zip(keys, v)) for v in itertools.product(*(GRID[k] for k in keys))]


def score_config(params, X, y, groups, n_splits, seed=0):
    """Mean macro F1 over GroupKFold splits of the rows handed in."""
    gk = GroupKFold(n_splits=n_splits)
    out = []
    for a, b in gk.split(X, y, groups=groups):
        m = HistGradientBoostingClassifier(**{**FIXED, **params, "random_state": seed})
        m.fit(X[a], y[a])
        out.append(f1_score(y[b], m.predict(X[b]), average="macro"))
    return float(np.mean(out))


def search(X, y, groups, cfgs, n_splits, n_jobs):
    scores = Parallel(n_jobs=n_jobs, verbose=0)(
        delayed(score_config)(c, X, y, groups, n_splits) for c in cfgs)
    i = int(np.argmax(scores))
    return cfgs[i], float(scores[i]), scores


def fit_predict(params, Xtr, ytr, Xte, seed=0):
    m = HistGradientBoostingClassifier(**{**FIXED, **params, "random_state": seed})
    m.fit(Xtr, ytr)
    return m.predict(Xte)


def paired_bootstrap(yte, pa, pb, n=2000, seed=0):
    """Distribution of macro F1(b) - macro F1(a) under resampling of the TEST ROWS.

    Paired: every resample scores both models on the same rows, so the shared difficulty of a
    draw cancels and what is left is the difference between the models.
    """
    rng = np.random.default_rng(seed)
    yte = np.asarray(yte); pa = np.asarray(pa); pb = np.asarray(pb)
    n_te = len(yte)
    out = np.empty(n)
    for i in range(n):
        ix = rng.integers(0, n_te, n_te)
        # A resample that happens to drop a whole class makes macro F1 undefined for it;
        # sklearn returns 0 for that class with zero_division=0, which would be a fake
        # difference, so those draws are skipped instead.
        if len(np.unique(yte[ix])) < len(np.unique(yte)):
            out[i] = np.nan
            continue
        out[i] = (f1_score(yte[ix], pb[ix], average="macro")
                  - f1_score(yte[ix], pa[ix], average="macro"))
    return out[~np.isnan(out)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indices", nargs="*", default=[])
    ap.add_argument("--bands", nargs="*", default=[])
    ap.add_argument("--bands-keep-families", nargs="*", default=None)
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--keep")
    ap.add_argument("--test-keep")
    ap.add_argument("--min-obs", type=int, default=10)
    ap.add_argument("--inner-splits", type=int, default=5)
    ap.add_argument("--inner-splits-nested", type=int, default=3,
                    help="inner folds inside each outer spatial fold; 3 keeps the nested "
                         "search to ~5x the temporal one")
    ap.add_argument("--outer-splits", type=int, default=5)
    ap.add_argument("--bootstrap", type=int, default=2000,
                    help="paired bootstrap resamples of the test rows")
    ap.add_argument("--n-jobs", type=int, default=-1)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    t0 = time.time()
    X, y, meta, cols = build_matrix(args)
    print(f"matrix {X.shape}", flush=True)
    scorable = (meta.index.isin(set(pd.read_csv(args.test_keep).TrialCode))
                if args.test_keep else np.ones(len(meta), bool))
    cfgs = configs()
    print(f"{len(cfgs)} configurations", flush=True)

    # ---------- temporal ----------
    tr = (meta.Year <= 2022).values
    te = ~tr & scorable
    print(f"temporal: train {tr.sum()}, test {te.sum()}", flush=True)
    best_t, best_cv, all_cv = search(X[tr], y[tr], meta.site.values[tr], cfgs,
                                     args.inner_splits, args.n_jobs)
    print(f"  best inner CV {best_cv:.4f}  {best_t}  ({time.time()-t0:.0f}s)", flush=True)

    rows_t, preds = [], {}
    for nm, prm in [("adopted (max_iter 400, lr 0.06)", ADOPTED),
                    ("scikit-learn defaults", SKLEARN_DEFAULT),
                    ("tuned", best_t)]:
        p = fit_predict(prm, X[tr], y[tr], X[te])
        preds[nm] = p
        f1 = f1_score(y[te], p, average="macro")
        ba = balanced_accuracy_score(y[te], p)
        # Determinism check: a second fit at a different random_state must return the same
        # predictions, otherwise the "seed noise is zero" claim in the docstring is wrong.
        same = bool((fit_predict(prm, X[tr], y[tr], X[te], seed=7) == p).all())
        rows_t.append((nm, prm, f1, ba, same))
        print(f"  {nm}: test macro F1 {f1:.4f} (seed-invariant: {same})", flush=True)

    adopted_nm = "adopted (max_iter 400, lr 0.06)"
    boot = paired_bootstrap(y[te], preds[adopted_nm], preds["tuned"], n=args.bootstrap)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    p_better = float((boot > 0).mean())
    print(f"  bootstrap tuned-adopted: {boot.mean():+.4f} [{lo:+.4f}, {hi:+.4f}], "
          f"P(tuned better) {p_better:.2f}", flush=True)

    # ---------- spatial, nested ----------
    print("spatial nested CV...", flush=True)
    gk = GroupKFold(n_splits=args.outer_splits)
    pred_tuned = np.empty(len(y), dtype=object)
    pred_adopted = np.empty(len(y), dtype=object)
    chosen = []
    for k, (a, b) in enumerate(gk.split(X, y, groups=meta.site.values), 1):
        bp, bs, _ = search(X[a], y[a], meta.site.values[a], cfgs,
                           args.inner_splits_nested, args.n_jobs)
        chosen.append(bp)
        m = HistGradientBoostingClassifier(**{**FIXED, **bp})
        m.fit(X[a], y[a]); pred_tuned[b] = m.predict(X[b])
        m2 = HistGradientBoostingClassifier(**{**FIXED, **ADOPTED})
        m2.fit(X[a], y[a]); pred_adopted[b] = m2.predict(X[b])
        print(f"  outer {k}/{args.outer_splits}: inner CV {bs:.4f} {bp} "
              f"({time.time()-t0:.0f}s)", flush=True)

    sp_tuned = f1_score(y[scorable], list(pred_tuned[scorable]), average="macro")
    sp_adopted = f1_score(y[scorable], list(pred_adopted[scorable]), average="macro")
    print(f"  spatial macro F1: adopted {sp_adopted:.4f}, tuned {sp_tuned:.4f}", flush=True)

    # ---------- report ----------
    L = ["# Hyperparameter tuning of the crop-group classifier", "",
         f"Generated by `src/paddocks/tune_hyperparams.py` on {time.strftime('%Y-%m-%d')}. "
         "Aggregate only: no trial codes.", "",
         f"- matrix: {X.shape[0]} trials, {X.shape[1]} features, 3 classes",
         f"- grid: {len(cfgs)} configurations over "
         + ", ".join(f"`{k}` {v}" for k, v in GRID.items()),
         f"- fixed: `class_weight='balanced'`, everything not in the grid at its "
         f"scikit-learn default",
         f"- the adopted model is **not** at scikit-learn defaults: `train_species.py` sets "
         f"`max_iter=400, learning_rate=0.06`",
         f"- runtime {time.time()-t0:.0f}s", "",
         "## Temporal split (train <=2022, test 2023-24)", "",
         "The grid was searched by 5-fold GroupKFold on `site` **inside the training rows "
         "only**; the winner was refit on all training rows and scored once on the fixed "
         f"{int(te.sum())}-row test set.", "",
         "| configuration | test macro F1 | balanced acc. | seed-invariant |",
         "|---|---|---|---|"]
    for nm, prm, f1, ba, same in rows_t:
        L.append(f"| {nm} | **{f1:.4f}** | {ba:.4f} | {'yes' if same else 'NO'} |")
    adopted_mu = rows_t[0][2]; tuned_mu = rows_t[2][2]
    delta = tuned_mu - adopted_mu
    L += ["", f"- tuned minus adopted: **{delta:+.4f}** macro F1",
          f"- best configuration found: `{json.dumps(best_t, sort_keys=True)}` "
          f"(inner CV {best_cv:.4f})", "",
          "`HistGradientBoostingClassifier` is deterministic on 2,194 rows (it subsamples only "
          "when binning >200k rows, and early stopping is off), so `random_state` changes "
          "nothing and seed spread is exactly zero. The yardstick is therefore the test set, "
          f"not the seed: a paired bootstrap over the {int(te.sum())} test trials "
          f"({len(boot)} usable resamples of {args.bootstrap}).", "",
          f"- tuned minus adopted, bootstrap mean **{boot.mean():+.4f}**, "
          f"95% interval **[{lo:+.4f}, {hi:+.4f}]**",
          f"- the tuned model scores higher on **{p_better:.0%}** of resamples",
          f"- the interval {'EXCLUDES' if (lo > 0 or hi < 0) else 'straddles'} zero", ""]
    L += ["## Spatial split (nested 5-fold GroupKFold on site)", "",
          "Every outer fold re-ran the whole grid search on its own training rows "
          f"({args.inner_splits_nested}-fold inner GroupKFold), so no fold's test paddocks "
          "influenced the settings used to predict them. Scored on the same fixed "
          f"{int(scorable.sum())} rows.", "",
          "| configuration | spatial macro F1 |", "|---|---|",
          f"| adopted (max_iter 400, lr 0.06) | **{sp_adopted:.4f}** |",
          f"| tuned (nested) | **{sp_tuned:.4f}** |", "",
          f"- tuned minus adopted: **{sp_tuned - sp_adopted:+.4f}** macro F1", "",
          "Configuration chosen by each outer fold:", "",
          "| fold | " + " | ".join(GRID) + " |",
          "|---|" + "---|" * len(GRID)]
    for i, c in enumerate(chosen, 1):
        L.append(f"| {i} | " + " | ".join(str(c[k]) for k in GRID) + " |")
    stable = len({json.dumps(c, sort_keys=True) for c in chosen}) == 1
    L += ["", f"- the outer folds {'agreed on one configuration' if stable else 'did NOT agree on a single configuration'}"
          + ("" if stable else ", which is itself evidence that the grid is picking up fold "
             "noise rather than a setting the data supports"), ""]

    # A gain counts only if the bootstrap interval clears zero AND the spatial split, which
    # re-searched independently in every fold, agrees. Either one alone is a coin flip.
    verdict = ("worth adopting" if lo > 0 and sp_tuned > sp_adopted else "not worth adopting")
    L += ["## Verdict", "",
          f"Tuning is **{verdict}** on this evidence. Temporal {delta:+.4f} macro F1 "
          f"(bootstrap 95% interval [{lo:+.4f}, {hi:+.4f}]) and spatial "
          f"{sp_tuned - sp_adopted:+.4f}."]
    if verdict == "not worth adopting":
        L += ["", "The adopted `max_iter=400, learning_rate=0.06` stands, and the national "
                  "predictions do not need to be rerun."]
    else:
        L += ["", "Rerunning the national predictions with the tuned configuration would be "
                  "needed before the map and the paper agree."]
    L.append("")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        f.write("\n".join(L) + "\n")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
