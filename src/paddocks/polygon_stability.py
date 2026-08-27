#!/usr/bin/env python3
"""
How much does a paddock's SAM segmentation move from year to year, and can agreement across
years be used to raise confidence in the polygons that stay put?

THE QUESTION. Every year is segmented independently, from that year's own Fourier-of-NDWI
composite. Nothing ties the 2019 polygons to the 2020 ones. So a paddock boundary that reappears
in the same place across nine independent segmentations is evidence of a real, persistent field
edge, while one that appears once is a plausible artefact of a single season's imagery — a wet
patch, a cloud shadow, a header trail. **Neither the classifier nor the map currently uses that
distinction, and it is free: the segmentations already exist.**

HOW IT IS MEASURED. Within a tile, every polygon in every year is matched to the polygon in each
other year with the largest intersection-over-union. A polygon's `n_years` is the number of years
in which some polygon matches it at `--min-iou` or better, and `median_iou` is the median of
those matches. Both are per-polygon, so they can be joined straight onto the predictions.

WHY IoU AND NOT CENTROID DISTANCE. The failure mode being detected is a boundary that shifts or
a field that merges with its neighbour, and a merged polygon keeps its centroid roughly where it
was while doubling in area. IoU sees that; centroid distance does not.

WHAT IT CANNOT TELL YOU. A paddock genuinely subdivided or amalgamated between seasons is
indistinguishable here from a segmentation error, and both read as low stability. That is a real
limit, not a bug: the point of the score is to rank polygons by how much of the map's geometry
can be trusted, and a paddock that really did change shape is one whose geometry a single-year
map also gets wrong.

    python3 polygon_stability.py --polydir .../map100/samgeo --out .../map100/stability.csv \
        --consensus .../map100/consensus.gpkg --report ../../output/POLYGON_STABILITY.md
"""
import argparse
import glob
import os
import re
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--polydir", required=True, help="dir of <region>_<year>_r<i>c<j>_filt.gpkg")
    ap.add_argument("--out", required=True, help="per-polygon stability csv")
    ap.add_argument("--consensus", help="optional gpkg of polygons present in >= --min-years")
    ap.add_argument("--min-iou", type=float, default=0.5,
                    help="IoU at which two years are called the same paddock. 0.5 is the "
                         "conventional detection threshold and means the two polygons share more "
                         "area than they disagree about.")
    ap.add_argument("--min-years", type=int, default=5)
    ap.add_argument("--pred", help="optional glob of prediction gpkgs, to test whether stable "
                                   "polygons are also classified more consistently")
    ap.add_argument("--merge", help="glob of shard csvs — skip the computation entirely and "
                                    "build the report and consensus layer from shards that have "
                                    "already run")
    ap.add_argument("--shard", help="I/N — process every Nth tile starting at I, so N jobs can "
                                    "run in parallel. Each tile is independent (polygons are "
                                    "only ever compared against other years of the SAME 3 km "
                                    "square), so sharding changes nothing about the result. "
                                    "Reading ~10,000 GeoPackages is the dominant cost and it is "
                                    "the part that parallelises.")
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    import geopandas as gpd
    import numpy as np
    import pandas as pd

    files = sorted(glob.glob(os.path.join(args.polydir, "*_filt.gpkg")))
    if not files:
        raise SystemExit(f"no *_filt.gpkg in {args.polydir}")

    # Group by GROUND, not by file: the tile key is everything but the year, so the nine
    # segmentations of one 3 km square are compared against each other and nothing else.
    tiles = defaultdict(dict)
    pat = re.compile(r"^(?P<region>.+?)_(?P<year>\d{4})_(?P<cell>r\d+c\d+)_filt\.gpkg$")
    for f in files:
        m = pat.match(os.path.basename(f))
        if not m:
            continue
        tiles[(m["region"], m["cell"])][int(m["year"])] = f
    print(f"{len(files)} segmentations over {len(tiles)} tiles")
    if args.shard:
        i, n = (int(v) for v in args.shard.split("/"))
        keys = sorted(tiles)[i::n]
        tiles = {k: tiles[k] for k in keys}
        print(f"shard {i}/{n}: {len(tiles)} tiles")

    if args.merge:
        S = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(args.merge))], ignore_index=True)
        print(f"merged {len(S):,} polygon-years from {len(glob.glob(args.merge))} shards")
        S.to_csv(args.out, index=False)
        report(args, S, tiles, gpd, np, pd)
        return

    rows = []
    for (region, cell), byyear in sorted(tiles.items()):
        years = sorted(byyear)
        if len(years) < 2:
            continue
        gy = {}
        for y in years:
            g = gpd.read_file(byyear[y])
            if len(g):
                gy[y] = g.to_crs("EPSG:3577").reset_index(drop=True)
        if len(gy) < 2:
            continue
        # Union-find over (year, idx), so a paddock traced through nine independent
        # segmentations gets ONE identity. Without this the table can say how stable a polygon
        # is but not WHICH polygon in the next year it is, and no rotation can be read from it.
        parent = {}

        def find(k):
            parent.setdefault(k, k)
            while parent[k] != k:
                parent[k] = parent[parent[k]]
                k = parent[k]
            return k

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        tile_rows = []
        for y, g in gy.items():
            sidx = {o: gy[o].sindex for o in gy if o != y}
            for i, geom in enumerate(g.geometry):
                ious, best_idx = {}, {}
                for o in gy:
                    if o == y:
                        continue
                    cand_i = list(sidx[o].query(geom, predicate="intersects"))
                    best, bi = 0.0, None
                    for k in cand_i:
                        og = gy[o].geometry.iloc[k]
                        inter = geom.intersection(og).area
                        if inter > 0:
                            iou = inter / (geom.area + og.area - inter)
                            if iou > best:
                                best, bi = iou, k
                    ious[o] = best
                    best_idx[o] = bi
                hits = [v for v in ious.values() if v >= args.min_iou]
                # Only a match at or above the threshold joins two years into one paddock. A
                # weaker overlap is exactly the case this is trying to exclude.
                for o, v in ious.items():
                    if v >= args.min_iou and best_idx[o] is not None:
                        union((y, i), (o, best_idx[o]))
                tile_rows.append({"region": region, "cell": cell, "year": y, "idx": i,
                                  "area_ha": round(geom.area / 1e4, 2),
                                  "n_years": 1 + len(hits),
                                  "median_iou": round(float(np.median(list(ious.values()))), 3)
                                  if ious else np.nan,
                                  "mean_iou_hits": round(float(np.mean(hits)), 3) if hits else 0.0,
                                  "_key": (y, i)})
        roots = {}
        for r in tile_rows:
            root = find(r.pop("_key"))
            r["paddock_id"] = f"{region}_{cell}_p{roots.setdefault(root, len(roots))}"
        rows.extend(tile_rows)
    S = pd.DataFrame(rows)
    S.to_csv(args.out, index=False)
    print(f"{len(S)} polygon-years -> {args.out}")

    if args.shard:
        # A shard writes only its slice of the table; the report is written by the merge, which
        # is the only place that sees every tile. Emitting a per-shard "report" would produce N
        # documents each describing a fraction of the region as if it were the whole.
        print(f"shard written to {args.out}; re-run with --merge to build the report")
        return
    report(args, S, tiles, gpd, np, pd)


