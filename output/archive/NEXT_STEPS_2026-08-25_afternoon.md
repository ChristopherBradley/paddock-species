# Where the project stands, and what to do next

Rewritten 2026-08-25 (afternoon). The previous 359-line version is
`output/archive/NEXT_STEPS_2026-08-25_full.md` — nothing in it is deleted, and its §0 remains the
record of the provenance investigation.

> **One paragraph.** A 3-class crop model (canola / cereals / legumes) works: macro F1 **0.821**
> temporal, reproduced in two independent runs. The 4th "Grazing" class does not, and cannot —
> AgriWebb records are presence-only, and **78.5 %** of the grazing negatives pass a crop-presence
> phenology test that 91.6 % of known sown crops pass. **The plan is now to stop making the
> absence claim**: segmentability becomes a mask, the classifier abstains instead of saying
> Grazing, and validation moves to ABS/ABARES sown area. The first such check is in and it is
> encouraging — canola share **26.3 % mapped vs 29.8 % ABS**, median error 4.6 points — but on a
> **1.6 % sample**, which is why the next run is 100 x 100 km, not national.

---

## 1. What is settled

| | |
|---|---|
| **3-class crop model** | macro F1 0.821 temporal / 0.823 spatial; canola at 5 % FPR 89.0 % |
| **Inference stage** | `predict_tile.py` — tile read once, every polygon a zonal statistic |
| **Demo maps** | 3 regions x 5 years, 3,709 paddocks; rotation plausible (no paddock canola every year) |
| **National cost** | **0.0553 SU/tile**; union of all three crops **5,497 SU/year**, ~14 h wall |
| **Grazing class** | **retired** — see `PRESENCE_ONLY_LABELS.md` |
| **Geometry as the cause** | **ruled out** — identical 86 holdout rows moved 36.0 % -> 36.0 % with geometry held constant (archived §0) |
| **Spend so far** | ~870 SU against a **50 KSU** budget |

## 2. What is being built instead

Full argument in **`PRESENCE_ONLY_LABELS.md`**; three changes:

1. **Segmentability is a mask, not a class.** Classify only SAM polygons at paddock scale
   (<= 300 ha + the compactness filter). As a pure geometry detector it keeps **77.9 %** of known
   crop paddocks and rejects **65 %** of pasture in cropping country. It costs 22 % of real crop
   paddocks — quote that with any coverage figure.
2. **The classifier abstains.** 3-class model behind the Stage-2 crop-presence gate (NDVI
   amplitude >= 0.35, fitted on presence labels alone). A paddock that fails the gate is left
   blank. "No crop signature detected" is supportable; "Grazing" is not.
3. **Validation is aggregate and independent.** ABS by SA2, ABARES by state — neither depends on
   NVT or AgriWebb.

**AgriWebb is being dropped.** The grazing negatives are the broken part; the 104 crop events are
valid presence records but too few to carry a validation section, and dropping the dataset removes
one NDA party from the paper review. It also reopens Microsoft Planetary Computer for Sentinel-1,
since the outbound-query decision for NVT trial AOIs was already taken.

## 3. Reference data — downloaded, tidied, cross-checked

In `derived/abs/`, fetchers in `src/paddocks/`:

| source | resolution | years | script |
|---|---|---|---|
| ABS `AG_BROADACRE` | **SA2** (318 regions) | 2022-2024 only | `abs_fetch.py` |
| ABARES Australian Crop Report | state | **1989-2026** | `abares_fetch.py` |
| ABS ASGS SA2 boundaries (2021, GDA2020) | — | — | downloaded, 50 MB |

ABS is the spatially detailed one but starts at 2022-23 (7121.0 was discontinued and replaced by
*Australian Agriculture* in June 2024). **ABARES is the only source covering the 2020 and 2021
maps**, and it carries ABARES' own quality flags (`final` / `s` estimate / `f` forecast), which are
preserved — judging a map against a *forecast* is a different claim from judging it against
history.

## 4. The first independent validation — `ABS_COMPARISON.md`

Composition, not area: of the land carrying a winter crop, what share is canola? Scale-free, so a
small box can be compared against a whole SA2.

| | mapped | ABS |
|---|---|---|
| Canola | 26.3 % | 29.8 % |
| Cereal | 58.1 % | 64.4 % |
| **Legume** | **7.5 %** | **3.2 %** |

Median absolute error on canola share **4.6 points**, r = 0.63 across 9 SA2-years.

**The precision floor, measured.** ABS and ABARES disagree with *each other* by a median **6.8 %**
on national sown area (worst: legumes 2023, 25 %). Any map-vs-reference gap smaller than that is
inside the noise between two official agencies and must not be reported as a map error. The canola
result sits at that floor; **the legume result — a 2.3x over-prediction — is well outside it.**

**Two things to take from it.** Legumes are over-predicted more than two-fold and cereals
under-predicted — consistent with Legume being the model's weakest class (F1 0.66-0.69), and the
first evidence of that failure from outside the training labels. And **the median sample is 1.56 %
of the SA2's crop area**, so none of these numbers can yet be told apart from sampling noise. That
is the entire case for §5.

## 5. In flight: the 100 x 100 km, 9-year Riverina run

Launched 2026-08-25 ~15:00. Driver `src/paddocks/run_map100.sh` (`aois` -> `presegment` -> `sam`
-> `predict`), every step idempotent.

| | |
|---|---|
| region | **Riverina**, 147.16 E / 34.73 S — the block NLUM picked for the demo, best coverage there (78-96 %) |
| extent | 34 x 34 tiles of 3 km = **102 km**, years **2017-2025** |
| scale | **10,404 tile-years**, ~575 SU (~80 % segmentation, ~20 % inference) |
| status | 30 pre-segment jobs running; 6 SAM jobs chained `afterany` behind them |

