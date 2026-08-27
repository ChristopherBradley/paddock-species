# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2194 paddocks, 51 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 600, Cereal 1113, Legume 481
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.798, balanced accuracy 0.796** (chance 0.333)

- **canola detected at 5 % FPR: 84.5%** (n=155)
- **average precision 0.924** (baseline = prevalence 0.285), ROC AUC 0.948

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.88 | 0.79 | 0.84 | 155 |
| Cereal | 0.87 | 0.90 | 0.88 | 279 |
| Legume | 0.65 | 0.70 | 0.67 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |123|15|17|
| **Cereal** |5|250|24|
| **Legume** |11|22|76|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.836, balanced accuracy 0.831** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.93 | 0.83 | 0.88 | 155 |
| Cereal | 0.89 | 0.93 | 0.91 | 279 |
| Legume | 0.71 | 0.73 | 0.72 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |128|10|17|
| **Cereal** |3|260|16|
| **Legume** |6|23|80|

(importance skipped: 'numpy.ndarray' object has no attribute 'values')

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.798 | 0.796 |
| spatial (GroupKFold on site) | 0.836 | 0.831 |
