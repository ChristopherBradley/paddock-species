# The national 2024 run — complete, scored, and it confirms the Riverina

Written 2026-08-27 (early morning). The 99,465-tile national run is finished, a 17 %
gap was found and closed, and the map has been scored against ABS sown area in every cropping
SA2 in Australia.

> **One paragraph.** The national map is built and verified — **1,346,582 polygons, 2.8 GB,
> 98,382 of 99,465 tiles**. Scored against ABS over 132 censused SA2s, **it calls 1.47x as much
> land crop as ABS says was sown**, and the excess is labelled **Cereal (+23.2 points) and Legume
> (+10.8), essentially never Canola (−0.3)**. That is the Riverina result reproduced on a
> continent: 1.59x there, 1.47x here, with the same class signature. **The crop-presence gate,
> not the classifier, is the dominant error, and it is now a national finding rather than a
> two-SA2 one.** Getting there required finding a defect that every existing instrument reported
> as healthy: **17,146 tiles were segmented but never predicted**, because the predictions were
> written before the repair re-segmented them. Uncorrected, that gap produced a national area
> ratio of **0.93** — a number that would have overturned the Riverina finding and been wrong.

---

## 1. What was delivered

| | |
|---|---|
| **national GeoPackage** | `national_2024_crops.gpkg` — **1,346,582 polygons**, 2.8 GB, layer `crops` |
| **CRS** | GDA94 / Australian Albers (EPSG:3577) |
| **tiles predicted** | 98,382 of 99,465 (98.9 %) |
| **spatial index** | built (R-tree on `geom`) — QGIS is unusable on this file without it |
| **ABS comparison** | `output/ABS_COMPARISON_NATIONAL.md` — 520 SA2s touched, 161 matched, 132 well-covered |
| **run definition** | 2024, mask = NLUM winter cereals ∪ oilseeds ∪ legumes at `prob > 2500` |

The merge was verified, not trusted: the sum of per-chunk feature counts across all 374 files is
**1,346,582**, exactly the merged total.

### The map, by class

| class | polygons | area |
|---|---|---|
| Cereal | 443,008 | 17.27 Mha |
| Legume | 119,578 | 4.71 Mha |
| Canola | 88,180 | 3.52 Mha |
| *(abstained)* | 695,816 | 49.08 Mha |

**25.51 Mha classified.** For scale, ABS 2024 national sown area is Cereal 17.63, Canola 3.67,
Legume 3.34 Mha — so the map's national *totals* are close for cereal and canola and ~1.4x for
legume. Do not read that as validation: the map's footprint is the NLUM mask, not Australia, and
only the SA2-level comparison in §4 controls for that properly.

Every polygon carries `area_ha`, `compactness`, `abstain_reason`, `stub`, `year`, `poly_idx`,
`ndvi_amp`, `pred`, `confidence`, `p_canola`, `p_cereal`, `p_legume`, `n_obs`, `clear_frac`,
`treed_frac`, `n_feat_present`. The map ships **permissive** (`--crop-gate-amp 0.35`,
`--max-area-ha 300`) so a reader can tighten the gate afterwards; `pred` is NULL where the model
abstained and `abstain_reason` says why.

### The 1,082 tiles that are not in it

1,083 tiles produced no polygons. The audit attributes **1,082** of them to a single cause —
`no polygon-dates clear enough`, i.e. no observation date on which ≥50 % of a polygon's pixels
were clear — and the count from the audit matches the count from the job logs **exactly**, so
none of them is lost work. They are geographic: **620 sit in two chunks that are 84 % north of
30 °S** (median latitude −27.5), against 0 % for the other 16,526 gap tiles (median −35.9).
Subtropical cloud over country where winter crop is marginal anyway. Verified reproducible by
re-running three of them interactively.

---

## 2. The defect: 17,146 tiles segmented but never predicted

**Found, closed, and the third instance of this failure family in this run — the first that every
existing instrument reported as healthy.**

The §5b repair re-segmented 17,925 tiles, its SAM jobs finishing between **12:47 and 15:56** on
2026-08-26. But 314 of the 320 prediction files had been written between **02:00 and 12:00**.
The predictions for essentially the whole continent were written over ground that had not yet
been re-segmented.

Measured by reading what the prediction files actually *contain*:

- **17,146 tiles were in a chunk's AOI list and absent from that chunk's own GeoPackage.** A
  stricter second pass requiring the tile's `_filt.gpkg` to exist *and* be non-empty independently
  returned **17,145** — so exactly one was a legitimately empty segmentation and the rest were real
- **236 of 320 chunks** affected; 66 held 16,150 of the missing tiles at 97–99 % absent each
- **16,116 of the 17,925 repaired tiles (89.9 %) contributed nothing**, with 14–39 polygons sitting unread in each `_filt.gpkg`

### Why nothing caught it

`status` and `repredict` both ask **whether the segmentation exists on disk**. That is the right
question while a run is in flight and the wrong one afterwards — it is answered by the state of
the world *now*, not by what a job read when it ran. Once the repair finished, segmentation was
genuinely 100 % and `SILENT HOLES` genuinely 0. `repredict` would have said *"no stale
predictions — nothing to redo"*.

**It was visible only as geography.** Victoria — where the repair was concentrated — scored an
area ratio of **0.09** against 1.46 in NSW, and the national median came out at **0.93**: two
opposite failures cancelling into a number that looked like a clean result and would have been
published as one.

### The fix

**Ask the prediction what it contains.** Every polygon carries the `stub` of its tile, so the set
of tiles a chunk actually predicted is recoverable from its own output — no job record, no
timestamp, no trust in an exit status. That is now `run_national.sh audit`. It checks the
**union** of all prediction files rather than each chunk against its own, because a gap re-run
writes recovered tiles into new files and a per-file test would report them missing forever.

The gap itself was closed by predicting **only the missing tiles** — 56 gap chunks
(`chunks_gap/p400–p455.csv` → `pred/p4*.gpkg`) rather than re-running all 236 affected chunks,
which cost **323 SU instead of ~920**. The `p4` prefix means `merge` and `abs_compare.py` pick
them up with no code change. Result: **+314,045 polygons (+30 %)**, 16,064 tiles recovered.

**Generalise it, because it is not the same lesson as the previous two.** The pooler bug was
*items failing inside a job*. The vanishing-job bug was *a job never running at all*. This one is
**a job that ran, exited 0, and read a stale version of its input** — and the only durable
evidence of that is the output's own contents. Compare a stage's outputs to its inputs, never to
the filesystem's current state.

---

## 3. Cost

Attributed by the AOIS path in each log's first line, so this is the national run only. Note
`run_national.sh cost` sums the whole log directory and therefore includes map100, training and
Sentinel-1 work — it is not this run's figure.

| stage | jobs | SU | exited non-zero | SU in those |
|---|---|---|---|---|
| presegment | 585 | 775.4 | 293 | 192.4 |
| presegment (repair) | 72 | 136.6 | 0 | 0.0 |
| sam | 80 | 3,527.3 | 0 | 0.0 |
| sam (repair) | 9 | 599.2 | 0 | 0.0 |
| predict | 326 | 1,255.0 | 6 | 0.1 |
| predict (gap) | 56 | 323.2 | 2 | 22.9 |
| merge ×2 | 2 | 0.2 | 0 | |
| ABS comparison ×3 | 3 | 5.5 | 1 | 1.4 |
| **total** | **1,133** | **6,622.6** | | **216.8** |

Against the ~5,500 original estimate and the ~6,240 revision, **the revision was close** — the
overshoot is the gap re-run, which was not foreseen. **SAM is 62 % of the run** (4,126 SU across
both passes), the GPU queue's 36 SU/hr doing the work.

Two honest caveats:

- The **216.8 SU** column counts jobs that *exited non-zero*. The first attempt's presegment jobs
  exited **0** while dropping 84 % of their tiles, so their SU sits in the "successful" 775.4.
  Silent failures are not separable from exit status — the same lesson, in the accounting.
- The six guard-aborts cost **0.1 SU total** and prevented six chunks of corrupt map. Cheapest
  line in the table by three orders of magnitude.

One efficiency note for next time: the gap chunks were built by sorting the *subset* in block
order, which does not preserve scene locality the way the full list does — consecutive gap tiles
can be 3,000 km apart. Those jobs ran 1–3 h each against the 5–30 min typical of a contiguous
chunk. Cluster a gap list spatially before chunking it.

---

## 4. What the ABS comparison says

Full report: `output/ABS_COMPARISON_NATIONAL.md`. The footprint touches **520 SA2s**; **161
SA2-years** pass the reference-quality filters and **132** are ≥50 % covered, so the map
*censuses* them rather than sampling. The Riverina run's entire claim rested on **15**.

