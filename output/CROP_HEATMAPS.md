# Paddock-median CFI heatmaps — canola vs wheat vs other

Generated 2026-08-07 by `src/paddocks/crop_heatmap.py`. Figures, GeoPackages and row tables
are in `/scratch/xe2/cb8590/paddock-species-data/derived/figures/crop_heatmaps/`
(SENSITIVE — TrialCodes and coordinates).

- metric `cfi_pad_median`, 40 panels, 2477 paddocks
- shared colour scale 252-1766 (CFI x10000)
- one figure per year x state; rows clustered on the CFI trace alone, never on the crop label

## What to open

| file | what it is |
|---|---|
| `cfi_group_profiles_SENSITIVE.png` | **start here** — median + IQR CFI per crop group, all 40 panels on one sheet |
| `cfi_heatmap_<year>_<state>_SENSITIVE.png` | the clustered heatmap; the number at the right of each row is its id |
| `cfi_heatmap_ALL_SENSITIVE.gpkg` | **every paddock in one QGIS layer**, with `panel` + `label` matching the figures |
| `cfi_heatmap_<year>_<state>_SENSITIVE.gpkg` | the same, split per panel (layers `paddocks`, `trials`) |
| `cfi_heatmap_ALL_rows_SENSITIVE.csv` | row id -> TrialCode, crop, paddock ha, match rule, peak CFI, peak DOY |

To check a row: read its number off the figure, then filter the GeoPackage on
`panel = '2020_SA' AND label = 65`.

## The flowering signature is there, and it is a specific date

Canola separates from both negative classes with a peak at **day-of-year 236-271**
(median 251, ~8 Sep), against a flat wheat baseline. It is clearest in 2020 SA, 2024 NSW,
2022 SA and 2023 SA; it is weak-to-absent in **2020 VIC, 2021 WA and 2024 VIC**, which are
the seasons to treat with suspicion rather than average away.

Max CFI in DOY 200-300, over the 2,477 paddocks that survived the quality filter:

| crop | n | median peak CFI |
|---|---|---|
| **Canola** | 682 | **0.2035** |
| Lentil | 81 | 0.1662 |
| Faba Bean | 83 | 0.1644 |
| Field Pea | 126 | 0.1618 |
| Lupin | 102 | 0.1617 |
| Oat | 112 | 0.1549 |
| Barley | 322 | 0.1451 |
| Wheat | 835 | 0.1420 |
| Chickpea | 134 | 0.1396 |

**Canola detected at a 5 % false-positive budget, per-season thresholds, mean over 32
season-states:**

| negative class | canola detected |
|---|---|
| Wheat only | **53.5 %** |
| Other (7 crops, no wheat) | **45.4 %** |
| Wheat + Other | **45.7 %** |

Two things follow. First, the wheat-only number **replicates** the established full-scale
result (54.5 % at 5 % FPR) on independently re-extracted data, so the pipeline change did not
break it. Second, and this is the new finding: **the honest negative class is 8 pp harder
than wheat.** Lentil, faba bean, field pea and lupin all sit above wheat on peak CFI —
consistent with CFI rising for any bright flowering canopy, not for canola specifically. A
canola-vs-wheat evaluation flatters the index; report the three-group number.

Cluster purity runs 36-57 % on three groups (chance ~40 %) but 62-82 % on the QLD panels,
which are wheat vs chickpea — the two crops sitting at the bottom of the table above. Purity
is low nationally because **wheat and Other are not separable from each other by CFI**, which
the profile sheet shows directly: the blue and green medians track each other almost exactly.
CFI answers "is this canola", not "which crop is this".

## Quality filter — 3,439 -> 2,484 trials

Trials whose matched polygon is not a plausible paddock are dropped. This is deliberately
**not** a filter on the full risk score: blind review of a stratified sample put the usable
rate at 83-92 % in *every* flag stratum, so `not_contained` / `edge_close` /
`bigger_neighbour` do not track real failure and filtering on them would discard mostly-good
data. What review did identify in imagery were shape and size failures, which is what this
removes.

| dropped | rule | why |
|---|---|---|
| 640 | `sliver` compactness > 6.0 | drainage lines, road-verge triangles; also the value that separated a real 51.6 ha neighbour (5.4) from an under-segmented 351.9 ha blob (7.2) in the user's own two rulings |
| 142 | `too_big` > 300 ha | SAM under-segmentation merging several fields, so the median mixes crops |
| 142 | `too_small` < 5 ha | below a broadacre paddock even after the upgrade rule had its chance |
| 27 | fewer than 15 clear observations | cannot resolve a 2-4 week flowering event |
| 4 | `treed` > 20 % canopy | not a paddock |

**Caveat worth carrying:** the compactness rule is the expensive one at 19 % of the data, and
6.0 was calibrated on two worked examples, not on a distribution. It is `--max-compactness`
if you want it looser.

## Two pipeline corrections made in this run

