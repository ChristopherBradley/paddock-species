#!/usr/bin/env python
"""
geometry_report.py -- write output/TILE_GEOMETRY_DECISION.md from geometry_decision.json
(+ visual_verdicts.json written by hand after looking at the disagreement figures).
"""
import argparse
import json
import os
import time

ACTUAL_2024 = 6622.6
ARM_DESC = {
    "prod_3km": ("3 km tiles, no overlap (production 2022-2024)", "3 km lattice", "1.5 km", "0"),
    "ov2000": ("4 km tiles on the 3 km lattice", "3 km lattice", "2.0 km", "1 km"),
    "ov2500": ("5 km tiles on the 3 km lattice", "3 km lattice", "2.5 km", "2 km"),
    "p9": ("9 km tiles, no overlap", "9 km lattice", "4.5 km", "0"),
    "p9ov1000": ("10 km tiles on the 9 km lattice", "9 km lattice", "5.0 km", "1 km"),
    "p9ov2000": ("11 km tiles on the 9 km lattice", "9 km lattice", "5.5 km", "2 km"),
}


def fmt(v, nd=2):
    return "—" if v is None else (f"{v:,.{nd}f}" if isinstance(v, (int, float)) else str(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decision", required=True)
    ap.add_argument("--verdicts", default=None)
    ap.add_argument("--recommended", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fig-dir", default="figures/tile_geometry")
    ap.add_argument("--n9", type=int, default=15968, help="parents in the national 9 km grid from grid9_from_2024.py")
    a = ap.parse_args()
    G = json.load(open(a.decision))
    # the real national 9 km grid (grid9_from_2024.py) has partial parents at the cropping margin, so it holds more
    # tiles than 99,465 / 9; rescale the 9 km arms' costs to the count the generator actually produced
    for k, v in G.items():
        if isinstance(v, dict) and v.get("cost") and v["cost"].get("n_tiles_national") == 11051 and a.n9:
            f = a.n9 / 11051
            for c in ("sam_su_year", "presegment_su_year", "predict_su_year", "total_su_year"):
                if v["cost"].get(c) is not None:
                    v["cost"][c] = round(v["cost"][c] * f)
            v["cost"]["n_tiles_national"] = a.n9
    V = json.load(open(a.verdicts)) if a.verdicts and os.path.exists(a.verdicts) else {}
    arms = [k for k in ARM_DESC if k in G]
    R = a.recommended
    P, C = G["prod_3km"], G[R]
    L = []
    A = L.append
    A("# Tile geometry for the national runs: 3 km production vs overlap vs 9 km, each predicted and merged")
    A("")
    A(f"Generated {time.strftime('%Y-%m-%d')} by `src/paddocks/bench/geometry_report.py` from `geometry_decision.py` on the "
      f"6 x 6-tile Riverina block (grid r932-937, c1182-1187, {G['block_km2']} km2; metrics inside the {G['interior_km2']} km2 interior, "
      "1 km in from the block edge so no arm's outer boundary counts). Every arm was segmented with the adopted SAM settings "
      "(`--prompt-image-only --fp16`), predicted with the production model and gates, and merged with `merge_tile_boundaries.py` on its "
      "own lattice; the production arm is the actual 2024 national output for the same tiles, merged the same way. Aggregate only.")
    A("")
    A("## 0. Decision")
    A("")
    A(f"- **Recommended for a from-scratch re-run: `{R}` — {ARM_DESC[R][0]}.** See §5 for why, and §6 for the commands.")
    A(f"- Cost per national year: {fmt(C['cost'].get('total_su_year'), 0)} SU vs {fmt(P['cost'].get('total_su_year'), 0)} SU for 3 km tiles at the "
      f"same optimised settings (2024 as actually run: {ACTUAL_2024:,.0f} SU).")
    A(f"- Edge artefacts after the merge: classified polygons with a raster-edge cut {fmt(C.get('cut_share_classified'), 3)} vs {fmt(P.get('cut_share_classified'), 3)}; "
      f"residual overlap {fmt(C.get('overlap_pct_area'))} % vs {fmt(P.get('overlap_pct_area'))} % of area; band density ratio {fmt(C.get('band_density_ratio'))} vs {fmt(P.get('band_density_ratio'))}.")
    A(f"- Agreement with the merged production block: {fmt(100 * (C.get('prod_matched_ge05') or 0), 0)} % of production polygons have a match at IoU >= 0.5 "
      f"({fmt(100 * (C.get('prod_matched_ge07') or 0), 0)} % at 0.7); class agrees on {fmt(100 * (C.get('class_agreement_on_matches') or 0), 0)} % of matched pairs.")
    A("")
    A("## 1. Arms")
    A("")
    A("| arm | tiles | lattice | tile half-width | overlap with neighbours | national tiles | polygons before -> after merge | away views |")
    A("|---|---|---|---|---|---|---|---|")
    for k in arms:
        d = ARM_DESC[k]; g = G[k]
        A(f"| {k} | {d[0]} | {d[1]} | {d[2]} | {d[3]} | {fmt(g['cost'].get('n_tiles_national'), 0)} | {fmt(g.get('n_before'), 0)} -> {fmt(g.get('n_after'), 0)} | {fmt(g.get('away_pct'), 0)} % |")
    A("")
    A("## 2. Cost per national year")
    A("")
    A("Per-tile seconds measured in this round (SAM: fp16 + image-only prompts, alone on a V100; presegment and predict on normalbw, "
      "all arms of a stage in the same time window so contention is shared), scaled to the national tile count of each lattice. "
      "Rates: gpuvolta 36 SU/h, normalbw 1.25 SU/h per tile-job.")
    A("")
    A("| arm | presegment s/tile | SAM s/tile | predict s/tile | presegment SU | SAM SU | predict SU | **total SU / year** | vs 3 km optimised | vs 2024 as run |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    base = P["cost"].get("total_su_year")
    for k in arms:
        c = G[k]["cost"]; t = c.get("total_su_year")
        A(f"| {k} | {fmt(c.get('presegment_s_per_tile'), 1)} | {fmt(c.get('sam_s_per_tile'), 2)} | {fmt(c.get('predict_s_per_tile'), 1)} | "
          f"{fmt(c.get('presegment_su_year'), 0)} | {fmt(c.get('sam_su_year'), 0)} | {fmt(c.get('predict_su_year'), 0)} | **{fmt(t, 0)}** | "
          f"{fmt(100 * t / base, 0) if (t and base) else '—'} % | {fmt(100 * t / ACTUAL_2024, 0) if t else '—'} % |")
    A("")
    A("## 3. Edge artefacts and product statistics after the merge (block interior)")
    A("")
    A("| arm | polygons/km2 | classified/km2 | classified median ha | cut share (classified, >= 100 m on own raster edge) | band density ratio | residual overlap % | class conflicts | abstained area ha | classified area ha |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for k in arms:
        g = G[k]
        A(f"| {k} | {fmt(g.get('per_km2'))} | {fmt(g.get('classified_per_km2'))} | {fmt(g.get('classified_median_ha'), 1)} | {fmt(g.get('cut_share_classified'), 3)} | "
          f"{fmt(g.get('band_density_ratio'))} | {fmt(g.get('overlap_pct_area'))} | {fmt(g.get('class_conflicts'), 0)} | {fmt(g.get('abstained_area_ha'), 0)} | {fmt(g.get('classified_area_ha'), 0)} |")
    A("")
    A("Area by class (ha, block interior):")
    A("")
    A("| arm | Canola | Cereal | Legume |")
    A("|---|---|---|---|")
    for k in arms:
        ab = G[k].get("area_ha_by_class", {})
        A(f"| {k} | {fmt(ab.get('Canola'), 0)} | {fmt(ab.get('Cereal'), 0)} | {fmt(ab.get('Legume'), 0)} |")
    A("")
    NR = json.load(open(a.decision.replace(".json", "_norescue.json"))) if os.path.exists(a.decision.replace(".json", "_norescue.json")) else {}
    if NR:
        A("Merge-rule variant: `--cover-min 0` (never rescue an away view; drop it even when the owning tile has no decided polygon there). "
          "This is the right rule when tiles overlap by more than a paddock width, because the owner then saw the ground whole; "
          "it is wrong for the 3 km production lattice, where the owner's view is often the truncated one.")
        A("")
        A("| arm | rule | cut share (classified) | residual overlap % | classified/km2 | classified area ha | production matched >= 0.5 |")
        A("|---|---|---|---|---|---|---|")
        for k in arms:
            for lab, GG in (("rescue (default)", G), ("no rescue", NR)):
                g = GG.get(k)
                if g:
                    A(f"| {k} | {lab} | {fmt(g.get('cut_share_classified'), 3)} | {fmt(g.get('overlap_pct_area'))} | {fmt(g.get('classified_per_km2'))} | {fmt(g.get('classified_area_ha'), 0)} | {fmt(g.get('prod_matched_ge05'), 3)} |")
        A("")
    o2, o5, p9n, p9o2n = G.get("ov2000", {}), G.get("ov2500", {}), NR.get("p9", {}), NR.get("p9ov2000", {})
    A("**Findings.**")
    A(f"- *Extra overlap on the 3 km lattice does not reduce edge artefacts and costs more.* With 1 km / 2 km overlap, {fmt(o2.get('away_pct'), 0)} % / {fmt(o5.get('away_pct'), 0)} % of "
      "polygons are away views; with real classes the merge cannot resolve most of the extra pairs (one side abstained, or two truncated views of a paddock wider than "
      f"the overlap), so residual overlap is {fmt(o2.get('overlap_pct_area'))} % / {fmt(o5.get('overlap_pct_area'))} % of area (production {fmt(P.get('overlap_pct_area'))} %) and the raster-edge "
      f"cut share rises to {fmt(o2.get('cut_share_classified'), 3)} / {fmt(o5.get('cut_share_classified'), 3)} (production {fmt(P.get('cut_share_classified'), 3)}). Dropping every away view instead "
      f"(no rescue) brings overlap to {fmt(NR.get('ov2000', {}).get('overlap_pct_area'))} % / {fmt(NR.get('ov2500', {}).get('overlap_pct_area'))} % but discards "
      f"{fmt(100 * (1 - (NR.get('ov2000', {}).get('classified_area_ha') or 0) / (P.get('classified_area_ha') or 1)), 0)} % / "
      f"{fmt(100 * (1 - (NR.get('ov2500', {}).get('classified_area_ha') or 0) / (P.get('classified_area_ha') or 1)), 0)} % of classified area. SAM time per tile rises "
      f"from {fmt(P['cost'].get('sam_s_per_tile'))} to {fmt(o2['cost'].get('sam_s_per_tile'))} / {fmt(o5['cost'].get('sam_s_per_tile'))} s (more image in the canvas means more prompts and masks even with the prompt fix), "
      f"so the year costs {fmt(100 * o2['cost'].get('total_su_year', 0) / base, 0)} % / {fmt(100 * o5['cost'].get('total_su_year', 0) / base, 0)} % of the optimised 3 km run.")
    A(f"- *9 km tiles are cheaper and cleaner.* Per tile the stages cost more, but there are 6 x fewer tiles and the per-tile overhead of the datacube query dominates presegment and predict: "
      f"{fmt(C['cost'].get('total_su_year'), 0)} SU per year ({fmt(100 * C['cost'].get('total_su_year', 0) / base, 0)} % of optimised 3 km, {fmt(100 * C['cost'].get('total_su_year', 0) / ACTUAL_2024, 0)} % of 2024 as run) "
      f"with a raster-edge cut share of {fmt(C.get('cut_share_classified'), 3)} against {fmt(P.get('cut_share_classified'), 3)}, the same classified area "
      f"({fmt(C.get('classified_area_ha'), 0)} vs {fmt(P.get('classified_area_ha'), 0)} ha) and no class conflicts left after the merge. The national 9 km grid has "
      f"{fmt(C['cost'].get('n_tiles_national'), 0)} parents rather than 99,465 / 9 because blocks at the cropping margin are partial; a mixed 3 km / 9 km grid for those "
      "margins would recover most of the difference but needs a two-lattice merge, not built.")
    A(f"- *Overlap on top of 9 km buys little under the default merge* (cut share {fmt(G.get('p9ov1000', {}).get('cut_share_classified'), 3)} / {fmt(G.get('p9ov2000', {}).get('cut_share_classified'), 3)}, "
      f"more residual overlap, 40-50 % more cost). With no rescue, 11 km tiles on the 9 km lattice reach a cut share of {fmt(p9o2n.get('cut_share_classified'), 3)} and "
      f"{fmt(p9o2n.get('overlap_pct_area'))} % overlap, the cleanest geometry measured, but lose {fmt(100 * (1 - (p9o2n.get('classified_area_ha') or 0) / (P.get('classified_area_ha') or 1)), 0)} % of classified area "
      "to dropped views the owner never segmented. That is the option if seam-free geometry matters more than coverage.")
    A(f"- *Agreement with production is the same for every candidate* ({fmt(100 * (o2.get('prod_matched_ge05') or 0), 0)}-{fmt(100 * (C.get('prod_matched_ge05') or 0), 0)} % of production polygons at IoU >= 0.5, "
      f"{fmt(100 * (C.get('class_agreement_on_matches') or 0), 0)} % class agreement on matches): any change to what SAM sees changes about a quarter of the boundaries. §5 looks at which side is right where they differ.")
    A("")
    A("## 4. Agreement with the merged production block")
    A("")
    A("| arm | production polygons matched at IoU >= 0.5 | >= 0.7 | median IoU | arm polygons matched at >= 0.5 | >= 0.7 | class agreement on matched pairs | unmatched: production / arm |")
    A("|---|---|---|---|---|---|---|---|")
    for k in arms:
        g = G[k]
        A(f"| {k} | {fmt(g.get('prod_matched_ge05'), 3)} | {fmt(g.get('prod_matched_ge07'), 3)} | {fmt(g.get('prod_to_arm_iou_median'), 3)} | "
          f"{fmt(g.get('arm_matched_ge05'), 3)} | {fmt(g.get('arm_matched_ge07'), 3)} | {fmt(g.get('class_agreement_on_matches'), 3)} | "
          f"{fmt(g.get('n_prod_unmatched'), 0)} / {fmt(g.get('n_arm_unmatched'), 0)} |")
    A("")
    if V:
        A("## 5. Where production and the recommended arm disagree: visual review")
        A("")
        A(f"The 1.5 km cells with the most unmatched polygons (IoU < 0.5 in either direction) were rendered as "
          f"[Sentinel-2 true colour | composite | production merged | {R} merged] (`{a.fig_dir}/disagree_{R}.png`) and judged by eye "
          "against the imagery. Verdicts below are the model's reading of the images, not ground truth.")
        A("")
        A("| window | what differs | verdict |")
        A("|---|---|---|")
        for w in V.get("windows", []):
            A(f"| {w['window']} | {w['what']} | **{w['verdict']}** |")
        A("")
        if V.get("summary"):
            A(V["summary"])
            A("")
    A("## 6. What to run for the 2024 re-run")
    A("")
    A("```")
    for line in V.get("commands", ["# (fill in after the decision)"]):
        A(line)
    A("```")
    A("")
    A("## 7. Files")
    A("")
    A(f"- Figures: `{a.fig_dir}/` — `compare_*.png` (same windows, production merged vs {R} merged), `disagree_{R}.png` (the review windows).")
    A(f"- Example GeoPackages (block interior, EPSG:3577, crops schema + merge provenance columns): `examples/tile_geometry/prod_3km_merged.gpkg` and "
      f"`examples/tile_geometry/{R}_merged.gpkg`; the unmerged inputs beside them as `*_before.gpkg`.")
    A("- Numbers: `derived/benchksu/decision/geometry_decision.json`; per-arm merge and audit outputs under `derived/benchksu/decision/<arm>/`.")
    A("")
    with open(a.out, "w") as f:
        f.write("\n".join(L) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
