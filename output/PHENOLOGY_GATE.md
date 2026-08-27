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

## Recall by crop — the number the pooled 91.9% was hiding

Written 2026-08-27, after the regional test below made this worth checking. Same deployable-variant population and threshold, split by the trial's own crop group:

| group | n | shape recall | amplitude recall |
|---|---|---|---|
| **Canola** | 580 | **83.4%** | 94.5% |
| Cereal | 1,113 | 95.1% | 96.0% |
| Legume | 484 | 95.5% | 91.3% |

**The pooled 91.9% headline is an average over a canola-specific shortfall and a cereal/legume surplus — it is not close to uniform.** Canola's median `senescence_drop` (0.659) sits well below cereal's (0.768): the crop most associated with this whole project (`initial_nora_prompt.md` named it the intended starting point) senesces less sharply post-flowering than cereal does, at least by this metric, so a single shared threshold systematically screens more of it out. **§6.2's acceptance criterion — "presence recall stays at or above 91.6%" — is met in aggregate and failed for canola specifically**, and canola is the class this matters most for.

## Regional test: the 100 km x 9-year Riverina run, `--crop-gate-shape` stacked on `--crop-gate-amp`

Run 2026-08-27 via `run_map100.sh predict-shapegate` — the existing segmentation (10,404 tile-years, unchanged), re-classified with the shape gate added. Cost: **120 SU**, 30/30 chunks succeeded. Scored with the same `abs_compare.py` methodology as the original baseline (`ABS_COMPARISON_100km.md`); full report: `ABS_COMPARISON_100km_shapegate.md`.

**The headline number moved exactly where §6.2 hoped.** Area ratio (mapped crop ha / ABS sown ha, median over the 6 well-covered SA2-years): **1.59 -> 1.00**. Coverage fell from 71.5% to 55.3% of polygons classified (`no_crop_shape` is now the single largest abstain reason, 40,089 polygons / 1.15 Mha) — the gate is doing real, substantial work, not passing everything.

**But the canola share error did not move: 23.4% mapped against ABS 36.2%, unchanged from baseline to the decimal point.** This is the canola-specific recall shortfall above, showing up exactly where it would: fixing the area over-call should have let canola's *diluted* share (what a perfect classifier reports once the excess land is divided out) converge toward the ABS share — and it did, `diluted` is now 36.1%, matching ABS almost exactly — but *mapped* stayed at 23.4%, so `absorbed` is now **-12.7 points**, a real classification/recall shortfall that the area fix simply unmasked. Before the shape gate, this same gap was explained entirely by dilution (`NEXT_STEPS.md` §4c: "there is no evidence here of a canola classification problem at all"); with the shape gate in place, that statement is no longer true.

**Verdict: not a clean win.** One of the two required numbers (area ratio) is a clear pass; the other (presence recall) passes in aggregate and fails for the map's headline crop. Shipping this gate as-is would trade an area-inflation problem for a canola-undercount problem — a different failure mode, not a smaller one.

## Next step

The gate as built uses ONE shared threshold across all crops, fit before classification runs (so it cannot know which crop it is looking at). Two ways to fix the canola gap without giving up the area-ratio win:
1. **A looser `senescence_drop` threshold specifically**, since that is the feature canola trails on — costs some of the amplitude-gate's fixed excess-land rejection back, needs re-measuring both numbers again.
2. **Two-pass gating**: run the cheap amplitude gate first (already 94.5% recall on canola), classify, then apply the shape gate only to non-canola predictions — canola is the class experience says the amplitude gate was already least wrong on (`PRESENCE_ONLY_LABELS.md` never singled it out as a problem), and this would stop a canola-specific fix from having to fight cereal/legume's stricter needs.
Not attempted here — this report's job was to measure honestly, not to keep tuning until a number looked good.
