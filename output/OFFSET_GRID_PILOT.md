# Offset-grid pilot: does shifting the tile grid per year fix chronic boundary splits?

**Status: pilot complete, result is negative-pending-redesign.** The offset-grid concept itself
checks out, but every matching implementation tried so far corrupts a meaningful slice of the
consensus layer, and the failure mode was only found because this was run as a cheap one-year
pilot first rather than committing to the full 9-year re-segmentation. **Do not run the full
9-year offset-grid production job on the current matching code.**

## Background

`CONSENSUS_LAYER.md` (22,771 paddocks) is built from nine years of SAM segmentation over the
same fixed 3km tile grid every year. `PIPELINE_ARCHITECTURE_AND_TILING.md` section 5 found
6.99-10.25% of national polygons sit within 10-15m of a grid line; because the grid never moves,
a paddock straddling one of those lines is cut identically in **every** year, so no amount of
cross-year voting can ever recover it — there is no year in which it is ever whole. The proposal:
shift the grid independently each year (`map_regions.py --offset-seed`) so a given paddock is
only cut in a minority of years, recoverable by consensus in the majority where it is not.

This requires two things neither of which existed before this pilot:
1. **Offset AOI generation** — added, `map_regions.py --offset-seed`.
2. **A cross-year matcher that doesn't assume the same tile label is the same ground** — the
   existing matcher groups files by `(region, cell)` parsed from the filename and only ever
   compares a tile's polygons against the same cell label in other years, which is only correct
   because the fixed grid never moves. Added as `polygon_stability.py --spatial-match`: builds
   one whole-region-per-year GeoDataFrame and matches every polygon against the whole region in
   every other year, not just its own cell label.

## Design

- Pilot year: 2024 (arbitrary; typically the richest-revisit year). Grid shifted by an
  independent random (dx, dy), uniform over one full tile width, seed=2024.
- Segmentation: 4 presegment jobs -> 1 gpuvolta SAM job -> 4 predict jobs, same PBS scripts and
  settings as the production `run_map100.sh`, just pointed at the offset AOIs. Total: 1,156
  tile-years (vs the ~575 SU it would cost across all 9 years).
- Combined 9-year corpus for stability: the 8 existing fixed-grid years (2017-2023, 2025)
  unchanged, plus the offset 2024 segmentation, symlinked into one polydir.
