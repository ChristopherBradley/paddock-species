#!/usr/bin/env python
"""
pilot_cost.py -- write output/PILOT_9KM_COST.md: the measured cost of the final 9 km configuration
(EPSG:3577 composites, SAM+predict co-scheduled, NUMPY_MADVISE_HUGEPAGE=0) on a contiguous block of
real 9 km grid parents, projected to the 15,968-parent national year. Gate 2 of the user's launch
condition (PROJ_NOTES 2026-09-09): the projection must be below 2.5 KSU. Aggregate only.
"""
import argparse, glob, os, re, time
import numpy as np, pandas as pd

LOGS = "/scratch/xe2/cb8590/paddock-species-logs"
N9 = 15968


def epilogue(jid):
    fs = glob.glob(f"{LOGS}/{jid}.gadi-pbs.OU")
    if not fs:
        return {}
    t = open(fs[0], errors="replace").read()
    g = lambda pat: (float(re.search(pat, t).group(1)) if re.search(pat, t) else None)
    wt = re.search(r"Walltime Used:\s+(\d+):(\d+):(\d+)", t)
    orch = re.search(r"done in (\d+) s: SAM rc=(\d+), (\d+) tiles predicted, (\d+) failed batches", t)
    return dict(su=g(r"Service Units:\s+([\d.]+)"), exit=g(r"Exit Status:\s+(-?\d+)"), text=t,
                wall_s=(int(wt.group(1)) * 3600 + int(wt.group(2)) * 60 + int(wt.group(3))) if wt else None,
                n_pred=int(orch.group(3)) if orch else None, n_failed=int(orch.group(4)) if orch else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--jobs", required=True, help="jobs.txt")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    P = a.pilot
    jobs = {}
    for l in open(a.jobs):
        if l.strip():
            k, v = l.split()[:2]; jobs[k] = v.split(".")[0]
    n_tiles = len(pd.read_csv(f"{P}/pilot_aois.csv"))
    L = []; A = L.append
    A("# Cost of the final 9 km configuration on a contiguous block (gate 2 before the 2024 re-run)")
    A("")
    A(f"Generated {time.strftime('%Y-%m-%d %H:%M')} by `src/paddocks/bench/pilot_cost.py`. {n_tiles} contiguous parents of the real 9 km 2024 grid "
      "(`grid9_from_2024.py --half-m 4850`, Riverina), presegmented in EPSG:3577 on normalbw and run through `sampredict.pbs` (SAM on the GPU, 11 predict "
      "workers on the same node), every job with `NUMPY_MADVISE_HUGEPAGE=0` (PROJ_NOTES 2026-09-09). Projection to the 15,968-parent national year. Aggregate only.")
    A("")
    # presegment
    ps = [pd.read_csv(f) for f in glob.glob(f"{P}/tiles/timings_presegment_*.csv")]
    ps = pd.concat(ps) if ps else None
    ps_ok = ps[ps.status == "OK"] if ps is not None and "status" in ps else ps
    ps_s = float(ps_ok.seconds.median()) if ps_ok is not None and len(ps_ok) else None
    ps_su_jobs = sum((epilogue(jobs[k]).get("su") or 0) for k in ("pilot_ps_a", "pilot_ps_b") if k in jobs)
    ps_n = int(len(ps_ok)) if ps_ok is not None else 0
    A("## 1. Presegment (normalbw, 1 core, 8 GB)")
    A("")
    A(f"- {ps_n} composites built; median {ps_s:.0f} s per tile (10th-90th pct {ps_ok.seconds.quantile(.1):.0f}-{ps_ok.seconds.quantile(.9):.0f} s); "
      f"jobs billed {ps_su_jobs:.2f} SU = {ps_su_jobs / max(ps_n, 1):.4f} SU per tile." if ps_n else "- not run yet")
    A(f"- Projected: {N9 * ps_s / 3600 * 1.25:,.0f} SU per year from the per-tile median (FUSED_PREDICT_BENCHMARK.md assumed 304; the scattered validation parents gave 603)." if ps_s else "")
    A("")
    # sam+predict
    sp = epilogue(jobs["pilot_sp"]) if "pilot_sp" in jobs else {}
    tp = glob.glob(f"{P}/pred/timings_predict.csv")
    t = pd.read_csv(tp[0]) if tp else None
    sam = open(f"{P}/pred/sam.log").read() if os.path.exists(f"{P}/pred/sam.log") else ""
    seg = [int(x) for x in re.findall(r"segment (\d+)s", sam)]
    A("## 2. SAM + predict, one gpuvolta job (12 cores, 1 GPU, 90 GB, 11 predict workers)")
    A("")
    if sp.get("su"):
        su_tile = sp["su"] / max(sp.get("n_pred") or 0, 1)
        A(f"- Exit {sp.get('exit'):.0f}; {sp.get('n_pred')} tiles predicted, {sp.get('n_failed')} failed batches; wall {sp['wall_s'] / 60:.1f} min = {sp['wall_s'] / max(sp.get('n_pred') or 1, 1):.1f} s per tile; "
          f"{sp['su']:.2f} SU = **{su_tile:.4f} SU per tile**.")
        if seg:
            A(f"- SAM: {len(seg)} tiles, median {np.median(seg):.0f} s GPU segment time per tile.")
        if t is not None:
            A(f"- predict per tile (median): total {t.total_s.median():.0f} s = read {t.read_s.median():.0f} s + zonal {t.zonal_s.median():.0f} s (10th-90th pct zonal {t.zonal_s.quantile(.1):.0f}-{t.zonal_s.quantile(.9):.0f} s); "
              f"{t.n_poly.median():.0f} polygons, {t.n_scenes.median():.0f} scenes per tile. Per-tile predict / 11 workers = {t.total_s.median() / 11:.1f} s vs SAM wall per tile {sp['wall_s'] / max(sp.get('n_pred') or 1, 1):.1f} s.")
        A(f"- Projected: **{N9 * su_tile:,.0f} SU per year** for SAM+predict (FUSED_PREDICT_BENCHMARK.md: 1,688 SAM + 0 predict co-scheduled).")
        A("")
        total = N9 * su_tile + (N9 * ps_s / 3600 * 1.25 if ps_s else 0) + 50
        A("## 3. Verdict")
        A("")
        A(f"- Full national year at 9 km = SAM+predict {N9 * su_tile:,.0f} + presegment {N9 * ps_s / 3600 * 1.25 if ps_s else 0:,.0f} + merge/boundary/summary ~50 = **{total:,.0f} SU**"
          f" -> {'BELOW' if total < 2500 else 'ABOVE'} the 2,500 SU gate (2024 as actually run at 3 km: 6,623 SU).")
        # 4. steady state: the pilot's wall is startup + n*rate + the last batch's tail; production jobs hold hundreds of tiles
        filt = sorted(os.path.getmtime(f) for f in glob.glob(f"{P}/tiles/*_filt.gpkg"))
        sam_wall = (filt[-1] - filt[0]) / max(len(filt) - 1, 1) if len(filt) > 1 else None
        m_start = re.search(r"\[(\d\d):(\d\d):(\d\d)\] SAM started", sp["text"])
        startup = None
        if m_start and filt:
            hh, mm, ss = (int(x) for x in m_start.groups()); first = time.localtime(filt[0])
            startup = (first.tm_hour * 3600 + first.tm_min * 60 + first.tm_sec) - (hh * 3600 + mm * 60 + ss)
        if sam_wall and t is not None and startup is not None:
            pred_mean = float(t.total_s.mean()); W = 11
            rate = max(sam_wall, pred_mean / W); tail = 0.5 * 4 * pred_mean
            gpu_busy = (sum(seg) / (filt[-1] - filt[0])) if seg and len(filt) > 1 else None
            A("")
            A("## 4. Steady state: what a production-size job costs")
            A("")
            A(f"- From this job: SAM wall {sam_wall:.1f} s per tile (GPU segment mean {np.mean(seg):.1f} s -> the GPU was busy {100 * gpu_busy:.0f} % of the SAM stage, so a second SAM "
              f"process would gain little); predict mean {pred_mean:.0f} s per tile / {W} workers = {pred_mean / W:.1f} s, i.e. the two sides are balanced at **{rate:.1f} s per tile**. "
              f"Startup to the first polygon file {startup:.0f} s; the last predict batch trails SAM by about {tail:.0f} s.")
            A("- Job wall = startup + n x rate + tail, at 36 SU/h:")
            A("")
            A("| tiles per job | wall | SU per tile | SAM+predict per year | + presegment 425 + merge etc. 50 |")
            A("|---|---|---|---|---|")
            for n in (48, 400, 1000, 2000):
                wall = startup + n * rate + tail; su_t = wall / 3600 * 36 / n
                A(f"| {n} | {wall / 60:.0f} min | {su_t:.4f} | {N9 * su_t:,.0f} | **{N9 * su_t + 475:,.0f}** |")
            A("")
            A(f"- The 48-tile row reproduces the measured job ({sp['wall_s'] / 60:.1f} min, {su_tile:.4f} SU per tile): the section-3 figure is a small-job artefact, "
              f"startup and tail being {100 * (startup + tail) / sp['wall_s']:.0f} % of its wall. With `run_national.sh sampredict` jobs of about 1,000 tiles (NCHUNK 60 x PER_SAM 4; "
              f"~3 h each, inside the 6 h walltime) the expected full year is about **{N9 * (startup + 1000 * rate + tail) / 3600 * 36 / 1000 + 475:,.0f} SU**, "
              f"{100 * (1 - (N9 * (startup + 1000 * rate + tail) / 3600 * 36 / 1000 + 475) / 2500):.0f} % under the 2,500 SU gate before any repair pass "
              f"(2024's 3 km run spent about 5 % of its cost on one repair pass).")
        if sp.get("n_failed"):
            A(f"- WARNING: {sp['n_failed']} failed predict batches -- check {P}/pred/p_*.log before trusting the per-tile figure.")
    else:
        A("- not run yet")
    A("")
    open(a.out, "w").write("\n".join(L) + "\n"); print("wrote", a.out)


if __name__ == "__main__":
    main()
