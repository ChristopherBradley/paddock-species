# Revision Log — Round 1 (2026-09-04)

Keyed to `MAJOR_ISSUES.md` / `MINOR_ISSUES.md` issue ids.

## M1 — Built Tables 2-5

- **Table 2** (`sections/06_results.md` §5.1): classifier precision/recall/F1 by class, both splits. Source: `output/arms/GROUP3_reviewed.md` (the exact file the manuscript already cites as having regenerated Fig. 3 from).
- **Table 3** (§5.2): ABS validation summary (ABS/diluted/mapped/absorbed shares by class, r/MAE, area over-call, ABS/ABARES floor). Source: `output/ABS_COMPARISON_NATIONAL.md`.
- **Table 4** (§5.4): presence recall by crop, three phenology-shape gate configurations. Source: `output/PHENOLOGY_GATE.md` ("Stacked with amplitude" table). Caption added a clarifying note that none of the three configurations is the actually-shipped design (amplitude gate alone) — the source file's own "baseline (shipped)" label refers to the shape-gate experiment's baseline threshold, not the production pipeline, a naming collision worth flagging so a reader isn't misled.
- **Table 5** (§5.7): Cereal yield model R²/RMSE by split and arm, plus the calibration factor. Source: `output/YIELD_cereal_pooled.md`.

All four tables use only numbers already stated in the manuscript's own Results prose or directly present in the cited source file — no new analysis, no fabrication.

## M2 — Reconciled Table 7 vs. Table 8

Added one sentence to Table 7's caption (`sections/07_discussion.md` §6.5) explaining that its 0.887/0.886 baseline is the candidate scored on the Sentinel-1-matched row subset (2,133 trials), distinct from Table 8's full-population 0.890/0.892 (2,194 trials) — both correct for their own comparison.

## M3 — Added the missing Legume Discussion point

New `## 6.7 The Legume classification error remains open` appended to `sections/07_discussion.md`, stating the finding plainly per `PAPER_PLAN.md` §16 point 3. Appended rather than inserted mid-sequence to avoid cascading renumbering risk across the many existing cross-references to §6.1-6.6. Cross-links added: Results §5.3 and Limitations item 2 now both point to §6.7.

## M4 — Added the ABS/ABARES floor caveat

- Abstract (`sections/01_abstract.md`): added "below the 6.8% floor set by ABS's own disagreement with a second official series" to the MAE claim; trimmed elsewhere to hold the abstract at 250 words (see Mod2).
- Results §5.2 (`sections/06_results.md`): added the same floor clause with a cross-reference to §3.3.

## Mod1 — Highlights character limits

Trimmed bullet 1 ("10 m crop-species map" → "10 m crop map") and bullet 5 ("presence-detection diagnosis" → "presence diagnosis") to 80 and 76 characters respectively (both were over RSE's 85-char limit).

## Mod2 — Abstract word count

Combined with the M4 addition; net effect after trims (removed "crop-mapping"/"crop-type" redundancy, shortened the closing sentence, tightened the over-call clause) is exactly 250 words, at the plan's target ceiling.

## Mod5 — Abstract precision wording

"classifier trained on 2,194... records" → "classifier built from 2,194... records," since 2,194 is the total labelled population (≈1,651 train + 543 held-out test), not literally the training set alone.

## Min1 — COVERAGE_GAPS.md bookkeeping

Corrected the stale claim that Table 6 "is not referenced in the draft" (it is, correctly, inside the `[PENDING: E8]` block).

## Reassembly

`MANUSCRIPT_DRAFT.md` was fully regenerated from the current `sections/*.md` (rather than patched with targeted string edits, given the number and spread of changes) via a Python script that strips each section's YAML front matter and reassembles with the original title block and `---`/`---` separators. Verified: all 8 tables present and correctly numbered, no orphaned `Section 6.5`/`6.6` cross-references, no leaked candidate-model numbers outside Discussion/Limitations/Conclusion. Word count: 9,237 (2026-08-30 v1.0) → ~10,150 (2026-09-03, post-findings-fold-in) → 11,159 (2026-09-04, post-review-fixes, driven almost entirely by the four new tables plus §6.7).

`sections_revised/*.md` created as a mirror of the current `sections/*.md` for this round, since fixes were applied directly in place (a deviation from this skill's stated convention of writing only to `sections_revised/`, made deliberately given the fast-turnaround, single-session context this loop ran in — noted here rather than silently departed from).
