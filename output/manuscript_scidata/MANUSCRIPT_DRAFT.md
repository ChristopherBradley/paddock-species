# Mapping Canola, Cereal and Legume Paddocks Across Australia at 10 m resolution

**Manuscript type**: Data Descriptor, Nature Scientific Data (backup: Earth System Science Data). **Draft status**: every 2024 national number is from the final 2024 map (2026-09-11). XXX marks a number that waits on the 2017-2023 and 2025 national runs, the consensus layer, the dataset DOI, the code repository or a citation to be confirmed.

---

# Abstract

We present a national dataset of canola, cereal and legume paddocks across Australia at 10 m resolution. Paddocks were segmented from Sentinel-2 imagery with the Segment Anything Model and classified into three crop groups by a gradient-boosted model on spectral indices. The classifier was trained on 2,194 Grains Research and Development Corporation (GRDC) National Variety Trial records. Each polygon carries a predicted class, a confidence score and, for cereals, a yield estimate. The 2024 national map contains 1,010,627 polygons, of which 429,951 carry a class. The same pipeline was run for every season from 2017 to 2025. The result is nine annual maps and a consensus layer of XXX paddocks with their crop group in each season. Mapped canola composition tracks Australian Bureau of Statistics sown-area statistics with r = 0.76 across 151 regions. The released map estimates 1.10 times as much cropland as those statistics. Crop presence agrees with WorldCereal at 76% of sampled paddocks. This is the first publicly available continental map of cropping polygons with classifications at 10 m resolution for Australia.

## Keywords

crop-type mapping; Sentinel-2; Segment Anything Model; paddock segmentation; presence detection; gradient boosting; Australia

---

# Background & Summary

Australia's grains industry grows wheat, barley, canola and pulses across a broad cropping belt. The belt runs from central Queensland through New South Wales, Victoria and South Australia to Western Australia. Knowing where each crop is grown each season supports market forecasting, biosecurity planning, input supply and research into the drivers of production. The Australian Bureau of Statistics (ABS) publishes sown area and production by region and state. Additionally, the Australian Bureau of Agricultural and Resource Economics and Sciences (ABARES) publishes state and national totals. However, no public dataset records which crop was grown in which paddock across the whole cropping belt. This dataset closes that gap.

Several products map cropland at national or global scale. WorldCereal (Van Tricht et al., 2023) provides global 10 m maps of temporary crops, maize and winter and spring cereals from Sentinel-1 and Sentinel-2. The maps are freely available, but have no canola or legume class. The reference data behind them also records a large gap over Australia (Boogaard et al., 2023). The National Land Use Map (NLUM) of ABARES provides 250 m probability surfaces per commodity for the 2020-21 season (ABARES, 2024). Two regional studies have classified crop types in Australia at 10 m. Sharma et al. (2026) mapped six crops in Western Australia from Sentinel-2 time series. Al-Shammari et al. (2024) separated cereals from canola across the Murray-Darling Basin with Sentinel-1, Sentinel-2 and MODIS. Both report accuracies above 90% within their regions. However, both trained on labels that are not public: another model's predictions and harvester yield maps respectively. Sharma et al. (2026) state that the datasets presented are not available because the crop data are proprietary, and Al-Shammari et al. (2024) that the data used are confidential. Neither paper points to a public release of its classified map. This dataset adds national coverage of three crop groups, released as paddock polygons, for nine seasons.

This dataset maps every segmented paddock in the Australian cropping belt from Sentinel-2 imagery. Paddocks were segmented with the Segment Anything Model (SAM, Kirillov et al., 2023). They were classified with a gradient-boosted model trained on GRDC National Variety Trial (NVT) records. Each polygon is assigned to one of three groups: canola, cereals (wheat, barley and oat) or legumes (chickpea, faba bean, field pea, lentil and lupin). Every polygon carries either a predicted class with its confidence, or the reason it was not classified. Cereal polygons also carry a yield estimate. Each polygon records its seasonal NDVI amplitude, which a user can apply to remove polygons unlikely to have grown a crop that year.

The 2024 national map contains 1,010,627 polygons, of which 429,951 carry a class. The same pipeline was applied without change to every season from 2017 to 2025. The result is nine annual national maps and a consensus layer of XXX paddocks. The consensus layer links each paddock across seasons and records its crop group in each one.

We validated the maps against ABS sown-area statistics and compared them with WorldCereal and NLUM. Canola composition tracks ABS with r = 0.76 across 151 regions, and the map calls 1.10 times as much land crop as ABS records. The excess sits in the cereal and legume classes rather than canola. Technical Validation reports these comparisons in full, and Usage Notes describes the fields a user can filter on to remove polygons that were unlikely to be cropped in that year.

