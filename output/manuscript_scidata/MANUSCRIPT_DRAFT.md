# Mapping Canola, Cereal, and Legume Paddocks Across Australia at 10 m

**Manuscript type**: Data Descriptor — Nature Scientific Data (backup: Data Description article, Earth System Science Data / ESSD) | **Draft status**: PARTIAL (see DRAFT_README.md) | **Date**: 2026-09-04, reviewed 2026-09-04 (paper-review-loop round 1)

---

---

# Abstract

We present a national, polygon-level dataset of Canola, Cereal, and Legume paddocks across Australia at 10 m resolution, derived from Sentinel-2 imagery and 2,194 trial records from the Grains Research and Development Corporation (GRDC) National Variety Trials. Paddocks are segmented with the Segment Anything Model and classified into three groups by a gradient-boosted spectral-index model. Each polygon carries a predicted class, a confidence score, and yield estimate. The completed 2024 national release contains XXX polygons. [Will add some details about the time-series here once it's done]. The total canola area agrees with independent ABS sown-area statistics [to some degree]. [It agrees with WorldCereal to some other degree]. [Did we manage to reduce the overcall by fixing the overlap issue?]. [Would be nice if we could say we quantitatively compared against Fields of the World and our version was much better. If this isn't possible then I guess we can just say we did this qualitatively]. This is the first publicly available continental map of cropping polygons with species classifications at 10 m resolution for Australia.

## Keywords

crop-type mapping; Sentinel-2; Segment Anything Model; presence detection; accuracy assessment; gradient boosting; Australia

---

---

# Background & Summary

[I'd like the first sentence to just focus on the positives of the grains industry, not mentioning the lack of polygon data. Then maybe the second sentence talks about the importance of having data to track this, for economic and research activities. Then close the paragraph by explaining that this dataset doesn't yet exist and is a gap we can close.] Australia's grains sector — wheat, barley, canola, and pulse/legume crops — is a major export industry with no continent-wide, field-verified, species-resolved crop map publicly available at paddock scale. Official production and area statistics from the Australian Bureau of Statistics (ABS) and the Australian Bureau of Agricultural and Resource Economics and Sciences (ABARES) are available only at coarse administrative-region granularity, with no spatial detail below the Statistical Area Level 2 (SA2) or state level, and the two agencies disagree with each other by a median 6.8% on national sown area — the practical floor against which any finer-grained dataset should be judged. A spatially explicit, species-resolved dataset lets growers, agronomists, and policy analysts see where each crop is actually grown, at paddock scale, rather than inferring it from a regional aggregate.

[Focus on what does exist, not what does not exist where possible. I think the last sentence in each paragraph is a nice place to tie back to what does not exist and the novelty of our work, but I prefer if the earlier sentences just focus on what does exist.] Existing global crop-mapping products, including WorldCereal (Van Tricht et al., 2023), classify cropland generically or at coarse crop-type resolution and are built around growing-calendar assumptions that do not match Australia's Southern Hemisphere, canola-and-pulse-rotation grains system. [Should be clear about the availability of these. Can other researchers download these datasets? I'm planning to release my polygons, so that could be a valuable advantage of my dataset, as well as being national and a 9 year time-series.] The two closest Australian precedents — an in-season Sentinel-2 classifier for six classes in Western Australia (Sharma et al., 2026) and a Sentinel-1/Sentinel-2/MODIS fusion classifier for cereals-versus-canola in the Murray-Darling Basin (Al-Shammari et al., 2024) — are both regional, and both train on either another model's output or opportunistic harvester-derived labels rather than field-verified ground truth.

[Focus on what my dataset does, not what other datasets don't do. I don't want my paper sounding like a political argument of bashing each others work.] This dataset closes that specific gap. It is continent-wide, trains on GRDC National Variety Trial records and segments paddocks with the Segment Anything Model (SAM; Kirillov et al., 2023). Each polygon is classified into one of three broad groups: canola; cereals (wheat, barley and oat), and legumes (chickpea, faba bean, field pea, lentil and lupin) by a gradient-boosted spectral-index model. Every polygon carries either a predicted class and confidence, predicted yield, and extra attributes such as [is there a better term for this?] green-up intensity that can be used to filter out polygons unlikely to have grown a crop in that year.

