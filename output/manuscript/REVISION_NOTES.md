# Revision Notes — prioritized next-pass actions

## Fixed this session (2026-09-03, third pass — v1.1 findings folded in)
- Folded 5 post-draft findings (S1 vs. current best classifier/yield model, Sharma6-vs-canola-yield, leading shipped+sharma6 classifier candidate) into Discussion §6.5 (new) and Limitations §7.1/§7.2, per updated `PAPER_PLAN.md` v1.1. Full change list in `DRAFT_README.md`'s new "v1.1 revision" section.
- Renumbered old Discussion §6.5 ("Generalizability across seasons") to §6.6 to make room for the new §6.5; found and fixed 3 forward-references to the old number (Section 3.2/4.6 study-area text, Section 5.6 results text, both in `sections/` and the assembled `MANUSCRIPT_DRAFT.md`).
- Caught and fixed a drafting error mid-pass: an early draft of the new future-work item on national S1-for-yield scale-up cited a nonexistent "crop-identity holdout (Section 5.3)" — Section 5.3 is actually the Legume classification-error subsection, and no AgriWebb-style ordinary-geometry holdout exists anywhere in this manuscript (the project's AgriWebb work is deliberately excluded from the paper per user instruction, per project memory). Corrected to a general statement with no false internal citation.
- Word count grew from 9,237 to ~10,150 (+~910 words), concentrated in Discussion (+~270) and Limitations/Future Work (+~285) plus the two new tables. Abstract, Introduction, Related Work, Study Area, Methods, and Results are untouched.

## Fixed this session (2026-08-30, second pass)
- **Triticale error**: `PAPER_PLAN.md` and two manuscript sections said Cereal = "wheat+barley+oat+triticale." Verified against `train_species.py`'s `GROUP` dict and `nvt_trials_labeled.csv`'s actual crop values (while building the evaluation-sites layer, below): there is no Triticale in the trial data at all — only Wheat, Canola, Barley, Chickpea, Oat, Field Pea, Lupin, Faba Bean, Lentil (9 species, matching the "9-class macro F1 0.38" figure used consistently elsewhere). Fixed to "wheat+barley+oat" in `PAPER_PLAN.md` §7 and manuscript §3.4/§4.2. Also fixed "the original ten-species scheme" (should be nine) in the same two manuscript locations — this one was internally inconsistent with the rest of the document, which correctly used nine-species throughout.

## For the user, before this goes to colleagues
1. **Read Section 8 (Conclusion)'s second paragraph** — it explicitly states this manuscript is meant to inform an ongoing discussion of validation methodology with colleagues before the national multi-year run proceeds. That's accurate and, we think, useful context for colleagues reading a draft rather than a submission-ready manuscript — but flag it if you'd rather that context live in a cover note instead of the manuscript text itself. Easy to remove/move before any eventual journal submission.
2. **The 133-vs-132 SA2 count discrepancy** (Section 3.1, 5.2, Abstract) is used as 133 throughout, per direct re-derivation from the published `ABS_COMPARISON_NATIONAL.md` table. This is a small, honestly-flagged rounding-boundary artifact (see `COVERAGE_GAPS.md`), not something that changes any substantive finding — but worth a five-minute check against `abs_compare.py`'s unrounded intermediate output if you want the number pinned down exactly before this goes further.
3. **Title/framing decision**: used option 1 from `PAPER_PLAN.md` §21 (dataset-and-validation framing). If colleague discussion shifts the paper's emphasis toward the presence-gate methodological finding as the lead story, option 2 ("Segmentability as a Crop-Presence Signal...") might fit better — flagged as a live decision, not settled.

## For the next drafting pass (mechanical, once E8 lands)
1. Fill Section 3.2, 5.6, 7.1, 8, and the Abstract's data-scale sentence with real national multi-year numbers, replacing every `[PENDING: national 2017-2025 run, E8]` marker — these are the only fabrication-risk points in the draft and are all explicitly tagged for exactly this reason.
2. Fill Table 6 (national multi-year summary) and Figure 7's national panel.
3. Re-run the terminology/figure-reference consistency pass (Section 6d equivalent) after those edits, since new national-scale numbers may interact with the existing regional framing in Section 6.6's discussion of weak years (renumbered from 6.5 this pass — see above).

## For the user, before/during `paper-review-loop` (this session, 2026-09-03)
1. **Open Issue #8 is unresolved**: adopt the leading shipped+sharma6 classifier candidate (macro F1 0.890/0.892) before finalizing Results, or keep the current shipped-model draft and report the candidate only in Discussion/Limitations (as this pass did)? Not decided here — flagged for you in `PAPER_PLAN.md` §24 and Limitations item 10.
2. `paper-review-loop` and `paper-covert` are about to run on this v1.1 draft per your instruction, **before** E8 completes — both will need a second pass once E8 lands and/or Open Issue #8 is resolved. Treat their outputs as an interim checkpoint for your review, not a final package.

## Not done in this pass, lower priority
1. Full reference-manager formatting pass for RSE's exact citation style (see `CITATION_GAPS.md`) — mechanical, belongs to `paper-covert`.
2. Word-count trim: current draft (~10,150 words body text) is slightly over `PAPER_PLAN.md` §19's 9,000-10,000 word target after this pass's additions — not urgent (the additions are disclosure, not padding) but worth a look before final submission, especially once E8's Results-section update adds more words on top.
3. `paper-review-loop` has not yet been run on this draft as of this pass — see "For the user" above, it is next in this session.
4. Author list, CRediT statement, competing-interests declaration, and acknowledgements are all placeholders (Section "Declarations") — this skill does not generate author information by design; the user must supply these.
