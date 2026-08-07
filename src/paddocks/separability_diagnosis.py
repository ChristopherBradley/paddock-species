#!/usr/bin/env python3
"""
Why does canola/non-canola separability swing so much between year x state panels?

Two competing explanations, and they imply opposite next steps:
  * DATA QUALITY — cloud gaps over a 2-4 week flowering event, thin samples, bad paddock
    matches, or a state so wide that its flowering dates smear. Fixable by better data.
  * REAL PHENOLOGY — some seasons genuinely have a weaker or shifted canola signature
    (drought years suppress flowering, and canola separability is known to be drought
    sensitive). Not fixable by better data; the model has to carry it.

This scores every panel's separability (AUC of max CFI in the flowering window, canola vs
everything else) and regresses it against measurable causes of each kind, so the answer is a
ranked table rather than an impression.

    python3 separability_diagnosis.py --ts "…/ts_v2/*_SENSITIVE.csv" \
        --rows …/crop_heatmaps/cfi_heatmap_ALL_rows_SENSITIVE.csv \
        --labeled …/nvt_trials_labeled.csv --out output/SEPARABILITY_DIAGNOSIS.md

Aggregate output only — no TrialCodes — so the report is committable.
"""
import argparse
import glob

import numpy as np
import pandas as pd

FLOWER = (200, 300)      # calendar DOY window holding the canola peak (median 251)


