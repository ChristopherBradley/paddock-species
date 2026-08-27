# Where the project stands, and what to do next

Rewritten 2026-08-25 (evening), after the 102 km Riverina run finished and was scored against ABS.
The long history is `output/archive/NEXT_STEPS_2026-08-25_full.md`. The afternoon version was
never committed and this rewrite overwrote it; `output/archive/NEXT_STEPS_2026-08-25_afternoon.md`
is a **reconstruction** of it, faithful in content but not verified byte-for-byte against the
original, which no longer exists.

> **One paragraph.** The 102 km, 9-year Riverina run is complete — 10,404 tile-years segmented,
> 246,885 polygons classified — and it was scored against ABS sown area over SA2s the map now
> *censuses* rather than samples. **The encouraging result from the 1.6 % sample did not survive.**
> Canola share is under-mapped by **12.2 points** (23.4 % against ABS 36.2 %), and the reason is
> not the classifier: the map calls **1.59x as much land "crop" as ABS says was sown**, and those
> extra hectares sit in the denominator of every share. Decomposing it, the excess land is
> labelled **Cereal (+32.4 points) and Legume (+5.0), almost never Canola (+0.6)**. So the
> dominant error in this map is the **crop-presence gate**, not the crop classifier — and that is
> good news, because the gate is a threshold on polygons that already exist, not a new dataset.
> **Do not launch the national run, and do not buy Sentinel-1, until the gate is fixed.**

---

## 1. What is settled

| | |
|---|---|
| **3-class crop model** | macro F1 0.821 temporal / 0.823 spatial; canola at 5 % FPR 89.0 % |
| **Inference stage** | `predict_tile.py` — tile read once, every polygon a zonal statistic |
| **102 km x 9-year run** | **complete** — 10,404 tile-years, 247,008 polygon-years |
| **Polygon stability** | 25-100 ha band reproduces at IoU 0.92-0.94 across nine independent years |
| **Rotation plausibility** | stable paddocks rotate, unstable ones repeat — §5 |
| **National cost** | **0.0553 SU/tile**; union of all three crops **5,497 SU/year**, ~14 h wall |
| **Grazing class** | **retired** — see `PRESENCE_ONLY_LABELS.md` |
| **Geometry as the cause** | **ruled out** — identical 86 holdout rows moved 36.0 % -> 36.0 % (archived §0) |
| **The map over-calls crop area** | **1.59x**, measured against ABS — §4, and the top priority |
| **Spend so far** | **6,770 SU** billed all-time, **5,253 of it on 2026-08-26** (the national run), against a **50 KSU** budget. Repair adds ~990. |

## 2. The design that is being validated

Full argument in **`PRESENCE_ONLY_LABELS.md`**; three changes, all now built and exercised at
scale:

1. **Segmentability is a mask, not a class.** Classify only SAM polygons at paddock scale
   (<= 300 ha + the compactness filter). As a pure geometry detector it keeps **77.9 %** of known
   crop paddocks and rejects **65 %** of pasture in cropping country. It costs 22 % of real crop
   paddocks — quote that with any coverage figure.
2. **The classifier abstains.** 3-class model behind the Stage-2 crop-presence gate (NDVI
   amplitude >= 0.35). A paddock that fails the gate is left blank, carrying its reason.
3. **Validation is aggregate and independent.** ABS by SA2, ABARES by state — neither depends on
   NVT or AgriWebb. **This is the leg that has now reported, and it does not pass.**

## 3. Reference data — downloaded, tidied, cross-checked

In `derived/abs/`, fetchers in `src/paddocks/`:

| source | resolution | years | script |
|---|---|---|---|
| ABS `AG_BROADACRE` | **SA2** (318 regions) | 2022-2024 only | `abs_fetch.py` |
| ABARES Australian Crop Report | state | **1989-2026** | `abares_fetch.py` |
| ABS ASGS SA2 boundaries (2021, GDA2020) | — | — | downloaded, 50 MB |

ABS is the spatially detailed one but starts at 2022-23. **ABARES is the only source covering the
2020 and 2021 maps**, and it carries ABARES' own quality flags (`final` / `s` / `f`), which are
preserved — judging a map against a *forecast* is a different claim from judging it against
history.

