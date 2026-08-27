# Sentinel-1 on the paddock medians: the result, and the comparison that nearly hid it

Written 2026-08-09, after the MPC download completed and the model arms were re-run under a
controlled comparison.

Companion reports: `REVIEWED_MODEL.md`, `NEXT_STEPS.md`, `GROUP3_MODEL.md`.
Arms in `output/arms/`; the controlled ones are the six `*_ctl_*.md`.

---

## 1. Headline: S1 helps temporal transfer, and the gain is concentrated in Legume

> **REVISED 2026-08-09 (evening).** The first version of this section reported **+0.044 on
> both splits** from 2,065 trials / 477 test rows. The AOI repair in §5 then added 68 trials
> and fixed clipped backscatter on others — a ~3 % change to the row set — and the same
> comparison moved to **+0.029 temporal and +0.007 spatial**. The numbers below are the
> repaired ones and supersede the earlier table. What that swing means is discussed in §2b;
> the short version is that the spatial gain was not robust and should not be quoted.

**Three-group model, identical 1,636 training rows and 497 test rows in every arm, macro F1:**

| features | temporal transfer | spatial transfer |
|---|---|---|
| optical (3 indices, 51 features) | 0.823 | 0.825 |
| **S1 alone** (VV/VH/VH-VV, 51 features) | 0.812 | 0.800 |
| **optical + S1** (102 features) | **0.852** | **0.832** |

**Adding S1 is +0.029 on temporal transfer and +0.007 on spatial.** For scale, the
size-matched control seeds in `REVIEWED_MODEL.md` had sd 0.010, and the hand review of 1,973
polygons bought +0.019. So the temporal gain is real and worth roughly 1.5 hand reviews; the
spatial gain is inside the noise and should be reported as "no measurable spatial benefit".

**It lands where it was predicted to land — Legume**, the class flagged in `NEXT_STEPS.md` §7
as the largest remaining headroom:

| class | optical | +S1 | change |
|---|---|---|---|
| **Legume F1 (temporal)** | 0.69 | **0.75** | **+0.06** |
| **Legume precision (temporal)** | 0.66 | **0.73** | **+0.07** |
| Legume F1 (spatial) | 0.70 | 0.71 | +0.01 |
| Canola F1 (temporal) | 0.88 | 0.89 | +0.01 |
| Cereal F1 (temporal) | 0.90 | 0.92 | +0.02 |

The specific failure S1 fixes is the one named in advance: **cereals leaking into Legume.**
Legume precision was 0.66 because the model called too many cereals pulses; backscatter
separates a bushy pulse canopy from a vertical cereal one and precision goes to 0.73.

**S1 alone is worse than optical alone (0.812 vs 0.823) but close, and it is not redundant** —
the combination beats both, so the two sensors carry different information rather than two
noisy copies of the same thing.

## 2b. How much of this is noise? Model seed: exactly none. Row composition: enough to matter.

Five seeds per arm (`s1_seeds.pbs`, `output/arms/seeds/`) returned **byte-identical scores**:
optical 0.823 / 0.825 and optical+S1 0.852 / 0.832 for every one of seeds 0-4.
`HistGradientBoostingClassifier` only uses its RNG for the binning subsample, which it skips
below 10,000 rows — at 2,133 rows the fit is deterministic. **So none of the movement between
the two runs is model noise; all of it is which rows went in.**

That is the useful conclusion, and it is uncomfortable: a 3 % change in the row set moved the
temporal gain by 0.015 and the spatial gain by 0.037. The earlier "+0.044 on both splits,
agreeing to three decimals" now reads as coincidence rather than corroboration, and I
over-read it at the time. **The honest statement is +0.03 on temporal transfer with an
uncertainty of roughly the same order, and no established spatial effect.** Narrowing that
needs a bootstrap over test rows rather than more seeds — seeds measure nothing here.

## 2. The comparison that nearly hid it, and why

