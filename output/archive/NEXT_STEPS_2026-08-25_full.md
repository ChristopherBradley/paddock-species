# Where the project stands, and what to do next

Rewritten 2026-08-25 after an overnight run that added the fourth class, built the inference
stage, produced the first wall-to-wall maps, and measured the national bill end to end.
Updated 2026-08-25 (morning): the provenance fix of §6.1 has now RUN, and moved the headline
number by 2.3 points instead of the sharp fall it predicted — §0.

> **The one-paragraph version.** The national-map blocker from `NONCROP_CLASS.md` is closed on
> the test set: with AgriWebb's dated grazing records as a fourth class the model reaches
> **Grazing F1 0.94 temporal / 0.97 spatial**, costing the crop classes 0.026 macro F1 and
> leaving canola-at-5%-FPR untouched at 89.0 %. The inference stage now exists
> (`predict_tile.py`) and has produced **3,709 classified paddocks across 3 regions x 5 years**,
> which show plausible crop rotation. A national single-year run of all three crop groups is
> measured at **5,497 SU and ~14 h wall** — 2.3x cheaper than the previous estimate. **But** the
> Grazing class is partly keyed on *polygon provenance* rather than land use, and the size of
> that artefact is large: 39.4 % of known-cropped AgriWebb paddocks are called Grazing against
> 1.3 % of NVT ones. **That fix has now been run and it did not work** — 36.0 % to 33.7 % on
> identical rows — so the mechanism is probably not polygon provenance. See §0.

**Read in this order:** `PRESENCE_ONLY_LABELS.md` (why the negative class does not work, and
what replaces it — **start here**) → `GRAZING_CLASS.md` (the model and the confound) →
`WALL_TO_WALL_MAPS.md` (the maps) → `NATIONAL_INFERENCE_BENCHMARK_V2.md` (the bill) →
`TREECOVER_CALIBRATION.md`, `HOLDOUT_AGRIWEBB.md` (supporting).
`SENTINEL1_ACCESS.md` covers the S1-on-NCI question: dz56 is the wrong project to ask for, fj7
is the right one, and DEA has no SAR product at all.

Earlier reports still current: `S1_MODEL.md`, `REVIEWED_MODEL.md`, `YIELD_MODEL.md`,
`CANOLA_FLOWERING_AUDIT.md`, `AGRIWEBB_TRAINING_CANDIDATES.md`, `TILE_SIZE_BENCHMARK.md`.
`NONCROP_CLASS.md` and the cost sections of `NATIONAL_INFERENCE_BENCHMARK.md` are superseded.

---

## 0. The provenance fix ran, and polygon provenance is NOT the mechanism (2026-08-25)

**All three models, scored on the identical 86 held-out crop paddock-years:**

| negatives | geometry | called Grazing |
|---|---|---|
| 741, farmer-drawn | farmer-drawn | **36.0 %** |
| 563, SAM | SAM, uncapped (64 % are whole-tile blobs) | **33.7 %** |
| 233, SAM | **SAM, both classes capped at 300 ha — geometry held constant** | **36.0 %** |

**The version of the experiment that actually holds geometry constant returns exactly the
number we started with.** `GRAZING_CLASS.md` §4 predicted a sharp fall; the effect of polygon
provenance on this holdout is nil. The 2.3 points the uncapped run appeared to buy came from the
blobs, not from removing provenance — and in the direction that flatters the fix, so it would
have been easy to report as a success.

**This closes the §6.1 branch.** The 39.4 % is real, it is not an artefact of where the polygons
came from, and the explanations still standing are AgriWebb's own label quality and a genuine
spectral overlap between grazed pasture and these crops. Those want completely different work
from anything planned here — see §6.

### What ran

