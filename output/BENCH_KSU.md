# Reducing the SU cost of a national year, and whether bigger tiles or more overlap buy fewer edge artefacts

Generated 2026-09-09 by `src/paddocks/bench/bench_report.py` from `bench_eval.py` and `tilesize_eval.py` outputs on one Riverina block (10 x 10 production tiles at grid r932-941, c1182-1191; everything measured on gadi from real PBS epilogues). Aggregate only.

## 0. Where a national year's SU goes today (2024, measured)

| stage | SU | share | queue / request | billed as |
|---|---|---|---|---|
| presegment (incl. repair) | 912 | 14 % | normal, 1 CPU, 4 GB | 1 core: 2.0 SU/h |
| SAM (incl. repair) | 4,126 | 62 % | gpuvolta, 1 V100 + 12 CPUs | 36 SU/h |
| predict (incl. gap) | 1,578 | 24 % | normal, 1 CPU, 8 GB | 2 cores: 4.0 SU/h |
| total | 6,623 | | | |

The shelterbelts lessons (`GADI_MEMORY_QUEUE_COSTS.md`) that apply here: memory is billed as cores (`SU/h = max(ncpus, mem/mem_per_core) x rate`), so predict's 8 GB on `normal` costs 4 SU/h; `normalbw` bills 8 GB as one core at 1.25 SU/h and `normalsl` 6 GB as one core at 1.5 SU/h; and the epilogue's "Memory Used" is page cache pinned at the request, so only sampled RSS says what a job needs.

## 1. CPU stages: queue and memory arms (same tiles, same code)

### presegment, 60 tiles of 2021 (no composite existed)

| arm | exit | SU | wall | SU/h | tiles | median s/tile | SU/tile | Memory Used / req | RSS peak | national SU |
|---|---|---|---|---|---|---|---|---|---|---|
| normal 4 GB (production) | 0 | 0.44 | 13 min | 1.99 | 60 | 9.9 | 0.0073 | 4.0 / 4 GB | 0.46 GB | 726 |
| normalbw 8 GB | 0 | 0.27 | 13 min | 1.23 | 60 | 10.0 | 0.0045 | 7.0 / 8 GB | 0.48 GB | 448 |
| normalsl 6 GB | 0 | 0.33 | 13 min | 1.50 | 60 | 11.0 | 0.0055 | 6.0 / 6 GB | 0.47 GB | 547 |

### predict, 40 tiles of 2022 (segmented, unpredicted; production model and gates, zarr on)

| arm | exit | SU | wall | SU/h | tiles | median s/tile | SU/tile | Memory Used / req | RSS peak | national SU |
|---|---|---|---|---|---|---|---|---|---|---|
| normal 8 GB (production) | 0 | 1.64 | 25 min | 3.99 | 40 | 27.4 | 0.0410 | 8.0 / 8 GB | 1.02 GB | 4,078 |
| normalbw 8 GB | 0 | 0.54 | 26 min | 1.25 | 40 | 36.2 | 0.0135 | 8.0 / 8 GB | 1.05 GB | 1,343 |
| normalsl 6 GB | 0 | 0.79 | 31 min | 1.51 | 40 | 35.4 | 0.0198 | 6.0 / 6 GB | 1.11 GB | 1,969 |
| normalbw 4 GB | 0 | 0.54 | 26 min | 1.24 | 40 | 31.8 | 0.0135 | 4.0 / 4 GB | 1.11 GB | 1,343 |

**Findings.** Both CPU stages are I/O-bound (datacube reads) and tiny in memory: presegment's process RSS peaks at 0.46 GB and predict's at 1.02 GB, while the epilogue reports the full request as "used" in every arm (page cache). Walltime is the same on every queue for presegment and within 6 % for predict, so the bill is just the queue rate: presegment 0.27 vs 0.44 SU on normalbw vs normal for the same 60 tiles, predict 0.54 vs 1.64 SU for the same 40 tiles, and normalbw at 4 GB costs the same as at 8 GB (0.54 SU) because both bill as one core. Outputs were diffed: all 60 composites are bit-identical on normalbw and normalsl, and all 713 predicted polygons have identical geometry, class, abstain reason, probabilities and yield on every queue (no AVX-512 effect in this code path).

## 2. SAM: throughput arms on the same 100 composites

