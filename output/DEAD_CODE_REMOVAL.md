# Dead code removed after the 2024 9 km national map (2026-09-10)

Aggregate only. This lists what was taken out of `src/` once the 9 km 2024 map was built, and what
was kept even though nothing on the map's path calls it. Everything removed is still in git history.
Restore any file with `git checkout <commit-before-removal> -- <path>`.

## Rule used

A file was removed if it is a superseded code path, or a finished one-off experiment whose result is
already written up in a report. A file was kept if any of these hold:

- it is on the production path of the 9 km map (labels, model training, segmentation, prediction,
  merge, boundary de-duplication, the Earth Engine upload)
- it generated a result the current manuscript cites (ABS, WorldCereal and NLUM comparisons,
  label-quality tests, the hand review, regional stability, the phenology gate, Presto embeddings,
  yield calibration, the adopted classifier's validation)
- it belongs to open work (the Sentinel-1 / fj7 experiment, the multi-year cut repair)
- it is used by `run_map100.sh`, which produced the regional nine-season evidence

## Removed from `run_national.sh` (882 -> 449 lines)

The 3 km stages the 9 km pipeline replaced: `sam`, `predict`, `repair`, `repair-check`, `repair-sam`,
`audit`, `repredict` and `resam`. The 9 km path re-runs `presegment` and `sampredict` to resume
instead, and `sampredict` records every predicted tile in `done_stubs.txt`.

The file had two `predict)` labels. Bash runs the first match, so the real 3 km `predict` stage
(the second label) was unreachable, and `predict` ran a stale copy of an early SAM+predict block.

Added: `classified` (the classified-only "good polygons" file from the boundary output).

## Removed files (26)

| file | why |
|---|---|
| `repredict_new_model.sh` | 3 km re-predict of 2022-2024, prepared but never launched; superseded by the 9 km re-run |
| `submit_paddocks.sh` | early two-stage submit script, superseded by `run_national.sh` and `run_map100.sh` |
| `train_group3.pbs`, `train_targets.pbs` | superseded model trainings (first three-group model, species-level archive) |
| `train_group3_19index.pbs`, `index_arch_sweep.pbs` | finished index-selection experiments (`INDEX_ARCHITECTURE_SWEEP.md`); the adopted model is `train_group3_shipped_plus_sharma6.pbs` |
| `eval_sam_sweep.py`, `sam_sweep.pbs` | finished SAM parameter sweep |
| `sam_segment_pps.pbs`, `tile_size_bench.py`, `tile_size_bench2.py`, `subtile_aois.py` | finished tile-size and prompt-density benchmarks; the decision itself is `bench/geometry_*` (kept) |
| `overlap_test.pbs`, `overlap_test2.pbs`, `find_boundary_pairs.py` | one-shot tile-boundary diagnostics on the retired 3 km map (`PIPELINE_ARCHITECTURE_AND_TILING.md` sections 5-6) |
| `pilot_spatial_stability.pbs` | one-off stability pilot, superseded by `stability.pbs` |
| `zarr_pilot_extra.py` | zarr persistence pilot scaffolding, marked "not production code" |
| `compare_estimators.py` | early paddock-median vs corner-window CFI comparison |
| `crop_heatmap.py`, `sentinel_ndvi/paddock_heatmap.py` | early exploratory CFI heatmaps |
| `agriwebb_eval_sites_gpkg.py`, `agriwebb_holdout_group3.py` | AgriWebb holdout, dropped from the manuscript on 2026-09-10 |
| `sentinel_ndvi/flowering_timing.py`, `crop_specificity.py`, `plot_timeseries.py`, `verify_tree_mask.py` | early Stage-2 diagnostics (2026-08-07) |

## Kept although nothing in `src/` calls them (your call)

These are not on the map's path and have no caller, but may have produced figures or labels:

- `map_figures.py`, `map_table.py` (regional small multiples and the flattened attribute table)
- `stability_merge.pbs` (one-pass merge, rotation section and consensus layer)
- `chunk_sites.py` (splits the site list for parallel extraction)
- `canola_flowering_audit.py` (label diagnostic behind the hand review)
- `filter_sweep.py` (per-paddock filter against ABS, the evidence behind the area-accurate subset)
- `aggregate_review.py`, `sample_review.py`, `make_qgis_package.py`, `review_render.py` (early hand-review round)

## Fixes made in the same pass

- `run_national.sh merge` linked the SAM+predict outputs as `sp<k>_p_<batch>.gpkg`, which the
  `p*.gpkg` glob in `merge_national.pbs` and `abs_national.pbs` never matched. The first 9 km merge
  merged 0 chunks. Links are now `p_sp<k>_<batch>.gpkg`, and `merge_national.pbs` stops with an error
  when it finds no input.
- `abs_national.pbs`, `nlum_compare.py`, `worldcereal_compare.py` and `upload_national_crops_gee.sh`
  hardcoded the retired 3 km map. They now take the map as an argument or environment variable,
  defaulting to the old paths.
