#!/usr/bin/env python3
"""
Sample paddocks that are probably NOT crop, so the classifier can learn to say "none of these".

WHY THIS IS NEEDED. Every training paddock so far is an NVT trial site, so the model has seen
Canola, Cereal and Legume and nothing else. Deployed nationally it meets a landscape that is
87 % grazing (287.9 Mha against 35.8 Mha for the three crop groups) and a three-way softmax has
no way to abstain — it will call pasture Cereal at a rate nothing in this project bounds.

THE SAMPLING DESIGN IS THE WHOLE POINT, and the obvious version of it is useless. Sampling
"high grazing probability" nationally lands in the Nullarbor and the Barkly, where the negatives
are trivially separable and teach the model nothing about its actual failure: a pasture paddock
sitting between two wheat paddocks in the Wimmera. So tiles are stratified by how much cropping
is in the NEIGHBOURHOOD:

  hard  grazing is high, crop is low HERE, but the surrounding ~25 km is cropping country.
        These are the negatives that matter — same soils, same climate, same rainfall, same
        paddock geometry as the crops, differing only in what is growing.
  easy  grazing high, crop low here and nearby. Rangeland. Included as a minority so the
        class covers the range the model will actually meet, and as a control: if the model
        cannot even reject these, the hard ones are hopeless.

WHAT THE LABEL IS WORTH. NLUM is a probability surface, not ground truth, so "likely grazing"
is a prior and not a label — which is exactly why these polygons go to human review before any
of them is used for training. A negative class built from NLUM alone would bake NLUM's errors
into the model and then be evaluated as if it were independent of NLUM.

Three modes:
  tiles    sample AOIs and write an aois csv for presegment.pbs / sam_segment.pbs
  package  after segmentation, build a single review GeoPackage for QGIS
  sites    turn those polygons into pseudo-trials so extract_paddock.py can run on them

WHY `sites` EXISTS RATHER THAN A SECOND EXTRACTOR. The negatives' features must be computed by
the same code, over the same bands, with the same erosion and the same tree mask as the crop
paddocks — otherwise a fourth class would be separable on extraction artefacts and the model
would look like it had learnt "not a crop" when it had learnt "came from the other script".
`extract_paddock.py` is point-driven, so each polygon is handed back its own representative
point (guaranteed interior, unlike a centroid) and matches itself under the `contains` rule.
Run it with `--no-upgrade`, or the upgrade rule may move a pseudo-trial onto a larger neighbour.

Not sensitive: NLUM is public and no trial records are involved.
"""
import argparse
import glob
import os

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

ALBERS = "EPSG:3577"
GRAZ = ["NLUM_v7_probSurf_2021_210_1_GRAZ_NOTIMBNP.tif",
        "NLUM_v7_probSurf_2021_320_3_GRAZ_NOTIMBSP.tif"]
CROP = ["NLUM_v7_probSurf_2021_331_5_W_CER.tif",
        "NLUM_v7_probSurf_2021_334_10_W_OILSEEDS.tif",
        "NLUM_v7_probSurf_2021_338_8_W_LEGUMES.tif"]


