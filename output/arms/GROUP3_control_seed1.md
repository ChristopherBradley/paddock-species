# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2194 paddocks, 51 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 601, Cereal 1124, Legume 469
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.795, balanced accuracy 0.795** (chance 0.333)

- **canola detected at 5 % FPR: 85.8%** (n=155)
- **average precision 0.926** (baseline = prevalence 0.285), ROC AUC 0.947

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.81 | 0.85 | 155 |
| Cereal | 0.87 | 0.87 | 0.87 | 279 |
| Legume | 0.62 | 0.70 | 0.66 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |126|11|18|
| **Cereal** |7|244|28|
| **Legume** |7|26|76|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.839, balanced accuracy 0.831** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.86 | 0.89 | 155 |
| Cereal | 0.89 | 0.94 | 0.91 | 279 |
| Legume | 0.74 | 0.70 | 0.72 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |133|8|14|
| **Cereal** |4|262|13|
| **Legume** |7|26|76|

(importance skipped: 'numpy.ndarray' object has no attribute 'values')

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.795 | 0.795 |
| spatial (GroupKFold on site) | 0.839 | 0.831 |
