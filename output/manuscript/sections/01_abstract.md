---
section: abstract
mode: full
word_target: 230
---

# Abstract

Australia's grains sector has no continent-wide, paddock-scale crop-species map built on recorded ground truth. Existing global products classify cropland generically, and the closest Australian precedents are regional. We present a national, field-level map that segments paddocks with the Segment Anything Model and classifies them into three groups: canola, cereal, and legume. The classifier is a gradient-boosted model built from spectral indices, trained on 2,194 Grains Research and Development Corporation (GRDC) National Variety Trial records. A presence gate then decides, for each segmented paddock, whether it carries enough evidence of cropping to classify at all. Classified cereal paddocks additionally receive a calibrated yield estimate. The completed 2024 national map contains 1,346,582 segmented polygons. 48.4% carry a classification, and the remainder carry an explicit abstain reason instead of being silently dropped. We validated the map against independent Australian Bureau of Statistics (ABS) sown-area statistics, with no connection to the training pipeline, across 133 censused Statistical Area Level 2 regions. Mapped canola composition tracks the official statistic closely (r = 0.82, median absolute error 5.5 percentage points). That error is below the 6.8% floor set by ABS's own disagreement with a second official series. The map over-calls crop-present area by 1.47 to 1.59 times, concentrated in cereal and legume rather than canola. This is a presence-detection problem, not a classification one, corroborated by independent comparison against WorldCereal and the National Land Use Map. A more theoretically principled phenology-shape presence gate closed the area-inflation gap in a regional test, but it disproportionately rejected real canola paddocks. We therefore rejected it, and report this as a transferable caution for presence-gate design in crop mapping generally.

## Highlights

- National, 10 m crop map of Australia built on recorded ground truth: 1.35M paddocks, 3 classes.
- Canola composition matches independent ABS statistics closely (r=0.82).
- Map over-calls crop area 1.5x — a presence, not classification, failure.
- A more principled presence gate fixed area but broke canola recall; rejected.
- Independent WorldCereal/NLUM comparison corroborates the presence diagnosis.

## Graphical Abstract

*Reuses Fig. 1's elements: the six-stage pipeline schematic (Sentinel-2 time series → SAM
segmentation → paddock mask → spectral-index classifier → presence gate → Cereal yield
calibration) above a small real-output map panel, coloured by predicted class with
unclassified (abstained) paddocks shown in grey rather than omitted. See
`output/figures/Fig01_hero.png` and its script `output/figures/scripts/Fig01_hero.py`.*
