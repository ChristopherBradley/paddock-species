#!/usr/bin/env python3
"""
Compare the three INDEPENDENT reference products against EACH OTHER -- WorldCereal 2021,
NLUM v7 2020-21 and the ABS / ABARES sown-area statistics -- to establish the inter-reference
disagreement floor. The project already does this for one pair (ABS vs ABARES, median 6.8 %
on national sown area, `output/ABS_COMPARISON_100km.md`); this extends it to the full
pairwise matrix. Nothing here touches our own map or any GRDC/NVT record.

Three stages, because one of them is too heavy for a login node:

  overlay   Aggregate WorldCereal's 10 m classification to a crop FRACTION inside every 250 m
            NLUM cell (GDAL warp, average resampling -- exact area-weighted fraction, handles
            the non-integer 24.46:1 pixel ratio and the 4326/4283 CRS difference properly),
            for every 256x256-cell NLUM block that touches the project's national tile mask
            (`national2024/aois.csv`, the same footprint the map was run on). Also rasterises
            the SA2 index onto the NLUM grid. ~18 M cropping-zone cells x 2 layers; measured
            at ~2 s per 273x273 block on a login node, so ~20-30 min single-threaded -- past
            the 1800 s login-node CPU limit, hence the (single, modest) PBS job in
            `reference_intercompare.pbs`.
  analyse   One chunked pass over the NLUM grid accumulating area-weighted histograms:
            joint (NLUM probability x WorldCereal fraction) per state, and per-SA2 marginal
            histograms of every quantity. Every threshold choice is then applied POST-HOC to
            the histograms, so the sensitivity tables cost nothing and cannot drift from the
            headline numbers. Writes `hists.npz` + `sa2_scalars.csv`.
  report    Reads the histograms and the ABS/ABARES tables, builds the pairwise matrix and
            writes `output/REFERENCE_INTERCOMPARISON.md`. Cheap; re-runnable on a login node.

NLUM SEMANTICS THAT DRIVE THE DESIGN (checked empirically, see the report): the 25 commodity
layers sum to ~10,000 basis points per pixel (median 10,035 in the cropping zone), i.e. they
are a per-pixel PARTITION over agricultural commodities, conditional on the pixel being
agricultural land (nodata elsewhere, and the six crop layers share one nodata mask). So
P(crop) is the SUM over crop layers, not the max, and sum(p x cell area) is a well-founded
expected area. The max is kept as a secondary variant because the task brief asked for it.

Cell areas are computed exactly on the GRS80 ellipsoid per latitude row (the NLUM grid is
geographic, so a cell is ~11 % smaller at Esperance than at Emerald).

    python3 reference_intercompare.py overlay  --out-dir $OUT --workers 4
    python3 reference_intercompare.py analyse  --out-dir $OUT
    python3 reference_intercompare.py report   --out-dir $OUT --report ../../output/REFERENCE_INTERCOMPARISON.md
"""
import argparse
import json
import os
import re
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from multiprocessing import Pool

import numpy as np
import pandas as pd
import rasterio
from affine import Affine
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.windows import Window

NLUM_DIR = "/g/data/xe2/cb8590/paddock-species-data/raw/NLUM_v7_250_AgProbabilitySurfaces_2020_21_geo_package_20241128"
NLUM_LAYERS = {
    "W_CER": "331_5_W_CER", "S_CER": "331_6_S_CER_EX_RICE",
    "W_OIL": "334_10_W_OILSEEDS", "S_OIL": "334_11_S_OILSEEDS",
    "W_LEG": "338_8_W_LEGUMES", "S_LEG": "338_9_S_LEGUMES",
    "HAY": "333_13_HAY", "COTTON": "336_14_COTTON", "RICE": "439_7_RICE", "VEG": "353_16_VEGETABLES",
}
NLUM_NODATA = 32767
WC_VRT = {
    "tc": "/scratch/xe2/cb8590/paddock-species-data/derived/worldcereal_compare/temporarycrops.vrt",
    "wc": "/scratch/xe2/cb8590/paddock-species-data/derived/worldcereal_compare/wintercereals.vrt",
}
AOIS = "/scratch/xe2/cb8590/paddock-species-data/derived/national2024/aois.csv"
ABS_DIR = "/scratch/xe2/cb8590/paddock-species-data/derived/abs"
SA2_SHP = f"{ABS_DIR}/SA2_2021_AUST_GDA2020.shp"
ABS_RAW = f"{ABS_DIR}/abs_broadacre_raw.csv"
ABARES_XLSX = f"{ABS_DIR}/03_AustCropRrt20260602_StateCropData_v1.0.0.xlsx"
DEFAULT_OUT = "/scratch/xe2/cb8590/paddock-species-data/derived/reference_intercompare"

ALBERS = "EPSG:3577"
TILE_EDGE_M = 3000.0          # nlum_tiles.py --half-m 1500
BLOCK = 256
NB = 101                      # percent bins 0..100
STATES = {0: "(no SA2)", 1: "New South Wales", 2: "Victoria", 3: "Queensland", 4: "South Australia",
          5: "Western Australia", 6: "Tasmania", 7: "Northern Territory",
          8: "Australian Capital Territory", 9: "Other Territories"}
NST = 10
# The NLUM-derived quantities that get a per-SA2 histogram. Values are percent (0-100).
QUANT = ["cereal_w", "cereal_ws", "oilseed_w", "legume_w", "legume_ws",
         "crop3_sum", "crop3_max", "grain_cotton_rice", "cropall_sum"]
JOINT = [("crop3_sum", "tc"), ("crop3_max", "tc"), ("cropall_sum", "tc"), ("grain_cotton_rice", "tc"),
         ("cereal_w", "wc"), ("cereal_ws", "wc")]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


# ----------------------------------------------------------------------------------- geometry
def nlum_grid():
    with rasterio.open(f"{NLUM_DIR}/NLUM_v7_probSurf_2021_{NLUM_LAYERS['W_CER']}.tif") as s:
        return s.crs, s.transform, s.height, s.width, s.bounds


def row_areas_m2(transform, r0, r1):
    """Exact GRS80 ellipsoid area of one cell in each row r0..r1-1 (geographic grid: the cell
    width in metres shrinks with latitude, so a flat 'cell = 6.25 ha' would be ~10 % wrong)."""
    a = 6378137.0
    f = 1 / 298.257222101
    e2 = f * (2 - f)
    e = np.sqrt(e2)
    b = a * (1 - f)

    def F(phi):
        s = np.sin(phi)
        return s / (1 - e2 * s * s) + np.log((1 + e * s) / (1 - e * s)) / (2 * e)

    rows = np.arange(r0, r1)
    lat_top = np.deg2rad(transform.f + rows * transform.e)
    lat_bot = np.deg2rad(transform.f + (rows + 1) * transform.e)
    dlon = np.deg2rad(abs(transform.a))
    return (b * b / 2) * dlon * (F(lat_top) - F(lat_bot))


def cropzone_mask(crs, transform, H, W):
    """The national tile mask (aois.csv) on the NLUM grid. The 3 km Albers grid is rebuilt
    exactly as nlum_tiles.py built it (verified: tile centres reproduce lat/lon to 5e-7 deg)."""
    with rasterio.open(f"{NLUM_DIR}/NLUM_v7_probSurf_2021_{NLUM_LAYERS['W_CER']}.tif") as s:
        tr, w, h = calculate_default_transform(s.crs, ALBERS, s.width, s.height, *s.bounds,
                                               resolution=TILE_EDGE_M)
    A = pd.read_csv(AOIS)
    m = np.zeros((h, w), np.uint8)
    m[A.grid_r.values, A.grid_c.values] = 1
    out = np.zeros((H, W), np.uint8)
    reproject(m, out, src_transform=tr, src_crs=ALBERS, dst_transform=transform, dst_crs=crs,
              resampling=Resampling.nearest, src_nodata=None, dst_nodata=None)
    return out


# ------------------------------------------------------------------------------------ overlay
_WC = {}
_GRID = {}


def _init_worker(crs_wkt, transform):
    _GRID["crs"] = crs_wkt
    _GRID["tr"] = transform
    for k, p in WC_VRT.items():
        _WC[k] = rasterio.open(p)


def _warp_block(blk):
    r0, c0, h, w = blk
    tr = _GRID["tr"] * Affine.translation(c0, r0)
    out = {}
    for k, src in _WC.items():
        dst = np.zeros((h, w), np.float32)
        # classification band is 0/100 with NO nodata (see raw/worldcereal/README.md), so the
        # area-weighted mean IS the percent of the 250 m cell that WorldCereal calls this class.
        reproject(rasterio.band(src, 1), dst, dst_transform=tr, dst_crs=_GRID["crs"],
                  resampling=Resampling.average, src_nodata=None, dst_nodata=None, num_threads=1)
        out[k] = np.clip(np.rint(dst), 0, 100).astype(np.uint8)
    return r0, c0, out


