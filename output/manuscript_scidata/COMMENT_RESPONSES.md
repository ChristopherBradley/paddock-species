# Responses to the bracketed comments on the Scientific Data draft

Every square bracket the user has left on `MANUSCRIPT_DRAFT.md` is listed here with what was done
or the answer. The draft itself carries no square brackets. `XXX` marks a value still pending;
the outstanding list is at the very bottom.

---

# Round 2 — comments on the 2026-09-11 draft (answered 2026-09-11, evening)

Three of these were requests to run something, not to edit text. All three were run, and the
results are in `output/HYPERPARAMETER_TUNING.md`, `output/YIELD_GROUP3_9INDEX.md` /
`output/YIELD_GROUP3_3INDEX.md`, `output/GROUP3_MODEL_sharma6_only.md` and
`output/FTW_COMPARISON.md`.

## Background & Summary

| Comment | Response |
|---|---|
| Do we grow all 4 of those in the Northern Territory? | No, and "every mainland state" was a weak claim anyway: the NT is a territory, not a state, and canola is negligible in Queensland. The sentence now names the belt geographically ("from central Queensland through New South Wales, Victoria and South Australia to Western Australia"), which is both accurate and more informative. |
| Is "the models were not trained on any Australian data" correct? | Not verifiable as written, so it has been replaced with a claim that is. WorldCereal's own reference-data paper (Boogaard et al., 2023, PLOS ONE) lists Australia among the continents with large remaining spatial gaps, and the public CC-BY reference repository on Zenodo contains no Australian dataset. The draft now says the reference data "records a large gap over Australia (Boogaard et al., 2023)", which is checkable and makes the same point. Australia is mentioned in the WorldCereal paper only under *irrigation* training samples, so a flat "no Australian data" would have been too strong. Boogaard et al. added to the reference list. |
| Confirm from the papers that the maps were not released publicly | Confirmed, from each paper's own Data Availability statement (both PDFs read from `Papers/`). Sharma et al. (2026): "The datasets presented in this article are not readily available because the crop data are proprietary and provided as a commercial product." Al-Shammari et al. (2024): "The data that has been used is confidential." Neither paper links a map release, and Sharma's only supplementary material is two tables (composite dates, index formulas). The draft now quotes both statements in substance instead of saying "we could not find". |
| Tile count not important | Removed. |

## Methods

