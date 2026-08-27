# The negative class is not a negative class, and what to do instead

Written 2026-08-25, after `NEXT_STEPS.md` §0 exonerated polygon geometry as the cause of the
39.4 % "known crops called Grazing" problem, and in response to the observation that **AgriWebb
records are presence-only**: a paddock with no sowing record was not necessarily not sown, it
may simply not have been recorded. Many "grazing" paddocks were plausibly sown to a crop and
then grazed rather than harvested.

> **The measurement below supports that reading, and it is the best explanation left standing.**
> 78.5 % of the "hard stratum" AgriWebb grazing paddocks — the ones inside the NLUM cropping mask,
> the ones that matter — show a seasonal green-up as strong as a known sown crop. The Grazing
> class has been trained on paddocks that substantially look like crops, so it absorbs crop
> phenology, and then pulls genuine crops into itself at test time. That is the 39.4 %.

---

## 1. The grazing negatives pass a crop-presence test

Gate: NDVI amplitude (p90 − p10 of the paddock-median series) ≥ 0.35 — the crop-presence
operating point fitted in Stage 2 on **presence labels only** (`memory/MEMORY.md`, held-out
J = 0.535). Paddock-years with ≥ 10 clear observations, farmer-drawn geometry (`ts_idx`), so
nothing here is contaminated by the SAM blob problem.

| group | n | median NDVI amplitude | passes the crop gate |
|---|---|---|---|
| NVT crop trials (known sown) | 3,439 | 0.639 | **91.6 %** |
| AgriWebb crop events (holdout, known sown) | 104 | 0.611 | **98.1 %** |
| **AgriWebb grazing, `hard` stratum** | 489 | **0.465** | **78.5 %** |
| AgriWebb grazing, `easy` stratum (rangeland) | 403 | 0.404 | 64.0 % |

The `easy`/`hard` split behaves exactly as it should — rangeland is least crop-like — which is a
sanity check on the gate itself. But **the hard stratum, which is the whole point of the negative
class, is only 13 points below known crops.**

**`grazing_confidence` does not rescue it.** The tier measures how much dated history backs the
Grazing state (`high` = ≥ 365 days of history and modified since 2022, all snapshots Grazing).
If it identified genuinely-never-cropped paddocks, `high` would pass the crop gate far less often.
It does not:

| tier | n | passes the crop gate |
|---|---|---|
| high | 435 | 69.2 % |
| medium | 77 | 70.1 % |
| low | 380 | 75.5 % |

A 6-point spread across a tier that spans "one undated snapshot" to "a year of confirmed
history". **AgriWebb's `PASTURE_STATE` is a current-state field, not an event log** — a paddock
sown to a crop and later grazed can sit in it as "Grazing" indefinitely, and more history does
not fix that.

**The honest caveat.** A strong NDVI amplitude does not prove a crop was sown. Improved annual
pasture — ryegrass, clover — greens up and senesces hard too, and this gate cannot separate that
from a sown crop that was grazed instead of harvested. So the correct conclusion is the weaker
one, and it is enough: **the negative class is not cleanly separable from crops on phenology, and
it was never a reliable "not-crop" label.** Whether the cause is unrecorded cropping or improved
pasture changes the remedy not at all.

## 2. SAM segmentability is a real, free, non-spectral crop signal

The §0 finding — SAM under-segments grazing land — is not only an obstacle. Measured as a
detector, with **no spectral information at all**, purely "did this point land inside a SAM
polygon of ≤ 300 ha":

| group | flagged as crop |
|---|---|
| AgriWebb crop paddocks (known sown) | **77.9 %** (81/104) |
| grazing, `hard` stratum | 34.9 % (173/495) |
| grazing, `easy` stratum | ~21 % |

Blob rate among matched rows, for the same reason, read the other way:

| group | matched polygon > 300 ha | median matched area |
|---|---|---|
| grazing `easy` | 78.8 % | 991.6 ha |
| grazing `hard` | 50.3 % | 388.8 ha |
| AgriWebb crops | **5.8 %** | **27.3 ha** |

This is orthogonal to phenology — it is about whether the ground has field boundaries — and it
costs nothing, because the segmentation has to run anyway to produce the polygons the map is
built on. **It is not free of error: as a mask it discards 22 % of known crop paddocks.** That is
the price, and it should be quoted with any coverage figure.

## 3. What follows for the national map

**Stop making the absence claim.** Every problem in `NEXT_STEPS.md` §0 traces back to a 4-class
softmax that must assign *something* to every polygon, trained on a negative class that presence-
only records cannot support.

1. **Segmentability becomes a mask, not a class.** Classify only SAM polygons that resolve to
   paddock scale (≤ 300 ha, plus the existing compactness filter). Ground SAM cannot resolve is
   left off the map rather than labelled.
2. **Drop Grazing from the classifier and gate on crop *presence* instead.** The 3-class crop
   model is the well-validated part of this project (macro F1 0.821 / 0.823, reproduced in two
   independent runs). Put the Stage-2 phenology gate in front of it — it was fitted on presence
   labels and needs no negative class — and leave paddocks that fail it blank. A blank paddock
   says "no crop signature detected here", which is a claim the data supports; "Grazing" is a
   claim it does not.
3. **Validate on aggregate area statistics, not on a negative class.** ABS/ABARES publish sown
   area by commodity, region and year. If mapped canola area by SA4 tracks the published series
   across 2020–2024, the mask and the classifier are both working — and that argument needs no
   absence labels at all. It is also the evidence a reviewer will ask for, and the data is free
   and public. Rotation plausibility (`WALL_TO_WALL_MAPS.md`) is the second leg; the presence
   recall of the mask on NVT + AgriWebb sowing records is the third.

### The abstain path, implemented and smoke-tested (2026-08-25)

`predict_tile.py` now takes `--max-area-ha` and `--crop-gate-amp`. Every polygon reaches the
output carrying an `abstain_reason`, because **white space that cannot be attributed to a cause
is indistinguishable from ground with no crop on it** — which is the confusion this whole reframe
exists to remove. Class probabilities are still written for abstained polygons, so the gate can be
audited rather than taken on trust.

Tested on 16 demo tiles (Riverina 2022, 346 polygons, 1.06 SU):

| | |
|---|---|
| **classified** | **266 of 346 (76.9 %), 88.3 % by area** |
| `area_below_min` | 42 |
| `no_crop_signal` | 35 |
| `too_few_observations` | 2 |
| `unsegmented_blob` | 1 |

Only one blob in sixteen tiles, which is the expected result in cropping country and the mirror
image of the grazing-land finding above — the mask costs almost nothing where SAM works, and does
its work where SAM does not.

**What this costs.** The Grazing F1 0.94 headline goes away — it was measuring something the
labels cannot support. What replaces it is a crop map with an explicit, quantified coverage
figure and an aggregate-area validation against an independent official source. That is a weaker
claim and a much better defended one.

**What it does not change.** The national compute case (`NATIONAL_INFERENCE_BENCHMARK_V2.md`,
5,497 SU) is unaffected — the same tiles get segmented and the same polygons get classified. If
anything the mask reduces the classification load.
