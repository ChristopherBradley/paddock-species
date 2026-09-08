---
section: results
mode: partial
word_target: 1650
---

# 5. Results

## 5.1 Classifier accuracy

The reviewed-and-cleaned label arm reached macro F1 0.821 under temporal transfer (training on trials sown 2022 or earlier, testing on 543 fixed trials sown 2023-2024) and 0.823 under spatial transfer (5-fold `GroupKFold` on trial site, scored on the same 543 fixed test trials); Table 2 and Fig. 3 report both confusion matrices and per-class precision/recall. Canola was detected at 89.0% recall at a 5% false-positive rate (average precision 0.944, ROC AUC 0.965) — a stricter operating-point metric distinct from the standard-decision precision/recall in Table 2. Per-class F1 under temporal transfer was 0.90 (Cereal), 0.88 (Canola), and 0.69 (Legume); Legume is the floor in both splits (recall 73% temporal, 70% spatial), driven predominantly by Cereal paddocks being misclassified as Legume (23 of 279 true Cereal paddocks under temporal transfer, 22 of 279 under spatial transfer) rather than the reverse.

**Table 2.** Classifier accuracy by class and transfer split (reviewed-and-cleaned arm, 543 fixed test trials).

| Split (macro F1) | Class | Precision | Recall | F1 | n |
|---|---|---|---|---|---|
| Temporal (0.821) | Canola | 0.94 | 0.83 | 0.88 | 155 |
| | Cereal | 0.89 | 0.90 | 0.90 | 279 |
| | Legume | 0.65 | 0.73 | 0.69 | 109 |
| Spatial (0.823) | Canola | 0.91 | 0.86 | 0.88 | 155 |
| | Cereal | 0.89 | 0.91 | 0.90 | 279 |
| | Legume | 0.68 | 0.70 | 0.69 | 109 | Hand-reviewing ambiguous trial-to-polygon matches (Section 4.2) improved macro F1 by +0.019 over a size-matched, unreviewed control arm (mean 0.802, standard deviation 0.010) — a modest but real gain, roughly two control standard deviations, not the substantially larger apparent gain (+0.107) an earlier, methodologically confounded comparison had produced by scoring the reviewed and unreviewed arms on different, unequally clean test rows. Fine-tuned Presto embeddings scored macro F1 0.775 alone, and 0.824 (statistically indistinguishable from 0.821) combined with the spectral-index features — a negative result for the foundation-model alternative at this label volume, discussed further in Section 6.3.

## 5.2 National map and ABS validation: composition versus area

The completed 2024 national map contains 1,346,582 segmented polygons across 99,465 tiles (Table 1; Fig. 4). Of these, 48.4% of polygons (34.4% of total area) carry a classification; the remainder carry one of four explicit abstain reasons (`area_below_min`, `no_crop_signal`, `unsegmented_blob`, `too_few_observations`) rather than being silently dropped. Validated against ABS sown-area statistics across the 133 SA2s where the mapped footprint covers at least 50% of the SA2 (Section 4.6), mapped canola *composition* — its share of total mapped crop area — tracks the ABS canola share closely: r = 0.82, median absolute error 5.5 percentage points, below the 6.8% median disagreement between ABS and ABARES that this paper treats as the accuracy floor for any map-versus-official-statistic comparison (Section 3.3; Fig. 5a; Table 3).

The map's absolute *area*, however, over-calls crop-present land relative to ABS by 1.47x nationally and, independently, by 1.59x in the 100 km regional test — the same mechanism reproduced at two spatial scales. Decomposing this over-call by class (Fig. 5b) shows it is concentrated almost entirely in Cereal (+23.2 percentage points of the over-called share) and Legume (+10.8 points), and is essentially absent from Canola (-0.3 points). Once the area over-call is divided out — comparing the mapped canola share against the *diluted* share a perfect classifier would report given the measured over-call, rather than against the raw ABS share directly — canola composition matches almost exactly (13.1% mapped versus a diluted expectation of 13.4%). This is the central interpretive result of the paper: the map's dominant disagreement with official statistics is a presence-detection problem (calling too much land "crop-present" in the first place), not a crop-species classification problem, and it is reproduced independently at national and regional scale with the same class signature both times (Section 6.1).

**Table 3.** ABS validation summary, national scale, 133 SA2s. `diluted` is the crop-share ABS would imply if the area over-call were spread proportionally across classes; `absorbed` is the difference between that and the actual mapped share — the excess this class's mapped area carries.

