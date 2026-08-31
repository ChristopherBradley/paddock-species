# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 231 features, 3 classes
- model: logistic regression, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.798, balanced accuracy 0.811** (chance 0.333)

- **canola detected at 5 % FPR: 77.4%** (n=155)
- **average precision 0.888** (baseline = prevalence 0.285), ROC AUC 0.956

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.82 | 0.83 | 0.82 | 155 |
| Cereal | 0.92 | 0.84 | 0.88 | 279 |
| Legume | 0.63 | 0.76 | 0.69 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |129|8|18|
| **Cereal** |14|234|31|
| **Legume** |15|11|83|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.811, balanced accuracy 0.820** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.85 | 0.82 | 0.83 | 155 |
| Cereal | 0.92 | 0.87 | 0.90 | 279 |
| Legume | 0.65 | 0.77 | 0.71 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |127|6|22|
| **Cereal** |13|243|23|
| **Legume** |10|15|84|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.798 | 0.811 |
| spatial (GroupKFold on site) | 0.811 | 0.820 |
