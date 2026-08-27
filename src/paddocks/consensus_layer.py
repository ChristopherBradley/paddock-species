#!/usr/bin/env python3
"""
Turn the raw consensus geometry into the layer a paper would actually publish: filtered to
paddock scale, and carrying what each paddock grew in every year.

WHAT THE CONSENSUS LAYER IS. `polygon_stability.py --consensus` writes one polygon per paddock
that nine independent annual segmentations agreed on (found in >= 5 of 9 years), taken from the
year in which it was largest. That is the geometry a multi-year product should use: it is not an
average of nine outlines — an averaged boundary belongs to no year and matches no imagery — it
is a real segmentation of a paddock the segmenter keeps finding.

WHY IT NEEDS FILTERING. The raw layer spans 1.1 to 1,101 ha, and both tails are known to be
unreal:
  * below `--min-area-ha` (5 ha, the `predict_tile.py` floor) a polygon is never classified in
    any year, so a consensus polygon there is an outline with no possible content;
  * above `--max-area-ha` (300 ha) is the under-segmentation blob — ground with no field
    boundaries returned as one shape. `POLYGON_STABILITY.md` corroborates this from a direction
    that owes nothing to the mask: the >300 ha band is found in a median of 5 years at median
    IoU 0.45, against 8 years and 0.94 in the 25-50 ha band. **The blobs are not merely
    implausibly large, they are the least reproducible thing in the dataset.**
The two thresholds are deliberately the SAME as the per-year map's, so the consensus layer never
contains a paddock the annual layers could not have classified.

WHAT IS ATTACHED. `crop_<year>` and `conf_<year>` for every year in the run, plus a rotation
summary. Note what the join means: the consensus outline is ONE year's geometry, while
`crop_2019` is the class of that paddock's 2019 polygon, whose boundary differs by a few metres.
That is the right join — the alternative, re-running inference against the consensus outline,
would report a class for a shape that year's imagery was never segmented into.

    python3 consensus_layer.py --consensus .../map100/consensus.gpkg \
        --attrs .../map100/attrs.parquet --out .../map100/consensus_crops.gpkg \
        --report ../../output/CONSENSUS_LAYER.md
"""
import argparse
import os

import numpy as np
import pandas as pd

