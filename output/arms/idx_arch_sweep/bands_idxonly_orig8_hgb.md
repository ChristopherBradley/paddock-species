# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 146 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.839, balanced accuracy 0.843** (chance 0.333)

- **canola detected at 5 % FPR: 85.2%** (n=155)
- **average precision 0.938** (baseline = prevalence 0.285), ROC AUC 0.967

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.93 | 0.83 | 0.87 | 155 |
| Cereal | 0.92 | 0.91 | 0.92 | 279 |
| Legume | 0.68 | 0.79 | 0.73 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |128|6|21|
| **Cereal** |4|255|20|
| **Legume** |6|17|86|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.854, balanced accuracy 0.856** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.93 | 0.82 | 0.87 | 155 |
| Cereal | 0.94 | 0.94 | 0.94 | 279 |
| Legume | 0.70 | 0.81 | 0.75 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |127|3|25|
| **Cereal** |4|263|12|
| **Legume** |6|15|88|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.839 | 0.843 |
| spatial (GroupKFold on site) | 0.854 | 0.856 |
