# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 248 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.895, balanced accuracy 0.898** (chance 0.333)

- **canola detected at 5 % FPR: 85.2%** (n=155)
- **average precision 0.939** (baseline = prevalence 0.285), ROC AUC 0.968

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.85 | 0.88 | 155 |
| Cereal | 0.95 | 0.96 | 0.96 | 279 |
| Legume | 0.81 | 0.88 | 0.85 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |132|7|16|
| **Cereal** |5|268|6|
| **Legume** |7|6|96|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.869, balanced accuracy 0.874** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.83 | 0.86 | 155 |
| Cereal | 0.96 | 0.95 | 0.96 | 279 |
| Legume | 0.75 | 0.83 | 0.79 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |129|3|23|
| **Cereal** |5|266|8|
| **Legume** |10|8|91|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.895 | 0.898 |
| spatial (GroupKFold on site) | 0.869 | 0.874 |
