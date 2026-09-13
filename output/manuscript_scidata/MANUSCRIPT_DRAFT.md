# Mapping Canola, Cereal and Legume Fields Across Australia at 10 m resolution

**Manuscript type**: Data Descriptor, Nature Scientific Data (backup: Earth System Science Data). **Draft status**: every 2024 national number is from the final 2024 map (2026-09-11). XXX marks a number that waits on the 2017-2023 and 2025 national runs, the consensus layer, the dataset DOI, the code repository or a citation to be confirmed.

---

# Abstract

We present a national dataset of canola, cereal and legume fields across Australia at 10 m resolution. Fields were segmented from Sentinel-2 imagery with the Segment Anything Model and classified into three crop groups by a gradient-boosted model on spectral indices. The classifier was trained on 2,194 Grains Research and Development Corporation (GRDC) National Variety Trial records. Each polygon carries a predicted class, a confidence score and, for cereals and legumes, a yield estimate. The 2024 national map contains 1,010,627 polygons, of which 429,951 carry a class. The same pipeline was run for every season from 2017 to 2025. The result is nine annual maps and a consensus layer of XXX fields with their crop group in each season. Mapped canola composition tracks Australian Bureau of Statistics sown-area statistics with r = 0.76 across 151 regions. The released map estimates 1.10 times as much cropland as those statistics. Crop presence agrees with WorldCereal at 76% of sampled fields. This is the first publicly available continental map of cropping polygons with classifications at 10 m resolution for Australia.

## Keywords

crop-type mapping; Sentinel-2; Segment Anything Model; field segmentation; presence detection; gradient boosting; Australia

---

# Background & Summary

Australia's grains industry covers [Are these the only crops it covers, or are there other things too?] cereals, oilseeds and pulses and is a major export industry. Its gross value of production was $26.7 billion in 2024-25 (ABARES, 2025). Wheat, barley, canola and pulses are grown across a broad cropping belt. The belt runs from central Queensland through New South Wales, Victoria and South Australia to Western Australia. Knowing where each crop is grown each season supports market forecasting, biosecurity planning, input supply and research into the drivers of production. The Australian Bureau of Statistics (ABS) publishes sown area and production by region and state for ...[for which years?]. Additionally, the Australian Bureau of Agricultural and Resource Economics and Sciences (ABARES) publishes state and national totals. However, no public dataset records exist showing which crop was grown in which field across the whole cropping belt. This dataset closes that gap.

Several products map cropland at national or global scale. WorldCereal (Van Tricht et al., 2023) provides global 10 m maps of temporary crops, maize and winter and spring cereals from Sentinel-1 and Sentinel-2. The maps are freely available, but have no canola or legume class and the training data has a large gap over Australia (Boogaard et al., 2023). The National Land Use Map (NLUM) of ABARES provides 250 m probability surfaces per commodity for the 2020-21 season (ABARES, 2024). Two regional studies have classified crop types in Australia at 10 m. Sharma et al. (2026) mapped six crops in Western Australia from Sentinel-2 time series, and Al-Shammari et al. (2024) separated cereals from canola across the Murray-Darling Basin with Sentinel-1, Sentinel-2 and MODIS. Both report accuracies above 90% within their regions. However, neither paper points to a public release of its classified map. This dataset adds national coverage of three crop groups, released as field polygons, for nine seasons.

The dataset we release maps every segmented field in the Australian cropping belt using Sentinel-2 imagery. Fields were segmented with the Segment Anything Model (SAM, Kirillov et al., 2023), then classified with a gradient-boosted model trained on GRDC National Variety Trial (NVT) records. Each polygon is assigned to one of three groups: canola, cereals (wheat, barley and oat) or legumes (chickpea, faba bean, field pea, lentil and lupin). Every polygon carries either a predicted class with confidence, or the reason it was not classified. Cereal polygons also carry a yield estimate. Each polygon records its seasonal NDVI amplitude, which users can apply to remove polygons unlikely to have grown a crop that year.

The 2024 national map contains 1,010,627 polygons, of which 429,951 carry a class. The same pipeline was applied without change to every season from 2017 to 2025. The result is nine annual national maps and a consensus layer of XXX fields. The consensus layer links each field across seasons and records its crop group in each one.

We validated the maps against ABS sown-area statistics and compared them with WorldCereal and NLUM. Canola composition tracks ABS with r = 0.76 across 151 regions, and the map calls 1.10 times as much land crop as the ABS. The excess sits in the cereal and legume classes rather than canola. Technical Validation reports these comparisons in full, and Usage Notes describes the attributes a user can filter on to remove polygons that were unlikely to be cropped in that year.

---

# Methods

Fig. 1 gives a pipeline overview alongside an example map, as an orientation to the stages described below.

## Study extent and temporal scope

