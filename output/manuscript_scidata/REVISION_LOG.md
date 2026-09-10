# Revision Log — Round 1 (2026-09-04, Scientific Data manuscript)

Keyed to `MAJOR_ISSUES.md` / `MINOR_ISSUES.md` issue ids.

## M1 — Abstract subject-mismatch fix

`sections/01_abstract.md`: "Mapped canola composition tracks independent ABS sown-area statistics closely (r = 0.82) and is corroborated by independent spatial comparison against WorldCereal and the National Land Use Map" → "Mapped canola composition tracks independent ABS sown-area statistics closely (r = 0.82); this dataset is further corroborated by independent spatial comparison against WorldCereal and the National Land Use Map, and discloses and quantifies a known area over-call...". Word count unchanged (166/170) — this was a subject-clause reword, not an addition.

## M2 + Mod2 — Gate-comparison table and prose fix

`sections/03_methods.md` (Presence gating):
- Prose: replaced "reduced stacked Canola presence recall from 94.5% (amplitude-only) to 78.3%, while leaving Cereal and Legume recall essentially unchanged (91.4% and 87.2% respectively)" with explicit per-crop deltas — Cereal 96.0%→91.4% (−4.6 pts), Legume 91.3%→87.2% (−4.1 pts) — plus the correct framing that Canola's 16.2-point drop is disproportionately larger, not that the other two are unaffected.
- Table: filled in the amplitude-only row's Cereal (96.0%) and Legume (91.3%) cells, sourced from `PHENOLOGY_GATE.md`'s "Recall by crop" table (2,177-trial deployable-variant population, the same population the other rows use). Left "Pooled recall" as an explained dash rather than fabricating a weighted average not directly reported at this population. Added "(stacked)" qualifiers to the other three rows' labels for clarity, since the table mixes an amplitude-only-alone row with three amplitude+shape-stacked rows.

## Mod1 — Population-size reconciliation

`sections/03_methods.md` (Presence gating): added one sentence explaining why the presence gate is fitted on 3,439 trials while the classifier/yield models use 2,194 — presence gating only needs to know a trial was sown (not its species), so a larger, less strictly labelled population qualifies.

## Mod3 — Cereal yield S1 gain number added

`sections/03_methods.md` (Yield estimation): added "Sentinel-1 backscatter improves this model too — spatial-transfer R² rises by +0.092 when added to the operational satellite-plus-year/state feature set — but is not yet included, for the same national acquisition-cost reason given below for canola." Per `PAPER_PLAN_SCIDATA.md` §9 point 5, which specified this number but it had not made it into the drafted prose.

## Mod4 — Long-sentence splitting

`sections/03_methods.md`: split the ~115-word Labelling justification sentence into three shorter sentences (no content removed), and the ~110-word canola-yield sentence in Yield estimation into three shorter sentences (no content removed).

## Min1 — `confidence` null-handling

`sections/04_data_records.md`: added "; null where `pred` is null, since a polygon that did not clear the presence gate was never scored by the classifier" to the `confidence` field description.

## Min2 — Usage Notes cross-reference fix

`sections/06_usage_notes.md`: "Technical Validation's sensitivity table (available in the accompanying validation reports, Code Availability)" → "Technical Validation's sensitivity table" (the table is printed directly in this manuscript's Technical Validation section, not an external report).

## Reassembly

`MANUSCRIPT_DRAFT.md` fully regenerated from `sections/*.md` (same reassembly script used for the 2026-09-04 first-draft pass and the RSE manuscript's own review-loop round). Verified post-reassembly: both critical checks clean (no candidate-model leak; no "we show/we find" language), both hard word limits compliant (166/170, 579-581/700), all 8 figures correctly referenced. Word count: 5,791 (first draft) → 5,976 (post-review-loop, +185 words from the fixes above, none of it padding — every addition traces to a named issue). `sections_revised/*.md` created as a mirror of the current `sections/*.md`, consistent with the same convention already documented for the RSE manuscript's review-loop round 1.
