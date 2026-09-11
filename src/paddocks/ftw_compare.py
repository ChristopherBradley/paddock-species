#!/usr/bin/env python3
"""
Fields of the World (FTW) against this project's SAM boundaries, over a few hundred NVT sites.

`PADDOCK_BOUNDARY_BENCHMARK.md` compared the two sources at ONE site. One site cannot separate
"FTW merged this paddock" from "FTW merges paddocks", so this scales the same comparison to
every 2024 NVT trial and adds numbers to what was previously an eyeball judgement.

WHY THIS NEEDS ITS OWN FETCH. `ftw_fetch.py fetch` selects parquet row groups against the
OVERALL bounding box of all sites. That is fine for one site, but 557 sites spread from
Esperance to the Darling Downs give an overall box the size of the continent, so the test
selects 207 of 255 Australian row groups (~272M polygons). Testing each row group's own bbox
against the individual site AOIs instead selects 76 (~70M polygons), and filtering rows on the
`bbox` struct columns BEFORE building shapely geometries keeps peak memory at one row group.
Geometry is the expensive column; the bbox columns are four floats and are already downloaded
with it, so the prefilter is free.

    # fetch (needs internet: gadi login node or -q copyq)
    python3 ftw_compare.py fetch --index .../ftw_file_index.csv \
        --sites .../nvt_trials_labeled.csv --year 2024 --buffer-m 1000 \
        --out .../ftw_2024_sites_SENSITIVE.gpkg

    # compare (no internet needed)
    python3 ftw_compare.py compare --ftw .../ftw_2024_sites_SENSITIVE.gpkg \
        --sam .../national_2024_crops_final.gpkg \
        --sites .../nvt_trials_labeled.csv --year 2024 --buffer-m 1000 \
        --out output/FTW_COMPARISON.md \
        --detail-csv .../ftw_site_detail_SENSITIVE.csv

The markdown report is aggregate-only (no TrialCodes, no coordinates) and safe to commit. The
--detail-csv is per-trial and therefore SENSITIVE.
"""
import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

BASE = "https://data.source.coop/ftw/global-data/predictions/vectors/alpha/results/"
ALBERS = "EPSG:3577"
# The production retention filter, from the manuscript's Segmentation section. Applied to BOTH
# sources so the comparison is "what each source yields to this pipeline", not "what each
# source contains".
MIN_HA, MAX_HA, MAX_COMPACT = 5.0, 300.0, 8.0


def site_boxes(sites_csv, year, buffer_m):
    """Sites with a lat/lon box of +/- buffer_m around each trial point."""
    s = pd.read_csv(sites_csv)
    if year:
        s = s[s.Year == year]
    s = s.dropna(subset=["lat", "lon"]).copy()
    dlat = buffer_m / 111_320.0
    s["w"] = s.lon - dlat / np.cos(np.radians(s.lat))
    s["e"] = s.lon + dlat / np.cos(np.radians(s.lat))
    s["s"] = s.lat - dlat
    s["n"] = s.lat + dlat
    return s


def _open_retry(fs, url, attempts=6):
    """source.coop returns sporadic 503s; one of them killed a 17-minute run on 2026-09-11.

    Every read is retried with exponential backoff, and the ParquetFile is re-opened rather
    than reused, because a failed range request leaves the old handle's connection unusable.
    """
    import pyarrow.parquet as pq
    for a in range(attempts):
        try:
            return pq.ParquetFile(fs.open(url))
        except Exception as e:
            if a == attempts - 1:
                raise
            print(f"    open failed ({type(e).__name__}), retry {a+1}/{attempts-1}", flush=True)
            time.sleep(2 ** a)


def _read_rg_retry(fs, url, i, cols, attempts=6):
    for a in range(attempts):
        try:
            return _open_retry(fs, url).read_row_groups([i], columns=cols)
        except Exception as e:
            if a == attempts - 1:
                raise
            print(f"    rg {i} read failed ({type(e).__name__}), retry {a+1}/{attempts-1}",
                  flush=True)
            time.sleep(2 ** a)


