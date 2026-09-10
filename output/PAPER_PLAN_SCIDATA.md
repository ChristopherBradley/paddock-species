# PAPER_PLAN_SCIDATA.md — paddock-species (Data Descriptor track)

**This is a separate plan for a separate submission.** It does not replace, supersede, or get consumed by `output/PAPER_PLAN.md` (the existing Remote Sensing of Environment research-paper plan, v1.1, already through `paper-review-loop` and `paper-covert`). The two plans target the same underlying project but different venues with materially different manuscript conventions, and downstream `paper-draft`/`paper-review-loop`/`paper-covert` runs must be told explicitly which plan file to read.

## §0. Document Status

- **Version**: 1.0 (first pass, not yet reviewed by the user)
- **Date**: 2026-09-04
- **Target venue**: **Nature *Scientific Data***, Springer Nature — see §2. **Backup: *Earth System Science Data* (ESSD)**, Copernicus/EGU.
- **Manuscript type**: Data Descriptor (Scientific Data) / Data Description article (ESSD) — a dataset-description track, **not** a research-findings track. This is the single biggest structural difference from `output/PAPER_PLAN.md`'s RSE plan and drives nearly every section below.
- **Readiness level**: **Partial draft** — see §25. Same live blockers as the RSE plan: the national 2017-2025 multi-year run (E8) is in progress in a parallel session (2 of 9 years done as of 2026-09-04); `PAPER_PLAN.md` §24 Open Issue #8 (whether to adopt a leading, not-yet-independently-reviewed classifier candidate) is unresolved. Neither is resolved here either — carried through unchanged.
- **Input files consumed**: `output/PAPER_PLAN.md` (v1.1, full — the richest single source of this project's claims, evidence, figures, and citations), `output/manuscript/MANUSCRIPT_DRAFT.md` (RSE prose, for exact numbers and phrasing, not for section structure), `output/figures/FIGURE_MANIFEST.md`, `output/figures/FIGURE_CAPTIONS.md`, `output/manuscript/CLAIM_SUPPORT_MAP.md`, `output/EXPERIMENT_PLAN.md`, `output/EXPERIMENT_TRACKER.md`. WebSearch used to verify Scientific Data's Data Descriptor requirements (abstract ≤170 words, Background & Summary ≤700 words, no new-scientific-findings claims — confirmed current via a fresh search, not just carried over from the RSE plan's earlier research) and ESSD's Data Description article requirements (not previously researched in this project — see §2).
- **Missing inputs**: same as the RSE plan — `RESEARCH_PLAN.md`, `output/refine-logs/FINAL_PROPOSAL.md`, `output/EXPERIMENT_RESULT.md`, `output/AUTO_REVIEW_REPORT.md` never existed for this project (it never ran the standard idea→refine→experiment-design pipeline). None block planning.
- **Not run this pass**: Phase 6 external cross-review (Codex MCP unavailable in this environment, same as every prior planning pass in this project).
- **Relationship to the RSE plan**: this is not a copy-and-relabel. Scientific Data's Data Descriptor format has one non-negotiable constraint the RSE plan does not: *the Abstract must not claim new scientific findings*. Concretely, four things that are headline "findings" in the RSE plan/manuscript become **method-selection justification** or **technical-validation reporting** here instead:
  1. The phenology-shape presence-gate test (RSE: a rejected fix, reported as a transferable methodological caution) → here: the reasoning behind choosing the shipped amplitude-only presence gate, told in Methods as a design decision with the recall numbers as its justification, not as a standalone finding with its own Discussion section.
  2. The Presto-vs-hand-built-features comparison (RSE: a "negative result... against unconditional foundation-model-superiority claims in the literature") → here: justification in Methods for why hand-built spectral indices were used as the feature set, told as an ablation supporting a design choice, not as a literature-positioning result.
  3. The Sentinel-1 task-split finding (RSE: a new v1.1 Discussion point, "a covariate's value is task-dependent") → here: a brief Methods/Usage Notes note that Sentinel-1 was evaluated and excluded from the shipped classifier (regresses accuracy) but is not yet included for either yield model, pending the same unresolved national acquisition-cost question — reported as a design/inclusion decision, not as a generalizable methodological lesson. **(v1.1, 2026-09-04)** This note now needs to say why canola yield is not shipped at all, not just why it lacks S1: re-tested against the current row-matched population, canola yield without S1 (spatial R² 0.271) does not clear the trivial year+state baseline (0.290), while canola yield with S1 does (0.371) — so unlike Cereal yield, which ships regardless of S1 status, canola yield's absence from this dataset and its S1 dependency are the same fact, not two separate points.
  4. The 69.7% label-co-location / 3-group descoping finding (RSE: reported as a finding about label-volume requirements) → here: Methods justification for the label-matching and class-collapsing procedure.
  The area-inflation diagnosis (presence-detection vs. classification problem) and the ABS/WorldCereal/NLUM validation numbers **do carry over substantively**, because Technical Validation is exactly where a Data Descriptor is expected to report exactly this kind of data-quality assessment — see §11 and §16 below for how the framing differs even though the underlying numbers do not.

---

## §1. One-Paragraph Summary

This paper describes a national, polygon-level, three-class (Canola/Cereal/Legume) crop-species dataset for Australia at 10 m resolution — the data product, not a scientific claim about crop mapping methodology — built from open Sentinel-2 imagery and field-verified GRDC/National Variety Trial ground truth, segmented with the Segment Anything Model, classified with a gradient-boosted spectral-index model, gated for crop presence, and attributed with a calibrated Cereal-yield estimate. Every polygon carries either a predicted class or one of four explicit abstain reasons, a confidence score, and (for Cereal) both raw and ABS-calibrated yield — the dataset is designed to be usable, and its own uncertainty legible, without a downstream user needing to re-derive it. Technical validation against independent Australian Bureau of Statistics sown-area statistics (no connection to the training pipeline) across 133 SA2s shows canola composition tracks the official statistic closely (r = 0.82) while total mapped area is inflated relative to ABS by 1.47-1.59x, a documented and quantified limitation concentrated in the Cereal and Legume classes; independent spatial comparison against WorldCereal and the National Land Use Map corroborates the same pattern from unrelated data. One national season (2024, 1,346,582 polygons) is released now; a nine-year regional (100 km) companion product demonstrates the same pipeline's multi-year behaviour; **the full national 2017-2025 multi-year extension is in progress and will be added as a data update once complete**.

---

## §2. Target Journal Strategy

**Primary target: Nature *Scientific Data*.** Verified via WebSearch (2026-09-04, current): Data Descriptor articles use a fixed structure — Abstract (**≤170 words**, must not claim new scientific findings), Background & Summary (**≤700 words**), Methods (unlimited length), Data Records, Technical Validation, Usage Notes, Code Availability, Author Contributions, Competing Interests, Figures, Tables, References. "Data Descriptors provide detailed descriptions of research datasets, including the methods used to collect the data and technical analyses supporting the quality of the measurements, and they focus on helping others reuse data, rather than testing hypotheses, or presenting new interpretations, methods or in-depth analyses." This is a close structural and philosophical match for what this project actually has: a validated, reusable national dataset with known, quantified limitations — not primarily a novel-algorithm paper (which is also true of the RSE framing, but Scientific Data's format fits it more literally, at the cost of not being able to foreground the phenology-gate and S1 findings as their own contributions the way RSE allows).

**Why try this now, as its own primary target, rather than leave it as the RSE plan's noted fallback** (`PAPER_PLAN.md` §2, §24 Open Issue #1): the RSE plan itself flagged this trade-off when it was first weighed — "this is the better structural fit if RSE reviewers push back on 'not enough of a single novel algorithmic contribution.'" Building the Scientific Data draft now, rather than waiting for that specific rejection signal, means the project has a ready-to-go alternative submission if RSE review goes that way, without a from-scratch rewrite under time pressure. It also matches this project's own actual center of gravity: the single strongest, best-supported claim in the whole project is the dataset's validation against an independent statistic (r=0.82, ABS/WorldCereal/NLUM triangulation) — exactly Scientific Data's evaluation axis ("reusability... validated against independent reference data"), whereas the phenology-gate and S1 findings, however genuine, are secondary by the RSE plan's own §5 framing.

**Backup: *Earth System Science Data* (ESSD), Copernicus/EGU.** Verified via WebSearch (2026-09-04, not previously researched in this project): ESSD's "Data Description" article type is explicitly for presenting original research data, with a required structure — Title page, Abstract, Introduction, numbered body sections (max 3 levels), **Data availability**, **Code availability**, Conclusions, Appendices, Author contribution, Competing interests, Acknowledgements, References. No stated overall word/abstract limit (unlike Scientific Data's hard caps), but explicitly states "extensive analysis and interpretation of data is considered out of scope" for this article type — the same underlying constraint as Scientific Data's "no new scientific findings," reached from a different angle (Scientific Data restricts the Abstract; ESSD restricts the whole article's interpretive depth). ESSD explicitly requires "a dedicated section on uncertainty and its evaluation" and evaluates submissions on **reusability**, specifically "validating data against independent reference data or... a plausibility assessment" — again, precisely the ABS/WorldCereal/NLUM validation this project already has. ESSD is also a strong precedent fit: it is the journal WorldCereal itself was published in (Van Tricht et al., 2023, already cited in the RSE Related Work), so an ESSD reviewer pool is already primed for exactly this kind of dataset.

**Practical consequence for drafting** (§19): because both venues converge on the same constraint (report the data and validate it; do not present interpretive findings as the headline), **one manuscript, built primarily to Scientific Data's stricter structure, converts to ESSD with mostly a section-relabelling pass** (Background & Summary → Introduction; Technical Validation content redistributes into ESSD's flexible numbered body sections; add a Conclusions section ESSD requires but Scientific Data does not use) rather than a substantive rewrite. This plan is written with that conversion path in mind — see §19's explicit mapping table.

