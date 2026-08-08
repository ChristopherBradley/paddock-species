# Can SAM parameters auto-fix the flagged polygons?

**No. Denser prompt sampling does not fix them, and adopting it would cost ~20 % of the
project's compute allocation to gain nothing measurable.** Recorded so this is not retried.

Tested because 624 polygons were queued for manual review — more than the user wants to hand-
label — and the dominant failure modes look like under-segmentation, which is exactly what
SAM's prompt density controls. Production ran with `sam_kwargs=None`, i.e. a 32-point grid
over a ~3 km tile.

## Setup

Three settings on the 23 AOIs holding all 37 hand-judged polygons (18 bad, 19 good), stage 2
only — the Fourier-NDWI composites already existed, so no datacube reads. GPU, 21 min total.

`pps32` is the **control**: it re-runs production settings, so any difference is attributable
to the parameter rather than to SAM nondeterminism or library drift since the original run.

## Result

| setting | bad FIXED | good KEPT | median polys/AOI | net /37 |
|---|---|---|---|---|
| `pps32` (control) | 2/18 (11 %) | 14/19 (74 %) | 14 | 16 |
| `pps64` | 5/18 (28 %) | 12/19 (63 %) | 17 | **17** |
| `pps64_crop1` | 4/18 (22 %) | 13/19 (68 %) | 24 | **17** |

A bad polygon counts as fixed when the trial point lands inside a plausible paddock (2-300 ha,
compactness <= 8). A good one counts as kept when it still overlaps what the user approved
(IoU >= 0.5) — no quality proxy is re-applied to a polygon the user already passed, since the
only question is whether the new setting *changed* it.

**The net is flat: 16 -> 17 -> 17 out of 37.** Every polygon `pps64` fixes, it pays for by
breaking one the user had approved.

## Why it fails, by failure mode

| mode | judged | pps32 | pps64 | pps64_crop1 | in the queue |
|---|---|---|---|---|---|
| whole region / multiple paddocks | 9 | 0 | 1 | 0 | **222** |
| trial site only | 4 | 0 | 0 | 0 | 52 |
| wrong paddock | 3 | 0 | 2 | 2 | (within 192) |
| overlapping paddock | 2 | 2 | 2 | 2 | 207 |

**The mode that dominates the queue is the one that does not respond.** The nine "whole
region" polygons stay enormous: median 565 ha at pps32, 498 ha at pps64. Doubling the prompt
grid barely dents a 500 ha blob, because the merge is not caused by too few prompts — those
fields genuinely share a wetness trajectory in the Fourier-NDWI composite, so SAM sees one
object however densely it is asked.

`pps64_crop1` is worse than it looks in the summary. On six of the nine whole-region AOIs it
produced **no usable polygon at all**, and the survivors collapsed to ~2 ha slivers (median
2.27 ha, from 565 ha). It shatters those tiles rather than segmenting them.

"Trial site only" is 0/4 everywhere, which is expected on reflection: denser sampling cannot
invent a surrounding paddock that the composite never separated.

## Cost, which settles it

`pps64` measured **~9x slower** than `pps32` (26 s/AOI against 2.8 s). Re-segmenting all 2,382
AOIs would cost roughly **1,994 SU — about 20 % of the 10 KSU project earmark** — for a net
change of one polygon in 37. Not worth doing, and not close.

## What DOES reduce the review burden

Since SAM cannot fix the >300 ha polygons and **all 9 judged ones were bad**, they should be
**auto-rejected rather than reviewed**:

| | polygons in queue | trials kept |
|---|---|---|
| review everything flagged | 624 | 3,222 |
| auto-reject `too_big`, review the rest | **425** (-32 %) | 2,955 (-267, -8.3 %) |

199 of the 222 are flagged for `too_big` and nothing else, so rejecting them removes a third
of the queue outright. The 267 discarded trials are 189 Cereal, 44 Canola, 34 Legume — and
they were carrying wrong features anyway, so dropping them should be neutral-to-positive for
the model rather than a loss.

**Confirm before committing to it.** The 9/9 evidence is nine polygons. Review ~30 of the 222
first; if the pattern holds, reject the remainder unseen. That is the same
sample-then-generalise move that the 150-polygon validation batch justified for the unflagged
pile, and it costs an hour rather than a day.

## Caveats

- 18 bad and 19 good is a small calibration set; differences of 2-3 polygons are within noise,
  which is itself the point — no setting produced an effect large enough to see at this size.
- Only prompt density was swept. `pred_iou_thresh` and `stability_score_thresh` were left at
  defaults, so this rules out the *most likely* fix rather than the whole parameter space.
- The control's "good kept" is 74 %, not 100 %, because the scorer picks the tightest
  containing polygon while production used the upgrade-aware matcher. That depresses all three
  columns equally, so the comparison holds even though the absolute numbers are pessimistic.
