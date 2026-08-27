# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2133 paddocks, 51 features, 2 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 571, Other 1562
- **fixed test set**: scoring restricted to 497 of 2133 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1636, test 497
- **macro F1 0.919, balanced accuracy 0.903** (chance 0.500)

- **canola detected at 5 % FPR: 86.8%** (n=144)
- **average precision 0.936** (baseline = prevalence 0.290), ROC AUC 0.954

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.94 | 0.83 | 0.88 | 144 |
| Other | 0.93 | 0.98 | 0.96 | 353 |

Confusion (row = truth, col = predicted):

| |Canola|Other|
|---|---|---|
| **Canola** |119|25|
| **Other** |7|346|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.908, balanced accuracy 0.891** (scored on 497 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.94 | 0.81 | 0.87 | 144 |
| Other | 0.92 | 0.98 | 0.95 | 353 |

Confusion (row = truth, col = predicted):

| |Canola|Other|
|---|---|---|
| **Canola** |116|28|
| **Other** |8|345|

(importance skipped: 'numpy.ndarray' object has no attribute 'values')

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.919 | 0.903 |
| spatial (GroupKFold on site) | 0.908 | 0.891 |