The national maps cover the Australian cropping belt as 15,968 tiles of 9 km (Fig. 2). A tile was kept if it contained at least one 250 m NLUM pixel whose probability of winter cereals, oilseeds or legumes exceeded 25%. The tiles therefore cover 129 M ha, about five times the 24.6 M ha that ABS records as sown to these crops in 2024. Every season from 2017 to 2025 was processed on this same grid. Results are reported in two units: the number of field polygons and their area in hectares. All geometry is stored in EPSG:3577 (GDA94 / Australian Albers).

## Data sources

Sentinel-2 surface reflectance was read from Digital Earth Australia's analysis-ready products (`ga_s2am_ard_3`, `ga_s2bm_ard_3` and `ga_s2cm_ard_3`) through the National Computational Infrastructure datacube. Ground truth for the classifier and the yield model came from the GRDC National Variety Trials, obtained on 1 May 2025. The file records 4,479 trials of nine crops sown from 2017 to 2024 with valid coordinates. Each trial coordinate marks a corner of a small block of variety plots inside a commercial field. NVT protocol requires the surrounding field to be sown to the same crop within about two weeks of the trial (GRDC, XXXX). The field around a trial point is therefore a labelled sample of that crop. This is an updated version of the dataset described by Newman and Furbank (2021), used with permission from the GRDC as in that study.

Independent validation used ABS sown-area statistics by Statistical Area Level 2 (SA2), the smallest region for which ABS publishes sown area, for 2022 to 2024. ABARES state-level sown area was used as a second reference series. The NLUM v7 250 m per-commodity probability surfaces for 2020-21 (ABARES, 2024) were used to select the 15,968 tiles of 9km x 9km mentioned above. They were also used as an independent comparison product for the ratio of the different crop groups. WorldCereal 2021 v100 (Van Tricht et al., 2023) was used as a fourth comparison product.

## Segmentation

{TODO: John Burley to update this section}
Field boundaries were delineated with the Segment Anything Model (`vit_h` checkpoint, default parameters, Kirillov et al., 2023). SAM was run through the samgeo wrapper (Wu and Osco, 2023), following the PaddockTS workflow (XXX). The input to SAM for each tile was a three-band composite of the seasonal NDWI time series (its leading Fourier components, as in PaddockTS). 

Neighbouring tiles overlap slightly, so a field near a tile edge is segmented more than once. Duplicate and part-cut polygons along tile boundaries were merged into a single polygon.

Segmented polygons were retained only within a 5-300 ha area range and with a compactness ratio (perimeter / sqrt(area)) of at most 8. Of the 557 NVT trials sown in 2024, 62.5% fell inside a segmented polygon and 55.7% inside one that passed this filter. A 3 km tile size was also tested and it (qualitatively) found some additional good polygons but also additional bad polygons. It cut significantly more fields at tile edges (57% of classified polygons against 16% at 9 km). The 9 km tile size appeared correct more often on inspection and better matched the independent area totals. Hence the 9km tile size was chosen for the national runs. Future work could look into applying SAMGeo at multiple resolutions or offsets each year and merging the results, but this was not done here due to compute constraints.

Fields of the World (Kerner et al., 2024) was tested as an alternative boundary source over the same 557 trials. It contains the trial point at 90.7% of trials, but only 49.7% fall inside a polygon that passes the same size and shape filter. Its containing polygon is over 300 ha at 24.4% of trials and fails the compactness limit at a further 15.1%. Where both sources contain the trial point, the Fields of the World polygon has a median area of 109 ha against 55 ha. It is at least three times larger at 32% of trials, due to frequently merging unrelated fields. Where both sources return a polygon that passes the filter, the two agree closely. The median area ratio is 1.02 and the median intersection over union (IoU) is 0.88.

## Feature construction

Each retained polygon was described by 153 field-median spectral features. Nine indices were computed for each pixel and date. They are NDVI (Rouse et al., 1974), NDYI (Sulik and Long, 2016), the canola flowering index (CFI, Tian et al., 2022), and six more indices suggested by Sharma et al. (2026): NDRE2, VI2, VI3, VDVI, VCI and EVI2. For each date, the spatial median was taken over cloud-masked pixels inside the polygon eroded by 10 m from the field boundary to reduce edge artifacts. A date contributed only if at least half the polygon's pixels were clear. The dates were then grouped into 13 bins of 20 consecutive days for each bin, from day 90 to day 350 of the year. The median value of the contributing dates was taken within each bin. Four whole-season summaries were added per index: the 10th and 90th percentiles, their difference (the amplitude) and the day of year of the peak. This gives 17 features per index and 153 total features.

## Labelling

Each NVT trial point was matched to the SAM polygon containing it, or to the nearest polygon within 50 m where no polygon contained it. The trial site was often found by SAMGeo, but is a small area and contains lots of bare soil between plots, so we looked for the field surrounding those polygons instead. A match smaller than 10 ha was therefore replaced by a neighbour at least three times larger within 150 m. 3,439 trials had a matched polygon and a field time series. Trials were then dropped if compactness was above 6, area was outside 5-300 ha or tree cover was above 20%. Trials with fewer than 15 clear observations across the calendar year were also dropped. These rules were set from a hand review of 100 sample sites.

