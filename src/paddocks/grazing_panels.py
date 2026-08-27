#!/usr/bin/env python3
"""
Per-polygon NDVI/CFI curves for the sampled grazing paddocks, drawn against the crop envelopes.

WHY THIS EXISTS. `nlum_negatives.py` sampled 128 paddocks that NLUM says are grazing, and NLUM
is a probability surface rather than ground truth, so every one of them needs a human verdict
before it can be used as a negative. Doing that from imagery alone is 128 separate QGIS
judgements about a paddock in a year the reviewer cannot see. The phenology is the faster
discriminator and it is the same evidence the model uses: a crop paddock climbs to a strong
NDVI peak and senesces, canola adds a CFI spike, pasture does neither.

WHAT THE GREY BANDS ARE. The 10th-90th percentile envelope of the reviewed-good crop paddocks
of each group, on the same DOY axis and the same paddock-median estimator. A candidate whose
curve sits inside the Cereal envelope is probably a crop and probably should be rejected as a
negative; one that stays flat and low all season is the pasture this class is meant to capture.

The verdict still belongs to the reviewer — this only puts the evidence in front of them. Write
verdicts into the `verdict` column of the GeoPackage from `nlum_negatives.py package`.

    python3 grazing_panels.py --ts .../ts_grazing.csv --sites .../grazing_sites.csv \
        --crop-ts ".../ts_v2/*_SENSITIVE.csv" --labeled .../nvt_trials_labeled.csv \
        --reviewed .../reviewed_trials_SENSITIVE.csv --outdir .../figures/grazing_panels
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd

GROUP = {"Canola": "Canola", "Wheat": "Cereal", "Barley": "Cereal", "Oat": "Cereal",
         "Triticale": "Cereal", "Lentil": "Legume", "Faba Bean": "Legume",
         "Field Pea": "Legume", "Lupin": "Legume", "Chickpea": "Legume"}
DOY = np.arange(90, 351, 10)
PER_PAGE = 24


def curves(ts, col):
    """DOY-binned median per paddock, on a common axis so paddocks and groups are comparable."""
    ts = ts.copy()
    ts["doy"] = pd.to_datetime(ts.time).dt.dayofyear
    ts["bin"] = pd.cut(ts.doy, np.append(DOY, DOY[-1] + 10), labels=DOY, right=False)
    p = ts.pivot_table(index="TrialCode", columns="bin", values=col,
                       aggfunc="median", observed=False)
    return p.reindex(columns=DOY)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", required=True, help="grazing index time series")
    ap.add_argument("--sites", required=True, help="grazing_sites.csv (stratum, area_ha)")
    ap.add_argument("--crop-ts", nargs="+", required=True, help="glob(s) of crop ts_v2")
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--reviewed", help="restrict the envelopes to reviewed-good trials")
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(args.outdir, exist_ok=True)
    g = pd.read_csv(args.ts)
    g = g[g.n_clear_px / g.n_px_paddock.clip(lower=1) >= 0.5]
    sites = pd.read_csv(args.sites).drop_duplicates("TrialCode").set_index("TrialCode")

    files = sorted({f for p in args.crop_ts for f in glob.glob(p)})
    c = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    c = c[c.n_clear_px / c.n_px_paddock.clip(lower=1) >= 0.5]
    lab = pd.read_csv(args.labeled).drop_duplicates("TrialCode").set_index("TrialCode")
    if args.reviewed:
        c = c[c.TrialCode.isin(set(pd.read_csv(args.reviewed).TrialCode))]

    env = {}
    for metric in ["ndvi_pad_median", "cfi_pad_median"]:
        C = curves(c, metric)
        grp = lab.reindex(C.index).crop.map(GROUP)
        env[metric] = {k: (np.nanpercentile(C[grp == k], 10, axis=0),
                           np.nanpercentile(C[grp == k], 90, axis=0))
                       for k in ["Canola", "Cereal", "Legume"] if (grp == k).sum() > 5}
        print(f"{metric}: envelopes from {int(grp.notna().sum())} crop paddocks")

    G = {m: curves(g, m) for m in ["ndvi_pad_median", "cfi_pad_median"]}
    ids = list(G["ndvi_pad_median"].index)
    print(f"{len(ids)} grazing paddocks with usable series")

    colours = {"Canola": "#d9a441", "Cereal": "#7a9e4f", "Legume": "#6a8caf"}
    for page in range(0, len(ids), PER_PAGE):
        chunk = ids[page:page + PER_PAGE]
        nr = int(np.ceil(len(chunk) / 4))
        fig, axes = plt.subplots(nr, 4, figsize=(16, 2.6 * nr), sharex=True)
        axes = np.atleast_2d(axes)
        for ax, pid in zip(axes.ravel(), chunk):
            for k, (lo, hi) in env["ndvi_pad_median"].items():
                ax.fill_between(DOY, lo, hi, color=colours[k], alpha=0.18, lw=0)
            ax.plot(DOY, G["ndvi_pad_median"].loc[pid], "k-", lw=1.6)
            ax.set_ylim(-0.1, 1.0)
            s = sites.loc[pid] if pid in sites.index else None
            ax.set_title(f"{pid}  {s.stratum if s is not None else ''} "
                         f"{s.area_ha:.0f} ha" if s is not None else pid, fontsize=8)
            # CFI on a twin axis: it is the canola discriminator and is on a different scale
            # entirely, so plotting it against the NDVI axis would flatten it into the floor.
            ax2 = ax.twinx()
            ax2.plot(DOY, G["cfi_pad_median"].loc[pid], color="#b5651d", lw=1.0, ls=":")
            ax2.set_ylim(-200, 1400)
            ax2.tick_params(labelsize=6)
            ax.tick_params(labelsize=7)
        for ax in axes.ravel()[len(chunk):]:
            ax.axis("off")
        fig.suptitle("Grazing candidates: NDVI (black) and CFI (dotted) against the "
                     "10-90 % crop envelopes — Canola gold, Cereal green, Legume blue",
                     fontsize=10)
        fig.tight_layout(rect=[0, 0, 1, 0.97])
        out = os.path.join(args.outdir, f"grazing_panels_{page//PER_PAGE:02d}.png")
        fig.savefig(out, dpi=110)
        plt.close(fig)
        print(f"wrote {out} ({len(chunk)} paddocks)")

    # A one-number summary per paddock, so the reviewer can sort rather than scan: how far the
    # NDVI curve sits below the Cereal envelope's lower edge, summed over the season.
    lo = env["ndvi_pad_median"]["Cereal"][0]
    N = G["ndvi_pad_median"]
    # nansum, not sum: a cloud-empty DOY bin is missing evidence, not evidence of nothing, and
    # a plain sum propagates its NaN over the whole paddock and silently drops it from the rank.
    gap = np.maximum(lo - N.values, 0)
    n_obs = np.isfinite(N.values).sum(axis=1)
    below = np.where(n_obs > 0, np.nansum(gap, axis=1) / np.maximum(n_obs, 1), np.nan)
    amp = np.nanmax(N.values, axis=1) - np.nanmin(N.values, axis=1)
    S = pd.DataFrame({"poly_id": N.index, "below_cereal": below.round(3),
                      "ndvi_amp": amp.round(3)}).set_index("poly_id")
    S = S.join(sites[["stratum", "area_ha"]]).sort_values("below_cereal", ascending=False)
    S.to_csv(os.path.join(args.outdir, "grazing_ranked.csv"))
    print(f"\nranked candidates -> {os.path.join(args.outdir, 'grazing_ranked.csv')}")
    print(S.groupby("stratum")[["below_cereal", "ndvi_amp"]].median().round(3).to_string())


if __name__ == "__main__":
    main()
