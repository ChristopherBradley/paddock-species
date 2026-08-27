# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2688 paddocks, 51 features, 4 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Grazing 494, Legume 490
- **fixed test set**: scoring restricted to 778 of 2688 rows listed in `testkeep_group4_sam_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1910, test 778
- **macro F1 0.836, balanced accuracy 0.836** (chance 0.250)

- **canola detected at 5 % FPR: 90.3%** (n=155)
- **average precision 0.918** (baseline = prevalence 0.199), ROC AUC 0.967

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.91 | 0.81 | 0.86 | 155 |
| Cereal | 0.85 | 0.91 | 0.88 | 279 |
| Grazing | 0.98 | 0.87 | 0.92 | 235 |
| Legume | 0.63 | 0.75 | 0.69 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |125|8|2|20|
| **Cereal** |2|255|3|19|
| **Grazing** |4|17|205|9|
| **Legume** |6|21|0|82|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.841, balanced accuracy 0.841** (scored on 778 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.86 | 0.86 | 0.86 | 155 |
| Cereal | 0.90 | 0.90 | 0.90 | 279 |
| Grazing | 0.97 | 0.96 | 0.97 | 235 |
| Legume | 0.63 | 0.64 | 0.64 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |133|5|0|17|
| **Cereal** |3|252|4|20|
| **Grazing** |3|2|226|4|
| **Legume** |16|21|2|70|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.836 | 0.836 |
| spatial (GroupKFold on site) | 0.841 | 0.841 |
