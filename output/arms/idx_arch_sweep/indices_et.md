# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2194 paddocks, 51 features, 3 classes
- model: extra-trees, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.823, balanced accuracy 0.823** (chance 0.333)

- **canola detected at 5 % FPR: 84.5%** (n=155)
- **average precision 0.922** (baseline = prevalence 0.285), ROC AUC 0.948

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.91 | 0.82 | 0.86 | 155 |
| Cereal | 0.89 | 0.91 | 0.90 | 279 |
| Legume | 0.68 | 0.74 | 0.71 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |127|10|18|
| **Cereal** |5|253|21|
| **Legume** |7|21|81|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.819, balanced accuracy 0.818** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.91 | 0.82 | 0.86 | 155 |
| Cereal | 0.89 | 0.91 | 0.90 | 279 |
| Legume | 0.66 | 0.72 | 0.69 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |127|7|21|
| **Cereal** |6|254|19|
| **Legume** |7|23|79|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.823 | 0.823 |
| spatial (GroupKFold on site) | 0.819 | 0.818 |
