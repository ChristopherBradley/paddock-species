#!/usr/bin/env python3
"""
Why does a paddock labelled canola not show a flowering signature?

Two questions, and the second is the one that has never been tested.

**Q1. Which canola paddocks fail to flower?** A per-panel threshold on peak CFI at a 5 % false
positive rate against the non-canola paddocks of that same year and state — the same rule the
project's headline detection rate is quoted under, so "not detected" here means exactly what
it means there, and the counts are comparable.

**Q2. Is the paddock outside the trial actually the trial's crop?** The whole design rests on
an assumption nobody has measured: NVT gives a point and a crop, SAM gives the surrounding
field, and the paddock median is taken to describe that crop. If the grower planted something
else in the rest of the field — or SAM merged two fields — the label is attached to the wrong
time series and no amount of model tuning will fix it.

The data already contains the control needed to test this, and it costs nothing to compute.
Every trial carries TWO series from the same pixels-in-time:

    cfi_win_mean    a 200 m window centred on the trial point  -> mostly the trial itself
    cfi_pad_median  the whole SAM paddock                      -> the field around it

**The window is 200 m x 200 m = 4 ha, against a 57 ha median paddock.** So it is 14x more
concentrated on the trial, not a pure sample of it: an NVT trial site is roughly 0.5-2 ha, so
the window is the trial plus two to eight times its area of whatever surrounds it. That makes
this a DIRECTIONAL test, not a clean one. It can only under-report — contamination of the
window by the surrounding field drags the two series together, so a paddock whose field really
is a different crop may still fail to separate. Read the resulting rate as a floor.

Where the field matches the trial the two must rise together in the flowering window. Where the
window flowers and the paddock does not, the trial is canola and **the field around it is not**
— which is the mislabelled-polygon mode, caught directly rather than inferred from geometry.

Two tests are reported, because a threshold crossing alone is too weak to carry the claim. The
per-panel threshold test is comparable with the project's headline detection rate but counts
any pair that straddles the cut, including pairs a few CFI units apart. The magnitude test asks
instead whether `win_amp - pad_amp` sits in the upper tail of the SAME quantity measured on
cereal and legume paddocks, where no systematic trial-versus-field difference should exist and
which therefore supplies the null this comparison needs.

That gives four outcomes, and each undetected canola paddock lands in exactly one:

| window flowers | paddock flowers | reading |
|---|---|---|
| yes | yes | assumption holds; the paddock is canola |
| yes | **no** | **paddock is not canola outside the trial** — wrong field or a merge |
| no | no | nothing flowered anywhere: cloud, or the crop genuinely did not flower |
| no | yes | the window is the odd one out — point misplaced, or window contaminated |

Cloud is separated before any of that, because an unobserved peak and an absent peak look
identical in a summary statistic. A trial with no clear scenes inside DOY 200-300 cannot show
flowering whatever it grew, so it is classified as unobservable and excluded from the ratio —
the year-round `min_obs 15` filter says nothing about whether the flowering weeks themselves
were seen.

SENSITIVE: the per-trial csv carries TrialCodes.
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                # noqa: E402

REFL_SCALE = 10000.0
FLOWER = (200, 300)      # the window this project established for canola in Stage 2
BASELINE = (100, 180)    # vegetative, before flowering: the paddock's own reference level
GROUP = {"Canola": "Canola", "Wheat": "Cereal", "Barley": "Cereal", "Oat": "Cereal",
         "Chickpea": "Legume", "Faba Bean": "Legume", "Field Pea": "Legume",
         "Lentil": "Legume", "Lupin": "Legume"}


def per_trial_features(ts, metric):
    """Peak, baseline and amplitude in the flowering window, per trial, for one metric."""
    d = ts.dropna(subset=[metric])
    fl = d[d.doy.between(*FLOWER)]
    bl = d[d.doy.between(*BASELINE)]
    f = fl.groupby("TrialCode")[metric].max().rename("peak") * REFL_SCALE
    b = bl.groupby("TrialCode")[metric].median().rename("base") * REFL_SCALE
    n = fl.groupby("TrialCode")[metric].size().rename("n_flower_obs")
    doy = fl.loc[fl.groupby("TrialCode")[metric].idxmax()].set_index("TrialCode").doy \
        .rename("peak_doy")
    out = pd.concat([f, b, n, doy], axis=1)
    # Largest run of days with no clear scene inside the flowering window. A 40-day hole can
    # hide the whole event while the observation COUNT still looks respectable.
    gap = {}
    for tc, g in fl.groupby("TrialCode"):
        v = np.sort(g.doy.unique())
        edges = np.concatenate([[FLOWER[0]], v, [FLOWER[1]]])
        gap[tc] = int(np.max(np.diff(edges))) if len(edges) > 1 else FLOWER[1] - FLOWER[0]
    out["max_gap_d"] = pd.Series(gap)
    out["amp"] = out.peak - out.base
    return out


def panel_threshold(df, col, fpr=0.05):
    """Value of `col` that admits `fpr` of the panel's NON-canola paddocks.

    Per-panel because absolute CFI level shifts between seasons and states — a national
    threshold was already measured on this dataset to score below every season it pooled.
    """
    neg = df.loc[df.crop_group != "Canola", col].dropna()
    if len(neg) < 8:
        return np.nan
    return float(np.quantile(neg, 1 - fpr))


def classify(r):
    """One row -> one reason. Order matters: an unobserved peak masquerades as an absent one."""
    if not r.observed:
        return "unobservable (cloud/no scenes in the flowering window)"
    if r.pad_detected:
        return "detected"
    if r.win_detected:
        return "paddock is not canola outside the trial"
    if r.win_amp_rank < 0.5:
        return "nothing flowered anywhere (window and paddock both flat)"
    return "weak everywhere (window elevated but below threshold)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", nargs="+", required=True)
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--reviewed", required=True)
    ap.add_argument("--review-gpkg", help="PADDOCK_REVIEW_SENSITIVE.gpkg — supplies "
                                          "match_rule_new/dist_m/share_n, which ts_v2 does "
                                          "NOT have: its `match_rule` predates the rematch "
                                          "and contains no 'upgraded' values at all")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--min-clear-frac", type=float, default=0.5)
    ap.add_argument("--min-flower-obs", type=int, default=3,
                    help="clear scenes needed inside DOY 200-300 to call flowering observable")
    ap.add_argument("--max-gap-d", type=int, default=45,
                    help="a longer hole inside the flowering window also counts as unobserved")
    ap.add_argument("--fpr", type=float, default=0.05)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    files = sorted({f for p in args.ts for f in glob.glob(p)})
    ts = pd.concat((pd.read_csv(f, parse_dates=["time"]) for f in files), ignore_index=True)
    ts = ts.drop_duplicates(subset=["TrialCode", "time"])
    ts = ts[ts["n_clear_px"] / ts["n_px_paddock"].clip(lower=1) >= args.min_clear_frac].copy()
    ts["doy"] = ts.time.dt.dayofyear

    rev = pd.read_csv(args.reviewed)
    usable = set(rev.loc[rev.usable.astype(bool), "TrialCode"])
    ts = ts[ts.TrialCode.isin(usable)]

    lab = pd.read_csv(args.labeled)[["TrialCode", "Year", "state", "region", "crop"]] \
        .drop_duplicates("TrialCode")
    pad = per_trial_features(ts, "cfi_pad_median").add_prefix("pad_")
    win = per_trial_features(ts, "cfi_win_mean").add_prefix("win_")
    # CONTROL. The paddock series is a MEDIAN and the window series is a MEAN, so any gap
    # between them could be the estimator rather than the ground. `cfi_pad_mean` makes the
    # comparison mean-vs-mean on identical pixels-in-time; if the gap survives that, it is
    # spatial structure and not an artefact of how the two were summarised.
    padm = per_trial_features(ts, "cfi_pad_mean").add_prefix("padmean_")
    d = pad.join(win, how="outer").join(padm, how="outer") \
        .reset_index(names="TrialCode").merge(lab, on="TrialCode")
    meta = ts.groupby("TrialCode").agg(paddock_ha=("paddock_ha", "first"),
                                       match_rule=("match_rule", "first"),
                                       edge_dist_m=("edge_dist_m", "first"),
                                       n_obs=("doy", "size")).reset_index()
    d = d.merge(meta, on="TrialCode", how="left")
    # ts_v2's `match_rule` is the PRE-rematch column: its values are contains/nearest_Nm and
    # it never says "upgraded", so any upgrade statistic computed from it silently reads 0 %.
    # The post-rematch rule lives only in the review package.
    if args.review_gpkg:
        import geopandas as gpd
        T = gpd.read_file(args.review_gpkg, layer="trials")
        cols = [c for c in ("match_rule_new", "dist_m", "share_n", "poly_id") if c in T.columns]
        d = d.merge(pd.DataFrame(T[["TrialCode"] + cols]), on="TrialCode", how="left")
    d["crop_group"] = d.crop.map(GROUP)
    d["panel"] = d.Year.astype(str) + "_" + d.state

    # Per-panel detection, on amplitude rather than raw peak: a paddock that is bright all
    # season is not flowering, and only the rise above its own baseline says it is.
    rows = []
    for panel, g in d.groupby("panel"):
        g = g.copy()
        for src in ("pad", "win"):
            thr = panel_threshold(g, f"{src}_amp", args.fpr)
            g[f"{src}_thr"] = thr
            g[f"{src}_detected"] = g[f"{src}_amp"] > thr if np.isfinite(thr) else False
            neg = g.loc[g.crop_group != "Canola", f"{src}_amp"].dropna()
            g[f"{src}_amp_rank"] = (g[f"{src}_amp"].rank(pct=True) if len(neg) < 8 else
                                    g[f"{src}_amp"].apply(
                                        lambda v: np.mean(neg < v) if np.isfinite(v) else np.nan))
        rows.append(g)
    d = pd.concat(rows, ignore_index=True)

    d["observed"] = (d.pad_n_flower_obs.fillna(0) >= args.min_flower_obs) & \
                    (d.pad_max_gap_d.fillna(999) <= args.max_gap_d)

    # MAGNITUDE TEST. `gap` is how much more the trial's own 4 ha flowered than its field. On
    # cereal and legume paddocks the trial and the field are the same crop by construction, so
    # their `gap` distribution is what this statistic looks like when the assumption HOLDS —
    # measurement noise, window contamination and paddock heterogeneity, and nothing else.
    # Anything past its upper tail on a canola paddock is a real trial-versus-field difference.
    d["gap"] = d.win_amp - d.pad_amp
    d["gap_meanmean"] = d.win_amp - d.padmean_amp
    null = d.loc[d.crop_group.ne("Canola") & d.observed, "gap"].dropna()
    gap_cut = float(np.quantile(null, 1 - args.fpr)) if len(null) >= 30 else np.nan
    d["gap_big"] = d.gap > gap_cut

    can = d[d.crop_group == "Canola"].copy()
    can["reason"] = can.apply(classify, axis=1)

    # ---- report -------------------------------------------------------------------------
    order = ["detected",
             "paddock is not canola outside the trial",
             "nothing flowered anywhere (window and paddock both flat)",
             "weak everywhere (window elevated but below threshold)",
             "unobservable (cloud/no scenes in the flowering window)"]
    counts = can.reason.value_counts().reindex(order).fillna(0).astype(int)

    obs = can[can.observed]
    L = []
    L.append("# Canola paddocks with no flowering signature — why\n")
    L.append(f"Generated by `src/paddocks/canola_flowering_audit.py` on the reviewed polygon "
             f"set ({len(rev[rev.usable.astype(bool)])} usable trials).\n")
    L.append(f"- flowering window DOY {FLOWER[0]}-{FLOWER[1]}, baseline DOY "
             f"{BASELINE[0]}-{BASELINE[1]}, amplitude = peak - baseline\n")
    L.append(f"- detection = amplitude above the per-panel {args.fpr:.0%}-FPR threshold set on "
             f"that panel's non-canola paddocks\n")
    L.append(f"- {len(can)} reviewed-good canola paddocks, of which {int((~can.observed).sum())}"
             f" are unobservable in the flowering window\n\n")

    L.append("## Verdict\n\n| reason | paddocks | % of observed |\n|---|---|---|\n")
    for k in order:
        pct = "" if k.startswith("unobservable") else f"{100*counts[k]/max(len(obs),1):.1f} %"
        L.append(f"| {k} | {counts[k]} | {pct} |\n")

    mis = can[can.reason == "paddock is not canola outside the trial"]
    flat = can[can.reason.str.startswith("nothing flowered")]
    L.append(f"\n## The assumption under test: does the field match the trial?\n\n")
    L.append(f"**The window is 4 ha and the median paddock is 57 ha**, so the window is 14x "
             f"more concentrated on the trial but still contains surrounding field. "
             f"Contamination can only pull the two series together, so every rate below is a "
             f"floor, not an estimate.\n\n")
    L.append(f"### Test 1 — threshold crossing (comparable with the headline rate)\n\n")
    L.append(f"The window clears its panel's {args.fpr:.0%}-FPR threshold and the paddock does "
             f"not, on **{len(mis)} of {len(obs)} observed canola paddocks "
             f"({100*len(mis)/max(len(obs),1):.1f} %)**.\n\n")
    L.append(f"### Test 2 — magnitude against a null (the stronger claim)\n\n")
    if np.isfinite(gap_cut):
        n_big = int((can.observed & can.gap_big).sum())
        both = int((can.observed & can.gap_big & ~can.pad_detected).sum())
        L.append(f"On cereal and legume paddocks the trial and its field grow the same crop by "
                 f"construction, so their `window - paddock` amplitude difference is this "
                 f"statistic's null: median {null.median():+.0f}, "
                 f"{args.fpr:.0%} tail at **{gap_cut:+.0f}** (n={len(null)}, CFI x10000).\n\n")
        L.append(f"- **{n_big} of {len(obs)} observed canola paddocks "
                 f"({100*n_big/max(len(obs),1):.1f} %) exceed that cut** — the trial flowered "
                 f"materially more than its field, beyond what same-crop paddocks ever show\n")
        L.append(f"- **{both} of those also fail paddock-level detection**, which is the "
                 f"defensible count of polygons whose field is probably not canola: "
                 f"{100*both/max(len(obs),1):.1f} % of observed canola paddocks\n")
        L.append(f"- for reference, canola's own median gap is {can.gap.median():+.0f} against "
                 f"the null's {null.median():+.0f}\n")

    L.append(f"\n### The gap runs the OTHER way, and that is the more useful finding\n\n")
    nullmm = d.loc[d.crop_group.ne("Canola") & d.observed, "gap_meanmean"].median()
    L.append(f"Canola's median `window - paddock` is **{can.gap.median():+.0f}**: on the "
             f"typical canola paddock the FIELD flowers harder than the trial does. Part of "
             f"that is the estimator and part is not — putting both supports on a mean "
             f"attenuates it to **{can.gap_meanmean.median():+.0f}** against a null of "
             f"{nullmm:+.0f}, so roughly "
             f"{100*(1 - (can.gap_meanmean.median() - nullmm) / (can.gap.median() - null.median())):.0f}"
             f" % of the raw gap was median-versus-mean and the remainder is real spatial "
             f"structure. The direction survives the control; only its size shrinks.\n\n")
    L.append(f"The agronomy explains it: an NVT canola trial is a mosaic of small variety "
             f"plots with tracks, buffers and staggered maturities inside a 4 ha window, while "
             f"the surrounding commercial paddock is one uniform crop flowering together. "
             f"**The paddock median is not merely a larger sample of the trial's crop — it is "
             f"a cleaner one.** That is a point in favour of the whole paddock-median design, "
             f"and it is the reason this test can only be read as a floor.\n")

    if len(mis):
        L.append(f"\nCharacter of the threshold-crossing set: median paddock "
                 f"{mis.paddock_ha.median():.0f} ha against {obs.paddock_ha.median():.0f} ha "
                 f"for all observed canola; median window amplitude {mis.win_amp.median():.0f} "
                 f"against paddock {mis.pad_amp.median():.0f}.\n")
        if "match_rule_new" in mis.columns and mis.match_rule_new.notna().any():
            # Counts, not percentages: 1/28 rounds to "4 %" next to a "0 %" that is really
            # 2/605, and the pair reads as a contrast that is not there.
            L.append(f"Upgraded matches: "
                     f"{int(mis.match_rule_new.astype(str).str.contains('upgraded').sum())}"
                     f"/{len(mis)} here against "
                     f"{int(obs.match_rule_new.astype(str).str.contains('upgraded').sum())}"
                     f"/{len(obs)} of all observed canola — the review had already dropped "
                     f"225 of the 259 upgraded matches as `point_outside`, which is the mode "
                     f"the upgrade rule was known to generate.\n")
    L.append(f"\nThe complementary case — nothing flowers in the window either — is "
             f"**{len(flat)} paddocks**. Those cannot be blamed on the polygon: the trial "
             f"point itself shows no flowering.\n\n")
    L.append(f"**What they are NOT is failed crops.** `CANOLA_YIELD_CHECK.md` joins these "
             f"paddocks to the raw NVT yield sheet: every one produced grain, none is flagged "
             f"`Abandoned`, and their median single-site yield is 1.67 t/ha against 2.55 for "
             f"detected canola (Mann-Whitney p = 2.6e-12). Canola cannot yield without "
             f"flowering, so these crops DID flower. The reading is weaker flowering on a "
             f"poorer crop, not absent flowering — and CFI amplitude tracks canola yield "
             f"continuously at Spearman rho = 0.38 across all 614 paddocks, so these "
             f"categories are bins on a gradient rather than distinct failure modes.\n")

    L.append("\n## Cloud\n\n")
    L.append(f"{int((~can.observed).sum())} canola paddocks have fewer than "
             f"{args.min_flower_obs} clear scenes inside DOY {FLOWER[0]}-{FLOWER[1]}, or a gap "
             f"longer than {args.max_gap_d} d inside it. Median clear scenes in the window for "
             f"the rest: {obs.pad_n_flower_obs.median():.0f}.\n")

    L.append("\n## Per-panel\n\n| panel | canola | detected | field mismatch | flat | "
             "unobservable |\n|---|---|---|---|---|---|\n")
    for panel, g in can.groupby("panel"):
        L.append(f"| {panel} | {len(g)} | {int((g.reason=='detected').sum())} | "
                 f"{int((g.reason=='paddock is not canola outside the trial').sum())} | "
                 f"{int(g.reason.str.startswith('nothing flowered').sum())} | "
                 f"{int((~g.observed).sum())} |\n")

    with open(args.report, "w") as f:
        f.write("".join(L))

    keep = ["TrialCode", "crop", "Year", "state", "region", "panel", "reason", "observed",
            "paddock_ha", "match_rule", "match_rule_new", "dist_m", "share_n", "poly_id",
            "edge_dist_m", "n_obs", "gap", "gap_big", "gap_meanmean", "padmean_amp",
            "pad_amp", "pad_peak", "pad_base", "pad_peak_doy", "pad_n_flower_obs",
            "pad_max_gap_d", "pad_thr", "pad_detected", "pad_amp_rank",
            "win_amp", "win_peak", "win_base", "win_peak_doy", "win_thr", "win_detected",
            "win_amp_rank"]
    csv = os.path.join(args.outdir, "canola_flowering_audit_SENSITIVE.csv")
    can[[c for c in keep if c in can.columns]].sort_values(
        ["reason", "pad_amp"]).to_csv(csv, index=False)

    draw(can, ts, os.path.join(args.outdir, "canola_no_flowering_SENSITIVE.png"))
    print("".join(L))
    print(f"\n-> {args.report}\n-> {csv}")


def draw(can, ts, png):
    """Window vs paddock amplitude, and the traces of the paddocks that fail."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))
    ax = axes[0]
    colours = {"detected": "#BBBBBB",
               "paddock is not canola outside the trial": "#D55E00",
               "nothing flowered anywhere (window and paddock both flat)": "#0072B2",
               "weak everywhere (window elevated but below threshold)": "#009E73",
               "unobservable (cloud/no scenes in the flowering window)": "#CC79A7"}
    for k, c in colours.items():
        g = can[can.reason == k]
        if not len(g):
            continue
        ax.scatter(g.win_amp, g.pad_amp, s=13, c=c, alpha=0.75, lw=0,
                   label=f"{k.split('(')[0].strip()} ({len(g)})")
    lim = np.nanpercentile(np.concatenate([can.win_amp.values, can.pad_amp.values]), 99.5)
    ax.plot([0, lim], [0, lim], color="k", lw=0.8, ls="--")
    ax.set_xlabel("window amplitude — the trial itself (CFI x10000)")
    ax.set_ylabel("paddock amplitude — the field (CFI x10000)")
    ax.set_title("Below the diagonal = the trial flowers and its field does not", fontsize=10)
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    ax.grid(alpha=0.2, lw=0.5)

    ax = axes[1]
    grid = np.arange(120, 340, 5)
    for k, c in colours.items():
        codes = can.loc[can.reason == k, "TrialCode"]
        if not len(codes):
            continue
        rows = []
        for tc, g in ts[ts.TrialCode.isin(set(codes))].groupby("TrialCode"):
            g = g.sort_values("doy").dropna(subset=["cfi_pad_median"])
            if len(g) < 3:
                continue
            rows.append(np.interp(grid, g.doy, g.cfi_pad_median * REFL_SCALE,
                                  left=np.nan, right=np.nan))
        if rows:
            ax.plot(grid, np.nanmedian(np.vstack(rows), axis=0), color=c, lw=1.8,
                    label=f"{k.split('(')[0].strip()} ({len(rows)})")
    ax.axvspan(*FLOWER, color="#E69F00", alpha=0.12, lw=0)
    ax.set_xlabel("day-of-year")
    ax.set_ylabel("paddock-median CFI (x10000)")
    ax.set_title("Median paddock trace by diagnosis; shaded = flowering window", fontsize=10)
    ax.legend(fontsize=7, frameon=False)
    ax.grid(alpha=0.2, lw=0.5)
    fig.suptitle("Canola paddocks that show no flowering signature — and why",
                 fontsize=13, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(png, dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    main()
