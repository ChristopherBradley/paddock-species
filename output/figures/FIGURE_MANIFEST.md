# Figure Manifest — paddock-species

Venue: Remote Sensing of Environment (backup: Scientific Data). Source of truth: `output/PAPER_PLAN.md` §13.

8 figures planned (MAX_FIGURES=8, soft cap). All code-generated (pathway=`code`) — no diagram
needed an external image model; the pipeline schematic (Fig01a) was simple enough to draw
directly with matplotlib `FancyBboxPatch`/`FancyArrowPatch`.

**Status as of 2026-08-30**: 8 of 8 ready. Fig07's national panel is an explicit
`[PENDING: E8]` placeholder, not a finding — the user has deferred E8 pending a colleague
discussion of validation methodology, so this stays pending for the foreseeable draft.

## Consistency Issues

- **Fig03 regenerated 2026-08-30** — the old `confusion_group3_reviewed.png` (flagged by
  `PAPER_PLAN.md` §13 as needing a numeric check) is replaced by `Fig03_confusion_matrices.png`,
  built directly from the raw confusion counts in `output/arms/GROUP3_reviewed.md`. Resolved.
- **PAPER_PLAN.md §13's Fig04 caption draft said "five abstain reasons"** — measured directly
  from `national_2024_crops.gpkg` (`GROUP BY abstain_reason`), there are only **four**:
  `area_below_min` (339,043), `no_crop_signal` (269,134), `unsegmented_blob` (48,016),
  `too_few_observations` (39,623). `PAPER_PLAN.md` should be corrected to say four, not five.
- **PAPER_PLAN.md §24's "132 well-covered SA2s" is off by one against a direct re-parse.**
  Re-deriving the cover>=50% subset from `ABS_COMPARISON_NATIONAL.md`'s own published table
  (Fig02's data source) gives **133**, not 132. Two SA2s display exactly "50%" after integer
  rounding (Mildura Surrounds, Millmerran); the discrepancy is almost certainly one of these
  sitting at e.g. 49.6% unrounded, just under `abs_compare.py`'s `--min-cover 0.5` cutoff,
  which only the unrounded figure (not in the markdown) can resolve. Fig02 reports 133 as
  measured; treat "132" in prose elsewhere as approximate pending a check against the
  script's own intermediate output.
- **Two national2024 GeoPackages exist and are easy to conflate**: `national_2024_crops.gpkg`
  (1,346,582 rows, columns `pred`/`abstain_reason`, includes abstained polygons — this is
  what Fig04 uses and what PAPER_PLAN's "1,346,582" figure refers to) vs.
  `national_2024_crops_classified.gpkg` (650,766 rows, column `predicted_crop_type`, a
  DERIVED subset with abstained rows already dropped). Do not use the second file for any
  claim about abstain rate or total polygon count.

## Registry

| ID | Title | Type | Pathway | Priority | Status | Data Source | Script | Notes |
|---|---|---|---|---|---|---|---|---|
| Fig01 | Pipeline overview + example output | hybrid (schematic + map) | code | HIGH | ready | `map100/consensus_crops.gpkg` (`crop_2024`) | `scripts/Fig01_hero.py` | 12km x 12km window, Riverina; 361 polygons, all 4 classes present |
| Fig02 | Study area map | study-area map | code | HIGH | ready | `national2024/aois.csv`, `map100/regions.csv`, `abs/SA2_2021_AUST_GDA2020.shp`, `ABS_COMPARISON_NATIONAL.md` | `scripts/Fig02_study_area.py` | EPSG:3577; 133 validation SA2s (see Consistency Issues) |
| Fig03 | Classifier confusion matrices (temporal + spatial) | confusion matrix | code | HIGH | ready | `output/arms/GROUP3_reviewed.md` | `scripts/Fig03_confusion_matrices.py` | Regenerated 2026-08-30 from raw counts; matches 0.821/0.823 exactly |
| Fig04 | National 2024 map, full continent | choropleth/density map | code | HIGH | ready | `national2024/national_2024_crops.gpkg` (via extracted centroid CSV) | `scripts/Fig04_national_map.py` | EPSG:3577; 3km majority-class grid, NOT per-polygon vectors (see script docstring) |
| Fig05 | ABS validation: composition and area-inflation | grouped bar + decomposition | code | HIGH | ready (prior pass) | `ABS_COMPARISON_100km.md`, `ABS_COMPARISON_NATIONAL.md` | `scripts/Fig05_abs_validation.py` | numbers copied verbatim from those reports |
| Fig06 | Presence-gate trade-off | grouped bar | code | HIGH | ready (prior pass) | `PHENOLOGY_GATE.md` | `scripts/Fig06_gate_tradeoff.py` | — |
| Fig07 | Multi-year regional evidence + national placeholder | line/bar + reserved panel | code | MEDIUM | ready (regional); **[PENDING: E8]** (national panel) | `ABS_COMPARISON_100km.md` | `scripts/Fig07_multiyear_regional.py` | do not fill panel (b) until the national multi-year run lands |
| Fig08 | Cereal yield model + ABS calibration | grouped bar + line | code | MEDIUM | ready (prior pass) | `YIELD_cereal_pooled.md`, `YIELD_CALIBRATION.md` | `scripts/Fig08_yield_summary.py` | aggregate-only by design — no per-trial scatter (GRDC NDA) |
