# Draft README, paddock-species Scientific Data manuscript

**Updated**: 2026-09-12. **Target venue**: Nature Scientific Data (backup ESSD). **Manuscript type**: Data Descriptor.

## Single source of truth

`MANUSCRIPT_DRAFT.md` is the manuscript. Edit it directly. There is no assemble step: the
per-section `sections/` and `sections_revised/` folders were the 2026-09-04 first draft and were
deleted on 2026-09-11, along with the 2026-09-04 review-round artifacts and both `paper-covert`
submission packages. All of it is in git history if it is ever wanted back.

## Status

- Every 2024 national number is from the final 2024 map (`national_2024_crops_final.gpkg`, 1,010,627 polygons) and the adopted nine-index classifier (macro F1 0.890 / 0.892).
- `XXX` marks a value still pending: the 2017-2023 and 2025 national runs, the consensus layer, the dataset DOI, the code repository, the GRDC request form and a few citations. `COMMENT_RESPONSES.md` lists them.
- The user's bracketed comments have been addressed in three rounds, all recorded in `COMMENT_RESPONSES.md`. No square brackets remain in the draft.
- House style follows `~/Projects/shelterbelts2/WRITING_STYLE.md`: sentences under 25 words, no em-dashes, no semicolons, no Oxford commas, passive Methods, Australian spelling.

## Figures

Numbering in the draft: 1 pipeline, 2 study area, 3 national map, 4 confusion matrices, 5 ABS validation, 6 yield (cereal and legume), 7 national multi-year. The gate trade-off figure is dropped. The files in `output/figures/` still carry the old numbers and most need regenerating from the final map (`COMMENT_RESPONSES.md`, Figures).

## Before submission

1. Finish the 2017-2023 and 2025 national runs and the consensus layer, then fill every XXX.
2. Regenerate Figs 2-5 and 7 from the final products.
3. Deposit the data and code and add the DOIs.
4. Confirm the flagged citations.
5. Re-run `paper-covert` to rebuild the LaTeX/PDF/DOCX submission package from this draft.
6. Send the manuscript to GRDC for sign-off (data-use agreement).

## Other files in this folder

`COMMENT_RESPONSES.md` — every bracketed comment the user has left on the draft, with what was
done or the answer, plus the running list of outstanding `XXX` values.
