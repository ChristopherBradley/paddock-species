#!/usr/bin/env python3
"""
Stage 2b: from the extracted Sentinel-2 time series, derive per-trial phenology
metrics and a heuristic verdict on whether the paddock signal is consistent with
the NVT trial crop. This CONFIRMS or FLAGS the Stage-1 labels; it does not fabricate.

    python3 phenology_check.py \
        --ts-dir /scratch/xe2/cb8590/paddock-species-data/derived/sentinel_ts \
        --out    /scratch/xe2/cb8590/paddock-species-data/derived/nvt_confirmed.csv

Heuristics (all tunable, documented in README):
  * A real annual crop shows a clear NDVI green-up then senescence (amplitude high).
  * Canola flowers yellow over a green canopy; wheat does not. That is measured by the
    **max CFI within the flowering window**, not by NDYI.
Verdict: CONFIRMED / UNCERTAIN / REJECTED, with the metrics kept for inspection.

NDYI was the original discriminator and was ABANDONED on evidence. Being pure visible-band
yellowness, it scores bare and senescing soil highly: across all 1,630 trials the shipped
0.12 threshold flagged 95.8% of Canola but also 78.4% of Wheat (Youden J = 0.17, near
chance), and its best achievable J was 0.458. CFI multiplies by NDVI, so the signal only
survives where there is both green biomass and yellowness — an actual flowering canopy.
`ndyi_peak` is still reported for comparison but no longer drives the verdict.

Two things matter about the window (both measured in cfi_report.py, not assumed):
  * CFI peaks a second time at senescence, so it must be maximised over a window rather
    than the whole season.
  * The window is defined in days after sowing, and the best placement is LATE
    (~120-180 DAS), well after the naive "flowering is ~2 months in" guess.
Selecting window and threshold on all data gives J = 0.604; re-selected on early sow years
and applied unchanged to 2021+, the held-out J is **0.535**. Quote the held-out figure.

Partially-cloudy scenes are discarded first (--min-clear-frac). The extractor keeps any
date with >=1 clear pixel, but scenes with only a handful of clear pixels sit
systematically low in both indices (swath edge / cloud halo). Left in, they depress the
p5/p20 baselines and so inflate BOTH ndvi_amp and ndyi_peak — a one-directional bias
toward CONFIRMED. Observed in the smoke test: 44/462 clear px reporting NDVI 0.28
between neighbours of 0.34 and 0.56.
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd

NDVI_AMP_MIN = 0.35        # min green-up amplitude for a cropped paddock
NDYI_FLOWER_MIN = 0.12     # legacy NDYI threshold — reported only, no longer used
MIN_CLEAR_FRAC = 0.5       # discard scenes with <50% of the window clear
# Operating point from cfi_report.py: window chosen on sow years <2021 and applied unchanged
# to 2021+ (held-out J = 0.535). Interior to the scanned grid, so it is a real maximum and
# not an artefact of where the search stopped.
CFI_FLOWER_MIN = 0.1309    # min max-CFI within the flowering window to call flowering
FLOWER_START_DAS = 120     # flowering window start, days after sowing
FLOWER_END_DAS = 190       # flowering window end, days after sowing


def summarise(g, flower_start=FLOWER_START_DAS, flower_end=FLOWER_END_DAS):
    g = g.sort_values("time")
    ndvi = g["ndvi_win_mean"].to_numpy()
    ndvi = ndvi[~np.isnan(ndvi)]
    if ndvi.size < 5:
        return None
    ndvi_amp = np.nanpercentile(ndvi, 95) - np.nanpercentile(ndvi, 5)
    peak_i = int(np.nanargmax(g["ndvi_win_mean"].to_numpy()))
    peak_time = pd.to_datetime(g["time"].to_numpy()[peak_i])
    out = dict(n_obs=len(g), ndvi_amp=ndvi_amp, ndvi_peak_doy=int(peak_time.dayofyear))

    if "ndyi_win_mean" in g:      # legacy metric, retained for comparison only
        ndyi = g["ndyi_win_mean"].to_numpy()
        out["ndyi_peak"] = np.nanmax(ndyi) - np.nanpercentile(ndyi, 20)

    # Max CFI inside the flowering window. NaN (not 0) when the window has no clear
    # observation at all — that is "could not be assessed", which must stay distinguishable
    # from "assessed and found no flowering".
    out["cfi_flower_max"] = np.nan
    out["n_obs_flower"] = 0
    if "cfi_win_mean" in g and "das" in g:
        w = g[(g["das"] >= flower_start) & (g["das"] <= flower_end)]["cfi_win_mean"].dropna()
        out["n_obs_flower"] = int(len(w))
        if len(w):
            out["cfi_flower_max"] = float(w.max())
    return out


def verdict(crop, m, ndvi_amp_min=NDVI_AMP_MIN, cfi_flower_min=CFI_FLOWER_MIN):
    if m is None or m["ndvi_amp"] < ndvi_amp_min:
        return "REJECTED"           # no cropping signal at this pixel
    cfi = m.get("cfi_flower_max", np.nan)
    if cfi is None or (isinstance(cfi, float) and np.isnan(cfi)):
        return "UNCERTAIN"          # flowering window never observed — cannot judge
    flowered = cfi >= cfi_flower_min
    if crop == "Canola":
        return "CONFIRMED" if flowered else "UNCERTAIN"
    if crop == "Wheat":
        # wheat should NOT show a flowering-yellow peak over a green canopy
        return "UNCERTAIN" if flowered else "CONFIRMED"
    return "UNCERTAIN"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-clear-frac", type=float, default=MIN_CLEAR_FRAC,
                    help="drop scenes whose clear-pixel fraction is below this")
    ap.add_argument("--ndvi-amp-min", type=float, default=NDVI_AMP_MIN,
                    help="min green-up amplitude to accept the pixel as cropped")
    ap.add_argument("--cfi-flower-min", type=float, default=CFI_FLOWER_MIN,
                    help="min max-CFI inside the flowering window to call flowering; "
                         "see cfi_report.py for the scan that produced the default")
    ap.add_argument("--flower-start", type=int, default=FLOWER_START_DAS,
                    help="flowering window start, days after sowing")
    ap.add_argument("--flower-end", type=int, default=FLOWER_END_DAS,
                    help="flowering window end, days after sowing")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.ts_dir, "*_ts.csv")))
    if not files:
        raise SystemExit(f"no *_ts.csv found in {args.ts_dir}")
    ts = pd.concat((pd.read_csv(f, parse_dates=["time"]) for f in files), ignore_index=True)

    for need in ("n_px_total", "cfi_win_mean", "sow"):
        if need not in ts.columns:
            raise SystemExit(f"time series lack '{need}' — re-run extract_ndvi.py (see README)")
    ts["sow"] = pd.to_datetime(ts["sow"])
    ts["das"] = (ts["time"] - ts["sow"]).dt.days
    n_before = len(ts)
    ts = ts[ts["n_clear_px"] / ts["n_px_total"] >= args.min_clear_frac].reset_index(drop=True)
    print(f"clear-frac >= {args.min_clear_frac}: kept {len(ts)}/{n_before} scenes "
          f"({n_before - len(ts)} partially-cloudy dropped)")
    print(f"flowering window {args.flower_start}-{args.flower_end} DAS, "
          f"CFI >= {args.cfi_flower_min}, NDVI amp >= {args.ndvi_amp_min}")

    rows = []
    for (tc, crop), g in ts.groupby(["TrialCode", "crop"]):
        m = summarise(g, args.flower_start, args.flower_end)
        v = verdict(crop, m, args.ndvi_amp_min, args.cfi_flower_min)
        rec = {"TrialCode": tc, "crop": crop, "verdict": v}
        rec.update(m or {})
        rows.append(rec)
    out = pd.DataFrame(rows)
    out.to_csv(args.out, index=False)
    print(out["verdict"].value_counts().to_string())
    print(f"wrote {args.out} ({len(out)} trials)")


if __name__ == "__main__":
    main()