def cmd_overlay(args):
    os.makedirs(args.out_dir, exist_ok=True)
    crs, transform, H, W, bounds = nlum_grid()
    prof = dict(driver="GTiff", height=H, width=W, count=1, crs=crs, transform=transform,
                tiled=True, blockxsize=BLOCK, blockysize=BLOCK, compress="lzw")

    log("cropping-zone mask from aois.csv -> NLUM grid")
    mask = cropzone_mask(crs, transform, H, W)
    with rasterio.open(f"{args.out_dir}/cropzone_mask250.tif", "w", dtype="uint8", nodata=None, **prof) as d:
        d.write(mask, 1)
    log(f"  {int(mask.sum()):,} NLUM cells in zone")

    blocks = []
    for r0 in range(0, H, BLOCK):
        for c0 in range(0, W, BLOCK):
            h, w = min(BLOCK, H - r0), min(BLOCK, W - c0)
            if mask[r0:r0 + h, c0:c0 + w].any():
                blocks.append((r0, c0, h, w))
    if args.max_blocks:
        blocks = blocks[:args.max_blocks]
    log(f"{len(blocks)} blocks of {BLOCK}x{BLOCK} touch the zone; warping WorldCereal with "
        f"{args.workers} workers")

    frac = {k: np.full((H, W), 255, np.uint8) for k in WC_VRT}
    t0 = time.time()
    with Pool(args.workers, initializer=_init_worker, initargs=(crs.to_wkt(), transform)) as pool:
        for i, (r0, c0, out) in enumerate(pool.imap_unordered(_warp_block, blocks, chunksize=2), 1):
            for k, a in out.items():
                frac[k][r0:r0 + a.shape[0], c0:c0 + a.shape[1]] = a
            if i % 25 == 0 or i == len(blocks):
                el = time.time() - t0
                log(f"  {i}/{len(blocks)} blocks, {el/60:.1f} min elapsed, "
                    f"eta {el/i*(len(blocks)-i)/60:.1f} min")
    for k, a in frac.items():
        with rasterio.open(f"{args.out_dir}/wc_{k}_frac250.tif", "w", dtype="uint8", nodata=255, **prof) as d:
            d.write(a, 1)
        log(f"wrote wc_{k}_frac250.tif ({100*(a != 255).mean():.1f} % of grid processed)")
    json.dump({"blocks": len(blocks), "block": BLOCK, "workers": args.workers,
               "minutes": (time.time() - t0) / 60, "zone_cells": int(mask.sum())},
              open(f"{args.out_dir}/overlay_meta.json", "w"), indent=1)
    del frac, mask

    # LAST, and after freeing the fraction rasters: rasterising 2,473 SA2 polygons onto the grid
    # peaks at ~1.65 GB on its own, and stacking it on top of the mask + fraction arrays is what
    # got the login-node smoke test killed. Nothing expensive is lost if this step fails.
    if args.skip_sa2:
        log("--skip-sa2: not rasterising the SA2 index")
        return
    log("rasterising SA2 index onto the NLUM grid")
    import geopandas as gpd
    from rasterio.features import rasterize
    S = gpd.read_file(SA2_SHP)[["SA2_CODE21", "SA2_NAME21", "STE_CODE21", "STE_NAME21", "geometry"]]
    S = S[S.geometry.notna()].reset_index(drop=True).to_crs(crs)
    S["idx"] = np.arange(1, len(S) + 1)
    S.drop(columns="geometry").to_csv(f"{args.out_dir}/sa2_lookup.csv", index=False)
    sa2 = rasterize(((g, i) for g, i in zip(S.geometry, S.idx)), out_shape=(H, W),
                    transform=transform, fill=0, dtype="int16")
    with rasterio.open(f"{args.out_dir}/sa2_index250.tif", "w", dtype="int16", nodata=0, **prof) as d:
        d.write(sa2, 1)
    log(f"wrote sa2_index250.tif ({len(S)} SA2s)")


