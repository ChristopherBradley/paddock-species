# Yield from the paddock-median series

- features: indices (51 columns)
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
| satellite features | 144 | **0.083** | +0.365 | 0.660 | 0.534 | 0.408 | 0.386 |
| satellite + year/state | 144 | **0.160** | +0.441 | 0.632 | 0.523 | 0.459 | 0.446 |

### spatial transfer — 5-fold GroupKFold on site

| arm | n | R2 | gain over baseline | RMSE t/ha | MAE | Pearson r | Spearman rho |
|---|---|---|---|---|---|---|---|
| year+state baseline | 571 | **0.290** | — | 0.745 | 0.597 | 0.550 | 0.514 |
| satellite features | 571 | **0.271** | -0.019 | 0.754 | 0.596 | 0.540 | 0.549 |
| satellite + year/state | 571 | **0.365** | +0.075 | 0.704 | 0.559 | 0.610 | 0.604 |

