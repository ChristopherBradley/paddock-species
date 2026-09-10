# Experiment Plan — Sentinel-1 via fj7, full-layer Presto, and the S2-only compute comparison

**Problem**: fj7 (Copernicus Australasia Regional Data Hub) access just landed, changing the
economics of national-scale Sentinel-1 — the earlier decision to buy S1 only for a 100 km pilot
(`SENTINEL1_VALUE.md`) was driven entirely by MPC's ~7,957 SU download cost, which a `/g/data`
filesystem read should delete. Three things follow: (1) re-test S1's classifier gain against the
*current* best model, not the 3-index baseline it was last measured against; (2) re-run Presto
with the two channel groups still masked (ERA5, SRTM) now filled in; (3) measure — not assume —
what fj7's raw-archive processing actually costs, since that was flagged as the one real unknown
the moment access landed.

**Method Thesis**: fj7 turns "S1 nationally" from a rejected 7,957-SU line item into a
filesystem read, *if* two unresolved blockers (scene discovery, RTC processing) turn out to be
cheap — which is unverified, not assumed, below.

**Date**: 2026-08-31

**Precondition check run this session** (see §Risks): fj7 is mounted and readable
(`/g/data/fj7/CopHub/Sentinel-1/`), but it holds **raw SLC/GRDH/OCN products only**, sharded by
opaque UUID (not by date/orbit/geography), and the one thing that would make those UUIDs
findable — the `filelists/*.csv.gz` catalogue — is **`-rw-------` to its owner, unreadable to
this account.** No RTC/terrain-correction toolchain (pyroSAR, SNAP, GAMMA) is installed in the
project's Python env or visible via `module avail`. Both were treated as open questions in
`SENTINEL1_ACCESS.md` §4a; both are now confirmed **not yet solved**, and Milestone 0 below exists
specifically to resolve them before any SU is spent on a pilot that cannot locate its own input.

---

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|---|---|---|---|
| **C1 (primary) — RESOLVED 2026-08-31, REFUTED.** S1 still improves the classifier once stacked on the *current* best feature set (shipped 3 indices + Sharma6, macro F1 0.890/0.892), not just the retired 3-index baseline it was measured against (+0.029/+0.007, `S1_MODEL.md`). | The Sharma6 indices were adopted partly because they fix the same Legume/Cereal confusion S1 was shown to fix. If they already absorbed it, buying S1 nationally buys nothing new. | A controlled arm, identical keep-set and test rows, `shipped+sharma6+S1` vs `shipped+sharma6`, with a gain clearly outside the established ~0.010 seed-noise floor. | B2 — **measured: −0.023 temporal / −0.018 spatial, a regression, not a null result. Worse than the anti-claim predicted. Full writeup: `S1_VS_LATEST_MODEL.md`.** |
| **C1y (new, added post-hoc).** S1 improves the shipped pooled-Cereal yield model (`cereal_yield.joblib`), never previously tested. | The classifier result above closes the classification case for national S1 — this is now the only accuracy-based argument left for buying it at scale. | A controlled arm, `indices+S1` vs `indices`, on the same yield target the shipped model fits. | B2 — **measured: R2 +0.092 (temporal, satellite+year/state), +0.022 to +0.054 elsewhere. Clear, consistent gain. `S1_VS_LATEST_MODEL.md`.** |
| **C2 (supporting).** Presto with all 9 channel groups unmasked ("the full article" — S2, S1, ERA5, SRTM, NDVI, i.e. the 5 data sources the user named) closes more of the remaining gap to hand-built features, concentrated on spatial transfer where the trend already points (`S1_MODEL.md` §5b: Presto(S1 only) 0.813/0.808 vs hand-built optical+S1 0.852/0.832 — behind on both, but the smaller gap is on temporal). | Two of Presto's nine channel groups are still masked, so the last verdict ("competitive but behind") is untested at full input, exactly as the S1 verdict was untested with S1 masked. | Presto(9/9) alone and Presto(9/9)+hand-built, same controlled rows, compared to the existing 7/9 numbers. | B3 |
| **Anti-claim to rule out.** The measured S1 gain is a property of NVT trial paddocks (larger, cleaner, better-segmented than average) and does not survive contact with the ordinary wall-to-wall geometry the national map actually uses — the same caveat `SENTINEL1_VALUE.md` §3.2 already flagged and never tested. | If true, national S1 spend buys a number that will not reproduce on the map that ships. | Held-out check against AgriWebb crop paddocks (104 farmer-recorded sites, never trained on, ordinary geometry) once S1 coverage extends past NVT trial sites. | B5 (conditional) |

