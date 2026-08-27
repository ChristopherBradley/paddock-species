# What a national run would cost, and what the output should look like

Written 2026-08-09, in answer to two questions: how long would it take to predict over every
NLUM location with canola probability > 1, and the same for cereals; and what format the
outputs should take for the paper and for downstream use.

Measured, not extrapolated: `nlum_tiles.py` counts the tiles, and a 12-tile benchmark
(`presegment.pbs` + `sam_segment.pbs` on real NLUM tiles in 2021) supplies the per-tile cost.

> **Updated 2026-08-10 — two sections have been overtaken by measurement.**
>
> **§5 (no "not a crop" class) — see `NONCROP_CLASS.md`.** The bound §5 says does not exist now
> does: **125 grazing paddocks, 100 % classified as a crop, 79 % as Cereal, median confidence
> 0.999 against 1.000 on real crops.** Option 3 (open-set rejection) is dead — every threshold
> discards as many crop paddocks as it rejects pasture. Option 2 (NLUM-labelled negatives) is
> not viable either: `graz_prob` is uncorrelated with crop-like phenology (r = 0.051), because
> NLUM is a long-run land-use prior and paddocks rotate. **Option 1 is the realistic default.**
>
> **§2 and §8 (per-tile cost) — see `TILE_SIZE_BENCHMARK.md`.** The per-tile costs here were
> measured on *scattered* tiles and overstate pre-segment by **4.0x**: cost is driven by
> Sentinel-2 scene-read locality, so spatially batched tiles run 1.40 s/km² against 5.64.
> Once batched, SAM dominates pre-segment rather than the reverse. Tile size is **not** a free
> cost knob — `samgeo`'s fixed 512 px window makes it a segmentation hyperparameter, and 9 km
> tiles return 23 % fewer, 29 % larger polygons on identical ground. Stay at 3 km.

---

## 1. The short answer

**`prob > 1` is not a filter.** It keeps any 250 m pixel with a greater than 0.01 % chance of
the commodity, and at that setting:

| | tiles (3 km) | mask area | NLUM's own expected area | inflation |
|---|---|---|---|---|
| canola `> 1` | **80,462** | 724,158 km² | 35,432 km² (3.54 Mha) | **20.4×** |
| cereals `> 1` | **142,343** | 1,281,087 km² | 267,560 km² (26.76 Mha) | **4.8×** |
| union of both | **146,152** | — | — | — |

NLUM's expected areas are trustworthy — summing probability × pixel area gives canola 3.55 Mha
and winter cereals 26.9 Mha, which match the national statistics. So the inflation figure is
real: **at `prob > 1` you would segment twenty hectares of Australia for every one hectare of
canola in it.**

**Cost of one year at `prob > 1`, using the measured per-tile numbers in §2:**

| run | tiles | SU | % of the 10 KSU project allocation |
|---|---|---|---|
| canola, no S1 | 80,462 | **~10,400** | **104 %** |
| cereals, with S1 | 142,343 | **~31,200** | **312 %** |
| cereals, no S1 | 142,343 | ~18,400 | 184 % |
| union, with S1 | 146,152 | **~32,000** | **320 %** |

**None of these fit.** And that is for a single season; segmentation is season-specific, so an
8-year product multiplies it.

**What does fit** is a defensible threshold. At `prob > 2500` (25 %), canola's mask is 24,941
tiles and its inflation drops to 6.3×; run without S1 (§4 shows canola does not need it) that
is **~3,200 SU, or 32 % of the allocation** — affordable, and it still covers a mask 6× larger
than the canola actually planted, so it is not a tight collar.

## 2. Measured per-tile cost

12 real NLUM tiles, 3 km, 2021, on gadi 2026-08-09:

