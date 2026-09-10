---
section: limitations_and_future_work
mode: full
word_target: 900
---

# 7. Limitations and Future Work

## 7.1 Limitations, in order of severity

1. Area over-call (1.47-1.59x), reproduced nationally and regionally, is the map's most consequential operating characteristic (Sections 5.2 and 6.1). It is mitigated but not eliminated by providing `ndvi_amp` and `abstain_reason` on every polygon (Section 6.4), which lets a downstream user filter to a tighter, more area-accurate subset when that matters more than completeness.
2. Legume misclassification (18.4% mapped against 8.7% ABS share) has no established mechanism. The argmax-versus-mean-probability check rules out a decision-rule artefact (Section 5.3), and Section 6.7 discusses it as the largest unresolved classification error in the map.
3. `unsegmented_blob`, SAM's largest segmentation failure mode, accounts for 48,016 polygons nationally. A size-aware second segmentation pass to split these has not been attempted (Section 4.1).
4. Single-season national coverage. The completed national map covers 2024 only; the national multi-year run (2017-2023, 2025) had not completed at the time of this draft [PENDING: E8]. This is the paper's largest scope gap, and the reason the multi-year results in Section 5.6 and Figure 7 are regional.
5. No canola yield, because it needs Sentinel-1 and Sentinel-1 is not in the deployed pipeline. An optical-only model's spatial-transfer coefficient of determination (0.271) does not exceed a year-and-state-mean baseline (0.290), and a yield estimate that underperforms guessing the season and region is worse than none. Adding Sentinel-1 raises the same spatial-transfer R² to 0.371 on the current row-matched population (Section 6.5), which agrees in direction and size with the original unrepeated test. Canola yield is therefore gated on the same national Sentinel-1 acquisition question as the Cereal yield extension (Section 7.2, item 7).
6. Sentinel-1's value depends on the task. Re-tested against the adopted classifier (Section 6.5; Limitation 10) rather than the retired baseline it was first measured on, Sentinel-1 lowers classification accuracy (−0.023 macro F1 temporal, concentrated on legume) but improves the deployed cereal yield model (+0.092 R² on its operational transfer bar; Table 7). No Sentinel-1 product is used at national scale for either task, in the classifier reported here or in the adopted one.
7. Three classes rather than the species-level roster originally scoped. A nine-species classifier reached macro F1 0.38 at the available recorded label volume, a finding about the label volume that species classification from recorded labels requires (Sections 1 and 4.2).
8. The ABS validation reference is itself uncertain, and is not an Olofsson-style probability-sample area estimate. ABS and ABARES disagree by a median 6.8% on national sown area, and no map-versus-ABS comparison in this paper should be read as more precise than that floor. No probability sample of recorded crop-species labels exists for Australia at the density an Olofsson-style (Olofsson et al., 2014) stratified area estimate with confidence intervals would require. This paper's validation is therefore a composition and area comparison against an independent statistic rather than a stratified accuracy assessment (Sections 2.4 and 4.6).
9. The WorldCereal and NLUM spatial comparisons (Section 5.5) carry a three-year reference-year mismatch (2021 versus this map's 2024). For WorldCereal, they cover only the presence and cereal classes, since canola and legume have no counterpart in WorldCereal's class scheme. Both comparisons were run on a stratified sample rather than the full polygon population, which is adequate for the proportions and agreement rates reported but not for an area-total comparison.
10. A classifier that outperforms the deployed model has been adopted since these results were produced. A candidate feature set, the deployed model's three indices plus six band-derived indices from Sharma et al. (2026), reaches macro F1 0.890 (temporal) and 0.892 (spatial) against the deployed model's 0.821/0.823, with no change to the operating-point canola detection rate (89.0% at a 5% false-positive rate; Table 8). The gain is not uniform across classes: legume F1 rises from 0.69 in both splits to 0.83 (temporal) and 0.82 (spatial), the largest per-class change of any covariate tested in this paper, driven by recall rising from 73%/70% to 89%/85%. This project requires an independent review, separate from the process that produced a candidate, before any model change is adopted. That review was completed on 2026-09-07: the training run reproduced byte-for-byte, the canola detection rate matched at full precision (138 of 155 test paddocks) and the verdict was to adopt. The candidate was adopted into the production pipeline on 2026-09-08. The national map has not yet been regenerated with it, so every classifier number and map statistic in this paper is from the earlier three-index model, referred to throughout this paper as the deployed model [PENDING: 2024 national re-run with the adopted classifier, in progress. The re-run also uses a revised tile geometry (9 km tiles with a tile-boundary merge), so the tile and polygon counts in Sections 3.1 and 5.2 will change].

| Metric | Deployed (3 indices, 51 features) | Adopted (deployed + Sharma et al. indices, 153 features) | Change |
|---|---|---|---|
| Macro F1, temporal | 0.821 | 0.890 | +0.069 |
| Macro F1, spatial | 0.823 | 0.892 | +0.069 |
| Legume F1, temporal | 0.69 | 0.83 | +0.14 |
| Legume F1, spatial | 0.69 | 0.82 | +0.13 |
| Canola detected @ 5% false-positive rate | 89.0% | 89.0% | +0.0 pp |
| Canola average precision | 0.944 | 0.935 | −0.009 |
| Canola ROC AUC | 0.965 | 0.962 | −0.003 |
| Independent review completed | Yes | Yes (2026-09-07, verdict adopt) | n/a |

**Table 8.** Adopted classifier versus the deployed model used for every result in this paper. No result elsewhere in this paper uses the adopted classifier.

## 7.2 Future work, in priority order

1. Complete the national 2017-2025 multi-year run (E8), the direct next step and the one this paper's multi-year claims are written to accommodate. The run followed a discussion of validation methodology and the multi-year regional approach with project colleagues, informed by an earlier version of this manuscript. It is in progress at the time of this draft. No season is final, because the seasons already processed are being re-run with the adopted classifier (Limitation 10).
2. Investigate the Legume over-prediction mechanism, the largest unexplained classification error in the map (Limitation 2).
3. A size-aware second SAM segmentation pass targeting the `unsegmented_blob` failure mode (Limitation 3).
4. Validate two-pass presence gating (exempting Canola from the phenology-shape gate) against the ABS area ratio. The variant restores canola recall to 94.5% at no measured cost to Cereal or Legume recall (Section 5.4), but has not been checked against the area-ratio metric that decided the original gate's rejection.
5. Extend the WorldCereal/NLUM spatial comparison from a 250,000-point sample to the full polygon population, and to additional independent products, once the reference-year mismatch can be narrowed (for example against a WorldCereal release closer to 2024) or a sensitivity check on reference year is added.
6. Regenerate the national map and the ABS validation with the adopted classifier (Limitation 10). The 2024 re-run is in progress at the time of this draft, and every Results number in this paper will be replaced when it completes.
7. Extend Sentinel-1 acquisition to national scale for the yield models rather than the classifier (Section 6.5). Cereal yield gains 0.092 R² on the operational transfer bar, and canola yield cannot be provided without it (Limitation 5): Sentinel-1 is the difference between a canola yield model below the year-and-state baseline (R² 0.271, spatial) and one above it (R² 0.371). Both are gated on two unresolved items: whether the yield gain holds on ordinary commercial paddocks rather than the National Variety Trial paddocks it was measured on (no yield-labelled holdout on ordinary paddock geometry exists), and a revisit-density covariate for the Sentinel-1B acquisition gap, which has not been implemented.