---

# Methods

Fig. 1 gives a pipeline overview alongside an example map, as an orientation to the stages described below.

## Study extent and temporal scope

The national maps cover the Australian cropping belt as 15,968 tiles of 9 km (Fig. 2). A tile was kept if it contained at least one 250 m NLUM pixel whose probability of winter cereals, oilseeds or legumes exceeded 25%. One qualifying pixel out of the 1,296 in a 9 km tile is enough, so the rule is permissive at tile scale. The mapped area exceeds the ABS sown area rather than falling short of it (Technical Validation). Every season from 2017 to 2025 was processed on this same grid. Results are reported in two units: the number of paddock polygons and their area in hectares. All geometry is stored in EPSG:3577 (GDA94 / Australian Albers).

## Data sources

Sentinel-2 surface reflectance was read from Digital Earth Australia's analysis-ready products (`ga_s2am_ard_3`, `ga_s2bm_ard_3` and `ga_s2cm_ard_3`) through the National Computational Infrastructure datacube. Ground truth for the classifier and the yield model came from the GRDC National Variety Trials, obtained on 1 May 2025. The file records 4,479 trials of nine crops sown from 2017 to 2024 with valid coordinates. Each trial coordinate marks a corner of a small block of variety plots inside a commercial paddock. NVT protocol requires the surrounding paddock to be sown to the same crop within about two weeks of the trial (GRDC, XXXX). The paddock around a trial point is therefore a labelled sample of that crop.

Independent validation used ABS sown-area statistics by Statistical Area Level 2 (SA2), the smallest region for which ABS publishes sown area, for 2022 to 2024. ABARES state-level sown area was used as a second reference series. The NLUM v7 250 m per-commodity probability surfaces for 2020-21 (ABARES, 2024) were used to select the 15,968 tiles of 9km x 9km mentioned above. They were also used as an independent comparison product for the ratio of the different crop groups. WorldCereal 2021 v100 (Van Tricht et al., 2023) was used as a fourth comparison product.

## Segmentation

{TODO: John Burley to update this section}
Paddock boundaries were delineated with the Segment Anything Model (`vit_h` checkpoint, default parameters, Kirillov et al., 2023). SAM was run through the samgeo wrapper (Wu and Osco, 2023), following the PaddockTS workflow (XXX). The input to SAM for each tile was a three-band composite of the seasonal NDWI time series (its leading Fourier components, as in PaddockTS). 

Neighbouring tiles overlap slightly, so a paddock near a tile edge is segmented more than once. Duplicate and part-cut polygons along tile boundaries were merged into a single polygon.

Segmented polygons were retained only within a 5-300 ha area range and with a compactness ratio (perimeter / sqrt(area)) of at most 8. Of the 270 NVT trials sown in 2024, 76.3% fell inside a segmented polygon that passed this filter. A 3 km tile size was also tested and it (qualitatively) found some additional good polygons but also additional bad polygons. It cut significantly more paddocks at tile edges (57% of classified polygons against 16% at 9 km). The 9 km tile size appeared correct more often on inspection and better matched the independent area totals. Hence the 9km tile size was chosen for the national runs. Future work could look into applying SAMGeo at multiple resolutions or offsets each year and merging the results, but this was not done here due to compute constraints.

Fields of the World (Kerner et al., 2024) was tested as an alternative boundary source over all 557 trials sown in 2024. It contains the trial point more often than the released map does, at 90.7% against 62.5%. The polygon it returns is larger, at a median 109 ha against 55 ha. That is a median ratio of 1.49, and at least three times larger at 32% of trials. Where both sources contain the point, the two polygons agree at a median IoU of 0.53, and below 0.5 at 46% of trials. Fields of the World therefore finds a paddock at more trial sites, but agrees less often on where that paddock ends. Further work could combine several tile sizes and offsets to recover paddocks the current product misses.

## Feature construction

Each retained polygon was described by 153 paddock-median spectral features. Nine indices were computed per pixel and date. They are NDVI, NDYI (Sulik and Long, 2016), the canola flowering index (CFI, Tian et al., 2022), and six more indices suggested by Sharma et al. (2026): NDRE2, VI2, VI3, VDVI, VCI and EVI2. For each date, the spatial median was taken over cloud-masked pixels inside the polygon eroded by 10 m. A date contributed only if at least half the polygon's pixels were clear. The dates were then grouped into 13 bins of 20 days, from day 90 to day 350 of the year. The median of the contributing dates was taken within each bin. Four whole-season summaries were added per index: the 10th and 90th percentiles, their difference (the amplitude) and the day of year of the peak. This gives 17 features per index and 153 total features.

