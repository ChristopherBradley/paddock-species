# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 391 features, 3 classes
- model: random forest, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.837, balanced accuracy 0.836** (chance 0.333)

- **canola detected at 5 % FPR: 84.5%** (n=155)
- **average precision 0.930** (baseline = prevalence 0.285), ROC AUC 0.966

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.85 | 0.88 | 155 |
| Cereal | 0.90 | 0.92 | 0.91 | 279 |
| Legume | 0.70 | 0.74 | 0.72 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |131|8|16|
| **Cereal** |3|257|19|
| **Legume** |9|19|81|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.817, balanced accuracy 0.818** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.85 | 0.87 | 155 |
| Cereal | 0.90 | 0.90 | 0.90 | 279 |
| Legume | 0.65 | 0.71 | 0.68 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |131|5|19|
| **Cereal** |4|252|23|
| **Legume** |10|22|77|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.837 | 0.836 |
| spatial (GroupKFold on site) | 0.817 | 0.818 |
