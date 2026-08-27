# Can yield be an attribute on the paddock map?

Written 2026-08-25 (overnight), answering "remind me where we got to with predicting yields, and
is this a feasible attribute to add". Source for every accuracy number: `YIELD_MODEL.md`,
`YIELD_optical.md`, `YIELD_optical_s1.md`, `CANOLA_YIELD_CHECK.md`.

> **Short answer: yes for cereals, no for canola without Sentinel-1, and it costs almost nothing
> to compute — but it is not ready to ship, for a reason that is about labels rather than
> models.** The regression works (wheat R² 0.58 spatial, 0.44 temporal). The features are
> already identical to the classifier's, so the marginal cost of a yield column is one extra
> `.predict()` call on a feature matrix that has already been built — no second imagery read.
> What is missing is (a) a deployable model file, (b) a resolution of Cereal = wheat-or-barley,
> and (c) an honest handle on the trial-to-paddock offset. (c) turns out to be more tractable
> than `YIELD_MODEL.md` concluded — see §4.

---

## 1. Where the yield work got to

Spatial transfer, 5-fold GroupKFold on site — the split that matches the product question,
"predict a paddock nobody has visited":

| crop | n | year+state baseline R² | optical R² | optical + S1 R² | RMSE t/ha |
|---|---|---|---|---|---|
| **Wheat** | 791 | 0.325 | **0.583** | 0.603 | 1.14 |
| **Barley** | 220 | 0.089 | **0.542** | 0.529 | 1.10 |
| **Canola** | 571 | 0.290 | 0.271 | **0.371** | 0.70 |

**Cereals are predictable from optical alone and canola is not.** Canola's optical R² (0.271)
does not beat knowing the year and the state (0.290) — the satellite adds nothing until
backscatter is included, and then it adds a lot (0.371). That is the exact inverse of the
classification result, where S1 did nothing for canola *identity* and everything for legumes.
The mechanism is coherent: canola identity is written in flowering colour, which CFI already
reads to saturation, while canola yield is biomass and canopy structure, which a flowering index
cannot see once the canopy is yellow.

RMSE is 26-29 % of the median in all three crops, which is large enough that a per-paddock number
must ship with an interval rather than alone.

## 2. What it would cost to compute — almost nothing

`train_yield.py` builds its features with **the same `build_features` from `train_species.py`**
that the classifier uses: 51 index columns, same DOY binning, same contract. So at inference the
feature matrix `predict_tile.py` has already assembled for the classifier is exactly the matrix a
yield model wants.

**It should run alongside, not as a separate script.** The expensive part of `predict_tile.py` is
reading the tile from the datacube and taking the zonal medians; the model call is milliseconds.
Running yield as a second pass would double a 0.0114 SU/tile stage to buy nothing. Concretely:

* add `--yield-model` to `predict_tile.py`, loading a second joblib and calling `.predict()` on
  the same `F`, writing `yield_tha` and an interval;
* the classifier's own output picks which yield model to apply per polygon — a paddock predicted
  Cereal gets the cereal model, Canola the canola model. That coupling is why it belongs in the
  same script: a separate pass would have to re-read the class from disk anyway.

**Marginal cost of the yield column at national scale: under 1 % of the inference stage**, which
is itself 21 % of the bill. Call it ~10 SU on a 5,500 SU run.

## 3. Three things block shipping it today

**(a) There is no deployable yield model.** `train_yield.py` is a *validation* script — it fits
per fold and reports scores, and dumps no joblib. The classifier has `fit_map_model.py` for
exactly this reason (fit on every usable row, save with the column list). Yield needs the
sibling, `fit_yield_model.py`. Small, but it does not exist.

