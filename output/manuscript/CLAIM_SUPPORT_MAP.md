# Claim Support Map

Every non-trivial numeric or empirical claim in `MANUSCRIPT_DRAFT.md`, mapped to its evidence source. Extends `PAPER_PLAN.md` §12 with the claims added during drafting (E9, Fig03 regeneration, verified citations).

| Claim | Evidence source | Confidence | Section(s) used |
|---|---|---|---|
| National 2024 map: 1,346,582 polygons, 99,465 tiles | `NATIONAL_2024_RUN.md` §1; independently re-verified via `ogrinfo COUNT(*)` on `national_2024_crops.gpkg` during figure generation | High — direct count, twice verified | Abstract, 3.1, 5.2 |
| 48.4% of polygons / 34.4% of area classified; 4 abstain reasons | `NATIONAL_2024_RUN.md`; abstain-reason breakdown independently re-verified via `GROUP BY abstain_reason` during Fig04 generation (area_below_min 339,043; no_crop_signal 269,134; unsegmented_blob 48,016; too_few_observations 39,623) | High | Abstract, 5.2, 7.1 |
| Classifier macro F1 0.821 (temporal) / 0.823 (spatial); confusion counts | `REVIEWED_MODEL.md`; raw counts in `arms/GROUP3_reviewed.md`, independently re-verified when regenerating Fig03 (counts reproduce the stated F1 exactly) | High — held-out, dual validation, numbers directly re-derived from raw counts | 5.1 |
| Canola r=0.82, MAE 5.5 pts vs. ABS | `ABS_COMPARISON_NATIONAL.md` | High — independent statistic, no training-pipeline connection | Abstract, 5.2 |
| 1.47x national / 1.59x regional (100km) area over-call, concentrated Cereal/Legume | `NATIONAL_2024_RUN.md` §4; `ABS_COMPARISON_100km.md` | High — same mechanism, reproduced independently at two scales | Abstract, 5.2, 6.1 |
| Phenology-shape gate: 1.59→1.00 ratio, canola stacked recall 78.3% vs. 91.4%/87.2% | `PHENOLOGY_GATE.md` | High — regional test, both metrics from the same run | 5.4, 6.2 |
| Legume 18.4% mapped vs. 8.7% ABS, argmax=mean-prob | `NATIONAL_2024_RUN.md` §4 | High — rules out decision-rule explanation; mechanism itself still open | 5.3, 7.1 |
| Cereal yield RMSE 1.21 t/ha; calibration 0.6248, checked +3.1%/+18.1% | `YIELD_cereal_pooled.md`, `YIELD_CALIBRATION.md` | High | 5.7 |
| ABS/ABARES median 6.8% mutual disagreement | `ABS_COMPARISON_100km.md` | High — stated floor | 1, 3.3, 7.1 |
| 9-yr regional polygon stability, median IoU 0.84, found 7/9 years | `POLYGON_STABILITY.md` | High | 4.7, 5.6 |
| 9-yr regional weak years 2017/2018 (classified share, ndvi_amp) | `ABS_COMPARISON_100km.md` | High — direct table | 5.6, 6.5 |
| Presto loses to hand-built features (0.775 vs 0.821 F1; combined 0.824) | `REVIEWED_MODEL.md` (verified as the exact source, resolving `PAPER_PLAN.md` §24 Open Issue #6's "verify exact source" flag) | High | 2.1, 5.1, 6.3 |
| AgriWebb Grazing retirement, 78.5% pass-rate finding | `PRESENCE_ONLY_LABELS.md` | High | 4.4, 6.4 |
| 69.7% of training trials co-located, 31.8% different crop; 3-group collapse resolves 69% | `PAPER_PLAN.md` §8 (sourcing project label-conflict analysis) | High | 4.2 |
| **WorldCereal presence agreement 73.1% (symmetric ~73% both directions)** | `output/WORLDCEREAL_COMPARISON.md` (n=250,000, seed=0) | High — large sample, but sampled not census (proportions, not areas) | 5.5, 6.1 |
| **WorldCereal wintercereals agreement with our Cereal class: 49.6%** | `output/WORLDCEREAL_COMPARISON.md` | High — n=82,411 | 5.5 |
| **NLUM enrichment: Canola 6.4x oilseed baseline, Legume 1.6x legume baseline** | `output/NLUM_COMPARISON.md` | Medium-High — enrichment-ratio metric constructed to correct a real cross-commodity scale artefact; see that file's own caveats | 5.5 |
| **NLUM grazing probability: 33.8% at abstained points vs. 10.8% at classified points** | `output/NLUM_COMPARISON.md` | High — large sample, independently corroborates `NONCROP_CLASS.md` | 5.5, 6.1 |
| **National multi-year (2017-2025) totals/trends** | none yet | **N/A — [PENDING: E8], not fabricated anywhere in the draft** | 3.2, 5.6, 7.1, 8 |
| Kirillov et al. 2023, Segment Anything, ICCV 2023, pp. 3992-4003 | Verified via WebSearch during drafting (resolves `PAPER_PLAN.md` §24 Open Issue #6) | High | 2.3, 4.1 |
| Olofsson et al. 2014, RSE 148:42-57, doi:10.1016/j.rse.2014.02.015 | Verified via WebSearch during drafting | High | 2.4, 4.6, 7.1 |
| Ashourloo et al. 2019, ISPRS J. Photogramm. Remote Sens. 156:63-76 | Verified via WebSearch during drafting | High | 3.4 |
| Lawes et al. 2022 (not 2021/2023 as `PAPER_PLAN.md` §22 guessed), Crop & Pasture Science, doi:10.1071/CP21386 | Verified via WebSearch during drafting — year corrected from the plan's placeholder | High | 2.2 |

**Unsupported/weak claims deliberately avoided in this draft** (per `PAPER_PLAN.md` §12): "the pipeline generalizes well across years nationally" (only regionally demonstrated); "canola yield is available" (explicitly not shipped); describing the ABS check as "ground-truth accuracy" (it validates against an independent *aggregate statistic*, itself uncertain by ~6.8%).
