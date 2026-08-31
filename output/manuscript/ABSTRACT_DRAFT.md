# Abstract

Australia's grains sector lacks a continent-wide, field-verified, paddock-scale crop-species map: existing global crop-mapping products classify cropland generically or at coarse crop-type resolution, and the closest Australian precedents are regional and do not train exclusively on field-verified ground truth. We present a national, polygon-level map that segments paddocks with the Segment Anything Model, classifies them into three groups (Canola, Cereal, Legume) with a gradient-boosted spectral-index classifier trained on 2,194 field-verified Grains Research and Development Corporation (GRDC) National Variety Trial records, applies a presence gate to decide whether a segmented paddock is classified at all, and attributes a calibrated Cereal yield to classified paddocks. The completed 2024 national map contains 1,346,582 segmented polygons; 48.4% carry a classification, and the remainder carry an explicit abstain reason rather than being silently dropped. Validated against independent Australian Bureau of Statistics (ABS) sown-area statistics across 133 censused Statistical Area Level 2 regions with no connection to the training pipeline, mapped canola composition tracks the official statistic closely (r = 0.82, median absolute error 5.5 percentage points), but the map over-calls crop-present area by 1.47-1.59x, concentrated almost entirely in Cereal and Legume and essentially absent from Canola — a presence-detection problem, not a classification problem, independently corroborated by comparison against the WorldCereal and National Land Use Map products. A more theoretically principled phenology-shape presence gate closed the area-inflation gap in a regional test but disproportionately rejected real canola paddocks, and was rejected. We report this as a transferable caution for presence-gate design in crop mapping generally, alongside the validated national dataset itself.

## Highlights

- National, field-verified, 10 m crop-species map of Australia: 1.35M paddocks, 3 classes.
- Canola composition matches independent ABS statistics closely (r=0.82).
- Map over-calls crop area 1.5x — a presence, not classification, failure.
- A more principled presence gate fixed area but broke canola recall; rejected.
- Independent WorldCereal/NLUM comparison corroborates the presence-detection diagnosis.

## Graphical Abstract

*Reuses Fig. 1's elements: the six-stage pipeline schematic (Sentinel-2 time series → SAM
segmentation → paddock mask → spectral-index classifier → presence gate → Cereal yield
calibration) above a small real-output map panel, coloured by predicted class with
unclassified (abstained) paddocks shown in grey rather than omitted. See
`output/figures/Fig01_hero.png` and its script `output/figures/scripts/Fig01_hero.py`.*
