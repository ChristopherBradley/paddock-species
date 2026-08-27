# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2194 paddocks, 128 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.775, balanced accuracy 0.766** (chance 0.333)

- **canola detected at 5 % FPR: 74.2%** (n=155)
- **average precision 0.862** (baseline = prevalence 0.285), ROC AUC 0.941

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.87 | 0.72 | 0.79 | 155 |
| Cereal | 0.85 | 0.93 | 0.89 | 279 |
| Legume | 0.65 | 0.65 | 0.65 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |111|18|26|
| **Cereal** |6|260|13|
| **Legume** |10|28|71|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.789, balanced accuracy 0.787** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.88 | 0.73 | 0.80 | 155 |
| Cereal | 0.88 | 0.92 | 0.90 | 279 |
| Legume | 0.63 | 0.72 | 0.67 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |113|15|27|
| **Cereal** |4|256|19|
| **Legume** |11|20|78|

(importance skipped: 'numpy.ndarray' object has no attribute 'values')

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.775 | 0.766 |
| spatial (GroupKFold on site) | 0.789 | 0.787 |
