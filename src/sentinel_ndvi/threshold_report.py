#!/usr/bin/env python3
"""
Stage 2c: evidence for choosing the phenology_check.py thresholds.

The README ships NDVI_AMP_MIN / NDYI_FLOWER_MIN as placeholders to be "tuned on the
smoke-test chunk". A handful of trials cannot support that choice, so this script reports
the actual distributions once the fleet has run, and — because the trial crop is known —
scores how well NDYI separates Canola from Wheat.

    python3 threshold_report.py \
        --ts-dir /scratch/xe2/cb8590/paddock-species-data/derived/sentinel_ts \
        --out    /scratch/xe2/cb8590/paddock-species-data/derived/threshold_report.md

This REPORTS, it does not auto-apply: the thresholds stay human-set constants in
phenology_check.py. Read the separability table before changing them.

Important caveat on the NDYI figure: it is a separability score, NOT an accuracy. The
crop label is the NVT trial's own crop, and the whole point of Stage 2 is that the
paddock around the trial may not match that label. Trials where the paddock genuinely
grew something else are counted here as errors, so a perfect score is not expected and
not desirable — treat this as "how much signal is there", not "how right is the label".
"""
import argparse
import os

import numpy as np
import pandas as pd

from phenology_check import (MIN_CLEAR_FRAC, NDVI_AMP_MIN, NDYI_FLOWER_MIN, summarise,
                             verdict)


def per_trial_metrics(ts):
    rows = []
    for (tc, crop), g in ts.groupby(["TrialCode", "crop"]):
        m = summarise(g)
        if m is None:
            rows.append({"TrialCode": tc, "crop": crop, "too_few_obs": True})
            continue
        rows.append({"TrialCode": tc, "crop": crop, "too_few_obs": False, **m})
    return pd.DataFrame(rows)


def q(s, name):
    s = s.dropna()
    if s.empty:
        return f"| {name} | – | – | – | – | – | – |"
    p = [s.quantile(x) for x in (0.05, 0.25, 0.50, 0.75, 0.95)]
    return (f"| {name} | {len(s)} | " + " | ".join(f"{v:.3f}" for v in p) +
            f" | {s.mean():.3f} |")


