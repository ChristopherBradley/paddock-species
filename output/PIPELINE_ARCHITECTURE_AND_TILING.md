# Model architecture, features, and tiling mechanics — technical detail

Written 2026-08-30 for internal understanding and the colleague validation-methodology
discussion. Not part of the manuscript — `output/manuscript/sections/05_methodology.md` §4.3
stays deliberately brief per the skill's word budget; this is the expanded version. Aggregate
only, no site-level records; safe to read/share alongside the manuscript.

---

## 1. Model architecture

**`HistGradientBoostingClassifier`** (scikit-learn) — histogram-binned gradient-boosted decision
trees, not a neural network. Same architecture, same 51-feature contract, used for both the
crop-species classifier (`--target group3`) and the Cereal yield regressor
(`HistGradientBoostingRegressor`).

Hyperparameters (`train_species.py:479-480`): `max_iter=400`, `learning_rate=0.06`,
`class_weight="balanced"` (compensates for Cereal 1,119 / Canola 585 / Legume 490 class
imbalance), `random_state=seed`. **Seed has zero measured effect** on this dataset — HGB's
`random_state` only governs an internal feature-binning subsample that only activates above
10,000 training rows; this model trains on 1,651-2,194 rows, so it never engages
(`EVAL_SEED_STABILITY.md`, confirmed across seeds 0-4, byte-identical results).

Why gradient-boosted trees rather than a deep model: the label volume is small (2,194
field-verified trials total) and the label volume, not architecture, was the binding
constraint — a 9-species version of the same architecture only reached macro F1 0.38, while
the 3-group version reaches 0.82; a deep model would not relax that constraint (`train_species.py`
top-of-file docstring). `HistGradientBoostingClassifier` also handles missing values (`NaN`)
natively by learning a default split direction per node, rather than requiring imputation — this
matters directly for the feature set below, where a cloudy fortnight leaves a real gap rather
than an invented value (`train_species.py:13-14`).

## 2. Features (51 total, exactly)

Three Sentinel-2 spectral indices, each **paddock-median**, each binned onto **calendar
day-of-year** (not days-after-sowing — measured on this dataset, flowering aligns tighter on
the calendar: IQR 26 days vs. 30, `train_species.py:12-13`), 13 bins of 20 days from DOY 90 to
330 (`BIN_START=90, BIN_END=350, BIN_STEP=20`, `train_species.py:38`) = **39 binned features**,
plus 4 whole-season summary statistics per index (10th percentile, 90th percentile, amplitude
`p90-p10`, and day-of-year of the seasonal peak) = **12 summary features**. 3 indices x
(13 + 4) = **51**.

The three indices (`train_species.py:94-97`, `add_indices`):
- **NDVI** — `(NIR - Red) / (NIR + Red)`, general vegetation vigour/greenness.
- **NDYI** — `(Green - Blue) / (Green + Blue)`, a yellowness index; canola's flowering signal.
- **CFI** (canola flowering index, after Tian et al. 2022 per the code comment — **not yet
  independently verified against the original publication**, unlike the citations already
  checked for the manuscript) — `NDVI x ((Red+Green) + (Green-Blue))`, combining greenness
  with the yellow flowering signal into one index.

**Why indices, not raw reflectance bands**: a 10-band model was tried and scored *worse* on
canola than the 3-index model, because CFI is non-linear in reflectance — the median of
per-pixel CFI (what the index files store) is not the same quantity as CFI computed from the
median reflectance (the most a band-only model could reconstruct). The index files carry a
signal the band files structurally cannot (`train_species.py:410-414`).

**What's deliberately excluded**: latitude/longitude/year are excluded by default
(`--with-geo` opts back in, used only for diagnostics). A model given coordinates can score
well by learning *where* crops are grown rather than what they look like spectrally — chickpea,
for instance, is effectively a Queensland crop, so geography would be a shortcut around the
actual imagery signal (`train_species.py:24-27`).

### 2.1 How NDVI/NDYI/CFI were chosen, and what else was tried

**The choice of *pathway* (bands vs. indices vs. combined) was tested empirically; the choice
of *which three indices* was inherited, not searched.** Two separate things happened here and
they're worth keeping apart:

