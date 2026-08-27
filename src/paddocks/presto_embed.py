#!/usr/bin/env python3
"""
Presto embeddings for the reviewed paddocks, as an alternative to hand-built features.

WHY PRESTO AND NOT MORE PSEUDO-LABELS. The unlabelled paddocks are the largest untapped asset
here, and `CANOLA_PSEUDO_LABELS.md` already ruled out the cheap way of using them —
CFI-thresholded pseudo-labels import the threshold's own errors as if they were ground truth.
Self-supervised pre-training uses the same unlabelled data without ever converting a model
output into a label, which is the distinction that matters.

WHAT PRESTO WANTS, and what this project can supply. Presto consumes 12 monthly timesteps of
17 channels. The 10-band paddock series covers 10 of them exactly:

    blue green red  red_edge_1 red_edge_2 red_edge_3  nir_1 nir_2  swir_2 swir_3
    B2   B3    B4   B5         B6         B7          B8    B8A    B11    B12

NDVI (channel 16) Presto derives from B8 and B4. That leaves **S1 (VV/VH), ERA5 and SRTM
unavailable**, and they are passed as MASKED rather than as zeros — Presto's pre-training
masks channel groups by design, so a masked group is a case it was trained to handle whereas a
zero-filled group is a lie it was not.

**This is the second reason to want Sentinel-1** (`s1_benchmark.py`): S1 is one of Presto's
nine channel groups, so obtaining it upgrades this model and the feature-based one at once.

CALENDAR YEAR, month=0. Presto positions timesteps by month index, so the 12 steps are Jan-Dec
of the trial year. Southern-Australian winter crops sit inside one calendar year — sown Apr-Jun,
harvested Nov-Dec — so a calendar window contains the whole season without splitting it.

Normalisation constants are Presto's own (`presto/dataops/pipelines/s1_s2_era5_srtm.py`),
reproduced here rather than imported because that module pulls in `earthengine-api`.

SENSITIVE: keyed by TrialCode, so embeddings are written to /scratch.
"""
import argparse
import glob
import os
import sys

import numpy as np
import pandas as pd

# Presto's NORMED_BANDS order, after B1/B9/B10 are dropped. Channel index is position here.
NORMED_BANDS = ["VV", "VH", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12",
                "temperature_2m", "total_precipitation", "elevation", "slope", "NDVI"]
ADD_BY = np.array([25.0, 25.0] + [0.0] * 10 + [-272.15, 0.0] + [0.0, 0.0] + [0.0])
DIVIDE_BY = np.array([25.0, 25.0] + [1e4] * 10 + [35.0, 0.03] + [2000.0, 50.0] + [1.0])
# Channel groups Presto masks together. Ours are missing wholesale, not per-timestep.
MISSING_GROUPS = {"S1": [0, 1], "ERA5": [12, 13], "SRTM": [14, 15]}
OUR_BANDS = {"blue": "B2", "green": "B3", "red": "B4", "red_edge_1": "B5",
             "red_edge_2": "B6", "red_edge_3": "B7", "nir_1": "B8", "nir_2": "B8A",
             "swir_2": "B11", "swir_3": "B12"}
NUM_TIMESTEPS = 12