| step | outcome |
|---|---|
| SAM segmentation | **502/502 tile-years**, 6,311 polygons. The overnight job did 474 and exited before the last 28 composites finished; a 3.5 min top-up (3.6 SU) closed it |
| re-point both classes | 919 negatives + 104 holdout rows, **0 dropped** for want of a segmented tile |
| re-extraction | **24 jobs, all exit 0**, 754 of 1,023 paddock-years, 38,810 rows, 98.3 % matched by `contains` |
| retrain, 10 arms | done, ~6 min on express. Reports are `output/arms/*_sam.md` |
| holdout | `HOLDOUT_AGRIWEBB_sam.md`, and `HOLDOUT_AGRIWEBB_common86.md` for the like-for-like |
| `GROUP4_geomctl`, `GROUP4_padcap` | done, exit 0 (the PBS server refused connections for ~40 min mid-morning; a retry loop caught it) |

### The 104-vs-86 trap, for whoever quotes these numbers next

The published 39.4 % was measured on 104 rows. The SAM run can only score **86** of them — the
other 18 are AgriWebb points that no SAM polygon contains. **So 39.4 % against 33.7 % is not a
valid comparison**, and quoting it would overstate the fix by a factor of two.
`HOLDOUT_AGRIWEBB_common86.md` exists to make the like-for-like available: it is the original
farmer-drawn model re-scored on exactly the 86, and it reads 36.0 %.

### Why the result is not yet decisive: SAM does not segment paddocks on grazing land

| matched polygon area | median | share > 300 ha |
|---|---|---|
| grazing negatives, **SAM geometry** | **781.7 ha** | **63.9 %** |
| crop positives, SAM geometry (`ts_v2`) | 63.6 ha | 9.8 % |
| grazing negatives, farmer-drawn (`ts_idx`) | 26.1 ha | 4.2 % |

The tile is ~1,140 ha, so **half the grazing negatives are now matched to a polygon that IS the
tile.** This was checked for the obvious explanations and is none of them:

* **Not a matching bug.** No site in the set has more than one containing polygon — SAM returns
  a partition, not nested candidates. Taking the smallest container instead of the first would
  move the median by **0.7 ha**.
* **Not fixable by tightening the polygon filter.** Capping at 300 ha keeps 95 % of polygons but
  drops site containment from 72.8 % to **31.0 %** — the blob *is* the only thing covering those
  points.
* It is simply that unimproved pasture has no field boundaries for SAM to find. Consistent with
  8283a8d, which already ruled out SAM parameter tuning as a fix for flagged polygons.

**So the run swapped one geometry confound for another, in the same direction**: the negative
class is now landscape averages and the positive class is still paddocks. Note which way that
cuts — blobs should be *easier* to reject than paddocks, and indeed Grazing F1 went **up**, to
0.96 temporal / 0.97 spatial on 563 negatives against 0.94 / 0.97 on 741. A model that learnt
"blob ⇒ Grazing" would also call the small-polygon crop holdout `crop` and drop the 39.4 % for
a reason that has nothing to do with land use. **It did not even do that** — which is the
strongest hint so far that the mechanism is not geometry at all.

### The two control arms, and what they say

Both are keep-set filters on columns that already exist, so neither needed a re-extraction.

**`GROUP4_padcap`** drops every row whose matched polygon exceeds 300 ha, **from both classes
alike** — the only version of the comparison where geometry is genuinely held constant. It costs
the negative class most of its rows (233 against 563). `GROUP4_padctl` is the full keep on the
same capped test set, so the blob rows' contribution is measured rather than assumed. On the
capped test set (122 grazing rows):

| arm | negatives | Grazing F1 temporal / spatial |
|---|---|---|
| `GROUP4_padcap` (all ≤ 300 ha) | 233 | 0.89 / 0.89 |
| `GROUP4_padctl` (blobs kept) | 563 | 0.93 / 0.93 |

So the blob rows are worth ~0.04 Grazing F1 — but that gap confounds geometry with the 2.4x
difference in negatives, which is exactly what `geomctl` is for.

