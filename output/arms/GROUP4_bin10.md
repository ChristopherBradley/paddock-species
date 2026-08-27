# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2935 paddocks, 90 features, 4 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Grazing 741, Legume 490
- **fixed test set**: scoring restricted to 892 of 2935 rows listed in `testkeep_group4_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 2043, test 892
- **macro F1 0.836, balanced accuracy 0.840** (chance 0.250)

- **canola detected at 5 % FPR: 90.3%** (n=155)
- **average precision 0.903** (baseline = prevalence 0.174), ROC AUC 0.958

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.85 | 0.86 | 0.85 | 155 |
| Cereal | 0.85 | 0.90 | 0.88 | 279 |
| Grazing | 0.98 | 0.91 | 0.95 | 349 |
| Legume | 0.66 | 0.69 | 0.67 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |133|5|2|15|
| **Cereal** |4|252|4|19|
| **Grazing** |14|12|318|5|
| **Legume** |6|28|0|75|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.867, balanced accuracy 0.866** (scored on 892 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.88 | 0.86 | 0.87 | 155 |
| Cereal | 0.89 | 0.91 | 0.90 | 279 |
| Grazing | 0.97 | 0.97 | 0.97 | 349 |
| Legume | 0.72 | 0.72 | 0.72 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |134|8|2|11|
| **Cereal** |4|253|7|15|
| **Grazing** |6|1|338|4|
| **Legume** |8|22|0|79|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.836 | 0.840 |
| spatial (GroupKFold on site) | 0.867 | 0.866 |