def auc(pos, neg):
    """Mann-Whitney AUC. 0.5 = no separation, 1.0 = perfect."""
    if len(pos) < 4 or len(neg) < 4:
        return np.nan
    a = np.concatenate([pos, neg])
    r = pd.Series(a).rank().values
    return (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", nargs="+", required=True)
    ap.add_argument("--rows", required=True, help="cfi_heatmap_ALL_rows csv (the kept set)")
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = pd.read_csv(args.rows).drop_duplicates("TrialCode")
    lab = pd.read_csv(args.labeled).drop_duplicates("TrialCode")
    files = sorted({f for p in args.ts for f in glob.glob(p)})
    ts = pd.concat((pd.read_csv(f, parse_dates=["time"]) for f in files), ignore_index=True)
    ts = ts.drop_duplicates(["TrialCode", "time"])
    ts = ts[ts.TrialCode.isin(set(rows.TrialCode))].copy()
    ts["doy"] = ts.time.dt.dayofyear
    ts = ts[ts.n_clear_px / ts.n_px_paddock.clip(lower=1) >= 0.5]

    w = ts[(ts.doy >= FLOWER[0]) & (ts.doy <= FLOWER[1])]
    peak = w.groupby("TrialCode").cfi_pad_median.max().rename("peak")
    nobs = w.groupby("TrialCode").size().rename("n_flower_obs")

    # Largest clear-observation gap inside the flowering window. A 2-4 week flowering event
    # inside a 25-day gap is simply not sampled, so "no peak" there is unfalsifiable — the
    # single most important data-quality candidate.
    def maxgap(g):
        d = np.sort(g.doy.values)
        if len(d) < 2:
            return FLOWER[1] - FLOWER[0]
        return int(np.max(np.diff(np.concatenate([[FLOWER[0]], d, [FLOWER[1]]]))))
    gap = w.groupby("TrialCode").apply(maxgap).rename("max_gap_d")

    # Season vigour, as a drought proxy: a failed season has a low NDVI amplitude regardless
    # of crop, and that is a REAL effect, not a measurement one.
    amp = (ts.groupby("TrialCode").ndvi_pad_median.quantile(0.95)
           - ts.groupby("TrialCode").ndvi_pad_median.quantile(0.05)).rename("ndvi_amp")

    d = (rows[["TrialCode", "crop", "crop_group", "Year", "state", "paddock_ha",
               "match_rule", "compactness"]]
         .join(peak, on="TrialCode").join(nobs, on="TrialCode")
         .join(gap, on="TrialCode").join(amp, on="TrialCode")
         .merge(lab[["TrialCode", "lat", "lon", "sow"]], on="TrialCode", how="left"))
    d = d.dropna(subset=["peak"])
    d["sow_doy"] = pd.to_datetime(d.sow).dt.dayofyear
    d["contains"] = d.match_rule.astype(str).str.startswith("contains")

    panels = []
    for (yr, st), g in d.groupby(["Year", "state"]):
        can = g[g.crop_group == "Canola"]
        oth = g[g.crop_group != "Canola"]
        a = auc(can.peak.values, oth.peak.values)
        if np.isnan(a):
            continue
        panels.append({
            "panel": f"{yr} {st}", "Year": yr, "state": st, "auc": a,
            "n_canola": len(can), "n_other": len(oth),
            "med_flower_obs": g.n_flower_obs.median(),
            "med_max_gap_d": g.max_gap_d.median(),
            "frac_gap_over_21d": (g.max_gap_d > 21).mean(),
            "frac_contains": g.contains.mean(),
            "med_paddock_ha": g.paddock_ha.median(),
            "med_compactness": g.compactness.median(),
            "lat_spread_deg": g.lat.std(),
            "lon_spread_deg": g.lon.std(),
            "sow_iqr_d": g.sow_doy.quantile(.75) - g.sow_doy.quantile(.25),
            "med_ndvi_amp": g.ndvi_amp.median(),
            "canola_peak_med": can.peak.median(),
            "other_peak_med": oth.peak.median(),
        })
    P = pd.DataFrame(panels).sort_values("auc", ascending=False)

    drivers = ["n_canola", "med_flower_obs", "med_max_gap_d", "frac_gap_over_21d",
               "frac_contains", "med_paddock_ha", "med_compactness", "lat_spread_deg",
               "lon_spread_deg", "sow_iqr_d", "med_ndvi_amp"]
    KIND = {"n_canola": "sampling", "med_flower_obs": "data quality",
            "med_max_gap_d": "data quality", "frac_gap_over_21d": "data quality",
            "frac_contains": "data quality", "med_paddock_ha": "data quality",
            "med_compactness": "data quality", "lat_spread_deg": "design",
            "lon_spread_deg": "design", "sow_iqr_d": "design",
            "med_ndvi_amp": "real (season vigour)"}
    corr = (P[drivers + ["auc"]].corr(method="spearman")["auc"].drop("auc")
            .rename("spearman_r").to_frame())
    corr["kind"] = [KIND[i] for i in corr.index]
    # 32 panels is a small n for a correlation, and reading a rank order off point estimates
    # alone is how a +0.41 gets written down as a finding when its interval spans zero.
    rb = np.random.default_rng(1)
    lo, hi = [], []
    for c in corr.index:
        b = [P.sample(len(P), replace=True, random_state=int(rb.integers(1e9)))[[c, "auc"]]
             .corr(method="spearman").iloc[0, 1] for _ in range(2000)]
        q = np.nanpercentile(b, [2.5, 97.5])
        lo.append(q[0]); hi.append(q[1])
    corr["ci_lo"], corr["ci_hi"] = lo, hi
    corr["excludes_zero"] = (corr.ci_lo > 0) | (corr.ci_hi < 0)
    corr["abs"] = corr.spearman_r.abs()
    corr = corr.sort_values("abs", ascending=False).drop(columns="abs")

    # How much of the swing is just small samples? Compare the observed spread in AUC against
    # what resampling the SAME pooled distribution at each panel's n would produce. If the two
    # match, there is no panel effect left to explain — that is the null worth ruling out
    # before attributing anything to cloud or drought.
    rng = np.random.default_rng(0)
    pooled_c = d[d.crop_group == "Canola"].peak.values
    pooled_o = d[d.crop_group != "Canola"].peak.values
    sim = []
    for _, r in P.iterrows():
        s = [auc(rng.choice(pooled_c, int(r.n_canola)), rng.choice(pooled_o, int(r.n_other)))
             for _ in range(200)]
        sim.append(np.std(s))
    null_sd = float(np.mean(sim))
    obs_sd = float(P.auc.std())

    with open(args.out, "w") as f:
        f.write("# Why separability swings between year x state panels\n\n")
        f.write(f"Separability = AUC of max CFI in DOY {FLOWER[0]}-{FLOWER[1]}, canola vs "
                f"every other crop, within a panel. {len(P)} panels, "
                f"{len(d)} paddocks.\n\n")
        f.write(f"- AUC range **{P.auc.min():.2f} to {P.auc.max():.2f}**, "
                f"median {P.auc.median():.2f}, sd {obs_sd:.3f}\n")
        f.write(f"- sd expected from SAMPLING ALONE at these panel sizes: **{null_sd:.3f}**\n")
        share = min(1.0, (null_sd ** 2) / (obs_sd ** 2))
        f.write(f"- so sampling noise accounts for about **{share:.0%}** of the observed "
                f"variance; the rest is a real panel effect\n\n")
        f.write("## What predicts a panel's separability\n\n")
        f.write("Spearman correlation against panel AUC, ranked by strength.\n\n")
        f.write("| driver | kind | spearman r | 95% CI | excludes 0 |\n"
                "|---|---|---|---|---|\n")
        for i, r in corr.iterrows():
            f.write(f"| `{i}` | {r['kind']} | {r['spearman_r']:+.2f} | "
                    f"[{r['ci_lo']:+.2f}, {r['ci_hi']:+.2f}] | "
                    f"{'yes' if r['excludes_zero'] else 'no'} |\n")
        f.write("\n## Panels, best to worst\n\n")
        f.write("| panel | AUC | n canola | n other | med flower obs | med max gap (d) | "
                "lat spread | med NDVI amp |\n|---|---|---|---|---|---|---|---|\n")
        for _, r in P.iterrows():
            f.write(f"| {r['panel']} | {r['auc']:.2f} | {int(r['n_canola'])} | "
                    f"{int(r['n_other'])} | {r['med_flower_obs']:.0f} | "
                    f"{r['med_max_gap_d']:.0f} | {r['lat_spread_deg']:.2f} | "
                    f"{r['med_ndvi_amp']:.2f} |\n")
    P.to_csv(args.out.replace(".md", "_panels.csv"), index=False)
    print(corr.to_string())
    print(f"\nobserved AUC sd {obs_sd:.3f} vs sampling-only {null_sd:.3f} "
          f"=> sampling explains ~{share:.0%} of variance")
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
