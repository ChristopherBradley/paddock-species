#!/usr/bin/env python3
"""
Combine reviewer verdicts into per-stratum error rates, and measure reviewer agreement.

Two outputs, and the second gates the first:

1. **Error rate per flag category.** The sample is stratified, so each category's rate is
   estimated from its own draw and can be extrapolated to that category's population. This
   is what decides where exhaustive review is worth the effort.
2. **Agreement on the overlap set**, where two reviewers saw identical panels. Without it the
   error rates are unfalsifiable: a reviewer that is confidently inconsistent produces
   plausible-looking numbers. Low agreement means the verdicts need discounting, and the
   human spot-check should target the disagreements first.

    python3 aggregate_review.py --sample .../sample.csv --verdicts .../verdicts_w*.csv \
        --qc .../verdicts_qc.csv --out .../REVIEW_CALIBRATION.md

Wilson intervals rather than normal approximation: with 12 per stratum, a 0/12 or 12/12
result would otherwise get a zero-width interval, which is exactly the wrong impression.
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd

# Verdicts meaning "these pixels are usable for the trial's crop".
OK = {"good", "trial_plot"}


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    d = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", required=True)
    ap.add_argument("--verdicts", nargs="+", required=True)
    ap.add_argument("--qc")
    ap.add_argument("--population", help="full review_sites.csv, to scale rates up")
    ap.add_argument("--out")
    args = ap.parse_args()

    samp = pd.read_csv(args.sample)
    # The sample carries EMPTY annotation columns for the human (verdict/note/claude_*).
    # Left in place they collide with the reviewer files on merge and become verdict_x/_y.
    samp = samp.drop(columns=[c for c in ("verdict", "note", "claude_verdict", "claude_note")
                              if c in samp.columns])
    files = [f for pat in args.verdicts for f in sorted(glob.glob(pat))]
    v = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    v = v.drop_duplicates("TrialCode", keep="first")
    d = samp.merge(v, on="TrialCode", how="left")

    L = ["# Trial→paddock match review — calibration\n",
         f"Reviewed {d.verdict.notna().sum()} of {len(samp)} sampled trials "
         f"from {len(files)} reviewer file(s).\n"]

    missing = d[d.verdict.isna()]
    if len(missing):
        L.append(f"**{len(missing)} sampled trials have no verdict** — "
                 "treat their strata as under-sampled.\n")

    L.append("## Verdict distribution\n")
    vc = d.verdict.value_counts()
    L.append("| verdict | n | share |")
    L.append("|---|---|---|")
    for k, n in vc.items():
        L.append(f"| `{k}` | {n} | {n/vc.sum():.0%} |")

    pop = None
    if args.population and os.path.exists(args.population):
        pop = pd.read_csv(args.population)

    L.append("\n## Usable rate per stratum (`good` or `trial_plot`)\n")
    L.append("| stratum | reviewed | usable | rate | 95% CI | population | est. bad |")
    L.append("|---|---|---|---|---|---|---|")
    tot_bad = 0
    for s, g in d.groupby("stratum"):
        g = g[g.verdict.notna()]
        if not len(g):
            continue
        k = int(g.verdict.isin(OK).sum())
        lo, hi = wilson(k, len(g))
        npop = ""
        est = ""
        if pop is not None:
            m = (pop["flags"].fillna("").str.contains(s) if s not in ("clean", "none")
                 else (pop["flags"].fillna("") == "") if s == "clean"
                 else (pop["match_rule"].fillna("") == "none"))
            npop = int(m.sum())
            est = int(round(npop * (1 - k / len(g))))
            tot_bad += est
        L.append(f"| `{s}` | {len(g)} | {k} | {k/len(g):.0%} | "
                 f"[{lo:.0%}, {hi:.0%}] | {npop} | {est} |")
    if pop is not None:
        L.append(f"\nExtrapolated unusable matches across the dataset: **~{tot_bad}**. "
                 "Strata overlap (a trial can carry several flags), so this double-counts "
                 "and is an upper bound, not a total.")

    if args.qc and os.path.exists(args.qc):
        q = pd.read_csv(args.qc).drop_duplicates("TrialCode")
        both = d.merge(q, on="TrialCode", suffixes=("", "_qc")).dropna(
            subset=["verdict", "verdict_qc"])
        if len(both):
            exact = (both.verdict == both.verdict_qc).mean()
            usable = (both.verdict.isin(OK) == both.verdict_qc.isin(OK)).mean()
            L.append(f"\n## Reviewer agreement (overlap n={len(both)})\n")
            L.append(f"- exact verdict match: **{exact:.0%}**")
            L.append(f"- agree on usable vs not: **{usable:.0%}** "
                     "(the decision that actually matters downstream)")
            dis = both[both.verdict != both.verdict_qc]
            if len(dis):
                L.append(f"\nDisagreements ({len(dis)}) — **review these first**:\n")
                L.append("| TrialCode | stratum | reviewer A | reviewer B |")
                L.append("|---|---|---|---|")
                for _, r in dis.iterrows():
                    L.append(f"| {r.TrialCode} | `{r.stratum}` | "
                             f"`{r.verdict}` | `{r.verdict_qc}` |")

    bad = d[d.verdict.notna() & ~d.verdict.isin(OK)]
    if len(bad):
        L.append(f"\n## Trials judged unusable ({len(bad)}) — shortlist to verify\n")
        L.append("| TrialCode | stratum | verdict | note |")
        L.append("|---|---|---|---|")
        for _, r in bad.iterrows():
            note = str(r.get("note", "") or "")[:70]
            L.append(f"| {r.TrialCode} | `{r.stratum}` | `{r.verdict}` | {note} |")

    text = "\n".join(L)
    print(text)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text + "\n")
        print(f"\n-> {args.out}")


if __name__ == "__main__":
    main()
