# S1 against the latest models: the classifier story reverses, the yield story doesn't

Written 2026-08-31, PBS job 177862351 (`s1_vs_latest.pbs`), 3.06 SU, 5:44 walltime. Answers the
question `EXPERIMENT_PLAN.md` Block 2 posed: every existing S1 number was measured against the
*retired* 3-index optical model — does S1 still help once stacked on the classifier actually
being considered for production (`shipped+sharma6`, macro F1 0.890/0.892) and the yield model
actually shipped (`cereal_yield.joblib`, pooled Wheat+Barley+Oat)?

**Headline: no and yes.** S1 now makes the classifier *worse*, specifically on the one class it
used to fix. S1 still makes the yield model clearly better, by more than the classifier lost.
These are opposite answers to the same question asked of two different models, and both are new
findings — neither was in `S1_MODEL.md`.

All numbers below use `keep_s1both` (2,133 trials, 497 of 543 fixed test rows) throughout,
including the S1-free baselines, so both arms in every comparison see exactly the same rows —
the discipline `S1_MODEL.md` §2 established after the opposite mistake once produced a false
result in each direction.

---

## 1. Classifier: S1 regresses `shipped+sharma6`, and it lands on Legume specifically

| arm | features | temporal macro F1 | spatial macro F1 | canola @ 5% FPR |
|---|---|---|---|---|
| `shipped+sharma6` alone | 153 | **0.887** | **0.886** | 84.0% |
| `shipped+sharma6` + S1 | 204 | 0.864 | 0.868 | 86.8% |
| **change** | +51 | **−0.023** | **−0.018** | +2.8 |

For scale: the established seed-noise floor is ~0.010 (`REVIEWED_MODEL.md`). This regression is
more than twice that, in both splits, in the direction opposite to every S1 arm run against the
old 3-index baseline (`S1_MODEL.md`: +0.029 temporal / +0.007 spatial on that weaker model).

**It lands exactly where the old gain used to be — Legume — but now in reverse:**

| class | F1 without S1 | F1 with S1 | change |
|---|---|---|---|
| **Legume (temporal)** | **0.82** | **0.77** | **−0.05** |
| Legume (spatial) | 0.82 | 0.78 | −0.04 |
| Canola (temporal) | 0.88 | 0.89 | +0.01 |
| Cereal (temporal) | 0.96 | 0.93 | −0.03 |

Temporal confusion, Legume row (100 true Legume trials): Legume→Cereal misclassifications go
**8 → 19**, more than doubling, while Legume recall drops from 87% to 76%. This is the mirror
image of `S1_MODEL.md`'s finding that S1 fixed cereals leaking into Legume against the old
baseline — Sharma6's `ndre2` etc. already fixed that same confusion (permutation importance:
`ndre2` alone carries +0.134 of macro-F1 without S1, the largest single family by a wide margin),
and once it is fixed, S1's 51 extra columns on 1,636 training rows have nothing left to correct
and instead **dilute the signal**: `ndre2`'s importance collapses to +0.018 in the +S1 arm, and
every other family (including `vv`/`vh`/`vhvv` themselves) scores *negative* importance —
shuffling them helps. This reads as classic feature dilution on a training set that did not grow
to match the added columns (153→204 features, same 1,636 rows), not a data quality problem.

**canola@5%FPR moved +2.8 points**, but at n=144 canola in the test set this is within the noise
`S1_MODEL.md` §6 already flagged at this exact operating point (a handful of paddocks swing it
several points either way) — not a real gain, and not large enough to offset the Legume loss.

**What this means for C1 and the anti-claim in `EXPERIMENT_PLAN.md`**: the anti-claim
("S1's gain is redundant with Sharma6") does not just hold, it undershoots — S1 is not neutral
once Sharma6 is in the model, it is actively harmful. **Do not add S1 to the classifier as it is
currently built**, regardless of what Block 1's fj7 cost benchmark finds. A national S1 buy
cannot be justified on crop-type accuracy against this baseline.

## 2. Yield: S1 still clearly helps the model that actually ships