| Comment | Response |
|---|---|
| 25% is a pretty stringent threshold | It reads stringent but is not, and the draft now says why. A tile survives if *any one* of its 1,296 NLUM pixels clears 25%, so at 9 km the rule is permissive. The check that matters is the outcome: the map calls 1.10x as much land crop as ABS, so tile selection is not cutting real cropping out. Confirmed in code that the national grid used `nlum_tiles.py --threshold 2500` on the 0-10000 probability scale, i.e. 25% exactly as written. |
| Not important how many had invalid coordinates | Bracket removed; the count was already gone. "with valid coordinates" is kept as it explains why the number is 4,479, without dwelling on it. |
| Be careful about the Newman and Furbank paper | It was not cited anywhere in the body, but it was still sitting in the reference list as an orphan entry. Removed. Nothing in this manuscript now points at it. (Note for the record: `PAPER_PLAN.md` §24 records that citing it was approved on 2026-08-29 under the signed GRDC agreement, so this is your call to reverse if you ever want it back. The manuscript still needs GRDC pre-submission sign-off either way.) |
| ABS + ABARES + NLUM + WorldCereal = 4 right? | Right. Four independent comparison products, WorldCereal is the fourth. Bracket removed, no change. |
| The tile-overlap sentence is too confusing; don't overdescribe the merge | Cut to two plain sentences: neighbouring tiles overlap, so an edge paddock is segmented more than once, and duplicate or part-cut polygons were merged into one. The 350 m figure is gone. |
| 300 ha explained twice | The second explanation is removed; the rule is stated once, in the retention paragraph. |
| Reader only cares about the final production index set | Bracket removed; the "original set" framing was already gone. |
| Check the NDYI reference matches the equation | It does. The code computes `(green - blue) / (green + blue)` (`extract_paddock.py:71`), which is the Normalised Difference Yellowness Index of Sulik and Long (2016). Also fixed a malformed fragment on the same line: "(CFI, Tian et al., 2022)" had lost its name and now reads "the canola flowering index (CFI, Tian et al., 2022)". Tian et al. (2022) is confirmed as *A Novel Spectral Index for Automatic Canola Mapping by Using Sentinel-2 Imagery*, Remote Sensing 14(5), 1113 — the CFI source. The implemented formula is PaddockTS's `NDVI * ((Red + Green) + (Green - Blue))`; MDPI blocks automated fetches, so the exact equation still wants a manual eyeball against the paper before submission. |
| Did we ever try just the 6 indices without the 3 originals? | No, that arm had never been run. `INDEX_ARCHITECTURE_SWEEP.md` isolated Sharma's six from round 1's five speculative indices, but always alongside the original set. It has now been run (`train_sharma6_only.pbs`, 0.35 SU): the six alone give macro F1 **0.883 temporal / 0.872 spatial** on 102 features, against **0.890 / 0.892** for the adopted nine on 153. So the three originals are worth keeping, mostly for spatial transfer (+0.020). One sentence added to Classification. |
| What was the cloudiness threshold? | A date contributes to a paddock's series only if at least half that paddock's pixels are clear (`n_clear_px / n_px_paddock >= 0.5`, applied in every loader). Stated in the draft now. |
| Is "bare ground" the right terminology? | "bare soil" is the standard remote-sensing term, so the sentence now reads "carries bare soil between plots". The sentence was also rewritten to fix "the the" and to drop the claim that SAMGeo found the trial site, which overstates it. |
| Is 15 clear observations the right time period? | Yes, and it is year-round, not season-only: the labelling keep-arm uses `min_obs 15` across the calendar year (confirmed in `canola_flowering_audit.py`, which calls it "the year-round `min_obs 15` filter"). The draft now says "across the calendar year" so it cannot be read as a within-season count. Note this is a different threshold from the map's own abstention rule, which is 10 clear observations. |
| 96 is close enough to round to 100 | Kept at the exact **96**, which is what the review actually covered and is no longer to write than "100". Easy to change back if you prefer the round number. Also fixed the missing "of": it read "a hand review 100 sample sites". |
| The reviewer sentence was unnecessary | Agreed and already gone; bracket removed. |
| Is (1)/(2) an OK way to number? | Fine for Scientific Data, but it reads better as prose at this length, so it is now "First, ... Second, ...". |
| Is 588 the correct number? | No. Recomputed directly from `paddock_conflicts_SENSITIVE.csv`: collapsing nine crops to three groups resolves **540** of **788** same-year shared-paddock conflicts (68.5%, so "69%" stands) and returns exactly those 540 trials to the training set. 588 does not correspond to anything in the data. Corrected. |
| Nice end to the paragraph | Kept as is. |

## Classification

| Comment | Response |
|---|---|
| Please try fitting hyperparameters. I'm hoping that doesn't help | **It doesn't help.** Full result in `output/HYPERPARAMETER_TUNING.md` (`tune_hyperparams.pbs`, 288 configurations, 80 min, ~16 SU). Tuned scores **0.8777** on the temporal holdout against **0.8904** adopted, so it is 0.013 *worse*; a paired bootstrap over the 543 test trials puts the difference at [-0.031, +0.004] and has the tuned model ahead on only 8% of resamples. On the nested spatial split it gains +0.0025, which is nothing. The five outer folds each picked a **different** configuration, which is the clearest sign that the grid was fitting fold noise rather than a setting the data supports. **The 2024 predictions do not need redoing.** Three sentences added to Classification. |
| | Two things worth knowing that came out of this. (1) The draft's claim that hyperparameters "were left at the scikit-learn defaults" was **false** — `train_species.py:643` sets `max_iter=400, learning_rate=0.06`. Corrected to state the real values. (2) `HistGradientBoostingClassifier` is fully deterministic at 2,194 rows, so the usual seed-spread sanity check is exactly 0.0000 and useless here. The bootstrap over test rows replaced it. Curiously, the plain scikit-learn defaults score 0.8922, marginally above the adopted settings, but that gap is inside the same noise band and is not a reason to change anything. |
| Fill in the number of sites the model was evaluated at | **543** held-out trials, the fixed test set in `testkeep_temporal_SENSITIVE.csv`. Written in. |
| Rewrite to talk only about the new model's F1 | Done. It now reads "The classifier reached a macro F1 of 0.890 on the temporal split and 0.892 on the spatial split", with no mention of the superseded three-index model. |

