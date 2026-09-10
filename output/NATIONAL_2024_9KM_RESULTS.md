# National 2024 map at 9 km: products, comparisons and validation (2026-09-10)

Aggregate only. No trial code, coordinate or other site-level record appears here. The per-site
retention table stays in `$M/compare/sites_2024_9km_SENSITIVE.csv`.

`$M` = `/scratch/xe2/cb8590/paddock-species-data/derived/national2024_9km`

## Products

| file | contents |
|---|---|
| `$M/national_2024_crops_merged.gpkg` | **The final map.** De-duplicated across tile overlaps. 1,158,824 polygons, layer `crops`, EPSG:3577, 3.1 GB |
| `$M/national_2024_crops_merged_classified.gpkg` | Every polygon with a predicted class: 462,028. Includes the 105,627 flagged `no_crop_shape`. `pred` renamed `predicted_crop_type`, QGIS style embedded |
| `$M/national_2024_crops_merged_good.gpkg` | **Good polygons**, the strict mask: a class and every gate passed (`abstain_reason` empty). 356,401 |
| `$M/national_2024_crops.gpkg` | Before de-duplication: 1,238,529 polygons |
| `projects/ee-christopher-bradley/assets/paddock_species_national_2024_9km_crops` | Earth Engine folder, 20 shards of the final map, public read. App: `src/paddocks/gee/visualise_national_crops.js` |

`raster_cut_m` and `class_conflict` are kept as columns in all of them for a further, optional mask
(`TILE_BOUNDARY_MERGE.md`).

## How "classified" is counted

The run predicts every class and records a failed phenology-shape check as `abstain_reason =
no_crop_shape` without removing the class (`--shape-gate-skip-classes Canola Cereal Legume`,
PROJ_NOTES 2026-09-07 (2a)). The manuscript rejects the shape gate, so its headline counts these
105,627 polygons as classified. That is also like-for-like with the 3 km map, which had no shape
gate. The `_good` file is the stricter reading.

## 1. Against the retired 3 km map

| | 3 km (retired) | 9 km (adopted) |
|---|---:|---:|
| polygons | 1,346,582 | 1,158,824 |
| classified | 650,766 (48.3%) | 462,028 (39.9%) |
| total polygon area | 74.6 M ha | 35.6 M ha |
| classified area | 25.5 M ha (34.2%) | 20.7 M ha (58.2%) |
| median classified polygon | 24.4 ha | 27.8 ha |
| canola / cereal / legume share of classified area | 13.8 / 67.7 / 18.5% | 15.4 / 66.6 / 18.0% |
| `unsegmented_blob` polygons | 48,016 (37.7 M ha) | 9,080 (4.4 M ha) |

On 300 random 9 km windows (28,227 km², `MAP_COMPARISON_3KM_VS_9KM_2024.md`):

- 53.6% of 9 km polygons (65.7% of their area) have a 3 km match at IoU >= 0.5. Only 47.9% of 3 km
  polygons (30.8% of their area) have a 9 km match. The median best IoU is 0.58 one way and 0.46 the other.
- Where both maps classify a matched paddock, they agree on the class 84.0% of the time (7,378 pairs).
- The 3 km map had more classified polygons per km² (0.52 against 0.37), largely paddocks split at
  3 km tile edges and counted twice in the overlap band.

## 2. ABS sown area (SA2, 2024)

| | 3 km (retired) | 9 km before de-duplication | **9 km final** |
|---|---:|---:|---:|
| SA2s used (>= 50% covered) | 132 | 151 | 151 |
| canola share r | 0.82 | 0.77 | 0.77 |
| canola share median abs. error (points) | 5.5 | 4.1 | 4.1 |
| canola share, mapped vs ABS | 13.1 vs 19.7% | 13.8 vs 19.2% | 13.8 vs 19.2% |
| area over-call | 1.47x | 1.31x | **1.18x** |
| absorbed canola / cereal / legume (points) | -0.3 / +23.2 / +10.8 | -0.8 / +14.8 / +9.3 | -2.4 / +8.7 / +8.5 |
| legume share, mapped vs ABS | 16.7 vs 8.7% | 16.1 vs 8.9% | 16.1 vs 8.9% |

Reports: `ABS_COMPARISON_NATIONAL.md` (3 km), `ABS_COMPARISON_NATIONAL_2024_9km_preboundary.md`,
`ABS_COMPARISON_NATIONAL_2024_9km.md`.

- The over-call fell from 1.47x to 1.18x. De-duplication accounts for 1.31x to 1.18x, since the
  overlap band was counted twice before it. The rest comes with the new tiles and classifier.
- The excess still sits in cereal and legume. However, canola is now 2.4 points below the share a
  perfect classifier would show at this over-call, against 0.3 on the first map. The manuscript's
  "near-exact" canola claim is marked [CHECK].
- The `_strict` ABS report gives identical composition numbers. `abs_compare.py` computes shares
  from `pred` and only its coverage section uses `abstain_reason`, so a strict-mask ABS composition
  would need a code change.

## 3. WorldCereal 2021 (250,000 centroids, seed 0)

| | 3 km | 9 km |
|---|---:|---:|
| overall presence agreement | 73.1% | 75.3% |
| our abstained points that WorldCereal calls no-crop | 73.0% | 80.9% |
| our classified points that WorldCereal calls crop | 73.2% | 66.8% |
| our cereal points that are `wintercereals`-positive | 49.6% | 43.2% |

Agreement is no longer symmetric (`WORLDCEREAL_COMPARISON_2024_9km.md`).

## 4. NLUM v7 (same sample)

| | 3 km | 9 km |
|---|---:|---:|
| oilseed enrichment at canola points | 6.42 | 8.38 |
| cereal enrichment at cereal points | 1.42 | 1.40 |
| legume enrichment at legume points | 1.62 | 0.92 |
| median grazing probability, abstained vs classified | 33.8 vs 10.8% | 57.4 vs 17.7% |

Legume enrichment fell below 1 (`NLUM_COMPARISON_2024_9km.md`).

## 5. Trial-site retention (270 NVT trials from 2024)

- 80.4% sit inside a polygon, and 76.3% inside one that passed the size and shape filter (the
  first map: 77.9% of known crop paddocks).
- The polygon's area is within a factor of 2 of the trial paddock's for 91.7% of sites.
- No F1 is reported. The production classifier was trained on every trial, so accuracy here would be
  in-sample. `VALIDATION_9KM.md` holds the held-out accuracy.

## 6. Cost

| stage | SU |
|---|---:|
| presegment (59 jobs + `p006`) | 414.2 |
| pilot slice | 41.2 |
| SAM + predict (15 groups) | 2,078.5 |
| merge + boundary | 3.7 |
| **map total** | **~2,538** (projection 2,512) |
| comparisons (ABS x4, compare job) | 10.6 |

## Open items

- Regional (100 km) numbers in the manuscript stay XXX until a regional re-run with the adopted classifier.
- Figures 2, 3, 4, 5a, 7a and 8 need regenerating.
- The manuscript's [CHECK] markers flag four claims the re-run changed: canola "near-exact" after
  dilution, "same over-call magnitude" nationally and regionally, WorldCereal symmetry, and legume
  NLUM enrichment.
