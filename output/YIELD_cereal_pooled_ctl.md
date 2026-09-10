# Yield from the paddock-median series

- features: indices (51 columns)
- target: NVT single-site yield, averaged over varieties within a trial
- **this is trial yield under trial management, not commercial paddock yield** — see the module docstring
- on the temporal split the year+state baseline collapses to **state only**: 2023 and 2024 are unseen in training, so their year dummies are all-zero. That is the real operational situation — you cannot know a season's effect in advance — so it is the honest bar, but it is a weaker bar than the spatial one.

## Cereal

- 1089 trials, yield 4.01 t/ha median, sd 1.76, range 0.33-9.20

- pooled species: Wheat 791 (72.6%), Barley 220 (20.2%), Oat 78 (7.2%)

### temporal transfer — train <=2022, test 2023-24

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 253 | **-0.789** | — | 2.197 | 1.851 | 0.025 | 0.101 |
| satellite features | 253 | **0.431** | +1.220 | 1.239 | 0.981 | 0.694 | 0.671 |
| satellite + year/state | 253 | **0.419** | +1.209 | 1.251 | 0.991 | 0.699 | 0.692 |

### spatial transfer — 5-fold GroupKFold on site

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 1089 | **0.320** | — | 1.451 | 1.111 | 0.568 | 0.586 |
| satellite features | 1089 | **0.514** | +0.194 | 1.227 | 0.945 | 0.720 | 0.723 |
| satellite + year/state | 1089 | **0.569** | +0.249 | 1.155 | 0.877 | 0.756 | 0.761 |