### The headline: 1.47x, and the Riverina was right

**The map calls 1.47x as much land crop as ABS says was sown**, median over the 132 censused
SA2-years. Decomposing that against the observed shares:

| | ABS | diluted | mapped | absorbed |
|---|---|---|---|---|
| Canola | 19.7 % | 13.4 % | 13.1 % | **−0.3** |
| Cereal | 67.3 % | 45.8 % | 69.0 % | **+23.2** |
| Legume | 8.7 % | 5.9 % | 16.7 % | **+10.8** |

`diluted` is the share a *perfect* classifier would report on this footprint — the ABS share
divided by the over-call. `absorbed` is what is left: the share of the map that is excess land
carrying that label. **The excess land is Cereal and Legume and essentially never Canola.**

Set beside the Riverina (`ABS_COMPARISON_100km.md`: ratio 1.59, Cereal +32.4, Legume +5.0,
Canola +0.6), **the structure is the same**. The 102 km result was not a Riverina artefact. The
canola share deficit is almost entirely dilution by the over-call, not misclassification:
**once you divide out the excess land, mapped canola is 13.1 % against a diluted expectation of
13.4 %.**

**This is the answer to the question §6 of `NEXT_STEPS.md` put first, and it is the opposite of
what the uncorrected map said.**

### By state

| state | SA2s | median area ratio | median sample | median canola error |
|---|---|---|---|---|
| Victoria | 37 | **1.77** | 139 % | −10.0 |
| New South Wales | 36 | **1.72** | 150 % | −7.0 |
| Queensland | 10 | **1.62** | 136 % | +0.6 |
| Western Australia | 22 | **1.35** | 113 % | −1.3 |
| South Australia | 28 | 0.76 | 68 % | −1.0 |

The over-call is an **everywhere** number, 1.35–1.77 across four states, with South Australia the
only one under 1. **64 % of censused SA2s over-call by more than 1.25x**; only 3 % are near-total
misses, against 27 % before the gap was closed.

### Composition

| | mapped (median) | ABS (median) |
|---|---|---|
| Canola | 13.1 % | 19.7 % |
| Cereal | 69.0 % | 67.3 % |
| Legume | 16.7 % | 8.7 % |

Canola share error **5.5 points** median absolute, **−4.5** signed; **r = 0.82** across 132 SA2s.
Closing the gap moved r from 0.70 to 0.82 — the correlation was being degraded by the hole, not
just the medians.

### It is not a decision-rule problem

| | argmax share | mean probability | ABS |
|---|---|---|---|
| Canola | 14.0 % | 14.2 % | 19.7 % |
| Cereal | 67.6 % | 67.1 % | 67.3 % |
| Legume | 18.4 % | 18.7 % | 8.7 % |

Argmax and mean probability agree within 0.5 points on every class. **The model is not being
tipped over by an argmax over a skewed prior** — re-weighting priors will not fix the legume
over-call, which at 18.4 % against 8.7 % is now the largest *classification* error in the map,
distinct from the presence over-call it sits inside.

### The gate is a weak lever

| gate | classified ha | canola share error | legume share error |
|---|---|---|---|
| 0.35 | 25,509,480 | 5.9 pts | 9.5 pts |
| 0.45 | 21,374,494 | 5.5 pts | 8.8 pts |
| 0.50 | 19,015,341 | 4.8 pts | 9.3 pts |

Raising the NDVI-amplitude gate from 0.35 to 0.50 discards **25 % of the classified area** to buy
1.1 points of canola error and 0.2 of legume. In the Riverina, `CONFIDENCE_FILTER.md` found the
gate recovered most of the error; nationally it does not. **A gate on amplitude is not the fix** —
which is what §6.2 of `NEXT_STEPS.md` already argued on phenological grounds.

### The precision floor

ABS and ABARES disagree with each other by a median of **6.8 %** on national sown area. The
canola error (5.5 points on a 19.7 % base, ~28 % relative) and the legume error (8.0 points on
8.7 %, ~92 % relative) are both well outside that floor. Both are real.

### Coverage

**650,749 of 1,345,129 polygons classified (48.4 %), 34.4 % by area.**

| abstain reason | polygons | ha |
|---|---|---|
| `unsegmented_blob` | 47,552 | **37,361,221** |
| `no_crop_signal` | 269,097 | 9,690,880 |
| `area_below_min` | 338,682 | 932,785 |
| `too_few_observations` | 39,049 | 736,719 |

