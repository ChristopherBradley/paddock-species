# A National, Field-Level Crop-Species Map of Australia from Sentinel-2

**Short title (for running head)**: A National Crop-Species Map of Australia from Sentinel-2
**Authors**: [PLACEHOLDER - author list and affiliations to be supplied by the user]
**Manuscript type**: Research Paper - Remote Sensing of Environment
**Draft status**: PARTIAL (see DRAFT_README.md). Every number marked XXX is a map-derived result awaiting the 2024 national re-run with the adopted nine-index classifier and the revised 9 km tile geometry (launched 2026-09-10); Section 5.1 already reports the adopted classifier.

<!-- Assembled 2026-09-10 from sections/ by assemble.py. Edit the section files, not this one. -->

---

# Abstract

Australia's grains sector has no continent-wide, paddock-scale crop-species map built on recorded ground truth. Global products classify cropland generically and the closest Australian precedents are regional. We present a national field-level map that segments paddocks with the Segment Anything Model and classifies them as canola, cereal or legume. The classifier is a gradient-boosted model on spectral indices, trained on 2,194 Grains Research and Development Corporation National Variety Trial records. A presence gate decides whether each segmented paddock carries enough evidence of cropping to classify. Classified cereal paddocks also receive a calibrated yield estimate. The 2024 national map contains XXX segmented polygons, of which XXX% carry a classification and the remainder an explicit abstain reason. We validated the map against independent Australian Bureau of Statistics (ABS) sown-area statistics across XXX censused Statistical Area Level 2 regions. Mapped canola composition tracks the official statistic with r = XXX and a median absolute error of XXX points; for comparison, ABS and a second official series disagree by a median 6.8%. The map over-calls crop-present area by XXX times, concentrated in cereal and legume rather than canola. The over-call is a presence-detection problem rather than a classification problem, which independent comparison against WorldCereal and the National Land Use Map supports. A phenology-shape presence gate, requiring green-up and senescence rather than amplitude alone, closed the area gap regionally but rejected real canola paddocks at a higher rate than cereal or legume, so we rejected it. This is a caution for presence-gate design in crop mapping.

## Highlights

- National 10 m map of XXX paddocks in 3 crop classes, from recorded ground truth.
- Canola composition matches independent ABS statistics closely (r = XXX).
- Map over-calls crop area XXXx: a presence failure, not a classification failure.
- A more principled presence gate fixed area but broke canola recall; rejected.
- Independent WorldCereal/NLUM comparison corroborates the presence diagnosis.

## Graphical Abstract

*Reuses Fig. 1's elements: the six-stage pipeline schematic (Sentinel-2 time series → SAM
segmentation → paddock mask → spectral-index classifier → presence gate → cereal yield
calibration) above a small real-output map panel, coloured by predicted class with
unclassified (abstained) paddocks shown in grey rather than omitted. See
`output/figures/Fig01_hero.png` and its script `output/figures/scripts/Fig01_hero.py`.*

---

# 1. Introduction

Australia's grains sector (wheat, barley, canola and pulse/legume crops) is a major export industry. Yet no continent-wide crop-species map, built on recorded ground truth, exists at paddock scale. Official production and area statistics from the Australian Bureau of Statistics (ABS) and the Australian Bureau of Agricultural and Resource Economics and Sciences (ABARES) are available only at coarse administrative-region granularity, with no spatial detail below the Statistical Area Level 2 (SA2) or state level. The two agencies disagree with each other by a median 6.8% on national sown area, which is the floor against which any finer-grained map should be judged. A spatially explicit, species-resolved product would let growers, agronomists and policy analysts see where each crop is actually grown, at the scale a single farm operates, instead of inferring it from a regional aggregate.

Remote sensing has made continent- and global-scale cropland mapping technically feasible, but scale and species resolution trade off against each other in practice. Products built for global coverage typically classify land as cropland versus non-cropland, or into a small number of broad crop-type groups defined by growing calendar rather than species, because building species-resolved training data at global scale is prohibitively expensive. Australia sits in a Southern Hemisphere, canola-and-legume-growing agricultural system that most global crop-calendar-based products were not designed around. Even where global coverage exists, its species resolution and seasonal assumptions may not transfer.

Three threads of prior work bear on this problem. Global crop-mapping infrastructure delivers broad coverage but coarse or generic crop-type resolution: WorldCereal (Van Tricht et al., 2023), foundation-model embeddings such as Presto (Tseng et al., 2024) and AlphaEarth (Brown et al., 2025) and generic land-cover products such as Esri/Impact Observatory's global land-use-land-cover layer (Karra et al., 2021). None of these has been evaluated for Australian species-level generalisability. Two Australian precedents come closer to species-level resolution. Sharma et al. (2026) built an in-season Sentinel-2 classifier for six classes in Western Australia. Al-Shammari et al. (2024) built a Sentinel-1/Sentinel-2/MODIS fusion classifier distinguishing cereals from canola in the Murray-Darling Basin. Both are regional studies, trained respectively on another model's pseudo-labels and on opportunistic harvester-derived labels. A third thread addresses the paddock-boundary problem this map also depends on. CSIRO's ePaddocks/Graincast system (Lawes et al., 2022) is the closest operational Australian precedent for boundary-plus-yield mapping at scale. The Segment Anything Model (SAM; Kirillov et al., 2023), the segmentation backbone used here, and Fields of the World (Kerner et al., 2024), a cloud-robust Sentinel-1/Sentinel-2 boundary-delineation benchmark, are the general-purpose segmentation methods this paper draws on instead of a bespoke Australian boundary product. Fields of the World does not itself cover Australia.

This paper targets a specific combination that, to our knowledge, no published map yet delivers for the Australian grains system: continent-wide coverage, paddock-scale resolution, species-level classification rather than cropland only, and training on recorded ground truth. The original scope was a classifier for around ten species, trained by foundation-model fine-tuning. The trial data contain nine species, and at the recorded label volume available a nine-species classifier reached only macro F1 0.38, while fine-tuned Presto embeddings scored worse than the three-index spectral feature set (macro F1 0.775 versus 0.821). We report both as negative results, and instead use a three-group classifier (canola, cereal and legume) built on day-of-year-binned spectral indices.

This paper makes two primary contributions. First, we present a national, field-level, three-class crop-species map of Australia at 10 m resolution, built end-to-end from open Sentinel-2 imagery and 2,194 GRDC National Variety Trial (NVT) records, recorded sowings rather than another model's predictions or opportunistic harvester data. Every polygon carries a predicted class or an explicit abstain reason, a per-polygon confidence and, for cereal, a calibrated yield estimate. The map is validated against independent ABS sown-area statistics with no connection to the training pipeline. Second, we quantify and explain a systematic area-inflation failure mode in presence-only crop mapping. The map over-calls crop-present area by XXXx, concentrated in the cereal and legume classes rather than canola. The more principled fix, a phenology-shape presence gate, closed the area gap but did so by rejecting real canola paddocks at a higher rate than the other crops, so we rejected it. This is a caution for presence-gate design in crop mapping generally. Two further findings support these contributions. First, collapsing species to three broad groups resolves 69% of the label conflicts that co-located trials create in a point-based agronomic trial network, and hand-reviewing the remainder improves macro F1 by 0.019 over an unreviewed control. Second, foundation-model embeddings did not beat spectral indices at this label volume, as reported above.

