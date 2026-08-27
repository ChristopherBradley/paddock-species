# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2194 paddocks, 51 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 600, Cereal 1126, Legume 468
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.814, balanced accuracy 0.812** (chance 0.333)

- **canola detected at 5 % FPR: 81.3%** (n=155)
- **average precision 0.921** (baseline = prevalence 0.285), ROC AUC 0.946

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.93 | 0.81 | 0.87 | 155 |
| Cereal | 0.86 | 0.89 | 0.88 | 279 |
| Legume | 0.67 | 0.73 | 0.70 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |126|15|14|
| **Cereal** |5|248|26|
| **Legume** |5|24|80|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.826, balanced accuracy 0.821** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.86 | 0.88 | 155 |
| Cereal | 0.88 | 0.92 | 0.90 | 279 |
| Legume | 0.71 | 0.68 | 0.69 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |133|8|14|
| **Cereal** |5|258|16|
| **Legume** |9|26|74|

(importance skipped: 'numpy.ndarray' object has no attribute 'values')

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.814 | 0.812 |
| spatial (GroupKFold on site) | 0.826 | 0.821 |
