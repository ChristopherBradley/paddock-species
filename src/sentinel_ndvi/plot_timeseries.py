#!/usr/bin/env python3
"""
Visual check: are Canola and Wheat separable by CFI / NDVI over the season?

Draws a random balanced sample of trials and plots both indices against days-after-sowing,
as line traces and as heatmaps.

    python3 plot_timeseries.py \
        --ts-dir /scratch/xe2/cb8590/paddock-species-data/derived/sentinel_ts \
        --outdir /scratch/xe2/cb8590/paddock-species-data/derived/figures \
        --n-per-crop 10

SENSITIVE DATA. Trial labels in the figure are anonymised (C01..., W01...) and the output
goes to the gitignored derived/ tree on /scratch — never into the repo, and never published
to any external service. The label -> TrialCode mapping is written beside the figure, in the
same protected directory, so results stay traceable.

Sampling is seeded, so the same --seed reproduces the same trials. Traces are shown on a
common days-after-sowing axis: calendar dates are not comparable across trials sown weeks
apart, and DAS is also the axis the flowering window is defined on.
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

CROP_COLOUR = {"Canola": "#E69F00", "Wheat": "#0072B2"}   # colourblind-safe pair
GRID = np.arange(0, 245, 5)                                # common DAS axis


def load(ts_dir, min_clear_frac):
    files = sorted(glob.glob(os.path.join(ts_dir, "*_ts.csv")))
    if not files:
        raise SystemExit(f"no *_ts.csv in {ts_dir}")
    ts = pd.concat((pd.read_csv(f, parse_dates=["time"]) for f in files), ignore_index=True)
    for need in ("cfi_win_mean", "sow"):
        if need not in ts.columns:
            raise SystemExit(f"time series lack '{need}' — re-run extract_ndvi.py")
    ts["sow"] = pd.to_datetime(ts["sow"])
    ts = ts[ts["n_clear_px"] / ts["n_px_total"] >= min_clear_frac].copy()
    ts["das"] = (ts["time"] - ts["sow"]).dt.days
    return ts


def pick(ts, n_per_crop, seed, min_obs):
    counts = ts.groupby(["TrialCode", "crop"]).size().rename("n").reset_index()
    counts = counts[counts["n"] >= min_obs]
    rng = np.random.default_rng(seed)
    out = {}
    for crop in ("Canola", "Wheat"):
        pool = counts[counts["crop"] == crop]["TrialCode"].to_numpy()
        if len(pool) < n_per_crop:
            raise SystemExit(f"only {len(pool)} {crop} trials with >={min_obs} obs")
        out[crop] = rng.choice(pool, n_per_crop, replace=False)
    return out


def resample(g, col):
    """Interpolate one trial onto the common DAS grid (no extrapolation)."""
    g = g.sort_values("das").dropna(subset=[col])
    if len(g) < 3:
        return np.full(GRID.shape, np.nan)
    v = np.interp(GRID, g["das"], g[col], left=np.nan, right=np.nan)
    v[(GRID < g["das"].min()) | (GRID > g["das"].max())] = np.nan
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts-dir", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--n-per-crop", type=int, default=10)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--min-obs", type=int, default=30)
    ap.add_argument("--min-clear-frac", type=float, default=0.5)
    ap.add_argument("--flower", type=int, nargs=2, default=(70, 140),
                    help="candidate flowering window, days after sowing")
    args = ap.parse_args()

    ts = load(args.ts_dir, args.min_clear_frac)
    chosen = pick(ts, args.n_per_crop, args.seed, args.min_obs)
    os.makedirs(args.outdir, exist_ok=True)

    labels, mapping, mats = [], [], {"cfi_win_mean": [], "ndvi_win_mean": []}
    for crop, pre in (("Canola", "C"), ("Wheat", "W")):
        for i, tc in enumerate(chosen[crop], 1):
            lab = f"{pre}{i:02d}"
            labels.append((lab, crop))
            mapping.append({"label": lab, "crop": crop, "TrialCode": tc})
            g = ts[ts["TrialCode"] == tc]
            for col in mats:
                mats[col].append(resample(g, col))

    fig, axes = plt.subplots(2, 2, figsize=(15, 10),
                             gridspec_kw={"height_ratios": [1, 1.25]})
    titles = {"cfi_win_mean": "CFI  (Canola Flower Index)",
              "ndvi_win_mean": "NDVI  (greenness)"}

    # --- row 1: line traces -------------------------------------------------------------
    for ax, col in zip(axes[0], ("cfi_win_mean", "ndvi_win_mean")):
        for (lab, crop), row in zip(labels, mats[col]):
            ax.plot(GRID, row, color=CROP_COLOUR[crop], alpha=0.55, lw=1.3)
        for crop in ("Canola", "Wheat"):
            sel = [r for (l, c), r in zip(labels, mats[col]) if c == crop]
            ax.plot(GRID, np.nanmean(np.vstack(sel), axis=0),
                    color=CROP_COLOUR[crop], lw=3.2, label=f"{crop} mean")
        ax.axvspan(*args.flower, color="grey", alpha=0.13, zorder=0)
        ax.set_title(titles[col], fontsize=12, weight="bold")
        ax.set_xlabel("days after sowing")
        ax.set_ylabel(titles[col].split()[0])
        ax.grid(alpha=0.25)
        ax.legend(loc="upper left", fontsize=9)

    # --- row 2: heatmaps ----------------------------------------------------------------
    for ax, col, cmap in zip(axes[1], ("cfi_win_mean", "ndvi_win_mean"),
                             ("YlOrBr", "YlGn")):
        M = np.vstack(mats[col])
        im = ax.imshow(M, aspect="auto", cmap=cmap, interpolation="nearest",
                       extent=[GRID[0], GRID[-1], len(labels) - 0.5, -0.5])
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels([l for l, _ in labels], fontsize=8)
        for tick, (_, crop) in zip(ax.get_yticklabels(), labels):
            tick.set_color(CROP_COLOUR[crop])
        ax.axhline(args.n_per_crop - 0.5, color="black", lw=2)
        for x in args.flower:
            ax.axvline(x, color="black", ls="--", lw=1.1, alpha=0.8)
        ax.set_xlabel("days after sowing")
        ax.set_title(f"{titles[col]} — per trial", fontsize=11)
        fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)

    fig.suptitle(
        f"Canola (n={args.n_per_crop}) vs Wheat (n={args.n_per_crop}) — Sentinel-2 season "
        f"traces\nshaded/dashed = candidate flowering window {args.flower[0]}-"
        f"{args.flower[1]} days after sowing",
        fontsize=13, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    png = os.path.join(args.outdir, "cfi_ndvi_timeseries_SENSITIVE.png")
    fig.savefig(png, dpi=150)
    pd.DataFrame(mapping).to_csv(
        os.path.join(args.outdir, "cfi_ndvi_timeseries_trial_map_SENSITIVE.csv"), index=False)
    print(f"wrote {png}")

    # Numbers behind the picture, so the visual impression can be checked against a stat.
    print(f"\nmax CFI within {args.flower[0]}-{args.flower[1]} DAS (this sample):")
    w = ts[(ts["das"] >= args.flower[0]) & (ts["das"] <= args.flower[1])]
    for crop in ("Canola", "Wheat"):
        pk = w[w["TrialCode"].isin(chosen[crop])].groupby("TrialCode")["cfi_win_mean"].max()
        print(f"  {crop:7} n={len(pk):2d}  median={pk.median():.4f}  "
              f"min={pk.min():.4f}  max={pk.max():.4f}")


if __name__ == "__main__":
    main()
