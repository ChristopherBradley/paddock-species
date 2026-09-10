# Yield from the paddock-median series

- features: indices + s1 (102 columns)
- target: NVT single-site yield, averaged over varieties within a trial
- **this is trial yield under trial management, not commercial paddock yield** — see the module docstring
- on the temporal split the year+state baseline collapses to **state only**: 2023 and 2024 are unseen in training, so their year dummies are all-zero. That is the real operational situation — you cannot know a season's effect in advance — so it is the honest bar, but it is a weaker bar than the spatial one.

## Canola

- 571 trials, yield 2.37 t/ha median, sd 0.88, range 0.14-4.70

- pooled species: Canola 571 (100.0%)

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

