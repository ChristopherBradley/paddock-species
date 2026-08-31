# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 493 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.880, balanced accuracy 0.880** (chance 0.333)

- **canola detected at 5 % FPR: 87.1%** (n=155)
- **average precision 0.939** (baseline = prevalence 0.285), ROC AUC 0.966

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.91 | 0.85 | 0.88 | 155 |
| Cereal | 0.94 | 0.95 | 0.95 | 279 |
| Legume | 0.79 | 0.83 | 0.81 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |132|7|16|
| **Cereal** |5|266|8|
| **Legume** |8|10|91|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.878, balanced accuracy 0.881** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.84 | 0.88 | 155 |
| Cereal | 0.96 | 0.96 | 0.96 | 279 |
| Legume | 0.76 | 0.84 | 0.80 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |130|3|22|
| **Cereal** |4|268|7|
| **Legume** |8|9|92|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.880 | 0.880 |
| spatial (GroupKFold on site) | 0.878 | 0.881 |
