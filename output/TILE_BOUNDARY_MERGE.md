# Tile-boundary artefacts in the national crop map: what they are, and a post-hoc merge that removes them

Generated 2026-09-08 by `src/paddocks/tile_boundary_report.py` from the outputs of `merge_tile_boundaries.py`, `boundary_seam_audit.py`, `cut_continuity.py`, `cross_year_check.py` and `repair_cuts_multiyear.py` on the Riverina 60 km test box (EPSG:3577 x 1,347,106-1,407,106, y -3,891,681 to -3,831,681; the same box as PIPELINE_ARCHITECTURE_AND_TILING.md §5). Everything here ran on the gadi login node in seconds to minutes; no PBS job was submitted and no GPU was used. Aggregate only.

## 0. Summary

- **The artefact is duplication, not a cut at the lattice line.** Each 3 km tile's raster is the EPSG:6933 bounding box of its rotated Albers square, so neighbouring rasters overlap by ~350-700 m and every paddock in that band is segmented and classified by both tiles. In the box, 6,871 of 10,304 polygons (67 %) extend past their own lattice square (max 353 m), 2,431 (23.6 %) have their centroid outside it, and 15.6 % of the summed polygon area is counted twice. SAM's polygons stop 2 px inside their own raster; nothing is cut at a neighbour's edge or at the lattice line (§1, `figures/tile_boundary_merge/raw_sam_edge_histogram.png`). PIPELINE_ARCHITECTURE_AND_TILING.md §4 said "no overlap"; it has been corrected.
- **A post-hoc merge on the merged GeoPackage removes it.** `merge_tile_boundaries.py` (rules in §2) takes the box from 10,304 to 7,278 polygons and double-counted area from 52,590 ha (15.6 %) to 2,082 ha (0.73 %), in 38 s. 1,004 whole paddocks are rebuilt from 2,078 cross-tile views; 71 class disagreements between two views of one paddock are reconciled by area-weighted probabilities and flagged; 19 confident disagreements are kept and flagged. Similar numbers on 2023 and on the offset-grid 2024 pilot (§3).
- **What remains is a view cut at its own raster edge whose twin the other tile never produced.** After the merge 2,120 classified polygons (37 %) still have >= 100 m of boundary along their raster edge, but an image test on the neighbour's composite says only about half of those are genuine cuts (971, 46 %); the rest are real fences that happen to lie within 30 m of the edge (§4). Genuine cuts concentrate in untouched and rescued polygons (84 % and 92 % genuine) and are rare on union products (22 %).
- **Those residual cuts are repairable from a second view of the same ground, and the repair is precise.** Re-cutting the merge's own 609 union polygons at their larger fragment's raster edge and repairing them from the offset-grid 2024 map restores 65 % of them at median IoU 0.993 against the known whole paddock (from 0.818 cut), 94 % >= 0.9 and none <= 0.7; the 2023 map as donor restores 44 % at median IoU 0.991 (§5). Applied for real, the two donors together repair 178 polygons (+2,214 ha; offset grid 131, 2023 47). Most residual cuts recur every year because the same neighbouring tile fails on the same paddock, so a same-year second view is worth more than more years.
- **Recommendation.** Run the merge (`run_national.sh boundary`, one small CPU job per year, §6) on every year as soon as it is merged; treat `raster_cut_m` and `class_conflict` as quality flags in the product; use the multi-view repair as an optional second pass once a second view exists for a year, preferring a same-year offset-grid segmentation over another year. Do not change the tiling or re-segment.

## 1. What the tiles actually do

`samgeo_segment.build_image` asks the datacube for an exact 3 km square in EPSG:3577 but for the raster in `output_crs="EPSG:6933"` (`samgeo_segment.py:177-180`). The square is rotated ~6.6° in EPSG:6933 at Riverina longitudes, and datacube fills the whole bounding box of the rotated square: every composite is 351 x 316 px at 10 m (11.1 km² instead of 9.0). The raster edge is a line tilted 6.6° that touches the lattice square at one corner and is ~350 m outside it at the other, so adjacent rasters overlap in a wedge-shaped band 350-700 m wide. The composites are clean across that band: the mean image gradient at the columns and rows where a neighbour's raster edge falls is at chance (fraction of those lines in a tile's top 1 % of gradient columns: 0.032, chance 0.03; 1,741 lines over the box's tiles).

