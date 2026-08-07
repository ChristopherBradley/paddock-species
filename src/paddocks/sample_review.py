#!/usr/bin/env python3
"""
Draw a stratified sample of trials for review, one stratum per flag category.

The worst-first ordering in `review_sites.csv` is right for a human working down a queue, but
wrong for *measuring* how good the matching is: it oversamples the tail and tells you nothing
about the 55 % that carry no flags. To decide where review effort is worth spending you need
an error rate PER CATEGORY, which means sampling each category — including the clean one.

    python3 sample_review.py --review .../review_full/review_sites.csv \
        --out .../review_full/sample.csv --per-stratum 12

Strata are the flag categories plus `clean` and `none` (no polygon matched). A trial carrying
several flags is assigned to its rarest one, so small categories actually get filled rather
than being swallowed by common co-occurring flags.

Each stratum is sampled with a fixed seed, so the sample is reproducible and a later
exhaustive pass can exclude exactly what was already reviewed.
"""
import argparse

import numpy as np
import pandas as pd

FLAGS = ["not_contained", "edge_close", "treed", "tiny", "bigger_neighbour", "sliver"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-stratum", type=int, default=12)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    d = pd.read_csv(args.review)
    d["flags"] = d["flags"].fillna("")
    present = [f for f in FLAGS if d["flags"].str.contains(f).any()]
    freq = {f: int(d["flags"].str.contains(f).sum()) for f in present}

    def stratum(row):
        if str(row.get("match_rule", "")) == "none":
            return "none"
        fl = [f for f in present if f in row["flags"]]
        if not fl:
            return "clean"
        return min(fl, key=lambda f: freq[f])      # rarest flag wins

    d["stratum"] = d.apply(stratum, axis=1)
    rng = np.random.default_rng(args.seed)
    out = []
    for s, g in d.groupby("stratum"):
        n = min(args.per_stratum, len(g))
        out.append(g.iloc[rng.choice(len(g), n, replace=False)].assign(stratum=s))
    samp = pd.concat(out).sort_values(["stratum", "TrialCode"])
    samp["claude_verdict"] = ""
    samp["claude_note"] = ""
    samp.to_csv(args.out, index=False)

    print(f"population {len(d)} trials")
    print(f"{'stratum':20s} {'population':>10s} {'sampled':>8s}")
    for s, g in d.groupby("stratum"):
        n = int((samp["stratum"] == s).sum())
        print(f"{s:20s} {len(g):10d} {n:8d}")
    print(f"\n-> {args.out} ({len(samp)} trials, "
          f"{int(np.ceil(len(samp)/12))} sheets at 12/sheet)")


if __name__ == "__main__":
    main()