## Paper Storyline

- **Main paper (current RSE draft) must prove**: nothing here is required — the manuscript is
  frozen on the shipped optical-only pipeline (`NEXT_STEPS.md`, "shipped and frozen for the
  remaining years"). This plan is deliberately scoped as work that does not block or reopen that
  decision.
- **Could support**: a Discussion/Future-Work paragraph citing a measured fj7 processing cost and
  a re-confirmed (or refuted) S1 gain on the current model, replacing the current text's
  qualitative "not bought at scale" with a number.
- **Could become its own thread**: if C1 and C2 both land positive and Milestone 1's cost comes in
  low, a national S1 extension is a natural second contribution — flag to the user as a decision
  point once M0–M3 report back, not something to commit to now.
- **Intentionally cut from this round**: fine-tuning Presto's weights (only linear-probe /
  embedding-as-features has been tried anywhere in this repo); any SAR-specific processing beyond
  standard RTC (e.g. multi-temporal speckle filtering) — out of scope until the basic RTC pipeline
  is shown to work at all.

## Experiment Blocks

### Block 0: fj7 reconnaissance — scene discovery and RTC toolchain (MUST-RUN, blocking)
- **Claim tested**: none directly — this is the sanity stage that everything else depends on.
- **Why this block exists**: confirmed this session that fj7's archive cannot currently be
  searched by AOI/date (catalogue unreadable) and that no terrain-correction toolchain exists in
  this project. Both are new findings, not previously documented.
- **Task**: (a) request read access to `/g/data/fj7/filelists/fj7_CopHub_Sentinel-1_files_*.csv.gz`
  from its owner (`mp2758`) or NCI helpdesk — this is a permissions ask, not a data-acquisition
  problem, and is almost certainly the fastest path to a working AOI→UUID lookup. (b) in parallel,
  check whether the **NCI THREDDS catalogue for fj7** (`SENTINEL1_ACCESS.md` §2, public, no
  account needed) exposes a queryable OPeNDAP/catalog.xml index by bounding box + date — this
  would remove the dependency on the restricted CSVs entirely and is worth 30 minutes to check
  before waiting on a permissions request. (c) install or module-load a GRD→RTC toolchain:
  `pyroSAR` (wraps SNAP or GAMMA) is the standard choice; GA's own `ga_sar_workflow` — already
  investigated in `SENTINEL1_ACCESS.md` §4 — is the reference implementation but needs `dg9`
  membership this account does not have, so a standalone pyroSAR+SNAP install is the more
  realistic path unless dg9 is also requested.
- **Dataset / split / task**: one known GRDH scene (e.g.
  `S1A_IW_GRDH_1SDV_20250623T215321_...` found under `Sentinel-1/00/24/...` this session) as a
  toolchain smoke test — process it through RTC with default settings, confirm output looks
  sane (backscatter in dB, correct CRS), regardless of whether it overlaps an AOI of interest.
- **Success criterion**: a scene can be found by AOI+date without a directory scan, AND one scene
  processes to RTC backscatter end to end.
- **Failure interpretation**: if catalogue access cannot be resolved quickly (e.g. owner
  unresponsive) and THREDDS does not expose a usable index, fj7 provides raw storage but not a
  practical search path — at that point, compare the *engineering* cost of building a local
  spatial index by scanning fj7's own SAFE metadata (feasible but slow — global archive, most of
  it not Australia) against simply keeping the MPC route for anything beyond the existing 100 km
  pilot. This is a genuine decision point, not a default to skip past.
- **Table / figure target**: none — internal blocker log only, written to `output/PROJ_NOTES.md`.
- **Priority**: MUST-RUN, and gates B1 and (fully) B5.

### Block 1: fj7 processing-cost benchmark, and the S1-vs-S2-only compute ratio the user asked for (MUST-RUN, gated on B0)
- **Claim tested**: none — this is the number `SENTINEL1_ACCESS.md` explicitly deferred
  ("do not treat fj7 as free until a pilot of a few tiles has been costed").
- **Why this block exists**: it is the direct answer to "benchmark how much more compute this
  uses compared to only using Sentinel-2," and it is the number that decides whether Blocks 3-5
  scale nationally or stay pilot-scale.
