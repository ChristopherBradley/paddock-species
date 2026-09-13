# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 153 features, 9 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Barley 227, Canola 585, Chickpea 126, Faba Bean 80, Field Pea 120, Lentil 78, Lupin 86, Oat 81, Wheat 811
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.364, balanced accuracy 0.384** (chance 0.111)

- **canola detected at 5 % FPR: 89.0%** (n=155)
- **average precision 0.943** (baseline = prevalence 0.285), ROC AUC 0.966

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Barley | 0.42 | 0.15 | 0.22 | 74 |
| Canola | 0.88 | 0.89 | 0.88 | 155 |
| Chickpea | 0.86 | 0.24 | 0.38 | 25 |
| Faba Bean | 0.29 | 0.25 | 0.27 | 24 |
| Field Pea | 0.29 | 0.62 | 0.40 | 26 |
| Lentil | 0.00 | 0.00 | 0.00 | 19 |
| Lupin | 0.26 | 0.40 | 0.32 | 15 |
| Oat | 0.17 | 0.06 | 0.08 | 18 |
| Wheat | 0.65 | 0.86 | 0.74 | 187 |

Confusion (row = truth, col = predicted):

| |Barley|Canola|Chickp|Faba B|Field |Lentil|Lupin|Oat|Wheat|
|---|---|---|---|---|---|---|---|---|---|
| **Barley** |11|3|0|1|1|0|1|1|56|
| **Canola** |1|138|0|2|6|0|3|0|5|
| **Chickpea** |0|1|6|4|10|0|2|0|2|
| **Faba Bean** |3|3|0|6|3|0|4|0|5|
| **Field Pea** |0|4|0|2|16|1|2|0|1|
| **Lentil** |0|2|1|2|9|0|4|0|1|
| **Lupin** |0|3|0|2|2|0|6|0|2|
| **Oat** |1|0|0|0|1|0|0|1|15|
| **Wheat** |10|3|0|2|7|0|1|4|160|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.328, balanced accuracy 0.330** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Barley | 0.35 | 0.15 | 0.21 | 74 |
| Canola | 0.88 | 0.88 | 0.88 | 155 |
| Chickpea | 0.33 | 0.12 | 0.18 | 25 |
| Faba Bean | 0.33 | 0.21 | 0.26 | 24 |
| Field Pea | 0.26 | 0.42 | 0.32 | 26 |
| Lentil | 0.25 | 0.16 | 0.19 | 19 |
| Lupin | 0.23 | 0.20 | 0.21 | 15 |
| Oat | 0.00 | 0.00 | 0.00 | 18 |
| Wheat | 0.62 | 0.83 | 0.71 | 187 |

Confusion (row = truth, col = predicted):

| |Barley|Canola|Chickp|Faba B|Field |Lentil|Lupin|Oat|Wheat|
|---|---|---|---|---|---|---|---|---|---|
| **Barley** |11|3|0|0|0|1|1|3|55|
| **Canola** |0|136|0|2|6|3|0|0|8|
| **Chickpea** |0|1|3|2|11|2|1|0|5|
| **Faba Bean** |1|4|3|5|3|0|4|0|4|
| **Field Pea** |1|4|1|1|11|3|2|0|3|
| **Lentil** |0|2|1|1|9|3|1|0|2|
| **Lupin** |0|4|0|1|2|0|3|0|5|
| **Oat** |2|0|0|1|0|0|0|0|15|
| **Wheat** |16|1|1|2|1|0|1|9|156|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.364 | 0.384 |
| spatial (GroupKFold on site) | 0.328 | 0.330 |
