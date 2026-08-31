# A phenology-SHAPE presence gate — green-up timing + post-harvest senescence

**Two variants, because one of them cannot be deployed.** The ORACLE variant windows on each trial's own recorded `sow`/`harv` date — the literal reading of "one green-up at the right time, ending in a hard senescence" — but a wall-to-wall map has no sow/harv date for an arbitrary polygon, so it cannot run at inference. The DEPLOYABLE variant windows on the series' own DETECTED peak instead (no external date needed) — what `predict_tile.py` can actually compute for every polygon. Both are reported so the cost of not knowing the true date is visible, not hidden.

- oracle: 2051 trials with a usable sow/harv date and clear observations either side of it
- deployable: 2177 trials with >= 3 clear observations (of 2194 passing --min-obs)

**Scope, stated up front.** Both variants measure held-out PRESENCE RECALL only — the same kind of number `PRESENCE_ONLY_LABELS.md` reports for the amplitude gate (91.6 %, over a different, larger population — see the caveat below the recall table). Neither measures the area-ratio impact against ABS, which needs a wall-to-wall re-run. `NEXT_STEPS.md` §6.2's acceptance criterion needs both numbers; this is the first, and only for the deployable variant does closing it out even make sense.

## The gates

Both conditions must clear their threshold in each variant (fit presence-only: the loosest percentile of the training positives that still keeps >= 91.6% of them, 5-fold cross-validated):

| | oracle (sow/harv-anchored) | deployable (peak-anchored) |
|---|---|---|
| `greenup_rise` >= | 0.671 | 0.271 |
| `senescence_drop` >= | 0.609 | 0.318 |

## Held-out recall, vs. the current amplitude gate on the same rows

**Not directly comparable to `PRESENCE_ONLY_LABELS.md`'s 91.6% headline** — that number is over the full 3,439 known-sown trials; both populations here are smaller (hand-reviewed geometry, `--keep keep_reviewed`, plus — for oracle — a usable sow/harv date). Within each column the two gates ARE comparable, because they share a population:

| gate | oracle population | deployable population |
|---|---|---|
| current (`ndvi_amp >= 0.35`) | 94.4% | 94.5% |
| **phenology-shape** (this gate) | **92.2%** | **91.9%** |

Fold recalls, oracle: 91.5%, 92.9%, 91.5%, 93.9%, 91.2%


Fold recalls, deployable: 91.7%, 89.9%, 89.2%, 94.7%, 94.0%

**The deployable variant gives up 0.3 points of recall relative to oracle** for the same target — the measurable cost of not knowing the true sow/harv date. This is the number that matters for shipping: the oracle column is a ceiling, not a candidate.

## What the deployable shape gate adds beyond amplitude

Same deployable-variant population, both gates applied (not a validation — these are all known-sown positives, so this shows *agreement*, not *correctness*):

| | passes amplitude | fails amplitude |
|---|---|---|
| **passes shape** | 87.0% | 5.1% |
| **fails shape** | 7.6% | 0.4% |

**7.6% of known-sown trials clear the amplitude gate but fail the shape gate** — high amplitude with no clean green-up-then-senescence pattern around the series' own peak. On a real crop these are false rejections (the cost of the shape gate being stricter); on sown-but-not-harvested land the amplitude gate over-admits, and the same mechanism should reject more of it — untested here, because that population has no clean label left in this repo (see the AgriWebb removal).

## Recall by crop

Same deployable-variant population and baseline threshold, split by the trial's own crop group (not cross-validated — exploratory, same status as the table above):

| group | n | shape recall | amplitude recall |
|---|---|---|---|
| **Canola** | 580 | 83.1% | 94.5% |
| **Cereal** | 1113 | 95.1% | 96.0% |
| **Legume** | 484 | 95.5% | 91.3% |

Median `senescence_drop`: Canola 0.659, Cereal 0.768, Legume 0.763. A single shared threshold screens out disproportionately more of whichever crop senesces least sharply post-flowering by this metric.

