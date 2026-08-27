# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2495 paddocks, 51 features, 4 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Grazing 301, Legume 490
- **fixed test set**: scoring restricted to 705 of 2495 rows listed in `testkeep_group4_sam_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1790, test 705
- **macro F1 0.821, balanced accuracy 0.817** (chance 0.250)

- **canola detected at 5 % FPR: 85.8%** (n=155)
- **average precision 0.915** (baseline = prevalence 0.220), ROC AUC 0.962

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.91 | 0.84 | 0.87 | 155 |
| Cereal | 0.84 | 0.89 | 0.86 | 279 |
| Grazing | 0.98 | 0.80 | 0.88 | 162 |
| Legume | 0.60 | 0.73 | 0.66 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |130|5|0|20|
| **Cereal** |5|249|2|23|
| **Grazing** |3|19|130|10|
| **Legume** |5|24|0|80|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.839, balanced accuracy 0.836** (scored on 705 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.88 | 0.88 | 0.88 | 155 |
| Cereal | 0.89 | 0.91 | 0.90 | 279 |
| Grazing | 0.97 | 0.90 | 0.94 | 162 |
| Legume | 0.63 | 0.65 | 0.64 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |136|5|0|14|
| **Cereal** |3|255|3|18|
| **Grazing** |2|4|146|10|
| **Legume** |14|23|1|71|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.821 | 0.817 |
| spatial (GroupKFold on site) | 0.839 | 0.836 |
