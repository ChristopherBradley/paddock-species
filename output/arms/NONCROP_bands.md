# Species classifier baseline — paddock-median Sentinel-2

- input: **10 bands** (10 columns), 2194 paddocks, 274 features, 3 classes
- model: hist gradient boosting, class-balanced; geography excluded
- class counts: Canola 585, Cereal 1119, Legume 490
- **fixed test set**: scoring restricted to 543 of 2194 rows listed in `testkeep_temporal_SENSITIVE.csv`

### Temporal transfer — train <=2022, test 2023-24

- train 1651, test 543
- **macro F1 0.826, balanced accuracy 0.833** (chance 0.333)

- **canola detected at 5 % FPR: 85.8%** (n=155)
- **average precision 0.924** (baseline = prevalence 0.285), ROC AUC 0.966

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.78 | 0.84 | 155 |
| Cereal | 0.92 | 0.90 | 0.91 | 279 |
| Legume | 0.65 | 0.82 | 0.72 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |121|8|26|
| **Cereal** |5|252|22|
| **Legume** |6|14|89|

### Out-of-class behaviour — paddocks that are none of these classes

- 125 non-crop paddocks scored by the <=2022 model; **every one is forced into a crop class**

| predicted | n | share |
|---|---|---|
| Canola | 2 | 1.6% |
| Cereal | 116 | 92.8% |
| Legume | 7 | 5.6% |

By stratum (`hard` = pasture inside cropping country, `easy` = rangeland):

| stratum | n | mean max-prob |
|---|---|---|
| easy | 16 | 0.975 |
| hard | 109 | 0.950 |

**Confidence.** Pasture median max-prob 0.998 against 1.000 on real crop paddocks the model also never saw.

| max-prob threshold | pasture rejected | crop kept | crop correct of kept |
|---|---|---|---|
| 0.50 | 1.6% | 99.8% | 85.1% |
| 0.60 | 2.4% | 98.2% | 85.6% |
| 0.70 | 4.0% | 95.4% | 86.7% |
| 0.80 | 8.8% | 92.3% | 87.8% |
| 0.90 | 14.4% | 89.7% | 89.5% |
| 0.95 | 20.8% | 85.5% | 91.4% |

### Spatial transfer — 5-fold GroupKFold on site

- **macro F1 0.852, balanced accuracy 0.861** (scored on 543 fixed rows)

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.91 | 0.83 | 0.87 | 155 |
| Cereal | 0.95 | 0.92 | 0.94 | 279 |
| Legume | 0.68 | 0.83 | 0.75 | 109 |

Confusion (row = truth, col = predicted):

| |Canola|Cereal|Legume|
|---|---|---|---|
| **Canola** |128|3|24|
| **Cereal** |4|257|18|
| **Legume** |8|10|91|

(importance skipped: skipped by --importance-repeats 0)

### Summary

| split | macro F1 | balanced accuracy |
|---|---|---|
| Temporal transfer — train <=2022, test 2023-24 | 0.826 | 0.833 |
| spatial (GroupKFold on site) | 0.852 | 0.861 |
