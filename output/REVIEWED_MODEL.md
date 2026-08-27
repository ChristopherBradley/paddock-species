# What the paddock review bought the model

Run 2026-08-08 by `src/paddocks/train_group3_reviewed.pbs` and `train_canola.pbs`.
Per-arm reports in `output/arms/`.

## The comparison had to be built three times, and the first two were wrong

Worth recording, because both wrong versions produced a *large* and entirely spurious gain.

1. **Each arm scored on its own rows.** The reviewed arm was evaluated on reviewed-good test
   labels while the baseline was evaluated on its dirtier ones. Reviewed appeared to score
   **0.823 against 0.716 — a +0.107 gain that was mostly a cleaner exam**, not a better model.
2. **A fixed test set that not every arm could reach.** Restricting scoring to the reviewed
   rows still let the reviewed arm score 2,301 rows and the baseline 1,929, because an arm can
   only score rows its own `--keep` contains.
3. **Correct.** Every arm's keep now *contains* the same 543 test rows (2023-24, reviewed-good,
   present in both keeps). Only the ≤2022 training rows differ. The exam is identical.

*A cleaned test set is not evidence that cleaning helps — it is evidence that the exam got
easier. Hold the test rows fixed, or the number measures the wrong thing.*

## Result: three groups, temporal transfer, 543 fixed test rows

| arm | training rows | macro F1 | canola @ 5 % FPR | AP |
|---|---|---|---|---|
| baseline (geometric filter) | 1,818 | 0.789 | 83.2 % | 0.920 |
| size-matched control, seed 0 | 1,651 | 0.798 | 84.5 % | 0.924 |
| size-matched control, seed 1 | 1,651 | 0.795 | 85.8 % | 0.926 |
| size-matched control, seed 2 | 1,651 | 0.814 | 81.3 % | 0.921 |
| **reviewed** | 1,651 | **0.821** | **89.0 %** | **0.944** |
| Presto embeddings only | 1,651 | 0.775 | 74.2 % | 0.862 |
| indices + Presto | 1,651 | 0.824 | 85.8 % | 0.929 |

Controls: mean **0.802**, sd 0.010. So **reviewed − control = +0.019, about 2 control sd.**

**This is a modest gain, not a transformation.** It sits close to the +0.03-0.04 that
`NEXT_STEPS.md` guessed from the co-location experiment, and it finally has a properly
controlled number behind it. Do not quote +0.10; that was the confounded version.

Per class (temporal), reviewed against baseline:

| group | F1 reviewed | F1 baseline | n |
|---|---|---|---|
| Cereal | 0.90 | 0.88 | 279 |
| Canola | **0.88** | 0.84 | 155 |
| Legume | 0.69 | 0.65 | 109 |

Legume is still the floor at 0.69 with precision 0.65 — cereals continue to leak into it, and
the review did not fix that. It remains the largest piece of headroom.

## Spatial transfer disagrees, and that matters

Scored on the same 543 rows, GroupKFold on site:

| arm | spatial macro F1 |
|---|---|
| reviewed | 0.823 |
| controls | 0.836 / 0.839 / 0.826 (mean 0.834) |
| baseline | 0.832 |

**The reviewed arm is slightly *worse* spatially** — about 1.6 control sd below. So the review's
benefit appears on temporal transfer and on canola detection, and does not appear when
generalising across sites. On one run at this sample size neither direction is decisive, and
the honest reading is that **cleaning the polygons helps canola detection clearly, helps
temporal transfer modestly, and does nothing demonstrable for spatial transfer.**

Note the baseline arm's pool is larger (2,361 vs 2,194), so baseline-vs-reviewed is not
size-controlled for the spatial number; reviewed-vs-control is, and is the pair to trust.

## The canola map (next-step 6)

Binary Canola vs Other — everything else, not wheat — on the same 543 fixed test rows:

| arm | macro F1 | canola @ 5 % FPR | AP (prevalence 0.285) |
|---|---|---|---|
| baseline | 0.915 | 87.1 % | 0.911 |
| **reviewed** | **0.928** | **89.0 %** | **0.947** |

| class | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.95 | 0.85 | 0.89 | 155 |
| Other | 0.94 | 0.98 | 0.96 | 388 |

**89.0 % of canola paddocks detected at a 5 % false-positive rate**, against the per-season CFI
threshold's 45.7 % on the same three-way negative class. That is the publishable result, and it
is now on hand-reviewed GRDC ground truth with an honest temporal split.

## Presto: a clean negative, with a named cause (next-step 5)

`src/paddocks/presto_embed.py`, pretrained `default_model.pt`, 2,333 paddocks → 128-dim
embeddings, run through the identical splits, model and metrics.

- **Presto alone scores 0.775 against 0.821 for 51 hand-built features** — worse, and much
  worse on canola detection (74.2 % vs 89.0 %).
- **Presto added to the hand-built features gives 0.824 against 0.821** — inside the control
  noise, i.e. nothing.

**The most likely cause is named and testable: 3 of Presto's 9 channel groups are missing.**
It expects S1 (VV/VH), ERA5 and SRTM alongside S2, and this project can supply only S2 and
NDVI. Those groups are passed as *masked* rather than zero-filled, which is the case Presto was
pre-trained to handle, but a third of its inputs are still absent. **Do not conclude that Presto
does not work here** — conclude that Presto without S1 does not beat CFI features, and that
getting S1 tests both propositions at once.

One further constraint worth recording: Presto's encoder asserts every sample in a batch has
the same number of masked tokens, so per-trial cloud gaps *cannot* be expressed through its
mask. They are linearly interpolated across the 12 monthly steps instead, and the mask is
reserved for the three uniformly-absent groups. Median months observed: 9 of 12.
