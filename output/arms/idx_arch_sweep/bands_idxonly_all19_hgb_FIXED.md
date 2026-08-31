# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 351 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.887, balanced accuracy 0.890** (chance 0.333)

- **canola detected at 5 % FPR: 85.8%** (n=155)
- **average precision 0.938** (baseline = prevalence 0.285), ROC AUC 0.967

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.91 | 0.85 | 0.88 | 155 |
| Cereal | 0.96 | 0.96 | 0.96 | 279 |
| Legume | 0.78 | 0.86 | 0.82 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |132|4|19|
| **Cereal** |5|267|7|
| **Legume** |8|7|94|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.872, balanced accuracy 0.873** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.86 | 0.89 | 155 |
| Cereal | 0.94 | 0.95 | 0.95 | 279 |
| Legume | 0.76 | 0.81 | 0.78 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |133|3|19|
| **Cereal** |4|266|9|
| **Legume** |8|13|88|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.887 | 0.890 |
| spatial (GroupKFold on site) | 0.872 | 0.873 |
