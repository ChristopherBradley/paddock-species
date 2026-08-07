#!/usr/bin/env python3
"""
Stage 2c(ii): evaluate the Canola Flower Index (CFI) as the Stage-2 discriminator.

CFI = NDVI * ((Red + Green) + (Green - Blue))     [Tian et al. 2022, Remote Sensing]
as implemented in PaddockTS `Code/indices_etc/indices.py`.

Why CFI rather than the NDYI this pipeline started with: NDYI is pure visible-band
yellowness, so bare and senescing soil scores high. Measured over all 1,630 trials, NDYI
flagged 78% of *wheat* sites at the shipped threshold (Youden J = 0.17, near chance).
CFI multiplies by NDVI, which suppresses soil — the signal only survives where there is
both green biomass and yellowness, i.e. a flowering canopy.

    python3 cfi_report.py \
        --ts-dir /scratch/xe2/cb8590/paddock-species-data/derived/sentinel_ts \
        --out    /scratch/xe2/cb8590/paddock-species-data/derived/cfi_report.md

Two things are measured, not assumed:
  1. Whether restricting to a flowering window beats a whole-season max. CFI rises again
     during senescence (canopy yellows while NDVI is still moderate), so an unrestricted
     max can lock onto the wrong event entirely.
  2. Where the flowering window should sit, by scanning candidate offsets from sowing.

Reports only — thresholds stay human-set in phenology_check.py. As in threshold_report.py,
the Canola/Wheat score is SEPARABILITY, not accuracy: the crop label is what the trial
claims, and Stage 2 exists precisely because the paddock may disagree.
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd

from phenology_check import MIN_CLEAR_FRAC


def load(ts_dir, min_clear_frac):
    files = sorted(glob.glob(os.path.join(ts_dir, "*_ts.csv")))
    if not files:
        raise SystemExit(f"no *_ts.csv found in {ts_dir}")
    ts = pd.concat((pd.read_csv(f, parse_dates=["time"]) for f in files), ignore_index=True)
    missing = [c for c in ("cfi_win_mean", "sow") if c not in ts.columns]
    if missing:
        raise SystemExit(f"time series lack {missing} — these come from the CFI-era "
                         f"extract_ndvi.py; re-run the extraction (see README run order)")
    ts["sow"] = pd.to_datetime(ts["sow"])
    n0 = len(ts)
    ts = ts[ts["n_clear_px"] / ts["n_px_total"] >= min_clear_frac].reset_index(drop=True)
    ts["das"] = (ts["time"] - ts["sow"]).dt.days      # days after sowing
    return ts, len(files), n0


def peak_in_window(ts, col, lo=None, hi=None):
    """Max of `col` per trial, optionally restricted to a days-after-sowing window."""
    d = ts if lo is None else ts[(ts["das"] >= lo) & (ts["das"] <= hi)]
    g = d.groupby(["TrialCode", "crop"])[col].max().reset_index()
    n = d.groupby(["TrialCode", "crop"]).size().rename("n_obs").reset_index()
    return g.merge(n, on=["TrialCode", "crop"])


def youden(df, col):
    can = df.loc[df["crop"] == "Canola", col].dropna().to_numpy()
    whe = df.loc[df["crop"] == "Wheat", col].dropna().to_numpy()
    if can.size == 0 or whe.size == 0:
        return None
    grid = np.quantile(np.concatenate([can, whe]), np.linspace(0.01, 0.99, 199))
    js = [( (can >= t).mean() - (whe >= t).mean() ) for t in grid]
    i = int(np.argmax(js))
    return {"t": float(grid[i]), "J": float(js[i]),
            "canola": float((can >= grid[i]).mean()),
            "wheat": float((whe >= grid[i]).mean()),
            "n_can": int(can.size), "n_whe": int(whe.size)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-clear-frac", type=float, default=MIN_CLEAR_FRAC)
    ap.add_argument("--flower-start", type=int, default=70,
                    help="flowering window start, days after sowing")
    ap.add_argument("--flower-end", type=int, default=140,
                    help="flowering window end, days after sowing")
    args = ap.parse_args()

    ts, n_files, n0 = load(args.ts_dir, args.min_clear_frac)

    L = ["# Stage-2: Canola Flower Index (CFI) evaluation\n",
         f"- files **{n_files}**, scenes **{len(ts)}** of {n0} "
         f"(clear-frac >= {args.min_clear_frac})",
         f"- trials **{ts.TrialCode.nunique()}**  |  CFI on 0-1 reflectance "
         f"(x10000 to compare with PaddockTS raw-DN values)",
         "- `CFI = NDVI * ((Red + Green) + (Green - Blue))`, Tian et al. 2022\n"]

    # --- 1. does the flowering window matter? ------------------------------------------
    L.append("## Whole-season max vs flowering-window max\n")
    L.append("The key question: CFI peaks again at senescence, so does restricting to the "
             "flowering window actually separate the crops better?\n")
    L.append("| metric | window (days after sow) | best t | Youden J | Canola flagged | Wheat flagged |")
    L.append("|---|---|---|---|---|---|")
    variants = [("cfi_win_mean", None, None, "whole season"),
                ("cfi_win_mean", args.flower_start, args.flower_end,
                 f"{args.flower_start}-{args.flower_end}"),
                ("ndyi_win_mean", None, None, "whole season")]
    for col, lo, hi, label in variants:
        if col not in ts.columns:
            continue
        r = youden(peak_in_window(ts, col, lo, hi), col)
        if r:
            L.append(f"| {col.replace('_win_mean','')} | {label} | {r['t']:.4f} | "
                     f"**{r['J']:.3f}** | {r['canola']:.1%} | {r['wheat']:.1%} |")

    # --- 2. where should the window sit? -----------------------------------------------
    L.append("\n## Scan of flowering-window placement (CFI)\n")
    scan = []
    # Scanned as a grid rather than a hand-picked list: the first version stopped at
    # 100-170 and that turned out to be the best cell, i.e. an optimum sitting on the edge
    # of the search — which says nothing about where the real maximum is. The grid must
    # extend past the peak on both sides for the answer to mean anything.
    best_win = None
    windows = [(lo, lo + w) for w in (50, 60, 70, 80, 90, 100)
               for lo in range(40, 171, 10)]
    for lo, hi in windows:
        pk = peak_in_window(ts, "cfi_win_mean", lo, hi)
        r = youden(pk, "cfi_win_mean")
        if not r:
            continue
        scan.append({"lo": lo, "hi": hi, "J": r["J"], "t": r["t"],
                     "canola": r["canola"], "wheat": r["wheat"], "n": len(pk)})
        if best_win is None or r["J"] > best_win[2]["J"]:
            best_win = (lo, hi, r)

    sc = pd.DataFrame(scan)
    # Grid as a J matrix (rows = start, cols = width) — makes it obvious at a glance
    # whether the maximum is interior or pinned to an edge.
    sc["width"] = sc["hi"] - sc["lo"]
    piv = sc.pivot(index="lo", columns="width", values="J")
    L.append("Youden J by window start (rows) x width (cols), days after sowing:\n")
    L.append("| start | " + " | ".join(f"w={w}" for w in piv.columns) + " |")
    L.append("|" + "---|" * (len(piv.columns) + 1))
    for lo_, row in piv.iterrows():
        cells = " | ".join("–" if pd.isna(v) else f"{v:.3f}" for v in row)
        L.append(f"| {lo_} | {cells} |")

    if best_win:
        lo, hi, r = best_win
        edge = (lo in (sc["lo"].min(), sc["lo"].max())
                or (hi - lo) in (sc["width"].min(), sc["width"].max()))
        note = ("**ON THE EDGE of the scanned grid — widen the scan before trusting it**"
                if edge else "interior to the scanned grid (a real maximum, not a boundary)")
        L.append(f"\n_Optimum is {note}._")
        L.append(f"\n**Best window: {lo}-{hi} days after sowing, "
                 f"Youden J = {r['J']:.3f} at CFI >= {r['t']:.4f}** "
                 f"(flags {r['canola']:.1%} of Canola vs {r['wheat']:.1%} of Wheat; "
                 f"n = {r['n_can']} Canola / {r['n_whe']} Wheat).")
        L.append(f"\nFor comparison, NDYI whole-season managed J = 0.458. "
                 f"Change in J: **{r['J'] - 0.458:+.3f}**.\n")

        # verdict mix at the chosen operating point
        pk = peak_in_window(ts, "cfi_win_mean", lo, hi)
        L.append("## Verdict mix at candidate CFI thresholds\n")
        L.append(f"(window {lo}-{hi} DAS; Canola CONFIRMED if CFI >= t, "
                 f"Wheat CONFIRMED if CFI < t)\n")
        L.append("| CFI threshold | Canola CONF | Canola UNC | Wheat CONF | Wheat UNC |")
        L.append("|---|---|---|---|---|")
        lo_q, hi_q = pk["cfi_win_mean"].quantile([0.10, 0.90])
        for t in np.linspace(lo_q, hi_q, 7):
            can = pk[pk.crop == "Canola"]["cfi_win_mean"]
            whe = pk[pk.crop == "Wheat"]["cfi_win_mean"]
            L.append(f"| {t:.4f} | {int((can >= t).sum())} | {int((can < t).sum())} | "
                     f"{int((whe < t).sum())} | {int((whe >= t).sum())} |")

    # ---- held-out check -----------------------------------------------------------------
    # The window and threshold above were both chosen to maximise J on all 1,630 trials, so
    # that J is an in-sample fit, not a performance estimate. Re-select on early seasons and
    # score on later ones. A temporal split is the honest test here: the lit review found
    # season-to-season transfer is harder than site-to-site, and it is the split that matches
    # how this would actually be used (fit on past seasons, apply to a new one).
    if best_win:
        ts["year"] = ts["sow"].dt.year
        yrs = sorted(ts["year"].dropna().unique())
        cut = yrs[len(yrs) // 2]
        L.append(f"\n## Held-out check (temporal split at sow year {cut})\n")
        tr_ts, te_ts = ts[ts["year"] < cut], ts[ts["year"] >= cut]
        best_tr = None
        for lo, hi in windows:
            r = youden(peak_in_window(tr_ts, "cfi_win_mean", lo, hi), "cfi_win_mean")
            if r and (best_tr is None or r["J"] > best_tr[2]["J"]):
                best_tr = (lo, hi, r)
        if best_tr and len(te_ts):
            lo_t, hi_t, r_tr = best_tr
            pk_te = peak_in_window(te_ts, "cfi_win_mean", lo_t, hi_t)
            can = pk_te.loc[pk_te.crop == "Canola", "cfi_win_mean"].dropna().to_numpy()
            whe = pk_te.loc[pk_te.crop == "Wheat", "cfi_win_mean"].dropna().to_numpy()
            if can.size and whe.size:
                j_te = (can >= r_tr["t"]).mean() - (whe >= r_tr["t"]).mean()
                L.append(f"- selected on sow years < {cut}: window **{lo_t}-{hi_t}**, "
                         f"CFI >= **{r_tr['t']:.4f}** (train J = {r_tr['J']:.3f})")
                L.append(f"- applied unchanged to sow years >= {cut} "
                         f"({can.size} Canola / {whe.size} Wheat): "
                         f"**held-out J = {j_te:.3f}** "
                         f"({(can >= r_tr['t']).mean():.1%} Canola vs "
                         f"{(whe >= r_tr['t']).mean():.1%} Wheat)")
                L.append(f"- in-sample J was {best_win[2]['J']:.3f}; "
                         f"**optimism = {best_win[2]['J'] - j_te:+.3f}**\n")
                L.append("Quote the held-out number, not the in-sample one.")

    text = "\n".join(L) + "\n"
    with open(args.out, "w") as fh:
        fh.write(text)
    print(text)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
