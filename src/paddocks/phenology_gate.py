#!/usr/bin/env python3
"""
Does the season have the SHAPE of a crop — one green-up timed to sowing, ending in a hard
senescence after harvest — rather than just enough amplitude? `NEXT_STEPS.md` §6.2 argues
amplitude alone cannot separate a sown-but-not-harvested paddock (or improved pasture) from a
real crop, because both green up hard; a gate on the season's SHAPE is the fittable alternative,
"exactly as the amplitude gate was" — on the 3,439 NVT presence labels alone, no negative class.

WHAT "SHAPE" MEANS HERE, CONCRETELY. Unlike the amplitude gate (one number, p90-p10 of the whole
DOY-binned series), this uses each trial's own recorded `sow`/`harv` dates (in
`nvt_trials_labeled.csv`) to ask two literal questions of the raw per-date series:
  * did it actually RISE into the season — is there a real green-up, not just already-green
    ground? (`greenup_rise`: peak NDVI vs the pre-sowing baseline)
  * did it actually FALL after harvest — a hard senescence, not a shoulder or a plateau?
    (`senescence_drop`: peak NDVI vs a window well after the recorded harvest date)
A paddock can have high amplitude from a mid-season dip-and-recover or from pasture that never
truly senesces, and still fail one of these; that is the extra information over amplitude alone.

WHY PER-TRIAL DATE WINDOWS, NOT THE SHARED DOY BINS. `build_features` bins on calendar
day-of-year pooled across all years, which is right for a classifier that has no sowing date at
inference. Here we DO have sow/harv for training, and a trial sown in April reads a different
part of the calendar to one sown in June — anchoring each trial's windows to its own dates is a
tighter, more literal test of "green-up near sowing, senescence near harvest" than a shared
calendar window could be.

VALIDATION, HONESTLY SCOPED. This reports held-out PRESENCE RECALL only (5-fold CV, matching the
current gate's own 91.6 % headline number) — it does NOT validate the area-ratio impact against
ABS, which needs a wall-to-wall re-run this script does not do. `NEXT_STEPS.md` §6.2's acceptance
criterion is explicit that both numbers are required, or neither counts as a fix; treat this as
the first of the two, not a finished result.

    python3 phenology_gate.py --indices "$D/samgeo/ts_v2/*_SENSITIVE.csv" \
        --labeled $D/nvt_trials_labeled.csv --keep $D/keep_arms/keep_reviewed_SENSITIVE.csv \
        --out $REPO/output/PHENOLOGY_GATE.md --model-out $D/models/phenology_gate.joblib
"""
import argparse
import glob

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

AMP_THRESHOLD = 0.35   # the current production --crop-gate-amp, for a like-for-like comparison
TARGET_RECALL = 0.916  # the current gate's own headline recall, PRESENCE_ONLY_LABELS.md


def load_ts(pats, min_clear_frac=0.5):
    files = sorted({f for p in pats for f in glob.glob(p)})
    if not files:
        raise SystemExit(f"no files matched {pats}")
    t = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    t = t.drop_duplicates(["TrialCode", "time"])
    t = t[t.n_clear_px / t.n_px_paddock.clip(lower=1) >= min_clear_frac]
    t["time"] = pd.to_datetime(t["time"])
    return t


def trial_shape_features(g, sow, harv, ndvi_col):
    """ORACLE variant: windows anchored on the trial's own recorded sow/harv dates.

    Not deployable — a wall-to-wall map has no sow/harv date per polygon. This is the upper
    bound: how good is the shape signal when the season's true boundaries are known exactly.
    """
    d, v = g["time"], g[ndvi_col]
    in_season = (d >= sow) & (d <= harv + pd.Timedelta(days=30))
    pre_sow = (d >= sow - pd.Timedelta(days=60)) & (d <= sow - pd.Timedelta(days=14))
    post_harv = (d >= harv + pd.Timedelta(days=14)) & (d <= harv + pd.Timedelta(days=75))
    if in_season.sum() < 3:
        return None
    peak = v[in_season].max()
    if not np.isfinite(peak) or peak <= 0:
        return None
    pre_val = v[pre_sow].median() if pre_sow.sum() >= 1 else np.nan
    post_val = v[post_harv].median() if post_harv.sum() >= 1 else np.nan
    q = v[in_season | pre_sow | post_harv]
    amp = (q.quantile(0.9) - q.quantile(0.1)) if len(q) >= 3 else np.nan
    return {
        "peak_ndvi": peak,
        "greenup_rise": ((peak - pre_val) / peak) if pd.notna(pre_val) else np.nan,
        "senescence_drop": ((peak - post_val) / peak) if pd.notna(post_val) else np.nan,
        "amp": amp,
        "n_pre": int(pre_sow.sum()), "n_post": int(post_harv.sum()),
        "n_in_season": int(in_season.sum()),
    }