`cereal_yield.joblib` pools Wheat+Barley+Oat into one Cereal-target regressor on indices-only
features — this is the first time it has been tested with S1 (the old `YIELD_optical_s1.md`
tested Wheat/Barley/Canola *separately*, which is not what ships).

| split | arm | R2 (satellite features) | R2 (satellite + year/state) |
|---|---|---|---|
| temporal (train ≤2022, test 2023-24) | indices only | 0.431 | 0.419 |
| temporal | **indices + S1** | **0.465 (+0.034)** | **0.511 (+0.092)** |
| spatial (GroupKFold on site) | indices only | 0.514 | 0.569 |
| spatial | **indices + S1** | **0.568 (+0.054)** | **0.591 (+0.022)** |

Every arm improves with S1, and the largest single gain (+0.092 R2) is on **satellite +
year/state, temporal transfer** — the metric the module's own docstring calls "the real
operational situation... the honest bar." RMSE moves with it: temporal satellite+year/state
1.251 → 1.149 t/ha. 1,089 trials (Wheat 791 / Barley 220 / Oat 78), consistent with the pooled
population `YIELD_cereal_pooled.md` used.

**S1 helps yield for a different reason than it used to help classification.** Backscatter is
sensitive to canopy structure and biomass, which is closer to what a yield regressor needs than
to what separates three crop *types* once phenology-shape indices (Sharma6) already do that job
well. The two questions this project has been asking S1 — "does it separate crops" and "does it
predict how much grain" — turn out to have different answers against the current models, where
they had the same (weak positive) answer against the retired ones.

## 3. What this changes for operationalising S1 at scale

- **The classifier does not need Sentinel-1.** This closes, not just defers, the classification
  half of `EXPERIMENT_PLAN.md`'s Block 2 — no amount of fj7 cost reduction changes a result that
  is now negative on accuracy grounds. Block 5 (national S1 extension, AgriWebb holdout) as
  originally scoped for the *classifier* is no longer worth running.
- **The yield model does.** This reframes the fj7 cost-benefit entirely: the argument for
  national S1 is no longer "fix crop-type Legume confusion" (already fixed by Sharma6, for free)
  but **"improve the yield map,"** which is a real, undiluted +0.09 R2 on the operational
  temporal-transfer bar. `EXPERIMENT_PLAN.md` Block 1's compute benchmark and Block 5's
  scale-up are both still worth running, but the success criterion they should be measured
  against is now the yield gain, not classifier macro F1.
- **Canola is still untouched** by any of this — no canola yield model ships, and S1's ~0 net
  effect on canola classification (already at ceiling per `S1_MODEL.md` §6) is unchanged.

## 4. What is still open

- This is measured on the 100 km Riverina NVT-trial pilot population (2,133 trials), the same
  caveat `SENTINEL1_VALUE.md` §3.2 flagged for the original classifier result: whether the yield
  gain survives on ordinary commercial paddock geometry (vs. clean trial paddocks) is untested.
  There is no yield-equivalent of the AgriWebb holdout to check this against (AgriWebb has crop
  labels, not yields) — worth asking whether any ordinary-geometry yield ground truth exists
  before committing to a national S1-for-yield extraction.
- The revisit-density covariate for the S1B failure discontinuity (`SENTINEL1_VALUE.md` §3.3,
  still not implemented — confirmed by grep) applies equally here: do not trust a multi-year
  (2017-2025) yield gain from S1 until that is built, for the same reason it was flagged for the
  classifier.
- Canola yield remains unshippable regardless (`YIELD_FEASIBILITY.md`) — this result does not
  reopen that question, since S1's classifier-side canola effect was noise-level here too.

## 5. Exact commands

```bash
cd src/paddocks
qsub s1_vs_latest.pbs   # normal queue, 3.06 SU, 5:44 walltime
```

Outputs: `output/arms/GROUP3_ctl_shipped_sharma6_{only,s1}.md`,
`output/YIELD_cereal_pooled_{ctl,s1}.md`, confusion PNGs in `output/figures/`.