## Yield estimation

| Comment | Response |
|---|---|
| Why wasn't the yield model refitted? Refit with the new indices, try legumes, re-fit canola | All three run in one job (`yield_refit.pbs`, 2 minutes, **1.09 SU**), both feature sets over the same rows and splits, reports `output/YIELD_GROUP3_9INDEX.md` and `output/YIELD_GROUP3_3INDEX.md`. Answers below. It was never refitted simply because the six Sharma indices were adopted for classification and the yield model was not revisited. |
| ... cereal with the new indices | A small gain that does not pay for a reissue: spatial-transfer R² **0.526 -> 0.564** against a year-and-state baseline of 0.294. On the temporal split it is 0.471 -> 0.486. With year and state added to the features the three-index model is actually *ahead* (0.577 against 0.566). The released `yield_tha` column stays as it is. |
| ... legumes | **This is the real finding.** Legume yield had never been fitted, and it is the most predictable of the three groups relative to its baseline: spatial-transfer R² **0.458** against a year-and-state baseline of **0.133**, and 0.426 on the temporal split against a *negative* baseline. The nine indices matter a lot here (0.371 at three indices). One caveat that keeps it out of this release: the five legume species have quite different yields, so part of that R² is the model inferring the species, and the map does not resolve legumes to species. The draft now reports the result and names it as the clearest candidate for the next version. The claim "Legume yield was not modelled because of the high variability between the 5 species" has been removed, since it is no longer true. |
| ... canola against the state-year average | Still does not beat it, on either feature set: spatial-transfer R² **0.299** (nine indices) and **0.284** (three) against a year-and-state baseline of **0.316**. This matches `PROJ_NOTES` 2026-08-31, where the Sharma indices were found to *regress* canola yield. The decision not to publish a canola yield stands. The draft keeps the existing 0.271/0.290/0.371 figures for the Sentinel-1 sentence, since those come from the S1-controlled row set (n=571) and are the right comparator for that specific claim. |

## Abstention rules

| Comment | Response |
|---|---|
| Did we find the `no_crop_shape` flag useful? Was there good evidence either way? | There is good evidence, and it is a genuine trade-off rather than a blank. On the 100 km Riverina pilot the shape gate was the single most effective thing ever measured against the area over-call: median ABS area ratio **1.59 -> 1.00** (loose variant 1.18, two-pass 1.19). It bought that by rejecting real crop. Canola presence recall fell from **94.5% to 78.3%**, cereal by 4.6 points and legume by 4.1 (`PHENOLOGY_GATE.md`). So it was not kept as a gate. What has changed since is that the problem it was solving has largely gone away by other means: the national over-call is now **1.10x** after the 9 km grid, the tile-boundary step and the overlap merge, against the 1.59x the gate was fighting. That weakens the case for reinstating it considerably. The flag itself still rides on the released file (105,627 polygons in 2024) as a quality flag that does not change the class, and Data Records and Usage Notes describe it in that role. Nothing to change in the draft. |

## Segmentation

| Comment | Response |
|---|---|
| Pull a few hundred sites with ftw_fetch and compare against Fields of the World, qualitatively and if possible quantitatively | Done quantitatively, over all **557** NVT trials sown in 2024. See the section below. |

### Fields of the World, quantitatively (557 sites)