CROPS = ["Canola", "Cereal", "Legume"]
SHORT = {"Canola": "C", "Cereal": "W", "Legume": "L"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--consensus", required=True)
    ap.add_argument("--attrs", required=True)
    ap.add_argument("--min-area-ha", type=float, default=5.0,
                    help="matches predict_tile.py --min-area-ha: below it no year is classified")
    ap.add_argument("--max-area-ha", type=float, default=300.0,
                    help="matches predict_tile.py --max-area-ha: above it is the blob band")
    ap.add_argument("--max-compactness", type=float, default=None,
                    help="P/sqrt(A); a square is 4.0 and a circle 3.54. Left off by default "
                         "because the segmentation filter has already applied one")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    import geopandas as gpd

    G = gpd.read_file(args.consensus)
    n0, ha0 = len(G), G.area_ha.sum()
    if "paddock_id" not in G.columns:
        raise SystemExit("consensus layer carries no paddock_id — rebuild it with the current "
                         "polygon_stability.py, otherwise nothing can be joined to it")

    small = G.area_ha < args.min_area_ha
    large = G.area_ha > args.max_area_ha
    drop = small | large
    if args.max_compactness and "compactness" in G.columns:
        drop = drop | (G.compactness > args.max_compactness)
    K = G[~drop].copy()
    print(f"{n0:,} -> {len(K):,} polygons after the area filter "
          f"({int(small.sum()):,} below {args.min_area_ha} ha, {int(large.sum()):,} above "
          f"{args.max_area_ha} ha)")

    T = pd.read_parquet(args.attrs) if args.attrs.endswith(".parquet") else pd.read_csv(args.attrs)
    T = T[T.paddock_id.notna()]
    years = sorted(T.year.unique())

    # A PADDOCK CAN HOLD TWO POLYGONS IN ONE YEAR, and the union-find is right to allow it: if
    # 2019's polygon A and 2019's polygon C both match 2020's polygon B above the IoU threshold,
    # they are the same ground and get one identity — a paddock that one season's segmentation
    # split in two. Measured on the Riverina run: **1,011 of 204,175 paddock-years (0.50 %)**,
    # and in 26.3 % of those the two halves were given DIFFERENT classes, which is worth knowing
    # because it is a within-paddock disagreement the per-year layers cannot show.
    #
    # Resolved by AREA, not by count: the class holding the most hectares that year wins, and
    # the confidence is the area-weighted mean. Taking the first row instead would let a 2 ha
    # sliver overrule the 40 ha paddock it was cut from.
    d = T[["paddock_id", "year", "pred", "confidence", "area_ha"]].dropna(subset=["paddock_id"])
    n_split = int((d.groupby(["paddock_id", "year"]).size() > 1).sum())
    by_class = (d[d.pred.notna()].groupby(["paddock_id", "year", "pred"])
                 .agg(ha=("area_ha", "sum"), conf=("confidence", "mean")).reset_index())
    win = by_class.sort_values("ha").groupby(["paddock_id", "year"]).tail(1)
    crop = win.pivot(index="paddock_id", columns="year", values="pred")
    conf = win.pivot(index="paddock_id", columns="year", values="conf")
    d = win.rename(columns={"conf": "confidence"})[["paddock_id", "year", "pred", "confidence"]]
    crop.columns = [f"crop_{y}" for y in crop.columns]
    conf.columns = [f"conf_{y}" for y in conf.columns]

    cls = d[d.pred.isin(CROPS)]
    summ = cls.groupby("paddock_id").agg(
        n_class_years=("pred", "size"),
        n_classes=("pred", "nunique"),
        canola_years=("pred", lambda s: int((s == "Canola").sum())),
        mean_conf=("confidence", "mean"))
    modal = cls.groupby("paddock_id").pred.agg(lambda s: s.value_counts().idxmax())
    summ["modal_crop"] = modal
    # A compact string like "W-C-W-.-L", one character per year in order, for QGIS labelling and
    # for eyeballing a rotation without reading nine columns.
    seq = (crop.reindex(columns=[f"crop_{y}" for y in years])
               .apply(lambda r: "-".join(SHORT.get(v, ".") for v in r), axis=1))
    summ["crop_seq"] = seq

    K = K.merge(crop, left_on="paddock_id", right_index=True, how="left")
    K = K.merge(conf, left_on="paddock_id", right_index=True, how="left")
    K = K.merge(summ, left_on="paddock_id", right_index=True, how="left")
    K["n_class_years"] = K.n_class_years.fillna(0).astype(int)
    K["canola_years"] = K.canola_years.fillna(0).astype(int)

    K.to_file(args.out, layer="consensus", driver="GPKG")
    print(f"{len(K):,} polygons x {len(K.columns)} columns -> {args.out}")

    L = ["# The consensus paddock layer", "",
         f"Generated by `consensus_layer.py` from `{os.path.basename(args.consensus)}`. One "
         f"polygon per paddock that at least 5 of the 9 annual segmentations agreed on, filtered "
         f"to paddock scale and carrying what it grew each year.", "",
         "## What the filter removed", "",
         "| | polygons | ha |", "|---|---|---|",
         f"| raw consensus | {n0:,} | {ha0:,.0f} |",
         f"| below {args.min_area_ha:g} ha (never classified in any year) | {int(small.sum()):,} | "
         f"{G.loc[small, 'area_ha'].sum():,.0f} |",
         f"| above {args.max_area_ha:g} ha (under-segmentation blobs) | {int(large.sum()):,} | "
         f"{G.loc[large, 'area_ha'].sum():,.0f} |",
         f"| **kept** | **{len(K):,}** | **{K.area_ha.sum():,.0f}** |", "",
         f"The blob band is {100 * G.loc[large, 'area_ha'].sum() / ha0:.0f} % of the raw layer's "
         f"area from {100 * large.mean():.1f} % of its polygons — which is why an unfiltered "
         f"consensus layer looks fine by polygon count and is dominated by blobs by area.", "",
         "## What the kept paddocks look like", "",
         "| | |", "|---|---|",
         f"| polygons | {len(K):,} |",
         f"| median area | {K.area_ha.median():.1f} ha |",
         f"| median years segmented | {K.n_years.median():.0f} of {len(years)} |",
         f"| median IoU across years | {K.median_iou.median():.2f} |",
         f"| median years classified | {K.n_class_years.median():.0f} |",
         f"| paddocks classified in every year | {int((K.n_class_years == len(years)).sum()):,} "
         f"({100 * (K.n_class_years == len(years)).mean():.1f} %) |",
         f"| paddock-years split into 2+ polygons | {n_split:,} (resolved by area) |", "",
         "## Rotation, over paddocks classified in at least 4 years", ""]
    R = K[K.n_class_years >= 4]
    L += [f"- **{len(R):,} paddocks**, median **{R.n_classes.median():.0f}** distinct classes",
          f"- one class in every classified year: **{100 * (R.n_classes == 1).mean():.1f} %** "
          f"— the signature of a model keying on something static, so lower is better",
          f"- canola in 1-3 years: **{100 * R.canola_years.between(1, 3).mean():.1f} %**", "",
          "| distinct classes | paddocks | share |", "|---|---|---|"]
    for k, v in R.n_classes.value_counts().sort_index().items():
        L.append(f"| {int(k)} | {v:,} | {100 * v / len(R):.1f} % |")
    L += ["", "## Most common rotations", "",
          "One character per year, in order: `C` canola, `W` cereal, `L` legume, `.` not "
          "classified that year.", "", "| sequence | paddocks |", "|---|---|"]
    for sq, v in R.crop_seq.value_counts().head(12).items():
        L.append(f"| `{sq}` | {v:,} |")
    L += ["", "## Columns", "",
          "| column | meaning |", "|---|---|",
          "| `paddock_id` | identity across the nine annual segmentations (union-find on IoU) |",
          "| `from_year` | the year whose segmentation supplied this outline |",
          "| `n_years`, `median_iou` | how many years found it, and how closely they agree |",
          "| `crop_<year>` | class of THAT year's polygon for this paddock; empty = abstained |",
          "| `conf_<year>` | the classifier's probability for that class |",
          "| `n_class_years`, `n_classes`, `canola_years`, `modal_crop`, `crop_seq` | rotation |",
          ""]
    open(args.report, "w").write("\n".join(L) + "\n")
    print(f"-> {args.report}")


if __name__ == "__main__":
    main()
