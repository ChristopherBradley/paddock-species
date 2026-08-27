# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2935 paddocks, 51 features, 2 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Crop 2194, Grazing 741
- **fixed test set**: scoring restricted to 892 of 2935 rows listed in `testkeep_group4_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 2043, test 892
- **macro F1 0.921, balanced accuracy 0.909** (chance 0.500)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Crop | 0.90 | 0.99 | 0.94 | 543 |
| Grazing | 0.98 | 0.83 | 0.90 | 349 |

Confusion (row = truth, col = predicted):

| |Crop|Grazin|
|---|---|---|
| **Crop** |538|5|
| **Grazing** |60|289|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.973, balanced accuracy 0.971** (scored on 892 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Crop | 0.97 | 0.99 | 0.98 | 543 |
| Grazing | 0.98 | 0.95 | 0.97 | 349 |

Confusion (row = truth, col = predicted):

| |Crop|Grazin|
|---|---|---|
| **Crop** |536|7|
| **Grazing** |16|333|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.921 | 0.909 |
| spatial (GroupKFold on site) | 0.973 | 0.971 |
