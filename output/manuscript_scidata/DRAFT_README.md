# Draft README, paddock-species Scientific Data manuscript

**Updated**: 2026-09-11. **Target venue**: Nature Scientific Data (backup ESSD). **Manuscript type**: Data Descriptor.

## Single source of truth

`MANUSCRIPT_DRAFT.md` is the manuscript. Edit it directly. The `sections/` and `sections_revised/` folders are the 2026-09-04 first draft and are stale. There is no assemble step for this manuscript (the RSE manuscript's `assemble.py` was deleted with that draft on 2026-09-11).

## Status

- Every 2024 national number is from the final 2024 map (`national_2024_crops_final.gpkg`, 1,010,627 polygons) and the adopted nine-index classifier (macro F1 0.890 / 0.892).
- `XXX` marks a value still pending: the 2017-2023 and 2025 national runs, the consensus layer, the dataset DOI, the code repository, the GRDC request form and a few citations. `COMMENT_RESPONSES.md` lists them.
- The user's 2026-09-11 bracketed comments were all addressed on 2026-09-11. Responses, and answers to the questions among them, are in `COMMENT_RESPONSES.md`.
- House style follows `~/Projects/shelterbelts2/WRITING_STYLE.md`: sentences under 25 words, no em-dashes, no semicolons, no Oxford commas, passive Methods, Australian spelling.

## Figures

Numbering in the draft: 1 pipeline, 2 study area, 3 national map, 4 confusion matrices, 5 ABS validation, 6 cereal yield, 7 national multi-year. The gate trade-off figure is dropped. The files in `output/figures/` still carry the old numbers and most need regenerating from the final map (`COMMENT_RESPONSES.md`, Figures).

## Before submission

1. Finish the 2017-2023 and 2025 national runs and the consensus layer, then fill every XXX.
2. Regenerate Figs 2-5 and 7 from the final products.
3. Deposit the data and code and add the DOIs.
4. Confirm the flagged citations.
5. Send the manuscript to GRDC for sign-off (data-use agreement).

## Other files in this folder

`ABSTRACT_DRAFT.md`, `CLAIM_SUPPORT_MAP.md`, `COVERAGE_GAPS.md`, `CITATION_GAPS.md`, `SECTION_NOTES.md`, `REVISION_NOTES.md`, `REVIEW_REPORT.md`, `MAJOR_ISSUES.md`, `MINOR_ISSUES.md`, `REVISION_LOG.md`, `NEXT_LOOP_PRIORITIES.md`, `SECTION_REVIEW_NOTES.md`, `JOURNAL_FIT_NOTES.md`, `CLAIM_RISK_REPORT.md` and `REVIEW_LOOP_STATE.json` are from the 2026-09-04 draft and review round. They predate the 9 km map and the adopted classifier.
