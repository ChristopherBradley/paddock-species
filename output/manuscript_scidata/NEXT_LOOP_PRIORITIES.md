# Next Loop Priorities (Scientific Data manuscript)

No unresolved Major or Moderate issues carry over from Round 1 — all were fixed (`MAJOR_ISSUES.md`, `MINOR_ISSUES.md`). One Minor (no References section) is correctly deferred, not carried over as an open defect.

## What should trigger the next round

Same two triggers as the sibling RSE manuscript's own `NEXT_LOOP_PRIORITIES.md`, since both describe the same underlying dataset:

1. **E8 completes** (national multi-year run, 2/9 years done as of this round) — replace every `[PENDING: national 2017-2025 multi-year run]` marker in Data Records and Technical Validation with real numbers, then re-run this review loop over the changed sections.
2. **`PAPER_PLAN.md` (RSE) §24 Open Issue #8 is resolved** — if the leading classifier candidate is ever adopted, this manuscript's §24 point 6 scoping decision (exclude it entirely) would need to be revisited: either the "shipped model" description throughout Methods/Data Records/Technical Validation changes to describe the newly-adopted model, or this manuscript stays describing the previously-shipped model as a versioned prior release. Not a decision to make now.

## Independent of the two triggers above — real, not-content-related blockers

1. **Dataset and code deposit** (DOI) — blocks actual submission, not drafting.
2. **GRDC pre-submission sign-off** — standing requirement, not yet done for either manuscript.
3. **No review-loop-independent packaging step has been run yet** (no `paper-covert`-equivalent for this venue) — the RSE manuscript's `output/submission/` package should not be reused for Scientific Data without rebuilding: different section structure, different citation style, different declarations.

## Recommended focus for the next actual round of this loop (once triggered)

1. Re-score all 6 dimensions post-fix (this round didn't commission a second cold read, same reasoning as the RSE manuscript's round 1: each fix mechanically addresses its named issue).
2. Once E8/Open Issue #8 resolve, re-run the terminology/figure-reference consistency check, since national-scale numbers will interact with the regional framing throughout Data Records and Technical Validation.
3. Consider whether to build the ESSD-structure conversion (`PAPER_PLAN_SCIDATA.md` §19's mapping table) at that point, if RSE review outcomes make Scientific Data's fit look weaker than expected.
