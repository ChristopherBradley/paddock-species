# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2361 paddocks, 51 features, 2 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 646, Other 1715
- **fixed test set**: scoring restricted to 543 of 2361 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1818, test 543
- **macro F1 0.915, balanced accuracy 0.895** (chance 0.500)

- **canola detected at 5 % FPR: 87.1%** (n=155)
- **average precision 0.911** (baseline = prevalence 0.285), ROC AUC 0.935

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.95 | 0.81 | 0.87 | 155 |
| Other | 0.93 | 0.98 | 0.95 | 388 |

Confusion (row = truth, col = predicted):

| |Canola|Other|
|---|---|---|
| **Canola** |125|30|
| **Other** |6|382|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.916, balanced accuracy 0.893** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.98 | 0.79 | 0.88 | 155 |
| Other | 0.92 | 0.99 | 0.96 | 388 |

Confusion (row = truth, col = predicted):

| |Canola|Other|
|---|---|---|
| **Canola** |123|32|
| **Other** |3|385|

(importance skipped: 'numpy.ndarray' object has no attribute 'values')

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.915 | 0.895 |
| spatial (GroupKFold on site) | 0.916 | 0.893 |
