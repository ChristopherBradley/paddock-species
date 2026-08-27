# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2194 paddocks, 51 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.821, balanced accuracy 0.821** (chance 0.333)

- **canola detected at 5 % FPR: 89.0%** (n=155)
- **average precision 0.944** (baseline = prevalence 0.285), ROC AUC 0.965

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.94 | 0.83 | 0.88 | 155 |
| Cereal | 0.89 | 0.90 | 0.90 | 279 |
| Legume | 0.65 | 0.73 | 0.69 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |128|8|19|
| **Cereal** |2|252|25|
| **Legume** |6|23|80|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.823, balanced accuracy 0.821** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.91 | 0.86 | 0.88 | 155 |
| Cereal | 0.89 | 0.91 | 0.90 | 279 |
| Legume | 0.68 | 0.70 | 0.69 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |133|8|14|
| **Cereal** |4|253|22|
| **Legume** |9|24|76|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.821 | 0.821 |
| spatial (GroupKFold on site) | 0.823 | 0.821 |
