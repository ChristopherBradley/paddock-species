# Yield from the paddock-median series

- features: indices (51 columns)
- target: NVT single-site yield, averaged over varieties within a trial
- **this is trial yield under trial management, not commercial paddock yield** — see the module docstring
- on the temporal split the year+state baseline collapses to **state only**: 2023 and 2024 are unseen in training, so their year dummies are all-zero. That is the real operational situation — you cannot know a season's effect in advance — so it is the honest bar, but it is a weaker bar than the spatial one.

## Canola

- 585 trials, yield 2.38 t/ha median, sd 0.88, range 0.14-4.70

### temporal transfer — train <=2022, test 2023-24

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 155 | **-0.237** | — | 0.758 | 0.586 | 0.134 | 0.125 |
| satellite features | 155 | **0.110** | +0.347 | 0.643 | 0.519 | 0.434 | 0.388 |
| satellite + year/state | 155 | **0.206** | +0.443 | 0.608 | 0.485 | 0.512 | 0.487 |

### spatial transfer — 5-fold GroupKFold on site

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 585 | **0.316** | — | 0.726 | 0.586 | 0.570 | 0.522 |
| satellite features | 585 | **0.284** | -0.032 | 0.742 | 0.600 | 0.544 | 0.532 |
| satellite + year/state | 585 | **0.376** | +0.061 | 0.693 | 0.546 | 0.615 | 0.606 |

## Wheat

- 811 trials, yield 3.92 t/ha median, sd 1.80, range 0.33-9.20

### temporal transfer — train <=2022, test 2023-24

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 187 | **-0.498** | — | 2.069 | 1.718 | 0.070 | -0.110 |
| satellite features | 187 | **0.514** | +1.012 | 1.178 | 0.896 | 0.730 | 0.728 |
| satellite + year/state | 187 | **0.527** | +1.026 | 1.162 | 0.906 | 0.748 | 0.754 |

### spatial transfer — 5-fold GroupKFold on site

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 811 | **0.294** | — | 1.511 | 1.150 | 0.552 | 0.569 |
| satellite features | 811 | **0.554** | +0.261 | 1.200 | 0.920 | 0.745 | 0.745 |
| satellite + year/state | 811 | **0.600** | +0.306 | 1.137 | 0.859 | 0.775 | 0.782 |

## Barley

- 227 trials, yield 4.18 t/ha median, sd 1.62, range 0.78-8.53

### temporal transfer — train <=2022, test 2023-24

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 74 | **-0.430** | — | 1.950 | 1.637 | -0.026 | -0.003 |
| satellite features | 74 | **0.510** | +0.940 | 1.141 | 0.878 | 0.715 | 0.734 |
| satellite + year/state | 74 | **0.519** | +0.949 | 1.131 | 0.895 | 0.721 | 0.731 |

### spatial transfer — 5-fold GroupKFold on site

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 227 | **0.168** | — | 1.479 | 1.195 | 0.414 | 0.410 |
| satellite features | 227 | **0.545** | +0.377 | 1.094 | 0.890 | 0.740 | 0.735 |
| satellite + year/state | 227 | **0.548** | +0.380 | 1.091 | 0.884 | 0.742 | 0.738 |