| Class | ABS share | Diluted share | Mapped share | Absorbed (points) |
|---|---|---|---|---|
| Canola | 19.7% | 13.4% | 13.1% | −0.3 |
| Cereal | 67.3% | 45.8% | 69.0% | +23.2 |
| Legume | 8.7% | 5.9% | 16.7% | +10.8 |

Canola composition: r = 0.82, median absolute error 5.5 percentage points (n = 133). Area over-call: 1.47x national, 1.59x regional (100 km). ABS/ABARES mutual disagreement (the accuracy floor, Section 3.3): median 6.8%.

## 5.3 Legume classification error

A distinct, unresolved classification error sits on top of the presence-detection problem: Legume is mapped at 18.4% of classified area nationally versus an ABS share of 8.7%. An argmax-versus-mean-predicted-probability check (Section 4.6) rules out the cheap explanation that this is a decision-rule artefact (e.g., a systematic argmax tie-break) — the two agree, so the disagreement reflects genuine classifier behaviour, not a threshold quirk. The mechanism remains open (Section 6.7, Section 7 Limitation 2); Section 5.1's confusion-matrix evidence (Cereal paddocks predicted as Legume more often than the reverse) is consistent with, but does not fully explain, the magnitude of the national over-prediction.

## 5.4 Presence-gate experiment: a rejected fix

A phenology-shape presence gate — requiring both a green-up rise and a post-harvest senescence drop, rather than seasonal amplitude alone (Section 4.4) — was tested against the full nine-year, 100 km regional dataset. On its own target metric, it succeeded: the regional area ratio against ABS fell from 1.59 to 1.00. But it did so at a real cost, visible only once presence recall is examined per crop rather than pooled: stacked presence recall (both the amplitude gate and the shape gate applied, as deployed) fell to 78.3% for Canola, against 91.4% for Cereal and 87.2% for Legume — the shape gate disproportionately rejects real canola paddocks specifically (Fig. 6; Table 4), even though canola recall under amplitude-only gating alone was 94.5%, comparable to the other two crops. Because Canola is the class whose composition already matches ABS most closely (Section 5.2) and is this dataset's most reliably classified crop (Section 5.1), a gate that fixes the area-ratio number by disproportionately removing real canola paddocks trades a well-understood problem (area over-call, for which the map already provides a documented workaround; Section 6.4) for a worse, less legible one (silently dropping real canola detections). We therefore rejected the phenology-shape gate and deployed the simpler amplitude-only design, despite the shape gate's superior performance on the area-ratio metric alone (Section 6.2). A two-pass variant that exempts Canola from the shape gate restores canola recall to 94.5% at no measured cost to Cereal or Legume recall, but has not been validated against the ABS area ratio and is reported as a future-work candidate, not a result (Section 7).

**Table 4.** Presence recall by crop for three tested phenology-shape gate configurations, each stacked with the amplitude gate (100 km regional dataset). None of these three is the design actually deployed to production, which applies the amplitude gate alone (94.5% Canola recall on this population, Section 4.4) and was retained because the phenology-shape gate's area-ratio gain came at the Canola-recall cost shown below.

| Gate configuration | Pooled recall | Canola | Cereal | Legume |
|---|---|---|---|---|
| Phenology-shape, baseline threshold | 87.0% | 78.3% | 91.4% | 87.2% |
| Phenology-shape, loosened senescence (−3 pts) | 89.6% | 87.6% | 91.6% | 87.6% |
| Phenology-shape, two-pass (Canola exempt) | 91.3% | 94.5% | 91.4% | 87.2% |

## 5.5 Independent spatial comparison: WorldCereal and NLUM

Because both the ABS validation (Section 5.2) and the Legume classification check (Section 5.3) rely on the same broad type of reference data (official area/production statistics) as each other, we additionally compared the national map spatially, at the pixel level, against two products with no connection to this project's own pipeline: WorldCereal 2021 v100 and NLUM v7 250 m per-commodity probability surfaces, on a stratified sample of 250,000 national paddock centroids (Section 4.6). Both comparisons carry a three-year reference-year mismatch (2021 versus this map's 2024) and are reported with that caveat throughout.

