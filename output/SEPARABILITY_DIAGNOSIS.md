# Why separability swings between year x state panels

Separability = AUC of max CFI in DOY 200-300, canola vs every other crop, within a panel. 32 panels, 2477 paddocks.

- AUC range **0.36 to 0.99**, median 0.81, sd 0.129
- sd expected from SAMPLING ALONE at these panel sizes: **0.064**
- so sampling noise accounts for about **24%** of the observed variance; the rest is a real panel effect

## What predicts a panel's separability

Spearman correlation against panel AUC, ranked by strength.

| driver | kind | spearman r | 95% CI | excludes 0 |
|---|---|---|---|---|
| `med_ndvi_amp` | real (season vigour) | +0.41 | [+0.03, +0.73] | yes |
| `sow_iqr_d` | design | +0.35 | [-0.00, +0.63] | no |
| `frac_contains` | data quality | +0.28 | [-0.09, +0.59] | no |
| `med_flower_obs` | data quality | -0.22 | [-0.54, +0.14] | no |
| `n_canola` | sampling | +0.18 | [-0.26, +0.57] | no |
| `med_max_gap_d` | data quality | +0.10 | [-0.28, +0.48] | no |
| `frac_gap_over_21d` | data quality | +0.09 | [-0.27, +0.45] | no |
| `med_paddock_ha` | data quality | -0.09 | [-0.47, +0.32] | no |
| `lon_spread_deg` | design | -0.06 | [-0.45, +0.38] | no |
| `lat_spread_deg` | design | +0.04 | [-0.35, +0.45] | no |
| `med_compactness` | data quality | +0.04 | [-0.35, +0.41] | no |

## Panels, best to worst

| panel | AUC | n canola | n other | med flower obs | med max gap (d) | lat spread | med NDVI amp |
|---|---|---|---|---|---|---|---|
| 2022 SA | 0.99 | 14 | 40 | 12 | 20 | 0.97 | 0.74 |
| 2024 NSW | 0.95 | 41 | 68 | 14 | 13 | 1.74 | 0.72 |
| 2017 NSW | 0.93 | 28 | 72 | 9 | 20 | 2.17 | 0.61 |
| 2023 WA | 0.92 | 13 | 46 | 15 | 15 | 2.50 | 0.63 |
| 2020 SA | 0.91 | 10 | 61 | 12 | 20 | 1.12 | 0.73 |
| 2020 NSW | 0.90 | 32 | 67 | 13 | 15 | 1.92 | 0.72 |
| 2021 SA | 0.90 | 20 | 47 | 13 | 15 | 1.08 | 0.73 |
| 2017 SA | 0.89 | 17 | 37 | 10 | 22 | 0.91 | 0.71 |
| 2021 NSW | 0.88 | 35 | 75 | 15 | 15 | 1.91 | 0.72 |
| 2024 WA | 0.87 | 25 | 57 | 15 | 15 | 2.45 | 0.70 |
| 2023 SA | 0.86 | 19 | 62 | 17 | 10 | 1.08 | 0.73 |
| 2019 NSW | 0.86 | 15 | 57 | 17 | 10 | 2.34 | 0.62 |
| 2018 SA | 0.85 | 16 | 34 | 14 | 15 | 1.05 | 0.71 |
| 2021 VIC | 0.85 | 18 | 46 | 14 | 15 | 0.78 | 0.69 |
| 2022 NSW | 0.84 | 23 | 68 | 11 | 22 | 1.86 | 0.69 |
| 2020 VIC | 0.82 | 28 | 56 | 13 | 17 | 0.78 | 0.71 |
| 2023 NSW | 0.81 | 30 | 70 | 16 | 15 | 1.53 | 0.69 |
| 2022 WA | 0.81 | 26 | 51 | 14 | 15 | 1.74 | 0.67 |
| 2022 VIC | 0.80 | 30 | 52 | 13 | 15 | 0.80 | 0.73 |
| 2019 WA | 0.77 | 20 | 51 | 15 | 15 | 1.87 | 0.56 |
| 2019 VIC | 0.76 | 27 | 44 | 14 | 15 | 0.55 | 0.71 |
| 2019 SA | 0.75 | 18 | 45 | 15 | 15 | 1.10 | 0.73 |
| 2018 VIC | 0.73 | 16 | 50 | 14 | 15 | 0.78 | 0.61 |
| 2024 SA | 0.73 | 16 | 44 | 15 | 15 | 1.08 | 0.67 |
| 2017 WA | 0.73 | 16 | 39 | 9 | 20 | 1.74 | 0.58 |
| 2017 VIC | 0.72 | 25 | 29 | 8 | 20 | 0.67 | 0.69 |
| 2018 WA | 0.71 | 14 | 45 | 15 | 13 | 3.47 | 0.65 |
| 2023 VIC | 0.70 | 28 | 47 | 15 | 15 | 0.82 | 0.69 |
| 2020 WA | 0.68 | 20 | 70 | 14 | 15 | 2.91 | 0.66 |
| 2018 NSW | 0.62 | 13 | 44 | 14 | 15 | 2.17 | 0.62 |
| 2024 VIC | 0.52 | 19 | 39 | 14 | 20 | 0.88 | 0.57 |
| 2021 WA | 0.36 | 10 | 48 | 15 | 14 | 3.36 | 0.72 |
