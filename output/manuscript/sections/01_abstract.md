---
section: abstract
mode: full
word_target: 230
---

# Abstract

Australia's grains sector has no continent-wide, paddock-scale crop-species map built on recorded ground truth. Global products classify cropland generically and the closest Australian precedents are regional. We present a national field-level map that segments paddocks with the Segment Anything Model and classifies them as canola, cereal or legume. The classifier is a gradient-boosted model on spectral indices, trained on 2,194 Grains Research and Development Corporation National Variety Trial records. A presence gate decides whether each segmented paddock carries enough evidence of cropping to classify. Classified cereal paddocks also receive a calibrated yield estimate. The 2024 national map contains 1,158,824 segmented polygons, of which 39.9% carry a classification and the remainder an explicit abstain reason. We validated the map against independent Australian Bureau of Statistics (ABS) sown-area statistics across 151 censused Statistical Area Level 2 regions. Mapped canola composition tracks the official statistic with r = 0.77 and a median absolute error of 4.1 points; for comparison, ABS and a second official series disagree by a median 6.8%. The map over-calls crop-present area by 1.18 times, concentrated in cereal and legume rather than canola. The over-call is a presence-detection problem rather than a classification problem, which independent comparison against WorldCereal and the National Land Use Map supports. A phenology-shape presence gate, requiring green-up and senescence rather than amplitude alone, closed the area gap regionally but rejected real canola paddocks at a higher rate than cereal or legume, so we rejected it. This is a caution for presence-gate design in crop mapping.

## Highlights

- National 10 m map of 1.16 million paddocks in 3 crop classes, from recorded ground truth.
- Canola composition matches independent ABS statistics closely (r = 0.77).
- Map over-calls crop area 1.18x: a presence failure, not a classification failure.
- A more principled presence gate fixed area but broke canola recall; rejected.
- Independent WorldCereal/NLUM comparison corroborates the presence diagnosis.

## Graphical Abstract

*Reuses Fig. 1's elements: the six-stage pipeline schematic (Sentinel-2 time series → SAM
segmentation → paddock mask → spectral-index classifier → presence gate → cereal yield
calibration) above a small real-output map panel, coloured by predicted class with
unclassified (abstained) paddocks shown in grey rather than omitted. See
`output/figures/Fig01_hero.png` and its script `output/figures/scripts/Fig01_hero.py`.*