def separability(met, lo=0.0, hi=0.6, step=0.005):
    """Youden's J for 'NDYI peak >= t => Canola' over the labelled trials."""
    d = met[(~met["too_few_obs"]) & met["crop"].isin(["Canola", "Wheat"])].dropna(
        subset=["ndyi_peak"])
    can = d.loc[d["crop"] == "Canola", "ndyi_peak"].to_numpy()
    whe = d.loc[d["crop"] == "Wheat", "ndyi_peak"].to_numpy()
    if can.size == 0 or whe.size == 0:
        return None, pd.DataFrame()
    rows = []
    for t in np.arange(lo, hi + 1e-9, step):
        tpr = float((can >= t).mean())          # canola correctly flagged as flowering
        fpr = float((whe >= t).mean())          # wheat wrongly flagged as flowering
        rows.append({"threshold": round(float(t), 4), "canola_flagged": tpr,
                     "wheat_flagged": fpr, "youden_j": tpr - fpr})
    tab = pd.DataFrame(rows)
    return tab.loc[tab["youden_j"].idxmax()], tab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-clear-frac", type=float, default=MIN_CLEAR_FRAC)
    args = ap.parse_args()

    import glob
    files = sorted(glob.glob(os.path.join(args.ts_dir, "*_ts.csv")))
    if not files:
        raise SystemExit(f"no *_ts.csv found in {args.ts_dir}")
    ts = pd.concat((pd.read_csv(f, parse_dates=["time"]) for f in files), ignore_index=True)
    n_before = len(ts)
    ts = ts[ts["n_clear_px"] / ts["n_px_total"] >= args.min_clear_frac].reset_index(drop=True)

    met = per_trial_metrics(ts)
    best, tab = separability(met)

    L = []
    L.append("# Stage-2 threshold evidence\n")
    L.append(f"- time-series files: **{len(files)}**")
    L.append(f"- scenes: **{len(ts)}** kept of {n_before} "
             f"(clear-frac >= {args.min_clear_frac})")
    L.append(f"- trials with metrics: **{int((~met['too_few_obs']).sum())}** "
             f"({int(met['too_few_obs'].sum())} had <5 clear observations)")
    L.append(f"- current constants: `NDVI_AMP_MIN={NDVI_AMP_MIN}`, "
             f"`NDYI_FLOWER_MIN={NDYI_FLOWER_MIN}`\n")

    L.append("## Distributions\n")
    L.append("| metric | n | p05 | p25 | p50 | p75 | p95 | mean |")
    L.append("|---|---|---|---|---|---|---|---|")
    ok = met[~met["too_few_obs"]]
    for crop in sorted(ok["crop"].dropna().unique()):
        s = ok[ok["crop"] == crop]
        L.append(q(s["ndvi_amp"], f"ndvi_amp — {crop}"))
    for crop in sorted(ok["crop"].dropna().unique()):
        s = ok[ok["crop"] == crop]
        L.append(q(s["ndyi_peak"], f"ndyi_peak — {crop}"))
    L.append(q(ok["n_obs"].astype(float), "n_obs (all)"))

    L.append("\n## How many trials each NDVI_AMP_MIN would reject\n")
    L.append("| NDVI_AMP_MIN | trials rejected | % |")
    L.append("|---|---|---|")
    for t in (0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50):
        n = int((ok["ndvi_amp"] < t).sum())
        L.append(f"| {t:.2f} | {n} | {100.0 * n / max(len(ok), 1):.1f}% |")

    L.append("\n## NDYI separability (Canola vs Wheat)\n")
    L.append("Rule scored: `ndyi_peak >= t` predicts Canola. See the caveat in the module "
             "docstring — the trial crop is the *claimed* label, so this is a signal-strength "
             "measure, not an accuracy.\n")
    if best is None:
        L.append("_Not computable: need both Canola and Wheat trials with metrics._")
    else:
        L.append(f"**Best Youden's J = {best['youden_j']:.3f} at t = {best['threshold']:.3f}** "
                 f"(flags {best['canola_flagged']:.1%} of Canola, "
                 f"{best['wheat_flagged']:.1%} of Wheat). "
                 f"Shipped default is {NDYI_FLOWER_MIN}.\n")
        L.append("| threshold | Canola flagged | Wheat flagged | Youden J |")
        L.append("|---|---|---|---|")
        for t in (0.06, 0.08, 0.10, 0.12, 0.14, 0.16, 0.20, 0.25, 0.30):
            r = tab.iloc[(tab["threshold"] - t).abs().idxmin()]
            L.append(f"| {r['threshold']:.3f} | {r['canola_flagged']:.1%} | "
                     f"{r['wheat_flagged']:.1%} | {r['youden_j']:.3f} |")

    # What the choice actually does to the verdicts — the number a human needs to see.
    L.append("\n## Verdict mix vs NDYI_FLOWER_MIN\n")
    L.append(f"(NDVI_AMP_MIN = {NDVI_AMP_MIN}; REJECTED is unaffected by the NDYI threshold)\n")
    L.append("| NDYI_FLOWER_MIN | Canola CONF | Canola UNC | Wheat CONF | Wheat UNC |")
    L.append("|---|---|---|---|---|")
    for t in (0.12, 0.16, 0.20, 0.24, 0.28):
        cnt = {}
        for _, r in ok.iterrows():
            v = verdict(r["crop"], r, NDVI_AMP_MIN, t)
            cnt[(r["crop"], v)] = cnt.get((r["crop"], v), 0) + 1
        L.append(f"| {t:.2f} | {cnt.get(('Canola','CONFIRMED'),0)} | "
                 f"{cnt.get(('Canola','UNCERTAIN'),0)} | {cnt.get(('Wheat','CONFIRMED'),0)} | "
                 f"{cnt.get(('Wheat','UNCERTAIN'),0)} |")

    # Sanity check on the window design: is the corner pixel a better discriminator than
    # the 200 m window mean? (The trial GPS is a paddock CORNER, so the window may include
    # a lot of non-trial land.) Answered empirically rather than assumed.
    if {"ndyi_corner", "ndyi_win_mean"}.issubset(ts.columns):
        def _peak(g, col):
            v = g[col].to_numpy(); v = v[~np.isnan(v)]
            return np.nan if v.size < 5 else np.nanmax(v) - np.nanpercentile(v, 20)
        rows = [{"crop": c, "win": _peak(g, "ndyi_win_mean"), "corner": _peak(g, "ndyi_corner")}
                for (_, c), g in ts.groupby(["TrialCode", "crop"])]
        cmp_df = pd.DataFrame(rows).dropna()
        L.append("\n## Window mean vs corner pixel (NDYI discriminator)\n")
        L.append("| metric | best t | Youden J | Canola flagged | Wheat flagged |")
        L.append("|---|---|---|---|---|")
        for col in ("win", "corner"):
            can = cmp_df.loc[cmp_df.crop == "Canola", col].to_numpy()
            whe = cmp_df.loc[cmp_df.crop == "Wheat", col].to_numpy()
            grid = np.arange(0.0, 0.8, 0.005)
            js = [(can >= t).mean() - (whe >= t).mean() for t in grid]
            i = int(np.argmax(js))
            L.append(f"| {col} | {grid[i]:.3f} | {js[i]:.3f} | "
                     f"{(can >= grid[i]).mean():.1%} | {(whe >= grid[i]).mean():.1%} |")

    text = "\n".join(L) + "\n"
    with open(args.out, "w") as fh:
        fh.write(text)
    print(text)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
