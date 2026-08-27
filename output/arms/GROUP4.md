# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2935 paddocks, 51 features, 4 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Grazing 741, Legume 490
- **fixed test set**: scoring restricted to 892 of 2935 rows listed in `testkeep_group4_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 2043, test 892
- **macro F1 0.834, balanced accuracy 0.839** (chance 0.250)

- **canola detected at 5 % FPR: 89.0%** (n=155)
- **average precision 0.910** (baseline = prevalence 0.174), ROC AUC 0.966

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.88 | 0.83 | 0.85 | 155 |
| Cereal | 0.85 | 0.90 | 0.88 | 279 |
| Grazing | 0.98 | 0.91 | 0.94 | 349 |
| Legume | 0.61 | 0.72 | 0.66 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |128|8|2|17|
| **Cereal** |2|252|4|21|
| **Grazing** |6|14|318|11|
| **Legume** |9|21|1|78|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.862, balanced accuracy 0.862** (scored on 892 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.89 | 0.88 | 0.89 | 155 |
| Cereal | 0.89 | 0.91 | 0.90 | 279 |
| Grazing | 0.98 | 0.97 | 0.97 | 349 |
| Legume | 0.68 | 0.70 | 0.69 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |136|3|2|14|
| **Cereal** |4|253|4|18|
| **Grazing** |5|3|338|3|
| **Legume** |7|25|1|76|

(importance skipped: 'numpy.ndarray' object has no attribute 'values')

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.834 | 0.839 |
| spatial (GroupKFold on site) | 0.862 | 0.862 |