def cmd_fetch(args):
    import fsspec
    import pyarrow.parquet as pq
    import geopandas as gpd
    from shapely.geometry import box
    from shapely.strtree import STRtree

    idx = pd.read_csv(args.index)
    s = site_boxes(args.sites, args.year, args.buffer_m)
    print(f"{len(s)} sites", flush=True)
    W, S, E, N = s.w.min(), s.s.min(), s.e.max(), s.n.max()
    boxes = [box(r.w, r.s, r.e, r.n) for r in s.itertuples()]
    tree = STRtree(boxes)
    aw, as_, ae, an = (s.w.values, s.s.values, s.e.values, s.n.values)

    cand = idx[(idx.east > W) & (idx.west < E) & (idx.north > S) & (idx.south < N)]
    print(f"candidate files {len(cand)}/{len(idx)}", flush=True)
    fs = fsspec.filesystem("http")
    # Per-row-group staging, so a dropped connection costs one row group and not the whole run.
    stage = args.stage_dir or (os.path.splitext(args.out)[0] + "_stage")
    os.makedirs(stage, exist_ok=True)
    parts, t0, n_rg, n_read = [], time.time(), 0, 0
    for j, fn in enumerate(cand.file, 1):
        pf = _open_retry(fs, BASE + fn)
        md = pf.metadata
        keep = []
        for i in range(md.num_row_groups):
            rg = md.row_group(i)
            st = {rg.column(c).path_in_schema: rg.column(c).statistics
                  for c in range(rg.num_columns)}
            try:
                x0, x1 = st["bbox.xmin"].min, st["bbox.xmax"].max
                y0, y1 = st["bbox.ymin"].min, st["bbox.ymax"].max
            except Exception:
                keep.append(i)
                continue
            # The row group's own extent against the individual AOIs, not their joint envelope.
            if len(tree.query(box(x0, y0, x1, y1))):
                keep.append(i)
        n_rg += len(keep)
        if not keep:
            continue
        for i in keep:
            sf = os.path.join(stage, f"{fn.split('-')[1]}_rg{i}.parquet")
            if os.path.exists(sf + ".empty"):
                continue
            if os.path.exists(sf):
                g = gpd.read_parquet(sf)
                parts.append(g)
                print(f"  [{j}/{len(cand)}] rg {i}: cached, {len(g)} polygons", flush=True)
                continue
            tbl = _read_rg_retry(fs, BASE + fn, i, ["geometry", "time", "label", "bbox"])
            bb = tbl.column("bbox").combine_chunks()
            xmin = np.asarray(bb.field("xmin")); xmax = np.asarray(bb.field("xmax"))
            ymin = np.asarray(bb.field("ymin")); ymax = np.asarray(bb.field("ymax"))
            # Any-AOI overlap, chunked so the row x AOI broadcast never allocates a huge array.
            hit = np.zeros(len(xmin), bool)
            step = 50_000
            for a in range(0, len(xmin), step):
                b = min(a + step, len(xmin))
                hit[a:b] = ((xmax[a:b, None] > aw) & (xmin[a:b, None] < ae) &
                            (ymax[a:b, None] > as_) & (ymin[a:b, None] < an)).any(1)
            n_read += len(xmin)
            if not hit.any():
                # Cache the empty result too, so a resumed run does not re-download this
                # row group only to discard it again.
                open(sf + ".empty", "w").close()
                continue
            sub = tbl.filter(hit)
            g = gpd.GeoDataFrame(
                {"time": sub.column("time").to_pandas(),
                 "label": sub.column("label").to_pandas()},
                geometry=gpd.GeoSeries.from_wkb(sub.column("geometry").to_pandas()),
                crs="EPSG:4326")
            g.to_parquet(sf)
            parts.append(g)
            print(f"  [{j}/{len(cand)}] rg {i}: {len(xmin)/1e6:.1f}M rows -> {len(g)} kept "
                  f"({time.time()-t0:.0f}s)", flush=True)

    if not parts:
        raise SystemExit("no polygons intersected the AOIs")
    out = pd.concat(parts, ignore_index=True)
    out = gpd.GeoDataFrame(out, geometry="geometry", crs="EPSG:4326")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out.to_file(args.out, driver="GPKG")
    print(f"\nwrote {args.out}: {len(out)} polygons from {n_rg} row groups "
          f"({n_read/1e6:.1f}M rows scanned) in {time.time()-t0:.0f}s")


