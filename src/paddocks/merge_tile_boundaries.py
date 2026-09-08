#!/usr/bin/env python
"""
merge_tile_boundaries.py -- cross-tile de-duplication + merge for the national crop-type map.

WHAT THE DATA ACTUALLY SHOWS (measured 2026-09-08, see output/TILE_BOUNDARY_MERGE.md). The
national map is 99,465 3 km tiles on an exact Albers lattice, and PIPELINE_ARCHITECTURE_AND_TILING
sec 4 states the tiles abut with no overlap. They do not. `samgeo_segment.build_image` queries a
3 km square in EPSG:3577 but asks the datacube for the raster in EPSG:6933, so the raster is the
6933 bounding box of that (rotated ~6.6 deg, rescaled) square: 351 x 316 px at 10 m, 11.09 km^2
instead of 9, reaching ~345 m PAST the nominal tile square on every side. Adjacent tiles overlap
in a ~690 m band and a paddock in that band is segmented and classified independently by both
tiles. The boundary artefact is therefore DUPLICATION (the same paddock twice, possibly with two
classes, sometimes one whole and one truncated at the other tile's raster edge), not a cut at the
lattice line -- and 15.5 % of the summed polygon area in the Riverina test box is double-counted.
The "boundary-touching" bbox statistic of sec 5 grows at a flat ~0.65 %/m with tolerance, which
is the background rate of real boundaries near a line: there is no excess at the lattice.

RULE SET. The lattice square of each tile is its CORE; a tile is authoritative on its own core
(the paddock is furthest from the raster edge in that tile's view).
  D1 ownership   -- a polygon whose centroid lies outside its own tile's core is an "away" view of
                    ground another tile owns.
  D2 coverage    -- an away polygon is DROPPED if >= --cover-min of its area is covered by the
                    owning tiles' own (non-away) polygons that made a decision on that ground
                    (cleanly classified or no_crop_signal; for an away polygon that is itself
                    abstained, any non-away polygon counts). Otherwise it is RESCUED and kept: the
                    home tile has no claim on that ground.
  D3 conflict    -- a dropped polygon's twin is the kept polygon with the largest intersection. If
                    the dropped polygon sits >= --dup-frac inside its twin, both are classified and
                    the classes differ, the twin's class is reconciled by the area-weighted mean of
                    (p_canola, p_cereal, p_legume) and flagged class_conflict=1 (with --no-reconcile
                    the owner's class stands and only the flag is written).
  M1 union       -- after D1-D3, two kept CLASSIFIED polygons from different tiles that still
                    overlap by >= --ovl-min of the smaller one are two truncated views of one
                    paddock wider than the overlap band; they are union-merged if the union is
                    <= --max-area-ha, compactness P/sqrt(A) <= --max-compactness (the pipeline's
                    own filters) and the classes are the same or reconcilable: the area-weighted
                    winner must be one of the two classes and BOTH must give it >= --conflict-pmin
                    (otherwise the two views are confidently different crops and both are kept,
                    flagged). Connected components of accepted pairs merge together (cap
                    --max-merge-n).
  M2 clip        -- whatever still overlaps after D1-M1 (boundary-disagreement slivers below
                    --ovl-min, and pairs that could not be merged) is resolved by OWNERSHIP: the
                    overlap goes to the polygon whose tile owns the lattice square it lies in (that
                    tile saw the ground furthest from its raster edge) and is subtracted from the
                    other, provided it is a sliver of the loser (<= --clip-max-frac of its area) and
                    the loser stays one polygon (crumbs < --clip-crumb-ha are discarded). The output
                    is then (very nearly) a planar partition, so summed areas stop double counting.
                    Skipped with --no-clip.
  raster_cut_m   -- with --samgeo-dir, every output polygon gets the length of its boundary that
                    runs within --cut-tol m of the raster edge of its own tile(s). SAM polygons stop
                    2 px (~20 m) inside the raster, so a value >= ~100 m marks a view that MAY be cut
                    by the tile window (a real fence within 30 m of the edge also scores; see
                    cut_continuity.py for the image test that tells them apart).

OUTPUT. A copy of the input in which dropped polygons are deleted, merged unions appended, and
twins updated; every other row is byte-identical apart from new provenance columns
(merged_from, merged_from_fid, merge_n, class_conflict, pre_merge_classes, boundary_action,
clip_ha, raster_cut_m) which are NULL on untouched rows (raster_cut_m is set on every row). Two decision tables: --away-csv (one row per away polygon) and
--pairs-csv (one row per cross-tile overlapping pair of kept polygons), and a --summary JSON.

Standalone and opt-in: does not touch predict_tile.py / merge_national.pbs / run_national.sh.
"""
import argparse
import json
import shutil
import sqlite3
import struct
import time

import numpy as np
import pandas as pd
import shapely
from shapely.ops import unary_union

CLASSES = ["Canola", "Cereal", "Legume"]
ATTR_COLS = ["stub", "poly_idx", "pred", "abstain_reason", "area_ha", "compactness", "ndvi_amp",
             "confidence", "p_canola", "p_cereal", "p_legume", "n_obs", "clear_frac",
             "treed_frac", "n_feat_present", "year"]
PROV_COLS = [("merged_from", "TEXT"), ("merged_from_fid", "TEXT"), ("merge_n", "INTEGER"),
             ("class_conflict", "INTEGER"), ("pre_merge_classes", "TEXT"),
             ("boundary_action", "TEXT"), ("clip_ha", "REAL"), ("raster_cut_m", "REAL")]
DECIDED = ("", "no_crop_signal")   # abstain_reason values that mean "the tile decided on this ground"


def _py(v):
    """sqlite3 binds numpy scalars as BLOBs (buffer protocol) with no error; coerce to Python types."""
    if v is None:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, float) and np.isnan(v):
        return None
    return v


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ----------------------------------------------------------------------------------------------
# GeoPackage binary helpers (spec 1.2 "GP" header)
# ----------------------------------------------------------------------------------------------
def gpb_header_len_and_env(blob):
    if blob is None or len(blob) < 8 or blob[:2] != b"GP":
        return None, None
    flags = blob[3]
    endian = "<" if (flags & 1) else ">"
    n = {0: 0, 1: 4, 2: 6, 3: 6, 4: 8}.get((flags >> 1) & 7)
    if n is None:
        return None, None
    hlen = 8 + 8 * n
    env = struct.unpack(f"{endian}{n}d", blob[8:hlen])[:4] if n else None
    return hlen, env


