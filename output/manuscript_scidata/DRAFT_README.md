# Draft README — paddock-species Scientific Data manuscript

**Date**: 2026-09-04; reviewed 2026-09-04 (`paper-review-loop` round 1 — see `REVIEW_REPORT.md`)
**Source plan**: `output/PAPER_PLAN_SCIDATA.md` (v1.1) — a separate plan from `output/PAPER_PLAN.md` (the RSE plan). This manuscript and `output/manuscript/MANUSCRIPT_DRAFT.md` (RSE) describe the same underlying dataset for two different venues; they are independent drafting outputs, not versions of each other.
**Target venue**: Nature *Scientific Data* (primary), backup *Earth System Science Data* (ESSD)
**Manuscript type**: Data Descriptor (Scientific Data) / Data Description article (ESSD)
**Paper type framing**: Pure dataset descriptor — no methods-innovation or applied-case-study framing, per `PAPER_PLAN_SCIDATA.md` §21.
**Title used**: Option 1 of 3 from `PAPER_PLAN_SCIDATA.md` §21 (dataset-first, no coined dataset name).

## Draft mode: PARTIAL

Same underlying reason as the RSE manuscript: the national multi-year run (E8) is genuinely incomplete (2/9 years done as of 2026-09-04, in progress in a parallel session), and every affected claim carries an explicit `[PENDING: national 2017-2025 multi-year run]` marker rather than a fabricated number. Everything else — classifier accuracy, ABS/WorldCereal/NLUM validation, Cereal yield validation, the 9-year regional companion evidence, and all Methods-section design justifications — is fully drafted and evidence-complete.

## What this draft is NOT

- **Not a relabeled copy of the RSE manuscript.** Different section structure (no Introduction/Related Work/Results/Discussion/Conclusion — Background & Summary/Methods/Data Records/Technical Validation/Usage Notes instead), different rhetorical register (data-quality description, never "we show/we find"), and one deliberate content exclusion the RSE manuscript does not make (the leading, unreviewed classifier candidate — see below).
- **Not submission-ready.** Two real, independent-of-content blockers: no dataset DOI yet, no code-repository deposit yet (both `[PENDING]` in Data Availability/Code Availability). Also not yet run through a review-loop-equivalent pass.

## Deliberate scoping decision, not an oversight

Per `PAPER_PLAN_SCIDATA.md` §24 point 6: **the leading classifier candidate (macro F1 0.890/0.892, RSE `PAPER_PLAN.md` §24 Open Issue #8) does not appear anywhere in this manuscript** — not disclosed, not caveated. The RSE manuscript discloses it explicitly (Discussion/Limitations, with the "not independently reviewed, not adopted" caveat) because RSE's format has sections built to host exactly that kind of honest disclosure. A Data Descriptor does not — Methods describes what was shipped, Technical Validation validates what was shipped, Usage Notes helps a user work with what was shipped. Verified absent by direct grep of `MANUSCRIPT_DRAFT.md` (no occurrence of "0.890", "0.892", "sharma6", or "candidate").

## Two findings resolved just before this draft was written, already reflected in it (not stale)

1. **3-groups-vs-9-species justification** now states both reasons together in Methods (label-conflict resolution AND the macro F1 0.38-vs-0.82 accuracy justification) — added to both this draft and the RSE manuscript on 2026-09-04, per explicit user request.
2. **Canola yield's absence** is now stated as "needs Sentinel-1, confirmed on re-test" (spatial R² 0.271 optical-only vs. 0.290 baseline vs. 0.371 with S1) rather than "doesn't work" — re-tested against the current row-matched population (job 178174639, `CANOLA_YIELD_s1ctl.md`/`CANOLA_YIELD_s1.md`) before being written into either manuscript, specifically to avoid propagating a possibly-stale number.

## Word counts (target vs. actual, `PAPER_PLAN_SCIDATA.md` §19)

| Section | Target | Actual | Note |
|---|---|---|---|
| Abstract | ≤170 (hard limit) | 166 | Compliant |
| Background & Summary | ≤700 (hard limit) | 579 | Compliant, not padded to fill |
| Methods | ~2,800-3,200 (soft) | 1,836 | Under the soft estimate; content-complete per `SECTION_NOTES.md` — not cut to hit a number, and Scientific Data's Methods has no actual cap |
| Data Records | ~700-900 (soft) | 666 | Slightly under; content-complete |
| Technical Validation | ~1,800-2,200 (soft) | 1,618 | Close to soft target; content-complete, 3 tables added beyond the first pass |
| Usage Notes | ~500-700 (soft) | 557 | On target |
| **Total body (Abstract → Usage Notes)** | ~6,600-7,600 | **5,443 → ~5,685 (post-review)** | Under the plan's own estimate — see `SECTION_NOTES.md` for why this is a format-appropriate length, not a completeness gap. `paper-review-loop` round 1 added ~185 words fixing two majors and four moderates (filled table cells, a missing S1 number, a population-size clarification, one reworded Abstract clause) — no padding. Declarations (~291 words) not counted, consistent with the RSE manuscript's convention. |

## Deliverable index

- `MANUSCRIPT_DRAFT.md` — the assembled manuscript (primary deliverable).
- `ABSTRACT_DRAFT.md` — stand-alone abstract, keywords, and the ESSD-style ≤500-character short summary.
- `sections/*.md` — per-section source files.
- `CLAIM_SUPPORT_MAP.md` — every claim mapped to its evidence source (same evidence base as the RSE manuscript).
- `COVERAGE_GAPS.md` — gaps, categorized, including the two real deposit blockers.
- `CITATION_GAPS.md` — citation list (much lighter than the RSE manuscript's, by design) and which RSE citations were deliberately dropped.
- `SECTION_NOTES.md` — per-section fidelity and word-count accounting.
- `REVISION_NOTES.md` — prioritized next actions.

## Next actions

1. Deposit the dataset and code to a citable repository (DOI) — blocks actual submission, not further drafting.
2. Review pass (cold-read subagent, mirroring the RSE manuscript's `paper-review-loop` treatment) — not yet run.
3. GRDC pre-submission sign-off — standing requirement, not yet done for either manuscript.
4. Once E8 completes: mechanical update pass replacing every `[PENDING]` marker in Data Records/Technical Validation, mirroring the equivalent RSE update.
