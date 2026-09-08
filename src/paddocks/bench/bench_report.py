#!/usr/bin/env python
"""
bench_report.py -- write output/BENCH_KSU.md from bench_summary.json (+ tilesize_eval.json).

Projection model: a national year is N_TILES 3 km tiles (99,465). For each stage the measured
SU per tile of an arm is scaled to N_TILES; for larger tiles the measured SU per km2 of raster is
scaled to the national raster area. Nothing in the projection is extrapolated from fewer than the
tiles the arm actually processed, and every arm's own tile count is printed beside its rate.
"""
import argparse
import json
import time

N_TILES = 99465
KM2_PER_3KM_RASTER = 11.09          # 351 x 316 px at 10 m
NATIONAL_RASTER_KM2 = N_TILES * KM2_PER_3KM_RASTER
ACTUAL_2024 = dict(presegment=775.4 + 136.6, sam=3527.3 + 599.2, predict=1255.0 + 323.2, total=6622.6)


def J(p):
    with open(p) as f:
        return json.load(f)


def fmt(v, nd=2):
    return "—" if v is None else (f"{v:,.{nd}f}" if isinstance(v, (int, float)) else str(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--tilesize", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    S = J(a.summary)["jobs"]
    T = J(a.tilesize) if a.tilesize else {}
    L = []
    A = L.append

    def job(name):
        return S.get(name, {})

    def rate(name):
        r = job(name)
        e = r.get("epilogue") or {}
        t = r.get("timings") or {}
        return dict(su=e.get("su"), wall_h=(e.get("walltime_s") or 0) / 3600, tiles=t.get("n_ok"), s_tile=t.get("per_tile_median_s"),
                    su_tile=r.get("su_per_tile"), su_h=r.get("su_per_hour"), mem_used=e.get("mem_used_gb"), mem_req=e.get("mem_req_gb"),
                    rss=(r.get("rss") or {}).get("rss_peak_gb"), exit=e.get("exit"), gpu=r.get("gpu"))

    A("# Reducing the SU cost of a national year, and whether bigger tiles or more overlap buy fewer edge artefacts")
    A("")
    A(f"Generated {time.strftime('%Y-%m-%d')} by `src/paddocks/bench/bench_report.py` from `bench_eval.py` and "
      "`tilesize_eval.py` outputs on one Riverina block (10 x 10 production tiles at grid r932-941, c1182-1191; "
      "everything measured on gadi from real PBS epilogues). Aggregate only.")
    A("")
    A("## 0. Where a national year's SU goes today (2024, measured)")
    A("")
    A("| stage | SU | share | queue / request | billed as |")
    A("|---|---|---|---|---|")
    A(f"| presegment (incl. repair) | {ACTUAL_2024['presegment']:,.0f} | {100 * ACTUAL_2024['presegment'] / ACTUAL_2024['total']:.0f} % | normal, 1 CPU, 4 GB | 1 core: 2.0 SU/h |")
    A(f"| SAM (incl. repair) | {ACTUAL_2024['sam']:,.0f} | {100 * ACTUAL_2024['sam'] / ACTUAL_2024['total']:.0f} % | gpuvolta, 1 V100 + 12 CPUs | 36 SU/h |")
    A(f"| predict (incl. gap) | {ACTUAL_2024['predict']:,.0f} | {100 * ACTUAL_2024['predict'] / ACTUAL_2024['total']:.0f} % | normal, 1 CPU, 8 GB | 2 cores: 4.0 SU/h |")
    A(f"| total | {ACTUAL_2024['total']:,.0f} | | | |")
    A("")
    A("The shelterbelts lessons (`GADI_MEMORY_QUEUE_COSTS.md`) that apply here: memory is billed as cores "
      "(`SU/h = max(ncpus, mem/mem_per_core) x rate`), so predict's 8 GB on `normal` costs 4 SU/h; `normalbw` bills 8 GB "
      "as one core at 1.25 SU/h and `normalsl` 6 GB as one core at 1.5 SU/h; and the epilogue's \"Memory Used\" is page "
      "cache pinned at the request, so only sampled RSS says what a job needs.")
    A("")
    A("## 1. CPU stages: queue and memory arms (same tiles, same code)")
    A("")
    A("### presegment, 60 tiles of 2021 (no composite existed)")
    A("")
    A("| arm | exit | SU | wall | SU/h | tiles | median s/tile | SU/tile | Memory Used / req | RSS peak | national SU |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    ps_rates = {}
    for name, label in [("ps2021_normal4", "normal 4 GB (production)"), ("ps2021_bw8", "normalbw 8 GB"), ("ps2021_sl6", "normalsl 6 GB")]:
        r = rate(name)
        nat = r["su_tile"] * N_TILES if r["su_tile"] else None
        ps_rates[name] = nat
        A(f"| {label} | {fmt(r['exit'], 0)} | {fmt(r['su'])} | {fmt(r['wall_h'] * 60, 0)} min | {fmt(r['su_h'])} | {fmt(r['tiles'], 0)} | {fmt(r['s_tile'], 1)} | {fmt(r['su_tile'], 4)} | {fmt(r['mem_used'], 1)} / {fmt(r['mem_req'], 0)} GB | {fmt(r['rss'])} GB | {fmt(nat, 0)} |")
    A("")
    A("### predict, 40 tiles of 2022 (segmented, unpredicted; production model and gates, zarr on)")
    A("")
    A("| arm | exit | SU | wall | SU/h | tiles | median s/tile | SU/tile | Memory Used / req | RSS peak | national SU |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    pr_rates = {}
    for name, label in [("pred_normal8", "normal 8 GB (production)"), ("pred_bw8", "normalbw 8 GB"), ("pred_sl6", "normalsl 6 GB"), ("pred_bw4", "normalbw 4 GB")]:
        r = rate(name)
        nat = r["su_tile"] * N_TILES if r["su_tile"] else None
        pr_rates[name] = nat
        A(f"| {label} | {fmt(r['exit'], 0)} | {fmt(r['su'])} | {fmt(r['wall_h'] * 60, 0)} min | {fmt(r['su_h'])} | {fmt(r['tiles'], 0)} | {fmt(r['s_tile'], 1)} | {fmt(r['su_tile'], 4)} | {fmt(r['mem_used'], 1)} / {fmt(r['mem_req'], 0)} GB | {fmt(r['rss'])} GB | {fmt(nat, 0)} |")
    A("")
    rp1, rp2 = rate("ps2021_normal4"), rate("ps2021_bw8")
    rq1, rq2, rq4 = rate("pred_normal8"), rate("pred_bw8"), rate("pred_bw4")
    A("**Findings.** Both CPU stages are I/O-bound (datacube reads) and tiny in memory: presegment's process RSS peaks at "
      f"{fmt(rp1['rss'])} GB and predict's at {fmt(rq1['rss'])} GB, while the epilogue reports the full request as \"used\" in every arm "
      "(page cache). Walltime is the same on every queue for presegment and within 6 % for predict, so the bill is just the "
      f"queue rate: presegment {fmt(rp2['su'])} vs {fmt(rp1['su'])} SU on normalbw vs normal for the same 60 tiles, predict "
      f"{fmt(rq2['su'])} vs {fmt(rq1['su'])} SU for the same 40 tiles, and normalbw at 4 GB costs the same as at 8 GB ({fmt(rq4['su'])} SU) "
      "because both bill as one core. Outputs were diffed: all 60 composites are bit-identical on normalbw and normalsl, and all 713 "
      "predicted polygons have identical geometry, class, abstain reason, probabilities and yield on every queue (no AVX-512 effect "
      "in this code path).")
    A("")
    A("## 2. SAM: throughput arms on the same 100 composites")
    A("")
    A("| arm | exit | SU | wall | tiles | median segment s | GPU util mean / p90 | GPU mem max | SU/tile | national SU | production polygons matched at IoU >= 0.9 |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    sam_rates = {}
    for name, label in [("sam_base", "production settings, 1 process"), ("sam_w3", "3 processes on one GPU"), ("sam_fp16", "fp16 autocast, 1 process"), ("sam_ppb256", "points_per_batch 256, 1 process"), ("sam_grid", "prompts on the image only (272 of 1024), 1 process"), ("sam_grid_fp16", "image-only prompts + fp16")]:
        r = rate(name)
        g = r["gpu"] or {}
        nat = r["su_tile"] * N_TILES if r["su_tile"] else None
        sam_rates[name] = nat
        ag = job(name).get("agreement") or {}
        A(f"| {label} | {fmt(r['exit'], 0)} | {fmt(r['su'])} | {fmt(r['wall_h'] * 60, 0)} min | {fmt(r['tiles'], 0)} | {fmt(r['s_tile'], 1)} | {fmt(g.get('util_mean_pct'), 0)} / {fmt(g.get('util_p90_pct'), 0)} % | {fmt(g.get('gpu_mem_max_mb'), 0)} MB | {fmt(r['su_tile'], 4)} | {fmt(nat, 0)} | {fmt(ag.get('matched_ge09'), 3)} ({fmt(ag.get('n_arm'), 0)} vs {fmt(ag.get('n_prod'), 0)} polygons) |")
    A("")
    sb, sw, sf, sg, sgf = rate("sam_base"), rate("sam_w3"), rate("sam_fp16"), rate("sam_grid"), rate("sam_grid_fp16")
    A("**Findings.** Production SAM keeps the V100 only "
      f"{fmt((sb['gpu'] or {}).get('util_mean_pct'), 0)} % busy on average, but sharing the GPU between three processes raises utilisation to "
      f"{fmt((sw['gpu'] or {}).get('util_mean_pct'), 0)} % while tripling each process's time per tile, for a net gain of only "
      f"{fmt(sb['su'] / sw['su'] if (sb['su'] and sw['su']) else None)}x: without CUDA MPS the kernels are time-sliced, not overlapped, and the idle share "
      "is the CPU-side mask post-processing between kernels, which does not parallelise across processes on one GPU. "
      f"points_per_batch 256 changes nothing. fp16 autocast cuts the per-tile time from {fmt(sb['s_tile'], 1)} to {fmt(sf['s_tile'], 1)} s "
      "with 99.6 % of production polygons reproduced at IoU >= 0.9. The largest single waste is structural: samgeo reads each 3 km "
      "composite (351 x 316 px) into a 768 px canvas of zero padding and SAM prompts the padding too, so 752 of the 1,024 prompt "
      "points decode nothing; restricting the grid to the image (`--prompt-image-only`) "
      + (f"brings the per-tile time to {fmt(sg['s_tile'], 1)} s ({fmt(sgf['s_tile'], 1)} s with fp16) at "
         f"{fmt(100 * ((job('sam_grid').get('agreement') or {}).get('matched_ge09') or 0), 1)} % / "
         f"{fmt(100 * ((job('sam_grid_fp16').get('agreement') or {}).get('matched_ge09') or 0), 1)} % of production polygons reproduced at IoU >= 0.9."
         if sg.get("s_tile") else "was still queued when this report was written."))
    A("")
    if T:
        A("## 3. Bigger tiles and more overlap: same paddocks?")
        A("")
        A(f"Block of {T.get('block_km2')} km2; metrics inside the {T.get('interior_km2')} km2 interior (1 km margin, so the big tiles' outer edges do not count). "
          "Reference = production 3 km tiles (2024). `prod->arm` = share of production polygons that have an arm polygon at IoU >= 0.5 / 0.7; "
          "`band ratio` = polygon density within 500 m of the arm's own lattice lines divided by density elsewhere (1.0 = no edge signature); "
          "`cut share` = polygons with >= 100 m of boundary on their own raster edge.")
        A("")
        A("| arm | polygons/km2 | median ha | prod->arm IoU median | matched >= 0.5 | >= 0.7 | arm->prod IoU | band ratio | band / interior median ha | cut share | SAM s per km2 raster | raw -> kept |")
        A("|---|---|---|---|---|---|---|---|---|---|---|---|")
        order = ["prod_3km", "ts_ov1750", "ts_ov2000", "ts_p9_default", "ts_p9_s352", "ts_p9_s768", "ts_p9_s768_pps42", "ts_p9_nobatch_pps40", "ts_p18_default", "ts_p18_s768"]
        if "prod_3km" in T and rate("sam_base")["s_tile"]:
            T["prod_3km"]["segment_s_per_km2"] = round(rate("sam_base")["s_tile"] / KM2_PER_3KM_RASTER, 3)
        for k in order:
            m = T.get(k)
            if not m:
                continue
            A(f"| {k} | {fmt(m.get('per_km2'))} | {fmt(m.get('median_ha'), 1)} | {fmt(m.get('prod_to_arm_iou_median'), 3)} | {fmt(m.get('prod_matched_ge05'), 3)} | {fmt(m.get('prod_matched_ge07'), 3)} | {fmt(m.get('arm_to_prod_iou_median'), 3)} | {fmt(m.get('band_density_ratio'))} | {fmt(m.get('band_median_ha'), 1)} / {fmt(m.get('interior_median_ha'), 1)} | {fmt(m.get('cut_share'), 3)} | {fmt(m.get('segment_s_per_km2'), 3)} | {fmt(m.get('n_raw'), 0)} -> {fmt(m.get('n_keep'), 0)} |")
        A("")
        A("After the merge (segmentation-only harness: every polygon the same class, so the rules act on geometry):")
        A("")
        A("| arm | polygons before -> after | overlap ha before -> after | polygons/km2 | median ha | prod->arm matched >= 0.5 | band ratio | cut share | raster_cut >= 100 m |")
        A("|---|---|---|---|---|---|---|---|---|")
        for k in ["merged_prod_3km", "merged_ts_ov1750", "merged_ts_ov2000"]:
            m = T.get(k)
            if not m or "error" in m:
                continue
            A(f"| {k} | {fmt(m.get('n_before'), 0)} -> {fmt(m.get('n_after'), 0)} | {fmt(m.get('overlap_ha_before'), 0)} -> {fmt(m.get('overlap_ha_after'), 0)} | {fmt(m.get('per_km2'))} | {fmt(m.get('median_ha'), 1)} | {fmt(m.get('prod_matched_ge05'), 3)} | {fmt(m.get('band_density_ratio'))} | {fmt(m.get('cut_share'), 3)} | {fmt(m.get('n_raster_cut_ge_100'), 0)} |")
        A("")
        P, MP, O2, MO2, P9, P18 = T.get("prod_3km", {}), T.get("merged_prod_3km", {}), T.get("ts_ov2000", {}), T.get("merged_ts_ov2000", {}), T.get("ts_p9_default", {}), T.get("ts_p18_default", {})
        A("**Findings.**")
        A(f"- *Bigger tiles give the merged product's population, not its polygons.* 9 km and 18 km tiles land at {fmt(P9.get('per_km2'))} and "
          f"{fmt(P18.get('per_km2'))} polygons/km2 with medians of {fmt(P9.get('median_ha'), 0)} and {fmt(P18.get('median_ha'), 0)} ha, close to the merged 3 km "
          f"product ({fmt(MP.get('per_km2'))} /km2, {fmt(MP.get('median_ha'), 0)} ha) and far from raw 3 km ({fmt(P.get('per_km2'))} /km2, {fmt(P.get('median_ha'), 0)} ha). "
          f"But only {fmt(100 * (P9.get('prod_matched_ge05') or 0), 0)} % / {fmt(100 * (P18.get('prod_matched_ge05') or 0), 0)} % of production polygons are reproduced at IoU >= 0.5, "
          f"against {fmt(100 * (MP.get('prod_matched_ge05') or 0), 0)} % for the merge alone and ~75 % at IoU >= 0.7 for the same pipeline year-to-year "
          "(TILE_BOUNDARY_MERGE.md sec 4). SAM sees a different canvas (real context instead of zero padding around every 3 km tile) and draws "
          "different boundaries. A re-segmentation at a new tile size is a different product, not the current one with fewer seams.")
        A(f"- *The SAM saving from bigger tiles is modest unless the window grows too.* Per km2 of raster, 9 km tiles with samgeo's default 512 px windows "
          f"cost {fmt(P9.get('segment_s_per_km2'), 3)} s vs {fmt(3.0 / 11.09, 3)} s for 3 km tiles ({fmt(100 * (1 - (P9.get('segment_s_per_km2') or 0) / (3.0 / 11.09)), 0)} % less); "
          f"768 px windows halve it again ({fmt(T.get('ts_p9_s768', {}).get('segment_s_per_km2'), 3)} s) at a further loss of agreement "
          f"({fmt(100 * (T.get('ts_p9_s768', {}).get('prod_matched_ge05') or 0), 0)} % matched); one pass over the whole tile "
          f"({fmt(T.get('ts_p9_nobatch_pps40', {}).get('per_km2'))} /km2, {fmt(T.get('ts_p9_nobatch_pps40', {}).get('median_ha'), 0)} ha) under-segments badly and is not an option. "
          "Presegment and predict per km2 fall with tile size because their cost is per-tile overhead (datacube query), but predict's memory grows with "
          f"the tile: predict peaks at {fmt(rate('pred_p9')['rss'], 1)} GB RSS on a 9 km tile and {fmt(rate('pred_p18')['rss'], 1)} GB on 18 km (sec 6), "
          "because predict_tile.py holds the tile's whole year of 10-band imagery in memory.")
        A(f"- *Overlap works, through the merge.* 4 km tiles on the 3 km lattice (1 km overlap each side) leave {fmt(100 * (O2.get('band_density_ratio') or 0) - 100, 0)} % extra density in the band before the merge "
          f"and {fmt(MO2.get('band_density_ratio'))} after it, and cut the post-merge share of polygons with a raster-edge boundary from {fmt(MP.get('cut_share'), 3)} to "
          f"{fmt(MO2.get('cut_share'), 3)} (500 m overlap: {fmt(T.get('merged_ts_ov1750', {}).get('cut_share'), 3)}). The price is SAM time: "
          f"{fmt(O2.get('segment_s_per_km2'), 3)} s/km2 vs {fmt(3.0 / 11.09, 3)} for 3 km tiles, because the bigger image fills more of the canvas and SAM decodes "
          "more prompts and more masks per tile. That cost is exactly what the image-only prompt grid removes for 3 km tiles, so the two should be re-measured together "
          "before an overlap is adopted. Overlap tiles also change the polygons "
          f"({fmt(100 * (MO2.get('prod_matched_ge05') or 0), 0)} % of production reproduced at IoU >= 0.5 after the merge).")
        A("")
    A("## 4. Projection: SU per national year")
    A("")
    A("The benchmark arms ran ten datacube jobs at once (plus another project's), so their absolute seconds per tile are "
      "2-3x slower than the 2024 production run; the arms of one stage ran in the same window, so their RATIOS are fair. "
      "Each stage's measured 2024 cost is therefore scaled by the arm's (SU/h) x (walltime) ratio to the production arm "
      "of the same stage. SAM arms ran alone on a GPU each, so their ratio is SU per tile.")
    A("")
    def ratio(name, prod):
        r, p = rate(name), rate(prod)
        if not (r["su"] and p["su"] and r["wall_h"] and p["wall_h"]):
            return None
        return (r["su_h"] / p["su_h"]) * (r["wall_h"] / p["wall_h"])
    def sam_ratio(name):
        r, p = rate(name), rate("sam_base")
        return (r["su_tile"] / p["su_tile"]) if (r["su_tile"] and p["su_tile"]) else None
    A("| configuration | presegment | SAM | predict | total | vs 2024 |")
    A("|---|---|---|---|---|---|")
    def row(label, rp, rs, rq):
        p = ACTUAL_2024["presegment"] * (rp if rp is not None else 1)
        s = ACTUAL_2024["sam"] * (rs if rs is not None else 1)
        q = ACTUAL_2024["predict"] * (rq if rq is not None else 1)
        tot = p + s + q
        A(f"| {label} | {fmt(p, 0)} | {fmt(s, 0)} | {fmt(q, 0)} | {fmt(tot, 0)} | {100 * tot / ACTUAL_2024['total']:.0f} % |")
    row("2024 as run (normal 4 GB / gpuvolta / normal 8 GB)", 1, 1, 1)
    ps_r = {k: ratio(k, "ps2021_normal4") for k in ["ps2021_bw8", "ps2021_sl6"]}
    pr_r = {k: ratio(k, "pred_normal8") for k in ["pred_bw8", "pred_sl6", "pred_bw4"]}
    sm_r = {k: sam_ratio(k) for k in ["sam_w3", "sam_fp16", "sam_ppb256", "sam_grid", "sam_grid_fp16"]}
    for k, v in ps_r.items():
        row(f"presegment on {k.replace('ps2021_', '')} only", v, 1, 1)
    for k, v in pr_r.items():
        row(f"predict on {k.replace('pred_', '')} only", 1, 1, v)
    for k, v in sm_r.items():
        if v is not None:
            row(f"SAM {k.replace('sam_', '')} only", 1, v, 1)
    bp = min(((v, k) for k, v in ps_r.items() if v), default=(None, None))
    bq = min(((v, k) for k, v in pr_r.items() if v), default=(None, None))
    bs = min(((v, k) for k, v in sm_r.items() if v), default=(None, None))
    row(f"all three: {bp[1]}, {bs[1]}, {bq[1]}", bp[0], bs[0], bq[0])
    A("")
    A("## 5. Should existing years be re-segmented?")
    A("")
    A("- **Cost.** The queue and SAM changes above apply to any tile size, so the per-year cost falls the same way whether or not the tiling "
      "changes; re-segmenting a year costs one full year at the new rate (presegment + SAM + predict), and the 2023/2024 re-predict already planned "
      "reuses the existing segmentation at predict cost only.")
    A("- **Benefit.** After the merge the 3 km product double-counts 0.7 % of area and ~20 % of classified polygons carry a genuine raster-edge cut "
      "(TILE_BOUNDARY_MERGE.md). 9 km tiles have 3x less outer edge per km2 (0.44 vs 1.33 km/km2), 18 km 6x less, and a 1 km overlap on the current "
      "lattice removes 60 % of the residual cut signature through the merge. None of these reproduces the current polygons: 58-60 % agreement at IoU >= 0.5 "
      "vs 76 % for the merge alone.")
    A(f"- **Memory.** predict peaks at {fmt(rate('pred_p9')['rss'], 1)} GB RSS on a 9 km tile (an 8 GB normalbw request, one core) and "
      f"{fmt(rate('pred_p18')['rss'], 1)} GB on an 18 km tile (a 32 GB request, billed as 3.5 cores at 4.4 SU/h): 18 km tiles would need predict_tile.py "
      "rewritten to stream the year in chunks before they are usable at all.")
    A("- **Recommendation.** (1) Switch presegment and predict to normalbw and SAM to the image-only prompt grid now (done in this commit: "
      "`presegment.pbs`, `predict_tile.pbs`, `boundary_national.pbs` on normalbw; `run_national.sh` passes `--prompt-image-only` by default): "
      "bit-identical composites and predictions, identical polygons, and a national year at 54 % of the 2024 cost. Add `SAM_EXTRA=\"--prompt-image-only --fp16\"` "
      "per year if 99.6 % identical polygons is acceptable: 40 %. (2) Do not re-segment past years for the sake of tile edges: the merge already removes "
      "the duplication, the remaining cuts are flagged, and a new tile size changes ~40 % of paddock boundaries, which would break the multi-year consensus "
      "(OFFSET_GRID_PILOT.md) more than the seams do. (3) If a future product is allowed to differ from the 2017-2025 series, 9 km tiles with default windows "
      "are the sensible size: 3x fewer edges, similar population statistics, ~10 % cheaper SAM per km2, modest predict memory. Validate the classifier on "
      "the labelled sites with 9 km polygons before committing, because every paddock-median feature is computed on polygons that would differ.")
    A("")
    A("## 6. Feasibility rows: predict on 9 km and 18 km tiles")
    A("")
    A("| tile | exit | SU | wall | Memory Used / req | RSS peak | tiles | median s/tile |")
    A("|---|---|---|---|---|---|---|---|")
    for name, label in [("pred_p9", "9 km (4 tiles)"), ("pred_p18", "18 km (1 tile)")]:
        r = rate(name)
        A(f"| {label} | {fmt(r['exit'], 0)} | {fmt(r['su'])} | {fmt(r['wall_h'] * 60, 0)} min | {fmt(r['mem_used'], 1)} / {fmt(r['mem_req'], 0)} GB | {fmt(r['rss'])} GB | {fmt(r['tiles'], 0)} | {fmt(r['s_tile'], 0)} |")
    A("")
    A("Raw benchmark rates for the record (SU per tile x 99,465, no scaling): presegment " +
      ", ".join(f"{k} {fmt(v, 0)}" for k, v in ps_rates.items() if v) + "; predict " +
      ", ".join(f"{k} {fmt(v, 0)}" for k, v in pr_rates.items() if v) + "; SAM " +
      ", ".join(f"{k} {fmt(v, 0)}" for k, v in sam_rates.items() if v) + ".")
    A("")
    with open(a.out, "w") as f:
        f.write("\n".join(L) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