Where the raw SAM polygons end is measured directly from `_segment.gpkg` in pixel space (`figures/tile_boundary_merge/raw_sam_edge_histogram.png`, 40 tiles): vertical boundary points per column spike 25x at column 2 and at column 350 of a 351-px raster and show no excess at columns 37-39 and 313-316, where the neighbours' raster edges fall. SAM's masks stop 2 px (~20 m) inside the image; nothing about the neighbouring tile is visible to it. So a paddock straddling a lattice line is normally seen by BOTH tiles, each view cut ~20 m inside that tile's own raster edge (170-350 m past the line), and the two views overlap by the width of the band.

| Riverina box, 2024 | value |
|---|---|
| polygons | 10,304 (8,150 cleanly classified) |
| extend past their own lattice square | 6,871 (66.7 %), max 353 m |
| centroid outside their own square ("away" views) | 2,431 (23.6 %) |
| cross-tile overlapping pairs | 4,591 |
| pairwise overlap area | 52,590 ha = 15.6 % of summed polygon area (45,293 ha between classified polygons) |
| classified polygons with >= 100 m of boundary within 30 m of their own raster edge | 4,664 (57 %) |

The earlier bbox statistic in PIPELINE_ARCHITECTURE_AND_TILING.md §5 (polygons whose bounding box touches a lattice line, 7 % at 10 m) measured the wrong thing: the artefact is not at the lattice line. It grows linearly with tolerance at the background rate of real boundaries near any line.

## 2. The merge rule set (`merge_tile_boundaries.py`)

The lattice square of each tile is its **core**; a tile is authoritative on its own core because it saw that ground furthest from its raster edge. All thresholds are CLI arguments; defaults are what was run here.

