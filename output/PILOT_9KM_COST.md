# Cost of the final 9 km configuration on a contiguous block (gate 2 before the 2024 re-run)

Generated 2026-09-09 23:35 by `src/paddocks/bench/pilot_cost.py`. 48 contiguous parents of the real 9 km 2024 grid (`grid9_from_2024.py --half-m 4850`, Riverina), presegmented in EPSG:3577 on normalbw and run through `sampredict.pbs` (SAM on the GPU, 11 predict workers on the same node), every job with `NUMPY_MADVISE_HUGEPAGE=0` (PROJ_NOTES 2026-09-09). Projection to the 15,968-parent national year. Aggregate only.

## 1. Presegment (normalbw, 1 core, 8 GB)

- 48 composites built; median 77 s per tile (10th-90th pct 48-116 s); jobs billed 1.38 SU = 0.0287 SU per tile.
- Projected: 425 SU per year from the per-tile median (FUSED_PREDICT_BENCHMARK.md assumed 304; the scattered validation parents gave 603).

## 2. SAM + predict, one gpuvolta job (12 cores, 1 GPU, 90 GB, 11 predict workers)

- Exit 0; 48 tiles predicted, 0 failed batches; wall 14.6 min = 18.3 s per tile; 8.77 SU = **0.1827 SU per tile**.
- SAM: 48 tiles, median 8 s GPU segment time per tile.
- predict per tile (median): total 105 s = read 76 s + zonal 21 s (10th-90th pct zonal 17-40 s); 110 polygons, 52 scenes per tile. Per-tile predict / 11 workers = 9.5 s vs SAM wall per tile 18.3 s.
- Projected: **2,917 SU per year** for SAM+predict (FUSED_PREDICT_BENCHMARK.md: 1,688 SAM + 0 predict co-scheduled).

## 3. Verdict

- Full national year at 9 km = SAM+predict 2,917 + presegment 425 + merge/boundary/summary ~50 = **3,392 SU** -> ABOVE the 2,500 SU gate (2024 as actually run at 3 km: 6,623 SU).

## 4. Steady state: what a production-size job costs

- From this job: SAM wall 9.3 s per tile (GPU segment mean 8.5 s -> the GPU was busy 93 % of the SAM stage, so a second SAM process would gain little); predict mean 114 s per tile / 11 workers = 10.3 s, i.e. the two sides are balanced at **10.3 s per tile**. Startup to the first polygon file 71 s; the last predict batch trails SAM by about 227 s.
- Job wall = startup + n x rate + tail, at 36 SU/h:

| tiles per job | wall | SU per tile | SAM+predict per year | + presegment 425 + merge etc. 50 |
|---|---|---|---|---|
| 48 | 13 min | 0.1653 | 2,640 | **3,115** |
| 400 | 74 min | 0.1107 | 1,767 | **2,242** |
| 1000 | 177 min | 0.1062 | 1,696 | **2,171** |
| 2000 | 349 min | 0.1047 | 1,672 | **2,147** |

- The 48-tile row reproduces the measured job (14.6 min, 0.1827 SU per tile): the section-3 figure is a small-job artefact, startup and tail being 34 % of its wall. With `run_national.sh sampredict` jobs of about 1,000 tiles (NCHUNK 60 x PER_SAM 4; ~3 h each, inside the 6 h walltime) the expected full year is about **2,171 SU**, 13 % under the 2,500 SU gate before any repair pass (2024's 3 km run spent about 5 % of its cost on one repair pass).