def trial_shape_features_deployable(g, ndvi_col):
    """DEPLOYABLE variant: windows anchored on the series' OWN detected peak, not an external
    sow/harv date. This is what `predict_tile.py` can actually compute for any polygon — it
    already builds this same per-date series for the amplitude gate, just needs the peak's date.
    """
    d, v = g["time"], g[ndvi_col]
    if len(v) < 3 or not np.isfinite(v.max()) or v.max() <= 0:
        return None
    peak = v.max()
    peak_date = d[v.idxmax()]
    pre = (d >= peak_date - pd.Timedelta(days=120)) & (d <= peak_date - pd.Timedelta(days=30))
    post = (d >= peak_date + pd.Timedelta(days=45)) & (d <= peak_date + pd.Timedelta(days=150))
    pre_val = v[pre].median() if pre.sum() >= 1 else np.nan
    post_val = v[post].median() if post.sum() >= 1 else np.nan
    amp = (v.quantile(0.9) - v.quantile(0.1)) if len(v) >= 3 else np.nan
    return {
        "peak_ndvi": peak,
        "greenup_rise": ((peak - pre_val) / peak) if pd.notna(pre_val) else np.nan,
        "senescence_drop": ((peak - post_val) / peak) if pd.notna(post_val) else np.nan,
        "amp": amp,
        "n_pre": int(pre.sum()), "n_post": int(post.sum()),
    }


