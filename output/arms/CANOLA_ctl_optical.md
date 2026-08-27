# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2133 paddocks, 51 features, 2 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 571, Other 1562
- **fixed test set**: scoring restricted to 497 of 2133 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1636, test 497
- **macro F1 0.924, balanced accuracy 0.912** (chance 0.500)

- **canola detected at 5 % FPR: 90.3%** (n=144)
- **average precision 0.949** (baseline = prevalence 0.290), ROC AUC 0.970

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.94 | 0.85 | 0.89 | 144 |
| Other | 0.94 | 0.98 | 0.96 | 353 |

Confusion (row = truth, col = predicted):

| |Canola|Other|
|---|---|---|
| **Canola** |122|22|
| **Other** |8|345|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.911, balanced accuracy 0.904** (scored on 497 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.85 | 0.87 | 144 |
| Other | 0.94 | 0.96 | 0.95 | 353 |

Confusion (row = truth, col = predicted):

| |Canola|Other|
|---|---|---|
| **Canola** |122|22|
| **Other** |14|339|

(importance skipped: 'numpy.ndarray' object has no attribute 'values')

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.924 | 0.912 |
| spatial (GroupKFold on site) | 0.911 | 0.904 |
