#!/usr/bin/env python3
"""
merge_overlaps.py -- the last national stage: merge every group of polygons that still overlaps
after merge_tile_boundaries.py, and give the merged polygon the attributes of its largest member.

WHY. merge_tile_boundaries.py unions cross-tile twins only when both views are classified and the
union passes its size and shape caps. On the 2024 9 km map that left 165,081 overlapping pairs
(2.75 M ha). On 40 random tile windows 99.8% of them were cross-tile and the median overlap was 98%
of the smaller polygon, so they are nearly always one paddock seen by two tiles. Most were skipped
because one or both views were abstained (69% of pairs both, 15% one).

RULE (user decision 2026-09-11). Two polygons overlap when their intersection exceeds
--min-overlap-m2 (default 100 m2, one Sentinel-2 pixel), so paddocks that only share an edge are
left alone. Chains (A overlaps B, B overlaps C) merge as one group. The group's union takes every
attribute of the member with the largest area: crop type, abstain_reason, confidence,
probabilities and yield. area_ha and compactness (P/sqrt(A), as in merge_tile_boundaries.py) are
recomputed from the union. overlap_merge_n (group size) and overlap_merged_from (the input fids
folded into this row) record the provenance. A merged polygon over --max-area-ha (300 ha) is then
abstained as `unsegmented_blob`, the reason predict_tile.py gives a single polygon over the same limit:
its class and yield are cleared and that reason replaces any other, since the pipeline checks area
before any spectral gate (user decision 2026-09-11).

A union that comes out as a MultiPolygon cannot go into this POLYGON layer. It keeps its largest
part when that part holds at least 99% of the union's area; otherwise the group is left unmerged
and counted.

OUTPUT. A copy of the input in which each group's largest member gets the union geometry and the
other members are deleted. Every other row is byte-identical. The R-tree stays live through the
GeoPackage triggers (register_gpkg_functions). Aggregate summary only, no site-level records.

    python3 merge_overlaps.py --in $M/national_2024_crops_merged.gpkg \
        --out $M/national_2024_crops_final.gpkg --summary $M/overlaps_summary.json --verify
"""
import argparse
import json
import shutil
import sqlite3
import time
from collections import Counter

import numpy as np
import shapely
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from merge_tile_boundaries import geom_to_blob, gpb_header_len_and_env, register_gpkg_functions


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def read_layer(path, layer):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    srs_id = con.execute("SELECT srs_id FROM gpkg_geometry_columns WHERE table_name=?", (layer,)).fetchone()[0]
    fids, wkbs, cls = [], [], []
    for fid, blob, pred, reason in con.execute(f'SELECT fid, geom, pred, abstain_reason FROM "{layer}"'):
        hlen, _ = gpb_header_len_and_env(blob)
        fids.append(fid)
        wkbs.append(bytes(blob[hlen:]))
        # "classified" as the manuscript counts it: a class, including the no_crop_shape flag
        cls.append(pred if pred and (reason or "") in ("", "no_crop_shape") else None)
    con.close()
    return srs_id, np.array(fids, dtype=np.int64), shapely.from_wkb(wkbs), np.array(cls, dtype=object)