def blob_to_geom(blob):
    hlen, _ = gpb_header_len_and_env(blob)
    return shapely.from_wkb(bytes(blob[hlen:]))


def geom_to_blob(geom, srs_id):
    b = geom.bounds
    return (b"GP" + bytes([0, 3]) + struct.pack("<i", srs_id) +
            struct.pack("<4d", b[0], b[2], b[1], b[3]) + shapely.to_wkb(geom, byte_order=1))


def register_gpkg_functions(con):
    """GDAL's R-tree triggers call ST_MinX/... which plain sqlite lacks; register Python versions so
    DELETE/INSERT keep the spatial index live."""
    def env_fn(i):
        def f(blob):
            _, env = gpb_header_len_and_env(blob)
            if env is None:
                bb = blob_to_geom(blob).bounds
                env = (bb[0], bb[2], bb[1], bb[3])
            return float(env[i])
        return f
    for i, name in enumerate(["ST_MinX", "ST_MaxX", "ST_MinY", "ST_MaxY"]):
        con.create_function(name, 1, env_fn(i))
    con.create_function("ST_IsEmpty", 1, lambda blob: 0 if blob else 1)


# ----------------------------------------------------------------------------------------------
# Lattice
# ----------------------------------------------------------------------------------------------
class Lattice:
    """Exact 3 km lattice recovered from aois.csv tile centres (EPSG:3577)."""

    def __init__(self, aois_csv):
        from pyproj import Transformer
        aois = pd.read_csv(aois_csv)
        half = float(aois.half_m.iloc[0])
        if not (aois.half_m == half).all():
            raise SystemExit("aois.csv has mixed half_m; the lattice is not a single grid")
        self.half, self.E = half, 2 * half
        to_alb = Transformer.from_crs("EPSG:4326", "EPSG:3577", always_xy=True)
        x, y = to_alb.transform(aois.lon.values, aois.lat.values)
        self.ox = float(np.median(x % self.E))
        self.oy = float(np.median(y % self.E))
        kx = np.round((x - self.ox) / self.E).astype(int)
        ky = np.round((y - self.oy) / self.E).astype(int)
        self.max_resid = float(max(np.abs(x - (self.ox + kx * self.E)).max(),
                                   np.abs(y - (self.oy + ky * self.E)).max()))
        self.stub_k = dict(zip(aois.stub.values, zip(kx.tolist(), ky.tolist())))
        self.n_tiles = len(aois)

    def core_bounds(self, kx, ky):
        cx, cy = self.ox + kx * self.E, self.oy + ky * self.E
        return cx - self.half, cy - self.half, cx + self.half, cy + self.half

    def k_from_xy(self, x, y):
        return (np.round((x - self.ox) / self.E).astype(int),
                np.round((y - self.oy) / self.E).astype(int))

    def dist_to_any_line(self, minx, miny, maxx, maxy):
        def d(v, origin):
            return np.abs(((v - origin + self.E / 2) % self.E) - self.E / 2)
        vx, vy = self.ox - self.half, self.oy - self.half
        return np.minimum.reduce([d(minx, vx), d(maxx, vx), d(miny, vy), d(maxy, vy)])


# ----------------------------------------------------------------------------------------------
# Scan / load
# ----------------------------------------------------------------------------------------------
def scan_bboxes(gpkg, layer):
    """fid + attributes + bbox for every feature, read from the GPKG header envelope."""
    con = sqlite3.connect(gpkg)
    cur = con.execute(f"SELECT fid, {', '.join(ATTR_COLS)}, substr(geom, 1, 72) FROM {layer}")
    fids, attrs, envs, need_full = [], [], [], []
    while True:
        rows = cur.fetchmany(50000)
        if not rows:
            break
        for r in rows:
            _, env = gpb_header_len_and_env(r[-1])
            if env is None:
                need_full.append(r[0])
                env = (np.nan,) * 4
            fids.append(r[0])
            attrs.append(r[1:-1])
            envs.append(env)
    df = pd.DataFrame(attrs, columns=ATTR_COLS)
    df.insert(0, "fid", fids)
    env = np.asarray(envs, dtype=float)
    df["minx"], df["maxx"], df["miny"], df["maxy"] = env[:, 0], env[:, 1], env[:, 2], env[:, 3]
    for fid in need_full:
        blob = con.execute(f"SELECT geom FROM {layer} WHERE fid=?", (fid,)).fetchone()[0]
        df.loc[df.fid == fid, ["minx", "miny", "maxx", "maxy"]] = blob_to_geom(blob).bounds
    srs = con.execute("SELECT srs_id FROM gpkg_geometry_columns WHERE table_name=?",
                      (layer,)).fetchone()[0]
    con.close()
    df["abstain_reason"] = df["abstain_reason"].fillna("")
    return df, int(srs)


def load_geoms(gpkg, layer, fids):
    con = sqlite3.connect(gpkg)
    out = {}
    fids = list(fids)
    for i in range(0, len(fids), 900):
        chunk = fids[i:i + 900]
        q = ",".join("?" * len(chunk))
        for fid, blob in con.execute(f"SELECT fid, geom FROM {layer} WHERE fid IN ({q})", chunk):
            out[fid] = blob_to_geom(blob)
    con.close()
    return out


# ----------------------------------------------------------------------------------------------
# Attribute helpers
# ----------------------------------------------------------------------------------------------
def pvec(r):
    return np.array([r["p_canola"], r["p_cereal"], r["p_legume"]], dtype=float)


def tag(r):
    pi = r["poly_idx"]
    return f"{r['stub']}:{int(pi)}" if pd.notna(pi) else f"{r['stub']}:fid{int(r['fid'])}"


def reconcile(rows_list):
    """Area-weighted mean of class probabilities over a list of attribute dicts.
    Returns (winner, pv, pmin_winner) or None if any probabilities are missing."""
    P = np.array([pvec(r) for r in rows_list])
    if np.isnan(P).any():
        return None
    a = np.array([r["area_ha"] for r in rows_list], dtype=float)
    pv = (a[:, None] * P).sum(0) / a.sum()
    wi = int(np.argmax(pv))
    return CLASSES[wi], pv, float(P[:, wi].min())


