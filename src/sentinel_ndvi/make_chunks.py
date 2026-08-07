#!/usr/bin/env python3
"""
Split the Stage-1 labelled trials into per-job chunk CSVs for Stage-2 extraction.

Keeps only clean + in-scope (Canola/Wheat by default) trials, then writes
chunk_000.csv, chunk_001.csv, ... into <outdir>/chunks/.

    python3 make_chunks.py \
        --labeled /scratch/xe2/cb8590/paddock-species-data/derived/nvt_trials_labeled.csv \
        --outdir  /scratch/xe2/cb8590/paddock-species-data/derived \
        --per-chunk 100 --crops Canola Wheat
"""
import argparse
import os

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--per-chunk", type=int, default=100)
    ap.add_argument("--crops", nargs="*", default=["Canola", "Wheat"])
    ap.add_argument("--all", action="store_true", help="ignore clean+crop filter")
    args = ap.parse_args()

    df = pd.read_csv(args.labeled)
    if not args.all:
        df = df[df["clean"] & df["crop"].isin(args.crops)]
    df = df[["TrialCode", "Year", "crop", "lat", "lon", "sow", "harv"]].reset_index(drop=True)
    chunk_dir = os.path.join(args.outdir, "chunks")
    os.makedirs(chunk_dir, exist_ok=True)
    n = 0
    for i in range(0, len(df), args.per_chunk):
        part = df.iloc[i:i + args.per_chunk]
        path = os.path.join(chunk_dir, f"chunk_{n:03d}.csv")
        part.to_csv(path, index=False)
        n += 1
    print(f"{len(df)} trials -> {n} chunks of <= {args.per_chunk} in {chunk_dir}")


if __name__ == "__main__":
    main()
