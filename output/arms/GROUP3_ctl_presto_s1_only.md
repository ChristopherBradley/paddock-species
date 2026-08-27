# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2133 paddocks, 128 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 571, Cereal 1089, Legume 473
- **fixed test set**: scoring restricted to 497 of 2133 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1636, test 497
- **macro F1 0.813, balanced accuracy 0.813** (chance 0.333)

- **canola detected at 5 % FPR: 81.2%** (n=144)
- **average precision 0.893** (baseline = prevalence 0.290), ROC AUC 0.959

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.78 | 0.84 | 144 |
| Cereal | 0.88 | 0.90 | 0.89 | 253 |
| Legume | 0.66 | 0.76 | 0.71 | 100 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |112|13|19|
| **Cereal** |5|228|20|
| **Legume** |5|19|76|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.808, balanced accuracy 0.802** (scored on 497 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.93 | 0.79 | 0.85 | 144 |
| Cereal | 0.86 | 0.91 | 0.88 | 253 |
| Legume | 0.67 | 0.70 | 0.69 | 100 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |114|16|14|
| **Cereal** |2|231|20|
| **Legume** |7|23|70|

(importance skipped: 'numpy.ndarray' object has no attribute 'values')

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.813 | 0.813 |
| spatial (GroupKFold on site) | 0.808 | 0.802 |