def overlap_pairs(G, min_m2, chunk=200_000):
    i, j = shapely.STRtree(G).query(G, predicate="intersects")
    k = i < j
    i, j = i[k], j[k]
    inter = np.empty(len(i))
    for s in range(0, len(i), chunk):
        inter[s:s + chunk] = shapely.area(shapely.intersection(G[i[s:s + chunk]], G[j[s:s + chunk]]))
    keep = inter > min_m2
    return len(k.nonzero()[0]), i[keep], j[keep], inter[keep]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--layer", default="crops")
    ap.add_argument("--min-overlap-m2", type=float, default=100.0,
                    help="intersection area above which two polygons count as overlapping (100 = 1 pixel)")
    ap.add_argument("--summary", help="JSON summary")
    ap.add_argument("--max-area-ha", type=float, default=300.0,
                    help="abstain a merged polygon larger than this as unsegmented_blob (predict_tile.py --max-area-ha); 0 disables")
    ap.add_argument("--verify", action="store_true", help="re-scan the output and count residual overlaps")
    args = ap.parse_args()

    srs_id, fid, G, cls = read_layer(args.inp, args.layer)
    area = shapely.area(G)
    log(f"{len(G):,} polygons read from {args.inp}")
    n_cand, i, j, inter = overlap_pairs(G, args.min_overlap_m2)
    log(f"{n_cand:,} intersecting candidate pairs, {len(i):,} overlap by > {args.min_overlap_m2:g} m2 "
        f"({inter.sum() / 1e4:,.0f} ha)")

    n = len(G)
    _, lab = connected_components(coo_matrix((np.ones(len(i)), (i, j)), shape=(n, n)), directed=False)
    size = np.bincount(lab)
    members = np.flatnonzero(size[lab] >= 2)
    members = members[np.argsort(lab[members], kind="stable")]
    groups = np.split(members, np.flatnonzero(np.diff(lab[members])) + 1) if len(members) else []
    log(f"{len(groups):,} groups to merge ({len(members):,} polygons)")

    upd, dele = [], []
    stats = Counter()
    hist = Counter()
    union_ha, member_ha, over300 = 0.0, 0.0, 0
    big, big_was_cls = [], 0
    for g in groups:
        w = g[np.argmax(area[g])]
        u = shapely.union_all(G[g])
        if u.geom_type == "MultiPolygon":
            parts = sorted(u.geoms, key=lambda p: p.area, reverse=True)
            if parts[0].area >= 0.99 * u.area:
                u = parts[0]
                stats["multipolygon_trimmed"] += 1
            else:
                stats["multipolygon_skipped"] += 1
                continue
        elif u.geom_type != "Polygon":
            stats["non_polygon_skipped"] += 1
            continue
        c = [x for x in cls[g] if x is not None]
        if not c:
            stats["all_abstained"] += 1
        elif len(c) == len(g):
            stats["all_classified_same_class" if len(set(c)) == 1 else "all_classified_class_conflict"] += 1
        else:
            stats["mixed_winner_classified" if cls[w] is not None else "mixed_winner_abstained"] += 1
        hist[min(len(g), 10)] += 1
        ua = u.area
        union_ha += ua / 1e4
        member_ha += area[g].sum() / 1e4
        over300 += ua / 1e4 > 300
        if args.max_area_ha and ua / 1e4 > args.max_area_ha:
            big.append(int(fid[w]))
            big_was_cls += cls[w] is not None
        folded = ",".join(str(int(fid[m])) for m in g if m != w)
        upd.append((geom_to_blob(u, srs_id), round(ua / 1e4, 2), float(u.length / np.sqrt(ua)),
                    int(len(g)), folded, int(fid[w])))
        dele.extend(int(fid[m]) for m in g if m != w)
    log(f"{len(upd):,} merged polygons, {len(dele):,} rows folded in; {dict(stats)}")

    log(f"copying {args.inp} -> {args.out}")
    shutil.copyfile(args.inp, args.out)
    con = sqlite3.connect(args.out)
    register_gpkg_functions(con)
    cols = [r[1] for r in con.execute(f'PRAGMA table_info("{args.layer}")')]
    for c, t in (("overlap_merge_n", "INTEGER"), ("overlap_merged_from", "TEXT")):
        if c not in cols:
            con.execute(f'ALTER TABLE "{args.layer}" ADD COLUMN {c} {t}')
    con.executemany(f'UPDATE "{args.layer}" SET geom=?, area_ha=?, compactness=?, overlap_merge_n=?, '
                    f'overlap_merged_from=? WHERE fid=?', upd)
    con.executemany(f'DELETE FROM "{args.layer}" WHERE fid=?', [(f,) for f in dele])
    if big:
        sets = ["pred=NULL", "abstain_reason='unsegmented_blob'"] + [f"{c}=NULL" for c in ("yield_tha", "yield_tha_calibrated") if c in cols]
        con.executemany(f'UPDATE "{args.layer}" SET {", ".join(sets)} WHERE fid=?', [(f,) for f in big])
        log(f"{len(big):,} merged polygons over {args.max_area_ha:g} ha abstained as unsegmented_blob "
            f"({big_was_cls:,} had a class)")
    ext = con.execute(f"SELECT min(minx), min(miny), max(maxx), max(maxy) FROM rtree_{args.layer}_geom").fetchone()
    if ext and ext[0] is not None:
        con.execute("UPDATE gpkg_contents SET min_x=?, min_y=?, max_x=?, max_y=? WHERE table_name=?", (*ext, args.layer))
    con.commit()
    n_after = con.execute(f'SELECT count(*) FROM "{args.layer}"').fetchone()[0]
    n_rt = con.execute(f"SELECT count(*) FROM rtree_{args.layer}_geom").fetchone()[0]
    con.close()
    log(f"wrote {args.out}: {n_after:,} features (rtree {n_rt:,}), {n - n_after:,} fewer than the input")
    assert n_after == n_rt, "R-tree out of step with the feature table"
    assert n_after == n - len(dele), "row count does not match the deletions"

    S = dict(input=args.inp, output=args.out, min_overlap_m2=args.min_overlap_m2, n_in=n, n_out=n_after,
             n_candidate_pairs=n_cand, n_overlap_pairs=int(len(i)), overlap_ha=round(float(inter.sum() / 1e4), 1),
             n_groups_merged=len(upd), n_rows_folded=len(dele), group_size_hist={str(k): v for k, v in sorted(hist.items())},
             group_types=dict(stats), union_ha=round(union_ha, 1), member_ha=round(member_ha, 1),
             double_counted_ha_removed=round(member_ha - union_ha, 1), n_unions_over_300ha=int(over300),
             max_area_ha=args.max_area_ha, n_merged_over_max_area_abstained=len(big),
             n_merged_over_max_area_were_classified=int(big_was_cls))
    if args.verify:
        _, fid2, G2, _ = read_layer(args.out, args.layer)
        _, i2, _, inter2 = overlap_pairs(G2, args.min_overlap_m2)
        S["residual_overlap_pairs"] = int(len(i2))
        S["residual_overlap_ha"] = round(float(inter2.sum() / 1e4), 1)
        log(f"verify: {len(i2):,} residual overlapping pairs ({inter2.sum() / 1e4:,.1f} ha)")
    if args.summary:
        json.dump(S, open(args.summary, "w"), indent=1)
    log(json.dumps(S))


if __name__ == "__main__":
    main()
