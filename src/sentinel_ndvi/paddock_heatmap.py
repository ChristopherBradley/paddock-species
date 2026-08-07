#!/usr/bin/env python3
"""
PaddockTS-style clustered CFI heatmap for NVT trial sites.

Mirrors the figure style used in PaddockTS (dendrogram, calendar x-axis, viridis, CFI on
the raw-DN scale) so the two are directly comparable, but rows are NVT trials rather than
segmented paddocks — and each row's true crop is known, which the paddock version cannot
say. Crop is shown only in the row label colour, never used to order the rows, so the
clustering is free to disagree with the label. Rows that cluster with the wrong crop are
the interesting ones: those are candidate label/paddock mismatches.

    python3 paddock_heatmap.py \
        --ts-dir  /scratch/.../derived/sentinel_ts \
        --labeled /scratch/.../derived/nvt_trials_labeled.csv \
        --outdir  /scratch/.../derived/figures \
        --year 2020 --state NSW

Why restrict to one season and region: flowering spread is IQR 26 d on calendar
day-of-year across the whole dataset, so pooling seasons and states smears the flowering
band into invisibility regardless of how the pixels are aggregated. That, not the colour
scale, was the main reason earlier pooled heatmaps looked washed out compared with the
PaddockTS ones.

SENSITIVE: labels anonymised, output stays on /scratch, mapping written alongside.
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                      # noqa: E402
from matplotlib.gridspec import GridSpec             # noqa: E402
from scipy.cluster.hierarchy import dendrogram, leaves_list, linkage  # noqa: E402

CROP_COLOUR = {
    "Canola": "#E69F00", "Wheat": "#0072B2", "Barley": "#009E73", "Lupin": "#CC79A7",
    "Chickpea": "#D55E00", "Oat": "#56B4E9", "Faba Bean": "#8C564B",
    "Field Pea": "#7F7F7F", "Lentil": "#BCBD22",
}
REFL_SCALE = 10000.0   # CFI on raw-DN scale, to match PaddockTS values


def load(ts_dir, labeled, min_clear_frac):
    files = sorted(glob.glob(os.path.join(ts_dir, "*_ts.csv")))
    if not files:
        raise SystemExit(f"no *_ts.csv in {ts_dir}")
    ts = pd.concat((pd.read_csv(f, parse_dates=["time"]) for f in files), ignore_index=True)
    if "cfi_win_mean" not in ts.columns:
        raise SystemExit("time series lack cfi_win_mean — re-run extract_ndvi.py")
    ts["sow"] = pd.to_datetime(ts["sow"])
    ts = ts[ts["n_clear_px"] / ts["n_px_total"] >= min_clear_frac].copy()
    ts["doy"] = ts["time"].dt.dayofyear
    lab = pd.read_csv(labeled)[["TrialCode", "state", "region", "Year"]].drop_duplicates("TrialCode")
    return ts.merge(lab, on="TrialCode", how="left")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts-dir", required=True)
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--state")
    ap.add_argument("--region")
    ap.add_argument("--crops", nargs="*", help="restrict to these crops")
    ap.add_argument("--max-rows", type=int, default=45)
    ap.add_argument("--min-obs", type=int, default=20)
    ap.add_argument("--min-clear-frac", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--metric", default="cfi_win_mean")
    args = ap.parse_args()

    ts = load(args.ts_dir, args.labeled, args.min_clear_frac)
    ts = ts[ts["Year"] == args.year]
    if args.state:
        ts = ts[ts["state"] == args.state]
    if args.region:
        ts = ts[ts["region"] == args.region]
    if args.crops:
        ts = ts[ts["crop"].isin(args.crops)]
    if ts.empty:
        raise SystemExit("no trials after filters")

    counts = ts.groupby(["TrialCode", "crop"]).size().rename("n").reset_index()
    counts = counts[counts["n"] >= args.min_obs]
    if counts.empty:
        raise SystemExit(f"no trials with >= {args.min_obs} clear observations")
    if len(counts) > args.max_rows:            # balanced across crops, seeded
        rng = np.random.default_rng(args.seed)
        take = max(1, args.max_rows // counts["crop"].nunique())
        counts = (counts.groupby("crop", group_keys=False)
                  .apply(lambda g: g.sample(min(len(g), take), random_state=args.seed)))

    grid = np.arange(int(ts["doy"].min()), int(ts["doy"].max()) + 5, 5)
    rows, labels = [], []
    for _, r in counts.iterrows():
        g = ts[ts["TrialCode"] == r["TrialCode"]].sort_values("doy").dropna(subset=[args.metric])
        if len(g) < 3:
            continue
        v = np.interp(grid, g["doy"], g[args.metric], left=np.nan, right=np.nan)
        v[(grid < g["doy"].min()) | (grid > g["doy"].max())] = np.nan
        rows.append(v * REFL_SCALE)
        labels.append((r["TrialCode"], r["crop"]))
    M = np.vstack(rows)

    # Cluster on the index trace alone — the crop label is deliberately withheld so that
    # agreement between clusters and crops is evidence, not construction.
    Mf = np.where(np.isnan(M), np.nanmean(M), M)
    Z = linkage(Mf, method="average", metric="correlation")
    order = leaves_list(Z)

    fig = plt.figure(figsize=(15, max(6, 0.32 * len(M) + 3)))
    gs = GridSpec(1, 3, width_ratios=[0.16, 1, 0.045], wspace=0.02)
    axd, axh, axc = fig.add_subplot(gs[0]), fig.add_subplot(gs[1]), fig.add_subplot(gs[2])

    dendrogram(Z, orientation="left", ax=axd, no_labels=True, color_threshold=0,
               link_color_func=lambda k: "#444444")
    axd.invert_yaxis(); axd.set_xticks([]); axd.set_yticks([])
    for sp in axd.spines.values():
        sp.set_visible(False)

    im = axh.imshow(M[order], aspect="auto", cmap="viridis", interpolation="nearest",
                    extent=[grid[0], grid[-1], len(M) - 0.5, -0.5])
    axh.set_yticks(range(len(M)))
    axh.set_yticklabels([f"{labels[i][1][:9]}" for i in order], fontsize=7)
    for tick, i in zip(axh.get_yticklabels(), order):
        tick.set_color(CROP_COLOUR.get(labels[i][1], "black"))
    axh.set_xlabel("calendar day-of-year")
    scope = f"{args.year}" + (f", {args.state}" if args.state else "") + \
            (f", {args.region}" if args.region else "")
    axh.set_title(f"NVT trial sites — CFI by day-of-year ({scope})\n"
                  f"rows clustered on the trace only; label colour = actual NVT crop",
                  fontsize=12, weight="bold")
    fig.colorbar(im, cax=axc, label="CFI (raw-DN scale, x10000)")

    os.makedirs(args.outdir, exist_ok=True)
    # The metric belongs in the filename: without it, comparing two estimators over the same
    # year/state silently overwrites the first figure with the second.
    tag = f"{args.year}" + (f"_{args.state}" if args.state else "") + \
          (f"_{args.region.replace(' ', '')}" if args.region else "") + \
          ("" if args.metric == "cfi_win_mean" else f"_{args.metric}")
    png = os.path.join(args.outdir, f"paddock_heatmap_{tag}_SENSITIVE.png")
    fig.savefig(png, dpi=150, bbox_inches="tight")   # GridSpec handles layout
    pd.DataFrame([{"row": int(np.where(order == i)[0][0]), "TrialCode": labels[i][0],
                   "crop": labels[i][1]} for i in range(len(labels))]
                 ).sort_values("row").to_csv(
        os.path.join(args.outdir, f"paddock_heatmap_{tag}_trial_map_SENSITIVE.csv"), index=False)
    print(f"wrote {png}  ({len(M)} trials, {counts['crop'].nunique()} crops)")

    # Does the clustering recover the crop labels? Reported as a number, not left to the eye.
    from scipy.cluster.hierarchy import fcluster
    k = counts["crop"].nunique()
    cl = fcluster(Z, k, criterion="maxclust")
    ct = pd.crosstab(pd.Series([l[1] for l in labels], name="crop"),
                     pd.Series(cl, name="cluster"))
    print("\ncrop x cluster (clustering never saw the crop):")
    print(ct.to_string())
    purity = ct.max(axis=0).sum() / ct.values.sum()
    print(f"\ncluster purity = {purity:.1%}")


if __name__ == "__main__":
    main()