| arm | exit | SU | wall | tiles | median segment s | GPU util mean / p90 | GPU mem max | SU/tile | national SU | production polygons matched at IoU >= 0.9 |
|---|---|---|---|---|---|---|---|---|---|---|
| production settings, 1 process | 0 | 3.67 | 6 min | 100 | 3.0 | 54 / 99 % | 6,662 MB | 0.0367 | 3,650 | 1.000 (2,467 vs 2,467 polygons) |
| 3 processes on one GPU | 0 | 3.44 | 6 min | 100 | 8.8 | 82 / 100 % | 19,978 MB | 0.0344 | 3,422 | 1.000 (2,467 vs 2,467 polygons) |
| fp16 autocast, 1 process | 0 | 2.79 | 5 min | 100 | 2.2 | 43 / 70 % | 7,202 MB | 0.0279 | 2,775 | 0.996 (2,463 vs 2,467 polygons) |
| points_per_batch 256, 1 process | 0 | 3.57 | 6 min | 100 | 2.9 | 53 / 100 % | 16,904 MB | 0.0357 | 3,551 | 1.000 (2,467 vs 2,467 polygons) |
| prompts on the image only (272 of 1024), 1 process | 0 | 2.24 | 4 min | 100 | 1.2 | 39 / 99 % | 6,662 MB | 0.0224 | 2,228 | 1.000 (2,467 vs 2,467 polygons) |
| image-only prompts + fp16 | 0 | 1.38 | 2 min | 100 | 0.8 | 29 / 73 % | 7,202 MB | 0.0138 | 1,373 | 0.996 (2,463 vs 2,467 polygons) |

**Findings.** Production SAM keeps the V100 only 54 % busy on average, but sharing the GPU between three processes raises utilisation to 82 % while tripling each process's time per tile, for a net gain of only 1.07x: without CUDA MPS the kernels are time-sliced, not overlapped, and the idle share is the CPU-side mask post-processing between kernels, which does not parallelise across processes on one GPU. points_per_batch 256 changes nothing. fp16 autocast cuts the per-tile time from 3.0 to 2.2 s with 99.6 % of production polygons reproduced at IoU >= 0.9. The largest single waste is structural: samgeo reads each 3 km composite (351 x 316 px) into a 768 px canvas of zero padding and SAM prompts the padding too, so 752 of the 1,024 prompt points decode nothing; restricting the grid to the image (`--prompt-image-only`) brings the per-tile time to 1.2 s (0.8 s with fp16) at 100.0 % / 99.6 % of production polygons reproduced at IoU >= 0.9.

## 3. Bigger tiles and more overlap: same paddocks?

