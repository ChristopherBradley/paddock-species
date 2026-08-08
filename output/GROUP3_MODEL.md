# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2477 paddocks, 51 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 682, Cereal 1269, Legume 526

### Temporal transfer — train <=2022, test 2023-24

- train 1818, test 659
- **macro F1 0.716, balanced accuracy 0.719** (chance 0.333)

- **canola detected at 5 % FPR: 68.6%** (n=191)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.84 | 0.69 | 0.76 | 191 |
| Cereal | 0.82 | 0.82 | 0.82 | 339 |
| Legume | 0.51 | 0.65 | 0.57 | 129 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |131|29|31|
| **Cereal** |11|278|50|
| **Legume** |14|31|84|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.707, balanced accuracy 0.698**

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.84 | 0.64 | 0.73 | 682 |
| Cereal | 0.78 | 0.86 | 0.82 | 1269 |
| Legume | 0.55 | 0.59 | 0.57 | 526 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |439|125|118|
| **Cereal** |42|1093|134|
| **Legume** |39|177|310|

### Where the signal is

Permutation importance on the 2023-24 holdout, macro-F1 scoring, summed within each family. Negative means the feature was not used and shuffling it happened to help.

| feature family | importance |
|---|---|
| `cfi_pad_median` | +0.0491 |
| `ndvi_pad_median` | +0.0176 |
| `ndvi_pad_median_90` | -0.0050 |
| `ndyi_pad_median` | -0.0074 |
| `cfi_pad_median_90` | -0.0144 |
| `ndyi_pad_median_90` | -0.0153 |

Top individual features: `cfi_pad_median__amp`, `cfi_pad_median_270`, `cfi_pad_median_250`, `cfi_pad_median_230`, `ndyi_pad_median_170`, `ndvi_pad_median_210`, `ndvi_pad_median_230`, `cfi_pad_median_190`, `cfi_pad_median_130`, `ndyi_pad_median_250`, `ndyi_pad_median__p90`, `ndvi_pad_median_330`

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.716 | 0.719 |
| spatial (GroupKFold on site) | 0.707 | 0.698 |
