# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2757 paddocks, 90 features, 4 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Grazing 563, Legume 490
- **fixed test set**: scoring restricted to 812 of 2757 rows listed in `testkeep_group4_sam_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1945, test 812
- **macro F1 0.842, balanced accuracy 0.842** (chance 0.250)

- **canola detected at 5 % FPR: 91.0%** (n=155)
- **average precision 0.911** (baseline = prevalence 0.191), ROC AUC 0.960

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.85 | 0.87 | 155 |
| Cereal | 0.87 | 0.91 | 0.89 | 279 |
| Grazing | 0.98 | 0.93 | 0.95 | 269 |
| Legume | 0.63 | 0.68 | 0.65 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |132|5|2|16|
| **Cereal** |2|253|3|21|
| **Grazing** |8|4|250|7|
| **Legume** |5|30|0|74|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.848, balanced accuracy 0.847** (scored on 812 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.89 | 0.81 | 0.84 | 155 |
| Cereal | 0.89 | 0.91 | 0.90 | 279 |
| Grazing | 0.98 | 0.97 | 0.98 | 269 |
| Legume | 0.64 | 0.70 | 0.67 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Grazin|Legume|
|---|---|---|---|---|
| **Canola** |125|7|2|21|
| **Cereal** |4|255|2|18|
| **Grazing** |5|0|261|3|
| **Legume** |7|25|1|76|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.842 | 0.842 |
| spatial (GroupKFold on site) | 0.848 | 0.847 |
