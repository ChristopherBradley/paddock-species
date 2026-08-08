#!/usr/bin/env python3
"""
Make the SAM input imagery findable by TrialCode.

The pre-segment composites are named by AOI (`aoi_2017_p1146_m0281.tif`), which is the right
key for the pipeline and the wrong one for a human reviewing a trial: there is no way to go
from a TrialCode in the review layer to the image SAM actually saw. This builds a directory of
SYMLINKS named `<TrialCode>_ndwi.tif`, plus a lookup CSV.

Symlinks, not copies: the composites total 1.6 GB and several trials share one AOI (3,222
trials over 2,382 AOIs), so copying would both waste space and create the possibility of two
divergent versions of the same image. Links are relative, so the tree can be moved or synced
without breaking.

WHAT THE IMAGE IS. Three uint8 bands holding the Fourier mean of an NDWI time series over the
AOI's season (`samgeo_segment.py build_image`, after PaddockTS `01_pre-segment.py`) — NOT a
plain RGB scene. Paddock boundaries are visible because fields differ in their wetness
trajectory across the season, which is why it segments well but does not look like imagery.
Judging whether a polygon follows a real paddock edge is best done against this, since it is
the evidence SAM had; judging whether the CROP is right needs true-colour imagery instead.

Also linked, when present:
  <TrialCode>_segment.tif  — SAM's raw mask
  <TrialCode>_filt.gpkg    — the filtered polygon set the matcher chose from
"""
import argparse
import glob
import os

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", nargs="+", required=True,
                    help="PREFIX=GLOB=POLYDIR triples, as for rematch_paddocks.py")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--csv", required=True, help="TrialCode -> file lookup")
    args = ap.parse_args()

    sites = []
    for spec in args.chunks:
        _, pat, polydir = spec.split("=", 2)
        for f in sorted(glob.glob(pat)):
            d = pd.read_csv(f)
            d["polydir"] = polydir
            sites.append(d)
    S = pd.concat(sites, ignore_index=True).drop_duplicates("TrialCode")
    os.makedirs(args.outdir, exist_ok=True)

    rows, made, missing = [], 0, 0
    for r in S.itertuples():
        stub, polydir = r.aoi_stub, r.polydir
        row = {"TrialCode": r.TrialCode, "Year": r.Year, "crop": r.crop,
               "aoi_stub": stub, "aoi_dir": polydir}
        for suffix, label in [(".tif", "ndwi"), ("_segment.tif", "segment"),
                              ("_filt.gpkg", "filt")]:
            src = os.path.join(polydir, f"{stub}{suffix}")
            if not os.path.exists(src):
                row[label] = ""
                if label == "ndwi":
                    missing += 1
                continue
            ext = ".gpkg" if suffix.endswith(".gpkg") else ".tif"
            dst = os.path.join(args.outdir, f"{r.TrialCode}_{label}{ext}")
            rel = os.path.relpath(src, args.outdir)
            if os.path.islink(dst) or os.path.exists(dst):
                os.remove(dst)
            os.symlink(rel, dst)
            row[label] = dst
            if label == "ndwi":
                made += 1
        rows.append(row)

    pd.DataFrame(rows).to_csv(args.csv, index=False)
    print(f"{len(S)} trials over {S.aoi_stub.nunique()} AOIs")
    print(f"  NDWI links created: {made}   AOIs with no composite: {missing}")
    print(f"-> {args.outdir}/<TrialCode>_ndwi.tif")
    print(f"-> {args.csv}")


if __name__ == "__main__":
    main()
