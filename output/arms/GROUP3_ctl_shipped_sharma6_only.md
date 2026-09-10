# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2133 paddocks, 153 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 571, Cereal 1089, Legume 473
- **fixed test set**: scoring restricted to 497 of 2133 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1636, test 497
- **macro F1 0.887, balanced accuracy 0.890** (chance 0.333)

- **canola detected at 5 % FPR: 84.0%** (n=144)
- **average precision 0.930** (baseline = prevalence 0.290), ROC AUC 0.956

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.84 | 0.88 | 144 |
| Cereal | 0.95 | 0.96 | 0.96 | 253 |
| Legume | 0.78 | 0.87 | 0.82 | 100 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |121|4|19|
| **Cereal** |5|243|5|
| **Legume** |5|8|87|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.886, balanced accuracy 0.890** (scored on 497 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.85 | 0.88 | 144 |
| Cereal | 0.96 | 0.96 | 0.96 | 253 |
| Legume | 0.77 | 0.86 | 0.82 | 100 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |123|3|18|
| **Cereal** |4|242|7|
| **Legume** |7|7|86|

### Where the signal is

Permutation importance on the 2023-24 holdout, macro-F1 scoring, summed within each family. Negative means the feature was not used and shuffling it happened to help.

| feature family | importance |
|---|---|
| `ndre2` | +0.1342 |
| `ndyi_pad_median` | +0.0641 |
| `vi3` | +0.0512 |
| `cfi_pad_median` | +0.0374 |
| `vci` | +0.0355 |
| `vi2` | +0.0318 |
| `evi2_sharma` | +0.0172 |
| `vdvi` | +0.0169 |
| `ndvi_pad_median` | +0.0095 |

Top individual features: `ndre2_230@bands`, `ndre2_110@bands`, `ndre2_210@bands`, `cfi_pad_median_250@indices`, `vi3_250@bands`, `ndyi_pad_median_290@indices`, `ndyi_pad_median__amp@indices`, `ndre2_250@bands`, `ndre2_270@bands`, `cfi_pad_median_150@indices`, `ndre2_170@bands`, `evi2_sharma_330@bands`

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.887 | 0.890 |
| spatial (GroupKFold on site) | 0.886 | 0.890 |