**(b) `Cereal` is wheat-or-barley, and they yield differently** — median 3.92 vs 4.18 t/ha.
`train_yield.py` selects rows with `meta.crop == crop`, so a pooled cereal model is a few lines
(map crop → group before selecting), but pooling two distributions that differ by 0.26 t/ha
inside a model whose RMSE is 1.14 t/ha is defensible only if stated. The alternative — splitting
Cereal into wheat and barley in the classifier — was tried and failed: `GROUP3_MODEL.md` records
barley→wheat as the dominant confusion in the 9-class model, which is why the 3-group target
exists at all.

**(c) The target is trial yield, not commercial paddock yield.** NVT single-site yield is a
replicated variety trial averaged over ~17 varieties under trial management, and trial plots
generally out-yield commercial crops. The label itself is precise (within-trial variety sd 0.28
t/ha, so the trial mean has a standard error near 0.07); all the uncertainty is in the transfer.
And that transfer is not even reliably one-directional — `CANOLA_FLOWERING_AUDIT.md` found the
surrounding field flowers *harder* than the trial, so the paddock is not simply a degraded copy.

## 4. (c) is more tractable than the yield report concluded

`YIELD_MODEL.md` says quantifying the offset "would need commercial yield data — grower records
or a yield-map dataset — which this project does not have". **That is no longer quite true.** The
ABS broadacre extract already downloaded for the area validation carries production in tonnes
(`Broad<Crop>_Prod_Levy`) alongside area (`Broad<Crop>_Area_Total`) for every SA2. Dividing gives
a regional commercial yield, which is precisely the missing reference — at region scale, not
paddock scale, but the offset is a *systematic* quantity and region scale is where you measure it.

Checked tonight against the national totals, and it holds up where it should:

| | ABS area | ABS production | implied yield |
|---|---|---|---|
| Wheat 2022 | 12.93 Mha | 41.20 Mt | **3.19 t/ha** |
| Wheat 2023 | 10.51 Mha | 28.03 Mt | 2.67 t/ha |
| Canola 2022 | 4.36 Mha | 8.92 Mt | **2.05 t/ha** |
| Canola 2024 | 3.67 Mha | 6.81 Mt | 1.86 t/ha |

Those are the right numbers for those seasons. **And the NVT medians sit above them exactly as
the trial-management story predicts** — NVT canola median 2.38 t/ha against ABS national 1.86-2.05,
NVT wheat 3.92 against 2.67-3.19. The offset is real, it is in the expected direction, and it is
now measurable rather than merely acknowledged.

**The caveat, measured, before anyone builds on this.** At SA2 level the levy-based production is
attributed to where the levy was paid, not where the grain grew, and grain moves to receival
points. Across the 355 SA2-years with more than 10,000 ha of wheat, the implied yield has a
sensible median (3.03 t/ha, IQR 2.34-4.11) but **9.3 % of them fall outside 1-6 t/ha**, which is
not physically plausible for broadacre wheat in either direction. Temora reads 7.35 and 8.81 t/ha
in 2022 and 2023 — it has major silos. So:

* **state and national yields from ABS are usable as a calibration reference;**
* **SA2 yields need outlier screening and should be quoted as indicative**, unlike ABS *area*,
  which drove the whole `ABS_COMPARISON_100km.md` result and does not have this problem.

## 5. What I would do, in order

1. **`fit_yield_model.py`** — the missing sibling of `fit_map_model.py`. Cereal pooled, canola
   optical-only for now. Half a day.
2. **Calibrate the trial-to-commercial offset against ABS state yields**, one multiplicative
   factor per crop per state, fitted on 2022 and checked on 2023-24. Report the map's yields
   both raw (NVT-equivalent) and calibrated, and never only calibrated.
3. **Add `--yield-model` to `predict_tile.py`**, writing `yield_tha` plus a prediction interval,
   only for polygons the classifier actually labelled.
4. **Do not ship canola yield until Sentinel-1 is available.** Optical-only canola yield is worse
   than a lookup table of year and state; publishing it would be worse than leaving the column
   empty, which the abstain path already knows how to express.
