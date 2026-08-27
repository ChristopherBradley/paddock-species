# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2133 paddocks, 51 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 571, Cereal 1089, Legume 473
- **fixed test set**: scoring restricted to 497 of 2133 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1636, test 497
- **macro F1 0.812, balanced accuracy 0.809** (chance 0.333)

- **canola detected at 5 % FPR: 84.7%** (n=144)
- **average precision 0.923** (baseline = prevalence 0.290), ROC AUC 0.947

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.85 | 0.88 | 144 |
| Cereal | 0.88 | 0.90 | 0.89 | 253 |
| Legume | 0.65 | 0.68 | 0.66 | 100 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |122|6|16|
| **Cereal** |4|228|21|
| **Legume** |7|25|68|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.800, balanced accuracy 0.792** (scored on 497 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.83 | 0.87 | 144 |
| Cereal | 0.86 | 0.93 | 0.90 | 253 |
| Legume | 0.65 | 0.62 | 0.63 | 100 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |119|6|19|
| **Cereal** |3|235|15|
| **Legume** |7|31|62|

(importance skipped: 'numpy.ndarray' object has no attribute 'values')

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.812 | 0.809 |
| spatial (GroupKFold on site) | 0.800 | 0.792 |