**`GROUP4_geomctl`** — old geometry, restricted to the rows that survived the move to SAM
(494 negatives). Grazing F1 **0.92 temporal / 0.97 spatial**, macro F1 0.836 / 0.841. Against
`GROUP4_sam`'s 0.96 / 0.97 on 563: the negative class lost about a quarter of its rows on the way
(72.8 % of AgriWebb points fall inside a SAM polygon of their own tile — 72.1 % of negatives,
78.8 % of holdout crops — and the nearest-within-50 m fallback rescues only 12 of the 278
misses), and the arms' test rows differ slightly for the same reason, so read this as a coarse
check, not a decimal-level comparison. **The holdout table at the top is the clean result; these
two are the supporting work.**

### Nothing overwrote last night's numbers

`train_group4.pbs` and `fit_and_holdout.pbs` now take `NEG_DIR` and `ARMS_TAG`, both defaulting
to the original values, so a bare `qsub` still reproduces §2; the SAM run wrote `*_sam.md` beside
the originals. One real bug was fixed on the way: `fit_and_holdout.pbs` selected the holdout by
the chunk-name glob `val_*`, which does not exist under the new chunking and would have scored
zero rows in silence. It now globs every extraction file and lets `--labeled` pick the rows.

### What to open in QGIS

`./run_samfix.sh qgis` collapses the 502 per-tile outputs into one package —
`derived/agriwebb/grazseg_review_SENSITIVE.gpkg`, **6,311 polygons, median 11.9 ha, 10 per tile**:

| layer | what it is | the check it supports |
|---|---|---|
| `paddocks` | every kept SAM polygon: `stub`, `year`, `area_ha`, `compactness` | **filter `area_ha > 300`** — 289 polygons, and they cover most of the grazing ground. This is the failure above, on screen |
| `sites` | the 1,023 AgriWebb paddock-years, with `crop`, `stratum`, `matched` | filter `matched = False` — the 278 rows the extraction dropped |
| `tiles` | one rectangle per segmented tile-year | coverage; a site outside every rectangle is unusable |

Per-tile files, for looking at one paddock closely, all in `derived/samgeo/grazseg/`:
`awt_<year>_<tx>_<ty>.tif` is the Fourier-of-NDWI composite (load as RGB — it is the image SAM
actually saw), `*_filt.gpkg` the kept polygons, `*_segment.gpkg` the raw SAM output before the
area/compactness filter, which is what to open when a paddock is missing and you want to know
whether SAM never found it or the filter rejected it.

**The comparison worth making by eye** is a grazing paddock's old farmer-drawn boundary from
`derived/agriwebb/neg/polys/` against its new SAM polygon from `grazseg/`, on that composite.
On grazing ground you will usually be looking at a whole-tile rectangle, which is the finding.

---

## 1. What is new since 2026-08-24

| | |
|---|---|
| **4th class trained** | 996 AgriWebb grazing paddock-years extracted, 664 in the training keep after the tree cut |
| **Grazing F1** | **0.94** temporal / **0.97** spatial (P 0.98) |
| **Cost to the crop classes** | −0.026 macro F1 temporal, +0.004 spatial |
| **Independent holdout** | macro F1 0.468 — **39.4 % of known crops called Grazing** ⚠ |
| **Inference stage** | `predict_tile.py` — whole tile read once, every polygon a zonal statistic |
| **Maps produced** | 3 regions x 5 years, 240 tiles, 3,709 paddocks, 49–96 % coverage |
| **National bill** | **0.055 SU/tile**; union of all crops **5,497 SU/year**, ~14 h wall |
| **SU spent overnight** | **~60 SU** of the 1 KSU budget |

## 2. The result, and the asterisk on it

Full detail in `GRAZING_CLASS.md`. On the identical 543 crop test rows:

| arm | crop macro F1 (temporal) | Grazing F1 |
|---|---|---|
| GROUP3_crop_only (reproduces the published 0.821) | 0.823 | — |
| **GROUP4** | 0.797 | **0.94** |
| GROUP4 at 10-day bins | 0.800 | 0.95 |

