#!/usr/bin/env python3
"""
Pull Fields of The World field-boundary polygons for Australian AOIs, cheaply.

The FTW global product is 8.2B polygons / ~629 GB of GeoParquet on Source Cooperative, so
downloading it is out of the question. Two properties make a targeted read possible:
  * the 1,001 part files are spatially COHERENT (part-00000 is South America), so most can
    be excluded on their file-level bbox alone;
  * each file carries per-row-group bbox.xmin/xmax/ymin/ymax statistics, so within a
    relevant file only the overlapping row groups need fetching.

So the cost is a one-off footer scan (cached) plus a few MB of range reads per AOI, rather
than a bulk download.

    # 1. one-off: build the file bbox index (~1,001 footer reads, threaded)
    python3 ftw_fetch.py index --out /scratch/.../ftw_file_index.csv

    # 2. per-AOI: fetch polygons around trial sites
    python3 ftw_fetch.py fetch --index /scratch/.../ftw_file_index.csv \
        --sites /scratch/.../nvt_trials_labeled.csv --buffer-m 500 \
        --out /scratch/.../ftw_paddocks.gpkg

Needs outbound internet: run on a gadi LOGIN node (compute nodes have none, unless the job
is submitted to -q copyq).
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

BASE = ("https://data.source.coop/ftw/global-data/predictions/vectors/alpha/results/")
LIST = "https://data.source.coop/ftw/?list-type=2&prefix=global-data/predictions/vectors/alpha/results/"


def list_parts():
    """Every part-*.parquet key, following S3 continuation tokens.

    Uses curl rather than urllib: this endpoint 403s on urllib's default User-Agent and
    then 503s consistently even with a spoofed one, while curl succeeds every time. Not
    worth reverse-engineering which header it dislikes.
    """
    import re
    import subprocess
    from urllib.parse import quote
    keys, token = [], None
    while True:
        # Continuation tokens contain +, / and = which must be percent-encoded,
        # otherwise the second page 4xx/5xxs and the listing silently truncates.
        url = LIST + "&max-keys=1000" + (
            f"&continuation-token={quote(token, safe='')}" if token else "")
        x = ""
        for attempt in range(5):
            r = subprocess.run(["curl", "-sS", "--max-time", "120", url],
                               capture_output=True, text=True)
            if r.returncode == 0 and "<ListBucketResult" in r.stdout:
                x = r.stdout
                break
            time.sleep(2 ** attempt)
        if not x:
            raise RuntimeError("S3 listing failed after retries")
        keys += [k for k in re.findall(r"<Key>([^<]+)</Key>", x) if k.endswith(".parquet")]
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", x)
        if not m:
            break
        token = m.group(1)
    return [k.rsplit("/", 1)[-1] for k in keys]


def file_bbox(name):
    """(west, south, east, north) for one part file, from its GeoParquet footer."""
    import fsspec
    import pyarrow.parquet as pq
    fs = fsspec.filesystem("http")
    f = pq.ParquetFile(fs.open(BASE + name))
    md = f.schema_arrow.metadata or {}
    bb = None
    if b"geo" in md:
        g = json.loads(md[b"geo"])
        for spec in g.get("columns", {}).values():
            if "bbox" in spec:
                bb = spec["bbox"]
    return name, bb, f.metadata.num_rows, f.metadata.num_row_groups


def cmd_index(args):
    names = list_parts()
    print(f"{len(names)} part files; reading footers with {args.workers} threads...")
    rows, t0 = [], time.time()
    with ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(file_bbox, n): n for n in names}
        for i, fu in enumerate(as_completed(futs), 1):
            try:
                n, bb, nrows, nrg = fu.result()
                if bb:
                    rows.append({"file": n, "west": bb[0], "south": bb[1], "east": bb[2],
                                 "north": bb[3], "rows": nrows, "row_groups": nrg})
            except Exception as e:
                print(f"  {futs[fu]}: {type(e).__name__}", file=sys.stderr)
            if i % 100 == 0:
                print(f"  {i}/{len(names)} ({time.time()-t0:.0f}s)", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False)
    au = df[(df.east > 112) & (df.west < 155) & (df.north > -45) & (df.south < -9)]
    print(f"\nwrote {args.out}: {len(df)} files, {time.time()-t0:.0f}s")
    print(f"files overlapping Australia: {len(au)} ({100*len(au)/max(len(df),1):.1f}%), "
          f"{au['rows'].sum()/1e6:.1f}M polygons")


def cmd_fetch(args):
    import fsspec
    import geopandas as gpd
    import pyarrow.parquet as pq
    import numpy as np
    from shapely.geometry import box

    idx = pd.read_csv(args.index)
    sites = pd.read_csv(args.sites)
    if "clean" in sites.columns:
        sites = sites[sites["clean"]]
    if args.limit:
        sites = sites.head(args.limit)
    dlat = args.buffer_m / 111320.0
    sites["w"] = sites.lon - dlat / np.cos(np.radians(sites.lat))
    sites["e"] = sites.lon + dlat / np.cos(np.radians(sites.lat))
    sites["s"] = sites.lat - dlat
    sites["n"] = sites.lat + dlat
    W, S, E, N = sites.w.min(), sites.s.min(), sites.e.max(), sites.n.max()
    print(f"{len(sites)} sites, overall bbox {W:.2f},{S:.2f} .. {E:.2f},{N:.2f}")

    cand = idx[(idx.east > W) & (idx.west < E) & (idx.north > S) & (idx.south < N)]
    print(f"candidate files: {len(cand)}/{len(idx)}")
    aois = [box(r.w, r.s, r.e, r.n) for r in sites.itertuples()]
    _s = gpd.GeoSeries(aois, crs="EPSG:4326")
    # union_all() is geopandas >=1.0; this env has 0.14.2 where it is unary_union.
    aoi_union = _s.union_all() if hasattr(_s, "union_all") else _s.unary_union

    fs = fsspec.filesystem("http")
    parts, t0 = [], time.time()
    for j, fn in enumerate(cand.file, 1):
        pf = pq.ParquetFile(fs.open(BASE + fn))
        keep_rg = []
        for i in range(pf.metadata.num_row_groups):
            rg = pf.metadata.row_group(i)
            st = {rg.column(c).path_in_schema: rg.column(c).statistics
                  for c in range(rg.num_columns)}
            try:
                if (st["bbox.xmax"].max > W and st["bbox.xmin"].min < E and
                        st["bbox.ymax"].max > S and st["bbox.ymin"].min < N):
                    keep_rg.append(i)
            except Exception:
                keep_rg.append(i)
        if not keep_rg:
            continue
        print(f"  [{j}/{len(cand)}] {fn[:28]}… row groups {len(keep_rg)}/{pf.metadata.num_row_groups}",
              flush=True)
        tbl = pf.read_row_groups(keep_rg, columns=["geometry", "time", "label", "bbox"])
        g = gpd.GeoDataFrame.from_arrow(tbl) if hasattr(gpd.GeoDataFrame, "from_arrow") else \
            gpd.GeoDataFrame(tbl.to_pandas(), geometry=gpd.GeoSeries.from_wkb(
                tbl.column("geometry").to_pandas()), crs="EPSG:4326")
        g = g[g.intersects(aoi_union)]
        if len(g):
            parts.append(g)

    if not parts:
        raise SystemExit("no polygons intersected the AOIs")
    out = pd.concat(parts, ignore_index=True)
    out = gpd.GeoDataFrame(out, geometry="geometry", crs="EPSG:4326")
    out.to_file(args.out, driver="GPKG")
    print(f"\nwrote {args.out}: {len(out)} polygons in {time.time()-t0:.0f}s")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("index"); a.add_argument("--out", required=True)
    a.add_argument("--workers", type=int, default=16); a.set_defaults(f=cmd_index)
    b = sub.add_parser("fetch")
    b.add_argument("--index", required=True); b.add_argument("--sites", required=True)
    b.add_argument("--out", required=True); b.add_argument("--buffer-m", type=float, default=500)
    b.add_argument("--limit", type=int); b.set_defaults(f=cmd_fetch)
    args = ap.parse_args()
    args.f(args)


if __name__ == "__main__":
    main()
