# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2194 paddocks, 51 features, 3 classes
- model: random forest, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.830, balanced accuracy 0.830** (chance 0.333)

- **canola detected at 5 % FPR: 85.2%** (n=155)
- **average precision 0.927** (baseline = prevalence 0.285), ROC AUC 0.955

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.84 | 0.87 | 155 |
| Cereal | 0.89 | 0.91 | 0.90 | 279 |
| Legume | 0.70 | 0.74 | 0.72 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |130|10|15|
| **Cereal** |7|253|19|
| **Legume** |8|20|81|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.820, balanced accuracy 0.814** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.89 | 0.82 | 0.85 | 155 |
| Cereal | 0.88 | 0.92 | 0.90 | 279 |
| Legume | 0.71 | 0.71 | 0.71 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |127|13|15|
| **Cereal** |7|256|16|
| **Legume** |9|23|77|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.830 | 0.830 |
| spatial (GroupKFold on site) | 0.820 | 0.814 |
