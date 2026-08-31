# Draft README — paddock-species manuscript

**Date**: 2026-08-30
**Target venue**: Remote Sensing of Environment (RSE), Elsevier — confirmed by user, `PAPER_PLAN.md` §24 Open Issue #1
**Manuscript type**: Research Paper (applied case study / dataset-and-validation)
**Paper type framing**: Applied case study, per `PAPER_PLAN.md` §21 — the two primary contributions are the dataset itself and a negative presence-gate finding, not a novel algorithm.
**Title used**: Option 1 of 3 from `PAPER_PLAN.md` §21 (see `REVISION_NOTES.md` for the live framing decision this depends on).

## Draft mode: PARTIAL

Per this skill's Phase 2 decision rule: ≥60% of core claims in `PAPER_PLAN.md` §12 are supported (all of E1-E7, E9 now also done), and figures/tables for Methods and multiple Results subsections exist (all 8 figures are DONE as of this pass), but one core experiment (E8, the national multi-year run) remains genuinely unrun, and every claim that depends on it is marked `[PENDING: national 2017-2025 run, E8]` rather than fabricated. This satisfies the `partial` criteria exactly, not `full` (E8 blocks a small number of specific claims) and not `skeleton` (the overwhelming majority of the manuscript, including all of Results 5.1-5.5 and 5.7, is fully supported).

**This mode was also a deliberate user choice, not only an evidence-availability one**: the user explicitly declined to run E8 in this session, pending a discussion of validation methodology and the consensus/multi-year regional approach with colleagues — this manuscript is intended in part to inform that discussion. See project memory `paper-draft-informs-colleague-discussion.md`.

## What changed since `PAPER_PLAN.md` was written (2026-08-29)

- All 8 figures are now DONE (were 4/8 when the plan was written); Fig03 was regenerated from verified source data rather than reused unverified.
- E9 (NLUM/WorldCereal spatial comparison) is now DONE and folded into Methods §4.6, Results §5.5, Discussion §6.1, and Limitations §7.1 — it did not exist when `PAPER_PLAN.md`'s Related Work, Results, and Limitations sections were originally planned, so this draft extends those sections beyond the plan's original text (see `SECTION_NOTES.md` for exactly where).
- Two errors in `PAPER_PLAN.md`'s own figure specs were found and corrected during figure generation (4, not 5, abstain reasons; 133, not 132, validation SA2s) and carried through consistently into this draft.
- Four citations flagged as "needs fresh lookup" (`PAPER_PLAN.md` §22/§24 Open Issue #6) were verified via WebSearch and are now complete, including one year correction (Lawes et al., corrected from a guessed "2021/2023" to the verified 2022).
- E8 remains not run, by explicit user decision this session (see above), not by default inaction.

## Word counts (target vs. actual, `PAPER_PLAN.md` §19)

| Section | Target | Actual | Note |
|---|---|---|---|
| Abstract | 200-250 | 230 (abstract only, excl. Highlights/Graphical Abstract) | On target |
| 1. Introduction | 800-1000 | 898 | On target |
| 2. Related Work | 1300-1600 | 1251 | Slightly under; acceptable — content-complete, not padded |
| 3. Study Area and Data | 600-800 | 805 | On target |
| 4. Methods | 1600-1900 | 1806 | On target (includes the new §4.6 E9 methodology) |
| 5. Results | 1200-1500 | 1554 | Slightly over; includes the new §5.5 E9 subsection |
| 6. Discussion | 900-1100 | 1067 | On target |
| 7. Limitations and Future Work | 500-700 | 726 | Slightly over; includes the new Limitation 9 (E9 caveats) |
| 8. Conclusion | 300-450 | 402 | On target |
| **Total body (Abstract-Conclusion)** | ~9,000-10,000 | **9,237** | On target |

Declarations (~309 words) and Title block are not counted against the body-text target, consistent with typical RSE practice.

## Deliverable index

- `MANUSCRIPT_DRAFT.md` — the assembled manuscript (this is the primary deliverable).
- `ABSTRACT_DRAFT.md` — stand-alone abstract, highlights, graphical-abstract description.
- `sections/*.md` — per-section source files (edit these, not `MANUSCRIPT_DRAFT.md` directly, then re-assemble).
- `CLAIM_SUPPORT_MAP.md` — every non-trivial claim mapped to its evidence source.
- `COVERAGE_GAPS.md` — every gap, conflict, or deferred item, categorized.
- `CITATION_GAPS.md` — citation verification status (all resolved this pass).
- `SECTION_NOTES.md` — per-section scope decisions and what changed relative to `PAPER_PLAN.md`.
- `REVISION_NOTES.md` — prioritized next actions, split into "before colleagues see this," "mechanical, once E8 lands," and "lower priority."

## Next actions (see `REVISION_NOTES.md` for full detail)

1. **User review** — this is a first-pass draft; `paper-review-loop` has not been run on it, per this project's generator-evaluator separation rule.
2. **Colleague discussion** on validation methodology and the consensus/multi-year regional approach (the reason E8 was deferred) — this manuscript is intended to support that discussion.
3. Once that discussion concludes and E8's scope/timing is decided, either proceed to run E8 and do a mechanical update pass (Section 3.2, 5.6, 7.1, 8, Abstract, Table 6, Fig. 7's national panel), or revise the draft's framing based on colleague feedback first.
