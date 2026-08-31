# Section Notes

Per-section scope decisions, softened claims, and deferred content.

## Abstract
Included one clause on the WorldCereal/NLUM corroboration (E9) in the main results sentence, kept brief per `PAPER_PLAN.md` §23's instruction not to over-promote secondary findings in the abstract — it appears as supporting evidence for the presence-detection diagnosis, not as a standalone headline claim. Did not include any multi-year national language, per E8 being unrun.

## 1. Introduction
Numbered contributions in prose (not a literal numbered list) to match RSE's typical Introduction style, but map one-to-one onto `PAPER_PLAN.md` §5's primary/supporting contribution structure. E9 not mentioned in the Introduction at all — it is validation evidence, introduced in Results/Discussion, not a contribution claimed up front.

## 2. Related Work
Followed the four-cluster structure from `PAPER_PLAN.md` §15 exactly, added a short 2.5 "positioning" paragraph and a closing note on Newman & Furbank's data lineage (per the resolved citation-handling instruction, framed as shared lineage only, never as an independent source).

## 3. Study Area and Data
Split NLUM's two distinct uses (coverage mask during national inference vs. independent post-hoc comparison product) explicitly, since conflating them would be a real evidence-source error — same underlying file, two different roles.

## 4. Methodology
Section 4.6 (Validation protocol) is where the E9 methodology (WorldCereal/NLUM sampling, enrichment-ratio construction, the springcereals zero-coverage finding) was folded in — placed in Methods rather than Results because it describes *how* the comparison was built, consistent with the skill's Methods/Results separation ("do not include runtime numbers... those belong in Results").

## 5. Results
Organized by experiment/claim (5.1-5.7), not by figure, per the skill's Results guidance. 5.5 is the new subsection carrying the E9 findings. The `[PENDING — depends on E8]` block at the end of the Results section mirrors `PAPER_PLAN.md` §11's own pending list verbatim in intent, not fabricated wording.

## 6. Discussion
6.3 (Presto) and 6.4 (abstain-reason design / AgriWebb retirement) are both explicitly framed as explaining a design decision rather than a standalone headline claim, per `PAPER_PLAN.md` §5's instruction for the "secondary/supporting findings." 6.1 was written to lead with the E9 corroboration as the *third* independent line of evidence for the presence-detection diagnosis (after composition/area divergence and cross-scale reproduction) — this is new relative to `PAPER_PLAN.md` §16, which was written before E9 existed, and is the most substantive integration of the E9 result into the paper's actual argument.

## 7. Limitations and Future Work
Limitations 1-7 mirror `PAPER_PLAN.md` §17's original numbered list one-to-one, in the same severity order. Limitations 8 and 9 are additions, not present as numbered items in the plan: Limitation 8 (ABS reference uncertainty / not an Olofsson-style stratified estimate) states explicitly, as a first-class limitation, a point the plan only made in passing (§2.4 Related Work, §4.6 Methods) — worth promoting to the Limitations list itself rather than leaving it implicit. Limitation 9 (WorldCereal/NLUM caveats: year mismatch, sampling, WorldCereal class coverage) is new because E9 didn't exist when the plan was written. Future-work item 2 (E9 spatial comparison) was in `PAPER_PLAN.md` §17 as "not started, single most reviewer-obvious addition" — since E9 is now done, this was replaced with "extend to full population / additional products" rather than removed outright, since the underlying limitation (sampled, not census; one reference year) is still real.

## 8. Conclusion
Explicitly states that this manuscript is intended to inform the ongoing colleague discussion about validation methodology before E8 proceeds — this is user-supplied context for this drafting pass (not written into `PAPER_PLAN.md` itself), included because it is true and relevant to how a reader should weight the "open threads" framing, not because a manuscript would normally state its own internal review process. **Flag for the user**: consider whether this sentence belongs in a version of the manuscript that eventually goes to actual journal submission — it may read as appropriate for an internal/colleague-facing draft but not for a final RSE submission, and should probably be trimmed or reworded once the colleague discussion has happened. See `REVISION_NOTES.md`.

## Declarations
GRDC pre-submission sign-off requirement stated explicitly in Data and Code Availability, per the standing project requirement — this is unusual content for a Data Availability Statement but reflects a real, non-optional constraint on this specific manuscript.