def coarse(path, tr, W, H, ref):
    with rasterio.open(path) as s:
        a = s.read(1).astype(np.float32)
        a = np.where(a == s.nodata, 0.0, a) / 1e4
        out = np.zeros((H, W), np.float32)
        reproject(a, out, src_transform=s.transform, src_crs=s.crs,
                  dst_transform=tr, dst_crs=ALBERS, resampling=Resampling.average)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["tiles", "package", "sites"])
    ap.add_argument("--nlum-dir", help="required by tiles mode only")
    ap.add_argument("--half-m", type=float, default=1500.0)
    ap.add_argument("--year", type=int, default=2021)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--hard-frac", type=float, default=0.7)
    ap.add_argument("--graz-min", type=float, default=0.50)
    ap.add_argument("--crop-max", type=float, default=0.05)
    ap.add_argument("--nbr-crop-min", type=float, default=0.20,
                    help="neighbourhood crop probability that makes a tile 'hard'")
    ap.add_argument("--nbr-km", type=float, default=25.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    # package mode
    ap.add_argument("--polydir", help="segmentation output dir (package mode)")
    ap.add_argument("--aois", help="the aois csv written by tiles mode (package mode)")
    # sites mode
    ap.add_argument("--gpkg", help="the review GeoPackage written by package mode (sites mode)")
    ap.add_argument("--verdict", nargs="*", default=[],
                    help="keep only these reviewer verdicts; default keeps every polygon so "
                         "the extraction can run before the review is finished")
    args = ap.parse_args()

    import pandas as pd

    if args.mode == "tiles":
        edge = 2 * args.half_m
        ref = os.path.join(args.nlum_dir, CROP[0])
        with rasterio.open(ref) as s:
            tr, W, H = calculate_default_transform(
                s.crs, ALBERS, s.width, s.height, *s.bounds, resolution=edge)
        g = sum(coarse(os.path.join(args.nlum_dir, f), tr, W, H, ref) for f in GRAZ)
        c = sum(coarse(os.path.join(args.nlum_dir, f), tr, W, H, ref) for f in CROP)

        # Neighbourhood cropping intensity: a box mean at ~nbr_km, which is what separates
        # "pasture in a cropping district" from "pasture in the rangelands".
        from scipy.ndimage import uniform_filter
        k = max(3, int(round(args.nbr_km * 1000 / edge)) | 1)
        nbr = uniform_filter(c, size=k, mode="constant")

        elig = (g >= args.graz_min) & (c <= args.crop_max)
        hard = elig & (nbr >= args.nbr_crop_min)
        easy = elig & (nbr < args.nbr_crop_min)
        print(f"tile grid {W}x{H} at {edge/1000:g} km; neighbourhood {k} tiles "
              f"(~{k*edge/1000:.0f} km)")
        print(f"eligible tiles: {int(elig.sum()):,}  hard {int(hard.sum()):,}  "
              f"easy {int(easy.sum()):,}")

        rng = np.random.default_rng(args.seed)
        n_hard = int(round(args.n * args.hard_frac))
        rows = []
        from pyproj import Transformer
        to_wgs = Transformer.from_crs(ALBERS, "EPSG:4326", always_xy=True)
        for name, m, want in [("hard", hard, n_hard), ("easy", easy, args.n - n_hard)]:
            ys, xs = np.nonzero(m)
            if len(ys) == 0:
                print(f"  no {name} tiles available")
                continue
            pick = rng.choice(len(ys), size=min(want, len(ys)), replace=False)
            for i in pick:
                x = tr.c + (xs[i] + 0.5) * tr.a
                y = tr.f + (ys[i] + 0.5) * tr.e
                lon, lat = to_wgs.transform(x, y)
                rows.append({"stub": f"graz_{args.year}_{name}_r{ys[i]}_c{xs[i]}",
                             "lat": round(lat, 6), "lon": round(lon, 6),
                             "half_m": int(args.half_m),
                             "start": f"{args.year}-01-01", "end": f"{args.year}-12-31",
                             "year": args.year, "n_trials": 0,
                             "stratum": name,
                             "graz_prob": round(float(g[ys[i], xs[i]]), 3),
                             "crop_prob": round(float(c[ys[i], xs[i]]), 4),
                             "nbr_crop_prob": round(float(nbr[ys[i], xs[i]]), 3)})
        d = pd.DataFrame(rows)
        d.to_csv(args.out, index=False)
        print(f"\nsampled {len(d)} tiles ({(d.stratum=='hard').sum()} hard, "
              f"{(d.stratum=='easy').sum()} easy) -> {args.out}")
        print(d.groupby("stratum")[["graz_prob", "crop_prob", "nbr_crop_prob"]]
              .median().round(3).to_string())
        return

    if args.mode == "sites":
        import geopandas as gpd
        P = gpd.read_file(args.gpkg).to_crs(ALBERS)
        if args.verdict:
            before = len(P)
            P = P[P.verdict.fillna("").isin(args.verdict)]
            print(f"verdict filter {args.verdict}: {before} -> {len(P)} polygons")
            if P.empty:
                raise SystemExit("no polygons left; has the review been filled in?")
        pt = P.geometry.representative_point().to_crs("EPSG:4326")
        # The read window must cover the DOY 90-350 bins train_species.py pivots on, and
        # extract_paddock.py pads by 30 days on each side, so these two dates are chosen to
        # land exactly on that span. They are not agronomic dates and nothing reads them as
        # such — the features are binned on calendar DOY, not on days after sowing.
        d = pd.DataFrame({
            "TrialCode": P.poly_id.values,
            "aoi_stub": P.stub.values,
            "lon": pt.x.round(6).values, "lat": pt.y.round(6).values,
            "sow": [f"{int(y)}-04-30" for y in P.year],
            "harv": [f"{int(y)}-11-16" for y in P.year],
            "Year": P.year.astype(int).values,
            "crop": "NotCrop",
            "stratum": P.stratum.values,
            "area_ha": P.area_ha.round(1).values,
        })
        d.to_csv(args.out, index=False)
        print(f"{len(d)} pseudo-trials -> {args.out}")
        print(d.groupby("stratum").agg(n=("TrialCode", "size"),
                                       median_ha=("area_ha", "median")).round(1).to_string())
        return

    # ---- package mode ----
    import geopandas as gpd
    aois = pd.read_csv(args.aois).set_index("stub")
    parts = []
    # `_filt.gpkg` is samgeo_segment's post-filter output (min/max area, compactness); the
    # unfiltered `_segment.gpkg` beside it still holds the 1-pixel specks and the whole-tile blobs.
    for f in sorted(glob.glob(os.path.join(args.polydir, "*_filt.gpkg"))):
        stub = os.path.basename(f).replace("_filt.gpkg", "")
        if stub not in aois.index:
            continue
        p = gpd.read_file(f).to_crs(ALBERS)
        if p.empty:
            continue
        a = aois.loc[stub]
        p["stub"] = stub
        for c in ["stratum", "graz_prob", "crop_prob", "nbr_crop_prob", "year"]:
            p[c] = a[c]
        parts.append(p)
    if not parts:
        raise SystemExit(f"no *_filt.gpkg found in {args.polydir}")
    P = pd.concat(parts, ignore_index=True)
    P = gpd.GeoDataFrame(P, geometry="geometry", crs=ALBERS)
    P["area_ha"] = P.geometry.area / 1e4
    P["compactness"] = P.geometry.length / (2 * np.sqrt(np.pi * P.geometry.area))
    P = P[(P.area_ha >= 5) & (P.area_ha <= 1000)].reset_index(drop=True)
    P["poly_id"] = [f"g{i:05d}" for i in range(len(P))]
    # The two columns the reviewer fills in. `verdict` is deliberately free of a default so an
    # unreviewed polygon is distinguishable from one judged unusable.
    P["verdict"] = ""
    P["note"] = ""
    P["label"] = (P.poly_id + " | " + P.stratum + " | " +
                  P.area_ha.round(0).astype(int).astype(str) + " ha")
    keep = ["poly_id", "stub", "stratum", "graz_prob", "crop_prob", "nbr_crop_prob",
            "year", "area_ha", "compactness", "verdict", "note", "label", "geometry"]
    P[keep].to_crs("EPSG:4326").to_file(args.out, layer="grazing_candidates", driver="GPKG")
    print(f"{len(P)} polygons from {P.stub.nunique()} tiles -> {args.out}")
    print(P.groupby("stratum").agg(n=("poly_id", "size"),
                                   median_ha=("area_ha", "median")).round(1).to_string())


if __name__ == "__main__":
    main()
