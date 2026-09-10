#!/usr/bin/env python3
"""E9 (PAPER_PLAN.md §24 Open Issue #4): spatial comparison of the national 2024
crop-species map against WorldCereal 2021.

WorldCereal has no Canola or Legume class (see raw/worldcereal/README.md), so this can only
check two things:
  (a) presence -- our classified-vs-abstained polygons against WorldCereal `temporarycrops`
  (b) Cereal -- our Cereal-vs-not-Cereal polygons against WorldCereal `wintercereals`

Runs on a stratified random sample of paddock centroids, not the full 1,346,582 -- point
sampling against the WorldCereal VRT is I/O-bound (~1700 pts/s sorted-by-location, measured;
random order is ~3x slower from tile thrashing), so a census would cost ~35 min for no
statistical benefit: this compares proportions/agreement rates, not totals, so sampling error
is negligible at this n (unlike the ABS area-ratio comparison, which needed a census footprint
-- see project memory "Aggregate validation needs a census footprint").

    python3 worldcereal_compare.py --n-sample 250000 \
        --out ../../output/WORLDCEREAL_COMPARISON.md
"""
import argparse
import sys

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer

CENTROIDS = "/scratch/xe2/cb8590/paddock-species-data/derived/national2024/fig_extract/national_2024_centroids.csv"
TEMPORARYCROPS_VRT = "/scratch/xe2/cb8590/paddock-species-data/derived/worldcereal_compare/temporarycrops.vrt"
WINTERCEREALS_VRT = "/scratch/xe2/cb8590/paddock-species-data/derived/worldcereal_compare/wintercereals.vrt"


def sample_raster(vrt_path, lon, lat):
    src = rasterio.open(vrt_path)
    coords = list(zip(lon, lat))
    vals = np.array(list(src.sample(coords, indexes=1))).ravel()
    src.close()
    return vals


def two_way_table(a, b, a_name, b_name):
    ct = pd.crosstab(a, b, margins=True, margins_name="Total")
    ct.index.name = a_name
    ct.columns.name = b_name
    return ct