**The precision floor.** ABS and ABARES disagree with *each other* by a median **6.8 %** on
national sown area. Any map-vs-reference gap smaller than that is inside the noise between two
official agencies. Everything reported in §4 is far outside it.

## 4. The validation, on ground the map censuses — `ABS_COMPARISON_100km.md`

The afternoon report (`ABS_COMPARISON.md`, now banner-marked **superseded**) scored 9 SA2-years at
a median **1.56 %** sample and found a 4.6-point canola error, which read as encouraging. The same
script over the 102 km box covers **63-77 %** of Junee and Temora, so those SA2s are censused, not
sampled. `abs_compare.py --aois` now reconstructs the tile grid exactly and reports the covered
fraction per row, because the old `sample_frac` (mapped crop / ABS crop) is not a footprint at all
— it moves when the model over-calls crop, so a map that hallucinates canola looks like a map with
better coverage.

**Two findings, and they are the same finding.**

**(a) Canola is under-mapped, consistently.** Over the 6 SA2-years at >= 50 % cover: mapped
**23.4 %** against ABS **36.2 %**, median absolute error **12.2 points**, and the sign is negative
in **14 of the 15** substantial SA2-years across all three years. (The exception is West Wyalong
2024, at 1 % cover.) On the small sample this looked like 4.6 points of noise; at census scale it
is a bias.

**(b) The map calls 1.59x as much land crop as ABS says was sown.** Now measurable, because the
footprint is known:

| SA2 | year | cover | crop share of covered land | ABS crop share of SA2 | ratio |
|---|---|---|---|---|---|
| Junee | 2023 | 63 % | **73 %** | 34 % | **2.17** |
| Junee | 2024 | 63 % | 73 % | 39 % | 1.89 |
| Junee | 2022 | 63 % | 64 % | 37 % | 1.75 |
| Temora | 2023 | 77 % | 61 % | 43 % | 1.42 |
| Temora | 2024 | 77 % | 65 % | 48 % | 1.36 |
| Temora | 2022 | 77 % | 47 % | 40 % | 1.18 |

And the classifier **abstained on 26 % of the mapped area besides**, so 1.59x is a floor. It is
also the opposite of what the mask predicts: segmentability discards 22 % of *real* crop paddocks,
so the map should undercount hectares, not overcount them by half again.

**(c) They are one result, and the decomposition says which part is broken.** Extra hectares sit
in the denominator of every share, so even a perfect classifier would read `ABS share / 1.59` on
this footprint. What is left over is the share of the map that is excess land wearing that label:

| | ABS | diluted by the over-call | mapped | absorbed excess |
|---|---|---|---|---|
| Canola | 36.2 % | 22.9 % | 23.4 % | **+0.6** |
| Cereal | 59.6 % | 37.6 % | 70.0 % | **+32.4** |
| Legume | 3.5 % | 2.2 % | 7.2 % | **+5.0** |

The residuals sum to 37 points, which is exactly the excess (1 − 1/1.59) — the arithmetic closes.
**Read it as: the canola share deficit is fully explained by the over-call, and the over-called
land is being labelled Cereal and Legume.** There is no evidence here of a canola classification
problem at all.

**(d) It is not a decision-rule problem.** Area-weighted mean class probability tracks the argmax
share to within 0.4 points (canola 23.2 % vs 23.0 %). The model is not narrowly losing canola at
the argmax; it is confidently calling this ground cereal. A class-prior correction would not move
it, and would in any case be fitting to the validation set.

**(e) The gate is the knob, and the sweep shows it.** Raising the NDVI-amplitude gate from 0.35 to
0.50 drops classified area from 5.66 Mha to 4.55 Mha (-20 %) and halves the canola share error
(11.0 -> 6.6 points). **This must not be used to choose the threshold** — that would make ABS a
training set and destroy the only independent validation the project has. It is evidence about the
mechanism, nothing more.