## Experimental: a looser senescence_drop threshold (slack 3 pts)

`senescence_drop` loosened from the 4.0th to the 1.0th percentile (0.318 -> 0.212); `greenup_rise` unchanged at 0.271. Full-population, not cross-validated — a recall trade-off number, not an area-ratio one.

| group | n | shape recall (loosened) | shape recall (baseline) |
|---|---|---|---|
| **Canola** | 580 | 93.1% | 83.1% |
| **Cereal** | 1113 | 95.4% | 95.1% |
| **Legume** | 484 | 96.1% | 95.5% |

Pooled recall: **94.9%** (baseline 91.9%). Whether this actually helps still needs the regional ABS re-run — loosening lets more real crop through, and by the same mechanism lets back some of the excess land the baseline gate was rejecting.

Saved: `/scratch/xe2/cb8590/paddock-species-data/derived/models/phenology_gate_loose.joblib`

## Experimental: two-pass gating (Canola exempted from the shape gate)

Canola trials pass on the amplitude gate alone; Cereal/Legume trials need both gates (baseline thresholds, unchanged). Full-population, not cross-validated — uses each trial's TRUE crop group as the stand-in for the classifier's predicted class, the same substitution the table above makes.

| | n | recall |
|---|---|---|
| **pooled** | 2177 | 91.3% |
| **Canola** | 580 | 94.5% |
| **Cereal** | 1113 | 91.4% |
| **Legume** | 484 | 87.2% |

No new model bundle needed — this is `predict_tile.py --shape-gate-skip-classes Canola` against the existing `--model-out` bundle. What this cannot show locally: whether exempting Canola from the shape gate lets non-crop land that the classifier mis-calls Canola back onto the map — that risk only shows up in the regional ABS re-run, same as the area-ratio number always has.

## Stacked with amplitude — the number that actually ships

`predict_tile.py` applies `--crop-gate-amp` and `--crop-gate-shape` together (either failing aborts the polygon), so this is the recall a reader of the map actually gets, not the shape-gate-alone number the tables above report:

| config | pooled | Canola | Cereal | Legume |
|---|---|---|---|---|
| baseline (shipped) | 87.0% | 78.3% | 91.4% | 87.2% |
| loosened senescence (-3 pts) | 89.6% | 87.6% | 91.6% | 87.6% |
| two-pass (Canola exempt) | 91.3% | 94.5% | 91.4% | 87.2% |

## Next step to close out the NEXT_STEPS.md §6.2 criterion

The deployable thresholds above are saved to the model bundle and are wireable into `predict_tile.py` as `--crop-gate-shape` (see the flag's help text — it is NOT the default; §6.2 needs the area-ratio number before that would be justified). Re-run a validation region (the 100 km Riverina block already has 9 years of ground truth) with it enabled, and re-score with `abs_compare.py`. Only if the area ratio moves toward 1.0 *while* this recall number holds does §6.2's bar get cleared.

**A correction, found while adding the tables above.** The regional test's headline canola number (83.4%) was the shape gate measured alone; `predict_tile.py` always stacks it with the amplitude gate, and stacked, canola's real presence recall under the shipped (rejected) shape-gate config is **78.3%**, not 83.4% — the canola-undercount problem the regional test found was understated, not overstated, by the verdict already on record in this file and in `NEXT_STEPS.md` §4.

**Of the two untried fixes, two-pass gating is the stronger local result**: it restores Canola to its amplitude-only recall (94.5%, vs. 78.3% baseline and 87.6% for the best achievable senescence-loosening) with zero effect on Cereal or Legume, because it does not touch their thresholds at all. Loosening `senescence_drop` tops out at 87.6% for Canola — the percentile search this gate uses (1st-40th) is already at its floor by slack 3, so a looser number is not reachable this way without changing the fitting method itself. Neither number is validated against the ABS area ratio yet; both need the regional rerun `run_map100.sh predict-shapegate-twopass` / `predict-shapegate-loose` now provide, each ~120 SU on the existing 9-year Riverina segmentation, before either is a candidate to ship.
