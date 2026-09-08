# Zarr raw-time-series persistence — cost benchmark

Written 2026-09-07. Answers a specific question: a colleague wants the RAW per-scene,
per-paddock time series (not just the DOY-binned classifier features) persisted permanently as
a `.zarr` store, modelled loosely on `johnburley3000/paddocktimeseries`, using this project's own
9 indices (NDVI/NDYI/CFI + the Sharma et al. 2026 six: ndre2/vi2/vi3/vdvi/vci/evi2_sharma). The
user's instruction: **if the extra compute+storage is under 10 %, implement it; otherwise flag
it back.**

> **One paragraph.** Measured on 5 real, already-segmented Riverina tiles (4–37 usable
> polygons), reusing `predict_tile.py`'s own `zonal_medians()` unmodified. **Both ratios blow
> through the 10 % threshold, and by a wide margin: extra compute is 52–135 % of the baseline
> predict-stage time per tile (mean 81 %, median 60 %), and the zarr store is 8–24 % of baseline
> per-tile storage as raw bytes, or 26–39 % once real filesystem block overhead is counted.**
> The dominant extra cost is NOT the Sharma6 arithmetic (measured at ~0.0003 s — free) or the
> zarr write (0.4–1.7 s) as the brief's framing anticipated — it is a second, bigger datacube
> read: the shipped classifier (`group3_map.joblib`, `kind="indices"`) only ever reads 4 of the
> 10 `ALL_BANDS` bands, so persisting raw reflectance means reading 10 bands instead of 4 in the
> same window, which is the single largest line item (7.9–63.5 s of the 21.8–84.4 s measured
> "extra" per tile). **Recommendation: do not implement as scoped — flag back to the user.** A
> consolidated (many-tiles-per-store) design would materially shrink the storage ratio but not
> the time ratio, which is the harder blocker of the two.

---

## 1. What was measured, and how

**No production file was modified** (`predict_tile.py`, `samgeo_segment.py`, `train_species.py`,
`run_national.sh` are all untouched). Two new scratch scripts under `src/paddocks/`:

- Baseline (A): `predict_tile.py` run **unmodified**, once per tile, via direct CLI invocation
  with `--timings`, using the actual production model and flags from `run_national.sh`'s
  `predict` case (`group3_map.joblib`, `--max-area-ha 300 --crop-gate-amp 0.35
  --crop-gate-shape phenology_gate.joblib --shape-gate-skip-classes Canola Cereal Legume
  --yield-model cereal_yield.joblib`, default `--doy 90 350`, tree-mask **on**). This reproduces
  the real production compute path byte-for-byte — it is not a re-implementation.
