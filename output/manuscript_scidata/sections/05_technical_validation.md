---
section: technical_validation
mode: full
word_target: 2000
---

# Technical Validation

## Classifier accuracy

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