NVT sites often hold trials of several crops side by side in one field. Trials that shared a polygon with a trial of a different crop group in the same year were removed because the category of such a field is unclear. We reduced the nine crops to the three groups defined above for two reasons. First, co-located trials are usually of the same agronomic group. The grouping therefore resolves 540 of the 788 shared-field conflicts, or 69%, and returns those trials to the training set. Second, crops within a group are spectrally similar and so harder to tell apart. A nine-species classifier on the same trials and features reached a macro F1 of only 0.36, against 0.89 for the three groups. After these filtering steps 2,194 trials remained for training and testing: 585 canola, 1,119 cereal and 490 legume.

## Classification

Crop groups were predicted by a `HistGradientBoostingClassifier` (scikit-learn, Pedregosa et al., 2011) on the 153 features described above. The classifier was trained class-balanced, with geographic location excluded from the features. It uses 400 boosting iterations at a learning rate of 0.06, and every other hyperparameter is at its scikit-learn default. A grid search over 288 configurations did not improve on these settings. It lost 0.013 macro F1 on the temporal test and gained 0.003 on the spatial one. The five nested spatial folds each chose a different configuration, which suggests the search was fitting fold noise rather than a real setting. The model was evaluated both spatially and temporally on 543 held-out trials. The temporal split trained on trials sown 2022 or earlier and tested on 2023-2024. The spatial split used five-fold `GroupKFold` grouped by trial site. The classifier reached a macro F1 of 0.890 on the temporal split and 0.892 on the spatial split. We also trialled random forests, extra trees, logistic regression, fine-tuned Presto embeddings (Tseng et al., 2024) and Sentinel-1 backscatter as additional features. None beat the gradient-boosted model on the spectral indices alone (Technical Validation). Keeping only the six indices of Sharma et al. (2026) lowered macro F1 to 0.883 temporal and 0.872 spatial. All nine indices are therefore retained.

## Yield estimation

Cereal yield (wheat, barley and oat pooled) was estimated by a `HistGradientBoostingRegressor` trained on 1,119 cereal trials. Legume yield (chickpea, faba bean, field pea, lentil and lupin pooled) was estimated by a second regressor trained on 490 legume trials. Both use the 153 features described above. The three indices NDVI, NDYI and CFI alone gave a lower spatial-transfer R² (0.526 against 0.564 for cereals and 0.371 against 0.458 for legumes). NVT trial yields exceed commercial field yields, so each model's output was calibrated to ABS with a single national multiplicative factor. The cereal factor is XXX and the legume factor is XXX. Each factor was fitted on the 2022 ABS implied yield and checked on 2023 and 2024. The calibrated cereal median fell within XXX% and XXX% of the ABS figure in those years. The legume median fell within XXX% and XXX%. Both the raw (NVT-equivalent) and the calibrated yield are provided on every classified cereal and legume polygon. Canola yield is not provided because an optical-only model was no better than a year-and-state mean (spatial-transfer R² 0.271 against 0.290). Adding Sentinel-1 backscatter raised canola R² to 0.371 and also improved the cereal model, but Sentinel-1 was not acquired nationally because of compute constraints.

## Abstention rules

A polygon was classified only if it passed four checks, and otherwise carries the reason it failed. Polygons under 5 ha are marked `area_below_min`. Polygons over 300 ha are marked `unsegmented_blob`, since above that size SAM has usually merged several fields into one shape. Polygons with fewer than 10 clear observations are marked `too_few_observations`. Polygons whose NDVI amplitude (90th minus 10th percentile of the field-median series) is below 0.35 are marked `no_crop_signal`. The classifier was trained only on trial fields known to be cropped. This presence gate is therefore what separates cropped fields from pasture, forests and other land that passes the size filter. The 0.35 threshold was fitted on the full 3,439 NVT trial fields before filtering, of which 91.6% pass it. Every polygon carries its NDVI amplitude, so a user can apply a stricter threshold if needed.

## Validation protocol

Crop composition percentages and total area were compared against ABS sown area for 2024. The comparison used the 151 SA2s where the mapped tiles cover at least 50% of the SA2. A second check compared two ways of computing class shares, to test whether any composition error was an artefact of the decision rule. The first assigns each polygon wholly to its most probable class. The second credits each class with the polygon area multiplied by that class's probability. A sensitivity table reports classified area and composition error at five NDVI amplitude thresholds, to help inform different thresholds that may be useful for different purposes. Confidence intervals on area are not reported, as no probability sample of crop labels exists for Australia at the density needed to follow the method described in Olofsson et al. (2014).

