# Tile size changes the paddocks, not just the bill. Tile *order* is worth 4x.

Written 2026-08-10. Answers a question `NATIONAL_INFERENCE_BENCHMARK.md` §2 left open: it
priced the national run per 3 km tile, which quietly assumes tile size is a free cost knob.
It is not — it is a segmentation hyperparameter — and the measurement that shows this also
overturns the reason §2 gave for where the cost goes.

**Three findings, in order of how much they matter:**

1. **Tile size silently changes the polygons.** 3 km tiles yield **2.02 polygons/km² at a
   14.9 ha median**; 9 km tiles yield **1.56 at 19.2 ha** on the same ground. Production must
   use the tile size the training paddocks came from, which is 3 km.
2. **Processing order is worth 4.0x** on pre-segment, the term §2 identified as dominant.
   Same tiles, same code — just visit neighbours together.
3. **Tile size is worth almost nothing on cost** (9 km is 1.17x cheaper overall), and it is
   the wrong lever to pull given finding 1.

---

## 1. What was measured

Two arms over **exactly the same 324 km² of ground**, 2021, on gadi 2026-08-09/10:

| arm | tiles | tile size | ground |
|---|---|---|---|
| `bench9km` | 4 | 9 km (81 km²) | 4 cropping-district footprints: NSW, WA, VIC, SA |
| `bench3km_matched` | 36 | 3 km (9 km²) | the 3x3 children of those same 4 footprints |

`subtile_aois.py` tiles each parent exactly — no gap, no overlap — so the only thing differing
between arms is where the tile boundaries fall.

**This control was necessary, and its absence had already produced a wrong answer.** The only
comparison available at first was `bench9km` against `nlum_bench`, 12 3 km tiles sampled
nationally. On those numbers 9 km tiles looked **3.6x cheaper per km²**. That is an artefact:
the national tiles are scattered, so each reads its Sentinel-2 scenes cold, while tiles sharing
a footprint mostly reuse the first one's reads. The confound was bigger than the effect.

## 2. Finding 1 — the polygons differ, and that is disqualifying

| arm | polygons/km² | median ha | kept/raw | tile edge km per km² |
|---|---|---|---|---|
| 9 km | 1.56 | 19.2 | 0.22 | 0.44 |
| **3 km** | **2.02** | **14.9** | 0.22 | 1.33 |

This is not noise and it is not edge truncation — the prediction going in was that 3 km tiles
would lose *more* paddocks to their 3x longer boundary, and they returned 30 % **more**.

**The cause is prompt density.** `samgeo` subdivides any raster into fixed **512x512** windows
(`common.py:1100`) and applies the same `points_per_side=32` grid to each, so prompts per unit
ground depend on tile size:

| tile | pixels | 512 px windows | prompt points | **points per km²** |
|---|---|---|---|---|
| 3 km | ~322 x 348 | 1 | 1,024 | **114** |
| 9 km | ~963 x 1043 | 6 | 6,144 | **76** |

A 1.5x difference in prompt density, producing a 1.3x difference in polygon density and a 1.29x
difference in median area. The directions and rough magnitudes agree, and it is the same
mechanism `samgeo_segment.py` already documents as the dominant review failure: too few prompts
across a tile merges adjacent fields into one mask.

**Consequence.** The reviewed training paddocks were segmented from AOIs of `half_m=1500`
(688 of 1,973 exactly 1500 m, the rest a tail just above it for multi-trial sites). A national
run at 9 km would hand the model paddocks delineated at a coarser scale than anything it was
trained or validated on, and `NEXT_STEPS.md` §1 shows this model is sensitive to polygon
quality — the hand review moved macro F1 by +0.019 on exactly these grounds. **Use 3 km.**

## 3. Finding 2 — pre-segment is a cache problem, worth 4.0x

Scene counts are matched across all three sets (90, 90, 91 per tile), so this is not a
revisit-density difference.

| set | tiles | s/tile | **s/km²** |
|---|---|---|---|
| 9 km, scattered footprints | 4 | 126.5 | **1.56** |
| 3 km matched, **first child of each footprint** (cold) | 4 | 26.2 | **2.91** |
| 3 km matched, **remaining children** (warm) | 32 | 10.9 | **1.21** |
| 3 km matched, all | 36 | 12.6 | **1.40** |
| 3 km, scattered nationally (`nlum_bench`) | 12 | 50.7 | **5.64** |

