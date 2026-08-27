# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2194 paddocks, 179 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.824, balanced accuracy 0.821** (chance 0.333)

- **canola detected at 5 % FPR: 85.8%** (n=155)
- **average precision 0.929** (baseline = prevalence 0.285), ROC AUC 0.972

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.91 | 0.81 | 0.86 | 155 |
| Cereal | 0.89 | 0.92 | 0.91 | 279 |
| Legume | 0.69 | 0.72 | 0.71 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |126|12|17|
| **Cereal** |2|258|19|
| **Legume** |10|20|79|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.829, balanced accuracy 0.831** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.85 | 0.88 | 155 |
| Cereal | 0.90 | 0.90 | 0.90 | 279 |
| Legume | 0.68 | 0.74 | 0.71 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |131|8|16|
| **Cereal** |4|252|23|
| **Legume** |8|20|81|

(importance skipped: 'numpy.ndarray' object has no attribute 'values')

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.824 | 0.821 |
| spatial (GroupKFold on site) | 0.829 | 0.831 |