Block of 324.0 km2; metrics inside the 256.0 km2 interior (1 km margin, so the big tiles' outer edges do not count). Reference = production 3 km tiles (2024). `prod->arm` = share of production polygons that have an arm polygon at IoU >= 0.5 / 0.7; `band ratio` = polygon density within 500 m of the arm's own lattice lines divided by density elsewhere (1.0 = no edge signature); `cut share` = polygons with >= 100 m of boundary on their own raster edge.

| arm | polygons/km2 | median ha | prod->arm IoU median | matched >= 0.5 | >= 0.7 | arm->prod IoU | band ratio | band / interior median ha | cut share | SAM s per km2 raster | raw -> kept |
|---|---|---|---|---|---|---|---|---|---|---|---|
| prod_3km | 2.14 | 30.4 | 1.000 | 1.000 | 1.000 | 1.000 | 1.51 | 29.1 / 45.0 | 0.600 | 0.271 | — -> — |
| ts_ov1750 | 2.80 | 30.1 | 0.733 | 0.704 | 0.537 | 0.671 | 2.07 | 29.9 / 34.3 | 0.532 | 0.400 | 6,883 -> 989 |
| ts_ov2000 | 3.61 | 30.4 | 0.667 | 0.653 | 0.481 | 0.609 | 1.44 | 31.2 / 21.8 | 0.490 | 0.549 | 8,641 -> 1,275 |
| ts_p9_default | 1.57 | 39.4 | 0.656 | 0.590 | 0.468 | 0.888 | 1.51 | 31.6 / 44.7 | 0.135 | 0.244 | 4,148 -> 632 |
| ts_p9_s352 | 1.63 | 34.2 | 0.607 | 0.565 | 0.448 | 0.838 | 1.46 | 26.6 / 41.0 | 0.100 | 0.406 | 4,213 -> 651 |
| ts_p9_s768 | 1.45 | 43.8 | 0.604 | 0.574 | 0.433 | 0.871 | 1.47 | 37.9 / 47.4 | 0.110 | 0.135 | 3,534 -> 575 |
| ts_p9_s768_pps42 | 1.52 | 40.3 | 0.645 | 0.596 | 0.455 | 0.881 | 1.45 | 36.3 / 45.3 | 0.111 | 0.204 | 3,879 -> 612 |
| ts_p9_nobatch_pps40 | 0.49 | 73.4 | 0.000 | 0.161 | 0.115 | 0.690 | 1.57 | 48.9 / 85.1 | 0.184 | 0.043 | 706 -> 194 |
| ts_p18_default | 1.39 | 41.8 | 0.637 | 0.580 | 0.464 | 0.911 | — | — / — | 0.000 | 0.132 | 3,525 -> 601 |
| ts_p18_s768 | 1.23 | 45.4 | 0.548 | 0.537 | 0.411 | 0.901 | — | — / — | 0.000 | 0.073 | 3,700 -> 532 |

After the merge (segmentation-only harness: every polygon the same class, so the rules act on geometry):

| arm | polygons before -> after | overlap ha before -> after | polygons/km2 | median ha | prod->arm matched >= 0.5 | band ratio | cut share | raster_cut >= 100 m |
|---|---|---|---|---|---|---|---|---|
| merged_prod_3km | 752 -> 560 | 4,108 -> 95 | 1.48 | 38.8 | 0.762 | 1.01 | 0.405 | 313 |
| merged_ts_ov1750 | 989 -> 600 | 14,794 -> 737 | 1.50 | 40.9 | 0.598 | 1.08 | 0.242 | 373 |
| merged_ts_ov2000 | 1,275 -> 656 | 31,255 -> 1,189 | 1.59 | 36.5 | 0.585 | 0.95 | 0.162 | 413 |

**Findings.**
- *Bigger tiles give the merged product's population, not its polygons.* 9 km and 18 km tiles land at 1.57 and 1.39 polygons/km2 with medians of 39 and 42 ha, close to the merged 3 km product (1.48 /km2, 39 ha) and far from raw 3 km (2.14 /km2, 30 ha). But only 59 % / 58 % of production polygons are reproduced at IoU >= 0.5, against 76 % for the merge alone and ~75 % at IoU >= 0.7 for the same pipeline year-to-year (TILE_BOUNDARY_MERGE.md sec 4). SAM sees a different canvas (real context instead of zero padding around every 3 km tile) and draws different boundaries. A re-segmentation at a new tile size is a different product, not the current one with fewer seams.
- *The SAM saving from bigger tiles is modest unless the window grows too.* Per km2 of raster, 9 km tiles with samgeo's default 512 px windows cost 0.244 s vs 0.271 s for 3 km tiles (10 % less); 768 px windows halve it again (0.135 s) at a further loss of agreement (57 % matched); one pass over the whole tile (0.49 /km2, 73 ha) under-segments badly and is not an option. Presegment and predict per km2 fall with tile size because their cost is per-tile overhead (datacube query), but predict's memory grows with the tile: predict peaks at 6.6 GB RSS on a 9 km tile and 24.8 GB on 18 km (sec 6), because predict_tile.py holds the tile's whole year of 10-band imagery in memory.
- *Overlap works, through the merge.* 4 km tiles on the 3 km lattice (1 km overlap each side) leave 44 % extra density in the band before the merge and 0.95 after it, and cut the post-merge share of polygons with a raster-edge boundary from 0.405 to 0.162 (500 m overlap: 0.242). The price is SAM time: 0.549 s/km2 vs 0.271 for 3 km tiles, because the bigger image fills more of the canvas and SAM decodes more prompts and more masks per tile. That cost is exactly what the image-only prompt grid removes for 3 km tiles, so the two should be re-measured together before an overlap is adopted. Overlap tiles also change the polygons (58 % of production reproduced at IoU >= 0.5 after the merge).

## 4. Projection: SU per national year

The benchmark arms ran ten datacube jobs at once (plus another project's), so their absolute seconds per tile are 2-3x slower than the 2024 production run; the arms of one stage ran in the same window, so their RATIOS are fair. Each stage's measured 2024 cost is therefore scaled by the arm's (SU/h) x (walltime) ratio to the production arm of the same stage. SAM arms ran alone on a GPU each, so their ratio is SU per tile.

| configuration | presegment | SAM | predict | total | vs 2024 |
|---|---|---|---|---|---|
| 2024 as run (normal 4 GB / gpuvolta / normal 8 GB) | 912 | 4,126 | 1,578 | 6,617 | 100 % |
| presegment on bw8 only | 558 | 4,126 | 1,578 | 6,263 | 95 % |
| presegment on sl6 only | 686 | 4,126 | 1,578 | 6,390 | 96 % |
| predict on bw8 only | 912 | 4,126 | 522 | 5,560 | 84 % |
| predict on sl6 only | 912 | 4,126 | 762 | 5,801 | 88 % |
| predict on bw4 only | 912 | 4,126 | 518 | 5,556 | 84 % |
| SAM w3 only | 912 | 3,868 | 1,578 | 6,358 | 96 % |
| SAM fp16 only | 912 | 3,137 | 1,578 | 5,627 | 85 % |
| SAM ppb256 only | 912 | 4,014 | 1,578 | 6,504 | 98 % |
| SAM grid only | 912 | 2,519 | 1,578 | 5,009 | 76 % |
| SAM grid_fp16 only | 912 | 1,552 | 1,578 | 4,042 | 61 % |
| all three: ps2021_bw8, sam_grid_fp16, pred_bw4 | 558 | 1,552 | 518 | 2,628 | 40 % |

## 5. Should existing years be re-segmented?

- **Cost.** The queue and SAM changes above apply to any tile size, so the per-year cost falls the same way whether or not the tiling changes; re-segmenting a year costs one full year at the new rate (presegment + SAM + predict), and the 2023/2024 re-predict already planned reuses the existing segmentation at predict cost only.
- **Benefit.** After the merge the 3 km product double-counts 0.7 % of area and ~20 % of classified polygons carry a genuine raster-edge cut (TILE_BOUNDARY_MERGE.md). 9 km tiles have 3x less outer edge per km2 (0.44 vs 1.33 km/km2), 18 km 6x less, and a 1 km overlap on the current lattice removes 60 % of the residual cut signature through the merge. None of these reproduces the current polygons: 58-60 % agreement at IoU >= 0.5 vs 76 % for the merge alone.
- **Memory.** predict peaks at 6.6 GB RSS on a 9 km tile (an 8 GB normalbw request, one core) and 24.8 GB on an 18 km tile (a 32 GB request, billed as 3.5 cores at 4.4 SU/h): 18 km tiles would need predict_tile.py rewritten to stream the year in chunks before they are usable at all.
- **Recommendation.** (1) Switch presegment and predict to normalbw and SAM to the image-only prompt grid now (done in this commit: `presegment.pbs`, `predict_tile.pbs`, `boundary_national.pbs` on normalbw; `run_national.sh` passes `--prompt-image-only` by default): bit-identical composites and predictions, identical polygons, and a national year at 54 % of the 2024 cost. Add `SAM_EXTRA="--prompt-image-only --fp16"` per year if 99.6 % identical polygons is acceptable: 40 %. (2) Do not re-segment past years for the sake of tile edges: the merge already removes the duplication, the remaining cuts are flagged, and a new tile size changes ~40 % of paddock boundaries, which would break the multi-year consensus (OFFSET_GRID_PILOT.md) more than the seams do. (3) If a future product is allowed to differ from the 2017-2025 series, 9 km tiles with default windows are the sensible size: 3x fewer edges, similar population statistics, ~10 % cheaper SAM per km2, modest predict memory. Validate the classifier on the labelled sites with 9 km polygons before committing, because every paddock-median feature is computed on polygons that would differ.

## 6. Feasibility rows: predict on 9 km and 18 km tiles

| tile | exit | SU | wall | Memory Used / req | RSS peak | tiles | median s/tile |
|---|---|---|---|---|---|---|---|
| 9 km (4 tiles) | 0 | 0.24 | 12 min | 8.0 / 8 GB | 6.63 GB | 4 | 172 |
| 18 km (1 tile) | 0 | 0.81 | 11 min | 32.0 / 32 GB | 24.78 GB | 1 | 636 |

Raw benchmark rates for the record (SU per tile x 99,465, no scaling): presegment ps2021_normal4 726, ps2021_bw8 448, ps2021_sl6 547; predict pred_normal8 4,078, pred_bw8 1,343, pred_sl6 1,969, pred_bw4 1,343; SAM sam_base 3,650, sam_w3 3,422, sam_fp16 2,775, sam_ppb256 3,551, sam_grid 2,228, sam_grid_fp16 1,373.

## 7. Figures and files

- `figures/bench_ksu/cmp_merged_prod_3km.png`, `cmp_merged_ov2000.png`, `cmp_p9_default.png`, `cmp_p18_default.png` — one 6 km window at the block centre (a lattice corner): production 3 km raw (middle) against each arm (right), over the composite with the 3 km lattice and raster footprints drawn.
- Harness: `src/paddocks/bench/` (`make_aois.py`, `bench_presegment.pbs`, `bench_predict.pbs`, `bench_sam.pbs`, `memsample.sh`, `bench_eval.py`, `tilesize_eval.py`, `bench_report.py`); segment-stage knobs `--sample-size --bound --no-batch --points-per-batch --fp16 --prompt-image-only` in `samgeo_segment.py`.
- Data: `/scratch/xe2/cb8590/paddock-species-data/derived/benchksu/` (AOI lists, per-arm outputs, PBS job ids in `jobs.txt`, `bench_summary.json`, `tilesize_eval.json`). Total benchmark cost: 25 jobs, ~32 SU.
- Verified after the 100-tile arms: the production code path rebuilds the prompt grid per composite; on 10 further tiles (job 178481584, grid r942-943) all 298 polygons are identical to production at IoU >= 0.9, 1.3 s per tile.
