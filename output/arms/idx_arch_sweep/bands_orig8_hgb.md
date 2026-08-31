# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 306 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.848, balanced accuracy 0.855** (chance 0.333)

- **canola detected at 5 % FPR: 85.2%** (n=155)
- **average precision 0.936** (baseline = prevalence 0.285), ROC AUC 0.966

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.85 | 0.88 | 155 |
| Cereal | 0.94 | 0.91 | 0.92 | 279 |
| Legume | 0.68 | 0.81 | 0.74 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |132|3|20|
| **Cereal** |5|253|21|
| **Legume** |7|14|88|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.840, balanced accuracy 0.841** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.82 | 0.87 | 155 |
| Cereal | 0.92 | 0.93 | 0.93 | 279 |
| Legume | 0.69 | 0.77 | 0.73 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |127|5|23|
| **Cereal** |4|260|15|
| **Legume** |7|18|84|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.848 | 0.855 |
| spatial (GroupKFold on site) | 0.840 | 0.841 |
