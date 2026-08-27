#!/usr/bin/env python3
"""
Split a sites csv into N chunks for parallel extraction, sorted so each chunk is spatially
and temporally compact.

WHY THE SORT MATTERS. Scene-cache locality is worth ~4x on datacube reads (see MEMORY.md):
two AOIs in the same year and the same corner of the country share most of their Sentinel-2
scenes, so a chunk built from neighbours re-reads far less than a chunk built from a random
shuffle. The sort costs nothing. Chunk *size* is worth almost nothing by comparison — pick a
count that keeps each job comfortably inside its walltime and stop tuning it.

Rows are ordered by (year, tile-x, tile-y) — the tile indices are already in `aoi_stub`, so
no reprojection is needed — then split into contiguous blocks. Because the sort key leads
with the stub, every row of a given tile-year lands in ONE chunk, which also means each
`<stub>_filt.gpkg` is opened by exactly one job.

    python3 chunk_sites.py --sites resites_SENSITIVE.csv --outdir sam_chunks --n 24 --prefix s
"""
import argparse
import os
import re

import pandas as pd


def sort_key(stub):
    """awt_<year>_<tx>_<ty> -> (year, tx, ty); anything else sorts last but stays grouped."""
    m = re.match(r"awt_(\d+)_(-?\d+)_(-?\d+)$", str(stub))
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (9999, 0, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", required=True, nargs="+", help="one or more sites csvs, concatenated")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--prefix", default="s")
    args = ap.parse_args()

    s = pd.concat([pd.read_csv(f) for f in args.sites], ignore_index=True)
    before = len(s)
    s = s.drop_duplicates(subset="TrialCode")
    if len(s) != before:
        print(f"dropped {before - len(s)} duplicate TrialCodes")
    s = s.sort_values("aoi_stub", key=lambda c: c.map(sort_key), kind="stable")

    os.makedirs(args.outdir, exist_ok=True)
    # Split on tile-year boundaries, not row boundaries, so one tile is never opened twice.
    groups = list(s.groupby("aoi_stub", sort=False))
    per = max(1, -(-len(groups) // args.n))
    for i in range(0, len(groups), per):
        block = pd.concat([g for _, g in groups[i:i + per]])
        out = os.path.join(args.outdir, f"{args.prefix}{i // per:02d}_SENSITIVE.csv")
        block.to_csv(out, index=False)
        print(f"{os.path.basename(out)}: {len(block)} rows, {block.aoi_stub.nunique()} tiles")
    print(f"{len(s)} rows, {len(groups)} tiles -> {-(-len(groups) // per)} chunks in {args.outdir}")


if __name__ == "__main__":
    main()