## Labelling

Each NVT trial point was matched to the SAM polygon containing it, or to the nearest polygon within 50 m where no polygon contained it. SAM often segments the trial block itself. The block is small and carries bare soil between plots, so the surrounding paddock was sought instead. A match smaller than 10 ha was therefore replaced by a neighbour at least three times larger within 150 m. 3,439 trials had a matched polygon and a paddock time series. Trials were then dropped if compactness was above 6, area outside 5-300 ha, tree cover above 20%, or fewer than 15 clear observations across the calendar year. These rules were set from a hand review of 96 sample sites.

NVT sites often hold trials of several crops side by side in one paddock. Trials that shared a polygon with a trial of a different crop group in the same year were removed because the category of such a paddock is unclear. We reduced the nine crops to the three groups defined above for two reasons. First, co-located trials are usually of the same agronomic group. The grouping therefore resolves 540 of the 788 shared-paddock conflicts, or 69%, and returns those trials to the training set. Second, crops within a group are spectrally similar and so harder to tell apart. A nine-species classifier reached a macro F1 of only 0.38, against 0.78 for the three groups on the same trials and features. After these filtering steps 2,194 trials remained for training and testing: 585 canola, 1,119 cereal and 490 legume.

## Classification

Crop groups were predicted by a `HistGradientBoostingClassifier` (scikit-learn, Pedregosa et al., 2011) on the 153 features described above. The classifier was trained class-balanced, with geographic location excluded from the features. It uses 400 boosting iterations at a learning rate of 0.06, and every other hyperparameter is at its scikit-learn default. A grid search over 288 configurations did not improve on these settings. It lost 0.013 macro F1 on the temporal test and gained 0.003 on the spatial one. The five nested spatial folds each chose a different configuration, which suggests the search was fitting fold noise rather than a real setting. The model was evaluated both spatially and temporally on 543 held-out trials. The temporal split trained on trials sown 2022 or earlier and tested on 2023-2024. The spatial split used five-fold `GroupKFold` grouped by trial site. The classifier reached a macro F1 of 0.890 on the temporal split and 0.892 on the spatial split. We also trialled random forests, extra trees, logistic regression, fine-tuned Presto embeddings (Tseng et al., 2024) and Sentinel-1 backscatter as additional features. None beat the gradient-boosted model on the spectral indices alone (Technical Validation). Keeping only the six indices of Sharma et al. (2026) and dropping the three original ones lowered macro F1 to 0.883 temporal and 0.872 spatial, so all nine are retained.

## Yield estimation

Cereal yield (wheat, barley and oat pooled) was estimated by a `HistGradientBoostingRegressor` trained on 1,119 cereal trials. It uses the 51 features from the three original indices. NVT trial yields exceed commercial paddock yields, so the model output was calibrated to ABS with a single national multiplicative factor of 0.6248. The factor was fitted on the 2022 ABS implied yield and checked on 2023 and 2024. The calibrated NVT median fell within 18% and 3% of the ABS figure in those years. Both the raw (NVT-equivalent) and the calibrated yield are provided on every classified cereal polygon. Canola yield is not provided because an optical-only model was no better than a year-and-state mean (spatial-transfer R² 0.271 against 0.290). Adding Sentinel-1 backscatter raised canola R² to 0.371 and also improved the cereal model, but Sentinel-1 was not acquired nationally because of compute constraints.

All three groups were refitted on the adopted nine-index feature set to check whether the shipped three-index yield model is still the right one. It is, for cereals. The nine-index features moved spatial-transfer R² from 0.526 to 0.564, against a year-and-state baseline of 0.294. That does not justify reissuing the released yield column. Canola remained at or below its baseline on either feature set (0.299 and 0.284 against 0.316), confirming the decision not to publish a canola yield. Legume yield had never been attempted. It proved the most predictable of the three relative to its baseline, at spatial-transfer R² 0.458 against a year-and-state baseline of 0.133. On the temporal split it reached 0.426 against a negative baseline. Part of that signal is the model recognising which of the five legume species a paddock grew. The released map does not resolve legumes to species, so no legume yield column is included here. It is the clearest candidate for the next version.

## Abstention rules

