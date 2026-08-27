# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2133 paddocks, 51 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 571, Cereal 1089, Legume 473
- **fixed test set**: scoring restricted to 497 of 2133 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1636, test 497
- **macro F1 0.823, balanced accuracy 0.821** (chance 0.333)

- **canola detected at 5 % FPR: 86.8%** (n=144)
- **average precision 0.943** (baseline = prevalence 0.290), ROC AUC 0.964

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.94 | 0.83 | 0.88 | 144 |
| Cereal | 0.89 | 0.92 | 0.90 | 253 |
| Legume | 0.66 | 0.72 | 0.69 | 100 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |119|8|17|
| **Cereal** |1|232|20|
| **Legume** |7|21|72|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.825, balanced accuracy 0.823** (scored on 497 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.89 | 0.83 | 0.86 | 144 |
| Cereal | 0.91 | 0.93 | 0.92 | 253 |
| Legume | 0.68 | 0.71 | 0.70 | 100 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |119|5|20|
| **Cereal** |4|236|13|
| **Legume** |11|18|71|

(importance skipped: 'numpy.ndarray' object has no attribute 'values')

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.823 | 0.821 |
| spatial (GroupKFold on site) | 0.825 | 0.823 |
