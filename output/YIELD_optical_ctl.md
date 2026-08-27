# Yield from the paddock-median series

- features: indices (51 columns)
- target: NVT single-site yield, averaged over varieties within a trial
- **this is trial yield under trial management, not commercial paddock yield** — see the module docstring
- on the temporal split the year+state baseline collapses to **state only**: 2023 and 2024 are unseen in training, so their year dummies are all-zero. That is the real operational situation — you cannot know a season's effect in advance — so it is the honest bar, but it is a weaker bar than the spatial one.

## Canola

- 571 trials, yield 2.37 t/ha median, sd 0.88, range 0.14-4.70

### temporal transfer — train <=2022, test 2023-24

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 144 | **-0.282** | — | 0.780 | 0.600 | 0.140 | 0.186 |
| satellite features | 144 | **0.083** | +0.365 | 0.660 | 0.534 | 0.408 | 0.386 |
| satellite + year/state | 144 | **0.160** | +0.441 | 0.632 | 0.523 | 0.459 | 0.446 |

### spatial transfer — 5-fold GroupKFold on site

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 571 | **0.290** | — | 0.745 | 0.597 | 0.550 | 0.514 |
| satellite features | 571 | **0.271** | -0.019 | 0.754 | 0.596 | 0.540 | 0.549 |
| satellite + year/state | 571 | **0.365** | +0.075 | 0.704 | 0.559 | 0.610 | 0.604 |

## Wheat

- 791 trials, yield 3.97 t/ha median, sd 1.80, range 0.33-9.20

### temporal transfer — train <=2022, test 2023-24

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 169 | **-0.650** | — | 2.144 | 1.806 | 0.114 | 0.112 |
| satellite features | 169 | **0.437** | +1.087 | 1.252 | 0.959 | 0.679 | 0.674 |
| satellite + year/state | 169 | **0.475** | +1.125 | 1.209 | 0.920 | 0.716 | 0.712 |

### spatial transfer — 5-fold GroupKFold on site

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 791 | **0.325** | — | 1.481 | 1.119 | 0.575 | 0.595 |
| satellite features | 791 | **0.583** | +0.258 | 1.165 | 0.902 | 0.764 | 0.766 |
| satellite + year/state | 791 | **0.625** | +0.300 | 1.104 | 0.827 | 0.792 | 0.794 |

## Barley

- 220 trials, yield 4.19 t/ha median, sd 1.63, range 0.78-8.53

### temporal transfer — train <=2022, test 2023-24

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 69 | **-0.389** | — | 1.928 | 1.617 | 0.002 | 0.021 |
| satellite features | 69 | **0.539** | +0.927 | 1.111 | 0.892 | 0.734 | 0.729 |
| satellite + year/state | 69 | **0.505** | +0.893 | 1.152 | 0.913 | 0.711 | 0.716 |

### spatial transfer — 5-fold GroupKFold on site

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 220 | **0.089** | — | 1.554 | 1.241 | 0.336 | 0.317 |
| satellite features | 220 | **0.542** | +0.453 | 1.102 | 0.894 | 0.739 | 0.742 |
| satellite + year/state | 220 | **0.541** | +0.451 | 1.104 | 0.898 | 0.738 | 0.739 |