A polygon was classified only if it passed four checks, and otherwise carries the reason it failed. Polygons under 5 ha are marked `area_below_min`. Polygons over 300 ha are marked `unsegmented_blob`, since above that size SAM has usually merged several fields into one shape. Polygons with fewer than 10 clear observations are marked `too_few_observations`. Polygons whose NDVI amplitude (90th minus 10th percentile of the paddock-median series) is below 0.35 are marked `no_crop_signal`. The classifier was trained only on trial paddocks known to be cropped. This presence gate is therefore what separates cropped paddocks from pasture, forests and other land that passes the size filter. The 0.35 threshold was fitted on the full 3,439 NVT trial paddocks before filtering, of which 91.6% pass it. Every polygon carries its NDVI amplitude, so a user can apply a stricter threshold if needed (Usage Notes).

## Validation protocol

Composition and area were compared against ABS sown area for 2024. The comparison used the 151 SA2s where the mapped tiles cover at least 50% of the SA2. Two comparisons were made. The composition comparison asks whether the share of mapped crop area in each class matches the ABS share. The area comparison asks whether the map calls more or less land crop than ABS records as sown. The two together separate a presence error, which changes area, from a classification error, which changes composition. An argmax-versus-mean-probability check tested whether any composition error could be a decision-rule artefact. A sensitivity table reports classified area and composition error at five NDVI amplitude thresholds. Note this is a sensitivity check, not a fitting procedure. Choosing the threshold that best matches ABS would make ABS a training set and remove the only independent check available. No probability sample of crop labels exists for Australia at the density an Olofsson et al. (2014) area estimate would need. No confidence intervals on area are therefore reported.

The 2024 map was also compared at the pixel level with WorldCereal 2021 v100 and the NLUM v7 probability surfaces. The comparison used a random sample of 250,000 of the 1,010,627 paddock centroids. WorldCereal has no canola or legume class, so it was used to check crop presence (its `temporarycrops` layer) and the cereal class (its `wintercereals` layer). NLUM was used to check whether polygons of each class sit on land NLUM rates as probable for that commodity. NLUM's commodity layers are not on a common scale, so each class was scored by an enrichment ratio. The ratio is the median NLUM probability at that class's centroids divided by the median at abstained centroids.

Finally, the map itself was scored at the 533 fixed test trials from 2023 and 2024 that fall on the tile grid. A copy of the classifier trained on trials sown 2022 or earlier was used. This checks the released pipeline, including segmentation and the abstention rules, rather than the feature-level model alone.

## Multi-year processing

The pipeline above was applied to every season from 2017 to 2025 on the same 15,968-tile grid. No model was refitted on a later season. Polygons were matched between seasons where their intersection over union (IoU) was at least 0.5. A consensus layer was built from paddocks found in at least five of the nine seasons. The outline was taken from the season in which the paddock was largest. Each consensus paddock carries the crop group and confidence of its matched polygon in every season. The same 5-300 ha filter as the annual maps applies. The ABS comparison above was repeated for 2022 and 2023, the other seasons with SA2 sown-area statistics. Mapped state totals were compared with ABARES sown area for all nine seasons, excluding figures still flagged as forecasts. Crop sequences were counted on consensus paddocks classified in consecutive seasons.

---

# Data Records

The dataset is released as two products in GeoPackage format (EPSG:3577, GDA94 / Australian Albers), deposited at XXX under DOI XXX.

## Product 1: annual national maps, 2017-2025

Nine GeoPackages, one per season, share a single schema. Each row is one segmented paddock polygon. Fig. 2 shows the tile grid and the SA2s used for validation. Fig. 3 shows the 2024 map at national extent, rasterised to a 3 km majority-class grid. Individual paddocks are smaller than a printed pixel at that scale. Table 1 gives the totals per season.

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

Each polygon carries the following fields.

- `pred`: the predicted class (`Canola`, `Cereal` or `Legume`), or null where the polygon was not classified.
- `abstain_reason`: why a polygon was not classified, one of `area_below_min`, `no_crop_signal`, `too_few_observations` or `unsegmented_blob` (Methods). In 2024 these hold 305,943, 227,263, 38,177 and 9,293 polygons respectively. A fifth value, `no_crop_shape`, flags a classified polygon whose seasonal NDVI curve lacks a clear green-up and senescence. Such a polygon keeps its class and counts as classified in every total reported here.
- `confidence`: the classifier's probability for the predicted class, and `p_canola`, `p_cereal` and `p_legume`, the probability of each class. Null where `pred` is null.
- `ndvi_amp`: the NDVI amplitude used by the presence gate, on every polygon.
- `yield_tha` and `yield_tha_calibrated`: raw (NVT-equivalent) and ABS-calibrated cereal yield in tonnes per hectare, on cereal polygons only.
- `area_ha`, `compactness`, `n_obs`, `clear_frac` and `treed_frac`: the polygon's area, compactness ratio, number of clear Sentinel-2 observations, mean clear fraction and estimated tree cover fraction.
- `year` and `stub`: the season and the tile the polygon came from.
- Provenance of the tile-overlap merge: `boundary_action`, `merge_n`, `class_conflict`, `raster_cut_m` and `overlap_merge_n`. `raster_cut_m` is the length of boundary within 30 m of the tile's raster edge, and `class_conflict` marks a paddock whose two tile views disagreed on class. Both can be used as quality flags.
- `geometry`: the paddock polygon.

