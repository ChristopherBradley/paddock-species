# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 231 features, 3 classes
- model: extra-trees, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.819, balanced accuracy 0.819** (chance 0.333)

- **canola detected at 5 % FPR: 84.5%** (n=155)
- **average precision 0.922** (baseline = prevalence 0.285), ROC AUC 0.957

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.93 | 0.81 | 0.86 | 155 |
| Cereal | 0.90 | 0.92 | 0.91 | 279 |
| Legume | 0.65 | 0.73 | 0.69 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |125|5|25|
| **Cereal** |4|256|19|
| **Legume** |6|23|80|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.832, balanced accuracy 0.828** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.84 | 0.88 | 155 |
| Cereal | 0.89 | 0.92 | 0.90 | 279 |
| Legume | 0.71 | 0.72 | 0.71 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |130|10|15|
| **Cereal** |4|257|18|
| **Legume** |8|22|79|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.819 | 0.819 |
| spatial (GroupKFold on site) | 0.832 | 0.828 |