| stage | queue | resources | walltime | SU | **SU/tile** |
|---|---|---|---|---|---|
| pre-segment (datacube + Fourier NDWI) | normal | 1 CPU / 8 GB | 10:39 | 0.71 | **0.059** |
| SAM segmentation | gpuvolta | 12 CPU / 1 V100 | 2:14 | 1.34 | 0.112 → **0.030** batched |
| feature extraction (est.) | normal | 1 CPU / 4 GB | — | — | ~0.040 |
| S1 download (measured earlier) | copyq | 1 CPU | 72 s/tile | — | **0.080** |
| **total, no S1** | | | | | **~0.129** |
| **total, with S1** | | | | | **~0.219** |

**Your presumption was that SAM would dominate. It does not — pre-segment does, by about 2×.**
SAM takes **3 s per tile** on a V100; the 0.112 figure above is inflated by the ~49 s model
load amortised over only 12 tiles, and at production batch sizes it falls to ~0.030 SU/tile.
The expensive half is the Sentinel-2 datacube read and the Fourier composite, which is
I/O-bound at ~25 % CPU and cannot be sped up by asking for more cores (measured previously:
quadrupling CPUs cost 4.3× and was not faster).

**Two things got more expensive than the older benchmark said.** Pre-segment was 0.020 SU/tile
in the 2026-08-07 measurement and is 0.059 now — 2× because 2021 tiles need 8 GB rather than
4 GB (charge is `max(ncpus, mem/4GB) × 2 SU/hr`), and the rest because 2021 carries 70-146
scenes per tile against the older years' ~70.

**Correction: do not size memory off the log.** The footer reported 8.00 GB used of 8 GB
requested, and I first read that as "it hit the cap, book more". gadi's `Memory Used` routinely
reads at the request without the job needing it, and since the charge doubles with every
doubling of memory, sizing off that figure silently doubles a 100,000-tile bill. **Book 4 GB and
raise only on a real OOM** (explicit message, or exit 137 with no traceback). At 4 GB the
pre-segment cost is ~0.030 SU/tile, not 0.059 — which halves every total in §1.

## 3. Walltime, and the thing that actually blocks

SU is the binding constraint, but wall-clock has its own answer:

| stage | serial time for 146,152 tiles | realistic |
|---|---|---|
| pre-segment @ 53 s/tile | 2,152 h (90 days) | ~22 h across 100 concurrent 1-CPU jobs |
| SAM @ 3 s/tile | 122 h | ~5 h across a few batched GPU jobs |
| **S1 download @ 72 s/tile** | **2,923 h (122 days)** | **~12 days at 10 concurrent copyq jobs** |

**Sentinel-1 from Microsoft Planetary Computer does not scale to a national run.** The trial
set was 1,149 AOIs and took 3.9 h × 6 shards; 146,152 tiles is 127× that. copyq is a small,
contended queue and it is the one resource here that cannot be parallelised away. If S1 is
wanted nationally, the `dz56` NCI collection (requested 2026-08-08, still pending) stops being
a convenience and becomes a precondition.

## 4. Which map needs S1, and which does not

From `S1_MODEL.md`: S1 adds **+0.029 macro F1 on temporal transfer for the three-group model**,
concentrated in Legume (F1 0.69 → 0.75), and **+0.007 on spatial transfer** — no measurable
spatial benefit. For **binary canola it adds nothing** (0.927 → 0.934, with detection at 5 %
FPR moving in the wrong direction and swinging on noise).

**So: the canola map should be produced without Sentinel-1.** That removes 0.080 SU/tile and
the 12-day copyq problem in one step, and costs nothing measurable in accuracy. S1 is worth its
price only for the three-group product, and mainly for the pulses.

## 5. The gap that matters more than the compute: there is no "not a crop" class

This is the biggest obstacle to a national product and it is not a cost problem.

The model has three classes — Canola, Cereal, Legume — and has **only ever seen those three**.
Every training paddock is an NVT trial site. It has never seen pasture, fallow, rangeland,
vineyard, orchard or forest, and a softmax over three classes cannot say "none of these".

