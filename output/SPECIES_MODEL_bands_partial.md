# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 1404 paddocks, 274 features, 9 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Barley 148, Canola 415, Chickpea 75, Faba Bean 47, Field Pea 80, Lentil 51, Lupin 57, Oat 65, Wheat 466

### Temporal transfer — train <=2022, test 2023-24

- train 1084, test 320
- **macro F1 0.338, balanced accuracy 0.340** (chance 0.111)

- **canola detected at 5 % FPR: 48.7%** (n=78)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Barley | 0.31 | 0.10 | 0.15 | 51 |
| Canola | 0.71 | 0.76 | 0.73 | 78 |
| Chickpea | 0.55 | 0.33 | 0.41 | 18 |
| Faba Bean | 0.20 | 0.21 | 0.21 | 14 |
| Field Pea | 0.25 | 0.12 | 0.16 | 17 |
| Lentil | 0.25 | 0.25 | 0.25 | 12 |
| Lupin | 0.50 | 0.46 | 0.48 | 13 |
| Oat | 0.00 | 0.00 | 0.00 | 14 |
| Wheat | 0.53 | 0.83 | 0.65 | 103 |

Confusion (row = truth, col = predicted):

| |Barley|Canola|Chickp|Faba B|Field |Lentil|Lupin|Oat|Wheat|
|---|---|---|---|---|---|---|---|---|---|
| **Barley** |5|5|0|1|2|0|0|1|37|
| **Canola** |3|59|0|4|0|0|4|0|8|
| **Chickpea** |0|3|6|2|0|1|0|0|6|
| **Faba Bean** |0|2|0|3|1|2|1|1|4|
| **Field Pea** |0|5|3|1|2|3|1|0|2|
| **Lentil** |0|4|1|1|0|3|0|0|3|
| **Lupin** |0|2|0|1|1|0|6|0|3|
| **Oat** |1|0|0|0|1|1|0|0|11|
| **Wheat** |7|3|1|2|1|2|0|2|85|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.295, balanced accuracy 0.292**

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Barley | 0.17 | 0.13 | 0.14 | 148 |
| Canola | 0.82 | 0.66 | 0.73 | 415 |
| Chickpea | 0.29 | 0.19 | 0.23 | 75 |
| Faba Bean | 0.27 | 0.17 | 0.21 | 47 |
| Field Pea | 0.26 | 0.29 | 0.27 | 80 |
| Lentil | 0.22 | 0.27 | 0.25 | 51 |
| Lupin | 0.29 | 0.16 | 0.20 | 57 |
| Oat | 0.00 | 0.00 | 0.00 | 65 |
| Wheat | 0.52 | 0.76 | 0.62 | 466 |

Confusion (row = truth, col = predicted):

| |Barley|Canola|Chickp|Faba B|Field |Lentil|Lupin|Oat|Wheat|
|---|---|---|---|---|---|---|---|---|---|
| **Barley** |19|9|2|3|6|2|2|4|101|
| **Canola** |11|272|5|5|10|11|12|1|88|
| **Chickpea** |2|2|14|2|17|11|0|0|27|
| **Faba Bean** |4|3|6|8|8|7|1|0|10|
| **Field Pea** |4|7|5|4|23|11|1|0|25|
| **Lentil** |1|3|3|4|12|14|1|0|13|
| **Lupin** |10|15|1|2|2|0|9|0|18|
| **Oat** |8|4|3|0|1|1|1|0|47|
| **Wheat** |56|15|10|2|9|6|4|8|356|

### Where the signal is

Permutation importance on the 2023-24 holdout, macro-F1 scoring, summed within each family. Negative means the feature was not used and shuffling it happened to help.

| feature family | importance |
|---|---|
| `red_edge_2` | +0.1645 |
| `ndyi` | +0.1310 |
| `cfi` | +0.0952 |
| `red_edge_1` | +0.0895 |
| `green` | +0.0847 |
| `ndwi` | +0.0801 |
| `ndre` | +0.0781 |
| `nbr` | +0.0744 |
| `nir_2` | +0.0735 |
| `swir_2` | +0.0730 |
| `swir_3` | +0.0709 |
| `blue` | +0.0682 |
| `red_edge_3` | +0.0590 |
| `psri` | +0.0540 |
| `ndvi` | +0.0461 |
| `nir_1` | +0.0447 |

Top individual features: `red_edge_2_250`, `ndre_110`, `ndyi_290`, `red_edge_2_270`, `cfi_270`, `ndvi_110`, `ndwi_110`, `ndre_90`, `swir_ratio_190`, `ndwi_190`, `nbr_250`, `nbr_330`

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.338 | 0.340 |
| spatial (GroupKFold on site) | 0.295 | 0.292 |
