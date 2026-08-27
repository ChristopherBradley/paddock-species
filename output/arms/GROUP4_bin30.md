# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2935 paddocks, 39 features, 4 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Grazing 741, Legume 490
- **fixed test set**: scoring restricted to 892 of 2935 rows listed in `testkeep_group4_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 2043, test 892
- **macro F1 0.816, balanced accuracy 0.831** (chance 0.250)

- **canola detected at 5 % FPR: 81.3%** (n=155)
- **average precision 0.892** (baseline = prevalence 0.174), ROC AUC 0.954

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.85 | 0.81 | 0.83 | 155 |
| Cereal | 0.84 | 0.87 | 0.86 | 279 |
| Grazing | 0.99 | 0.87 | 0.92 | 349 |
| Legume | 0.57 | 0.77 | 0.65 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |126|6|0|23|
| **Cereal** |7|244|4|24|
| **Grazing** |5|25|302|17|
| **Legume** |10|15|0|84|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.851, balanced accuracy 0.850** (scored on 892 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.85 | 0.79 | 0.82 | 155 |
| Cereal | 0.88 | 0.92 | 0.90 | 279 |
| Grazing | 0.98 | 0.97 | 0.97 | 349 |
| Legume | 0.70 | 0.72 | 0.71 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |123|10|2|20|
| **Cereal** |7|256|6|10|
| **Grazing** |3|4|339|3|
| **Legume** |11|20|0|78|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.816 | 0.831 |
| spatial (GroupKFold on site) | 0.851 | 0.850 |