**What could still be wrong with (b), stated honestly.** `expected` spreads each SA2's sown area
evenly over the covered fraction, so if the box sits on the more intensively cropped part of an
SA2 the ratio is inflated. Temora, the better-covered of the two at 77 %, does show the smaller
ratios (1.18-1.42 against Junee's 1.75-2.17), which is consistent with some of that. But both are
above 1 in all three years, and 6.8 % is the noise floor.

## 4b. A per-paddock score does recover an ABS-consistent map — `CONFIDENCE_FILTER.md`

Asked overnight: rather than deleting the excess, attach a score and let the reader filter —
strict for an area-accurate map, permissive for "everything with a crop-like season, including
pasture sown and then grazed rather than harvested". **Measured, and it works — but only for two
of the five candidate scores, and the control is what shows it.**

The control matters because any filter that removes area moves the ratio toward 1.0. Removing
polygons **at random** to the same retained area moves the ratio exactly as intended and leaves
the canola error at **12.1-12.5 points at every level** — it never improves. So the bar is clear:

| score | threshold | area kept | area ratio | canola err | vs random |
|---|---|---|---|---|---|
| `confidence` (max class prob) | 1.0 | 62 % | 0.98 | **4.8** | **-7.3 pts** |
| **`ndvi_amp`** | **0.60** | **59 %** | **0.98** | **5.8** | **-6.7 pts** |
| `n_obs` | 33 | 40 % | 0.90 | 6.0 | -6.2 pts |
| `median_iou` | 0.66 | 65 % | 1.04 | 11.1 | -1.2 pts |
| `n_years` | 7 | 60 % | 0.97 | 11.2 | -1.1 pts |

**`ndvi_amp` is the one to ship as the headline score.** `confidence` reaches a marginally lower
canola error but it *worsens* cereal (8.8 against 7.5 unfiltered) and it saturates — 62 % of the
mapped area sits at confidence exactly 1.0, so above that the score has no resolution at all.
`ndvi_amp` improves all three classes at once (canola 12.2 → 5.1, cereal 7.5 → 4.0, legume 4.1 →
2.1 at its 0.583 operating point) and is monotone.

**The negative result is as useful as the positive one. Geometric stability does not find the
excess.** `n_years` and `median_iou` — the project's only quality signals that owe nothing to the
spectra — barely beat random. They are excellent measures of whether a *boundary* is real and
say nothing about whether a *crop* is there. **They are two different confidences and must ship
as two different columns**, never blended into one score.

**What the marginal land looks like** is consistent with the sown-but-not-harvested reading: the
low-`ndvi_amp` half has the same median size (22 vs 26 ha) and the same segmentation stability
(7 years both halves), but a weaker season (0.52 vs 0.68) and a *higher* cereal share (74 % vs
67 %). Real paddocks, weaker seasons, disproportionately called cereal.

**This does not license hard-coding 0.583.** Choosing the threshold that matches ABS would make
ABS a training set and destroy the only independent validation the project has. The map ships
permissive with the score attached; the ABS-matched threshold is documented, not applied.

## 4c. The consensus paddock layer — `CONSENSUS_LAYER.md`

`derived/map100/consensus_crops.gpkg`: one polygon per paddock that at least 5 of the 9 annual
segmentations agreed on, filtered to 5-300 ha — **the same bounds `predict_tile.py` uses**, so
the layer never contains a paddock the annual layers could not have classified.

| | polygons | ha |
|---|---|---|
| raw consensus | 25,082 | 931,602 |
| below 5 ha | −2,178 | −7,138 |
| above 300 ha (blobs) | −133 | −101,110 |
| **kept** | **22,771** | **823,354** |

**133 blob polygons — 0.5 % of the layer — carried 11 % of its area.** An unfiltered consensus
layer looks fine by polygon count and is dominated by blobs by area, which is exactly the trap
the size filter exists for.

Each polygon carries `crop_2017 … crop_2025`, `conf_<year>`, and a rotation summary
(`crop_seq` like `W-C-W-.-L`, `n_classes`, `canola_years`, `modal_crop`). Of the 18,310 paddocks
classified in 4+ years, **54.8 % show 2 distinct classes and 29.1 % show 3**, with 16.1 % stuck on
one — the rotation signature, now attached to geometry rather than sitting in a report.

Two things surfaced while building it, both fixed at source:
* the consensus layer had **no `paddock_id`**, so nothing could be joined to it — it could never
  have been told what it grew;
* **1,011 paddock-years (0.50 %) hold two polygons**, where one season's segmentation split a
  paddock the others kept whole, and **26.3 % of those splits were given different classes**.
  Resolved by area, not by row order, so a 2 ha sliver cannot overrule the 40 ha paddock.

## 5. The 102 km run — complete

Driver `src/paddocks/run_map100.sh` (`aois` -> `presegment` -> `sam` -> `predict`), every step
idempotent. Riverina, 147.16 E / 34.73 S, 34 x 34 tiles of 3 km, years 2017-2025.

| | |
|---|---|
| cost | **597 SU** billed today, the run's share of it dominant — against a ~575 SU estimate |
| segmentation | **10,404 / 10,404** tile-years, 0 failures |
| inference | 30 chunks, **246,885 polygons**, 71.5 % classified (74.2 % by area) |
| classified share by year | 52.5 % (2018) to 78.5 % (2025) — see below |

**The two weak years are 2017 and 2018.**

| year | polygons | classified | `no_crop_signal` | mean n_obs | mean clear_frac | mean ndvi_amp |
|---|---|---|---|---|---|---|
| 2017 | 25,604 | 59.0 % | 23.7 % | **24.7** | 0.71 | 0.46 |
| **2018** | **22,467** | **52.5 %** | **27.0 %** | 35.2 | 0.68 | **0.42** |
| 2019 | 29,231 | 73.4 % | 10.5 % | 40.7 | 0.76 | 0.56 |
| 2020 | 30,445 | 77.8 % | 6.1 % | 29.5 | **0.56** | 0.60 |
| 2021 | 30,254 | 73.8 % | 9.7 % | 34.6 | 0.65 | 0.57 |
| 2022 | 24,728 | 69.4 % | 12.7 % | 25.1 | **0.50** | 0.52 |
| 2023 | 26,769 | 76.6 % | 7.4 % | 32.4 | 0.61 | 0.56 |
| 2024 | 27,120 | 76.8 % | 7.2 % | 35.9 | 0.67 | 0.60 |
| 2025 | 30,267 | 78.5 % | 4.9 % | 43.5 | 0.66 | **0.62** |

2017 has a known cause: Sentinel-2B only became operational mid-2017, so the revisit is roughly
halved, and it yields ~4,600 fewer polygons than 2019-2021 on the fewest observations of any year.

**2018 is the lower of the two, and the cause is the season, not the satellite — measured, not
assumed.** 2018 has *more* observations than 2017, 2020 or 2022 (35.2) and a mid-range clear
fraction (0.68); only 1.3 % of its polygons fail on `too_few_observations`. What it has is **the
lowest mean NDVI amplitude of the nine years, 0.42 against 0.56-0.62 in normal years**, and the
highest `no_crop_signal` rate, 27.0 %. 2018 sits inside the 2017-2019 eastern-Australian drought.

**This is the one clear piece of evidence that the gate works at all.** It rejects most in the
year with least growth and least in 2025, the greenest, and it does so on years with plenty of
clear imagery — so it is tracking the season rather than the sensor. Read together with §4, the
verdict on the gate is *calibrated too loose*, not *broken*, which is what makes §6.1 a
recalibration rather than a redesign. The counter-example is worth noting too: 2020 has the
**worst** clear fraction of any year (0.56) and the second-*highest* classified share, so clear
fraction is not what drives this.

**Year-to-year polygon stability — `POLYGON_STABILITY.md`.** 247,008 polygon-years over 1,156
tiles resolve to 58,457 distinct paddocks; the median polygon is found in **7 of 9 years** at
median IoU **0.84**, and 26.9 % in all nine. Stability peaks in the **25-50 ha** band (median 8
years, IoU 0.94) and falls away at both ends — the **>300 ha blobs are the least reproducible
thing in the dataset**, an independent geometric corroboration of the `--max-area-ha 300` mask on
247k polygons with no spectral information and no labels.

**Stable polygons rotate; unstable ones repeat.** This is the question the nine years were run
for. A paddock that reads the same class nine years running is keying on something static, like
soil colour; a real rotation is 2-3 classes with canola in a minority of years.

| | n | median distinct classes | same class every year | canola in 1-3 yrs |
|---|---|---|---|---|
| stable (found in 5+ years) | 19,788 | 2.0 | **16.2 %** | **63.3 %** |
| unstable | 1,667 | 2.0 | 33.3 % | 44.8 % |

Geometric stability, computed with no reference to the imagery's spectra, predicts a more
plausible crop sequence — an internal consistency check that costs nothing and that the map
passes.

**Consensus layer — done.** `derived/map100/consensus.gpkg`, **25,082 polygons** present in at
least 5 of the 9 years, each taken from the year in which it was largest: the geometry a
multi-year product should use. Two things worth carrying forward from building it:

- **It cost 0.61 SU and 9 minutes**, against a standing estimate in the code of ~4 hours. That
  estimate came from timing a single cold-cache GeoPackage open at 1.5 s; over 10,400 of them the
  real figure is ~30 ms. Both comments have been corrected — a wrong cost estimate in a comment
  is what stops a cheap step from being run.
- **It was picking the wrong representative.** The pick grouped on `(region, cell, idx)`, but
  `idx` is a polygon's slot number *inside one year's file*, so the same `idx` is different ground
  in different years: **86.8 % of the groups mixed more than one paddock**, and the layer would
  have held 33,701 "largest thing ever to occupy slot i" polygons instead of 25,082 paddocks.
  Fixed to group on `paddock_id`, the union-find identity that survives the years.

## 5b. The national 2024 run — launched 2026-08-25 ~23:50

`src/paddocks/run_national.sh`. **2024, not 2025**, and the reason is the reference data: ABS
publishes sown area by SA2 for 2022-2024 only, and ABARES' 2025 state figures still carry the `f`
forecast flag. 2025 has the better imagery — 43.5 clear observations per paddock against 35.9,
and the highest classified share of the nine Riverina years — and no way to score it. A map that
cannot be checked is not the one to spend 5 KSU on.

| | |
|---|---|
| mask | union of NLUM winter cereals + oilseeds + legumes at `prob > 2500` |
| tiles | **99,465** (895,185 km², 2.7x NLUM's own expected 33.1 Mha of crop) |
| geography | 94.5 % south of 25 °S; WA wheatbelt 21,661 tiles, eastern belt 59,054 |
| predicted cost | **~5,500 SU** at the measured 0.0553 SU/tile |
| structure | 320 chunks -> 320 presegment / 40 GPU SAM / 320 predict, fully chained |
| output | `derived/national2024/national_2024_crops.gpkg` |

**It ships permissive.** `--crop-gate-amp 0.35`, `--max-area-ha 300`, and every polygon carries
`ndvi_amp`, `confidence`, the three class probabilities and its `abstain_reason`. §4b is the
reason: the score is what lets a reader choose between an area-accurate map and one that includes
the sown-but-not-harvested land. Baking in the ABS-matched threshold would spend the validation.

### The first attempt failed silently, and that is the lesson worth keeping

The run was first submitted as **320 jobs all at once**. Every one of them started, and every one
exited **0**. They had produced almost nothing:

```
FAILED nlum_2024_r933_c961: (psycopg2.OperationalError)
    FATAL:  no more connections allowed (max_client_conn)
```

**8,757 tiles FAILED against 1,608 OK — 84 % — and PBS reported success on every chunk**, because
each AOI is individually wrapped in `try/except` so one bad tile cannot kill a batch. That is the
right behaviour for a bad tile and the wrong behaviour for a systemic failure, and nothing
downstream would have noticed: the composites would simply have been absent, SAM would have found
nothing to segment, and the national map would have had holes where no error was ever raised.

Two causes, both now fixed in `samgeo_segment.py`:

1. **A `Datacube` connection was opened per TILE, not per job** — 310 open/close cycles per chunk,
   ~99,000 across the run, against a pooler shared with every other DEA user on gadi. Now one
   connection per process.
2. **No retry.** A transient pooler exhaustion was indistinguishable from a bad AOI, so the tile
   was dropped. Now `with_retry` backs off 20 s doubling to ~10 min, with jitter — the failure is
   *correlated* across jobs, so an un-jittered sleep would send the whole fleet back in lockstep.

And the submission itself is now **laned**: at most 64 chunks run at once, each lane a serial
chain. Verified before relaunching — a single chunk gave **16/16 OK**, and the relaunched fleet
gave **2,918 OK and 0 FAILED across 64 concurrent jobs**.

**Generalise it: a per-item `try/except` inside a batch job converts a systemic failure into a
silent one.** Any stage that swallows per-item errors needs a job-level check that the count of
successes is what was asked for — exit 0 is not evidence.

### The second attempt failed silently too, in a different place (found 2026-08-26 09:30)

The relaunch fixed the pooler and then lost **17.5 % of the continent** to an unrelated fault.
Checked at 09:30 the next morning: **81,540 of 99,465 composites (82.0 %)**, and **74 of 320
chunks below 98 % segmented**. Every PBS job had again reported success.

**56 chunks — p264 to p319 — never ran a single tile.** Their presegment jobs were each
**destroyed at the instant their dependency was satisfied**, rather than being released into the
queue. The PBS records are unambiguous: every one has an `mtime` 7-10 s *before* its parent's
completion.

| dead job | died | parent | parent finished | parent exit |
|---|---|---|---|---|
| `ps_p264` | 05:15:27 | `ps_p200` | 05:15:36 | 0 |
| `ps_p300` | 04:02:34 | `ps_p236` | 04:02:41 | 0 |
| `ps_p316` | 05:31:27 | `ps_p252` | 05:31:36 | −29 |

They left **no log, no `Exit_status` and no comment**. The parent's exit status is irrelevant
(both 0 and −29 appear), so `afterany` behaved correctly — the failure is the requeue on the far
side of it.

**Why the requeue was refused is inferred, not proven.** PBS recorded no reason. The evidence
points at the per-user queued-job ceiling, `queued_jobs_threshold = [u:PBS_GENERIC=200]`
(`qstat -Qf normal-exec`): all 320 jobs sat in the queue from submit time, because **a dependency
staggers when a job STARTS, not when it is QUEUED** — which is exactly what `LANES` does not fix.
The casualties are precisely the last job in each of lanes 8-63, the deepest in their chains and
released last while ~300 siblings still occupied the queue; the 5th jobs of lanes 0-7
(p256-p263) released earlier and survived. **`Hold_Types = s` is not evidence of any of this** —
it is how PBS marks any dependency hold, healthy ones included, and it was misread as a smoking
gun once already.

**The gap was contiguous and it was Victoria**, because chunks are block-sorted for scene
locality:

| region | tiles | share |
|---|---|---|
| **VIC** | **15,709** | **90.5 %** |
| SA | 1,383 | 8.0 % |
| TAS | 263 | 1.5 % |

**Then predict ran over it anyway and exited 0.** `afterany` releases a predict job whether or
not its SAM job produced anything, and `predict_tile.py` treated a missing `_filt.gpkg` as one
skippable tile — the right response to one unsegmentable tile and the wrong one to 307 of them.
**63 chunks were predicted over 15,419 tiles that had never been segmented**, each writing a
plausible GeoPackage from the handful of tiles that did exist. `p316` classified 42 polygons from
**3 tiles of 310 in 2m13s** and printed `Done predict_tile`. A `merge` would have produced a
clean-looking national map with the Wimmera and Mallee cut out of it — and that map would have
gone straight into the ABS comparison that 2024 was chosen for.

**A 17th failure mode: the monitoring read zero.** `run_national.sh status` was reporting
`composites: 0` throughout. `ls $POLY/*.tif` over 162,334 files exceeds `ARG_MAX`, so `ls` died
and `wc -l` counted an empty pipe — **the one instrument that would have shown the gap read zero
whether the true count was 0 or 81,540.** Worse than no check at all.

**Fixed, all of it:**

* `status` uses `find` (streams, never builds an argv) and now reports percentages plus two
  derived counts: chunks below 98 % segmented, and — the one that matters — **chunks PREDICTED
  over incomplete segmentation**.
* `samgeo_segment.py segment` gained `--max-missing-frac` (default 0.10). A missing *input* is
  no longer a warning: 310 absent composites now exits non-zero instead of printing "nothing to
  segment" and returning 0. This is distinct from `--max-fail-frac`, which catches a stage
  failing on its own items; this catches **the stage before it never having run**.
* `predict_tile.py` gained `--max-missing-frac` (default 0.10), checked **before** the datacube
  connection is opened, so an aborting job costs nothing and never touches the shared pooler.
* `run_national.sh presegment` measures real queue headroom (`MAXQ`, default 180) and stops at
  it rather than feeding a queue deep enough for a release to be refused. It also skips chunks
  that are already fully composited, so re-running genuinely resumes.
* `merge` **refuses** to build a national GeoPackage while any chunk is below 98 % segmented
  (override with `FORCE_MERGE=1`). A merge is the last point at which a gap is still attributable
  to a chunk; after it, the hole is just missing ground.
* New `repair` / `repair-check` / `repair-sam` / `repredict` subcommands, which re-derive what is
  missing **from the files on disk rather than from any job record** — so they are correct no
  matter how the gap was produced.

**Generalise this one too, because it is not the same lesson as the pooler.** The pooler bug was
*items failing inside a job*. This was *a job never running at all*, which no in-job assertion
can catch — the code never executes. **The check has to live in the stage downstream, asking
whether its input is there, and in the submitter, which must not build a queue deeper than the
scheduler will honour.** And a monitoring command that can fail silently is a liability, not a
safeguard: `status` reported zero for hours and nobody doubted it.

**Repair in flight (submitted 09:5x, 2026-08-26).** 17,925 tiles missing a composite → **72
presegment jobs** at 250 tiles each (6 h walltime, against the 3 h that killed 16 of the
originals), in **24 lanes** rather than 64 — shallower chains mean fewer releases under a loaded
queue. Then **9 repair SAM jobs**, then `repredict` drops the 63 stale prediction files so
`predict` resubmits exactly those chunks. Estimated **~990 SU**, taking the run to ~6,240 against
the ~5,500 estimate. `repair-check` watches for the original failure recurring: a job that is
neither live nor logged did not run.

## 6. What to do next, in order

1. **Land the national 2024 run and score it the way the Riverina run was scored.**
   **BLOCKED until the repair in §5b lands** — 17.5 % of the run, 90 % of it Victoria, was
   never segmented, and 63 chunks hold predictions written over that empty ground. `merge`
   now refuses while any chunk is incomplete, so this cannot be started by accident. Watch
   it with `run_national.sh status` (the `SILENT HOLES` line must reach 0) and
   `run_national.sh repair-check`. This is the
   one that matters: `abs_compare.py --aois` over the national predictions gives an area ratio and
   a share error in **every cropping SA2 in Australia**, not two. The whole of §4 rests on Junee
   and Temora, and the open question is whether **1.59x is a Riverina number or an everywhere
   number** — a WA wheatbelt paddock and a Riverina paddock do not have the same season, and the
   `ndvi_amp` threshold that recovers ABS in §4b is calibrated on one of them. `map_table.py`
   builds the attribute cache for this in one pass; everything after it is seconds.
2. **Fix the crop-presence gate properly.** §4b shows a *filter* recovers most of the error, which
   is a workaround, not a fix: it costs 40 % of the mapped area to get there. The gate itself
   should not be admitting that land.
   **It must be fitted on something other than ABS** — ABS is the only independent validation this
   project has and spending it as a training signal leaves nothing to check the result with.
   - **Phenology shape, not amplitude — tried, 2026-08-27, `PHENOLOGY_GATE.md`.** `phenology_gate.py`
     fits a peak-anchored green-up + post-harvest-senescence gate on the NVT presence labels, and
     `run_map100.sh predict-shapegate` re-scored the full 100 km x 9-year Riverina run with it
     stacked on the amplitude gate (120 SU). **The area ratio moved exactly where hoped: 1.59 ->
     1.00.** But this is **not a clean win** — canola-specific presence recall is only **83.4%**,
     against cereal's 95.1% and legume's 95.5% (canola senesces less sharply post-flowering by
     this metric, so one shared threshold screens more of it out), and the acceptance criterion
     below is met in aggregate (91.9% pooled) and **fails for canola specifically**. Mapped canola
     share did not move (still 23.4% vs ABS 36.2%) — fixing the area over-call unmasked a real
     canola recall shortfall that dilution was previously hiding. **Verdict: trades an
     area-inflation problem for a canola-undercount problem, not a smaller problem.** Not shipped
     as the default. Two untried fixes for the canola gap, in `PHENOLOGY_GATE.md`'s own next
     step: a looser `senescence_drop` threshold, or two-pass gating (amplitude only for
     canola-like signals, shape for the rest).
   - **Sentinel-1 for crop PRESENCE rather than crop type.** A ploughed or stubble paddock and a
     standing pasture differ in backscatter far more than in NDVI amplitude. This is a *different*
     use of S1 from the one costed in `SENTINEL1_VALUE.md`. Not tried.
   **Acceptance criterion, fixed before the work started:** the area ratio moves from 1.59 toward
   1.0 *while* presence recall on the NVT trials stays at or above the 91.6 % the current gate
   achieves. Both numbers or neither — a gate can reach ratio 1.0 by rejecting everything. **The
   phenology-shape attempt got exactly one of the two.**
3. **Ship the two confidences separately, never blended.** §4b: `ndvi_amp` orders paddocks by
   whether a crop is there; `n_years`/`median_iou` order them by whether the *boundary* is real
   and are no better than random at the first job. One column each.
4. **Yield — `YIELD_FEASIBILITY.md`.** Feasible and nearly free to compute (same features, one
   extra `.predict()`), but blocked on three things: no deployable model file, `Cereal` being
   wheat-or-barley with different yield distributions, and the NVT trial-to-commercial offset.
   The offset is now measurable — ABS carries production in tonnes by SA2, so regional yield is
   derivable — but **only at state/national scale**: 9.3 % of SA2-years give physically
   implausible wheat yields because levy production is attributed to the receival point.
5. **Sentinel-1 — the case has changed, re-read before spending.** `SENTINEL1_VALUE.md` argued for
   buying S1 for this region for 2019-2021 (~277 SU) on its legume gain. §4(c) shows **5.0 of the
   7.2 points of mapped legume are excess land, not misclassified crop**, so most of that error is
   the gate. Fix the gate, re-measure the legume residual, then decide. Access is a separate open
   question: ask `fj7`, not `dz56` (`SENTINEL1_ACCESS.md`).
6. **Do not re-tune SAM.** Ruled out in commit 8283a8d, corroborated by §5's stability result.

## 7. Where the artefacts are

| artefact | location |
|---|---|
| production models | `derived/models/group3_map.joblib`, `group4_map*.joblib` |
| **the 102 km run** | `derived/map100/` — `aois.csv`, `chunks/`, `samgeo/` (10,404), `pred/` (30) |
| stability table | `derived/map100/stability_all.csv` — 247,008 polygon-years |
| consensus geometry | `derived/map100/consensus.gpkg` — 25,082 stable paddocks |
| demo map predictions | `derived/mapdemo/pred/*.gpkg` — 3,709 paddocks, 15 region-years |
| SAM re-segmentation + QGIS package | `derived/samgeo/grazseg/`, `derived/agriwebb/grazseg_review_SENSITIVE.gpkg` |
| reference series | `derived/abs/` |
| per-arm reports | `output/arms/` — 13 arms incl. the `_sam`, `padcap` and `geomctl` controls |
| the long history | `output/archive/` |

## 8. Reports, in reading order

`ABS_COMPARISON_100km.md` (**the validation, and the current top priority**) ->
`PRESENCE_ONLY_LABELS.md` (why the negative class fails, and why the gate is the weak point) ->
`POLYGON_STABILITY.md` (nine years of geometry, and rotation plausibility) ->
`WALL_TO_WALL_MAPS.md` (the maps) -> `NATIONAL_INFERENCE_BENCHMARK_V2.md` (the bill) ->
`SENTINEL1_VALUE.md` (read §4(c) above first) -> `SENTINEL1_ACCESS.md` (how to get it on NCI).
Still current: `S1_MODEL.md`, `REVIEWED_MODEL.md`, `YIELD_MODEL.md`, `CANOLA_FLOWERING_AUDIT.md`,
`TILE_SIZE_BENCHMARK.md`. Superseded: `ABS_COMPARISON.md`, `NONCROP_CLASS.md`, `GRAZING_CLASS.md`,
`AGRIWEBB_TRAINING_CANDIDATES.md`, `HOLDOUT_AGRIWEBB*.md`, and the cost sections of
`NATIONAL_INFERENCE_BENCHMARK.md`.
