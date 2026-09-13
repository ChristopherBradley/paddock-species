# Field crop-type mapping (Australia)

Maps canola, cereal and legume fields across the Australian cropping belt from Sentinel-2, one map per
season from 2017 to 2025. The classifier is trained on GRDC National Variety Trial (NVT) records.
It began as an input to later work on tree-shelter effects on productivity, but stands alone. The
original brief is in `initial_nora_prompt.md`.

Status (2026-09-13): all nine national maps are built or finishing. 2017 is in post-processing and
the other eight are done. The dataset is being written up as a Scientific Data descriptor in
`output/manuscript_scidata/MANUSCRIPT_DRAFT.md`. GRDC/NVT trial data is under NDA and is never
committed (see "Sensitive data" below). This repo holds the code and aggregate findings only.

## How the pipeline works

1. Segmentation. Field polygons come from the Segment Anything Model (`vit_h`, default parameters)
   through [samgeo](https://github.com/opengeos/segment-geospatial). It follows the pre-segment and
   SAM workflow in [PaddockTS](https://github.com/johnburley3000/PaddockTS). SAM runs on 15,968 tiles
   of 9 km selected from NLUM v7, covering 129 M ha. Duplicate and part-cut polygons along tile
   edges are merged afterwards, so polygons in a released map do not overlap.
2. Features. Each polygon gets 153 field-median features. These are nine indices (NDVI, NDYI, CFI
   and six from Sharma et al. 2026) in 13 bins of 20 days, plus four whole-season summaries each.
3. Classification. A `HistGradientBoostingClassifier` predicts Canola, Cereal or Legume. It was
   trained on 2,194 NVT trials after hand review and removal of trials sharing a field with another
   crop group. The production model is `group3_map_sharma6.joblib`.
4. Abstention. A polygon is classified only if it passes four checks. Otherwise it carries the
   reason: `area_below_min` (under 5 ha), `unsegmented_blob` (over 300 ha), `too_few_observations`
   or `no_crop_signal` (NDVI amplitude under 0.35). `no_crop_shape` flags a classified polygon with
   no clear green-up and senescence, and it keeps its class.
5. Yield. Cereal polygons carry `yield_tha` (NVT-equivalent) and `yield_tha_calibrated`.

`src/paddocks/run_national.sh` runs every stage for one year. The eight years other than 2024 were
driven by a self-resubmitting PBS orchestrator, described in `output/MULTIYEAR_9KM_RUN.md`.

## Accuracy

Classifier accuracy on 543 fixed test trials sown in 2023-2024:

| Split | Macro F1 | Canola F1 | Cereal F1 | Legume F1 |
|---|---:|---:|---:|---:|
| Temporal (train 2022 or earlier) | 0.890 | 0.89 | 0.96 | 0.83 |
| Spatial (five-fold GroupKFold on site) | 0.892 | 0.89 | 0.96 | 0.82 |

Legume is the weakest class, with precision 0.77 temporal and 0.79 spatial. The main confusion is
canola predicted as legume. Canola is detected at 89.0% recall at a 5% false-positive rate. Random
forests, extra trees, fine-tuned Presto embeddings and Sentinel-1 backscatter all scored lower.

The released pipeline was also scored at the 533 test trials that fall on the tile grid. 122 had no
segmented polygon and 62 fell in an abstained polygon. On the remaining 349 the map reached a macro
F1 of 0.898.

## Validation of the 2024 map

Against ABS sown area over the 151 SA2s that the tiles cover by at least half:

- Canola share of crop area tracks ABS with r = 0.76 and a median absolute error of 4.3%.
- The map calls 1.10 times as much land crop as ABS records as sown. The first 3 km map called 1.47
  times. The tile-edge merge, the 9 km tiles and the nine-index classifier account for the fall.
- The excess sits in cereal and legume. Legume is 16.1% of classified area against 8.9% in ABS, the
  largest composition error in the map.
- Raising the NDVI amplitude threshold to 0.50 removes 26% of classified area. It changes canola
  share error by only 0.5%, so composition is insensitive to the threshold while area is not.

Against WorldCereal 2021, the classified or abstained call agrees with its temporary-crops layer at
76.1% of 250,000 sampled centroids. Against NLUM v7, canola polygons sit on land with 8.5 times the
oilseed probability of abstained land. Legume polygons show no enrichment for NLUM's legume layer.

Full detail: `output/NATIONAL_2024_9KM_RESULTS.md` and the Technical Validation section of the
manuscript.

## The national maps

| Season | Polygons | Classified | Strict (every gate passed) | Classified area (M ha) | SU |
|---|---:|---:|---:|---:|---:|
| 2017 | post-processing | | | | 2,244 |
| 2018 | 1,053,010 | 306,143 | 243,711 | 12.7 | 2,832 |
| 2019 | 1,025,733 | 362,732 | 295,744 | 15.1 | 2,242 |
| 2020 | 999,096 | 429,579 | 300,563 | 19.0 | 2,345 |
| 2021 | 1,009,494 | 439,072 | 304,170 | 19.8 | 2,294 |
| 2022 | 944,916 | 412,388 | 259,443 | 19.2 | 2,459 |
| 2023 | 996,244 | 380,905 | 273,124 | 17.1 | 3,537 |
| 2024 | 1,010,627 | 429,951 | 344,416 | 19.6 | 2,538 |
| 2025 | 996,839 | 457,110 | 358,688 | 20.9 | 2,598 |

Classified counts include polygons flagged `no_crop_shape`, as the manuscript does. 2018 has the most
segmented polygons and the fewest classified. It was a severe drought year across eastern Australia,
which would fit, but that has not been checked. Only 2022-2024 can be scored against ABS by SA2, and
2022 and 2023 have not been scored yet.

Each season is released as three GeoPackages in EPSG:3577: `final` (every polygon), `final_classified`
and `final_good` (strict). Locations:

- 2017-2023 and 2025: `/g/data/xe2/cb8590/paddock-species-national-9km/`
- 2024: `/scratch/xe2/cb8590/paddock-species-data/derived/national2024_9km/`
- 2024 on Earth Engine: public table assets in
  `projects/ee-christopher-bradley/assets/paddock_species_national_2024_9km_crops` (20 shards).
  The viewer is `src/paddocks/gee/visualise_national_crops.js`.

## Compute usage

| Run | SU |
|---|---:|
| 100 km x 9-year Riverina validation run | 597 |
| National 2024 at 3 km (retired) | 6,623 |
| National 2024 at 9 km | 2,538 |
| National 2017-2023 and 2025 at 9 km | 20,551 |

The 9 km configuration costs about 2,500 SU per season against 6,600 at 3 km. The saving came from
the `normalbw` queue, prompting SAM only on the image and not its padding, fp16 and the larger
tiles. 2023 cost the most because its GPU jobs ran alongside the most concurrent presegment jobs,
which slowed them through filesystem contention.

## Field stability (100 km x 9-year Riverina trial, 2017-2025)

247,008 polygon-years resolve to 58,457 distinct fields. The median field is found in 7 of 9 years
at median IoU 0.84, and 26.9% are found in all nine. Stability peaks in the 25-50 ha band (median 8
years, IoU 0.94). It is worst for polygons over 300 ha, which supports the 300 ha cap from an
independent direction. Detail: `output/POLYGON_STABILITY.md` and `output/CONSENSUS_LAYER.md`.

These numbers come from the 3 km Riverina run. The national consensus layer on the 9 km maps has
not been built.

## Yield

Cereal yield (wheat, barley and oat pooled) reaches a spatial-transfer R² of 0.564 and RMSE of 1.16
t/ha. It is in every national map. A legume model reaches R² 0.458, but its predictions are not in
any national map yet. Canola yield is not provided, because an optical-only model (R² 0.271) was no
better than a year-and-state mean (0.290). Sentinel-1 raised it to 0.371, but Sentinel-1 was not
acquired nationally. The ABS calibration factors for `yield_tha_calibrated` still need to be
confirmed. Detail: `output/YIELD_FEASIBILITY.md` and the manuscript's yield sections.

## Still to do

- Finish 2017 post-processing, which the orchestrator does unattended.
- ABS SA2 comparison for 2022 and 2023, and ABARES state totals for all nine seasons.
- The national consensus layer and the cross-year rotation counts.
- Legume yield and the ABS calibration factors in the maps, or remove them from the manuscript.
- Earth Engine upload for the other eight years, and the dataset DOI.
- Send the manuscript to GRDC for sign-off before submission.

## Sensitive data

GRDC/NVT trial data (site coordinates, crop type, dates and yield) is under a signed NDA and is never
committed. See `.gitignore` and `CLAUDE.md`. Everything in this repo is code or aggregate findings
with no site-level records. Reports that contain site-level records are named `*_SENSITIVE.*`, which
git ignores.
