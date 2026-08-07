# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2477 paddocks, 51 features, 9 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Barley 322, Canola 682, Chickpea 134, Faba Bean 83, Field Pea 126, Lentil 81, Lupin 102, Oat 112, Wheat 835

### Temporal transfer — train <=2022, test 2023-24

- train 1818, test 659
- **macro F1 0.316, balanced accuracy 0.329** (chance 0.111)

- **canola detected at 5 % FPR: 77.0%** (n=191)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Barley | 0.38 | 0.16 | 0.22 | 95 |
| Canola | 0.85 | 0.77 | 0.81 | 191 |
| Chickpea | 0.50 | 0.24 | 0.33 | 29 |
| Faba Bean | 0.40 | 0.16 | 0.23 | 25 |
| Field Pea | 0.17 | 0.37 | 0.23 | 30 |
| Lentil | 0.20 | 0.04 | 0.07 | 23 |
| Lupin | 0.20 | 0.41 | 0.27 | 22 |
| Oat | 0.00 | 0.00 | 0.00 | 25 |
| Wheat | 0.59 | 0.81 | 0.68 | 219 |

Confusion (row = truth, col = predicted):

| |Barley|Canola|Chickp|Faba B|Field |Lentil|Lupin|Oat|Wheat|
|---|---|---|---|---|---|---|---|---|---|
| **Barley** |15|4|0|1|8|0|5|2|60|
| **Canola** |3|147|2|3|11|0|9|0|16|
| **Chickpea** |1|3|7|0|11|0|2|0|5|
| **Faba Bean** |3|3|2|4|6|0|2|0|5|
| **Field Pea** |1|3|1|1|11|1|4|1|7|
| **Lentil** |0|4|1|1|10|1|3|0|3|
| **Lupin** |1|3|0|0|1|0|9|0|8|
| **Oat** |2|1|0|0|1|1|1|0|19|
| **Wheat** |13|5|1|0|7|2|10|3|178|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.273, balanced accuracy 0.267**

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Barley | 0.19 | 0.13 | 0.15 | 322 |
| Canola | 0.81 | 0.68 | 0.74 | 682 |
| Chickpea | 0.39 | 0.24 | 0.29 | 134 |
| Faba Bean | 0.13 | 0.07 | 0.09 | 83 |
| Field Pea | 0.28 | 0.28 | 0.28 | 126 |
| Lentil | 0.23 | 0.12 | 0.16 | 81 |
| Lupin | 0.16 | 0.11 | 0.13 | 102 |
| Oat | 0.00 | 0.00 | 0.00 | 112 |
| Wheat | 0.50 | 0.77 | 0.61 | 835 |

Confusion (row = truth, col = predicted):

| |Barley|Canola|Chickp|Faba B|Field |Lentil|Lupin|Oat|Wheat|
|---|---|---|---|---|---|---|---|---|---|
| **Barley** |42|11|10|4|7|3|5|2|238|
| **Canola** |16|465|3|8|16|5|27|7|135|
| **Chickpea** |15|12|32|7|17|7|3|0|41|
| **Faba Bean** |7|10|8|6|8|6|4|0|34|
| **Field Pea** |16|14|7|5|35|8|2|1|38|
| **Lentil** |10|10|3|5|22|10|0|0|21|
| **Lupin** |11|22|0|3|3|1|11|0|51|
| **Oat** |19|3|0|1|6|0|1|0|82|
| **Wheat** |89|30|20|8|12|3|15|13|645|

### Where the signal is (permutation importance, summed)

| feature family | importance |
|---|---|
| `ndyi` | -0.0156 |
| `cfi` | -0.0456 |
| `ndvi` | -0.0578 |

Top individual features: `ndvi_pad_median_290`, `ndyi_pad_median__p10`, `cfi_pad_median_150`, `ndyi_pad_median_130`, `ndvi_pad_median__p10`, `cfi_pad_median_270`, `ndyi_pad_median_330`, `ndyi_pad_median_170`, `ndvi_pad_median_130`, `cfi_pad_median_330`, `cfi_pad_median__amp`, `ndvi_pad_median_210`

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.316 | 0.329 |
| spatial (GroupKFold on site) | 0.273 | 0.267 |
