# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2133 paddocks, 204 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 571, Cereal 1089, Legume 473
- **fixed test set**: scoring restricted to 497 of 2133 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1636, test 497
- **macro F1 0.864, balanced accuracy 0.857** (chance 0.333)

- **canola detected at 5 % FPR: 86.8%** (n=144)
- **average precision 0.926** (baseline = prevalence 0.290), ROC AUC 0.963

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.94 | 0.85 | 0.89 | 144 |
| Cereal | 0.91 | 0.96 | 0.93 | 253 |
| Legume | 0.78 | 0.76 | 0.77 | 100 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |122|6|16|
| **Cereal** |3|244|6|
| **Legume** |5|19|76|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.868, balanced accuracy 0.868** (scored on 497 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.94 | 0.83 | 0.88 | 144 |
| Cereal | 0.93 | 0.96 | 0.94 | 253 |
| Legume | 0.75 | 0.82 | 0.78 | 100 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |119|6|19|
| **Cereal** |3|242|8|
| **Legume** |5|13|82|

### Where the signal is

Permutation importance on the 2023-24 holdout, macro-F1 scoring, summed within each family. Negative means the feature was not used and shuffling it happened to help.

| feature family | importance |
|---|---|
| `ndre2` | +0.0177 |
| `ndvi_pad_median` | -0.0007 |
| `ndyi_pad_median` | -0.0084 |
| `vdvi` | -0.0185 |
| `vci` | -0.0220 |
| `vi3` | -0.0220 |
| `evi2_sharma` | -0.0227 |
| `vhvv_pad_median` | -0.0230 |
| `vh_pad_median` | -0.0239 |
| `vv_pad_median` | -0.0266 |
| `cfi_pad_median` | -0.0351 |
| `vi2` | -0.0409 |

Top individual features: `ndre2_230@bands`, `vhvv_pad_median__p90@s1`, `vi3_250@bands`, `ndre2_210@bands`, `ndyi_pad_median__p10@indices`, `vi2_90@bands`, `ndre2_290@bands`, `ndre2__amp@bands`, `ndvi_pad_median__peak_doy@indices`, `vci__peak_doy@bands`, `ndre2_110@bands`, `vhvv_pad_median__amp@s1`

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.864 | 0.857 |
| spatial (GroupKFold on site) | 0.868 | 0.868 |