Two derived subsets accompany each annual file for convenience. The classified subset keeps only polygons with a class, with `pred` renamed `predicted_crop_type` and a QGIS style embedded. The strict subset keeps only polygons with a class and an empty `abstain_reason`. For 2024 these hold 429,951 and 344,868 polygons. Neither subset should be used for any claim about abstain rates, total polygon counts or total mapped area. Each removes the rows those claims depend on.

## Product 2: consensus paddock layer, 2017-2025

One GeoPackage holds one polygon per paddock that at least five of the nine annual segmentations agreed on, filtered to 5-300 ha. It contains XXX paddocks. Each carries `crop_<year>` and `conf_<year>` for every season from 2017 to 2025. It also records the number of seasons in which the paddock was found and classified, and the number of distinct crop groups it grew. The outline is one season's real segmentation rather than an average across seasons, since an averaged boundary matches no year's imagery. Note this means `crop_2019`, for example, is the class of the 2019 polygon matched to the consensus outline, whose boundary differs by a few metres.

## Model artefacts

The classifier (`group3_map_sharma6.joblib`) and the cereal yield model (`cereal_yield.joblib`) are released with the data (Code Availability). A user can re-derive any prediction from the 153-feature paddock-median input described in Methods.

---

# Technical Validation

## Classifier accuracy

The classifier reaches a macro F1 of 0.890 under temporal transfer and 0.892 under spatial transfer (Table 2, Fig. 4). Both are scored on the fixed test set of 543 trials. Canola is detected at 89.0% recall at a 5% false-positive rate (average precision 0.935, ROC AUC 0.962). Legume is the weakest class in both splits, with precision 0.77 and 0.79. The main confusion is canola predicted as legume (19 of 155 true canola paddocks under temporal transfer, 16 under spatial transfer). The next is cereal predicted as legume (10 and 8 of 279).

**Table 2.** Classifier accuracy by class and split, 543 fixed test trials sown in 2023-2024.

| Split (macro F1) | Class | Precision | Recall | F1 | n |
|---|---|---|---|---|---|
| Temporal (0.890) | Canola | 0.93 | 0.85 | 0.89 | 155 |
| | Cereal | 0.96 | 0.95 | 0.96 | 279 |
| | Legume | 0.77 | 0.89 | 0.83 | 109 |
| Spatial (0.892) | Canola | 0.91 | 0.88 | 0.89 | 155 |
| | Cereal | 0.97 | 0.96 | 0.96 | 279 |
| | Legume | 0.79 | 0.85 | 0.82 | 109 |

The alternatives listed in Methods were scored on the same test set. With the three original indices, random forests (0.830 temporal, 0.820 spatial) and extra trees (0.823, 0.819) matched the gradient-boosted model (0.821, 0.823). Logistic regression fell short (0.745, 0.768). Fine-tuned Presto embeddings scored 0.775 alone and 0.824 combined with the indices. Adding Sentinel-1 backscatter to the final classifier lowered macro F1 by 0.023 (temporal) and 0.018 (spatial), concentrated in the legume class.

## Map accuracy at trial sites

The released pipeline was scored at the 533 test trials from 2023 and 2024 that fall on the tile grid. The classifier copy trained on trials sown 2022 or earlier was used. 122 sites had no segmented polygon and 62 fell in a polygon that abstained. On the 349 scored sites the map reached a macro F1 of 0.898 (canola 0.893, cereal 0.952, legume 0.848). The polygon containing a site was within a factor of two of the trial paddock's recorded area at 91% of sites.

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