Summing NLUM's expected areas over all 23 commodity surfaces:

| | Mha | share of agricultural land |
|---|---|---|
| grazing (native + sown pasture) | **287.9** | **87.2 %** |
| winter cereals | 26.9 | 8.2 % |
| winter oilseeds | 3.6 | 1.1 % |
| winter legumes | 2.9 | 0.9 % |
| everything else (hay, cotton, sugar, horticulture, rice) | 8.9 | 2.7 % |
| **total** | **330.2** | |

**The three target groups are 10.8 % of NLUM's agricultural land; grazing outnumbers them
roughly 8:1.** Deployed as-is over any of the masks in §1, the model will confidently label
pasture paddocks as Cereal — and there is no number in this project that bounds how often,
because no such paddock has ever been in a test set.

The segmentation benchmark already shows the shape of the problem: of the 12 sampled tiles,
one produced a single 981 ha polygon and another four polygons with a 196 ha median, against
the 57 ha median of the reviewed trial paddocks. Those are rangeland tiles where there are no
field boundaries to find.

**This must be solved before a national map, not after.** Three options, cheapest first:

1. **Reject on the NLUM prior.** Only classify paddocks whose NLUM crop probability clears a
   threshold, and label the rest "not assessed". Free, honest, and it makes the product a
   refinement of NLUM rather than an independent map — which weakens the paper's claim.
2. **Add a fourth class from unlabelled paddocks.** Sample paddocks from strongly-grazing NLUM
   cells, treat them as negatives, and accept that the labels are NLUM's rather than ground
   truth. Cheap, and testable against held-out NVT sites.
3. **Open-set rejection on the existing model** — threshold the max class probability, calibrate
   the threshold on held-out NVT, and report coverage/accuracy trade-off. No new data, but a
   3-class softmax is poorly calibrated for inputs unlike anything it trained on, so this is
   the weakest of the three.

I would do (2) with (1) as the reported fallback, and state the limitation explicitly whatever
happens.

## 6. Output format

Your proposal was three GeoPackages, one per group, plus paddock yield where defensible, plus a
10 m yield raster. Broadly right; four changes.