# ------------------------------------------------------------------------------------ analyse
def _pct(bp, top=100):
    """basis points (int32, possibly summed) -> integer percent bin, rounded half-up, uint8"""
    return np.minimum((bp + 50) // 100, top).astype(np.uint8)


def cmd_analyse(args):
    crs, transform, H, W, bounds = nlum_grid()
    rd = {k: rasterio.open(f"{args.out_dir}/{k}") for k in
          ["cropzone_mask250.tif", "sa2_index250.tif", "wc_tc_frac250.tif", "wc_wc_frac250.tif"]}
    nl = {k: rasterio.open(f"{NLUM_DIR}/NLUM_v7_probSurf_2021_{v}.tif") for k, v in NLUM_LAYERS.items()}
    lut = pd.read_csv(f"{args.out_dir}/sa2_lookup.csv")
    n_sa2 = int(lut.idx.max())
    state_of = np.zeros(n_sa2 + 1, np.int64)
    state_of[lut.idx.values] = lut.STE_CODE21.values.astype(int)

    joint = {f"{q}|{w}": np.zeros(NST * NB * NB) for q, w in JOINT}          # zone & nlum-valid & wc-valid
    nodata_wc = {w: np.zeros(NST * NB) for w in ("tc", "wc")}               # zone & NLUM nodata: what WC says
    sa2_q = {d: {q: np.zeros((n_sa2 + 1) * NB) for q in QUANT} for d in ("zone", "all")}
    sa2_w = {d: {w: np.zeros((n_sa2 + 1) * NB) for w in ("tc", "wc")} for d in ("zone", "proc")}
    scal = {k: np.zeros(n_sa2 + 1) for k in
            ["area_all", "area_nlumvalid", "area_zone", "area_zone_nlumvalid", "area_zone_wcvalid", "area_proc"]}
    sumcheck = np.zeros(NB * 2)   # histogram of the 10-layer partial sum in percent (0..200), zone cells

    row_lo, row_hi = (args.rows if args.rows else (0, H))
    chunk = args.chunk_rows
    t0 = time.time()
    for r0 in range(row_lo, row_hi, chunk):
        r1 = min(row_hi, r0 + chunk)
        win = Window(0, r0, W, r1 - r0)
        h = r1 - r0
        n = h * W
        # Everything below works on FLAT arrays and on index subsets chosen once per domain --
        # the first version masked 9.7 M-cell int64 arrays ~45 times per chunk and peaked at
        # 2 GB, which the login node killed and which would have cost the job ~3 h.
        mask = rd["cropzone_mask250.tif"].read(1, window=win).ravel().astype(bool)
        sa2 = rd["sa2_index250.tif"].read(1, window=win).ravel().astype(np.int32)
        tc = rd["wc_tc_frac250.tif"].read(1, window=win).ravel()
        wc = rd["wc_wc_frac250.tif"].read(1, window=win).ravel()
        L = {}
        for k, s in nl.items():
            a = s.read(1, window=win).ravel()
            if k == "W_CER":
                valid = a != NLUM_NODATA
            a[a == NLUM_NODATA] = 0
            L[k] = a.astype(np.int32)
        area = np.repeat(row_areas_m2(transform, r0, r1), W)
        wcvalid = tc != 255
        if not valid.any() and not wcvalid.any():
            scal["area_all"] += np.bincount(sa2, weights=area, minlength=n_sa2 + 1)
            continue

        crop3 = L["W_CER"] + L["S_CER"] + L["W_OIL"] + L["S_OIL"] + L["W_LEG"] + L["S_LEG"]
        Q = {
            "cereal_w": _pct(L["W_CER"]),
            "cereal_ws": _pct(L["W_CER"] + L["S_CER"]),
            "oilseed_w": _pct(L["W_OIL"]),
            "legume_w": _pct(L["W_LEG"]),
            "legume_ws": _pct(L["W_LEG"] + L["S_LEG"]),
            "crop3_sum": _pct(crop3),
            "crop3_max": _pct(np.maximum.reduce([L[k] for k in ("W_CER", "S_CER", "W_OIL", "S_OIL", "W_LEG", "S_LEG")])),
            "grain_cotton_rice": _pct(crop3 + L["COTTON"] + L["RICE"]),
            "cropall_sum": _pct(crop3 + L["COTTON"] + L["RICE"] + L["HAY"] + L["VEG"]),
        }
        tot10 = _pct(sum(L.values()), 2 * NB - 1)
        del L, crop3
        Wf = {"tc": tc, "wc": wc}

        def acc(target, ii, key_fn, nbins):
            if len(ii):
                target += np.bincount(key_fn(ii), weights=area[ii], minlength=nbins)

        dom = {
            "valid": np.flatnonzero(valid),
            "zone": np.flatnonzero(mask),
            "zv": np.flatnonzero(mask & valid),
            "zvw": np.flatnonzero(mask & valid & wcvalid),
            "znw": np.flatnonzero(mask & ~valid & wcvalid),
            "zw": np.flatnonzero(mask & wcvalid),
            "proc": np.flatnonzero(wcvalid),
        }
        scal["area_all"] += np.bincount(sa2, weights=area, minlength=n_sa2 + 1)
        for key, d in [("area_nlumvalid", "valid"), ("area_zone", "zone"), ("area_zone_nlumvalid", "zv"),
                       ("area_zone_wcvalid", "zw"), ("area_proc", "proc")]:
            acc(scal[key], dom[d], lambda ii: sa2[ii], n_sa2 + 1)
        ii = dom["zvw"]
        st_ii = state_of[sa2[ii]]
        for q, w in JOINT:
            acc(joint[f"{q}|{w}"], ii, lambda jj: (st_ii * NB + Q[q][jj]) * NB + Wf[w][jj], NST * NB * NB)
        ii = dom["znw"]
        st_ii = state_of[sa2[ii]]
        for w in ("tc", "wc"):
            acc(nodata_wc[w], ii, lambda jj: st_ii * NB + Wf[w][jj], NST * NB)
        for d, dn in (("zone", "zw"), ("proc", "proc")):
            ii = dom[dn]
            s_ii = sa2[ii].astype(np.int64) * NB
            for w in ("tc", "wc"):
                acc(sa2_w[d][w], ii, lambda jj: s_ii + Wf[w][jj], (n_sa2 + 1) * NB)
        for d, dn in (("zone", "zv"), ("all", "valid")):
            ii = dom[dn]
            s_ii = sa2[ii].astype(np.int64) * NB
            for q in QUANT:
                acc(sa2_q[d][q], ii, lambda jj: s_ii + Q[q][jj], (n_sa2 + 1) * NB)
        acc(sumcheck, dom["zv"], lambda jj: tot10[jj].astype(np.int64), 2 * NB)
        log(f"rows {r0}-{r1} done ({(time.time()-t0)/60:.1f} min; zone cells {len(dom['zone']):,})")

    np.savez_compressed(f"{args.out_dir}/hists.npz",
                        **{f"joint|{k}": v.reshape(NST, NB, NB) for k, v in joint.items()},
                        **{f"nodata_wc|{w}": v.reshape(NST, NB) for w, v in nodata_wc.items()},
                        **{f"sa2q|{d}|{q}": v.reshape(n_sa2 + 1, NB) for d in sa2_q for q, v in sa2_q[d].items()},
                        **{f"sa2w|{d}|{w}": v.reshape(n_sa2 + 1, NB) for d in sa2_w for w, v in sa2_w[d].items()},
                        sumcheck=sumcheck, state_of=state_of)
    pd.DataFrame({"idx": np.arange(n_sa2 + 1), **scal}).to_csv(f"{args.out_dir}/sa2_scalars.csv", index=False)
    log("wrote hists.npz, sa2_scalars.csv")


# ---------------------------------------------------------------------------- reference tables
def load_abs_raw():
    """ABS AG_BROADACRE, tidied with the crop-year convention of abs_fetch.py (financial year
    2022-23 -> winter crop sown in 2022). Returns long table: level, region, crop_year, item, ha."""
    d = pd.read_csv(ABS_RAW, low_memory=False)
    d = d[d.UNIT_MEASURE == "HA"].copy()
    d["level"] = d.REGION.astype(str).str.len().map({1: "state", 3: "national_agg", 9: "SA2"})
    d["crop_year"] = d.TIME_PERIOD.str.slice(0, 4).astype(int)
    d["item"] = d.DATAITEM.str.replace("Broad", "").str.replace("_Area_Total", "")
    return d.groupby(["level", "REGION", "crop_year", "item"], as_index=False).OBS_VALUE.sum() \
            .rename(columns={"REGION": "region", "OBS_VALUE": "ha"})


ABS_DEFS = {   # item names as they appear after stripping Broad/_Area_Total
    "canola": ["Canola"],
    "cereal_wb": ["Wheat", "Barley"],                       # the project's ABS 'Cereal'
    "wintercereal": ["Wheat", "Barley", "Oats"],            # ABS has no triticale item
    "legume4": ["Lupins", "Chickpeas", "Fababeans", "Lentils"],   # the project's ABS 'Legume'
    "legume5": ["Lupins", "Chickpeas", "Fababeans", "Lentils", "Fieldpeas"],
    "all14": ["Lentils", "Lupins", "Cotton", "Canola", "Barley", "Chickpeas", "Fieldpeas", "Sugarcane",
              "Oats", "Wheat", "Fababeans", "Rice", "Maize", "Sorghum"],
    "grain_cotton_rice": ["Lentils", "Lupins", "Cotton", "Canola", "Barley", "Chickpeas", "Fieldpeas",
                          "Oats", "Wheat", "Fababeans", "Rice", "Maize", "Sorghum"],
}


def abs_groups(d, level):
    p = d[d.level == level].pivot_table(index=["region", "crop_year"], columns="item", values="ha",
                                        aggfunc="sum").fillna(0.0)
    out = pd.DataFrame(index=p.index)
    for g, items in ABS_DEFS.items():
        out[g] = p.reindex(columns=items).fillna(0.0).sum(axis=1)
    return out.reset_index()


def _xlsx_sheets(path):
    z = zipfile.ZipFile(path)
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rid = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    ss = ET.fromstring(z.read("xl/sharedStrings.xml"))
    strings = ["".join(t.text or "" for t in si.iter("{%s}t" % ns["m"])) for si in ss.findall("m:si", ns)]
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    for s in wb.find("m:sheets", ns):
        path_ = "xl/" + rels[s.get(rid)]
        sh = ET.fromstring(z.read(path_))
        rows = []
        for r in sh.find("m:sheetData", ns):
            cells = {}
            for c in r:
                v = c.find("m:v", ns)
                if v is None:
                    continue
                val = v.text
                if c.get("t") == "s":
                    val = strings[int(val)]
                col = re.match(r"[A-Z]+", c.get("r")).group(0)
                cells[col] = val
            rows.append(cells)
        yield s.get("name"), rows


def load_abares():
    """ABARES state workbook -> long table (state, crop_year, status, section, crop, ha), using
    the same unit-row rule as abares_fetch.py. Cotton appears twice (seed and lint) with the same
    area; only 'Cottonseed' is kept so the summer total does not double-count it."""
    rows = []
    for sheet, data in _xlsx_sheets(ABARES_XLSX):
        if sheet == "Index":
            continue
        hdr = next((i for i, r in enumerate(data)
                    if sum(bool(re.match(r"^\d{4}[–-]\d{2}", str(v))) for v in r.values()) >= 5), None)
        if hdr is None:
            continue
        lab_c = next(c for c, v in data[hdr].items() if str(v).strip() == "Crops")
        unit_c = chr(ord(lab_c) + 1)
        years = {}
        for c, v in data[hdr].items():
            m = re.match(r"^(\d{4})[–-]\d{2}\s*([a-z]?)$", str(v).strip())
            if m:
                years[c] = (int(m.group(1)), m.group(2) or "final")
        section, crop = None, None
        for r in data[hdr + 1:]:
            label = str(r.get(lab_c, "")).strip()
            unit = str(r.get(unit_c, "")).strip()
            if label in ("Winter crops", "Summer crops"):
                section, crop = label.split()[0].lower(), None
            elif label == "Area" and "000 ha" in unit and crop:
                for c, (yr, status) in years.items():
                    v = r.get(c)
                    if v is not None and v != "na":
                        rows.append({"state": sheet, "crop_year": yr, "status": status, "section": section,
                                     "crop": crop, "ha": float(v) * 1000})
            elif label and label not in ("Production", "Area"):
                crop = None if label.startswith("Cotton lint") else label
    return pd.DataFrame(rows)


ABARES_DEFS = {
    "canola": ["Canola"],
    "cereal_wbt": ["Wheat", "Barley", "Triticale"],                 # the project's ABARES 'Cereal'
    "wintercereal": ["Wheat", "Barley", "Oats", "Triticale"],
    "legume5": ["Chickpeas", "Faba beans", "Field peas", "Lentils", "Lupins"],
    "winter_all": None, "summer_all": None, "all_crops": None,
}


def abares_groups(B):
    p = B.pivot_table(index=["state", "crop_year"], columns="crop", values="ha", aggfunc="sum").fillna(0.0)
    sec = B.drop_duplicates("crop").set_index("crop").section
    out = pd.DataFrame(index=p.index)
    for g, items in ABARES_DEFS.items():
        if items:
            out[g] = p.reindex(columns=items).fillna(0.0).sum(axis=1)
    out["winter_all"] = p[[c for c in p.columns if sec[c] == "winter"]].sum(axis=1)
    out["summer_all"] = p[[c for c in p.columns if sec[c] == "summer"]].sum(axis=1)
    out["all_crops"] = out.winter_all + out.summer_all
    st = B.groupby(["state", "crop_year"]).status.first()
    out["status"] = st
    return out.reset_index()


# ------------------------------------------------------------------------------------- report
def hist_area_ge(hist, t):
    """area with value >= t percent, along the last axis"""
    return hist[..., t:].sum(axis=-1)


def hist_expected(hist):
    """sum(value/100 x area) along the last axis"""
    return (hist * (np.arange(NB) / 100.0)).sum(axis=-1)


def area_matched_threshold(marg):
    """smallest t such that area(p >= t) <= expected area -- the threshold at which the
    binarised NLUM map has the same total area NLUM itself expects."""
    exp = hist_expected(marg)
    cum = np.cumsum(marg[::-1])[::-1]     # cum[t] = area(p >= t)
    t = int(np.argmax(cum <= exp))
    return t, exp, cum[t]


def confusion(J, tn, tw):
    """J: (..., NB, NB) joint area hist of (nlum p, wc f). Returns dict of 2x2 metrics."""
    a = J[..., tn:, tw:].sum(axis=(-2, -1))
    b = J[..., tn:, :tw].sum(axis=(-2, -1))
    c = J[..., :tn, tw:].sum(axis=(-2, -1))
    d = J[..., :tn, :tw].sum(axis=(-2, -1))
    n = a + b + c + d
    with np.errstate(divide="ignore", invalid="ignore"):
        po = (a + d) / n
        pe = ((a + b) * (a + c) + (c + d) * (b + d)) / (n * n)
        return {"a": a, "b": b, "c": c, "d": d, "n": n,
                "agree": po, "kappa": (po - pe) / (1 - pe), "iou": a / (a + b + c),
                "p_wc_given_nlum": a / (a + b), "p_nlum_given_wc": a / (a + c),
                "ratio_nlum_over_wc": (a + b) / (a + c)}


def joint_stats(J):
    """area-weighted means / correlation / calibration from a (NB, NB) joint hist"""
    p = np.arange(NB) / 100.0
    n = J.sum()
    mp, mf = (J.sum(1) * p).sum() / n, (J.sum(0) * p).sum() / n
    cov = (J * np.outer(p - mp, p - mf)).sum() / n
    sp, sf = np.sqrt((J.sum(1) * (p - mp) ** 2).sum() / n), np.sqrt((J.sum(0) * (p - mf) ** 2).sum() / n)
    return {"mean_p": mp, "mean_f": mf, "r": cov / (sp * sf), "n_area": n}


def fmt_ha(x):
    """histogram bins hold m2; render as kha"""
    return f"{x/1e7:,.0f}"


def fmt_ratio(x):
    return "n/a" if not np.isfinite(x) else f"{x:.2f}"


def pct_diff(x):
    return "n/a" if not np.isfinite(x) else f"{100*abs(x-1):.1f} %"


def cmd_report(args):
    Hh = np.load(f"{args.out_dir}/hists.npz")
    meta = json.load(open(f"{args.out_dir}/overlay_meta.json"))
    lut = pd.read_csv(f"{args.out_dir}/sa2_lookup.csv")
    scal = pd.read_csv(f"{args.out_dir}/sa2_scalars.csv")
    state_of = Hh["state_of"]
    n_sa2 = len(state_of) - 1

    def J(q, w):
        return Hh[f"joint|{q}|{w}"]          # (NST, NB, NB)

    def SQ(d, q):
        return Hh[f"sa2q|{d}|{q}"]           # (n_sa2+1, NB)

    def SW(d, w):
        return Hh[f"sa2w|{d}|{w}"]

    def by_state(sa2_hist):
        out = np.zeros((NST, NB))
        np.add.at(out, state_of, sa2_hist)
        return out

    # -------- NLUM partition check
    sc = Hh["sumcheck"]
    cum = np.cumsum(sc) / sc.sum()
    pct_sum = {k: int(np.argmax(cum >= k / 100)) for k in (5, 25, 50, 75, 95)}

    # -------- national joint (zone & NLUM-valid & WC-valid), summed over states
    Jn = {f"{q}|{w}": J(q, w).sum(0) for q, w in JOINT}
    zone_valid_area = Jn["crop3_sum|tc"].sum()
    nod_tc = Hh["nodata_wc|tc"].sum(0)
    nod_wc = Hh["nodata_wc|wc"].sum(0)
    zone_nodata_area = nod_tc.sum()

    # area-matched thresholds (national, in zone, NLUM-valid)
    tstar = {}
    for q in ["crop3_sum", "crop3_max", "cropall_sum", "grain_cotton_rice", "cereal_w", "cereal_ws",
              "oilseed_w", "legume_w"]:
        marg = by_state(SQ("zone", q)).sum(0)
        tstar[q] = area_matched_threshold(marg)

    # -------- ABS / ABARES
    absd = load_abs_raw()
    abs_state = abs_groups(absd, "state")
    abs_sa2 = abs_groups(absd, "SA2")
    abs_state["state_code"] = abs_state.region.astype(int)
    B = load_abares()
    ab = abares_groups(B)
    name_to_code = {v: k for k, v in STATES.items()}
    ab["state_code"] = ab.state.map(name_to_code).fillna(0).astype(int)   # Australia -> 0

    # -------- state-level areas from the spatial products (ha)
    rows = []
    for s in range(1, 7):
        r = {"state": STATES[s], "state_code": s}
        # bins are m2 -> kha is /1e7
        for w in ("tc", "wc"):
            r[f"wc_{w}_zone"] = hist_expected(by_state(SW("zone", w))[s]) / 1e7
            r[f"wc_{w}_proc"] = hist_expected(by_state(SW("proc", w))[s]) / 1e7
        for q in QUANT:
            for d in ("zone", "all"):
                hz = by_state(SQ(d, q))[s]
                r[f"nlum_{q}_exp_{d}"] = hist_expected(hz) / 1e7
                for t in (25, 50, 75):
                    r[f"nlum_{q}_ge{t}_{d}"] = hist_area_ge(hz, t) / 1e7
                r[f"nlum_{q}_gestar_{d}"] = hist_area_ge(hz, tstar[q][0]) / 1e7 if q in tstar else np.nan
        rows.append(r)
    ST = pd.DataFrame(rows).set_index("state_code")
    nat = ST.sum(numeric_only=True)

    def abs_nat(g, yr):
        v = abs_state[abs_state.crop_year == yr].set_index("state_code")[g]
        return v.reindex(range(1, 7)).fillna(0.0), v.sum()

    def abares_nat(g, yr):
        v = ab[(ab.crop_year == yr) & (ab.state_code >= 1)].set_index("state_code")[g]
        aus = ab[(ab.crop_year == yr) & (ab.state == "Australia")][g]
        return v.reindex(range(1, 7)).fillna(0.0), (float(aus.iloc[0]) if len(aus) else v.sum())

    def state_median_absdiff(x, y, min_ha=20000):
        """median |x/y - 1| over states where the reference y >= min_ha (a 3,600 ha Tasmanian
        canola figure would otherwise dominate a national statement)"""
        x, y = np.asarray(x, float), np.asarray(y, float)
        m = y >= min_ha
        if m.sum() == 0:
            return np.nan, 0
        return float(np.median(np.abs(x[m] / y[m] - 1))), int(m.sum())

    L = []
    L.append("# The three references against each other: WorldCereal 2021 vs NLUM v7 2020-21 vs ABS / ABARES")
    L.append("")
    L.append("Generated by `src/paddocks/reference_intercompare.py`. Aggregate only — public products, no "
             "GRDC/NVT records, nothing from our own map.")
    L.append("")
    L.append("**Why this exists.** Every validation of the national map so far scored it against ONE reference "
             "at a time (ABS by SA2, WorldCereal and NLUM by point sample). The project already treats the "
             "ABS-vs-ABARES gap (median 6.8 % on national sown area, `ABS_COMPARISON_100km.md`) as the "
             "precision floor for any map-vs-reference claim. This report extends that to the full pairwise "
             "matrix: if two references disagree with EACH OTHER by X, a map disagreeing with either by less "
             "than X is at the noise floor of the references, not of the map.")
    L.append("")

    # ---------------------------------------------------------------- methods
    L += ["## Methods — every threshold and year choice", "",
          "### Products, years, classes", "",
          "| product | what it is | year used | classes usable here |", "|---|---|---|---|",
          "| **WorldCereal** (WC) | ESA global 10 m classification, `temporarycrops` (annual cropland incl. "
          "fallow/rotation, FAO definition) and `wintercereals` (wheat/barley-type winter cereals); no canola "
          "or legume class | **2021** season | presence, cereal |",
          "| **NLUM v7** | ABARES 250 m per-commodity probability surfaces derived from the ABS 2020-21 "
          "agricultural census; layers are a per-pixel partition over commodities on agricultural land "
          "(see partition check below) | **2020-21** — the ABS financial year, i.e. the winter crop sown in "
          "calendar **2020** under this project's `crop_year` convention (`abs_fetch.py`). Per the task "
          "brief it is compared against **2021** statistics, and 2020 is shown alongside | presence, cereal, "
          "canola (W_OILSEEDS), legume (W_LEGUMES) |",
          "| **ABS** `AG_BROADACRE` | census/survey sown area by SA2 and state | **2022** is the earliest year "
          "in the current dataflow (series starts 2022-23) — a 1-year gap to WC and 2 to NLUM | canola, "
          "cereal, legume, oats, 14-commodity total |",
          "| **ABARES** Australian Crop Report | state estimates, long series | **2021** (and 2020), both "
          "`final` | canola, cereal, oats, triticale, legume, winter/summer totals |",
          "",
          "### Class alignment", "",
          "| class | WorldCereal | NLUM | ABS | ABARES |", "|---|---|---|---|---|",
          "| presence | `temporarycrops` fraction | sum of W_CER+S_CER_EX_RICE+W/S_OILSEEDS+W/S_LEGUMES "
          "+COTTON+RICE (`grain_cotton_rice`, matches ABARES scope); `+HAY+VEGETABLES` (`cropall_sum`, "
          "closer to WC scope) | sum of all 14 broadacre items (`all14`) or the 13 excluding sugarcane | "
          "winter + summer crops (12 crops) |",
          "| cereal | `wintercereals` fraction | W_CER (winter cereals, includes oats) | wheat+barley+oats "
          "(`wintercereal`); wheat+barley is the project's narrower `Cereal` | wheat+barley+oats+triticale; "
          "wheat+barley+triticale is the project's `Cereal` |",
          "| canola | — | W_OILSEEDS | canola | canola |",
          "| legume | — | W_LEGUMES | lupins+chickpeas+faba+lentils+field peas (`legume5`); the project's "
          "`Legume` omits field peas | chickpeas+faba+field peas+lentils+lupins |",
          "",
          "### Spatial overlay (WC vs NLUM)", "",
          f"- WorldCereal's 10 m classification was aggregated to the **fraction of each 250 m NLUM cell** "
          f"(GDAL warp, average resampling — exact area weighting across the non-integer 24.46:1 pixel ratio "
          f"and the EPSG:4326/4283 difference). {meta['blocks']} blocks of 256x256 NLUM cells, "
          f"{meta['workers']} workers, {meta['minutes']:.0f} min in one PBS job (4 CPU, 16 GB).",
          f"- **Cropping-zone restriction**: the project's national tile mask (`national2024/aois.csv`, "
          f"{meta['zone_cells']:,} NLUM cells = {scal.area_zone.sum()/1e10:.1f} Mha; the 3 km tiles where any "
          f"NLUM cereal/oilseed/legume pixel exceeds 25 %). Comparing over desert where both say 'no crop' "
          f"would inflate agreement; **conditional agreement rates and IoU are reported because they are "
          f"insensitive to the both-negative count anyway**.",
          f"- Cells inside the zone but NLUM-nodata (non-agricultural land in NLUM's base map): "
          f"{zone_nodata_area/1e10:.2f} Mha of {(zone_valid_area+zone_nodata_area)/1e10:.2f} Mha "
          f"({100*zone_nodata_area/(zone_valid_area+zone_nodata_area):.1f} %). They are excluded from the "
          f"agreement tables (NLUM makes no statement there) and reported separately below.",
          "- WorldCereal is binarised at **fraction >= 50 %** of the cell (majority), with 25 % / 75 % shown.",
          "- NLUM is binarised at **25 / 50 / 75 %** and at the **area-matched threshold t\\*** — the "
          "probability at which the thresholded area equals NLUM's own expected area sum(p x cell area). "
          "t\\* is the only threshold that makes a hard NLUM map self-consistent with NLUM's soft totals, so "
          "it is used for the headline; the fixed thresholds show the sensitivity.",
          "- Cell areas: exact GRS80 ellipsoid area per latitude row (geographic grid).",
          "",
          "### NLUM partition check", "",
          f"Area-weighted percentiles of the sum over the 10 NLUM layers read here (6 crop + hay, cotton, rice, "
          f"vegetables) on zone cells, in percent: p5 = {pct_sum[5]}, p25 = {pct_sum[25]}, median = "
          f"{pct_sum[50]}, p75 = {pct_sum[75]}, p95 = {pct_sum[95]}. A separate check over all 25 layers on "
          f"three 50 km windows (Riverina, WA wheatbelt, Darling Downs) gave a median of 10,035 basis points "
          f"(range 10,004–11,024): the layers partition each agricultural pixel, so **P(crop) is the sum over "
          f"crop layers** and the max (used in `NLUM_COMPARISON.md`'s argmax check) under-states it — "
          f"Riverina median crop-sum 63 % vs crop-max 40 %.",
          ""]

    # ---------------------------------------------------------------- WC vs NLUM spatial
    L += ["## 1. WorldCereal vs NLUM, spatially (cropping zone, NLUM-valid cells, "
          f"{zone_valid_area/1e10:.1f} Mha)", ""]
    for title, q, w, in [("Presence: WC `temporarycrops` vs NLUM crop-sum (grain+cotton+rice)", "grain_cotton_rice", "tc"),
                         ("Presence: WC `temporarycrops` vs NLUM crop-sum incl. hay+vegetables", "cropall_sum", "tc"),
                         ("Presence: WC `temporarycrops` vs NLUM crop-MAX over the six cereal/oilseed/legume layers", "crop3_max", "tc"),
                         ("Cereal: WC `wintercereals` vs NLUM W_CER", "cereal_w", "wc"),
                         ("Cereal: WC `wintercereals` vs NLUM W_CER + S_CER_EX_RICE", "cereal_ws", "wc")]:
        Jq = Jn[f"{q}|{w}"]
        st = joint_stats(Jq)
        ts, exp_a, thr_a = tstar[q]
        L += [f"### {title}", "",
              f"- soft totals in zone: WC area **{fmt_ha(st['mean_f']*st['n_area'])} kha** vs NLUM expected "
              f"**{fmt_ha(st['mean_p']*st['n_area'])} kha** → ratio NLUM/WC = "
              f"**{st['mean_p']/st['mean_f']:.2f}**; area-weighted r(p, f) = **{st['r']:.2f}**",
              f"- area-matched NLUM threshold t\\* = **{ts} %** (thresholded {fmt_ha(thr_a)} kha vs expected "
              f"{fmt_ha(exp_a)} kha)", "",
              "| NLUM >= | WC >= | agreement | kappa | IoU | P(WC crop \\| NLUM crop) | P(NLUM crop \\| WC crop) | "
              "NLUM+ / WC+ area |", "|---|---|---|---|---|---|---|---|"]
        for tn in sorted({25, 50, 75, ts}):
            for tw in (50,) if tn != ts else (25, 50, 75):
                c = confusion(Jq, tn, tw)
                tag = f"{tn} (t\\*)" if tn == ts else f"{tn}"
                L.append(f"| {tag} | {tw} | {100*c['agree']:.1f} % | {c['kappa']:.2f} | {c['iou']:.2f} | "
                         f"{100*c['p_wc_given_nlum']:.1f} % | {100*c['p_nlum_given_wc']:.1f} % | "
                         f"{c['ratio_nlum_over_wc']:.2f} |")
        # calibration: mean WC fraction by NLUM probability decile
        p = np.arange(NB) / 100.0
        cal = []
        for lo in range(0, 100, 10):
            hi = min(lo + 10, 101) if lo < 90 else 101
            blk = Jq[lo:hi]
            a = blk.sum()
            cal.append(f"{100*(blk.sum(0)*p).sum()/a:.0f}" if a > 0 else "–")
        L += ["", "Mean WC fraction (%) by NLUM probability band 0-9, 10-19, …, 90-100: " + " / ".join(cal), ""]

    # by-state headline (grain_cotton_rice at t*, cereal_w at t*)
    L += ["### By state (headline settings: NLUM >= t\\*, WC >= 50 %)", "",
          "| state | zone valid Mha | presence IoU | P(WC\\|NLUM) | P(NLUM\\|WC) | cereal IoU | P(WC\\|NLUM) | P(NLUM\\|WC) |",
          "|---|---|---|---|---|---|---|---|"]
    for s in range(1, 7):
        cp = confusion(J("grain_cotton_rice", "tc")[s], tstar["grain_cotton_rice"][0], 50)
        cc = confusion(J("cereal_w", "wc")[s], tstar["cereal_w"][0], 50)
        if cp["n"] < 1e8:
            continue
        L.append(f"| {STATES[s]} | {cp['n']/1e10:.2f} | {cp['iou']:.2f} | {100*cp['p_wc_given_nlum']:.0f} % | "
                 f"{100*cp['p_nlum_given_wc']:.0f} % | {cc['iou']:.2f} | {100*cc['p_wc_given_nlum']:.0f} % | "
                 f"{100*cc['p_nlum_given_wc']:.0f} % |")
    L += ["", "### Where NLUM has no agricultural land but the zone does", "",
          f"On the {zone_nodata_area/1e10:.2f} Mha of zone cells that are NLUM-nodata, WorldCereal calls "
          f"**{100*hist_expected(nod_tc)/nod_tc.sum():.1f} %** of the area temporary crops and "
          f"**{100*hist_expected(nod_wc)/nod_wc.sum():.1f} %** winter cereals "
          f"(≈ {fmt_ha(hist_expected(nod_tc))} kha and {fmt_ha(hist_expected(nod_wc))} kha). This is crop that "
          f"NLUM's base land-use map cannot contain at all, and it is part of the disagreement between them.",
          ""]

    # ---------------------------------------------------------------- area vs statistics
    L += ["## 2. Implied crop area vs ABS and ABARES, by state", "",
          "Spatial-product areas are **inside the cropping zone** unless marked `all` (NLUM is read over its "
          "whole extent too; WC only exists where the overlay ran). NLUM areas are the **expected** area "
          "sum(p x cell area); thresholded variants follow. ABS = 2022 (earliest available), ABARES = 2021 "
          "(`final`). `kha` throughout.", ""]

    # presence
    ab21_all, ab21_all_nat = abares_nat("all_crops", 2021)
    ab20_all, _ = abares_nat("all_crops", 2020)
    abs22_13, abs22_13_nat = abs_nat("grain_cotton_rice", 2022)
    abs22_14, abs22_14_nat = abs_nat("all14", 2022)
    L += ["### Presence / total crop area", "",
          "| state | WC tc 2021 (zone) | NLUM grain+cotton+rice exp (zone) | NLUM same (all) | NLUM +hay+veg (all) | "
          "ABARES all crops 2021 | ABARES 2020 | ABS 13-item 2022 |", "|---|---|---|---|---|---|---|---|"]
    for s in range(1, 7):
        r = ST.loc[s]
        L.append(f"| {STATES[s]} | {r.wc_tc_zone:,.0f} | {r.nlum_grain_cotton_rice_exp_zone:,.0f} | "
                 f"{r.nlum_grain_cotton_rice_exp_all:,.0f} | {r.nlum_cropall_sum_exp_all:,.0f} | "
                 f"{ab21_all[s]/1e3:,.0f} | {ab20_all[s]/1e3:,.0f} | {abs22_13[s]/1e3:,.0f} |")
    L.append(f"| **Australia** | {nat.wc_tc_zone:,.0f} | {nat.nlum_grain_cotton_rice_exp_zone:,.0f} | "
             f"{nat.nlum_grain_cotton_rice_exp_all:,.0f} | {nat.nlum_cropall_sum_exp_all:,.0f} | "
             f"{ab21_all_nat/1e3:,.0f} | {ab20_all.sum()/1e3:,.0f} | {abs22_13_nat/1e3:,.0f} |")
    L.append("")
    L.append("WorldCereal `temporarycrops` follows FAO's temporary-cropland definition (annual crops **plus** "
             "temporary fallow, hay and sown pasture in rotation), so it is expected to exceed any *sown* "
             "grain/cotton/rice total; the excess is a definitional gap, not an error of either product.")
    L.append("")

    # cereal
    ab21_wc, ab21_wc_nat = abares_nat("wintercereal", 2021)
    ab20_wc, _ = abares_nat("wintercereal", 2020)
    ab21_c, ab21_c_nat = abares_nat("cereal_wbt", 2021)
    abs22_wc, abs22_wc_nat = abs_nat("wintercereal", 2022)
    abs22_c, abs22_c_nat = abs_nat("cereal_wb", 2022)
    L += ["### Winter cereals", "",
          "| state | WC wintercereals 2021 (zone) | NLUM W_CER exp (zone) | NLUM W_CER exp (all) | "
          f"NLUM W_CER >= t\\*={tstar['cereal_w'][0]} (all) | ABARES wheat+barley+oats+triticale 2021 | "
          "ABARES 2020 | ABS wheat+barley+oats 2022 | ABS wheat+barley 2022 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for s in range(1, 7):
        r = ST.loc[s]
        L.append(f"| {STATES[s]} | {r.wc_wc_zone:,.0f} | {r.nlum_cereal_w_exp_zone:,.0f} | "
                 f"{r.nlum_cereal_w_exp_all:,.0f} | {r.nlum_cereal_w_gestar_all:,.0f} | {ab21_wc[s]/1e3:,.0f} | "
                 f"{ab20_wc[s]/1e3:,.0f} | {abs22_wc[s]/1e3:,.0f} | {abs22_c[s]/1e3:,.0f} |")
    L.append(f"| **Australia** | {nat.wc_wc_zone:,.0f} | {nat.nlum_cereal_w_exp_zone:,.0f} | "
             f"{nat.nlum_cereal_w_exp_all:,.0f} | {nat.nlum_cereal_w_gestar_all:,.0f} | {ab21_wc_nat/1e3:,.0f} | "
             f"{ab20_wc.sum()/1e3:,.0f} | {abs22_wc_nat/1e3:,.0f} | {abs22_c_nat/1e3:,.0f} |")
    L.append("")

    # canola & legume (NLUM only)
    ab21_can, ab21_can_nat = abares_nat("canola", 2021)
    ab20_can, _ = abares_nat("canola", 2020)
    abs22_can, abs22_can_nat = abs_nat("canola", 2022)
    ab21_leg, ab21_leg_nat = abares_nat("legume5", 2021)
    ab20_leg, _ = abares_nat("legume5", 2020)
    abs22_leg, abs22_leg_nat = abs_nat("legume5", 2022)
    abs22_leg4, abs22_leg4_nat = abs_nat("legume4", 2022)
    L += ["### Canola (NLUM W_OILSEEDS) and winter legumes (NLUM W_LEGUMES) — WorldCereal has no such class", "",
          "| state | NLUM oilseed exp (all) | ABARES canola 2021 | ABARES 2020 | ABS canola 2022 | "
          "NLUM legume exp (all) | ABARES pulses 2021 | ABARES 2020 | ABS 5 pulses 2022 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for s in range(1, 7):
        r = ST.loc[s]
        L.append(f"| {STATES[s]} | {r.nlum_oilseed_w_exp_all:,.0f} | {ab21_can[s]/1e3:,.0f} | {ab20_can[s]/1e3:,.0f} | "
                 f"{abs22_can[s]/1e3:,.0f} | {r.nlum_legume_w_exp_all:,.0f} | {ab21_leg[s]/1e3:,.0f} | "
                 f"{ab20_leg[s]/1e3:,.0f} | {abs22_leg[s]/1e3:,.0f} |")
    L.append(f"| **Australia** | {nat.nlum_oilseed_w_exp_all:,.0f} | {ab21_can_nat/1e3:,.0f} | {ab20_can.sum()/1e3:,.0f} | "
             f"{abs22_can_nat/1e3:,.0f} | {nat.nlum_legume_w_exp_all:,.0f} | {ab21_leg_nat/1e3:,.0f} | "
             f"{ab20_leg.sum()/1e3:,.0f} | {abs22_leg_nat/1e3:,.0f} |")
    L.append("")

    # NLUM expected vs thresholded sensitivity (national, all)
    L += ["### NLUM: expected area vs thresholded area (national, whole extent)", "",
          "Thresholding a probability surface is not area-preserving; this is why the expected area is the "
          "primary NLUM figure and why t\\* exists.", "",
          "| NLUM quantity | expected | >= 25 % | >= 50 % | >= 75 % | t\\* | >= t\\* |", "|---|---|---|---|---|---|---|"]
    for q in ["grain_cotton_rice", "cropall_sum", "crop3_max", "cereal_w", "oilseed_w", "legume_w"]:
        L.append(f"| {q} | {nat[f'nlum_{q}_exp_all']:,.0f} | {nat[f'nlum_{q}_ge25_all']:,.0f} | "
                 f"{nat[f'nlum_{q}_ge50_all']:,.0f} | {nat[f'nlum_{q}_ge75_all']:,.0f} | {tstar[q][0]} % | "
                 f"{nat[f'nlum_{q}_gestar_all']:,.0f} |")
    L.append("")

    # ---------------------------------------------------------------- SA2 level (ABS 2022)
    sa2_rows = []
    abs22 = abs_sa2[abs_sa2.crop_year == 2022].copy()
    abs22["region"] = abs22.region.astype(str)
    lut2 = lut.set_index("idx")
    scal2 = scal.set_index("idx")
    # per-SA2 areas in ha (bins are m2)
    exp_all = {q: hist_expected(SQ("all", q)) / 1e4 for q in ["cereal_w", "oilseed_w", "legume_w", "grain_cotton_rice"]}
    wc_zone = {w: hist_expected(SW("zone", w)) / 1e4 for w in ("tc", "wc")}
    for _, a in abs22.iterrows():
        hit = lut2[lut2.SA2_CODE21.astype(str) == a.region]
        if not len(hit):
            continue
        i = hit.index[0]
        cover = scal2.area_zone[i] / scal2.area_all[i] if scal2.area_all[i] > 0 else 0
        sa2_rows.append({"sa2": hit.SA2_NAME21.iloc[0], "cover": cover,
                         "abs_crop": a.canola + a.cereal_wb + a.legume4,
                         "abs_canola": a.canola, "abs_wintercereal": a.wintercereal, "abs_legume5": a.legume5,
                         "abs_13": a.grain_cotton_rice,
                         "nlum_canola": exp_all["oilseed_w"][i], "nlum_cereal": exp_all["cereal_w"][i],
                         "nlum_legume": exp_all["legume_w"][i], "nlum_13": exp_all["grain_cotton_rice"][i],
                         "wc_tc": wc_zone["tc"][i], "wc_wc": wc_zone["wc"][i]})
    SA = pd.DataFrame(sa2_rows)
    SAw = SA[(SA.cover >= 0.5) & (SA.abs_crop >= 5000)]

    def sa2_med(num, den, min_ha=1000):
        d = SAw[SAw[den] >= min_ha]
        r = d[num] / d[den]
        return float(np.median(np.abs(r - 1))), float(np.median(r)), len(d)

    L += ["## 3. SA2 level vs ABS 2022 (NLUM and WC vs the finest reference)", "",
          f"{len(SA)} ABS-reporting SA2s matched; **{len(SAw)}** have >= 50 % of their area inside the "
          f"cropping zone and >= 5,000 ha ABS crop (the `abs_compare.py` filters). Ratio = spatial product / ABS; "
          f"NLUM over the whole SA2, WC inside the zone. Median |ratio − 1| is the metric the project already "
          f"uses at SA2 level.", "",
          "| comparison (2022 ABS vs) | n SA2 | median ratio | median \\|ratio − 1\\| |", "|---|---|---|---|"]
    for lab, num, den in [("NLUM W_OILSEEDS vs ABS canola", "nlum_canola", "abs_canola"),
                          ("NLUM W_CER vs ABS wheat+barley+oats", "nlum_cereal", "abs_wintercereal"),
                          ("NLUM W_LEGUMES vs ABS 5 pulses", "nlum_legume", "abs_legume5"),
                          ("NLUM grain+cotton+rice vs ABS 13-item total", "nlum_13", "abs_13"),
                          ("WC wintercereals vs ABS wheat+barley+oats", "wc_wc", "abs_wintercereal"),
                          ("WC temporarycrops vs ABS 13-item total", "wc_tc", "abs_13")]:
        mad, mr, n = sa2_med(num, den)
        L.append(f"| {lab} | {n} | {mr:.2f} | **{100*mad:.1f} %** |")
    L.append("")

    # ---------------------------------------------------------------- ABS vs ABARES at state level
    L += ["## 4. ABS vs ABARES at state level (2022-2024)", "",
          "The national 6.8 % figure is cited from `ABS_COMPARISON_100km.md` (median over 9 year x group "
          "ratios, project class definitions). Recomputed here at state level, both with the project's "
          "definitions and with harmonised ones (ABS legumes without field peas vs ABARES with them is a "
          "definitional gap inside the 6.8 %).", "",
          "| group | definition | n state-years (ref >= 20 kha) | median \\|ABS/ABARES − 1\\| |", "|---|---|---|---|"]
    abs_ab = []
    for lab, ga, gb in [("canola", "canola", "canola"), ("cereal (project: wheat+barley vs wheat+barley+triticale)", "cereal_wb", "cereal_wbt"),
                        ("winter cereal (harmonised, +oats)", "wintercereal", "wintercereal"),
                        ("legume (project: 4 pulses vs 5)", "legume4", "legume5"),
                        ("legume (harmonised 5 pulses)", "legume5", "legume5"),
                        ("total (ABS 13-item vs ABARES 12 crops)", "grain_cotton_rice", "all_crops")]:
        xs, ys = [], []
        for yr in (2022, 2023, 2024):
            a, _ = abs_nat(ga, yr)
            b, _ = abares_nat(gb, yr)
            xs += list(a.values)
            ys += list(b.values)
        mad, n = state_median_absdiff(xs, ys)
        abs_ab.append((lab, mad))
        L.append(f"| {lab} | {ga} vs {gb} | {n} | **{100*mad:.1f} %** |")
    L.append("")
    st_flags = ab[(ab.crop_year.isin([2022, 2023, 2024])) & (ab.state == "Australia")][["crop_year", "status"]]
    L.append("ABARES quality flags for those years: " + ", ".join(f"{int(r.crop_year)} `{r.status}`" for _, r in st_flags.iterrows()) +
             " (`s` = ABARES estimate; 2020 and 2021 are `final`). ABS carries a field-peas item only from "
             "2024, so the two legume rows coincide for 2022-23; the legume gap is a genuine ABS/ABARES "
             "difference, not a definitional one.")
    L.append("")

    # ---------------------------------------------------------------- the matrix
    def nat_ratio(x, y):
        return x / y if y else np.nan

    # WC–NLUM national (zone, soft)
    wn_pres = joint_stats(Jn["grain_cotton_rice|tc"])
    wn_cer = joint_stats(Jn["cereal_w|wc"])
    c_pres = confusion(Jn["grain_cotton_rice|tc"], tstar["grain_cotton_rice"][0], 50)
    c_cer = confusion(Jn["cereal_w|wc"], tstar["cereal_w"][0], 50)

    cells = {}
    # presence
    cells[("WC", "NLUM", "presence")] = (f"area ratio {nat_ratio(nat.wc_tc_zone, nat.nlum_grain_cotton_rice_exp_zone):.2f} "
                                          f"(WC/NLUM, zone); IoU {c_pres['iou']:.2f}; "
                                          f"P(WC\\|NLUM) {100*c_pres['p_wc_given_nlum']:.0f} %, P(NLUM\\|WC) {100*c_pres['p_nlum_given_wc']:.0f} %")
    r = nat_ratio(nat.wc_tc_zone * 1e3, ab21_all_nat)
    m, n = state_median_absdiff(ST.wc_tc_zone * 1e3, ab21_all)
    cells[("WC", "ABARES", "presence")] = f"national ratio {r:.2f} (WC tc / ABARES all crops, 2021); state median \\|diff\\| {100*m:.0f} % (n={n})"
    r = nat_ratio(nat.wc_tc_zone * 1e3, abs22_13_nat)
    m, n = state_median_absdiff(ST.wc_tc_zone * 1e3, abs22_13)
    cells[("WC", "ABS", "presence")] = f"national ratio {r:.2f} (WC tc 2021 / ABS 13-item 2022); state median \\|diff\\| {100*m:.0f} % (n={n})"
    r = nat_ratio(nat.nlum_grain_cotton_rice_exp_all * 1e3, ab21_all_nat)
    r20 = nat_ratio(nat.nlum_grain_cotton_rice_exp_all * 1e3, ab20_all.sum())
    m, n = state_median_absdiff(ST.nlum_grain_cotton_rice_exp_all * 1e3, ab21_all)
    m20, _ = state_median_absdiff(ST.nlum_grain_cotton_rice_exp_all * 1e3, ab20_all)
    cells[("NLUM", "ABARES", "presence")] = (f"national ratio {r:.2f} vs 2021 ({r20:.2f} vs 2020); state median \\|diff\\| "
                                             f"{100*m:.0f} % (2021) / {100*m20:.0f} % (2020), n={n}")
    r = nat_ratio(nat.nlum_grain_cotton_rice_exp_all * 1e3, abs22_13_nat)
    m, n = state_median_absdiff(ST.nlum_grain_cotton_rice_exp_all * 1e3, abs22_13)
    mad13, _, n13 = sa2_med("nlum_13", "abs_13")
    cells[("NLUM", "ABS", "presence")] = (f"national ratio {r:.2f} (NLUM 2020-21 / ABS 2022); state median \\|diff\\| "
                                          f"{100*m:.0f} % (n={n}); SA2 median \\|diff\\| {100*mad13:.0f} % (n={n13})")
    cells[("ABS", "ABARES", "presence")] = f"state median \\|diff\\| {100*abs_ab[5][1]:.1f} % (13 vs 12 crops, 2022-24)"
    # cereal
    cells[("WC", "NLUM", "cereal")] = (f"area ratio {nat_ratio(nat.wc_wc_zone, nat.nlum_cereal_w_exp_zone):.2f} "
                                        f"(WC/NLUM, zone); IoU {c_cer['iou']:.2f}; "
                                        f"P(WC\\|NLUM) {100*c_cer['p_wc_given_nlum']:.0f} %, P(NLUM\\|WC) {100*c_cer['p_nlum_given_wc']:.0f} %")
    r = nat_ratio(nat.wc_wc_zone * 1e3, ab21_wc_nat)
    m, n = state_median_absdiff(ST.wc_wc_zone * 1e3, ab21_wc)
    cells[("WC", "ABARES", "cereal")] = f"national ratio {r:.2f} (WC wintercereals / ABARES w+b+o+t, 2021); state median \\|diff\\| {100*m:.0f} % (n={n})"
    r = nat_ratio(nat.wc_wc_zone * 1e3, abs22_wc_nat)
    m, n = state_median_absdiff(ST.wc_wc_zone * 1e3, abs22_wc)
    madw, _, nw = sa2_med("wc_wc", "abs_wintercereal")
    cells[("WC", "ABS", "cereal")] = (f"national ratio {r:.2f} (2021 vs ABS w+b+o 2022); state median \\|diff\\| {100*m:.0f} % (n={n}); "
                                      f"SA2 median \\|diff\\| {100*madw:.0f} % (n={nw})")
    r = nat_ratio(nat.nlum_cereal_w_exp_all * 1e3, ab21_wc_nat)
    r20 = nat_ratio(nat.nlum_cereal_w_exp_all * 1e3, ab20_wc.sum())
    m, n = state_median_absdiff(ST.nlum_cereal_w_exp_all * 1e3, ab21_wc)
    m20, _ = state_median_absdiff(ST.nlum_cereal_w_exp_all * 1e3, ab20_wc)
    cells[("NLUM", "ABARES", "cereal")] = (f"national ratio {r:.2f} vs 2021 ({r20:.2f} vs 2020); state median \\|diff\\| "
                                           f"{100*m:.0f} % (2021) / {100*m20:.0f} % (2020), n={n}")
    r = nat_ratio(nat.nlum_cereal_w_exp_all * 1e3, abs22_wc_nat)
    m, n = state_median_absdiff(ST.nlum_cereal_w_exp_all * 1e3, abs22_wc)
    madc, _, nc = sa2_med("nlum_cereal", "abs_wintercereal")
    cells[("NLUM", "ABS", "cereal")] = (f"national ratio {r:.2f} (vs ABS w+b+o 2022); state median \\|diff\\| {100*m:.0f} % (n={n}); "
                                        f"SA2 median \\|diff\\| {100*madc:.0f} % (n={nc})")
    cells[("ABS", "ABARES", "cereal")] = (f"state median \\|diff\\| {100*abs_ab[2][1]:.1f} % (harmonised w+b+o[+t]); "
                                          f"{100*abs_ab[1][1]:.1f} % with the project's definitions")
    # canola
    cells[("WC", "NLUM", "canola")] = "not comparable — WorldCereal has no canola class"
    cells[("WC", "ABARES", "canola")] = "not comparable — WorldCereal has no canola class"
    cells[("WC", "ABS", "canola")] = "not comparable — WorldCereal has no canola class"
    r = nat_ratio(nat.nlum_oilseed_w_exp_all * 1e3, ab21_can_nat)
    r20 = nat_ratio(nat.nlum_oilseed_w_exp_all * 1e3, ab20_can.sum())
    m, n = state_median_absdiff(ST.nlum_oilseed_w_exp_all * 1e3, ab21_can)
    m20, _ = state_median_absdiff(ST.nlum_oilseed_w_exp_all * 1e3, ab20_can)
    cells[("NLUM", "ABARES", "canola")] = (f"national ratio {r:.2f} vs 2021 ({r20:.2f} vs 2020); state median \\|diff\\| "
                                           f"{100*m:.0f} % (2021) / {100*m20:.0f} % (2020), n={n}")
    r = nat_ratio(nat.nlum_oilseed_w_exp_all * 1e3, abs22_can_nat)
    m, n = state_median_absdiff(ST.nlum_oilseed_w_exp_all * 1e3, abs22_can)
    madk, _, nk = sa2_med("nlum_canola", "abs_canola")
    cells[("NLUM", "ABS", "canola")] = (f"national ratio {r:.2f} (vs ABS 2022); state median \\|diff\\| {100*m:.0f} % (n={n}); "
                                        f"SA2 median \\|diff\\| {100*madk:.0f} % (n={nk})")
    cells[("ABS", "ABARES", "canola")] = f"state median \\|diff\\| {100*abs_ab[0][1]:.1f} % (2022-24); national 6.8 % floor cited from ABS_COMPARISON_100km.md"
    # legume
    cells[("WC", "NLUM", "legume")] = "not comparable — WorldCereal has no legume class"
    cells[("WC", "ABARES", "legume")] = "not comparable — WorldCereal has no legume class"
    cells[("WC", "ABS", "legume")] = "not comparable — WorldCereal has no legume class"
    r = nat_ratio(nat.nlum_legume_w_exp_all * 1e3, ab21_leg_nat)
    r20 = nat_ratio(nat.nlum_legume_w_exp_all * 1e3, ab20_leg.sum())
    m, n = state_median_absdiff(ST.nlum_legume_w_exp_all * 1e3, ab21_leg)
    m20, _ = state_median_absdiff(ST.nlum_legume_w_exp_all * 1e3, ab20_leg)
    cells[("NLUM", "ABARES", "legume")] = (f"national ratio {r:.2f} vs 2021 ({r20:.2f} vs 2020); state median \\|diff\\| "
                                           f"{100*m:.0f} % (2021) / {100*m20:.0f} % (2020), n={n}")
    r = nat_ratio(nat.nlum_legume_w_exp_all * 1e3, abs22_leg_nat)
    m, n = state_median_absdiff(ST.nlum_legume_w_exp_all * 1e3, abs22_leg)
    madl, _, nl_ = sa2_med("nlum_legume", "abs_legume5")
    cells[("NLUM", "ABS", "legume")] = (f"national ratio {r:.2f} (vs ABS 5 pulses 2022); state median \\|diff\\| {100*m:.0f} % (n={n}); "
                                        f"SA2 median \\|diff\\| {100*madl:.0f} % (n={nl_})")
    cells[("ABS", "ABARES", "legume")] = (f"state median \\|diff\\| {100*abs_ab[4][1]:.1f} % (harmonised 5 pulses); "
                                          f"{100*abs_ab[3][1]:.1f} % with the project's definitions")

    L += ["## 5. The pairwise disagreement matrix", "",
          "Metric named in every cell. *National ratio* = product A total / product B total; *state median "
          "\\|diff\\|* = median over states of |A/B − 1| where B >= 20 kha; *SA2 median \\|diff\\|* likewise over "
          "the well-covered SA2s of section 3; spatial cells (WC–NLUM) additionally give IoU and the two "
          "conditional agreement rates at the headline thresholds. Year of each side stated; ABS is always "
          "2022 (earliest available).", ""]
    for cls in ["presence", "cereal", "canola", "legume"]:
        L += [f"### {cls}", "", "| pair | disagreement |", "|---|---|"]
        for pair in [("WC", "NLUM"), ("WC", "ABARES"), ("WC", "ABS"), ("NLUM", "ABARES"), ("NLUM", "ABS"), ("ABS", "ABARES")]:
            L.append(f"| {pair[0]} – {pair[1]} | {cells[(pair[0], pair[1], cls)]} |")
        L.append("")

    # ---------------------------------------------------------------- headline floors
    def collect(cls):
        """the national-ratio disagreements available for a class, as |ratio-1| in %"""
        out = {}
        if cls == "presence":
            out["WC–NLUM"] = abs(nat_ratio(nat.wc_tc_zone, nat.nlum_grain_cotton_rice_exp_zone) - 1)
            out["WC–ABARES"] = abs(nat_ratio(nat.wc_tc_zone * 1e3, ab21_all_nat) - 1)
            out["WC–ABS"] = abs(nat_ratio(nat.wc_tc_zone * 1e3, abs22_13_nat) - 1)
            out["NLUM–ABARES"] = abs(nat_ratio(nat.nlum_grain_cotton_rice_exp_all * 1e3, ab21_all_nat) - 1)
            out["NLUM–ABS"] = abs(nat_ratio(nat.nlum_grain_cotton_rice_exp_all * 1e3, abs22_13_nat) - 1)
        if cls == "cereal":
            out["WC–NLUM"] = abs(nat_ratio(nat.wc_wc_zone, nat.nlum_cereal_w_exp_zone) - 1)
            out["WC–ABARES"] = abs(nat_ratio(nat.wc_wc_zone * 1e3, ab21_wc_nat) - 1)
            out["WC–ABS"] = abs(nat_ratio(nat.wc_wc_zone * 1e3, abs22_wc_nat) - 1)
            out["NLUM–ABARES"] = abs(nat_ratio(nat.nlum_cereal_w_exp_all * 1e3, ab21_wc_nat) - 1)
            out["NLUM–ABS"] = abs(nat_ratio(nat.nlum_cereal_w_exp_all * 1e3, abs22_wc_nat) - 1)
        if cls == "canola":
            out["NLUM–ABARES"] = abs(nat_ratio(nat.nlum_oilseed_w_exp_all * 1e3, ab21_can_nat) - 1)
            out["NLUM–ABS"] = abs(nat_ratio(nat.nlum_oilseed_w_exp_all * 1e3, abs22_can_nat) - 1)
        if cls == "legume":
            out["NLUM–ABARES"] = abs(nat_ratio(nat.nlum_legume_w_exp_all * 1e3, ab21_leg_nat) - 1)
            out["NLUM–ABS"] = abs(nat_ratio(nat.nlum_legume_w_exp_all * 1e3, abs22_leg_nat) - 1)
        return out

    L += ["## 6. Headline: the reference-noise floor per class", "",
          "National-total |ratio − 1| for every pair that can be formed (the same metric as the existing "
          "ABS–ABARES 6.8 %), plus that 6.8 % itself. The *floor* a map should be held to is the disagreement "
          "between the two references it is being scored against — not the best pair, not the worst.", "",
          "| class | pairwise national disagreements | ABS–ABARES (cited) |", "|---|---|---|"]
    summary = {}
    for cls in ["presence", "cereal", "canola", "legume"]:
        c = collect(cls)
        summary[cls] = c
        L.append(f"| {cls} | " + "; ".join(f"{k} {100*v:.0f} %" for k, v in c.items()) +
                 f" | {'6.8 % (canola/cereal/legume pooled, national)' if cls != 'presence' else 'no total-crop figure in the project tables; ' + f'{100*abs_ab[5][1]:.0f} % state-level here'} |")
    L.append("")
    json.dump({"summary": {k: {kk: float(vv) for kk, vv in v.items()} for k, v in summary.items()},
               "tstar": {k: int(v[0]) for k, v in tstar.items()},
               "abs_abares_state": {k: float(v) for k, v in abs_ab},
               "cells": {"|".join(k): v for k, v in cells.items()}},
              open(f"{args.out_dir}/matrix_summary.json", "w"), indent=1)

    # ---------------------------------------------------------------- caveats + implications
    L += ["## Caveats", "",
          "- **Resolution.** WC at 10 m was aggregated to NLUM's 250 m cells before any comparison; the spatial "
          "agreement is therefore at 250 m and says nothing about paddock-boundary accuracy. NLUM is a "
          "statistical *probability* product, not an observation: cells with p = 60 % are, by construction, "
          "40 % something else, and no threshold recovers that.",
          "- **Years.** WC = 2021 season; NLUM = ABS 2020-21 census (the 2020 winter crop in this project's "
          "convention, compared to 2021 statistics as briefed, with 2020 alongside); ABS SA2/state = 2022 at the "
          "earliest; ABARES = 2021 `final`. Sown area moves 5-15 % between years (ABARES canola 2020→2021: "
          f"{ab20_can.sum()/1e6:.2f}→{ab21_can_nat/1e6:.2f} Mha), so every cross-year cell carries real "
          "year-on-year change inside its number.",
          "- **Class scope.** WC `temporarycrops` includes fallow/hay/rotational pasture; NLUM W_CER includes "
          "oats, which the project's ABS/ABARES `Cereal` excludes (hence the harmonised wheat+barley+oats[+triticale] "
          "columns); NLUM W_OILSEEDS is compared to canola alone; ABS legumes exclude field peas in the project's "
          "definition. Every cell states which definition it used.",
          "- **Cropping-zone restriction.** WC areas exist only inside the project's tile mask. NLUM's expected "
          f"grain+cotton+rice area inside the zone is {nat.nlum_grain_cotton_rice_exp_zone:,.0f} kha of "
          f"{nat.nlum_grain_cotton_rice_exp_all:,.0f} kha nationally "
          f"({100*nat.nlum_grain_cotton_rice_exp_zone/nat.nlum_grain_cotton_rice_exp_all:.0f} %), so the "
          "zone truncates crop area by that much for NLUM and, by proxy, for WC; the truncation is concentrated "
          "in summer-crop country (Qld, northern NSW) that the winter-crop mask never targeted.",
          "- **WC nodata.** The export has no nodata value; uncovered pixels read as 0 (no-crop). Inside the "
          "cropping zone this is a small effect but it biases WC low, not high.",
          "- **ABS suppression.** Only 318 SA2s carry ABS broadacre figures (small cells are suppressed); state "
          "totals come from the state-level rows, which are not affected.",
          "",
          "## What this means for the paper's validation-precision floor", ""]
    pres = summary["presence"]
    cer = summary["cereal"]
    L.append(f"The references disagree with each other by far more than the 6.8 % the paper currently quotes, "
             f"once the comparison leaves the two official statistical series. For **crop presence**, the three "
             f"pairwise national ratios that can be formed between the spatial products and the statistics sit at "
             f"{', '.join(f'{100*v:.0f} %' for v in pres.values())} — the spatial products and the statistics are "
             f"measuring different things (temporary cropland vs sown grain), and no map should be scored against "
             f"a presence total without saying which. For **cereal**, the WC–NLUM–ABS/ABARES disagreements are "
             f"{', '.join(f'{100*v:.0f} %' for v in cer.values())}; and at 250 m the two spatial references agree "
             f"on only IoU = {c_cer['iou']:.2f} of the cereal area (P(WC|NLUM) = {100*c_cer['p_wc_given_nlum']:.0f} %, "
             f"P(NLUM|WC) = {100*c_cer['p_nlum_given_wc']:.0f} %), so the 49.6 % point agreement between our map "
             f"and WC (`WORLDCEREAL_COMPARISON.md`) should be read against that, not against 100 %. For **canola** "
             f"and **legume** only NLUM can be set against the statistics: "
             f"{', '.join(f'{k} {100*v:.0f} %' for k, v in summary['canola'].items())} for canola and "
             f"{', '.join(f'{k} {100*v:.0f} %' for k, v in summary['legume'].items())} for legumes. The paper should "
             f"therefore state the floor **per reference pair and per class** — 6.8 % (national) / "
             f"{100*abs_ab[0][1]:.0f}–{100*abs_ab[2][1]:.0f} % (state) when scoring against ABS or ABARES, and the "
             f"far larger WC/NLUM figures above when scoring against a spatial product — rather than a single 6.8 %.")
    L.append("")

    os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
    open(args.report, "w").write("\n".join(L) + "\n")
    ST.to_csv(f"{args.out_dir}/state_areas.csv")
    SA.to_csv(f"{args.out_dir}/sa2_areas.csv", index=False)
    log(f"wrote {args.report}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("overlay")
    o.add_argument("--out-dir", default=DEFAULT_OUT)
    o.add_argument("--workers", type=int, default=4)
    o.add_argument("--max-blocks", type=int, default=0, help="debug: only this many blocks")
    o.add_argument("--skip-sa2", action="store_true", help="debug: skip the SA2 rasterisation")
    a = sub.add_parser("analyse")
    a.add_argument("--out-dir", default=DEFAULT_OUT)
    a.add_argument("--chunk-rows", type=int, default=256)
    a.add_argument("--rows", type=int, nargs=2, metavar=("R0", "R1"), help="debug: only this row range")
    r = sub.add_parser("report")
    r.add_argument("--out-dir", default=DEFAULT_OUT)
    r.add_argument("--report", required=True)
    args = ap.parse_args()
    {"overlay": cmd_overlay, "analyse": cmd_analyse, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