The 2024 map was also compared at the pixel level with WorldCereal 2021 v100 and the NLUM v7 probability surfaces. The comparison used a random sample of 250,000 of the 1,010,627 field centroids. WorldCereal has no canola or legume class, so it was used to check crop presence (its `temporarycrops` layer) and the cereal class (its `wintercereals` layer). NLUM was used to check whether polygons of each class sit on land NLUM rates as probable for that commodity. NLUM's commodity layers are not on a common scale, so each class was scored by an enrichment ratio. The ratio is the median NLUM probability at that class's centroids divided by the median at abstained centroids.

Finally, the map itself was scored at the 533 fixed test trials from 2023 and 2024 that fall on the tile grid. A copy of the classifier trained on trials sown 2022 or earlier was used. This checks the released pipeline, including segmentation and the abstention rules, rather than the feature-level model alone.

## Multi-year processing

The pipeline above was applied to every season from 2017 to 2025 on the same 15,968-tile grid. Polygons were matched between seasons where their IoU was at least 0.5. A consensus layer was built from fields found in at least five of the nine seasons. The outline was taken from the season in which the field was largest. Each consensus field carries the crop group and confidence of its matched polygon in every season. The same 5-300 ha filter as the annual maps applies. The ABS comparison above was repeated for 2022 and 2023, the other seasons with SA2 sown-area statistics. Mapped state totals were compared with ABARES sown area for all nine seasons, excluding figures still flagged as forecasts. Crop sequences were counted on consensus fields classified in consecutive seasons.

---

# Data Records

The dataset is released as two products in GeoPackage format (EPSG:3577, GDA94 / Australian Albers), deposited at XXX under DOI XXX.

## Product 1: annual national maps, 2017-2025

Nine GeoPackages, one per season, share a single schema. Each row is one segmented field polygon. Fig. 2 shows the tile grid and the SA2s used for validation. Fig. 3 shows the 2024 map at national extent, rasterised to a 3 km majority-class grid. Individual fields are smaller than a printed pixel at that scale. Table 1 gives the totals per season.

**Table 1.** Annual national maps. Classified polygons carry a predicted class and the remainder carry an abstain reason.

| Season | Polygons | Classified polygons | Classified area (M ha) | File size |
|---|---:|---:|---:|---:|
| 2017 | XXX | XXX | XXX | XXX |
| 2018 | XXX | XXX | XXX | XXX |
| 2019 | XXX | XXX | XXX | XXX |
| 2020 | XXX | XXX | XXX | XXX |
| 2021 | XXX | XXX | XXX | XXX |
| 2022 | XXX | XXX | XXX | XXX |
| 2023 | XXX | XXX | XXX | XXX |
| 2024 | 1,010,627 | 429,951 (42.5%) | 19.6 | 3.2 GB |
| 2025 | XXX | XXX | XXX | XXX |

Each polygon carries the following attributes.

- `pred`: the predicted class (`Canola`, `Cereal` or `Legume`), or null where the polygon was not classified.
- `abstain_reason`: why a polygon was not classified, one of `area_below_min`, `no_crop_signal`, `too_few_observations` or `unsegmented_blob` (Methods). In 2024 these hold 305,943, 227,263, 38,177 and 9,293 polygons respectively. A fifth value, `no_crop_shape`, flags a classified polygon whose seasonal NDVI curve lacks a clear green-up and senescence. Such a polygon keeps its class and counts as classified in every total reported here.
- `confidence`: the classifier's probability for the predicted class, and `p_canola`, `p_cereal` and `p_legume`, the probability of each class. Null where `pred` is null.
- `ndvi_amp`: the NDVI amplitude used by the presence gate, on every polygon.
- `yield_tha` and `yield_tha_calibrated`: raw (NVT-equivalent) and ABS-calibrated yield in tonnes per hectare, on cereal and legume polygons only.
- `area_ha`, `compactness`, `n_obs`, `clear_frac` and `treed_frac`: the polygon's area, compactness ratio, number of clear Sentinel-2 observations, mean clear fraction and estimated tree cover fraction.
- `year` and `stub`: the season and the tile the polygon came from.
- Provenance of the tile-overlap merge: `boundary_action`, `merge_n`, `class_conflict`, `raster_cut_m` and `overlap_merge_n`. `raster_cut_m` is the length of boundary within 30 m of the tile's raster edge, and `class_conflict` marks a field whose two tile views disagreed on class. Both can be used as quality flags.
- `geometry`: the field polygon.

A companion file for each season holds only the polygons with a class and an empty `abstain_reason`, 344,416 polygons in 2024. It has `pred` renamed `predicted_crop_type` and a QGIS style embedded.

## Product 2: consensus field layer, 2017-2025

