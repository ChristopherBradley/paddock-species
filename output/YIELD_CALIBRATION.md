# Calibrating NVT trial yield to ABS commercial yield

Written 2026-08-27. Closes item 2 of `YIELD_FEASIBILITY.md` §5: "calibrate the trial-to-commercial
offset against ABS state yields... fitted on 2022 and checked on 2023-24."

## Why a calibration is needed at all

`cereal_yield.joblib` (`fit_yield_model.py`) is trained on NVT single-site yield — a replicated
variety trial under trial management, which consistently out-yields the commercial paddock around
it. `YIELD_FEASIBILITY.md` §4 already showed the offset is real and in the expected direction at
national scale. This closes the loop: a measured multiplicative factor, applied at inference.

## The factor

Both sides pooled Wheat+Barley+Oat, matching the classifier's `Cereal` group exactly (not just
Wheat+Barley — see `fit_yield_model.py`'s docstring for why Oat has to be included):

- **ABS side**: `abs_broadacre_raw.csv`, `Broad{Wheat,Barley,Oats}_{Area_Total,Prod_Levy}`,
  summed over **SA2-level regions only** (`REGION` mixes state/national-aggregate/SA2 codes in
  one column at 1/3/9 character lengths respectively — summing without filtering to 9-character
  SA2 codes triple-counts every hectare, exactly as `abs_fetch.py` already documented for the
  area-only comparison). Implied yield = production / area.
- **NVT side**: pooled-Cereal median single-site yield by `Year`, from the same labeled/yield
  join `fit_yield_model.py` trains on.

| year | ABS implied yield (Wheat+Barley+Oat) | NVT pooled-Cereal median |
|---|---|---|
| 2022 (fit) | 3.216 t/ha | 5.147 t/ha |
| 2023 (check) | 2.640 t/ha | 3.460 t/ha |
| 2024 (check) | 2.663 t/ha | 4.129 t/ha |

**Factor = 3.216 / 5.147 = 0.6248**, fit on 2022 only (matching the plan's stated methodology,
not a multi-year average — see "how good is a one-year fit" below for why that matters).

## How good is a one-year fit

| year | NVT median x factor | vs ABS actual | error |
|---|---|---|---|
| 2023 | 2.162 t/ha | 2.640 t/ha | **+18.1%** |
| 2024 | 2.580 t/ha | 2.663 t/ha | **+3.1%** |

**This is not a precise correction — it is a coarse offset, and the 2023 residual says so
plainly.** Year-to-year variation in the true NVT-to-commercial gap (season, region mix, disease
pressure) is not something a single constant can capture; this project has said as much for yield
generally ("most yield variance in Australian cropping is season x region," `train_yield.py`).
Treat the calibrated column as a directionally-corrected estimate, not a validated commercial
yield map — its own uncertainty (roughly ±3-18% on top of the model's measured RMSE, ±1.21 t/ha /
30% of the median, `output/YIELD_cereal_pooled.md`) has not itself been formally quantified beyond
these two check years, because ABS only publishes 2022-2024.

## What ships

`predict_tile.py --yield-model` now writes **both** columns on every Cereal-classified polygon,
never only the calibrated one:

- `yield_tha` — raw, NVT-trial-equivalent
- `yield_tha_calibrated` — `yield_tha x calibration_factor` (0.6248, stored in the model bundle
  alongside a `calibration_note` recording exactly how it was derived, for audit)

`run_national.sh predict` now passes `--yield-model $D/models/cereal_yield.joblib` by default, so
the next national run ships both yield columns on Cereal polygons without further setup.