---

## §3. Research Context and Motivation *(compressed — feeds a 700-word Background & Summary, not a full Introduction)*

Australia's grains sector has no continent-wide, field-verified, species-resolved crop map publicly available at paddock scale; existing global crop-mapping products (WorldCereal, Esri/Impact Observatory LULC) classify cropland generically or at coarse crop-type resolution and are not built for the Southern Hemisphere canola-and-pulse rotation system Australia's grains sector actually runs. The two closest Australian precedents (Sharma et al., 2026; Al-Shammari et al., 2024) are both regional and both train on model-derived or opportunistic labels rather than field-verified ground truth. This dataset closes that specific gap: it is continent-wide, trains exclusively on GRDC National Variety Trial records (genuine field-recorded sowings), and validates against an independent official statistic with no connection to the training pipeline. Unlike the RSE plan's §3-4 (which spends ~900 words building this into a positioned research contribution against five ranked literature gaps), the Background & Summary here should motivate the dataset's *existence and reuse value* in 2-3 tight paragraphs, not argue a novelty case — save the space for what Scientific Data readers actually come for: what the data is, how good it is, and how to use it.

---

## §4. Research Gap → reframed as "Why this dataset, not this study"

Not a separate section in the Data Descriptor structure — fold directly into §3/Background & Summary above. The RSE plan's five-gap literature analysis (`PAPER_PLAN.md` §4) is available as source material for Methods' brief related-context framing, but a Data Descriptor does not carry a dedicated gap-argument section the way a research article does — keep this to at most one sentence in Background & Summary ("no continent-wide, field-verified, paddock-scale, species-resolved crop dataset for Australia currently exists") and let Technical Validation carry the actual evidence for why this one is trustworthy.

