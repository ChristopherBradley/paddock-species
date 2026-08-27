# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2361 paddocks, 51 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 646, Cereal 1209, Legume 506
- **fixed test set**: scoring restricted to 543 of 2361 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1818, test 543
- **macro F1 0.789, balanced accuracy 0.789** (chance 0.333)

- **canola detected at 5 % FPR: 83.2%** (n=155)
- **average precision 0.920** (baseline = prevalence 0.285), ROC AUC 0.943

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.88 | 0.79 | 0.84 | 155 |
| Cereal | 0.87 | 0.89 | 0.88 | 279 |
| Legume | 0.62 | 0.69 | 0.65 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |123|13|19|
| **Cereal** |5|247|27|
| **Legume** |11|23|75|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.832, balanced accuracy 0.826** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.93 | 0.84 | 0.88 | 155 |
| Cereal | 0.88 | 0.93 | 0.91 | 279 |
| Legume | 0.71 | 0.71 | 0.71 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |130|8|17|
| **Cereal** |4|260|15|
| **Legume** |6|26|77|

(importance skipped: 'numpy.ndarray' object has no attribute 'values')

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.789 | 0.789 |
| spatial (GroupKFold on site) | 0.832 | 0.826 |
