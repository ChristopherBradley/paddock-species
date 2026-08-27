# Is Sentinel-1 worth its cost? The numbers, and a recommendation

> **UPDATE, 2026-08-25 evening — the recommendation below is on hold, and §2 is out of date.**
> The 102 km run has now been scored against ABS over SA2s it *censuses* rather than samples
> (`ABS_COMPARISON_100km.md`). The legume over-prediction that motivated buying S1 is still there,
> but it decomposes: the map calls **1.59x** as much land crop as ABS says was sown, and of the
> 7.2 points of mapped legume, **5.0 are excess land absorbed by the Legume label** and only ~2 are
> the crop-vs-crop confusion S1 was measured to fix. S1's +0.06 legume F1 was measured on NVT
> paddocks that are all real crops, so it addresses the smaller half of the problem. **Fix the
> crop-presence gate, re-measure the legume residual, and only then decide.** Everything in §1
> below — the measured accuracy of S1 features — is unaffected.

Written 2026-08-25. Companion to `SENTINEL1_ACCESS.md`, which covers *how* to get S1 on NCI.
This one is about whether to bother. Source for every accuracy figure: `S1_MODEL.md`.

> **Recommendation in one line: do not buy national Sentinel-1 (~7,957 SU). Buy it for the
> 100 km Riverina region for three years (~277 SU) and test whether it fixes the one error the
> ABS comparison independently found.** That converts an internal +0.029 into an external
> validation for 3.5 % of the national price, and it is the only version of this question that
> can currently be answered.

---

## 1. What S1 actually bought, measured

Three-group model, identical 1,636 training rows and 497 test rows in every arm, macro F1:

| features | temporal transfer | spatial transfer |
|---|---|---|
| optical (3 indices, 51 features) | 0.823 | 0.825 |
| S1 alone (VV/VH/VH-VV, 51 features) | 0.812 | 0.800 |
| **optical + S1** (102 features) | **0.852** | **0.832** |

**+0.029 temporal, +0.007 spatial.** For scale: the hand review of 1,973 polygons bought +0.019,
and the size-matched control seeds had sd 0.010. So the temporal gain is real and worth roughly
1.5 hand reviews. **The spatial gain is inside the noise and must be reported as "no measurable
spatial benefit".**

### Where the gain sits — and this is the important part

| class | optical | +S1 | change |
|---|---|---|---|
| **Legume F1 (temporal)** | 0.69 | **0.75** | **+0.06** |
| **Legume precision (temporal)** | 0.66 | **0.73** | **+0.07** |
| Cereal F1 (temporal) | 0.90 | 0.92 | +0.02 |
| Canola F1 (temporal) | 0.88 | 0.89 | +0.01 |

The specific failure S1 fixes is **cereals leaking into Legume**. Backscatter separates a bushy
pulse canopy from a vertical cereal one, and legume precision goes 0.66 -> 0.73.

S1 alone is *worse* than optical alone but close, and the combination beats both — so the two
sensors carry different information, not two noisy copies of the same thing.

## 2. Why that number just got more interesting

`ABS_COMPARISON.md`, run today against ABS SA2 sown area — **a source with no connection to NVT,
AgriWebb, or anything else in the training pipeline** — found exactly one error outside the noise
floor:

| | mapped | ABS |
|---|---|---|
| Canola | 26.3 % | 29.8 % |
| Cereal | 58.1 % | 64.4 % |
| **Legume** | **7.5 %** | **3.2 %** |

**Legumes over-predicted 2.3x, cereals under-predicted.** ABS and ABARES disagree with each other
by a median 6.8 %, so canola is at the noise floor and cannot yet be called an error — but a 2.3x
gap is far outside it.

**That is the same defect, found twice, by two methods that share no data.** The internal test set
said legume precision is the weak point (0.66, cereals called pulses); the external area
statistics say legumes are over-predicted and cereals under-predicted. They agree, and S1 is the
only intervention measured to move it.

## 3. Three reasons not to write the cheque yet

1. **The uncertainty on the gain is the same size as the gain.** `S1_MODEL.md` §2b: a 3 % change
   in the row set moved the temporal gain from +0.044 to +0.029 and the spatial gain from +0.044
   to +0.007. Model seeds contribute exactly nothing (the fit is deterministic below 10,000 rows),
   so all of that movement is row composition. The honest statement is **+0.03 with an uncertainty
   of roughly the same order**.

2. **It was measured on NVT trial paddocks, not on wall-to-wall SAM polygons.** Every number in §1
   comes from paddocks containing a trial site — larger, cleaner and better-segmented than the
   average polygon in a national map. Whether the legume gain survives on ordinary ground is
   untested, and it is the whole question.

3. **Sentinel-1 coverage is not constant across the years being mapped, and the discontinuity
   lands in the middle of the series.** Sentinel-1B suffered a power anomaly on **23 December
   2021** and its mission was declared over in July 2022; Sentinel-1C launched 5 December 2024 and
   became fully operational in **early May 2025**. So the constellation was two satellites through
   2021, **one satellite from 2022 to April 2025**, and two again after. For the 2017-2025 run now
   under way, **four of the nine years carry roughly half the revisit of the others** — an
   instrument change sitting exactly where a temporal-transfer model would read it as land-use
   change. Any S1 feature built across this series needs a revisit-density covariate or it will
   confound the two.

## 4. The cost, restated

| option | SU | share of the 50 KSU budget |
|---|---|---|
| **S1 for the 100 km region, 3 years** | **~277** | 0.6 % |
| S1 for the 100 km region, all 9 years | ~832 | 1.7 % |
| S1 nationally, one year (MPC via copyq) | **~7,957** | 16 % |
| the optical national map itself | 5,497 | 11 % |

copyq bills 4.00 SU/hr per CPU — twice `normal` — measured from this project's own download jobs.
`fj7`, if it lands, removes the download line entirely, but its GRD->RTC processing cost is
unmeasured and could exceed what it replaces.

## 5. My recommendation, and the decision rule

**Run S1 over the 100 km Riverina region for 2019, 2020 and 2021** — three consecutive
two-satellite years, so revisit density is constant and §3.3 cannot confound the result. ~277 SU.
Then re-run `abs_compare.py` on optical and optical+S1 and read one number: **does the legume
share move from 7.5 % toward ABS's 3.2 %?**

* **If it does** — national S1 is justified. 7,957 SU buys a correction to the only error the
  independent data can see, and that is a defensible 16 % of the budget.
* **If it does not** — the +0.029 was a property of trial paddocks and does not survive contact
  with wall-to-wall geometry. **8,000 SU saved for 277**, and the legume problem needs a different
  fix (more legume training rows, or collapsing legumes into a single "pulse" class rather than
  pretending to resolve them).

**The trade at national scale, stated plainly.** +0.03 macro F1 for 16 % of the annual budget is a
poor deal on its own — it is roughly what better label review bought for free. What makes it
arguable is that the gain is concentrated in precisely the class the external validation says is
broken. That is a good reason to spend 277 SU finding out, and not yet a good reason to spend
7,957.
