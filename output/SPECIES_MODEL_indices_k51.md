# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2477 paddocks, 51 features, 9 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Barley 322, Canola 682, Chickpea 134, Faba Bean 83, Field Pea 126, Lentil 81, Lupin 102, Oat 112, Wheat 835

### Temporal transfer — train <=2022, test 2023-24

- train 1818, test 659
- **macro F1 0.287, balanced accuracy 0.303** (chance 0.111)

- **canola detected at 5 % FPR: 69.1%** (n=191)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Barley | 0.31 | 0.17 | 0.22 | 95 |
| Canola | 0.82 | 0.71 | 0.76 | 191 |
| Chickpea | 0.33 | 0.21 | 0.26 | 29 |
| Faba Bean | 0.17 | 0.12 | 0.14 | 25 |
| Field Pea | 0.22 | 0.37 | 0.28 | 30 |
| Lentil | 0.00 | 0.00 | 0.00 | 23 |
| Lupin | 0.18 | 0.36 | 0.24 | 22 |
| Oat | 0.12 | 0.04 | 0.06 | 25 |
| Wheat | 0.55 | 0.76 | 0.64 | 219 |

Confusion (row = truth, col = predicted):

| |Barley|Canola|Chickp|Faba B|Field |Lentil|Lupin|Oat|Wheat|
|---|---|---|---|---|---|---|---|---|---|
| **Barley** |16|6|0|1|4|0|6|1|61|
| **Canola** |3|135|2|5|8|0|10|0|28|
| **Chickpea** |3|4|6|0|9|0|2|0|5|
| **Faba Bean** |1|2|4|3|3|0|2|0|10|
| **Field Pea** |2|4|3|1|11|0|3|0|6|
| **Lentil** |1|4|3|1|8|0|3|0|3|
| **Lupin** |3|4|0|0|1|1|8|0|5|
| **Oat** |1|1|0|0|2|0|1|1|19|
| **Wheat** |21|5|0|7|4|0|10|6|166|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.286, balanced accuracy 0.275**

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Barley | 0.21 | 0.19 | 0.20 | 322 |
| Canola | 0.82 | 0.69 | 0.75 | 682 |
| Chickpea | 0.43 | 0.28 | 0.34 | 134 |
| Faba Bean | 0.15 | 0.11 | 0.12 | 83 |
| Field Pea | 0.24 | 0.19 | 0.21 | 126 |
| Lentil | 0.20 | 0.10 | 0.13 | 81 |
| Lupin | 0.19 | 0.14 | 0.16 | 102 |
| Oat | 0.14 | 0.03 | 0.04 | 112 |
| Wheat | 0.52 | 0.76 | 0.61 | 835 |

Confusion (row = truth, col = predicted):

| |Barley|Canola|Chickp|Faba B|Field |Lentil|Lupin|Oat|Wheat|
|---|---|---|---|---|---|---|---|---|---|
| **Barley** |61|11|6|5|8|3|6|2|220|
| **Canola** |25|468|3|12|14|2|28|3|127|
| **Chickpea** |21|11|38|6|14|7|3|0|34|
| **Faba Bean** |5|6|10|9|7|6|4|0|36|
| **Field Pea** |19|19|12|9|24|9|3|1|30|
| **Lentil** |16|11|6|7|16|8|1|0|16|
| **Lupin** |11|18|0|4|5|1|14|1|48|
| **Oat** |18|4|1|0|3|1|1|3|81|
| **Wheat** |120|23|13|10|9|3|14|12|631|

### Where the signal is

Permutation importance on the 2023-24 holdout, macro-F1 scoring, summed within each family. Negative means the feature was not used and shuffling it happened to help.

| feature family | importance |
|---|---|
| `ndyi_pad_median_90` | +0.0024 |
| `ndvi_pad_median_90` | +0.0023 |
| `cfi_pad_median_90` | -0.0006 |
| `ndvi_pad_median` | -0.0073 |
| `ndyi_pad_median` | -0.0110 |
| `cfi_pad_median` | -0.0245 |

Top individual features: `cfi_pad_median_250`, `ndvi_pad_median_250`, `ndyi_pad_median_330`, `cfi_pad_median_110`, `cfi_pad_median__amp`, `cfi_pad_median_270`, `ndyi_pad_median_310`, `cfi_pad_median_230`, `ndyi_pad_median__p10`, `ndvi_pad_median_270`, `ndvi_pad_median_110`, `ndvi_pad_median_210`

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.287 | 0.303 |
| spatial (GroupKFold on site) | 0.286 | 0.275 |
