#!/usr/bin/env python3
"""
Can the paddock-median satellite series predict YIELD, not just crop type?

The lead came from `CANOLA_YIELD_CHECK.md`: CFI flowering amplitude tracks canola single-site
yield at Spearman rho 0.38. That was a by-product of asking why some canola paddocks looked
flat, and it is worth testing properly.

THE BASELINE THAT DECIDES WHETHER THIS IS A RESULT. Most yield variance in Australian cropping
is season x region — a drought year in the Mallee is a bad year for everyone in it. A model
given the satellite series will look impressive against a constant-mean baseline and mean
nothing. So every arm here is scored against **year + state alone**, which is free, requires no
imagery, and is the number any yield map has to beat to justify itself. Reported as
`R2_vs_mean` (the usual R2) and `R2_gain_over_yearstate`.

WHAT THE TARGET ACTUALLY IS, and why it limits the paper's claim. NVT single-site yield is a
small replicated VARIETY TRIAL yield under trial management, averaged across ~17 varieties. It
is not the yield of the surrounding commercial paddock, and trial plots generally out-yield
commercial crops. Within-trial variety sd is ~0.28 t/ha, so the trial mean is well determined
(~0.07 t/ha s.e.) — the uncertainty is in the transfer from trial to paddock, not in the label.
Anything built on this predicts "NVT-equivalent yield", and a paddock yield map derived from it
inherits an unquantified offset. `CANOLA_FLOWERING_AUDIT.md` measured the same support mismatch
from the other side: the field flowers HARDER than the trial (median window-paddock CFI
amplitude -144), so the bias is not even reliably one-directional.

SPLITS ARE THE SAME AS THE CLASSIFIER'S and for the same reasons: GroupKFold on `site` so a
paddock cannot appear in both halves, and a temporal split to 2023-24. Geography is excluded
from the feature arms by default — with lat/lon in the matrix a booster learns the yield map of
Australia rather than what a crop looks like, which is exactly the confound the year+state
baseline is there to expose.

SENSITIVE: reads TrialCodes and yields; report is aggregate-only and safe to commit.
"""
import argparse
import glob

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from scipy.stats import pearsonr, spearmanr

from train_species import build_features


def load_ts(pat):
    files = sorted(glob.glob(pat))
    if not files:
        raise SystemExit(f"no files matched {pat}")
    t = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    t = t.drop_duplicates(["TrialCode", "time"])
    return t[t.n_clear_px / t.n_px_paddock.clip(lower=1) >= 0.5]


def load_yield(path):
    x = pd.ExcelFile(path)
    parts = []
    for s in x.sheet_names:
        d = x.parse(s)
        parts.append(d[["TrialCode", "Single Site Yield", "Abandoned"]])
    Y = pd.concat(parts, ignore_index=True)
    Y = Y[Y["Single Site Yield"].notna()]
    g = Y.groupby("TrialCode").agg(yield_tha=("Single Site Yield", "mean"),
                                   n_var=("Single Site Yield", "size"),
                                   var_sd=("Single Site Yield", "std"))
    return g


def metrics(yt, yp):
    return {"R2": r2_score(yt, yp), "RMSE": mean_squared_error(yt, yp) ** 0.5,
            "MAE": mean_absolute_error(yt, yp),
            "pearson_r": pearsonr(yt, yp)[0], "spearman_rho": spearmanr(yt, yp)[0]}