1. **Tree masking now applies to the paddock median** (it previously applied only to the
   200 m window). Measured effect: a median 0.9 % of paddock pixels are canopy, but 20 % of
   paddocks lose >5 % and one loses 62 %. **The effect on CFI is nil — median change
   +0.00000, p90 +0.00025 over 64,169 trial-dates.** Erosion plus a median was already doing
   the job. It is kept because it is now applied identically to every crop group, so the
   three-way comparison cannot be blamed on differential tree contamination.
2. **The matcher was running at `min_paddock_ha=5.0`, not the tuned 10.0.** `match_polygon`'s
   default was raised to 10.0 per the Example A ruling, but `argparse` re-declared
   `default=5.0` and silently overrode it, so that ruling never took effect. Both CLI flags
   now default to `None` and defer to the function. Effect: 23 of 1,375 shared trials (1.7 %)
   changed paddock, median 7.2 ha -> 51.6 ha, and upgrades across the canola/wheat set rose
   156 -> 187. Both of the user's worked examples now reproduce exactly.

## Coverage

Segmentation and extraction were run for the seven crops that had never been segmented
(barley, chickpea, oat, field pea, lupin, faba bean, lentil): 1,028 new AOIs, of which 1,020
segmented (99.2 %). Total paddock time series now **3,439 trials across all 9 NVT crops**
(was 2,103 canola/wheat only). 272 other-crop trials reused an existing canola/wheat AOI.

## Per-panel detail

| panel | rows | Canola | Wheat | Other | cluster purity | canola peak DOY |
|---|---|---|---|---|---|---|
| 2017, NSW | 100 | 28 | 42 | 30 | 43% | 261.0 |
| 2017, QLD | 13 | 0 | 9 | 4 | 77% | - |
| 2017, SA | 54 | 17 | 11 | 26 | 48% | 261.0 |
| 2017, VIC | 54 | 25 | 11 | 18 | 50% | 261.0 |
| 2017, WA | 55 | 16 | 17 | 22 | 44% | 241.0 |
| 2018, NSW | 57 | 13 | 27 | 17 | 47% | 271.0 |
| 2018, QLD | 13 | 0 | 9 | 4 | 69% | - |
| 2018, SA | 50 | 16 | 15 | 19 | 42% | 256.0 |
| 2018, VIC | 66 | 16 | 16 | 34 | 55% | 256.0 |
| 2018, WA | 59 | 14 | 20 | 25 | 47% | 246.0 |
| 2019, NSW | 72 | 15 | 34 | 23 | 47% | 251.0 |
| 2019, QLD | 16 | 0 | 10 | 6 | 62% | - |
| 2019, SA | 63 | 18 | 19 | 26 | 43% | 251.0 |
| 2019, VIC | 71 | 27 | 15 | 29 | 46% | 266.0 |
| 2019, WA | 71 | 20 | 22 | 29 | 44% | 251.0 |
| 2020, NSW | 99 | 32 | 38 | 29 | 40% | 246.0 |
| 2020, QLD | 16 | 0 | 10 | 6 | 75% | - |
| 2020, SA | 71 | 10 | 23 | 38 | 56% | 241.0 |
| 2020, VIC | 84 | 28 | 20 | 36 | 46% | 256.0 |
| 2020, WA | 90 | 20 | 26 | 44 | 49% | 246.0 |
| 2021, NSW | 110 | 35 | 47 | 28 | 43% | 256.0 |
| 2021, QLD | 22 | 0 | 17 | 5 | 82% | - |
| 2021, SA | 67 | 20 | 14 | 33 | 52% | 261.0 |
| 2021, VIC | 64 | 18 | 17 | 29 | 52% | 261.0 |
| 2021, WA | 58 | 10 | 20 | 28 | 50% | 243.0 |
| 2022, NSW | 91 | 23 | 40 | 28 | 45% | 261.0 |
| 2022, QLD | 19 | 0 | 12 | 7 | 68% | - |
| 2022, SA | 54 | 14 | 10 | 30 | 57% | 246.0 |
| 2022, VIC | 82 | 30 | 21 | 31 | 44% | 251.0 |
| 2022, WA | 77 | 26 | 24 | 27 | 36% | 243.0 |
| 2023, NSW | 100 | 30 | 44 | 26 | 44% | 246.0 |
| 2023, QLD | 12 | 0 | 7 | 5 | 67% | - |
| 2023, SA | 81 | 19 | 25 | 37 | 46% | 241.0 |
| 2023, VIC | 75 | 28 | 17 | 30 | 41% | 258.0 |
| 2023, WA | 59 | 13 | 17 | 29 | 49% | 236.0 |
| 2024, NSW | 109 | 41 | 41 | 27 | 41% | 246.0 |
| 2024, QLD | 23 | 0 | 15 | 8 | 65% | - |
| 2024, SA | 60 | 16 | 17 | 27 | 47% | 266.0 |
| 2024, VIC | 58 | 19 | 14 | 25 | 53% | 256.0 |
| 2024, WA | 82 | 25 | 22 | 35 | 44% | 241.0 |
