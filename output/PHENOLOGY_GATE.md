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

## Next step to close out the NEXT_STEPS.md §6.2 criterion

The deployable thresholds above are saved to the model bundle and are wireable into `predict_tile.py` as `--crop-gate-shape` (see the flag's help text — it is NOT the default; §6.2 needs the area-ratio number before that would be justified). Re-run a validation region (the 100 km Riverina block already has 9 years of ground truth) with it enabled, and re-score with `abs_compare.py`. Only if the area ratio moves toward 1.0 *while* this recall number holds does §6.2's bar get cleared.
