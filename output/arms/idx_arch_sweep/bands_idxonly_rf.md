# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 231 features, 3 classes
- model: random forest, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.838, balanced accuracy 0.833** (chance 0.333)

- **canola detected at 5 % FPR: 84.5%** (n=155)
- **average precision 0.920** (baseline = prevalence 0.285), ROC AUC 0.958

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.84 | 0.88 | 155 |
| Cereal | 0.90 | 0.94 | 0.92 | 279 |
| Legume | 0.72 | 0.72 | 0.72 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |130|8|17|
| **Cereal** |4|261|14|
| **Legume** |8|22|79|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.826, balanced accuracy 0.822** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.86 | 0.88 | 155 |
| Cereal | 0.89 | 0.91 | 0.90 | 279 |
| Legume | 0.70 | 0.69 | 0.69 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |134|7|14|
| **Cereal** |6|255|18|
| **Legume** |9|25|75|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.838 | 0.833 |
| spatial (GroupKFold on site) | 0.826 | 0.822 |
