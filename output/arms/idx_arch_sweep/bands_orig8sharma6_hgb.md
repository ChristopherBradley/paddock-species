# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 408 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.883, balanced accuracy 0.882** (chance 0.333)

- **canola detected at 5 % FPR: 87.1%** (n=155)
- **average precision 0.943** (baseline = prevalence 0.285), ROC AUC 0.970

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.91 | 0.85 | 0.88 | 155 |
| Cereal | 0.94 | 0.96 | 0.95 | 279 |
| Legume | 0.81 | 0.83 | 0.82 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |132|7|16|
| **Cereal** |5|268|6|
| **Legume** |8|10|91|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.869, balanced accuracy 0.873** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.83 | 0.86 | 155 |
| Cereal | 0.96 | 0.96 | 0.96 | 279 |
| Legume | 0.75 | 0.83 | 0.79 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |128|3|24|
| **Cereal** |5|267|7|
| **Legume** |9|9|91|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.883 | 0.882 |
| spatial (GroupKFold on site) | 0.869 | 0.873 |
