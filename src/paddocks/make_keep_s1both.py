#!/usr/bin/env python3
"""
The keep set that makes an optical-vs-S1 comparison fair.

WHY THIS EXISTS. A paddock with no Sentinel-1 coverage still has optical features, so an
optical arm scores it and an S1-only arm cannot. Scoring both on the same nominal row list
therefore does NOT control the comparison — it taxes whichever arm is blind on those rows. The
first S1 run lost a real +0.044 that way: 66 of 543 test rows had no backscatter, were scored
anyway with every S1 feature NaN, and dragged the combined arm back to a dead heat with optical.
(The opposite error, letting each arm pick its own easier rows, produced the +0.107 mirage in
REVIEWED_MODEL.md. Same root cause, opposite sign.)

So: intersect down to the rows every arm can actually answer, and state the row count loudly
wherever the scores are quoted. The alternative — imputing the missing backscatter — would put
a model's guess into the input and then measure that model.

Filters mirror train_species.py exactly: the >=50 % clear-pixel rule from its loader and the
--min-obs floor. If either changes there, change it here or the keep set silently stops
matching the rows the model actually builds.

SENSITIVE: writes TrialCodes, so /scratch only.
"""
import argparse
import glob

import pandas as pd


def load(pat):
    files = sorted(glob.glob(pat))
    if not files:
        raise SystemExit(f"no files matched {pat}")
    t = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    t = t.drop_duplicates(["TrialCode", "time"])
    return t[t.n_clear_px / t.n_px_paddock.clip(lower=1) >= 0.5]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indices", required=True)
    ap.add_argument("--s1", required=True)
    ap.add_argument("--keep", required=True, help="keep_reviewed_SENSITIVE.csv")
    ap.add_argument("--test-keep", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-obs", type=int, default=10)
    args = ap.parse_args()

    keep = set(pd.read_csv(args.keep).TrialCode)
    n = {}
    for name, pat in [("optical", args.indices), ("s1", args.s1)]:
        t = load(pat)
        t = t[t.TrialCode.isin(keep)]
        c = t.groupby("TrialCode").size()
        n[name] = set(c[c >= args.min_obs].index)
        print(f"{name}: {len(n[name])} of {len(keep)} reviewed-good trials clear {args.min_obs} obs")

    both = sorted(n["optical"] & n["s1"])
    pd.DataFrame({"TrialCode": both}).to_csv(args.out, index=False)
    test = set(pd.read_csv(args.test_keep).TrialCode)
    kept = len(test & set(both))
    print(f"BOTH: {len(both)} trials -> {args.out}")
    print(f"test rows retained: {kept} of {len(test)} "
          f"({100 * kept / len(test):.1f} %) — quote this next to every score")


if __name__ == "__main__":
    main()
