# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2757 paddocks, 39 features, 4 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Grazing 563, Legume 490
- **fixed test set**: scoring restricted to 812 of 2757 rows listed in `testkeep_group4_sam_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1945, test 812
- **macro F1 0.821, balanced accuracy 0.832** (chance 0.250)

- **canola detected at 5 % FPR: 81.3%** (n=155)
- **average precision 0.893** (baseline = prevalence 0.191), ROC AUC 0.950

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.83 | 0.79 | 0.81 | 155 |
| Cereal | 0.88 | 0.89 | 0.88 | 279 |
| Grazing | 0.99 | 0.86 | 0.92 | 269 |
| Legume | 0.59 | 0.78 | 0.67 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |123|6|0|26|
| **Cereal** |7|249|2|21|
| **Grazing** |11|13|232|13|
| **Legume** |8|16|0|85|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.833, balanced accuracy 0.834** (scored on 812 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.85 | 0.81 | 0.83 | 155 |
| Cereal | 0.88 | 0.90 | 0.89 | 279 |
| Grazing | 0.97 | 0.93 | 0.95 | 269 |
| Legume | 0.64 | 0.70 | 0.67 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |125|10|2|18|
| **Cereal** |6|252|6|15|
| **Grazing** |3|6|250|10|
| **Legume** |13|20|0|76|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.821 | 0.832 |
| spatial (GroupKFold on site) | 0.833 | 0.834 |
