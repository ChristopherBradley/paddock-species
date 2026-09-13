# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 490 paddocks, 153 features, 5 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Chickpea 126, Faba Bean 80, Field Pea 120, Lentil 78, Lupin 86
- **fixed test set**: scoring restricted to 109 of 490 rows listed in `testkeep_temporal_legume_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 381, test 109
- **macro F1 0.355, balanced accuracy 0.386** (chance 0.200)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Chickpea | 0.58 | 0.28 | 0.38 | 25 |
| Faba Bean | 0.44 | 0.29 | 0.35 | 24 |
| Field Pea | 0.35 | 0.65 | 0.45 | 26 |
| Lentil | 0.40 | 0.11 | 0.17 | 19 |
| Lupin | 0.33 | 0.60 | 0.43 | 15 |

Confusion (row = truth, col = predicted):

| |Chickp|Faba B|Field |Lentil|Lupin|
|---|---|---|---|---|---|
| **Chickpea** |7|2|12|0|4|
| **Faba Bean** |1|7|8|2|6|
| **Field Pea** |2|2|17|1|4|
| **Lentil** |1|2|10|2|4|
| **Lupin** |1|3|2|0|9|

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.343, balanced accuracy 0.353** (scored on 109 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Chickpea | 0.35 | 0.24 | 0.29 | 25 |
| Faba Bean | 0.38 | 0.38 | 0.38 | 24 |
| Field Pea | 0.40 | 0.54 | 0.46 | 26 |
| Lentil | 0.44 | 0.21 | 0.29 | 19 |
| Lupin | 0.25 | 0.40 | 0.31 | 15 |

Confusion (row = truth, col = predicted):

| |Chickp|Faba B|Field |Lentil|Lupin|
|---|---|---|---|---|---|
| **Chickpea** |6|7|8|0|4|
| **Faba Bean** |4|9|4|3|4|
| **Field Pea** |2|2|14|2|6|
| **Lentil** |1|3|7|4|4|
| **Lupin** |4|3|2|0|6|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.355 | 0.386 |
| spatial (GroupKFold on site) | 0.343 | 0.353 |
