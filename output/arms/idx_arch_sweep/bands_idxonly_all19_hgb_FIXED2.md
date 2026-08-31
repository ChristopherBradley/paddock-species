# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 323 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.886, balanced accuracy 0.893** (chance 0.333)

- **canola detected at 5 % FPR: 85.8%** (n=155)
- **average precision 0.938** (baseline = prevalence 0.285), ROC AUC 0.965

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.85 | 0.88 | 155 |
| Cereal | 0.96 | 0.95 | 0.95 | 279 |
| Legume | 0.77 | 0.88 | 0.82 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |132|4|19|
| **Cereal** |5|264|10|
| **Legume** |7|6|96|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.867, balanced accuracy 0.869** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.86 | 0.88 | 155 |
| Cereal | 0.95 | 0.95 | 0.95 | 279 |
| Legume | 0.75 | 0.80 | 0.77 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |133|3|19|
| **Cereal** |4|265|10|
| **Legume** |10|12|87|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.886 | 0.893 |
| spatial (GroupKFold on site) | 0.867 | 0.869 |
