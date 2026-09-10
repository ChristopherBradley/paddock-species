#!/usr/bin/env python
"""
validation_report.py -- write output/VALIDATION_9KM.md: the 9 km pipeline in its final form
(EPSG:3577 composites, 350 m buffer, image-only prompts + fp16, SAM+predict in one GPU job, zarr
on) scored at the 543 fixed test trials against the 3 km production pipeline, with the same
temporal-holdout model (trained on 2017-2022) on both. Aggregate only.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import time

import numpy as np
import pandas as pd

LOGS = "/scratch/xe2/cb8590/paddock-species-logs"
N9 = 15968
CLASSES = ["Canola", "Cereal", "Legume"]


def J(p):
    return json.load(open(p)) if os.path.exists(p) else None


def fmt(v, nd=3):
    return "—" if v is None else (f"{v:,.{nd}f}" if isinstance(v, (int, float)) else str(v))


def epilogue(jid):
    fs = glob.glob(f"{LOGS}/{jid}.gadi-pbs.OU")
    if not fs:
        return {}
    t = open(fs[0], errors="replace").read()
    g = lambda pat: (float(re.search(pat, t).group(1)) if re.search(pat, t) else None)
    wt = re.search(r"Walltime Used:\s+(\d+):(\d+):(\d+)", t)
    orch = re.search(r"done in (\d+) s: SAM rc=(\d+), (\d+) tiles predicted, (\d+) failed batches, ([\d.]+) s wall per predicted tile", t)
    return dict(su=g(r"Service Units:\s+([\d.]+)"), wall_s=(int(wt.group(1)) * 3600 + int(wt.group(2)) * 60 + int(wt.group(3))) if wt else None,
                exit=g(r"Exit Status:\s+(-?\d+)"), orch=orch.groups() if orch else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--val", required=True, help="benchksu/validation dir")
    ap.add_argument("--bench", required=True)
    ap.add_argument("--decision", default=None, help="geometry_decision.json with the p9_3577 arm")
    ap.add_argument("--visual", default=None, help="visual_verdicts_sites.json (aggregate verdicts)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    V, B = a.val, a.bench
    jobs = dict(l.split()[:2] for l in open(f"{B}/jobs.txt") if l.strip())
    E3 = {y: J(f"{V}/eval3_{y}.json") for y in ("2023", "2024", "pooled")}
    E9 = {y: J(f"{V}/eval9_{y}.json") for y in ("2023", "2024", "pooled")}
    G = J(a.decision) if a.decision else None
    VV = J(a.visual) if a.visual else None
    L = []; A = L.append
    A("# Validating the 9 km pipeline before the 2024 re-run")
    A("")
    A(f"Generated {time.strftime('%Y-%m-%d')} by `src/paddocks/bench/validation_report.py`. Both products were scored at the model's 543 fixed test "
      "trials (2023 and 2024; 533 fall on the tile lattice) with a temporal-holdout copy of the adopted classifier (`group3_map_sharma6_le2022.joblib`: "
      "same 153 features and flags, trained on 2017-2022 only), so the numbers are honest for both and directly comparable with the feature-level "
      "0.890 macro F1 the model was adopted on. The site's polygon is the one containing it, preferring the tile whose lattice square holds the site. Aggregate only.")
    A("")
    A("## 0. Verdict")
    A("")
    p3, p9 = E3.get("pooled") or {}, E9.get("pooled") or {}
    if p3 and p9:
        A(f"- Macro F1 at the test sites: **{fmt(p9.get('macro_f1'))} (9 km, final pipeline) vs {fmt(p3.get('macro_f1'))} (3 km production)**; balanced accuracy "
          f"{fmt(p9.get('balanced_accuracy'))} vs {fmt(p3.get('balanced_accuracy'))}; sites scored {p9.get('n_scored')} vs {p3.get('n_scored')} of {p9.get('n_sites')} "
          f"(no polygon {p9.get('no_polygon')} vs {p3.get('no_polygon')}; abstained {p9.get('abstained')} vs {p3.get('abstained')}).")
        a3, a9 = p3.get("area_vs_label", {}), p9.get("area_vs_label", {})
        A(f"- Polygon area vs the trial paddock area in the label set: median |log ratio| {fmt(a9.get('median_abs_log_ratio'))} vs {fmt(a3.get('median_abs_log_ratio'))}; "
          f"within a factor of 2: {fmt(100 * (a9.get('within_factor_2') or 0), 0)} % vs {fmt(100 * (a3.get('within_factor_2') or 0), 0)} % "
          f"(polygon median {fmt(a9.get('poly_median_ha'), 1)} vs {fmt(a3.get('poly_median_ha'), 1)} ha; label median {fmt(a3.get('label_median_ha'), 1)} ha).")
    A("")
    A("## 1. Per-class precision, recall and F1 at the test sites")
    A("")
    A("| product | year | n scored | class | n | precision | recall | F1 | macro F1 | balanced acc. | recall counting missing/abstained sites as misses |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    for lab, E in (("3 km production", E3), ("9 km final", E9)):
        for y in ("2023", "2024", "pooled"):
            e = E.get(y)
            if not e:
                continue
            for k in CLASSES:
                c = e["by_class"][k]
                A(f"| {lab} | {y} | {e['n_scored']} | {k} | {c['n']} | {fmt(c['precision'])} | {fmt(c['recall'])} | {fmt(c['f1'])} | "
                  f"{fmt(e['macro_f1']) if k == 'Canola' else ''} | {fmt(e['balanced_accuracy']) if k == 'Canola' else ''} | {fmt(e['recall_all_sites_by_class'][k])} |")
    A("")
    if p3 and p9:
        A("Confusion matrices (rows = label, columns = predicted; Canola, Cereal, Legume), pooled:")
        A("")
        A(f"- 3 km production: {p3.get('confusion_rows_true_cols_pred')}")
        A(f"- 9 km final: {p9.get('confusion_rows_true_cols_pred')}")
        A("")
        A(f"Abstention reasons at sites — 3 km: {p3.get('abstain_reasons')}; 9 km: {p9.get('abstain_reasons')}. "
          f"Sites seen by more than one tile: 3 km {p3.get('multi_view_sites')}, 9 km {p9.get('multi_view_sites')}.")
        A("")
    # cost of the final configuration from the validation jobs themselves
    A("## 2. What the final configuration cost, per tile, in these runs")
    A("")
    rows = []
    for name in ("val_sp9_2023", "val_sp9_2024", "sp_p9_3577"):
        jid = jobs.get(name, "").split(".")[0]
        e = epilogue(jid) if jid else {}
        preddir = {"val_sp9_2023": f"{V}/pred9_2023", "val_sp9_2024": f"{V}/pred9_2024", "sp_p9_3577": f"{B}/pred_p9_3577"}[name]
        tp = glob.glob(f"{preddir}/timings_predict.csv")
        t = pd.read_csv(tp[0]) if tp else None
        n_tiles = int(subprocess.run(["bash", "-c", f"wc -l < {preddir}/done_stubs.txt"], capture_output=True, text=True).stdout or 0) if os.path.exists(f"{preddir}/done_stubs.txt") else 0
        z = subprocess.run(["du", "-sm"] + glob.glob(f"{preddir}/p_*.zarr"), capture_output=True, text=True).stdout if glob.glob(f"{preddir}/p_*.zarr") else ""
        zarr_mb = sum(int(l.split()[0]) for l in z.strip().splitlines()) if z else 0
        rows.append(dict(job=name, su=e.get("su"), wall_s=e.get("wall_s"), tiles=n_tiles, s_per_tile=(e.get("wall_s") / n_tiles) if (e.get("wall_s") and n_tiles) else None,
                         su_per_tile=(e.get("su") / n_tiles) if (e.get("su") and n_tiles) else None,
                         pred_total_s=float(t.total_s.median()) if t is not None else None, pred_read_s=float(t.read_s.median()) if t is not None else None,
                         pred_zonal_s=float(t.zonal_s.median()) if t is not None else None, zarr_mb_per_tile=(zarr_mb / n_tiles) if n_tiles else None, orch=e.get("orch"),
                         exit=e.get("exit")))
    A("| job | exit | tiles | SU | wall | wall s / tile | SU / tile | predict s / tile (read, zonal) | zarr MB / tile | orchestrator line |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        A(f"| {r['job']} | {fmt(r['exit'], 0)} | {r['tiles']} | {fmt(r['su'], 2)} | {fmt((r['wall_s'] or 0) / 60, 0)} min | {fmt(r['s_per_tile'], 1)} | {fmt(r['su_per_tile'], 4)} | "
          f"{fmt(r['pred_total_s'], 0)} ({fmt(r['pred_read_s'], 0)}, {fmt(r['pred_zonal_s'], 0)}) | {fmt(r['zarr_mb_per_tile'], 1)} | {r['orch']} |")
    A("")
    bad = [r for r in rows if r["su_per_tile"] and r["exit"] != 0]
    if bad:
        A(f"Jobs with a non-zero exit ({', '.join(r['job'] for r in bad)}) are listed but excluded from the projection. `val_sp9_2023` hit its 2 h walltime "
          "with 64 of 131 tiles predicted; its `tiles` column counts the whole list because the remaining 67 were predicted afterwards by a CPU top-up job "
          "(`val_top9_2023`: `sampredict.pbs` with `ORCH_EXTRA=--no-sam` on normalbw, 4 workers). SAM had finished all 131 tiles at the normal 9 s/tile; "
          "the predict workers ran the zonal step at 482 s/tile (5 s per polygon) against 16 s/tile in the identical 2024 job. **Cause found and fixed "
          "(2026-09-09):** the zonal phase allocates large fresh arrays (astype/where/stack over the (t, y, x) cube); numpy 1.26 marks every large "
          "allocation MADV_HUGEPAGE and gadi runs transparent huge pages with defrag=madvise, so the kernel compacts memory synchronously on those "
          "faults, for a time that depends on the node's memory fragmentation. One 9 km tile, one core: zonal 41-396 s across nodes with the default, "
          "22-25 s on three nodes with `NUMPY_MADVISE_HUGEPAGE=0`; user time identical (47-48 s), system time 32-80 s vs 7-11 s, and the kernel's "
          "compact_stall counter moving on the slow runs. Not the year (the profiled 2023 and 2024 tiles cost the same), not threads, not the cgroup "
          "limit (a 24 GB run was the slowest). Every PBS script and `segment_predict.py`'s worker environment now set the variable. The remaining "
          "67 tiles of 2023 were predicted by a CPU top-up job (`val_top9_2023`, `sampredict.pbs` with `ORCH_EXTRA=--no-sam` on normalbw) and the 3 km "
          "arm the same way (`val_top3_*`) after two 1-core jobs hit a 4 h walltime at ~175 s per scattered tile with the GeoPackage unwritten.")
        A("")
    ok = [r for r in rows if r["su_per_tile"] and r["exit"] == 0]
    if ok:
        su_tile = float(np.average([r["su_per_tile"] for r in ok], weights=[r["tiles"] for r in ok]))
        ps = glob.glob(f"{V}/tiles9/timings_presegment_*.csv")
        pst = pd.concat([pd.read_csv(f) for f in ps]) if ps else None
        ps_s = float(pst[pst.status == "OK"].seconds.median()) if pst is not None else None
        ps_su = N9 * ps_s / 3600 * 1.25 if ps_s else None
        zarr_tb = np.average([r["zarr_mb_per_tile"] for r in ok if r["zarr_mb_per_tile"]], weights=[r["tiles"] for r in ok if r["zarr_mb_per_tile"]]) * N9 / 1e6 if any(r["zarr_mb_per_tile"] for r in ok) else None
        A(f"**Projected national year (15,968 parents):** SAM+predict {N9 * su_tile:,.0f} SU ({su_tile:.4f} SU per tile from the co-scheduled jobs, zarr on) "
          f"+ presegment {fmt(ps_su, 0)} SU ({fmt(ps_s, 0)} s per tile on normalbw) = **{N9 * su_tile + (ps_su or 0):,.0f} SU**; "
          f"zarr stores {fmt(zarr_tb, 2)} TB per year. Merge/boundary/summary add a few SU. 2024 as actually run: 6,623 SU.")
        A("")
        A("**Read this projection as an upper bound.** The site parents are scattered across the country, so the datacube read had no scene-cache locality: "
          "188 s per tile here against 93 s on the contiguous 36-tile block in `FUSED_PREDICT_BENCHMARK.md`, which made the 2024 job predict-bound "
          "(30 s wall per tile) where the contiguous benchmark had SAM (10.6 s) covering predict/11 (8.5 s). The 4-tile block arm is start-up dominated. "
          "On the real 9 km grid the contiguous-tile figures apply: about 2,000 SU for SAM+predict and 2,500 SU for the year, now that the zonal "
          "stall above is fixed; a like-for-like re-measurement with the fix is the gate before the 2024 re-run.")
        A("")
    if G and "p9_3577" in G:
        g, p = G["p9_3577"], G["prod_3km"]
        A("## 3. Edge artefacts in the final configuration (Riverina block, after the merge)")
        A("")
        A("| product | polygons/km2 | classified median ha | cut share (classified) | band density ratio | residual overlap % | class conflicts | classified area ha | production polygons matched at IoU >= 0.5 |")
        A("|---|---|---|---|---|---|---|---|---|")
        for lab, x in (("3 km production", p), ("9 km, EPSG:6933 (decision report)", G.get("p9", {})), ("9 km, EPSG:3577 + 350 m buffer (final)", g)):
            A(f"| {lab} | {fmt(x.get('per_km2'), 2)} | {fmt(x.get('classified_median_ha'), 1)} | {fmt(x.get('cut_share_classified'))} | {fmt(x.get('band_density_ratio'), 2)} | "
              f"{fmt(x.get('overlap_pct_area'), 2)} | {fmt(x.get('class_conflicts'), 0)} | {fmt(x.get('classified_area_ha'), 0)} | {fmt(x.get('prod_matched_ge05'))} |")
        A("")
    if VV:
        A("## 4. Visual check at test sites")
        A("")
        A(VV.get("summary", ""))
        A("")
        A("| window | what differs | verdict |")
        A("|---|---|---|")
        for w in VV.get("windows", []):
            A(f"| {w['window']} | {w['what']} | **{w['verdict']}** |")
        A("")
    A("## 5. Files")
    A("")
    A("- Per-site results (SENSITIVE, derived only): `benchksu/validation/eval{3,9}_*_sites_SENSITIVE.csv`; aggregate JSON beside them.")
    A("- Pipeline pieces validated here: `samgeo_segment.py presegment --output-crs EPSG:3577`, `grid9_from_2024.py --half-m 4850`, `segment_predict.py` + `sampredict.pbs`, `run_national.sh sampredict`, `eval_map_at_sites.py`.")
    A("")
    open(a.out, "w").write("\n".join(L) + "\n"); print("wrote", a.out)


if __name__ == "__main__":
    main()