- Also added while building this: `polygon_stability.py --aois` for a new `touches_grid` /
  `dist_to_grid_m` per-polygon attribute (computed from the tile's *intended* bounds — the
  downloaded composite raster is padded ~200-500m past the true AOI window, so measuring against
  the raster's own bounds would flag the padding edge, not the tile-to-tile abutment line).

All new flags are opt-in and verified byte-identical to today's production output when omitted
(diffed against a real shard of the existing 9-year run at each step).

## Result 1 (confirms the premise): boundary risk relocates, it doesn't concentrate

`touches_grid` rate (10m tolerance) is uniform across every year in the combined corpus,
including the offset year:

| year | touches_grid rate |
|---|---|
| 2017-2023, 2025 (fixed) | 4.63-4.82% |
| **2024 (offset)** | **4.93%** |

This is exactly what the theory predicts: shifting the grid moves *which* paddocks sit near a
line, not the *fraction* that do. It does not, by itself, validate that shifting helps — see
below.

## Result 2 (the actual test): worse in aggregate, and the reason why is a real bug

Naive `--spatial-match --min-containment 0.5`, no further safeguards:

| | median n_years | % found >=5 yrs | median IoU | 2024's own median IoU |
|---|---|---|---|---|
| Original (fixed grid, all 9 years) | 7 | 73.8% | 0.84 | **0.869** (2024 was the *best* year) |
| Pilot (8 fixed + 1 offset, spatial-match) | 7 | 71.3% | 0.77 | **0.523** |

Swapping just one year to an offset grid should, if the matcher works, cost almost nothing in
aggregate (the previously-chronically-cut ~5% of paddocks should improve a lot; a similarly-sized
but different ~5% newly cut only in 2024 should lose almost nothing, since they still match fine
in the other 8 years). Instead 2024's own match quality collapsed. Root cause, confirmed directly:

**A small number of known "unsegmented_blob" artifacts (already documented elsewhere as
non-reproducible junk, `POLYGON_STABILITY.md`'s own ">300ha" band) act as transitive bridges.**
`containment(a,b) = intersection/min(area)` scores near 1.0 whenever a huge blob overlaps a much
smaller real polygon in another year. Under the old tile-restricted matcher this was harmless — a
blob's candidates were confined to its own tile, so it could corrupt at most one tile's identity.
Under whole-region `--spatial-match`, a single blob can bridge dozens of unrelated real paddocks
across many tiles into one union-find identity:

- 111 paddock identities (out of thousands) each span >=5 distinct tile cells — geometrically
  impossible for a real paddock, which is smaller than one tile.
- Together they absorbed **30.7% of all 247,247 polygon-years** in the run.
- The worst single identity reached **208 of the 1,156 tiles** (18,159 polygon-years, max member
  1,084.89ha).
- 98.1% of every >300ha polygon in the whole run sat inside these 111 groups.

**Fix attempt 1 — `--max-match-area-ha 300`** (matches `predict_tile.py`'s own convention):
exclude any polygon above this size from either side of a match. Tested on a 30-tile reproduction
of the worst group: eliminated the single 30-cell/2,714-row mega-merge entirely. Real
improvement, but not sufficient — the same reproduction, with the blob exclusion active, still
produced a 9-cell, 252-row group mixing dozens of genuinely distinct 5-280ha real paddocks with
no oversized anchor involved at all.

**Root cause 2: plain union-find is fully transitive.** A chain of individually-plausible small/
medium links (A matches B, B matches C, C matches D, ...) can walk an identity arbitrarily far
even once no single link involves a blob.

**Fix attempt 2 — `--max-group-diag-m`**: refuse a union if it would grow that identity's overall
bounding-box diagonal past a cap, checked incrementally per union (stops a chain at the first
over-extending link, not just after the fact). Swept three cap values on the same 30-tile
reproduction, `--max-match-area-ha 300` active throughout:

| cap | worst group | n_cells distribution |
|---|---|---|
| 6000m (2x tile edge) | 6 cells, 130 rows | up to 6 cells |
| 3500m | 4 cells, 117 rows | up to 4 cells |
| **3000m (1x tile edge)** | **4 cells, 124 rows** | up to 4 cells |

Tightening the cap shrinks the *number of cells* reachable but **not the row count** — a 4-cell
box can still absorb 124 polygon-years across 9 years if enough small real paddocks happen to sit
near that corner and pairwise satisfy a lenient one-directional threshold. The cap bounds the
blast radius; it does not fix the underlying looseness of `--min-containment 0.5` at full-region
candidate density (this threshold was validated on n=4 known real fragment/whole pairs scoring
0.911-0.945, against one confirmed non-match scoring 0.065 — a fine margin at n=4, evidently not
tight enough against the false-positive rate produced by tens of thousands of pairwise
comparisons at full scale).

## What this pilot cost

~1.5-3 SU total across the segmentation chain and every stability-rebuild iteration (the stability
job itself ran in 32 CPU-minutes / 1.48 SU — far under the ~9-16h budgeted, apparently because the
files were still warm in page cache from repeated testing). Trivial against the ~600 SU a full
9-year run would have cost, and the corrupted consensus that run would have produced would only
have been discovered afterward, with the fix-and-rerun cycle then costing that full amount again
per iteration.

## Recommendation

**Do not run the full 9-year offset-grid production job with the current matcher.** The
geometric premise survives (touches_grid uniformity); the matching implementation does not yet.
Three live options, none attempted yet:

1. **Raise `--min-containment` well above 0.5** (e.g. 0.8-0.9) and/or require it to be each
   polygon's *mutual* best match (not just one-directional threshold-crossing) — standard
   technique against exactly this kind of false-positive accumulation, moderate implementation
   effort.
2. **Abandon full transitivity**: chain matches year-to-year in sequence (2017->2018->2019->...)
   rather than searching all-pairs-at-once, so an identity can only ever grow by one genuinely
   adjacent link per year instead of accumulating cross-links from every possible pair.
3. **Shelve this and prioritize the phenology-gate refinements** already flagged in
   `PROJ_NOTES.md` (2026-08-31) as the bigger, more tractable lever on the area-overcall problem
   this was adjacent to — the boundary-split issue affects ~7-10% of polygons; the presence-gate
   over-call affects the whole map (1.35-1.77x across states) and already has two designed,
   untried fixes.

Not recommending a choice here — this is a real fork, not a default to proceed on.

## Artifacts

- Code: `map_regions.py --offset-seed`, `polygon_stability.py --spatial-match
  --max-match-area-ha --max-group-diag-m --aois` (all opt-in, verified byte-identical to
  production when omitted).
- Segmentation: `/scratch/.../map100/pilot2024/` (offset AOIs, samgeo, pred, combined_polydir).
- Stability output: `pilot2024/stability_pilot.csv`, `pilot2024/consensus_pilot.gpkg` (both from
  the naive run, before the two fix attempts — kept as the reproduction case, not a usable
  consensus layer).
- One-off PBS script: `pilot_spatial_stability.pbs` (not production infrastructure — see its own
  header).