- **Dataset / split / task**: process **10 GRDH scenes** end to end on `normal`
  (fj7 filesystem read → RTC terrain correction → paddock-median VV/VH, reusing `s1_extract.py`'s
  reduction logic once the input format is backscatter GeoTIFF instead of MPC's STAC items),
  chosen to span low/high relief terrain (SRTM slope varies RTC cost) and at least one scene
  known to cover part of the existing 100 km Riverina pilot region, so results are directly
  comparable to `s1_paddock_ts_SENSITIVE.csv`.
- **Compared systems / reference points** (all already measured, reuse rather than re-derive):
  | route | SU | source |
  |---|---|---|
  | MPC download, 2,390 AOI-seasons (NVT-trial-site pilot) | ~91.5 SU | `S1_MODEL.md` §9 |
  | MPC download, national wall-to-wall, one pass (99,465 tiles) | ~7,957 SU | `SENTINEL1_ACCESS.md` §4a |
  | National optical (S2) map, one year (2024), all stages | 6,622.6 SU | `NATIONAL_2024_RUN.md` |
  | — of which SAM segmentation alone | 4,126 SU (62%) | `NATIONAL_2024_RUN.md` |
  | **fj7 RTC processing, 10 scenes** | **[TO MEASURE]** | this block |
- **Metrics**: SU/scene, SU/paddock (via scene→paddock overlap count), extrapolated SU for (a) the
  2,320-trial NVT population, directly comparable to the 91.5 SU MPC figure, and (b) full national
  wall-to-wall, directly comparable to the 7,957 SU MPC figure and the 6,622.6 SU S2 baseline —
  this last ratio is the literal "how much more compute than S2-only" the user asked for.
- **Setup details**: `normal` queue, 2 SU/hr; do not default to `gpuvolta` before checking whether
  RTC processing is CPU- or memory-bound (the project's own prior lesson,
  `pbs-memory-reporting-is-unreliable` / `scene-cache-locality-dominates-tiling` in memory —
  benchmark before assuming GPU helps here, SNAP's RTC step is not typically GPU-accelerated).
  Cap the pilot at a hard **100 SU** budget regardless of what 10 scenes end up costing, and stop
  to report back rather than silently scaling up if early scenes are expensive.
- **Success criterion**: fj7 route is substantially below the MPC-equivalent figure at whichever
  scale it's compared to (the entire reason fj7 was requested).
- **Failure interpretation**: if RTC processing cost approaches or exceeds MPC's, fj7 has not
  changed the economics and the earlier 100 km-pilot-only decision stands — note honestly that the
  original *governance* argument for fj7 (avoiding sending AgriWebb coordinates off-site) was
  already flagged as weakened once AgriWebb was dropped (`SENTINEL1_ACCESS.md` §4), so a
  cost failure here removes both of fj7's original justifications, not just one.
- **Table / figure target**: a compute-comparison table for the Discussion / Future Work section,
  or `output/SENTINEL1_FJ7_BENCHMARK.md` as a standalone report either way.
- **Priority**: MUST-RUN.

### Block 2: Re-test S1's classifier gain against the CURRENT best model (DONE 2026-08-31)

> **Result, run as `s1_vs_latest.pbs` (job 177862351, 3.06 SU): classifier REGRESSES
> (−0.023 temporal / −0.018 spatial, Legume F1 0.82→0.77), yield IMPROVES (R2 +0.092 temporal).
> Full writeup: `S1_VS_LATEST_MODEL.md`.** The classifier scope below is resolved and should not
> be re-run without a reason; the yield scope was added mid-session at the user's request and is
> also done. Kept below for the record of what was planned and why.

- **Claim tested**: C1, and the anti-claim (Sharma6/S1 redundancy).
- **Why this block exists**: every existing S1 classifier number (`S1_MODEL.md`,
  `SENTINEL1_VALUE.md`) was measured against the retired 3-index optical model (0.823/0.825). The
  shipped model is now `shipped+sharma6` (0.890/0.892, `GROUP3_MODEL_shipped_plus_sharma6.md`) —
  a different, stronger baseline that was itself partly adopted for fixing the Legume/Cereal
  confusion S1 was shown to fix. This has never been checked.
- **Dataset / split / task**: **no new data needed** — the MPC-derived
  `derived/s1_paddock_ts_SENSITIVE.csv` (2,320 trials) and `keep_s1both_SENSITIVE.csv` /
  `testkeep_temporal_SENSITIVE.csv` already exist from the 100 km pilot. This can run immediately,
  independent of Blocks 0/1.
- **Compared systems**: three controlled arms, identical rows throughout:
  1. `shipped+sharma6` alone (the current production feature set)
  2. `shipped+sharma6 + S1` (new — the actual test)
  3. `optical(3-idx) + S1` (existing `GROUP3_ctl_both.md`, for continuity with the old headline number)
- **Setup details** (exact commands, following `train_group3_shipped_plus_sharma6.pbs`'s pattern):
  ```bash
  PY=/g/data/xe2/John/geospatenv/bin/python
  D=/scratch/xe2/cb8590/paddock-species-data/derived
  KEEP=$D/keep_arms/keep_s1both_SENSITIVE.csv
  TESTKEEP=$D/keep_arms/testkeep_temporal_SENSITIVE.csv

  # arm 1: shipped+sharma6, but scored on the S1-availability-restricted keep set (fair baseline)
  $PY train_species.py \
      --indices "$D/samgeo/ts_v2/*_SENSITIVE.csv" --bands "$D/samgeo/bands_ts/*_SENSITIVE.csv" \
      --bands-keep-families ndre2 vi2 vi3 vdvi vci evi2_sharma \
      --labeled $D/nvt_trials_labeled.csv --keep $KEEP --test-keep $TESTKEEP \
      --target group3 --importance-repeats 5 \
      --out output/arms/GROUP3_ctl_shipped_sharma6_only.md

  # arm 2: shipped+sharma6 + S1 — the actual test of C1
  $PY train_species.py \
      --indices "$D/samgeo/ts_v2/*_SENSITIVE.csv" --bands "$D/samgeo/bands_ts/*_SENSITIVE.csv" \
      --bands-keep-families ndre2 vi2 vi3 vdvi vci evi2_sharma \
      --s1 $D/s1_paddock_ts_SENSITIVE.csv \
      --labeled $D/nvt_trials_labeled.csv --keep $KEEP --test-keep $TESTKEEP \
      --target group3 --importance-repeats 5 \
      --out output/arms/GROUP3_ctl_shipped_sharma6_s1.md
  ```
  Both must use the identical `keep_s1both` row set — `S1_MODEL.md` §2's fixed-test-set-but-not-
  every-arm-can-see-it bug is the single most important thing to not repeat here.
- **Metrics**: macro F1 (temporal + spatial), per-class F1 (Legume specifically), canola @ 5% FPR
  (must not regress — this is the operating point the codebase's own comments call load-bearing).
- **Success criterion**: gain on arm 2 vs arm 1 clearly exceeds the established ~0.010 seed-noise
  floor (`REVIEWED_MODEL.md`), replicated on Legume F1 specifically.
- **Failure interpretation**: a near-zero gain confirms the anti-claim — Sharma6 already captured
  what S1 was fixing, and national S1 spend should not be justified on classifier accuracy alone
  (though it could still be justified by B5's map-level ABS check, a separate question).
- **Table / figure target**: `output/S1_MODEL_v2.md` or an addendum section in `S1_MODEL.md`.
- **Priority**: MUST-RUN, run first (cheapest, fastest, no new data).

### Block 3: Presto, all 5 data sources unmasked (MUST-RUN, gated on ERA5/SRTM sourcing not on B0/B1)
- **Claim tested**: C2.
- **Why this block exists**: `presto_s1.pbs`'s own comment says it plainly — "this is Presto with
  8 of 9 groups, not the full article." The last two groups (ERA5, SRTM) were never sourced.
- **What "5 layers" means here**, made explicit since the user's phrasing doesn't map 1:1 onto the
  code's "9 channel groups": Presto's 17 input channels come from **5 distinct data sources** —
  S2 (10 bands), S1 (VV/VH), ERA5 (temperature_2m, total_precipitation), SRTM (elevation, slope),
  and NDVI (derived from S2, channel 16). `MISSING_GROUPS` in `presto_embed.py` already has ERA5
  and SRTM keys wired up structurally — they were designed for from the start, just never fed.
- **New sourcing work required** (neither exists in this codebase — confirmed by grep):
  - **ERA5**: monthly `temperature_2m` and `total_precipitation`, per-paddock or per-AOI-centroid,
    for the trial year. Recommend Google Earth Engine's `ECMWF/ERA5_LAND/MONTHLY_AGGR` collection
    — the project already has a GEE service account (used for WorldCereal) and this is a tiny
    per-point reduction, not imagery volume, so it should cost negligible GEE compute quota. CLAUDE.md
    flags that quota as "unconfirmed — ask the user to check if it becomes a constraint": worth
    doing before this block, not after.
  - **SRTM**: elevation + slope, same per-point reduction, `USGS/SRTMGL1_003` on GEE (simplest) or
    the pre-existing 112 GB GAMMA SRTM mosaic seen at `/g/data/dz56/GAMMA_DEM_SRTM_1as_mosaic.ige`
    (that project is not one this account has read access to, per this session's `ls` — GEE is the
    practical route).
  - **Code**: extend `presto_embed.py` with `--era5` / `--srtm` CSV args mirroring the existing
    `--s1` pattern (fill channels 12-15, drop them from `missing`), and a small new
    `era5_srtm_fetch.py` (GEE point-reduction script, same shape as `nlum_compare.py`'s existing
    GEE usage).
- **Dataset / split / task**: same 2,320-trial `keep_s1both` population as Block 2, so all four
  Presto generations (3/9, 7/9, 9/9 masked-groups, plus hand-built) are directly comparable.
- **Compared systems**:
  | arm | masked groups | temporal | spatial | source |
  |---|---|---|---|---|
  | Presto, S1+ERA5+SRTM masked | 3 | ~0.775 | [not recorded in reports read this session] | superseded, pre-`presto_s1.pbs` |
  | Presto(S1) alone | ERA5, SRTM | 0.813 | 0.808 | `S1_MODEL.md` §5b |
  | optical+S1+Presto(S1) | ERA5, SRTM | 0.857 | 0.858 | `S1_MODEL.md` §5b |
  | **Presto(S1+ERA5+SRTM) alone** | **none** | **[TO MEASURE]** | **[TO MEASURE]** | this block |
  | **shipped+sharma6+S1 + Presto(full)** | **none** | **[TO MEASURE]** | **[TO MEASURE]** | this block |
- **Setup details**: `presto_s1.pbs`'s two-arm pattern (Presto alone; Presto stacked on the best
  hand-built arm — now `shipped+sharma6+S1` from Block 2, not the old `optical+S1`), same
  `keep_s1both` rows, same batch-uniform-mask constraint (trials without S1 dropped, not masked).
- **Metrics**: macro F1 temporal + spatial, with spatial transfer as the metric of interest —
  every group added so far has moved spatial more than temporal (0.808→0.858 spatial vs
  0.813→0.857 temporal going from Presto-alone to Presto-stacked), which is the axis hand-built
  features contribute least to.
- **Success criterion**: Presto(full) alone closes materially more of the gap to hand-built
  features than Presto(7/9) did, OR Presto(full) stacked on `shipped+sharma6+S1` beats
  `shipped+sharma6+S1` alone by more than the stacking gain already seen (+0.005 temporal / +0.026
  spatial at 7/9 masked).
- **Failure interpretation**: if ERA5/SRTM add nothing, that's consistent with both groups being
  coarse, slowly-varying signals a paddock-level classifier gets little marginal information from
  once phenology (S2) and structure (S1) are already present — a plausible, reportable null result,
  not a bug to chase.
- **Table / figure target**: extend `S1_MODEL.md` §5b's table, or a new `PRESTO_FULL.md`.
- **Priority**: MUST-RUN once ERA5/SRTM sourcing (cheap, no fj7 dependency) is done.

### Block 4: Frontier-necessity check — Presto vs. ERA5/SRTM as plain features (NICE-TO-HAVE)
- **Claim tested**: is the foundation-model embedding earning its complexity over just adding
  4 extra numeric columns (monthly temp, precip, elevation, slope) to the existing HGB model?
- **Why this block exists**: this project has now built three model generations (hand-built →
  hand-built+S1 → Presto), and never directly asked whether Presto's value over `shipped+sharma6+S1`
  is separable from simply having ERA5/SRTM at all. Cheap once Block 3's sourcing exists — same
  data, two different consumption paths.
- **Compared systems**: `shipped+sharma6+S1` (Block 2) vs. `shipped+sharma6+S1` + 4 plain ERA5/SRTM
  columns vs. `shipped+sharma6+S1` + Presto(full) embedding (Block 3).
- **Success criterion**: if the plain-column version matches Presto(full)'s gain, that's the
  honest finding — Presto's marginal value here is close to zero once the same raw information is
  available any way at all, and the paper-worthy claim shifts to "ERA5/SRTM matter, Presto's
  self-supervision doesn't add much on top of hand-built + S1" rather than "Presto is the answer."
- **Failure interpretation**: negative result here is informative either way — do not skip it just
  because it might undercut Presto.
- **Priority**: NICE-TO-HAVE — cheap (reuses Block 3's data), run only if B3 shows a real Presto gain.

### Block 5: National-scale S1 (conditional MUST-RUN — gated on B0 + B1, re-scoped to YIELD only)

> **Re-scoped 2026-08-31 after Block 2 ran.** This block was written to test whether the
> classifier's Legume gain survives on ordinary geometry. Block 2 found no such gain to test —
> S1 *regresses* `shipped+sharma6` (−0.023/−0.018, concentrated on Legume) — so the classifier
> half of Block 5 is cut (`EXPERIMENT_TRACKER.md` R009). What survives is C1y: S1 clearly
> improves `cereal_yield.joblib` (+0.092 R2, temporal). Everything below now reads as being
> about that yield gain, not crop type — see `S1_VS_LATEST_MODEL.md`.

- **Claim tested**: does the yield gain (C1y) survive on ordinary commercial-paddock geometry,
  not just clean NVT trial sites — the same transfer question `SENTINEL1_VALUE.md` §3.2
  originally posed for the classifier, now asked of the regressor instead. No yield-labelled
  ordinary-geometry set is currently known to exist (unlike AgriWebb for crop type) — finding
  one, or deciding none exists and this claim stays untested, is itself the first task here.
- **New engineering required before trusting any multi-year S1 feature**: the revisit-density
  covariate `SENTINEL1_VALUE.md` §3.3 called for (S1B failed Dec 2021; constellation was 1
  satellite 2022–Apr 2025, 2 satellites otherwise) is **still not implemented anywhere in this
  codebase** — confirmed by grep this session, only a comment noting the gap exists
  (`train_species.py:410`). Build it before any 2017-2025 S1 feature is trusted, or the instrument
  change will read as land-use change in a temporal-transfer model, exactly as warned.
- **Dataset / split / task**: extend S1 coverage from 2,320 NVT trials to (a) the 104 AgriWebb
  ordinary-geometry holdout paddocks first (cheap, existing labels, direct test of the anti-claim,
  reuses `agriwebb_holdout_group3.py`'s pattern) — then (b) full national multi-year only if (a)
  and B1's cost check both clear.
- **Success criterion**: AgriWebb holdout macro F1 improves with S1 beyond noise, on paddocks that
  look nothing like clean NVT trial sites.
- **Priority**: conditional MUST-RUN — do not start until B0-B2 report back. This is the expensive
  tail of the plan and should not be pre-committed to.

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Cost | Risk |
|---|---|---|---|---|---|
| M0 | Resolve fj7 scene discovery + confirm/install RTC toolchain | B0 | Can a scene be found by AOI+date, and processed to RTC, at all? | ~0 SU (permissions ask + one scene) + toolchain install time | Owner unresponsive; THREDDS doesn't expose a usable index; pyroSAR+SNAP install nontrivial on gadi |
| M1 | Cost fj7 RTC processing | B1 | Cheaper than MPC's 91.5 / 7,957 SU reference points? | ≤100 SU (hard cap) | RTC cost could exceed the download it replaces, exactly as `SENTINEL1_ACCESS.md` warned |
| M2 | Re-test S1 gain on current model | B2 | Gain clearly outside ~0.010 noise floor? | 3.06 SU actual (job 177862351) | **DONE.** Classifier: −0.023/−0.018 (regression, worse than the anti-claim). Yield: +0.092 R2 (clear gain, C1y, not originally in the claim map). `S1_VS_LATEST_MODEL.md` |
| M3 | Source ERA5/SRTM, re-run Presto full | B3 | Does 9/9 close more of the spatial-transfer gap? | negligible SU; unconfirmed GEE quota (flag to user first) | GEE quota tighter than assumed |
| M4 | Presto vs. plain ERA5/SRTM columns | B4 | Does Presto beat the cheap alternative? | negligible (reuses M3 data) | — |
| M5 | National S1 scale-up **(yield only — classifier scope cut)** | B5 | Does the yield gain survive on ordinary geometry? (no candidate dataset identified yet) | ~277-7,957 SU depending on M1's actual number | M2 is done: classifier case is closed (negative), yield case is open. Do not start before M0-M1 report; this is still the one expensive commitment in the plan |

**Run order**: M2 first (free, immediate, answers the most important open question — does S1 even
still matter). M0 in parallel (pure reconnaissance, no SU risk). M1 once M0 clears. M3-M4 in
parallel with M0/M1 (independent of fj7 entirely — ERA5/SRTM sourcing has nothing to do with the
Sentinel-1 archive). M5 only after M0-M2 land.

## Compute and Data Budget

- **Total estimated SU, must-run blocks only (M0-M4)**: roughly 100-150 SU — dominated entirely by
  M1's capped pilot; M2-M4 are each in the single digits to tens of SU.
- **M5, if triggered**: bounded above by the already-costed 7,957 SU MPC national figure (the
  point of this whole plan is to beat that substantially) and below by the already-costed 277 SU
  100 km/3-year figure if fj7 turns out no cheaper than MPC and the fallback is just extending the
  existing pilot region.
- **Data preparation needs**: GEE service-account calls for ERA5/SRTM (negligible volume, quota
  unconfirmed — flag before M3); fj7 read access is filesystem, not download, so no /scratch
  volume concern at pilot scale.
- **Human evaluation needs**: none — every block is a metric comparison against existing labels.
- **Biggest bottleneck**: M0. Everything else in this plan is either free (M2, reuses existing
  data) or cheap-and-independent (M3/M4), but M1 and M5 cannot start until fj7 scenes can actually
  be located, and that is currently unsolved, not merely unbenchmarked.

## Risks and Mitigations

- **Risk**: fj7's catalogue stays inaccessible and THREDDS doesn't substitute.
  **Mitigation**: fall back to querying an external free catalogue (Copernicus Data Space
  Ecosystem OData API, or ASF) for scene IDs/footprints from `copyq`, cross-referencing footprint
  + date against fj7's own directory tree only within the narrowed candidate set — still requires
  solving the product-ID → UUID mapping, which is not obviously possible from outside; treat this
  as a fallback to attempt, not a guaranteed fix, and report back honestly if it doesn't resolve.
- **Risk**: RTC processing cost (M1) exceeds MPC's, making fj7 pointless on cost grounds, and the
  governance argument for fj7 is already weakened (AgriWebb dropped, per `SENTINEL1_ACCESS.md` §4).
  **Mitigation**: this is a valid, useful negative result — it closes the question cleanly rather
  than leaving fj7 as a permanent "maybe cheaper" unknown. Report and stop; do not chase sunk cost
  into M5.
- **Risk**: GEE quota (M3) is tighter than assumed. **Mitigation**: CLAUDE.md already flags this
  as "ask the user to check if it becomes a constraint" — do that before M3 runs, not after a
  failure.
- **Risk**: reintroducing the fixed-test-set-but-not-every-arm-can-see-it bug from `S1_MODEL.md`
  §2 in Block 2's new arms. **Mitigation**: the exact commands in B2 already use `keep_s1both` for
  every arm including the S1-free baseline — this is deliberate, not an oversight, and should not
  be "simplified" back to the full 543-row test set.
- **Risk (spatial-validity, per `experiment-design` skill's conditional gate)**: none of these
  blocks introduce a new spatial split — all reuse the existing GroupKFold-on-site spatial
  transfer test already validated in `REVIEWED_MODEL.md`. No new MAUP/autocorrelation check is
  needed for this round; noted and skipped deliberately, not by omission.

## Final Checklist

- [ ] M0 resolved (scene discovery + toolchain) before any SU is spent on M1
- [ ] M2 uses `keep_s1both` for every arm, including the S1-free baseline
- [ ] M1 capped at 100 SU regardless of early-scene cost, with an explicit stop-and-report
- [ ] GEE quota checked with the user before M3
- [ ] Revisit-density covariate built before any multi-year (2017-2025) S1 feature is trusted (M5)
- [ ] M5 not started until M0-M2 have reported back
- [ ] No TrialCode, coordinate, or site-level record written to any non-`*_SENSITIVE` file
