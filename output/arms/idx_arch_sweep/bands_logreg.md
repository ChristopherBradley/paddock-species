# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 391 features, 3 classes
- model: logistic regression, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.802, balanced accuracy 0.817** (chance 0.333)

- **canola detected at 5 % FPR: 74.2%** (n=155)
- **average precision 0.861** (baseline = prevalence 0.285), ROC AUC 0.945

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.82 | 0.79 | 0.81 | 155 |
| Cereal | 0.94 | 0.86 | 0.90 | 279 |
| Legume | 0.62 | 0.81 | 0.70 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |122|6|27|
| **Cereal** |13|239|27|
| **Legume** |13|8|88|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.815, balanced accuracy 0.827** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.83 | 0.78 | 0.80 | 155 |
| Cereal | 0.95 | 0.89 | 0.92 | 279 |
| Legume | 0.65 | 0.82 | 0.72 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |121|6|28|
| **Cereal** |12|247|20|
| **Legume** |13|7|89|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.802 | 0.817 |
| spatial (GroupKFold on site) | 0.815 | 0.827 |
