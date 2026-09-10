# Validating the 9 km pipeline before the 2024 re-run

Generated 2026-09-09 by `src/paddocks/bench/validation_report.py`. Both products were scored at the model's 543 fixed test trials (2023 and 2024; 533 fall on the tile lattice) with a temporal-holdout copy of the adopted classifier (`group3_map_sharma6_le2022.joblib`: same 153 features and flags, trained on 2017-2022 only), so the numbers are honest for both and directly comparable with the feature-level 0.890 macro F1 the model was adopted on. The site's polygon is the one containing it, preferring the tile whose lattice square holds the site. Aggregate only.

## 0. Verdict

- Macro F1 at the test sites: **0.898 (9 km, final pipeline) vs 0.885 (3 km production)**; balanced accuracy 0.900 vs 0.882; sites scored 349 vs 367 of 533 (no polygon 122 vs 94; abstained 62 vs 72).
- Polygon area vs the trial paddock area in the label set: median |log ratio| 0.020 vs 0.097; within a factor of 2: 91 % vs 80 % (polygon median 49.8 vs 45.5 ha; label median 57.2 ha).

## 1. Per-class precision, recall and F1 at the test sites

| product | year | n scored | class | n | precision | recall | F1 | macro F1 | balanced acc. | recall counting missing/abstained sites as misses |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 km production | 2023 | 193 | Canola | 45 | 0.833 | 0.889 | 0.860 | 0.869 | 0.870 | 0.571 |
| 3 km production | 2023 | 193 | Cereal | 102 | 0.961 | 0.961 | 0.961 |  |  | 0.726 |
| 3 km production | 2023 | 193 | Legume | 46 | 0.814 | 0.761 | 0.787 |  |  | 0.603 |
| 3 km production | 2024 | 174 | Canola | 50 | 0.938 | 0.900 | 0.918 | 0.907 | 0.900 | 0.529 |
| 3 km production | 2024 | 174 | Cereal | 97 | 0.920 | 0.948 | 0.934 |  |  | 0.672 |
| 3 km production | 2024 | 174 | Legume | 27 | 0.885 | 0.852 | 0.868 |  |  | 0.479 |
| 3 km production | pooled | 367 | Canola | 95 | 0.885 | 0.895 | 0.890 | 0.885 | 0.882 | 0.548 |
| 3 km production | pooled | 367 | Cereal | 199 | 0.941 | 0.955 | 0.948 |  |  | 0.699 |
| 3 km production | pooled | 367 | Legume | 73 | 0.841 | 0.795 | 0.817 |  |  | 0.547 |
| 9 km final | 2023 | 172 | Canola | 42 | 0.881 | 0.881 | 0.881 | 0.878 | 0.882 | 0.529 |
| 9 km final | 2023 | 172 | Cereal | 88 | 0.965 | 0.932 | 0.948 |  |  | 0.607 |
| 9 km final | 2023 | 172 | Legume | 42 | 0.778 | 0.833 | 0.805 |  |  | 0.603 |
| 9 km final | 2024 | 177 | Canola | 43 | 0.927 | 0.884 | 0.905 | 0.920 | 0.919 | 0.447 |
| 9 km final | 2024 | 177 | Cereal | 99 | 0.950 | 0.960 | 0.955 |  |  | 0.693 |
| 9 km final | 2024 | 177 | Legume | 35 | 0.889 | 0.914 | 0.901 |  |  | 0.667 |
| 9 km final | pooled | 349 | Canola | 85 | 0.904 | 0.882 | 0.893 | 0.898 | 0.900 | 0.484 |
| 9 km final | pooled | 349 | Cereal | 187 | 0.957 | 0.947 | 0.952 |  |  | 0.651 |
| 9 km final | pooled | 349 | Legume | 77 | 0.827 | 0.870 | 0.848 |  |  | 0.632 |

Confusion matrices (rows = label, columns = predicted; Canola, Cereal, Legume), pooled:

- 3 km production: [[85, 5, 5], [3, 190, 6], [8, 7, 58]]
- 9 km final: [[75, 3, 7], [3, 177, 7], [5, 5, 67]]

Abstention reasons at sites — 3 km: {'classified': 367, 'area_below_min': 25, 'no_crop_shape': 25, 'no_crop_signal': 16, 'unsegmented_blob': 6}; 9 km: {'classified': 349, 'no_crop_shape': 21, 'no_crop_signal': 19, 'area_below_min': 18, 'unsegmented_blob': 4}. Sites seen by more than one tile: 3 km 21, 9 km 17.

## 2. What the final configuration cost, per tile, in these runs

