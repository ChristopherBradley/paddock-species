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

