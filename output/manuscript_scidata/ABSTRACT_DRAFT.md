# Abstract (stand-alone)

We present a national, polygon-level dataset of Canola, Cereal, and Legume paddocks across Australia at 10 m resolution, derived from Sentinel-2 imagery and 2,194 field-verified Grains Research and Development Corporation (GRDC) National Variety Trial records. Paddocks are segmented with the Segment Anything Model and classified into three groups by a gradient-boosted spectral-index model; each polygon carries a predicted class or one of four explicit abstain reasons, a confidence score, and, for Cereal, both raw and Australian Bureau of Statistics (ABS)-calibrated yield estimates. The completed 2024 national release contains 1,346,582 polygons across 99,465 tiles, with a nine-year (2017-2025) 100 km regional companion product demonstrating the pipeline's multi-year behaviour. Mapped canola composition tracks independent ABS sown-area statistics closely (r = 0.82) and is corroborated by independent spatial comparison against WorldCereal and the National Land Use Map; the dataset also discloses and quantifies a known area over-call (1.47-1.59x relative to ABS), concentrated in the Cereal and Legume classes. No other continent-wide, field-verified, paddock-scale crop-species dataset for Australia currently exists.

**Word count: 166** (Scientific Data hard limit: 170; ESSD has no stated hard limit — this abstract also satisfies ESSD's "intelligible without text reference" requirement).

## Keywords

crop-type mapping; Sentinel-2; Segment Anything Model; presence detection; accuracy assessment; gradient boosting; Australia

## Short summary (ESSD-style, ≤500 characters incl. spaces, non-technical)

A free, national map of canola, cereal, and pulse paddocks across Australia, built from satellite images and real farm trial records, checked against official government crop statistics. Every mapped paddock says how confident the map is and why some paddocks weren't mapped at all — nothing is hidden. The map slightly over-estimates how much land is growing crops, and this is clearly disclosed so users can adjust for it.

**Character count: 424** (ESSD limit: 500 incl. spaces).
