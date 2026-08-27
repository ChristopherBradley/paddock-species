# Sample wall-to-wall species maps

Aggregate only — no site-level records, no trial codes.

## Regions

| region | state | lon | lat | canola_prob | cereal_prob | legume_prob | edge_km |
|---|---|---|---|---|---|---|---|
| wa_0 | WA | 121.446677 | -33.702299 | 0.2478 | 0.3252 | 0.0273 | 12.0 |
| sa_1 | SA | 135.54604 | -34.452615 | 0.2324 | 0.1892 | 0.0251 | 12.0 |
| nsw_2 | NSW | 147.160275 | -34.726507 | 0.2259 | 0.4715 | 0.028 | 12.0 |

Each region is a 5-year run over a 4x4 grid of the 3 km production tile, i.e. 12 x 12 km of ground. Tile size is held at 3 km because `samgeo`'s fixed 512 px window makes it a segmentation hyperparameter rather than a partition of the same work.

## Coverage, and what the white space is

Each region is 14,400 ha (4x4 tiles x 900 ha). `coverage` is the share of that area inside a classified polygon. The remainder is ground SAM did not resolve into a paddock above the 5 ha floor, or paddocks with fewer than 10 clear observations — **not** ground with no crop on it.

| region | year | polygons | classified_ha | median_ha | over_300ha | median_obs | median_conf | coverage |
|---|---|---|---|---|---|---|---|---|
| nsw_2 | 2020 | 410 | 13282 | 25.0 | 0 | 28.0 | 1.0 | 0.922 |
| nsw_2 | 2021 | 369 | 12902 | 28.7 | 0 | 34.0 | 1.0 | 0.896 |
| nsw_2 | 2022 | 302 | 11198 | 29.7 | 1 | 25.0 | 1.0 | 0.778 |
| nsw_2 | 2023 | 379 | 13702 | 29.5 | 0 | 31.0 | 1.0 | 0.952 |
| nsw_2 | 2024 | 366 | 13809 | 29.0 | 1 | 35.0 | 1.0 | 0.959 |
| sa_1 | 2020 | 199 | 8261 | 19.5 | 5 | 30.0 | 0.9999 | 0.574 |
| sa_1 | 2021 | 182 | 7078 | 19.9 | 3 | 31.0 | 0.9997 | 0.492 |
| sa_1 | 2022 | 124 | 9071 | 16.5 | 8 | 23.0 | 0.99965 | 0.63 |
| sa_1 | 2023 | 145 | 8822 | 19.6 | 8 | 32.0 | 0.9997 | 0.613 |
| sa_1 | 2024 | 202 | 7841 | 19.8 | 3 | 27.0 | 0.9951 | 0.545 |
| wa_0 | 2020 | 240 | 9884 | 24.5 | 2 | 63.0 | 0.9997 | 0.686 |
| wa_0 | 2021 | 191 | 9604 | 27.5 | 4 | 55.0 | 0.9998 | 0.667 |
| wa_0 | 2022 | 227 | 10628 | 28.0 | 6 | 54.0 | 1.0 | 0.738 |
| wa_0 | 2023 | 172 | 7530 | 22.1 | 5 | 63.0 | 1.0 | 0.523 |
| wa_0 | 2024 | 201 | 8699 | 27.7 | 2 | 57.0 | 0.9973 | 0.604 |

**48 of 3709 polygons (1.3%) exceed 300 ha** — the tile-scale blobs SAM returns where there are no field boundaries to find. They are kept, with `area_ha` and `compactness` on every row, because a national product cannot be hand-reviewed and the fields the review used have to travel with the data.

## Predicted area by class (hectares)