1. **Bands vs. indices vs. combined — tested, at the original 9-species scope, before the
   3-group collapse** (`SPECIES_MODEL_bands.md`, `SPECIES_MODEL_indices.md`,
   `SPECIES_MODEL_combined.md`, plus `_k51`/`_partial` variants): 10 raw bands (274 features,
   including derived NDRE/NDWI/NBR/PSRI/swir-ratio — see below), 3 indices alone (51 features),
   and both together (325 features) scored macro F1 0.287-0.319 (temporal) at 9 species — all
   within noise of each other, none clearly better. This rough parity at 9-species is why the
   project moved to the 3-group collapse rather than continuing to search feature sets at a
   scope the label volume couldn't support (Section 1 above).
2. **Which three indices — NDVI, NDYI, and CFI specifically — traces to `PaddockTS`'s
   `indices.py`**, referenced directly in `BRIEF.md` as the starting point ("Canola is the
   likely starting species via the Canola Flower Index... as referenced in the PaddockTS
   `indices.py` script"). These were the pre-existing, already-extracted index files this
   project inherited, not the output of a literature-driven search across the vegetation-index
   space.

**EVI, SAVI, GNDVI, and the other indices used in the two closest Australian precedents were
never computed or tried anywhere in this codebase** — confirmed by a direct source search, not
an absence of evidence. `LIT_REVIEW_REPORT.md` already has the relevant citations on record:
Sharma et al. (2026) used NDVI/EVI2/SAVI/NDRE2/VDVI/VCI/Vi2/Vi3; Al-Shammari et al. (2024) used
monthly/percentile EVI and red-edge CIr alongside S1/MODIS; a further paper flagged in the
review ("A Novel Spectral Index for Automatic Canola Mapping") was explicitly logged as a
"competing index to benchmark against PaddockTS's CFI" and that benchmark was never run. So the
honest answer is: the *pathway* decision has real evidence behind it (bands add nothing indices
don't already carry, per `train_species.py`'s note that CFI computed from median reflectance is
not the same quantity as the median of per-pixel CFI), but the *specific 3 indices* have not
been benchmarked against the broader vegetation-index literature this project's own lit review
already surfaced. That's a real, addressable gap — not large in effort (the additional indices
Sharma/Al-Shammari used are standard band-ratio formulas, cheap to add to `add_indices()` and
re-run through the identical `train_species.py` pipeline once the label volume question is
settled at 3-group scope), and worth naming explicitly as a candidate next step alongside E8/E9.

