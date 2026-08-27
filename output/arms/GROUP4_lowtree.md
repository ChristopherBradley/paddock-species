# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2545 paddocks, 51 features, 4 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Grazing 351, Legume 490
- **fixed test set**: scoring restricted to 701 of 2545 rows listed in `testkeep_group4_lowtree_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1844, test 701
- **macro F1 0.839, balanced accuracy 0.836** (chance 0.250)

- **canola detected at 5 % FPR: 85.8%** (n=155)
- **average precision 0.926** (baseline = prevalence 0.221), ROC AUC 0.963

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.82 | 0.86 | 155 |
| Cereal | 0.87 | 0.91 | 0.89 | 279 |
| Grazing | 0.99 | 0.88 | 0.93 | 158 |
| Legume | 0.63 | 0.73 | 0.68 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |127|8|0|20|
| **Cereal** |2|254|2|21|
| **Grazing** |3|11|139|5|
| **Legume** |9|20|0|80|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.848, balanced accuracy 0.844** (scored on 701 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.88 | 0.83 | 0.85 | 155 |
| Cereal | 0.89 | 0.93 | 0.91 | 279 |
| Grazing | 0.98 | 0.95 | 0.96 | 158 |
| Legume | 0.66 | 0.67 | 0.66 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |128|5|0|22|
| **Cereal** |4|260|2|13|
| **Grazing** |1|4|150|3|
| **Legume** |13|22|1|73|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.839 | 0.836 |
| spatial (GroupKFold on site) | 0.848 | 0.844 |
