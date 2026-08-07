# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2477 paddocks, 274 features, 9 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Barley 322, Canola 682, Chickpea 134, Faba Bean 83, Field Pea 126, Lentil 81, Lupin 102, Oat 112, Wheat 835

### Temporal transfer — train <=2022, test 2023-24

- train 1818, test 659
- **macro F1 0.319, balanced accuracy 0.321** (chance 0.111)

- **canola detected at 5 % FPR: 69.1%** (n=191)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Barley | 0.27 | 0.19 | 0.22 | 95 |
| Canola | 0.83 | 0.68 | 0.75 | 191 |
| Chickpea | 0.43 | 0.34 | 0.38 | 29 |
| Faba Bean | 0.41 | 0.28 | 0.33 | 25 |
| Field Pea | 0.17 | 0.33 | 0.23 | 30 |
| Lentil | 0.12 | 0.09 | 0.10 | 23 |
| Lupin | 0.20 | 0.23 | 0.21 | 22 |
| Oat | 0.00 | 0.00 | 0.00 | 25 |
| Wheat | 0.56 | 0.75 | 0.64 | 219 |

Confusion (row = truth, col = predicted):

| |Barley|Canola|Chickp|Faba B|Field |Lentil|Lupin|Oat|Wheat|
|---|---|---|---|---|---|---|---|---|---|
| **Barley** |18|6|2|3|5|0|3|0|58|
| **Canola** |8|130|0|0|22|3|10|0|18|
| **Chickpea** |0|1|10|3|5|1|1|0|8|
| **Faba Bean** |2|3|1|7|1|3|0|2|6|
| **Field Pea** |0|6|2|1|10|1|2|0|8|
| **Lentil** |0|4|2|1|7|2|1|0|6|
| **Lupin** |1|2|3|0|2|0|5|0|9|
| **Oat** |5|1|0|0|1|2|0|0|16|
| **Wheat** |33|4|3|2|5|4|3|1|164|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.285, balanced accuracy 0.278**

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Barley | 0.22 | 0.19 | 0.21 | 322 |
| Canola | 0.80 | 0.67 | 0.73 | 682 |
| Chickpea | 0.37 | 0.30 | 0.33 | 134 |
| Faba Bean | 0.17 | 0.14 | 0.16 | 83 |
| Field Pea | 0.16 | 0.17 | 0.17 | 126 |
| Lentil | 0.18 | 0.12 | 0.14 | 81 |
| Lupin | 0.23 | 0.14 | 0.17 | 102 |
| Oat | 0.10 | 0.03 | 0.04 | 112 |
| Wheat | 0.52 | 0.74 | 0.61 | 835 |

Confusion (row = truth, col = predicted):

| |Barley|Canola|Chickp|Faba B|Field |Lentil|Lupin|Oat|Wheat|
|---|---|---|---|---|---|---|---|---|---|
| **Barley** |62|11|2|6|10|2|3|4|222|
| **Canola** |36|454|9|5|40|10|18|5|105|
| **Chickpea** |14|3|40|10|15|9|2|2|39|
| **Faba Bean** |7|5|12|12|6|10|3|0|28|
| **Field Pea** |10|22|18|9|22|11|6|1|27|
| **Lentil** |6|6|13|11|14|10|6|0|15|
| **Lupin** |5|27|3|5|5|3|14|1|39|
| **Oat** |13|8|0|2|4|0|1|3|81|
| **Wheat** |128|28|11|10|21|2|7|14|614|

### Where the signal is

Permutation importance on the 2023-24 holdout, macro-F1 scoring, summed within each family. Negative means the feature was not used and shuffling it happened to help.

| feature family | importance |
|---|---|
| `red_edge_2` | +0.0416 |
| `ndwi` | +0.0258 |
| `green` | +0.0213 |
| `blue` | +0.0192 |
| `cfi` | +0.0182 |
| `swir_ratio` | +0.0164 |
| `nbr` | +0.0150 |
| `red_edge_1` | +0.0138 |
| `ndre` | +0.0110 |
| `nir_1` | +0.0076 |
| `ndyi` | +0.0003 |
| `blue_90` | +0.0000 |
| `cfi_90` | +0.0000 |
| `ndyi_90` | +0.0000 |
| `ndre_90` | +0.0000 |
| `ndwi_90` | +0.0000 |

Top individual features: `red_edge_2__amp`, `blue__p10`, `swir_ratio_210`, `ndwi_190`, `cfi_290`, `green_230`, `red_edge_2_270`, `red_edge_1_230`, `nir_1_190`, `ndre_230`, `red_edge_2_250`, `nbr_210`

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.319 | 0.321 |
| spatial (GroupKFold on site) | 0.285 | 0.278 |
