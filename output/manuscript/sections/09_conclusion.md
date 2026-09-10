---
section: conclusion
mode: full
word_target: 400
---

# 8. Conclusion

We have presented a national, field-level, three-class crop-species map of Australia at 10 m resolution, built end-to-end from open Sentinel-2 imagery and 2,194 recorded GRDC National Variety Trial records. To our knowledge, this is the first product to combine continent-wide coverage, paddock-scale resolution and training on field-recorded sowings for this problem. The completed 2024 national map contains XXX segmented polygons, each carrying a predicted class or one of four abstain reasons, a confidence and, for cereal, a raw and an ABS-calibrated yield estimate. We validated the map against independent ABS sown-area statistics with no connection to the training pipeline. Mapped canola composition tracks the official statistic closely (r = XXX), so the classifier and segmentation pipeline are sound where they can be checked most directly.

The map's most consequential limitation is a XXXx area over-call, reproduced independently at national and regional scale and corroborated by independent spatial comparison against WorldCereal and the National Land Use Map. This is a presence-detection problem rather than a species-classification problem, and the distinction matters for how the map is used as well as for diagnosis. A more principled fix, a phenology-shape presence gate, worked on its own target metric but harmed the map's best-classified crop, so we rejected it. Evaluating a stricter presence criterion on a single pooled metric can conceal which sub-population pays its cost, and this is a caution for presence-gate design in crop mapping generally.

Two threads remain open. First, the national multi-year extension of this pipeline (2017-2023, 2025) is in progress at the time of this draft, following a discussion of validation methodology and the multi-year regional approach with project colleagues that this manuscript helped inform. The multi-year results in this paper are regional (100 km, nine seasons) until that extension completes. Second, the legume over-prediction (XXX% mapped against XXX% ABS) has no established mechanism and is the largest unresolved classification error in the map.