def fit_gate(feat, target_recall, cols):
    """Smallest per-column percentile (searched jointly) that keeps >= target_recall of `feat`.

    Presence-only, exactly as the amplitude gate was fit: no negative class, just "what cutoff
    keeps most of what we know is a real crop". Searches a shared percentile `p` for every
    feature in `cols` simultaneously (all must clear their own p-th percentile), so the gate
    stays a single one-knob choice like `--crop-gate-amp` rather than a per-feature grid.
    """
    best = None
    for p in np.arange(1, 40, 0.5):
        thr = {c: np.nanpercentile(feat[c], p) for c in cols}
        passed = np.all([feat[c].fillna(-np.inf) >= thr[c] for c in cols], axis=0)
        recall = passed.mean()
        if recall >= target_recall:
            best = (p, thr, recall)
    return best  # loosest (highest-p) threshold that still clears target_recall, or None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--indices", nargs="+", required=True)
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--keep", required=True)
    ap.add_argument("--min-obs", type=int, default=10)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model-out", default=None, help="optional: save fitted thresholds as joblib")
    args = ap.parse_args()

    ts = load_ts(args.indices)
    ndvi_col = next(c for c in ts.columns if "ndvi" in c and c.endswith("_pad_median"))
    lab = pd.read_csv(args.labeled).drop_duplicates("TrialCode")
    lab["sow"] = pd.to_datetime(lab["sow"], errors="coerce")
    lab["harv"] = pd.to_datetime(lab["harv"], errors="coerce")
    keep = set(pd.read_csv(args.keep).TrialCode)

    ts = ts[ts.TrialCode.isin(keep)]
    n = ts.groupby("TrialCode").size()
    ts = ts[ts.TrialCode.isin(set(n[n >= args.min_obs].index))]

    lab_idx = lab.set_index("TrialCode")
    oracle_rows, deploy_rows = [], []
    for tc, g in ts.groupby("TrialCode"):
        fd = trial_shape_features_deployable(g, ndvi_col)
        if fd is not None:
            fd["TrialCode"] = tc
            deploy_rows.append(fd)
        if tc not in lab_idx.index:
            continue
        row = lab_idx.loc[tc]
        sow, harv = row.get("sow"), row.get("harv")
        if pd.isna(sow) or pd.isna(harv):
            continue
        fo = trial_shape_features(g, sow, harv, ndvi_col)
        if fo is not None:
            fo["TrialCode"] = tc
            oracle_rows.append(fo)

    def clean(rows):
        f = pd.DataFrame(rows).set_index("TrialCode")
        return f[f[["greenup_rise", "senescence_drop", "amp"]].notna().all(axis=1)]

    feat_oracle = clean(oracle_rows)
    feat_deploy = clean(deploy_rows)
    print(f"oracle (true sow/harv): {len(feat_oracle)} trials usable")
    print(f"deployable (self-detected peak): {len(feat_deploy)} trials usable")

    def evaluate(feat, seed):
        """K-fold: fit thresholds on 4 folds (presence-only), measure recall on the 5th."""
        skf = StratifiedKFold(n_splits=args.folds, shuffle=True, random_state=seed)
        fold_recalls, fold_amp_recalls, thresholds = [], [], []
        dummy_y = np.zeros(len(feat))  # only one class here; StratifiedKFold just needs a y
        for tr_idx, te_idx in skf.split(feat, dummy_y):
            tr, te = feat.iloc[tr_idx], feat.iloc[te_idx]
            fit = fit_gate(tr, TARGET_RECALL, ["greenup_rise", "senescence_drop"])
            if fit is None:
                continue
            _, thr, _ = fit
            thresholds.append(thr)
            passed_te = np.all([te[c] >= thr[c] for c in thr], axis=0)
            fold_recalls.append(passed_te.mean())
            fold_amp_recalls.append((te["amp"] >= AMP_THRESHOLD).mean())
        mean_recall = float(np.mean(fold_recalls))
        full_fit = fit_gate(feat, TARGET_RECALL, ["greenup_rise", "senescence_drop"])
        final_thr = ({c: round(v, 4) for c, v in full_fit[1].items()} if full_fit
                     else {c: float(np.mean([t[c] for t in thresholds])) for c in thresholds[0]})
        return mean_recall, final_thr, fold_recalls, float(np.mean(fold_amp_recalls))

    oracle_recall, oracle_thr, oracle_folds, oracle_amp = evaluate(feat_oracle, args.seed)
    deploy_recall, deploy_thr, deploy_folds, deploy_amp = evaluate(feat_deploy, args.seed)

    # ---- what the deployable shape gate adds beyond amplitude, on the same positives ----
    shape_pass = np.all([feat_deploy[c] >= deploy_thr[c] for c in deploy_thr], axis=0)
    amp_pass = feat_deploy["amp"] >= AMP_THRESHOLD
    both = (shape_pass & amp_pass).mean()
    amp_only = (amp_pass & ~shape_pass).mean()
    shape_only = (shape_pass & ~amp_pass).mean()
    neither = (~shape_pass & ~amp_pass).mean()

    lines = [
        "# A phenology-SHAPE presence gate — green-up timing + post-harvest senescence",
        "",
        "**Two variants, because one of them cannot be deployed.** The ORACLE variant windows "
        "on each trial's own recorded `sow`/`harv` date — the literal reading of "
        "\"one green-up at the right time, ending in a hard senescence\" — but a wall-to-wall map "
        "has no sow/harv date for an arbitrary polygon, so it cannot run at inference. The "
        "DEPLOYABLE variant windows on the series' own DETECTED peak instead (no external date "
        "needed) — what `predict_tile.py` can actually compute for every polygon. Both are "
        "reported so the cost of not knowing the true date is visible, not hidden.",
        "",
        f"- oracle: {len(feat_oracle)} trials with a usable sow/harv date and clear observations "
        "either side of it",
        f"- deployable: {len(feat_deploy)} trials with >= 3 clear observations "
        f"(of {ts.TrialCode.nunique()} passing --min-obs)",
        "",
        "**Scope, stated up front.** Both variants measure held-out PRESENCE RECALL only — the "
        "same kind of number `PRESENCE_ONLY_LABELS.md` reports for the amplitude gate (91.6 %, "
        "over a different, larger population — see the caveat below the recall table). Neither "
        "measures the area-ratio impact against ABS, which needs a wall-to-wall re-run. "
        "`NEXT_STEPS.md` §6.2's acceptance criterion needs both numbers; this is the first, and "
        "only for the deployable variant does closing it out even make sense.",
        "",
        "## The gates",
        "",
        f"Both conditions must clear their threshold in each variant (fit presence-only: the "
        f"loosest percentile of the training positives that still keeps >= {TARGET_RECALL:.1%} "
        f"of them, {args.folds}-fold cross-validated):",
        "",
        "| | oracle (sow/harv-anchored) | deployable (peak-anchored) |",
        "|---|---|---|",
        f"| `greenup_rise` >= | {oracle_thr['greenup_rise']:.3f} | {deploy_thr['greenup_rise']:.3f} |",
        f"| `senescence_drop` >= | {oracle_thr['senescence_drop']:.3f} | {deploy_thr['senescence_drop']:.3f} |",
        "",
        "## Held-out recall, vs. the current amplitude gate on the same rows",
        "",
        "**Not directly comparable to `PRESENCE_ONLY_LABELS.md`'s 91.6% headline** — that number "
        "is over the full 3,439 known-sown trials; both populations here are smaller (hand-"
        "reviewed geometry, `--keep keep_reviewed`, plus — for oracle — a usable sow/harv date). "
        "Within each column the two gates ARE comparable, because they share a population:",
        "",
        "| gate | oracle population | deployable population |",
        "|---|---|---|",
        f"| current (`ndvi_amp >= {AMP_THRESHOLD}`) | {oracle_amp:.1%} | {deploy_amp:.1%} |",
        f"| **phenology-shape** (this gate) | **{oracle_recall:.1%}** | **{deploy_recall:.1%}** |",
        "",
        f"Fold recalls, oracle: " + ", ".join(f"{r:.1%}" for r in oracle_folds),
        f"\n\nFold recalls, deployable: " + ", ".join(f"{r:.1%}" for r in deploy_folds),
        "",
        f"**The deployable variant gives up {(oracle_recall - deploy_recall) * 100:.1f} points "
        f"of recall relative to oracle** for the same target — the measurable cost of not "
        "knowing the true sow/harv date. This is the number that matters for shipping: the "
        "oracle column is a ceiling, not a candidate.",
        "",
        "## What the deployable shape gate adds beyond amplitude",
        "",
        "Same deployable-variant population, both gates applied (not a validation — these are "
        "all known-sown positives, so this shows *agreement*, not *correctness*):",
        "",
        "| | passes amplitude | fails amplitude |",
        "|---|---|---|",
        f"| **passes shape** | {both:.1%} | {shape_only:.1%} |",
        f"| **fails shape** | {amp_only:.1%} | {neither:.1%} |",
        "",
        f"**{amp_only:.1%} of known-sown trials clear the amplitude gate but fail the shape "
        f"gate** — high amplitude with no clean green-up-then-senescence pattern around the "
        f"series' own peak. On a real crop these are false rejections (the cost of the shape "
        f"gate being stricter); on sown-but-not-harvested land the amplitude gate over-admits, "
        f"and the same mechanism should reject more of it — untested here, because that "
        f"population has no clean label left in this repo (see the AgriWebb removal).",
        "",
        "## Next step to close out the NEXT_STEPS.md §6.2 criterion",
        "",
        "The deployable thresholds above are saved to the model bundle and are wireable into "
        "`predict_tile.py` as `--crop-gate-shape` (see the flag's help text — it is NOT the "
        "default; §6.2 needs the area-ratio number before that would be justified). Re-run a "
        "validation region (the 100 km Riverina block already has 9 years of ground truth) with "
        "it enabled, and re-score with `abs_compare.py`. Only if the area ratio moves toward 1.0 "
        "*while* this recall number holds does §6.2's bar get cleared.",
    ]
    with open(args.out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"-> {args.out}")

    if args.model_out:
        import joblib
        joblib.dump({
            "variant": "deployable_peak_anchored",
            "thresholds": deploy_thr,
            "cols": list(deploy_thr.keys()),
            "target_recall": TARGET_RECALL,
            "held_out_recall": deploy_recall,
            "n_train": len(feat_deploy),
            "fold_recalls": deploy_folds,
            "pre_window_days": [120, 30],   # relative to detected peak
            "post_window_days": [45, 150],  # relative to detected peak
        }, args.model_out)
        print(f"-> {args.model_out}")


if __name__ == "__main__":
    main()
