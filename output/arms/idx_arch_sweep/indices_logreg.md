# Species classifier baseline — paddock-median Sentinel-2

- input: **3 indices** (3 columns), 2194 paddocks, 51 features, 3 classes
- model: logistic regression, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.745, balanced accuracy 0.764** (chance 0.333)

- **canola detected at 5 % FPR: 75.5%** (n=155)
- **average precision 0.898** (baseline = prevalence 0.285), ROC AUC 0.946

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.85 | 0.75 | 0.80 | 155 |
| Cereal | 0.90 | 0.77 | 0.83 | 279 |
| Legume | 0.50 | 0.77 | 0.61 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |117|5|33|
| **Cereal** |14|214|51|
| **Legume** |7|18|84|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.768, balanced accuracy 0.779** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.85 | 0.83 | 0.84 | 155 |
| Cereal | 0.90 | 0.81 | 0.85 | 279 |
| Legume | 0.55 | 0.70 | 0.61 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |128|5|22|
| **Cereal** |11|227|41|
| **Legume** |12|21|76|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.745 | 0.764 |
| spatial (GroupKFold on site) | 0.768 | 0.779 |