| job | exit | tiles | SU | wall | wall s / tile | SU / tile | predict s / tile (read, zonal) | zarr MB / tile | orchestrator line |
|---|---|---|---|---|---|---|---|---|---|
| val_sp9_2023 | -29 | 131 | 72.66 | 121 min | 55.5 | 0.5547 | 632 (219, 397) | 1.3 | None |
| val_sp9_2024 | 0 | 137 | 41.13 | 69 min | 30.0 | 0.3002 | 202 (188, 16) | 1.3 | ('4107', '0', '137', '0', '30.0') |
| sp_p9_3577 | 0 | 4 | 6.56 | 11 min | 164.0 | 1.6400 | 137 (123, 15) | 1.0 | ('650', '0', '4', '0', '162.5') |

Jobs with a non-zero exit (val_sp9_2023) are listed but excluded from the projection. `val_sp9_2023` hit its 2 h walltime with 64 of 131 tiles predicted; its `tiles` column counts the whole list because the remaining 67 were predicted afterwards by a CPU top-up job (`val_top9_2023`: `sampredict.pbs` with `ORCH_EXTRA=--no-sam` on normalbw, 4 workers). SAM had finished all 131 tiles at the normal 9 s/tile; the predict workers ran the zonal step at 482 s/tile (5 s per polygon) against 16 s/tile in the identical 2024 job. **Cause found and fixed (2026-09-09):** the zonal phase allocates large fresh arrays (astype/where/stack over the (t, y, x) cube); numpy 1.26 marks every large allocation MADV_HUGEPAGE and gadi runs transparent huge pages with defrag=madvise, so the kernel compacts memory synchronously on those faults, for a time that depends on the node's memory fragmentation. One 9 km tile, one core: zonal 41-396 s across nodes with the default, 22-25 s on three nodes with `NUMPY_MADVISE_HUGEPAGE=0`; user time identical (47-48 s), system time 32-80 s vs 7-11 s, and the kernel's compact_stall counter moving on the slow runs. Not the year (the profiled 2023 and 2024 tiles cost the same), not threads, not the cgroup limit (a 24 GB run was the slowest). Every PBS script and `segment_predict.py`'s worker environment now set the variable. The remaining 67 tiles of 2023 were predicted by a CPU top-up job (`val_top9_2023`, `sampredict.pbs` with `ORCH_EXTRA=--no-sam` on normalbw) and the 3 km arm the same way (`val_top3_*`) after two 1-core jobs hit a 4 h walltime at ~175 s per scattered tile with the GeoPackage unwritten.

**Projected national year (15,968 parents):** SAM+predict 5,401 SU (0.3382 SU per tile from the co-scheduled jobs, zarr on) + presegment 603 SU (109 s per tile on normalbw) = **6,003 SU**; zarr stores 0.02 TB per year. Merge/boundary/summary add a few SU. 2024 as actually run: 6,623 SU.

**Read this projection as an upper bound.** The site parents are scattered across the country, so the datacube read had no scene-cache locality: 188 s per tile here against 93 s on the contiguous 36-tile block in `FUSED_PREDICT_BENCHMARK.md`, which made the 2024 job predict-bound (30 s wall per tile) where the contiguous benchmark had SAM (10.6 s) covering predict/11 (8.5 s). The 4-tile block arm is start-up dominated. On the real 9 km grid the contiguous-tile figures apply: about 2,000 SU for SAM+predict and 2,500 SU for the year, now that the zonal stall above is fixed; a like-for-like re-measurement with the fix is the gate before the 2024 re-run.

## 3. Edge artefacts in the final configuration (Riverina block, after the merge)

| product | polygons/km2 | classified median ha | cut share (classified) | band density ratio | residual overlap % | class conflicts | classified area ha | production polygons matched at IoU >= 0.5 |
|---|---|---|---|---|---|---|---|---|
| 3 km production | 1.55 | 45.0 | 0.569 | 1.04 | 1.07 | 3 | 17,034 | 1.000 |
| 9 km, EPSG:6933 (decision report) | 1.36 | 47.8 | 0.155 | 1.15 | 2.37 | 0 | 17,094 | 0.746 |
| 9 km, EPSG:3577 + 350 m buffer (final) | 1.28 | 49.2 | 0.166 | 1.08 | 0.91 | 0 | 16,018 | 0.712 |

## 5. Files

- Per-site results (SENSITIVE, derived only): `benchksu/validation/eval{3,9}_*_sites_SENSITIVE.csv`; aggregate JSON beside them.
- Pipeline pieces validated here: `samgeo_segment.py presegment --output-crs EPSG:3577`, `grid9_from_2024.py --half-m 4850`, `segment_predict.py` + `sampredict.pbs`, `run_national.sh sampredict`, `eval_map_at_sites.py`.

