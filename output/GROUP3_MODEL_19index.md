> **SUPERSEDED 2026-08-31.** This report predates the `family()` bugfix
> (`INDEPENDENT_REVIEW_19index.md` #1) — its 333-feature count includes 10 raw-band columns
> that `--bands-drop-raw` should have dropped. The bug-fixed re-run (323 features) is
> `output/arms/idx_arch_sweep/bands_idxonly_all19_hgb_FIXED2.md`; the recommended candidate is
> the simpler, cleaner `output/GROUP3_MODEL_shipped_plus_sharma6.md` (153 features, same or
> better macro F1, no canola regression) — see
> `output/GROUP3_MODEL_shipped_plus_sharma6_VALIDATION.md` for the full writeup. Kept here
> unmodified as the historical record of what the independent review actually reviewed.

# Species classifier baseline — paddock-median Sentinel-2 [SUPERSEDED, see banner above]

- input: **10 bands** (10 columns), 2194 paddocks, 333 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.892, balanced accuracy 0.898** (chance 0.333)

- **canola detected at 5 % FPR: 85.8%** (n=155)
- **average precision 0.939** (baseline = prevalence 0.285), ROC AUC 0.967

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.85 | 0.89 | 155 |
| Cereal | 0.96 | 0.95 | 0.96 | 279 |
| Legume | 0.78 | 0.89 | 0.83 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |132|4|19|
| **Cereal** |5|266|8|
| **Legume** |6|6|97|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.884, balanced accuracy 0.888** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.86 | 0.88 | 155 |
| Cereal | 0.96 | 0.95 | 0.96 | 279 |
| Legume | 0.78 | 0.85 | 0.81 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |133|3|19|
| **Cereal** |5|266|8|
| **Legume** |9|7|93|

### Where the signal is

Permutation importance on the 2023-24 holdout, macro-F1 scoring, summed within each family. Negative means the feature was not used and shuffling it happened to help.

| feature family | importance |
|---|---|
| `ndre2` | +0.1077 |
| `nbr` | +0.0365 |
| `vi3` | +0.0349 |
| `cfi` | +0.0310 |
| `ndyi` | +0.0238 |
| `swir_ratio` | +0.0226 |
| `vi2` | +0.0214 |
| `vci` | +0.0172 |
| `vdvi` | +0.0128 |
| `psri` | +0.0121 |
| `ndre` | +0.0103 |
| `ndvi` | +0.0069 |
| `ndwi` | +0.0049 |
| `vci_90` | +0.0031 |
| `evi2_sharma` | +0.0027 |
| `evi` | +0.0021 |

Top individual features: `ndre2_230`, `vi3_250`, `cfi__amp`, `ndre2_250`, `vci__peak_doy`, `ndre2__amp`, `ndre2_270`, `ndyi__amp`, `ndre2__p90`, `ndre2_110`, `nbr_230`, `ndre2_210`

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.892 | 0.898 |
| spatial (GroupKFold on site) | 0.884 | 0.888 |
