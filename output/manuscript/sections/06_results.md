---
section: results
mode: partial
word_target: 1650
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
