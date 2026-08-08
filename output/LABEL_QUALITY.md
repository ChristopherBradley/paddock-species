# Do co-located trial labels explain the species model's failure?

Every arm is trained on a different subset of the SAME pre-2023 pool and scored on the SAME 323 clean 2023-24 trials (co-location >= 200 m AND not on a conflicting shared polygon), so only the training data varies. 2000 bootstrap resamples of the test set, paired across arms.

Training pool 1818; of the full 2477 kept trials, **31.8% sit on a polygon shared with a different-crop trial in the same year** and 50.6% lie within 200 m of a different-crop trial.

## 1. Nine classes

| training set | n | macro F1 (9 class) |
|---|---|---|
| all | 1818 | **0.378** [0.314, 0.432] |
| drop conflicting | 1181 | **0.372** [0.309, 0.426] |
| drop co-located | 894 | **0.413** [0.341, 0.478] |
| random subsample (control) | 894 | **0.388** [0.307, 0.462] |

| vs `all` | paired difference | verdict |
|---|---|---|
| drop conflicting | **-0.006** [-0.067, +0.055] | indistinguishable |
| drop co-located | **+0.034** [-0.033, +0.102] | indistinguishable |
| random subsample (control) | **+0.007** [-0.068, +0.086] | indistinguishable |

## 2. Three groups — Canola / Cereal / Legume

`9->3` collapses a nine-class model's predictions; `3class` trains on the three groups directly. Both are scored on the identical three-group task, so the comparison is paired and fair.

| training set | n | 9->3 collapsed | 3-class native |
|---|---|---|---|
| all | 1818 | **0.783** [0.731, 0.830] | **0.770** [0.717, 0.815] |
| drop conflicting | 1181 | **0.812** [0.761, 0.856] | **0.782** [0.729, 0.829] |
| drop co-located | 894 | **0.817** [0.766, 0.861] | **0.781** [0.730, 0.827] |
| random subsample (control) | 894 | **0.774** [0.721, 0.820] | **0.746** [0.694, 0.794] |

| training set | native 3-class - collapsed 9-class | verdict |
|---|---|---|
| all | **-0.013** [-0.059, +0.033] | indistinguishable |
| drop conflicting | **-0.030** [-0.077, +0.015] | indistinguishable |
| drop co-located | **-0.036** [-0.076, +0.003] | indistinguishable |
| random subsample (control) | **-0.028** [-0.068, +0.014] | indistinguishable |

### Cleaning vs a random subsample of the same size

`drop co-located` and `random subsample` both train on 894 rows, so this pair isolates the effect of WHICH rows were removed from the effect of how many.

| task | drop co-located - random subsample | verdict |
|---|---|---|
| 9class | **+0.027** [-0.052, +0.101] | indistinguishable |
| 9->3 | **+0.042** [-0.004, +0.089] | indistinguishable |
| 3class | **+0.035** [-0.018, +0.085] | indistinguishable |

## 3. Per-class, on the clean test set


### 9class

| class | n | all | drop conflicting | drop co-located | random subsample (control) |
|---|---|---|---|---|---|
| Barley | 16 | 0.23 | 0.17 | 0.25 | 0.16 |
| Canola | 145 | 0.90 | 0.89 | 0.90 | 0.88 |
| Chickpea | 15 | 0.61 | 0.58 | 0.64 | 0.48 |
| Faba Bean | 14 | 0.35 | 0.31 | 0.42 | 0.32 |
| Field Pea | 6 | 0.07 | 0.19 | 0.25 | 0.21 |
| Lentil | 4 | 0.00 | 0.00 | 0.00 | 0.00 |
| Lupin | 15 | 0.46 | 0.46 | 0.35 | 0.44 |
| Oat | 7 | 0.00 | 0.00 | 0.14 | 0.22 |
| Wheat | 101 | 0.78 | 0.75 | 0.77 | 0.77 |

### 3class

| class | n | all | drop conflicting | drop co-located | random subsample (control) |
|---|---|---|---|---|---|
| Canola | 145 | 0.87 | 0.90 | 0.89 | 0.84 |
| Cereal | 124 | 0.84 | 0.84 | 0.83 | 0.85 |
| Legume | 54 | 0.61 | 0.60 | 0.62 | 0.55 |
