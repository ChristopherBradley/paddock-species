# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2757 paddocks, 51 features, 4 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Grazing 563, Legume 490
- **fixed test set**: scoring restricted to 812 of 2757 rows listed in `testkeep_group4_sam_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1945, test 812
- **macro F1 0.852, balanced accuracy 0.856** (chance 0.250)

- **canola detected at 5 % FPR: 88.4%** (n=155)
- **average precision 0.925** (baseline = prevalence 0.191), ROC AUC 0.968

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.84 | 0.88 | 155 |
| Cereal | 0.87 | 0.90 | 0.89 | 279 |
| Grazing | 0.99 | 0.93 | 0.96 | 269 |
| Legume | 0.63 | 0.76 | 0.69 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |130|8|0|17|
| **Cereal** |3|251|3|22|
| **Grazing** |4|6|249|10|
| **Legume** |4|22|0|83|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.838, balanced accuracy 0.836** (scored on 812 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.84 | 0.84 | 0.84 | 155 |
| Cereal | 0.88 | 0.92 | 0.90 | 279 |
| Grazing | 0.98 | 0.96 | 0.97 | 269 |
| Legume | 0.66 | 0.62 | 0.64 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |130|5|2|18|
| **Cereal** |4|258|3|14|
| **Grazing** |6|3|257|3|
| **Legume** |14|26|1|68|

### Where the signal is

Permutation importance on the 2023-24 holdout, macro-F1 scoring, summed within each family. Negative means the feature was not used and shuffling it happened to help.

| feature family | importance |
|---|---|
| `ndvi_pad_median` | +0.1401 |
| `cfi_pad_median` | +0.1176 |
| `ndyi_pad_median` | +0.0499 |
| `ndvi_pad_median_90` | +0.0302 |
| `cfi_pad_median_90` | +0.0229 |
| `ndyi_pad_median_90` | +0.0052 |

Top individual features: `ndvi_pad_median_90`, `ndvi_pad_median__amp`, `cfi_pad_median_90`, `cfi_pad_median_250`, `ndvi_pad_median_130`, `ndvi_pad_median__p10`, `cfi_pad_median_270`, `ndvi_pad_median__peak_doy`, `cfi_pad_median__amp`, `ndyi_pad_median_250`, `ndvi_pad_median_110`, `ndyi_pad_median_330`

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.852 | 0.856 |
| spatial (GroupKFold on site) | 0.838 | 0.836 |