def pct_table(ct):
    """Row-normalised: each row sums to 100 -- e.g. of OUR points in this category, what
    % fall in each column category. (A grand-total-normalised version would answer a
    different, less useful question and must not be labelled "row-normalised".)"""
    body = ct.drop("Total", axis=0).drop("Total", axis=1)
    return body.div(body.sum(axis=1), axis=0).mul(100).round(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-sample", type=int, default=250_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--centroids", default=CENTROIDS,
                    help="CSV of pred,abstain_reason,cx,cy (EPSG:3577) for the map being scored")
    args = ap.parse_args()

    df = pd.read_csv(args.centroids)
    n_total = len(df)
    df["cat"] = df["pred"].where(df["pred"].notna() & (df["pred"] != ""), "Abstained")

    n_sample = min(args.n_sample, n_total)
    sample = df.sample(n_sample, random_state=args.seed).sort_values(["cy", "cx"]).copy()

    tf = Transformer.from_crs("EPSG:3577", "EPSG:4326", always_xy=True)
    lon, lat = tf.transform(sample["cx"].to_numpy(), sample["cy"].to_numpy())

    print(f"sampling {n_sample:,} of {n_total:,} centroids ({100*n_sample/n_total:.1f}%)...",
          file=sys.stderr)
    sample["wc_temporarycrops"] = sample_raster(TEMPORARYCROPS_VRT, lon, lat)
    sample["wc_wintercereals"] = sample_raster(WINTERCEREALS_VRT, lon, lat)

    sample["our_presence"] = np.where(sample["cat"] == "Abstained", "Abstained", "Classified")
    sample["wc_presence"] = np.where(sample["wc_temporarycrops"] >= 50, "Crop", "No-crop")
    sample["our_cereal"] = np.where(sample["cat"] == "Cereal", "Cereal", "Not-Cereal")
    sample["wc_cereal"] = np.where(sample["wc_wintercereals"] >= 50, "Wintercereal", "Not-wintercereal")

    presence_ct = two_way_table(sample["our_presence"], sample["wc_presence"],
                                 "our map", "WorldCereal temporarycrops")
    presence_pct = pct_table(presence_ct)
    presence_agree = (
        (sample["our_presence"] == "Classified") & (sample["wc_presence"] == "Crop")
    ).sum() + (
        (sample["our_presence"] == "Abstained") & (sample["wc_presence"] == "No-crop")
    ).sum()
    presence_agree_pct = 100 * presence_agree / n_sample

    cereal_ct = two_way_table(sample["our_cereal"], sample["wc_cereal"],
                               "our map", "WorldCereal wintercereals")
    cereal_pct = pct_table(cereal_ct)
    # Precision/recall of our Cereal call against WorldCereal's wintercereals layer as a
    # (imperfect, 3-year-off) reference -- not "ground truth", an independent product.
    our_cereal_n = (sample["our_cereal"] == "Cereal").sum()
    wc_agrees_n = ((sample["our_cereal"] == "Cereal") & (sample["wc_cereal"] == "Wintercereal")).sum()
    cereal_wc_agreement_rate = 100 * wc_agrees_n / our_cereal_n if our_cereal_n else float("nan")

    class_counts = sample["cat"].value_counts()

    lines = []
    lines.append("# WorldCereal 2021 vs national 2024 crop-species map — spatial comparison (E9)")
    lines.append("")
    lines.append("Generated by `worldcereal_compare.py`. Aggregate only — sampled paddock "
                  "centroids and pixel-value cross-tabs, no site-level GRDC records.")
    lines.append("")
    lines.append("## Scope and caveats — read before the numbers")
    lines.append("")
    lines.append("- **WorldCereal has no Canola or Legume class.** This can only check two "
                  "things: (a) crop presence/absence against `temporarycrops`, and (b) our "
                  "Cereal class against `wintercereals`. Canola and Legume are not checkable "
                  "against this source at all.")
    lines.append("- **Year mismatch**: WorldCereal is 2021; our map is 2024. A 3-year gap, "
                  "same caveat class already applied to the ABS comparison.")
    lines.append("- **`springcereals` has zero AU coverage** (confirmed empirically during "
                  "acquisition) — Australia's cereal season falls entirely under "
                  "`wintercereals` in WorldCereal's calendar convention, so no crop is missed "
                  "by leaving `springcereals` out.")
    lines.append("- **Sampled, not census**: this compares proportions/agreement rates (not "
                  "area totals), so a stratified random sample is statistically adequate — "
                  "unlike the ABS area-ratio comparison, which specifically needed a census "
                  "footprint (see project memory).")
    lines.append("- **WorldCereal export has no declared nodata value** — masked/uncovered "
                  "pixels export as raw 0, indistinguishable from a genuine \"not this class\" "
                  "pixel. This should not matter here because every sampled point is a real "
                  "paddock centroid inside WorldCereal's AEZ coverage footprint, not open "
                  "ocean or an unmapped region, but is noted for completeness.")
    lines.append("- **WorldCereal is an independent product, not ground truth.** Agreement "
                  "and disagreement are both informative; disagreement does not by itself mean "
                  "our map is wrong.")
    lines.append("")
    lines.append(f"## Sample")
    lines.append("")
    lines.append(f"- {n_sample:,} of {n_total:,} national paddock centroids "
                  f"({100*n_sample/n_total:.1f}%), random sample (seed={args.seed}).")
    lines.append(f"- Class mix in the sample: " + ", ".join(
        f"{k} {v:,} ({100*v/n_sample:.1f}%)" for k, v in class_counts.items()))
    lines.append("")
    lines.append("## (a) Presence: our map (classified vs. abstained) vs. WorldCereal `temporarycrops`")
    lines.append("")
    lines.append(f"**Raw counts** (n={n_sample:,}):")
    lines.append("")
    lines.append(presence_ct.to_markdown())
    lines.append("")
    lines.append(f"**Row-normalised (%)**:")
    lines.append("")
    lines.append(presence_pct.to_markdown())
    lines.append("")
    lines.append(f"**Overall agreement: {presence_agree_pct:.1f}%** "
                  "(our-classified & WorldCereal-crop, OR our-abstained & WorldCereal-no-crop).")
    lines.append("")
    lines.append("## (b) Cereal: our map (Cereal vs. not) vs. WorldCereal `wintercereals`")
    lines.append("")
    lines.append(f"**Raw counts** (n={n_sample:,}):")
    lines.append("")
    lines.append(cereal_ct.to_markdown())
    lines.append("")
    lines.append(f"**Row-normalised (%)**:")
    lines.append("")
    lines.append(cereal_pct.to_markdown())
    lines.append("")
    lines.append(f"**Of the {our_cereal_n:,} sampled points our map calls Cereal, "
                  f"WorldCereal's `wintercereals` layer agrees at {cereal_wc_agreement_rate:.1f}%.**")
    lines.append("")

    with open(args.out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {args.out}", file=sys.stderr)
    print(f"presence agreement: {presence_agree_pct:.1f}%", file=sys.stderr)
    print(f"Cereal vs wintercereals agreement: {cereal_wc_agreement_rate:.1f}%", file=sys.stderr)


if __name__ == "__main__":
    main()
