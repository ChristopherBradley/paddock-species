# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 231 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.845, balanced accuracy 0.850** (chance 0.333)

- **canola detected at 5 % FPR: 85.2%** (n=155)
- **average precision 0.935** (baseline = prevalence 0.285), ROC AUC 0.965

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.94 | 0.84 | 0.88 | 155 |
| Cereal | 0.93 | 0.91 | 0.92 | 279 |
| Legume | 0.67 | 0.80 | 0.73 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |130|3|22|
| **Cereal** |4|255|20|
| **Legume** |5|17|87|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.833, balanced accuracy 0.833** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.82 | 0.87 | 155 |
| Cereal | 0.92 | 0.93 | 0.92 | 279 |
| Legume | 0.67 | 0.75 | 0.71 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |127|3|25|
| **Cereal** |5|259|15|
| **Legume** |6|21|82|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.845 | 0.850 |
| spatial (GroupKFold on site) | 0.833 | 0.833 |