- New (B): `src/paddocks/zarr_pilot_extra.py` (new file, ~230 lines) — imports
  `zonal_medians()`, `ALL_BANDS`, `IDX_BANDS`, `PRODUCTS` directly from `predict_tile.py`
  (no re-derivation of the aggregation formula) and, per tile:
  1. re-reads the SAME datacube window with `IDX_BANDS` only (reproduces (A)'s read, for a
     same-process A/B read-cost comparison — see §4 caveat on why this is done in addition to
     using (A)'s own numbers),
  2. re-reads it again with all 10 `ALL_BANDS` (+`oa_fmask`) — what raw-band persistence needs,
  3. rasterises labels with the identical 10 m erosion + `TreeMasker` logic `predict_tile.py`'s
     `main()` uses (copied here since that logic isn't its own importable function — not timed
     as "extra", since a real implementation computes it once and shares it),
  4. calls `zonal_medians()` **twice**, unmodified: `kind="indices"` (NDVI/NDYI/CFI,
     per-pixel-then-median — byte-identical semantics to what the classifier already computes)
     and `kind="bands"` (raw reflectance, medianed per scene),
  5. derives the 6 Sharma et al. (2026) Table S2 formulas verbatim from `train_species.py`'s
     `add_indices()`, applied to the already-band-medianed `(paddock, time, band)` array —
     **index-of-median, not median-of-index**, which is not a shortcut invented for this
     benchmark: it is exactly how `add_indices()` already treats these 6 indices in production
     (it only ever runs on binned band medians, never on a per-pixel array). NDVI/NDYI/CFI, by
     contrast, keep the per-pixel-then-median semantics from step 4, matching the classifier
     exactly. This is a real, worth-flagging asymmetry in the proposed 9-index store: 3 of the 9
     are a different mathematical quantity (index-of-median) than the other 3 (median-of-index),
     inherited from how the project already computes each family — not something this benchmark
     introduced.
  6. assembles a `(paddock, time)` `xarray.Dataset` (10 raw bands + 9 indices, float32) and
     writes it to its own `.zarr` store (one store per tile — see §5 on the consolidation
     question), timed.

`extra_s = read_extra_s (ALL_BANDS read − IDX_BANDS read) + zonal_bands_s + sharma6_s +
zarr_write_s`. Rasterisation/erosion/tree-mask time is measured but excluded from `extra_s`
since a real implementation would not duplicate it.

**Cost of running this benchmark: $0 SU.** Everything ran interactively on the gadi login node
(`gadi-login-09`, confirmed reachable to the DEA datacube without a PBS job), ~12 minutes of
wall-clock total across both scripts, no PBS jobs submitted — the constraint was to avoid
touching the shared queue while the user's national 2022 run is in flight, and this satisfies it
with room to spare.

## 2. Tiles used

5 tiles from `/scratch/xe2/cb8590/paddock-species-data/derived/national2024/samgeo/`, already
composited + SAM-segmented (real `_filt.gpkg` reused, nothing re-segmented), chosen from the
Riverina cropping box (`lon 147.0–147.4, lat -34.9…-34.5`, per
`output/PIPELINE_ARCHITECTURE_AND_TILING.md` §6) to span the paddock-density range actually
observed there (8–44 raw polygons per tile before predict's own `min-area-ha 5` filter):

| stub | usable polygons (`n_poly`) | Sentinel-2 scenes (2024, DOY 90–350) |
|---|---|---|
| `nlum_2024_r936_c1197` | 4 (sparsest) | 52 |
| `nlum_2024_r942_c1189` | 17 | 52 |
| `nlum_2024_r938_c1189` | 28 | 52 |
| `nlum_2024_r945_c1195` | 30 | 52 |
| `nlum_2024_r948_c1194` | 37 (densest) | 52 |

## 3. Results — per tile

### 3a. Time

| tile | `n_poly` | baseline total_s (A) | extra_s (B) | **extra / baseline** |
|---|---|---|---|---|
| r936_c1197 | 4 | 62.7 | 84.41 | **135 %** |
| r942_c1189 | 17 | 42.0 | 21.75 | **52 %** |
| r938_c1189 | 28 | 43.3 | 46.30 | **107 %** |
| r945_c1195 | 30 | 43.3 | 25.83 | **60 %** |
| r948_c1194 | 37 | 52.0 | 27.86 | **54 %** |
| **mean** | | | | **81 %** |
| **median** | | | | **60 %** |

Breakdown of `extra_s` (r948_c1194, the densest tile, as a representative example):
`read_extra_s` 9.64 s + `zonal_bands_s` 17.78 s + `sharma6_s` 0.0002 s + `zarr_write_s` 0.43 s =
27.86 s. **The Sharma6 formulas and the zarr write together are under 2 % of the extra cost on
every tile measured** — the brief's framing ("most of the extra should be the indices
computation... not re-deriving the whole pipeline") undershoots badly. The two real cost
drivers are (a) the second, wider datacube read (10 bands vs the shipped model's 4) and (b) the
raw-band `zonal_medians` pass itself (13.5–19.3 s — aggregating 10 columns instead of 3 costs
real CPU, not just I/O).

**No tile came in under the 10 % time threshold. The best case (52 %) is more than 5x over it.**

### 3b. Storage

| tile | baseline (tif+filt+pred, bytes) | zarr, logical bytes | zarr, on-disk bytes (`du`, real block usage) | **ratio (logical)** | **ratio (`du`)** |
|---|---|---|---|---|---|
| r936_c1197 | 519,382 | 40,698 | 134,906 | 7.8 % | 26.0 % |
| r942_c1189 | 591,567 | 85,311 | 179,519 | 14.4 % | 30.3 % |
| r938_c1189 | 582,133 | 120,923 | 215,131 | 20.8 % | 37.0 % |
| r945_c1195 | 602,054 | 127,742 | 221,950 | 21.2 % | 36.9 % |
| r948_c1194 | 626,464 | 151,991 | 246,199 | 24.3 % | 39.3 % |
| **mean** | | | | **17.7 %** | **33.9 %** |

`baseline` here is this pilot's own single-tile output files (composite `.tif` + `_filt.gpkg` +
a predictions `.gpkg` produced by running (A) once per tile) — exactly as the brief specified
for the per-tile ratio. **Every tile exceeds 10 % on the `du` (real, physical) basis; 4 of 5
exceed it on the logical-bytes basis too** — only the sparsest tile (4 polygons) stays under 10 %
logical, and even it is 26 % on disk.

**Why logical and physical bytes diverge so much**: each per-tile `.zarr` store contains 22
arrays (10 bands + 9 indices + `stub`, plus `paddock`/`time` coordinates), each needing its own
`.zarray`+`.zattrs`, plus a `.zgroup`/`.zattrs`/`.zmetadata` at the store root — **47 metadata
files, ~25 KB logical, per store, regardless of how many polygons or scenes the tile has**
(confirmed identical byte count across all 5 tiles). `/scratch` is Lustre with a 4 KB block
size, so on a small tile most of those 47 files (plus the 22 single-chunk data files, since
every array here fits in one chunk) round up to at least one block — this is why the sparsest
tile shows the *worst* ratio increase from logical to physical (7.8 %→26.0 %, a 3.3x jump)
while the densest tile's data payload is large enough to dilute the fixed overhead more
(24.3 %→39.3 %, a 1.6x jump). **Per-store fixed overhead, not per-polygon data volume, is what
makes the sparsest tiles disproportionately expensive to persist** — the opposite of the "extra
cost scales with what's already there" intuition.

## 4. Caveats on the absolute numbers (read before trusting them at face value)

- **Login-node timing is noisy and not the same environment as a PBS compute node.** The
  sparsest tile's `IDX_BANDS` read timed at 12.6 s inside `zarr_pilot_extra.py`'s controlled
  same-process A/B, but the *same query* timed at 54.7 s minutes earlier inside the
  independently-run baseline (A). Both are real measurements; the 4x swing is Lustre client
  cache warmth and/or login-node contention with other users' jobs, not a bug — but it means the
  **ratio** (extra/baseline), not either absolute number alone, is the trustworthy quantity, and
  even the ratio has real per-tile variance (52–135 %, one clear outlier at 135 % from an
  anomalously slow `ALL_BANDS` read on the first tile of the run — excluding it, the range
  tightens to 52–107 %, mean 68 %, still 5-10x over 10 %).
- **Cross-checked against real production accounting, not just this pilot, for the national
  extrapolation** (§6) — `output/NATIONAL_2024_RUN.md`'s §3 cost table gives the actual national
  predict-stage cost (1,578.2 SU across the main + gap runs, over ~99,465 tiles), which amortises
  connection/model-load overhead across ~311 tiles per job in a way a single-tile CLI invocation
  cannot. That real number (≈14.3 s/tile, amortised) is ~3-4x cheaper than this pilot's raw
  per-tile timings (43-63 s) — confirming the pilot's *absolute* per-tile costs overstate true
  production cost (each of the 5 pilot invocations paid its own one-time connection/model-load
  cost that production amortises over ~311 tiles), which is exactly why §6 scales the
  **measured ratio**, not the pilot's raw seconds, onto the real production baseline.
- **`NDVI`/`NDYI`/`CFI` are computed per-pixel-then-median in this pilot (matching the
  classifier); the 6 Sharma indices are computed from the already-medianed band array**
  (matching `add_indices()`'s existing treatment of them). A store built this way is internally
  inconsistent in what each column actually represents — worth flagging to whoever consumes the
  zarr downstream, not a benchmark artefact.
- Only **one .zarr per tile** was tested (99,465 stores at national scale) — see §5.

## 5. One store per tile vs a consolidated store

This pilot tested **one `.zarr` per tile** because that mirrors the tile-by-tile structure
`predict_tile.py` already writes its own outputs in. At national scale that is **99,465
separate store directories, ~69 files each ≈ 6.86 million files** — for comparison, production's
own prediction output uses ~320 chunk files covering ~311 tiles each specifically to avoid this
(`run_national.sh`'s own comment: "NCI bills walltime used... short jobs schedule into gaps").
The fixed ~25 KB (logical) / much more on `du` metadata cost measured in §3b is paid **once per
store**, so a consolidated design — one `.zarr` per existing prediction chunk (~311 tiles,
matching `chunks/p*.csv`), with `paddock` spanning all of that chunk's polygons rather than one
tile's — would pay that fixed cost ~311x less often nationally, materially shrinking the storage
ratio (roughly, the logical-bytes ratio would fall from ~18 % toward the pure-data-payload floor
of a few percent; the physical/`du` ratio would fall closer to the logical figure once file count
drops by ~300x and block-rounding stops dominating). **This would NOT shrink the time ratio** —
`zarr_write_s` is already only ~2 % of `extra_s`; the dominant cost (the wider datacube read +
the raw-band zonal aggregation) is per-tile compute that consolidation doesn't touch. Not tested
directly (would require re-running the pilot with a multi-tile write, which the "no
multi-hundred-tile jobs" constraint makes awkward to do cheaply) — this is reasoning from the
measured fixed-vs-variable split in §3b, not a second measurement.

## 6. National extrapolation — LABELLED ESTIMATE, not a re-measurement

**Time.** Applying this pilot's measured ratio to the *real, already-measured* national
predict-stage cost (`output/NATIONAL_2024_RUN.md` §3: 1,255.0 SU main + 323.2 SU gap-fill =
**1,578.2 SU**, `predict_tile.pbs`'s 8 GB/1-CPU `normal`-queue rate of 4 SU/hr ⇒ ~394.6 hours ⇒
~14.3 s/tile amortised over ~99,465 tiles):

| ratio used | extra SU, national (predict stage only) |
|---|---|
| median (60 %) | ~940 SU |
| mean, outlier excluded (68 %) | ~1,070 SU |
| mean, all tiles (81 %) | ~1,280 SU |
| max observed, outlier excluded (107 %) | ~1,690 SU |

For scale: the entire national 2024 predict stage cost 1,578 SU. **This would add roughly
another half-to-slightly-more-than-a-full predict stage's worth of compute, nationally, every
year the map is run** — not a rounding error against the project's ~50 KSU/quarter earmark, but
a material, recurring line item.

**Storage.** Using the *amortised, real* national baseline (average composite `.tif` 296 KB +
average `_filt.gpkg` 127 KB, both from a 200-tile random sample across `national2024/samgeo/`,
+ average prediction share 28.5 KB/tile, from the real national output's 2.8 GB ÷ 98,382 tiles
predicted, per `NATIONAL_2024_RUN.md`) ≈ **451 KB/tile baseline**, ≈ **44.9 GB nationally**:

| | per tile (mean of 5) | national (×99,465) |
|---|---|---|
| zarr, logical bytes | 105 KB | ~10.5 GB |
| zarr, on-disk (`du`) | 200 KB | ~19.8 GB |
| **ratio, logical** | | **23.3 %** |
| **ratio, `du`** | | **44.2 %** |

(These ratios are *higher* than the per-pilot-tile ratios in §3b because the amortised national
baseline — 451 KB/tile — is smaller than this pilot's own isolated single-tile prediction
`.gpkg` files, ~140 KB average, which pay the same kind of per-file GPKG overhead the zarr
stores pay. Production's real per-tile storage is cheaper than the pilot's own baseline files
because production batches ~311 tiles per output file; a one-`.zarr`-per-tile design does not
get that benefit unless redesigned per §5.)

**What might not scale linearly, honestly flagged rather than assumed away**: (1) the read-extra
cost varied 7.9–63.5 s per tile in this small sample with no clear relationship to `n_poly`
(scene count was fixed at 52 for all 5 tiles, so this variance is read-environment noise, not a
real density effect — a genuinely useful test would need tiles with different scene counts,
which this 5-tile, same-year sample can't provide); (2) file-count overhead is a Lustre
operational concern independent of bytes — 6.86 million small files is the kind of thing NCI's
metadata servers notice regardless of the SU/GB math; (3) this used one production year
(2024, 52 scenes/tile); years with denser Sentinel-2 revisit (2023+, three satellites flying)
would cost more per tile on both axes, and this was not tested.

## 7. Recommendation

**Flag back — do not implement as scoped.** Both ratios the user asked for exceed 10 %, by a
wide margin on the harder axis:

- **Extra compute: 52–135 % of baseline (mean 81 %, median 60 %) — 5x to 13.5x over the 10 %
  threshold.** This is the harder blocker: it is driven by a real architectural fact (the shipped
  classifier deliberately reads only 4 of 10 bands, `predict_tile.py`'s own docstring: "the read
  is ~98% of this stage's runtime"), not something the Sharma6/zarr-write side of the change can
  be optimised away — the benchmark specifically measured that those two are under 2 % of the
  extra cost.
- **Extra storage: 8–24 % logical / 26–39 % physical, one-store-per-tile — 1x to 4x over
  threshold.** A consolidated (chunk-level, not tile-level) store design would likely bring the
  logical-bytes ratio close to threshold, but was not tested directly, and would not touch the
  time ratio at all.

Neither number was fabricated or rounded favourably; both were measured on real, production
composites/polygons via the project's actual `zonal_medians()` code, with the controls described
in §4. If the user wants to proceed anyway — e.g. accepting the recurring ~1,000 SU/year cost,
or only persisting a subset of tiles (crop-mask tiles only, or a sample), or redesigning to a
consolidated store first — that is a real option this benchmark doesn't foreclose, but it is a
deliberate cost/benefit call for the user to make, not a "goes ahead automatically" outcome under
the stated 10 % rule.

## 8. Proposed schema, if the user decides to proceed anyway

Hooks in at `predict_tile.py`'s per-tile loop (`main()`, right after the existing
`zonal_medians(ds, labels, n_poly, value_cols, kind)` call, ~line 380), and would require
changing `measurements` (line 285) to always request `ALL_BANDS` rather than switching on
`kind` — the one change to a production file this would actually need, since the classifier's
own indices-zonal call must still run from the same wider read rather than a second one.

- **Store granularity**: one `.zarr` per existing prediction **chunk** (~311 tiles,
  `chunks/p*.csv`), not per tile — per §5, this is the difference between ~320 stores and
  ~99,465. `paddock` dimension carries a `stub` coordinate (already planned in this pilot) so a
  consumer can still filter to one tile.
- **Dimensions**: `(paddock, time)`. `time` as the real per-scene datetime (`ds["time"].values`,
  already `group_by="solar_day"`-deduplicated) — not a DOY bin; that's the entire point of this
  ask versus what `train_species.py` already has.
- **Variables**: 10 raw bands (`ALL_BANDS`, renamed without the `nbart_` prefix) + 9 indices
  (`ndvi`, `ndyi`, `cfi`, `ndre2`, `vi2`, `vi3`, `vdvi`, `vci`, `evi2_sharma`), all `float32`,
  `NaN` fill (matches `zonal_medians`' own `np.nan` fill for no-clear-pixel dates — do not impute).
  Carry `n_clear`/`n_px` per (paddock, date) alongside — `zonal_medians()` already returns them
  and they're what a consumer needs to know whether a NaN means "cloudy" vs "not queried yet".
- **Compression**: zarr-python's default Blosc/lz4/clevel5/shuffle=1 was applied automatically
  in this pilot with no explicit config and is a reasonable default; worth a quick A/B against
  `zstd` at a higher level given this is write-once, read-many data (not benchmarked here — out
  of scope for a compute/storage-ratio pilot, but cheap to check before committing to a codec).
- **Chunking**: at chunk-store granularity, chunk `paddock` in groups of a few hundred (matching
  the ~311-tile store population) and `time` by full season (all ~50-90 scenes/year in one
  chunk) — avoids the "22 arrays, each one single chunk" degenerate case this pilot's per-tile
  stores fell into, which wastes zarr's chunking machinery entirely at tile scale.

## Files

- Pilot script (new, does not modify production code):
  `/home/147/cb8590/Projects/paddock-species/src/paddocks/zarr_pilot_extra.py`
- Baseline timings (real `predict_tile.py`, unmodified, run once per tile):
  `/scratch/xe2/cb8590/paddock-species-data/derived/zarr_pilot/pred/baseline_timings.csv`
- Baseline per-tile prediction outputs:
  `/scratch/xe2/cb8590/paddock-species-data/derived/zarr_pilot/pred/*_baseline.gpkg`
- Extra-cost timings + zarr sizes:
  `/scratch/xe2/cb8590/paddock-species-data/derived/zarr_pilot/zarr_extra_timings.csv`
- The 5 per-tile zarr stores built for this pilot:
  `/scratch/xe2/cb8590/paddock-species-data/derived/zarr_pilot/zarr/*.zarr`
- AOI subsets used: `/scratch/xe2/cb8590/paddock-species-data/derived/zarr_pilot/aois/`