One GeoPackage holds one polygon per field that at least five of the nine annual segmentations agreed on, filtered to 5-300 ha. It contains XXX fields. Each carries `crop_<year>` and `conf_<year>` for every season from 2017 to 2025. It also records the number of seasons in which the field was found and classified, and the number of distinct crop groups it grew. The outline is one season's real segmentation rather than an average across seasons, since an averaged boundary matches no year's imagery. Note this means `crop_2019`, for example, is the class of the 2019 polygon matched to the consensus outline, whose boundary differs by a few metres.

## Model artefacts

The classifier (`group3_map_sharma6.joblib`) and the cereal and legume yield models (`cereal_yield.joblib` and `legume_yield.joblib`) are released with the data (Code Availability). A user can re-derive any prediction from the 153-feature field-median input described in Methods.

---

# Technical Validation

## Classifier accuracy

The classifier reaches a macro F1 of 0.890 under temporal transfer and 0.892 under spatial transfer (Table 2, Fig. 4). Both are scored on the fixed test set of 543 trials. Canola is detected at 89.0% recall at a 5% false-positive rate (average precision 0.935, ROC AUC 0.962). Legume is the weakest class in both splits, with precision 0.77 and 0.79. The main confusion is canola predicted as legume (19 of 155 true canola fields under temporal transfer, 16 under spatial transfer). The next is cereal predicted as legume (10 and 8 of 279). A five-species classifier trained on the 490 legume trials alone reached a macro F1 of 0.36 temporal and 0.34 spatial, against 0.20 for chance. The map therefore does not resolve legumes to species.

**Table 2.** Classifier accuracy by class and split, 543 fixed test trials sown in 2023-2024.

| Split (macro F1) | Class | Precision | Recall | F1 | n |
|---|---|---|---|---|---|
| Temporal (0.890) | Canola | 0.93 | 0.85 | 0.89 | 155 |
| | Cereal | 0.96 | 0.95 | 0.96 | 279 |
| | Legume | 0.77 | 0.89 | 0.83 | 109 |
| Spatial (0.892) | Canola | 0.91 | 0.88 | 0.89 | 155 |
| | Cereal | 0.97 | 0.96 | 0.96 | 279 |
| | Legume | 0.79 | 0.85 | 0.82 | 109 |

The alternatives listed in Methods were scored on the same test set. On the nine indices, random forests reached a macro F1 of 0.857 temporal and 0.852 spatial. Extra trees reached 0.852 and 0.850. The gradient-boosted model reached 0.890 and 0.892 on the same rows. With only the three indices NDVI, NDYI and CFI, random forests (0.830, 0.820) and extra trees (0.823, 0.819) matched the gradient-boosted model (0.821, 0.823). Logistic regression on those three indices fell short (0.745, 0.768). Fine-tuned Presto embeddings scored 0.775 alone and 0.824 combined with the three indices. Adding Sentinel-1 backscatter to the final classifier lowered macro F1 by 0.023 (temporal) and 0.018 (spatial), concentrated in the legume class.

## Map accuracy at trial sites

The released pipeline was scored at the 533 test trials from 2023 and 2024 that fall on the tile grid. The classifier copy trained on trials sown 2022 or earlier was used. 122 sites had no segmented polygon and 62 fell in a polygon that abstained. On the 349 scored sites the map reached a macro F1 of 0.898 (canola 0.893, cereal 0.952, legume 0.848). The polygon containing a site was within a factor of two of the trial field's recorded area at 91% of sites.

## Composition and area against ABS

Neither ABS nor ABARES is ground truth. The two agencies' national sown-area figures differ by a median of 6.8% across the three seasons and three crop groups in Table 3. No map-versus-reference difference smaller than that should be read as a map error.

**Table 3.** National sown area from the two official series.

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

Across the 151 well-covered SA2s, the mapped canola share of crop area tracks the ABS share (Fig. 5). The correlation is r = 0.76 and the median absolute error in canola share is 4.3%. The mapped area of all three classes combined, however, is larger than the sown area ABS records. The median ratio of mapped crop area to ABS sown area over the same SA2s is 1.10.

Table 4 divides the over-call by class. The diluted share is the ABS share divided by the over-call. The absorbed column is the excess mapped share each class carries. The excess sits in cereal and legume. The mapped canola share sits 3.7% below its diluted share. The map therefore calls slightly less land canola and more land legume than the ABS data.

**Table 4.** Composition against ABS, 151 SA2s, 2024. Shares are medians over SA2s.

| Class | ABS share | Diluted share | Mapped share | Absorbed (%) |
|---|---|---|---|---|
| Canola | 19.2% | 17.4% | 13.7% | -3.7 |
| Cereal | 67.3% | 61.2% | 65.8% | +4.7 |
| Legume | 8.9% | 8.1% | 16.1% | +8.0 |

