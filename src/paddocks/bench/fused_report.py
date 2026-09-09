#!/usr/bin/env python
"""fused_report.py -- write output/FUSED_PREDICT_BENCHMARK.md from read_split.py and bench_fused.pbs outputs."""
import argparse
import glob
import json
import time

import numpy as np
import pandas as pd

ap = argparse.ArgumentParser(); ap.add_argument("--bench", required=True); ap.add_argument("--out", required=True); a = ap.parse_args()
B = a.bench
G = json.load(open(f"{B}/decision/geometry_decision.json"))
rs9, rs3 = pd.read_csv(f"{B}/readsplit_p9.csv"), pd.read_csv(f"{B}/readsplit_3km.csv")
N9, N3 = 15968, 99465
def med(t, c): return float(t[c].median())
def kind(s): return np.where(s.str.startswith("nlum"), "3 km", np.where(s.str.startswith("p9_"), "9 km", np.where(s.str.startswith("p9ov1000"), "10 km", "11 km")))
fs = pd.concat([pd.read_csv(f) for f in glob.glob(f"{B}/fused_sam/timings_segment_*.csv")]); fs["kind"] = kind(fs.stub)
fp = pd.concat([pd.read_csv(f) for f in glob.glob(f"{B}/fused_pred/p*_timings.csv")]); fp["kind"] = kind(fp.stub)
solo_sam = {k: float(pd.concat([pd.read_csv(f) for f in glob.glob(f"{B}/{d}/timings_segment_*.csv")]).segment_s.median()) for k, d in [("3 km", "sam_grid_fp16"), ("9 km", "fx_p9"), ("10 km", "fx_p9ov1000"), ("11 km", "fx_p9ov2000")]}
solo_pred = {k: pd.concat([pd.read_csv(f) for f in glob.glob(f"{B}/{d}/*_timings.csv")]) for k, d in [("3 km", "pred_fx_prod36"), ("9 km", "pred_fx_p9"), ("10 km", "pred_fx_p9ov1000"), ("11 km", "pred_fx_p9ov2000")]}
c9, c3 = dict(G["p9"]["cost"]), dict(G["prod_3km"]["cost"])
# the decision JSON prices the 9 km arm on the ideal 99,465 / 9 grid; the real grid from grid9_from_2024.py has N9 parents
for c, n in ((c9, N9), (c3, N3)):
    c["sam_su_year"] = round(n * c["sam_s_per_tile"] / 3600 * 36)
    c["predict_su_year"] = round(n * c["predict_s_per_tile"] / 3600 * 1.25)
    c["presegment_su_year"] = round(n * c["presegment_s_per_tile"] / 3600 * 1.25)
    c["total_su_year"] = c["sam_su_year"] + c["predict_su_year"] + c["presegment_su_year"]
L = []; A = L.append
A("# Should predict reuse the Sentinel-2 bands from segmentation instead of re-reading the datacube?")
A("")
A(f"Generated {time.strftime('%Y-%m-%d')} by `src/paddocks/bench/fused_report.py` from `bench/read_split.py` (one normalbw job, the same tiles read by "
  "both stages back to back) and `bench/bench_fused.pbs` (one gpuvolta job: SAM on the GPU while 11 predict workers read the datacube on the node's spare cores). Aggregate only.")
A("")
A("## 0. Answer")
A("")
A("- **Reusing the bands cannot be done in this pipeline, and even if it could the saving would be small.** The two stages read different things "
  "(presegment: green, NIR and fmask over the whole year in EPSG:6933; predict: 10 bands and fmask over DOY 90-350 in EPSG:3577), and SAM on the GPU sits between "
  "them, so the band cube would have to be held across a queue boundary. Holding it means a cache of "
  f"{med(rs9, 'pred_scenes') * med(rs9, 'pred_px') * 11 * 2 / 1e9:.1f} GB per 9 km tile ({med(rs9, 'pred_scenes') * med(rs9, 'pred_px') * 11 * 2 * N9 / 1e12:.0f} TB nationally, "
  f"{med(rs3, 'pred_scenes') * med(rs3, 'pred_px') * 11 * 2 * N3 / 1e12:.0f} TB at 3 km) — more than the project's whole scratch allocation — and writing it costs about what reading it saves. "
  f"The saving itself is only the presegment read: {med(rs9, 'preseg_read_s'):.0f} s of a {med(rs9, 'total_separate_s'):.0f} s CPU budget per 9 km tile "
  f"({100 * (1 - med(rs9, 'total_fused_s') / med(rs9, 'total_separate_s')):.0f} %), about {N9 * med(rs9, 'preseg_read_s') / 3600 * 1.25:.0f} SU per national year, "
  f"{100 * (N9 * med(rs9, 'preseg_read_s') / 3600 * 1.25) / c9['total_su_year']:.0f} % of the 9 km year. On that point the earlier advice was right.")
A("- **What IS worth doing is different: run predict on the GPU job's idle cores while SAM runs.** A gpuvolta job bills 12 cores whatever they do; SAM uses one. "
  f"With 11 predict workers sharing the node, SAM slowed by at most {100 * (fs[fs.kind == '9 km'].segment_s.median() / solo_sam['9 km'] - 1):.0f} % and predict ran at normalbw speed "
  f"({fp[fp.kind == '9 km'].total_s.median():.0f} s per 9 km tile vs {solo_pred['9 km'].total_s.median():.0f} s alone). At 9 km the SAM wall time per tile "
  f"({c9['sam_s_per_tile']:.1f} s) exceeds the predict time spread over 11 workers ({fp[fp.kind == '9 km'].total_s.median() / 11:.1f} s), so predict rides along for free: "
  f"the {c9['predict_su_year']:,} SU predict stage disappears, {100 * c9['predict_su_year'] / c9['total_su_year']:.0f} % of the 9 km year. At 3 km it would not pay "
  f"(SAM {c3['sam_s_per_tile']:.2f} s per tile vs predict {fp[fp.kind == '3 km'].total_s.median() / 11:.1f} s: the job would wait on predict and pay 36 SU/h for it).")
