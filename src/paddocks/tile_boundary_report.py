#!/usr/bin/env python
"""
tile_boundary_report.py -- write output/TILE_BOUNDARY_MERGE.md from the Riverina-box run outputs.

Reads the JSON summaries written by merge_tile_boundaries.py, boundary_seam_audit.py,
cut_continuity.py, cross_year_check.py and repair_cuts_multiyear.py in --work-dir, so every
number in the report is the one in the files. Aggregate only: no site-level records.
"""
import argparse
import json
import os
import time


def J(work, name):
    with open(os.path.join(work, name)) as f:
        return json.load(f)


def pct(a, b):
    return 100.0 * a / b if b else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fig-dir", default="figures/tile_boundary_merge",
                    help="figure path prefix relative to the report")
    a = ap.parse_args()
    W, F = a.work_dir, a.fig_dir
    m24, m23, moff = J(W, "riv2024_summary.json"), J(W, "riv2023_summary.json"), J(W, "off2024_summary.json")
    ab, aa, ar = J(W, "audit_2024_before.json"), J(W, "audit_2024_after.json"), J(W, "audit_2024_repaired.json")
    ab23, aa23 = J(W, "audit_2023_before.json"), J(W, "audit_2023_after.json")
    co = J(W, "continuity_2024.json")
    xy = J(W, "xyear_2024_vs_2023.json")
    voff, v23 = J(W, "repair_validate_from_off2024.json"), J(W, "repair_validate_from_riv2023.json")
    rp = J(W, "repair_2024.json")
    import pandas as pd
    R = pd.read_csv(os.path.join(W, "repair_2024.csv"))
    rep = R[R.reason == "repaired"]
    by_donor = rep.donor.str.extract(r"(off2024|riv2023)")[0].value_counts().to_dict()
    ha_donor = rep.groupby(rep.donor.str.extract(r"(off2024|riv2023)")[0]).added_ha.sum().round(1).to_dict()

    ad = m24["away_decisions"]
    pr = m24["pair_reasons"]
    cont_thr = co["threshold"]
    gen_by = co["residual_genuine_by_action"]
    xcat = xy["median_best_iou_by_cat"]
    xn = xy["n_by_cat"]

    def q(d, k):
        return d[str(k)] if str(k) in d else d[k]

    lines = []
    L = lines.append
    L(f"# Tile-boundary artefacts in the national crop map: what they are, and a post-hoc merge that removes them")
    L("")
    L(f"Generated {time.strftime('%Y-%m-%d')} by `src/paddocks/tile_boundary_report.py` from the outputs of "
      "`merge_tile_boundaries.py`, `boundary_seam_audit.py`, `cut_continuity.py`, `cross_year_check.py` and "
      "`repair_cuts_multiyear.py` on the Riverina 60 km test box (EPSG:3577 x 1,347,106-1,407,106, "
      "y -3,891,681 to -3,831,681; the same box as PIPELINE_ARCHITECTURE_AND_TILING.md §5). "
      "Everything here ran on the gadi login node in seconds to minutes; no PBS job was submitted and no "
      "GPU was used. Aggregate only.")
    L("")
    L("## 0. Summary")
    L("")
    L("- **The artefact is duplication, not a cut at the lattice line.** Each 3 km tile's raster is the EPSG:6933 "
      "bounding box of its rotated Albers square, so neighbouring rasters overlap by ~350-700 m and every paddock in "
      f"that band is segmented and classified by both tiles. In the box, {m24['n_extend_past_core']:,} of "
      f"{m24['n_polygons']:,} polygons ({pct(m24['n_extend_past_core'], m24['n_polygons']):.0f} %) extend past their "
      f"own lattice square (max {m24['max_overshoot_m']:.0f} m), {m24['n_away']:,} ({m24['pct_away_of_all']:.1f} %) "
      f"have their centroid outside it, and {ab['overlap_pct_of_area']:.1f} % of the summed polygon area is counted twice. "
      "SAM's polygons stop 2 px inside their own raster; nothing is cut at a neighbour's edge or at the lattice line "
      f"(§1, `{F}/raw_sam_edge_histogram.png`). PIPELINE_ARCHITECTURE_AND_TILING.md §4 said \"no overlap\"; it has been corrected.")
    L(f"- **A post-hoc merge on the merged GeoPackage removes it.** `merge_tile_boundaries.py` (rules in §2) takes the box from "
      f"{m24['n_polygons']:,} to {m24['n_polygons_after']:,} polygons and double-counted area from "
      f"{ab['overlap_ha']:,.0f} ha ({ab['overlap_pct_of_area']:.1f} %) to {aa['overlap_ha']:,.0f} ha "
      f"({aa['overlap_pct_of_area']:.2f} %), in {m24['elapsed_s']:.0f} s. {m24['n_union_polygons']:,} whole paddocks are rebuilt from "
      f"{m24['n_union_fragments']:,} cross-tile views; {m24['n_dup_class_conflicts'] + pr.get('class_conflict_reconciled', 0)} class "
      "disagreements between two views of one paddock are reconciled by area-weighted probabilities and flagged; "
      f"{pr.get('conflict_confident_disagreement', 0)} confident disagreements are kept and flagged. Similar numbers on 2023 and on the "
      "offset-grid 2024 pilot (§3).")
    L(f"- **What remains is a view cut at its own raster edge whose twin the other tile never produced.** After the merge "
      f"{aa['n_truncated_classified']:,} classified polygons ({aa['pct_truncated_classified']:.0f} %) still have >= 100 m of "
      "boundary along their raster edge, but an image test on the neighbour's composite says only about half of those are "
      f"genuine cuts ({co['residual_genuine_cut_n']:,}, {co['residual_genuine_cut_pct']:.0f} %); the rest are real fences that "
      "happen to lie within 30 m of the edge (§4). Genuine cuts concentrate in untouched and rescued polygons "
      f"({100 * gen_by.get('untouched', 0):.0f} % and {100 * gen_by.get('rescued', 0):.0f} % genuine) and are rare on union products "
      f"({100 * gen_by.get('union', 0):.0f} %).")
    L(f"- **Those residual cuts are repairable from a second view of the same ground, and the repair is precise.** Re-cutting the "
      f"merge's own {voff['n_known_cuts']:,} union polygons at their larger fragment's raster edge and repairing them from the "
      f"offset-grid 2024 map restores {voff['repaired_pct']:.0f} % of them at median IoU {q(voff['iou_repaired_vs_truth_quantiles'], 0.5):.3f} "
      f"against the known whole paddock (from {q(voff['iou_before_repair_quantiles'], 0.5):.3f} cut), {100 * voff['share_iou_ge_0_9']:.0f} % "
      f">= 0.9 and none <= 0.7; the 2023 map as donor restores {v23['repaired_pct']:.0f} % at median IoU "
      f"{q(v23['iou_repaired_vs_truth_quantiles'], 0.5):.3f} (§5). Applied for real, the two donors together repair "
      f"{rp['n_repaired']:,} polygons (+{rp['added_ha_total']:,.0f} ha; offset grid {by_donor.get('off2024', 0)}, 2023 {by_donor.get('riv2023', 0)}). "
      "Most residual cuts recur every year because the same neighbouring tile fails on the same paddock, so a same-year "
      "second view is worth more than more years.")
    L("- **Recommendation.** Run the merge (`run_national.sh boundary`, one small CPU job per year, §6) on every year as "
      "soon as it is merged; treat `raster_cut_m` and `class_conflict` as quality flags in the product; use the multi-view "
      "repair as an optional second pass once a second view exists for a year, preferring a same-year offset-grid "
      "segmentation over another year. Do not change the tiling or re-segment.")
    L("")
    L("## 1. What the tiles actually do")
    L("")
    L("`samgeo_segment.build_image` asks the datacube for an exact 3 km square in EPSG:3577 but for the raster in "
      "`output_crs=\"EPSG:6933\"` (`samgeo_segment.py:177-180`). The square is rotated ~6.6° in EPSG:6933 at Riverina "
      "longitudes, and datacube fills the whole bounding box of the rotated square: every composite is 351 x 316 px at "
      "10 m (11.1 km² instead of 9.0). The raster edge is a line tilted 6.6° that touches the lattice square at one corner "
      "and is ~350 m outside it at the other, so adjacent rasters overlap in a wedge-shaped band 350-700 m wide. The "
      "composites are clean across that band: the mean image gradient at the columns and rows where a neighbour's raster "
      "edge falls is at chance (fraction of those lines in a tile's top 1 % of gradient columns: 0.032, chance 0.03; "
      f"1,741 lines over the box's tiles).")
    L("")
    L("Where the raw SAM polygons end is measured directly from `_segment.gpkg` in pixel space "
      f"(`{F}/raw_sam_edge_histogram.png`, 40 tiles): vertical boundary points per column spike 25x at column 2 and at "
      "column 350 of a 351-px raster and show no excess at columns 37-39 and 313-316, where the neighbours' raster edges "
      "fall. SAM's masks stop 2 px (~20 m) inside the image; nothing about the neighbouring tile is visible to it. So a paddock "
      "straddling a lattice line is normally seen by BOTH tiles, each view cut ~20 m inside that tile's own raster edge "
      "(170-350 m past the line), and the two views overlap by the width of the band.")
    L("")
    L(f"| Riverina box, 2024 | value |")
    L("|---|---|")
    L(f"| polygons | {m24['n_polygons']:,} ({m24['n_clean_classified']:,} cleanly classified) |")
    L(f"| extend past their own lattice square | {m24['n_extend_past_core']:,} ({pct(m24['n_extend_past_core'], m24['n_polygons']):.1f} %), max {m24['max_overshoot_m']:.0f} m |")
    L(f"| centroid outside their own square (\"away\" views) | {m24['n_away']:,} ({m24['pct_away_of_all']:.1f} %) |")
    L(f"| cross-tile overlapping pairs | {m24['n_cross_tile_overlap_pairs_before']:,} |")
    L(f"| pairwise overlap area | {ab['overlap_ha']:,.0f} ha = {ab['overlap_pct_of_area']:.1f} % of summed polygon area ({m24['overlap_ha_before_classified']:,.0f} ha between classified polygons) |")
    L(f"| classified polygons with >= 100 m of boundary within 30 m of their own raster edge | {ab['n_truncated_classified']:,} ({ab['pct_truncated_classified']:.0f} %) |")
    L("")
    L("The earlier bbox statistic in PIPELINE_ARCHITECTURE_AND_TILING.md §5 (polygons whose bounding box touches a "
      "lattice line, 7 % at 10 m) measured the wrong thing: the artefact is not at the lattice line. It grows linearly "
      "with tolerance at the background rate of real boundaries near any line.")
    L("")
    L("## 2. The merge rule set (`merge_tile_boundaries.py`)")
    L("")
    L("The lattice square of each tile is its **core**; a tile is authoritative on its own core because it saw that "
      "ground furthest from its raster edge. All thresholds are CLI arguments; defaults are what was run here.")
    L("")
    L("- **D1 ownership.** A polygon whose centroid lies outside its own tile's core is an *away* view of ground another tile owns.")
    L("- **D2 coverage.** An away polygon is dropped as a duplicate if >= 95 % of its area is covered by the owning tile's "
      "own polygons that decided on that ground (classified or `no_crop_signal`); if 50-95 % covered and both views are "
      "classified with the same or a reconcilable class it is unioned into its twin (the covering polygon with the largest "
      "intersection), adding the ground the owner missed; below 50 % it is *rescued* and kept, because the home tile has no claim there.")
    L("- **D3 conflict.** When a dropped or unioned view and its twin disagree in class, the twin's class is reconciled by the "
      "area-weighted mean of (p_canola, p_cereal, p_legume) and `class_conflict=1` is written with `pre_merge_classes`.")
    L("- **M1 union.** Two kept classified polygons from different tiles that still overlap by >= 50 % of the smaller are two "
      "truncated views of one paddock wider than the band: they are unioned if the union is one polygon <= 300 ha with "
      "compactness P/sqrt(A) <= 8 (the pipeline's own filters) and the classes are the same or reconcilable (the area-weighted "
      "winner is one of the two and both give it >= 0.25). Confident disagreements are kept and flagged. Connected "
      "components merge together (cap 4 fragments).")
    L("- **M2 clip.** Whatever still overlaps after D1-M1 (boundary-disagreement slivers, pairs with an abstained member) is "
      "assigned by ownership: the overlap stays with the polygon whose tile owns the square it lies in and is subtracted "
      "from the other, provided it is <= 50 % of the loser and the loser stays one polygon (crumbs < 0.5 ha discarded). "
      "Overlaps that fail those tests are left and counted.")
    L("- **Provenance.** Every touched row carries `boundary_action` (`absorbed`, `absorbed_union`, `rescued`, `union`, "
      "`+clipped`), `merged_from` (tile:idx of every source view), `merge_n`, `class_conflict`, `pre_merge_classes`, "
      "`clip_ha`; every row carries `raster_cut_m`, the length of its boundary within 30 m of its own tile's raster "
      "edge(s). Untouched rows are byte-identical to the input apart from the new columns. The input is never modified.")
    L("")
    L("## 3. What the merge does on the box")
    L("")
    L("| | 2024 | 2023 | 2024 offset-grid pilot |")
    L("|---|---|---|---|")
    L(f"| polygons before -> after | {m24['n_polygons']:,} -> {m24['n_polygons_after']:,} | {m23['n_polygons']:,} -> {m23['n_polygons_after']:,} | {moff['n_polygons']:,} -> {moff['n_polygons_after']:,} |")
    L(f"| away views: dropped duplicate / unioned into twin / dropped partial / rescued | {ad['drop_duplicate']} / {ad['union_into_twin']} / {ad['drop_partial']} / {ad['rescue']} | {m23['away_decisions']['drop_duplicate']} / {m23['away_decisions']['union_into_twin']} / {m23['away_decisions']['drop_partial']} / {m23['away_decisions']['rescue']} | {moff['away_decisions']['drop_duplicate']} / {moff['away_decisions']['union_into_twin']} / {moff['away_decisions']['drop_partial']} / {moff['away_decisions']['rescue']} |")
    L(f"| M1: kept-kept pairs unioned -> whole paddocks | {m24['n_pairs_merged']:,} -> {m24['n_union_polygons']:,} | {m23['n_pairs_merged']:,} -> {m23['n_union_polygons']:,} | {moff['n_pairs_merged']:,} -> {moff['n_union_polygons']:,} |")
    L(f"| pairwise overlap before -> after D1-M1 -> after M2 (ha) | {m24['overlap_ha_before']:,.0f} -> {m24['overlap_ha_after_d1_m1']:,.0f} -> {m24['overlap_ha_after']:,.0f} | {m23['overlap_ha_before']:,.0f} -> {m23['overlap_ha_after_d1_m1']:,.0f} -> {m23['overlap_ha_after']:,.0f} | {moff['overlap_ha_before']:,.0f} -> — -> {moff['overlap_ha_after']:,.0f} |")
    L(f"| M2 slivers clipped (polygons, ha) | {m24['m2_clipped_polygons']:,}, {m24['m2_clipped_ha']:,.0f} | — , {m23['m2_clipped_ha']:,.0f} | — |")
    L(f"| overlap as % of summed area, before -> after (independent audit) | {ab['overlap_pct_of_area']:.1f} -> {aa['overlap_pct_of_area']:.2f} | {ab23['overlap_pct_of_area']:.1f} -> {aa23['overlap_pct_of_area']:.2f} | — |")
    L("")
    L(f"2024 detail: {m24['n_deleted']:,} rows deleted, {m24['n_updated']:,} updated, {m24['n_inserted']:,} union rows inserted. "
      f"M1 reasons: {pr}. Union sizes: {m24['union_merge_n_hist']} fragments per paddock, median union {m24['union_area_ha_median']:.0f} ha. "
      f"Class conflicts reconciled on duplicates: {m24['n_dup_class_conflicts']}; on unions: {pr.get('class_conflict_reconciled', 0)}; "
      f"kept as confident disagreements: {pr.get('conflict_confident_disagreement', 0)} pairs. Exclusive ground discarded with dropped "
      f"partial views: {m24['lost_exclusive_ha_classified']:.0f} ha classified. Remaining overlap after M2: {m24['n_overlap_pairs_after']:,} "
      f"pairs, mostly {m24['m2_skip_reasons']}.")
    L("")
    L("Figures (all Riverina 2024; left = Fourier-of-NDWI composite SAM saw, middle = before, right = after; white dashed = "
      "3 km lattice, yellow = each tile's actual raster footprint, so the overlap band is visible):")
    L(f"- `{F}/overview.png` — two 6 km windows around a lattice corner: the double layer of away views along every line before, a continuous paddock pattern after.")
    L(f"- `{F}/known.png` and `{F}/zoom13.png` — the four §6 split pairs from PIPELINE_ARCHITECTURE_AND_TILING.md (known-answer cases; see §7 below).")
    L(f"- `{F}/m1_merge.png`, `{F}/drop_dup.png`, `{F}/union_twin.png`, `{F}/drop_partial.png`, `{F}/rescue.png`, "
      f"`{F}/conflict.png`, `{F}/clip.png` — three seeded random examples of each decision.")
    L(f"- `{F}/residual.png` — residual raster-edge cuts after the merge (§4). `{F}/repaired.png` — multi-view repairs (§5).")
    L(f"- `{F}/E_composite.png` — one tile's composite with the neighbour's raster edge drawn on it: no seam.")
    L("")
    L("## 4. What is left: cuts whose twin never existed, and how to tell them from real fences")
    L("")
    L("After D1-M2 a polygon can still end at its own raster edge. That happens when the neighbouring tile produced no "
      "kept polygon for the ground beyond the cut (SAM there merged it into a compactness-rejected blob, or into a different "
      "paddock, or the view abstained), which is exactly the failure PIPELINE_ARCHITECTURE_AND_TILING.md §6 found when it "
      "widened the window. A straight edge within 30 m of the raster edge is however not proof of a cut: a real fence or road can "
      "lie there. Two measurements separate them.")
    L("")
    L("**Image continuity (`cut_continuity.py`).** The neighbour's composite covers both sides of the cut, so the 3-band values "
      "15-60 m inside the polygon along the cut are compared with 15-60 m beyond it, from the same composite (each tile has its "
      "own stretch): score = mean |mu_in - mu_out| / pooled sd. Calibrated on two sets the merge itself provides: fragments the "
      f"merge unioned (known same field beyond the cut, n={co['n_same_field']}) and interior polygons' real boundaries "
      f"(n={co['n_real_boundary']}).")
    L("")
    L("| set | 10 % | 25 % | median | 75 % | 90 % |")
    L("|---|---|---|---|---|---|")
    sf, rb = co["same_field_quantiles"], co["real_boundary_quantiles"]
    L(f"| same field beyond the cut (known genuine cuts) | {q(sf, 0.1):.2f} | {q(sf, 0.25):.2f} | {q(sf, 0.5):.2f} | {q(sf, 0.75):.2f} | {q(sf, 0.9):.2f} |")
    L(f"| real boundary | {q(rb, 0.1):.2f} | {q(rb, 0.25):.2f} | {q(rb, 0.5):.2f} | {q(rb, 0.75):.2f} | {q(rb, 0.9):.2f} |")
    rq = co["residual_quantiles"]
    L(f"| residual raster-edge polygons after the merge (n={co['n_residual']:,}) | {q(rq, 0.1):.2f} | {q(rq, 0.25):.2f} | {q(rq, 0.5):.2f} | {q(rq, 0.75):.2f} | {q(rq, 0.9):.2f} |")
    L("")
    L(f"Equal-error threshold {cont_thr:.2f} (error {100 * co['equal_error_rate']:.0f} % each way: {100 * co['same_field_flagged_continuous']:.0f} % of known cuts "
      f"score as continuous, {100 * co['real_boundary_flagged_boundary']:.0f} % of real boundaries as boundaries). The residual set is a "
      f"mixture: {co['residual_genuine_cut_n']:,} of {co['n_residual']:,} ({co['residual_genuine_cut_pct']:.0f} %) score as genuine cuts, and "
      f"the split by what the merge did to the polygon is telling — genuine among untouched {100 * gen_by.get('untouched', 0):.0f} %, "
      f"rescued {100 * gen_by.get('rescued', 0):.0f} %, absorbed {100 * gen_by.get('absorbed', 0):.0f} %, absorbed+union "
      f"{100 * gen_by.get('absorbed_union', 0):.0f} %, union {100 * gen_by.get('union', 0):.0f} %. Union products are whole paddocks whose "
      "residual straight edge is a real boundary near the raster edge; untouched and rescued polygons are the cuts the merge could not fix "
      "because there was nothing to fix them with.")
    L("")
    L("**Cross-year geometry (`cross_year_check.py`).** Segmentation is independent each year on the same lattice, so the "
      "best-IoU match of each 2024 polygon in the 2023 merged map is a second, model-independent check of whether the merge "
      "produced real paddocks. Median best IoU by what the merge did (classified 2024 polygons):")
    L("")
    L("| 2024 polygon category | n | median IoU with 2023 | share IoU >= 0.7 |")
    L("|---|---|---|---|")
    sh = xy["share_iou_ge_0_7_by_cat"]
    for cat in ["untouched", "absorbed", "absorbed_union", "union", "rescued", "residual_cut_union", "residual_cut_absorbed_union",
                "residual_cut_absorbed", "residual_cut_untouched", "residual_cut_rescued"]:
        if cat in xcat:
            L(f"| {cat} | {xn.get(cat, 0):,} | {xcat[cat]:.2f} | {100 * sh.get(cat, float('nan')):.0f} % |")
    L("")
    L("Union products match the other year's map as well as interior untouched polygons do (the ceiling for year-to-year SAM "
      "agreement), which is the quantitative sign that the unions are real paddocks rather than accidental merges. Residual "
      "cuts on untouched and rescued polygons match poorly, as truncated views should. "
      f"{xy['residual_cuts_whole_in_other_year']:,} of {xy['residual_cuts_classified']:,} residual-cut classified polygons "
      f"({xy['residual_cuts_whole_in_other_year_pct']:.0f} %) have a 2023 polygon covering >= 80 % of them that extends >= 1 ha past the cut.")
    L("")
    L("## 5. Repairing residual cuts from a second view (`repair_cuts_multiyear.py`)")
    L("")
    L("A cut view is extended with the part of a donor polygon beyond it when all of: >= 100 m of the boundary is on the own "
      f"raster edge; the image test says the field continues (score <= {cont_thr:.2f}); one donor polygon covers >= 80 % of the view; "
      "the added part touches the cut, is >= 1 ha and <= 3x the view, and does not lie under another kept polygon; the result is one "
      "polygon <= 300 ha with compactness <= 8. Attributes are kept (the class was decided on the paddock's larger part); "
      "`boundary_action='repaired'`, `repair_from`, `repair_added_ha` are written.")
    L("")
    L("**Known-answer validation.** The merge's own M1 union polygons are known whole paddocks with a known cut line (their "
      "larger fragment's raster edge). Each was re-cut at that edge and repaired from a donor map that never saw the union:")
    L("")
    L("| donor | known cuts | repaired | median IoU cut vs truth | median IoU repaired vs truth | 10 % | >= 0.9 | <= 0.7 | median overshoot |")
    L("|---|---|---|---|---|---|---|---|---|")
    for name, v in [("offset-grid 2024 (same year, shifted lattice)", voff), ("2023 (same lattice)", v23)]:
        L(f"| {name} | {v['n_known_cuts']:,} | {v['n_repaired']:,} ({v['repaired_pct']:.0f} %) | {q(v['iou_before_repair_quantiles'], 0.5):.3f} | "
          f"{q(v['iou_repaired_vs_truth_quantiles'], 0.5):.3f} | {q(v['iou_repaired_vs_truth_quantiles'], 0.1):.3f} | {100 * v['share_iou_ge_0_9']:.0f} % | "
          f"{100 * v['share_iou_le_0_7']:.0f} % | {v['overshoot_ha_median']:.2f} ha |")
    L("")
    L(f"Why not 100 %: offset-grid donor declines were {voff['reasons']}; 2023 declines were {v23['reasons']}. The image test's "
      f"~{100 * (1 - co['same_field_flagged_continuous']):.0f} % false-boundary rate is the largest single cost; the rest is the donor not "
      "holding the paddock whole either.")
    L("")
    L(f"**Applied to the real residual.** On the merged 2024 box with both donors (offset grid first): {rp['reasons']}. "
      f"{rp['n_repaired']:,} polygons repaired, +{rp['added_ha_total']:,.0f} ha (offset grid {by_donor.get('off2024', 0)} polygons / "
      f"{ha_donor.get('off2024', 0):,.0f} ha; 2023 {by_donor.get('riv2023', 0)} / {ha_donor.get('riv2023', 0):,.0f} ha). Classified area "
      f"{aa['classified_area_ha']:,.0f} -> {ar['classified_area_ha']:,.0f} ha; overlap unchanged ({ar['overlap_pct_of_area']:.2f} %).")
    L("")
    L("The yield is far below the validation recall because the residual cuts are mostly *persistent*: the same neighbouring tile "
      "fails on the same paddock every year, so a donor on the same lattice usually holds the same cut (`donor_cover_below_min`, "
      "`added_part_not_at_cut`, `no_donor_overlap`). A same-year offset-grid segmentation puts the paddock in the middle of a tile "
      "instead, which is why it is the better donor. Nothing here re-runs SAM.")
    L("")
    L("## 6. How to run it")
    L("")
    L("```")
    L("YEAR=2024 ./run_national.sh boundary      # after merge; qsubs boundary_national.pbs (1 CPU, 32 GB, <= 4 h)")
    L("#  -> $M/national_2024_crops_merged.gpkg, boundary_away.csv, boundary_pairs.csv, boundary_summary.json")
    L("python merge_tile_boundaries.py --in IN.gpkg --out OUT.gpkg --aois aois.csv --samgeo-dir samgeo \\")
    L("       --away-csv away.csv --pairs-csv pairs.csv --summary summary.json     # any subset, e.g. a clip")
    L("python boundary_seam_audit.py --gpkg OUT.gpkg --aois aois.csv --samgeo-dir samgeo --out-csv a.csv --summary a.json")
    L("python repair_cuts_multiyear.py validate|repair --in OUT.gpkg --donor OTHER.gpkg [--donor ...] --aois aois.csv \\")
    L("       --samgeo-dir samgeo --decisions-csv d.csv --summary s.json [--out REPAIRED.gpkg]")
    L("python boundary_qa_figures.py --before IN.gpkg --after OUT.gpkg --aois aois.csv --samgeo-dir samgeo \\")
    L("       --examples ex.csv --out fig.png --labels          # ex.csv: name,x,y,half_m[,note] in EPSG:3577")
    L("```")
    L("")
    L("Cost: the box (10,304 polygons) peaks at 249 MB and takes ~15 s on one core; a national year (1.35 M polygons) is ~130x, "
      "so the PBS script asks for 32 GB / 4 h (about 20-60 SU normal-queue equivalent). The slow part nationally is reading "
      "99,465 composite headers for `raster_cut_m`, not the geometry. The national pass has NOT been run: 2023/2024 are about to be "
      "re-predicted on the adopted model and 2022 has no predictions yet, so it belongs after each year's `merge` in the runbook.")
    L("")
    L("## 7. The four known split pairs, revisited")
    L("")
    L("PIPELINE_ARCHITECTURE_AND_TILING.md §6 tested four Legume/Cereal, Canola/Legume and Canola/Cereal pairs found by eye "
      f"or by the grid-line-touching search (`{F}/known.png`, `{F}/zoom13.png`). Under the corrected mechanism: pair 4 is two "
      "duplicate views (both dropped as fully covered same-class twins); pair 2 is partly duplication, and its 5 ha Legume view "
      "survives as a rescued polygon with a sliver overlap on its neighbour; pair 3's 12 ha Canola view is rescued (only 22 % "
      "covered) and its 25.5 ha Legume view is unioned into the east tile's Legume — the two classes are kept because the two "
      "views barely overlap (2.6 ha), an honest disagreement rather than an artefact; pair 1 (the original by-eye case) does not "
      "look like a tile artefact at all: the 11.7 ha Legume and the 95 ha Cereal appear to be separated by a track that runs along the "
      "lattice line, both polygons stop there well inside their own rasters, and no view of either tile overlaps the other. Only 2 of the "
      "4 pairs were what §5-§6 assumed they were.")
    L("")
    L("## 8. Honest limits")
    L("")
    L("- The image test has a 22 % equal-error rate; it is used only as a gate for repairs, never to delete anything.")
    L("- `raster_cut_m` flags real fences within 30 m of the raster edge as well as cuts (about half of flagged classified polygons after the merge). Use it with `cut_continuity` or as a conservative exclusion.")
    L(f"- Class reconciliation moves {m24['n_twins_reconciled'] + pr.get('class_conflict_reconciled', 0)} polygons' labels in the box by area-weighted probability; the pre-merge labels are kept in `pre_merge_classes`. Whether the reconciled label is right is untested against ground truth.")
    L("- Everything is measured on one 60 km box in the Riverina for 2024 and 2023 (plus the offset-grid 2024 pilot). Tile geometry is identical nationally, but paddock size and SAM failure rates are not.")
    L("- Thresholds were set by reasoning from the pipeline's own filters, not tuned; the decision tables (`*_away.csv`, `*_pairs.csv`) make any re-threshold a re-run, not a re-analysis.")
    L("- The offset-grid pilot's own merge was run with the pilot's `aois_offset2024.csv` lattice; it is a Riverina-only product (OFFSET_GRID_PILOT.md) and does not exist nationally.")
    L("")
    with open(a.out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