The first S1 arm run against the standard 543-row test set said **0.819 against the optical
model's 0.821 — no gain at all.** That number is in `output/arms/GROUP3_s1_plus.md` and it is
wrong to read it as "S1 does not help".

**66 of those 543 test rows have no Sentinel-1 data.** They are scored anyway, with every
backscatter feature NaN. So 12 % of the exam was sat by the S1 model with one sensor missing,
and the average of "helps a lot on 477 rows" and "handicapped on 66" came out flat.

This is the mirror image of the mistake recorded in `REVIEWED_MODEL.md` §"The headline that
got away", where each arm was scored on its own cleaner test rows and manufactured a +0.107
gain. Same root cause, opposite sign:

> **A fixed test set is necessary but not sufficient. Every arm must also be *able to see* every
> row in it.** Holding the row list constant while one arm's features are absent on part of it
> does not control the comparison, it taxes one arm. The fix is not to impute the missing
> sensor — it is to shrink the comparison to the rows all arms can actually answer, and to say
> so.

Hence `keep_s1both_SENSITIVE.csv` (2,065 trials, 477 of the 543 test rows) and the `_ctl_`
arms. **Scores in §1 are comparable only to each other**, not to the 543-row numbers in
`REVIEWED_MODEL.md`. On its own restricted rows the optical model scores 0.812, not 0.821.

## 3. Independent confirmation: one S1 number beats peak CFI

Before any model, the median VV over DOY 200-300 — a single number per paddock — separates the
groups better than peak CFI, the index this project has been built around:

**Univariate AUC, 2,194 trials, flowering window:**

| pair | VV | VH | VH-VV | peak CFI |
|---|---|---|---|---|
| Canola vs Cereal | **0.933** | 0.927 | 0.662 | 0.843 |
| Legume vs Cereal | **0.836** | 0.712 | 0.248 † | 0.628 |
| Canola vs Legume | 0.759 | 0.819 | **0.852** | 0.772 |

† below 0.5 means the ordering is inverted — Legume sits *lower* on VH-VV than Cereal, which is
a signal of the same strength as 0.752 in the other direction.

**This is not regional confounding.** Stratifying so that only trials in the same state, or the
same year, are ever compared:

| | VV | peak CFI | VV wins |
|---|---|---|---|
| Legume vs Cereal, median within-state | 0.891 | 0.575 | **5 / 5 states** |
| Legume vs Cereal, median within-year | 0.854 | 0.633 | **8 / 8 years** |
| Canola vs Cereal, median within-state | 0.939 | 0.817 | **4 / 4 states** |
| Canola vs Cereal, median within-year | 0.950 | 0.863 | **8 / 8 years** |

**Every stratum, both pairs, no exceptions — 25 of 25.** On Legume vs Cereal, where CFI is
close to useless (0.575-0.633), a single VV median reaches 0.85-0.89.

Note this compares one S1 number against one optical number, not against the 51-feature optical
model — the model extracts far more from CFI than its peak. But it does establish that the
information S1 adds in §1 is visible before any classifier touches it, which is why the +0.044
should be believed.

## 4. A hypothesis tested and refuted: the Sentinel-1B failure does not bite

`NEXT_STEPS.md` §6 warned that S1B's failure in Dec 2021 could leave the 2023-24 temporal test
set thin, and that a 2023 result should not be read before checking. It was worth checking and
it is not a problem:

| | 2017-2021 (S1A+S1B) | 2022-2024 (S1A only) |
|---|---|---|
| median revisit | 6 days | **6 days** |
| median VV / VH / VH-VV | -12.2 / -18.8 / -6.4 | -12.1 / -18.6 / -6.2 |

**The revisit does not degrade and the backscatter levels do not shift.** Multiple relative
orbits cover these sites, so losing one satellite did not halve the effective cadence. Group
separation in the flowering window is if anything *wider* in the test era (Legume−Cereal VH-VV
−0.79 dB before, −1.07 dB after). Coverage of the training universe is 95.0-97.5 % in every
year, with no downward trend into the test period.