`src/paddocks/ftw_compare.py`, new. `ftw_fetch.py`'s own `fetch` selects parquet row groups against
the *overall* bounding box of all sites, which is fine for one site but becomes the whole continent
for 557, selecting 207 of 255 Australian row groups (~272M polygons). Testing each row group's bbox
against the individual site AOIs instead selects 76 (~70M rows), and filtering on the `bbox` struct
columns before building any shapely geometry keeps peak memory at one row group. 49,367 FTW
polygons pulled over 1 km boxes around every 2024 trial, for **13.4 SU**. Full report:
`output/FTW_COMPARISON.md`.

| | FTW | SAM (released map) |
|---|---|---|
| trial point inside a polygon | **90.7%** | 62.5% |
| median area of that polygon | **109.2 ha** | 54.7 ha |
| median FTW/SAM area ratio | **1.49x** (FTW larger at 73% of trials) | |
| FTW at least 3x larger | **32.4%** of trials | |
| median IoU of the two polygons | **0.53** (below 0.5 at 45.5%) | |

The single-site finding generalises: FTW returns a polygon that merges the trial paddock with its
neighbours, at a median 1.5x the area and at 3x or more on a third of trials. What the one-site
check could *not* see is the other half of the picture, and it is the more interesting half. FTW
contains the trial point far more often than the released map does (90.7% against 62.5%), so it is
better at finding *a* paddock and worse at bounding it. That is a real argument for combining the
two rather than choosing between them.

**One comparison in the report is not clean, and the report now says so inline.** The released map
had the compactness filter applied during production, so almost nothing in it fails on shape
(0.15% above compactness 8, and those come from the later merge), while FTW is compared raw. That
makes the "share passing the retention filter" and "share under 1 ha" rows flatter SAM. The
manuscript therefore cites only the containment rate, the area ratio and the IoU, which
pre-filtering cannot distort. The area range is genuinely not pre-filtered: sub-5 ha polygons are
32% of the released file.

Two operational notes, since this will be re-run. The fetch died once on a transient HTTP 503 from
source.coop after 17 minutes of good work, so it now retries with backoff and checkpoints each row
group to a stage directory; a restart resumes. And the compare step reads ~1M SAM polygons and
needs about 8 GB, which a login node will not allow, so it belongs in a PBS job. The PBS script
skips the fetch when the GeoPackage is already present, so re-running the comparison alone costs
no network time.



---

# Round 1 — comments on the 2026-09-04 draft (answered 2026-09-11, morning)

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

## Still outstanding, as of the end of round 2

Values the draft still marks `XXX`:

- Consensus-layer paddock count and every multi-year number (Table 8, Technical Validation, Abstract). These wait on the 2017-2023 and 2025 national runs.
- Dataset DOI and repository, code repository, GRDC request form URL, Earth Engine asset path.
- GRDC NVT guideline citation for the same-crop paddock rule.
- PaddockTS software citation, also referenced from the Segmentation section.
- References still to confirm: ABARES NLUM v7 (title, DOI), Wu and Osco (2023) for samgeo, and the Kerner et al. (2024) author list.

Also open, though not marked `XXX`:

- The Segmentation section still carries `{TODO: John Burley to update this section}`.
- The CFI equation. Tian et al. (2022) is confirmed as the right paper, but the implemented formula comes from PaddockTS and MDPI blocks automated fetches, so the equation itself wants one manual check against the paper.
- The Abstract sits on the Scientific Data 170-word limit (174 by a count that treats numerals as words). Worth a trim pass before submission.

Resolved during round 2, previously listed here:

- Sulik and Long (2016) confirmed as the NDYI source, and the code's `(green - blue) / (green + blue)` matches it.
- Tian et al. (2022) confirmed as the CFI source (*Remote Sensing* 14(5), 1113).
- Whether Sharma et al. (2026) and Al-Shammari et al. (2024) released their maps: neither did, per their own Data Availability statements.
- Newman and Furbank (2021) removed from the reference list; it was never cited in the body.
