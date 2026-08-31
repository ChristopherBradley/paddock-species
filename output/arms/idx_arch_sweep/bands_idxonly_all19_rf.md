# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 333 features, 3 classes
- model: random forest, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.855, balanced accuracy 0.855** (chance 0.333)

- **canola detected at 5 % FPR: 84.5%** (n=155)
- **average precision 0.930** (baseline = prevalence 0.285), ROC AUC 0.967

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.85 | 0.87 | 155 |
| Cereal | 0.93 | 0.94 | 0.93 | 279 |
| Legume | 0.74 | 0.78 | 0.76 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |131|5|19|
| **Cereal** |6|262|11|
| **Legume** |8|16|85|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.851, balanced accuracy 0.847** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.91 | 0.86 | 0.88 | 155 |
| Cereal | 0.91 | 0.94 | 0.93 | 279 |
| Legume | 0.75 | 0.73 | 0.74 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |134|5|16|
| **Cereal** |5|263|11|
| **Legume** |9|20|80|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.855 | 0.855 |
| spatial (GroupKFold on site) | 0.851 | 0.847 |