The remainder of this paper is organised as follows. Section 2 reviews related work in global crop mapping, Australian precedents, paddock-boundary delineation and accuracy-assessment standards. Section 3 describes the study area and data sources. Section 4 describes the segmentation, labelling, classification, presence-gating and yield-calibration methods. Section 5 reports classifier accuracy, the ABS validation, the phenology-gate experiment, yield calibration and an independent spatial comparison against the WorldCereal and National Land Use Map (NLUM) products. Section 6 discusses the area-inflation finding and its implications for presence-gate design. Section 7 states limitations, of which the largest is single-season (2024) national coverage pending the multi-year national extension, and Section 8 concludes.

---

# 2. Related Work

## 2.1 Global crop-mapping infrastructure and foundation models

A growing ecosystem of global and continental crop-mapping products now provides open, regularly updated coverage. WorldCereal (Van Tricht et al., 2023) is the most directly comparable product. It is a dynamic, open-source system producing seasonal maize, winter-cereal and spring-cereal classifications, plus a general temporary-cropland extent layer, from Sentinel-1 and Sentinel-2, tiled across 106 globally defined agro-ecological zones. Its design priorities target globally widespread cereal and maize systems, and it has no canola or legume class, reflecting a different agricultural focus than the Southern Hemisphere oilseed-and-pulse rotations that structure the Australian grains sector. Foundation-model embeddings offer a general-purpose alternative to spectral features. Presto (Tseng et al., 2024) pretrains a lightweight transformer on multi-modal pixel time series (optical, radar, climate, terrain) for downstream fine-tuning. AlphaEarth (Brown et al., 2025) extends this idea to a general-purpose annual embedding at global scale. Generic land-use-land-cover products such as Esri/Impact Observatory's global layer (Karra et al., 2021) classify cropland as a single category, without species or crop-type resolution.

Relative to this cluster, this paper is a local adaptation and comparison study with two negative results rather than a new infrastructure contribution. We fine-tuned Presto on our own recorded labels and found it lost to day-of-year-binned spectral indices (NDVI, a canola-specific flowering index and a chlorophyll-fluorescence-related index) at this label volume and class granularity: macro F1 0.775 versus 0.821 for the three-index feature set that preceded the adopted classifier (Section 4.3), and worse on canola detection (74.2% versus 89.0% at a 5% false-positive rate). Combining Presto embeddings with these features gave no improvement over the features alone (0.824 versus 0.821, within the noise of a size-matched control comparison). Three of Presto's nine expected input channel groups (Sentinel-1 radar, ERA5 climate and SRTM terrain) were absent from our input data and had to be passed as masked. We read this as a limitation of our input data rather than a finding about Presto's architecture. We also directly compared our national map against WorldCereal's 2021 products at the pixel level (Section 5.5). Because WorldCereal has no canola or legume class, only the presence/absence extent layer and the wintercereals layer are checkable against our output. Neither product is treated as ground truth.

## 2.2 Australia-specific crop-type classification precedents