Rows 2 and 3 are the whole story: a 3 km tile costs 26 s cold and 11 s once a neighbour has
read its scenes. **`5.64 → 1.40 s/km²` is 4.0x, from processing order alone**, with tile
geometry unchanged. A national run walking tiles in spatial blocks gets it; one sharding a
shuffled tile list does not.

## 4. Finding 3 — total cost, priced off gadi's charging rule

`normal` bills `max(ncpus, mem/4GB) x 2 SU/hr`; `gpuvolta` bills its 12-CPU/1-V100 unit at
36 SU/hr. The ~14 s model load is excluded as it amortises to nothing at production batch size.

| arm | pre-segment SU/km² | SAM SU/km² | **total SU/km²** |
|---|---|---|---|
| 9 km | 0.00087 | 0.00271 | **0.00357** |
| 3 km matched | 0.00078 | 0.00339 | **0.00417** |

**9 km is 1.17x cheaper overall** — pre-segment is a wash (slightly favouring 3 km), and the
edge comes entirely from SAM, which for the same reason as §2 does less work per km² when
prompted less densely. It is buying the cost saving by segmenting more coarsely, so it is not a
saving at all.

Note the inversion against §2, which found pre-segment dominating SAM by ~2x. Once tiles are
spatially batched, **SAM dominates pre-segment by 3-4x**. §2's ratio was measured on cold,
scattered tiles.

## 5. What this changes about the national run

§2 priced pre-segment at 0.059 SU/tile (8 GB) or ~0.030 (4 GB), both on **scattered** tiles.
The national run covers contiguous country, so the warm number applies.

| | s/km² | SU/km² at 1 CPU / 4 GB |
|---|---|---|
| as priced in §2 (scattered) | 5.64 | 0.00313 |
| **spatially batched** | **1.40** | **0.00078** |

Against the §8 recommendation — canola at `prob > 2500`, 24,941 tiles, 224,469 km² —
pre-segment falls from **~700 SU to ~175 SU**. It does not change any go/no-go by itself, since
SAM and feature extraction are untouched, but it removes pre-segment as the leading term and
costs nothing: it is a `sort`, not a code change.

**One incidental result worth keeping: 9 km tiles pre-segment fine in 4 GB.** They ran on
`presegment.pbs` defaults with 0 failures despite holding 9x the pixels of the 3 km tiles that
§2 believed needed 8 GB. Third time this project has been misled by gadi's `Memory Used` line,
which reads at the request rather than the requirement.

## 6. Recommendation

1. **Keep 3 km tiles** — not for cost, but because the model's paddocks were delineated at that
   scale and `samgeo`'s fixed 512 px window makes tile size a segmentation parameter.
2. **Order the national tile list spatially** and give each job a contiguous block, never a
   stride over a shuffled list. Cheapest saving found in this project.
3. **Book pre-segment at 4 GB** whatever the tile size.
4. **If SAM cost ever needs cutting, cut `points_per_side`, not tile size** — that at least
   makes the accuracy/cost trade explicit and measurable instead of hiding it in geometry.
5. Never compare tile geometry across different landscapes. Use `subtile_aois.py`.

## 7. Caveats

The warm/cold split rests on 4 footprints — 32 warm tiles against 4 cold — so the 4.0x is
solid in direction and rough in magnitude. The polygon-density comparison is 4 footprints in
4 states with no hand review of which delineation is *better*; it establishes that tile size
changes the answer, not which answer is right. Whether the cache benefit survives at production
batch size should be re-checked on the first real block.

## 8. Exact commands

```bash
cd src/paddocks
D=/scratch/xe2/cb8590/paddock-species-data/derived
PY=/g/data/xe2/John/geospatenv/bin/python

# cut the 9 km benchmark AOIs into their 3 km children, same ground
$PY subtile_aois.py --aois $D/samgeo/aois_bench9km.csv --n 3 \
    --out $D/samgeo/aois_bench3km_matched.csv

qsub -v AOIS=$D/samgeo/aois_bench3km_matched.csv,OUTDIR=$D/samgeo/bench3km_matched presegment.pbs
qsub -v AOIS=$D/samgeo/aois_bench3km_matched.csv,OUTDIR=$D/samgeo/bench3km_matched sam_segment.pbs

# price both arms off gadi's own charging rule
$PY tile_size_bench.py --dirs 9km=$D/samgeo/bench9km 3km_matched=$D/samgeo/bench3km_matched \
    --report ../../output/tile_size_table.md
```