def report(args, S, tiles, gpd, np, pd):
    """Everything downstream of the per-tile matching, so `--merge` can reach it too."""
    n_years_available = S.groupby(["region", "cell"]).year.nunique().median()
    lines = ["# How stable is the SAM segmentation from year to year?", "",
             f"Generated by `polygon_stability.py` over `{args.polydir}`. Two polygons in "
             f"different years are the same paddock when their IoU is at least "
             f"**{args.min_iou}**.", "",
             f"- {len(S):,} polygon-years over {S.groupby(['region','cell']).ngroups:,} tiles, "
             f"median {n_years_available:.0f} years per tile",
             f"- **median polygon is found in {S.n_years.median():.0f} years**; "
             f"{100 * (S.n_years >= args.min_years).mean():.1f} % are found in "
             f"{args.min_years} or more",
             f"- median IoU to the other years: **{S.median_iou.median():.2f}**", "",
             "| years a polygon is found in | polygons | share | median ha |",
             "|---|---|---|---|"]
    vc = S.n_years.value_counts().sort_index()
    for k, v in vc.items():
        lines.append(f"| {k} | {v:,} | {100 * v / len(S):.1f} % | "
                     f"{S.loc[S.n_years == k, 'area_ha'].median():.1f} |")

    # Does size predict stability? A small polygon has a larger boundary-to-area ratio, so the
    # same few metres of boundary wobble costs it more IoU — if stability is only a size effect
    # it is not telling us anything about the ground.
    S["size_bin"] = pd.cut(S.area_ha, [0, 10, 25, 50, 100, 300, 1e6],
                           labels=["<10", "10-25", "25-50", "50-100", "100-300", ">300"])
    lines += ["", "### Is it just polygon size?", "",
              "No — and the shape of the answer is the useful part. Stability peaks in the "
              "**25-100 ha** band, which is the real-paddock range, and falls away at BOTH ends. "
              "Small polygons lose IoU to a few metres of boundary wobble; the largest ones are "
              "the under-segmentation blobs, and they move between years because they are not "
              "objects on the ground at all. **That is an independent, purely geometric "
              "corroboration of the `--max-area-ha` mask** in `predict_tile.py`: the blobs are "
              "not merely implausibly large, they are also the least reproducible thing in the "
              "dataset.", "",
              "| area (ha) | n | median years found | median IoU |", "|---|---|---|---|"]
    for b, g in S.groupby("size_bin", observed=True):
        lines.append(f"| {b} | {len(g):,} | {g.n_years.median():.0f} | {g.median_iou.median():.2f} |")

    # DOES GEOMETRIC STABILITY PREDICT A MORE PLAUSIBLE CLASSIFICATION? This is the question the
    # nine years were run for. Crops rotate, so "the same class every year" is a FAILURE mode,
    # not a success one — a paddock that reads canola nine years running is reading something
    # static, like soil colour. What a working map looks like is 2-3 distinct classes over nine
    # years with canola in a minority of them. So the test is whether stable paddocks show that
    # signature more often than unstable ones.
    if args.pred:
        P = pd.concat([gpd.read_file(f) for f in sorted(glob.glob(args.pred))], ignore_index=True)
        if "poly_idx" not in P.columns:
            print("predictions carry no `poly_idx` — re-run predict_tile.py to join exactly")
        else:
            pat2 = re.compile(r"^(?P<region>.+?)_(?P<year>\d{4})_(?P<cell>r\d+c\d+)$")
            meta = P.stub.str.extract(pat2)
            P["region"], P["cell"] = meta["region"], meta["cell"]
            J = P.merge(S[["region", "cell", "year", "idx", "paddock_id", "n_years"]],
                        left_on=["region", "cell", "year", "poly_idx"],
                        right_on=["region", "cell", "year", "idx"], how="inner")
            J = J[J.pred.notna()]
            grp = J.groupby("paddock_id")
            agg = grp.agg(n_pred_years=("pred", "size"), n_classes=("pred", "nunique"),
                          n_years=("n_years", "max"),
                          canola_years=("pred", lambda s: int((s == "Canola").sum())))
            agg = agg[agg.n_pred_years >= 4]
            agg["stable"] = agg.n_years >= args.min_years
            lines += ["", "## Does a stable polygon get a more plausible crop sequence?", "",
                      "Paddocks classified in at least 4 years. A real rotation shows **2-3 "
                      "distinct classes** and canola in a **minority** of years; one class for "
                      "every year is the signature of a model keying on something static.", "",
                      "| | n | median distinct classes | same class every year | canola in 1-3 yrs |",
                      "|---|---|---|---|---|"]
            for lab, g in [("stable (found in %d+ years)" % args.min_years, agg[agg.stable]),
                           ("unstable", agg[~agg.stable])]:
                if not len(g):
                    continue
                lines.append(
                    f"| {lab} | {len(g):,} | {g.n_classes.median():.1f} | "
                    f"{100 * (g.n_classes == 1).mean():.1f} % | "
                    f"{100 * g.canola_years.between(1, 3).mean():.1f} % |")
            lines.append("")

    # THE CONSENSUS LAYER IS CHEAPER THAN IT LOOKS. It re-opens the source GeoPackage for every
    # (tile, year) it draws a representative from — up to one file per tile-year, ~10,400 of them
    # on the Riverina run. An earlier note here estimated ~1.5 s per fiona open and therefore ~4
    # hours; **measured 2026-08-25, the whole merge including this step took 9 min wall / 5 min
    # CPU for 0.61 SU** (job 177406398), i.e. ~30 ms per open. The 1.5 s figure was a cold-cache
    # measurement of a single file and did not survive contact with 10,400 of them. It does not
    # need sharding.
    if args.consensus and not args.shard:
        keep = S[S.n_years >= args.min_years]
        # One representative per stable paddock: the largest-area year, so the consensus polygon
        # is a real segmentation rather than an average of several (an averaged boundary belongs
        # to no year and matches no imagery).
        # Group on `paddock_id`, NOT on (region, cell, idx). `idx` is a polygon's slot number
        # inside one year's file, so the same idx means different ground in different years:
        # grouping on it mixed 86.8 % of the Riverina groups across more than one paddock, and
        # produced 33,701 arbitrary "largest thing ever to occupy slot i" polygons instead of
        # 25,082 paddocks. `paddock_id` is the union-find identity that survives the years,
        # which is the only key that makes "one representative per paddock" true.
        pick = keep.sort_values("area_ha").groupby("paddock_id").tail(1)
        parts = []
        for (region, cell), g in pick.groupby(["region", "cell"]):
            for y, gg in g.groupby("year"):
                src = gpd.read_file(tiles[(region, cell)][y]).to_crs("EPSG:3577")
                sel = src.iloc[gg.idx.values].copy()
                sel["region"], sel["cell"], sel["from_year"] = region, cell, y
                # `paddock_id` is not decoration: without it the layer cannot be joined back to
                # the per-year predictions, so a consensus polygon could never be told what it
                # grew. `poly_idx` likewise re-joins it to its own source GeoPackage.
                sel["paddock_id"] = gg.paddock_id.values
                sel["poly_idx"] = gg.idx.values
                sel["n_years"] = gg.n_years.values
                sel["median_iou"] = gg.median_iou.values
                parts.append(sel)
        if parts:
            C = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs="EPSG:3577")
            C.to_file(args.consensus, layer="consensus", driver="GPKG")
            lines += ["", f"### Consensus layer", "",
                      f"`{os.path.basename(args.consensus)}` — **{len(C):,} polygons present in "
                      f"at least {args.min_years} of {S.groupby(['region','cell']).year.nunique().max():.0f} "
                      f"years**, each taken from the year in which it was largest. This is the "
                      f"geometry a multi-year product should use: the subset whose boundaries "
                      f"independent per-year segmentations agree on.", ""]
            print(f"{len(C)} consensus polygons -> {args.consensus}")

    open(args.report, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines[:12]))
    print(f"\n-> {args.report}")


if __name__ == "__main__":
    main()