The completed 2024 national release contains XXX segmented polygons. A nine-year (2017-2025), 100 km regional companion product, covering a mixed-cropping district of the Riverina, New South Wales, demonstrates the identical pipeline's behaviour across multiple growing seasons, including polygon geometric stability and year-to-year coverage. A national multi-year extension (2017-2023, 2025), applying the identical pipeline nationally across all nine seasons is released at XXX. Results of the national multi-year product is described in this paper.

We validated the total cropping area against independent ABS sown-area statistics, as well as WorldCereal and the National Land Use Map (NLUM). [Way too many adjectives and double banger words, see style guide in the shelterbelts project.] This dataset provides the first continent-wide, paddock-scale, field-verified crop-species product for the Australian grains sector, together with a quantified, disclosed characterization of its own known limitations — principally an area over-call relative to ABS, concentrated in the Cereal and Legume classes — reported in full in Technical Validation below.

---

---

# Methods

Fig. 1 gives a pipeline overview alongside an example map which is a useful orientation to the stage-by-stage description below.

## Study extent and temporal scope

The national 2024 release covers continent-wide Australia: 99,465 processed tiles, restricted to the extent that NLUM v7 indicates carries non-trivial agricultural probability for one of the three target crop groups. The national map was processed using the same algorithm for all 9 years of 2017-2025. All spatial processing and reported geometry use EPSG:3577 (GDA94 / Australian Albers Equal Area). [Presumably we have two main units: number of paddock polygons, and area]

## Data sources

