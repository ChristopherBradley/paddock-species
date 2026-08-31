# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 391 features, 3 classes
- model: extra-trees, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.839, balanced accuracy 0.840** (chance 0.333)

- **canola detected at 5 % FPR: 84.5%** (n=155)
- **average precision 0.919** (baseline = prevalence 0.285), ROC AUC 0.952

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.93 | 0.84 | 0.88 | 155 |
| Cereal | 0.91 | 0.92 | 0.92 | 279 |
| Legume | 0.68 | 0.76 | 0.72 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |130|5|20|
| **Cereal** |3|257|19|
| **Legume** |7|19|83|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.830, balanced accuracy 0.833** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.82 | 0.87 | 155 |
| Cereal | 0.92 | 0.91 | 0.91 | 279 |
| Legume | 0.66 | 0.77 | 0.71 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |127|5|23|
| **Cereal** |4|254|21|
| **Legume** |7|18|84|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.839 | 0.840 |
| spatial (GroupKFold on site) | 0.830 | 0.833 |