Across the 151 well-covered SA2s, the mapped canola share of crop area tracks the ABS share (Fig. 5). The correlation is r = 0.76 and the median absolute error is 4.3 percentage points. That error is below the 6.8% disagreement between the two official series. The mapped area, however, is larger than the sown area ABS records. The median ratio of mapped crop area to ABS sown area over the same SA2s is 1.10. Earlier versions of the map called more. The ratio was 1.47 on a 3 km-tile map with no de-duplication. It was 1.31 on the 9 km map before the tile-overlap step and 1.18 after it. The final overlap merge and the 300 ha cap on merged polygons brought the ratio to 1.10.

Table 4 divides the over-call by class. The diluted share is what a perfect classifier would report on this footprint, the ABS share divided by the over-call. The absorbed column is the excess mapped share each class carries. The excess sits in cereal and legume. Canola sits 3.7 points below its diluted share, so the map calls slightly too little land canola and too much land legume.

**Table 4.** Composition against ABS, 151 SA2s, 2024. Shares are medians over SA2s.

| Class | ABS share | Diluted share | Mapped share | Absorbed (points) |
|---|---|---|---|---|
| Canola | 19.2% | 17.4% | 13.7% | -3.7 |
| Cereal | 67.3% | 61.2% | 65.8% | +4.7 |
| Legume | 8.9% | 8.1% | 16.1% | +8.0 |

The legume share, 16.1% of classified area against 8.9% in ABS, is the largest composition error in the map. An argmax-versus-mean-probability check rules out a decision-rule artefact such as a systematic tie-break (Table 5). Area-weighted over the same polygons, the share of each class by argmax and by mean predicted probability agree within 0.6 points for every class. The classifier favours legume at this rate rather than reporting it inconsistently. The confusion matrices point the same way, since canola and cereal paddocks are predicted as legume more often than the reverse. However they do not account for the size of the gap. The mechanism remains open.

**Table 5.** Class share of classified area by decision rule, national 2024 map.

| Class | Argmax share | Mean probability share | ABS |
|---|---|---|---|
| Canola | 15.4% | 15.7% | 19.2% |
| Cereal | 66.7% | 66.1% | 67.3% |
| Legume | 18.0% | 18.2% | 8.9% |

Table 6 re-scores the same polygons at five presence-gate thresholds. Thresholds below 0.35 cannot add polygons, because the released map was built at 0.35. Raising the threshold to 0.50 removes 26% of classified area and changes the canola share error by 0.5 points. Composition is therefore insensitive to the threshold while area is not. This is consistent with the reading that the map's main disagreement with ABS is presence rather than class.

**Table 6.** Sensitivity of the 2024 map to the NDVI amplitude threshold. Share errors are medians over the 151 SA2s.

| Threshold | Classified area (ha) | Canola share error (points) | Legume share error (points) |
|---|---|---|---|
| 0.25 | 19,575,177 | 5.7 | 9.1 |
| 0.30 | 19,575,177 | 5.7 | 9.1 |
| 0.35 (released) | 19,575,177 | 5.7 | 9.1 |
| 0.40 | 18,036,667 | 5.7 | 8.8 |
| 0.45 | 16,341,696 | 5.3 | 8.6 |
| 0.50 | 14,462,331 | 5.2 | 8.0 |

## Comparison with WorldCereal and NLUM

Both products predate the 2024 map by three years, so some disagreement is real change in what was grown. Against WorldCereal's `temporarycrops` layer, the map's classified-versus-abstained presence call agrees at 76.1% of the 250,000 sampled centroids. 82.1% of abstained centroids are also no-crop in WorldCereal, and 67.9% of classified centroids are also crop. Of the 71,684 centroids the map calls cereal, 44.3% are `wintercereals` in WorldCereal. WorldCereal is an independent product rather than ground truth, so this does not establish which product is right where they differ.

Against NLUM, the median oilseed probability at canola centroids is 8.5 times the median at abstained centroids. The cereal ratio at cereal centroids is 1.5 and the legume ratio at legume centroids is 1.0. NLUM therefore rates the map's canola and cereal polygons as more probable for those commodities than abstained land, but not its legume polygons. NLUM's grazing layer supports the presence-gate reading from an unrelated source. The median grazing probability is 60.7% at abstained centroids against 16.9% at classified centroids. Abstained land is therefore concentrated on land NLUM rates as probable grazing country.

## Cereal yield

The cereal yield model reaches a spatial-transfer root-mean-square error of 1.21 t/ha, 30.4% of the 3.97 t/ha median trial yield (Table 7, Fig. 6). On the temporal split the year-and-state baseline collapses to a state-only model, because the test seasons are unseen. The satellite features still reach an R² of 0.47. The ABS calibration factor, fitted on 2022, reproduced the ABS implied yield within 18.1% in 2023 and 3.1% in 2024.

