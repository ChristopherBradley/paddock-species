# Yield from the paddock-median series

- features: indices + s1 (102 columns)
- target: NVT single-site yield, averaged over varieties within a trial
- **this is trial yield under trial management, not commercial paddock yield** — see the module docstring
- on the temporal split the year+state baseline collapses to **state only**: 2023 and 2024 are unseen in training, so their year dummies are all-zero. That is the real operational situation — you cannot know a season's effect in advance — so it is the honest bar, but it is a weaker bar than the spatial one.

## Canola

- 571 trials, yield 2.37 t/ha median, sd 0.88, range 0.14-4.70

### temporal transfer — train <=2022, test 2023-24

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 144 | **-0.282** | — | 0.780 | 0.600 | 0.140 | 0.186 |
| satellite features | 144 | **0.212** | +0.494 | 0.612 | 0.484 | 0.525 | 0.501 |
| satellite + year/state | 144 | **0.205** | +0.487 | 0.614 | 0.502 | 0.525 | 0.491 |

### spatial transfer — 5-fold GroupKFold on site

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 571 | **0.290** | — | 0.745 | 0.597 | 0.550 | 0.514 |
| satellite features | 571 | **0.371** | +0.081 | 0.701 | 0.564 | 0.619 | 0.625 |
| satellite + year/state | 571 | **0.378** | +0.088 | 0.697 | 0.567 | 0.624 | 0.624 |

## Wheat

- 791 trials, yield 3.97 t/ha median, sd 1.80, range 0.33-9.20

### temporal transfer — train <=2022, test 2023-24

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 169 | **-0.650** | — | 2.144 | 1.806 | 0.114 | 0.112 |
| satellite features | 169 | **0.506** | +1.156 | 1.173 | 0.924 | 0.722 | 0.725 |
| satellite + year/state | 169 | **0.489** | +1.138 | 1.194 | 0.925 | 0.713 | 0.709 |

### spatial transfer — 5-fold GroupKFold on site

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 791 | **0.325** | — | 1.481 | 1.119 | 0.575 | 0.595 |
| satellite features | 791 | **0.603** | +0.278 | 1.136 | 0.876 | 0.777 | 0.785 |
| satellite + year/state | 791 | **0.633** | +0.308 | 1.092 | 0.831 | 0.796 | 0.804 |

## Barley

- 220 trials, yield 4.19 t/ha median, sd 1.63, range 0.78-8.53

### temporal transfer — train <=2022, test 2023-24

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 69 | **-0.389** | — | 1.928 | 1.617 | 0.002 | 0.021 |
| satellite features | 69 | **0.516** | +0.905 | 1.138 | 0.889 | 0.721 | 0.727 |
| satellite + year/state | 69 | **0.506** | +0.895 | 1.150 | 0.895 | 0.713 | 0.710 |

### spatial transfer — 5-fold GroupKFold on site

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 220 | **0.089** | — | 1.554 | 1.241 | 0.336 | 0.317 |
| satellite features | 220 | **0.529** | +0.440 | 1.118 | 0.917 | 0.729 | 0.727 |
| satellite + year/state | 220 | **0.532** | +0.443 | 1.114 | 0.915 | 0.731 | 0.730 |