The legume share, 16.1% of classified area against 8.9% in ABS, is the largest composition error in the map. It arises from canola and cereals being misclassified as legumes. Table 5 compares the class shares under the two decision rules described in Validation protocol. Assigning each polygon to its most probable class gives a legume share of 18.0%, and weighting each polygon by its legume probability gives 18.2%. The two rules agree within 0.6% for every class, so the legume excess is not an artefact of the decision rule. The classifier places that much probability on legume.

**Table 5.** Class share of classified area by decision rule, national 2024 map.

| Class | Most probable class | Probability-weighted | ABS |
|---|---|---|---|
| Canola | 15.4% | 15.7% | 19.2% |
| Cereal | 66.7% | 66.1% | 67.3% |
| Legume | 18.0% | 18.2% | 8.9% |

Table 6 re-scores the same polygons at five presence-gate thresholds. Raising the threshold to 0.50 removes 26% of classified area. It changes the canola share error by only 0.5% and the legume share error by 1.1%. Composition is therefore insensitive to the threshold while area is not.

**Table 6.** Sensitivity of the 2024 map to the NDVI amplitude threshold. Share errors are medians over the 151 SA2s.

| Threshold | Classified area (ha) | Canola share error (%) | Legume share error (%) |
|---|---|---|---|
| 0.25 | 19,575,177 | 5.7 | 9.1 |
| 0.30 | 19,575,177 | 5.7 | 9.1 |
| 0.35 (released) | 19,575,177 | 5.7 | 9.1 |
| 0.40 | 18,036,667 | 5.7 | 8.8 |
| 0.45 | 16,341,696 | 5.3 | 8.6 |
| 0.50 | 14,462,331 | 5.2 | 8.0 |

## Comparison with WorldCereal and NLUM
{TODO: repeat this comparison with the 2021 map against WorldCereal 2021 once the 2021 run finishes}
Both products predate the 2024 map by three years, so some disagreement is real change in what was grown. Against WorldCereal's `temporarycrops` layer, the map's classified-versus-abstained presence call agrees at 76.1% of the 250,000 sampled centroids. 82.1% of abstained centroids are also no-crop in WorldCereal, and 67.9% of classified centroids are also crop. Of the 71,684 centroids the map calls cereal, 44.3% are `wintercereals` in WorldCereal. WorldCereal is an independent product rather than ground truth, so this does not establish which product is right where they differ.

Against NLUM, the median oilseed probability at canola centroids is 8.5 times the median at abstained centroids. The cereal ratio at cereal centroids is 1.5 and the legume ratio at legume centroids is 1.0. NLUM therefore rates the map's canola and cereal polygons as more probable for those commodities than abstained land, but not its legume polygons. NLUM's grazing layer supports the presence-gate reading from an unrelated source. The median grazing probability is 60.7% at abstained centroids against 16.9% at classified centroids. Abstained land is therefore concentrated on land NLUM rates as probable grazing country.

## Yield

The cereal yield model reaches a spatial-transfer root-mean-square error of 1.16 t/ha, 29% of the 3.97 t/ha median trial yield (Table 7, Fig. 6). The legume model reaches 0.84 t/ha, 43% of the 1.93 t/ha median. On the temporal split the year-and-state baseline collapses to a state-only model, because the test seasons are unseen. The satellite features still reach an R² of 0.49 for cereals and 0.43 for legumes. The ABS calibration factors were fitted on 2022. They reproduced the ABS implied yield within XXX% in 2023 and XXX% in 2024 for cereals, and within XXX% and XXX% for legumes.

**Table 7.** Yield models before calibration. Cereal pools wheat, barley and oat. Legume pools chickpea, faba bean, field pea, lentil and lupin.

| Crop | Split | Features | n | R² | RMSE (t/ha) |
|---|---|---|---|---|---|
| Cereal | Temporal (train 2022 or earlier, test 2023-24) | Year and state baseline | 279 | -0.643 | 2.111 |
| | | Satellite features | 279 | 0.486 | 1.181 |
| | | Satellite, year and state | 279 | 0.501 | 1.163 |
| | Spatial (five-fold GroupKFold on site) | Year and state baseline | 1,119 | 0.294 | 1.473 |
| | | Satellite features | 1,119 | 0.564 | 1.157 |
| | | Satellite, year and state | 1,119 | 0.566 | 1.154 |
| Legume | Temporal | Year and state baseline | 109 | -0.518 | 1.170 |
| | | Satellite features | 109 | 0.426 | 0.720 |
| | | Satellite, year and state | 109 | 0.402 | 0.734 |
| | Spatial | Year and state baseline | 490 | 0.133 | 1.056 |
| | | Satellite features | 490 | 0.458 | 0.835 |
| | | Satellite, year and state | 490 | 0.451 | 0.840 |

## National multi-year maps

