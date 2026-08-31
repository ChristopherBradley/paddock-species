---
section: limitations_and_future_work
mode: full
word_target: 650
---

# 7. Limitations and Future Work

## 7.1 Limitations, in order of severity

1. **Area over-call (1.47-1.59x), reproduced nationally and regionally**, is the map's most consequential operating characteristic (Section 5.2, Section 6.1). It is mitigated, but not eliminated, by shipping `ndvi_amp` and `abstain_reason` on every polygon (Section 6.4), which lets a downstream user filter toward a tighter, more area-accurate subset when that matters more than completeness.
2. **Legume misclassification** — 18.4% mapped versus 8.7% ABS share, with the argmax-versus-mean-probability check ruling out a decision-rule artefact (Section 5.3) — has no established mechanism yet and remains untouched by this round of work.
3. **`unsegmented_blob`**, SAM's single largest segmentation failure mode, accounts for 48,016 polygons nationally; a size-aware second segmentation pass to split these was never attempted (Section 4.1).
4. **Single-season national coverage.** The completed national map covers 2024 only; a national multi-year extension (2017-2023, 2025) is planned but not yet executed [PENDING: E8]. This is currently the paper's largest scope gap relative to its own framing as a multi-year resource, and the reason the multi-year results in Section 5.6 and Figure 7 are explicitly regional rather than national.
5. **No canola yield.** An optical-only model's coefficient of determination (0.27) did not exceed a trivial year-and-state-mean baseline (0.29); we judged shipping a yield estimate that underperforms guessing the season and region to be worse than shipping none, and disclose this rather than silently omitting canola yield without explanation.
6. **Sentinel-1 evaluated, not deployed at scale.** A measured +0.03 macro F1 gain, concentrated in the Legume class, likely overlaps the presence-gate problem (Section 5.4, Section 6.1) rather than representing distinct classifier confusion, and was not judged to justify the additional acquisition and processing cost at national scale.
7. **Three classes, not the full ten-species roster** originally scoped. A nine-species classifier reached only macro F1 0.38 at the available field-verified label volume; this is a finding about label-volume requirements for field-verified species classification (Section 1, Section 4.2), stated here for completeness and stated earlier, in the Introduction, so that a reader encounters it as a design decision rather than discovers it only in the Results.
8. **The ABS validation reference is itself uncertain, and is not an Olofsson-style probability-sample area estimate.** ABS and ABARES disagree with each other by a median 6.8% on national sown area; no map-versus-ABS comparison in this paper should be read as more precise than that floor. No probability sample of field-verified crop-species labels exists for Australia at the density an Olofsson-style (Olofsson et al., 2014) stratified area estimate with confidence intervals would require, so this paper's validation is a composition-and-area comparison against an independent statistic, not a stratified accuracy assessment (Section 2.4, Section 4.6).
9. **The WorldCereal and NLUM spatial comparisons (Section 5.5) carry a three-year reference-year mismatch** (2021 versus this map's 2024) and, for WorldCereal, cover only the presence and Cereal classes (Canola and Legume have no counterpart in WorldCereal's class scheme); both comparisons were run on a stratified sample rather than the full polygon population, adequate for the proportions and agreement rates reported but not for an area-total comparison.

## 7.2 Future work, in priority order

1. **Complete the national 2017-2025 multi-year run (E8)** — the direct next step, and the one this paper's own multi-year claims are explicitly written to accommodate once it lands. At the time of this draft, this step has been deliberately deferred pending discussion of the current validation methodology and the consensus/multi-year regional approach with project colleagues, using this manuscript as part of that discussion.
2. **Investigate the Legume over-prediction mechanism** — the largest unexplained classification error in the map (Limitation 2).
3. **A size-aware second SAM segmentation pass** targeting the `unsegmented_blob` failure mode (Limitation 3).
4. **Validate two-pass presence gating** (exempting Canola from the phenology-shape gate) against the ABS area ratio. This variant restores canola recall to 94.5% at no measured cost to Cereal or Legume recall in the presence-recall check alone (Section 5.4), but has not yet been checked against the area-ratio metric that decided the original phenology-shape gate's rejection, and should not be treated as validated until it has.
5. **Extend the WorldCereal/NLUM spatial comparison from a 250,000-point sample to the full polygon population**, and to additional independent products, once the reference-year mismatch can be narrowed (e.g., against a future WorldCereal release closer to 2024) or a sensitivity check against reference year is added.
