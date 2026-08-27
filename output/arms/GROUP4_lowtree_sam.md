# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2391 paddocks, 51 features, 4 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Grazing 197, Legume 490
- **fixed test set**: scoring restricted to 640 of 2391 rows listed in `testkeep_group4_lowtree_sam_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1751, test 640
- **macro F1 0.830, balanced accuracy 0.825** (chance 0.250)

- **canola detected at 5 % FPR: 87.1%** (n=155)
- **average precision 0.927** (baseline = prevalence 0.242), ROC AUC 0.963

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.83 | 0.87 | 155 |
| Cereal | 0.88 | 0.90 | 0.89 | 279 |
| Grazing | 0.94 | 0.84 | 0.89 | 97 |
| Legume | 0.62 | 0.73 | 0.67 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |128|5|2|20|
| **Cereal** |3|252|3|21|
| **Grazing** |3|5|81|8|
| **Legume** |5|24|0|80|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.832, balanced accuracy 0.823** (scored on 640 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.88 | 0.86 | 0.87 | 155 |
| Cereal | 0.87 | 0.92 | 0.90 | 279 |
| Grazing | 0.95 | 0.85 | 0.90 | 97 |
| Legume | 0.66 | 0.67 | 0.67 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |133|5|0|17|
| **Cereal** |3|256|4|16|
| **Grazing** |4|7|82|4|
| **Legume** |11|25|0|73|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.830 | 0.825 |
| spatial (GroupKFold on site) | 0.832 | 0.823 |
