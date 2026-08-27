# Where to cut the grazing negatives on tree cover

Written by `calibrate_treecover.py`. `treed_frac` is the share of a polygon's pixels removed by the 1 m canopy mask: `n_tree_px / (n_tree_px + n_px_paddock)`, taken as the median over the paddock's observation dates.

## 1. Coverage first — missing height tiles are not open ground

| set | paddocks | with a canopy tile | no tile (kept, reported apart) |
|---|---|---|---|
| reviewed-good crop | 2194 | 2194 (100.0%) | 0 |
| AgriWebb grazing | 996 | 996 (100.0%) | 0 |

## 2. The two distributions

Percentiles of `treed_frac`, over the paddocks that have a canopy tile.

| set | n | p50 | p75 | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|
| crop | 2194 | 0.008 | 0.031 | 0.075 | 0.116 | 0.222 | 0.564 |
| grazing | 996 | 0.154 | 0.358 | 0.595 | 0.756 | 0.924 | 0.999 |

## 3. What each cut costs

| cut | threshold | grazing dropped | grazing kept | crop that would fail it |
|---|---|---|---|---|
| crop-p95 | 0.116 | 574 (57.6%) | 422 | 5.0% |
| majority | 0.500 | 152 (15.3%) | 844 | 0.2% |

## 4. Read this before picking

- **15.3% of the grazing candidates with canopy data are more than half tree cover.** That is the silvopasture the exercise is aimed at, and it is the only group whose label is arguably wrong rather than merely inconvenient.
- The `crop-p95` cut at 0.116 would drop 57.6% of the grazing candidates. Whether that is right depends on what the negative class is FOR: if it is to reject pasture inside the NLUM cropping mask, lightly-timbered pasture is part of what the map will meet and discarding it makes the class narrower than deployment.

