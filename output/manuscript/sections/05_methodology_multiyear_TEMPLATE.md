---
section: methodology
mode: template
note: TEMPLATE for review. Assumes the national 2017-2025 run has completed. Every XXX is a placeholder, not a result.
---

## 4.8 National multi-year run (2017-2025) [TEMPLATE]

The national map was produced for each season from 2017 to 2025 with the pipeline described in Sections 4.1 to 4.5. Every season used the same 15,968-tile grid, copied from the 2024 grid and relabelled by year. A fixed grid means a difference between seasons reflects the imagery rather than a change in where the pipeline looked. The adopted nine-index classifier, the presence gate and the cereal yield model were applied unchanged to every season. No model was refitted on a later season's data.

Each season was processed as the 2024 season was. Composites and segmentation were built per tile. SAM segmentation and classification then ran together in one GPU job per group of tiles. The per-tile outputs were merged and de-duplicated across the tile overlap band (Section 4.1).

ABS publishes sown area by SA2 for 2022, 2023 and 2024 only. The SA2 comparison of Section 4.6 was therefore repeated for those three seasons. For all nine seasons, mapped state totals were compared against ABARES state-level sown area, the second reference series in Section 3.3. ABARES figures still carrying a forecast flag were excluded.

Two cross-season checks do not depend on the classifier. Polygon geometric stability was measured by matching each season's polygons to the adjacent season's by IoU, as in the regional check (Section 4.7). Crop sequences were built for polygons matched across consecutive seasons at an IoU of at least 0.5. A sequence was only counted where both seasons carry a classification.
