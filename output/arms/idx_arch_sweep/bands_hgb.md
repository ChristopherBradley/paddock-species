# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 391 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.841, balanced accuracy 0.845** (chance 0.333)

- **canola detected at 5 % FPR: 86.5%** (n=155)
- **average precision 0.932** (baseline = prevalence 0.285), ROC AUC 0.963

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.91 | 0.83 | 0.87 | 155 |
| Cereal | 0.93 | 0.93 | 0.93 | 279 |
| Legume | 0.68 | 0.78 | 0.73 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |128|3|24|
| **Cereal** |4|259|16|
| **Legume** |8|16|85|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.846, balanced accuracy 0.850** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.93 | 0.82 | 0.87 | 155 |
| Cereal | 0.93 | 0.93 | 0.93 | 279 |
| Legume | 0.69 | 0.80 | 0.74 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |127|3|25|
| **Cereal** |4|260|15|
| **Legume** |6|16|87|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.841 | 0.845 |
| spatial (GroupKFold on site) | 0.846 | 0.850 |
