# Responses to the bracketed comments in the 2026-09-11 draft

Every square bracket in the annotated draft (commit 2e27603) is listed here with what was done or the answer. The revised draft has no square brackets. XXX marks a number or citation that is still pending, listed in the last section.

Numbers come from the final 2024 map after today's overlap merge and 300 ha cap (`output/MAP_COMPARISON_3KM_VS_9KM_2024.md`, `ABS_COMPARISON_NATIONAL_2024_9km.md`, `WORLDCEREAL_COMPARISON_2024_9km.md`, `NLUM_COMPARISON_2024_9km.md`, all regenerated this afternoon on `national_2024_crops_final.gpkg`). The RSE draft was read from git (commit ecaa045) rather than restored, so nothing needed deleting again. Its numbers were one step behind these (1,158,824 polygons, over-call 1.18x) because it predates the overlap merge.

## Abstract

| Comment | Response |
|---|---|
| XXX polygons | 1,010,627 polygons, 429,951 classified. |
| Will add some details about the time-series here once it's done | Written as two sentences with XXX for the consensus-layer count. |
| The total canola area agrees with ABS [to some degree] | Canola share r = 0.76 across 151 SA2s, median absolute error 4.3 points. The canola *area* is not compared directly, the composition is. |
| It agrees with WorldCereal [to some other degree] | Crop presence agrees at 76.1% of 250,000 sampled centroids. |
| Did we manage to reduce the overcall by fixing the overlap issue? | Yes. 1.47x on the 3 km map, 1.31x on the 9 km map before de-duplication, 1.18x after the tile-boundary step, 1.10x after today's overlap merge and 300 ha cap. Written into Technical Validation. |
| Quantitative comparison against Fields of the World? | Only a small one exists: one Yorke Peninsula site plus four trial sites (`PADDOCK_BOUNDARY_BENCHMARK.md`). At the site, FTW merged the trial paddock with two neighbours (339 ha against 57 ha from SAM) and 79% of FTW polygons in the 3 km AOI were slivers under 1 ha. This is in Methods (Segmentation) as a one-site comparison. It is not in the abstract, since n is too small to call it a benchmark. A proper comparison would need the FTW product over a few hundred 2024 trial paddocks, which the existing `ftw_fetch.py` could pull for 0 SU. |

## Background & Summary

| Comment | Response |
|---|---|
| First sentence on the positives of the grains industry, then data importance, then the gap | Rewritten in that order. No production figure is quoted because none was verified. If you want one, ABARES Australian Crop Report gives national tonnes and value. |
| Focus on what exists, availability of these datasets | WorldCereal is downloadable (CC BY 4.0). The two Australian studies trained on non-public labels (confirmed from the PDFs, `LIT_REVIEW_REPORT.md`). Whether their classified maps were released could not be confirmed from here (MDPI and Elsevier both block fetches from gadi), so the draft says "we could not find a public release of either classified map". Please check the two PDFs in `extra papers/` on your laptop. |
| Don't sound like bashing other work | Paragraph 3 now only describes what this dataset does. |
| Better term than "green-up intensity" | "Seasonal NDVI amplitude", which is what the field `ndvi_amp` is. |
| Too many adjectives in the closing paragraph | Rewritten. |

## Methods

