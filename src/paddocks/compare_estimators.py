#!/usr/bin/env python3
"""
Does paddock-median CFI separate canola from wheat better than the 200 m corner window?

Reads the paired output of `extract_paddock.py` (both estimators, same trials, same dates)
and reports Youden J for each, plus a PAIRED BOOTSTRAP over trials for the difference.

The bootstrap is the point. A pilot of ~100 trials gives a J with a standard error of
several points, so "0.58 vs 0.535" on its own is not evidence of anything. Resampling trials
and recomputing both estimators on each resample answers the question that actually matters:
is paddock-median better *on the same trials*, more often than not?

    python3 compare_estimators.py --ts .../paddock_ts_SENSITIVE.csv \
        --lo 120 --hi 190 --out .../paddock_vs_window.md

Both estimators are scored IN-SAMPLE here (threshold chosen on the same trials), so the
absolute J values are optimistic — equally so for both, since they share trials, dates and
threshold-selection procedure. This is a paired comparison of estimators, NOT an honest
absolute accuracy. The held-out J = 0.535 baseline was computed on a temporal split over the
full 1,630-trial set and is not directly comparable to these pilot absolutes.
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "sentinel_ndvi"))
from cfi_report import peak_in_window, youden          # noqa: E402

ESTIMATORS = [("cfi_win_mean", "200 m window mean (baseline)"),
              ("cfi_pad_median", "paddock median"),
              ("cfi_pad_mean", "paddock mean")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", required=True)
    ap.add_argument("--lo", type=int, default=120, help="flowering window start, DAS")
    ap.add_argument("--hi", type=int, default=190)
    ap.add_argument("--min-clear-frac", type=float, default=0.5)
    ap.add_argument("--contains-only", action="store_true",
                    help="keep only trials whose point falls inside a paddock")
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--out")
    args = ap.parse_args()

    ts = pd.read_csv(args.ts, parse_dates=["time", "sow"])
    n0 = ts.TrialCode.nunique()
    if args.contains_only:
        ts = ts[ts.match_rule.str.startswith("contains")]
    # Same partial-cloud guard as Stage 2: sparse-clear scenes read systematically low and
    # bias every index in the same direction. Deliberately keyed on the PADDOCK's clear
    # fraction for both estimators — a single shared date filter keeps the comparison paired.
    # Filtering each estimator by its own clear fraction would give them different date sets
    # and reintroduce exactly the confound this script exists to avoid.
    ts = ts[ts["n_clear_px"] / ts["n_px_paddock"] >= args.min_clear_frac]
    ts["das"] = (ts["time"] - ts["sow"]).dt.days

    L = [f"# Paddock median vs 200 m window — CFI canola/wheat separation\n",
         f"Trials: {ts.TrialCode.nunique()} of {n0} "
         f"(clear-frac >= {args.min_clear_frac}"
         + (", contains-only" if args.contains_only else "") + ")",
         f"Flowering window: {args.lo}-{args.hi} days after sowing\n"]

    peaks = {}
    rows = []
    for col, label in ESTIMATORS:
        pk = peak_in_window(ts, col, args.lo, args.hi)
        r = youden(pk, col)
        if r is None:
            L.append(f"- **{label}**: not computable (one crop absent)")
            continue
        peaks[col] = pk.set_index("TrialCode")
        rows.append({"estimator": label, "J": r["J"], "t": r["t"],
                     "canola_flagged": r["canola"], "wheat_flagged": r["wheat"],
                     "n_can": r["n_can"], "n_whe": r["n_whe"]})

    if rows:
        df = pd.DataFrame(rows)
        L.append("| estimator | Youden J | threshold | canola flagged | wheat flagged |")
        L.append("|---|---|---|---|---|")
        for _, r in df.iterrows():
            L.append(f"| {r.estimator} | **{r.J:.3f}** | {r.t:.4f} | "
                     f"{r.canola_flagged:.1%} | {r.wheat_flagged:.1%} |")
        L.append(f"\n(n = {int(df.n_can.iloc[0])} canola, {int(df.n_whe.iloc[0])} wheat)\n")

    # --- Per-year, because pooling years collapses J for EVERY estimator ---
    # Measured on this pilot: window J is 0.400-0.778 within a year but 0.318 pooled. The
    # absolute CFI level shifts between seasons, so one shared threshold cannot serve all of
    # them. This is the same "pooling seasons and regions" effect already identified as cause
    # #1 of the weak heatmap contrast — it applies to the threshold analysis too, and it
    # means pooled numbers must NOT be compared against the per-season held-out J = 0.535.
    ts["year"] = ts["sow"].dt.year
    years = sorted(ts["year"].unique())
    if len(years) > 1:
        L.append("## Per-year Youden J (pooling across years is misleading)\n")
        L.append("| year | n canola | n wheat | " +
                 " | ".join(lbl for _, lbl in ESTIMATORS) + " |")
        L.append("|---|---|---|" + "---|" * len(ESTIMATORS))
        per_year = {c: [] for c, _ in ESTIMATORS}
        for yr in years:
            g = ts[ts["year"] == yr]
            cells, nc, nw = [], 0, 0
            for col, _ in ESTIMATORS:
                pk = peak_in_window(g, col, args.lo, args.hi)
                r = youden(pk, col)
                cells.append(f"{r['J']:.3f}" if r else "—")
                if r:
                    per_year[col].append(r["J"])
                    nc, nw = r["n_can"], r["n_whe"]
            L.append(f"| {yr} | {nc} | {nw} | " + " | ".join(cells) + " |")
        L.append("| **mean** | | | " +
                 " | ".join(f"**{np.mean(per_year[c]):.3f}**" for c, _ in ESTIMATORS) + " |")
        L.append("")

    # Paired bootstrap: resample TRIALS, recompute both estimators on each resample.
    base = "cfi_win_mean"
    if base in peaks:
        common = None
        for col in peaks:
            idx = set(peaks[col].index)
            common = idx if common is None else (common & idx)
        common = sorted(common)
        crop = peaks[base].loc[common, "crop"].to_numpy()
        vals = {c: peaks[c].loc[common, c].to_numpy() for c in peaks}

        def j_of(v, y):
            can, whe = v[y == "Canola"], v[y == "Wheat"]
            can, whe = can[~np.isnan(can)], whe[~np.isnan(whe)]
            if can.size == 0 or whe.size == 0:
                return np.nan
            grid = np.quantile(np.concatenate([can, whe]), np.linspace(0.01, 0.99, 199))
            return float(np.max([(can >= t).mean() - (whe >= t).mean() for t in grid]))

        rng = np.random.default_rng(0)
        n = len(common)
        yr_of = peaks[base].loc[common].join(
            ts.groupby("TrialCode").year.first())["year"].to_numpy()
        # Year-stratified: resample within each season and average the per-season J, so the
        # comparison is not dominated by the cross-season threshold shift documented above.
        blocks = [np.where(yr_of == y)[0] for y in np.unique(yr_of)]

        def j_strat(v, y, idx_blocks):
            js = [j_of(v[b], y[b]) for b in idx_blocks]
            js = [j for j in js if not np.isnan(j)]
            return float(np.mean(js)) if js else np.nan

        L.append(f"## Paired bootstrap ({args.n_boot} resamples of {n} trials)\n")
        L.append("| comparison | median ΔJ | 95% CI | P(better) |")
        L.append("|---|---|---|---|")
        for col, label in ESTIMATORS:
            if col == base or col not in vals:
                continue
            d = np.empty(args.n_boot)
            ds = np.empty(args.n_boot)
            for k in range(args.n_boot):
                s = rng.integers(0, n, n)
                d[k] = j_of(vals[col][s], crop[s]) - j_of(vals[base][s], crop[s])
                # stratified: resample inside each year, keeping season sizes fixed
                sb = [b[rng.integers(0, len(b), len(b))] for b in blocks]
                idx = np.concatenate(sb)
                off, rb = 0, []
                for b in sb:
                    rb.append(np.arange(off, off + len(b)))
                    off += len(b)
                ds[k] = (j_strat(vals[col][idx], crop[idx], rb) -
                         j_strat(vals[base][idx], crop[idx], rb))
            for tag, arr in (("pooled", d), ("**year-stratified**", ds)):
                a = arr[~np.isnan(arr)]
                lo, hi = np.percentile(a, [2.5, 97.5])
                L.append(f"| {label} − baseline ({tag}) | {np.median(a):+.3f} | "
                         f"[{lo:+.3f}, {hi:+.3f}] | {(a > 0).mean():.0%} |")
        L.append("\nΔJ > 0 means the paddock estimator separates the crops better than the "
                 "200 m window on the same trials. A CI spanning 0 means this pilot cannot "
                 "tell them apart — report that rather than picking the larger number.\n")

    # Match quality, since it bounds how far this generalises.
    mr = (ts.groupby("TrialCode").match_rule.first().str.split("+").str[0]
          .str.replace(r"nearest_.*", "nearest", regex=True).value_counts())
    L.append("## Trial-to-paddock matching\n")
    for k, v in mr.items():
        L.append(f"- `{k}`: {v} trials ({v/mr.sum():.0%})")
    ph = ts.groupby("TrialCode").paddock_ha.first()
    L.append(f"\nPaddock area: median {ph.median():.0f} ha "
             f"(p10 {ph.quantile(.1):.0f}, p90 {ph.quantile(.9):.0f})")
    ed = ts.groupby("TrialCode").edge_dist_m.first()
    L.append(f"Trial distance to paddock edge: median {ed.median():.0f} m "
             f"(p10 {ed.quantile(.1):.0f}, p90 {ed.quantile(.9):.0f})")

    text = "\n".join(L)
    print(text)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text + "\n")
        print(f"\n-> {args.out}")


if __name__ == "__main__":
    main()