`unsegmented_blob` is **37 Mha across 48k polygons** — ~785 ha each, far over the 300 ha cap, and
**four times every other abstain reason combined**. That is SAM failing to split large tracts. It
does not inflate the area ratio (it is excluded from the numerator), but it is the largest single
block of unusable ground in the product.

---

## 5. Where the files are, and how to get them locally

`derived/` lives on **`/scratch`, which NCI purges after ~100 days** — pull anything worth keeping.

| what | path on gadi |
|---|---|
| **national map** | `/scratch/xe2/cb8590/paddock-species-data/derived/national2024/national_2024_crops.gpkg` |
| per-chunk predictions | `/scratch/xe2/cb8590/paddock-species-data/derived/national2024/pred/p*.gpkg` (374) |
| AOI list | `/scratch/xe2/cb8590/paddock-species-data/derived/national2024/aois.csv` |
| chunk definitions | `.../national2024/chunks/p*.csv` and `.../chunks_gap/p4*.csv` |
| segmentation (55 GB) | `/scratch/xe2/cb8590/paddock-species-data/derived/national2024/samgeo/` |
| model | `/scratch/xe2/cb8590/paddock-species-data/derived/models/group3_map.joblib` |
| reference series | `/scratch/xe2/cb8590/paddock-species-data/derived/abs/` |
| PBS logs | `/scratch/xe2/cb8590/paddock-species-logs/` |
| ABS report | `~/Projects/paddock-species/output/ABS_COMPARISON_NATIONAL.md` (in the repo) |

### Copy the map to your laptop

**Do not** use `sync_to_gadi.sh pull` for this — it brings the whole `derived/` tree, and
`national2024/` alone is **~57 GB** (55 GB of it segmentation rasters). Pull the one file, over
the **data-mover node** as NCI policy requires:

```bash
mkdir -p data/derived/national2024
rsync -avzP \
  cb8590@gadi-dm.nci.org.au:/scratch/xe2/cb8590/paddock-species-data/derived/national2024/national_2024_crops.gpkg \
  data/derived/national2024/
```

2.8 GB — a few minutes on a decent link. Open in QGIS: **Layer → Add Layer → Add Vector Layer**,
select the `.gpkg`, layer `crops`. Useful filters once loaded:

```
-- categorise by class
"pred"

-- the area-accurate view; §4 says this costs 25 % of the area for 1.1 points
"ndvi_amp" > 0.5 AND "pred" IS NOT NULL

-- only what the model committed to
"pred" IS NOT NULL AND "confidence" > 0.7

-- the 37 Mha of unsplit blobs — the biggest single defect in the product
"abstain_reason" = 'unsegmented_blob'
```

`./sync/sync_to_gadi.sh pull-code` brings the repo's `output/` back without the data.

---

## 6. What to do next

1. **The gate is the problem, and amplitude is not the fix.** §4 settles this nationally: the map
   over-calls crop presence by 1.47x, the excess is Cereal and Legume, and raising the amplitude
   gate costs 25 % of the area to buy 1.1 points. `NEXT_STEPS.md` §6.2's two candidates stand —
   **phenological shape** (one green-up, at the right time, ending in a hard senescence, fittable
   on the 3,439 NVT presence labels) and **Sentinel-1 for presence rather than type**. The
   acceptance criterion there is unchanged and should be kept: ratio toward 1.0 *while* presence
   recall on NVT stays ≥91.6 %.
2. **Legume is now the largest classification error** — 18.4 % mapped against 8.7 % ABS, and the
   argmax/probability agreement rules out a prior correction. This is separate from the presence
   over-call and needs its own diagnosis.
3. **`unsegmented_blob` holds 37 Mha**, four times every other abstain reason combined. Ruling out
   SAM *parameter* tuning (commit 8283a8d) did not rule out a size-aware second pass over blobs
   that exceed the 300 ha cap.
4. **Run `run_national.sh audit` before believing any future run.** It is the only check that sees
   a prediction written over a stale input.
5. **Re-read `SENTINEL1_VALUE.md` before spending.** Its case rested on a legume gain; §4 shows
   10.8 of the 16.7 points of mapped legume are excess land rather than misclassified crop, so
   most of that error is the gate. Fix the gate, re-measure the legume residual, then decide.
