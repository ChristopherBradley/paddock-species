# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 333 features, 3 classes
- model: logistic regression, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.801, balanced accuracy 0.814** (chance 0.333)

- **canola detected at 5 % FPR: 74.2%** (n=155)
- **average precision 0.872** (baseline = prevalence 0.285), ROC AUC 0.945

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.82 | 0.76 | 0.79 | 155 |
| Cereal | 0.95 | 0.88 | 0.91 | 279 |
| Legume | 0.62 | 0.80 | 0.70 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |118|3|34|
| **Cereal** |14|246|19|
| **Legume** |12|10|87|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.813, balanced accuracy 0.822** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.83 | 0.76 | 0.79 | 155 |
| Cereal | 0.94 | 0.91 | 0.93 | 279 |
| Legume | 0.66 | 0.80 | 0.72 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |118|5|32|
| **Cereal** |13|253|13|
| **Legume** |12|10|87|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.801 | 0.814 |
| spatial (GroupKFold on site) | 0.813 | 0.822 |