Table 8 summarises the nine seasons. Classified share ranged from XXX% (XXX) to XXX% (XXX). Against ABS at SA2, mapped canola composition gave r = XXX, XXX and XXX for 2022, 2023 and 2024. The area ratio was XXX, XXX and XXX. Against ABARES state totals, the median absolute error of mapped canola area was XXX% over XXX state-seasons. The median IoU between a field's polygons in consecutive seasons was XXX. A consensus field was found in a median of XXX of the nine seasons. Of consensus fields classified in two consecutive seasons, XXX% changed class, and canola was followed by cereal in XXX% of cases (Fig. 7). Canola is normally grown as a break crop between cereals. Note this means a high rate of repeated canola would point to classification error rather than agronomy. The 2025 season has no ABS figures and no final ABARES figures, so its map is unscored.

**Table 8.** National maps by season. ABS SA2 statistics exist for 2022-2024 only.

| Season | Classified (%) | Canola / cereal / legume share (%) | ABS canola r | Area ratio | ABARES state MAE (%) |
|---|---:|---|---:|---:|---:|
| 2017 | XXX | XXX / XXX / XXX | - | - | XXX |
| 2018 | XXX | XXX / XXX / XXX | - | - | XXX |
| 2019 | XXX | XXX / XXX / XXX | - | - | XXX |
| 2020 | XXX | XXX / XXX / XXX | - | - | XXX |
| 2021 | XXX | XXX / XXX / XXX | - | - | XXX |
| 2022 | XXX | XXX / XXX / XXX | XXX | XXX | XXX |
| 2023 | XXX | XXX / XXX / XXX | XXX | XXX | XXX |
| 2024 | 42.5 | 15.4 / 66.6 / 17.9 | 0.76 | 1.10 | XXX |
| 2025 | XXX | XXX / XXX / XXX | - | - | - |

---

# Usage Notes

Every polygon carries either a class or an abstain reason, together with `ndvi_amp`, `confidence` and the class probabilities. A user who needs area accuracy rather than composition accuracy can filter the map with these attributes instead of waiting for a revised release. Raising the `ndvi_amp` threshold above 0.35 trades completeness for a lower area over-call, and Table 6 quantifies the trade-off. The companion file (Data Records), which removes polygons flagged `no_crop_shape`, is a ready-made stricter view. The `raster_cut_m` and `class_conflict` attributes identify polygons cut at a tile edge or seen differently by two tiles.

Users computing absolute crop area should expect the map to call about 1.10 times the area ABS records as sown, unless they filter as above. The excess sits in cereal and legume rather than canola. Composition estimates that rest on canola are therefore the most directly validated use of the map.

Yield users should read both yield columns. `yield_tha` reflects trial management, which out-yields commercial fields, and `yield_tha_calibrated` applies a single national factor per crop group checked against ABS at state level only. The calibrated column is indicative at field scale, not exact. The legume estimate pools five species whose trial yields differ two-fold (median 1.5 t/ha for chickpea against 3.1 t/ha for faba bean), and the map does not resolve which species a polygon grew. No canola yield is provided. Canola yield needs Sentinel-1 backscatter to beat a year-and-state mean (Methods), and Sentinel-1 is not part of the pipeline.

The legume class is mapped at 16.1% of classified area against an ABS share of 8.9%, and the cause is not established. Users relying on the legume class should weight it accordingly against the cereal and canola classes.

Polygons marked `unsegmented_blob` are SAM's main failure mode, ground where several fields were returned as one shape. They carry no class and cannot be recovered from this release without a second segmentation pass. In 2024 they number 9,293 polygons covering 4.5 M ha.

The 2024 map can also be viewed and queried in Google Earth Engine as a public asset (XXX asset path). A viewer script is in the code repository.

The GRDC National Variety Trial records used to build and validate this dataset are covered by a data-use agreement. They cannot be released at the site level (coordinates, trial identifiers or yields). This dataset and its validation reports contain only aggregate statistics derived from those records.

---

# Data Availability

The annual national maps and the consensus field layer described in Data Records are deposited at XXX under DOI XXX. The NVT training dataset is covered by a data use agreement, so the authors cannot directly share it. It can be requested from the GRDC using the form at (XXX). ABS and ABARES statistics, the NLUM probability surfaces and WorldCereal are public.

# Code Availability

The pipeline code (segmentation, labelling, classification, abstention, yield calibration, multi-year consensus and validation scripts) contains no site-level records and is released at XXX. The classifier (`group3_map_sharma6.joblib`) and the two yield models (`cereal_yield.joblib` and `legume_yield.joblib`) used to produce the released data are included in the same repository.

# Author Contributions

C.B.: conceptualisation, methodology, software, formal analysis, data curation, visualisation, writing (original draft), writing (review and editing). J.B.: conceptualisation, software, writing (original draft), writing (review and editing). Y.A.A.: conceptualisation, software, writing (original draft), writing (review and editing). J.O.B.: funding acquisition, supervision, writing (review and editing).

# Competing Interests

The authors declare no competing interests.

# Acknowledgements

