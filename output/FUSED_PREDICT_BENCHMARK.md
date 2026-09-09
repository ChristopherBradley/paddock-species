# Should predict reuse the Sentinel-2 bands from segmentation instead of re-reading the datacube?

Generated 2026-09-09 by `src/paddocks/bench/fused_report.py` from `bench/read_split.py` (one normalbw job, the same tiles read by both stages back to back) and `bench/bench_fused.pbs` (one gpuvolta job: SAM on the GPU while 11 predict workers read the datacube on the node's spare cores). Aggregate only.

## 0. Answer

- **Reusing the bands cannot be done in this pipeline, and even if it could the saving would be small.** The two stages read different things (presegment: green, NIR and fmask over the whole year in EPSG:6933; predict: 10 bands and fmask over DOY 90-350 in EPSG:3577), and SAM on the GPU sits between them, so the band cube would have to be held across a queue boundary. Holding it means a cache of 1.4 GB per 9 km tile (22 TB nationally, 15 TB at 3 km) — more than the project's whole scratch allocation — and writing it costs about what reading it saves. The saving itself is only the presegment read: 37 s of a 215 s CPU budget per 9 km tile (17 %), about 204 SU per national year, 8 % of the 9 km year. On that point the earlier advice was right.
- **What IS worth doing is different: run predict on the GPU job's idle cores while SAM runs.** A gpuvolta job bills 12 cores whatever they do; SAM uses one. With 11 predict workers sharing the node, SAM slowed by at most 4 % and predict ran at normalbw speed (93 s per 9 km tile vs 91 s alone). At 9 km the SAM wall time per tile (10.6 s) exceeds the predict time spread over 11 workers (8.5 s), so predict rides along for free: the 506 SU predict stage disappears, 20 % of the 9 km year. At 3 km it would not pay (SAM 1.23 s per tile vs predict 5.2 s: the job would wait on predict and pay 36 SU/h for it).
- **Recommendation for the 2024 9 km re-run:** keep the stages separate for this run (it is the simplest thing that works and the predict stage is already 3x cheaper on normalbw), and build the SAM+predict co-scheduled job as the next optimisation once the 9 km product is validated. It needs an orchestrator (predict workers consuming tiles as their `_filt.gpkg` lands), not a code change to either stage.

## 1. What each stage reads, on the same tiles (one job, back to back, normalbw)

| tile | presegment read (green, NIR, fmask; whole year; EPSG:6933) | Fourier composite | predict read (10 bands + fmask; DOY 90-350; EPSG:3577) | zonal medians | separate total | read-once total | saving |
|---|---|---|---|---|---|---|---|
| 9 km (4 tiles) | 36.8 s (73 scenes, 1000 k px) | 29.1 s | 89.1 s (52 scenes, 1220 k px) | 77.2 s | 214.7 s | 177.9 s | 17 % |
| 3 km (8 tiles) | 5.7 s (73 scenes, 112 k px) | 3.2 s | 16.2 s (52 scenes, 131 k px) | 1.6 s | 26.6 s | 20.9 s | 21 % |

Medians; per-tile spread is large (9 km presegment read 13-52 s, predict read 39-123 s) because datacube read time is dominated by the DB and Lustre, not pixels. A read-once design would still have to read the predict superset (10 bands, whole year) and derive the composite from it, so `read-once total` is the predict read plus both computes. The presegment read is the only thing saved.

## 2. Co-scheduling: SAM on the GPU while predict workers use the spare cores (one gpuvolta job)

| tile | SAM s/tile alone | SAM s/tile with 11 predict workers | predict s/tile alone (normalbw) | predict s/tile on the GPU node, 11 workers | predict read s alone / shared |
|---|---|---|---|---|---|
| 3 km | 0.80 | 0.80 | 39 | 57 | 30 / 54 |
| 9 km | 8.55 | 8.85 | 91 | 93 | 61 / 64 |
| 10 km | 10.10 | 10.55 | 213 | 100 | 88 / 72 |
| 11 km | 11.25 | 11.60 | 152 | 111 | 121 / 80 |

112 composites segmented (12 large, 100 at 3 km) in 299 s while 22 tiles were predicted by 11 workers in 304 s; job cost 3.23 SU; node load average 42 on 48 cores; GPU utilisation 38 % because the SAM list was short relative to the predict list. The 10 km and 11 km solo predict runs were slower than the shared ones, so the shared numbers are not inflated by contention.

## 3. Cost model per national year (9 km grid, 15,968 tiles; 3 km, 99,465 tiles)

| configuration | SAM job wall s/tile | SAM SU | predict SU | presegment SU | total SU | note |
|---|---|---|---|---|---|---|
| 9 km, separate stages | 10.6 | 1,688 | 506 | 304 | **2,498** | the plan |
| 9 km, predict co-scheduled in the SAM job | 10.6 | 1,688 | 0 | 304 | **1,992** | wall = max(SAM, predict/11 workers) |
| 9 km, bands cached and reused (not feasible) | 10.6 | 1,688 | 506 | 100 | **2,294** | saves only the presegment read; needs a 22 TB cache |
| 3 km, separate stages | 1.2 | 1,223 | 1,333 | 345 | **2,901** | optimised 3 km, for reference |
| 3 km, predict co-scheduled | 5.2 | 5,145 | 0 | 345 | **5,490** | predict-bound: worse than separate |

## 4. Files

- `bench/read_split.py`, `bench/bench_readsplit.pbs` (jobs 178497628, 178498784); `bench/bench_fused.pbs` (job 178497626).
- Raw timings: `derived/benchksu/readsplit_p9.csv`, `readsplit_3km.csv`, `fused_sam/timings_segment_*.csv`, `fused_pred/p*_timings.csv`.

