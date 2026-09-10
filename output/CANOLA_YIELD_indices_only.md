# Yield from the paddock-median series

- features: indices (51 columns)
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
| satellite features | 155 | **0.110** | +0.347 | 0.643 | 0.519 | 0.434 | 0.388 |
| satellite + year/state | 155 | **0.206** | +0.443 | 0.608 | 0.485 | 0.512 | 0.487 |

### spatial transfer — 5-fold GroupKFold on site

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 585 | **0.316** | — | 0.726 | 0.586 | 0.570 | 0.522 |
| satellite features | 585 | **0.284** | -0.032 | 0.742 | 0.600 | 0.544 | 0.532 |
| satellite + year/state | 585 | **0.376** | +0.061 | 0.693 | 0.546 | 0.615 | 0.606 |