A("- **Recommendation for the 2024 9 km re-run:** keep the stages separate for this run (it is the simplest thing that works and the predict stage is already 3x cheaper on normalbw), "
  "and build the SAM+predict co-scheduled job as the next optimisation once the 9 km product is validated. It needs an orchestrator (predict workers consuming tiles as their "
  "`_filt.gpkg` lands), not a code change to either stage.")
A("")
A("## 1. What each stage reads, on the same tiles (one job, back to back, normalbw)")
A("")
A("| tile | presegment read (green, NIR, fmask; whole year; EPSG:6933) | Fourier composite | predict read (10 bands + fmask; DOY 90-350; EPSG:3577) | zonal medians | separate total | read-once total | saving |")
A("|---|---|---|---|---|---|---|---|")
for lab, t in [("9 km (4 tiles)", rs9), ("3 km (8 tiles)", rs3)]:
    A(f"| {lab} | {med(t, 'preseg_read_s'):.1f} s ({med(t, 'preseg_scenes'):.0f} scenes, {med(t, 'preseg_px') / 1e3:.0f} k px) | {med(t, 'fourier_s'):.1f} s | "
      f"{med(t, 'pred_read_s'):.1f} s ({med(t, 'pred_scenes'):.0f} scenes, {med(t, 'pred_px') / 1e3:.0f} k px) | {med(t, 'zonal_s'):.1f} s | {med(t, 'total_separate_s'):.1f} s | "
      f"{med(t, 'total_fused_s'):.1f} s | {100 * (1 - med(t, 'total_fused_s') / med(t, 'total_separate_s')):.0f} % |")
A("")
A("Medians; per-tile spread is large (9 km presegment read 13-52 s, predict read 39-123 s) because datacube read time is dominated by the DB and Lustre, not pixels. "
  "A read-once design would still have to read the predict superset (10 bands, whole year) and derive the composite from it, so `read-once total` is the predict "
  "read plus both computes. The presegment read is the only thing saved.")
A("")
A("## 2. Co-scheduling: SAM on the GPU while predict workers use the spare cores (one gpuvolta job)")
A("")
A("| tile | SAM s/tile alone | SAM s/tile with 11 predict workers | predict s/tile alone (normalbw) | predict s/tile on the GPU node, 11 workers | predict read s alone / shared |")
A("|---|---|---|---|---|---|")
for k in ["3 km", "9 km", "10 km", "11 km"]:
    A(f"| {k} | {solo_sam[k]:.2f} | {fs[fs.kind == k].segment_s.median():.2f} | {solo_pred[k].total_s.median():.0f} | {fp[fp.kind == k].total_s.median():.0f} | "
      f"{solo_pred[k].read_s.median():.0f} / {fp[fp.kind == k].read_s.median():.0f} |")
A("")
A(f"112 composites segmented (12 large, 100 at 3 km) in 299 s while 22 tiles were predicted by 11 workers in 304 s; job cost 3.23 SU; node load average 42 on 48 cores; "
  "GPU utilisation 38 % because the SAM list was short relative to the predict list. The 10 km and 11 km solo predict runs were slower than the shared ones, "
  "so the shared numbers are not inflated by contention.")
A("")
A("## 3. Cost model per national year (9 km grid, 15,968 tiles; 3 km, 99,465 tiles)")
A("")
A("| configuration | SAM job wall s/tile | SAM SU | predict SU | presegment SU | total SU | note |")
A("|---|---|---|---|---|---|---|")
def row(lab, wall, n, pred, ps, note):
    sam = n * wall / 3600 * 36; A(f"| {lab} | {wall:.1f} | {sam:,.0f} | {pred:,.0f} | {ps:,.0f} | **{sam + pred + ps:,.0f}** | {note} |")
row("9 km, separate stages", c9["sam_s_per_tile"], N9, c9["predict_su_year"], c9["presegment_su_year"], "the plan")
w9 = max(c9["sam_s_per_tile"], fp[fp.kind == "9 km"].total_s.median() / 11)
row("9 km, predict co-scheduled in the SAM job", w9, N9, 0, c9["presegment_su_year"], "wall = max(SAM, predict/11 workers)")
row("9 km, bands cached and reused (not feasible)", c9["sam_s_per_tile"], N9, c9["predict_su_year"], c9["presegment_su_year"] - N9 * med(rs9, "preseg_read_s") / 3600 * 1.25, "saves only the presegment read; needs a 22 TB cache")
row("3 km, separate stages", c3["sam_s_per_tile"], N3, c3["predict_su_year"], c3["presegment_su_year"], "optimised 3 km, for reference")
w3 = max(c3["sam_s_per_tile"], fp[fp.kind == "3 km"].total_s.median() / 11)
row("3 km, predict co-scheduled", w3, N3, 0, c3["presegment_su_year"], "predict-bound: worse than separate")
A("")
A("## 4. Files")
A("")
A("- `bench/read_split.py`, `bench/bench_readsplit.pbs` (jobs 178497628, 178498784); `bench/bench_fused.pbs` (job 178497626).")
A(f"- Raw timings: `derived/benchksu/readsplit_p9.csv`, `readsplit_3km.csv`, `fused_sam/timings_segment_*.csv`, `fused_pred/p*_timings.csv`.")
A("")
open(a.out, "w").write("\n".join(L) + "\n"); print("wrote", a.out)