**Training vs. prediction-time feature code is the same function**, not a re-implementation:
`predict_tile.py:208,352` imports `build_features` directly from `train_species.py` and calls
it with the exact `bin_step` the model was trained with (`predict_tile.py:339` comment: "the
SAME `build_features` the model was trained with does the binning"). There is no separate
prediction-time feature pipeline to drift out of sync with training.

---

### 2.2 The "paddock-median" is a median of medians, computed identically at train and predict time

**Yes, exactly as described: spatial median first (per date), then temporal median across
dates within a bin.** Two stages, verified in both the training-extraction code and the
prediction-time code, which do the identical operation (not just similar):

**Stage 1 — spatial, per individual satellite observation date.** For each paddock polygon,
at each date the satellite passed over: (a) the polygon is **eroded inward by 10 m**
(`--erode-m`, default 10.0, both `extract_paddock.py:171` and `predict_tile.py:155`) so that
boundary pixels mixed with the road, fence line, or neighbouring tree canopy are excluded
before anything is averaged — "eroded... so boundary pixels mixed with road and tree line do
not re-import the contamination the erosion exists to remove" (`predict_tile.py:19-20`); if
erosion would empty a narrow polygon, the raw (unedoded) shape is used instead as a fallback,
identically in both places. (b) cloud/shadow-masked pixels are dropped (`oa_fmask` != clear ->
NaN, `predict_tile.py:70`). (c) **NDVI/NDYI/CFI are computed per pixel first**, then the
median is taken over the surviving clear, eroded-interior pixels for that one date
(`extract_paddock.py:347`: `.median(dim=("x","y"))`; `predict_tile.py:107`:
`np.nanmedian(S[:, px, :], axis=1)`). This order matters and is deliberate, not incidental:
CFI is non-linear in reflectance, so `median(CFI-per-pixel)` is a different, more correct
number than `CFI(median-reflectance)` — computing the index first preserves information a
band-only model structurally cannot recover (same rationale as Section 2's bands-vs-indices
result). This produces one value per (paddock, date, index) — the `*_pad_median` columns.

**Stage 2 — temporal, across dates within a 20-day calendar bin.** `train_species.py`'s
`build_features()` takes those per-date paddock-medians and, for each `TrialCode` and each
20-day day-of-year bin, takes the **median across however many clear observation dates fall in
that bin**: `pivot_table(index="TrialCode", columns="bin", values=value_cols,
aggfunc="median")`. A bin with zero clear observations stays `NaN` (handled natively by the
gradient booster, Section 1) rather than being imputed.

**Both stages use median, never mean**, at every point — robust to a single noisy pixel or a
single partially-cloud-contaminated date slipping past the fmask, rather than let one bad value
pull the aggregate. (The extraction also computes `*_pad_mean` and `*_win_mean` — mean over the
paddock, and mean over a larger surrounding window — alongside `*_pad_median`, but the shipped
model uses only the `_pad_median` columns; `value_cols` in `train_species.py` is filtered to
`.endswith("_pad_median")` explicitly.)

## 3. Tiling for the national run

**3 km x 3 km tiles** (`half_m = 1500`, i.e. AOI half-width 1,500 m; every one of the 99,465
national tiles in `national2024/aois.csv` has `half_m=1500`). This is a deliberate, benchmarked
choice, not a default: `TILE_SIZE_BENCHMARK.md` found tile size changes segmentation output
itself, because SAM's fixed 512x512-pixel prompt window makes tile size a real segmentation
hyperparameter (3 km tiles: 2.02 polygons/km², 14.9 ha median; 9 km tiles: 1.56 polygons/km²,
19.2 ha median). 3 km was chosen because it matches the scale the *training* trial AOIs were
segmented at, keeping train/inference consistent — **not** for cost (9 km tiles are only 1.17x
cheaper, so cost was explicitly not the deciding factor, `TILE_SIZE_BENCHMARK.md` §4).

## 4. Tile overlap: none

Tiles are laid out **edge-to-edge with no overlap and no gap**. `nlum_tiles.py:69` sets
`edge = 2 * half_m` and feeds it directly as the grid `resolution` — i.e. tile centres are
spaced by exactly one tile-width, and `TILE_SIZE_BENCHMARK.md:29` states this explicitly:
"tiles each parent exactly — no gap, no overlap." Confirmed at the imagery-read level too:
`samgeo_segment.py:156-157` queries Sentinel-2 with `x=(cx-half_m, cx+half_m), y=(cy-half_m,
cy+half_m)` — an exact square, no buffer term anywhere in the function or its callers.

The national merge (`merge_national.pbs:29-41`) is a **pure concatenation**: every tile's
prediction chunk is appended into one national GeoPackage with `ogr2ogr -append`, with a
spatial index built afterward purely for query speed. There is no clip-to-tile-core step, no
cross-tile polygon deduplication, and no boundary-reconciliation pass anywhere in the pipeline.

## 5. Why boundary artifacts aren't usually obvious — and why the duplicate-class paddocks you found are real

**The mechanism is real, not a data error.** Because tiles abut with zero overlap and each
tile's Sentinel-2 read is bounded exactly to its own square, a real paddock that straddles a
tile boundary gets cut by the read window itself. SAM then segments each fragment
independently within its own tile's `SamGeo.generate()` call, producing two separate polygons
in the two adjacent tiles' output. `predict_tile.py` classifies each tile's polygons from that
tile's own datacube read, so the two fragments are scored independently and **can legitimately
receive different predicted classes** — which is exactly the wheat/legume case you found. This
is confirmed as a known, explicitly *unaddressed* category: `flag_paddock_conflicts.py:56-58`
notes "near-duplicate polygons are a separate (milder) problem and are not flagged here,"
in a different but related context (training-label matching, not national-map production) —
the project is aware duplicate/near-duplicate polygons exist as a class of issue and has not
built tooling to detect or merge them anywhere in the pipeline.

**Why it isn't visually obvious most of the time — this part is reasoning from the mechanism,
not a separate measurement:**
- **Detectability bias.** When a split paddock's two fragments get the *same* predicted class,
  the seam is invisible at normal viewing scale — it just looks like two adjacent same-coloured
  paddocks, indistinguishable from two genuinely separate real paddocks. Only when the two
  fragments get *different* classes (your screenshot's case) does the split become visible at
  all. So what you're seeing is not a rare event made visible — it's the ordinary rate of
  boundary splits, filtered down to the subset that happens to be detectable by colour alone.
- **Most paddocks are far smaller than a tile.** Real paddocks run tens of hectares (median
  ~15-30 ha per `TILE_SIZE_BENCHMARK.md`) against a 3 km x 3 km = 900 ha tile, so only paddocks
  whose true boundary happens to sit close to the fixed 3 km lattice are affected at all — most
  of a tile's paddocks are nowhere near an edge.
- **Measured 2026-08-30** (not estimated): reconstructed the exact 3km tile lattice from
  `national2024/aois.csv` (grid origin recovered to within 0.03m consistency across all 99,465
  tile centres — the grid is real and exact, not approximate), then checked every one of the
  1,346,582 national polygons' bounding boxes for an edge within tolerance of a grid line
  (`ST_MinX/MaxX/MinY/MaxY` via GDAL's SQLite dialect, no full-geometry load needed — 24s for
  all 1.3M polygons).

  | tolerance | polygons flagged | % of national total |
  |---|---|---|
  | 1 m (near-exact) | 9,737 | 0.72% |
  | 10 m (one Sentinel-2 pixel) | 94,114 | 6.99% |
  | 15 m | 138,084 | 10.25% |
  | 30 m | 251,481 | 18.68% |

  **This is an upper bound on "structurally at risk," not a count of confirmed duplicate-class
  cases** — a flagged polygon's twin fragment may have been filtered out entirely
  (`area_below_min`), or may have received the *same* class (invisible, per the detectability
  argument above), so this doesn't directly say how many are visible duplicate-class pairs like
  the one you found. The class distribution among flagged polygons is essentially identical to
  the national distribution (Cereal 32.2% vs 32.9% overall, abstain 52.0% vs 51.7% overall) —
  boundary-touching polygons are not systematically biased toward any one class or toward
  abstaining, they're a representative cut of the map. Median area is slightly lower among
  flagged polygons (12.6 ha vs 14.1 ha nationally), consistent with some genuine edge-trimming.

  **Concrete confirmed example** (not just a bbox coincidence): searched a 60km box around the
  Riverina test region for pairs of polygons whose bounding boxes meet exactly across the same
  grid line — found 30 such pairs in that one area alone, 13 with a class mismatch, including
  one real **Legume/Cereal split** (11.67 ha Legume fragment + 95.01 ha Cereal fragment,
  sharing a boundary at approximately 147.108degE, -34.623degS) — likely the same kind of case
  your screenshot shows. Extracted for the overlap test below (§6).

## 6. Overlap experiment — does a buffered AOI fix the split?

**Status: complete. Two PBS jobs, gpuvolta queue — job 177786687 (2026-08-30, 1 pair, 1.84 SU,
3 min) and job 177801921 (2026-08-31, 3 more pairs, 4.5 min, exit 0). n=4 boundary-split pairs
tested in total.** `src/paddocks/overlap_test.pbs` and `overlap_test2.pbs`.

**Test design, all 4 pairs identical:** a single AOI centred exactly on the confirmed split's
shared boundary point, half-width 2000m (4km square, comfortably containing both original
fragments plus margin), same year (2024) and same SAM settings as production (`sam_kwargs=None`
— confirmed `run_national.sh`'s `sam` case and `samgeo_segment.py`'s `add_filter_args` pass no
overrides), via `samgeo_segment.py all` (segmentation only — this tests geometry, not
whether the classifier would still disagree on the result). The first pair (Legume 11.67ha /
Cereal 95.01ha, 147.108degE/-34.623degS) was the one found by eye in §5. The other 3 were found
by re-deriving the same "60km-box, grid-line-touching-pair" search that produced §5's "30 pairs,
13 mismatched" finding — that original query was ad hoc and wasn't saved to a script, so it was
independently reconstructed as `src/paddocks/find_boundary_pairs.py` against the same national
bbox extract (`national2024/fig_extract/national_2024_bboxes.csv`). At 10m tolerance (one
Sentinel-2 pixel) the reconstruction found 41 touching pairs / 9 class-mismatches in the same
box — not an exact match to the original 30/13 (different tolerance, and the original wasn't
saved to compare directly), but it re-found the *same* Legume/Cereal pair already tested,
confirming the reconstruction is sound. The 3 new pairs were chosen to span both boundary
orientations (horizontal and vertical grid lines) and a range of fragment sizes (5-34 ha):

| pair | small fragment | large fragment | location |
|---|---|---|---|
| 1 (orig.) | Legume 11.67 ha | Cereal 95.01 ha | 147.108degE, -34.623degS |
| 2 | Legume 5.08 ha | Cereal 16.96 ha | 147.164degE, -34.536degS |
| 3 | Canola 11.96 ha | Legume 25.50 ha | 147.360degE, -34.734degS |
| 4 | Canola 11.81 ha | Cereal 14.59 ha | 147.346degE, -34.654degS |

**Methodology upgrade over the original n=1 write-up:** rather than eyeballing whether a
similarly-sized polygon appears nearby, each original fragment's *exact* polygon geometry was
pulled from the national output (`national_2024_crops_classified.gpkg`) and intersected against
every polygon in the new wider-AOI segmentation — both the **raw** SAM output
(`*_segment.gpkg`, before any filtering) and the **filtered** output (`*_filt.gpkg`, after
`filter_polygons`'s min-area/max-area/max-compactness rules, `samgeo_segment.py:212-226`). This
answers a sharper question than "does something similarly-sized turn up nearby": exactly what
fraction of each original fragment's *footprint* survives, and at which pipeline stage does it
get lost.

**Result — the fragment is never actually invisible to SAM. What kills it is the compactness
filter, and it's a coin flip which side it hits:**

| pair | fragment | raw recovery | filt recovery | what absorbed it |
|---|---|---|---|---|
| 1 | Legume 11.67ha (small) | **100%** | **0%** | 442.5 ha polygon, compactness 36.5 (limit 8.0) → **rejected** |
| 1 | Cereal 95.01ha (large) | 99% | 99% | 94.2 ha polygon, compactness 4.6 → kept, near-unchanged |
| 2 | Legume 5.08ha (small) | 91% | 91% | 39.7 ha polygon, compactness 4.8 → kept (merged into a bigger neighbour) |
| 2 | Cereal 16.96ha (large) | 98% | 98% | 16.7 ha polygon, compactness 4.7 → kept, near-unchanged |
| 3 | Canola 11.96ha (small) | 94% | 94% | 63.0 ha polygon, compactness 6.3 → kept (merged into a bigger neighbour) |
| 3 | Legume 25.50ha (large) | 98% | **6%** | 114.4 ha polygon, compactness 34.0 (limit 8.0) → **rejected** |
| 4 | Canola 11.81ha (small) | 99% | 99% | 19.6 ha polygon, compactness 5.1 → kept, redrawn close to original |
| 4 | Cereal 14.59ha (large) | 100% | 100% | 17.6 ha polygon, compactness 4.9 → kept, redrawn close to original |

In every single case, **91-100% of the original fragment's footprint is present in SAM's raw
segmentation** of the wider AOI — the paddock is not something SAM fails to "see" once the
tile-edge cut is removed. What varies is what SAM does with that visibility: sometimes it
redraws a compact polygon close to the original fragment (pair 4, both sides), sometimes it
absorbs the fragment into a modestly larger but still-compact neighbouring merge that survives
filtering (pair 2's small side, pair 3's small side), and sometimes — unpredictably — it merges
the fragment together with several unrelated paddocks into one large, highly irregular blob
(114-442 ha, compactness 34-37 against an 8.0 limit) that the pipeline's own shape filter then
rejects outright. That last outcome is not new or unaddressed: it's exactly the
`unsegmented_blob` `abstain_reason` category already present in the national output and counted
in §5's table. **Which fragment it hits is not biased toward the small one** — in pair 1 the
*small* Legume fragment was destroyed this way, but in pair 3 it was the *large* 25.5 ha Legume
fragment, disproving any assumption that this specifically threatens small paddocks.

**Revised verdict (supersedes the n=1 "might be a segmentation artifact" framing): a wider,
boundary-crossing AOI does not reliably fix these splits.** Across n=4 it never once produced a
single clean polygon spanning both original fragments' combined footprint — the "merge" pairs 2
and 3 instead absorbed the smaller side into a larger, *different* neighbouring paddock, and
pair 4 simply redrew two still-separate polygons close to (not merged with) the original split.
And in 2 of 4 pairs, the wider read window actively introduced a **new** failure — over-merging
into a blob the compactness filter deletes — that destroys just as much real paddock area
(11.67-95 percent of a fragment, gone) as the original tile-cut problem it was meant to fix.
Net effect on data completeness across this sample is a wash, not an improvement, and the loss
mechanism is the existing `max_compactness=8.0` filter interacting badly with a bigger read
window, not a gap that overlap-and-stitch logic would need to invent new handling for — it would
need to specifically detect and reconcile blob-vs-fragment cases against the *original* tile
output, not just rerun segmentation on a bigger window and trust the filter to behave.

**Reproducibility:** pair-finding query, mismatch candidates, and the "before" fragment extracts
for pairs 2-4 are at `src/paddocks/find_boundary_pairs.py`,
`.../fig_extract/mismatch_pairs.csv` (paths per that script), and
`.../overlap_test/before_pair{2,3,4}.gpkg`; segmentation outputs (raw + filtered, all 4 pairs)
are at `.../overlap_test/overlap_demo{,2,3,4}_{segment,filt}.gpkg`.

## 7. Fields of the World vs. SAMGeo — the original prototyping comparison

**Already exists, not regenerated**: `PADDOCK_BOUNDARY_BENCHMARK.md` (2026-08-07) is exactly
this — a Yorke Peninsula SA canola site, 3km AOI, side-by-side satellite-imagery panels with
both polygon sets overlaid. SAMGeo traces the real 57.3 ha trial paddock exactly (follows the
roads, excludes a bare patch, stops at the treed boundary); FTW merges the same paddock with
two neighbours into one 339.1 ha blob. Across a wider 4-site check the same pattern holds
(FTW-containing polygons of 130, 339 (x2), and 1,307 ha) and the failure is systematic: 79% of
FTW's polygons in the test AOI are sub-1ha slivers, not a paddock-size distribution at all —
consistent with FTW's own published benchmark excluding Australia (only its model-predicted
global product covers us).

The rendered figure is at
`/scratch/xe2/cb8590/paddock-species-data/derived/figures/boundary_comparison_arth_SENSITIVE.png`
— **marked SENSITIVE** because it's zoomed into real satellite imagery of an actual GRDC trial
site with the trial points marked (yellow/black dots), which is itself a form of site-location
disclosure even without printed coordinates. Same handling as every other `_SENSITIVE` file:
fine for the internal colleague discussion, not for anything leaving that circle. If a
wider-distributable version is wanted later, the trial-point markers are the one element to
strip — the imagery and polygon comparison alone make the methodological point without
pinpointing a specific real farm.

## Sources

`src/paddocks/train_species.py`, `src/paddocks/predict_tile.py`, `src/paddocks/samgeo_segment.py`,
`src/paddocks/nlum_tiles.py`, `src/paddocks/merge_national.pbs`,
`src/paddocks/flag_paddock_conflicts.py`, `src/paddocks/find_boundary_pairs.py`,
`src/paddocks/overlap_test.pbs`, `src/paddocks/overlap_test2.pbs`, `output/TILE_SIZE_BENCHMARK.md`,
`output/EVAL_SEED_STABILITY.md`. §6's overlay analysis (raw-vs-filtered fragment recovery, pairs
2-4) was run directly against `national_2024_crops_classified.gpkg` and the
`overlap_test/overlap_demo*` outputs, not from memory or prior reports — see §6's own
reproducibility note for exact paths. All file:line references verified directly against the
code during this write-up (2026-08-30/31), not from memory or prior reports.