def fit_eval(X, y, tr, te, seed=0):
    m = HistGradientBoostingRegressor(random_state=seed)
    m.fit(X[tr], y[tr])
    return metrics(y[te], m.predict(X[te]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indices")
    ap.add_argument("--s1")
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--yields", required=True, help="NVT xlsx")
    ap.add_argument("--keep", required=True)
    ap.add_argument("--crops", nargs="+", default=["Canola", "Wheat", "Barley"])
    ap.add_argument("--min-obs", type=int, default=10)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    lab = pd.read_csv(args.labeled).drop_duplicates("TrialCode")
    keep = set(pd.read_csv(args.keep).TrialCode)
    Y = load_yield(args.yields)

    sources = []
    if args.indices:
        t = load_ts(args.indices)
        sources.append(("indices", t, [c for c in t.columns if c.endswith("_pad_median")]))
    if args.s1:
        t = load_ts(args.s1)
        sources.append(("s1", t, [c for c in t.columns if c.endswith("_pad_median")]))
    if not sources:
        raise SystemExit("give --indices and/or --s1")

    parts = []
    for name, t, cols in sources:
        t = t[t.TrialCode.isin(keep)]
        n = t.groupby("TrialCode").size()
        t = t[t.TrialCode.isin(set(n[n >= args.min_obs].index))]
        f = build_features(t, cols, False, lab)
        if len(sources) > 1:
            f = f.add_suffix(f"@{name}")
        parts.append(f)
    F = parts[0] if len(parts) == 1 else parts[0].join(parts[1:], how="inner")
    F = F.loc[:, F.notna().any()]

    meta = lab.set_index("TrialCode").reindex(F.index)[["crop", "Year", "site", "state"]]
    F = F.join(Y[["yield_tha"]])
    ok = F.yield_tha.notna() & meta.crop.notna()
    F, meta = F[ok], meta[ok]
    feat_cols = [c for c in F.columns if c != "yield_tha"]

    lines = ["# Yield from the paddock-median series", "",
             f"- features: {' + '.join(n for n, _, _ in sources)} "
             f"({len(feat_cols)} columns)",
             f"- target: NVT single-site yield, averaged over varieties within a trial",
             "- **this is trial yield under trial management, not commercial paddock yield** "
             "— see the module docstring",
             "- on the temporal split the year+state baseline collapses to **state only**: "
             "2023 and 2024 are unseen in training, so their year dummies are all-zero. That "
             "is the real operational situation — you cannot know a season's effect in "
             "advance — so it is the honest bar, but it is a weaker bar than the spatial one.",
             ""]

    for crop in args.crops:
        sel = meta.crop == crop
        if sel.sum() < 60:
            lines += [f"## {crop}", "", f"only {int(sel.sum())} trials — skipped", ""]
            continue
        sub, m = F[sel], meta[sel]
        y = sub.yield_tha.values
        X = sub[feat_cols].values
        # year+state baseline, one-hot; no imagery, and this is the bar to beat
        B = pd.get_dummies(m[["Year", "state"]].astype(str)).values.astype(float)

        lines += [f"## {crop}", "",
                  f"- {len(sub)} trials, yield {np.median(y):.2f} t/ha median, "
                  f"sd {y.std():.2f}, range {y.min():.2f}-{y.max():.2f}", ""]

        rows = []
        # temporal transfer
        tr = (m.Year <= 2022).values
        te = ~tr
        if te.sum() >= 30:
            for nm, XX in [("year+state baseline", B), ("satellite features", X),
                           ("satellite + year/state", np.hstack([X, B]))]:
                r = fit_eval(XX, y, tr, te)
                rows.append(("temporal", nm, int(te.sum()), r))
        # spatial transfer
        gk = GroupKFold(n_splits=5)
        for nm, XX in [("year+state baseline", B), ("satellite features", X),
                       ("satellite + year/state", np.hstack([X, B]))]:
            pred = np.full(len(y), np.nan)
            for a, b in gk.split(XX, y, groups=m.site.values):
                mo = HistGradientBoostingRegressor(random_state=0).fit(XX[a], y[a])
                pred[b] = mo.predict(XX[b])
            rows.append(("spatial", nm, len(y), metrics(y, pred)))

        for split in ["temporal", "spatial"]:
            rr = [r for r in rows if r[0] == split]
            if not rr:
                continue
            base = next((r[3]["R2"] for r in rr if r[1] == "year+state baseline"), np.nan)
            lines += [f"### {split} transfer" +
                      (" — train <=2022, test 2023-24" if split == "temporal"
                       else " — 5-fold GroupKFold on site"), "",
                      "| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |",
                      "|---|---|---|---|---|---|---|---|"]
            for _, nm, n, r in rr:
                g = "—" if nm == "year+state baseline" else f"{r['R2']-base:+.3f}"
                lines.append(f"| {nm} | {n} | **{r['R2']:.3f}** | {g} | {r['RMSE']:.3f} | "
                             f"{r['MAE']:.3f} | {r['pearson_r']:.3f} | {r['spearman_rho']:.3f} |")
            lines.append("")

    with open(args.out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