The one real trace of S1B is at the tail: trials with fewer than 3 scenes in DOY 200-300 go
from 0.0 % in 2017-2021 to 3.6 % in 2023 and 8.4 % in 2024. Worth a footnote, not a caveat.

## 5. A real bug in the download, quantified and repaired

**`s1_download.py` centres its AOI box on the trial point, but the thing being measured is the
chosen paddock** — which the matcher may move up to 150 m away and which can exceed 300 ha. The
box is centred on one object and sized for another.

Diagnosed by comparing `n_px_paddock` against `paddock_ha` (10 m pixels, so H ha = H×100 px),
which is what separates true clipping from the 10 m erosion every paddock legitimately loses:

| | trials | share |
|---|---|---|
| paddock wholly outside the raster — **no S1 rows at all** | 54 | 2.5 % |
| AOI never downloaded (6 hard failures, mostly expired SAS tokens on a 4 h job) | 25 | 1.1 % |
| less than 70 % of the paddock captured | 28 | 1.3 % |
| **total needing repair** | **107** | **4.9 %** |
| median capture fraction across all trials | 0.935 | — |

The 25 missing downloads are a separate, ordinary failure — a signed-URL token expiring partway
through a four-hour job — and are swept up by the same repair. Only the 54 are the AOI-box bug.

**A strict bounding-box test would have overstated this about sixfold.** 282 of 1,157 boxes
(24 %) fail to contain their paddock's bounding-box corner, which looks alarming; but a corner
poking out costs almost no area, and the measured capture fraction says only 107 trials lost
anything worth having. The `<90 % captured` group is 94 % small paddocks losing area to
erosion by design. **Sizing the repair off the corner test would have cost four times the
transfer to fix nothing** — the lesson being to measure the quantity you actually care about
(pixels retained) rather than a geometric proxy for it.

`s1_repair.pbs` re-fetches the **63 affected AOIs** with `half_m` recomputed from the paddock
extent (median 3,500 m, max 8,500 m against the old flat 1,500 m), ~1.3 h on copyq. Superseded
files move to `derived/s1_superseded/` rather than being deleted, so the repair is resumable.

**Done 2026-08-09.** The repair ran (61 of 63 AOIs re-fetched, 2 hard failures, 5 AOIs genuinely
have no scenes in the season). Coverage went **2,251 → 2,320 trials of 2,333**, AOIs with no S1
file 13 → 7, and the controlled row set 2,065 → 2,133 with **497 of 543 test rows (91.5 %)**.
The remaining 46 test rows are sites S1 genuinely does not cover densely enough, not a bug.

The repaired data is what §1 now reports, and it is also what moved the answer — see the
revision note there. Re-running the comparison on better data changed the conclusion more than
any modelling choice made today, which is the argument for fixing the data first.

## 5b. Presto, re-run with S1 — the earlier verdict does not survive

`NEXT_STEPS.md` §5 concluded "Presto without S1 does not beat CFI features" with 3 of Presto's
9 channel groups masked. S1 is now supplied, so only ERA5 and SRTM stay masked, and the
embedding is rebuilt over 2,320 trials.

**On the controlled rows (2,133 trials / 497 test rows), macro F1:**

| arm | temporal | spatial |
|---|---|---|
| optical only | 0.823 | 0.825 |
| optical + S1 (hand-built) | 0.852 | 0.832 |
| **Presto(S1) alone** | 0.813 | 0.808 |
| **optical + S1 + Presto(S1)** | **0.857** | **0.858** |

**Presto alone goes 0.775 → 0.813** and is now within 0.010 of the 51 hand-built optical
features, from a general-purpose embedding that was given no crop-specific index at all. Added
on top it gives **+0.005 temporal and +0.026 spatial** over optical+S1 — and the spatial number
is the one the hand-built S1 features failed to move.

