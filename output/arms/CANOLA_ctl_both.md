# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2133 paddocks, 102 features, 2 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 571, Other 1562
- **fixed test set**: scoring restricted to 497 of 2133 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1636, test 497
- **macro F1 0.932, balanced accuracy 0.917** (chance 0.500)

- **canola detected at 5 % FPR: 84.7%** (n=144)
- **average precision 0.935** (baseline = prevalence 0.290), ROC AUC 0.965

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.96 | 0.85 | 0.90 | 144 |
| Other | 0.94 | 0.99 | 0.96 | 353 |

Confusion (row = truth, col = predicted):

| |Canola|Other|
|---|---|---|
| **Canola** |122|22|
| **Other** |5|348|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.930, balanced accuracy 0.921** (scored on 497 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.93 | 0.87 | 0.90 | 144 |
| Other | 0.95 | 0.97 | 0.96 | 353 |

Confusion (row = truth, col = predicted):

| |Canola|Other|
|---|---|---|
| **Canola** |125|19|
| **Other** |9|344|

(importance skipped: 'numpy.ndarray' object has no attribute 'values')

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.932 | 0.917 |
| spatial (GroupKFold on site) | 0.930 | 0.921 |
