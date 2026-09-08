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
    ap.add_argument("--min-containment", type=float, default=None,
                    help="PROTOTYPE, opt-in (default off, reproduces exactly today's matching "
                         "when omitted). containment(a,b) = intersection.area / min(a.area, "
                         "b.area) -- 1.0 when the SMALLER polygon sits entirely inside the "
                         "larger one, regardless of the size gap. IoU structurally cannot score "
                         "a small tile-boundary fragment against the whole paddock it belongs "
                         "to: a real confirmed case (5.08ha fragment inside a 39.7ha polygon) "
                         "scores IoU 0.115 (fails --min-iou 0.5) but containment 0.911. A match "
                         "counts if EITHER metric clears its threshold, tracked as separate best "
                         "candidates per other-year -- the IoU-best and containment-best match "
                         "are often different polygons (the true whole-paddock match is rarely "
                         "the best-IoU candidate for a fragment). Only useful once a paddock is "
                         "actually whole in some years and cut in others -- e.g. after a "
                         "per-year tile-grid shift; on the current fixed grid the same paddocks "
                         "are cut the same way every year, so this has nothing to find yet. "
                         "Validated against 3 of the 4 confirmed real boundary-split pairs in "
                         "PIPELINE_ARCHITECTURE_AND_TILING.md section 6 -- the 4th pair's large "
                         "fragment scores low on BOTH metrics because it was absorbed into a "
                         "blob the compactness filter rejects outright, which no matching metric "
                         "can fix; containment only recovers the 'absorbed into a surviving "
                         "compact neighbour' failure mode, not the 'rejected as a blob' one.")
    ap.add_argument("--spatial-match", action="store_true",
                    help="PROTOTYPE, opt-in (default off, reproduces exactly today's per-tile "
                         "matching when omitted). REQUIRED for a per-year offset grid "
                         "(map_regions.py --offset-seed): the default matcher groups files by "
                         "(region, cell) parsed from the filename and only ever compares a "
                         "tile's polygons against the SAME cell label in other years -- correct "
                         "only because the fixed grid makes cell r17c17 the same ground every "
                         "year. Once the grid moves per year, r17c17 in 2024 is different ground "
                         "from r17c17 in 2019, so that grouping would compare the wrong tiles "
                         "outright. This mode instead concatenates ALL cells of a region into "
                         "ONE per-year GeoDataFrame with a single spatial index, and matches "
                         "every polygon against the whole region in every other year, not just "
                         "its own cell label -- correct regardless of whether the grid moved. "
                         "Same IoU/containment logic as the default path (same helper), just a "
                         "wider candidate search. Does not support --shard: unsharded, single "
                         "process, for pilot-scale validation before this earns a sharded "
                         "rewrite.")
    ap.add_argument("--aois", help="aois.csv used for this run (columns stub,lat,lon,half_m) -- "
                                   "enables the touches_grid/dist_to_grid_m attributes below. "
                                   "Omit to skip both columns entirely.")
    ap.add_argument("--grid-touch-tol-m", type=float, default=10.0,
                    help="a polygon within this many metres of its tile's edge is flagged "
                         "touches_grid=True. Default matches the 10m (one Sentinel-2 pixel) "
                         "tolerance used throughout PIPELINE_ARCHITECTURE_AND_TILING.md's "
                         "boundary-split quantification. Computed against the tile's INTENDED "
                         "bounds (centre lat/lon +/- half_m from --aois, reprojected to "
                         "EPSG:3577), not the downloaded composite raster's own bounds -- the "
                         "raster is padded some hundreds of metres past the true AOI window "
                         "(confirmed: riverina_2024_r0c0.tif is 3510x3160m against a nominal "
                         "3000x3000m tile), so measuring against it would flag the padding edge, "
                         "not the tile-to-tile abutment line the rest of the pipeline cares about.")
    ap.add_argument("--same-grid-restrict", action="store_true",
                    help="PROTOTYPE, opt-in, requires --aois. For each YEAR PAIR being "
                         "compared, restricts candidates to the anchor's own (region, cell) if "
                         "the two years share the same grid (cell r0c0 sits on the same ground "
                         "in both), and searches the whole region if they do not -- correct "
                         "because 'same cell label' only means 'same ground' when the grid "
                         "hasn't moved between the two years being compared. SUPERSEDES an "
                         "earlier attempt (2026-09-01, since removed) that restricted by whether "
                         "the ANCHOR touched a grid line instead of by whether the YEAR PAIR "
                         "shared a grid: that version broke ordinary interior matching for the "
                         "whole offset year (median IoU collapsed to 0.27, n_years to 1) because "
                         "same-cell is meaningless for ANY polygon once the grid has moved, not "
                         "just the boundary-touching ones. This version keeps same-grid year "
                         "pairs (e.g. all 8 fixed years against each other) exactly as safe as "
                         "the default matcher, and only opens whole-region search for pairs "
                         "actually involving a different grid.")
    ap.add_argument("--max-containment-ratio", type=float, default=None,
                    help="PROTOTYPE, opt-in (default off, reproduces exactly today's matching "
                         "when omitted). Excludes a containment match if max(area)/min(area) "
                         "exceeds this, even when both polygons are individually under "
                         "--max-match-area-ha. Found necessary because the blob exclusion alone "
                         "does not stop containment's structural weakness: inter/min(area) can "
                         "sit near 1.0 at extreme size mismatch between two otherwise-ordinary "
                         "polygons, and a single moderately-large 'hub' well under 300ha can "
                         "still bridge many small real paddocks. Measured 2026-09-01: with "
                         "--max-match-area-ha 300 and --max-group-diag-m 3000 both active, a "
                         "30-tile reproduction still produced groups mixing dozens of distinct "
                         "real paddocks via hub polygons 14.6x-131.7x the size of their smallest "
                         "member (e.g. one 100.23ha hub bridging a 1.02ha polygon). The 3 real "
                         "confirmed containment matches this flag was designed around "
                         "(PIPELINE_ARCHITECTURE_AND_TILING.md section 6) top out at 7.8x "
                         "(5.08ha fragment / 39.7ha whole); a cap only slightly above that "
                         "preserves them while excluding the hub cases found here.")
    ap.add_argument("--max-match-area-ha", type=float, default=None,
                    help="PROTOTYPE, opt-in (default off, reproduces exactly today's matching "
                         "when omitted). Excludes any polygon above this size from EITHER side "
                         "of a match (as anchor or as candidate) -- found necessary for "
                         "--spatial-match: an oversized under-segmentation blob (already known "
                         "junk, see the >300ha band in this report's own 'Is it just polygon "
                         "size?' section) scores containment near 1.0 against every smaller real "
                         "polygon it happens to overlap in another year, and once candidate "
                         "search is whole-region rather than same-tile, a single blob can "
                         "transitively bridge dozens of unrelated real paddocks across many "
                         "tiles into one union-find identity. Measured on the 2026-09-01 offset-"
                         "grid pilot: 111 paddock_ids (of thousands) each spanning >=5 distinct "
                         "tile cells absorbed 30.7% of all polygon-years, one single identity "
                         "reaching 208 of 1,156 tiles; 98.1% of all >300ha polygons in the whole "
                         "run sat inside these 111 groups. 300 matches predict_tile.py's and "
                         "consensus_layer.py's own max-area-ha convention. Under the default "
                         "tile-restricted matcher this was never possible -- a blob's candidates "
                         "were already confined to its own (region, cell), so it could corrupt "
                         "at most one tile's worth of identity, which is why this was never "
                         "needed before --spatial-match existed.")
    ap.add_argument("--max-group-diag-m", type=float, default=None,
                    help="PROTOTYPE, opt-in (default off, reproduces exactly today's matching "
                         "when omitted). Refuses a union if it would grow that paddock "
                         "identity's overall bounding-box diagonal past this many metres. "
                         "REQUIRED for --spatial-match even with --max-match-area-ha set: "
                         "excluding oversized blobs stops the single-hub failure mode but not "
                         "the general one -- plain union-find is fully transitive, so a chain of "
                         "individually-plausible small/medium links (no blob involved) can still "
                         "walk an identity across many tiles. Measured 2026-09-01: a 30-tile "
                         "repro of one such chain, WITH --max-match-area-ha 300 already applied, "
                         "still produced a 9-cell, 252-row group mixing dozens of genuinely "
                         "distinct 5-280ha paddocks. A real paddock split by a per-year grid "
                         "shift can move by at most one tile width in each axis, so its group's "
                         "true extent is bounded; ~6000m (2x the 3km tile edge) is a generous "
                         "cap that admits a real cross-boundary split while refusing a long "
                         "transitive walk. Checked incrementally per union, not as a post-hoc "
                         "filter, so a chain is stopped at the first over-extending link.")
    ap.add_argument("--max-group-area-ratio", type=float, default=None,
                    help="PROTOTYPE, opt-in (default off, reproduces exactly today's matching "
                         "when omitted). Refuses a union if it would grow that identity's overall "
                         "max(area_ha)/min(area_ha) past this. --max-containment-ratio bounds "
                         "each PAIRWISE link's size mismatch, not how many links accumulate: "
                         "measured 2026-09-01, a smooth size gradient (each hop within ratio 8x "
                         "of its neighbour) still let groups reach 13-74x overall spread, WITHIN "
                         "A SINGLE (region, cell) across years -- --cross-cell-only-if-touching "
                         "does not help here, the drift is not cross-cell. Checked incrementally "
                         "per union alongside --max-group-diag-m, same reasoning: stop the chain "
                         "at the first over-extending link.")
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
    if args.spatial_match and args.shard:
        raise SystemExit("--spatial-match does not support --shard yet (unsharded prototype)")
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

    aoi_lookup, to_albers, grid_sig = None, None, {}
    if args.aois:
        from pyproj import Transformer
        to_albers = Transformer.from_crs("EPSG:4326", "EPSG:3577", always_xy=True)
        Aoi = pd.read_csv(args.aois)
        pat_stub = re.compile(r"^(?P<region>.+?)_(?P<year>\d{4})_(?P<cell>r\d+c\d+)$")
        aoi_lookup = {}
        for _, r in Aoi.iterrows():
            m = pat_stub.match(str(r.stub))
            if m:
                aoi_lookup[(m["region"], int(r.year), m["cell"])] = (r.lat, r.lon, r.half_m)
        print(f"loaded {len(aoi_lookup):,} tile definitions from {args.aois} "
              f"for touches_grid/dist_to_grid_m")
        # PROTOTYPE (--same-grid-restrict, see match_group): whether two
        # years share the SAME grid, from cell r0c0's own (lat, lon) -- if r0c0 sits on
        # different ground in year A vs year B, EVERY cell label means different ground between
        # those two years, not just the boundary-touching ones. Falls back to any one cell
        # common to both years if r0c0 is absent for either (shouldn't happen for this project's
        # own AOI layout, but the fallback costs nothing).
        grid_sig = {}
        for (region, year, cell), (lat, lon, _) in aoi_lookup.items():
            key = (region, year)
            if cell == "r0c0" or key not in grid_sig:
                grid_sig[key] = (round(lat, 6), round(lon, 6))

    def match_group(id_prefix, region, year_files):
        """Shared by both grouping modes below -- identical IoU/containment matching either
        way, the only difference is how much ground one `gy[y]` GeoDataFrame covers.
        `year_files`: {year: [(cell, path), ...]}. Default mode calls this once per (region,
        cell) with exactly one path per year (today's behaviour, unchanged). --spatial-match
        calls it once per region with EVERY cell's path for that year, so `gy[y]` spans the
        whole region and a polygon's candidates in another year are not restricted to its own
        cell label."""
        years = sorted(year_files)
        if len(years) < 2:
            return []
        gy = {}
        for y in years:
            parts = []
            for cell, path in year_files[y]:
                g = gpd.read_file(path)
                if len(g):
                    g = g.to_crs("EPSG:3577").reset_index(drop=True)
                    g["_cell"], g["_idx"] = cell, np.arange(len(g))
                    if aoi_lookup is not None:
                        tile = aoi_lookup.get((region, y, cell))
                        if tile is not None:
                            lat, lon, half_m = tile
                            cx, cy = to_albers.transform(lon, lat)
                            b = g.bounds
                            dx = np.minimum(np.abs(b.minx - (cx - half_m)),
                                            np.abs(b.maxx - (cx + half_m)))
                            dy = np.minimum(np.abs(b.miny - (cy - half_m)),
                                            np.abs(b.maxy - (cy + half_m)))
                            dist = np.minimum(dx, dy)
                        else:
                            dist = pd.Series(np.nan, index=g.index)
                        g["_dist_grid"] = dist.round(1)
                        g["_touch_grid"] = dist <= args.grid_touch_tol_m
                    parts.append(g)
            if parts:
                gy[y] = pd.concat(parts, ignore_index=True) if len(parts) > 1 else parts[0]
        if len(gy) < 2:
            return []
        # Union-find over (year, row), so a paddock traced through nine independent
        # segmentations gets ONE identity. Without this the table can say how stable a polygon
        # is but not WHICH polygon in the next year it is, and no rotation can be read from it.
        parent = {}

        def find(k):
            parent.setdefault(k, k)
            while parent[k] != k:
                parent[k] = parent[parent[k]]
                k = parent[k]
            return k

        # PROTOTYPE (--max-group-diag-m): plain union-find is fully transitive, so a chain of
        # individually-plausible links (A matches B, B matches C, C matches D, ...) can walk an
        # identity arbitrarily far even with --max-match-area-ha excluding blobs -- confirmed on
        # the 2026-09-01 pilot: after excluding blobs, a 30-tile repro still produced a 9-cell,
        # 252-row group mixing dozens of genuinely distinct real paddocks (5-280ha each), no
        # single oversized anchor responsible. A real paddock split by a grid shift can move by
        # at most one tile width in each axis; this refuses any union that would grow the
        # group's overall bounding-box diagonal past a physically plausible cap, checked
        # incrementally (cheap: one bbox per root, updated on every successful union) rather
        # than as a post-hoc filter, so a long chain is stopped at the FIRST link that would
        # over-extend it, not just the most obviously oversized member.
        bbox = {}
        # PROTOTYPE (--max-group-area-ratio): --max-containment-ratio bounds each PAIRWISE
        # link's size mismatch but not how many links accumulate -- confirmed 2026-09-01, a
        # smooth size gradient (each hop within ratio 8x of its neighbour) still let a group's
        # overall max/min area reach 13-74x, even confined to a single (region, cell) across
        # years (--cross-cell-only-if-touching does not help here -- the drift is within-cell).
        # Tracked incrementally like bbox above, for the same reason: stop the chain at the
        # first over-extending link, not after the fact.
        arange = {}

        def union(a, b, a_bounds, b_bounds, a_area, b_area):
            ra, rb = find(a), find(b)
            if ra == rb:
                return
            if args.max_group_diag_m is not None:
                ba, bb = bbox.get(ra, a_bounds), bbox.get(rb, b_bounds)
                minx, miny = min(ba[0], bb[0]), min(ba[1], bb[1])
                maxx, maxy = max(ba[2], bb[2]), max(ba[3], bb[3])
                if ((maxx - minx) ** 2 + (maxy - miny) ** 2) ** 0.5 > args.max_group_diag_m:
                    return
            if args.max_group_area_ratio is not None:
                amin, amax = arange.get(ra, (a_area, a_area))
                bmin, bmax = arange.get(rb, (b_area, b_area))
                new_min, new_max = min(amin, bmin), max(amax, bmax)
                if new_max / new_min > args.max_group_area_ratio:
                    return
            if args.max_group_diag_m is not None:
                bbox[rb] = (minx, miny, maxx, maxy)
                bbox.pop(ra, None)
            if args.max_group_area_ratio is not None:
                arange[rb] = (new_min, new_max)
                arange.pop(ra, None)
            parent[ra] = rb

        tile_rows = []
        for y, g in gy.items():
            sidx = {o: gy[o].sindex for o in gy if o != y}
            if args.max_match_area_ha is not None:
                oversized = (g.geometry.area / 1e4) > args.max_match_area_ha
            else:
                oversized = pd.Series(False, index=g.index)
            for i, geom in enumerate(g.geometry):
                ious, best_idx = {}, {}
                # PROTOTYPE (--min-containment): tracked as a SEPARATE best-candidate per other-
                # year, not folded into the IoU search above. A fragment's best-IoU neighbour and
                # its best-containment neighbour are frequently different polygons -- IoU is
                # dragged down by the size mismatch exactly when containment is high, so hunting
                # for a single "best overall" candidate would usually still pick the wrong one.
                conts, cont_idx = {}, {}
                # PROTOTYPE (--max-match-area-ha): an oversized anchor never matches anything --
                # see the flag's help text for why this is required once candidate search stops
                # being confined to one tile.
                own_cell = g["_cell"].iloc[i]
                for o in gy:
                    if o == y or oversized.iloc[i]:
                        continue
                    cand_i = list(sidx[o].query(geom, predicate="intersects"))
                    # PROTOTYPE (--same-grid-restrict): see the flag's help text. Per-YEAR-PAIR,
                    # not per-anchor -- correct regardless of whether THIS anchor happens to sit
                    # near a boundary, because same-cell is only meaningful when y and o actually
                    # share a grid.
                    if args.same_grid_restrict and grid_sig.get((region, y)) == \
                            grid_sig.get((region, o)):
                        cand_i = [k for k in cand_i if gy[o]["_cell"].iloc[k] == own_cell]
                    best, bi = 0.0, None
                    cbest, cbi = 0.0, None
                    for k in cand_i:
                        if args.max_match_area_ha is not None and \
                                gy[o].geometry.iloc[k].area / 1e4 > args.max_match_area_ha:
                            continue
                        og = gy[o].geometry.iloc[k]
                        inter = geom.intersection(og).area
                        if inter > 0:
                            iou = inter / (geom.area + og.area - inter)
                            if iou > best:
                                best, bi = iou, k
                            if args.min_containment is not None and (
                                    args.max_containment_ratio is None
                                    or max(geom.area, og.area) / min(geom.area, og.area)
                                    <= args.max_containment_ratio):
                                cont = inter / min(geom.area, og.area)
                                if cont > cbest:
                                    cbest, cbi = cont, k
                    ious[o] = best
                    best_idx[o] = bi
                    conts[o] = cbest
                    cont_idx[o] = cbi
                hits = [v for v in ious.values() if v >= args.min_iou]
                # Only a match at or above the threshold joins two years into one paddock. A
                # weaker overlap is exactly the case this is trying to exclude.
                for o, v in ious.items():
                    if v >= args.min_iou and best_idx[o] is not None:
                        og = gy[o].geometry.iloc[best_idx[o]]
                        union((y, i), (o, best_idx[o]), geom.bounds, og.bounds,
                              geom.area, og.area)
                if args.min_containment is not None:
                    for o, v in conts.items():
                        if v >= args.min_containment and cont_idx[o] is not None:
                            og = gy[o].geometry.iloc[cont_idx[o]]
                            union((y, i), (o, cont_idx[o]), geom.bounds, og.bounds,
                                  geom.area, og.area)
                row = {"cell": g["_cell"].iloc[i], "year": y,
                       "idx": int(g["_idx"].iloc[i]),
                       "area_ha": round(geom.area / 1e4, 2),
                       "n_years": 1 + len(hits),
                       "median_iou": round(float(np.median(list(ious.values()))), 3)
                       if ious else np.nan,
                       "mean_iou_hits": round(float(np.mean(hits)), 3) if hits else 0.0}
                if aoi_lookup is not None:
                    row["touches_grid"] = bool(g["_touch_grid"].iloc[i])
                    row["dist_to_grid_m"] = float(g["_dist_grid"].iloc[i])
                row["_key"] = (y, i)
                tile_rows.append(row)
        roots = {}
        for r in tile_rows:
            root = find(r.pop("_key"))
            r["paddock_id"] = f"{id_prefix}_p{roots.setdefault(root, len(roots))}"
        return tile_rows

    rows = []
    if args.spatial_match:
        # Regroup the same `tiles` index by region only, so every cell's file for a given year
        # lands in one list -- see match_group's docstring for why this is required once the
        # grid is not the same ground every year.
        region_years = defaultdict(lambda: defaultdict(list))
        for (region, cell), byyear in tiles.items():
            for y, path in byyear.items():
                region_years[region][y].append((cell, path))
        for region, year_files in sorted(region_years.items()):
            tile_rows = match_group(region, region, year_files)
            rows.extend({"region": region, **r} for r in tile_rows)
    else:
        for (region, cell), byyear in sorted(tiles.items()):
            tile_rows = match_group(f"{region}_{cell}", region,
                                     {y: [(cell, path)] for y, path in byyear.items()})
            rows.extend({"region": region, **r} for r in tile_rows)
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
            # abstain_reason, not pred, is authoritative for "cleanly classified" -- see
            # predict_tile.py's shape-gate comment (2026-09-07): a --shape-gate-skip-classes
            # class can carry a non-null pred alongside a non-empty abstain_reason.
            J = J[J.abstain_reason.fillna("") == ""] if "abstain_reason" in J.columns else J[J.pred.notna()]
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
                if "touches_grid" in gg.columns:
                    sel["touches_grid"] = gg.touches_grid.values
                    sel["dist_to_grid_m"] = gg.dist_to_grid_m.values
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
