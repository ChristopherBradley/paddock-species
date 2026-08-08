> **SUPERSEDED IN TWO PLACES, 2026-08-08.** Read `LABEL_QUALITY.md` and `MODEL_UNCERTAINTY.md`
> before acting on this document.
>
> 1. **Section 1's "not mainly a data-quality problem" is wrong as stated.** It tested only
>    per-trial drivers and so could not see the real defect, which is *between* trials:
>    31.8 % of training trials share their paddock polygon with a different-crop trial in the
>    same year, and canola on such a polygon reads 482 CFI lower [+348, +551]. The signal
>    damage is real. (Dropping those trials does not measurably improve the model, though —
>    see `LABEL_QUALITY.md`.)
> 2. **Section 2's bands-vs-indices conclusion is over-read.** The macro-F1 gap it rests on is
>    -0.015 [-0.058, +0.027], i.e. noise. The canola-specific loss is real (-11.0 pp
>    [-16.1, -1.0]) and does support the CFI-nonlinearity explanation.
>
> The headline canola result survives: +33.0 pp [+18.5, +47.0] over a per-season CFI threshold.

# Where the project stands, and what to do next

Written 2026-08-07 overnight, answering two questions: is the panel-to-panel separability
swing a data-quality problem, and are we ready to train a species model for a 10 m map.

Companion reports: `SEPARABILITY_DIAGNOSIS.md`, `SPECIES_MODEL_indices.md`,
`SPECIES_MODEL_bands.md`, `CROP_HEATMAPS.md`.

---

## 1. The separability swing is NOT mainly a data-quality problem

Measured on 32 year x state panels, separability = AUC of max CFI in DOY 200-300, canola vs
all other crops. Range **0.51 to 0.99**, sd 0.129.