**Table 7.** Cereal yield model before calibration, pooled wheat, barley and oat.

| Split | Features | n | R² | RMSE (t/ha) |
|---|---|---|---|---|
| Temporal (train 2022 or earlier, test 2023-24) | Year and state baseline | 279 | -0.643 | 2.111 |
| | Satellite features | 279 | 0.471 | 1.197 |
| | Satellite, year and state | 279 | 0.486 | 1.181 |
| Spatial (five-fold GroupKFold on site) | Year and state baseline | 1,119 | 0.294 | 1.473 |
| | Satellite features | 1,119 | 0.526 | 1.207 |
| | Satellite, year and state | 1,119 | 0.577 | 1.140 |

## National multi-year maps

Table 8 summarises the nine seasons. Classified share ranged from XXX% (XXX) to XXX% (XXX). Against ABS at SA2, mapped canola composition gave r = XXX, XXX and XXX for 2022, 2023 and 2024. The area ratio was XXX, XXX and XXX. Against ABARES state totals, the median absolute error of mapped canola area was XXX% over XXX state-seasons. The median IoU between a paddock's polygons in consecutive seasons was XXX. A consensus paddock was found in a median of XXX of the nine seasons. Of consensus paddocks classified in two consecutive seasons, XXX% changed class, and canola was followed by cereal in XXX% of cases (Fig. 7). Canola is normally grown as a break crop between cereals. Note this means a high rate of repeated canola would point to classification error rather than agronomy. The 2025 season has no ABS figures and no final ABARES figures, so its map is unscored.

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

Every polygon carries either a class or an abstain reason, together with `ndvi_amp`, `confidence` and the class probabilities. A user who needs area accuracy rather than composition accuracy can filter the map with these fields instead of waiting for a revised release. Raising the `ndvi_amp` threshold above 0.35 trades completeness for a lower area over-call, and Table 6 quantifies the trade-off. The strict subset (Data Records), which removes polygons flagged `no_crop_shape`, is a ready-made stricter view. The `raster_cut_m` and `class_conflict` fields identify polygons cut at a tile edge or seen differently by two tiles.

Users computing absolute crop area should expect the map to call about 1.10 times the area ABS records as sown, unless they filter as above. The excess sits in cereal and legume rather than canola. Composition estimates that rest on canola are therefore the most directly validated use of the map.

Cereal yield users should read both yield columns. `yield_tha` reflects trial management, which out-yields commercial paddocks, and `yield_tha_calibrated` applies a single national factor checked against ABS at state level only. The calibrated column is indicative at paddock scale, not exact. No canola or legume yield is provided. Canola yield needs Sentinel-1 backscatter to beat a year-and-state mean (Methods), and Sentinel-1 is not yet part of the pipeline. A legume model does beat that baseline, but the map does not resolve legumes to species, so legume yield is held for a future release (Methods).

The legume class is mapped at 16.1% of classified area against an ABS share of 8.9%, and the cause is not established. Users relying on the legume class should weight it accordingly against the cereal and canola classes.

Polygons marked `unsegmented_blob` are SAM's main failure mode, ground where several fields were returned as one shape. They carry no class and cannot be recovered from this release without a second segmentation pass. In 2024 they number 9,293 polygons covering 4.5 M ha.

The 2024 map can also be viewed and queried in Google Earth Engine as a public asset (XXX asset path). A viewer script is in the code repository.

The GRDC National Variety Trial records used to build and validate this dataset are covered by a data-use agreement. They cannot be released at the site level (coordinates, trial identifiers or yields). This dataset and its validation reports contain only aggregate statistics derived from those records.

---

# Data Availability

The annual national maps and the consensus paddock layer described in Data Records are deposited at XXX under DOI XXX. The GRDC National Variety Trial records used for training and validation cannot be released under the data-use agreement covering them. These are the trial coordinates, crop identities, sowing and harvest dates and yields. They can be requested from the GRDC at XXX. The restriction applies to the raw trial records only, not to the released maps or the aggregate statistics reported here. ABS and ABARES statistics, the NLUM probability surfaces and WorldCereal are public. This manuscript will be provided to the GRDC for review before submission, as the data-use agreement requires.

# Code Availability

The pipeline code (segmentation, labelling, classification, abstention, yield calibration, multi-year consensus and validation scripts) contains no site-level records and is released at XXX. The classifier (`group3_map_sharma6.joblib`) and the cereal yield model (`cereal_yield.joblib`) used to produce the released data are included in the same repository.

# Author Contributions

