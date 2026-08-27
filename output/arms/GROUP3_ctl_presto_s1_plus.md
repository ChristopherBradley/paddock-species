# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2133 paddocks, 230 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 571, Cereal 1089, Legume 473
- **fixed test set**: scoring restricted to 497 of 2133 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1636, test 497
- **macro F1 0.857, balanced accuracy 0.856** (chance 0.333)

- **canola detected at 5 % FPR: 86.1%** (n=144)
- **average precision 0.930** (baseline = prevalence 0.290), ROC AUC 0.971

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.93 | 0.85 | 0.89 | 144 |
| Cereal | 0.92 | 0.94 | 0.93 | 253 |
| Legume | 0.74 | 0.78 | 0.76 | 100 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |122|6|16|
| **Cereal** |3|238|12|
| **Legume** |6|16|78|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.858, balanced accuracy 0.856** (scored on 497 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.93 | 0.85 | 0.89 | 144 |
| Cereal | 0.91 | 0.94 | 0.93 | 253 |
| Legume | 0.74 | 0.78 | 0.76 | 100 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |122|6|16|
| **Cereal** |4|238|11|
| **Legume** |5|17|78|

(importance skipped: 'numpy.ndarray' object has no attribute 'values')

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.857 | 0.856 |
| spatial (GroupKFold on site) | 0.858 | 0.856 |