**The region is pinned, not re-searched.** `map_regions.py --centre` exists because re-scoring at
a 102 km block moves the winning cell, and a time series that changes location between runs is not
a time series.

**2017 is not like the other years.** Sentinel-2B only became operational mid-2017, so that year
carries roughly half the revisit of the rest. Expect fewer and worse polygons — sensor
availability, not land use.

**Year-to-year polygon stability — DONE, full report in `POLYGON_STABILITY.md`.** 20 shards,
**1.1 SU** for the whole thing. **247,008 polygon-years over 1,156 tiles resolve to 58,457
distinct paddocks**, tracked across nine independent annual segmentations by IoU:

| | |
|---|---|
| median polygon is found in | **7 of 9 years**, median IoU **0.84** |
| found in 5+ years | 73.8 % |
| found in **all nine** | **26.9 %** (66,530 polygon-years) |

**Stability is not monotone in size, and that is the useful part.**

| area (ha) | n | median years found | median IoU |
|---|---|---|---|
| <10 | 75,472 | 5 | 0.49 |
| 10-25 | 73,591 | 7 | 0.89 |
| **25-50** | 62,512 | **8** | **0.94** |
| 50-100 | 27,159 | 8 | 0.92 |
| 100-300 | 6,881 | 7 | 0.76 |
| **>300** | 1,393 | **5** | **0.45** |

It peaks in the real-paddock band and falls away at both ends. Small polygons lose IoU to a few
metres of boundary wobble; **the >300 ha blobs are the least reproducible thing in the dataset** —
an independent, purely geometric corroboration of the `--max-area-ha 300` mask, on 247k polygons,
with no spectral information and no labels.

**The positive result is worth stating on its own: in the 25-100 ha band SAM reproduces its own
paddock boundaries across nine independent annual segmentations at IoU 0.92-0.94.** That is a far
stronger validation of the segmentation than anything the trial-site work could provide, because
nothing ties one year's segmentation to the next.

**Still to run: the consensus layer** (`--consensus`), the geometry a multi-year product should
use. It is slow for a mechanical reason — it re-opens a GeoPackage per tile-year, ~4 h of file
opening — so it wants sharding like the main pass. The report above needs none of it.

**The abstain path is built and smoke-tested** (`PRESENCE_ONLY_LABELS.md` §3): 76.9 % of polygons
classified on 16 demo tiles, 88.3 % by area, with every unclassified polygon carrying its reason.
Inference for this run uses `--max-area-ha 300 --crop-gate-amp 0.35` and the **3-class** model.

## 6. What to do next, in order

1. **Run inference when segmentation lands** — `./run_map100.sh predict`, then re-run
   `abs_compare.py`. The Riverina 102 km box spans many SA2s, so the sample fraction goes from
   ~1.6 % to a large share of each: that is what turns §4 from a smoke test into a validation.
2. **Read the polygon-stability question the 9 years were run for**: how much does a paddock's
   segmentation move year to year, and can agreement across years raise confidence for the
   polygons that stay put? Nothing in the pipeline does this yet — it needs writing.
3. **Then decide on the national run.** 5,497 SU is ~11 % of the budget, so cost is no longer the
   constraint; the 100 km result is.
4. **Sentinel-1 — recommendation written, see `SENTINEL1_VALUE.md`.** The gain is +0.029 macro F1
   temporal, concentrated almost entirely in Legume (F1 0.69 -> 0.75, precision 0.66 -> 0.73), and
   §4 above independently found Legume to be the one class broken outside the noise floor. **Do
   not buy national S1 (~7,957 SU) yet; buy the 100 km region for 2019-2021 (~277 SU)** — three
   consecutive two-satellite years, since S1B failed in Dec 2021 and S1C was only operational from
   May 2025, leaving four of these nine years at half revisit. Decision rule: does the legume share
   move from 7.5 % toward ABS's 3.2 %?

## 7. Where the artefacts are

| artefact | location |
|---|---|
| production models | `derived/models/group3_map.joblib`, `group4_map*.joblib` |
| demo map predictions | `derived/mapdemo/pred/*.gpkg` — 3,709 paddocks, 15 region-years |
| SAM re-segmentation + QGIS package | `derived/samgeo/grazseg/`, `derived/agriwebb/grazseg_review_SENSITIVE.gpkg` |
| reference series | `derived/abs/` |
| per-arm reports | `output/arms/` — 13 arms incl. the `_sam`, `padcap` and `geomctl` controls |
| the long history | `output/archive/NEXT_STEPS_2026-08-25_full.md` |
| the 100 km run | `derived/map100/` — `aois.csv`, `chunks/`, `samgeo/`, `pred/` |

## 8. Reports, in reading order

`PRESENCE_ONLY_LABELS.md` (why the negative class fails, and what replaces it) ->
`ABS_COMPARISON.md` (the first independent validation) -> `WALL_TO_WALL_MAPS.md` (the maps) ->
`NATIONAL_INFERENCE_BENCHMARK_V2.md` (the bill) -> `SENTINEL1_VALUE.md` (is S1 worth buying) ->
`SENTINEL1_ACCESS.md` (how to get it on NCI).
Still current: `S1_MODEL.md`, `REVIEWED_MODEL.md`, `YIELD_MODEL.md`, `CANOLA_FLOWERING_AUDIT.md`,
`TILE_SIZE_BENCHMARK.md`. Superseded: `NONCROP_CLASS.md`, `GRAZING_CLASS.md`,
`AGRIWEBB_TRAINING_CANDIDATES.md`, `HOLDOUT_AGRIWEBB*.md`, and the cost sections of
`NATIONAL_INFERENCE_BENCHMARK.md`.