class UnionFind:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


# ----------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", help="output GeoPackage (omit with --dry-run)")
    ap.add_argument("--aois", required=True, help="aois.csv defining the lattice")
    ap.add_argument("--layer", default="crops")
    ap.add_argument("--away-csv", required=True, help="one row per away polygon (D1-D3 decisions)")
    ap.add_argument("--pairs-csv", required=True, help="one row per kept-kept cross-tile overlap (M1)")
    ap.add_argument("--summary", help="JSON summary")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reach-m", type=float, default=520.0,
                    help="only polygons whose bbox comes within this of their own core edge can "
                         "touch another tile's raster (national max overshoot measured 500.3 m)")
    ap.add_argument("--cover-min", type=float, default=0.5,
                    help="away polygon covered by >= this fraction by home-tile polygons -> not rescued")
    ap.add_argument("--dup-full", type=float, default=0.95,
                    help="coverage >= this -> pure duplicate, dropped; below it (and >= cover-min) "
                         "the away polygon is unioned into its twin when classes are compatible")
    ap.add_argument("--dup-frac", type=float, default=0.5,
                    help="fraction of the away polygon inside its single largest twin for the pair "
                         "to count as 'the same paddock' (class reconciliation / union)")
    ap.add_argument("--ovl-min", type=float, default=0.5)
    ap.add_argument("--max-area-ha", type=float, default=300.0)
    ap.add_argument("--max-compactness", type=float, default=8.0)
    ap.add_argument("--conflict-pmin", type=float, default=0.25)
    ap.add_argument("--max-merge-n", type=int, default=4)
    ap.add_argument("--no-reconcile", action="store_true",
                    help="keep the owner's class on duplicates; only flag conflicts")
    ap.add_argument("--no-clip", action="store_true", help="skip M2 (leave residual overlaps)")
    ap.add_argument("--clip-max-frac", type=float, default=0.5,
                    help="M2 only subtracts an overlap that is <= this fraction of the losing polygon")
    ap.add_argument("--clip-crumb-ha", type=float, default=0.5,
                    help="M2: discard detached pieces smaller than this after clipping; if larger, do not clip")
    ap.add_argument("--samgeo-dir", help="dir with <stub>.tif composites; enables the raster_cut_m column")
    ap.add_argument("--cut-tol", type=float, default=30.0)
    args = ap.parse_args()
    if not args.dry_run and not args.out:
        ap.error("--out is required unless --dry-run")
    t0 = time.time()

    lat = Lattice(args.aois)
    log(f"lattice: E={lat.E:.0f} m, origin ({lat.ox:.3f}, {lat.oy:.3f}), {lat.n_tiles:,} tiles, "
        f"max centre residual {lat.max_resid:.3f} m")

    # ---------------- scan ----------------
    df, srs_id = scan_bboxes(args.inp, args.layer)
    n_all = len(df)
    if df.stub.isna().any():
        raise SystemExit(f"{int(df.stub.isna().sum())} polygons have no stub; ownership undefined")
    k = np.array([lat.stub_k.get(s, (None, None)) for s in df.stub], dtype=object)
    if any(kk[0] is None for kk in k):
        raise SystemExit("some stubs are not in aois.csv")
    df["kx"] = [kk[0] for kk in k]
    df["ky"] = [kk[1] for kk in k]
    cb = np.array([lat.core_bounds(a, b) for a, b in zip(df.kx, df.ky)])
    d_edge = np.minimum.reduce([df.minx.values - cb[:, 0], df.miny.values - cb[:, 1],
                                cb[:, 2] - df.maxx.values, cb[:, 3] - df.maxy.values])
    df["d_core_edge"] = d_edge            # negative = extends past own core
    df["dist_to_grid_m"] = lat.dist_to_any_line(df.minx.values, df.miny.values,
                                                df.maxx.values, df.maxy.values)
    clean = (df.abstain_reason == "")
    touch10_before = int((df.dist_to_grid_m <= 10).sum())
    part_mask = df.d_core_edge < args.reach_m
    log(f"scanned {n_all:,} polygons ({int(clean.sum()):,} cleanly classified); "
        f"{int((d_edge < 0).sum()):,} extend past their own core (max {(-d_edge).max():.1f} m); "
        f"{int(part_mask.sum()):,} within {args.reach_m:g} m of a lattice line are participants")

    part = df[part_mask].copy()
    geoms = load_geoms(args.inp, args.layer, part.fid.tolist())
    log(f"loaded {len(geoms):,} participant geometries")
    G = np.array([geoms[f] for f in part.fid], dtype=object)
    cen = shapely.centroid(G)
    hk = lat.k_from_xy(shapely.get_x(cen), shapely.get_y(cen))
    part["home_kx"], part["home_ky"] = hk
    part["away"] = (part.home_kx != part.kx) | (part.home_ky != part.ky)
    part = part.reset_index(drop=True)
    rows = {r["fid"]: r for r in part.to_dict("records")}
    for f in rows:
        rows[f]["geom"] = geoms[f]
    n_away = int(part.away.sum())
    log(f"{n_away:,} away polygons (centroid outside own core) = "
        f"{100 * n_away / n_all:.2f}% of all polygons")

    # ---------------- overlap census (before) ----------------
    tree_all = shapely.STRtree(G)
    ii, jj = tree_all.query(G, predicate="intersects")
    m = ii < jj
    ii, jj = ii[m], jj[m]
    fid_arr = part.fid.values
    stub_arr = part.stub.values
    cross = stub_arr[ii] != stub_arr[jj]
    ii, jj = ii[cross], jj[cross]
    inter_before = shapely.area(shapely.intersection(G[ii], G[jj]))
    keep = inter_before > 0
    ii, jj, inter_before = ii[keep], jj[keep], inter_before[keep]
    same_tile_overlaps = int((~cross).sum())
    cls_arr = (part.abstain_reason == "").values
    ov_before_cls = float(inter_before[cls_arr[ii] & cls_arr[jj]].sum() / 1e4)
    log(f"before: {len(ii):,} cross-tile overlapping pairs, pairwise overlap "
        f"{inter_before.sum() / 1e4:,.1f} ha (classified-classified {ov_before_cls:,.1f} ha); "
        f"same-tile overlapping pairs: {same_tile_overlaps}")

    # ---------------- D1-D3: away polygons ----------------
    kept_idx = np.where(~part.away.values)[0]
    tree_kept = shapely.STRtree(G[kept_idx])
    updates = {}          # fid -> dict of attribute/provenance changes on kept polygons
    dropped = set()
    away_recs = []

    def compatible(ra, rb):
        """Class rule R4 for two classified rows -> (ok, winner, pv, pmin, why)."""
        res = reconcile([ra, rb])
        if res is None:
            return False, "", None, np.nan, "missing_probabilities"
        winner, pv, pmin = res
        if ra["pred"] == rb["pred"]:
            return True, winner, pv, pmin, "same_class"
        if winner not in (ra["pred"], rb["pred"]):
            return False, winner, pv, pmin, "conflict_no_majority_class"
        if pmin < args.conflict_pmin:
            return False, winner, pv, pmin, "conflict_confident_disagreement"
        return True, winner, pv, pmin, "class_conflict_reconciled"

    for i in np.where(part.away.values)[0]:
        r = rows[fid_arr[i]]
        g = G[i]
        cand = kept_idx[tree_kept.query(g, predicate="intersects")]
        if r["abstain_reason"] == "":
            cand = [c for c in cand if part.abstain_reason.values[c] in DECIDED]
        inters = [(c, g.intersection(G[c])) for c in cand]
        inters = [(c, x) for c, x in inters if x.area > 0]
        cover = unary_union([x for _, x in inters]).area / g.area if inters else 0.0
        rec = dict(fid=r["fid"], stub=r["stub"], tag=tag(r), pred=r["pred"],
                   abstain_reason=r["abstain_reason"], area_ha=r["area_ha"],
                   own_kx=r["kx"], own_ky=r["ky"], home_kx=r["home_kx"], home_ky=r["home_ky"],
                   cx=round(float(shapely.get_x(cen[i])), 1), cy=round(float(shapely.get_y(cen[i])), 1),
                   n_covering=len(inters), coverage=round(cover, 3),
                   twin_fid=np.nan, twin_pred="", twin_abstain="", twin_frac=np.nan, twin_iou=np.nan,
                   decision="", reason="", lost_ha=0.0, class_conflict=0, reconciled_class="")
        if inters:
            c, x = max(inters, key=lambda t: t[1].area)
            tw = rows[fid_arr[c]]
            rec.update(twin_fid=tw["fid"], twin_pred=tw["pred"] if pd.notna(tw["pred"]) else "",
                       twin_abstain=tw["abstain_reason"], twin_frac=round(x.area / g.area, 3),
                       twin_iou=round(x.area / g.union(G[c]).area, 3))
        if cover < args.cover_min:
            rec["decision"], rec["reason"] = "rescue", "uncovered"
            updates.setdefault(r["fid"], dict(absorbed=[], conflict=0, classes=[]))["rescued"] = True
            away_recs.append(rec)
            continue
        twf = int(rec["twin_fid"])
        tw = rows[twf]
        u = updates.setdefault(twf, dict(absorbed=[], conflict=0, classes=[]))
        both_cls = (r["abstain_reason"] == "" and tw["abstain_reason"] == "")
        is_dup = rec["twin_frac"] >= args.dup_frac
        excl_ha = r["area_ha"] * (1 - cover)
        if cover >= args.dup_full:
            rec["decision"], rec["reason"] = "drop_duplicate", "fully_covered"
            rec["lost_ha"] = round(excl_ha, 3)
        elif not both_cls:
            rec["decision"], rec["reason"] = "drop_partial", "not_both_classified"
            rec["lost_ha"] = round(excl_ha, 3)
        elif not is_dup:
            rec["decision"], rec["reason"] = "drop_partial", "no_single_twin"
            rec["lost_ha"] = round(excl_ha, 3)
        else:
            ok, winner, pv, pmin, why = compatible(tw, r)
            ug = unary_union([tw["geom"], g])
            ua, uc = ug.area / 1e4, ug.length / np.sqrt(ug.area)
            if ug.geom_type != "Polygon":
                ok, why = False, "union_not_single_polygon"
            elif ua > args.max_area_ha:
                ok, why = False, "union_over_max_area"
            elif uc > args.max_compactness:
                ok, why = False, "union_over_max_compactness"
            if ok:
                rec["decision"], rec["reason"] = "union_into_twin", why
                tw["geom"] = ug
                tw["area_ha"] = round(ua, 2)
                tw["compactness"] = float(uc)
                u["geom_changed"] = True
            else:
                rec["decision"], rec["reason"] = "drop_partial", why
                rec["lost_ha"] = round(excl_ha, 3)
        dropped.add(r["fid"])
        u["absorbed"].append(r)
        if both_cls and is_dup and r["pred"] != tw["pred"]:
            rec["class_conflict"] = 1
            u["conflict"] = 1
            u["classes"].append(r["pred"])
            if not args.no_reconcile:
                res = reconcile([tw] + [a for a in u["absorbed"] if a["abstain_reason"] == ""])
                if res is not None:
                    winner, pv, _ = res
                    rec["reconciled_class"] = winner
                    u["new_class"] = (winner, pv)
        away_recs.append(rec)
    A = pd.DataFrame(away_recs)
    dec_counts = A.decision.value_counts().to_dict() if len(A) else {}
    n_dup_conflict = int(A.class_conflict.sum()) if len(A) else 0
    lost_ha = float(A.lost_ha.sum()) if len(A) else 0.0
    log(f"D1-D3: {dec_counts}; {n_dup_conflict:,} absorbed duplicates disagreed in class with "
        f"their twin; exclusive ground discarded with drops: {lost_ha:,.1f} ha")

    # apply reconciled classes / provenance to twins (in memory)
    for f, u in updates.items():
        r = rows[f]
        if u.get("rescued"):
            r["boundary_action"] = "rescued"
        if u["absorbed"]:
            r["boundary_action"] = "absorbed_union" if u.get("geom_changed") else "absorbed"
            r["merge_n"] = 1 + len(u["absorbed"])
            r["merged_from"] = ";".join(tag(a) for a in u["absorbed"])
            r["merged_from_fid"] = ";".join(str(int(a["fid"])) for a in u["absorbed"])
            r["class_conflict"] = u["conflict"]
            if u["conflict"]:
                r["pre_merge_classes"] = "|".join([r["pred"]] + u["classes"])
                if "new_class" in u:
                    winner, pv = u["new_class"]
                    r["pred"] = winner
                    r["confidence"] = round(float(pv.max()), 4)
                    r["p_canola"], r["p_cereal"], r["p_legume"] = [round(float(v), 4) for v in pv]

    # ---------------- M1: kept-kept overlaps (census recomputed on updated geometries) ----------------
    kept_mask = ~part.fid.isin(dropped).values
    for i in np.where(kept_mask)[0]:
        G[i] = rows[fid_arr[i]]["geom"]
    kidx = np.where(kept_mask)[0]
    tree_k = shapely.STRtree(G[kidx])
    ka_, kb_ = tree_k.query(G[kidx], predicate="intersects")
    mk = ka_ < kb_
    ka_, kb_ = kidx[ka_[mk]], kidx[kb_[mk]]
    mk = stub_arr[ka_] != stub_arr[kb_]
    ka_, kb_ = ka_[mk], kb_[mk]
    inter_k = shapely.area(shapely.intersection(G[ka_], G[kb_]))
    mk = inter_k > 0
    ka_, kb_, inter_k = ka_[mk], kb_[mk], inter_k[mk]
    pair_recs = []
    uf = UnionFind()
    accepted_pairs = []
    for a, b, inter in zip(ka_, kb_, inter_k):
        ra, rb = rows[fid_arr[a]], rows[fid_arr[b]]
        small = min(G[a].area, G[b].area)
        ovl_small = inter / small
        iou = inter / G[a].union(G[b]).area
        rec = dict(fid_a=ra["fid"], fid_b=rb["fid"], tag_a=tag(ra), tag_b=tag(rb),
                   pred_a=ra["pred"], pred_b=rb["pred"], abstain_a=ra["abstain_reason"],
                   abstain_b=rb["abstain_reason"], area_a=ra["area_ha"], area_b=rb["area_ha"],
                   inter_ha=round(inter / 1e4, 3), ovl_small=round(ovl_small, 3), iou=round(iou, 3),
                   away_a=int(ra["away"]), away_b=int(rb["away"]),
                   union_area_ha=np.nan, union_comp=np.nan, merged_class="", pmin_winner=np.nan,
                   decision="", reason="", component_id=-1,
                   mid_x=round(float(G[a].intersection(G[b]).centroid.x), 1),
                   mid_y=round(float(G[a].intersection(G[b]).centroid.y), 1))
        if ovl_small < args.ovl_min:
            rec["decision"], rec["reason"] = "leave", "sliver_below_ovl_min"
        elif ra["abstain_reason"] != "" or rb["abstain_reason"] != "":
            rec["decision"], rec["reason"] = "leave", "not_both_classified"
        else:
            u = unary_union([G[a], G[b]])
            ua, uc = u.area / 1e4, u.length / np.sqrt(u.area)
            rec["union_area_ha"], rec["union_comp"] = round(ua, 2), round(uc, 3)
            ok, winner, pv, pmin, why = compatible(ra, rb)
            rec["merged_class"], rec["pmin_winner"] = winner, round(pmin, 3) if pd.notna(pmin) else np.nan
            if u.geom_type != "Polygon":
                rec["decision"], rec["reason"] = "leave", "union_not_single_polygon"
            elif ua > args.max_area_ha:
                rec["decision"], rec["reason"] = "leave", "union_over_max_area"
            elif uc > args.max_compactness:
                rec["decision"], rec["reason"] = "leave", "union_over_max_compactness"
            elif not ok:
                rec["decision"], rec["reason"] = "leave", why
            else:
                rec["decision"], rec["reason"] = "merge", why
        if rec["decision"] == "merge":
            uf.union(ra["fid"], rb["fid"])
            accepted_pairs.append(rec)
        pair_recs.append(rec)
    P = pd.DataFrame(pair_recs)

    # components -> merged features
    comps = {}
    for rec in accepted_pairs:
        comps.setdefault(uf.find(rec["fid_a"]), []).append(rec)
    merged_feats, comp_id = [], 0
    for root, plist in comps.items():
        comp_id += 1
        fids = sorted({f for d in plist for f in (d["fid_a"], d["fid_b"])})
        frs = [rows[f] for f in fids]
        for d in plist:
            d["component_id"] = comp_id
        reason = None
        if len(fids) > args.max_merge_n:
            reason = "component_too_large"
        else:
            u = unary_union([r["geom"] for r in frs])
            ua, uc = u.area / 1e4, u.length / np.sqrt(u.area)
            res = reconcile(frs)
            if u.geom_type != "Polygon":
                reason = "component_union_not_single_polygon"
            elif ua > args.max_area_ha:
                reason = "component_over_max_area"
            elif uc > args.max_compactness:
                reason = "component_over_max_compactness"
            elif res is None:
                reason = "missing_probabilities"
            else:
                winner, pv, pmin = res
                preds = [r["pred"] for r in frs]
                conflict = len(set(preds)) > 1
                if conflict and (winner not in preds or pmin < args.conflict_pmin):
                    reason = "component_conflict"
        if reason:
            for d in plist:
                d["decision"], d["reason"] = "leave", reason
            continue
        areas = np.array([r["area_ha"] for r in frs], dtype=float)
        order = np.argsort(-areas)
        big = frs[order[0]]

        def wmean(col):
            v = np.array([r[col] for r in frs], dtype=float)
            ok = ~np.isnan(v)
            return float((areas[ok] * v[ok]).sum() / areas[ok].sum()) if ok.any() else None
        src_tags, src_fids, pre = [], [], []
        for i in order:
            r = frs[i]
            src_tags.append(tag(r))
            src_fids.append(str(int(r["fid"])))
            pre.append(r["pre_merge_classes"] if r.get("pre_merge_classes") else r["pred"])
            if r.get("merged_from"):
                src_tags.append(r["merged_from"])
                src_fids.append(r["merged_from_fid"])
        any_dup_conflict = any(r.get("class_conflict") for r in frs)
        feat = dict(
            geom=geom_to_blob(u, srs_id), area_ha=round(ua, 2), compactness=float(uc),
            abstain_reason="", stub=big["stub"],
            year=int(big["year"]) if pd.notna(big["year"]) else None,
            poly_idx=float(big["poly_idx"]) if pd.notna(big["poly_idx"]) else None,
            ndvi_amp=round(wmean("ndvi_amp"), 4) if wmean("ndvi_amp") is not None else None,
            pred=winner, confidence=round(float(pv.max()), 4),
            p_canola=round(float(pv[0]), 4), p_cereal=round(float(pv[1]), 4),
            p_legume=round(float(pv[2]), 4),
            n_obs=wmean("n_obs"), clear_frac=wmean("clear_frac"), treed_frac=wmean("treed_frac"),
            n_feat_present=float(np.nanmin([r["n_feat_present"] for r in frs])),
            merged_from=";".join(src_tags), merged_from_fid=";".join(src_fids),
            merge_n=int(sum(r.get("merge_n") or 1 for r in frs)),
            class_conflict=int(conflict or any_dup_conflict),
            pre_merge_classes="|".join(pre), boundary_action="union",
            component_id=comp_id, source_fids=[int(r["fid"]) for r in frs],
            frag_area_ha=float(areas.sum()), union_geom=u,
        )
        merged_feats.append(feat)
    n_union_frag = {f for m in merged_feats for f in m["source_fids"]}
    log(f"M1: {len(P):,} kept-kept cross-tile overlapping pairs; "
        f"{int((P.decision == 'merge').sum()) if len(P) else 0:,} merged into {len(merged_feats):,} "
        f"polygons from {len(n_union_frag):,} fragments; reasons: "
        f"{P.reason.value_counts().to_dict() if len(P) else {}}")

    # ---------------- residual overlap (after) ----------------
    fg_fids = [f for f, km in zip(fid_arr, kept_mask) if km and f not in n_union_frag]
    final_geoms = {f: rows[f]["geom"] for f in fg_fids}
    FG = np.array([final_geoms[f] for f in fg_fids] + [m["union_geom"] for m in merged_feats],
                  dtype=object)
    f_stub = np.array([rows[f]["stub"] for f in fg_fids] + [m["stub"] for m in merged_feats])
    f_cls = np.array([rows[f]["abstain_reason"] == "" for f in fg_fids] + [True] * len(merged_feats))
    tree_f = shapely.STRtree(FG)
    fi, fj = tree_f.query(FG, predicate="intersects")
    mm = (fi < fj)
    fi, fj = fi[mm], fj[mm]
    inter_after = shapely.area(shapely.intersection(FG[fi], FG[fj]))
    ka = inter_after > 0
    fi, fj, inter_after = fi[ka], fj[ka], inter_after[ka]
    ov_after = float(inter_after.sum() / 1e4)
    ov_after_cls = float(inter_after[f_cls[fi] & f_cls[fj]].sum() / 1e4)
    log(f"after D1-M1: {len(fi):,} overlapping pairs among participants, pairwise overlap {ov_after:,.1f} ha "
        f"(classified-classified {ov_after_cls:,.1f} ha)")

    # ---------------- M2: clip residual overlaps to the owning tile ----------------
    def stub_keys(stub, merged_from):
        keys = {lat.stub_k[stub]}
        for t in (merged_from or "").split(";"):
            st = t.split(":")[0]
            if st in lat.stub_k:
                keys.add(lat.stub_k[st])
        return keys
    f_keys = ([stub_keys(rows[f]["stub"], rows[f].get("merged_from")) for f in fg_fids] +
              [stub_keys(m["stub"], m["merged_from"]) for m in merged_feats])
    n_fg = len(fg_fids)
    clip_ha = np.zeros(len(FG))
    clipped = set()
    n_clip_pairs = n_clip_skipped = 0
    clip_skip_reasons = {}
    if not args.no_clip and len(fi):
        order = np.argsort(-inter_after)          # biggest overlaps first
        for a, b in zip(fi[order], fj[order]):
            x = FG[a].intersection(FG[b])
            if x.is_empty or x.area <= 0:
                continue
            pt = x.representative_point()
            ok_ = lat.k_from_xy(np.array([pt.x]), np.array([pt.y]))
            owner = (int(ok_[0][0]), int(ok_[1][0]))
            a_own, b_own = owner in f_keys[a], owner in f_keys[b]
            if a_own and not b_own:
                loser, winner = b, a
            elif b_own and not a_own:
                loser, winner = a, b
            else:
                loser, winner = (a, b) if FG[a].area <= FG[b].area else (b, a)
            if x.area > args.clip_max_frac * FG[loser].area:
                n_clip_skipped += 1
                clip_skip_reasons["overlap_not_a_sliver"] = clip_skip_reasons.get("overlap_not_a_sliver", 0) + 1
                continue
            new = FG[loser].difference(FG[winner]).buffer(0)
            if new.geom_type == "MultiPolygon":
                parts = sorted(new.geoms, key=lambda p: -p.area)
                crumbs = sum(p.area for p in parts[1:]) / 1e4
                if crumbs > args.clip_crumb_ha:
                    n_clip_skipped += 1
                    clip_skip_reasons["would_split_polygon"] = clip_skip_reasons.get("would_split_polygon", 0) + 1
                    continue
                new = parts[0]
            if new.is_empty or new.geom_type != "Polygon" or new.area < 1e3:
                n_clip_skipped += 1
                clip_skip_reasons["loser_would_vanish"] = clip_skip_reasons.get("loser_would_vanish", 0) + 1
                continue
            clip_ha[loser] += (FG[loser].area - new.area) / 1e4
            FG[loser] = new
            clipped.add(loser)
            n_clip_pairs += 1
        # apply to rows / merged_feats
        for i in clipped:
            g = FG[i]
            if i < n_fg:
                f = int(fg_fids[i])      # numpy ints bind as BLOBs in sqlite3: the UPDATE would match nothing
                r = rows[f]
                r["geom"] = g
                r["area_ha"] = round(g.area / 1e4, 2)
                r["compactness"] = float(g.length / np.sqrt(g.area))
                r["clip_ha"] = round(float(clip_ha[i]), 3)
                r["boundary_action"] = (r.get("boundary_action") + "+clipped") if r.get("boundary_action") else "clipped"
                updates.setdefault(f, dict(absorbed=[], conflict=0, classes=[]))["geom_changed"] = True
            else:
                m = merged_feats[i - n_fg]
                m["union_geom"] = g
                m["geom"] = geom_to_blob(g, srs_id)
                m["area_ha"] = round(g.area / 1e4, 2)
                m["compactness"] = float(g.length / np.sqrt(g.area))
                m["clip_ha"] = round(float(clip_ha[i]), 3)
                m["boundary_action"] = "union+clipped"
        tree_f2 = shapely.STRtree(FG)
        gi, gj = tree_f2.query(FG, predicate="intersects")
        mm2 = gi < gj
        gi, gj = gi[mm2], gj[mm2]
        inter2 = shapely.area(shapely.intersection(FG[gi], FG[gj]))
        ov_m2 = float(inter2[inter2 > 0].sum() / 1e4)
        n_ov_m2 = int((inter2 > 0).sum())
        log(f"M2: clipped {n_clip_pairs:,} residual overlaps from {len(clipped):,} polygons "
            f"({clip_ha.sum():,.1f} ha removed); skipped {n_clip_skipped:,} {clip_skip_reasons}; "
            f"overlap now {ov_m2:,.1f} ha in {n_ov_m2:,} pairs")
    else:
        ov_m2, n_ov_m2 = ov_after, int(len(fi))
    for m in merged_feats:
        m.setdefault("clip_ha", None)

    # ---------------- raster_cut_m: boundary length along the own tile raster edge(s) ----------------
    raster_cut = {}
    if args.samgeo_dir:
        import os
        import rasterio
        from pyproj import Transformer
        t6933 = Transformer.from_crs("EPSG:6933", "EPSG:3577", always_xy=True)
        inv_k = {v: k for k, v in lat.stub_k.items()}
        edge_cache = {}

        def edge_buf(stub):
            if stub not in edge_cache:
                pth = f"{args.samgeo_dir}/{stub}.tif"
                if not os.path.exists(pth):
                    edge_cache[stub] = None
                else:
                    with rasterio.open(pth) as src:
                        b = src.bounds
                    xs, ys = np.linspace(b.left, b.right, 25), np.linspace(b.bottom, b.top, 25)
                    ring = ([(x, b.bottom) for x in xs] + [(b.right, y) for y in ys] +
                            [(x, b.top) for x in xs[::-1]] + [(b.left, y) for y in ys[::-1]])
                    edge_cache[stub] = shapely.Polygon([t6933.transform(x, y) for x, y in ring]).exterior.buffer(args.cut_tol)
            return edge_cache[stub]

        def cut_of(g, keys):
            tot = 0.0
            for k in keys:
                st = inv_k.get(k)
                eb = edge_buf(st) if st else None
                if eb is not None and g.intersects(eb):
                    tot += g.boundary.intersection(eb).length
            return round(float(tot), 1)
        # every non-participant polygon: own tile only (cheap: bbox test first)
        non_part = df[~part_mask]
        np_geoms = load_geoms(args.inp, args.layer, non_part.fid.tolist())
        for f, st in zip(non_part.fid.values, non_part.stub.values):
            raster_cut[int(f)] = cut_of(np_geoms[f], {lat.stub_k[st]})
        for i, f in enumerate(fg_fids):
            raster_cut[int(f)] = cut_of(FG[i], f_keys[i])
        for i, m in enumerate(merged_feats):
            m["raster_cut_m"] = cut_of(FG[n_fg + i], f_keys[n_fg + i])
        n_cut = sum(1 for v in raster_cut.values() if v >= 100) + sum(1 for m in merged_feats if m["raster_cut_m"] >= 100)
        log(f"raster_cut_m computed for {len(raster_cut) + len(merged_feats):,} polygons; "
            f"{n_cut:,} have >= 100 m of boundary within {args.cut_tol:g} m of their own raster edge")
    else:
        for m in merged_feats:
            m["raster_cut_m"] = None

    # ---------------- write decision tables + summary ----------------
    A.to_csv(args.away_csv, index=False)
    P.to_csv(args.pairs_csv, index=False)
    part_cls = part[part.abstain_reason == ""]
    summary = dict(
        input=args.inp, n_polygons=n_all, n_clean_classified=int(clean.sum()),
        n_participants=int(part_mask.sum()), n_extend_past_core=int((d_edge < 0).sum()),
        max_overshoot_m=round(float((-d_edge).max()), 1),
        n_away=n_away, pct_away_of_all=round(100 * n_away / n_all, 3),
        n_away_classified=int(part_cls.away.sum()),
        away_by_abstain=part[part.away].abstain_reason.replace("", "classified").value_counts().to_dict(),
        n_cross_tile_overlap_pairs_before=int(len(ii)),
        overlap_ha_before=round(float(inter_before.sum() / 1e4), 1),
        overlap_ha_before_classified=round(ov_before_cls, 1),
        away_decisions=dec_counts,
        away_decision_reasons=({f"{d}/{r}": int(n) for (d, r), n in A.groupby(["decision", "reason"]).size().items()}
                               if len(A) else {}),
        away_decisions_classified=(A[A.abstain_reason == ""].decision.value_counts().to_dict()
                                   if len(A) else {}),
        n_away_removed=len(dropped),
        lost_exclusive_ha=round(lost_ha, 1),
        lost_exclusive_ha_classified=(round(float(A[A.abstain_reason == ""].lost_ha.sum()), 1)
                                      if len(A) else 0.0),
        n_dup_class_conflicts=n_dup_conflict,
        n_dup_classified_pairs=int((A.decision.isin(["drop_duplicate", "union_into_twin", "drop_partial"]) &
                                    (A.abstain_reason == "") & (A.twin_abstain == "") &
                                    (A.twin_frac >= args.dup_frac)).sum()) if len(A) else 0,
        n_twins_reconciled=int(sum(1 for u in updates.values() if "new_class" in u)),
        n_twins_geom_changed=int(sum(1 for u in updates.values() if u.get("geom_changed"))),
        n_kept_pairs=int(len(P)), n_pairs_merged=int((P.decision == "merge").sum()) if len(P) else 0,
        pair_reasons=P.reason.value_counts().to_dict() if len(P) else {},
        n_union_polygons=len(merged_feats), n_union_fragments=len(n_union_frag),
        n_union_class_conflict=int(sum(m["class_conflict"] for m in merged_feats)),
        union_merge_n_hist=pd.Series([m["merge_n"] for m in merged_feats]).value_counts().sort_index().to_dict(),
        union_area_ha_total=round(sum(m["area_ha"] for m in merged_feats), 1),
        union_area_ha_median=(round(float(np.median([m["area_ha"] for m in merged_feats])), 2)
                              if merged_feats else None),
        overlap_ha_after_d1_m1=round(ov_after, 1), overlap_ha_after_d1_m1_classified=round(ov_after_cls, 1),
        n_overlap_pairs_after_d1_m1=int(len(fi)),
        m2_clipped_pairs=n_clip_pairs, m2_clipped_polygons=len(clipped), m2_clipped_ha=round(float(clip_ha.sum()), 1),
        m2_skipped=n_clip_skipped, m2_skip_reasons=clip_skip_reasons,
        overlap_ha_after=round(ov_m2, 1), n_overlap_pairs_after=n_ov_m2,
        n_raster_cut_ge_100=(sum(1 for v in raster_cut.values() if v >= 100) +
                             sum(1 for m in merged_feats if (m.get("raster_cut_m") or 0) >= 100)) if args.samgeo_dir else None,
        n_touch10_before=touch10_before, pct_touch10_before=round(100 * touch10_before / n_all, 3),
        thresholds=dict(reach_m=args.reach_m, cover_min=args.cover_min, dup_frac=args.dup_frac,
                        ovl_min=args.ovl_min, max_area_ha=args.max_area_ha,
                        max_compactness=args.max_compactness, conflict_pmin=args.conflict_pmin,
                        max_merge_n=args.max_merge_n, reconcile=not args.no_reconcile,
                        clip=not args.no_clip, clip_max_frac=args.clip_max_frac, clip_crumb_ha=args.clip_crumb_ha,
                        cut_tol=args.cut_tol),
    )

    # ---------------- write output ----------------
    if not args.dry_run:
        log(f"copying {args.inp} -> {args.out}")
        shutil.copyfile(args.inp, args.out)
        con = sqlite3.connect(args.out)
        register_gpkg_functions(con)
        existing = {r[1] for r in con.execute(f"PRAGMA table_info({args.layer})")}
        for c, t in PROV_COLS:
            if c not in existing:
                con.execute(f'ALTER TABLE "{args.layer}" ADD COLUMN "{c}" {t}')
        del_fids = sorted(dropped | n_union_frag)
        con.executemany(f'DELETE FROM "{args.layer}" WHERE fid=?', [(int(f),) for f in del_fids])
        upd_rows, upd_geom_rows = [], []
        for f, u in updates.items():
            if f in n_union_frag or f in dropped:
                continue
            r = rows[f]
            attrs = tuple(_py(v) for v in (r["pred"], r["confidence"], r["p_canola"], r["p_cereal"], r["p_legume"],
                     r.get("merged_from"), r.get("merged_from_fid"), r.get("merge_n"),
                     r.get("class_conflict"), r.get("pre_merge_classes"), r.get("boundary_action"),
                     r.get("clip_ha")))
            if u.get("geom_changed"):
                upd_geom_rows.append((geom_to_blob(r["geom"], srs_id), float(r["area_ha"]),
                                      float(r["compactness"])) + attrs + (int(f),))
            else:
                upd_rows.append(attrs + (int(f),))
        set_attrs = ('pred=?, confidence=?, p_canola=?, p_cereal=?, p_legume=?, merged_from=?, '
                     'merged_from_fid=?, merge_n=?, class_conflict=?, pre_merge_classes=?, '
                     'boundary_action=?, clip_ha=?')
        con.executemany(f'UPDATE "{args.layer}" SET {set_attrs} WHERE fid=?', upd_rows)
        con.executemany(f'UPDATE "{args.layer}" SET geom=?, area_ha=?, compactness=?, {set_attrs} '
                        f'WHERE fid=?', upd_geom_rows)
        upd_rows += upd_geom_rows
        cols = ["geom", "area_ha", "compactness", "abstain_reason", "stub", "year", "poly_idx",
                "ndvi_amp", "pred", "confidence", "p_canola", "p_cereal", "p_legume", "n_obs",
                "clear_frac", "treed_frac", "n_feat_present"] + [c for c, _ in PROV_COLS]
        con.executemany(f'INSERT INTO "{args.layer}" ({",".join(cols)}) VALUES ({",".join("?" * len(cols))})',
                        [tuple(m[c] for c in cols) for m in merged_feats])
        if raster_cut:
            con.executemany(f'UPDATE "{args.layer}" SET raster_cut_m=? WHERE fid=?',
                            [(float(v), int(f)) for f, v in raster_cut.items()])
        ext = con.execute(f"SELECT min(minx), min(miny), max(maxx), max(maxy) FROM rtree_{args.layer}_geom").fetchone()
        if ext and ext[0] is not None:
            con.execute("UPDATE gpkg_contents SET min_x=?, min_y=?, max_x=?, max_y=? WHERE table_name=?",
                        (*ext, args.layer))
        con.commit()
        n_after = con.execute(f'SELECT count(*) FROM "{args.layer}"').fetchone()[0]
        n_rt = con.execute(f"SELECT count(*) FROM rtree_{args.layer}_geom").fetchone()[0]
        con.close()
        log(f"wrote {args.out}: {n_after:,} features (rtree {n_rt:,}); {len(del_fids):,} deleted, "
            f"{len(upd_rows):,} updated, {len(merged_feats):,} inserted")
        df2, _ = scan_bboxes(args.out, args.layer)
        d2 = lat.dist_to_any_line(df2.minx.values, df2.miny.values, df2.maxx.values, df2.maxy.values)
        summary.update(output=args.out, n_polygons_after=int(n_after), n_deleted=len(del_fids),
                       n_updated=len(upd_rows), n_inserted=len(merged_feats),
                       n_clean_classified_after=int((df2.abstain_reason == "").sum()),
                       n_touch10_after=int((d2 <= 10).sum()),
                       pct_touch10_after=round(100 * float((d2 <= 10).mean()), 3))
    summary["elapsed_s"] = round(time.time() - t0, 1)
    if args.summary:
        with open(args.summary, "w") as f:
            json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
