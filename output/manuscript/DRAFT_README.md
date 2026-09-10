# Draft README — paddock-species manuscript

**Date**: 2026-08-30; revised 2026-09-03 (v1.1 findings folded in); reviewed 2026-09-04 (`paper-review-loop` round 1 — see `REVIEW_REPORT.md`); house-style pass and model-adoption update 2026-09-10 (see the 2026-09-10 section below)
**Target venue**: Remote Sensing of Environment (RSE), Elsevier — confirmed by user, `PAPER_PLAN.md` §24 Open Issue #1
**Manuscript type**: Research Paper (applied case study / dataset-and-validation)
**Paper type framing**: Applied case study, per `PAPER_PLAN.md` §21 — the two primary contributions are the dataset itself and a negative presence-gate finding, not a novel algorithm.
**Title used**: Option 1 of 3 from `PAPER_PLAN.md` §21 (see `REVISION_NOTES.md` for the live framing decision this depends on).

## Draft mode: PARTIAL

Per this skill's Phase 2 decision rule: ≥60% of core claims in `PAPER_PLAN.md` §12 are supported (all of E1-E7, E9 now also done), and figures/tables for Methods and multiple Results subsections exist (all 8 figures are DONE as of this pass), but one core experiment (E8, the national multi-year run) remains genuinely unrun, and every claim that depends on it is marked `[PENDING: national 2017-2025 run, E8]` rather than fabricated. This satisfies the `partial` criteria exactly, not `full` (E8 blocks a small number of specific claims) and not `skeleton` (the overwhelming majority of the manuscript, including all of Results 5.1-5.5 and 5.7, is fully supported).

**This mode was also a deliberate user choice, not only an evidence-availability one**: the user explicitly declined to run E8 in this session, pending a discussion of validation methodology and the consensus/multi-year regional approach with colleagues — this manuscript is intended in part to inform that discussion. See project memory `paper-draft-informs-colleague-discussion.md`.

## 2026-09-10 pass: house style, model-adoption update, reassembly

- `MANUSCRIPT_DRAFT.md` was two days behind `sections/` (the 2026-09-07/08 citation and wording edits to sections 01, 02, 03, 06, 07 and 09 had never been reassembled). It is now rebuilt by `assemble.py`, which strips each section's front matter and concatenates in filename order (Declarations now precede References, matching the section numbering). Run `python3 assemble.py` after any edit to `sections/`.
- Full pass against the house style (`~/Projects/shelterbelts2/WRITING_STYLE.md`): 71 em-dashes removed, Oxford commas removed, Australian spelling, Methods (Section 4) in passive voice with no first person, bold lead-ins removed from the Limitations and Future Work lists, process meta-commentary and reviewer-bait adjectives cut, over-long sentences split. Numbers and claims unchanged.
- Facts updated: the shipped+sharma6 classifier passed independent review on 2026-09-07 (`output/INDEPENDENT_REVIEW_shipped_sharma6.md`, verdict adopt) and was adopted in production on 2026-09-08 (commit `9b21c08`); the 2024 national re-run with it (9 km tiles, tile-boundary merge) launched 2026-09-10. Limitation 10, Table 8, Future Work items 1 and 6, Discussion 6.5, Limitation 6 and the Conclusion now say so. Every Results number is still the earlier three-index model ("the deployed model" throughout), flagged in the title block and in a `[PENDING]` marker in Limitation 10.
- Three cross-reference errors fixed: Section 3.1 pointed at Limitation 1 for single-season coverage (it is Limitation 4); Section 4.6 pointed at Section 5.2 for the Legume over-prediction (it is 5.3); Section 4.1 now names Limitation 3.
- Table 2's last row had the following paragraph glued onto it; split.
- `sections_revised/` deleted: it was a 2026-09-04 snapshot of `sections/` (the review loop applied its fixes in place, per `REVISION_LOG.md`), and every later edit lived only in `sections/`.
- Not done: the Results/Methods rewrite for the adopted model and the 9 km geometry (waits on the re-run); `paper-covert` (both `output/submission*/` packages date from 2026-09-04 and are stale).

## What changed since `PAPER_PLAN.md` was written (2026-08-29)

