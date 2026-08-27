# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2194 paddocks, 51 features, 2 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Other 1609
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.928, balanced accuracy 0.914** (chance 0.500)

- **canola detected at 5 % FPR: 89.0%** (n=155)
- **average precision 0.947** (baseline = prevalence 0.285), ROC AUC 0.968

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.95 | 0.85 | 0.89 | 155 |
| Other | 0.94 | 0.98 | 0.96 | 388 |

Confusion (row = truth, col = predicted):

| |Canola|Other|
|---|---|---|
| **Canola** |131|24|
| **Other** |7|381|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.910, balanced accuracy 0.901** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.84 | 0.87 | 155 |
| Other | 0.94 | 0.96 | 0.95 | 388 |

Confusion (row = truth, col = predicted):

| |Canola|Other|
|---|---|---|
| **Canola** |130|25|
| **Other** |14|374|

(importance skipped: 'numpy.ndarray' object has no attribute 'values')

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.928 | 0.914 |
| spatial (GroupKFold on site) | 0.910 | 0.901 |