So the fair statement is now: **Presto with 8 of 9 channel groups is competitive alone and adds
a little on top, mostly on spatial transfer.** One caveat worth keeping — trials without S1 are
dropped rather than masked, because Presto's encoder asserts a uniform mask across a batch, so
this arm cannot be run on the full 543 rows either.

## 6. Canola: already at its ceiling, and S1 does not move it

Binary Canola vs Other, same controlled rows:

| features | temporal macro F1 | canola @ 5 % FPR | average precision |
|---|---|---|---|
| optical | 0.927 | 87.8 % | 0.945 |
| S1 alone | 0.922 | **92.1 %** | 0.944 |
| optical + S1 | **0.934** | 85.6 % | 0.942 |

**+0.007 macro F1 for S1, and the detection rate moves in the wrong direction.** At n=139
canola in the test set, a 5 %-FPR detection rate swings several points on a handful of paddocks,
so the 92.1 % from S1 alone and the 85.6 % from the combination should both be treated as noise
around ~88 %, not as findings.

**The canola map does not need Sentinel-1.** It was already publishable on optical alone
(`NEXT_STEPS.md` §3) and this does not change that. S1's value is entirely in the three-group
problem, and specifically in Legume.

## 7. What this changes

1. **Sentinel-1 is now a core input, not an experiment.** It is the largest measured feature
   gain in the project and it addresses the class that was the stated bottleneck.
2. **Finish the AOI repair (§5) and re-run the controlled arms**, so the headline can be stated
   on the full 543-row test set instead of 477.
3. **Re-run Presto.** `NEXT_STEPS.md` §5 concluded "Presto without S1 does not beat CFI
   features" with 3 of its 9 channel groups masked. S1 is one of the three, and it has just been
   shown to carry the signal the optical features lack — so that conclusion is now genuinely
   untested rather than merely caveated.
4. **Legume is no longer the obvious next target.** At F1 0.75 / precision 0.75 it is close to
   Canola's 0.89 and Cereal's 0.93. The remaining gap is more likely the co-located-paddock
   label problem (`MEMORY.md`: 31.8 % of trials share a polygon with a different crop) than a
   missing sensor.
5. **Do not re-read the 543-row S1 arms.** `GROUP3_s1_plus.md` and `CANOLA_s1_plus.md` are kept
   for the record but their comparison to the optical arms is taxed by the 66 blind rows.

## 8. Exact commands

```bash
cd src/paddocks
D=/scratch/xe2/cb8590/paddock-species-data/derived
PY=/g/data/xe2/John/geospatenv/bin/python

qsub s1_repair.pbs          # copyq, ~1.3 h — 63 undersized AOIs, single shard by design

# then rebuild the S1 table and re-run every arm
qsub -v S1_FORCE_EXTRACT=1 s1_features.pbs    # extraction + the 543-row arms, ~10 min
qsub s1_controlled.pbs                        # the 6 controlled arms, ~5 min

# the keep set that makes the comparison fair (regenerate after the repair)
# keep_s1both = keep_reviewed AND >=10 S1 obs AND >=10 optical obs
```

`train_species.py` had a crash on the S1-only path — with no optical block, the feature-assembly
line indexed an empty list. Fixed; `--s1` alone now works.

## 9. State of the S1 data

| artefact | location | scale |
|---|---|---|
| RTC cubes from MPC | `derived/s1/` | 1,149 AOIs, 33 GB |
| paddock-median VV/VH/VH-VV | `derived/s1_paddock_ts_SENSITIVE.csv` | 61,041 trial-dates, 2,251 trials |
| controlled keep set | `derived/keep_arms/keep_s1both_SENSITIVE.csv` | 2,065 trials, 477 test rows |
| AOIs needing repair | `derived/samgeo/aois_s1_repair_SENSITIVE.csv` | 63 AOIs |
| controlled arms | `output/arms/{GROUP3,CANOLA}_ctl_{optical,s1,both}.md` | 6 arms |

Download cost: 6 copyq shards, ~3.9 h each, **91.5 SU** for 1,149 AOIs.
