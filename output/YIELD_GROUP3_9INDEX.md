# Yield from the paddock-median series

- features: indices + bands (153 columns)
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
| satellite features | 279 | **0.486** | +1.129 | 1.181 | 0.923 | 0.724 | 0.710 |
| satellite + year/state | 279 | **0.501** | +1.144 | 1.163 | 0.927 | 0.736 | 0.711 |

### spatial transfer — 5-fold GroupKFold on site

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 1119 | **0.294** | — | 1.473 | 1.138 | 0.547 | 0.569 |
| satellite features | 1119 | **0.564** | +0.270 | 1.157 | 0.905 | 0.751 | 0.752 |
| satellite + year/state | 1119 | **0.566** | +0.272 | 1.154 | 0.889 | 0.754 | 0.755 |

## Canola

- 585 trials, yield 2.38 t/ha median, sd 0.88, range 0.14-4.70

- pooled species: Canola 585 (100.0%)

### temporal transfer — train <=2022, test 2023-24

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 155 | **-0.237** | — | 0.758 | 0.586 | 0.134 | 0.125 |
| satellite features | 155 | **0.007** | +0.243 | 0.680 | 0.540 | 0.418 | 0.430 |
| satellite + year/state | 155 | **0.012** | +0.248 | 0.678 | 0.547 | 0.408 | 0.419 |

### spatial transfer — 5-fold GroupKFold on site

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 585 | **0.316** | — | 0.726 | 0.586 | 0.570 | 0.522 |
| satellite features | 585 | **0.299** | -0.017 | 0.735 | 0.594 | 0.556 | 0.550 |
| satellite + year/state | 585 | **0.322** | +0.007 | 0.722 | 0.583 | 0.576 | 0.571 |

## Legume

- 490 trials, yield 1.93 t/ha median, sd 1.13, range 0.07-6.52

- pooled species: Chickpea 126 (25.7%), Field Pea 120 (24.5%), Lupin 86 (17.6%), Faba Bean 80 (16.3%), Lentil 78 (15.9%)

### temporal transfer — train <=2022, test 2023-24

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 109 | **-0.518** | — | 1.170 | 0.973 | 0.208 | 0.089 |
| satellite features | 109 | **0.426** | +0.944 | 0.720 | 0.557 | 0.664 | 0.674 |
| satellite + year/state | 109 | **0.402** | +0.920 | 0.734 | 0.546 | 0.652 | 0.688 |

### spatial transfer — 5-fold GroupKFold on site

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 490 | **0.133** | — | 1.056 | 0.833 | 0.389 | 0.380 |
| satellite features | 490 | **0.458** | +0.325 | 0.835 | 0.635 | 0.683 | 0.699 |
| satellite + year/state | 490 | **0.451** | +0.318 | 0.840 | 0.647 | 0.679 | 0.688 |