Against WorldCereal's `temporarycrops` layer, our classified-versus-abstained presence call agrees at 73.1% overall, and the agreement is symmetric: 73.0% of our abstained points are also called "no-crop" by WorldCereal, and 73.2% of our classified points are also called "crop." Against WorldCereal's `wintercereals` layer, agreement on the Cereal class specifically is markedly weaker — 49.6% of the points our map calls Cereal are also called `wintercereals`-positive by WorldCereal — a real disagreement, not sampling noise at this sample size (n=82,411), though WorldCereal is an independent product rather than ground truth and this disagreement does not by itself establish which product is correct.

NLUM's per-commodity probability surfaces, which unlike WorldCereal cover all three of our target groups directly, show a consistent enrichment pattern: median NLUM oilseed probability at our Canola-classified points is 6.4 times the median at our abstained points (the largest ratio in its column, correctly identifying Canola as the class most enriched for oilseed probability), and median legume probability at our Legume-classified points is 1.6 times the abstained-point median (likewise the largest ratio in its column). Independently of the classification comparison, NLUM's grazing-probability layer corroborates the presence-gate mechanism from an unrelated data source: median grazing probability is 33.8% at our abstained points versus 10.8% at our classified points, consistent with this project's earlier finding, from a retired absence-labelled grazing dataset (Section 6.4), that abstained land preferentially overlaps land NLUM independently rates as probable grazing country rather than being a uniform sample of "everything the classifier could not decide about."

## 5.6 Multi-year regional evidence

Across the nine-year (2017-2025), 100 km regional re-run, classified share ranged from 52.5% (2018) and 59.0% (2017) up to 78.5% (2025); mean NDVI amplitude was correspondingly lowest in 2018 (0.42) and 2017 (0.46) against 0.60-0.62 in 2024-2025 (Fig. 7a). We attribute the two weak years to Sentinel-2B's mid-2017 operational start (reducing revisit frequency and cloud-gap robustness in the earliest seasons) and a documented drought in 2018 respectively (Section 6.6). Polygon geometric stability across the same nine years — independent of any spectral classification — peaked in the 25-100 ha range (the range real paddocks predominantly occupy) and fell at both smaller and larger extremes, an independent, purely geometric corroboration of the area/compactness presence mask (Section 4.1). This regional evidence is suggestive of, but does not establish, similar behaviour at national scale; Figure 7's national panel and the corresponding national multi-year totals are explicitly reserved and left blank pending the national multi-year extension **[PENDING: national 2017-2025 run, E8]**.

## 5.7 Cereal yield

The Cereal yield model reached a spatial-transfer root-mean-square error of 1.21 t/ha (30.4% of the 3.97 t/ha median observed yield). The ABS calibration factor (0.6248, fit on one year of ABS data) checked to within +3.1% to +18.1% of ABS-implied yield on two held-out years (Fig. 8; Table 5). Both raw (NVT-trial-equivalent) and ABS-calibrated yield columns are provided on every classified Cereal polygon (Section 4.5).

**Table 5.** Cereal yield model performance (pooled Wheat/Barley/Oat, satellite-index features), before ABS calibration.

| Split | Arm | n | R² | RMSE (t/ha) |
|---|---|---|---|---|
| Temporal (train ≤2022, test 2023-24) | Year+state baseline | 279 | −0.643 | 2.111 |
| | Satellite features | 279 | 0.471 | 1.197 |
| | Satellite + year/state | 279 | 0.486 | 1.181 |
| Spatial (5-fold GroupKFold on site) | Year+state baseline | 1,119 | 0.294 | 1.473 |
| | Satellite features | 1,119 | 0.526 | 1.207 |
| | Satellite + year/state | 1,119 | 0.577 | 1.140 |

ABS calibration factor: 0.6248 (fit on one year), checked +3.1% to +18.1% against ABS-implied yield on two held-out years. Canola yield is not provided: an optical-only model's coefficient of determination (0.27) did not exceed a trivial year-and-state-mean baseline (0.29), and no yield estimate is provided for a class where the model does not outperform simply guessing the season and region (Section 7, Limitation 5).

**[PENDING — depends on E8, not fabricated here]**: national multi-year (2017-2025) polygon and area totals by year (Table 6); national year-over-year canola/cereal/legume share trends; any claim that the single-national-season (2024) results reported above generalize nationally across seasons — the regional nine-year evidence in Section 5.6 is suggestive, not proof, at national scale.
