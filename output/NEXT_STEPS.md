# Where the project stands, and what to do next

Rewritten 2026-08-08, replacing the overnight version. Two decisions changed the shape of the
project since then: the target is now **three groups, not nine species**, and the **paddock
polygons are being reviewed by hand** before anything is published.

Companion reports: `GROUP3_MODEL.md`, `LABEL_QUALITY.md`, `MODEL_UNCERTAINTY.md`,
`CANOLA_PSEUDO_LABELS.md`, `CROP_HEATMAPS.md`, `SEPARABILITY_DIAGNOSIS.md`.

---

## 1. The target is Canola / Cereal / Legume

Species-level never worked and the confusion matrix (`figures/confusion_species.png`) shows
why: the errors are almost entirely *within* the proposed groups. Barley→Wheat 60 against 15
correct, Oat→Wheat 19 against 0 correct, chickpea and lentil both collapsing into field pea.
Canola is the only species that stands clear. Collapsing therefore merges the distinctions the
model was never making, rather than discarding ones it had.

It is also better-posed, not merely easier. Co-located NVT trials are usually of the same
agronomic group — pulse trials sit together, cereal trials sit together — so the collapse
**resolves 540 of the 788 same-polygon label conflicts (69 %)** described in section 3.

### Result (`GROUP3_MODEL.md`, 3 indices, 2,477 paddocks)

| split | macro F1 | balanced accuracy |
|---|---|---|
| temporal (train <=2022, test 2023-24) | **0.716** | 0.719 |
| spatial (GroupKFold on site) | **0.707** | 0.698 |

chance = 0.333.

| group | F1 (temporal) | F1 (spatial) | note |
|---|---|---|---|
| Cereal | 0.82 | 0.82 | |
| Canola | 0.76 | 0.73 | precision 0.84, recall 0.69 |
| Legume | 0.57 | 0.57 | precision 0.51 — cereals leak into it |

**Spatial and temporal transfer are now nearly equal (0.707 vs 0.716).** At species level they
were 0.273 vs 0.316, a much larger gap. Generalising over the fence was the harder test and the
grouped model has largely closed it, which is the single most encouraging number here.

**Correction to a figure quoted earlier in conversation.** `LABEL_QUALITY.md` reports 0.78-0.82
for the 3-group task; that was measured on the CLEAN test subset (323 trials with no
co-location and no polygon conflict), which is both smaller and easier. On the full 659-trial
test set the honest number is **0.716**. Quote 0.716; the clean-subset figure is only valid
alongside its restriction, and that subset is also 41.8 % canola against 14.1 % in the rest.

CFI dominates the signal (permutation importance +0.049, against NDVI +0.018 and NDYI
negative), and its most useful forms are the season amplitude and the DOY 230-270 bins — the
flowering window this project established in Stage 2.

## 2. What is settled, with intervals

From `MODEL_UNCERTAINTY.md` (paired bootstrap, 2,000 resamples). These supersede the overnight
point estimates:

- **Modelling beats thresholding, decisively**: canola at 5 % FPR, model minus per-season CFI
  threshold = **+33.0 pp [+18.5, +47.0]**.
- **Bands vs indices on macro F1 is NOISE**: -0.015 [-0.058, +0.027]. The overnight conclusion
  that "ten bands do not beat three indices" was over-read on this metric and should not be
  quoted.
- **But the canola-specific loss is real**: -11.0 pp [-16.1, -1.0], which supports the
  CFI-nonlinearity explanation — a band file can only reconstruct CFI from median reflectance,
  and CFI is non-linear.
- **Combined features help spatial transfer**: +0.027 [+0.005, +0.050].
- The fits are deterministic across seeds, so no difference between runs is re-fit jitter.

## 3. The critical path is the paddock review, not the model

**This is the blocking item.** NVT runs several crop trials side by side in one field; SAM
segments that field as one polygon; every trial there gets an identical time series under a
different label. 69.7 % of trials share their polygon with another trial, **31.8 % with a
different crop**. Measured within canola alone, so no class-mix confound: canola on a shared
polygon reads median CFI **1489 against 1971** unshared, a gap of **+482 [+348, +551]**.

Whether cleaning it helps the model is **not established**: against a size-matched random
control, dropping co-located trials gives +0.027 [-0.052, +0.101] on 9 classes and +0.042
[-0.004, +0.089] on 3 groups. All arms point the same way and the best barely misses zero, so
the benefit is probably real at around +0.03-0.04 — but 323 clean test trials cannot confirm
it. **Do not claim the cleaning fixes the model.**

### Review workflow (in progress)

