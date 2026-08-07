#!/usr/bin/env python3
"""
Stage 1 labeller: NVT ground-truth site-cleanliness analysis.

Reads the NVT yield/quality workbook, collapses trial x variety rows to trial
level, and flags trials that are "clean" = no different-crop trial within
THRESHOLD_M in the same year (paddock-contamination filter). Writes a sensitive
per-trial labelled table to data/derived/ (gitignored) and non-sensitive summary
figures to output/figures/.

Run locally (pandas only, no geospatial deps):
    python src/explore_nvt_sites.py [threshold_m]

Outputs:
    data/derived/nvt_trials_labeled.csv   (SENSITIVE - gitignored)
    output/figures/nvt_contamination_distance.png
    output/figures/nvt_clean_by_crop.png
    data/derived/nvt_sites_map_SENSITIVE.png (SENSITIVE - gitignored)
"""
import os, sys, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = os.path.join(REPO, "data", "raw",
                    "2017-2024 NVT Yield and Grain Quality - cbradley - 01.05.2025.xlsx")
DERIVED = os.path.join(REPO, "data", "derived")
FIGDIR = os.path.join(REPO, "output", "figures")
THRESHOLD_M = float(sys.argv[1]) if len(sys.argv) > 1 else 200.0
FOCUS = {"Canola", "Wheat"}   # scope chosen for Stage 2


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def load_trials():
    sheets = pd.read_excel(XLSX, sheet_name=None, dtype=str)
    frames = []
    for name, df in sheets.items():
        df = df.rename(columns={"Trial GPS Lat": "lat", "Trial GPS Long": "lon",
                                "Crop.Name": "crop"})
        df["sheet"] = name
        frames.append(df)
    raw = pd.concat(frames, ignore_index=True)
    for c in ("lat", "lon"):
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    raw["Year"] = pd.to_numeric(raw["Year"], errors="coerce").astype("Int64")
    raw["abandoned"] = raw["Abandoned"].astype(str).str.strip().str.lower().isin(
        ["true", "1", "-1"])
    trials = raw.groupby("TrialCode", dropna=False).agg(
        Year=("Year", "first"), crop=("crop", "first"),
        lat=("lat", "first"), lon=("lon", "first"),
        state=("State", "first"), region=("RegionName", "first"),
        site=("SiteDescription", "first"),
        sow=("SowingDate", "first"), harv=("HarvestDate", "first"),
        abandoned=("abandoned", "max"),
        n_varieties=("VarietyDisplayName", "nunique"),
    ).reset_index()
    valid = trials["lat"].between(-44, -10) & trials["lon"].between(112, 154)
    return trials[valid & ~trials["abandoned"]].reset_index(drop=True), len(raw), len(trials)


def nearest_diff_crop_same_year(t):
    nn = np.full(len(t), np.inf)
    for _, idx in t.groupby("Year").groups.items():
        idx = list(idx)
        sub = t.loc[idx]
        la, lo, cr = sub["lat"].values, sub["lon"].values, sub["crop"].values
        for i in range(len(idx)):
            d = haversine(la[i], lo[i], la, lo)
            mask = cr != cr[i]
            if mask.any():
                nn[idx[i]] = d[mask].min()
    return nn


def main():
    os.makedirs(DERIVED, exist_ok=True)
    os.makedirs(FIGDIR, exist_ok=True)
    t, n_rows, n_all = load_trials()
    print(f"rows={n_rows}  trials={n_all}  usable={len(t)}")
    t["nearest_diffcrop_same_year_m"] = nearest_diff_crop_same_year(t)
    d = t["nearest_diffcrop_same_year_m"]
    t["clean"] = np.isinf(d) | (d > THRESHOLD_M)
    t["focus"] = t["crop"].isin(FOCUS)
    t.to_csv(os.path.join(DERIVED, "nvt_trials_labeled.csv"), index=False)
    print(f"clean@{THRESHOLD_M:.0f}m: {int(t['clean'].sum())}/{len(t)}  "
          f"clean+focus(Canola/Wheat): {int((t['clean'] & t['focus']).sum())}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    dd = d.replace(np.inf, np.nan)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.hist(dd.clip(upper=2000).dropna(), bins=40, color="#4C78A8", edgecolor="white")
    ax.axvline(THRESHOLD_M, color="#E45756", ls="--", lw=1.5,
               label=f"{THRESHOLD_M:.0f} m threshold")
    ax.set_xlabel("Distance to nearest different-crop trial, same year (m; clipped 2 km)")
    ax.set_ylabel("Trials")
    ax.set_title("NVT paddock-contamination risk")
    ax.legend(); fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "nvt_contamination_distance.png"), dpi=130)
    plt.close(fig)

    g = t.groupby("crop")["clean"].agg(["sum", "size"])
    g["contam"] = g["size"] - g["sum"]
    g = g.sort_values("size")
    fig, ax = plt.subplots(figsize=(7, 4.6))
    ax.barh(g.index, g["sum"], color="#59A14F", label=f"clean (>{THRESHOLD_M:.0f} m)")
    ax.barh(g.index, g["contam"], left=g["sum"], color="#B07AA1", label="contaminated")
    ax.set_xlabel("Trials"); ax.set_title("Clean trials by species")
    ax.legend(loc="lower right"); fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "nvt_clean_by_crop.png"), dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.5, 6))
    cc, xx = t[t["clean"]], t[~t["clean"]]
    ax.scatter(xx["lon"], xx["lat"], s=4, c="#B07AA1", alpha=.6, label="contaminated")
    ax.scatter(cc["lon"], cc["lat"], s=4, c="#59A14F", alpha=.6, label="clean")
    ax.set_xlabel("lon"); ax.set_ylabel("lat")
    ax.set_title("NVT trial sites (SENSITIVE)")
    ax.legend(); fig.tight_layout()
    fig.savefig(os.path.join(DERIVED, "nvt_sites_map_SENSITIVE.png"), dpi=120)
    plt.close(fig)
    print("done")


if __name__ == "__main__":
    main()
