# What a national run costs — measured end to end, including inference

Written 2026-08-25 (overnight run). Supersedes the cost sections of
`NATIONAL_INFERENCE_BENCHMARK.md`, which estimated the feature-extraction stage rather than
measuring it and had no inference stage at all because none existed.

**Every number here is billed SU from a completed PBS job, divided by tiles actually produced.**
No stage is extrapolated from walltime, and the express-queue jobs are converted to their
normal-queue equivalent (measured: express bills **6.00 SU/hr per charged CPU**, exactly 3x
normal's 2.00).

Two sample sets, deliberately different:
* **mapdemo** — 240 tile-years, 3 regions x 5 years, the demonstration maps
  (`WALL_TO_WALL_MAPS.md`). Dense cropping country.
* **natbench** — 119 tiles drawn as **12 clusters of 4x4** from the *national* canola mask at
  `prob > 2500`. Clustered, not scattered, because scene-read locality is worth 4.0x
  (`TILE_SIZE_BENCHMARK.md`) and a real run walks the mask in spatial order. A scattered sample
  prices a run nobody would perform.

---

## 1. The headline

| | old estimate | **measured** |
|---|---|---|
| per tile-year, no S1 | 0.129 SU | **0.055 SU** |
| canola at `prob > 2500`, 1 year | ~3,200 SU | **1,378 SU** |

**A national run is about 2.3x cheaper than the last estimate**, and the reason is not a trick:
pre-segment was previously measured on **scattered** tiles at **8 GB**, and it is now run on
spatially batched tiles at **4 GB**. Both halvings are real and both were verified (§3).

**And the union costs almost nothing extra.** At `prob > 2500`:

| mask | tiles | SU / year | SU for 8 years |
|---|---|---|---|
| canola | 24,941 | 1,378 | 11,028 |
| legumes | 17,599 | 973 | 7,782 |
| cereals | 95,910 | 5,301 | 42,408 |
| **union of all three** | **99,465** | **5,497** | **43,980** |

**96.4 % of the union is already in the cereal mask.** Mapping canola and legumes as well as
cereals costs **3.6 % more tiles**, not 44 % more. There is no case for running the crops
separately, and no case for a canola-only product on cost grounds — the decision is simply
whether to fund cereals at all.

**Against the 10 KSU earmarked for this project:** one year of the full three-group national
product is **5,497 SU ≈ 55 %** of the allocation. An 8-year product is **44 KSU — 4.4x the
allocation** and needs its own funding decision. A single year of **canola alone is 1,378 SU
(14 %)**, which fits comfortably.

## 2. Per-tile cost, by stage

3 km tiles, spatially batched, normal-queue equivalent:

| stage | queue booked | SU/tile | share | evidence |
|---|---|---|---|---|
| pre-segment (Fourier-NDWI) | normal, 1 CPU / **4 GB** | **0.0104** | 19 % | 1.24 SU / 119 natbench tiles |
| SAM segmentation | gpuvolta, batched | **0.0334** | **60 %** | 3.98 SU / 119 tiles; 8.27 SU / 240 tiles |
| inference (`predict_tile.py`) | normal, 1 CPU / 6 GB | **0.0114** | 21 % | 11.53 SU / 337 tiles on express ÷ 3 |
| **total** | | **0.0553** | | |

**The old report's central claim about where the money goes is now wrong, and by design.** It
said "your presumption was that SAM would dominate. It does not — pre-segment does, by about
2x." With pre-segment on 4 GB and batched tiles, **SAM now dominates at 60 % of the bill**, and
pre-segment is the cheapest of the three stages. Nothing about SAM changed; pre-segment got 5.7x
cheaper.

**What that implies for further optimisation.** SAM costs 0.0334 SU/tile of which the GPU work
is **3.1 s/tile** (measured: `segment_s` median 2.9 s, `polygonise_s` 0.1 s, model load 12.7 s
paid once for 240 tiles). At gpuvolta's 36 SU/hr, 3.1 s is 0.031 SU — so the stage is already
almost pure GPU time and there is little overhead left to remove. The remaining lever is
**segmenting once per multi-year run instead of once per year**, which is a scientific decision
(boundaries move between seasons) and not a tuning one.

## 3. The two things that made it cheaper, both verified

**Spatial batching.** Pre-segment on the old scattered 12-tile benchmark: 53 s/tile. On batched
tiles here: **median 10 s, mean 19 s**. The natbench sample is *also* clustered and lands at
0.0104 SU/tile, within 1 % of the demo regions — so the saving is not an artefact of the demo
regions being unusually easy.

**4 GB, not 8 GB.** `presegment.pbs` carried a standing note to book 8 GB for 2023+ because a
4 GB job had once been OOM-killed. That note was tested rather than trusted: the same 16
**2024** tiles were rebuilt at 4 GB in a clean output directory.

| | 8 GB | 4 GB |
|---|---|---|
| SU for 16 tiles of 2024 | 0.31 | **0.08** |
| exit status | 0 | **0** |
| memory used | 8.00 GB *(reported at the request)* | **3.08 GB** |

**The 8 GB booking cost 3.9x for identical work.** Note the memory figures: the 8 GB job reports
"8.00 GB used", pinned at the request, which is exactly the misleading reading the standing note
warns about — while the 4 GB job reports a genuine 3.08 GB. A sub-cap reading is informative; a
reading equal to the request is not. **The 8 GB advice applied to the wider AOIs it was measured
on, not to 3 km tiles, and should not be applied to a national run.**

## 4. Walltime, and what actually blocks

Per-tile wall seconds, measured:

| stage | median | mean | serial for 99,465 tiles | realistic |
|---|---|---|---|---|
| pre-segment | 10 s | 19 s | 525 h | **~5 h** across 100 concurrent 1-CPU jobs |
| SAM | 3.1 s | 3.1 s | 86 h | **~4 h** across a few batched GPU jobs |
| inference | 13 s | 19 s | 525 h | **~5 h** across 100 concurrent jobs |
| **total** | | | | **~14 h wall for a national single-year run** |

**Wall-clock is not the constraint; SU is.** A national single-year run is a long day, not a
month. What blocked the old plan — 12 days of copyq for Sentinel-1 — is absent here because
**none of these three stages needs S1** (`NATIONAL_INFERENCE_BENCHMARK.md` §4: S1 adds nothing
to binary canola and +0.029 to the three-group model, and it does not scale). S1 returns to the
critical path only if canola *yield* ships (§7 there), and that remains true.

**Caveat on the wall figures, stated because it cuts the other way from everything else here.**
The demo tiles were read twice within a short window — once by pre-segment, once by inference —
so the second read hit a warm cache. The national sample, read cold, is only modestly slower
(median 12.7 s vs 9.4 s), so the effect is real but small. A production run that schedules
pre-segment and inference over the same tiles back to back gets the warm read legitimately;
one that runs them months apart should budget the cold figure.

## 5. What the product would contain

From the 119-tile national sample of the canola mask, and the 240 demo tile-years:

| | national canola mask | demo regions |
|---|---|---|
| polygons per 3 km tile (mean) | **9.5** | 15.9 |
| median paddock | 25.4 ha | 25.0 ha |
| polygons > 300 ha (tile-scale blobs) | 4.2 % | 1.3 % |

So a national single-year union run yields roughly **99,465 x 9.5 ≈ 0.95 million classified
paddocks**, with class probabilities and quality fields on every row. That is comfortably inside
GeoParquet's range and well past the ~1 M feature point where GPKG becomes slow — the format
recommendation in `NATIONAL_INFERENCE_BENCHMARK.md` §6 stands.

**What the classes look like on the real national mask.** All 119 sampled tiles, 1,131 paddocks,
79,405 ha classified — **74.1 % of the sampled tile area**, 2021, canola mask at `prob > 2500`:

| class | paddocks | share of paddocks | area (ha) | share of area |
|---|---|---|---|---|
| **Grazing** | 345 | 30.5 % | **37,947** | **47.8 %** |
| Cereal | 473 | 41.8 % | 27,774 | 35.0 % |
| Canola | 174 | 15.4 % | 7,402 | 9.3 % |
| Legume | 139 | 12.3 % | 6,283 | 7.9 % |

**The Grazing class fires hard on SAM-segmented geometry** — nearly half the classified area
inside the *canola* mask. That is the direct national-scale check on the provenance confound in
`GRAZING_CLASS.md` §4, and it cuts against the worst-case reading: the model plainly does not
refuse to say Grazing on the geometry it associates with crops.

**But it is not obviously right either, and the number should not be taken as validation.**
`prob > 2500` means "NLUM gives this 250 m pixel at least a 25 % chance of canola", which selects
mixed farming country where real pasture is common — so a high grazing share is plausible. It is
equally consistent with the model over-calling Grazing. Nothing in this sample can separate those
two readings, because there are no labels in it. Canola at 9.3 % of classified area against
NLUM's expectation of 15.8 % of *all* land in those tiles (3.54 Mha of 22.4 Mha) is the right
order of magnitude, but the denominators differ and that too is a sanity check, not a validation.
**Resolving this needs the §6 fix in `GRAZING_CLASS.md`, not a bigger sample.**

**Median confidence is 0.9996.** The model is grossly overconfident on unseen ground, so softmax
probability must not be used as a quality filter — use `n_obs`, `clear_frac`, `area_ha` and
`compactness`, which is why they ship on every row. **47 of 1,131 polygons (4.2 %) exceed 300 ha**
on the national mask, against 1.3 % in the demo regions: tile-scale SAM blobs are commoner in
country with fewer field boundaries, exactly where the product is least reliable.

**Coverage is the honest limitation, not the count.** In the demo regions the classified
polygons cover **49-96 % of the ground** depending on region (`WALL_TO_WALL_MAPS.md`): NSW
Riverina 78-96 %, SA Eyre Peninsula 49-63 %, WA Esperance 52-74 %. The uncovered remainder is
ground SAM did not resolve into a paddock above the 5 ha floor, or paddocks with fewer than 10
clear observations — **not** ground with no crop on it. A national product will have a coverage
map as well as a class map, and the coverage map is the one that decides whether the product is
usable in a given district.

## 6. Recommendation

1. **One year of the union at `prob > 2500` costs 5,497 SU and ~14 h wall.** That is the run to
   propose. It is 55 % of the project allocation, so it is a real decision but not an
   impossible one.
2. **Do not run the crops separately.** The union is 3.6 % more tiles than cereals alone.
3. **Book pre-segment at 4 GB and batch tiles spatially.** Together these are worth 5.7x on that
   stage, and they are the whole reason the total fell from 0.129 to 0.055 SU/tile.
4. **SAM is now the target for any further saving**, and the only lever left is segmenting once
   per multi-year run rather than once per year — a scientific decision about whether paddock
   boundaries are stable enough between seasons, not a tuning knob.
5. **Ship the coverage fraction with the map.** At 49-63 % in SA, a class map alone would
   misrepresent what was actually assessed.
6. **The blocker is no longer compute.** It is `GRAZING_CLASS.md` §4: the Grazing class is
   partly keyed on polygon provenance, and until that is resolved the thing this run would
   produce a million of is a paddock whose non-crop label is not yet trustworthy.
