# Section Notes (Scientific Data draft)

Per-section scope decisions and fidelity, cross-checked against `PAPER_PLAN_SCIDATA.md`.

| Section | Fidelity | Notes |
|---|---|---|
| Title | full | Option 1 from `PAPER_PLAN_SCIDATA.md` §21 — dataset-first framing, no dataset name coined (Option 3 would require one, not yet decided). |
| Abstract | full | 166/170 words. No "we show/we find" language — verified by re-reading against §20's blueprint sentence-by-sentence. |
| Background & Summary | full | 579/700 words — under the hard cap with room to spare; did not pad to fill it, per "cut before padding." |
| Methods | full | 1,836 words vs. the plan's ~2,800-3,200 estimate — under the *soft* target (Scientific Data's Methods has no hard cap; the plan's number was a budget estimate, not a limit). Contains all four §0 reframing blocks (label-scheme justification, feature-set justification, gate-design justification, S1 inclusion-status note) plus the newly-confirmed canola-yield-S1 finding, and references to Fig. 1 and Fig. 6. |
| Data Records | full | 666 words. New section, not present in the RSE manuscript's structure — built from `NATIONAL_2024_RUN.md` schema detail and the abstain-reason breakdown, cross-checked against `FIGURE_MANIFEST.md`'s own warning not to conflate `national_2024_crops.gpkg` with the derived classified-only subset. References Fig. 2 and Fig. 4. |
| Technical Validation | full | 1,618 words vs. the plan's ~1,800-2,200 estimate, close to the soft target and substantively complete — every V1-V8 validation procedure from the plan's §10 is represented. Three tables added beyond the initial draft (argmax-vs-mean-probability, gate-threshold sensitivity, ABS/ABARES per-year disagreement) directly from `ABS_COMPARISON_NATIONAL.md`, strengthening rather than padding the section. References Fig. 3, 5, 7, 8. |
| Usage Notes | full | Covers the abstain-reason/confidence design, the area-over-call practical guidance, the yield-column guidance (both raw and calibrated), the canola-yield-needs-S1 disclosure, the Legume-discrepancy caveat, and the `unsegmented_blob` gap — one paragraph each, per plan §17. |
| Data Availability / Code Availability | partial | Structurally complete but both contain a genuine `[PENDING]` gap (no DOI/repository deposit exists yet) — not a drafting shortfall, a real prerequisite not yet done (`COVERAGE_GAPS.md`). |
| Author Contributions / Competing Interests / Acknowledgements | placeholder | By design — this skill does not generate author information. |

## Deviations from plan-evidence conflicts

None found. Every number in this draft traces to the same evidence base as the RSE manuscript's `CLAIM_SUPPORT_MAP.md`, re-verified where the plan flagged a specific update (canola-yield-S1, 3-groups-vs-9-species — both confirmed current via the 2026-09-04 re-test before drafting, not carried forward from a possibly-stale RSE version).

## Word count vs. plan budget

Total body (Abstract → Usage Notes, excluding Declarations): 5,443 words, against the plan's ~6,600-7,600 estimate. The shortfall is entirely in Methods and Technical Validation's soft-budget sections, both already fully covering their planned content (see rows above) — this is not a completeness gap, and no content was cut to hit a target. If a reviewer wants more Methods depth (e.g., a fuller reproducibility walkthrough), there is real room to expand within Scientific Data's unlimited Methods length; this was not done speculatively in a first drafting pass.
