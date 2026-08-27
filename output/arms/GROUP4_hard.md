# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2596 paddocks, 51 features, 4 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Grazing 402, Legume 490
- **fixed test set**: scoring restricted to 754 of 2596 rows listed in `testkeep_group4_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1842, test 754
- **macro F1 0.823, balanced accuracy 0.829** (chance 0.250)

- **canola detected at 5 % FPR: 89.0%** (n=155)
- **average precision 0.914** (baseline = prevalence 0.206), ROC AUC 0.964

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.89 | 0.85 | 0.87 | 155 |
| Cereal | 0.84 | 0.89 | 0.87 | 279 |
| Grazing | 0.98 | 0.79 | 0.87 | 211 |
| Legume | 0.61 | 0.79 | 0.69 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |132|5|0|18|
| **Cereal** |2|248|4|25|
| **Grazing** |8|24|166|13|
| **Legume** |6|17|0|86|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.850, balanced accuracy 0.849** (scored on 754 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.89 | 0.86 | 0.87 | 155 |
| Cereal | 0.88 | 0.92 | 0.90 | 279 |
| Grazing | 0.97 | 0.91 | 0.94 | 211 |
| Legume | 0.67 | 0.72 | 0.69 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |133|5|0|17|
| **Cereal** |4|256|4|15|
| **Grazing** |3|10|191|7|
| **Legume** |10|20|1|78|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.823 | 0.829 |
| spatial (GroupKFold on site) | 0.850 | 0.849 |
