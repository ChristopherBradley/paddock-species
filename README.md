# Paddock species mapping (Australia)

Maps crop species (Canola / Cereal / Legume) per paddock across Australia from Sentinel-2, trained
on GRDC/NVT trial sites. Built as an intermediate product for later work on tree-shelter effects on
productivity, but stands alone. The original brief is in `initial_nora_prompt.md`.

**Status: one full year (2024) mapped nationally, ready for feedback before spending the ~45 KSU to
do the remaining years.** GRDC/NVT trial data itself is under NDA and is never committed — see
"Sensitive data" below. This repo holds the code and aggregate findings only.

## How the model works

1. **Segmentation — SAMGeo, not fine-tuned.** Paddock polygons come from Meta's Segment Anything via
   [`SamGeo`](https://github.com/opengeos/segment-geospatial), following the pre-segment + SAM
   pipeline in John Burley's [PaddockTS](https://github.com/johnburley3000/PaddockTS)
   (`01_pre-segment.py` + `02_SAMGeo_paddocks.py`). Stock `vit_h` checkpoint, default parameters —
   re-tuning SAM was tried and explicitly ruled out (commit `8283a8d`; corroborated by the
   year-to-year stability result below). Segmentability itself is used as a mask, not a class:
   polygons are kept only at paddock scale (5-300 ha + a compactness filter), which keeps 77.9 % of
   known crop paddocks and rejects 65 % of pasture in cropping country.
2. **Classification — 3-class gradient-boosted model on Sentinel-2 indices.** Trained on the paddock
   polygon surrounding each NVT trial site, labelled with that trial's sown crop, collapsed from 9
   species to 3 groups (Canola / Cereal / Legume). Collapsing matters because **NVT often runs
   several trials in one field that SAM segments as a single polygon** — 69.7 % of training trials
   share their paddock with another trial, 31.8 % with a *different* crop, so a naive per-trial label
   is often wrong. Collapsing to 3 broad groups resolves 69 % of those conflicts (co-located trials
   are usually the same agronomic group); the polygon-trial matches were also hand-reviewed, which
   added +0.019 macro F1 on top.
3. **Presence gate.** A segmentable paddock is only classified if its NDVI amplitude clears 0.35
   (evidence of a real growing season); otherwise it abstains and carries a reason. This gate is the
   current #1 known weakness — see "Known limitation" below.

## Accuracy

3-class model, 543 fixed hand-reviewed test trials (2023-24), scored two ways:

| | macro F1 | canola @ 5% FPR | AP |
|---|---|---|---|
| **Temporal transfer** (train ≤2022) | **0.821** | **89.0%** | 0.944 |
| **Spatial transfer** (leave-site-out) | **0.823** | — | — |

Per class (temporal): Cereal F1 0.90, Canola 0.88, **Legume 0.69** (the floor — cereal leaks into
legume; Sentinel-1 addresses this, see below). Full detail: `output/REVIEWED_MODEL.md`.

**Known limitation, found by independent validation.** Scored against ABS sown-area statistics by
SA2 (a source with no connection to NVT) over 132 censused SA2s, the national map calls **1.47x** as
much land "crop" as ABS says was sown — almost entirely excess Cereal and Legume, essentially never
Canola. This is a **crop-presence gate** problem (the NDVI-amplitude threshold is too loose, likely
admitting sown-but-not-harvested pasture), not a classifier problem: once the over-call is divided
out, mapped canola share matches ABS almost exactly. Full detail: `output/NATIONAL_2024_RUN.md` §4,
`output/ABS_COMPARISON_100km.md`.

## Compute usage

| run | cost |
|---|---|
| 100 km x 9-year Riverina validation run | 597 SU |
| National 2024 run (segment + classify, all of Australia) | 6,623 SU (SAM segmentation is 62% of it) |
| **Project budget** | **50 KSU earmarked**; remaining years not yet run |

Detail, including two silent-failure incidents found and fixed mid-run: `output/NATIONAL_2024_RUN.md` §3.

## Paddock stability (100 km x 9-year Riverina trial, 2017-2025)

247,008 polygon-years resolve to 58,457 distinct paddocks. The median paddock is found in **7 of 9
years** at median **IoU 0.84**; 26.9% are found in all nine. Stability peaks in the 25-50 ha band
(median 8 years, IoU 0.94) and is worst for >300 ha "blob" polygons — an independent geometric
confirmation of the 300 ha segmentability cap above. Stable paddocks (found 5+ years) show a more
plausible crop rotation (63.3% grow canola in 1-3 of their years) than unstable ones (44.8%).

**Consensus layer** (`consensus.gpkg`: one polygon per paddock seen in ≥5 of 9 years): started at
25,082 polygons / 931,602 ha, removed 2,311 polygons (**9.2%**) / 108,248 ha (**11.6%**) — almost all
of it 133 oversized "blob" polygons that were just 0.5% of the count but 11% of the raw area. Kept:
22,771 polygons / 823,354 ha. Detail: `output/POLYGON_STABILITY.md`, `output/CONSENSUS_LAYER.md`.

## Yield — feasible, not yet shipped

Same features as the classifier, so a yield column would cost under 1% of inference (~10 SU
nationally). **Wheat and barley are predictable from Sentinel-2 alone** (spatial R² 0.58 / 0.54);
**canola is not** without Sentinel-1 (R² 0.27 optical-only — no better than guessing year+state —
vs 0.37 with S1). Blocked on three things: no deployable yield model file yet (`fit_map_model.py`
has a training-only sibling, `fit_yield_model.py` doesn't exist yet), `Cereal` pooling
wheat-and-barley which yield differently, and the NVT-trial-vs-commercial yield offset — now roughly
quantifiable via ABS production/area by SA2 (NVT trial yields consistently read above ABS regional
averages, in the expected direction), though SA2-level estimates need outlier screening before
trusting them individually. Full detail and a prioritised plan: `output/YIELD_FEASIBILITY.md`.

## Next steps

1. **Fix the crop-presence gate** — the dominant error in the map today (1.47x area over-call).
   Two candidates, both fittable without touching ABS (which must stay an independent check):
   - **Phenology shape, not amplitude.** A gate on the season's *shape* (one green-up at the right
     time, ending in a hard senescence) rather than just its height — pasture can green up as hard
     as a crop but rarely senesces like one. Fittable on the existing 3,439 NVT presence labels;
     needs a small feature-dump change and a ~100-tile re-run (~6 SU) to test.
   - **Sentinel-1 for crop *presence*** (a ploughed/stubble paddock backscatters very differently
     from standing pasture) — a different use of S1 than the species-classification test below.
2. **Sentinel-1 for species classification — measured, not yet bought nationally.** +0.03 macro F1
   (temporal transfer only; spatial gain is within noise), concentrated entirely in Legume (F1 0.69
   → 0.75, fixing cereal misclassified as legume). Estimated cost: ~277 SU to test on the Riverina
   region over 3 years vs. ~7,957 SU nationally. **Two caveats that weakened the case since first
   measured:** most of the mapped legume over-prediction turned out to be the presence-gate problem
   above rather than classifier confusion, so S1's real-world benefit may be smaller than +0.03; and
   Sentinel-1B's failure (Dec 2021) plus Sentinel-1C's late start (operational May 2025) leave uneven
   revisit density across the 2017-2025 run that any S1 feature needs to correct for. Recommendation:
   fix the gate and re-measure the legume residual before deciding. Full detail:
   `output/SENTINEL1_VALUE.md`, `output/SENTINEL1_ACCESS.md`.
3. **Yield model** — see above, roughly half a day of work once the gate is fixed.
4. Do not re-tune SAM parameters (already ruled out).

## Sensitive data

GRDC/NVT trial data (site coordinates, crop type, dates, yield) is under a signed NDA and is never
committed — see `.gitignore` and `CLAUDE.md`. Everything in this repo is code, or aggregate
findings with no site-level records.

## Where the outputs are

- National 2024 crop map: shared as public Earth Engine table assets under
  `projects/ee-christopher-bradley/assets/paddock_species_national_2024_crops` (20 shards, merge
  client-side with `.merge()` — see `src/paddocks/gee/visualise_national_crops.js`), and as a 2.8 GB
  GeoPackage on gadi (`output/NATIONAL_2024_RUN.md` §5 has the pull command).
- Full report index, in reading order: `output/NEXT_STEPS.md` §8.
