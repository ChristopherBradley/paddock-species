# PAPER_PLAN.md — paddock-species

## §0. Document Status

- **Version**: 1.1 (incremental update — post-draft findings folded in; not yet reviewed by the user)
- **Date**: 2026-08-29 (v1.0); updated 2026-09-03 (v1.1)
- **Target venue**: **Remote Sensing of Environment (RSE)**, Elsevier — see §2 for how this was chosen and the backup option
- **Manuscript type**: Research Paper (applied case study / dataset-and-validation, RSE's "Research Papers" track — RSE has no separate data-descriptor track)
- **Readiness level**: **Partial draft** — see §25. Blocked on one real, not-yet-run experiment (national 2017-2025 multi-year mapping, currently in progress in a parallel session: 2 of 9 years done as of 2026-09-03). Journal (RSE) and the Newman & Furbank citation are resolved as of 2026-08-29 (§24); manuscript **submission** (not drafting) is now gated on sending the finished manuscript to GRDC for sign-off, per the project's signed data-use agreement (§24 Open Issue #2).
- **v1.1 update (2026-09-03)**: folded in five findings produced after the 2026-08-30 draft — S1 re-tested against the current best classifier and yield model (classifier REGRESSES, yield IMPROVES — reversing/splitting the original single "S1 helps" story), Sharma6 indices tested for canola yield (regresses), and a new leading classifier candidate (shipped 3 indices + Sharma6's 6, macro F1 0.890/0.892 vs. shipped 0.821/0.823, not yet independently reviewed or adopted). See §5, §10, §11, §12, §16, §17, §24 for the specific changes. This is an incremental update — the existing 26-section structure, E8-pending gating, and prior decisions (§24 Open Issues #1-#4) are preserved, not rebuilt.
- **Input files consumed (v1.0)**: `BRIEF.md`, `output/LIT_REVIEW_REPORT.md`, `output/IDEA_REPORT.md`, `output/NARRATIVE_REPORT.md`, `output/PHENOLOGY_GATE.md`, `output/NEXT_STEPS.md`, `output/POLYGON_STABILITY.md`, `output/ABS_COMPARISON_100km.md`, `output/ABS_COMPARISON_100km_shapegate.md`
- **Additional input files consumed (v1.1)**: `output/S1_VS_LATEST_MODEL.md`, `output/YIELD_cereal_pooled_ctl.md`, `output/YIELD_cereal_pooled_s1.md`, `output/CANOLA_YIELD_indices_only.md`, `output/CANOLA_YIELD_shipped_sharma6.md`, `output/GROUP3_MODEL_shipped_plus_sharma6_VALIDATION.md`, `output/EXPERIMENT_PLAN.md`, `output/EXPERIMENT_TRACKER.md`
- **Missing inputs** (soft failures, per skill design — this project never ran the standard idea→refine→experiment-design pipeline, confirmed in `NARRATIVE_REPORT.md` §1): `RESEARCH_PLAN.md`, `output/refine-logs/FINAL_PROPOSAL.md`, `output/EXPERIMENT_PLAN.md`, `output/EXPERIMENT_RESULT.md`, `output/AUTO_REVIEW_REPORT.md`. None of these block planning — `NARRATIVE_REPORT.md` is the richer, retrospective substitute the skill's own rules say to prefer when present.
- **Not run this pass**: Phase 6's external cross-review (GPT-5.4 via Codex MCP / fresh subagent). Codex MCP is not configured in this environment, and spawning a full review subagent on top of plan+figures+draft in one sitting works against the Claude Code quota constraints `CLAUDE.md` flags. Recommend the user's own read of this plan serve as the checkpoint instead (§24).

---

## §1. One-Paragraph Summary

This paper documents a national, polygon-level, three-class (Canola / Cereal / Legume) crop-species map of Australia at 10 m resolution, built end-to-end from open Sentinel-2 imagery and field-verified GRDC/National Variety Trials (NVT) ground truth — segmented with Segment-Anything-based paddock delineation, classified with a gradient-boosted spectral-index model, gated for crop presence, and attributed with a calibrated cereal-yield estimate. Validated against independent ABS sown-area statistics across 132 censused SA2s (no connection to the training pipeline), the map's canola composition tracks the official statistic closely (r = 0.82, median absolute error 5.5 points) but the map as a whole over-calls crop-present area by 1.47-1.59x, concentrated almost entirely in Cereal and Legume and essentially absent from Canola — a presence-detection problem, not a classification problem, confirmed by a more sophisticated phenology-shape presence gate that fixed the area ratio but broke canola recall specifically, and was rejected. A single national season (2024) is complete and validated; a nine-year regional test (100 km, Riverina NSW, 2017-2025) validates the pipeline's temporal behaviour, including two identified structurally-weaker years (2017, 2018); **extending the identical pipeline to a full national 2017-2025 multi-year run is planned but not yet executed**, and is the one open experiment this plan is written around.

---

## §2. Target Journal Strategy

**Primary target: Remote Sensing of Environment.** Three reasons: (1) it was the brief's original target venue (`BRIEF.md` §4); (2) it is one of the three candidates `NARRATIVE_REPORT.md` §7 names when it reframes this project's contribution as a dataset paper; (3) unlike a pure data-descriptor venue, RSE's full research-article format has room to present the project's several genuine secondary findings (the NVT label-conflict resolution, the Presto-vs-hand-built-features negative result, the presence-only design vs. the retired absence-labelled AgriWebb approach, and — the strongest one — the phenology-gate trade-off) as first-class discussion material rather than folding them into a methods appendix. RSE also already carries this project's methodological precedent for aggregate accuracy assessment (Olofsson et al. 2014, in the existing lit review).

RSE's author guidance (checked via WebSearch, no strict overall word cap found; standard Elsevier "Research Paper" format) requires: a Highlights list (3-5 bullets, ≤85 characters each), a graphical abstract, a CRediT author-contribution statement, and a Data Availability Statement — all included in §19/§26 below. Abstract ≤ ~250 words. Citation style: Elsevier journals vary by title; RSE's exact in-text/reference style was not confirmed by this search — **verify in the live "Guide for Authors" page before final formatting** (`paper-covert` stage, not blocking drafting).

**Backup option: Nature *Scientific Data*.** Checked via WebSearch: strict Data Descriptor format (Background & Summary ≤700 words, Methods unlimited, ≤8 figures, ≤10 tables, abstract ≤170 words, **abstract must not claim new scientific findings**). This is the better structural fit if RSE reviewers push back on "not enough of a single novel algorithmic contribution" — the pipeline's Background & Summary / Methods / Data Records / Technical Validation / Usage Notes sections map almost one-to-one onto material already written in `NARRATIVE_REPORT.md` §7. The cost of switching: the Presto negative result, the gate trade-off, and the label-conflict finding would need to be reframed as methods justification rather than reported findings, since Scientific Data abstracts explicitly disallow "new scientific findings" framing.

**This is a judgement call, not a locked decision** — see §24 Open Issue #1.

---

## §3. Research Context and Motivation

Australia's grains sector (wheat, barley, canola, and pulse/legume crops) is a major export industry with no continent-wide, field-verified, species-resolved crop map publicly available at paddock scale. Existing global crop-mapping infrastructure (WorldCereal, Esri/Impact Observatory LULC, Dynamic World) classifies cropland generically or at coarse crop-type resolution; Australia is not covered by any published foundation-model crop-type generalizability study (`LIT_REVIEW_REPORT.md` Theme A). The two closest Australian precedents — an in-season Sentinel-2 classifier for six classes in Western Australia (Sharma et al. 2026) and a Sentinel-1+2+MODIS fusion classifier for cereals-vs-canola in the Murray-Darling Basin (Al-Shammari et al. 2024) — are both regional, and both train on either another model's output or opportunistic harvester data rather than field-verified ground truth (`LIT_REVIEW_REPORT.md`, "Public availability" section). Meanwhile, official production and area statistics (ABS, ABARES) exist only at coarse administrative-region granularity, with no spatial detail below the SA2/state level and with the two agencies disagreeing with each other by a median 6.8% on national sown area (`ABS_COMPARISON_100km.md`) — the honest floor against which any finer-grained map should be judged, not zero.

This paper addresses that gap directly: it uses the GRDC/NVT trial network — genuine field-recorded sowings, not another model's predictions — as ground truth for a national, paddock-scale, 10 m map, and validates the result against ABS as an independent check with no connection to the training pipeline.

---

## §4. Research Gap

`LIT_REVIEW_REPORT.md`'s Gap Analysis ranked five gaps; **this paper's actual contribution reframes which of those gaps it closes**, because the shipped pipeline diverged from the originally-selected Gap #1 (foundation-model species-level classification — see `NARRATIVE_REPORT.md` §1 for the full account of why: Presto measured worse than hand-built features, and 9-species classification was not reachable at the available label volume, both genuine negative results reported here rather than hidden).

The paper as actually positioned closes:
- **Gap #4, Validation gap (0.70 in the original ranking)** — "No study cross-validates a national Australian crop-species map against NLUM and a WorldCereal-style global product using Olofsson-style rigorous area/accuracy estimation." This paper closes the ABS-composition half of that gap at national scale; the NLUM/WorldCereal spatial-comparison half remains open (§17, §24 Open Issue #4) and Olofsson-style stratified-sample area estimation with confidence intervals is explicitly *not* attempted (no probability sample of field-verified labels exists at the needed density) — stated as a limitation, not silently substituted.
- **Gap #3, Geographic/scale/ground-truth gap (0.72)**, partially — this map is continent-wide and trains only on field-verified labels (unlike both Australian precedents), but ships 3 classes, not the full ~10-species GRDC roster the gap originally called for. The descoping is stated up front (§7), not discovered by the reader in the results.

Gaps #1 (foundation-model methodology), #2 (ePaddocks data-linkage), and #5 (Southern-Hemisphere canola-flower recalibration) are **not** closed by this paper and should not be claimed — Gap #1 was tried and lost to a simpler baseline; Gap #2's boundary source (ePaddocks) was replaced by SAM-based segmentation early in the project; Gap #5 was never pursued as its own line of work.

---

## §5. Novelty and Contributions

**Primary contribution (dominant).** A national, polygon-level, three-class (Canola/Cereal/Legume) crop-species map of Australia at 10 m, built end-to-end from open Sentinel-2 and field-verified GRDC/NVT ground truth, carrying per-polygon confidence, an explicit abstain reason where unclassified, and a calibrated Cereal-yield attribute — validated against an independent official statistic (ABS sown area, 132 SA2s) with no connection to the training pipeline. One national season (2024, 1,346,582 polygons) is complete; **the multi-year national extension (2017-2023, 2025) is planned and this plan is written to accommodate its results once available (§24 Open Issue #3)**.

**Primary contribution (supporting).** A quantified, mechanistically-explained area-inflation failure mode common to presence-only crop mapping (1.47-1.59x over-call, concentrated in Cereal/Legume, essentially absent from Canola), plus a documented negative result from the natural, more principled fix: a phenology-shape presence gate that closed the area-ratio gap (1.59 → 1.00 regionally) but did so by disproportionately rejecting real canola paddocks (stacked presence recall 78.3% vs. cereal 91.4%/legume 87.2%), and was rejected for that reason. This is a transferable caution for anyone building a presence gate from season-shape heuristics: the more "correct-looking" fix is not automatically the better trade.

**Secondary/supporting findings** (each explains a design decision rather than standing alone as a headline claim — do not over-promote these in the abstract/intro, per §23):
1. A label-conflict finding specific to point-based agronomic trial-network ground truth: 69.7% of training trials share their segmented paddock with another NVT trial, 31.8% with a different crop; collapsing 9 species to 3 broad groups resolves 69% of those conflicts, and hand-reviewing the remainder adds +0.019 macro F1.
2. A negative result for foundation-model embeddings (Presto) against hand-built DOY-binned spectral indices, at this label volume and class structure (macro F1 0.775 vs. 0.821).
3. A demonstrated failure mode for absence-labelled negative classes built from presence-only farmer records (the retired AgriWebb "Grazing" class, 78.5% of "hard stratum" grazing paddocks passing the same crop-presence test as known crops), motivating the segmentability-as-mask + presence-gate design actually shipped.
4. A measured, honestly-caveated NVT-trial-to-commercial-yield offset (multiplicative factor 0.6248, checked +3.1% to +18.1% against ABS on two held-out years) — both raw and calibrated columns ship, never only the calibrated one.
5. **(Added v1.1)** Sentinel-1's marginal value is task-dependent, not a single "helps/doesn't help" verdict — once measured against the current best models rather than the retired 3-index baseline, S1 *regresses* the classifier (macro F1 −0.023 temporal/−0.018 spatial, concentrated on Legume 0.82→0.77, because Sharma6's `ndre2` index already fixed the Legume/Cereal confusion S1 used to fix) but *improves* the shipped Cereal yield model (+0.092 temporal / +0.022 spatial R², the largest single gain on the model's own "honest operational bar"). A second covariate swap runs the same direction in reverse: Sharma6 indices, which help classification, regress canola yield prediction (temporal R² 0.206→0.012). Full evidence: `S1_VS_LATEST_MODEL.md`, `YIELD_cereal_pooled_s1.md`, `CANOLA_YIELD_shipped_sharma6.md`. Framed in Discussion (§16) as a second transferable caution alongside the phenology-gate finding: a feature or covariate validated as helpful for one task in a shared pipeline can be actively harmful for another.
6. **(Added v1.1, NOT adopted — reported as a discussion/future-work finding, not a Results-section headline)** A leading classifier candidate (the shipped 3 indices + Sharma et al. 2026's 6 band-derived indices, 153 features) reaches macro F1 0.890 temporal / 0.892 spatial — up from the shipped model's 0.821/0.823 — with no regression on the decision-relevant canola-at-5%-FPR metric (89.0%, exact match). This candidate has **not yet been independently reviewed** (per this project's generator-evaluator separation rule) and is **not the model used to produce the 2024 national map or any result reported in this paper** — see §24 Open Issue #8 for the explicit, still-open decision about whether to adopt it before submission. `GROUP3_MODEL_shipped_plus_sharma6_VALIDATION.md`.

**What this paper is *not* claiming**: not a species-level (10-class) classifier (descoped to 3 groups, stated as a finding not a footnote); not a foundation-model methods paper (Presto was tried and lost); not a canola-yield product (optical-only R² does not beat guessing the year and state); not, yet, a spatial comparison against NLUM or WorldCereal (open — §17); not, until the pending run completes, a validated national multi-year time series (only single-season-national + multi-year-regional exist today).

---

## §6. Research Questions and Hypotheses

- **RQ1.** Can a SAM-based paddock segmentation + gradient-boosted spectral classifier, trained only on field-verified point-in-paddock trial labels, produce a national crop-species map whose composition matches independent official area statistics? — **Answered, partially**: yes for Canola composition (r=0.82), not for absolute area (1.47-1.59x over-call).
- **RQ2.** Is the pipeline's dominant disagreement with official statistics a classification error or a presence/absence-detection error? — **Answered**: presence/absence. Dividing out the area over-call recovers near-exact canola-share agreement; Legume remains a real classification error on top of that (18.4% mapped vs. 8.7% ABS, unexplained by argmax-vs-mean-probability disagreement).
- **RQ3.** Does tightening the presence criterion using season shape (green-up + post-harvest senescence) rather than amplitude alone reduce area over-call without disproportionately harming any one crop's recall? — **Answered: no.** It reduces the area ratio (1.59→1.00 regionally) but disproportionately harms Canola recall specifically (78.3% stacked vs. 91.4%/87.2% for Cereal/Legume) — rejected.
- **RQ4** [depends on the pending national multi-year run]**.** Does the pipeline's accuracy and area-inflation behaviour generalize consistently across a full national multi-season run (2017-2025), or does it vary by season the way the 100 km regional test's weak years (2017, 2018) suggest it might? — **Not yet answerable at national scale.** Regional (100 km) evidence exists and is reported as such (§11); national evidence is the pending extension.

---

## §7. Study Scope and Boundaries

- **Spatial**: continent-wide Australia (99,465 tiles) for the completed 2024 national run; a 100 km × 100 km Riverina, NSW block for the intensively-validated multi-year regional test.
- **Temporal**: single season (2024) at national scale — complete. Nine seasons (2017-2025) at regional (100 km) scale — complete. Nine seasons (2017-2023, 2025 remaining) at **national** scale — planned, not yet run; this is the gap this plan is written around.
- **Species/class scope**: 3 groups only — Canola, Cereal (wheat+barley+oat), Legume (chickpea+faba bean+field pea+lentil+lupin) — not the full ~10-species GRDC roster named in the original brief. **Correction 2026-08-30**: earlier drafts of this line said "wheat+barley+oat+triticale" — verified against `train_species.py`'s `GROUP` dict and `nvt_trials_labeled.csv`'s actual crop values: there is no Triticale in the trial data at all (9 species present: Wheat, Canola, Barley, Chickpea, Oat, Field Pea, Lupin, Faba Bean, Lentil), so Cereal is wheat+barley+oat only. State this descoping explicitly and early (§5, §23); it is a finding (9-class macro F1 0.38 vs. 3-group's 0.78-0.82), not an oversight.
- **Method scope**: crop presence + 3-class classification + Cereal-only calibrated yield. No canola yield (ships blank, with the reason stated). Sentinel-1 evaluated (+0.03 macro F1, concentrated in Legume) but never deployed at scale — its measured benefit substantially overlaps the presence-gate problem, not classifier confusion.
- **Explicit non-goals**: no attempt at species-level (10-class) resolution; no spatial pixel/polygon-level comparison against NLUM or WorldCereal (aggregate ABS composition only); no Olofsson-style stratified-probability accuracy assessment with confidence intervals (no suitable probability sample of field-verified labels exists); no downstream tree-shelter-productivity analysis (explicitly out of scope per `BRIEF.md` §11, a separate later project).

---

## §8. Data and Materials

| Dataset | Role | Resolution/Extent | Access/License note |
|---|---|---|---|
| Sentinel-2 (via DEA ARD, `ga_s2am/bm/cm_ard_3`, NCI datacube) | Primary imagery, DOY-binned spectral indices (NDVI/NDYI/CFI) | 10 m, national, 2017-2025 | Open |
| GRDC / National Variety Trials (NVT) | Training/validation ground truth: sown crop per trial site, field-verified | Point-in-paddock, national, 2017-2025 | **NDA-restricted — never released, described only in aggregate. See §18.** |
| ABS sown-area statistics | Independent validation reference, no connection to training pipeline | SA2-level, 132 censused SA2s, national | Public (ABS) |
| ABARES production statistics | Cross-check on ABS itself (median 6.8% mutual disagreement — the accuracy floor) | State/national | Public |
| NLUM v7 250 m Ag Probability Surfaces | Coverage mask for the national run only (mask = winter cereals ∪ oilseeds ∪ legumes) | 250 m, national | Already in repo (`data/raw/`) — used as a mask, **not yet as a compared product** (§17 open thread) |
| SAM (Segment Anything, Meta), `vit_h`, via SAMGeo/PaddockTS | Paddock-scale segmentation, stock parameters (re-tuning tried and ruled out) | 10 m-derived polygons | Open model weights |

Preprocessing: paddock polygons kept only at 5-300 ha with compactness ≤ 8 (a free, non-spectral presence signal — keeps 77.9% of known crop paddocks, rejects 65% of pasture, costs 22% of real crop paddocks). 51 paddock-median spectral features, DOY-binned. Trial-to-polygon label matching hand-reviewed to resolve the co-located-trial conflict (§5).

---

## §9. Methodological Plan

1. **Segmentation** — SAMGeo (`vit_h`, stock parameters) over each tile; polygons retained only within the 5-300 ha + compactness ≤ 8 mask.
2. **Labelling** — NVT trial point matched to its enclosing SAM polygon; 9 species collapsed to 3 groups to resolve co-located-trial label conflicts; remaining ambiguous matches hand-reviewed.
3. **Classification** — `HistGradientBoostingClassifier` on 51 paddock-median DOY-binned spectral features (NDVI/NDYI/CFI), 3 classes. Evaluated both temporally (train ≤2022, test 2023-24) and spatially (5-fold `GroupKFold` on site) to separate "does it generalize across time" from "does it generalize across new locations."
4. **Presence gating** — primary/shipped: NDVI amplitude (p90-p10) ≥ 0.35, fitted presence-only on 3,439 NVT trials. Tested alternative: a two-variant (oracle sow/harv-anchored vs. deployable peak-anchored) phenology-shape gate requiring both a green-up rise and a post-harvest senescence drop, evaluated for held-out presence recall and, critically, for **regional area-ratio impact against ABS** — the step the amplitude gate's presence-recall number alone cannot answer.
5. **Yield** — `HistGradientBoostingRegressor`, same 51-feature contract, Cereal only (Wheat+Barley+Oat pooled to match the classifier's own class), calibrated to ABS with a single national multiplicative factor fit on one year and checked on two held-out years.
6. **Validation protocol** — aggregate composition and area comparison against ABS sown-area statistics across 132 SA2s where the mapped footprint sufficiently covers the SA2 (≥50% cover threshold used for headline numbers); argmax-vs-mean-probability agreement used to distinguish decision-rule artefacts from genuine presence/classification uncertainty; a fixed-threshold sensitivity table reported as a sensitivity check, explicitly *not* as a fitting procedure against ABS (fitting to ABS would destroy the only independent validation available).
7. **Multi-year generalization check** — 9-year (2017-2025) regional (100 km) re-run of the identical pipeline, used for polygon geometric stability (median IoU 0.84 across years) and per-year coverage/classification-rate behaviour (§11). **National-scale multi-year re-run: planned, not yet executed.**

---

## §10. Experiments

| ID | Experiment | Status |
|---|---|---|
| E1 | Classifier accuracy, temporal + spatial transfer | **Done** — `REVIEWED_MODEL.md` |
| E2 | Presence gate (amplitude) design + held-out recall | **Done** — `PRESENCE_ONLY_LABELS.md` |
| E3 | National 2024 map generation + ABS validation | **Done** — `NATIONAL_2024_RUN.md`, `ABS_COMPARISON_NATIONAL.md` |
| E4 | Phenology-shape gate: design, oracle vs. deployable, regional (100 km × 9-yr) test | **Done, rejected** — `PHENOLOGY_GATE.md`, `ABS_COMPARISON_100km_shapegate.md` |
| E5 | Sentinel-1 marginal value | **Done, not adopted** — `SENTINEL1_VALUE.md`, `S1_MODEL.md` |
| E6 | Cereal yield model + ABS calibration | **Done** — `YIELD_cereal_pooled.md`, `YIELD_CALIBRATION.md` |
| E7 | 9-year regional (100 km) polygon geometric stability | **Done** — `POLYGON_STABILITY.md` |
| E8 | **National multi-year run (2017-2023, 2025)** | **[IN PROGRESS as of 2026-09-03 — 2024 and 2023 done]**. `run_national.sh predict`, unchanged shipped config, per year, running in a parallel session. Per-year SU cost ~ the 2024 national run's 6,622.6 SU as reference (`NATIONAL_2024_RUN.md` §3); ~8 additional years. |
| E9 (optional, recommended) | Spatial comparison against NLUM / WorldCereal | **Done** 2026-08-30 — `output/WORLDCEREAL_COMPARISON.md`, `output/NLUM_COMPARISON.md` (§24 Open Issue #4) |
| E10 *(v1.1)* | S1 re-tested against the *current* best classifier (shipped+sharma6) and the *current* shipped yield model (`cereal_yield.joblib`) — every prior S1 number used the retired 3-index classifier | **Done** — `S1_VS_LATEST_MODEL.md`. Classifier: **REGRESSES** (−0.023 temporal/−0.018 spatial macro F1, Legume-concentrated), reversing the earlier `S1_MODEL.md` verdict. Yield: **CONFIRMS/IMPROVES** (+0.092 temporal/+0.022 spatial R², `YIELD_cereal_pooled_ctl.md` vs `_s1.md`). |
| E11 *(v1.1)* | Sharma6 indices tested for canola yield (first regression test — Sharma6 was validated for classification only) | **Done, regresses** — `CANOLA_YIELD_indices_only.md` (R² 0.206) vs `CANOLA_YIELD_shipped_sharma6.md` (R² 0.012), temporal split |
| E12 *(v1.1)* | Leading classifier candidate: shipped 3 indices + Sharma6's 6, full validation incl. independent-review follow-up items | **Done, candidate — NOT independently reviewed, NOT adopted** — `GROUP3_MODEL_shipped_plus_sharma6_VALIDATION.md`. Macro F1 0.890 temporal / 0.892 spatial vs. shipped 0.821/0.823, canola@5%FPR unchanged (89.0%). See §24 Open Issue #8. |

---

## §11. Results Summary

**Headline (available now):**
- National 2024 map: **1,346,582 polygons**, 2.8 GB, 99,465 tiles (98.9% of national coverage). 48.4% of polygons (34.4% of area) carry a classification; the rest carry a specific abstain reason.
- Classifier: macro F1 **0.821** (temporal) / **0.823** (spatial); Canola recall 89.0% @ 5% FPR; per-class precision Canola 0.94/0.91, Cereal 0.89/0.89, Legume 0.65/0.68 (temporal/spatial).
- ABS validation (national, 132 SA2s): canola share **r = 0.82**, median absolute error **5.5 points**; area over-call **1.47x**, concentrated in Cereal (+23.2 pts) and Legume (+10.8 pts), essentially absent from Canola (-0.3 pts); once divided out, canola share matches ABS almost exactly (13.1% vs. a diluted 13.4%).
- Legume classification error, distinct from the presence problem: 18.4% mapped vs. 8.7% ABS, argmax and mean-probability agreeing (rules out a decision-rule fix) — **unexplained, open** (§17).
- Phenology-shape gate (100 km regional test, 9 years, 120 SU): area ratio 1.59 → 1.00, but stacked canola presence recall 78.3% vs. cereal 91.4%/legume 87.2% — **rejected**.
- Cereal yield: spatial-transfer RMSE 1.21 t/ha (30.4% of 3.97 t/ha median); ABS calibration factor 0.6248, checked +3.1% to +18.1% on two held-out years.
- 9-year regional (100 km) polygon geometric stability: median polygon found in 7 of 9 years, median IoU 0.84; stability peaks at 25-100 ha (real-paddock range) and falls at both extremes — an independent, purely geometric corroboration of the area mask.
- 9-year regional (100 km) year-by-year coverage (shipped, amplitude-gate config; `ABS_COMPARISON_100km.md`): classified share ranges from **52.5% (2018)** and **59.0% (2017)** — the two flagged weak years — up to **78.5% (2025)**; mean `ndvi_amp` is correspondingly lowest in 2018 (0.42) and 2017 (0.46) vs. 0.60-0.62 in 2024-2025. This is real, already-collected multi-year evidence, **but it is regional (100 km), not national.**

**Post-draft findings, folded in v1.1 (2026-09-03) — describe candidate/ablation results, not the shipped model that produced the headline numbers above:**
- S1 re-tested against the current best classifier (shipped+sharma6, not the retired 3-index baseline): **regresses** macro F1 by −0.023 temporal/−0.018 spatial, concentrated on Legume (F1 0.82→0.77, Legume→Cereal errors 8→19). Mechanism: Sharma6's `ndre2` already fixed the Legume/Cereal confusion S1 used to fix; its permutation importance collapses from +0.134 to +0.018 once S1 is added, with every other family scoring negative — classic feature dilution on 1,636 rows against 204 features. `S1_VS_LATEST_MODEL.md` §1.
- S1 re-tested against the shipped Cereal yield model (`cereal_yield.joblib`, pooled Wheat+Barley+Oat, 1,089 trials): **clear gain**, R² +0.092 temporal (0.419→0.511, satellite+year/state) / +0.022-0.054 spatial. Opposite direction from the classifier result. `S1_VS_LATEST_MODEL.md` §2, `YIELD_cereal_pooled_ctl.md`/`_s1.md`.
- Sharma6 indices (which help classification) tested for canola yield for the first time: **regresses**, temporal R² 0.206→0.012, spatial edge over year+state baseline nearly erased (0.376→0.322 vs. baseline 0.316). `CANOLA_YIELD_indices_only.md`/`CANOLA_YIELD_shipped_sharma6.md`.
- A leading classifier candidate exists (shipped 3 indices + Sharma6's 6, 153 features): macro F1 0.890 temporal/0.892 spatial vs. the shipped model's 0.821/0.823 above, canola@5%FPR unchanged (89.0%). **Not independently reviewed, not adopted, not used to produce any number elsewhere in this Results section** — reported here for completeness only; see §24 Open Issue #8 for the live decision on whether to adopt it before submission. `GROUP3_MODEL_shipped_plus_sharma6_VALIDATION.md`.

**[PENDING — depends on E8, in progress as of 2026-09-03, 2 of 9 years complete]:**
- National multi-year (2017-2025) polygon/area totals and per-year coverage.
- National year-over-year canola/cereal/legume share trends.
- Any claim that the single-national-season (2024) accuracy numbers above generalize nationally across seasons — the regional 9-year evidence is suggestive, not proof, at national scale.

---

## §12. Claim-to-Evidence Map

| Claim | Evidence source | Confidence |
|---|---|---|
| National 2024 map: 1,346,582 polygons, 2.8 GB | `NATIONAL_2024_RUN.md` §1 | High — direct count |
| Classifier macro F1 0.821/0.823, per-class precision | `REVIEWED_MODEL.md` | High — held-out, dual validation (temporal+spatial) |
| Canola share r=0.82, MAE 5.5 pts vs. ABS | `ABS_COMPARISON_NATIONAL.md` | High — independent statistic, no training-pipeline connection |
| 1.47x national area over-call, concentrated Cereal/Legume | `NATIONAL_2024_RUN.md` §4 | High |
| 1.59x regional (100 km) area over-call (shipped config) | `ABS_COMPARISON_100km.md` | High — same mechanism as national, reproduced independently |
| Phenology-shape gate: 1.59→1.00 ratio, canola recall 78.3% stacked | `PHENOLOGY_GATE.md` | High — regional test, 120 SU, both metrics from the same run |
| Legume 18.4% mapped vs. 8.7% ABS, argmax=mean-prob | `NATIONAL_2024_RUN.md` §4 | High — rules out decision-rule explanation, mechanism itself still open |
| Cereal yield RMSE 1.21 t/ha, calibration 0.6248 | `YIELD_cereal_pooled.md`, `YIELD_CALIBRATION.md` | High |
| ABS/ABARES median 6.8% mutual disagreement | `ABS_COMPARISON_100km.md` | High — both are official series, disagreement is the stated floor |
| 9-yr regional polygon stability, median IoU 0.84 | `POLYGON_STABILITY.md` | High |
| 9-yr regional weak years 2017/2018 (lower classified share, lower ndvi_amp) | `ABS_COMPARISON_100km.md` | High — direct table |
| Presto loses to hand-built features (0.775 vs 0.821 F1) | `NARRATIVE_REPORT.md` §1 (sourcing `REVIEWED_MODEL.md`) | Medium-High — verify exact source file before drafting (§24) |
| AgriWebb Grazing retirement, 78.5% pass-rate finding | `PRESENCE_ONLY_LABELS.md` | High |
| **National multi-year (2017-2025) totals/trends** | **none yet** | **N/A — [PENDING], in progress (2/9 years done 2026-09-03)** |
| NLUM/WorldCereal spatial comparison: WorldCereal presence agreement 73.1%, wintercereals-vs-Cereal 49.6%; NLUM enrichment ratios (Canola 6.4x, Legume 1.6x), abstain-point grazing probability 33.8% vs. 10.8% | `output/WORLDCEREAL_COMPARISON.md`, `output/NLUM_COMPARISON.md` | High — 250k-point stratified sample, independent of training pipeline |
| *(v1.1)* S1 regresses shipped+sharma6 classifier: −0.023 temporal/−0.018 spatial macro F1, concentrated on Legume (0.82→0.77) | `S1_VS_LATEST_MODEL.md` §1 | High — controlled arm, identical rows both sides, gain more than 2x the established seed-noise floor |
| *(v1.1)* S1 improves shipped Cereal yield model: +0.092 temporal/+0.022 spatial R² | `S1_VS_LATEST_MODEL.md` §2, `YIELD_cereal_pooled_ctl.md`/`_s1.md` | High — controlled arm, largest gain on the model's own "honest operational bar" |
| *(v1.2)* S1 confirmed necessary for canola yield to clear the year+state baseline: spatial R² 0.271 (optical alone, below baseline 0.290) → 0.371 (with S1, above baseline) | `CANOLA_YIELD_s1ctl.md`/`CANOLA_YIELD_s1.md`, job 178174639, re-tested 2026-09-04 against the row-matched `keep_s1both` population | High — re-test of an earlier (2026-08-25) unverified number, confirmed rather than reversed on re-test, same discipline as the classifier/Cereal-yield re-tests |
| *(v1.1)* Sharma6 indices regress canola yield: temporal R² 0.206→0.012 | `CANOLA_YIELD_indices_only.md`, `CANOLA_YIELD_shipped_sharma6.md` | High — first regression test of Sharma6 on this target |
| *(v1.1)* Leading classifier candidate (shipped+sharma6): macro F1 0.890/0.892, no canola@5%FPR regression (89.0%, exact match) | `GROUP3_MODEL_shipped_plus_sharma6_VALIDATION.md` | Medium-High — clean controlled experiment, but **not independently reviewed and not adopted**; report as discussion/future-work only (§24 Open Issue #8) |

**Unsupported/weak claims to avoid in drafting**: "the pipeline generalizes well across years nationally" (only regionally demonstrated); "canola yield is available" (explicitly not shipped); "this validates against ground-truth accuracy" when describing the ABS check (it validates against an independent *aggregate statistic*, itself uncertain by ~6.8% — not pixel-level ground truth); "Sentinel-1 improves the map" as an unqualified statement (true for yield, false for classification — always name the task); "the shipped+sharma6 candidate is the model" or citing its 0.890/0.892 as the paper's classifier accuracy (it is an unreviewed, unadopted candidate — every Results-section number in this paper comes from the shipped 0.821/0.823 model).

---

## §13. Figures Plan

MAX_FIGURES = 8 (soft cap). All figures below use only completed data; none require the pending national multi-year run except the placeholder panel noted in Fig. 7.

### Fig. 1 — HERO: Pipeline overview + example output
**What it shows**: A horizontal pipeline schematic (Sentinel-2 → SAM segmentation → paddock mask → spectral-feature classifier → presence gate → Cereal yield) on top, paired below with a real map panel (a representative sub-region, e.g. part of the Riverina 100 km box) showing actual output polygons coloured by class (Canola/Cereal/Legume/abstained-with-reason).
**Why a skim reader gets the paper from this alone**: it shows both *how* the dataset was made and *what it looks like*, including that a meaningful fraction of polygons are retained-but-unclassified (a design choice, not missing data) — the single fact a reviewer most needs before reading further.
**Caption draft**: "Pipeline overview and example output. Sentinel-2 time series drive both SAM-based paddock segmentation and a 3-class spectral classifier; a presence gate determines whether a segmented paddock is classified at all. The lower panel shows real output over [region], coloured by predicted class or abstain reason."
**Data source**: `derived/map100/pred/` (existing regional run output) or `derived/national2024/national_2024_crops_classified.gpkg`. **Status: DONE 2026-08-30** — `output/figures/Fig01_hero.png/.pdf`. Used `map100/consensus_crops.gpkg`'s 2024 layer (a map100-pred-derived product) for the real map panel, 12km x 12km Riverina window, 361 polygons.

### Fig. 2 — Study area map
Australia national footprint (2024 run extent) with the 100 km × 100 km Riverina regional validation box and the 132 validation SA2s overlaid.
**Caption draft**: "Study area. National coverage of the 2024 map (grey), the 100 km × 100 km Riverina, NSW block used for the nine-year (2017-2025) regional test (outlined), and the 132 SA2s used for ABS composition validation (points/polygons, coloured by state)."
**Status: DONE 2026-08-30** — `output/figures/Fig02_study_area.png/.pdf`. **Correction**: re-deriving the >=50%-covered subset directly from `ABS_COMPARISON_NATIONAL.md`'s own published table gives **133** SA2s, not 132 — see `output/figures/FIGURE_MANIFEST.md` "Consistency Issues" for the rounding-boundary explanation. Update this section's "132" to "133" (or re-check against `abs_compare.py`'s unrounded intermediate output) before the manuscript locks the number in.

### Fig. 3 — Classifier confusion matrices (temporal + spatial)
**Status: DONE 2026-08-30** — `output/figures/Fig03_confusion_matrices.png/.pdf`, regenerated from the raw confusion counts in `output/arms/GROUP3_reviewed.md` (the "reviewed" arm, macro F1 0.821 temporal / 0.823 spatial — matches exactly, since these are the same counts the F1 was computed from). Replaces the old unverified `confusion_group3_reviewed.png`.

### Fig. 4 — National 2024 map, full continent
Full-continent map, coloured by predicted class, with abstained polygons shown in a distinct neutral colour/pattern (not blank — the map's abstain rate is part of the story).
**Caption draft**: "The national 2024 crop-species map (1,346,582 polygons). Classified polygons coloured by predicted class (Canola/Cereal/Legume); unclassified polygons shown in grey, carrying one of five abstain reasons (Table 1)."
**Status: DONE 2026-08-30** — `output/figures/Fig04_national_map.png/.pdf`. **Two corrections found while building this**: (1) the correct source is `national_2024_crops.gpkg` (1,346,582 rows, `pred`/`abstain_reason` columns) — `national_2024_crops_classified.gpkg` is a DERIVED 650,766-row subset with abstained rows already dropped and cannot show the abstain story; using it would have silently produced a map with zero abstained polygons. (2) There are **four** abstain reasons in the data, not five: `area_below_min` (339,043), `no_crop_signal` (269,134), `unsegmented_blob` (48,016), `too_few_observations` (39,623) — verified via `GROUP BY abstain_reason`. Rendered as a 3km majority-class grid, not per-polygon vectors (paddocks are far smaller than one printed pixel at national extent) — see the script's docstring for why.

### Fig. 5 — ABS validation: composition and area-inflation
Two-panel: (a) mapped vs. ABS share by class, per SA2 (scatter, canola highlighted); (b) the "absorbed" over-call breakdown table from `ABS_COMPARISON_100km.md` as a stacked bar (ABS / diluted / mapped / absorbed, by class).
**Caption draft**: "(a) Mapped vs. ABS crop-share composition across 132 SA2s (canola highlighted; r=0.82, MAE 5.5 pts). (b) Decomposition of the area over-call by class: ABS share, the diluted share a perfect classifier would report given the over-call, the actual mapped share, and the absorbed excess — showing the over-call sits almost entirely in Cereal and Legume, not Canola."
**Status: Needed** (data exists in the ABS_COMPARISON files, needs plotting).

### Fig. 6 — Presence-gate trade-off
Grouped bar: pooled + per-crop stacked presence recall for amplitude-only vs. phenology-shape (baseline) vs. loosened-senescence vs. two-pass, from `PHENOLOGY_GATE.md`'s final comparison table. This is the figure that makes RQ3's rejection legible at a glance.
**Caption draft**: "Stacked presence recall (amplitude gate AND presence-shape gate both applied) by crop, across four gate configurations. The shipped (baseline) config trades Canola recall (78.3%) for Cereal/Legume recall unchanged from amplitude-only; two-pass gating (Canola exempted from the shape gate) restores Canola to 94.5% at no cost to the other classes but is not yet validated against the ABS area ratio."
**Status: Needed.**

### Fig. 7 — Multi-year regional evidence, with a national placeholder
Line/bar chart: year-by-year classified share and mean `ndvi_amp`, 2017-2025, 100 km Riverina box (`ABS_COMPARISON_100km.md` table) — flagging 2017/2018 as the weak years. **A second panel for the equivalent national series is reserved but left blank/marked pending** until E8 completes — do not fabricate it. **Status: Needed for the regional panel now; national panel [PENDING].**

### Fig. 8 — Yield: predicted vs. ABS-calibrated
Scatter or residual plot, predicted vs. actual Cereal yield, raw and calibrated. **Status: Needed**, from `YIELD_cereal_pooled.md` / `YIELD_CALIBRATION.md` underlying data.

---

## §14. Tables Plan

| ID | Content | Source | Status |
|---|---|---|---|
| Table 1 | Dataset/pipeline summary: tiles, polygons, area, classified %, abstain-reason breakdown (2024 national) | `NATIONAL_2024_RUN.md` | Ready to build |
| Table 2 | Classifier accuracy: macro F1, per-class precision/recall, temporal vs. spatial | `REVIEWED_MODEL.md` | Ready to build |
| Table 3 | ABS validation summary: canola r/MAE, cereal/legume shares, area ratio, ABS/ABARES floor | `ABS_COMPARISON_NATIONAL.md`, `ABS_COMPARISON_100km.md` | Ready to build |
| Table 4 | Gate comparison: pooled + per-crop stacked recall, amplitude vs. shape variants | `PHENOLOGY_GATE.md` | Ready to build |
| Table 5 | Yield model performance + calibration factor and its checked range | `YIELD_cereal_pooled.md`, `YIELD_CALIBRATION.md` | Ready to build |
| Table 6 | **National multi-year (2017-2025) summary**: total polygons/area/coverage by year | none yet | **[PENDING — E8, in progress]** |
| Table 7 *(v1.1, Discussion/Future Work, not Results)* | S1 marginal value by task: classifier (regresses), Cereal yield (improves), and Sharma6-for-canola-yield (regresses) side by side | `S1_VS_LATEST_MODEL.md`, `YIELD_cereal_pooled_ctl.md`/`_s1.md`, `CANOLA_YIELD_shipped_sharma6.md` | Ready to build |
| Table 8 *(v1.1, Discussion/Future Work, not Results — contingent on §24 Open Issue #8)* | Leading classifier candidate vs. shipped: macro F1, canola@5%FPR, feature count | `GROUP3_MODEL_shipped_plus_sharma6_VALIDATION.md` | Ready to build |

---

## §15. Related Work Synthesis

**Cluster A — Global crop-mapping infrastructure & foundation models** (WorldCereal, Presto, AlphaEarth, Esri/Impact Obs LULC). This paper relates to this cluster as a *local adaptation-and-comparison* story with a real negative result: Presto embeddings were fine-tuned on the project's own labels and lost to hand-built spectral indices at this label volume/class granularity — worth reporting as a data point against blanket "foundation models win" framing in this literature. Representative: Van Tricht et al. 2023 (WorldCereal, ESSD); Tseng et al. 2024 (Presto, arXiv 2304.14065); Brown et al. 2025 (AlphaEarth, arXiv 2507.22291).

**Cluster B — Australia-specific crop-type classification precedents.** Sharma et al. 2026 (*Remote Sensing* 18(10):1653, WA, 6 classes, DAS-derived pseudo-labels + a small field-verified test set) and Al-Shammari et al. 2024 (*RSASE* 34:101200, MDB, 2 crop classes, harvester-yield-map labels, S1+S2+MODIS fusion) are the two closest precedents. Both reach >90% accuracy but neither is continent-wide, and neither trains exclusively on field-verified ground truth — this paper's genuine methodological edge is being trained end-to-end on real recorded sowings, at the cost of coarser class resolution (3 groups, not 6). CSIRO's Graincast/ePaddocks (Lawes et al. 2021/2023) is the closest operational Australian precedent for the boundary+yield pattern, worth citing as prior art even though this project replaced ePaddocks with SAM-based segmentation.

**Cluster C — Field/paddock boundary delineation.** SAM (Kirillov et al. 2023) via the SAMGeo/PaddockTS wrapper is the actual method used, a departure from the brief's original plan (ePaddocks). Fields of the World (Kerner et al. 2024, arXiv 2409.16252) is a relevant methodological comparison point (cloud-robust S1+S2 delineation) though it does not cover Australia.

**Cluster D — Accuracy-assessment standards for crop maps.** Olofsson et al. 2014 (RSE) is the field's stated good-practice standard (stratified probability sampling, error matrices with confidence intervals) and is *not* what this paper does — it is explicitly named here so the paper's Discussion can state, rather than obscure, why an aggregate ABS-composition check is used instead (no suitable probability sample of field-verified labels exists for Australia at the needed density).

**Note on Newman & Furbank (2021, Scientific Data)** — describes the same underlying GRDC NVT trial network this paper's ground truth comes from. **This is not an independent public dataset**; per project memory, GRDC previously objected to that paper's data release on legal grounds. **RESOLVED 2026-08-29 (§24 Open Issue #2)**: the project holds a signed GRDC data-use agreement covering this publication, conditional on sending the finished manuscript to GRDC for verification before submission. Citation is permitted but must still not imply independence or point a reader toward accessing that data as a substitute.

---

## §16. Discussion Plan

1. **The central interpretive move**: the 1.47-1.59x area over-call is a presence-detection failure, not a classification failure — supported by canola-share parity once the over-call is divided out, and reproduced independently at two spatial scales (national 1.47x, 100 km regional 1.59x, same class signature both times).
2. **The phenology-gate negative result as a general caution**: a fix that is more theoretically principled (season *shape*, not just amplitude) and that succeeds on its own target metric (area ratio 1.59→1.00) can still be the wrong choice to ship, because it redistributes error onto the map's most important species. Frame as a transferable lesson for presence-gate design generally, not just this pipeline.
3. **Legume over-prediction remains open** — state plainly as the largest unresolved classification error, distinct from the presence problem, with the argmax-vs-mean-probability check ruling out the cheap explanation (decision-rule artefact).
4. **Practical implication of the abstain-reason/ndvi_amp design**: because both ship on every polygon, a downstream user can already filter toward the tighter, less-complete view if they need area-accurate rather than composition-accurate output — position this as the dataset's actual answer to the area-inflation limitation, not just a caveat.
5. **Generalizability across seasons**: discuss the regional 9-year evidence (weak years 2017/2018, driven by S2B's mid-year start and a genuine drought respectively) as a reason to expect, but not yet confirm, similar national multi-year behaviour — explicitly flag this as the open question E8 will answer.
6. **(Added v1.1) A covariate's value is task-dependent, not pipeline-dependent — a second transferable caution alongside #2.** Sentinel-1, evaluated against the current best models rather than the retired baseline, regresses the classifier (Sharma6 already fixed the confusion S1 used to fix, so S1 now only dilutes signal) but clearly improves the shipped Cereal yield model (structure/biomass signal a classifier built to separate species by phenology-shape does not need). Symmetrically, Sharma6 — which helps classification — regresses canola yield prediction. Frame this explicitly as a caution for anyone assembling a shared feature pipeline across multiple downstream tasks: validate each covariate per task, not once for "the model." Table 7 makes this legible at a glance. Note in Discussion (not Results) only — see §24 Open Issue #8 for whether the shipped+sharma6 candidate classifier itself should be adopted, which is a separate decision from this general lesson.

---

## §17. Limitations and Future Work

**Limitations (severity-ordered):**
1. **1.47-1.59x area over-call**, nationally and regionally reproduced — the map's most consequential operating characteristic. High severity, but mitigated by shipping `ndvi_amp`/`abstain_reason` per polygon.
2. **Legume misclassification**, 18.4% mapped vs. 8.7% ABS, mechanism unexplained. High severity, untouched by this round of work.
3. **`unsegmented_blob`**: 37 Mha across ~48k polygons, SAM's single largest failure mode; a size-aware second segmentation pass was never attempted. Medium severity.
4. **Single-season national coverage** (2024 only) pending the multi-year national extension — currently the paper's largest scope gap relative to its own framing as a multi-year resource. High severity until E8 lands; this plan is written to make that update mechanical once it does (§25).
5. **No canola yield, specifically because it needs Sentinel-1** — optical-only R² (0.271, spatial) loses to guessing the year and state (0.290); shipping it would be worse than the blank column. **(v1.2, 2026-09-04, re-tested and confirmed)** This is not a dead model: re-tested against the current row-matched population (`CANOLA_YIELD_s1ctl.md`/`CANOLA_YIELD_s1.md`, job 178174639), adding S1 raises spatial R² to 0.371 — clearly above baseline, matching the direction and magnitude of the original 2026-08-25 test this limitation was first based on, now confirmed current rather than carried forward unverified (the same re-test discipline `S1_VS_LATEST_MODEL.md` applied to the classifier and Cereal yield, which for the classifier reversed the old verdict — canola yield's did not reverse). Low severity as shipped (honestly disclosed, not attempted-and-hidden); the open item is now purely the same national S1 acquisition-cost question gating the Cereal yield extension (§17 future-work item 7), not a broken model.
6. **Sentinel-1 not used at scale for classification** — **superseded finding (v1.1)**: the original +0.03 macro F1 gain was measured against the retired 3-index baseline. Re-tested against the current best classifier (shipped+sharma6), S1 **regresses** macro F1 by −0.023 temporal/−0.018 spatial (Legume-concentrated) — a closed, negative case for classification, not an open one. S1 does, however, clearly improve the shipped Cereal yield model (+0.092 temporal R²) — the case for national S1 now rests entirely on yield, not classification. `S1_VS_LATEST_MODEL.md`. Severity: low for classification (closed, negative); the yield opportunity is a future-work item (#6 below), not a limitation.
7. **3 classes, not the full 10-species roster** originally proposed — a finding (9-class macro F1 0.38), not an omission, but must be stated early, not discovered by the reader in Results.
8. **(Added v1.1) The shipped classifier (macro F1 0.821/0.823, every number in this paper's Results) is not the best-performing configuration found during this project.** A leading candidate (shipped 3 indices + Sharma6's 6, macro F1 0.890/0.892, no canola-detection regression) exists but has not been independently reviewed or adopted — see §24 Open Issue #8. Medium-high severity as a disclosure item: a reviewer who finds `GROUP3_MODEL_shipped_plus_sharma6_VALIDATION.md` in the code repository without it being mentioned in the paper would reasonably ask why a better model was not used.
9. **(Added v1.1) Sharma6 indices, adopted as the leading candidate's basis for classification, regress canola yield prediction** (temporal R² 0.206→0.012) — a concrete instance of the task-dependent-covariate caution (§16 point 6). Not a limitation of the shipped map (which does not use Sharma6 or ship canola yield at all), but relevant if the candidate classifier is ever adopted alongside a future canola yield product. Low severity today, flagged for future-work coherence.

**Future work** (in priority order, from `NEXT_STEPS.md` §5, updated v1.1):
1. Complete the national 2017-2025 multi-year run (E8) — the direct next step, and this paper's own open thread. **In progress as of 2026-09-03 (2/9 years done).**
2. ~~A direct spatial comparison against NLUM (250 m) or a WorldCereal/Dynamic World-style product (E9)~~ — **DONE 2026-08-30**, see §11, §24 Open Issue #4.
3. Investigate the legume over-prediction mechanism.
4. A size-aware second SAM pass for `unsegmented_blob`.
5. Of the two untried phenology-gate refinements recorded in `PHENOLOGY_GATE.md` (looser senescence threshold; two-pass gating exempting Canola), two-pass gating is the stronger local candidate (restores Canola to 94.5% recall with zero effect on Cereal/Legume) but is **not validated against the ABS area ratio** — flag as future work, not a claim.
6. **(Added v1.1)** An independent review of the shipped+sharma6 classifier candidate (macro F1 0.890/0.892), and — contingent on that review and the user's decision (§24 Open Issue #8) — either adopt it for a re-run of the national map/ABS validation, or report it purely as a future-work direction.
7. **(Added v1.1; scope widened v1.2, 2026-09-04)** National-scale Sentinel-1 extraction for **both yield models**, not the classifier — Cereal yield gains accuracy from it (+0.092 R²); canola yield cannot ship at all without it (confirmed on re-test, §17 item 5). Gated on two unresolved items: whether the yield gain survives on ordinary commercial-paddock geometry rather than clean NVT trial paddocks (no yield-equivalent of the AgriWebb holdout exists to check this), and the still-unimplemented revisit-density covariate for the S1B multi-year discontinuity (`SENTINEL1_VALUE.md` §3.3, confirmed not built via grep).

---

## §18. Reproducibility and Open Science Plan

- **Code**: pipeline code (`src/paddocks/`) can be released; contains no site-level records.
- **GRDC/NVT trial data**: **cannot be released** (NDA-covered — see `CLAUDE.md` Sensitive Data section). The Data Availability Statement must say this explicitly, not merely omit the data.
- **Model artifacts**: `group3_map.joblib`, `cereal_yield.joblib`, and the (unused-in-production) `phenology_gate.joblib` — releasable, contain no site-level records.
- **Output map**: `national_2024_crops_classified.gpkg` (public-styled, classified-only) is releasable; the full `national_2024_crops.gpkg` should be checked for any residual site-level linkage before release (it should not contain any, but verify before publication — this is a hard NDA constraint, not a style preference).
- **Validation reference data**: ABS/ABARES statistics are already public; no release action needed.

---

## §19. Manuscript Structure Plan

RSE format: Highlights, Graphical Abstract, Abstract (~250 words), then numbered sections. No hard word cap found (§2); target ~9,000-10,000 words body text, typical for an RSE full research article.

| Section | Words (approx.) | Goal |
|---|---|---|
| Highlights (3-5 bullets, ≤85 chars each) | — | One line each for: the dataset, the area-inflation finding, the gate-rejection finding |
| Graphical Abstract | — | Pipeline schematic + example map panel (reuse Fig. 1 elements) |
| Abstract | 200-250 | See §20 |
| 1. Introduction | 800-1000 | Motivate the gap (§3-4), end with numbered contributions (§5) |
| 2. Related Work | 1300-1600 | Four clusters (§15) |
| 3. Study Area and Data | 600-800 | §7-8, Fig. 2, Table 1 |
| 4. Methods | 1600-1900 | §9, Fig. 1, Fig. 3 |
| 5. Results | 1200-1500 | §11, Fig. 4-8, Tables 2-6 (Table 6 marked pending until E8) |
| 6. Discussion | 1000-1250 *(v1.1: +100-150 for the task-dependent-covariate finding, §16 point 6, Table 7, and the candidate-model disclosure, §16/§24 #8, Table 8)* | §16 |
| 7. Limitations and Future Work | 500-700 | §17 |
| 8. Conclusion | 300-450 | Mirror contributions, restate the E8/E9 open threads |
| Data & Code Availability, CRediT, Declaration of Interests | — | §18, boilerplate |

---

## §20. Abstract Blueprint

1. **Background** (1-2 sentences): Australia's grains sector lacks a continent-wide, field-verified, paddock-scale crop-species map.
2. **Gap** (1 sentence): existing global products lack species resolution; existing Australian precedents are regional and not fully field-verified.
3. **Method** (2 sentences): SAM-based paddock segmentation + gradient-boosted spectral classifier + presence gate + calibrated Cereal yield, trained on GRDC/NVT field-verified trial labels.
4. **Data** (1 sentence): national 2024 map — 1,346,582 polygons; [PENDING: + multi-year 2017-2025 national extension, if complete by drafting time].
5. **Main results** (2-3 sentences): canola composition tracks ABS closely (r=0.82); the map over-calls area 1.47-1.59x, a presence-detection not classification problem; a more principled phenology-shape fix was tested, worked on its target metric, but broke canola recall and was rejected.
6. **Significance** (1 sentence): a validated national dataset plus a transferable caution about presence-gate design for anyone building similar maps.

---

## §21. Title and Framing Options

1. "A National, Polygon-Level Crop-Species Map of Australia from Sentinel-2: Presence-Gated Classification, Calibrated Yield, and Validation Against Official Statistics"
2. "Segmentability as a Crop-Presence Signal: A National Three-Class Crop Map of Australia and the Cost of a Stricter Presence Gate"
3. "Mapping Canola, Cereal, and Legume Paddocks Across Australia at 10 m: A Field-Verified, ABS-Validated Dataset"

Dominant framing: **applied case study / dataset-and-validation paper**, not a methods-innovation paper — the two primary contributions (§5) are the dataset itself and the (negative) presence-gate finding, not a novel algorithm.

---

## §22. Citation and Evidence Bank

- **§Intro/§Related A** (global infrastructure): Van Tricht et al. 2023 (WorldCereal, ESSD); Tseng et al. 2024 (Presto, arXiv 2304.14065); Brown et al. 2025 (AlphaEarth, arXiv 2507.22291); Karra et al. 2021 (Esri/Impact Obs LULC, IGARSS).
- **§Related B** (Australia precedents): Sharma, Eslick, Pires, Singh & Tareque 2026, *Remote Sensing* 18(10):1653, doi:10.3390/rs18101653; Al-Shammari, Fuentes, Whelan, Wang, Filippi & Bishop 2024, *RSASE* 34:101200, doi:10.1016/j.rsase.2024.101200; Lawes et al. 2021/2023 (Graincast — **[VERIFY exact citation]**, not fully resolved in `LIT_REVIEW_REPORT.md`).
- **§Related C** (segmentation): Kirillov et al. 2023 (Segment Anything — **[VERIFY exact citation]**, not in `LIT_REVIEW_REPORT.md`'s table, needs a fresh lookup); Kerner et al. 2024 (Fields of the World, arXiv 2409.16252).
- **§Related D / §Methods evaluation protocol**: Olofsson et al. 2014 (RSE — **[VERIFY exact citation]**, title/volume not captured in `LIT_REVIEW_REPORT.md`'s table, needs a fresh lookup).
- **§Methods, canola flowering signal**: Ashourloo et al. 2019 (ISPRS J. Photogramm. — **[VERIFY exact citation]**).
- **Sensitive**: Newman & Furbank 2021 (*Scientific Data*) — citation approved (§15, §24 Open Issue #2). The manuscript as a whole still requires GRDC pre-submission sign-off before it can go to any venue, independent of this citation.

**None of these citations should be typed into the manuscript from memory** — `paper-draft` must re-verify author/year/venue/DOI for each before use, per the citation rules in this skill and the paper-draft skill.

---

## §23. Writing Instructions for Downstream Agent

**Non-negotiable:**
- Never fabricate or interpolate national multi-year (2017-2025) numbers. Where a multi-year national claim would go, write `[PENDING: national 2017-2025 run, E8]` verbatim rather than a plausible-sounding placeholder number.
- Always report both raw (NVT-equivalent) and ABS-calibrated Cereal yield columns together — never only the calibrated one (this is a standing project rule, `NEXT_STEPS.md` §3).
- Always state the ABS/ABARES 6.8% mutual disagreement alongside any map-vs-ABS accuracy claim tighter than that — do not report a map error smaller than the floor as if it were precise.
- State the 3-group descoping (from the original 10-species brief) explicitly in the Introduction or Methods, not buried in Limitations — it is a finding.
- Describe the ABS validation as validation against an **independent official statistic**, never as "ground truth" or "validation accuracy" in the pixel-level sense.
- The phenology-gate result (§5, §16) is a **negative result reported honestly** — do not soften it into "future work could refine this further" language that undersells the actual finding (it was tested at regional scale and rejected on real evidence, not left untried).
- Do not name or describe GRDC/NVT site-level records (coordinates, TrialCodes, yields) anywhere in the manuscript text or figures — aggregate-only, per `CLAUDE.md`.
- Newman & Furbank may be cited (§24 Open Issue #2, resolved) — frame it as the same underlying GRDC NVT lineage, never as an independent dataset. This does not remove the standing requirement to send the finished manuscript to GRDC for sign-off before submission.
- **(Added v1.1)** Every classifier accuracy number in Results/Abstract (macro F1, confusion matrices, canola@5%FPR) describes the **shipped** model (0.821/0.823) — the one actually used to produce the 2024 national map and every figure/table in this plan. The shipped+sharma6 candidate (0.890/0.892) may be mentioned **only** in Discussion or Future Work, **always** with the "not independently reviewed, not adopted" caveat attached in the same sentence — never presented as, or substituted for, "the model's" reported performance.
- **(Added v1.1)** State Sentinel-1's value by task, never as a single verdict: it regresses the classifier (with Sharma6 in place) and improves the Cereal yield model. A sentence like "S1 was evaluated and improves the map" is false for half the pipeline — say which half.

**Section priorities if time/space is constrained**: Introduction, Methods, and the area-inflation/gate-rejection portion of Results/Discussion are the paper's actual spine — protect these first. Related Work Cluster A (foundation models) can be trimmed before Cluster B (Australia precedents) or D (validation standards), which are more load-bearing for positioning.

---

## §24. Open Issues Before Drafting

1. **Journal choice — RESOLVED 2026-08-29.** User confirmed RSE as primary target; proceed on RSE's word-budget/structure conventions.
2. **Newman & Furbank (2021, Scientific Data) citation handling — RESOLVED 2026-08-29.** User confirmed the project holds a signed data-use agreement with GRDC covering this publication, **conditional on sending the finished manuscript to GRDC for verification before submission**. Newman & Furbank may now be cited (still framed as the same underlying lineage, never as an independent dataset — §15). **Standing action item, not yet done**: the manuscript must go to GRDC for sign-off before it is submitted anywhere — carry this into `paper-review-loop`/`paper-covert`'s pre-submission checklist.
3. **National multi-year (2017-2023, 2025) run (E8) — user confirmed 2026-08-29: draft now, backfill later.** Proceed with `paper-draft` as a partial draft using `[PENDING: E8]` placeholders per §25's recommended strategy; update Results/Table 6/Fig. 7/abstract once E8 completes.
4. **NLUM/WorldCereal spatial comparison (E9) — user approved 2026-08-29; DONE 2026-08-30.** Both halves complete: `output/WORLDCEREAL_COMPARISON.md` and `output/NLUM_COMPARISON.md` (`src/paddocks/worldcereal_compare.py` / `nlum_compare.py`, 250,000-point stratified sample of national paddock centroids, seed=0, same sample both files).
   - **WorldCereal** (no Canola/Legume class, so presence + Cereal only): 73.1% presence agreement (our classified-vs-abstained against WorldCereal `temporarycrops`) — symmetric: 73.0% of our abstained points are also "no-crop" per WorldCereal, 73.2% of our classified points are also "crop." Of points we call Cereal, WorldCereal's `wintercereals` layer agrees at only 49.6% — a real, load-bearing disagreement, not noise at n=82,411. `springcereals` confirmed zero AU coverage.
   - **NLUM** (has direct oilseed/cereal/legume commodity layers, so all 3 classes checkable): built an enrichment-ratio metric (median commodity probability at our-class points ÷ at Abstained points, same commodity) because raw cross-commodity probabilities are not comparable — NLUM's cereal layer runs high everywhere. Result: Canola points show 6.4x the abstained-baseline oilseed probability, Legume 1.6x the legume probability — both correctly the largest ratio in their own column. **Independent validation of the abstain mechanism**: NLUM grazing probability is 33.8% (median) at our abstained points vs 10.8% at classified points — corroborates `NONCROP_CLASS.md`'s prior finding from a different angle.
   - Both reports carry a full caveats section (year mismatch 2021 vs 2024, sampling not census, WorldCereal-nodata handling, NLUM cross-commodity scale non-comparability) — read before citing any number in the manuscript.
   - **Not yet done**: turning these into a manuscript figure/table and folding the write-up into §11/§16/§17. That's a `paper-draft`-stage task, not part of E9 itself.
5. **Author list / affiliations** — not specified; placeholder only, per this skill's rule against generating author information.
6. **Two citations need a fresh lookup, not memory** — Segment Anything (Kirillov et al. 2023) and Olofsson et al. 2014 are referenced by name in project reports but their full citations were not captured in `LIT_REVIEW_REPORT.md`'s tables; `paper-draft` (or a quick `lit-review` follow-up) should verify both before the manuscript cites them.
7. **No external cross-review of this plan was run** (Phase 6) — Codex MCP unavailable, and a subagent review was skipped for quota reasons (§0). Recommend the user's own review substitute for it.
8. **(RESOLVED 2026-09-07 — ADOPT, independent review complete and favorable.)** After reading the Scientific Data submission PDF, the user decided the shipped+sharma6 candidate (macro F1 0.890/0.892, no canola@5%FPR regression) should become the production model, and confirmed the independent-review gate (`CLAUDE.md`'s generator-evaluator rule) should be satisfied first rather than waived. A fresh, independently-briefed reviewer (no exposure to this project's own reasoning) verified the candidate against raw evidence — full byte-for-byte reproduction of the training run, the canola@5%FPR "exact match" confirmed at full unrounded precision (0.890323 for both models, on identical held-out rows), the prior candidate's `family()` bug confirmed fixed and unable to recur here (allow-list, not drop-list), no raw-band leakage, formulas and citation both verified. **Verdict: ADOPT.** Two minor, non-blocking caveats for the record (full detail: `output/INDEPENDENT_REVIEW_shipped_sharma6.md`): (a) a loosely-worded citation in the validation report about row-identity verification — cosmetic; (b) ~20 feature/architecture combinations were scored against the same fixed 543-row test set before this one was recommended (`INDEX_ARCHITECTURE_SWEEP.md`) — an unacknowledged multiple-comparisons exposure that doesn't undermine the current numbers (the gain is large and consistent across two structurally different splits) but is worth closing with a genuinely fresh holdout before defending 0.890/0.892 to a skeptical external reviewer.

   User also confirmed 2023 and 2024 (already merged on the shipped model) will be RE-PREDICTED once the new model is in production, so the eventual national multi-year map uses one consistent classifier throughout — but explicitly asked that no prediction (or model-fitting) jobs be launched yet (concurrent large-scale compute on another project). Progress made without launching anything: `fit_map_model.py` (the actual production-fitting script — `train_species.py` only evaluates, it has no model-save path) had no way to combine `--indices` and `--bands --bands-keep-families` together; extended it to do so, mirroring `train_species.py`'s exact multi-source join logic without modifying that already-reviewed file. Verified correct via a lightweight login-node run (not a PBS job): `fitted on 2194 paddocks x 153 features` — matches the reviewed spec exactly (102 from the 6 Sharma6 families + 51 from the 3 shipped indices).

   **Done 2026-09-08 (code only, no jobs):** a second blocker was found and fixed first — `predict_tile.py` computed a single feature source, so the two-source candidate would have been scored from a half-NaN matrix with no error (HGB accepts NaN); it now runs one zonal pass per bundle source, verified on a real tile for both the old model (byte-identical to its pre-change output) and the new one (all 153 features present). The production joblib was then fitted on the full 2,194-row reviewed keep set (`derived/models/group3_map_sharma6.joblib`) and every `MODEL=` in `run_national.sh`/`run_map100.sh` now points at it; the retired `group3_map.joblib` stays on disk only until 2023/2024 are re-predicted.

   Remaining, gated on the user confirming compute is free: (1) predict 2022 (not yet predicted) and re-predict-then-remerge 2023/2024; (2) re-run the ABS validation and every Results-section number against the new model's output, since every current number in this plan and the manuscript still describes the shipped 0.821/0.823 model; (3) optionally, score the exact 153-feature configuration once against a genuinely fresh holdout per the review's caveat (b), before finalizing the number for submission.
9. **(NEW v1.1, informational, no action needed)** The original single "S1 helps" framing (§5 secondary finding #2 in v1.0, §17 limitation #6) is superseded — S1's value now splits by task (regresses classifier, improves Cereal yield). This has been folded into §5, §10, §11, §12, §16, §17 in this pass; no further open question, but double-check during `paper-draft`/`paper-review-loop` that no leftover v1.0 language still states the old single-direction story.

---

## §25. Final Readiness Assessment

**Ready for a full first-pass draft now**: Introduction, Related Work, Study Area and Data, Methods, most of Results (everything from E1-E7), Discussion, Limitations and Future Work, Conclusion (with E8/E9 stated as open threads rather than promises).

**Blocked on**:
- E8 (national multi-year run) — needed for the abstract's data-scale claim, Results Table 6, Fig. 7's national panel, and any "this generalizes nationally across seasons" language.
- GRDC pre-submission sign-off (§24 Open Issue #2) — does not block drafting, but blocks actual submission to any venue.

Open Issues #1 and #2 are resolved as of 2026-08-29: RSE confirmed as journal; Newman & Furbank citation approved under the project's signed GRDC agreement.

**Recommended drafting strategy**: proceed to `paper-figure-generate` for the 7 non-pending figures (Fig. 1-6, 8, plus Fig. 7's regional panel), then `paper-draft` for a **partial draft** covering everything not blocked, with `[PENDING: E8]` placeholders exactly where multi-year national numbers would go. This gets the manuscript to roughly 85% complete now; the remaining 15% (Results/Abstract updates, Table 6, Fig. 7's national panel) becomes a short, mechanical update pass once the national run completes — not a rewrite.

---

## §26. Executive Summary for Manuscript Writer

**What the paper is about**: a national, field-verified, polygon-level 3-class (Canola/Cereal/Legume) crop map of Australia from Sentinel-2, validated against independent ABS statistics, plus a documented, mechanistically-explained area-inflation problem and a rejected fix for it.

**Why it's publishable**: no continent-wide, field-verified-ground-truth Australian crop-species map exists in the literature; the area-inflation finding and its rejected fix are a genuine, transferable methodological result, not just a dataset release.

**Strongest evidence**: the ABS validation (independent statistic, no training-pipeline connection, r=0.82 on canola share) and the phenology-gate regional test (a real 120-SU experiment with both a positive metric — area ratio fixed — and the specific negative one — canola recall broken — from the same run).

**Weakest/most exposed evidence**: the Legume over-prediction has no explanation yet; the national multi-year story is now in progress (E8, 2/9 years done) but not complete; a leading classifier candidate outperforms the shipped model and is disclosed but not adopted (§24 Open Issue #8) — a sharp-eyed reviewer may ask why.

**What to emphasize**: the dataset's honesty machinery (abstain_reason, ndvi_amp, both yield columns) as a first-class design feature, not an apology; the phenology-gate result as a general lesson, not a footnote; **(v1.1)** the task-dependent-covariate finding (S1 helps yield, hurts classification; Sharma6 helps classification, hurts canola yield) as a second general lesson of the same character.

**What to be careful about**: never imply national multi-year validation before E8 completes; never cite Newman & Furbank without the user's explicit sign-off; never describe the ABS check as ground-truth-level accuracy; keep the 3-group descoping visible early rather than discovered late; **(v1.1)** never quote the shipped+sharma6 candidate's 0.890/0.892 as "the model's" accuracy — every Results number is the shipped 0.821/0.823 model; never state S1's value as a single unqualified verdict — it splits by task.

---

## Figure & Table Plan (consolidated)

| ID | Type | Description | Data Source | Priority | Status |
|----|------|-------------|-------------|----------|--------|
| Fig 1 | Hero/schematic + map | Pipeline overview + example output panel | `derived/map100/pred/` or national gpkg | HIGH | Needed |
| Fig 2 | Map | Study area: national extent + 100km box + validation SA2s | GIS boundaries | HIGH | Needed |
| Fig 3 | Confusion matrix | Classifier accuracy, temporal + spatial | `output/figures/confusion_group3_reviewed.png` | HIGH | Ready (verify numbers) |
| Fig 4 | Map | National 2024 classified map, full continent | `national_2024_crops_classified.gpkg` | HIGH | Needed |
| Fig 5 | Scatter + stacked bar | ABS composition validation + area-inflation breakdown | `ABS_COMPARISON_NATIONAL.md`, `ABS_COMPARISON_100km.md` | HIGH | Needed |
| Fig 6 | Grouped bar | Presence-gate trade-off (amplitude vs. shape variants) | `PHENOLOGY_GATE.md` | HIGH | Needed |
| Fig 7 | Line/bar + PENDING panel | 9-yr regional coverage/ndvi_amp by year; national panel reserved | `ABS_COMPARISON_100km.md` (+ E8 pending) | MEDIUM | Needed (regional); PENDING (national) |
| Fig 8 | Scatter/residual | Yield: predicted vs. ABS-calibrated | `YIELD_cereal_pooled.md` | MEDIUM | Needed |
| Table 1 | Summary | Dataset/pipeline summary, 2024 national | `NATIONAL_2024_RUN.md` | HIGH | Ready to build |
| Table 2 | Comparison | Classifier accuracy | `REVIEWED_MODEL.md` | HIGH | Ready to build |
| Table 3 | Comparison | ABS validation summary | `ABS_COMPARISON_NATIONAL.md` | HIGH | Ready to build |
| Table 4 | Comparison | Gate comparison, recall by config/crop | `PHENOLOGY_GATE.md` | HIGH | Ready to build |
| Table 5 | Summary | Yield model + calibration | `YIELD_cereal_pooled.md` | MEDIUM | Ready to build |
| Table 6 | Summary | National multi-year totals by year | none yet | MEDIUM | **PENDING (E8, in progress)** |
| Table 7 | Comparison | S1 marginal value by task (classifier/Cereal yield/canola yield) | `S1_VS_LATEST_MODEL.md` + yield reports | MEDIUM | Ready to build (Discussion) |
| Table 8 | Comparison | Leading classifier candidate vs. shipped | `GROUP3_MODEL_shipped_plus_sharma6_VALIDATION.md` | MEDIUM | Ready to build (Discussion, contingent on §24 #8) |

---

## Citation Plan

- §Intro: Van Tricht et al. 2023 (WorldCereal); Sharma et al. 2026; Al-Shammari et al. 2024 (problem motivation, closest precedents)
- §Related-A: Van Tricht et al. 2023; Tseng et al. 2024 (Presto); Brown et al. 2025 (AlphaEarth); Karra et al. 2021
- §Related-B: Sharma et al. 2026; Al-Shammari et al. 2024; Lawes et al. 2021/2023 [VERIFY]
- §Related-C: Kirillov et al. 2023 (SAM) [VERIFY]; Kerner et al. 2024 (Fields of the World)
- §Related-D / §Methods: Olofsson et al. 2014 [VERIFY]
- §Methods (flowering signal): Ashourloo et al. 2019 [VERIFY]
- **Excluded pending user decision**: Newman & Furbank 2021

---

**Status update 2026-08-30**: `paper-figure-generate` (8/8 figures done) and `paper-draft` (partial draft, 9,237 words, `output/manuscript/MANUSCRIPT_DRAFT.md`) are both complete. E8 remains deliberately deferred pending a colleague discussion of validation methodology and the consensus/multi-year regional approach — see `output/manuscript/DRAFT_README.md` for full status and next actions. `paper-review-loop` has not yet been run.

**Status update 2026-09-03 (v1.1)**: this plan updated in place to fold in five post-draft findings (§0). E8 is now in progress in a parallel session (2/9 national years done). Next in this session: re-run `paper-draft` to fold these findings into `output/manuscript/MANUSCRIPT_DRAFT.md` (currently still v1.0/pre-findings), then `paper-review-loop` and `paper-covert` — with the explicit understanding that both will be re-run again once E8 completes and Open Issue #8 (candidate-model adoption) is resolved.

*End of PAPER_PLAN.md.*
