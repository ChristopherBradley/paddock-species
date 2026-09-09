# Tile geometry for the national runs: 3 km production vs overlap vs 9 km, each predicted and merged

Generated 2026-09-09 by `src/paddocks/bench/geometry_report.py` from `geometry_decision.py` on the 6 x 6-tile Riverina block (grid r932-937, c1182-1187, 324.0 km2; metrics inside the 256.0 km2 interior, 1 km in from the block edge so no arm's outer boundary counts). Every arm was segmented with the adopted SAM settings (`--prompt-image-only --fp16`), predicted with the production model and gates, and merged with `merge_tile_boundaries.py` on its own lattice; the production arm is the actual 2024 national output for the same tiles, merged the same way. Aggregate only.

## 0. Decision

- **Recommended for a from-scratch re-run: `p9` — 9 km tiles, no overlap.** See §5 for why, and §6 for the commands.
- Cost per national year: 2,176 SU vs 2,476 SU for 3 km tiles at the same optimised settings (2024 as actually run: 6,623 SU).
- Edge artefacts after the merge: classified polygons with a raster-edge cut 0.155 vs 0.569; residual overlap 2.37 % vs 1.07 % of area; band density ratio 1.15 vs 1.04.
- Agreement with the merged production block: 75 % of production polygons have a match at IoU >= 0.5 (65 % at 0.7); class agrees on 92 % of matched pairs.

## 1. Arms

| arm | tiles | lattice | tile half-width | overlap with neighbours | national tiles | polygons before -> after merge | away views |
|---|---|---|---|---|---|---|---|
| prod_3km | 3 km tiles, no overlap (production 2022-2024) | 3 km lattice | 1.5 km | 0 | 99,465 | 752 -> 580 | 23 % |
| ov2000 | 4 km tiles on the 3 km lattice | 3 km lattice | 2.0 km | 1 km | 99,465 | 1,277 -> 694 | 63 % |
| ov2500 | 5 km tiles on the 3 km lattice | 3 km lattice | 2.5 km | 2 km | 99,465 | 1,779 -> 890 | 74 % |
| p9 | 9 km tiles, no overlap | 9 km lattice | 4.5 km | 0 | 15,968 | 633 -> 573 | 26 % |
| p9ov1000 | 10 km tiles on the 9 km lattice | 9 km lattice | 5.0 km | 1 km | 15,968 | 735 -> 648 | 41 % |
| p9ov2000 | 11 km tiles on the 9 km lattice | 9 km lattice | 5.5 km | 2 km | 15,968 | 897 -> 778 | 50 % |

## 2. Cost per national year

Per-tile seconds measured in this round (SAM: fp16 + image-only prompts, alone on a V100; presegment and predict on normalbw, all arms of a stage in the same time window so contention is shared), scaled to the national tile count of each lattice. Rates: gpuvolta 36 SU/h, normalbw 1.25 SU/h per tile-job.

| arm | presegment s/tile | SAM s/tile | predict s/tile | presegment SU | SAM SU | predict SU | **total SU / year** | vs 3 km optimised | vs 2024 as run |
|---|---|---|---|---|---|---|---|---|---|
| prod_3km | 10.0 | 0.80 | 38.6 | 345 | 796 | 1,335 | **2,476** | 100 % | 37 % |
| ov2000 | 13.5 | 2.10 | 35.5 | 466 | 2,089 | 1,224 | **3,779** | 153 % | 57 % |
| ov2500 | 19.4 | 2.90 | 62.5 | 670 | 2,884 | 2,160 | **5,714** | 231 % | 86 % |
| p9 | 54.9 | 8.55 | 91.3 | 305 | 1,365 | 506 | **2,176** | 88 % | 33 % |
| p9ov1000 | 86.7 | 10.10 | 212.6 | 481 | 1,613 | 1,179 | **3,273** | 132 % | 49 % |
| p9ov2000 | 69.0 | 11.25 | 152.2 | 383 | 1,796 | 844 | **3,023** | 122 % | 46 % |

## 3. Edge artefacts and product statistics after the merge (block interior)

| arm | polygons/km2 | classified/km2 | classified median ha | cut share (classified, >= 100 m on own raster edge) | band density ratio | residual overlap % | class conflicts | abstained area ha | classified area ha |
|---|---|---|---|---|---|---|---|---|---|
| prod_3km | 1.55 | 1.17 | 45.0 | 0.569 | 1.04 | 1.07 | 3 | 2,665 | 17,034 |
| ov2000 | 1.68 | 1.18 | 45.8 | 0.767 | 1.00 | 7.92 | 5 | 4,157 | 18,535 |
| ov2500 | 2.00 | 1.32 | 45.8 | 0.697 | 0.94 | 14.36 | 12 | 4,302 | 20,034 |
| p9 | 1.36 | 1.06 | 47.8 | 0.155 | 1.15 | 2.37 | 0 | 2,336 | 17,094 |
| p9ov1000 | 1.42 | 1.05 | 46.0 | 0.156 | 1.10 | 5.64 | 2 | 2,843 | 16,636 |
| p9ov2000 | 1.62 | 1.15 | 45.5 | 0.150 | 1.05 | 7.68 | 1 | 3,361 | 16,664 |

Area by class (ha, block interior):

| arm | Canola | Cereal | Legume |
|---|---|---|---|
| prod_3km | 2,525 | 13,554 | 956 |
| ov2000 | 3,287 | 14,033 | 1,215 |
| ov2500 | 3,773 | 15,066 | 1,195 |
| p9 | 3,383 | 12,742 | 970 |
| p9ov1000 | 3,568 | 12,183 | 885 |
| p9ov2000 | 3,574 | 11,748 | 1,343 |

Merge-rule variant: `--cover-min 0` (never rescue an away view; drop it even when the owning tile has no decided polygon there). This is the right rule when tiles overlap by more than a paddock width, because the owner then saw the ground whole; it is wrong for the 3 km production lattice, where the owner's view is often the truncated one.

| arm | rule | cut share (classified) | residual overlap % | classified/km2 | classified area ha | production matched >= 0.5 |
|---|---|---|---|---|---|---|
| prod_3km | rescue (default) | 0.569 | 1.07 | 1.17 | 17,034 | 1.000 |
| prod_3km | no rescue | 0.555 | 0.61 | 1.13 | 16,837 | 1.000 |
| ov2000 | rescue (default) | 0.767 | 7.92 | 1.18 | 18,535 | 0.719 |
| ov2000 | no rescue | 0.737 | 5.19 | 1.01 | 16,324 | 0.710 |
| ov2500 | rescue (default) | 0.697 | 14.36 | 1.32 | 20,034 | 0.756 |
| ov2500 | no rescue | 0.667 | 4.13 | 0.98 | 15,607 | 0.728 |
| p9 | rescue (default) | 0.155 | 2.37 | 1.06 | 17,094 | 0.746 |
| p9 | no rescue | 0.129 | 1.77 | 1.03 | 16,489 | 0.752 |
| p9ov1000 | rescue (default) | 0.156 | 5.64 | 1.05 | 16,636 | 0.709 |
| p9ov1000 | no rescue | 0.098 | 3.18 | 0.95 | 15,408 | 0.721 |
| p9ov2000 | rescue (default) | 0.150 | 7.68 | 1.15 | 16,664 | 0.722 |
| p9ov2000 | no rescue | 0.048 | 0.00 | 0.98 | 14,916 | 0.731 |

**Findings.**
- *Extra overlap on the 3 km lattice does not reduce edge artefacts and costs more.* With 1 km / 2 km overlap, 63 % / 74 % of polygons are away views; with real classes the merge cannot resolve most of the extra pairs (one side abstained, or two truncated views of a paddock wider than the overlap), so residual overlap is 7.92 % / 14.36 % of area (production 1.07 %) and the raster-edge cut share rises to 0.767 / 0.697 (production 0.569). Dropping every away view instead (no rescue) brings overlap to 5.19 % / 4.13 % but discards 4 % / 8 % of classified area. SAM time per tile rises from 0.80 to 2.10 / 2.90 s (more image in the canvas means more prompts and masks even with the prompt fix), so the year costs 153 % / 231 % of the optimised 3 km run.
- *9 km tiles are cheaper and cleaner.* Per tile the stages cost more, but there are 6 x fewer tiles and the per-tile overhead of the datacube query dominates presegment and predict: 2,176 SU per year (88 % of optimised 3 km, 33 % of 2024 as run) with a raster-edge cut share of 0.155 against 0.569, the same classified area (17,094 vs 17,034 ha) and no class conflicts left after the merge. The national 9 km grid has 15,968 parents rather than 99,465 / 9 because blocks at the cropping margin are partial; a mixed 3 km / 9 km grid for those margins would recover most of the difference but needs a two-lattice merge, not built.
- *Overlap on top of 9 km buys little under the default merge* (cut share 0.156 / 0.150, more residual overlap, 40-50 % more cost). With no rescue, 11 km tiles on the 9 km lattice reach a cut share of 0.048 and 0.00 % overlap, the cleanest geometry measured, but lose 12 % of classified area to dropped views the owner never segmented. That is the option if seam-free geometry matters more than coverage.
- *Agreement with production is the same for every candidate* (72-75 % of production polygons at IoU >= 0.5, 92 % class agreement on matches): any change to what SAM sees changes about a quarter of the boundaries. §5 looks at which side is right where they differ.

## 4. Agreement with the merged production block

| arm | production polygons matched at IoU >= 0.5 | >= 0.7 | median IoU | arm polygons matched at >= 0.5 | >= 0.7 | class agreement on matched pairs | unmatched: production / arm |
|---|---|---|---|---|---|---|---|
| prod_3km | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0 / 0 |
| ov2000 | 0.719 | 0.622 | 0.917 | 0.714 | 0.621 | 0.926 | 84 / 86 |
| ov2500 | 0.756 | 0.635 | 0.920 | 0.727 | 0.602 | 0.907 | 73 / 92 |
| p9 | 0.746 | 0.652 | 0.945 | 0.819 | 0.720 | 0.924 | 76 / 49 |
| p9ov1000 | 0.709 | 0.605 | 0.929 | 0.796 | 0.681 | 0.910 | 87 / 55 |
| p9ov2000 | 0.722 | 0.625 | 0.927 | 0.802 | 0.689 | 0.912 | 83 / 58 |

## 5. Where production and the recommended arm disagree: visual review

The 1.5 km cells with the most unmatched polygons (IoU < 0.5 in either direction) were rendered as [Sentinel-2 true colour | composite | production merged | p9 merged] (`figures/tile_geometry/disagree_p9.png`) and judged by eye against the imagery. Verdicts below are the model's reading of the images, not ground truth.

| window | what differs | verdict |
|---|---|---|
| p9_dis1 (1368750, -3848250) | Production splits the top-left paddock along the vertical 3 km line into a union (798) plus a separate fragment (446); 9 km has it as one polygon (220) bounded by the visible tracks. | **production fragment, 9 km right** |
| p9_dis2 (1359750, -3852750) | One large dark-green paddock is cut into four quadrants by the 3 km lattice cross in production (177/189/208/238), none unioned; 9 km has one polygon (133). | **production fragment, 9 km right** |
| p9_dis3 (1368750, -3849750) | Production's union at the lattice cross (797) is an irregular shape spanning three visible fields; 9 km gives rectangles that follow the roads (234/238/239/255). | **production fragment, 9 km right** |
| p9_dis4 (1367250, -3849750) | A block of small rectangular paddocks; both products draw them, with one small paddock merged with its neighbour in production (459) and split in 9 km (245/246). | **both plausible** |
| p9_dis5 (1361250, -3845250) | Same treed paddock in both (106 vs 40), near-identical outline; production calls it Legume, 9 km calls it Canola. Geometry agrees, the class does not. | **geometry both fine, class differs (undecidable here)** |
| p9_dis6 (1365750, -3846750) | A large pale-green paddock with scattered trees: production splits it at the horizontal line into a union (793) and a second polygon (790); 9 km holds it as one union across its own line (634). | **production fragment, 9 km right** |

The disagreements concentrate on production's 3 km lattice lines. In four of the six windows the production polygons are lattice-aligned fragments that the merge could not fully restore (the two views did not overlap enough, or one view was abstained), and the 9 km polygons follow the field boundaries visible in the true-colour scene. One window is a genuine draw and one is a class disagreement on the same geometry. Nothing in these windows looked like a paddock the 9 km tiling had broken or over-merged. At the block centre (`compare_p9_centre.png`, not selected for disagreement) the two products are close, with 61 vs 70 polygons and fewer fragments in the 9 km version.

## 6. What to run for the 2024 re-run

```
# 1. the 9 km grid from the 2024 3 km grid (15,968 parents; partial parents at the cropping margin keep their 3x3 block centre)
python grid9_from_2024.py --aois-2024 $D/national2024/aois.csv --year 2024 --out $D/national2024_9km/aois.csv
# 2. the normal stages, in their own directory (M override added to run_national.sh), NCHUNK ~ 60 so each predict job holds ~270 tiles
export M=$D/national2024_9km; YEAR=2024 NCHUNK=60 ./run_national.sh chunks
YEAR=2024 ./run_national.sh presegment      # normalbw 8 GB (presegment.pbs); 9 km composite RSS 1.8 GB
SAM_EXTRA="--prompt-image-only --fp16" YEAR=2024 ./run_national.sh sam     # ~8.6 s per 9 km tile on a V100
YEAR=2024 ./run_national.sh predict         # normalbw 8 GB (predict_tile.pbs); 9 km predict RSS 6.6 GB -- watch the first chunk
YEAR=2024 ./run_national.sh merge && YEAR=2024 ./run_national.sh boundary && YEAR=2024 ./run_national.sh summary
# 3. compare with the retired 3 km 2024 map after ITS boundary step: abs_compare.py on both, and bench/geometry_decision.py-style IoU matching
```

## 7. Files

- Figures: `figures/tile_geometry/` — `compare_*.png` (same windows, production merged vs p9 merged), `disagree_p9.png` (the review windows).
- Example GeoPackages (block interior, EPSG:3577, crops schema + merge provenance columns): `tile_geometry_examples/prod_3km_merged.gpkg` and `tile_geometry_examples/p9_merged.gpkg`; the unmerged inputs beside them as `*_before.gpkg`.
- Numbers: `derived/benchksu/decision/geometry_decision.json`; per-arm merge and audit outputs under `derived/benchksu/decision/<arm>/`.