Two studies are the closest direct precedents. Sharma et al. (2026) built an in-season Sentinel-2 classifier for six crop classes in Western Australia, using day-after-sowing-derived pseudo-labels for the bulk of training data, supplemented by a smaller recorded test set. Al-Shammari et al. (2024) fused Sentinel-1, Sentinel-2 and MODIS to distinguish cereals from canola across the Murray-Darling Basin, training on harvester-derived yield-map labels rather than recorded sowings. Both reach classification accuracies above 90% within their study regions. This paper trades species resolution (three broad groups rather than six crops) for continent-wide coverage and for training on GRDC National Variety Trial records. Those records are field-recorded sowings, whereas Sharma et al.'s pseudo-labels are model-derived and Al-Shammari et al.'s harvester labels are opportunistic records of what a combine harvested, not confirmed sowings. As far as we are aware, neither study's classified output has been released as a public dataset; this paper's national map, releasable as described in the Data and Code Availability statement, extends what is publicly checkable in this space **[VERIFY: we could not confirm this from the published articles directly - please check against the papers' own data-availability statements before submission]**.

A third, operationally oriented precedent is CSIRO's Graincast system (Lawes et al., 2022), which combines a field-boundary product (ePaddocks) with a satellite-and-climate-driven yield model to monitor crop production across the Australian grainbelt at national scale. Graincast's boundary-plus-yield pattern is the closest operational analogue to this paper. The original project brief specified ePaddocks as the boundary source, but this project replaced it with Segment Anything Model (SAM) segmentation early in development (Section 2.3).

## 2.3 Field and paddock boundary delineation

Paddock boundaries were delineated with the Segment Anything Model (SAM; Kirillov et al., 2023), a general-purpose, promptable image-segmentation foundation model, applied here via the SAMGeo/PaddockTS geospatial wrapper with stock parameters. Fields of the World (Kerner et al., 2024) is the closest purpose-built boundary-delineation method: a cloud-robust Sentinel-1 and Sentinel-2 field-boundary model evaluated against a multi-country benchmark. The benchmark does not include Australia; only a model-predicted global product extends to the continent. The absence of Australian ground-truth boundary data was one reason for choosing a general-purpose segmentation model over a boundary-specific method that could not be evaluated locally.

## 2.4 Accuracy-assessment standards for crop and land-cover maps

Olofsson et al. (2014) set out the field's stated good-practice standard for map accuracy assessment and area estimation: stratified probability sampling of reference data, error matrices and confidence intervals on both accuracy and estimated area. Our validation departs from this standard, and the reason matters for how the results should be read. Olofsson-style area estimation requires a probability sample of reference labels, stratified by map class. No such sample of recorded crop-species labels exists for Australia at the density this would require, because the GRDC/NVT trial network is a purposively sited agronomic trial program rather than a probability sample of the landscape. In its place, this paper validates against ABS sown-area statistics, aggregated to the SA2 level. This is an independent, non-training-derived reference, though itself uncertain (ABS and ABARES, its sister agency, disagree with each other by a median 6.8% on national sown area). We report composition and area-ratio comparisons rather than a stratified accuracy assessment with confidence intervals (Section 7, Limitation 8).

## 2.5 Positioning relative to the nearest competing approaches

The nearest competing approaches are WorldCereal for global coverage, and Sharma et al. (2026) and Al-Shammari et al. (2024) for Australian species-level classification. This paper differs from them in ground-truth provenance and geographic coverage: continent-wide, three classes, trained end-to-end on field-recorded sowings. The cost is coarser species resolution than either Australian precedent. The original species-level scope was not reachable at the available recorded label volume (nine-class macro F1 0.38), and the three-group design is itself a finding about the label volume that species classification from recorded labels requires (Sections 1 and 4.2).

*Note on data lineage*: Newman and Furbank (2021, *Nature Plants*) describes the same underlying GRDC National Variety Trial network this paper's ground truth is drawn from. It is not an independent public dataset, and this paper does not point readers toward it as a substitute or independent replication source. It is cited here only to acknowledge the shared data lineage.

---

# 3. Study Area and Data

## 3.1 Study area

The completed national map covers continent-wide Australia, comprising XXX tiles for the 2024 growing season, which cover XXX% of the national extent where the National Land Use Map (NLUM) probability surfaces indicate agricultural probability for one of the three target crop groups. A 100 km × 100 km block in the Riverina region of New South Wales, a major mixed-cropping district, was used for a nine-season (2017-2025) regional test of the same pipeline. It is reported separately from the national result because only the regional extent has multi-year coverage (Section 3.2; Section 7, Limitation 4). Fig. 2 [XXX: regenerate from the re-run] shows the national tile coverage, the Riverina block and the SA2 regions used for validation (Section 3.3).

## 3.2 Temporal scope

A single growing season, 2024, is complete and validated at national scale. Nine seasons (2017-2025) are complete at the 100 km regional scale. A national extension to the remaining eight seasons (2017-2023, 2025) is planned but has not yet been run at the time of this draft [PENDING: national 2017-2025 run, E8]. All multi-year results and figures in this paper are regional, and are evidence for but not proof of national multi-year generalisation (Section 6.6).

## 3.3 Data sources

Table 1 summarises the datasets used. Sentinel-2 surface-reflectance imagery was accessed via Digital Earth Australia's Analysis Ready Data product (`ga_s2am/bm/cm_ard_3`) through the National Computational Infrastructure's datacube, at 10 m resolution, nationally, 2017-2025. Ground truth for training and validation is drawn from the Grains Research and Development Corporation (GRDC) National Variety Trial (NVT) network: recorded, point-located records of sown crop per trial site, spanning 2017-2025 nationally. This dataset is covered by a data-use agreement and cannot be released or described at the site level (coordinates, trial identifiers or yields); all reporting in this paper is aggregate. Independent validation uses ABS sown-area statistics aggregated to the SA2 level, which have no connection to the training pipeline. ABARES production statistics provide a cross-check on ABS itself, and the two agencies' median 6.8% disagreement on national sown area is the accuracy floor this paper measures its map against (Section 5.2). The NLUM v7 250 m per-commodity agricultural probability surfaces (2020-21) were used for two purposes: during national inference, to restrict segmentation and classification to tiles with non-trivial probability for one of the three target crop groups; and afterwards, as an independent spatial-comparison product (Section 5.5). Paddock boundaries were delineated with the Segment Anything Model (`vit_h` checkpoint, stock parameters; Kirillov et al., 2023) via the SAMGeo/PaddockTS wrapper. Re-tuning SAM's parameters was tested as a fix for poorly segmented polygons and ruled out (Section 4.1).

**Table 1.** Dataset and pipeline summary.

| Dataset | Role | Resolution / extent | Access |
|---|---|---|---|
| Sentinel-2 (DEA ARD) | Primary imagery; day-of-year-binned spectral indices | 10 m, national, 2017-2025 | Open |
| GRDC / NVT trial records | Training and validation ground truth | Point-in-paddock, national, 2017-2025 | Data-use agreement; not releasable; aggregate reporting only |
| ABS sown-area statistics | Independent validation reference | SA2-level, XXX SA2s, national | Public |
| ABARES production statistics | Cross-check on ABS (6.8% median mutual disagreement) | State / national | Public |
| NLUM v7 250 m Ag. Probability Surfaces | (a) National-run coverage mask; (b) independent spatial-comparison product | 250 m, national | Public |
| WorldCereal 2021 v100 | Independent spatial-comparison product | 10 m, national AU extent | Public (CC-BY 4.0) |
| Segment Anything Model (SAM) | Paddock-scale segmentation, stock parameters | 10 m-derived polygons | Open weights |

## 3.4 Preprocessing

Segmented polygons were retained only within a 5-300 ha area range and with a compactness ratio (perimeter / sqrt(area)) of at most 8. This geometric filter is also a non-spectral presence signal, since land without paddock-scale field boundaries is rarely segmented into polygons in this size range; it retains XXX% of NVT trial paddocks and excludes the remainder as too small, too large or too irregular. Per retained polygon, 153 paddock-median spectral features were computed (17 per index, binned by day of year across the growing season) from nine indices: NDVI, a canola-specific flowering index following the general approach of Ashourloo et al. (2019), a chlorophyll-fluorescence-related index and six band-derived indices used by Sharma et al. (2026): NDRE2, VI2, VI3, VDVI, VCI and EVI2 (Section 4.3). NVT trial points were matched to their enclosing (or, where no polygon contained the point, nearest plausible) SAM polygon. Because 69.7% of training trials share a segmented paddock with another NVT trial (31.8% with a different crop, reflecting how trial networks co-locate multiple varieties), the original nine-species label scheme was collapsed to three broad groups, resolving 69% of these label conflicts, and the remainder were resolved by hand review (Section 4.2).

---

# 4. Methodology

Figure 1 summarises the pipeline: Sentinel-2 time series drive both paddock segmentation and a spectral-index classifier; a presence gate determines whether a segmented paddock is classified at all; and a calibrated model attributes cereal yield to classified paddocks. Section 5 reports the accuracy and validation results the design choices below were selected against.

## 4.1 Segmentation

Each tile was segmented with the Segment Anything Model (`vit_h` checkpoint, stock parameters; Kirillov et al., 2023), applied via the SAMGeo/PaddockTS wrapper. Re-tuning SAM's segmentation parameters (point-grid density, IoU and stability-score thresholds) was tested as a way to reduce large under-segmented "blob" polygons, SAM's largest failure mode in this application (Section 7, Limitation 3). Parameter sweeps did not resolve the failure mode, and the area and compactness mask (Section 3.4) was retained as the primary control instead. Polygons were filtered to a 5-300 ha area range and a compactness ratio of at most 8, a geometric presence filter applied ahead of any spectral classification.

## 4.2 Labelling

GRDC National Variety Trial (NVT) points were matched to their enclosing (or, where no polygon contained the point, nearest plausible) SAM polygon. Two label-integrity problems were addressed. First, because NVT trials are agronomic variety comparisons, trials of different crops are often co-located within one paddock (69.7% of training trials share a segmented paddock with at least one other trial; 31.8% of those co-located pairs are of different crops), which would inject label noise into paddock-level features. Collapsing the original nine-species scheme to three broad groups (canola; cereal, comprising wheat, barley and oat; legume, comprising chickpea, faba bean, field pea, lentil and lupin) resolves 69% of these conflicts by construction, because co-located trials of different species within the same group no longer conflict. The three-group scheme is also justified on accuracy: a nine-species classifier trained on the same label pool, with the three-index feature set and the evaluation protocol of Section 4.3, reached macro F1 0.38, whereas the three-group scheme reached 0.821-0.823 with the same features (Section 5.1). The two justifications are separate. The conflict-resolution benefit follows from having fewer classes regardless of accuracy, and the accuracy gap follows from per-class label volume, but both point to the same design. The remaining ambiguous matches were resolved by hand review of a stratified sample of flagged polygons, which improved macro F1 by 0.019 over a size-matched unreviewed control (Section 5.1). Second, a small number of matches to implausibly small polygons (a road or laneway sliver rather than the adjacent paddock) were upgraded to a polygon at least three times larger within 150 m of the trial point. The same matcher rule is used for training-label extraction and for human review, so the two cannot drift apart.

## 4.3 Classification

A `HistGradientBoostingClassifier` was trained on the 153 paddock-median, day-of-year-binned spectral features described in Section 3.4 to predict one of the three crop groups. The feature set was built in two stages. The first national map used three indices (NDVI, the canola flowering index and the chlorophyll-fluorescence-related index; 51 features). Adding six band-derived indices used by Sharma et al. (2026), NDRE2 (a normalised difference of near-infrared and the 740 nm red-edge band), the band-difference indices VI2 and VI3, the visible-band index VDVI, the fractional-cover index VCI and EVI2 in the form Sharma et al. published, raised macro F1 from 0.821 to 0.890 under temporal transfer and from 0.823 to 0.892 under spatial transfer (Section 5.1). The nine-index model passed an independent review before adoption and is the classifier reported in this paper; the national map is being regenerated with it, and map-derived numbers marked XXX await that run. A crop map intended for repeated multi-season use must generalise across time (seasons the model was not trained on) and across space (paddocks and regions it was not trained on), so the classifier was evaluated under two held-out protocols rather than a single train/test split: a temporal-transfer split (training on trials sown 2022 or earlier, testing on 543 fixed trials sown 2023-2024) and a spatial-transfer split (5-fold `GroupKFold` cross-validation grouped by trial site, scored on the same fixed 543-trial test set). Using the same fixed test set for both splits ensures the two numbers differ because of the question asked (transfer across time versus transfer to new locations) and not because of which rows are scorable under each protocol. An earlier comparison scored each arm only on the rows its own label-cleaning step retained, which produced a spuriously large apparent gain from label review alone (Section 5.1).

## 4.4 Presence gating

Because the classifier is trained only on trial points known a priori to be one of the three crop groups, it has no mechanism to recognise a segmented polygon that is not cropped at all (pasture, native vegetation, urban land or any other land use that passes the geometric filter). A presence gate is therefore applied ahead of classification to decide whether a segmented, geometrically plausible polygon is classified at all, or is instead retained with an explicit abstain reason.

The deployed presence gate uses NDVI seasonal amplitude (the difference between the 90th- and 10th-percentile NDVI values across the growing season) with a threshold of 0.35, fitted by presence-only optimisation against 3,439 NVT trial paddocks. These are the only population known to be cropped; no comparable population of land known not to be cropped was available to fit a presence/absence classifier against (Section 6.4).

A phenology-shape presence gate, which requires both a green-up rise and a post-harvest senescence drop in the seasonal NDVI curve, was tested as a stricter alternative to amplitude alone, in two variants: an oracle version anchored to each trial's recorded sowing and harvest dates, and a deployable version anchored to the detected seasonal NDVI peak, since sowing and harvest dates are not available at inference time outside the trial network. Both variants were evaluated for held-out presence recall against the same fixed test population as the amplitude gate, and then for their effect on the regional (100 km Riverina) area ratio against ABS sown-area statistics across all nine regional seasons (Section 5.4). Presence recall alone cannot show whether a stricter gate improves the area over-call, which is why the second test was needed.

## 4.5 Yield estimation

A `HistGradientBoostingRegressor` was trained on the 51 features from the three original indices (Section 4.3) to predict cereal yield (wheat, barley and oat pooled to match the classifier's cereal group) for classified cereal polygons. canola yield is not provided: an optical-only model's coefficient of determination (0.27) was below a year-and-state-mean baseline (0.29), so the estimate would be worse than guessing the year and region (Section 7, Limitation 5). NVT trial yields are agronomic-trial yields and differ systematically from commercial-paddock yields, so the cereal yield model's raw output was calibrated to ABS state-level yield statistics with a single national multiplicative factor (XXX), fitted on one year of ABS data and checked against two further held-out years. Both the raw (NVT-trial-equivalent) and the ABS-calibrated yield columns are provided on every classified cereal polygon, so the size and direction of the calibration are visible to a downstream user.

## 4.6 Validation protocol

The national map is validated against ABS sown-area statistics aggregated to the SA2 level, restricted to the subset of SA2s where the mapped tile footprint covers at least 50% of the SA2's area. This threshold turns the comparison from a spatial sample of an SA2's crop mix, which spatial clustering of crops can bias, into something closer to a census of it. Two comparisons are made: a composition comparison (does the map's crop-type share, for example the fraction of mapped crop area that is canola, match the ABS share) and, for the well-covered SA2s where the mapped footprint's absolute area is meaningful, an area-ratio comparison (does the map call more or less land crop-present than ABS records as sown). The distinction lets Section 5.2 separate a presence-detection failure (an area-ratio problem) from a classification failure (a composition problem). An Olofsson-style (Olofsson et al., 2014) stratified probability-sample area estimate with confidence intervals was not attempted, because no probability sample of recorded crop-species labels exists for Australia at the density it would require (Section 2.4; Section 7, Limitation 8).

A separate diagnostic compared each polygon's argmax-predicted class against its mean predicted-probability class, to test whether the legume over-prediction (Section 5.3) could be a decision-rule artefact (systematic near-ties broken one way by argmax) rather than a classification error. The two agree (Section 5.3).

Independently of the ABS comparison, the national map was compared at the pixel level against two products with no connection to this project's training or validation: WorldCereal 2021 v100 (Van Tricht et al., 2023) and the NLUM v7 250 m per-commodity probability surfaces (2020-21). Because WorldCereal has no canola or legume class, this comparison is restricted to (a) crop presence, checked against WorldCereal's `temporarycrops` layer, and (b) the cereal class, checked against its `wintercereals` layer. WorldCereal's `springcereals` layer was confirmed to have zero coverage over the Australian bounding box, consistent with the Australian cereal season falling under its `wintercereals` calendar. NLUM provides a per-commodity probability surface for all three target groups (oilseed, cereal and legume, each taking the maximum of the winter and summer variants), plus a grazing-probability layer, which was used to test whether abstained polygons fall preferentially on land with high grazing probability. NLUM's commodity layers are not on comparable scales (the cereal layer runs higher everywhere than the oilseed or legume layers), so comparisons across commodities use an enrichment ratio rather than raw probabilities: the median commodity probability at points of a given predicted class divided by the median at abstained points, within the same layer. Both comparisons were run on a stratified random sample of 250,000 of the XXX national paddock centroids (XXX%). A sample is adequate because these comparisons measure proportions and agreement rates, whereas the ABS area-ratio comparison measures area totals and needs a census-like footprint.

## 4.7 Multi-year regional generalisation check

The same pipeline (segmentation through classification and presence gating) was re-run across nine seasons (2017-2025) over the 100 km Riverina block, for two purposes. The first is a geometric check of polygon stability across years, independent of any spectral classification, since a real paddock's boundary should be roughly stable from year to year (median IoU XXX, with each polygon found in a median of XXX of 9 years). The second is a year-by-year check of classified share and mean NDVI amplitude, to identify seasons where the pipeline behaves differently (Section 5.6). The national multi-year run had not completed at the time of this draft [PENDING: national 2017-2025 run, E8]. All multi-year results in this paper are from the 100 km regional extent.

---

# 5. Results

## 5.1 Classifier accuracy

The adopted nine-index classifier reached macro F1 0.890 under temporal transfer (training on trials sown 2022 or earlier, testing on 543 fixed trials sown 2023-2024) and 0.892 under spatial transfer (5-fold `GroupKFold` on trial site, scored on the same 543 fixed test trials). Table 2 reports per-class precision and recall for both splits and Fig. 3 the confusion matrices [XXX: Fig. 3 shows the three-index model; regenerate for the adopted classifier]. canola was detected at 89.0% recall at a 5% false-positive rate (average precision 0.935, ROC AUC 0.962), a stricter operating-point metric than the standard-decision precision and recall in Table 2. Per-class F1 under temporal transfer was 0.96 (cereal), 0.89 (canola) and 0.83 (legume). legume remains the weakest class in both splits (precision 0.77 temporal, 0.79 spatial), now mostly because canola paddocks are misclassified as legume (19 of 155 true canola paddocks under temporal transfer, 16 of 155 under spatial transfer); cereal-to-legume confusion is 10 and 8 of 279.

**Table 2.** Classifier accuracy by class and transfer split (adopted nine-index classifier, reviewed-and-cleaned labels, 543 fixed test trials).

| Split (macro F1) | Class | Precision | Recall | F1 | n |
|---|---|---|---|---|---|
| Temporal (0.890) | canola | 0.93 | 0.85 | 0.89 | 155 |
| | cereal | 0.96 | 0.95 | 0.96 | 279 |
| | legume | 0.77 | 0.89 | 0.83 | 109 |
| Spatial (0.892) | canola | 0.91 | 0.88 | 0.89 | 155 |
| | cereal | 0.97 | 0.96 | 0.96 | 279 |
| | legume | 0.79 | 0.85 | 0.82 | 109 |

Adding the six Sharma et al. (2026) band-derived indices to the three original indices (Section 4.3) raised macro F1 from 0.821 to 0.890 (temporal) and from 0.823 to 0.892 (spatial). The gain is concentrated in legume, whose F1 rose from 0.69 in both splits to 0.83 and 0.82 as recall rose from 73% and 70% to 89% and 85%, while canola detection at a 5% false-positive rate was unchanged at 89.0% (average precision 0.944 to 0.935, ROC AUC 0.965 to 0.962). The remaining ablations were run with the three-index feature set. Hand-reviewing ambiguous trial-to-polygon matches (Section 4.2) improved macro F1 by 0.019 over a size-matched unreviewed control arm (mean 0.802, standard deviation 0.010), about two control standard deviations. An earlier comparison that scored the reviewed and unreviewed arms on different test rows had put the gain at 0.107. Fine-tuned Presto embeddings scored macro F1 0.775 alone and 0.824 combined with the three indices, indistinguishable from the 0.821 of the indices alone (Section 6.3).

## 5.2 National map and ABS validation: composition versus area

The completed 2024 national map contains XXX segmented polygons across XXX tiles (Table 1; Fig. 4 [XXX: regenerate from the re-run]). Of these, XXX% of polygons (XXX% of total area) carry a classification. The remainder carry one of four abstain reasons (`area_below_min`, `no_crop_signal`, `unsegmented_blob`, `too_few_observations`). Across the XXX SA2s where the mapped footprint covers at least 50% of the SA2 (Section 4.6), mapped canola composition (its share of total mapped crop area) against the ABS canola share gives r = XXX and a median absolute error of XXX percentage points; the reference floor is the 6.8% median disagreement between ABS and ABARES (Section 3.3; Fig. 5a [XXX: regenerate]; Table 3).

The map's absolute area over-calls crop-present land relative to ABS by XXXx nationally and by XXXx in the 100 km regional test. By class (Fig. 5b), the over-called share splits as cereal +XXX percentage points, legume +XXX points and canola XXX points. Once the over-call is divided out, by comparing the mapped canola share against the diluted share a perfect classifier would report given the measured over-call, canola composition is XXX% mapped versus XXX% expected. This is the central result of the paper [XXX: held on the first national map; confirm on the re-run]: the map's main disagreement with official statistics is a presence-detection problem (too much land called crop-present) rather than a classification problem, and it reproduces at national and regional scale with the same class signature (Section 6.1).

**Table 3.** ABS validation summary, national scale, XXX SA2s. `diluted` is the crop-share ABS would imply if the area over-call were spread proportionally across classes; `absorbed` is the difference between that and the actual mapped share, the excess this class's mapped area carries.

| Class | ABS share | Diluted share | Mapped share | Absorbed (points) |
|---|---|---|---|---|
| canola | XXX | XXX | XXX | XXX |
| cereal | XXX | XXX | XXX | XXX |
| legume | XXX | XXX | XXX | XXX |

Canola composition: r = XXX, median absolute error XXX percentage points (n = XXX). Area over-call: XXXx national, XXXx regional (100 km). ABS/ABARES mutual disagreement (the accuracy floor, Section 3.3): median 6.8%.

## 5.3 Legume classification error

A separate classification error sits on top of the presence problem: legume is mapped at XXX% of classified area nationally against an ABS share of XXX%. The argmax and mean-predicted-probability classes agree (Section 4.6), which rules out a decision-rule artefact such as a systematic tie-break. The mechanism remains open (Section 6.7; Section 7, Limitation 2). The confusion matrices in Section 5.1 (canola and cereal paddocks predicted as legume more often than the reverse) are consistent in direction with the over-prediction but do not account for its size.

## 5.4 Presence-gate experiment: a rejected fix

The phenology-shape presence gate (Section 4.4) was tested against all nine seasons of the 100 km regional dataset. On its target metric it succeeded: on the earlier 3 km regional run, the area ratio against ABS fell from 1.59 to 1.00. The cost is visible only when presence recall is examined per crop rather than pooled. With both the amplitude gate and the shape gate applied, presence recall fell to 78.3% for canola against 91.4% for cereal and 87.2% for legume (Fig. 6; Table 4), whereas canola recall under the amplitude gate alone was 94.5%, comparable to the other two crops. Canola is the class the ABS comparison checks most directly (Section 5.2) and is detected at 89.0% recall at a 5% false-positive rate (Section 5.1). A gate that fixes the area ratio by removing real canola paddocks trades a known problem, area over-call, for which the map provides a workaround (Section 6.4), for a worse one, dropping real canola detections without a record. We therefore rejected the phenology-shape gate and deployed the amplitude-only design (Section 6.2). A two-pass variant that exempts canola from the shape gate restores canola recall to 94.5% at no measured cost to cereal or legume recall, but has not been checked against the ABS area ratio (Section 7.2, item 4).

**Table 4.** Presence recall by crop for three tested phenology-shape gate configurations, each stacked with the amplitude gate (earlier 3 km run of the 100 km regional dataset). None of the three is the deployed design, which applies the amplitude gate alone (94.5% canola recall on this population; Section 4.4).

| Gate configuration | Pooled recall | Canola | Cereal | Legume |
|---|---|---|---|---|
| Phenology-shape, baseline threshold | 87.0% | 78.3% | 91.4% | 87.2% |
| Phenology-shape, loosened senescence (−3 pts) | 89.6% | 87.6% | 91.6% | 87.6% |
| Phenology-shape, two-pass (canola exempt) | 91.3% | 94.5% | 91.4% | 87.2% |

## 5.5 Independent spatial comparison: WorldCereal and NLUM

The ABS validation (Section 5.2) and the legume check (Section 5.3) both rely on official statistics, so we also compared the national map at the pixel level against two products with no connection to this project's pipeline, WorldCereal 2021 v100 and the NLUM v7 250 m per-commodity probability surfaces, on a stratified sample of 250,000 national paddock centroids (Section 4.6). Both products predate this map by three years (2021 versus 2024).

Against WorldCereal's `temporarycrops` layer, our classified-versus-abstained presence call agrees at XXX% overall, and the agreement is symmetric: XXX% of our abstained points are also called no-crop by WorldCereal, and XXX% of our classified points are also called crop. Against WorldCereal's `wintercereals` layer, agreement on the cereal class is weaker: XXX% of the points our map calls cereal are `wintercereals`-positive in WorldCereal (n = XXX). WorldCereal is an independent product rather than ground truth, so this does not establish which product is correct.

NLUM's per-commodity surfaces cover all three target groups. Median NLUM oilseed probability at our canola-classified points is XXX times the median at our abstained points, the largest ratio in its column, and median legume probability at our legume-classified points is XXX times the abstained-point median, again the largest in its column. NLUM's grazing-probability layer supports the presence-gate reading from an unrelated source: median grazing probability is XXX% at our abstained points against XXX% at our classified points. Abstained land is therefore concentrated on land NLUM rates as probable grazing country, rather than being a uniform sample of everything the classifier could not decide (Section 6.4).

## 5.6 Multi-year regional evidence

Across the nine-year (2017-2025), 100 km regional re-run, classified share ranged from XXX% (2018) and XXX% (2017) up to XXX% (2025). Mean NDVI amplitude was lowest in 2018 (XXX) and 2017 (XXX), against XXX in 2024-2025 (Fig. 7a [XXX: regenerate]). We attribute the two weak years to the mid-2017 start of Sentinel-2B operations, which reduced revisit frequency in the earliest seasons, and to the 2018 drought respectively (Section 6.6). Polygon geometric stability across the same nine years, independent of any spectral classification, peaked in the XXX ha range, where most real paddocks sit, and fell at both extremes. This supports the area and compactness mask on geometric grounds alone (Section 4.1). This regional evidence does not establish the same behaviour at national scale. Figure 7's national panel and the national multi-year totals are left blank pending the national multi-year run [PENDING: national 2017-2025 run, E8].

## 5.7 Cereal yield

The cereal yield model reached a spatial-transfer root-mean-square error of 1.21 t/ha (30.4% of the 3.97 t/ha median observed yield). The ABS calibration factor (XXX, fitted on one year of ABS data) checked to within XXX% to XXX% of ABS-implied yield on two held-out years (Fig. 8 [XXX: regenerate]; Table 5). Both raw (NVT-trial-equivalent) and ABS-calibrated yield columns are provided on every classified cereal polygon (Section 4.5).

**Table 5.** cereal yield model performance (pooled wheat/barley/oat, three-index satellite features), before ABS calibration.

| Split | Arm | n | R² | RMSE (t/ha) |
|---|---|---|---|---|
| Temporal (train ≤2022, test 2023-24) | Year+state baseline | 279 | −0.643 | 2.111 |
| | Satellite features | 279 | 0.471 | 1.197 |
| | Satellite + year/state | 279 | 0.486 | 1.181 |
| Spatial (5-fold GroupKFold on site) | Year+state baseline | 1,119 | 0.294 | 1.473 |
| | Satellite features | 1,119 | 0.526 | 1.207 |
| | Satellite + year/state | 1,119 | 0.577 | 1.140 |

ABS calibration factor: XXX (fitted on one year), checked XXX% to XXX% against ABS-implied yield on two held-out years. Canola yield is not provided: an optical-only model's coefficient of determination (0.27) did not exceed a year-and-state-mean baseline (0.29) (Section 7, Limitation 5).

[PENDING: E8] National multi-year (2017-2025) polygon and area totals by year (Table 6); national year-on-year canola, cereal and legume share trends; any claim that the 2024 national results generalise across seasons.

---

# 6. Discussion

## 6.1 A presence-detection failure rather than a classification failure

The central result of this paper is that the map's main disagreement with ABS statistics is a presence-detection problem rather than a species-classification problem. Three lines of evidence support this reading. First, canola composition matches ABS closely (r = XXX) while total mapped area over-calls ABS by XXXx, and dividing out the over-call recovers near-exact canola-share agreement (Section 5.2). A presence problem produces this pattern (too much land called crop-present, with the crop mix among that land roughly right); a classification problem would produce the right amount of land called crop with the wrong species assigned to some of it. Second, the same over-call magnitude and the same class concentration (cereal and legume rather than canola) reproduce at national and 100 km regional scale, which an artefact of one region or one year would not do. Third, the WorldCereal and NLUM comparisons (Section 5.5), which share no data with the ABS validation, point the same way: presence agreement against WorldCereal is symmetric and moderate (XXX% in both directions) rather than poor in one direction, and NLUM's grazing-probability layer shows abstained land is more grazing-like than classified land (median grazing probability XXX% against XXX%). Non-cropped land, rather than crops the classifier failed to recognise, is therefore the main source of the abstained population.

## 6.2 The phenology-gate result as a general caution

The phenology-shape presence gate (Section 5.4) is on paper the more principled fix: it requires the shape a real growing season should produce (green-up, then senescence) rather than treating any large seasonal amplitude as evidence of cropping. It also worked on its own target metric. On the earlier regional run the area ratio fell from 1.59 to 1.00, which removes the area-inflation problem this paper otherwise reports as its most consequential limitation. We rejected it because the metric it was evaluated against first, area ratio, was not the metric that matters most for the map's usefulness, per-crop presence recall, and checking recall per crop showed that the fix worked by removing real canola paddocks, the crop the ABS comparison checks most directly. This is a caution for presence-gate design in crop mapping generally. A more principled fix that succeeds on its headline metric can still be the wrong choice to deploy if a pooled metric conceals which sub-population pays for the improvement. A stricter gate should be evaluated on the metric that matters for the map's use, broken out by the sub-populations a pooled metric hides.

## 6.3 Foundation-model embeddings did not help here

The Presto result (Sections 2.1 and 5.1) runs against a common framing in the crop-mapping literature that foundation-model embeddings outperform spectral features. At this label volume (2,194 recorded trials) and class granularity (three groups) they did not: Presto alone scored macro F1 0.775 against 0.821 for the three-index feature set that preceded the adopted classifier, and combining the two gave 0.824. This is not evidence that Presto's architecture is unsuited to crop mapping. Three of its nine input channel groups (Sentinel-1 radar, ERA5 climate and SRTM terrain) were unavailable here and were passed as masked, a testable explanation for the gap that our data did not allow us to close. The result is a data point against unconditional claims that foundation models win, conditioned on label volume, class granularity and input-channel completeness.

## 6.4 The abstain-reason and confidence fields as the map's answer to area inflation

Every polygon in the national map carries either a predicted class or one of four abstain reasons, plus its NDVI amplitude and classification confidence, so a user who needs area-accurate rather than composition-accurate output can filter to a tighter view of the map without waiting for a methodological fix. No population of land known not to be cropped was available to train an explicit non-crop class (Section 4.4), so instead of forcing a binary crop/non-crop decision the available labels could not support, the map reports its uncertainty on every polygon.

## 6.5 A covariate's value depends on the task

Two further findings add a second general caution alongside the phenology-gate result (Section 6.2). Sentinel-1 was re-tested against the adopted nine-index classifier (Section 4.3) rather than against the three-index baseline it was first measured on. Against this baseline, Sentinel-1 lowers classifier accuracy by 0.023 macro F1 (temporal) and 0.018 (spatial), concentrated on the legume class (F1 0.82 to 0.77), the class Sentinel-1 originally appeared to help. Permutation importance explains the reversal: the Sharma et al. red-edge index already resolves most of the legume/cereal confusion Sentinel-1 previously corrected (importance +0.134 without Sentinel-1), and once that confusion is resolved Sentinel-1's extra columns have little signal left and dilute the model on a training set that did not grow to match them (importance +0.018, with every other feature family negative). The same evaluation against the deployed cereal yield model gives the opposite result: Sentinel-1 adds 0.092 R² on the yield model's operational bar (satellite plus year/state, temporal transfer), its largest gain in any arm tested. The reverse also holds: the band-derived indices that improve classification lower canola yield prediction when substituted for the yield model's three indices, with temporal R² falling from 0.206 to 0.012. Table 7 summarises all three results.

| Task | Covariate tested | Without | With | Change |
|---|---|---|---|---|
| Classification, macro F1 (temporal) | Sentinel-1, added to the adopted classifier | 0.887 | 0.864 | −0.023 |
| Classification, macro F1 (spatial) | Sentinel-1, added to the adopted classifier | 0.886 | 0.868 | −0.018 |
| cereal yield, R² (temporal, satellite+year/state) | Sentinel-1, added to the deployed yield model | 0.419 | 0.511 | +0.092 |
| cereal yield, R² (spatial, satellite+year/state) | Sentinel-1, added to the deployed yield model | 0.569 | 0.591 | +0.022 |
| canola yield, R² (temporal, satellite+year/state) | Sharma et al. (2026) indices, substituted for the yield model's three indices | 0.206 | 0.012 | −0.194 |

**Table 7.** Marginal value of Sentinel-1 and the Sharma et al. (2026) band-derived indices, by downstream task. The same covariate that regresses classification helps cereal yield; the same substitution that helps classification regresses canola yield. The classification rows' "without" baseline (0.887/0.886) is the adopted classifier scored on the row-matched subset with Sentinel-1 coverage (2,133 trials, 497 of 543 test rows), so it differs by 0.003-0.006 from the same model's full-population score in Section 5.1 (0.890/0.892, 2,194 trials).

A covariate validated for one task in a shared feature pipeline should not be assumed useful for every task that pipeline feeds, even within one project and one set of satellite inputs. Sentinel-1 backscatter is sensitive to canopy structure and biomass, which a yield regressor needs and a phenology classifier, once its main residual confusion is resolved, does not. For this project, national Sentinel-1 acquisition is now justified as a yield lever rather than a classifier lever (Section 7.2).

## 6.6 Generalisation across seasons: regional evidence, national open question

The nine-year 100 km regional test identifies two weaker years, 2017 and 2018, with lower classified share and lower mean NDVI amplitude than the other seven seasons, attributable to the mid-2017 start of Sentinel-2B operations and the 2018 drought respectively. The pipeline's behaviour is therefore not uniform across seasons, and a national multi-year run should be expected to show season-to-season variation. We do not extrapolate the regional pattern to a national claim. A 100 km block is one climatic and cropping context among several across the continent, and whether the same two mechanisms dominate nationally, or other regions have different weak seasons for different reasons, is the question the national multi-year run (Section 3.2; Section 7) is designed to answer. The 2024 national results describe one season's performance.

## 6.7 The legume classification error remains open

Legume classification carries its own unresolved error, separate from the presence problem: the national map assigns XXX% of classified area to legume against an ABS share of XXX% (Section 5.3). This is not an artefact of the decision rule. Argmax and mean predicted probability give the same share (XXX% and XXX%; Section 4.6), so the classifier favours legume at this rate rather than reporting it inconsistently. The confusion matrices point the same way but do not account for the size of the gap: canola and cereal paddocks are misclassified as legume more often than the reverse (19 of 155 true canola and 10 of 279 true cereal paddocks under temporal transfer, against 6 and 6 legume paddocks the other way; Section 5.1). This is a species-level confusion (which crop, given that something is present) rather than a presence-level one, and the largest unresolved classification error in the map. We leave the mechanism open (Section 7, Limitation 2).

---

# 7. Limitations and Future Work

## 7.1 Limitations, in order of severity

1. Area over-call (XXXx), reproduced nationally and regionally on the first national map [XXX: confirm on the re-run], is the map's most consequential operating characteristic (Sections 5.2 and 6.1). It is mitigated but not eliminated by providing `ndvi_amp` and `abstain_reason` on every polygon (Section 6.4), which lets a downstream user filter to a tighter, more area-accurate subset when that matters more than completeness.
2. Legume misclassification (XXX% mapped against XXX% ABS share) has no established mechanism. The argmax-versus-mean-probability check rules out a decision-rule artefact (Section 5.3), and Section 6.7 discusses it as the largest unresolved classification error in the map.
3. `unsegmented_blob`, SAM's largest segmentation failure mode, accounts for XXX polygons nationally. A size-aware second segmentation pass to split these has not been attempted (Section 4.1).
4. Single-season national coverage. The completed national map covers 2024 only; the national multi-year run (2017-2023, 2025) had not completed at the time of this draft [PENDING: E8]. This is the paper's largest scope gap, and the reason the multi-year results in Section 5.6 and Figure 7 are regional.
5. No canola yield, because it needs Sentinel-1 and Sentinel-1 is not in the deployed pipeline. An optical-only model's spatial-transfer coefficient of determination (0.271) does not exceed a year-and-state-mean baseline (0.290), and a yield estimate that underperforms guessing the season and region is worse than none. Adding Sentinel-1 raises the same spatial-transfer R² to 0.371 on the current row-matched population (Section 6.5), which agrees in direction and size with the original unrepeated test. Canola yield is therefore gated on the same national Sentinel-1 acquisition question as the cereal yield extension (Section 7.2, item 6).
6. Sentinel-1's value depends on the task. Re-tested against the adopted classifier (Sections 4.3 and 6.5) rather than the retired baseline it was first measured on, Sentinel-1 lowers classification accuracy (−0.023 macro F1 temporal, concentrated on legume) but improves the deployed cereal yield model (+0.092 R² on its operational transfer bar; Table 7). No Sentinel-1 product is used at national scale for either task.
7. Three classes rather than the species-level roster originally scoped. A nine-species classifier reached macro F1 0.38 at the available recorded label volume, a finding about the label volume that species classification from recorded labels requires (Sections 1 and 4.2).
8. The ABS validation reference is itself uncertain, and is not an Olofsson-style probability-sample area estimate. ABS and ABARES disagree by a median 6.8% on national sown area, and no map-versus-ABS comparison in this paper should be read as more precise than that floor. No probability sample of recorded crop-species labels exists for Australia at the density an Olofsson-style (Olofsson et al., 2014) stratified area estimate with confidence intervals would require. This paper's validation is therefore a composition and area comparison against an independent statistic rather than a stratified accuracy assessment (Sections 2.4 and 4.6).
9. The WorldCereal and NLUM spatial comparisons (Section 5.5) carry a three-year reference-year mismatch (2021 versus this map's 2024). For WorldCereal, they cover only the presence and cereal classes, since canola and legume have no counterpart in WorldCereal's class scheme. Both comparisons were run on a stratified sample rather than the full polygon population, which is adequate for the proportions and agreement rates reported but not for an area-total comparison.

## 7.2 Future work, in priority order

1. Complete the national 2017-2025 multi-year run (E8), the direct next step and the one this paper's multi-year claims are written to accommodate. The run followed a discussion of validation methodology and the multi-year regional approach with project colleagues, informed by an earlier version of this manuscript. It is in progress at the time of this draft. No season is final, because the seasons already processed are being re-run with the adopted classifier (Section 4.3).
2. Investigate the legume over-prediction mechanism, the largest unexplained classification error in the map (Limitation 2).
3. A size-aware second SAM segmentation pass targeting the `unsegmented_blob` failure mode (Limitation 3).
4. Validate two-pass presence gating (exempting canola from the phenology-shape gate) against the ABS area ratio. The variant restores canola recall to 94.5% at no measured cost to cereal or legume recall (Section 5.4), but has not been checked against the area-ratio metric that decided the original gate's rejection.
5. Extend the WorldCereal/NLUM spatial comparison from a 250,000-point sample to the full polygon population, and to additional independent products, once the reference-year mismatch can be narrowed (for example against a WorldCereal release closer to 2024) or a sensitivity check on reference year is added.
6. Extend Sentinel-1 acquisition to national scale for the yield models rather than the classifier (Section 6.5). Cereal yield gains 0.092 R² on the operational transfer bar, and canola yield cannot be provided without it (Limitation 5): Sentinel-1 is the difference between a canola yield model below the year-and-state baseline (R² 0.271, spatial) and one above it (R² 0.371). Both are gated on two unresolved items: whether the yield gain holds on ordinary commercial paddocks rather than the National Variety Trial paddocks it was measured on (no yield-labelled holdout on ordinary paddock geometry exists), and a revisit-density covariate for the Sentinel-1B acquisition gap, which has not been implemented.

---

# 8. Conclusion

We have presented a national, field-level, three-class crop-species map of Australia at 10 m resolution, built end-to-end from open Sentinel-2 imagery and 2,194 recorded GRDC National Variety Trial records. To our knowledge, this is the first product to combine continent-wide coverage, paddock-scale resolution and training on field-recorded sowings for this problem. The completed 2024 national map contains XXX segmented polygons, each carrying a predicted class or one of four abstain reasons, a confidence and, for cereal, a raw and an ABS-calibrated yield estimate. We validated the map against independent ABS sown-area statistics with no connection to the training pipeline. Mapped canola composition tracks the official statistic closely (r = XXX), so the classifier and segmentation pipeline are sound where they can be checked most directly.

The map's most consequential limitation is a XXXx area over-call, reproduced independently at national and regional scale and corroborated by independent spatial comparison against WorldCereal and the National Land Use Map. This is a presence-detection problem rather than a species-classification problem, and the distinction matters for how the map is used as well as for diagnosis. A more principled fix, a phenology-shape presence gate, worked on its own target metric but harmed the map's best-classified crop, so we rejected it. Evaluating a stricter presence criterion on a single pooled metric can conceal which sub-population pays its cost, and this is a caution for presence-gate design in crop mapping generally.

Two threads remain open. First, the national multi-year extension of this pipeline (2017-2023, 2025) is in progress at the time of this draft, following a discussion of validation methodology and the multi-year regional approach with project colleagues that this manuscript helped inform. The multi-year results in this paper are regional (100 km, nine seasons) until that extension completes. Second, the legume over-prediction (XXX% mapped against XXX% ABS) has no established mechanism and is the largest unresolved classification error in the map.

---

# Data and Code Availability

The pipeline code (segmentation, labelling, classification, presence gating, yield calibration and validation scripts) contains no site-level records and can be released alongside this manuscript.

The GRDC/National Variety Trial ground-truth data used for training and validation (trial coordinates, crop identities, sowing and harvest dates and yields) cannot be released, in accordance with the data-use agreement covering this dataset. The restriction applies to the raw trial records only, not to the resulting map or the aggregate statistics reported in this paper.

The classified-only national output map is releasable. The full national output, which also carries per-polygon provenance fields used during development, will be checked for residual site-level linkage before release; none is expected.

Model artefacts (the crop classifier and the cereal yield model) contain no site-level records and are releasable. The phenology-gate model evaluated in Section 5.4 and rejected is retained for reproducibility of that experiment but is not part of the deployed pipeline.

ABS and ABARES reference statistics used for validation are already public and require no release action.

This manuscript will be provided to the Grains Research and Development Corporation (GRDC) for verification before submission, consistent with the data-use agreement covering the trial network.

# CRediT Author Statement

[PLACEHOLDER - author contributions and role assignments to be supplied by the authors.]

# Declaration of Competing Interests

[PLACEHOLDER - to be completed by the authors.]

# Acknowledgements

[PLACEHOLDER - to be completed by the authors. Should acknowledge the Grains Research and Development Corporation and the National Variety Trials network for the underlying trial data, and the National Computational Infrastructure (NCI) for compute access via Digital Earth Australia.]

---

# References

Al-Shammari, D., Fuentes, I., Whelan, B.M., Wang, C., Filippi, P., Bishop, T.F.A. (2024). Combining Sentinel 1, Sentinel 2 and MODIS data for major winter crop type classification over the Murray Darling Basin in Australia. *Remote Sensing Applications: Society and Environment*, 34, 101200. doi:10.1016/j.rsase.2024.101200

Ashourloo, D., Shahrabi, H.S., Azadbakht, M., Aghighi, H., Nematollahi, H., Alimohammadi, A., Matkan, A.A. (2019). Automatic canola mapping using time series of Sentinel-2 images. *ISPRS Journal of Photogrammetry and Remote Sensing*, 156, 63-76.

Brown, C.F., et al. (2025). AlphaEarth Foundations: an embedding field model for accurate and efficient global mapping from sparse label data. arXiv:2507.22291.

Karra, K., Kontgis, C., et al. (2021). Global land use / land cover with Sentinel-2 and deep learning. In *2021 IEEE International Geoscience and Remote Sensing Symposium (IGARSS)*.

Kerner, H., et al. (2024). Fields of The World: a machine learning benchmark dataset for global agricultural field boundary segmentation. arXiv:2409.16252.

Kirillov, A., Mintun, E., Ravi, N., Mao, H., Rolland, C., Gustafson, L., Xiao, T., Whitehead, S., Berg, A.C., Lo, W.-Y., Dollár, P., Girshick, R. (2023). Segment Anything. In *2023 IEEE/CVF International Conference on Computer Vision (ICCV)*, 3992-4003.

Lawes, R., Hochman, Z., Jakku, E., Butler, R., Chai, J., Waldner, F., Donohue, R. (2022). Graincast: monitoring crop production across the Australian grainbelt. *Crop & Pasture Science*. doi:10.1071/CP21386

Newman, R., Furbank, R.T. (2021). Explainable machine learning models of major crop traits from satellite-monitored continent-wide field trial data. *Nature Plants*, 7, 1354-1363.

Olofsson, P., Foody, G.M., Herold, M., Stehman, S.V., Woodcock, C.E., Wulder, M.A. (2014). Good practices for estimating area and assessing accuracy of land change. *Remote Sensing of Environment*, 148, 42-57. doi:10.1016/j.rse.2014.02.015

Sharma, S., Eslick, H., Pires, R., Singh, B., Tareque, H. (2026). Temporal sensitivity of in-season crop classification: an explainable multi-year Sentinel-2 analysis in Western Australia. *Remote Sensing*, 18(10), 1653. doi:10.3390/rs18101653

Tseng, G., Cartuyvels, R., Zvonkov, I., Purohit, M., Rolnick, D., Kerner, H. (2024). Lightweight, pre-trained transformers for remote sensing timeseries. arXiv:2304.14065.

Van Tricht, K., et al. (2023). WorldCereal: a dynamic open-source system for global-scale, seasonal, and reproducible crop and irrigation mapping. *Earth System Science Data*, 15, 5491-5515. doi:10.5194/essd-15-5491-2023

Note on completeness. This list resolves every in-text citation used in the manuscript, verified against the source. Entries marked "et al." have a confirmed lead author and venue but an incompletely resolved full author list; a reference-manager pass (DOI resolution, full author lists, publisher-exact formatting per RSE house style) is recommended before submission. One correction made during this pass: the Newman and Furbank citation was previously recorded elsewhere in project files as *Scientific Data*; it is *Nature Plants* (verified via publisher and PubMed listing).
