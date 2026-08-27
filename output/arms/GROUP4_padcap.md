# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2427 paddocks, 51 features, 4 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Grazing 233, Legume 490
- **fixed test set**: scoring restricted to 665 of 2427 rows listed in `testkeep_group4_padcap_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1762, test 665
- **macro F1 0.827, balanced accuracy 0.823** (chance 0.250)

- **canola detected at 5 % FPR: 85.8%** (n=155)
- **average precision 0.924** (baseline = prevalence 0.233), ROC AUC 0.963

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.89 | 0.85 | 0.87 | 155 |
| Cereal | 0.88 | 0.89 | 0.88 | 279 |
| Grazing | 0.97 | 0.83 | 0.89 | 122 |
| Legume | 0.61 | 0.72 | 0.66 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |131|5|0|19|
| **Cereal** |3|249|3|24|
| **Grazing** |4|9|101|8|
| **Legume** |9|21|0|79|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.827, balanced accuracy 0.825** (scored on 665 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.84 | 0.88 | 0.86 | 155 |
| Cereal | 0.89 | 0.89 | 0.89 | 279 |
| Grazing | 0.93 | 0.86 | 0.89 | 122 |
| Legume | 0.66 | 0.67 | 0.67 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |136|5|2|12|
| **Cereal** |6|249|6|18|
| **Grazing** |4|6|105|7|
| **Legume** |16|20|0|73|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.827 | 0.823 |
| spatial (GroupKFold on site) | 0.827 | 0.825 |
