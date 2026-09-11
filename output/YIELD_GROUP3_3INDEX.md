# Yield from the paddock-median series

- features: indices (51 columns)
- target: NVT single-site yield, averaged over varieties within a trial
- **this is trial yield under trial management, not commercial paddock yield** — see the module docstring
- on the temporal split the year+state baseline collapses to **state only**: 2023 and 2024 are unseen in training, so their year dummies are all-zero. That is the real operational situation — you cannot know a season's effect in advance — so it is the honest bar, but it is a weaker bar than the spatial one.

## Cereal

- 1119 trials, yield 3.97 t/ha median, sd 1.75, range 0.33-9.20

- pooled species: Wheat 811 (72.5%), Barley 227 (20.3%), Oat 81 (7.2%)

### temporal transfer — train <=2022, test 2023-24

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 279 | **-0.643** | — | 2.111 | 1.765 | 0.032 | 0.137 |
| satellite features | 279 | **0.471** | +1.114 | 1.197 | 0.930 | 0.720 | 0.694 |
| satellite + year/state | 279 | **0.486** | +1.128 | 1.181 | 0.931 | 0.730 | 0.718 |

### spatial transfer — 5-fold GroupKFold on site

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 1119 | **0.294** | — | 1.473 | 1.138 | 0.547 | 0.569 |
| satellite features | 1119 | **0.526** | +0.232 | 1.207 | 0.944 | 0.727 | 0.726 |
| satellite + year/state | 1119 | **0.577** | +0.283 | 1.140 | 0.877 | 0.760 | 0.765 |

## Canola

- 585 trials, yield 2.38 t/ha median, sd 0.88, range 0.14-4.70

- pooled species: Canola 585 (100.0%)

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

## Legume

- 490 trials, yield 1.93 t/ha median, sd 1.13, range 0.07-6.52

- pooled species: Chickpea 126 (25.7%), Field Pea 120 (24.5%), Lupin 86 (17.6%), Faba Bean 80 (16.3%), Lentil 78 (15.9%)

### temporal transfer — train <=2022, test 2023-24

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 109 | **-0.518** | — | 1.170 | 0.973 | 0.208 | 0.089 |
| satellite features | 109 | **0.261** | +0.779 | 0.817 | 0.616 | 0.536 | 0.609 |
| satellite + year/state | 109 | **0.325** | +0.843 | 0.780 | 0.578 | 0.588 | 0.680 |

### spatial transfer — 5-fold GroupKFold on site

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 490 | **0.133** | — | 1.056 | 0.833 | 0.389 | 0.380 |
| satellite features | 490 | **0.371** | +0.239 | 0.899 | 0.701 | 0.632 | 0.641 |
| satellite + year/state | 490 | **0.402** | +0.270 | 0.877 | 0.684 | 0.649 | 0.655 |

