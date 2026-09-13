# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 153 features, 3 classes
- model: random forest, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.857, balanced accuracy 0.855** (chance 0.333)

- **canola detected at 5 % FPR: 86.5%** (n=155)
- **average precision 0.923** (baseline = prevalence 0.285), ROC AUC 0.959

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.84 | 0.87 | 155 |
| Cereal | 0.92 | 0.95 | 0.93 | 279 |
| Legume | 0.76 | 0.78 | 0.77 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |130|6|19|
| **Cereal** |7|264|8|
| **Legume** |8|16|85|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.852, balanced accuracy 0.849** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.84 | 0.87 | 155 |
| Cereal | 0.91 | 0.95 | 0.93 | 279 |
| Legume | 0.75 | 0.76 | 0.76 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |130|7|18|
| **Cereal** |6|264|9|
| **Legume** |8|18|83|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.857 | 0.855 |
| spatial (GroupKFold on site) | 0.852 | 0.849 |
