# How much of the model comparison is real?

Paired bootstrap, 2000 resamples, 95 % percentile intervals. All configs scored on an **identical** trial set (n=2477, temporal test n=659) so differences are paired row-by-row.

Feature counts: indices 51, bands 274, combined 325.

## 1. Each config on its own

| config | temporal macro F1 | canola @ 5 % FPR | spatial macro F1 |
|---|---|---|---|
| indices | **0.316** [0.273, 0.356] | **77.0** [67.0, 82.9] | **0.273** [0.246, 0.298] |
| bands | **0.301** [0.262, 0.337] | **66.0** [58.9, 76.4] | **0.287** [0.256, 0.316] |
| combined | **0.302** [0.260, 0.344] | **66.0** [53.8, 74.2] | **0.300** [0.270, 0.327] |
| CFI threshold, pooled seasons | — | **37.2** [29.1, 58.4] | — |
| CFI threshold, per season | — | **44.0** [29.3, 57.8] | — |

The per-season CFI row is the baseline that matters: this project measured that one pooled threshold cannot serve multiple seasons, so the pooled row understates what thresholding CFI can do.

## 2. The comparisons the conclusions rest on (paired)

A difference whose interval spans zero is not evidence of an ordering.

| comparison | metric | paired difference | verdict |
|---|---|---|---|
| bands - indices | temporal macro F1 | **-0.015** [-0.058, +0.027] | indistinguishable |
| bands - indices | canola @ 5 % FPR | **-11.0** [-16.1, -1.0] | real |
| bands - indices | spatial macro F1 | **+0.014** [-0.007, +0.035] | indistinguishable |
| combined - indices | temporal macro F1 | **-0.014** [-0.056, +0.031] | indistinguishable |
| combined - indices | canola @ 5 % FPR | **-11.0** [-21.5, -4.1] | real |
| combined - indices | spatial macro F1 | **+0.027** [+0.005, +0.050] | real |
| combined - bands | temporal macro F1 | **+0.001** [-0.027, +0.028] | indistinguishable |
| combined - bands | canola @ 5 % FPR | **+0.0** [-8.9, +3.5] | indistinguishable |
| combined - bands | spatial macro F1 | **+0.013** [-0.005, +0.031] | indistinguishable |
| indices model - cfi pooled | canola @ 5 % FPR | **+39.8** [+17.3, +48.3] | real |
| bands model - cfi pooled | canola @ 5 % FPR | **+28.8** [+8.4, +38.1] | real |
| combined model - cfi pooled | canola @ 5 % FPR | **+28.8** [+4.9, +36.5] | real |
| indices model - cfi per season | canola @ 5 % FPR | **+33.0** [+18.5, +47.0] | real |
| bands model - cfi per season | canola @ 5 % FPR | **+22.0** [+9.7, +37.4] | real |
| combined model - cfi per season | canola @ 5 % FPR | **+22.0** [+7.1, +35.0] | real |

## 3. Is any of the spread just the seed?

Refits of each config on identical data at `random_state` 0, 1. Largest macro-F1 sd across seeds: **0.0000**.

**Zero — the fits are bit-identical.** `HistGradientBoostingClassifier` only consumes its seed for the early-stopping validation split, and early stopping is off below 10,000 samples (we have 1818 training rows). So the seed is not a noise source here, and none of the differences between the overnight runs can be waved away as re-fit jitter — but equally, seeds cannot be used to estimate this model's variance. Test-set sampling, in sections 1-2, is the noise that matters.

## 4. Per-class intervals on the temporal split

Where the macro average's uncertainty comes from — the minority classes. Same resamples across configs, so columns are comparable row-by-row.

| crop | n in test | indices | bands | combined |
|---|---|---|---|---|
| Barley | 95 | 0.22 [0.13, 0.32] | 0.20 [0.12, 0.30] | 0.18 [0.10, 0.27] |
| Canola | 191 | 0.81 [0.76, 0.85] | 0.77 [0.72, 0.82] | 0.75 [0.70, 0.80] |
| Chickpea | 29 | 0.33 [0.11, 0.50] | 0.40 [0.19, 0.58] | 0.38 [0.18, 0.56] |
| Faba Bean | 25 | 0.23 [0.06, 0.44] | 0.22 [0.05, 0.35] | 0.20 [0.05, 0.33] |
| Field Pea | 30 | 0.23 [0.11, 0.34] | 0.34 [0.21, 0.44] | 0.28 [0.15, 0.39] |
| Lentil | 23 | 0.07 [0.00, 0.21] | 0.00 [0.00, 0.00] | 0.12 [0.00, 0.26] |
| Lupin | 22 | 0.27 [0.15, 0.41] | 0.06 [0.00, 0.19] | 0.06 [0.00, 0.20] |
| Oat | 25 | 0.00 [0.00, 0.00] | 0.10 [0.00, 0.23] | 0.11 [0.00, 0.26] |
| Wheat | 219 | 0.68 [0.64, 0.73] | 0.62 [0.57, 0.66] | 0.63 [0.58, 0.68] |