Sentinel-2 surface-reflectance imagery was accessed via Digital Earth Australia's Analysis Ready Data product (`ga_s2am/bm/cm_ard_3`) through the National Computational Infrastructure's datacube. Ground truth for classifier and yield-model training is drawn from the Grains Research and Development Corporation (GRDC) National Variety Trial (NVT) obtained on XXX date. This dataset contained XXX trial sites, which was reduced to XXX locations where just a single crop group was grown (canola, cereals, or legumes). [Should move this to the data availability statement. Don't need to reproduce twice.] The dataset is covered by a data-use agreement but can be requested from the GRDC via this form (XXX).

 Independent validation uses ABS sown-area statistics and ABARES production statistics [What is the SA2 level? Do we describe that abbreviation somewhere?]. National Land Use Map (NLUM) v7 250 m per-commodity agricultural probability surfaces (2020-21) were used to mask the segmentation to tiles with non-null cropping probability. It was also used to compare the ratios of land area of the resulting crop groups. [This sentence and everything after probably belongs in the following segmentation section, rather than "data sources"] Paddock boundaries were delineated with the Segment Anything Model (`vit_h` checkpoint, stock parameters; Kirillov et al., 2023) via the SAMGeo/PaddockTS wrapper. The tile size used was 9km with 350m overlap and polygons were merged if any polygons overlapped between tiles. A 3km tile size was also tested which identified some additional cropping polygons, and some additional non-cropping polygons. The 9km tile size was chosen as it visually appeared to be correct more often, and better matched the independent validation cropping area totals. Further work could investigate using multiple tile sizes and offsets to find additional polygons that are missed from the current product. 
 [Something about how paddocks were marked as abstained]

## Segmentation

Segmented polygons were retained only within a 5-300 ha area range with a compactness ratio (perimeter / sqrt(area)) of at most 8. 

[I think this sentence is based on data from Agriwebb? So needs to be removed.] This is estimated to retain 77.9% of known crop paddocks in validation while rejecting 65% of pasture polygons, at a cost of excluding 22% of real crop paddocks that fall outside the size/shape mask.

## Feature construction

[This sentence should be split into multiple sentences of length 10-25 words.]
Fifty-one paddock-median spectral features were computed per retained polygon: spatial medians over 10 m-eroded, cloud-masked paddock pixels per observation date, then temporal medians across dates within 20-day day-of-year bins across the growing season, from three per-pixel indices — NDVI, a canola-specific flowering index following the general approach of Ashourloo et al. (2019), and a chlorophyll-fluorescence-related index.

## Labelling

GRDC NVT points were matched to their enclosing [I thought we removed the nearest plausible function, so it had to be enclosing?] SAM polygon, corresponding to the surrounding paddock around the trial site. Trials that had multiple different crop groups within the same paddock were removed, as that made the category of the surrounding paddock unclear. [Have we already specified which species are in which groups? If so, I don't think we need to respecify it here. If not, then we should specify it here] We reduced the initial 9 crop types into three broad groups, partly because this reduced conflicts within a paddock increasing the sample size by [is this number correct?] 69%, and partly because crop types within the same broad group were highly spectrally similar. This meant that training a 9-species classifier resulted in an F1 of only 32%, compared to the final F1 of [is this number from the latest 153 index model?] 82% in the 3-species classifier. 

[I think my hand-review just helped establish the rules to ignore conflicting categories. I didn't actually relabel anything.] [I think we removed this remapping rule in the latest version?].

## Classification

Species-group labels are predicted by a `HistGradientBoostingClassifier` operating on the [Don't like the term hand-built. Need to update this to the actual number in the latest model] XXX spectral features described above, evaluated both temporally (training on trials sown 2022 or earlier, testing on 543 fixed trials sown 2023-2024) and spatially (5-fold `GroupKFold` on trial site). We trialled a Presto model, random forest, [anything else we trialled?] but found the HistGradientBoostingClassifier to work best.

The classifier is trained class-balanced, with geographic location deliberately excluded. [Should we have tried tuning the hyperparameters to better predict the NVT data?] Hyperparameters follow scikit-learn's `HistGradientBoostingClassifier` defaults with no additional tuning beyond the feature-set and label-scheme decisions described above.


## Presence gating

[I don't like the word 'shipped' in a paper. This sentence can probably be moved to the end of the yield estimation paragraph.]
We included a presence gate based on NDVI amplitude (90th minus 10th percentile) at a threshold of 0.35. It is fitted presence-only on the full 3,439 known-sown NVT trials with a held-out recall of 91.6%. [Don't think the phenology gate is interesting enough to write about if we didn't include it in the final dataset.] 

## Yield estimation

Cereal yield (pooled wheat, barley, and oat) is estimated by a `HistGradientBoostingRegressor` on the same [wrong feature count] XXX-feature contract, calibrated to ABS with a single national multiplicative factor [Did this change with the latest model?] (XXX) fit on one year of ABS data and checked against two held-out years [Guessing also wrong?](+XXX% to +XXX% error). Both raw (NVT-trial-equivalent) and ABS-calibrated yield columns are provided with each cereal polygon. We did not provide yield estimates for canola and legumes as these predictions were no better than just taking a state-year average. [Is this correct?] We found that Sentinel-1 improved canola yield estimates, but did not adopt this for the national runs due to compute constraints.

[A graph showing the cereal yield correlation would be good here.]

## Validation protocol

[Keep sentences under 25 words, stick to just full stops, commas and parenthesis wher possible]
Composition and area were compared against ABS sown-area statistics across SA2s where the mapped footprint covers at least 50% of the [What is SA2?] SA2 (133 SA2s nationally). [What an awful word. Can we avoid hyphens where possible?] [Don't like the word genuine]. The national map was also compared against WorldCereal 2021 and NLUM 250 m per-commodity probability surfaces, on a stratified random sample of 250,000 of the [out-of-date I think] 1,346,582 national paddock centroids. [Given this is the methods section, I wouldn't expect the results to be here anyway. I think it's only worth mentioning something is reported somewhere else, if it would otherwise be expected to be reported here]

## Multi-year pipeline

[I want to just prepare the final paper as closely as possible now, and then slot in new numbers once I do the complete run. There's no point describing an initial pilot run like this paragraph.]
We ran the full pipeline on every year from 2017-2025. 

---

# Data Records

[Product 1: 9x national gpkgs. Product 2: a single merged gpkg showing consensus polygons with metadata for those polygons showing the crop type in each year from 2017-2025. Should update the rest of this data records section accordingly.]
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

---

---

# Technical Validation

## Classifier accuracy

[Need to update all of these results based on the latest model.]
The classifier reaches macro F1 0.821 under temporal transfer (training on trials sown 2022 or earlier, testing on 543 fixed trials sown 2023-2024) and 0.823 under spatial transfer (5-fold `GroupKFold` on trial site), against a 543-trial fixed test set common to both splits. Canola is detected at 89.0% recall at a 5% false-positive rate (average precision 0.944, ROC AUC 0.965).

| Split (macro F1) | Class | Precision | Recall | F1 | n |
|---|---|---|---|---|---|
| Temporal (0.821) | Canola | 0.94 | 0.83 | 0.88 | 155 |
| | Cereal | 0.89 | 0.90 | 0.90 | 279 |
| | Legume | 0.65 | 0.73 | 0.69 | 109 |
| Spatial (0.823) | Canola | 0.91 | 0.86 | 0.88 | 155 |
| | Cereal | 0.89 | 0.91 | 0.90 | 279 |
| | Legume | 0.68 | 0.70 | 0.69 | 109 |

Legume is the floor in both splits, driven predominantly by Cereal paddocks misclassified as Legume (23 of 279 true Cereal paddocks under temporal transfer, 22 of 279 under spatial transfer) rather than the reverse. Fig. 3 shows both confusion matrices directly.

## Composition and area validation against ABS

Validated against ABS sown-area statistics across the 133 SA2s where the mapped footprint covers at least 50% of the SA2, mapped canola composition — its share of total mapped crop area — tracks the ABS canola share closely: r = 0.82, median absolute error 5.5 percentage points, below the 6.8% median disagreement between ABS and ABARES that this dataset's validation treats as the accuracy floor for any map-versus-official-statistic comparison (ABS and ABARES are two official series that themselves disagree by that amount; no validation number tighter than this should be read as more precise than the reference data allows).

The 6.8% floor itself is derived directly from ABS and ABARES's own mutual disagreement, shown here for the three years spanning this dataset's national release:

| Year | Class | ABS area (ha) | ABARES area (ha) | ABS/ABARES ratio |
|---|---|---|---|---|
| 2022 | Canola | 4,356,211 | 3,900,000 | 1.12 |
| 2022 | Cereal | 16,732,981 | 17,229,002 | 0.97 |
| 2022 | Legume | 1,849,231 | 2,154,200 | 0.86 |
| 2023 | Canola | 3,714,767 | 3,507,000 | 1.06 |
| 2023 | Cereal | 14,508,085 | 16,633,296 | 0.87 |
| 2023 | Legume | 1,697,392 | 2,250,103 | 0.75 |
| 2024 | Canola | 3,671,196 | 3,438,500 | 1.07 |
| 2024 | Cereal | 17,627,545 | 17,733,000 | 0.99 |
| 2024 | Legume | 3,340,448 | 3,183,800 | 1.05 |

Neither ABS nor ABARES is ground truth; the median disagreement between them (6.8%) is the practical precision floor this dataset's own validation is measured against throughout.

The dataset's total mapped area, however, over-calls crop-present land relative to ABS by 1.47x nationally and, independently, 1.59x in the 100 km regional companion — the same mechanism reproduced at two spatial scales.

| Class | ABS share | Diluted share | Mapped share | Absorbed (points) |
|---|---|---|---|---|
| Canola | 19.7% | 13.4% | 13.1% | −0.3 |
| Cereal | 67.3% | 45.8% | 69.0% | +23.2 |
| Legume | 8.7% | 5.9% | 16.7% | +10.8 |

`Diluted` is the share ABS would imply if the area over-call were spread proportionally across classes; `absorbed` is the excess mapped area a class actually carries beyond that. The over-call is concentrated almost entirely in Cereal and Legume and essentially absent from Canola: once divided out, canola composition matches almost exactly (13.1% mapped versus a diluted expectation of 13.4%). This pattern — canola composition matching closely, total area over-calling, and the over-call concentrated in Cereal/Legume rather than uniform — indicates the dataset's dominant source of disagreement with ABS is presence detection (calling too much land crop-present) rather than species misclassification, and this diagnosis reproduces independently at national and 100 km-regional scale with the same class signature both times. Users needing area-accurate rather than composition-accurate output can filter toward a stricter subset using the `ndvi_amp` and `abstain_reason` fields shipped on every polygon (Data Records; Usage Notes).

A distinct, unexplained discrepancy sits on top of the area over-call: Legume is mapped at 18.4% of classified area nationally versus an ABS share of 8.7%. An argmax-versus-mean-predicted-probability check, area-weighted over the same national polygons, rules out a decision-rule artefact:

| Class | Argmax share | Mean probability | ABS |
|---|---|---|---|
| Canola | 14.0% | 14.2% | 19.7% |
| Cereal | 67.6% | 67.1% | 67.3% |
| Legume | 18.4% | 18.7% | 8.7% |

Argmax and mean-probability shares agree closely for every class, including Legume — a gap between the two columns would indicate a decision-rule problem (for example, a systematic tie-break); agreement instead indicates the classifier genuinely, if wrongly, favours Legume at this rate. The mechanism is not established and is disclosed as an open limitation (Usage Notes).

**Sensitivity of area to the presence-gate threshold.** The shipped gate uses an NDVI-amplitude threshold of 0.35; the same national polygons re-scored at five alternative thresholds show the area/composition trade-off directly, reported here as a sensitivity characterization of the released data, not as a fitting procedure against ABS (fitting the gate to minimize ABS error would make ABS a training target and destroy its value as an independent check):

| Threshold | Classified area (ha) | Canola share error (pts) | Legume share error (pts) |
|---|---|---|---|
| 0.25 | 25,509,480 | 5.9 | 9.5 |
| 0.30 | 25,509,480 | 5.9 | 9.5 |
| 0.35 (shipped) | 25,509,480 | 5.9 | 9.5 |
| 0.40 | 23,528,343 | 5.8 | 8.9 |
| 0.45 | 21,374,494 | 5.5 | 8.8 |
| 0.50 | 19,015,341 | 4.8 | 9.3 |

Composition error is comparatively insensitive to threshold choice across this range, while classified area is not — consistent with the diagnosis above that the dominant disagreement with ABS is presence detection rather than species discrimination: tightening the presence criterion changes how much land is called crop-present far more than it changes which crop that land is called. Fig. 5 shows the composition-versus-ABS comparison and the area-over-call decomposition together.

## Independent spatial corroboration: WorldCereal and NLUM

The national map was additionally compared, at the pixel level, against two products with no connection to this dataset's training or ABS-validation pipeline: WorldCereal 2021 v100 and NLUM v7 250 m per-commodity probability surfaces, on a stratified sample of 250,000 of the 1,346,582 national paddock centroids. Both comparisons carry a three-year reference-year mismatch (2021 versus this release's 2024) and are reported with that caveat.

Against WorldCereal's `temporarycrops` layer, classified-versus-abstained presence agrees at 73.1% overall, symmetrically (73.0% of abstained points also called no-crop by WorldCereal; 73.2% of classified points also called crop). Against WorldCereal's `wintercereals` layer, Cereal-class agreement is markedly weaker (49.6%, n=82,411) — a real disagreement between two independent products, not sampling noise, though neither product is ground truth. NLUM's per-commodity probability surfaces, covering all three target groups directly, show a consistent enrichment pattern: median NLUM oilseed probability at Canola-classified points is 6.4 times the abstained-point median (the largest ratio in its column), and median legume probability at Legume-classified points is 1.6 times the abstained-point median (likewise the largest in its column). NLUM's grazing-probability layer independently corroborates the presence-gate mechanism: median grazing probability is 33.8% at abstained points versus 10.8% at classified points, consistent with abstained land preferentially overlapping land NLUM independently rates as probable grazing country.

## Cereal yield validation

The Cereal yield model reaches a spatial-transfer RMSE of 1.21 t/ha (30.4% of the 3.97 t/ha median observed yield).

| Split | Arm | n | R² | RMSE (t/ha) |
|---|---|---|---|---|
| Temporal (train ≤2022, test 2023-24) | Year+state baseline | 279 | −0.643 | 2.111 |
| | Satellite features | 279 | 0.471 | 1.197 |
| | Satellite + year/state | 279 | 0.486 | 1.181 |
| Spatial (5-fold GroupKFold on site) | Year+state baseline | 1,119 | 0.294 | 1.473 |
| | Satellite features | 1,119 | 0.526 | 1.207 |
| | Satellite + year/state | 1,119 | 0.577 | 1.140 |

The ABS calibration factor (0.6248, fit on one year of ABS data) checks to within +3.1% to +18.1% of ABS-implied yield on two held-out years. Fig. 8 shows model performance by arm and the calibration check together.

## Multi-year regional evidence

Across the nine-year (2017-2025), 100 km regional companion product, classified share ranges from 52.5% (2018) and 59.0% (2017) up to 78.5% (2025); mean NDVI amplitude is correspondingly lowest in 2018 (0.42) and 2017 (0.46) against 0.60-0.62 in 2024-2025, attributable respectively to a documented 2018 drought and Sentinel-2B's mid-2017 operational start (reduced early-mission revisit frequency and cloud-gap robustness). Polygon geometric stability across the same nine years — independent of any spectral classification — peaks in the 25-100 ha range (the range real paddocks predominantly occupy: median found in 7 of 9 years, median IoU 0.84) and falls at both smaller and larger extremes, an independent, purely geometric corroboration of the area/compactness presence mask (Methods). Fig. 7 shows the year-by-year regional evidence; its national panel is explicitly reserved and left blank pending the national multi-year release (Data Records), not fabricated as a null result. This regional evidence is suggestive of, but does not establish, similar national multi-year behaviour; the national multi-year release is the direct test of that question and is in progress, not yet complete.

**[PENDING — national 2017-2025 multi-year run]**: national multi-year totals, per-year national coverage, and any claim that the single-national-season (2024) validation above generalizes nationally across seasons are not reported here ahead of that release.

---

---

# Usage Notes

**Filtering toward area-accurate rather than composition-accurate output.** Because every polygon carries either a predicted class or one of four explicit abstain reasons, plus `ndvi_amp` and classifier `confidence`, a user who needs area-accurate rather than composition-accurate output already has the information required to filter toward a tighter, more conservative view of the dataset without waiting for a future methodological revision. Raising the `ndvi_amp` threshold above the shipped 0.35 cutoff trades completeness for a lower area over-call; Technical Validation's sensitivity table quantifies this trade-off at several thresholds and should be consulted before choosing a project-specific cutoff. This design was itself informed by an earlier failure mode: an initial design considered building an explicit absence-labelled "non-crop" class from presence-only farmer-recorded grazing records, and was abandoned after finding that 78.5% of a deliberately hard stratum of grazing paddocks passed the same crop-presence test as known crop paddocks — presence-only farmer records could not be reliably inverted into confirmed absence labels. The abstain-reason and confidence fields shipped instead are this dataset's considered response: rather than force a binary crop/non-crop decision the available negative-label data could not support reliably, every polygon reports its uncertainty explicitly as a first-class field.

**The area over-call is the single most consequential characteristic to account for.** Users computing absolute crop area from this dataset (rather than composition/share, which is comparatively well validated) should expect a 1.47-1.59x over-call relative to ABS unless they filter using the fields above; the over-call is concentrated in Cereal and Legume and essentially absent from Canola (Technical Validation), so composition estimates that rely primarily on Canola are the most directly trustworthy use of this dataset as released.

**Cereal yield: use both columns, never only the calibrated one.** `yield_tha_raw` reflects National Variety Trial management conditions, which generally out-yield commercial paddocks; `yield_tha_calibrated` applies a single national multiplicative factor to correct for this, checked against ABS-implied yield on two held-out years (+3.1% to +18.1% error) but not validated at finer spatial resolution than state level. Users needing paddock-level yield accuracy should treat the calibrated column as indicative, not exact, and consult both columns rather than the calibrated one alone.

**No canola or legume yield is shipped, and canola yield's absence has a specific, addressable cause.** Canola yield requires Sentinel-1 backscatter to clear a trivial year-and-state-mean baseline (Methods); Sentinel-1 is not yet part of this dataset's production pipeline, pending a national acquisition-cost assessment. This is disclosed rather than silently omitted so that a user is not left guessing whether canola yield was attempted and failed outright, or is simply not yet built.

**The Legume-class discrepancy (18.4% mapped vs. 8.7% ABS) has no established mechanism** and should be treated as an open, disclosed limitation rather than a solved or well-understood one; users relying on Legume-class output specifically should weight it accordingly against Cereal or Canola output.

**`unsegmented_blob`** is SAM's single largest segmentation failure mode (48,016 polygons nationally, Data Records); these polygons carry no class prediction and are not recoverable from this release without a separate segmentation pass.

**Sensitive underlying ground truth.** The GRDC/NVT trial records used to build and validate this dataset cannot be released at the site level (coordinates, trial identifiers, or yields) under the data-use agreement covering them; this dataset and its accompanying validation reports contain only aggregate statistics derived from those records, never site-level values.

---

---

# Data Availability
The national 2024 release and the nine-year (2017-2025) 100 km regional companion product described in Data Records will be deposited at a public repository with a persistent identifier (DOI) before submission. **[PENDING — dataset deposit not yet complete; identifier(s) to be added here once assigned — `PAPER_PLAN_SCIDATA.md` §24 point 7.]** The underlying GRDC/National Variety Trial ground-truth data used for training and validation — trial coordinates, crop identities, sowing/harvest dates, and yields — cannot be released, in accordance with the data-use agreement covering this dataset; this restriction applies only to the raw trial records and does not restrict release of the resulting map or the aggregate statistics reported in this Data Descriptor. ABS and ABARES reference statistics used for validation are already public and require no release action.

# Code Availability

The pipeline code (segmentation, labelling, classification, presence gating, yield calibration, and validation scripts) contains no site-level records and will be released alongside this Data Descriptor. **[PENDING — code repository deposit not yet complete; identifier to be added here.]** The classifier (`group3_map.joblib`) and Cereal yield model (`cereal_yield.joblib`) used to produce the released data are releasable and contain no site-level records. An unused-in-production phenology-shape presence-gate model, evaluated in Methods and not adopted, is retained for reproducibility but is not part of the shipped pipeline.

# Author Contributions

[Should tidy these up to use the usual terminology for papers.]
Christopher Bradley - Writing, coding, ideas, editing
John Burley - Writing, coding, ideas, editing 
Yasar Adeel Ansari - Writing, coding, ideas, editing
Justin Borevitz - funding acquisition, editing

# Competing Interests

None

# Acknowledgements

We would like to acknowledge the Grains Research and Development Corporation and the National Variety Trials network for the underlying trial data, and the National Computational Infrastructure (NCI) for compute access via Digital Earth Australia.

[Should also acknowledge claude usage and NORA usage (and reference NORA)]