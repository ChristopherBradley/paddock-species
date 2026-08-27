# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2935 paddocks, 51 features, 4 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Grazing 741, Legume 490
- **fixed test set**: scoring restricted to 701 of 2935 rows listed in `testkeep_group4_lowtree_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 2043, test 701
- **macro F1 0.840, balanced accuracy 0.837** (chance 0.250)

- **canola detected at 5 % FPR: 89.0%** (n=155)
- **average precision 0.930** (baseline = prevalence 0.221), ROC AUC 0.964

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.91 | 0.83 | 0.86 | 155 |
| Cereal | 0.87 | 0.90 | 0.89 | 279 |
| Grazing | 0.95 | 0.91 | 0.93 | 158 |
| Legume | 0.64 | 0.72 | 0.68 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |128|8|2|17|
| **Cereal** |2|252|4|21|
| **Grazing** |2|8|143|5|
| **Legume** |9|21|1|78|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.864, balanced accuracy 0.862** (scored on 701 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.88 | 0.90 | 155 |
| Cereal | 0.89 | 0.91 | 0.90 | 279 |
| Grazing | 0.96 | 0.97 | 0.96 | 158 |
| Legume | 0.70 | 0.70 | 0.70 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |136|3|2|14|
| **Cereal** |4|253|4|18|
| **Grazing** |1|3|153|1|
| **Legume** |7|25|1|76|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.840 | 0.837 |
| spatial (GroupKFold on site) | 0.864 | 0.862 |
