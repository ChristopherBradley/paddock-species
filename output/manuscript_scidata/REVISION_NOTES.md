# Revision Notes — Scientific Data draft, first pass (2026-09-04)

## For the user, before this goes further

1. **Dataset and code deposits are the real blocker to actual submission**, not manuscript content. Neither Scientific Data nor ESSD will accept a Data Availability/Code Availability statement without a real persistent identifier. Both are marked `[PENDING]` in the draft rather than faked — resolving this is independent of any further drafting work.
2. **`paper-review-loop` has not been run on this draft.** Recommend the same cold-read treatment the RSE manuscript got (a fresh subagent, not the agent that wrote this draft) before treating any section as final — this project's generator-evaluator separation rule applies here too.
3. **Title decision**: Option 1 (`PAPER_PLAN_SCIDATA.md` §21) was used — no dataset name. If a named-dataset framing (Option 3, e.g. "AusCropMap") is preferred, that name needs to be chosen first; not done here to avoid blocking the draft on a naming decision.
4. **GRDC pre-submission sign-off** is required before this manuscript can go to any venue, same standing requirement as the RSE manuscript (`PAPER_PLAN_SCIDATA.md` §24 point 2) — not yet done for either manuscript.

## For the next drafting pass, once E8 lands

1. Fill Data Records' "Planned update" section and Technical Validation's `[PENDING]` block with real national multi-year numbers, replacing the markers exactly as the RSE manuscript's equivalent pass will need to do.
2. Add a national panel description to the Fig. 7 reference once the national multi-year Fig. 7 panel (b) is filled — currently referenced as reserved/blank, matching the actual figure file's current state.

## Not done in this pass, lower priority

1. Full reference-manager formatting pass for the target venue's exact citation style — mechanical, belongs to a `paper-covert`-equivalent step for this venue (not yet run; the RSE manuscript's `paper-covert` output at `output/submission/` should not be reused for this venue without checking — different section structure, different citation style expectations).
2. Word-count check against Scientific Data's actual overall submission-length norms (only Abstract and Background & Summary have hard caps; Methods/Data Records/Technical Validation/Usage Notes have no stated limit, so this draft's 5,443-word body is not a compliance question, just a completeness one — see `SECTION_NOTES.md`).
3. ESSD-specific structural conversion (Background & Summary → Introduction; add a Conclusions section ESSD requires but Scientific Data does not use) — not built in this pass since Scientific Data is the primary target; `PAPER_PLAN_SCIDATA.md` §19's mapping table has the conversion path ready if/when needed.
4. Author list, CRediT-equivalent contributions, competing-interests declaration, and acknowledgements are all placeholders — this skill does not generate author information by design.
