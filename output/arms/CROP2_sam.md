# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2757 paddocks, 51 features, 2 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Crop 2194, Grazing 563
- **fixed test set**: scoring restricted to 812 of 2757 rows listed in `testkeep_group4_sam_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1945, test 812
- **macro F1 0.915, balanced accuracy 0.896** (chance 0.500)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Crop | 0.91 | 0.99 | 0.95 | 543 |
| Grazing | 0.98 | 0.80 | 0.88 | 269 |

Confusion (row = truth, col = predicted):

| |Crop|Grazin|
|---|---|---|
| **Crop** |539|4|
| **Grazing** |54|215|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.976, balanced accuracy 0.972** (scored on 812 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Crop | 0.98 | 0.99 | 0.98 | 543 |
| Grazing | 0.98 | 0.95 | 0.97 | 269 |

Confusion (row = truth, col = predicted):

| |Crop|Grazin|
|---|---|---|
| **Crop** |539|4|
| **Grazing** |13|256|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.915 | 0.896 |
| spatial (GroupKFold on site) | 0.976 | 0.972 |