**Two design questions are now settled.** A two-stage crop/not-crop pipeline is *not* worth it —
the binary `CROP2` arm reaches Grazing F1 0.90 temporal where the 4-class softmax reaches 0.94,
so the softmax wins on both accuracy and simplicity. And the 20-day DOY bin is near-optimal:
10-day is +0.003, 30-day is −0.017.

**The asterisk.** Every crop positive is a SAM segmentation and every grazing negative is a
farmer-drawn AgriWebb boundary. Scored on AgriWebb paddocks with farmer-recorded *crop* events,
the model calls **39.4 %** of them Grazing, against **1.3 %** of held-out NVT crop paddocks. It
is not paddock size (no monotone trend) and it is not the known forage-oats label ambiguity
(**canola, the least ambiguous label, is worst at 52 %**). The model has learnt polygon
provenance alongside land use, and the reported 0.94 is therefore an upper bound.

**One piece of reassurance.** On the actual maps, where every polygon is SAM-segmented, the
model does *not* refuse to say Grazing — it assigns 17–59 % of paddock area to Grazing depending
on region and year. So the failure is not a total collapse in the deployment direction; its size
is simply unmeasured until §6 lands.

## 3. The maps work, and rotation is the evidence

`WALL_TO_WALL_MAPS.md`, figure `output/figures/species_maps_by_year.png`. Three 12 x 12 km
regions (a 4x4 grid of the 3 km production tile) chosen by NLUM canola probability, one per
state — **Esperance WA, Eyre Peninsula SA, Riverina NSW** — for 2020–2024.

**A map with no ground truth in it is unfalsifiable by eye, so the check is rotation:**

| region | paddocks tracked across ≥4 years | median distinct classes | same class every year | canola in 1–3 of 5 years |
|---|---|---|---|---|
| nsw_2 | 229 | 2.0 | 15.7 % | 55.5 % |
| sa_1 | 74 | 2.5 | 10.8 % | 63.5 % |
| wa_0 | 69 | 2.0 | 21.7 % | 44.9 % |

**No paddock in any region is canola every year**, and roughly half to two-thirds are canola in
one to three years of five — which is what a real canola rotation looks like. A model keying on
something static (soil colour, a persistent boundary) could not produce that.

**Coverage is the limitation to quote alongside any map.** NSW Riverina 78–96 %, SA Eyre
49–63 %, WA Esperance 52–74 %. The white space is ground SAM did not resolve into a paddock
above 5 ha, or paddocks with under 10 clear observations — not ground with no crop. 1.3 % of
polygons exceed 300 ha: the tile-scale blobs SAM returns where there are no field boundaries.
`area_ha` and `compactness` ship on every row so a user can filter them.

**Also worth knowing: the model is grossly overconfident.** Median prediction confidence is
**1.000** almost everywhere. The "faded = confidence below 50 %" device in the figure shows
almost nothing, because the argmax is always near-certain. Do not use raw softmax confidence as
a quality filter; use `n_obs`, `clear_frac`, `area_ha` and `compactness`.

## 4. The national bill, measured

`NATIONAL_INFERENCE_BENCHMARK_V2.md`. Billed SU from completed jobs, express converted to
normal-queue equivalent at the measured 3x.

| stage | SU/tile | share |
|---|---|---|
| pre-segment (4 GB, batched) | 0.0104 | 19 % |
| **SAM** | **0.0334** | **60 %** |
| inference | 0.0114 | 21 % |
| **total** | **0.0553** | |

| mask at `prob > 2500` | tiles | SU/year |
|---|---|---|
| canola | 24,941 | 1,378 |
| cereals | 95,910 | 5,301 |
| **union of all three** | **99,465** | **5,497** |

**Two findings that change the plan.** First, **96.4 % of the union is already in the cereal
mask** — mapping all three groups costs 3.6 % more tiles than cereals alone, so there is no case
for running the crops separately. Second, **SAM now dominates the bill at 60 %**, reversing the
old report's conclusion; pre-segment got 5.7x cheaper (spatial batching plus 4 GB instead of
8 GB, both verified) and SAM did not change.