We thank the Grains Research and Development Corporation and the National Variety Trials network for providing the training data that made the crop classifications possible. We also thank the National Computational Infrastructure for compute access. Lastly, we thank Geoscience Australia for the Digital Earth Australia datacube and its analysis-ready Sentinel-2 products.

---

# References

ABARES (2024). Land use of Australia 2010-11 to 2020-21: agricultural commodity probability surfaces, version 7 (NLUM v7, 250 m). Australian Bureau of Agricultural and Resource Economics and Sciences, Canberra. XXX

ABARES (2025). Agricultural commodities: September quarter 2025. Australian Bureau of Agricultural and Resource Economics and Sciences, Canberra. XXX

Al-Shammari, D., Fuentes, I., Whelan, B.M., Wang, C., Filippi, P. and Bishop, T.F.A. (2024). Combining Sentinel 1, Sentinel 2 and MODIS data for major winter crop type classification over the Murray Darling Basin in Australia. *Remote Sensing Applications: Society and Environment*, 34, 101200. doi:10.1016/j.rsase.2024.101200

Boogaard, H., Pratihast, A.K., Laso Bayas, J.C., Karanam, S., Fritz, S., Van Tricht, K., Degerickx, J. and Gilliams, S. (2023). Building a community-based open harmonised reference data repository for global crop mapping. *PLOS ONE*, 18(7), e0287731. doi:10.1371/journal.pone.0287731

GRDC (XXXX). National Variety Trials protocols. Grains Research and Development Corporation. XXX

Kerner, H., Chaudhari, S., Ghosh, A., Robinson, C., Ahmad, A., Choi, E., Joshi, N., Tadros, M., Malkin, N. and Ortiz, C. (2024). Fields of The World: a machine learning benchmark dataset for global agricultural field boundary segmentation. arXiv:2409.16252.

Kirillov, A., Mintun, E., Ravi, N., Mao, H., Rolland, C., Gustafson, L., Xiao, T., Whitehead, S., Berg, A.C., Lo, W.-Y., Dollár, P. and Girshick, R. (2023). Segment Anything. In *2023 IEEE/CVF International Conference on Computer Vision (ICCV)*, 3992-4003.

Newman, S.J. and Furbank, R.T. (2021). Explainable machine learning models of major crop traits from satellite-monitored continent-wide field trial data. *Nature Plants*, 7, 1354-1363. doi:10.1038/s41477-021-01001-0

Olofsson, P., Foody, G.M., Herold, M., Stehman, S.V., Woodcock, C.E. and Wulder, M.A. (2014). Good practices for estimating area and assessing accuracy of land change. *Remote Sensing of Environment*, 148, 42-57. doi:10.1016/j.rse.2014.02.015

PaddockTS (XXXX). XXX

Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M. and Duchesnay, É. (2011). Scikit-learn: machine learning in Python. *Journal of Machine Learning Research*, 12, 2825-2830.

Rouse, J.W., Haas, R.H., Schell, J.A. and Deering, D.W. (1974). Monitoring vegetation systems in the Great Plains with ERTS. In *Third Earth Resources Technology Satellite-1 Symposium*, NASA SP-351, Vol. 1, 309-317.

Sharma, S., Eslick, H., Pires, R., Singh, B. and Tareque, H. (2026). Temporal sensitivity of in-season crop classification: an explainable multi-year Sentinel-2 analysis in Western Australia. *Remote Sensing*, 18(10), 1653. doi:10.3390/rs18101653

Sulik, J.J. and Long, D.S. (2016). Spectral considerations for modeling yield of canola. *Remote Sensing of Environment*, 184, 161-174. XXX

Tian, H., Chen, T., Li, Q., Mei, Q., Wang, S., Yang, M., Wang, Y. and Qin, Y. (2022). A novel spectral index for automatic canola mapping by using Sentinel-2 imagery. *Remote Sensing*, 14(5), 1113. XXX

Tseng, G., Cartuyvels, R., Zvonkov, I., Purohit, M., Rolnick, D. and Kerner, H. (2024). Lightweight, pre-trained transformers for remote sensing timeseries. arXiv:2304.14065.

Van Tricht, K., Degerickx, J., Gilliams, S., Zanaga, D., Battude, M., Grosu, A., Brombacher, J., Lesiv, M., Bayas, J.C.L., Karanam, S., Fritz, S., Becker-Reshef, I., Franch, B., Mollà-Bononad, B., Boogaard, H., Pratihast, A.K., Koetz, B. and Szantoi, Z. (2023). WorldCereal: a dynamic open-source system for global-scale, seasonal, and reproducible crop and irrigation mapping. *Earth System Science Data*, 15, 5491-5515. doi:10.5194/essd-15-5491-2023

Wu, Q. and Osco, L.P. (2023). samgeo: a Python package for segmenting geospatial data with the Segment Anything Model (SAM). *Journal of Open Source Software*, 8(89), 5663. XXX