def build_arrays(ts, lab, reviewed, s1=None):
    """(n, 12, 17) normalised inputs, (n, 12, 17) mask, latlons, and the TrialCode index.

    With `s1`, VV/VH are filled and the S1 group is unmasked — recovering one of the three
    channel groups Presto was missing here. Trials without S1 are DROPPED rather than left
    masked, because Presto's encoder asserts every sample in a batch carries the same number of
    masked tokens; a per-trial S1 mask cannot be expressed. Embedding the two populations in
    separate passes would satisfy the assertion but hand the classifier a systematic difference
    that tracks S1 availability rather than the crop, so the row set is narrowed instead — the
    same `keep_s1both` discipline the feature arms use.
    """
    ts = ts[ts.TrialCode.isin(reviewed)].copy()
    ts["time"] = pd.to_datetime(ts.time)
    ts["mon"] = ts.time.dt.month - 1
    have = [c for c in OUR_BANDS if c in ts.columns]
    if len(have) < 10:
        raise SystemExit(f"only {len(have)} of 10 bands present: {have}")

    # Monthly mean per trial. Presto's timestep is a month, and a month holds 2-6 clear
    # revisits, so averaging within it is the intended reduction rather than a shortcut.
    g = ts.groupby(["TrialCode", "mon"])[have].mean()
    codes = sorted(ts.TrialCode.unique())
    ci = {c: i for i, c in enumerate(codes)}
    X = np.full((len(codes), NUM_TIMESTEPS, len(NORMED_BANDS)), np.nan, np.float32)
    for (tc, mon), row in g.iterrows():
        for c in have:
            # Reflectance 0-1 in our files; Presto divides by 1e4, so hand it raw DN.
            X[ci[tc], int(mon), NORMED_BANDS.index(OUR_BANDS[c])] = row[c] * 1e4

    obs = np.isfinite(X[:, :, NORMED_BANDS.index("B4")])   # months that were seen at all

    # Sentinel-1 into channels 0/1. Values are already dB, which is what Presto's (x+25)/25
    # normalisation below expects, so they go in raw. SAR sees through cloud, so unlike the
    # optical bands a missing month here means no acquisition, not an obscured one.
    has_s1 = np.ones(len(codes), bool)
    if s1 is not None:
        s1 = s1[s1.TrialCode.isin(codes)].copy()
        s1["time"] = pd.to_datetime(s1.time)
        s1["mon"] = s1.time.dt.month - 1
        pair = {"vv_pad_median": "VV", "vh_pad_median": "VH"}
        gs = s1.groupby(["TrialCode", "mon"])[list(pair)].mean()
        for (tc, mon), row in gs.iterrows():
            for c, band in pair.items():
                X[ci[tc], int(mon), NORMED_BANDS.index(band)] = row[c]
        has_s1 = np.isfinite(X[:, :, NORMED_BANDS.index("VV")]).any(axis=1)
        print(f"S1 present for {int(has_s1.sum())} of {len(codes)} trials")

    # CLOUD GAPS ARE INTERPOLATED, NOT MASKED, and the reason is a hard constraint in Presto:
    # its encoder asserts every sample in a batch has the SAME number of masked tokens
    # ("we assume the number of masked patches is the same"), so a per-trial cloud pattern
    # cannot be expressed through the mask at all. The mask is therefore reserved for the
    # three channel groups that are missing identically for every trial, and month-to-month
    # gaps are filled by linear interpolation along the year — the same treatment the CFI
    # heatmaps already give a gappy trace, and closer to the truth than a zero.
    idx = np.arange(NUM_TIMESTEPS)
    interp_bands = [NORMED_BANDS.index(v) for v in OUR_BANDS.values()]
    if s1 is not None:
        interp_bands += [NORMED_BANDS.index("VV"), NORMED_BANDS.index("VH")]
    for i in range(X.shape[0]):
        for b in interp_bands:
            col = X[i, :, b]
            good = np.isfinite(col)
            if good.sum() >= 2:
                X[i, :, b] = np.interp(idx, idx[good], col[good])
            elif good.sum() == 1:
                X[i, :, b] = col[good][0]
    X = (X + ADD_BY) / DIVIDE_BY
    b8, b4 = X[:, :, NORMED_BANDS.index("B8")], X[:, :, NORMED_BANDS.index("B4")]
    with np.errstate(invalid="ignore", divide="ignore"):
        X[:, :, NORMED_BANDS.index("NDVI")] = np.where((b8 + b4) != 0, (b8 - b4) / (b8 + b4), 0)

    # mask = 1 means "not observed", and it is IDENTICAL for every trial: S1, ERA5 and SRTM
    # are absent for all of them, which is exactly the uniform-mask case Presto requires.
    mask = np.zeros_like(X, dtype=np.float32)
    missing = dict(MISSING_GROUPS)
    if s1 is not None:
        missing.pop("S1")
    for g in missing.values():
        mask[:, :, g] = 1.0
    print(f"masked channel groups: {sorted(missing) or 'none'}")
    X = np.nan_to_num(X, nan=0.0)

    # A trial seen in fewer than 4 of 12 months has more interpolation than data behind it.
    enough = (obs.sum(1) >= 4) & has_s1
    if not enough.all():
        print(f"dropping {int((~enough).sum())} trials: <4 months of 12 observed"
              + (", or no S1" if s1 is not None else ""))
    ll = lab.set_index("TrialCode").reindex(codes)[["lat", "lon"]].values.astype(np.float32)
    codes = list(np.array(codes)[enough])
    return X[enough], mask[enough], ll[enough], codes, obs[enough]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bands", nargs="+", required=True)
    ap.add_argument("--s1", help="s1_paddock_ts csv; fills VV/VH and unmasks Presto's S1 group")
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--reviewed", required=True)
    ap.add_argument("--presto-dir", default="/g/data/xe2/cb8590/models/presto")
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch", type=int, default=256)
    args = ap.parse_args()

    import torch
    sys.path.insert(0, args.presto_dir)
    from single_file_presto import Presto

    files = sorted({f for p in args.bands for f in glob.glob(p)})
    ts = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    ts = ts.drop_duplicates(["TrialCode", "time"])
    ts = ts[ts.n_clear_px / ts.n_px_paddock.clip(lower=1) >= 0.5]
    lab = pd.read_csv(args.labeled).drop_duplicates("TrialCode")
    rev = pd.read_csv(args.reviewed)
    reviewed = set(rev.loc[rev.usable.astype(bool), "TrialCode"])
    print(f"{ts.TrialCode.nunique()} trials with bands, {len(reviewed)} reviewed-usable")

    s1 = None
    if args.s1:
        s1 = pd.read_csv(args.s1).drop_duplicates(["TrialCode", "time"])
        s1 = s1[s1.n_clear_px / s1.n_px_paddock.clip(lower=1) >= 0.5]
        print(f"{s1.TrialCode.nunique()} trials with S1")

    X, mask, ll, codes, obs = build_arrays(ts, lab, reviewed, s1)
    print(f"input {X.shape}, months observed per trial: median "
          f"{np.median(obs.sum(1)):.0f} of 12")

    model = Presto.construct()
    sd = torch.load(os.path.join(args.presto_dir, "data", "default_model.pt"),
                    map_location="cpu")
    model.load_state_dict(sd)
    model.eval()
    enc = model.encoder

    embs = []
    with torch.no_grad():
        for i in range(0, len(X), args.batch):
            sl = slice(i, i + args.batch)
            n = X[sl].shape[0]
            embs.append(enc(
                x=torch.from_numpy(X[sl]).float(),
                dynamic_world=torch.full((n, NUM_TIMESTEPS), 9, dtype=torch.long),
                latlons=torch.from_numpy(ll[sl]).float(),
                mask=torch.from_numpy(mask[sl]).float(),
                month=0, eval_task=True).numpy())
    E = np.vstack(embs)
    print(f"embeddings {E.shape}")

    out = pd.DataFrame(E, index=pd.Index(codes, name="TrialCode"),
                       columns=[f"presto_{i:03d}" for i in range(E.shape[1])])
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out.reset_index().to_csv(args.out, index=False)
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
