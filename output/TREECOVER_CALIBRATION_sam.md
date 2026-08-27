# Where to cut the grazing negatives on tree cover

Written by `calibrate_treecover.py`. `treed_frac` is the share of a polygon's pixels removed by the 1 m canopy mask: `n_tree_px / (n_tree_px + n_px_paddock)`, taken as the median over the paddock's observation dates.

## 1. Coverage first — missing height tiles are not open ground

| set | paddocks | with a canopy tile | no tile (kept, reported apart) |
|---|---|---|---|
| reviewed-good crop | 2194 | 2194 (100.0%) | 0 |
| AgriWebb grazing | 754 | 754 (100.0%) | 0 |

## 2. The two distributions

Percentiles of `treed_frac`, over the paddocks that have a canopy tile.

| set | n | p50 | p75 | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|
| crop | 2194 | 0.008 | 0.031 | 0.075 | 0.116 | 0.222 | 0.564 |
| grazing | 754 | 0.220 | 0.400 | 0.538 | 0.596 | 0.908 | 0.945 |

## 3. What each cut costs

| cut | threshold | grazing dropped | grazing kept | crop that would fail it |
|---|---|---|---|---|
| crop-p95 | 0.116 | 483 (64.1%) | 271 | 5.0% |
| majority | 0.500 | 103 (13.7%) | 651 | 0.2% |

## 4. Read this before picking

- **13.7% of the grazing candidates with canopy data are more than half tree cover.** That is the silvopasture the exercise is aimed at, and it is the only group whose label is arguably wrong rather than merely inconvenient.
- The `crop-p95` cut at 0.116 would drop 64.1% of the grazing candidates. Whether that is right depends on what the negative class is FOR: if it is to reject pasture inside the NLUM cropping mask, lightly-timbered pasture is part of what the map will meet and discarding it makes the class narrower than deployment.

