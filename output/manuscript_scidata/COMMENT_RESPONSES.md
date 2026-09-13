# Responses to the bracketed comments on the Scientific Data draft

Every square bracket the user has left on `MANUSCRIPT_DRAFT.md` is listed here with what was done
or the answer. The draft itself carries no square brackets. `XXX` marks a value still pending;
the outstanding list is at the very bottom.

---

# Round 3 — comments on the 2026-09-12 draft (answered 2026-09-12)

The two questions that decide whether to start the 2017-2023 and 2025 runs now are answered
first (sections 1 to 3). Everything else follows in document order (section 4), then the Fields
of the World examples (5) and the confidence-interval guess (6). Runs this round:
`train_rf_9index_legume_species.pbs` (random forests, extra trees, a nine-species model and a
legume-only five-species model, all on the adopted 153 features and the same rows and splits as
the adopted classifier), `ftw_examples.py` on the login node, and three small login-node scripts
(the FTW filter pass, per-species NVT yields, a bootstrap on the SA2 area ratio).

## 1. Random forest on the nine indices: no, keep the gradient-boosted model

| model | features | temporal macro F1 | spatial macro F1 | legume F1 (temporal / spatial) |
|---|---|---|---|---|
| gradient boosting (adopted) | 153 | **0.890** | **0.892** | 0.83 / 0.82 |
| random forest | 153 | 0.857 | 0.852 | 0.77 / 0.76 |
| extra trees | 153 | 0.852 | 0.850 | 0.76 / 0.76 |
| random forest | 51 (three indices) | 0.830 | 0.820 | |
| gradient boosting | 51 (three indices) | 0.821 | 0.823 | |

The forests sit 0.033 to 0.040 macro F1 *below* the booster on the nine indices, so the "more
than 1% better" bar is missed by a wide margin and the 2024 predictions do not change. The
three-index tie did not carry over: the booster gains 0.07 from the six extra index families and
the forests gain 0.03, and most of the gap is the legume class. Reports:
`GROUP3_MODEL_rf_9index.md`, `GROUP3_MODEL_et_9index.md`, scored on the same 543 fixed test
trials as the adopted model. The Technical Validation sentence now gives these numbers.

## 2. Legume species, and whether a pooled legume yield makes sense

### Can the classifier tell the five legumes apart?

No. Two runs, both on the adopted 153 features, the same rows and the same fixed test trials
as the adopted classifier (`LEGUME_SPECIES_MODEL_9index.md`, `SPECIES_MODEL_9index.md`; the
whole job was 5.3 SU and 13 minutes).

**Legume-only, five species** (trained on the 490 legume trials, scored on the 109 legume test
trials, so this is "given we already know it is a legume, which one?"): macro F1 **0.355 temporal
and 0.343 spatial**, against 0.20 for guessing. Per species (temporal / spatial F1): field pea
0.45 / 0.46, lupin 0.43 / 0.31, chickpea 0.38 / 0.29, faba bean 0.35 / 0.38, lentil 0.17 / 0.29.
The confusion matrices have no structure to exploit: chickpea is called field pea more often
than chickpea (12 of 25 against 7), lentil is called field pea at 10 of 19, and the best any
species manages is field pea at 17 of 26 with 30 false positives. Confusion matrices are in
`output/figures/confusion_legume5_9index_*.png`.