**The 8 GB pre-segment advice was tested and is wrong for 3 km tiles**: the same 16 tiles of
2024 cost 0.31 SU at 8 GB and **0.08 SU at 4 GB**, both exit 0, with the 4 GB job reporting a
genuine 3.08 GB used.

## 5. Exact commands

```bash
cd src/paddocks
D=/scratch/xe2/cb8590/paddock-species-data/derived
PY=/g/data/xe2/John/geospatenv/bin/python

# --- the provenance fix, end to end (see §0) ---
./run_samfix.sh resites ; ./run_samfix.sh qgis ; ./run_samfix.sh extract
./run_samfix.sh check                                     # how far the extraction has got
./run_samfix.sh train                                     # retrain + holdout, tagged `_sam`
./run_samfix.sh ctl                                       # the geometry-vs-sample-size control

# --- the 4-class model (all arms, ~50 min on express, 4 CPUs) ---
qsub -q express -l walltime=00:50:00 train_group4.pbs     # rebuilds labels+keeps in-job
# NEG_DIR and ARMS_TAG both default to the ts_idx run, so the bare qsub above reproduces §2.

# --- fit the production model + score the independent holdout ---
qsub fit_and_holdout.pbs
# The holdout glob must cover EVERY extraction file, not a chunk-name prefix — which chunk a
# held-out paddock lands in changes whenever the chunking changes, and `--labeled` is what
# actually selects the 104 rows. This is now fixed inside fit_and_holdout.pbs; it silently
# scored zero rows once.

# --- the demonstration maps ---
$PY map_regions.py --nlum-dir $NL --out $D/mapdemo/regions.csv \
    --aois-out $D/mapdemo/aois_regions.csv --years 2020 2021 2022 2023 2024 --n 3
# then, per region-year: presegment.pbs (4 GB) -> sam_segment.pbs -> predict_tile.pbs
./run_mapdemo.sh fit ; ./run_mapdemo.sh predict ; ./run_mapdemo.sh figures

# --- national cost sample (12 clusters of 4x4 from the real mask) ---
$PY nlum_tiles.py --raster $NL/NLUM_v7_probSurf_2021_334_10_W_OILSEEDS.tif \
    --threshold 2500 --sample 12 --cluster 4 --year 2021 --out $D/natbench/aois.csv
```

**Book pre-segment at 4 GB.** **Sort AOIs spatially before chunking** — scene-cache locality is
worth 4.0x and costs nothing but the sort. **Never run the model scripts on a login node**, and
note `nlum_tiles.py` on a full national raster needs ~32 GB, so it is a job, not a shell command.

## 6. What to do next, in order

**Superseded by `PRESENCE_ONLY_LABELS.md` (2026-08-25 afternoon).** The label-review step below
was written before the presence-only argument was measured, and the measurement changed the
conclusion: 78.5 % of the `hard`-stratum grazing negatives pass a crop-presence phenology gate
that 91.6 % of known sown crops pass. **The negative class is not a not-crop class**, and no
amount of reviewing the 104 holdout rows fixes a problem that lives in the 919 negatives.

1. **Re-frame the map as presence-only.** Segmentability becomes a *mask*, not a class; the
   3-class crop model is gated on crop presence and abstains rather than saying "Grazing";
   validation moves to aggregate ABS/ABARES sown area by region and year. Full argument and
   numbers in `PRESENCE_ONLY_LABELS.md` §3.

2. **Get the ABS/ABARES series and score the existing demo maps against it.** This is free,
   public, needs no SU, and it is the first validation in this project that does not depend on
   NVT or AgriWebb. The three demo regions x 5 years already exist (`derived/mapdemo/pred/`), so
   the comparison can be run before any national job is booked.