def compactness(g):
    """perimeter / sqrt(area), the manuscript's shape ratio. Circle ~3.54, square 4."""
    a = g.area.values
    return np.where(a > 0, g.length.values / np.sqrt(np.maximum(a, 1e-9)), np.nan)


def prep(g, name):
    """Project to Albers, drop empties, attach area_ha and compactness."""
    import geopandas as gpd
    g = g[g.geometry.notna() & ~g.geometry.is_empty].copy()
    g = g.to_crs(ALBERS)
    # Self-intersecting FTW rings would make .area meaningless; buffer(0) repairs them.
    bad = ~g.geometry.is_valid
    if bad.any():
        print(f"  {name}: repairing {int(bad.sum())} invalid geometries")
        g.loc[bad, "geometry"] = g.loc[bad, "geometry"].buffer(0)
        g = g[g.geometry.notna() & ~g.geometry.is_empty]
    g["area_ha"] = g.area / 1e4
    g["compact"] = compactness(g.geometry)
    return g.reset_index(drop=True)


def passes(d):
    return ((d.area_ha >= MIN_HA) & (d.area_ha <= MAX_HA) & (d.compact <= MAX_COMPACT)).values


def cmd_compare(args):
    import geopandas as gpd
    from shapely.geometry import box, Point

    s = site_boxes(args.sites, args.year, args.buffer_m)
    pts = gpd.GeoDataFrame(s.copy(),
                           geometry=[Point(xy) for xy in zip(s.lon, s.lat)],
                           crs="EPSG:4326").to_crs(ALBERS)
    aois = gpd.GeoDataFrame(
        s[["TrialCode"]].copy(),
        geometry=[box(r.w, r.s, r.e, r.n) for r in s.itertuples()],
        crs="EPSG:4326").to_crs(ALBERS)
    aoi_area_ha = aois.area.values / 1e4

    print("loading FTW...", flush=True)
    ftw = gpd.read_file(args.ftw)
    if "label" in ftw.columns:
        ftw = ftw[ftw.label == "field"]
    if args.ftw_year and "time" in ftw.columns:
        t = pd.to_datetime(ftw["time"], errors="coerce")
        keep = t.dt.year == args.ftw_year
        if keep.any():
            ftw = ftw[keep]
    ftw = prep(ftw, "FTW")
    print(f"  FTW {len(ftw)} polygons", flush=True)

    print("loading SAM (bbox-windowed)...", flush=True)
    bounds = tuple(aois.total_bounds)
    sam = gpd.read_file(args.sam, bbox=bounds)
    sam = prep(sam, "SAM")
    print(f"  SAM {len(sam)} polygons in window", flush=True)

    ftw["ftw_pass"] = passes(ftw)
    sam["sam_pass"] = passes(sam)

    # ---- per-site: the polygon each source offers for this trial point ----
    rows = []
    fi = gpd.sjoin(pts[["TrialCode", "crop", "geometry"]], ftw.reset_index()[
        ["index", "area_ha", "compact", "ftw_pass", "geometry"]],
        how="left", predicate="within").rename(columns={"index_right": "_ir"})
    si = gpd.sjoin(pts[["TrialCode", "crop", "geometry"]], sam.reset_index()[
        ["index", "area_ha", "compact", "sam_pass", "geometry"]],
        how="left", predicate="within").rename(columns={"index_right": "_ir"})
    # A trial point can fall inside overlapping polygons; keep the smallest, which is the
    # paddock rather than an enclosing blob.
    fi = fi.sort_values("area_ha").drop_duplicates("TrialCode").set_index("TrialCode")
    si = si.sort_values("area_ha").drop_duplicates("TrialCode").set_index("TrialCode")

    for r in s.itertuples():
        tc = r.TrialCode
        f = fi.loc[tc] if tc in fi.index else None
        m = si.loc[tc] if tc in si.index else None
        fa = float(f["area_ha"]) if f is not None and pd.notna(f["area_ha"]) else np.nan
        ma = float(m["area_ha"]) if m is not None and pd.notna(m["area_ha"]) else np.nan
        iou = np.nan
        if f is not None and m is not None and pd.notna(f["index"]) and pd.notna(m["index"]):
            gf = ftw.geometry.iloc[int(f["index"])]
            gm = sam.geometry.iloc[int(m["index"])]
            inter = gf.intersection(gm).area
            union = gf.union(gm).area
            iou = inter / union if union > 0 else np.nan
        rows.append({
            "TrialCode": tc, "crop": r.crop, "state": r.state,
            "ftw_contains": bool(f is not None and pd.notna(f["area_ha"])),
            "sam_contains": bool(m is not None and pd.notna(m["area_ha"])),
            "ftw_area_ha": fa, "sam_area_ha": ma,
            "ftw_compact": float(f["compact"]) if f is not None and pd.notna(f["compact"]) else np.nan,
            "sam_compact": float(m["compact"]) if m is not None and pd.notna(m["compact"]) else np.nan,
            "ftw_pass": bool(f["ftw_pass"]) if f is not None and pd.notna(f["area_ha"]) else False,
            "sam_pass": bool(m["sam_pass"]) if m is not None and pd.notna(m["area_ha"]) else False,
            "iou": iou,
        })
    det = pd.DataFrame(rows)

    # ---- per-AOI: what each source puts on the same ground ----
    fj = gpd.sjoin(ftw[["area_ha", "compact", "ftw_pass", "geometry"]], aois,
                   how="inner", predicate="intersects")
    sj = gpd.sjoin(sam[["area_ha", "compact", "sam_pass", "geometry"]], aois,
                   how="inner", predicate="intersects")

    def aoi_stats(j, passcol):
        g = j.groupby("TrialCode")
        return pd.DataFrame({
            "n": g.size(),
            "median_ha": g.area_ha.median(),
            "sliver_frac": g.area_ha.apply(lambda x: (x < 1.0).mean()),
            "over300_frac": g.area_ha.apply(lambda x: (x > MAX_HA).mean()),
            "pass_frac": g[passcol].mean(),
        })

    fa_s, sa_s = aoi_stats(fj, "ftw_pass"), aoi_stats(sj, "sam_pass")

    # ---- report (aggregate only) ----
    n = len(det)
    L = []
    L.append("# Fields of the World against SAM boundaries, over the 2024 NVT trials")
    L.append("")
    L.append(f"Generated by `src/paddocks/ftw_compare.py` on {time.strftime('%Y-%m-%d')}. "
             f"Aggregate only: no trial codes, no coordinates.")
    L.append("")
    L.append(f"- sites: **{n}** NVT trials sown in {args.year}")
    L.append(f"- AOI: {args.buffer_m:.0f} m box around each trial point "
             f"({np.median(aoi_area_ha):.0f} ha)")
    L.append(f"- FTW: `label == field`" +
             (f", year {args.ftw_year}" if args.ftw_year else "") +
             f", {len(ftw)} polygons over these AOIs")
    L.append(f"- SAM: `{os.path.basename(args.sam)}`, {len(sam)} polygons over these AOIs")
    L.append(f"- retention filter applied to both: {MIN_HA:.0f}-{MAX_HA:.0f} ha and "
             f"compactness <= {MAX_COMPACT:.0f}")
    L.append("")
    L.append("## 1. Does the source give this trial a paddock?")
    L.append("")
    L.append("| | FTW | SAM |")
    L.append("|---|---|---|")
    L.append(f"| trial point inside a polygon | {det.ftw_contains.mean():.1%} | "
             f"{det.sam_contains.mean():.1%} |")
    L.append(f"| inside a polygon that passes the filter | {det.ftw_pass.mean():.1%} | "
             f"{det.sam_pass.mean():.1%} |")
    L.append("")
    L.append("The second row is the share of trials that would yield a usable labelled paddock "
             "if the pipeline were built on that source. **It is not a clean head-to-head.** "
             "The released SAM map has already had this filter applied during production, so "
             "almost nothing in it fails on shape (0.15% of polygons exceed compactness 8, and "
             "those come from the later boundary merge), while FTW is compared raw. Every row "
             "of this section flatters SAM by that much. The comparisons that do not depend on "
             "SAM's pre-filtering are the area distribution and the IoU in section 2, because "
             "the map retains polygons across the whole 5-300 ha range and beyond "
             f"(sub-5 ha and over-300 ha polygons are both present in it).")
    L.append("")
    L.append("### Why the containing polygon fails the filter")
    L.append("")
    L.append("| reason | FTW | SAM |")
    L.append("|---|---|---|")
    for lab, cond in [("no containing polygon", None),
                      (f"under {MIN_HA:.0f} ha", "small"),
                      (f"over {MAX_HA:.0f} ha", "big"),
                      (f"compactness > {MAX_COMPACT:.0f}", "shape")]:
        vals = []
        for pre in ["ftw", "sam"]:
            a = det[f"{pre}_area_ha"]; c = det[f"{pre}_compact"]
            has = det[f"{pre}_contains"]
            if cond is None:
                v = (~has).mean()
            elif cond == "small":
                v = (has & (a < MIN_HA)).mean()
            elif cond == "big":
                v = (has & (a > MAX_HA)).mean()
            else:
                v = (has & (a >= MIN_HA) & (a <= MAX_HA) & (c > MAX_COMPACT)).mean()
            vals.append(f"{v:.1%}")
        L.append(f"| {lab} | {vals[0]} | {vals[1]} |")
    L.append("")
    L.append("## 2. How big is the polygon it gives?")
    L.append("")
    both = det[det.ftw_contains & det.sam_contains]
    L.append(f"On the **{len(both)}** trials where both sources contain the point:")
    L.append("")
    L.append("| statistic | FTW | SAM |")
    L.append("|---|---|---|")
    for nm, fn in [("median area (ha)", np.median), ("mean area (ha)", np.mean),
                   ("90th percentile (ha)", lambda x: np.percentile(x, 90))]:
        L.append(f"| {nm} | {fn(both.ftw_area_ha):.1f} | {fn(both.sam_area_ha):.1f} |")
    L.append(f"| median compactness | {both.ftw_compact.median():.2f} | "
             f"{both.sam_compact.median():.2f} |")
    ratio = both.ftw_area_ha / both.sam_area_ha
    L.append("")
    L.append(f"- median FTW/SAM area ratio **{ratio.median():.2f}x** "
             f"(FTW larger on {(ratio > 1).mean():.0%} of trials)")
    L.append(f"- FTW at least 3x larger on **{(ratio >= 3).mean():.1%}** of trials, "
             f"at least 10x larger on **{(ratio >= 10).mean():.1%}**")
    L.append(f"- median IoU between the two containing polygons **{both.iou.median():.2f}**")
    L.append(f"- IoU below 0.5 on **{(both.iou < 0.5).mean():.1%}** of trials")
    L.append("")
    L.append("A high area ratio with a low IoU is the merged-paddock failure the single-site "
             "check found: FTW returns one polygon covering the trial paddock and its "
             "neighbours.")
    L.append("")
    L.append("## 3. What each source puts on the same ground")
    L.append("")
    L.append(f"Per-AOI, over the {args.buffer_m:.0f} m boxes, medians across sites:")
    L.append("")
    L.append("| statistic | FTW | SAM |")
    L.append("|---|---|---|")
    L.append(f"| polygons per AOI | {fa_s.n.median():.0f} | {sa_s.n.median():.0f} |")
    L.append(f"| median polygon area (ha) | {fa_s.median_ha.median():.1f} | "
             f"{sa_s.median_ha.median():.1f} |")
    L.append(f"| share under 1 ha (slivers) | {fa_s.sliver_frac.median():.1%} | "
             f"{sa_s.sliver_frac.median():.1%} |")
    L.append(f"| share over {MAX_HA:.0f} ha | {fa_s.over300_frac.median():.1%} | "
             f"{sa_s.over300_frac.median():.1%} |")
    L.append(f"| share passing the filter | {fa_s.pass_frac.median():.1%} | "
             f"{sa_s.pass_frac.median():.1%} |")
    L.append("")
    L.append("Pooled over every polygon in every AOI (not per-AOI medians):")
    L.append("")
    L.append("| statistic | FTW | SAM |")
    L.append("|---|---|---|")
    L.append(f"| polygons | {len(fj)} | {len(sj)} |")
    L.append(f"| share under 1 ha | {(fj.area_ha < 1).mean():.1%} | "
             f"{(sj.area_ha < 1).mean():.1%} |")
    L.append(f"| share over {MAX_HA:.0f} ha | {(fj.area_ha > MAX_HA).mean():.1%} | "
             f"{(sj.area_ha > MAX_HA).mean():.1%} |")
    L.append(f"| median area (ha) | {fj.area_ha.median():.1f} | {sj.area_ha.median():.1f} |")
    L.append("")
    L.append("## 4. By state")
    L.append("")
    L.append("| state | trials | FTW usable | SAM usable | median FTW/SAM area ratio |")
    L.append("|---|---|---|---|---|")
    for st, g in det.groupby("state"):
        b = g[g.ftw_contains & g.sam_contains]
        rr = (b.ftw_area_ha / b.sam_area_ha).median() if len(b) else np.nan
        rs = "n/a" if not np.isfinite(rr) else f"{rr:.2f}x"
        L.append(f"| {st} | {len(g)} | {g.ftw_pass.mean():.1%} | {g.sam_pass.mean():.1%} | "
                 f"{rs} |")
    L.append("")
    L.append("Read the state rows with the same caveat as section 1, and note that a row with "
             "only a handful of trials carries no weight.")
    L.append("")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        f.write("\n".join(L) + "\n")
    print(f"wrote {args.out}")
    if args.detail_csv:
        os.makedirs(os.path.dirname(os.path.abspath(args.detail_csv)), exist_ok=True)
        det.to_csv(args.detail_csv, index=False)
        print(f"wrote {args.detail_csv} (SENSITIVE, per-trial)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("fetch")
    a.add_argument("--index", required=True)
    a.add_argument("--sites", required=True)
    a.add_argument("--year", type=int)
    a.add_argument("--buffer-m", type=float, default=1000.0)
    a.add_argument("--out", required=True)
    a.add_argument("--stage-dir", help="per-row-group cache so a dropped connection does not "
                                       "cost the whole run (default: <out>_stage)")
    a.set_defaults(f=cmd_fetch)

    b = sub.add_parser("compare")
    b.add_argument("--ftw", required=True)
    b.add_argument("--sam", required=True)
    b.add_argument("--sites", required=True)
    b.add_argument("--year", type=int)
    b.add_argument("--ftw-year", type=int, default=2024,
                   help="FTW carries 2024 and 2025 predictions; match the SAM map's season")
    b.add_argument("--buffer-m", type=float, default=1000.0)
    b.add_argument("--out", required=True)
    b.add_argument("--detail-csv")
    b.set_defaults(f=cmd_compare)

    args = ap.parse_args()
    args.f(args)


if __name__ == "__main__":
    main()
