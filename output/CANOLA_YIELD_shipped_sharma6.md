# Yield from the paddock-median series

- features: indices + bands (153 columns)
- target: NVT single-site yield, averaged over varieties within a trial
- **this is trial yield under trial management, not commercial paddock yield** — see the module docstring
- on the temporal split the year+state baseline collapses to **state only**: 2023 and 2024 are unseen in training, so their year dummies are all-zero. That is the real operational situation — you cannot know a season's effect in advance — so it is the honest bar, but it is a weaker bar than the spatial one.

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