3. **Do NOT spend more on paddock geometry for the negatives, or on the Grazing class.** Between
   §0 and the SAM parameter sweep ruled out in 8283a8d, two independent attempts failed to move
   the 39.4 %, and `PRESENCE_ONLY_LABELS.md` explains why neither could have: the labels do not
   carry the information the class was asking of them.

4. ~~**Add the missing control arm for `GROUP4_hard`.**~~ **Moot** if (1) lands — it scores a
   class that is being removed.
   Original note: The hard-negatives arm scored Grazing F1
   0.87 against 0.94, but on a different test set, so it says nothing. Run the full keep on the
   hard test set — the same device already used for the tree comparison.
5. ~~**Get more hard negatives.**~~ **Moot for the same reason, and it was always the wrong
   lever**: `PRESENCE_ONLY_LABELS.md` shows the limit is the labels' *quality*, not their count —
   more paddocks drawn from the same field would carry the same 78.5 % crop-gate pass rate.
   Original note: only **404 candidates nationally** clear the "pasture in
   cropping country" bar, from **21 farms**. That is the binding limit on the whole exercise.
   `BETA_PADDOCKS_HISTORY` crop-type transitions are the untried source.
6. **Then decide on the national run.** 5,497 SU for one year of the union is 55 % of the
   project allocation; the compute case is settled and the blocker is now (1), not cost.
7. **Sentinel-1 — the access question is now answered, see `SENTINEL1_ACCESS.md`.** DEA has no
   SAR product (checked: 120 products indexed, zero SAR), dz56 is a GA InSAR working area rather
   than a collection, and `fj7` — the Copernicus Australasia Hub, physically hosted at NCI — is
   the project to request. **If fj7 lands, the governance objection below dissolves**: the query
   never leaves NCI, so no AgriWebb coordinates are sent anywhere. Original note follows.
   It is the sensor most
   likely to separate pasture from crop by canopy structure, but fetching it means sending
   **AgriWebb farm coordinates** to Microsoft Planetary Computer. The earlier outbound-query
   decision covered NVT trial AOIs; this is different data and a different call, and it is
   yours, not mine. It also does not scale nationally (~12 days of copyq).

## 7. State of the data

| artefact | location | scale |
|---|---|---|
| grazing negatives, time series | `derived/agriwebb/ts_idx/` | 996 paddock-years, 100 % `contains` match |
| combined labels (NVT + AgriWebb) | `derived/labels_combined_SENSITIVE.csv` | 5,370 rows, `label_src` on every row |
| 4-class keep / fixed test set | `derived/keep_arms/keep_group4*`, `testkeep_group4*` | 2,858 keep / 856 test |
| production models | `derived/models/group4_map.joblib`, `group3_map.joblib` | + `.json` sidecar with the feature contract |
| demo map predictions | `derived/mapdemo/pred/*.gpkg` | 3,709 paddocks, 15 region-years |
| national cost sample | `derived/natbench/` | 119 tiles, 12 clusters |
| grazing re-segmentation | `derived/samgeo/grazseg/` | **502/502 tile-years, 6,311 polygons** |
| re-pointed sites + extraction chunks | `derived/agriwebb/sam/` | 1,023 rows, 24 chunks |
| SAM-geometry time series | `derived/agriwebb/ts_sam/` | 754 paddock-years, 38,810 rows |
| SAM-run arms, keeps, models | `output/arms/*_sam.md`, `keep_arms/*_sam_*`, `models/group4_map_sam.joblib` | 10 arms |
| control arms | `output/arms/GROUP4_padcap.md`, `GROUP4_padctl.md`, `GROUP4_geomctl.md` | 3 arms |
| holdout, all three models | `output/HOLDOUT_AGRIWEBB{,_sam,_padcap,_common86}.md` | 86–104 rows |
| QGIS review package | `derived/agriwebb/grazseg_review_SENSITIVE.gpkg` | 3 layers — see §0 |
| per-arm reports | `output/arms/` | 10 arms |
