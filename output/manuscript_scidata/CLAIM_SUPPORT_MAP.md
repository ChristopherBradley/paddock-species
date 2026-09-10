# Claim Support Map (Scientific Data draft)

Every non-trivial numeric claim in `MANUSCRIPT_DRAFT.md`, mapped to its evidence source. Sources are identical to the RSE manuscript's `output/manuscript/CLAIM_SUPPORT_MAP.md` — this project has one evidence base, drafted twice for two venues — with wording recalibrated per `PAPER_PLAN_SCIDATA.md` §0/§23 (data-quality description, not "we show/we find" claims).

| Claim | Evidence source | Confidence | Section(s) used |
|---|---|---|---|
| National 2024 map: 1,346,582 polygons, 99,465 tiles, 2.8 GB | `NATIONAL_2024_RUN.md` §1 | High | Abstract, Background & Summary, Data Records |
| 48.4% of polygons / 34.4% of area classified; 4 abstain reasons with exact counts | `NATIONAL_2024_RUN.md`; `GROUP BY abstain_reason` re-verification | High | Data Records |
| Classifier macro F1 0.821/0.823, per-class precision/recall/confusion | `output/arms/GROUP3_reviewed.md` | High | Technical Validation |
| Canola composition r=0.82, MAE 5.5 pts vs. ABS | `ABS_COMPARISON_NATIONAL.md` | High | Abstract, Technical Validation |
| 1.47x national / 1.59x regional area over-call, ABS/diluted/mapped/absorbed breakdown | `NATIONAL_2024_RUN.md` §4, `ABS_COMPARISON_100km.md`, `ABS_COMPARISON_NATIONAL.md` | High | Technical Validation |
| Argmax-vs-mean-probability table (Canola/Cereal/Legume) | `ABS_COMPARISON_NATIONAL.md` | High | Technical Validation |
| Presence-gate threshold sensitivity table | `ABS_COMPARISON_NATIONAL.md` | High | Technical Validation |
| ABS/ABARES per-year, per-class disagreement table; 6.8% median floor | `ABS_COMPARISON_100km.md`, `ABS_COMPARISON_NATIONAL.md` | High | Technical Validation |
| Phenology-shape gate comparison table (baseline/loosened/two-pass) | `PHENOLOGY_GATE.md` | High | Methods |
| Cereal yield RMSE 1.21 t/ha, R²/RMSE table by arm/split, calibration 0.6248 (+3.1%/+18.1%) | `YIELD_cereal_pooled.md`, `YIELD_CALIBRATION.md` | High | Technical Validation |
| WorldCereal presence agreement 73.1%, wintercereals 49.6%; NLUM enrichment ratios, grazing corroboration | `WORLDCEREAL_COMPARISON.md`, `NLUM_COMPARISON.md` | High | Technical Validation |
| 9-yr regional polygon stability (median IoU 0.84), weak years 2017/2018 | `POLYGON_STABILITY.md`, `ABS_COMPARISON_100km.md` | High | Technical Validation |
| Presto loses to hand-built features (0.775 vs 0.821; combined 0.824) | `REVIEWED_MODEL.md` | High | Methods (as feature-set justification, not a literature-positioning result) |
| 69.7% co-located trials, 31.8% different crop; 9-class macro F1 0.38 vs 3-group 0.82 | Project label-conflict analysis; `train_species.py` 9-class run | High | Methods (as label-scheme justification) |
| Canola yield: optical-only R² 0.271 (spatial) below baseline 0.290; +S1 R² 0.371 | `CANOLA_YIELD_s1ctl.md`, `CANOLA_YIELD_s1.md` (re-tested 2026-09-04, job 178174639) | High — re-tested against the current row-matched population and confirmed, not a stale carry-forward | Methods, Usage Notes |
| S1 regresses the classifier (not included) | `S1_VS_LATEST_MODEL.md` | High | Methods (as inclusion-status note only, not the general "task-dependent covariate" lesson — that framing is deliberately excluded, `PAPER_PLAN_SCIDATA.md` §0) |
| AgriWebb Grazing retirement, 78.5% pass-rate finding | `PRESENCE_ONLY_LABELS.md` | High | Usage Notes |
| **National multi-year (2017-2025) totals/trends** | none yet | **N/A — [PENDING: national 2017-2025 run], not fabricated anywhere in the draft** | Data Records, Technical Validation |

**Deliberately excluded from this manuscript** (per `PAPER_PLAN_SCIDATA.md` §24 point 6 — not a gap, a scoping decision): the leading shipped+sharma6 classifier candidate (macro F1 0.890/0.892) and its independent-review status. Confirmed absent from `MANUSCRIPT_DRAFT.md` by direct grep (no occurrence of "0.890", "0.892", "sharma6", or "candidate").

**Unsupported/weak claims deliberately avoided in this draft**: any "we show/we find/this reveals" framing (Scientific Data's abstract rule extended to the whole manuscript's tone); "the pipeline generalizes well across years nationally" (only regionally demonstrated); "canola yield is available" (explicitly not shipped, with the specific reason stated); describing the ABS check as "ground-truth accuracy" (it validates against an independent aggregate statistic, itself uncertain by ~6.8%); the phenology-gate and Presto content stated as generalizable findings rather than design justification.