**Nine species on everything** (the paper's 0.38 figure redone on the adopted features): macro
F1 **0.364 temporal and 0.328 spatial**. Canola is still 0.88 and wheat 0.74, but barley is 0.22,
oat 0.08 and every legume is between 0.00 (lentil) and 0.40 (field pea). So the cereals cannot
be split either: 56 of 74 barley trials are called wheat. The three-group collapse is doing all
the work, and the nine indices did not change that (0.36 against 0.38 on the three indices).

So the species question is settled: the map cannot say which legume was grown, and neither the
extra indices nor a legume-only model gets it above a third. The Labelling sentence now quotes
the 0.36 against 0.89 on the adopted features, and Technical Validation says in one sentence
that legumes are not resolved to species.

### How different are the species' yields?

From the NVT single-site yields on the 2,194 training trials. The variance share is a one-way
ANOVA R² of species, and it is 19.2% for legumes after removing year x state means, so it is
not a geography artefact.

| group | species (n) and median t/ha | group median | yield variance between species |
|---|---|---|---|
| Cereal | wheat (811) 3.92, barley (227) 4.18, oat (81) 3.85 | 3.97 | 0.5% |
| Legume | chickpea (126) 1.51, field pea (120) 1.87, lentil (78) 2.00, lupin (86) 2.01, faba bean (80) 3.14 | 1.93 | 18.5% |
| Canola | canola (585) 2.38 | 2.38 | - |

The cereal pooling is nearly free: the three cereals yield within 9% of each other. The legume
pooling is not: faba bean yields twice what chickpea does, and species explain about a fifth of
the variance.

### Does that matter for a pooled legume yield column?

Less than it looks, because the yield model never sees the species either way. At map time the
cereal model does not know wheat from barley and a legume model would not know chickpea from faba
bean. Their scores (spatial-transfer R² 0.564 cereal and 0.458 legume, against year-and-state
baselines of 0.294 and 0.133) are already scored without species. The between-species share is an
upper bound on how much of the legume R² is the model recognising the species from its spectra:
at most 0.19 of the 0.458, so at least 0.27 is within-species yield signal. RMSE is 0.84 t/ha,
43% of the median, against 29% for cereals. So the species question is about interpretation,
not validity: a legume polygon's yield reads as "yield if this were a typical legume", low for a
faba bean field and high for a chickpea field. That is the same kind of statement as the cereal
column, only with a wider spread.

### Recommendation

Include the pooled legume yield, raw and calibrated, exactly as for cereals, and say in Usage
Notes what the pooling hides. It beats its baseline by more than the cereal model beats its own
(+0.33 against +0.27 R²), and a reader can ignore a column far more easily than regenerate one.
**The draft is written that way**: Abstract, Background paragraph 3, Methods "Yield estimation",
Data Records (`yield_tha` on cereal and legume polygons, `legume_yield.joblib`), Technical
Validation "Yield" with a legume block in Table 7, Usage Notes and Code Availability. The legume
calibration factor and its 2023 and 2024 checks are XXX because the model has not been fitted
for release and the ABS legume implied yields have not been pulled.

If you decide against it, revert those paragraphs to their versions in commit 2beb98c (your
edits #4). The one sentence there that must still change is "This was found to estimate yield
slightly better than the 9-index model", which was not right (section 3, item 2). Replace it with:
"A refit on all nine indices raised the spatial-transfer R² from 0.526 to 0.564 (Technical
Validation)." And replace the Usage Notes sentence on legumes with: "Legume yield was modelled
(spatial-transfer R² 0.458 against 0.133 for a year-and-state mean) but is not provided, because
the five species differ two-fold in trial yield and the map does not resolve which was grown."

## 3. What this means for starting the other years

The random-forest result removes one reason to wait. The legume result adds one back, and it
brings a second one with it.

1. **Legume yield needs a predict-stage change.** `predict_tile.py` takes one `--yield-model`
   and scores only polygons whose class matches that model's crop. It needs to accept two, and a
   `legume_yield.joblib` has to be fitted (`fit_yield_model.py --crop Legume --group`).
2. **The cereal model should move to the nine indices at the same time.** The draft sentence
   "the three indices were found to estimate yield slightly better than the 9-index model" was
   not right for the released model. `cereal_yield.joblib` is satellite-only on 51 features
   (spatial R² 0.526, temporal 0.471). The nine-index refit on the same rows is 0.564 and 0.486
   (`YIELD_GROUP3_9INDEX.md` against `YIELD_GROUP3_3INDEX.md`). The three-index model was ahead
   only with year and state added as features (0.577 against 0.566), which the released model
   does not use. For legumes the nine indices matter more (0.458 against 0.371). One catch:
   `fit_yield_model.py` reads only the `--indices` files and does not have the bands pathway
   that `train_yield.py` and the classifier use, so it needs that added before either model
   can be fitted on 153 features. The 0.6248 factor and the 18% and 3% checks belong to the
   51-feature model and have to be refitted with it.
3. **Cost.** The 2024 SAM polygons are on disk (`national2024_9km/samgeo`, 63,948 files), so a
   predict-only pass (`sampredict.pbs` with `ORCH_EXTRA=--no-sam`) re-scores them without
   re-running SAM. The 2024 SAM+predict stage cost 2,078 SU. The predict half is the CPU zonal
   step and should be well under half of that, but one chunk should be benchmarked before the
   full pass rather than guessed.
4. **One change worth making while the stage is open.** Have `predict_tile.py` write the 153
   per-polygon features to a parquet beside each tile's GeoPackage. The features are the
   expensive part and are currently discarded, so any later change (a recalibration, a different
   yield model, a class-prior correction) becomes a re-score costing almost nothing instead of a
   re-run costing hundreds of SU per season.

So: if legume yield goes in the release, adjust the predict stage first, re-run 2024 predict-only,
then run the other eight seasons once. If it does not, start the eight seasons now with the
option B text above, and the cereal model stays on 51 features for the whole series.

## 4. The other comments, in document order

### Background & Summary

| Comment | Response |
|---|---|
| A number on the total dollar value of the grains industry? Are canola and pulses grain? Is there a better word? | Yes to "grains": the GRDC's remit and ABARES's "grains" category both cover cereals, oilseeds and pulses (the GRDC's 25 leviable crops include canola and every pulse in this paper), so the draft now says so in the first sentence rather than searching for another word. Value written in: gross value of production $26.7 billion in 2024-25, from Grain Producers Australia and Grains Australia both citing ABARES (Grains Australia rounds it to $26 billion from the June 2025 estimates). Cited as ABARES (2025), Agricultural commodities: September quarter 2025, with an XXX URL. The DAFF/ABARES site timed out from gadi and the PDF resisted text extraction, so please confirm the figure and report title against the ABARES page from your laptop before it goes further. |
| Use "field" instead of "paddock" across the paper | Done: 53 replacements, `PaddockTS` kept as a name, and the title, keywords and "field-median" follow. Because "field" then also meant a table column, the four attribute-sense uses ("the following fields", "filter on these fields", "the `raster_cut_m` and `class_conflict` fields") are now "attributes". For the record, GRDC and Australian agronomy do use "paddock" for cropping, but "field" is the international term and the venue is international. One `sed` reverts it if you change your mind. |
| We're also training on data that isn't public | Note only, no change. Bracket removed. |

### Methods

| Comment | Response |
|---|---|
| Is "mapped area" the tile area or the polygon area? | It meant the tile footprint, and the sentence was a non sequitur in either reading. It now says what it is: the 15,968 tiles cover 129 M ha (15,968 x 81 km²), about five times the 24.6 M ha ABS records as sown to these crops in 2024. The polygon over-call (1.10) is a different number and stays in Technical Validation. |
| Add the Newman and Furbank sentence, with the right reference | Added: "This is an updated version of the dataset described by Newman and Furbank (2021), used with permission from the GRDC as in that study." Reference restored with doi:10.1038/s41477-021-01001-0 (Nature Plants 7, 1354-1363). One thing to know before GRDC reads it: that paper has a 2022 Author Correction (doi:10.1038/s41477-022-01096-z) concerning data probity and the permission under which the NVT data were reused, which is presumably the legal concern you mentioned in round 2. "As in that study" ties your permission to theirs. If that is not what you want GRDC to read, "used under a data-use agreement with the GRDC" says the same thing without the comparison. |
| Is 270 correct? | Technically yes, but it was the wrong set. 270 is the number of 2024 trials in the fixed 543-trial test set that fall on the tile grid (278 sown in 2024 are in the test set, 270 on the grid). The test set only contains trials whose matched polygon passed the labelling filters, so 76.3% flatters SAM. Checked directly: on the 278 test-set trials SAM contains the point at 79.9% and gives a passing polygon at 75.5%, on the other 279 trials sown in 2024 it is 45.2% and 35.8%. |
| Why does 557 differ from the 270 above? | Same reason. 557 is every NVT trial sown in 2024 with coordinates, before any filtering, which is the honest denominator for "does this source give a field at a trial". The draft now uses 557 for both sources: SAM contains the point at 62.5% and gives a passing polygon at 55.7%. |
| What happens with a filter pass on Fields of the World too? | It had already been run (`FTW_COMPARISON.md` applies the 5-300 ha and compactness 8 filter to both sources) but the draft never said so. With the filter, FTW gives a usable field at 49.7% of trials against SAM's 55.7%. FTW loses on size and shape: its containing polygon is over 300 ha at 24.4% of trials and fails compactness at a further 15.1% (under 5 ha at 1.4%). On the 172 trials where both sources pass the filter, they agree closely: median 64.6 ha against 52.1 ha, median area ratio 1.02, median IoU 0.88, IoU below 0.5 at only 12.8%. On the 321 where both merely contain the point it is 109 against 55 ha, ratio 1.49, IoU 0.53, so the merged-field failures are exactly the polygons the filter removes. The draft now reports both the unfiltered and the filtered comparison. The SAM compactness pre-filtering caveat affects the "contains the point" row only, not the "passes the filter" row, since a polygon that failed compactness in production shows as absent either way. Also worth knowing: either source passes at 74.5% of trials (FTW only 18.9%, SAM only 24.8%), so the two are complementary. |
| More example comparisons, PNGs or GPKGs I can copy | Made, section 5. |
| Revert the "sought" sentence to my version | Reverted to your sentence from commit f6e22bf, with "the the" fixed, "bare soil" kept, and paddock changed to field. |
| Don't use "original" anywhere | Removed from the yield paragraph, the alternatives sentence and the six-indices sentence. The one remaining "original" is "writing (original draft)" in Author Contributions, which is the CRediT taxonomy term Nature journals use. Say the word if you want that changed too. |
| Can we reference "the three indices estimate yield slightly better than the nine"? | It is not true of the released model, so it has not been referenced but corrected (section 3, item 2). The draft now gives the 0.526 against 0.564 comparison and points to Technical Validation, where Table 7 carries the nine-index numbers. |
| Legume yield question | Section 2. |
| Get rid of the quad-hyphenated word | Rewritten as three sentences saying what the two share calculations are. |
| Hazard a guess at the confidence interval | Section 6, not in the paper. |

### Data Records

| Comment | Response |
|---|---|
| Only the 344,868 subset, one sentence | One sentence now. The count is 344,416, not 344,868: counted from `national_2024_crops_final.gpkg` (rows with a class and an empty `abstain_reason`) and it matches `national_2024_crops_final_good.gpkg` exactly. The 344,868 was from before the overlap merge. The `no_crop_shape` flag is on 85,535 polygons in the final file. |

### Technical Validation

| Comment | Response |
|---|---|
| Retry the random forest on the nine indices | Section 1. |
| Is the area ratio all three classes combined? | Yes. The sentence now says "the mapped area of all three classes combined". |
| What do argmax and mean probability mean here? | Two ways to turn per-polygon class probabilities into a class share of area. "Argmax" assigns each polygon wholly to its most probable class and sums area by class, which is how the map's `pred` column is made. "Mean probability" credits each class with the polygon's area multiplied by that class's probability, so a polygon that is 55% legume and 45% cereal contributes 0.55 of its area to legume rather than all of it. If argmax gave a much larger legume share than the probability-weighted version, the legume excess would be a decision-rule artefact: many polygons sitting just over the line, which a prior correction could fix. They agree within 0.6% (18.0% against 18.2%), so the classifier genuinely puts that much probability on legume, and the fix has to be in the features or the labels. The draft now explains it in those words and Table 5's headers are "Most probable class" and "Probability-weighted". |
| "points" as a percentage | Replaced everywhere: the 4.3 and 3.7 sentences, the Table 4 and Table 6 headers, and my new argmax sentence. Recorded in `WRITING_STYLE.md` section 7 with the other rules from this round (no "original", no chained hyphens, field not paddock, one-sentence companion files, do not rewrite your sentences). No numeric "points" remain in the draft. |
| The legume composition disagrees with ABS, so that sentence seemed wrong | Agreed, the sentence you deleted stays deleted. The threshold sentence now gives the actual changes (canola share error 0.5%, legume 1.1%) instead of "not more than 1%", since the legume change is just over 1%. |

### Acknowledgements

| Comment | Response |
|---|---|
| Thank Geoscience Australia for the datacube? | Yes, Digital Earth Australia is a Geoscience Australia program and NCI hosts it. Written: "Lastly, we thank Geoscience Australia for the Digital Earth Australia datacube and its analysis-ready Sentinel-2 products." |

### Not in brackets but done

- The NDVI note in Feature construction: cited to Rouse et al. (1974), the ERTS symposium paper, and added to the references.
- The "(todo: update to compare against the 2021 product)" is now a `{TODO: ...}` in the house convention, since it waits on the 2021 run.
- Ten sentences I wrote this round ran over 25 words and were split. Sentences of yours over 25 words were left alone.

## 5. Fields of the World against SAM: 42 sites to look at

`src/paddocks/ftw_examples.py` (new). Eight trials per state from the 557 sown in 2024 (Tasmania
has two), cycling through the four outcomes the comparison found so each is represented: both
sources give a passing polygon (10 sites), FTW contains the point where SAM does not (12), FTW's
polygon is at least three times SAM's (10), everything else (10). For each site it draws the
Fields of the World polygons (magenta) and the released map's polygons (cyan) over the clearest
Sentinel-2 true-colour scene from August to mid-October 2024 in a 2 km box, thick line for the
polygon containing the trial point, yellow dot for the trial. The SAM panel title gives the
containing polygon's area and its class or abstain reason.

Files, all on scratch because every one carries a TrialCode and a location:

- `/scratch/xe2/cb8590/paddock-species-data/derived/ftw/examples/ftw_vs_sam_<STATE>_<TrialCode>_SENSITIVE.png`, one per site
- `.../examples/ftw_vs_sam_examples_SENSITIVE.gpkg`, layers `aoi`, `trial_points`, `ftw`, `sam`, in EPSG:3577, with `contains_trial` and `passes_filter` on the FTW polygons and the map's own attributes on the SAM ones
- `.../examples/ftw_vs_sam_examples_SENSITIVE.csv`, the 42 sites with their outcome

To copy them to your laptop:

```
scp -r gadi:/scratch/xe2/cb8590/paddock-species-data/derived/ftw/examples .
```

The run finished on the login node in about 20 minutes: 42 PNGs, and the GeoPackage holds
8,455 FTW polygons and 480 SAM polygons over the 42 boxes. `examples_run.log` in the same
folder lists every site with both containing-polygon areas. The clearest scene in the window is
still cloudy at a few sites (Walgett, for one), so read those panels for the polygons only. The
earlier four-site check from August (2020 Yorke Peninsula sites) is still in
`.../derived/figures/ftw/`.

## 6. A guess at the confidence interval, and a flag on the 1.10

Not in the paper. The 1.10 is the median over 151 SA2s of mapped crop area divided by the ABS
sown area scaled to the tile cover of that SA2. A 5,000-resample bootstrap over SA2s puts a 95%
interval of 1.00 to 1.24 on that median. The SA2 ratios themselves are wide: interquartile range
0.77 to 1.73, 10th to 90th percentile 0.50 to 2.52. So any single region's crop area is uncertain
by roughly a factor of two either way, and the median over-call is known to about plus or minus
12%. An Olofsson-style interval on the national area would need a probability sample of crop
labels and is not possible with what exists.

The flag. The area-weighted version of the same ratio, total mapped area over total cover-scaled
ABS area across the same 151 SA2s, is 0.88 (bootstrap 0.81 to 0.96). The map over-calls in the
median region and under-calls in aggregate, because the largest cropping SA2s under-call (Buloke
0.64, Balonne 0.51) while many small ones over-call by two to three times. This agrees with the
national totals already in the paper (19.6 M ha classified against 24.6 M ha in ABS, a ratio of
0.80) and with 41% of mapped area being abstained. So the abstract's "estimates 1.10 times as
much cropland as those statistics" is true of the median region and not of the country. I have
not changed it, but I think it needs a qualifier such as "in the median region", and the
Usage Notes sentence "expect the map to call about 1.10 times the area ABS records" has the same
problem. Your call.

## Still outstanding, as of the end of round 3

Values the draft marks `XXX`:

- Consensus-layer count and every multi-year number (Table 8, Technical Validation, Abstract): the 2017-2023 and 2025 runs.
- Legume yield calibration factor and its 2023 and 2024 checks, and the cereal factor and checks if the cereal model is refitted on the nine indices (section 3).
- Dataset DOI and repository, code repository, GRDC request form URL, Earth Engine asset path.
- ABARES (2025) report URL, and the figure itself confirmed against the ABARES page.
- GRDC NVT protocols citation (the protocols page returns 403 from gadi).
- PaddockTS citation, ABARES NLUM v7 DOI, Wu and Osco (2023) DOI, Sulik and Long (2016) DOI, Tian et al. (2022) DOI.

Also open, not marked `XXX`:

- The 1.10 sentences in the Abstract and Usage Notes (section 6).
- Fig. 6 (yield summary) needs regenerating with the legume block if legume yield stays in.
- Table 8's 2024 shares (15.4 / 66.6 / 17.9) do not quite match Table 5 (15.4 / 66.7 / 18.0). Table 5 is the 151-SA2 footprint and Table 8 is national, so they need not agree, but `NATIONAL_2024_9KM_RESULTS.md` gives the national legume share as 18.0, not 17.9.
- Segmentation still carries `{TODO: John Burley to update this section}`, and the CFI equation still wants a manual check against Tian et al. (2022).
- The Newman and Furbank wording, before GRDC review (section 4).
- The Abstract is at the 170-word limit and now contains one more clause (cereals and legumes).

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