- **D1 ownership.** A polygon whose centroid lies outside its own tile's core is an *away* view of ground another tile owns.
- **D2 coverage.** An away polygon is dropped as a duplicate if >= 95 % of its area is covered by the owning tile's own polygons that decided on that ground (classified or `no_crop_signal`); if 50-95 % covered and both views are classified with the same or a reconcilable class it is unioned into its twin (the covering polygon with the largest intersection), adding the ground the owner missed; below 50 % it is *rescued* and kept, because the home tile has no claim there.
- **D3 conflict.** When a dropped or unioned view and its twin disagree in class, the twin's class is reconciled by the area-weighted mean of (p_canola, p_cereal, p_legume) and `class_conflict=1` is written with `pre_merge_classes`.
- **M1 union.** Two kept classified polygons from different tiles that still overlap by >= 50 % of the smaller are two truncated views of one paddock wider than the band: they are unioned if the union is one polygon <= 300 ha with compactness P/sqrt(A) <= 8 (the pipeline's own filters) and the classes are the same or reconcilable (the area-weighted winner is one of the two and both give it >= 0.25). Confident disagreements are kept and flagged. Connected components merge together (cap 4 fragments).
- **M2 clip.** Whatever still overlaps after D1-M1 (boundary-disagreement slivers, pairs with an abstained member) is assigned by ownership: the overlap stays with the polygon whose tile owns the square it lies in and is subtracted from the other, provided it is <= 50 % of the loser and the loser stays one polygon (crumbs < 0.5 ha discarded). Overlaps that fail those tests are left and counted.
- **Provenance.** Every touched row carries `boundary_action` (`absorbed`, `absorbed_union`, `rescued`, `union`, `+clipped`), `merged_from` (tile:idx of every source view), `merge_n`, `class_conflict`, `pre_merge_classes`, `clip_ha`; every row carries `raster_cut_m`, the length of its boundary within 30 m of its own tile's raster edge(s). Untouched rows are byte-identical to the input apart from the new columns. The input is never modified.

## 3. What the merge does on the box

| | 2024 | 2023 | 2024 offset-grid pilot |
|---|---|---|---|
| polygons before -> after | 10,304 -> 7,278 | 10,034 -> 7,465 | 11,047 -> 7,781 |
| away views: dropped duplicate / unioned into twin / dropped partial / rescued | 897 / 710 / 345 / 479 | 845 / 488 / 511 / 528 | 1029 / 751 / 368 / 540 |
| M1: kept-kept pairs unioned -> whole paddocks | 1,074 -> 1,004 | 725 -> 679 | 1,118 -> 1,041 |
| pairwise overlap before -> after D1-M1 -> after M2 (ha) | 52,590 -> 11,853 -> 2,123 | 48,350 -> 14,580 -> 4,117 | 56,821 -> — -> 2,604 |
| M2 slivers clipped (polygons, ha) | 966, 9,773 | — , 10,522 | — |
| overlap as % of summed area, before -> after (independent audit) | 15.6 -> 0.73 | 15.2 -> 1.51 | — |

2024 detail: 4,030 rows deleted, 2,471 updated, 1,004 union rows inserted. M1 reasons: {'same_class': 1051, 'sliver_below_ovl_min': 1024, 'not_both_classified': 264, 'class_conflict_reconciled': 23, 'conflict_confident_disagreement': 19, 'union_over_max_area': 3, 'union_over_max_compactness': 3}. Union sizes: {'2': 639, '3': 310, '4': 51, '5': 4} fragments per paddock, median union 49 ha. Class conflicts reconciled on duplicates: 48; on unions: 23; kept as confident disagreements: 19 pairs. Exclusive ground discarded with dropped partial views: 297 ha classified. Remaining overlap after M2: 381 pairs, mostly {'overlap_not_a_sliver': 176, 'would_split_polygon': 34}.

Figures (all Riverina 2024; left = Fourier-of-NDWI composite SAM saw, middle = before, right = after; white dashed = 3 km lattice, yellow = each tile's actual raster footprint, so the overlap band is visible):
- `figures/tile_boundary_merge/overview.png` — two 6 km windows around a lattice corner: the double layer of away views along every line before, a continuous paddock pattern after.
- `figures/tile_boundary_merge/known.png` and `figures/tile_boundary_merge/zoom13.png` — the four §6 split pairs from PIPELINE_ARCHITECTURE_AND_TILING.md (known-answer cases; see §7 below).
- `figures/tile_boundary_merge/m1_merge.png`, `figures/tile_boundary_merge/drop_dup.png`, `figures/tile_boundary_merge/union_twin.png`, `figures/tile_boundary_merge/drop_partial.png`, `figures/tile_boundary_merge/rescue.png`, `figures/tile_boundary_merge/conflict.png`, `figures/tile_boundary_merge/clip.png` — three seeded random examples of each decision.
- `figures/tile_boundary_merge/residual.png` — residual raster-edge cuts after the merge (§4). `figures/tile_boundary_merge/repaired.png` — multi-view repairs (§5).
- `figures/tile_boundary_merge/E_composite.png` — one tile's composite with the neighbour's raster edge drawn on it: no seam.

## 4. What is left: cuts whose twin never existed, and how to tell them from real fences

After D1-M2 a polygon can still end at its own raster edge. That happens when the neighbouring tile produced no kept polygon for the ground beyond the cut (SAM there merged it into a compactness-rejected blob, or into a different paddock, or the view abstained), which is exactly the failure PIPELINE_ARCHITECTURE_AND_TILING.md §6 found when it widened the window. A straight edge within 30 m of the raster edge is however not proof of a cut: a real fence or road can lie there. Two measurements separate them.

**Image continuity (`cut_continuity.py`).** The neighbour's composite covers both sides of the cut, so the 3-band values 15-60 m inside the polygon along the cut are compared with 15-60 m beyond it, from the same composite (each tile has its own stretch): score = mean |mu_in - mu_out| / pooled sd. Calibrated on two sets the merge itself provides: fragments the merge unioned (known same field beyond the cut, n=400) and interior polygons' real boundaries (n=400).

| set | 10 % | 25 % | median | 75 % | 90 % |
|---|---|---|---|---|---|
| same field beyond the cut (known genuine cuts) | 0.15 | 0.22 | 0.36 | 0.54 | 0.84 |
| real boundary | 0.33 | 0.58 | 0.90 | 1.32 | 1.62 |
| residual raster-edge polygons after the merge (n=2,118) | 0.20 | 0.36 | 0.69 | 1.28 | 1.92 |

Equal-error threshold 0.61 (error 22 % each way: 82 % of known cuts score as continuous, 74 % of real boundaries as boundaries). The residual set is a mixture: 971 of 2,118 (46 %) score as genuine cuts, and the split by what the merge did to the polygon is telling — genuine among untouched 84 %, rescued 92 %, absorbed 46 %, absorbed+union 20 %, union 22 %. Union products are whole paddocks whose residual straight edge is a real boundary near the raster edge; untouched and rescued polygons are the cuts the merge could not fix because there was nothing to fix them with.

**Cross-year geometry (`cross_year_check.py`).** Segmentation is independent each year on the same lattice, so the best-IoU match of each 2024 polygon in the 2023 merged map is a second, model-independent check of whether the merge produced real paddocks. Median best IoU by what the merge did (classified 2024 polygons):

| 2024 polygon category | n | median IoU with 2023 | share IoU >= 0.7 |
|---|---|---|---|
| untouched | 2,616 | 0.94 | 74 % |
| absorbed | 640 | 0.95 | 75 % |
| absorbed_union | 162 | 0.93 | 72 % |
| union | 226 | 0.86 | 64 % |
| rescued | 23 | 0.28 | 30 % |
| residual_cut_union | 650 | 0.92 | 69 % |
| residual_cut_absorbed_union | 246 | 0.93 | 74 % |
| residual_cut_absorbed | 84 | 0.91 | 64 % |
| residual_cut_untouched | 170 | 0.65 | 49 % |
| residual_cut_rescued | 124 | 0.57 | 40 % |

Union products match the other year's map as well as interior untouched polygons do (the ceiling for year-to-year SAM agreement), which is the quantitative sign that the unions are real paddocks rather than accidental merges. Residual cuts on untouched and rescued polygons match poorly, as truncated views should. 562 of 1,447 residual-cut classified polygons (39 %) have a 2023 polygon covering >= 80 % of them that extends >= 1 ha past the cut.

## 5. Repairing residual cuts from a second view (`repair_cuts_multiyear.py`)

A cut view is extended with the part of a donor polygon beyond it when all of: >= 100 m of the boundary is on the own raster edge; the image test says the field continues (score <= 0.61); one donor polygon covers >= 80 % of the view; the added part touches the cut, is >= 1 ha and <= 3x the view, and does not lie under another kept polygon; the result is one polygon <= 300 ha with compactness <= 8. Attributes are kept (the class was decided on the paddock's larger part); `boundary_action='repaired'`, `repair_from`, `repair_added_ha` are written.

**Known-answer validation.** The merge's own M1 union polygons are known whole paddocks with a known cut line (their larger fragment's raster edge). Each was re-cut at that edge and repaired from a donor map that never saw the union:

| donor | known cuts | repaired | median IoU cut vs truth | median IoU repaired vs truth | 10 % | >= 0.9 | <= 0.7 | median overshoot |
|---|---|---|---|---|---|---|---|---|
| offset-grid 2024 (same year, shifted lattice) | 609 | 394 (65 %) | 0.818 | 0.993 | 0.958 | 94 % | 0 % | 0.11 ha |
| 2023 (same lattice) | 609 | 268 (44 %) | 0.827 | 0.991 | 0.941 | 94 % | 0 % | 0.20 ha |

Why not 100 %: offset-grid donor declines were {'repaired': 394, 'image_says_boundary': 111, 'donor_cover_below_min': 79, 'added_part_not_at_cut': 10, 'no_donor_overlap': 7, 'added_below_min': 4, 'result_not_single_polygon': 2, 'added_over_ratio': 1, 'result_over_max_compactness': 1}; 2023 declines were {'repaired': 268, 'image_says_boundary': 111, 'no_donor_overlap': 97, 'donor_cover_below_min': 96, 'added_part_not_at_cut': 26, 'added_below_min': 7, 'result_not_single_polygon': 2, 'result_over_max_compactness': 1, 'added_over_ratio': 1}. The image test's ~18 % false-boundary rate is the largest single cost; the rest is the donor not holding the paddock whole either.

**Applied to the real residual.** On the merged 2024 box with both donors (offset grid first): {'not_cut': 3558, 'image_says_boundary': 1147, 'added_part_not_at_cut': 309, 'donor_cover_below_min': 230, 'no_donor_overlap': 190, 'repaired': 178, 'added_below_min': 38, 'result_not_single_polygon': 10, 'result_over_max_compactness': 8, 'added_over_ratio': 7, 'image_no_sample': 1, 'nothing_to_add': 1}. 178 polygons repaired, +2,214 ha (offset grid 131 polygons / 1,747 ha; 2023 47 / 467 ha). Classified area 243,907 -> 246,121 ha; overlap unchanged (0.74 %).

The yield is far below the validation recall because the residual cuts are mostly *persistent*: the same neighbouring tile fails on the same paddock every year, so a donor on the same lattice usually holds the same cut (`donor_cover_below_min`, `added_part_not_at_cut`, `no_donor_overlap`). A same-year offset-grid segmentation puts the paddock in the middle of a tile instead, which is why it is the better donor. Nothing here re-runs SAM.

## 6. How to run it

```
YEAR=2024 ./run_national.sh boundary      # after merge; qsubs boundary_national.pbs (1 CPU, 32 GB, <= 4 h)
#  -> $M/national_2024_crops_merged.gpkg, boundary_away.csv, boundary_pairs.csv, boundary_summary.json
python merge_tile_boundaries.py --in IN.gpkg --out OUT.gpkg --aois aois.csv --samgeo-dir samgeo \
       --away-csv away.csv --pairs-csv pairs.csv --summary summary.json     # any subset, e.g. a clip
python boundary_seam_audit.py --gpkg OUT.gpkg --aois aois.csv --samgeo-dir samgeo --out-csv a.csv --summary a.json
python repair_cuts_multiyear.py validate|repair --in OUT.gpkg --donor OTHER.gpkg [--donor ...] --aois aois.csv \
       --samgeo-dir samgeo --decisions-csv d.csv --summary s.json [--out REPAIRED.gpkg]
python boundary_qa_figures.py --before IN.gpkg --after OUT.gpkg --aois aois.csv --samgeo-dir samgeo \
       --examples ex.csv --out fig.png --labels          # ex.csv: name,x,y,half_m[,note] in EPSG:3577
```

Cost: the box (10,304 polygons) peaks at 249 MB and takes ~15 s on one core; a national year (1.35 M polygons) is ~130x, so the PBS script asks for 32 GB / 4 h (about 20-60 SU normal-queue equivalent). The slow part nationally is reading 99,465 composite headers for `raster_cut_m`, not the geometry. The national pass has NOT been run: 2023/2024 are about to be re-predicted on the adopted model and 2022 has no predictions yet, so it belongs after each year's `merge` in the runbook.

## 7. The four known split pairs, revisited

PIPELINE_ARCHITECTURE_AND_TILING.md §6 tested four Legume/Cereal, Canola/Legume and Canola/Cereal pairs found by eye or by the grid-line-touching search (`figures/tile_boundary_merge/known.png`, `figures/tile_boundary_merge/zoom13.png`). Under the corrected mechanism: pair 4 is two duplicate views (both dropped as fully covered same-class twins); pair 2 is partly duplication, and its 5 ha Legume view survives as a rescued polygon with a sliver overlap on its neighbour; pair 3's 12 ha Canola view is rescued (only 22 % covered) and its 25.5 ha Legume view is unioned into the east tile's Legume — the two classes are kept because the two views barely overlap (2.6 ha), an honest disagreement rather than an artefact; pair 1 (the original by-eye case) does not look like a tile artefact at all: the 11.7 ha Legume and the 95 ha Cereal appear to be separated by a track that runs along the lattice line, both polygons stop there well inside their own rasters, and no view of either tile overlaps the other. Only 2 of the 4 pairs were what §5-§6 assumed they were.

## 8. Honest limits

- The image test has a 22 % equal-error rate; it is used only as a gate for repairs, never to delete anything.
- `raster_cut_m` flags real fences within 30 m of the raster edge as well as cuts (about half of flagged classified polygons after the merge). Use it with `cut_continuity` or as a conservative exclusion.
- Class reconciliation moves 71 polygons' labels in the box by area-weighted probability; the pre-merge labels are kept in `pre_merge_classes`. Whether the reconciled label is right is untested against ground truth.
- Everything is measured on one 60 km box in the Riverina for 2024 and 2023 (plus the offset-grid 2024 pilot). Tile geometry is identical nationally, but paddock size and SAM failure rates are not.
- Thresholds were set by reasoning from the pipeline's own filters, not tuned; the decision tables (`*_away.csv`, `*_pairs.csv`) make any re-threshold a re-run, not a re-analysis.
- The offset-grid pilot's own merge was run with the pilot's `aois_offset2024.csv` lattice; it is a Riverina-only product (OFFSET_GRID_PILOT.md) and does not exist nationally.

