# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 153 features, 3 classes
- model: extra-trees, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.852, balanced accuracy 0.852** (chance 0.333)

- **canola detected at 5 % FPR: 84.5%** (n=155)
- **average precision 0.924** (baseline = prevalence 0.285), ROC AUC 0.956

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.91 | 0.82 | 0.86 | 155 |
| Cereal | 0.93 | 0.95 | 0.94 | 279 |
| Legume | 0.73 | 0.79 | 0.76 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |127|5|23|
| **Cereal** |6|264|9|
| **Legume** |7|16|86|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.850, balanced accuracy 0.848** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.83 | 0.86 | 155 |
| Cereal | 0.92 | 0.95 | 0.93 | 279 |
| Legume | 0.74 | 0.77 | 0.76 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |128|7|20|
| **Cereal** |6|264|9|
| **Legume** |8|17|84|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.852 | 0.852 |
| spatial (GroupKFold on site) | 0.850 | 0.848 |