| Comment | Response |
|---|---|
| Two main units: polygon count and area | Stated in Study extent. |
| NVT obtained on XXX date, XXX trial sites reduced to XXX | 1 May 2025 (from the file name, please confirm), 4,502 trials of which 4,479 have valid coordinates, 3,439 with a matched paddock, 2,194 used for training and testing (585 canola, 1,119 cereal, 490 legume). |
| Move the data-use sentence to Data Availability | Moved. The request form URL is XXX. |
| What is SA2? | Defined at first use as Statistical Area Level 2, the smallest region for which ABS publishes sown area. |
| SAM text belongs in Segmentation | Moved. Segmentation now also covers the tile overlap, the boundary merge and today's overlap merge. |
| Something about how paddocks were marked as abstained | New subsection "Abstention rules" with the four reasons and thresholds (5 ha, 300 ha, 10 clear observations, NDVI amplitude 0.35). Placed after Yield estimation, which is where you asked the presence-gate sentence to go. |
| 77.9% / 65% / 22% sentence based on AgriWebb? | Yes, the 65% pasture rejection was measured on AgriWebb grazing paddocks. Removed. Replaced with the NVT-only figure: 80.4% of the 270 trials sown in 2024 fall inside a segmented polygon and 76.3% inside one that passed the filter. |
| Feature sentence split into 10-25 word sentences | Done. 153 features = 9 indices x (13 twenty-day bins + p10 + p90 + amplitude + peak day). |
| "Enclosing" polygon, or was nearest removed? | The matcher still does both: containing polygon first, else the nearest polygon within 50 m (`extract_paddock.py`, `--max-dist-m 50`). The "upgrade to a bigger neighbour" rule is also still active (matches under 10 ha move to a paddock-shaped neighbour at least 3x larger within 150 m). What was switched off is only the variant that blocked an upgrade onto a polygon another crop had claimed. The draft describes the rules as they run. |
| Species per group already specified? | Yes, in Background paragraph 3. Not repeated in Labelling. |
| Is 69% correct? | 69% is the share of same-year shared-paddock conflicts that the three-group collapse resolves (540 of 788), not a sample-size increase. Reworded. |
| Is 82% from the latest 153-feature model? | No. 82% was the three-index model. The adopted model is 0.890 temporal / 0.892 spatial. The nine-species figure was 0.38 (not 32%), against 0.78 for three groups on the same trials and features (`LABEL_QUALITY.md`). |
| Hand review only established rules, no relabelling | Written that way: the review of 96 matches set the shape and size rules and changed no labels. |
| Remapping rule removed in the latest version? | The road-verge upgrade rule is still in the code and was used for the training labels, so it stays in the draft (one sentence). |
| Number of features, drop "hand-built" | 153, no "hand-built". |
| Anything else we trialled? | Random forests, extra trees, logistic regression, Presto embeddings and Sentinel-1 as extra features. Numbers are in Technical Validation. |
| Should we have tuned hyperparameters? | Not done. All arms used scikit-learn defaults. A small grid over learning rate, leaf count, regularisation and iterations on the temporal split would cost about 1 SU and is safe because the 543 test rows are held out. Gains for gradient boosting at ~2,000 rows are usually a point or two of F1. It would be an honest improvement to try before submission, but the paper is correct as written. |
| "Shipped", move the presence gate after yield | "Shipped" removed everywhere. The gate is now in "Abstention rules" directly after Yield estimation. |
| Phenology gate not interesting | The gate experiment is gone from Methods, Technical Validation and Code Availability. The released file still carries the `no_crop_shape` flag (105,627 polygons before the merge), so Data Records describes it in two sentences as a quality flag that keeps the class. If you would rather strip that column before release, delete those two sentences. |
| Yield feature count | 51 (the yield model still uses the three original indices). |
| Did the calibration change with the latest model? | No. The yield model was not refitted, so 0.6248 and the +18.1% / +3.1% checks stand. |
| Canola and legume yield no better than a state-year average, is this correct? | Canola: yes (spatial R² 0.271 against 0.290 for the year-and-state mean). Legume: no legume yield model was ever fitted, so the draft says "Legume yield was not modelled". |
| A graph of the cereal yield correlation | Fig. 6 (was Fig. 8) shows R² by arm and the calibration check. A predicted-versus-observed scatter of the 1,119 trials is possible without exposing sites if drawn as a hexbin density rather than points. Not made yet, flagged as a next step. |
| Validation protocol: sentence length, punctuation, "genuine", hyphens, SA2, stale polygon count | Rewritten. 151 SA2s (not 133), 250,000 of 1,010,627 centroids. |
| Multi-year: describe the final product, not a pilot | Methods now has "Multi-year processing" (same grid, no refitting, IoU 0.5 matching, consensus layer). Technical Validation has a national multi-year section and Table 8 with XXX cells. |

## Data Records

Restructured to Product 1 (nine annual national GeoPackages, one schema, Table 1 with the 2024 row filled) and Product 2 (one consensus GeoPackage with `crop_<year>` and `conf_<year>`). Field list taken from the columns of `national_2024_crops_final.gpkg`. The Riverina companion product and the "planned update" section are gone.

## Technical Validation

Every number updated to the adopted classifier and the final 2024 map. New subsection "Map accuracy at trial sites" from `VALIDATION_9KM.md` (macro F1 0.898 at 349 scored test sites with a temporal-holdout copy of the classifier), which validates the released pipeline rather than the feature-level model.

## Author contributions

Mapped to CRediT terms: ideas = conceptualisation, coding = software, writing = writing (original draft), editing = writing (review and editing). I added formal analysis, data curation and visualisation for C.B. and supervision for J.O.B. Remove any you disagree with.

## Figures

Renumbered so first mentions run in order and the gate figure is dropped:

| New | Old file | Note |
|---|---|---|
| Fig. 1 | Fig01_hero | unchanged |
| Fig. 2 | Fig02_study_area | regenerate with the 9 km tiles and 151 SA2s |
| Fig. 3 | Fig04_national_map | regenerate from the final map |
| Fig. 4 | Fig03_confusion_matrices | regenerate for the adopted classifier |
| Fig. 5 | Fig05_abs_validation | regenerate from the final ABS report |
| Fig. 6 | Fig08_yield_summary | unchanged numbers |
| Fig. 7 | Fig07_multiyear_regional | becomes the national multi-year figure once the runs finish |
| dropped | Fig06_gate_tradeoff | gate experiment removed from the paper |

## Still XXX in the draft

- Consensus-layer paddock count and every multi-year number (Table 8, Technical Validation, Abstract).
- Dataset DOI and repository, code repository, GRDC request form URL, Earth Engine asset path.
- GRDC NVT guideline citation for the same-crop paddock rule.
- PaddockTS software citation.
- Three references to confirm: ABARES NLUM v7 (title, DOI), Sulik and Long (2016) as the NDYI source, Tian et al. (2022) as the CFI source, Wu and Osco (2023) for samgeo, and the Kerner et al. (2024) author list.
- Whether Sharma et al. (2026) and Al-Shammari et al. (2024) released their classified maps.
