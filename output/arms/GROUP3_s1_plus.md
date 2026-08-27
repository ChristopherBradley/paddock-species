# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2194 paddocks, 102 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.828, balanced accuracy 0.838** (chance 0.333)

- **canola detected at 5 % FPR: 81.9%** (n=155)
- **average precision 0.927** (baseline = prevalence 0.285), ROC AUC 0.959

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.94 | 0.80 | 0.86 | 155 |
| Cereal | 0.93 | 0.89 | 0.91 | 279 |
| Legume | 0.62 | 0.83 | 0.71 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |124|3|28|
| **Cereal** |4|248|27|
| **Legume** |4|15|90|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.842, balanced accuracy 0.837** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.93 | 0.88 | 0.90 | 155 |
| Cereal | 0.89 | 0.93 | 0.91 | 279 |
| Legume | 0.73 | 0.71 | 0.72 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |136|6|13|
| **Cereal** |4|259|16|
| **Legume** |7|25|77|

(importance skipped: 'numpy.ndarray' object has no attribute 'values')

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.828 | 0.838 |
| spatial (GroupKFold on site) | 0.842 | 0.837 |
