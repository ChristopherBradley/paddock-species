#!/usr/bin/env python3
"""
Stage 2d: how variable is canola flowering timing, and is it predictable?

Answers three questions that bear directly on how Stage 2 should be built:

  1. Is flowering better aligned by DAYS AFTER SOWING or by CALENDAR day-of-year?
     Whichever is tighter is the axis a heatmap should use, and the axis the
     flowering window should be defined on.
  2. Is the timing predictable from latitude / longitude / season? If it is, the
     window can be shifted per site instead of being one fixed range for all of
     Australia.
  3. How often does cloud simply hide the flowering peak? If a trial has no clear
     observation near its peak, "no flowering detected" is unfalsifiable for that
     trial and it should be excluded rather than counted as evidence.

    python3 flowering_timing.py \
        --ts-dir  /scratch/xe2/cb8590/paddock-species-data/derived/sentinel_ts \
        --labeled /scratch/xe2/cb8590/paddock-species-data/derived/nvt_trials_labeled.csv \
        --out     /scratch/xe2/cb8590/paddock-species-data/derived/flowering_timing.md

Uses only CONFIRMED-canola-like trials (those whose CFI actually peaks) so that
"timing" means the timing of a real event, not the argmax of noise.
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd


def load(ts_dir, labeled, min_clear_frac=0.5):
    files = sorted(glob.glob(os.path.join(ts_dir, "*_ts.csv")))
    ts = pd.concat((pd.read_csv(f, parse_dates=["time"]) for f in files), ignore_index=True)
    ts["sow"] = pd.to_datetime(ts["sow"])
    ts = ts[ts["n_clear_px"] / ts["n_px_total"] >= min_clear_frac].copy()
    ts["das"] = (ts["time"] - ts["sow"]).dt.days
    ts["doy"] = ts["time"].dt.dayofyear
    lab = pd.read_csv(labeled)[["TrialCode", "lat", "lon", "state", "Year"]]
    return ts.merge(lab.drop_duplicates("TrialCode"), on="TrialCode", how="left")


def peaks(ts, crop, cfi_min):
    """Per-trial CFI peak, restricted to trials that actually show a peak."""
    d = ts[ts["crop"] == crop]
    rows = []
    for tc, g in d.groupby("TrialCode"):
        g = g.dropna(subset=["cfi_win_mean"])
        if len(g) < 8:
            continue
        i = int(g["cfi_win_mean"].to_numpy().argmax())
        r = g.iloc[i]
        if r["cfi_win_mean"] < cfi_min:
            continue                      # no flowering event to time
        # gap to the nearest clear observation on either side of the peak
        das = np.sort(g["das"].to_numpy())
        pos = np.searchsorted(das, r["das"])
        gap = np.diff(das).max() if len(das) > 1 else np.nan
        rows.append({"TrialCode": tc, "peak_das": r["das"], "peak_doy": r["doy"],
                     "peak_cfi": r["cfi_win_mean"], "lat": r["lat"], "lon": r["lon"],
                     "state": r["state"], "year": r["Year"], "max_gap_days": gap,
                     "n_obs": len(g)})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts-dir", required=True)
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cfi-min", type=float, default=0.1309)
    args = ap.parse_args()

    ts = load(args.ts_dir, args.labeled)
    can = peaks(ts, "Canola", args.cfi_min)
    whe = peaks(ts, "Wheat", args.cfi_min)

    L = ["# Canola flowering timing: variance and predictability\n",
         f"- canola trials with a CFI peak >= {args.cfi_min}: **{len(can)}**",
         f"- wheat trials that also cross it (false positives): **{len(whe)}**\n"]

    # --- 1. which alignment is tighter? --------------------------------------------------
    L.append("## 1. Days-after-sowing vs calendar day-of-year\n")
    L.append("Lower spread = better alignment axis for a window or a heatmap.\n")
    L.append("| alignment | n | p05 | median | p95 | IQR | std |")
    L.append("|---|---|---|---|---|---|---|")
    for name, col in (("days after sowing", "peak_das"), ("calendar day-of-year", "peak_doy")):
        s = can[col].dropna()
        iqr = s.quantile(0.75) - s.quantile(0.25)
        L.append(f"| {name} | {len(s)} | {s.quantile(0.05):.0f} | {s.median():.0f} | "
                 f"{s.quantile(0.95):.0f} | **{iqr:.0f}** | {s.std():.1f} |")

    das_iqr = (can["peak_das"].quantile(0.75) - can["peak_das"].quantile(0.25))
    doy_iqr = (can["peak_doy"].quantile(0.75) - can["peak_doy"].quantile(0.25))
    better = "calendar day-of-year" if doy_iqr < das_iqr else "days after sowing"
    L.append(f"\n**Tighter axis: {better}** (IQR {min(das_iqr, doy_iqr):.0f} d vs "
             f"{max(das_iqr, doy_iqr):.0f} d).\n")

    # --- 2. predictable from where/when? -------------------------------------------------
    L.append("## 2. Predictability of peak timing\n")
    L.append("| predictor | Pearson r vs peak_doy | r vs peak_das |")
    L.append("|---|---|---|")
    for p in ("lat", "lon", "year"):
        s = can[[p, "peak_doy", "peak_das"]].dropna()
        if len(s) > 10:
            L.append(f"| {p} | {s[p].corr(s['peak_doy']):+.3f} | "
                     f"{s[p].corr(s['peak_das']):+.3f} |")
    L.append("\nBy state (peak day-of-year):\n")
    L.append("| state | n | median DOY | IQR |")
    L.append("|---|---|---|---|")
    for st, g in can.groupby("state"):
        if len(g) >= 10:
            L.append(f"| {st} | {len(g)} | {g['peak_doy'].median():.0f} | "
                     f"{g['peak_doy'].quantile(.75) - g['peak_doy'].quantile(.25):.0f} |")
    L.append("\nBy season (peak day-of-year) — tests whether one fixed window can serve all years:\n")
    L.append("| year | n | median DOY | IQR |")
    L.append("|---|---|---|---|")
    for yr, g in can.groupby("year"):
        if len(g) >= 10:
            L.append(f"| {int(yr)} | {len(g)} | {g['peak_doy'].median():.0f} | "
                     f"{g['peak_doy'].quantile(.75) - g['peak_doy'].quantile(.25):.0f} |")

    # --- 3. does cloud hide the peak? ----------------------------------------------------
    L.append("\n## 3. Observation gaps around flowering\n")
    L.append("Canola flowering lasts ~2-4 weeks. A revisit gap wider than that inside the "
             "flowering window means the peak can be missed entirely — and then 'no flowering "
             "detected' says nothing about the crop.\n")
    fw = ts[(ts["crop"] == "Canola") & (ts["das"].between(100, 200))]
    gaps = []
    for tc, g in fw.groupby("TrialCode"):
        das = np.sort(g["das"].dropna().to_numpy())
        gaps.append({"TrialCode": tc, "n_in_window": len(das),
                     "max_gap": np.diff(das).max() if len(das) > 1 else np.nan})
    gp = pd.DataFrame(gaps)
    L.append(f"- canola trials with observations in 100-200 DAS: **{len(gp)}**")
    L.append(f"- median observations inside that window: **{gp['n_in_window'].median():.0f}**")
    for thr in (14, 21, 28):
        n = int((gp["max_gap"] > thr).sum())
        L.append(f"- trials with a clear-observation gap > {thr} d inside the window: "
                 f"**{n}** ({100 * n / max(len(gp), 1):.1f}%)")
    L.append(f"- trials with fewer than 3 observations in the window: "
             f"**{int((gp['n_in_window'] < 3).sum())}**")

    text = "\n".join(L) + "\n"
    with open(args.out, "w") as fh:
        fh.write(text)
    print(text)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
