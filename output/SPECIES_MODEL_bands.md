# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2477 paddocks, 274 features, 9 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Barley 322, Canola 682, Chickpea 134, Faba Bean 83, Field Pea 126, Lentil 81, Lupin 102, Oat 112, Wheat 835

### Temporal transfer — train <=2022, test 2023-24

- train 1818, test 659
- **macro F1 0.301, balanced accuracy 0.314** (chance 0.111)

- **canola detected at 5 % FPR: 66.0%** (n=191)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Barley | 0.28 | 0.16 | 0.20 | 95 |
| Canola | 0.81 | 0.74 | 0.77 | 191 |
| Chickpea | 0.56 | 0.31 | 0.40 | 29 |
| Faba Bean | 0.20 | 0.24 | 0.22 | 25 |
| Field Pea | 0.25 | 0.53 | 0.34 | 30 |
| Lentil | 0.00 | 0.00 | 0.00 | 23 |
| Lupin | 0.08 | 0.05 | 0.06 | 22 |
| Oat | 0.13 | 0.08 | 0.10 | 25 |
| Wheat | 0.55 | 0.72 | 0.62 | 219 |

Confusion (row = truth, col = predicted):

| |Barley|Canola|Chickp|Faba B|Field |Lentil|Lupin|Oat|Wheat|
|---|---|---|---|---|---|---|---|---|---|
| **Barley** |15|7|0|1|10|0|2|1|59|
| **Canola** |9|141|6|6|0|0|5|0|24|
| **Chickpea** |0|3|9|0|10|1|1|0|5|
| **Faba Bean** |1|4|1|6|5|0|1|0|7|
| **Field Pea** |0|6|0|0|16|0|0|1|7|
| **Lentil** |0|4|0|0|14|0|0|0|5|
| **Lupin** |2|4|0|4|3|0|1|1|7|
| **Oat** |3|1|0|1|1|0|0|2|17|
| **Wheat** |24|4|0|12|6|4|2|10|157|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.287, balanced accuracy 0.280**

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Barley | 0.22 | 0.19 | 0.20 | 322 |
| Canola | 0.82 | 0.66 | 0.73 | 682 |
| Chickpea | 0.36 | 0.25 | 0.30 | 134 |
| Faba Bean | 0.18 | 0.17 | 0.18 | 83 |
| Field Pea | 0.23 | 0.21 | 0.22 | 126 |
| Lentil | 0.21 | 0.16 | 0.18 | 81 |
| Lupin | 0.15 | 0.09 | 0.11 | 102 |
| Oat | 0.10 | 0.03 | 0.04 | 112 |
| Wheat | 0.52 | 0.77 | 0.62 | 835 |

Confusion (row = truth, col = predicted):

| |Barley|Canola|Chickp|Faba B|Field |Lentil|Lupin|Oat|Wheat|
|---|---|---|---|---|---|---|---|---|---|
| **Barley** |61|12|4|4|6|2|4|6|223|
| **Canola** |29|448|11|13|16|12|18|3|132|
| **Chickpea** |12|5|34|15|25|7|5|0|31|
| **Faba Bean** |4|9|5|14|9|10|3|0|29|
| **Field Pea** |14|10|15|10|26|14|4|3|30|
| **Lentil** |7|6|8|10|19|13|4|1|13|
| **Lupin** |13|23|1|4|6|2|9|0|44|
| **Oat** |19|6|2|1|2|0|1|3|78|
| **Wheat** |117|25|14|5|6|3|11|13|641|

### Where the signal is

Permutation importance on the 2023-24 holdout, macro-F1 scoring, summed within each family. Negative means the feature was not used and shuffling it happened to help.

| feature family | importance |
|---|---|
| `blue` | +0.0158 |
| `ndyi` | +0.0125 |
| `ndre_90` | +0.0079 |
| `green` | +0.0053 |
| `swir_2` | +0.0049 |
| `psri_90` | +0.0039 |
| `nir_1_90` | +0.0027 |
| `swir_3_90` | +0.0023 |
| `ndyi_90` | +0.0021 |
| `blue_90` | +0.0020 |
| `ndvi_90` | +0.0018 |
| `nbr_90` | +0.0014 |
| `red_edge_2_90` | +0.0011 |
| `red_edge_1_90` | +0.0003 |
| `swir_3` | -0.0000 |
| `nir_2_90` | -0.0002 |

Top individual features: `ndre_90`, `blue__p10`, `nbr_170`, `ndyi_110`, `green_170`, `blue__peak_doy`, `ndyi_330`, `nir_1_210`, `blue__p90`, `psri_290`, `blue_230`, `psri_170`

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.301 | 0.314 |
| spatial (GroupKFold on site) | 0.287 | 0.280 |
