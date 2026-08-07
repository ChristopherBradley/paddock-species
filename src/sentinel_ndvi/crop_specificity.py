#!/usr/bin/env python3
"""
Stage 2e: is CFI actually canola-SPECIFIC, or just canola-vs-wheat?

The pipeline was built on Canola vs Wheat, which quietly assumes anything that is not
canola looks like wheat. Lupin, faba bean, chickpea and field pea all flower, so that
assumption had never been tested. This scores the CFI operating point against all nine
clean NVT crops.

    python3 crop_specificity.py --ts-dir .../sentinel_ts --out .../crop_specificity.md
"""
import argparse, glob, os
import numpy as np, pandas as pd
from phenology_check import CFI_FLOWER_MIN, FLOWER_END_DAS, FLOWER_START_DAS, MIN_CLEAR_FRAC


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cfi-min", type=float, default=CFI_FLOWER_MIN)
    ap.add_argument("--flower", type=int, nargs=2,
                    default=(FLOWER_START_DAS, FLOWER_END_DAS))
    args = ap.parse_args()

    d = pd.concat([pd.read_csv(f, parse_dates=["time"])
                   for f in sorted(glob.glob(os.path.join(args.ts_dir, "*_ts.csv")))],
                  ignore_index=True)
    d["sow"] = pd.to_datetime(d["sow"])
    d["das"] = (d["time"] - d["sow"]).dt.days
    d = d[d.n_clear_px / d.n_px_total >= MIN_CLEAR_FRAC]
    w = d[(d.das >= args.flower[0]) & (d.das <= args.flower[1])]
    pk = w.groupby(["TrialCode", "crop"]).cfi_win_mean.max().reset_index()

    L = [f"# CFI specificity across all NVT crops\n",
         f"- flowering window {args.flower[0]}-{args.flower[1]} DAS, threshold "
         f"CFI >= {args.cfi_min}\n", "| crop | n | median | p25 | p75 | % over threshold |",
         "|---|---|---|---|---|---|"]
    g = pk.groupby("crop").cfi_win_mean
    tab = pd.DataFrame({"n": g.count(), "median": g.median(),
                        "p25": g.quantile(.25), "p75": g.quantile(.75),
                        "pct": 100 * pk.assign(f=pk.cfi_win_mean >= args.cfi_min)
                        .groupby("crop").f.mean()}).sort_values("median", ascending=False)
    for c, r in tab.iterrows():
        L.append(f"| {c} | {int(r.n)} | {r['median']:.4f} | {r.p25:.4f} | {r.p75:.4f} | "
                 f"{r.pct:.1f}% |")

    can = pk[pk.crop == "Canola"].cfi_win_mean.to_numpy()
    oth = pk[pk.crop != "Canola"].cfi_win_mean.to_numpy()
    grid = np.quantile(np.concatenate([can, oth]), np.linspace(.01, .99, 199))
    J = [(can >= t).mean() - (oth >= t).mean() for t in grid]
    i = int(np.argmax(J))
    L.append(f"\n**Canola vs ALL other crops: best Youden J = {J[i]:.3f} at CFI >= "
             f"{grid[i]:.4f}** (flags {(can>=grid[i]).mean():.1%} of Canola, "
             f"{(oth>=grid[i]).mean():.1%} of non-Canola).\n")
    L.append("CFI is NOT canola-specific. `CFI = NDVI * (Red + 2*Green - Blue)` rises for any "
             "bright flowering canopy: white lupin flowers lift R, G and B together, netting "
             "+2 units, which is why ~50% of lupins clear a canola threshold. That is "
             "acceptable for Stage 2, which asks whether a paddock is CONSISTENT with its "
             "claimed canola label, but CFI alone cannot carry a multi-class crop model.")

    text = "\n".join(L) + "\n"
    open(args.out, "w").write(text)
    print(text)


if __name__ == "__main__":
    main()