C.B.: conceptualisation, methodology, software, formal analysis, data curation, visualisation, writing (original draft), writing (review and editing). J.B.: conceptualisation, software, writing (original draft), writing (review and editing). Y.A.A.: conceptualisation, software, writing (original draft), writing (review and editing). J.O.B.: funding acquisition, supervision, writing (review and editing).

# Competing Interests

The authors declare no competing interests.

# Acknowledgements

We thank the Grains Research and Development Corporation and the National Variety Trials network for the trial data. We thank the National Computational Infrastructure for compute access and the Digital Earth Australia datacube.

---

# References

ABARES (2024). Land use of Australia 2010-11 to 2020-21: agricultural commodity probability surfaces, version 7 (NLUM v7, 250 m). Australian Bureau of Agricultural and Resource Economics and Sciences, Canberra. XXX

Al-Shammari, D., Fuentes, I., Whelan, B.M., Wang, C., Filippi, P. and Bishop, T.F.A. (2024). Combining Sentinel 1, Sentinel 2 and MODIS data for major winter crop type classification over the Murray Darling Basin in Australia. *Remote Sensing Applications: Society and Environment*, 34, 101200. doi:10.1016/j.rsase.2024.101200

GRDC (XXXX). National Variety Trials protocols. Grains Research and Development Corporation. XXX

Boogaard, H., Pratihast, A.K., Laso Bayas, J.C., Karanam, S., Fritz, S., Van Tricht, K., Degerickx, J. and Gilliams, S. (2023). Building a community-based open harmonised reference data repository for global crop mapping. *PLOS ONE*, 18(7), e0287731. doi:10.1371/journal.pone.0287731

Kerner, H., Chaudhari, S., Ghosh, A., Robinson, C., Ahmad, A., Choi, E., Joshi, N., Tadros, M., Malkin, N. and Ortiz, C. (2024). Fields of The World: a machine learning benchmark dataset for global agricultural field boundary segmentation. arXiv:2409.16252.

Kirillov, A., Mintun, E., Ravi, N., Mao, H., Rolland, C., Gustafson, L., Xiao, T., Whitehead, S., Berg, A.C., Lo, W.-Y., Dollár, P. and Girshick, R. (2023). Segment Anything. In *2023 IEEE/CVF International Conference on Computer Vision (ICCV)*, 3992-4003.

Olofsson, P., Foody, G.M., Herold, M., Stehman, S.V., Woodcock, C.E. and Wulder, M.A. (2014). Good practices for estimating area and assessing accuracy of land change. *Remote Sensing of Environment*, 148, 42-57. doi:10.1016/j.rse.2014.02.015

PaddockTS (XXXX). XXX

Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M. and Duchesnay, É. (2011). Scikit-learn: machine learning in Python. *Journal of Machine Learning Research*, 12, 2825-2830.

Sharma, S., Eslick, H., Pires, R., Singh, B. and Tareque, H. (2026). Temporal sensitivity of in-season crop classification: an explainable multi-year Sentinel-2 analysis in Western Australia. *Remote Sensing*, 18(10), 1653. doi:10.3390/rs18101653

Sulik, J.J. and Long, D.S. (2016). Spectral considerations for modeling yield of canola. *Remote Sensing of Environment*, 184, 161-174. XXX

Tian, H., Chen, T., Li, Q., Mei, Q., Wang, S., Yang, M., Wang, Y. and Qin, Y. (2022). A novel spectral index for automatic canola mapping by using Sentinel-2 imagery. *Remote Sensing*, 14(5), 1113. XXX

Tseng, G., Cartuyvels, R., Zvonkov, I., Purohit, M., Rolnick, D. and Kerner, H. (2024). Lightweight, pre-trained transformers for remote sensing timeseries. arXiv:2304.14065.

Van Tricht, K., Degerickx, J., Gilliams, S., Zanaga, D., Battude, M., Grosu, A., Brombacher, J., Lesiv, M., Bayas, J.C.L., Karanam, S., Fritz, S., Becker-Reshef, I., Franch, B., Mollà-Bononad, B., Boogaard, H., Pratihast, A.K., Koetz, B. and Szantoi, Z. (2023). WorldCereal: a dynamic open-source system for global-scale, seasonal, and reproducible crop and irrigation mapping. *Earth System Science Data*, 15, 5491-5515. doi:10.5194/essd-15-5491-2023

Wu, Q. and Osco, L.P. (2023). samgeo: a Python package for segmenting geospatial data with the Segment Anything Model (SAM). *Journal of Open Source Software*, 8(89), 5663. XXX
