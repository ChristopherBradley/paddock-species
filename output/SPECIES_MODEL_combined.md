# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2476 paddocks, 325 features, 9 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Barley 322, Canola 682, Chickpea 134, Faba Bean 83, Field Pea 126, Lentil 81, Lupin 102, Oat 112, Wheat 834

### Temporal transfer — train <=2022, test 2023-24

- train 1817, test 659
- **macro F1 0.302, balanced accuracy 0.308** (chance 0.111)

- **canola detected at 5 % FPR: 65.4%** (n=191)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Barley | 0.27 | 0.13 | 0.17 | 95 |
| Canola | 0.78 | 0.74 | 0.76 | 191 |
| Chickpea | 0.67 | 0.34 | 0.45 | 29 |
| Faba Bean | 0.17 | 0.20 | 0.18 | 25 |
| Field Pea | 0.25 | 0.47 | 0.32 | 30 |
| Lentil | 0.17 | 0.04 | 0.07 | 23 |
| Lupin | 0.07 | 0.05 | 0.06 | 22 |
| Oat | 0.09 | 0.04 | 0.06 | 25 |
| Wheat | 0.56 | 0.76 | 0.64 | 219 |

Confusion (row = truth, col = predicted):

| |Barley|Canola|Chickp|Faba B|Field |Lentil|Lupin|Oat|Wheat|
|---|---|---|---|---|---|---|---|---|---|
| **Barley** |12|7|0|1|9|0|1|1|64|
| **Canola** |6|142|0|8|6|3|5|2|19|
| **Chickpea** |3|4|10|0|4|1|0|0|7|
| **Faba Bean** |1|4|1|5|5|0|1|0|8|
| **Field Pea** |0|6|2|0|14|1|0|1|6|
| **Lentil** |0|4|2|0|9|1|2|0|5|
| **Lupin** |2|5|0|4|3|0|1|2|5|
| **Oat** |1|2|0|1|0|0|1|1|19|
| **Wheat** |20|7|0|11|7|0|3|4|167|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.302, balanced accuracy 0.293**

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Barley | 0.21 | 0.16 | 0.18 | 322 |
| Canola | 0.80 | 0.67 | 0.73 | 682 |
| Chickpea | 0.41 | 0.31 | 0.35 | 134 |
| Faba Bean | 0.23 | 0.22 | 0.22 | 83 |
| Field Pea | 0.28 | 0.21 | 0.24 | 126 |
| Lentil | 0.21 | 0.16 | 0.18 | 81 |
| Lupin | 0.24 | 0.12 | 0.16 | 102 |
| Oat | 0.08 | 0.02 | 0.03 | 112 |
| Wheat | 0.52 | 0.77 | 0.62 | 834 |

Confusion (row = truth, col = predicted):

| |Barley|Canola|Chickp|Faba B|Field |Lentil|Lupin|Oat|Wheat|
|---|---|---|---|---|---|---|---|---|---|
| **Barley** |53|15|5|3|7|3|4|7|225|
| **Canola** |29|457|8|17|17|8|15|0|131|
| **Chickpea** |16|8|41|11|8|7|3|0|40|
| **Faba Bean** |9|7|8|18|6|9|3|1|22|
| **Field Pea** |17|18|14|9|27|12|4|1|24|
| **Lentil** |8|8|7|11|15|13|3|1|15|
| **Lupin** |11|21|1|4|2|2|12|0|49|
| **Oat** |13|6|0|0|2|2|1|2|86|
| **Wheat** |98|33|16|6|11|6|6|14|644|

### Where the signal is

Permutation importance on the 2023-24 holdout, macro-F1 scoring, summed within each family. Negative means the feature was not used and shuffling it happened to help.

| feature family | importance |
|---|---|
| `swir_ratio_330@bands` | +0.0115 |
| `ndwi_290@bands` | +0.0085 |
| `blue_250@bands` | +0.0068 |
| `ndvi_110@bands` | +0.0060 |
| `psri_170@bands` | +0.0057 |
| `ndyi_pad_median_250@indices` | +0.0054 |
| `ndvi_pad_median_310@indices` | +0.0053 |
| `swir_ratio_210@bands` | +0.0053 |
| `cfi_pad_median_230@indices` | +0.0050 |
| `ndyi_230@bands` | +0.0047 |
| `swir_3_170@bands` | +0.0047 |
| `ndyi_290@bands` | +0.0046 |
| `ndvi_pad_median_130@indices` | +0.0046 |
| `cfi_pad_median_310@indices` | +0.0044 |
| `cfi_230@bands` | +0.0042 |
| `nir_2_210@bands` | +0.0042 |

Top individual features: `swir_ratio_330@bands`, `red_edge_2__p90@bands`, `ndwi_290@bands`, `blue_250@bands`, `ndvi_110@bands`, `psri_170@bands`, `ndyi_pad_median_250@indices`, `ndvi_pad_median_310@indices`, `swir_ratio_210@bands`, `cfi_pad_median_230@indices`, `ndyi_230@bands`, `swir_3_170@bands`

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.302 | 0.308 |
| spatial (GroupKFold on site) | 0.302 | 0.293 |