- **Sampling noise alone explains ~24 % of the variance** (resampling the pooled distribution
  at each panel's n gives sd 0.064). So ~76 % is a real panel effect — the swing is not just
  small-n jitter, and your instinct that something systematic is going on is right.
- **The only driver whose 95 % CI excludes zero is season vigour** — median NDVI amplitude,
  r = +0.41 [+0.03, +0.73]. Panels where the crop grew well separate well. That is an
  agronomic effect, not a measurement one, and it matches the literature note that canola
  separability is drought-sensitive.
- **Every data-quality candidate came back indistinguishable from zero:** max cloud gap in
  the flowering window (+0.10), fraction of trials with a >21 d gap (+0.09), fraction matched
  by `contains` (+0.28), paddock size (-0.09), compactness (+0.04). None excludes zero.

Read that as *no evidence for* the data-quality explanation rather than *evidence against* it:
32 panels is an underpowered sample, and a real effect of r ~ 0.3 would not be detectable
here. But the ranking is clear enough to act on — **more/cleaner observations is not the
lever.** The lever is a model that can use a weak season's other signals, which is where
the next section goes.

One counterintuitive result worth not over-reading: median flowering-window observation count
correlates *negatively* with separability (-0.22, CI spans zero). That is almost certainly
confounded — revisit density rose with S2C over exactly the years, regions and cloudiness that
also changed — not evidence that more observations hurt.

## 2. Are we ready to train a species model? Partly — and the answer splits by crop

I built the classifier and ran it, rather than estimating. Paddock-median time series,
features = each band binned to 20-day calendar DOY windows plus derived indices and
whole-season shape, histogram gradient boosting, class-balanced, **geography excluded**
(lat/lon/year would let the model learn that chickpea is a Queensland crop rather than what
chickpea looks like).

Two honest splits, both reported:
- **temporal** — train <=2022, test 2023-24
- **spatial** — 5-fold GroupKFold **on site**, so no location appears in train and test. This
  matters more than it sounds: the same paddock recurs across years, and a random split would
  let the model memorise locations and report a fantasy score.

### Result: canola is close to solved; the other species are not

From 3 indices alone (2,477 paddocks), temporal transfer:

| | macro F1 | balanced acc |
|---|---|---|
| 3 indices | 0.316 | 0.329 |
| chance | 0.111 | 0.111 |

But the macro number hides the shape of it:

| crop | F1 | note |
|---|---|---|
| **Canola** | **0.81** | precision 0.85, recall 0.77 |
| Wheat | 0.68 | recall 0.81 but precision 0.59 — everything else falls into wheat |
| Chickpea | 0.33 | |
| Lupin / Field Pea / Faba Bean / Barley | 0.22-0.27 | |
| Lentil | 0.07 | |
| Oat | 0.00 | never predicted |

**The single most useful number tonight: canola detected at a 5 % false-positive budget goes
from 45.7 % (CFI threshold, three-group) to 77.0 % (model, same three indices).** A
multivariate model over the whole seasonal shape is worth **+31 pp** over thresholding one
index at one time. That is a strong signal that the modelling direction is right, and it was
obtained without adding a single new band.

### Do the extra bands help? On the full data: NOT on their own

I extracted all 10 Sentinel-2 bands as paddock medians for every trial (91 jobs, ~38 CPU-hours
— this had never been done; only 3 indices were ever stored, so no multi-band model was
possible before tonight). Full-data result, same quality-filtered trials, same splits:

| | 3 indices (n=2,477) | 10 bands (n=2,399) |
|---|---|---|
| temporal macro F1 | **0.316** | 0.301 |
| spatial macro F1 | 0.273 | **0.304** |
| canola F1 (temporal) | **0.81** | 0.74 |
| canola @ 5 % FPR | **77.0 %** | 62.9 % |

**Correction to an earlier read in this session.** A preliminary run on 57 % of the data
showed large minor-crop gains (lupin 0.27 -> 0.48, lentil 0.07 -> 0.25) and I wrote that the
evidence favoured bands. **On the full data those gains vanished** — lentil went to 0.00 and
lupin to 0.14, i.e. *worse* than the 3-index baseline. The partial-run gains were sample-size
artefacts, exactly the caveat attached to them at the time. Ten bands alone do not beat three
indices here, except on spatial transfer.

**The likely reason, and it is a fixable methodology bug rather than a fact about bands.**
CFI is non-linear in reflectance. The index files store the median of *per-pixel* CFI; a band
file can only reconstruct CFI from the *median reflectance*, and those are not the same
quantity. So the band model's CFI-equivalent is a degraded version of the one the index model
gets for free — which fits the observation that the band model's biggest loss is precisely on
canola, the class CFI carries.

That predicts the two feature sets are complementary rather than competing, so a combined run
(`SPECIES_MODEL_combined.md`, 325 features) is fitting now. **Read that before concluding
anything about bands.** If combined beats both, the answer is "bands help, but only alongside
properly-computed indices"; if it matches the 3-index model, the extra bands genuinely add
little at paddock-median resolution and the next lever is Sentinel-1, not more optical bands.

**Either way, don't give up on wheat-vs-other yet.** Two things are still untested and both
are cheap: (a) per-pixel indices computed *before* aggregation for the full band set, and
(b) the 274-feature model is probably overfitting 2,399 samples across 9 imbalanced classes —
note that bands won on *spatial* transfer, which is the split less sensitive to that.

## 3. Recommended next steps, in order

1. **Read `SPECIES_MODEL_bands.md` first.** If full-data bands beat 0.316/0.273 macro F1 and
   lift barley/oat, the feature story is settled and Presto becomes worth the effort. If they
   only lift the pulses, the cereal problem needs something else (Sentinel-1 backscatter is
   the obvious candidate — it separates cereals by structure, and the MDB study found it
   useful).
2. **Fix the class imbalance properly before chasing architecture.** Oat scores 0.00 with 112
   samples against wheat's 835. Class-balanced weights are not enough. Worth trying before
   any deep model, because it is free.
3. **Then Presto.** The case for it is now concrete rather than aspirational: we have 3,439
   labelled paddock time series across 9 crops with all 10 bands, which is exactly its input
   format. Fine-tune rather than train from scratch given the sample size.
4. **A canola-only 10 m map is already defensible** and is the fastest publishable output —
   0.81 F1 with honest spatial CV, on GRDC ground truth rather than model-derived labels,
   which is the edge over both Australian papers in the lit review. Do not wait for the
   9-class model to work before shipping this.
5. **Do not use the year x state panel structure as a QC signal.** Per section 1, weak panels
   are mostly weak seasons, so dropping them would discard real agronomic variation and
   optimistically bias any accuracy estimate.

## 4. State of the data

| artefact | location | scale |
|---|---|---|
| paddock-median 3 indices | `derived/samgeo/ts_v2/` | 3,439 trials, 9 crops |
| **paddock-median 10 bands** | `derived/samgeo/bands_ts/` | 3,304+ trials (a few jobs outstanding) |
| quality-filtered trial list | `derived/figures/crop_heatmaps/cfi_heatmap_ALL_rows_SENSITIVE.csv` | 2,477 |
| heatmaps + GeoPackages | `derived/figures/crop_heatmaps/` | 40 panels |

A handful of band-extraction jobs were still running at write-up. `extract_paddock.py` resumes
by skipping TrialCodes already present, so re-running the same `qsub` lines tops up the gaps
without redoing finished work. Total spend tonight ~200 SU (~2 % of the project earmark).

## 5. When you wake up — exact commands

The band model was still fitting when the window closed. It runs under `nohup` on the login
node, so it survives the session; check it first:

```bash
cat output/SPECIES_MODEL_bands.md          # written when it finishes
```

It was trained on the 2,399 trials available at launch. Once the last extraction jobs land
(check `qstat -u cb8590`), re-run it on the complete set — same command, ~10 min:

```bash
cd src/paddocks
D=/scratch/xe2/cb8590/paddock-species-data/derived
/g/data/xe2/John/geospatenv/bin/python train_species.py \
    --bands "$D/samgeo/bands_ts/*_SENSITIVE.csv" \
    --labeled $D/nvt_trials_labeled.csv \
    --keep $D/figures/crop_heatmaps/cfi_heatmap_ALL_rows_SENSITIVE.csv \
    --out ../../output/SPECIES_MODEL_bands.md
```

Useful variants, both one-flag changes:

```bash
--with-geo          # adds lat/lon/year: the map-product number, NOT evidence about imagery
--model rf          # random forest instead of gradient boosting, as a robustness check
```

To top up any missing band extractions (safe to re-run; finished trials are skipped):

```bash
for f in $D/samgeo/bands_ts/chunks/A_*.csv $D/samgeo/bands_ts/chunks/AR_*.csv; do
    qsub -v SITES=$f,POLYDIR=$D/samgeo/full,\
OUT=$D/samgeo/bands_ts/$(basename $f .csv)_SENSITIVE.csv,EXTRA_ARGS=--all-bands \
        extract_paddock.pbs
done
```
(and the same with `B_*.csv` against `POLYDIR=$D/samgeo/other`).
