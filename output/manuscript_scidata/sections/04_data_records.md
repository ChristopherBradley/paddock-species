---
section: data_records
mode: full
word_target: 800
---

# Data Records

The dataset is released as two products, both in GeoPackage format (EPSG:3577, GDA94 / Australian Albers), described below. **[PENDING — data deposit]**: both products will be assigned a persistent identifier (DOI) at a public repository before submission; this section will be updated with the resolved identifier(s).

## National 2024 release

Fig. 2 shows the national tile coverage, the 100 km Riverina regional block, and the SA2 regions used for ABS validation (Technical Validation); Fig. 4 shows the released classes at national extent, rasterised to a 3 km majority-class grid for legibility (individual paddocks are far smaller than one printed pixel at national scale — Fig. 4 is a density visualization for orientation, not the polygon layer itself, which is the actual data record).

The primary product is a single national GeoPackage, 2.8 GB, containing 1,346,582 segmented polygons across 99,465 processed tiles (98.9% of the national extent carrying non-trivial agricultural probability for one of the three target crop groups, per NLUM). Each row is one segmented paddock polygon and carries:

- **`pred`** — the predicted class (`Canola`, `Cereal`, or `Legume`) where classified, or null where the polygon did not clear the presence gate.
- **`abstain_reason`** — populated only where `pred` is null; one of four values: `area_below_min` (339,043 polygons), `no_crop_signal` (269,134), `unsegmented_blob` (48,016), or `too_few_observations` (39,623). No polygon is silently dropped: every row in the release carries either a class or a named reason it was not classified.
- **`confidence`** — the classifier's predicted-class probability; null where `pred` is null, since a polygon that did not clear the presence gate was never scored by the classifier.
- **`ndvi_amp`** — the NDVI amplitude (90th minus 10th percentile) used by the presence gate; shipped on every polygon regardless of gate outcome, so a downstream user can apply a stricter threshold than the shipped 0.35 cutoff without re-deriving the underlying signal.
- **`yield_tha_raw`**, **`yield_tha_calibrated`** — populated only where `pred = Cereal`; raw (NVT-trial-equivalent) and ABS-calibrated Cereal yield in tonnes per hectare, respectively (Methods). No yield fields are populated for Canola or Legume polygons.
- **`geometry`** — the segmented paddock polygon.

Of the 1,346,582 polygons, 48.4% (34.4% of total mapped area) carry a classification; the remaining 51.6% carry one of the four abstain reasons above. A derived, classified-only subset (650,766 rows, dropping abstained polygons and the `abstain_reason`/`ndvi_amp` fields) is also provided for users who need only classified paddocks; it should not be used for any claim about abstain rate, total polygon count, or total mapped area, since it silently removes exactly the rows those claims depend on.

## Nine-year regional companion (2017-2025, 100 km, Riverina)

A 100 km × 100 km block in the Riverina, New South Wales, processed with the identical pipeline across all nine seasons 2017-2025, is released as nine per-year GeoPackages (one per season) plus a consensus GeoPackage linking each paddock's identity across years (union-find on inter-year IoU ≥ 0.5, paddock outline taken from the season in which it was largest). This product carries the same per-polygon fields as the national release, plus year and a stability flag (found in ≥5 of 9 years). It exists specifically to demonstrate multi-year pipeline behaviour — polygon geometric stability, year-to-year coverage — ahead of the national multi-year release described below, and should not be treated as a substitute for national-extent coverage in any of the nine years it spans.

## Planned update: national multi-year release (2017-2023, 2025)

A national-scale re-run of the identical pipeline across all nine seasons (2017-2025) is in progress at the time of this Data Descriptor, with two of nine seasons (2023, 2024) complete. Once complete, per-year national GeoPackages with the same schema as the 2024 release above will be added as a dataset update, and this section will be revised to describe them. **[PENDING: national 2017-2025 multi-year run]** — no national multi-year files exist in the current release.

## Model artifacts

The classifier (`group3_map.joblib`) and Cereal yield model (`cereal_yield.joblib`) used to produce the national and regional products above are released alongside the data (Code Availability), so that a user can verify or re-derive predictions from the same 51-feature paddock-median input used to generate this release.
