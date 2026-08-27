# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2757 paddocks, 51 features, 4 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Grazing 563, Legume 490
- **fixed test set**: scoring restricted to 640 of 2757 rows listed in `testkeep_group4_lowtree_sam_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1945, test 640
- **macro F1 0.844, balanced accuracy 0.839** (chance 0.250)

- **canola detected at 5 % FPR: 87.1%** (n=155)
- **average precision 0.928** (baseline = prevalence 0.242), ROC AUC 0.963

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.84 | 0.88 | 155 |
| Cereal | 0.88 | 0.90 | 0.89 | 279 |
| Grazing | 0.97 | 0.86 | 0.91 | 97 |
| Legume | 0.65 | 0.76 | 0.70 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |130|8|0|17|
| **Cereal** |3|251|3|22|
| **Grazing** |4|4|83|6|
| **Legume** |4|22|0|83|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.825, balanced accuracy 0.818** (scored on 640 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.84 | 0.84 | 0.84 | 155 |
| Cereal | 0.88 | 0.92 | 0.90 | 279 |
| Grazing | 0.93 | 0.89 | 0.91 | 97 |
| Legume | 0.67 | 0.62 | 0.64 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |130|5|2|18|
| **Cereal** |4|258|3|14|
| **Grazing** |6|3|86|2|
| **Legume** |14|26|1|68|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.844 | 0.839 |
| spatial (GroupKFold on site) | 0.825 | 0.818 |