`PADDOCK_REVIEW_SENSITIVE.gpkg` — **1,973 distinct polygons**, not 3,222 trials, because the
same paddock recurs across seasons (39 % less work). Layers `review` (polygons, editable
`verdict`), `trials` (points, carrying the verdict for zoomed-out viewing), `manual_polygons`
(digitise replacements here).

Triage, calibrated on 36 hand-judged polygons, catches **17/17 bad at 2/19 false-flagged** —
but only because the three failure modes each need a *different* signal:

| mode | signal | flagged |
|---|---|---|
| wrong paddock / trial site only | trial point >25 m outside its polygon | 192 |
| whole region / multiple paddocks | area >300 ha | 222 |
| overlapping paddock | different crop shares the polygon | 207 |

**That 17/17 is in-sample** (three thresholds fitted to 36 points), which is why 150 unflagged
polygons are sampled as `review_batch = validation`. Review those too — otherwise the 1,199
"presumed OK" is an assumption with no evidence behind it.

**Methodological trap recorded, because it cost a wrong conclusion.** A first pass declared
that no geometric rule could reproduce the verdicts, citing two polygons 0.1 ha apart at one
site with opposite verdicts. That was wrong: only area and compactness had been tested, and
the pair is separated cleanly by containment (0 m vs 137 m). The confusion came from
`match_rule` reading `contains+upgraded_...`, where "contains" describes the polygon the point
fell in *before* the upgrade moved the match. **All 259 upgraded matches have their trial point
outside the polygon they ended up with**, and the upgrade searches to 150 m — far enough to
cross a road into the next field. *"No rule can separate these" is only ever a statement about
the features tried.*

## 4. Recommended next steps, in order

1. **Finish the review**, flagged and validation batches first. Everything downstream inherits
   these labels, and the paper cannot claim GRDC ground truth while a third of the polygons are
   contested. Re-run `build_review_package.py refresh` to push verdicts onto the points.
2. **Re-run the 3-group model on the reviewed set** and compare against 0.716/0.707. With clean
   labels the co-location experiment can finally be answered rather than left at "probably
   +0.03-0.04".
3. **Attack the Legume class** — F1 0.57, precision 0.51, i.e. cereals leak into it. This is
   where the remaining headroom is; canola and cereal are both above 0.73.
4. **Sentinel-1 backscatter** as the next feature, not more optical bands. It separates by
   canopy structure, so it fails on different paddocks than CFI does — unlike the extra optical
   bands, whose gains were indistinguishable from noise.
5. **Then Presto.** Self-supervised pre-training is also the right way to use unlabelled
   paddocks; thresholded pseudo-labels are not (`CANOLA_PSEUDO_LABELS.md`).
6. **A canola-only 10 m map remains the fastest publishable output** — 0.76 F1 with honest
   spatial CV on GRDC ground truth, against the two Australian papers' model-derived labels.

## 5. Exact commands

```bash
cd src/paddocks
D=/scratch/xe2/cb8590/paddock-species-data/derived
PY=/g/data/xe2/John/geospatenv/bin/python

# push review verdicts onto the points layer (safe, never touches `review`)
$PY build_review_package.py refresh --out $D/figures/crop_heatmaps/PADDOCK_REVIEW_SENSITIVE.gpkg

# turn verdicts into a training filter once enough are judged
$PY build_review_package.py ingest --out $D/figures/crop_heatmaps/PADDOCK_REVIEW_SENSITIVE.gpkg \
    --trials-out $D/reviewed_trials_SENSITIVE.csv

# retrain (qsub, NOT the login node — see below)
qsub train_group3.pbs
```

**Never run the model scripts on a login node.** They are killed with no traceback, no
"Killed", the log simply stops — read a silent disappearance as an external kill, not a bug.
And size the job for `permutation_importance`, which dominates runtime and used to scale
silently with ambient core count: the same run took ~10 min on a login node, over 90 min
unfinished on 4 CPUs, and **75 seconds on 12 CPUs** with `--importance-repeats 5`.

## 6. State of the data

| artefact | location | scale |
|---|---|---|
| paddock-median 3 indices | `derived/samgeo/ts_v2/` | 3,439 trials, 9 crops |
| paddock-median 10 bands | `derived/samgeo/bands_ts/` | 3,304+ trials |
| review package | `derived/figures/crop_heatmaps/PADDOCK_REVIEW_SENSITIVE.gpkg` | 1,973 polygons |
| NDWI composites by TrialCode | `derived/samgeo/by_trial/<TrialCode>_ndwi.tif` | 4,191 symlinks |
| conflict flags | `derived/paddock_conflicts_SENSITIVE.csv` | 2,477 trials |
| seed verdicts | `derived/seed_verdicts_SENSITIVE.csv` | 36 judged |
