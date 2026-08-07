# Paddock median vs 200 m window — CFI canola/wheat separation

Trials: 129 of 169 (clear-frac >= 0.5, contains-only)
Flowering window: 120-190 days after sowing

| estimator | Youden J | threshold | canola flagged | wheat flagged |
|---|---|---|---|---|
| 200 m window mean (baseline) | **0.318** | 0.1280 | 78.8% | 46.9% |
| paddock median | **0.398** | 0.1777 | 50.0% | 10.2% |
| paddock mean | **0.401** | 0.1755 | 46.2% | 6.1% |

(n = 80 canola, 49 wheat)

## Per-year Youden J (pooling across years is misleading)

| year | n canola | n wheat | 200 m window mean (baseline) | paddock median | paddock mean |
|---|---|---|---|---|---|
| 2018 | 9 | 5 | 0.689 | 0.600 | 0.600 |
| 2019 | 24 | 10 | 0.433 | 0.508 | 0.508 |
| 2020 | 15 | 5 | 0.400 | 0.400 | 0.400 |
| 2021 | 13 | 10 | 0.469 | 0.669 | 0.669 |
| 2022 | 9 | 10 | 0.500 | 0.500 | 0.500 |
| 2023 | 10 | 9 | 0.778 | 0.778 | 0.778 |
| **mean** | | | **0.545** | **0.576** | **0.576** |

## Paired bootstrap (2000 resamples of 129 trials)

| comparison | median ΔJ | 95% CI | P(better) |
|---|---|---|---|
| paddock median − baseline (pooled) | +0.072 | [-0.053, +0.211] | 86% |
| paddock median − baseline (**year-stratified**) | +0.026 | [-0.095, +0.149] | 66% |
| paddock mean − baseline (pooled) | +0.078 | [-0.047, +0.230] | 87% |
| paddock mean − baseline (**year-stratified**) | +0.026 | [-0.085, +0.141] | 68% |

ΔJ > 0 means the paddock estimator separates the crops better than the 200 m window on the same trials. A CI spanning 0 means this pilot cannot tell them apart — report that rather than picking the larger number.

## Trial-to-paddock matching

- `contains`: 129 trials (100%)

Paddock area: median 35 ha (p10 7, p90 139)
Trial distance to paddock edge: median 46 m (p10 8, p90 154)
