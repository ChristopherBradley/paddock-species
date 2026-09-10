# Section Review Notes — Round 1 (Scientific Data manuscript)

Cross-check against `PAPER_PLAN_SCIDATA.md`, adapted from this skill's Phase 3 table for the Data Descriptor format (many of the standard table's rows — Related Work, Discussion, RQs — are N/A by design for this venue, not gaps).

| Plan § | Question | Answer | Severity |
|---|---|---|---|
| §1 Title & claim | Title matches the plan's dataset-first framing? | Yes — Option 1, no coined dataset name. | ok |
| §2 Journal strategy | Tone matches Scientific Data (data-quality description, never "we show/we find")? | Yes, confirmed by grep. | ok |
| §0/§16 Reframing | Discussion-shaped RSE content redistributed cleanly into Methods as design-justification, not left as generalizable findings? | Yes — confirmed by the reviewer's targeted grep for generalizable-lesson phrasing, zero hits. | ok |
| §9 Methods | Specific enough, and does it correctly justify the label-scheme, feature-set, gate, and S1-inclusion decisions? | Was undermined by M1/M2/Mod1/Mod3 (imprecise gate claim, unreconciled populations, missing Cereal-yield S1 number) — all fixed this round. | was major, now ok |
| §19 Manuscript structure | Data Records exists as a genuinely new section (not present in the RSE manuscript's structure)? | Yes — full schema/file description, cross-checked against `FIGURE_MANIFEST.md`'s classified-only-subset warning. | ok |
| §11/Technical Validation | All planned validation procedures (V1-V8) represented? | Yes, all present with real numbers; three extra tables (argmax-vs-mean-probability, threshold sensitivity, ABS/ABARES disagreement) strengthen the section. | ok |
| §12 Claim-evidence map | Every row at the right strength, none overclaimed? | Two rows' manuscript wording outran the map (M1, M2) — both fixed. | was major, now ok |
| §13 Figures | All 8 reused figures correctly placed, none phantom? | Yes, verified by the reviewer against `FIGURE_MANIFEST.md`. | ok |
| §17 Limitations → Technical Validation/Usage Notes | All planned limitations present in their redistributed homes? | Yes — area over-call, Legume discrepancy, `unsegmented_blob`, single-season coverage, no canola/legume yield (with the S1 cause stated), Sentinel-1 exclusion, 3-group descoping all present. | ok |
| §18/Data & Code Availability | Present as named sections, with genuine `[PENDING]` markers for the two real deposit prerequisites? | Yes, not faked. | ok |
| §20 Abstract blueprint | Background → scale → per-record content → validation → reuse value, no findings claims? | Yes; M1's subject-mismatch was the one precision issue, now fixed. | was major, now ok |
| §24 point 6 | Candidate-model exclusion executed, not leaked anywhere? | Confirmed clean by direct grep, independent of drafting. | ok |
| §25 Readiness | Honestly stated as partial, gated on E8 + two deposits + a review pass? | Yes — `DRAFT_README.md` states this accurately. | ok |

## Per-section fidelity this round

- **Abstract**: revised (M1) — one sentence's subject reworded, word count unchanged.
- **Background & Summary**: untouched — no issues found.
- **Methods**: revised (M2, Mod1, Mod2, Mod3, Mod4) — the section carrying nearly all of this round's fixes, since it's where the RSE-Discussion-content redistribution and the gate/S1 justifications live.
- **Data Records**: revised (Min1) — one field-description clause added.
- **Technical Validation**: untouched — no issues found; already the manuscript's strongest section per the reviewer.
- **Usage Notes**: revised (Min2) — one cross-reference simplified.
- **Data Availability, Code Availability, declarations**: untouched — no issues found.