---

## §5. Novelty and Contributions → reframed as "What this dataset provides" (no novelty-claim language)

**What Scientific Data's Abstract and Background & Summary may state**: this is a national, polygon-level, three-class crop-species dataset for Australia at 10 m, with per-polygon confidence and abstain-reason fields, and a calibrated Cereal-yield attribute, validated against an independent official statistic. That is a description of the artifact, not a claim of scientific novelty — safe under the "no new scientific findings" rule.

**What must NOT appear in the Abstract or Background & Summary** (must be pushed to Methods/Technical Validation/Usage Notes instead, per §0's reframing table):
1. The phenology-gate rejection as a "transferable methodological caution."
2. The Presto negative result as a claim "against unconditional foundation-model-superiority claims in the literature."
3. The S1 task-dependent-covariate framing as a general lesson.
4. Any claim that the area-inflation diagnosis is itself a *finding* about presence-only crop mapping generally, rather than a *property of this specific dataset* being disclosed to its users.

**Where the substance still lives**: Methods (design decisions 1-3, told as justified choices) and Technical Validation (the area-inflation diagnosis, told as a quantified, disclosed data-quality characteristic — see §11, §16).

---

## §6. Research Questions and Hypotheses → not applicable in this form

Data Descriptors do not carry a Research Questions/Hypotheses section — this is a hallmark of the "not testing hypotheses" framing Scientific Data's own guidance states directly. The RSE plan's RQ1-RQ4 (`PAPER_PLAN.md` §6) remain useful *internally*, as a checklist for what Technical Validation needs to cover (does composition match ABS? is the disagreement presence or classification? does a stricter gate help without cost?), but they should not appear in the manuscript as framed questions. Fold their answers directly into Technical Validation as reported validation results instead.

---

## §7. Study Scope and Boundaries

Identical underlying scope to the RSE plan (`PAPER_PLAN.md` §7) — same spatial extent (continent-wide 2024 national run, 100 km Riverina 9-year regional companion), same temporal scope (2024 national; 2017-2025 regional; national 2017-2025 extension **[PENDING: E8]**), same 3-group species scope (Canola/Cereal/Legume, not the original ~10-species brief), same method scope (crop presence + 3-class classification + Cereal-only calibrated yield, no canola yield). State the 3-group descoping in Methods as a label-volume-driven design decision (per §0 reframing #4), not as a "finding" the way RSE's §7 does.

---

## §8. Data and Materials

Same datasets as `PAPER_PLAN.md` §8 (Sentinel-2 via DEA ARD, GRDC/NVT trial network, ABS sown-area statistics, ABARES, NLUM v7 250 m, SAM). **This section carries more direct weight here than in the RSE plan**: Data Descriptor readers use this table (and the forthcoming Data Records section) as the primary orientation to the dataset, not as background before a Results section. Preprocessing detail (5-300 ha + compactness ≤8 mask, 51 paddock-median spectral features, DOY-binned) stays in Methods as usual.

---

## §9. Methodological Plan

Same seven-step pipeline as `PAPER_PLAN.md` §9 (segmentation, labelling, classification, presence gating, yield, validation protocol, multi-year check), **plus** the four reframed justification blocks from §0 folded in as their natural Methods subsections rather than isolated as Discussion:

1. Segmentation (SAM, `vit_h`, stock parameters; re-tuning investigated and ruled out as not cost-effective — one sentence, not a Discussion section).
2. Labelling, including the two independent justifications for the 3-group collapse (§0 reframing #4), both stated together — reviewers will ask "why not species-level" and the Methods section should answer it directly rather than requiring a hunt through Background & Summary: (a) label-conflict resolution — "69.7% of training trials share a segmented paddock with another NVT trial; collapsing 9 species to 3 broad groups resolves 69% of these conflicts"; (b) label-volume/accuracy — "a nine-species classifier trained on the same field-verified label pool reached only macro F1 0.38, versus the three-group scheme's 0.82 on the same population" — the two justifications are separable (conflict resolution follows from fewer classes regardless of accuracy; the accuracy gap is a direct consequence of per-class label volume) but both point to the same design, which is why it was adopted rather than treated as a fallback.
3. Classification: `HistGradientBoostingClassifier` on 51 hand-built spectral features. **Feature-set justification** (§0 reframing #2): fine-tuned Presto embeddings were evaluated and scored lower (macro F1 0.775 vs. 0.821) at this label volume and were not adopted; reported here as why the shipped model uses hand-built indices, not as a literature-positioning result.
4. Presence gating: amplitude-only gate shipped. **Gate-design justification** (§0 reframing #1): a phenology-shape alternative was evaluated and specifically improved the area-ratio metric but reduced Canola presence recall from 94.5% to 78.3%; the amplitude-only gate was retained for that reason. Reported as why the shipped gate is amplitude-only, not as a standalone rejected-fix narrative with its own general lesson.
5. Yield: `HistGradientBoostingRegressor`, Cereal only, ABS-calibrated. No canola yield is shipped — see Data Records/Technical Validation for why. **Covariate-inclusion note** (§0 reframing #3): Sentinel-1 was evaluated for the classifier (regresses accuracy, not included), the Cereal yield model (improves R² by +0.09, not yet included pending a national acquisition-cost assessment still in progress), and canola yield (required, not optional: spatial R² 0.271 without S1 vs. 0.290 baseline, 0.371 with S1 — canola yield is absent from this dataset specifically because Sentinel-1 is not yet in the pipeline, confirmed on re-test against the current row-matched population, `CANOLA_YIELD_s1ctl.md`/`CANOLA_YIELD_s1.md`) — stated as current inclusion/exclusion status, not as a generalizable "covariate value is task-dependent" lesson.
6. Validation protocol: aggregate ABS composition/area comparison, argmax-vs-mean-probability check, sensitivity table (explicitly not a fitting procedure).
7. Multi-year regional check: 9-year (2017-2025) Riverina re-run for geometric stability and coverage. National-scale re-run **[PENDING: E8]**.

---

## §10. Experiments → reframed as "Validation Procedures" (feeds Technical Validation, not a standalone section)

Same seven completed procedures as `PAPER_PLAN.md` §10 (E1-E7, E9), all **Done**, reframed here as validation steps rather than "experiments" in the hypothesis-testing sense — this is purely a labeling change, the underlying work is identical:

| ID | Validation procedure | Status |
|---|---|---|
| V1 | Classifier accuracy, temporal + spatial transfer | Done |
| V2 | Presence-gate design + held-out recall | Done |
| V3 | National 2024 map generation + ABS validation | Done |
| V4 | Phenology-shape gate evaluation (alternative considered, not adopted) | Done |
| V5 | Sentinel-1 marginal-value evaluation (classifier + yield) | Done |
| V6 | Cereal yield model + ABS calibration | Done |
| V7 | 9-year regional polygon geometric stability | Done |
| V8 | Spatial comparison against NLUM / WorldCereal | Done |
| V9 | National multi-year extension | **[PENDING — E8, in progress, 2/9 years done]** |
| V10 | Independent review of the leading classifier-candidate feature set | **Not started — `PAPER_PLAN.md` §24 Open Issue #8, unresolved. This dataset's Data Records/Methods describe the SHIPPED model only; the candidate is not adopted and is not otherwise mentioned in this Data Descriptor** (see §24 below — narrower treatment than the RSE plan's, since a Data Descriptor has no Discussion section to disclose it in; see the explicit decision in §24). |

---

## §11. Results Summary → reframed as Technical Validation content (data-quality reporting, not findings)

**This is the section where the RSE plan's Results content most directly carries over** — Technical Validation is *for* exactly this kind of reporting. The framing shift is tone and structure, not substance: report each number as evidence of data quality/limitation, not as an argued scientific result.

- Dataset scale: 1,346,582 polygons, 2.8 GB, 99,465 tiles (98.9% of national coverage), 2024. 48.4% of polygons (34.4% of area) carry a classification; the rest carry a specific, disclosed abstain reason.
- Classifier accuracy (reported as data-quality evidence, not a headline result): macro F1 0.821 (temporal) / 0.823 (spatial); Canola recall 89.0% @ 5% FPR.
- **Composition validation** (the dataset's strongest reusability evidence): canola share vs. ABS, r = 0.82, MAE 5.5 points, n=133 SA2s.
- **Area-ratio limitation, quantified and disclosed** (not framed as "a presence-detection failure, not a classification failure" the way RSE's central interpretive move does — framed instead as: "users should be aware the dataset over-calls crop-present area by 1.47-1.59x relative to ABS, concentrated in Cereal and Legume; the `abstain_reason` and `ndvi_amp` fields let users filter toward a stricter, more area-accurate subset if needed" — a Usage Notes-flavoured disclosure, cross-referenced from Technical Validation).
- Legume-class discrepancy: 18.4% mapped vs. 8.7% ABS, argmax=mean-probability (rules out a decision-rule artefact) — reported as an open, disclosed data-quality caveat, mechanism unexplained.
- Independent spatial corroboration: WorldCereal presence agreement 73.1%; NLUM enrichment ratios (Canola 6.4x, Legume 1.6x) and grazing-probability corroboration of the abstain mechanism (33.8% vs 10.8%).
- Cereal yield: spatial RMSE 1.21 t/ha; ABS calibration factor 0.6248, checked +3.1%/+18.1% on two held-out years.
- 9-year regional stability: median IoU 0.84, found in 7/9 years; 2017/2018 flagged as structurally weaker seasons (lower classified share, lower `ndvi_amp`) — reported as evidence about the underlying imagery/pipeline's temporal behaviour, relevant to a user deciding whether to trust a single season.

**[PENDING — E8]**: national multi-year totals/trends — not fabricated, marked exactly as in the RSE plan.

---

## §12. Claim-to-Evidence Map

Same underlying evidence sources as `PAPER_PLAN.md` §12 — not re-listing every row here (see that file; every source path is identical). The only change for this plan: **every row's "claim" column should be read as a "data-quality assertion," and §23's writing instructions must enforce that no row is worded as a scientific finding in the Abstract/Background & Summary.** Two rows do NOT carry over into this manuscript in any form:
- The 19-index/candidate-model exploration numbers (0.890/0.892) — see §24, deliberately excluded from this Data Descriptor entirely, not just softened.
- The general "covariate value is task-dependent" framing — the underlying S1 numbers carry over (§9 point 5), the generalizable-lesson framing does not (no Discussion section exists to host it).

---

## §13. Figures Plan

**Reuse the existing 8 figures — do not regenerate.** `output/figures/FIGURE_MANIFEST.md` confirms 8/8 DONE, exactly matching Scientific Data's own soft convention (most Data Descriptors run 4-8 figures) and comfortably inside ESSD's (no hard cap, but individual files <5 MB — the existing PDFs/PNGs already satisfy this). Captions from `output/figures/FIGURE_CAPTIONS.md` are reusable near-verbatim; only light rewording needed to strip "finding"-flavoured language from Fig. 6's caption specifically (see below), everything else is descriptive as-is.

| Fig | RSE placement | Scientific Data placement | Caption change needed? |
|---|---|---|---|
| Fig 1 (hero: pipeline + example map) | Methods (start) | Methods (start) | No |
| Fig 2 (study area) | Study Area/Data | Data Records | No |
| Fig 3 (confusion matrices) | Results §5.1 | Technical Validation | No |
| Fig 4 (national map) | Results §5.2 | Data Records or Technical Validation | No |
| Fig 5 (ABS validation) | Results §5.2 | Technical Validation | No |
| Fig 6 (presence-gate trade-off) | Results §5.4 / Discussion §6.2 | Methods (as the gate-design justification evidence, §9 point 4) | **Yes, minor**: RSE's caption implies a rejected-fix narrative ("the shipped (baseline) configuration trades Canola recall..."); reword to plain comparison framing ("presence recall by crop across gate configurations; the amplitude-only configuration was selected for the shipped dataset based on this comparison") — same numbers, method-justification tone instead of results-narrative tone. |
| Fig 7 (multi-year regional + reserved national panel) | Results §5.6 | Technical Validation | No — `[PENDING: E8]` panel (b) stays reserved exactly as in the RSE version. |
| Fig 8 (yield calibration) | Results §5.7 | Technical Validation | No |

**MAX_FIGURES**: Scientific Data has no hard published cap (typical range 4-8, this project's 8 is at the high end but justified — confirm during `paper-review-loop` for this plan whether any figure should move to a table or supplement if editorial feedback asks for fewer). ESSD has no cap at all beyond file-size limits (5 MB/figure, 30 MB total submission).

---

## §14. Tables Plan

Same six tables already built for the RSE manuscript (`output/manuscript/MANUSCRIPT_DRAFT.md` Tables 1-6, plus Tables 7-8 added in `paper-review-loop` round 1) are reusable as source data, but **Tables 7-8 (S1/Sharma6 marginal value by task; leading-candidate-vs-shipped comparison) should NOT be reused in this Data Descriptor** — they are exactly the "candidate model" and "task-dependent covariate lesson" content §0 and §24 exclude here. Tables 1-6 carry over (dataset/pipeline summary, classifier accuracy, ABS validation summary, gate comparison, yield model, national multi-year summary [PENDING]) — all within Scientific Data's ≤10-table limit and ESSD's uncapped allowance.

| ID | Content | Placement (Scientific Data) | Status |
|---|---|---|---|
| Table 1 | Dataset/pipeline summary | Data Records | Ready (reuse from RSE manuscript) |
| Table 2 | Classifier accuracy by class/split | Technical Validation | Ready (reuse) |
| Table 3 | ABS validation summary | Technical Validation | Ready (reuse) |
| Table 4 | Gate comparison | Methods (justification for gate choice) | Ready (reuse, reworded per §13) |
| Table 5 | Yield model + calibration | Technical Validation | Ready (reuse) |
| Table 6 | National multi-year summary | Technical Validation | **[PENDING — E8]** |

---

## §15. Related Work Synthesis → compressed into Background & Summary + brief Methods context, no standalone Related Work section

Data Descriptors do not carry a Related Work section. The RSE plan's four clusters (`PAPER_PLAN.md` §15) remain the source of truth for the handful of citations Background & Summary needs (WorldCereal, the two closest Australian precedents, SAM) — see §22. Do not attempt to reproduce RSE's full cluster-by-cluster literature engagement; a Data Descriptor reader expects at most a short paragraph of context, not a positioned literature review.

---

## §16. Discussion Plan → does not exist as a section; redistributed into Technical Validation + Usage Notes

This is the largest structural departure from the RSE plan. Scientific Data's format has **no Discussion section**. Everything RSE's §16 covers gets redistributed:

1. **The presence-detection-vs-classification diagnosis** (RSE Discussion §6.1) → Technical Validation, stated as an evidence-based data-quality characterization (three convergent lines of evidence: composition-vs-area pattern, cross-scale reproduction, WorldCereal/NLUM corroboration), not as "the central interpretive result of the paper."
2. **The phenology-gate result as a general caution** (RSE Discussion §6.2) → Methods, as design justification only (§9 point 4). The "transferable caution for presence-gate design generally" framing is dropped entirely — a Data Descriptor doesn't argue general methodological lessons.
3. **The Presto negative result** (RSE Discussion §6.3) → Methods, as feature-set justification only (§9 point 3).
4. **The abstain-reason/confidence design as the map's answer to area inflation** (RSE Discussion §6.4) → Usage Notes, almost unchanged — this is exactly what Usage Notes is for (telling a downstream user how to work with the data's known limitations).
5. **The task-dependent-covariate finding** (RSE Discussion §6.5, v1.1) → Methods, as the S1 inclusion/exclusion status note only (§9 point 5). The general "a covariate's value is task-dependent" lesson is dropped.
6. **Generalizability across seasons** (RSE Discussion §6.6) → Technical Validation, reported as the regional 9-year evidence bearing on how much a single national season should be trusted — factual, not argued.
7. **The Legume classification error** (RSE Discussion §6.7, added in `paper-review-loop` round 1) → Technical Validation, stated as an open, quantified limitation (exactly as it already is in the RSE Limitations section) — no change needed beyond section placement.

---

## §17. Limitations and Future Work → becomes part of Technical Validation (severity-ordered disclosure) + Usage Notes (practical guidance); "Future Work" itself is atypical for a Data Descriptor

Data Descriptors do not have a "Future Work" section in the research-article sense (a Data Descriptor's dataset either is or isn't updated later — Scientific Data allows a brief note on planned updates, not a future-research agenda). Recommended handling:

**Limitations (fold into Technical Validation, same severity order as `PAPER_PLAN.md` §17, reworded as disclosed data characteristics, not research shortcomings):**
1. Area over-call (1.47-1.59x) — highest severity, already covered in §11/§16 point 1.
2. Legume misclassification (18.4% vs 8.7% ABS) — covered in §16 point 7.
3. `unsegmented_blob` (37 Mha, ~48k polygons) — SAM's largest single failure mode; state as a known data gap.
4. Single-season national coverage (2024 only) pending the multi-year extension — **the single most important "planned update" note for Scientific Data's allowed brief mention**: "A national multi-year extension (2017-2023, 2025) is in progress and will be released as a dataset update" — this is squarely appropriate Data Descriptor content, unlike the RSE-style "this paper's own open thread" framing.
5. No canola yield — state plainly that this is specifically because it needs Sentinel-1, which is not yet in the shipped pipeline (spatial R² 0.271 optical-only vs. 0.290 baseline vs. 0.371 with S1, confirmed on re-test 2026-09-04) — consistent with the RSE version, updated the same way.
6. Sentinel-1 not included — covered in §9 point 5, cross-reference from Usage Notes.
7. 3 classes, not the full 10-species roster — covered in §9 point 2.

**"Future work" → recast as "Planned updates" (a legitimate, narrow Scientific Data convention)**: (a) the national multi-year extension (in progress); (b) nothing else should be promised here — Scientific Data Data Descriptors do not carry a research future-work agenda (the phenology-gate refinements, Legume-mechanism investigation, etc. are RSE-appropriate future-research directions, not Scientific Data-appropriate planned-dataset-update items — omit them from this manuscript, they belong to the RSE paper's Future Work section only).

---

## §18. Reproducibility and Open Science Plan

Identical to `PAPER_PLAN.md` §18 in substance (code releasable, GRDC/NVT trial data cannot be released per the data-use agreement, model artifacts releasable, output map releasable with a site-level-linkage check first) — **but this content is far more load-bearing here**: Scientific Data requires a dedicated **Data Availability** statement with a persistent identifier (DOI) for the dataset itself, and a separate **Code Availability** statement, both as named top-level sections (not folded into a general "Reproducibility" discussion the way a research article can). ESSD requires the same two as named sections too. **Action item before drafting**: the dataset needs an actual deposit + DOI (e.g., Zenodo, Figshare, or a domain repository) before this manuscript can state a real identifier — currently a placeholder gap, flag in §24.

---

## §19. Manuscript Structure Plan

**Primary structure (Scientific Data Data Descriptor)**:

| Section | Word budget | Maps from (RSE plan) |
|---|---|---|
| Title | — | §21, Option 1 below |
| Abstract | **≤170** (hard limit) | Compressed from RSE Abstract; no findings language |
| Background & Summary | **≤700** (hard limit) | Compressed RSE Introduction (§3-4), ~1/3 length |
| Methods | ~2,800-3,200 (unlimited, but keep tight) | RSE Methodology (§9) + reframed Discussion content (§0 reframing #1-4) |
| Data Records | ~700-900 (new — not present in the RSE plan in this form) | RSE Study Area/Data (§8) + Table 1 + national map structure/schema detail not previously written up as its own section |
| Technical Validation | ~1,800-2,200 | RSE Results (§11) + relevant Discussion (§16 points 1, 6, 7) |
| Usage Notes | ~500-700 | RSE Discussion §6.4 (abstain-reason design) + Limitations practical guidance |
| Data Availability | ~100-150 | RSE Declarations |
| Code Availability | ~100-150 | RSE Declarations |
| Author Contributions, Competing Interests | boilerplate | RSE Declarations |
| **Total body (Abstract → Usage Notes)** | **~6,600-7,600** | roughly 60% of the RSE manuscript's length — expected and correct for this format, not a shortfall |

**Backup structure (ESSD Data Description), for reference if the venue switches** — same content, different headings/order: Title/Abstract (no hard limit, but keep close to the Scientific Data version for consistency) → Introduction (= Background & Summary, can expand slightly since no 700-word cap) → 2 Data and Methods (= Methods + Data Records merged) → 3 Technical Validation (ESSD's explicitly *required* "dedicated section on uncertainty and its evaluation" — this project already has exactly that content) → 4 Usage Notes (ESSD doesn't name this exact heading but a numbered subsection under Data and Methods or its own short section works) → **Data availability** (named section, required) → **Code availability** (named section, required) → **Conclusions** (ESSD requires this; Scientific Data does not — write 150-250 words summarizing the dataset's value and validation status, reusable as-is if targeting ESSD, simply omit if targeting Scientific Data) → Author contribution → Competing interests → Acknowledgements → References.

---

## §20. Abstract Blueprint (≤170 words, hard limit)

1. **What the dataset is** (1-2 sentences): a national, polygon-level, 3-class crop-species dataset for Australia at 10 m, from Sentinel-2 and field-verified GRDC/NVT records.
2. **Scale** (1 sentence): 2024 national coverage, 1,346,582 polygons; a 9-year (2017-2025) 100 km regional companion.
3. **What each record carries** (1 sentence): predicted class or abstain reason, confidence, calibrated Cereal yield.
4. **Validation** (1-2 sentences, factual, no interpretive claim): validated against independent ABS statistics (r=0.82 canola composition) and independently corroborated against WorldCereal/NLUM; area over-call of 1.47-1.59x is disclosed and quantified.
5. **Reuse value** (1 sentence): closes a real gap — no other continent-wide, field-verified, paddock-scale Australian crop dataset exists.
**Explicitly excluded**: any sentence framed as "we show that," "we find that," "this reveals," or similar — replace with "the dataset provides," "validation indicates," "polygons are labelled."

---

## §21. Title and Framing Options

1. **"Mapping Canola, Cereal, and Legume Paddocks Across Australia at 10 m: A Field-Verified, ABS-Validated Dataset"** — RECOMMENDED. This is RSE Option 3 (`PAPER_PLAN.md` §21), already flagged there as "closer to the Scientific Data backup framing" — dataset-first, no methodological-novelty claim in the title, matches Scientific Data conventions directly.
2. "A National Crop-Species Polygon Dataset for Australia (2024): Sentinel-2-Derived Segmentation, Presence-Gated Classification, and Calibrated Cereal Yield"
3. "AusCropMap: A Field-Verified Crop-Species and Yield Dataset for Australia from Sentinel-2, 2024" — a named-dataset framing, common in Scientific Data/ESSD titles; **requires picking an actual dataset name**, not yet decided anywhere in this project — flag as an open decision in §24 if this option is preferred.

**Dominant framing**: pure dataset descriptor — no methods-innovation or applied-case-study framing language in the title, unlike the RSE options.

---

## §22. Citation and Evidence Bank

Reuse `PAPER_PLAN.md` §22's verified citation list in full — no new citations needed beyond what RSE already verified (Van Tricht et al. 2023, Tseng et al. 2024, Brown et al. 2025, Karra et al. 2021, Sharma et al. 2026, Al-Shammari et al. 2024, Lawes et al. 2022, Kirillov et al. 2023, Kerner et al. 2024, Olofsson et al. 2014, Ashourloo et al. 2019). **Citation load will be much lighter in the actual manuscript** — Background & Summary's 700-word cap and Methods' reuse-focused tone mean most of RSE's Related Work citations (Cluster A foundation-model citations especially: Tseng/Presto, Brown/AlphaEarth, Karra) may not need in-text citation at all here, since the Presto comparison itself is now Methods-justification prose, not a literature-positioning argument — cite Presto's own paper once, in Methods, and drop the rest of Cluster A unless Background & Summary's tight space allows a one-clause mention. Newman & Furbank (2021) handling is unchanged from the RSE plan (§15/§24 there): citable, same shared-lineage framing, same GRDC pre-submission sign-off requirement (§24 below).

---

## §23. Writing Instructions for Downstream Agent

**Non-negotiable:**
- **The Abstract and Background & Summary must never state a claim in "we show/we find/this reveals" form.** Use dataset-description verbs: "the dataset provides," "polygons are labelled," "validation indicates," "X% of polygons carry Y."
- **Never fabricate or interpolate national multi-year (2017-2025) numbers.** Write `[PENDING: national 2017-2025 run, E8]` verbatim exactly as the RSE manuscript does.
- **The leading classifier candidate (macro F1 0.890/0.892) and its Open-Issue-#8 status must NOT appear anywhere in this manuscript** — not even in a caveated Methods/Usage-Notes mention. Unlike the RSE manuscript (which discloses it explicitly, per that plan's §24 Open Issue #8), a Data Descriptor describes the SHIPPED dataset only; a not-adopted alternative model has no natural home in Data Records/Methods/Technical Validation/Usage Notes without either (a) implying it's part of the dataset, which it is not, or (b) turning into exactly the kind of "in-depth analysis"/interpretive content this format excludes. See §24 for the explicit reasoning — this is a deliberate scoping decision for this venue, not an oversight, and differs from the RSE manuscript's treatment on purpose.
- Always report both raw (NVT-equivalent) and ABS-calibrated Cereal yield columns together, per the same standing project rule as the RSE plan.
- Always state the ABS/ABARES 6.8% mutual disagreement alongside any map-vs-ABS accuracy claim tighter than that (same rule as RSE §23, and the same fix `paper-review-loop` round 1 already had to make once on the RSE draft — get it right the first time here).
- State the 3-group descoping explicitly in Methods (§9 point 2), not buried.
- Describe the ABS validation as validation against an independent official statistic, never as ground-truth-level accuracy.
- The phenology-gate and Presto content must read as **method justification**, not as reported findings — if a sentence would be equally at home in the RSE Discussion section, it is worded wrong for this manuscript; rewrite it as "we selected X because Y" rather than "we found that Y."
- Do not name or describe GRDC/NVT site-level records anywhere, per `CLAUDE.md`.
- Newman & Furbank may be cited under the same terms as the RSE plan (§24 below) — this does not remove the standing GRDC pre-submission sign-off requirement.

**Section priorities if space/time is constrained**: Abstract, Background & Summary, and Technical Validation are this manuscript's actual spine (a Data Descriptor lives or dies on "is the data good and is that demonstrated," not on Methods elegance) — protect these first. Methods' reframed justification content (§9 points 2-5) is important for completeness but can be trimmed to single sentences per point if space is tight, since none of it is this manuscript's headline content the way it partially is in RSE's Discussion.

---

## §24. Open Issues Before Drafting

1. **Journal choice** — user-directed 2026-09-04: Scientific Data primary, ESSD backup. Not yet cross-reviewed externally (Codex MCP unavailable, consistent with every prior planning pass in this project).
2. **Newman & Furbank (2021) citation handling** — same resolution as the RSE plan (`PAPER_PLAN.md` §24 Open Issue #2): citable under the project's signed GRDC data-use agreement, same shared-lineage framing, same standing requirement that the finished manuscript go to GRDC for sign-off before submission to **any** venue — this applies to this Scientific Data/ESSD manuscript too, not just the RSE one, and is not yet done for either.
3. **National multi-year run (E8)** — in progress in a parallel session (2/9 years done as of 2026-09-04), same status as the RSE plan. Draft now with `[PENDING: E8]` markers; update once it completes.
4. **NLUM/WorldCereal spatial comparison (E9)** — DONE (same reports as RSE: `output/WORLDCEREAL_COMPARISON.md`, `output/NLUM_COMPARISON.md`), directly reusable in Technical Validation with no additional work.
5. **Author list / affiliations** — not specified; placeholder only, per this skill's rule against generating author information (same as RSE).
6. **NEW, specific to this plan — the leading classifier candidate (Open Issue #8 from the RSE plan) is deliberately EXCLUDED from this manuscript entirely, not disclosed-with-caveat the way the RSE manuscript handles it.** Reasoning: a Data Descriptor describes the dataset that was actually shipped; the candidate is not shipped, not adopted, and not independently reviewed. The RSE manuscript can disclose it because RSE's Discussion/Limitations sections exist specifically to host exactly this kind of "here is something we know but didn't ship" honesty; Scientific Data's format has no section built for that (Methods describes what was done, Technical Validation validates what was done, Usage Notes helps a user work with what was shipped — none of these are the right place for "and here is a different model we didn't use"). **This is a deliberate scoping decision, flagged explicitly here rather than silently applied** — if the user disagrees and wants it disclosed anyway (e.g., in a brief Methods aside), that is a real available choice, just not the default recommendation. Revisit if/when Open Issue #8 itself resolves (if the candidate is eventually adopted and independently reviewed, this whole question moves to "which model does the shipped dataset actually use," not "do we disclose an unshipped candidate").
7. **NEW — dataset deposit and DOI.** Scientific Data and ESSD both require a persistent identifier for the dataset itself in the Data Availability section. This project has not yet deposited the national 2024 map (or the model artifacts) to a citable repository (Zenodo, Figshare, or similar) — this is a real, not-yet-done prerequisite for a submittable Data Availability statement, independent of manuscript drafting. Flagged here so it is not discovered late.
8. **NEW — dataset naming.** If Title Option 3 (a named dataset, e.g. "AusCropMap") is preferred over the plainer Option 1, a name needs to be chosen — not yet decided anywhere in this project. Option 1 (no dataset name required) is the default recommendation specifically to avoid blocking on this.
9. **No external cross-review of this plan was run** (Phase 6, Codex MCP unavailable) — same standing limitation as every prior planning pass.

---

## §25. Final Readiness Assessment

**Ready for a full first-pass draft now**: Abstract, Background & Summary, Methods (including all four reframed justification blocks), Data Records, Technical Validation (everything sourced from V1-V8), Usage Notes, Data/Code Availability (modulo Open Issue #7's DOI gap — draft can note "to be assigned" and still be internally complete).

**Blocked on**:
- E8 (national multi-year run) — needed for Technical Validation's Table 6, Fig. 7's national panel, and Methods/Usage Notes' "planned update" framing to describe real timing rather than an open-ended one.
- Dataset DOI deposit (Open Issue #7) — does not block drafting (can placeholder), blocks actual submission.
- GRDC pre-submission sign-off (Open Issue #2) — does not block drafting, blocks actual submission, exactly as for the RSE manuscript.

**Recommended drafting strategy**: proceed directly to `paper-draft` against this plan (figures do not need regeneration — `paper-figure-generate` can be skipped entirely for this venue, reusing the existing 8 figures with the one caption reword noted in §13). This should produce a **partial draft** (same category as the RSE manuscript, same reason — E8-gated), at roughly 60% of the RSE manuscript's word count, reflecting the format's own much tighter budget rather than any completeness gap.

---

## §26. Executive Summary for Manuscript Writer

**What this manuscript is about**: the same underlying national, field-verified crop-species dataset as the RSE paper, described and validated as a *data product* rather than argued as a *research contribution* — same numbers, materially different rhetoric.

**Why it's publishable here specifically**: Scientific Data's Data Descriptor format rewards exactly what this project's strongest asset already is — a validated, reusable dataset with honestly quantified limitations — without requiring the kind of "is this novel enough" positioning argument RSE review might push back on.

**Strongest evidence** (unchanged from RSE): the ABS validation (r=0.82, independent statistic) and the cross-corroborating WorldCereal/NLUM comparison.

**Weakest/most exposed evidence** (unchanged from RSE, restated in data-quality terms): the Legume over-prediction has no mechanism yet; the national multi-year story doesn't exist yet (only regional); the area over-call itself, while well-quantified, is a real and sizeable limitation a careful reviewer will weigh heavily given Scientific Data's explicit "reusability" evaluation axis.

**What to emphasize**: the abstain_reason/confidence/dual-yield-column design as first-class reuse infrastructure — this is Usage Notes' actual job, and this project already has genuinely good content for it.

**What to be careful about**: never let Methods' reframed justification content (§9 points 2-5) drift back into RSE-style "this is a general finding" language — that is the one failure mode most likely to make an editor bounce this as miscategorized (should have been a research article, not a Data Descriptor); never disclose the leading classifier candidate (§24 point 6); never state a national multi-year claim before E8 completes; never cite Newman & Furbank without confirming the GRDC sign-off status is still current.

---

*End of PAPER_PLAN_SCIDATA.md.*