| region | year | Canola | Cereal | Grazing | Legume |
|---|---|---|---|---|---|
| nsw_2 | 2020 | 1275 | 8432 | 3398 | 177 |
| nsw_2 | 2021 | 2329 | 7073 | 2972 | 528 |
| nsw_2 | 2022 | 2809 | 4404 | 3612 | 372 |
| nsw_2 | 2023 | 2243 | 7341 | 3918 | 200 |
| nsw_2 | 2024 | 2528 | 7241 | 3566 | 474 |
| sa_1 | 2020 | 1533 | 2805 | 3325 | 599 |
| sa_1 | 2021 | 1519 | 1966 | 3062 | 531 |
| sa_1 | 2022 | 1248 | 2160 | 5381 | 282 |
| sa_1 | 2023 | 734 | 3116 | 4868 | 104 |
| sa_1 | 2024 | 1199 | 2066 | 3082 | 1494 |
| wa_0 | 2020 | 1290 | 3797 | 3991 | 807 |
| wa_0 | 2021 | 1999 | 3134 | 4278 | 193 |
| wa_0 | 2022 | 2226 | 2052 | 6001 | 348 |
| wa_0 | 2023 | 1225 | 2116 | 3739 | 450 |
| wa_0 | 2024 | 1901 | 3627 | 1464 | 1708 |

## Predicted share by class

| region | year | Canola | Cereal | Grazing | Legume |
|---|---|---|---|---|---|
| nsw_2 | 2020 | 0.096 | 0.635 | 0.256 | 0.013 |
| nsw_2 | 2021 | 0.181 | 0.548 | 0.23 | 0.041 |
| nsw_2 | 2022 | 0.251 | 0.393 | 0.323 | 0.033 |
| nsw_2 | 2023 | 0.164 | 0.536 | 0.286 | 0.015 |
| nsw_2 | 2024 | 0.183 | 0.524 | 0.258 | 0.034 |
| sa_1 | 2020 | 0.186 | 0.34 | 0.402 | 0.073 |
| sa_1 | 2021 | 0.215 | 0.278 | 0.433 | 0.075 |
| sa_1 | 2022 | 0.138 | 0.238 | 0.593 | 0.031 |
| sa_1 | 2023 | 0.083 | 0.353 | 0.552 | 0.012 |
| sa_1 | 2024 | 0.153 | 0.263 | 0.393 | 0.191 |
| wa_0 | 2020 | 0.131 | 0.384 | 0.404 | 0.082 |
| wa_0 | 2021 | 0.208 | 0.326 | 0.445 | 0.02 |
| wa_0 | 2022 | 0.209 | 0.193 | 0.565 | 0.033 |
| wa_0 | 2023 | 0.163 | 0.281 | 0.497 | 0.06 |
| wa_0 | 2024 | 0.219 | 0.417 | 0.168 | 0.196 |

## Rotation check

Polygons are matched across years on a 200 m grid of their representative point, because segmentation is re-run per year and the boundaries are not the same objects between runs. A paddock that reads the same class every year is either perennial, irrigated, or the model keying on something static.

| region | n_tracked | median_classes | single_class_pct | canola_every_year_pct | canola_1_to_3_years_pct |
|---|---|---|---|---|---|
| wa_0 | 69 | 2.0 | 0.217 | 0.0 | 0.449 |
| sa_1 | 74 | 2.5 | 0.108 | 0.0 | 0.635 |
| nsw_2 | 229 | 2.0 | 0.157 | 0.0 | 0.555 |

## Against NLUM's expectation for the same ground

NLUM is a 2020-21 prior and cannot adjudicate a single season. It is here because it is the only independent statement about this ground, and a multi-year mean that lands far from it needs an explanation.

| region | NLUM canola | mapped canola (mean over years) | NLUM cereal | mapped cereal | NLUM legume | mapped legume |
|---|---|---|---|---|---|---|
| wa_0 | 0.248 | 0.186 | 0.325 | 0.320 | 0.027 | 0.078 |
| sa_1 | 0.232 | 0.155 | 0.189 | 0.294 | 0.025 | 0.076 |
| nsw_2 | 0.226 | 0.175 | 0.471 | 0.527 | 0.028 | 0.027 |

NLUM's probabilities are shares of ALL land in the block including non-agricultural; the mapped shares are of segmented paddocks only, so the two columns are not expected to be equal. The comparison that means something is their RATIO between crops.

## Confidence

| pred | count | 25% | 50% | 75% |
|---|---|---|---|---|
| Canola | 617.0 | 0.975 | 1.0 | 1.0 |
| Cereal | 1514.0 | 0.999 | 1.0 | 1.0 |
| Grazing | 1336.0 | 0.996 | 1.0 | 1.0 |
| Legume | 242.0 | 0.779 | 0.942 | 0.994 |
