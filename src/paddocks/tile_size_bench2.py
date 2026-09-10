#!/usr/bin/env python3
"""
Tile size, round 2: is the 3 km-vs-9 km polygon difference a prompt-density artefact?

TILE_SIZE_BENCHMARK.md (2026-08-10) found that 3 km and 9 km tiles return different paddocks
on identical ground, and attributed it to prompt density: `points_per_side**2 / AOI_area`, which
gives 114 points/km² at 3 km and 76 at 9 km. That arithmetic is wrong, and this script exists
partly to show why.

WHAT SAMGEO ACTUALLY DOES (verified against the installed source, not the docs):

  samgeo/common.py:calculate_sample_grid  strides the raster in `sample_size` = 512 px steps
  starting at -`bound` = -128, and read_block reads a 512 + 2*128 = **768 x 768** window at each
  step with `boundless=True, fill_value=0`. Every window handed to SAM is therefore exactly
  768 x 768 pixels whatever the raster's size. segment_anything's build_point_grid lays
  `points_per_side` points across the *image it is given*, so the prompt grid is always
  768/pps pixels apart == 7680/pps metres at 10 m resolution.

  **Prompt spacing on the ground does not depend on tile size.** At pps=32 it is 240 m in a
  3 km tile and 240 m in a 9 km tile: (pps/7.68)**2 = 17.4 prompts/km**2 for both. The v1 figure
  divided pps**2 by the AOI area, which silently assumed one prompt grid is stretched over the
  whole tile. It is not; it is re-applied per 768 px window.

So "raise points_per_side in proportion to tile size to restore density" would not restore
parity — it would give a 9 km tile 3x the prompt density of a 3 km tile. What genuinely differs
with tile size is instead:

  1. **Zero padding.** A 3 km raster is ~348 x 321 px inside that 768 x 768 canvas: 81 % of what
     SAM sees is black, and ~81 % of the prompts land on it. A 9 km raster fills 9 windows, most
     of them entirely real data.
  2. **Internal seams.** Only the centre 512 x 512 of each window is written to the output mask
     (write_block crops the 128 px bound), so any raster wider than 512 - (-128) = 384 px is
     mosaicked from independent segmentations. A 9 km tile has internal seams every 5.12 km;
     a 3 km tile has none. Bigger tiles do not remove tile boundaries, they replace some of
     them with samgeo's own 5.12 km grid.

This script measures, on ground clipped to the same four 9 km parent footprints:
  polygons/km2, median + IQR area, kept/raw, exposure to tile edges AND to the 512 px seams,
  geometric agreement (best-IoU) against the 3 km baseline, and measured SU/km2.

    python3 tile_size_bench2.py \
        --arm 3km=$D/bench3km_matched:32 --arm 9km_pps32=$D/bench9km:32 \
        --baseline 3km --parents $D/aois_bench9km.csv --report ../../output/tile_size_v2.md
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd

ALBERS = "EPSG:3577"          # equal-area; the AOI squares are defined here
SAMPLE = 512                  # samgeo common.py tiff_to_tiff sample_size
BOUND = 128                   # samgeo common.py tiff_to_tiff bound
RES_M = 10.0
NORMAL_SU_HR = 2.0            # x max(ncpus, mem/4GB)
GPUVOLTA_SU_HR = 36.0         # the whole 12-CPU + 1-V100 unit, billed whole


# --------------------------------------------------------------------------- samgeo arithmetic

def window_origins(n_px):
    """Top-left offsets samgeo reads from, per axis: range(-bound, n, sample)."""
    return list(range(-BOUND, n_px, SAMPLE))


def prompt_stats(width, height, pps):
    """Prompts SAM actually places on real (non-padding) pixels, and the ground spacing.

    build_point_grid puts point i at (i + 0.5) / pps of the image, and the image is always
    768 x 768, so in raster coordinates a window at origin o carries points at
    o + (i + 0.5) * 768 / pps.
    """
    span = SAMPLE + 2 * BOUND
    step = span / pps
    def on_axis(n):
        hits = 0
        for o in window_origins(n):
            p = o + (np.arange(pps) + 0.5) * step
            hits += int(((p >= 0) & (p < n)).sum())
        return hits
    # Windows overlap in their bound margins, so the axis-wise count double-counts the overlap.
    # The count that governs the OUTPUT is the prompts inside each window's written core.
    def core_axis(n):
        hits = 0
        for o in window_origins(n):
            p = o + (np.arange(pps) + 0.5) * step
            lo, hi = o + BOUND, min(o + BOUND + SAMPLE, n)
            hits += int(((p >= max(lo, 0)) & (p < hi)).sum())
        return hits
    nx, ny = len(window_origins(width)), len(window_origins(height))
    km2 = width * height * RES_M ** 2 / 1e6
    return dict(px=f"{width}x{height}", windows=f"{nx}x{ny}={nx * ny}", n_windows=nx * ny,
                fill_pct=100.0 * width * height / (nx * ny * span * span),
                spacing_m=step * RES_M,
                prompts_total=nx * ny * pps ** 2,
                prompts_core=core_axis(width) * core_axis(height),
                prompts_on_data=on_axis(width) * on_axis(height),
                raster_km2=km2,
                prompts_per_km2=core_axis(width) * core_axis(height) / km2)


def seam_lines(width, height):
    """Interior 512 px mosaic seams, in raster pixel coordinates (x list, y list).

    Window k writes its core starting at origin + bound, i.e. at 0, 512, 1024, ... so the joins
    between independently segmented blocks fall on multiples of 512 strictly inside the raster.
    """
    xs = [x for x in range(SAMPLE, width, SAMPLE)]
    ys = [y for y in range(SAMPLE, height, SAMPLE)]
    return xs, ys


# --------------------------------------------------------------------------- geometry helpers

def parent_squares(parents_csv):
    """The 9 km parent AOI squares in EPSG:3577 — the matched ground every arm is clipped to."""
    from pyproj import Transformer
    from shapely.geometry import box
    src = pd.read_csv(parents_csv)
    to_alb = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)
    out = {}
    for _, r in src.iterrows():
        x, y = to_alb.transform(float(r.lon), float(r.lat))
        h = float(r.half_m)
        out[r.stub] = box(x - h, y - h, x + h, y + h)
    return out


def tile_frames(outdir, stubs):
    """Per tile: its raster footprint and its interior seam lines, as EPSG:3577 geometries.

    The truncating boundary is the RASTER edge, not the AOI square: pre-segment writes the
    bounding box (in EPSG:6933) of the AOI square (defined in EPSG:3577), which is a little
    larger and slightly rotated relative to it.
    """
    import geopandas as gpd
    import rasterio
    from shapely.geometry import LineString, box
    frames = {}
    for stub in stubs:
        tif = os.path.join(outdir, stub + ".tif")
        if not os.path.exists(tif):
            continue
        with rasterio.open(tif) as s:
            b, T, W, H, crs = s.bounds, s.transform, s.width, s.height, s.crs
            edge = box(*b).exterior
            xs, ys = seam_lines(W, H)
            seams = ([LineString([T * (x, 0), T * (x, H)]) for x in xs] +
                     [LineString([T * (0, y), T * (W, y)]) for y in ys])
        g = gpd.GeoSeries([edge] + seams, crs=crs).to_crs(ALBERS)
        frames[stub] = dict(edge=g.iloc[0], seams=list(g.iloc[1:]), n_seams=len(seams),
                            px=(W, H), crs=str(crs))
    return frames


def load_arm(outdir, aois_csv, parents, tol_m=15.0):
    """Every polygon of an arm, clipped to its parent square, tagged with edge/seam contact."""
    import geopandas as gpd
    aois = pd.read_csv(aois_csv)
    stub_parent = dict(zip(aois.stub, aois.get("parent", aois.stub)))
    frames = tile_frames(outdir, list(aois.stub))

    parts = []
    n_raw_total = n_keep_total = 0
    for stub, parent in stub_parent.items():
        f = os.path.join(outdir, stub + "_filt.gpkg")
        if not os.path.exists(f) or stub not in frames:
            continue
        g = gpd.read_file(f).to_crs(ALBERS)
        raw = os.path.join(outdir, stub + "_segment.gpkg")
        if os.path.exists(raw):
            n_raw_total += len(gpd.read_file(raw))
        n_keep_total += len(g)
        fr = frames[stub]
        # Contact is measured on the FULL tile output, before the parent clip, so the clip
        # itself cannot manufacture an edge.
        g["touch_edge"] = g.geometry.distance(fr["edge"]) < tol_m
        if fr["seams"]:
            import shapely
            seam = shapely.union_all(fr["seams"])
            g["touch_seam"] = g.geometry.distance(seam) < tol_m
        else:
            g["touch_seam"] = False
        g["stub"] = stub
        g["parent"] = parent
        sq = parents[parent]
        g = g[g.geometry.centroid.within(sq)]     # centroid rule: no polygon counted twice
        parts.append(g)
    if not parts:
        raise SystemExit(f"no polygons found under {outdir}")
    G = pd.concat(parts, ignore_index=True)
    G = gpd.GeoDataFrame(G, geometry="geometry", crs=ALBERS)
    G["area_ha"] = G.area / 1e4
    return G, n_raw_total, n_keep_total, frames


def iou_agreement(A, B):
    """For every polygon of A, best IoU against B. Returns (median, frac>=0.5, n)."""
    from shapely.strtree import STRtree
    tree = STRtree(list(B.geometry))
    best = []
    for geom in A.geometry:
        idx = tree.query(geom)
        b = 0.0
        for i in idx:
            o = B.geometry.iloc[int(i)]
            inter = geom.intersection(o).area
            if inter <= 0:
                continue
            b = max(b, inter / (geom.area + o.area - inter))
        best.append(b)
    best = np.asarray(best)
    return (float(np.median(best)) if len(best) else float("nan"),
            float((best >= 0.5).mean()) if len(best) else float("nan"), len(best))


# --------------------------------------------------------------------------- timings

def timings(outdir, stage):
    fs = glob.glob(os.path.join(outdir, f"timings_{stage}*.csv"))
    if not fs:
        return None
    d = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    return d[d.status == "OK"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True,
                    help="NAME=dir:pps[:aois_csv]; aois defaults to the arm's own AOI list")
    ap.add_argument("--aois", action="append", default=[], help="NAME=path override")
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--parents", required=True)
    ap.add_argument("--pre-mem-gb", type=float, default=4.0)
    ap.add_argument("--report")
    args = ap.parse_args()

    aois_override = dict(a.split("=", 1) for a in args.aois)
    parents = parent_squares(args.parents)
    ground_km2 = sum(p.area for p in parents.values()) / 1e6

    arms = {}
    order = []
    for spec in args.arm:
        name, rest = spec.split("=", 1)
        d, pps = rest.split(":")
        arms[name] = dict(dir=d, pps=int(pps), aois=aois_override[name])
        order.append(name)

    # ---------------------------------------------------------------- collect
    for name in order:
        a = arms[name]
        G, n_raw, n_keep, frames = load_arm(a["dir"], a["aois"], parents)
        a["G"], a["n_raw"], a["n_keep"], a["frames"] = G, n_raw, n_keep, frames
        w, h = next(iter(frames.values()))["px"]
        a["prompt"] = prompt_stats(w, h, a["pps"])
        a["seg"] = timings(a["dir"], "segment")
        a["pre"] = timings(a["dir"], "presegment")
        half = float(pd.read_csv(a["aois"]).half_m.iloc[0])
        a["tile_km"] = 2 * half / 1000.0
        a["n_tiles"] = len(frames)

    base = arms[args.baseline]

    out = []
    A = out.append
    A(f"Ground: {len(parents)} parent footprints, {ground_km2:.0f} km2, clipped identically "
      f"for every arm (polygon counted where its centroid falls).")
    A("")
    A("## Prompt geometry, from the installed samgeo/segment_anything source")
    A("")
    A("| arm | tile | raster px | 768px windows | canvas filled | prompt spacing | "
      "prompts/km2 |")
    A("|---|---|---|---|---|---|---|")
    for name in order:
        a, p = arms[name], arms[name]["prompt"]
        A(f"| {name} (pps={a['pps']}) | {a['tile_km']:g} km | {p['px']} | {p['windows']} | "
          f"{p['fill_pct']:.0f} % | {p['spacing_m']:.0f} m | {p['prompts_per_km2']:.1f} |")
    A("")

    # ---------------------------------------------------------------- polygon metrics
    A("## Polygons on matched ground")
    A("")
    A("| arm | polygons | polygons/km2 | median ha | IQR ha | kept/raw | % touching tile edge | "
      "% touching 512px seam | edge+seam km/km2 |")
    A("|---|---|---|---|---|---|---|---|---|")
    for name in order:
        a = arms[name]
        G = a["G"]
        q1, q3 = np.percentile(G.area_ha, [25, 75])
        f = next(iter(a["frames"].values()))
        seam_km = sum(s.length for s in f["seams"]) / 1000.0
        edge_km = f["edge"].length / 1000.0
        tile_km2 = a["tile_km"] ** 2
        A(f"| {name} (pps={a['pps']}) | {len(G)} | {len(G) / ground_km2:.2f} | "
          f"{G.area_ha.median():.1f} | {q1:.1f}-{q3:.1f} | "
          f"{a['n_keep'] / max(a['n_raw'], 1):.2f} | {100 * G.touch_edge.mean():.0f} % | "
          f"{100 * G.touch_seam.mean():.0f} % | {(edge_km + seam_km) / tile_km2:.2f} |")
    A("")

    # ---------------------------------------------------------------- IoU
    A(f"## Geometric agreement against `{args.baseline}`")
    A("")
    A("| arm | baseline->arm median IoU | frac >= 0.5 | arm->baseline median IoU | frac >= 0.5 |")
    A("|---|---|---|---|---|")
    for name in order:
        a = arms[name]
        m1, f1, _ = iou_agreement(base["G"], a["G"])
        m2, f2, _ = iou_agreement(a["G"], base["G"])
        A(f"| {name} (pps={a['pps']}) | {m1:.3f} | {f1:.2f} | {m2:.3f} | {f2:.2f} |")
    A("")

    # ---------------------------------------------------------------- cost
    A("## Measured cost (gadi's charging rule: normal 2 SU/hr x max(ncpus, mem/4GB); "
      "gpuvolta 36 SU/hr)")
    A("")
    A("| arm | tiles | SAM s/tile | SAM s/window | SAM SU/km2 | pre s/tile | pre SU/km2 | "
      "total SU/km2 | total SU for 324 km2 |")
    A("|---|---|---|---|---|---|---|---|---|")
    for name in order:
        a = arms[name]
        km2 = a["tile_km"] ** 2
        seg, pre = a["seg"], a["pre"]
        # Drop the first AOI of each job: it carries CUDA warm-up, which amortises away at
        # production batch size and would otherwise penalise whichever arm had fewer tiles.
        s = seg.segment_s.iloc[1:] if seg is not None and len(seg) > 2 else \
            (seg.segment_s if seg is not None else None)
        seg_s = float(s.mean()) if s is not None else float("nan")
        poly_s = float(seg.polygonise_s.mean()) if seg is not None else 0.0
        seg_su = GPUVOLTA_SU_HR * (seg_s + poly_s) / 3600.0 / km2
        pre_s = float(pre.seconds.mean()) if pre is not None else float("nan")
        pre_su = (NORMAL_SU_HR * max(1.0, args.pre_mem_gb / 4.0) * pre_s / 3600.0 / km2
                  if pre is not None else float("nan"))
        tot = seg_su + pre_su
        A(f"| {name} (pps={a['pps']}) | {a['n_tiles']} | {seg_s:.1f} | "
          f"{seg_s / a['prompt']['n_windows']:.2f} | {seg_su:.5f} | {pre_s:.1f} | "
          f"{pre_su:.5f} | **{tot:.5f}** | {tot * ground_km2:.2f} |")

    txt = "\n".join(out)
    print(txt)
    if args.report:
        with open(args.report, "w") as fh:
            fh.write(txt + "\n")


if __name__ == "__main__":
    main()