- All 8 figures are now DONE (were 4/8 when the plan was written); Fig03 was regenerated from verified source data rather than reused unverified.
- E9 (NLUM/WorldCereal spatial comparison) is now DONE and folded into Methods §4.6, Results §5.5, Discussion §6.1, and Limitations §7.1 — it did not exist when `PAPER_PLAN.md`'s Related Work, Results, and Limitations sections were originally planned, so this draft extends those sections beyond the plan's original text (see `SECTION_NOTES.md` for exactly where).
- Two errors in `PAPER_PLAN.md`'s own figure specs were found and corrected during figure generation (4, not 5, abstain reasons; 133, not 132, validation SA2s) and carried through consistently into this draft.
- Four citations flagged as "needs fresh lookup" (`PAPER_PLAN.md` §22/§24 Open Issue #6) were verified via WebSearch and are now complete, including one year correction (Lawes et al., corrected from a guessed "2021/2023" to the verified 2022).
- E8 remains not run at the time of this draft, but is now **in progress** in a parallel session (2 of 9 national years complete as of 2026-09-03), following the colleague discussion this manuscript was written in part to inform.

## v1.1 revision (2026-09-03) — folding in post-draft findings

Against `PAPER_PLAN.md` v1.1, this pass added the five findings produced after the 2026-08-30 draft (see `PAPER_PLAN.md` §0 for the full list). None of these touch Results or the shipped model's reported accuracy numbers — they are Discussion- and Limitations-level findings about covariates and an alternative model candidate, per `PAPER_PLAN.md` §23's non-negotiable instruction that every Results-section number stays the shipped model (0.821/0.823).

- **New Discussion §6.5** ("A covariate's value is task-dependent, not pipeline-dependent"): Sentinel-1 regresses the classifier once measured against the current best model, but improves the shipped Cereal yield model; Sharma6 indices regress canola yield. New Table 7. (Renumbered the old §6.5 "Generalizability across seasons" to §6.6 — all forward references updated.)
- **Limitations §7.1, item 6 rewritten**: the old single-direction "S1 gives a weak +0.03 gain, not worth it" framing was factually superseded and is corrected to the task-split finding.
- **Limitations §7.1, new item 10**: discloses the leading shipped+sharma6 classifier candidate (macro F1 0.890/0.892 vs. shipped 0.821/0.823, no canola@5%FPR regression) as **not independently reviewed and not adopted** — every classifier number elsewhere in the paper is the shipped model. New Table 8.
- **Future Work §7.2**: item 1 updated to reflect E8 now in progress (was "deliberately deferred"); two new items added — independent review of the candidate model, and national Sentinel-1-for-yield scale-up (gated on two named open sub-problems).
- **Conclusion**: "Two open threads" became "Three open threads," adding the candidate-model disclosure alongside E8 and the Legume mechanism.
- **Not changed**: Abstract, Highlights, Introduction, Related Work, Study Area/Data, Methodology, and Results (Sections 5.1-5.7) are untouched — per `PAPER_PLAN.md` §23, these secondary findings are explicitly Discussion/Future-Work material, not headline claims. All `[PENDING: E8]` markers are untouched.
- **Left explicitly open, not resolved by this pass**: whether to adopt the candidate classifier before submission (`PAPER_PLAN.md` §24 Open Issue #8) is a live decision for the user, not made here.

## Word counts (target vs. actual, `PAPER_PLAN.md` §19)

| Section | Target | Actual (v1.0) | Actual (v1.1) | Note |
|---|---|---|---|---|
| Abstract | 200-250 | 230 | 230 | Unchanged this pass |
| 1. Introduction | 800-1000 | 898 | 898 | Unchanged this pass |
| 2. Related Work | 1300-1600 | 1251 | 1251 | Unchanged this pass |
| 3. Study Area and Data | 600-800 | 805 | 805 | Unchanged this pass (one cross-reference number fixed) |
| 4. Methods | 1600-1900 | 1806 | 1806 | Unchanged this pass |
| 5. Results | 1200-1500 | 1554 | 1554 | Unchanged this pass (one cross-reference number fixed) |
| 6. Discussion | 1000-1250 | 1067 | ~1340 | +§6.5 (task-dependent covariates) + Table 7 |
| 7. Limitations and Future Work | 500-900 | 726 | ~1010 | Item 6 rewritten, item 10 + Table 8 added, 2 new future-work items |
| 8. Conclusion | 300-450 | 402 | ~460 | Third open thread (candidate model) added |
| **Total body (Abstract-Conclusion)** | ~9,000-10,000 | **9,237** | **~10,150 → ~11,159 (post-review)** | Round 1 of `paper-review-loop` added 4 tables (Tables 2-5, ~500 words) and a new Discussion §6.7 (~250 words) to fix real completeness gaps (`MAJOR_ISSUES.md` M1, M3) — tables carry most of their own weight in structured data, not prose, so the word-count-vs-target comparison is less meaningful for this delta than for earlier prose-only growth. Section-length balance (Limitations/Future Work vs. Discussion) flagged as Moderate and deferred — see `NEXT_LOOP_PRIORITIES.md`. |

Declarations (~309 words) and Title block are not counted against the body-text target, consistent with typical RSE practice. Word-count trim (if RSE's confirmed word limit requires it) is a `paper-covert`-stage task, not done here.

## Deliverable index

- `MANUSCRIPT_DRAFT.md` — the assembled manuscript (this is the primary deliverable).
- `ABSTRACT_DRAFT.md` — stand-alone abstract, highlights, graphical-abstract description.
- `sections/*.md` — per-section source files (edit these, not `MANUSCRIPT_DRAFT.md` directly, then run `assemble.py`).
- `assemble.py` — rebuilds `MANUSCRIPT_DRAFT.md` from `sections/`.
- `CLAIM_SUPPORT_MAP.md` — every non-trivial claim mapped to its evidence source.
- `COVERAGE_GAPS.md` — every gap, conflict, or deferred item, categorized.
- `CITATION_GAPS.md` — citation verification status (all resolved this pass).
- `SECTION_NOTES.md` — per-section scope decisions and what changed relative to `PAPER_PLAN.md`.
- `REVISION_NOTES.md` — prioritized next actions, split into "before colleagues see this," "mechanical, once E8 lands," and "lower priority."

## Next actions (see `REVISION_NOTES.md` for full detail)

1. **`paper-review-loop` and `paper-covert`, next in this session** (2026-09-03) — run against this v1.1 draft while E8 finishes in a parallel session. Both will need to be **re-run once E8 completes and/or Open Issue #8 (candidate-model adoption) is resolved**, so treat this pass's outputs as an interim, review-ready checkpoint, not the final package.
2. Once E8 completes: a mechanical update pass (Section 3.2, 5.6, 7.1, 8, Abstract, Table 6, Fig. 7's national panel) replacing every `[PENDING: E8]` marker, then re-run `paper-review-loop`/`paper-covert` again.
3. Resolve `PAPER_PLAN.md` §24 Open Issue #8 (adopt the leading classifier candidate, or keep it as a disclosed-only finding) — if adopted, this requires an independent review pass plus re-running the national map/ABS validation, a larger scope change than the mechanical E8 update above.