**One run, not three.** Segment the union mask once and classify every paddock into all three
groups, then split the output by predicted class. Running canola and cereals separately would
segment the overlap twice — and the overlap is nearly total: canola's tiles are a near-subset
of the cereal tiles (union 146,152 against cereals' own 142,343 at `prob > 1`).

**Ship probabilities, not just the class.** One column per group plus the argmax. Every
operating-point result in this project — canola at 5 % FPR, the precision/recall trade — is
unrecoverable from a hard label, and a downstream user who wants high-precision canola needs
the score. Add `n_clear_obs` and the S1/optical availability flags so a user can filter on
input quality rather than trusting every polygon equally.

**Carry the segmentation-quality fields.** `area_ha`, `compactness`, and the flags the review
used (`too_big`, `point_outside`, `too_small`). The hand review threw away 27 % of polygons on
these grounds; a national product cannot be hand-reviewed, so the fields have to travel with
the data and the paper should report accuracy stratified by them.

**On the 10 m yield raster — ship it, but name it for what it is.** The model consumes
*paddock-median* features and emits one value per paddock, so a 10 m raster is a polygon burned
to a constant. It will look like a 10 m yield map and carry paddock-resolution information.
That is fine as a convenience product if it is called `*_paddock_constant_10m.tif` and the
limitation is in the metadata; it is misleading if it is called a 10 m yield map. Genuine
within-paddock yield variation would need per-pixel features and per-pixel labels, and this
project has neither.

Concretely:

| product | format | notes |
|---|---|---|
| paddock polygons + class + probabilities | **GeoParquet** (analysis) + **GPKG** (QGIS) | ~1.75 M polygons at `prob > 1`; GPKG is slow above ~1 M features, GeoParquet is not |
| per-group extracts | GPKG, one per group | what you asked for — derive from the master, do not produce independently |
| yield | column on the polygons, `yield_tha` + `yield_p10`/`yield_p90` | all three groups, but **canola yield needs the S1 layer** — see §7 |
| yield raster | COG, EPSG:3577, 10 m, LZW + overviews | name it `paddock_constant`, one file per year |

CRS **EPSG:3577** throughout (equal-area, so `area_ha` is correct and the 10 m grid is uniform),
with the GPKG copies reprojected to GDA2020 geographic if that suits QGIS better.

## 7. Yield: all three work, but canola only with Sentinel-1

Full numbers in `YIELD_MODEL.md`. Spatial transfer (GroupKFold on site — the split that matches
"predict a paddock we have never seen"), all arms on **identical rows**:

| crop | n | year+state baseline R² | optical R² | **optical + S1 R²** |
|---|---|---|---|---|
| Canola | 571 | 0.290 | 0.271 (−0.019) | **0.371 (+0.081)** |
| Wheat | 791 | 0.325 | 0.583 (+0.258) | **0.603 (+0.278)** |
| Barley | 220 | 0.089 | 0.542 (+0.453) | 0.529 (+0.440) |

**Canola yield is the one that needs S1, and it needs it badly: R² 0.271 → 0.371.** Without
backscatter, satellite features do not beat knowing the year and the state (−0.019); with it
they beat that baseline by +0.081. Cereals barely move (+0.020 wheat, −0.013 barley).

**This is the exact inverse of the classification result**, where S1 did nothing for canola and
everything for pulses. It is also mechanically sensible: canola's *identity* is written in
flowering colour, which CFI already reads, whereas canola's *yield* is a function of biomass
and canopy structure, which is what backscatter measures and what a flowering index saturates
against. `CANOLA_YIELD_CHECK.md` found CFI amplitude tracks canola yield at Spearman 0.38 —
real, but not enough on its own, and now we know what completes it.

**So `yield_tha` is defensible on all three groups, with a condition: canola yield requires the
S1 layer.** RMSE is 0.70 t/ha for canola (on a 2.38 t/ha median), 1.14 for wheat, 1.10 for
barley. Report `yield_p10`/`yield_p90` alongside — an RMSE that is 29 % of the median for
canola is a real number but not a precise one.

A caveat that belongs in the paper, not just the metadata: **the target is NVT trial yield
under trial management, averaged over ~17 varieties — not commercial paddock yield.** Trial
plots generally out-yield commercial crops, so a paddock yield map built on this carries an
unquantified offset, and `CANOLA_FLOWERING_AUDIT.md` shows the support mismatch is not even
reliably one-directional (the surrounding field flowers *harder* than the trial).

## 8. Recommendation

1. **Do not run at `prob > 1`.** Use `prob > 2500` for canola (24,941 tiles, ~3,200 SU without
   S1) and treat cereals separately — cereals are 85,574 tiles even at `prob > 5000`, so a
   national cereal map is a ~15,000 SU proposition and needs its own funding decision.
2. **Solve the "not a crop" class first** (§5). Everything else is wasted until a paddock of
   pasture can be labelled as such.
3. **Canola CLASSIFICATION without S1** — but **canola YIELD needs S1** (§7), so if the product
   carries yield for canola, the S1 layer is back on the critical path and with it the copyq
   problem in §3. Cereal yield does not need it. This is the sharpest planning trade-off here:
   dropping canola yield removes 0.080 SU/tile and 12 days of downloads.
4. **One segmentation run, split afterwards**; probabilities and quality fields on every polygon.
5. **Yield on all three groups**, with canola conditional on S1 and `yield_p10`/`yield_p90` shipped.
6. **Book pre-segment at 4 GB, not 8.** See the correction in §2 — the 8 GB request was made
   on a misread log line and doubles the charge for the same work.
