# Auto Review Log — manuscript

Cumulative record of `paper-review-loop` passes, per-dimension scores, and top issues. Generator-evaluator separation: review scoring is always done by a cold-read subagent that did not author the draft/revision it is scoring (Codex MCP unavailable in this environment, per `PAPER_PLAN.md` §0).

## Round 1 — 2026-09-04

**Verdict**: almost (pre-fix) — all 4 named blockers fixed this round without touching E8 or Open Issue #8.

| Dimension | Score |
|---|---|
| gap_clarity | 8.0 |
| novelty_precision | 8.0 |
| methods_rigor | 6.0 |
| results_discipline | 7.0 |
| discussion_depth | 7.0 |
| literature_positioning | 8.0 |
| journal_fit | 6.5 |
| language_flow | 7.0 |

**Top 3 majors** (all fixed this round, see `MAJOR_ISSUES.md`):
1. Tables 2-5 were referenced in running text but never built.
2. Table 7 and Table 8 reported different numbers for the same candidate model, unreconciled.
3. The Legume classification finding had no dedicated Discussion-level treatment, per `PAPER_PLAN.md` §16.

**Critical check requested and passed**: the unreviewed leading classifier candidate's numbers (0.890/0.892) do not leak into any Results/Abstract/Introduction claim anywhere in the manuscript — every occurrence is confined to Discussion/Limitations/Conclusion and correctly caveated.

Full detail: `output/manuscript/REVIEW_REPORT.md`.

## Round 1 — Scientific Data manuscript — 2026-09-04

Separate manuscript (`output/manuscript_scidata/`, from `output/PAPER_PLAN_SCIDATA.md`), reviewed independently of the RSE manuscript above.

**Verdict**: almost (pre-fix) — both majors fixed this round without touching E8 or either deposit prerequisite.

| Dimension | Score |
|---|---|
| structural_fit | 9.0 |
| claim_evidence_alignment | 6.0 |
| methods_rigor | 7.0 |
| technical_validation_completeness | 9.0 |
| journal_fit | 9.0 |
| language_flow | 7.0 |

**Top majors** (both fixed this round, see `output/manuscript_scidata/MAJOR_ISSUES.md`):
1. Abstract sentence implied WorldCereal/NLUM corroborate canola *composition* specifically, when the evidence only supports a general presence check and a non-composition enrichment ratio.
2. Central gate-design justification claimed Cereal/Legume recall was "essentially unchanged" under the phenology-shape gate while the comparison table left those exact cells blank — the real deltas (Cereal −4.6 pts, Legume −4.1 pts) are non-trivial.

**Critical checks requested and passed**: the excluded leading classifier candidate (0.890/0.892) does not leak anywhere in this manuscript, confirmed by direct search; both newly-added findings (3-groups-vs-9-species dual justification, canola-yield-needs-S1) were confirmed present and correctly worded.

Full detail: `output/manuscript_scidata/REVIEW_REPORT.md`.
