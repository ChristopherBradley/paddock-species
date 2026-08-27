# Pipeline Memory — paddock-species

## Stage Status
- [x] `/launcher` — BRIEF.md + configs/default.yaml written
- [x] `/lit-review` — completed 2026-07-24. Output: `output/LIT_REVIEW_REPORT.md`, `output/paper-cache/lit-review-2026-07-24.json`
- [x] `/generate-idea` — completed 2026-07-24. Output: `output/IDEA_REPORT.md`. 10 ideas ranked as one coherent program under Gap #1 (backbone: Idea 1, national 10-species Presto fine-tune). No pilots run (no local/interactive-remote GPU) — all flagged "needs pilot validation on NCI Gadi", to be sized properly in `/deploy-experiment`.
- [x] **Stage 2 — Sentinel-2 phenology confirmation** (`src/sentinel_ndvi/`), COMPLETE 2026-08-07.
      Extraction: **1,630/1,630 trials, 0 FAILED, 74,326 rows, 0 duplicates**
      (900 Canola / 730 Wheat) in `…/derived/sentinel_ts/`.
      Discriminator is **CFI**, not NDYI (user's call — see below). Verdicts in
      `…/derived/nvt_confirmed.csv`; evidence in `…/derived/cfi_report.md` +
      `threshold_report.md`; figure in `…/derived/figures/`.
      **Result: CONFIRMED 1,229 (75.4%) | UNCERTAIN 284 (17.4%) | REJECTED 117 (7.2%)**
      — Canola 756/103/41, Wheat 473/181/76.
      Operating point: max CFI in **120-190 days after sowing >= 0.1309**, NDVI amp >= 0.35.
      Held-out J = **0.535** (selected on sow years <2021, applied to 2021+).
      All thresholds are CLI flags — rerun `phenology_check.py` to change them.

## Stage-2 flowering-timing findings (2026-08-07) — `flowering_timing.md`
Measured on 821 canola trials with a real CFI peak:
- **Calendar day-of-year aligns flowering tighter than days-after-sowing** (IQR 26 d vs
  30 d). Median peak **DOY 251 (~8 Sep)**. The DAS axis used so far is the weaker one.
- **Timing is only partly predictable**: lat r=-0.36, lon r=+0.22, year r=-0.16. State
  medians 242 (WA) → 258 (VIC), but within-state IQR is 20-31 d. Location narrows the
  window, it does not pin it. **Weather-based prediction is not worth it yet** — a fixed
  generous window plus a cloud-gap filter captures most of the benefit.
- **Cloud hides the peak**: 17 % of canola trials have a >21 d clear gap inside 100-200 DAS,
  11 % have >28 d, against a flowering event lasting only 2-4 weeks. So for ~1 in 6 trials
  "no flowering detected" is unfalsifiable. **Filter on observability before believing a
  negative.**

## Why the colleague's PaddockTS heatmap looked so much sharper (2026-08-07)
Diagnosed, not guessed. Two independent causes, in order of size:
1. **Pooling seasons and regions.** Restricting to one year + one state + calendar axis +
   hierarchical clustering reproduces the signature: canola CFI peaks sharply at DOY ~255
   (0.18) vs wheat flat ~0.10, and clustering separates 9/10 wheat from 10/10 canola. That
   alone recovers most of the contrast. (`plot_timeseries.py --align doy --year --state
   --cluster`.)
2. **200 m window mean at a paddock CORNER vs paddock median.** Still un-tested, and the
   remaining gap. The trial GPS marks a corner, so much of the window is neighbouring
   paddocks, roads and trees. PaddockTS segments paddocks (`02_SAMGeo_paddocks.py`,
   `03_paddock-ts.py`) and takes the median — reuse that rather than Fields of The World,
   whose *benchmark* excludes Australia (only the model-predicted global product covers it,
   2024/25 only).
NOT a cause: colour scaling. Their 300-2300 raw-DN range is 0.03-0.23 in our 0-1 units,
i.e. the same range we plot.
Bonus: one wheat-labelled trial (see `memory/WORKED_EXAMPLES_SENSITIVE.md`) clusters with the canola block and shares their CFI
shape — a concrete label-mismatch candidate of exactly the kind Stage 2 exists to find.

## Cause #2 resolved (2026-08-07): use SAMGeo paddocks, NOT Fields of The World
Full write-up in `output/PADDOCK_BOUNDARY_BENCHMARK.md`. Benchmarked head to head on a
Yorke Peninsula 2020 canola site, judged on imagery, not on assumption:
- **SAMGeo traces the trial paddock exactly (57.3 ha); FTW merges it with two neighbouring
  paddocks (339.1 ha).** In a 3 km AOI: SAMGeo 25 polygons, all >=1 ha, median 32.6 ha;
  FTW 63 polygons of which **79 % are <1 ha slivers**, and its real ones run to 339 ha
  (1,307 ha at another site). FTW's size distribution is not a paddock distribution.
  Containment rate does NOT separate them (4/4 vs 3/3) — **polygon size is the discriminator**.
  Consistent with the known fact that the FTW *benchmark* excludes Australia.
- **Filter bug, worth remembering as a class:** PaddockTS's `perim_area = length/(area/1000)`
  is not dimensionless and is calibrated against its own 10x-inflated area. We had corrected
  the area to `/10000` but left their threshold ⇒ ratio 10x larger ⇒ **all 638 polygons
  silently rejected** (`638 raw -> 0 after filter`). Fixing one half of a coupled pair emptied
  the output with no error. Replaced with dimensionless **`P/sqrt(A) <= 8`** (square 4.0,
  circle 3.54) ⇒ 159 kept, median 33.1 ha.
- **Cost SOLVED (measured 2026-08-07): 2.51 -> 0.113 SU/AOI, a 22x cut.** Canola+wheat at
  full scale is now **154 SU (1.5 % of allocation)**, not 3,419 SU. Two gains multiply:
  1. **Size AOIs to their trials, not a fixed 0.1deg box** (`make_aois.py`): the median cell
     holds only **2** trials, so the median AOI is **3.0 km wide, not 11 km** ⇒ **10.9x less
     area**. This was the single biggest lever and it is nothing to do with queue tuning.
  2. **Split the pipeline and apply the OPPOSITE rule to each half** — the key insight:
     - *Stage 1 pre-segment is I/O-bound* (~25 % CPU). The user's "many small jobs" heuristic
       holds exactly: 4 CPU/16 GB cost **4.3x more and was not faster** (5:06 vs 4:52, same
       CPU-time). Cheapest bookable `normal` unit **1 CPU / 4 GB wins ⇒ 0.020 SU/AOI**.
     - *Stage 2 SAM is compute-bound and the heuristic INVERTS* — GPU is **8.3x cheaper** than
       CPU (2.8 s/AOI on V100 vs 339 s on 4 CPUs = **121x speedup**, easily repaying
       gpuvolta's 4.5x hourly rate). **0.093 SU/AOI.** Identical polygons either device.
  The monolithic job hid this: a 121x GPU speedup was buried behind a datacube read that was
  62 % of runtime. Don't reason about queue choice until the stages are separated.
- Smaller: model load is **9.4 s warm** (the 49 s figure was cold-cache), so batching matters
  less than expected — but ~40 s fixed job overhead still favours ~40 AOIs/GPU job.
  `gpuvolta` bills 12 CPUs per GPU regardless, so trimming its memory saves nothing. On
  `normal` the charge is `max(ncpus, mem/4GB) x 2 SU/hr`, so raising stage 1 from 4 GB to
  8 GB would DOUBLE its cost — 4 GB is sufficient for ~3 km AOIs, verified.
- **Caveat that constrains the whole approach:** the trial point sits **17-24 m from the
  paddock edge (~2 pixels)**, so containment is marginal and a 1-2 px error reassigns a site
  to the wrong paddock. Extraction needs an explicit nearest-polygon fallback that records
  which rule fired, and polygons should be eroded ~1 px before taking the median.
- **The "whole paddock = trial's crop" assumption is SOUND, per NVT protocol** (user,
  2026-08-07): NVT guidelines require the paddock surrounding a trial to be the **same crop
  type, sown within ~2 weeks** of the trial. This is a design property of the trial network,
  which is what justifies paddock-median as the estimator. Public GRDC pages corroborate the
  timing half ("sow at the same time as the grower for the paddock used or within days"); the
  same-crop-type clause is user-supplied from the NVT guideline doc and **should be cited from
  that doc before it appears in a paper** — I could not find it in public material. Verifiable
  from our own data once the CFI canola signature is clean.

## Paddock-median PILOT RESULT (2026-08-07) — adopt it; full write-up `output/PADDOCK_MEDIAN_PILOT.md`
42 AOIs / 203 trials, 2018-2023, every AOI holding both crops; both estimators extracted from
the **same scenes in one pass** so only spatial support varies. 6.6 SU total.
- **Paddock beats the window where it matters: at a 5 % wheat false-positive budget it
  detects 52.0 % of canola vs the window's 27.0 % — +21.0 pp, 95 % CI [+2.0, +39.7].** The
  only comparison here whose CI excludes zero.
- **Youden J hides this** (+0.026 [-0.095, +0.149], year-stratified — not significant). J
  weights the whole ROC equally and the curves cross; the gain sits at the high-specificity
  end, which is exactly the regime Stage 2 needs (a wheat trial called canola is the
  expensive error). **Always report sensitivity-at-fixed-FPR alongside J from now on.**
  Caveat recorded honestly: the fixed-FPR metric was chosen AFTER seeing the specificity gap,
  so it is a strong lead to confirm at full scale, not a settled number.
- **POOLING SEASONS DESTROYS SEPARATION — pooled J (0.318) is BELOW every individual season
  (0.400-0.778).** Absolute CFI level shifts between seasons so one shared threshold cannot
  serve all. **Fit CFI thresholds PER SEASON** — worth up to ~0.2 J, more than the estimator
  change itself. Same "pooling" effect as heatmap cause #1, now known to hit thresholds too.
- **Pilot validates against known baseline:** window per-season mean J = **0.545** vs the
  established full-set held-out **0.535** ⇒ the 42-AOI subset is representative.
- Matching: 76 % `contains`, 24 % `nearest<=50 m`, **17 % (34/203) had NO polygon within 50 m
  and were dropped — investigate before the full run** (may be the compactness filter, not
  the segmentation, discarding small/irregular paddocks). Restricting to `contains` doubles
  the advantage, i.e. the mechanism behaves as predicted.
- `pad_median` vs `pad_mean` correlate **0.9955** — the eroded paddock is near-homogeneous,
  independent support for the NVT same-crop-surround property. Use median anyway (free
  robustness to an unmasked tree line).
- **Next: run the full canola+wheat set (1,362 AOIs, ~154 SU).** The pilot's limit is power,
  not cost — 2,761 trials shrink the interval ~4.5x. The definitive run is cheaper than
  further deliberation.

## Infrastructure notes (2026-08-07)
- **gadi LOGIN nodes have direct outbound internet** (OpenAlex, HuggingFace, source.coop all
  200, no proxy). COMPUTE nodes do not — that asymmetry is what caused the PROJ hang. So
  literature search and dataset downloads can be done from a login node; keep bulk transfers
  on `gadi-dm`.
- **Login nodes KILL multi-threaded fits with NO error message (2026-08-08).** A bootstrap
  run of 21 boosted fits under `nohup` at `OMP_NUM_THREADS=8` simply vanished partway through
  — no traceback, no "Killed", the log just stops mid-progress. Cause is the login-node
  resource limit: at 8 threads CPU-time accrues ~4x faster than wall-clock, so a ~10 min job
  trips it. **Read a silent disappearance as an external kill, not a script bug** — the
  temptation is to go hunting for an exception that was never raised. Single-config
  `train_species.py` runs had fitted fine on the login node, which is why the limit had not
  been hit before; scale, not kind, is what changed. Anything with more than a couple of fits
  goes to PBS (`model_uncertainty.pbs`, ~4 SU).
- **The "1 CPU / 4 GB is cheapest" rule is for the I/O-bound extraction jobs and does NOT
  generalise.** Model fitting is compute-bound, so cores are used rather than billed idle;
  `normal` charges `max(ncpus, mem/4GB)` so 4 CPUs + 16 GB costs the same as 16 GB alone.
- Repo is now a **git repo** (first commit 2026-08-07). `.gitignore` hardened with a
  `**/*SENSITIVE*` catch-all plus per-trial output patterns.
- **derived/ moved `/g/data` → `/scratch/xe2/cb8590/paddock-species-data/derived`**; raw stays
  on `/g/data`. Scratch is purged after ~100 days — `./sync/sync_to_gadi.sh pull` anything
  worth keeping.

## Stage-2 finding (2026-08-07): CFI replaced NDYI, on the user's instruction
User directed: use **max CFI in the flowering period** (`CFI = NDVI * ((Red+Green) +
(Green-Blue))`, Tian et al. 2022; per `PaddockTS/Code/indices_etc/indices.py`). This was the
right call and fixed the NDYI failure below: NDYI is pure visible-band yellowness so bare and
senescing soil scores high, whereas CFI's `NDVI *` factor keeps only yellowness over a green
canopy. Measured, all 1,630 trials:
- **CFI held-out J = 0.535** (in-sample 0.604; optimism +0.069) vs **NDYI 0.443-0.458
  in-sample**, i.e. NDYI's *optimistic* number is below CFI's *honest* one.
- Best flowering window is **late: 120-190 DAS**, not the naive ~70-140. Window placement
  matters more than width (J is flat across widths 50-100 once the start is right).
- Two methodology traps hit and fixed here: (1) the first window scan's optimum sat on the
  edge of the scanned grid — meaningless until the grid was widened past the peak;
  (2) window and threshold were both tuned on the same data, so a temporal held-out split
  was added. `cfi_report.py` now flags edge-optima automatically and always reports held-out J.
- Raw band means (`red/green/blue/nir_win_mean`, 0-1 reflectance) are now stored per scene,
  so a further index change costs **no** re-extraction. This rerun happened only because the
  first pass stored indices but not the bands behind them — don't repeat that.
- CFI is linear in reflectance so it is **scale-dependent** (unlike NDVI/NDYI): ours is on
  0-1, PaddockTS on raw DN, so absolute thresholds differ by 10000x and are not portable.
- Visual check (`figures/cfi_ndvi_timeseries_SENSITIVE.png`): canola CFI peaks clearly above
  wheat, NDVI does not separate the crops at all. Individual traces still overlap — CFI is a
  good discriminator, not a clean one. Also visible: canola stays greener than wheat
  ~130-190 DAS, an independent late-senescence signal worth testing as a complement.

## SUPERSEDED Stage-2 finding: NDYI is a WEAK canola discriminator here
Measured on all 1,630 trials, not assumed:
- Shipped default `NDYI_FLOWER_MIN=0.12` is **badly miscalibrated** — it flags 95.8 % of
  Canola but also 78.4 % of Wheat (Youden J = 0.17, near chance). It would label 844/900
  Canola CONFIRMED but only 100/730 Wheat, dumping **554 Wheat trials into UNCERTAIN**.
- Best achievable is **J = 0.458 at t = 0.240** (63.8 % Canola vs 17.9 % Wheat) — moderate
  at best. **No threshold gives a clean split**; the canola/wheat `ndyi_peak` distributions
  overlap heavily (medians 0.268 vs 0.181).
- The corner pixel is **worse** than the 200 m window mean (J = 0.331 vs 0.458), so the
  window design is not the limiting factor and shrinking it will not help.
- `NDVI_AMP_MIN=0.35` rejects 117/1630 (7.2 %) as "not a cropped paddock" — plausible, and
  it is a crop-presence filter, not a crop-type one (Canola/Wheat `ndvi_amp` medians are
  0.586 vs 0.578, i.e. no discriminating power, as expected).

Likely causes to investigate before trusting NDYI: the trial GPS is a paddock **corner** so
the window may cover substantial non-trial land; and canola flowering is brief (~2-3 weeks)
against a median of only 36 clear observations spread over ~8 months, so the flowering peak
is often simply not sampled. Reconsider whether NDYI can carry the confirmation step at all,
or whether Stage 2 needs a different discriminator.
- [ ] `/novelty-check` — SKIPPED. Never run; the direction was locked from the lit review instead.
      Owed before writing, since the novelty claim in a paper cannot rest on an unrun check.
- [ ] `/idea-review` — SKIPPED, same.
- [ ] `/experiment-design-pipeline` — SKIPPED. The experiment plan was built ad hoc, report by
      report, rather than as an up-front roadmap.
- [x] `/deploy-experiment` — **effectively COMPLETE as of 2026-08-25, run manually rather than
      through the skill.** ~870 SU across ~500 PBS jobs: paddock segmentation, the 3-class model
      (macro F1 0.821), the abandoned 4-class Grazing model, the inference stage, demo maps, the
      national cost benchmark, and the first ABS/ABARES validation. `output/NEXT_STEPS.md` is the
      current state; `output/archive/` holds the long history.
- [ ] `/auto-review-loop` — NOT STARTED. This is the next pipeline stage once the 100 km maps land.
- [ ] `/generate-report` — NOT STARTED.
- [ ] paper-writing-pipeline stages — NOT STARTED.

**Honest position in the pipeline (2026-08-25): stage 2 of 4 — experiments — nearly done, with
three earlier stages skipped.** The skipped ones are cheap to run and matter for the paper, not
for the science: novelty-check and idea-review would be run before drafting, not before more
experiments.

## Direction locked in (2026-07-24)
User selected **Gap #1 only** (foundation-model fine-tuning on GRDC labels for species-level classification) as the direction to pursue. Gaps #2–#5 stay in the report for context but are not separate contributions right now. Hard constraint: **output must stay 10 m resolution** throughout (downstream tree-shelter project needs paddock/tree-line detail) — this rules out MODIS-based features/comparisons as core inputs.

## Key lit-review takeaways carried forward
- Two 2024/2026 Australia-specific papers (WA XGBoost/LSTM; MDB Sentinel-1+2+MODIS fusion) — now fully read (PDFs in `extra papers/`). Both train on privately-sourced, non-field-verified labels (DAS model output; harvester yield-monitor polygons), not GRDC-style ground truth — a real edge for this project. Also yielded two design insights: (1) MODIS winter GPP beat Sentinel-1 as a single predictor in the MDB study — test it as a cheap feature; (2) spatial (site-to-site) transfer outperformed temporal (season-to-season) transfer — structure this project's own validation to test both. Canola separability is drought-sensitive, not unconditionally easy.
- Newman & Furbank (2021) NVT dataset **confirmed** (by user) to be the same underlying GRDC trial network — not independent public data. GRDC contested its publication on legal grounds. See auto-memory `grdc-data-legal-sensitivity`. No further follow-up needed.
- No `arxiv_fetch.py` / `semantic_scholar_fetch.py` tools found in `~/.claude/skills/` — external search this round used WebSearch only (metadata-level, no PDF downloads despite `ARXIV_DOWNLOAD: true`). Locate or install these before a deeper lit pass.
- Full gap ranking and literature tables are in `output/LIT_REVIEW_REPORT.md` — read that before starting `/generate-idea`.

## Stage 2 engineering notes (2026-08-06)
Three changes made to `src/sentinel_ndvi/` after the smoke test exposed problems — all
documented in that folder's README:
1. **Partial-cloud bias (correctness).** The extractor kept any date with ≥1 clear pixel.
   Sparse-clear scenes (swath edge / cloud halo) read systematically low in *both* NDVI and
   NDYI, so they depressed the p5/p20 baselines and inflated *both* `ndvi_amp` and
   `ndyi_peak` — a one-directional bias toward CONFIRMED (and wheat → UNCERTAIN). Fixed by
   recording `n_px_total` in extraction and filtering on `--min-clear-frac` (default 0.5) in
   `phenology_check.py`. Kept as two steps so the raw extraction stays reusable.
2. **Crash/timeout resilience.** Results were accumulated in memory and written once at the
   end, so a walltime overrun lost the whole chunk. Now appended per trial; re-running a
   chunk resumes from its status file, and `extract_ndvi.sh` skips only *complete* chunks
   (compares row counts) so partial chunks are resubmitted, not silently accepted.
3. **PBS sizing.** 16 GB → **4 GB** (peak RSS measured 240 MB). On the `normal` queue the
   charge is `max(ncpus, mem/4GB)`, so 16 GB billed 4 CPU-equivalents for unused headroom.
   Also moved `.o`/`.e` logs to `/scratch/xe2/cb8590/paddock-species-logs/` (they were
   landing in the git repo) and added a `.gitignore` pattern as backup.

Measured: ~33 s/trial, 25 % CPU (I/O-bound on `/g/data`) ⇒ ~55 min per 100-trial chunk.
Note PBS only stages `.o`/`.e` logs back at job *exit*, so the per-trial
`chunk_###_status.csv` is the only live progress signal.

## ✅ ROOT CAUSE FOUND 2026-08-07 — `PROJ_NETWORK=ON` + no internet on compute nodes
**`module load dea/20231204` exports `PROJ_NETWORK=ON`.** PROJ then fetches datum grids from
`cdn.proj.org` (CloudFront `108.158.20.x`); **gadi compute nodes have no outbound internet**,
so it retries forever at ~0 % CPU until walltime kills the job. Fix: `export
PROJ_NETWORK=OFF` **after** the module load in `extract_ndvi.pbs` (also set defensively in
`extract_ndvi.py`). Validated: chunk_001 went from 0 trials in 21 min to ~37 s/trial.

Whether a trial hangs depends on its **location** (some sites need a grid, some don't) — so
it looks random and load-dependent when it is neither. **Concurrency was a red herring; the
database was never involved.** The two sections below record what was believed at the time
and are kept only as a reminder of how the misdiagnosis happened — do not act on them.

Debug sequence that worked, reusable for any "gadi job hangs at 0 % CPU":
1. `qstat -f <job>` → `resources_used.cput` tiny vs walltime ⇒ blocked, not slow.
2. Probe the suspected service from the login node *while jobs are stuck*.
3. `dc.find_datasets(...).uris` to check local-file vs S3 resolution.
4. `ssh <compute-node>` (allowed while you have a job there) → `strace -p <pid>` — this is
   what actually named the culprit. Also `/proc/<pid>/status` `SigPnd`/`SigCgt`.

Lesson about my own reasoning: I twice asserted a cause from correlation (recovery
coincided with killing jobs) rather than from a mechanism, and wrote it into the docs as
near-fact. The user's pushback ("I run 200 jobs at once") was the correct signal and it was
right to go and read their reference scripts. **Get a mechanism before writing a cause down.**

## ✗ SUPERSEDED (kept as a record of the misdiagnosis) — "DEA index pool exhaustion"
All 17 chunks submitted at once; every job blocked with no error; 16 killed at the 4 h
walltime. Cost **~136 SU (8.06 × 17) for 130/1630 trials**.
Symptoms: **8 of 16 jobs wrote zero trials in 4 h** (blocked before their first result)
while jobs that got going ran up to 90 min longer; login-node `dc.list_products()` hung;
all recovered once jobs were killed. **Signature: TCP to `dea-db.nci.org.au:6432` connects
instantly while queries hang** — pgbouncer accepting the socket, then blocking for a
backend slot.

**Do not treat pool exhaustion as established.** The recovery coincided with killing the
jobs, so an unannounced outage ending then is not excluded (no NCI notice covers the
window). Strong counter-evidence from the user: their
`shelterbelts/pbs_scripts/sentinel.sh` routinely fans out **~200 concurrent jobs** against
the *same* index (`datacube.Datacube()` + `load_ard`, one connection held per run, zero
concurrency control) without this failure — i.e. **this project's access pattern is not
materially different from theirs**. Only clear difference: their walltime is 30 min vs 4 h
here, so a starved job there dies fast and reads as an ordinary missing chunk. The real
per-user limit is **unmeasured**; if this recurs, ask the NCI/DEA helpdesk rather than
guessing again.

User's standing instruction (2026-08-07): since the two approaches are equivalent, cap at
**4 concurrent jobs**.

Defences added and verified (`src/sentinel_ndvi/`): lane-based submission with
`-W depend=afterany` (`--lanes`, default 4); a 60 s index pre-flight probe exiting 75;
a per-trial SIGALRM watchdog (`--trial-timeout` 300 s) recording `FAILED`/`TIMEOUT`;
`--max-consecutive-timeouts` 5 aborting the job; and `FAILED` trials being **retried on
resume** so an outage cannot silently become permanent missing data.

What saved the run: results are appended per trial, so 130 trials survived. The original
buffer-until-the-end code would have salvaged **nothing** from a 4 h walltime kill.

## Token/cost notes
- CLAUDE.md `AUTO_PROCEED` flipped from `false` to `true` mid-session on 2026-07-24 (external edit, not by this session) — later stages may proceed without a checkpoint unless the user says otherwise.

## Trial→paddock REVIEW system (2026-08-07) — `make_review_layers.py`, `review_render.py`
User inspected `_filt.gpkg` in QGIS and found some chosen paddocks bad. Root issue: the trial
point was not in any layer, so "which polygon was chosen" was invisible. Now written per AOI:
`<stub>_trials.gpkg` (points + flags) and `<stub>_chosen.gpkg` (the ONE selected polygon).
- **Risk-ranked `review_sites.csv`, worst-first** — the ranking is the point: reviewing ~2,000
  sites in file order has no stopping rule; worst-first lets the user stop when flags go quiet.
- **Measured failure modes on 169 pilot trials** (NOT the ones assumed):
  - `not_contained` 36.5 %, `edge_close` 31 %, `bigger_neighbour` 21 %, `sliver` 17 %,
    `tiny` 8.4 %. **44 % score high-risk.**
  - **`treed` is a NON-issue: tree fraction over chosen polygons maxes at 0.036** (median
    0.000). The user's "treed area" impression came from viewing ALL polygons in `_filt.gpkg`
    rather than the chosen one. My first threshold (0.20) was dead — recalibrated to 0.02.
    **Lesson: calibrate flag thresholds to the observed distribution, not to intuition.**
  - **The real algorithmic bug: a tiny road/laneway sliver chosen over the adjacent real
    paddock** — 7/169 (4 %) picked <5 ha while a >20 ha polygon sat within 250 m (median
    2.2 ha vs 40.2 ha available). Visible in the top-risk contact sheet as trial points in
    narrow strips between fields. Fix in the matcher (prefer largest plausible polygon /
    minimum area) BEFORE asking a human to annotate these.
  - Overall matching is healthier than it looked: median chosen area **33.8 ha**, 76 %
    `contains`. The worst-first sheet oversold the prevalence — checked before believing it.
- **Claude-in-the-loop works and is cheap**: `review_render.py` builds CONTACT SHEETS (6 sites
  per PNG, not one) so many sites cost one image read. Model and human read the same
  `review_sites.csv`, so verdicts are directly comparable.

## FULL segmentation done (2026-08-07) + two findings from visual review
- **1,349/1,362 AOIs segmented for 97.6 SU** (under the 154 SU estimate), stage 1 finished in
  ~25 min at only 8 lanes. **Concurrency does NOT affect SU** — SU = per-job resources x
  walltime, so lanes buy wall-clock only. Only JOB COUNT costs anything (~40 s fixed startup
  each, so 20 AOIs/job ≈ 6 % overhead, 10/job ≈ 11 %).
- **4 GB OOM-killed the 2024 chunk (exit 137).** S2A+S2B+S2C all fly now, so revisit density
  and therefore the in-memory NDWI cube are far larger than in the 2017-2020 years the 4 GB
  figure was benchmarked on. **Use `-l mem=8GB` for 2023+ or AOIs wider than ~5 km.** The
  earlier "4 GB has no headroom" caution was right and this is where it bit.
- **DISCOVERY: SAM segments the NVT TRIAL PLOTS themselves as distinct polygons.** In the
  contact sheets many chosen polygons are 3-15 ha rectangles showing visible **plot striping**
  (the variety strips). 22 % of chosen polygons fall in 3-15 ha, 29 of 38 containing the
  point. So a "suspiciously small polygon" is often NOT an error — it is the trial itself.
  This reframes the `tiny` flag and means the upgrade rule (below) is a judgement call, not a
  pure fix: the trial plot is the most directly-labelled pixels, the surrounding paddock has
  more of them (and per NVT protocol the same crop). **Ask the user which they want.**
- **Matcher upgrade rule added** (`match_polygon`, shared by extraction AND review so they
  cannot drift): a match under 5 ha is upgraded to a >=3x larger polygon within 150 m. Fired
  on 7/169 pilot trials; visual check says 5-6 clearly right, 1 questionable (farmyard).
  Rule name records the upgrade (`+upgraded_1.3to35ha`) so it is auditable/reversible.
- **Genuine bad polygons visible only in imagery**, which no flag caught well: a 448 ha
  polygon that is a linear DRAINAGE LINE, and thin road-verge triangles. Shape flags catch
  some; `sliver` (compactness>6) is the useful one.
- **Review contact sheets: 12 panels/sheet is legible** (tested) — halves the cost of a review
  pass vs 6. ~2,761 trials, ~45 % flagged ⇒ ~100 sheet reads for a full flagged pass.

## Review CALIBRATION result (2026-08-07) — `…/review_full/REVIEW_CALIBRATION.md`
Stratified sample, 60/96 trials reviewed by 3 independent model reviewers (2 stopped early on
the user's instruction to save quota). **Reviewer agreement 92 % exact, 96 % on usable-vs-not**
⇒ the verdicts are reproducible and the rates can be relied on.
- **Matched trials are in good shape**: usable rate `clean` 92 %, `edge_close` 92 %,
  `not_contained` 92 %, `bigger_neighbour` 83 %. **The flags do NOT track real failure** —
  most flagged matches are fine, and a risk-0 panel hid a cloud write-off. So exhaustive
  review of flagged sites is NOT worth it.
- **The one real problem is the `none` stratum: 0/12 usable, 657 trials (24 %)**, and
  reviewers saw a cropped field at the dot in 10/12.
- **DIAGNOSED, and the obvious fix is WRONG.** 97 % of unmatched trials have a RAW polygon
  containing them; the **compactness filter removed 98 % of them**. But those polygons are
  median **632 ha, compactness 12.8** — SAM under-segmented and merged many fields into one
  blob. Relaxing compactness would inject multi-crop blobs, i.e. recreate the exact Fields of
  The World failure this project rejected. **The filter is right; SAM is the weak link here.**
  ⇒ Recommended: **hybrid fallback** — paddock median where a real paddock exists (76 %),
  200 m window (already extracted in Stage 2) for the rest. Free, loses nothing.
- **COST LESSON (measured):** a subagent reviewing 2 contact sheets burned **101,677 tokens**
  — ~50k/sheet, **13x my estimate** of ~3.7k, because tool calls/reasoning/cross-checking
  dwarf the ~2.5k image tokens. Session went 16 % → 45 % on this stage alone. **Never size an
  image-review job from image tokens alone.** Exhaustive passes (113-231 sheets) are
  infeasible; stratified sampling is the only affordable design.
- Caveat on extrapolation: strata are "trials whose RAREST flag is X" but the population
  counts are "trials carrying flag X" — overlapping, so the ~922 estimate is a loose upper
  bound. The `none` stratum is exact (match_rule is unambiguous).

## User verdicts that TUNED the matcher (2026-08-07) — two worked examples, both encoded
User reviewed `review_shortlist_SENSITIVE.gpkg` in QGIS and gave two rulings that pull in
OPPOSITE directions, which is what made them useful:
- **Example A** (`memory/WORKED_EXAMPLES_SENSITIVE.md`) — chosen 5.1 ha trial strip; "take the bigger paddock immediately west"
  (51.6 ha, compactness 5.4, 41 m away). Upgrade WANTED.
- **Example B** (same file) — chosen 11.6 ha is "good enough (a small subset of the paddock)"; the
  larger SAMGeo polygon (351.9 ha, **compactness 7.2**) is BAD because it spans neighbouring
  paddocks and forest. Upgrade REFUSED.
⇒ Three changes to `match_polygon`, verified to reproduce both rulings exactly:
1. `min_paddock_ha` 5.0 → **10.0**. MING6's 5.1 ha missed the old threshold by 0.1 ha; 10.0
   sits between the two chosen areas (5.1 and 11.6) so it catches one and spares the other.
2. New **`max_upgrade_compactness=6.0`** — the upgrade TARGET must itself be paddock-shaped.
   Compactness cleanly separates a real neighbouring paddock (5.4) from an under-segmented
   blob (7.2). Bigger is not better; this is the guard against recreating the FTW failure.
3. Tiebreak is **NEAREST eligible, not largest**. Largest reached past the correct 51.6 ha
   paddock at 41 m to an unrelated 96.7 ha one at 98 m. The trial sits on the edge of its own
   field, so "immediately alongside" is the right target.
**Lesson: two opposing user judgements pinned down a rule that neither alone could.** When a
threshold is contested, ask for one example each side rather than guessing a value.

## User DECISION (2026-08-07): accept SAMGeo's misses, keep only good samples
For the ~24 % of trials where SAMGeo under-segments, the user chose (over tuning SAM
parameters or trying another segmenter): **accept the loss and keep only the good samples for
training** — "easiest for now". Tuning SAM / alternative segmentation stays on the table as
future work, not now. So downstream training must filter on match quality, and the
`match_rule` column is the filter key.

## User preference: reports live in the REPO
Write markdown reports to `output/` in the repo, not `/scratch` — the user has VSCode open
there. Anything with TrialCodes/coordinates must be named `*_SENSITIVE.*` so `.gitignore`'s
`**/*SENSITIVE*` catches it: readable in the editor, never committable. Recorded in CLAUDE.md.
Also: per-AOI layer filenames are AOI stubs, NOT TrialCodes — the user could not map one to
the other. `make_qgis_package.py` now consolidates a shortlist into ONE gpkg (layers
`trials`/`chosen`/`candidates`) so review is a single drag-and-drop.

## FULL-SCALE RESULT (2026-08-07): pilot replicated on 2,103 trials
Paddock extraction over all 2,761 canola+wheat trials with the tuned matcher:
**2,103 matched (76 %)** — 1,234 Wheat, 869 Canola. Rules: 1,545 `contains`, 402 `nearest`,
156 `upgraded`. Median chosen paddock 58 ha (p10 10.5, p90 289).
- **Canola detected at a 5 % wheat false-positive budget, per-season thresholds:
  window 32.4 % → paddock median 54.5 %, gain +22.1 pp** over 8 seasons. The pilot's
  +21.0 pp [+2.0, +39.7] on 129 trials replicates almost exactly at 16x the sample. This is
  now a solid result, not a lead.
- **Sensitivity check: excluding paddocks >300 ha barely moves it (+23.0 pp, n=1,907)** — so
  the large/under-segmented polygons neither drive nor materially damage the headline.
- **9 % of chosen polygons exceed 300 ha (max 1,310 ha)** and this is NOT the upgrade rule's
  doing — 9 % of non-upgraded vs 10 % of upgraded, i.e. equal. The cause is the base filter's
  `--max-area-ha 1500` admitting under-segmented merges. Pending user decision whether to
  tighten to ~300 ha (their own rubric calls >300 ha with no internal structure `too_big`).
  Do NOT change it unilaterally: it affects 9 % of the training set.

## THREE-GROUP HEATMAPS DELIVERED (2026-08-07) — `src/paddocks/crop_heatmap.py`
Full write-up `output/CROP_HEATMAPS.md`. 40 figures (year x state) + one profile sheet +
per-panel and consolidated GeoPackages, in `derived/figures/crop_heatmaps/`. ~100 SU.
- **Coverage went 2,103 -> 3,439 trials across all 9 NVT crops.** The 7 non-canola/wheat crops
  had NEVER been segmented; 1,028 new AOIs, 1,020 segmented (99.2 %). Only 272 other-crop
  trials could reuse an existing AOI — the canola/wheat AOIs are sized tight to their own
  trials, so requiring a 1500 m paddock margin rejects most apparent overlaps. Don't assume
  co-located trials share an AOI; check the margin.
- **The signature is real and dated: canola peaks at DOY 236-271 (median 251)** against a flat
  wheat baseline, in nearly every panel. Weak-to-absent in 2020 VIC, 2021 WA, 2024 VIC.
- **NEW AND IMPORTANT — the honest negative class is 8 pp harder than wheat.** Canola detected
  at 5 % FPR: **53.5 % vs wheat, 45.4 % vs the other 7 crops, 45.7 % vs both.** Wheat-only
  replicates the established 54.5 %, so the pipeline change is sound; but lentil, faba bean,
  field pea and lupin all sit ABOVE wheat on peak CFI. **Stop reporting canola-vs-wheat alone
  — it flatters the index.** Median peak CFI: Canola .204 >> Lentil .166, Faba .164, FieldPea
  .162, Lupin .162, Oat .155, Barley .145, Wheat .142, Chickpea .140.
- **Wheat and Other are NOT separable from each other by CFI** (their median profiles overlay
  almost exactly), which is why 3-group cluster purity is only 36-57 % nationally while the
  wheat-vs-chickpea QLD panels hit 62-82 %. CFI answers "is this canola", not "which crop".
- Clustering recovers canola blocks without seeing labels — e.g. 2020 SA puts all 10 canola
  trials in one contiguous block. Rows that cluster with the wrong colour are the
  label-mismatch candidates the user can now open directly in QGIS by `panel` + `label`.

## Two pipeline BUGS found and fixed (2026-08-07)
1. **`argparse` silently overrode a tuned default.** `match_polygon`'s `min_paddock_ha` was
   raised 5.0 -> 10.0 per the user's Example A ruling, but `--min-paddock-ha` still declared
   `default=5.0`, so EVERY run matched at 5.0 and that ruling never took effect. Fixed by
   defaulting the CLI flags to `None` in both `extract_paddock.py` and `make_review_layers.py`.
   Effect: 1.7 % of trials changed paddock (median 7.2 -> 51.6 ha), upgrades 156 -> 187.
   **Class of bug worth remembering: a default written in two places will drift, and the
   symptom is silence — the tuning "was applied" and nothing failed.** Regression anchors are
   now in `memory/WORKED_EXAMPLES_SENSITIVE.md`; re-run them after any matcher change.
2. **Row labels were being painted over by the colorbar** in the first heatmap draft — the
   figure looked finished while missing the one thing linking it to the GeoPackage. GridSpec
   needs an explicit spacer column for right-hand tick labels.

## Tree masking on the paddock median: implemented, and measurably POINTLESS (2026-08-07)
`extract_paddock.py` now applies the same 1 m canopy mask the 200 m window used. Measured:
median 0.9 % of paddock pixels are canopy, 20 % of paddocks lose >5 %, one loses 62 % — but
the effect on CFI is **nil (median +0.00000, p90 +0.00025 over 64,169 trial-dates)**. Erosion
plus a median already handled it. KEPT anyway, because it must be applied identically to every
crop group or the three-way comparison confounds spatial support with tree contamination.
Answering "does this matter?" with a number was worth more than the change itself.

## GIT/NDA: `memory/MEMORY.md` is TRACKED and had TrialCodes in it (2026-08-07)
Caught before any commit — `git show HEAD:memory/MEMORY.md` had zero matches, so nothing
leaked. Codes moved to `memory/WORKED_EXAMPLES_SENSITIVE.md` (gitignored via `**/*SENSITIVE*`)
and MEMORY.md now says "Example A/B". **When writing to MEMORY.md, never paste a TrialCode —
it is a tracked file.** Checked: 0 tracked files now contain a TrialCode pattern.

## Quality filter for "was this paddock segmented correctly" (2026-08-07)
User asked to drop bad segmentations. Filter is deliberately NOT the risk score — calibration
showed 83-92 % usable in every flag stratum, so `not_contained`/`edge_close`/`bigger_neighbour`
would discard mostly-good data. Shape and size are what review actually caught in imagery:
`sliver` compactness>6 (640 dropped, 19 % — the expensive one, calibrated on only two worked
examples, tunable via `--max-compactness`), `too_big` >300 ha (142), `too_small` <5 ha (142),
<15 clear obs (27), `treed` >20 % (4). 3,439 -> 2,484 trials.

## TARGET IS NOW 3 GROUPS (2026-08-08, user's decision) — `GROUP3_MODEL.md`
Canola / Cereal / Legume, replacing 9-class species. `train_species.py --target` defaults to
`group3`; species kept only for the archived confusion matrix.
- **Temporal macro F1 0.716, spatial 0.707** (chance 0.333), full 659-trial test set.
  Cereal F1 0.82, Canola 0.76, **Legume 0.57 (precision 0.51) — the remaining headroom**.
- **Spatial ≈ temporal now (0.707 vs 0.716)**, where 9-class was 0.273 vs 0.316. Generalising
  over the fence was the harder test and grouping largely closed it. Best news in the run.
- **BEWARE the 0.78-0.82 figure in `LABEL_QUALITY.md`** — that is the CLEAN test subset (323
  trials, no co-location/conflict), which is smaller, easier, and 41.8 % canola vs 14.1 % in
  the rest. **Quote 0.716.** A restricted-subset score is not comparable to a full-set one.
- Justified by the species confusion matrix, not just convenience: errors are almost entirely
  WITHIN the groups (Barley->Wheat 60 vs 15 correct, Oat->Wheat 19 vs 0, chickpea+lentil both
  into field pea). Collapsing merges distinctions the model never made.

## PSEUDO-LABELLING CANOLA RULED OUT (2026-08-08) — `CANOLA_PSEUDO_LABELS.md`
- **Precision is prevalence-dependent; TPR/FPR are not.** NVT is 27.5 % canola, a real
  landscape ~5-10 %. Peak CFI hits 99 % precision at 0.9 % recall in-sample, but the same rule
  gives 84.7 % precision at 10 % prevalence and 72.5 % at 5 %. **Never carry a precision figure
  from a curated set to the wild — carry TPR/FPR.**
- **The confidently-labelled paddocks are the ones already classified correctly**: model recall
  100 % on the top CFI decile, 93 % at 75-90th, **62 % on the bottom half**. A confidence rule
  selects from the top by construction, so the selection mechanism and the failure mechanism
  are the same mechanism. Self-training would sharpen the boundary, not extend it.
- Right way to use unlabelled paddocks is self-supervised pre-training (Presto), which selects
  on nothing.

## PADDOCK REVIEW IS THE CRITICAL PATH (2026-08-08) — `build_review_package.py`
User is reviewing all polygons by hand before publishing. **Review by POLYGON not trial: 3,222
trials share 1,973 distinct polygons (39 % less work).** Triage catches 17/17 hand-judged bad
at 2/19 false-flagged, via THREE different signals — point >25 m outside (192), area >300 ha
(222), crop conflict (207). In-sample on 36 points, hence a 150-polygon `validation` batch
sampled from the UNFLAGGED pile to measure the miss rate rather than assume it.
- **MY WRONG CONCLUSION, worth remembering as a class.** I declared "no geometric rule can
  separate good from bad" from two polygons 0.1 ha apart with opposite verdicts — having tested
  only AREA and COMPACTNESS. Containment separates them cleanly (0 m vs 137 m). The trap:
  `match_rule` reads `contains+upgraded_...` where "contains" describes the polygon the point
  fell in BEFORE the upgrade moved the match. **All 259 upgraded matches have their point
  OUTSIDE the polygon they ended up with**; the upgrade searches to 150 m, enough to cross a
  road. **"No rule can separate these" is only ever a statement about the features tried.**
- User's policy: **full paddock always, never the trial site.** The collision-aware upgrade
  block is therefore OFF by default (it was leaving trials on 3.1 ha strips).
- `link_tifs_by_trial.py` exposes the Fourier-NDWI composite SAM segmented as
  `by_trial/<TrialCode>_ndwi.tif` (symlinks, 884 KB for 1.6 GB of composites).

## PBS SIZING: permutation_importance dominates `train_species.py` (2026-08-08)
It uses `n_jobs=-1`, so **runtime scaled silently with ambient core count**: ~10 min on a login
node (many cores), **>90 min unfinished on 4 CPUs**, **75 s on 12 CPUs** with
`--importance-repeats 5`. The 4-CPU job would have hit walltime and lost everything, because
the report only flushes when the file closes. Set `OMP_NUM_THREADS=1` when the importance
workers are already using every core. **A script whose runtime depends on ambient hardware is
a trap — make the cost an explicit flag.**

## CO-LOCATED TRIALS SHARE ONE PADDOCK — the label problem (2026-08-08)
User's correction: when they asked about "data quality" they meant **bad paddock
segmentation**, not cloud gaps. They were right and `separability_diagnosis.py` could not
have found it — every driver it tested (cloud gap, match rule, paddock size, compactness) is
a property of ONE trial's polygon, while this is a property of the RELATION between trials.
**Class of blind spot worth remembering: a per-row diagnostic cannot see a between-row defect.**
- **Mechanism**: NVT runs several crop trials side by side in one field. SAM segments that
  field as ONE polygon ⇒ every trial there gets an IDENTICAL paddock-median series under a
  DIFFERENT crop label. Where 4 crops share a polygon, no classifier can exceed 25 % on them.
- **Scale (2,477 training trials): 69.7 % share their polygon with another trial in the same
  year; 31.8 % (788) share it with a DIFFERENT crop.** 381 trials share exact coordinates.
  One 2021 WA site has 4 crops on one 41.6 ha polygon, another 3 crops on 6.7 ha.
- **Proof of harm, measured WITHIN canola so no class-mix confound: canola on a shared
  polygon reads median CFI 1489 vs 1971 unshared — +482 [95 % CI +348, +551].** The paddock
  median is averaging canola with its neighbour.
- Per-crop co-location rate tracks per-crop F1 at **spearman -0.854 (p=0.003)**, stronger than
  class size (+0.628, p=0.070). Canola least co-located (24 %) and best (0.81); lentil most
  (89 %) and worst (0.07). The two are confounded — rare crops are also the co-located ones.
- **The upgrade rule is a main generator**: 72.3 % of upgraded matches land on a polygon
  another trial also uses; upgraded trials conflict 41.9 % vs 30.6 % non-upgraded; upgrades
  from a <2 ha origin score AUC 0.749 vs 0.832. This matches the user's visual calls — the
  trials they flagged as wrong paddocks were upgraded from ~1 ha origins.
- **Collapsing to Canola/Cereal/Legume resolves 540 of the 788 conflicts (69 %)** because
  co-located trials are usually the same agronomic group. Only 59 polygon-groups are
  genuinely cross-group.
- **BUT cleaning does not MEASURABLY improve the model — suggestive, not established.**
  Against the full training set, dropping conflicted trials gives -0.006 [-0.067, +0.055].
  Against a random subsample of IDENTICAL size (n=894, the comparison that separates *which*
  rows were dropped from *how many*), dropping co-located trials gives **+0.027 [-0.052,
  +0.101] on 9-class, +0.042 [-0.004, +0.089] collapsed to 3 groups, +0.035 [-0.018, +0.085]
  native 3-class**. All three point the same way and the 9->3 one barely misses zero, so the
  benefit is probably real and around +0.03-0.04 — but 323 clean test trials cannot confirm
  it. **Do not claim the cleaning fixes the model; say it is unconfirmed and give the CI.**
  Real signal damage does not automatically convert into recoverable accuracy.
- **Where the model actually works is the 3-group task: macro F1 0.78-0.82 vs 0.38 on
  9 classes.** And native 3-class training is NOT better than collapsing 9-class predictions
  (all four arms favour collapsing, none significantly) ⇒ **keep the 9-class model and
  collapse at prediction time** — same score, finer output retained.
- **Confound to respect**: the "clean" subset is 41.8 % canola vs 14.1 % in the rest, so a
  higher score on clean test rows is NOT evidence of label purity alone. Paddock sizes are
  comparable (median 54 vs 60 ha), so it is a class-mix confound, not a paddock-quality one.
- Tools: `flag_paddock_conflicts.py` (per-trial `conflict_9class`/`conflict_3class`),
  `rematch_paddocks.py` (matching-only re-run, no datacube — verify geometry before spending
  SU on re-extraction), `label_quality_experiment.py`. `extract_paddock.py`'s upgrade now
  refuses a polygon a different crop already claimed.

## MODELLING STARTED (2026-08-07 night) — `train_species.py`, `separability_diagnosis.py`
Reports: `output/NEXT_STEPS.md` (read this first), `SEPARABILITY_DIAGNOSIS.md`,
`SPECIES_MODEL_indices.md`, `SPECIES_MODEL_bands.md`.
- **10 BANDS NOW EXTRACTED — this had never been done.** Every prior pass stored only
  ndvi/ndyi/cfi, so no multi-band model was possible. `extract_paddock.py --all-bands` writes
  paddock medians of all 10 Presto bands; 91 jobs, ~38 CPU-h, `derived/samgeo/bands_ts/`.
  **Repeat of the Stage-2 mistake avoided: store BANDS, derive indices downstream.**
- **User's separability question ANSWERED: not mainly data quality.** 32 panels, AUC 0.51-0.99.
  Sampling explains ~24 % of variance. Only driver whose CI excludes zero is **season vigour**
  (median NDVI amp, r=+0.41 [+0.03,+0.73]) — agronomic, not measurement. Cloud gap, match
  rule, paddock size, compactness all indistinguishable from zero. Underpowered at n=32, so
  "no evidence for" not "evidence against". **Don't use weak panels as a QC filter** — that
  would discard real agronomic variation and bias accuracy optimistically.
- **Canola is nearly solved; the rest are not.** 3 indices, temporal transfer, geography
  EXCLUDED: macro F1 0.316 / spatial 0.273 (chance 0.111). But Canola **F1 0.81**, Wheat 0.68,
  Chickpea 0.33, pulses 0.22-0.27, Lentil 0.07, **Oat 0.00**.
- **THE headline number: canola at 5 % FPR goes 45.7 % (CFI threshold) -> 77.0 % (model on the
  SAME 3 indices), +31 pp.** Modelling the whole seasonal shape beats thresholding one index
  at one time by more than any data change so far. A canola-only 10 m map is already
  defensible and is the fastest publishable output — don't gate it on the 9-class model.
- **10 BANDS ALONE DO NOT BEAT 3 INDICES — corrected result, believe this one.** A partial run
  (57 % of data) showed big minor-crop gains (Lupin 0.27->0.48, Lentil 0.07->0.25) and I wrote
  that bands were winning. **On full data those gains VANISHED** (Lentil 0.00, Lupin 0.14 —
  worse than baseline). Full data: temporal macro F1 **0.301 bands vs 0.316 indices**, canola
  @5%FPR **62.9 % vs 77.0 %**. Bands DID win on spatial transfer (0.304 vs 0.273).
  **Lesson: a partial-extraction run is a sample-size experiment, not a feature experiment —
  do not read crop-level F1 off one.**
- **Probable cause, and it is a methodology bug not a fact about bands:** CFI is NON-LINEAR in
  reflectance, so median(per-pixel CFI) — what `ts_v2` stores — is NOT CFI(median reflectance)
  — all a band file can reconstruct. The band model's CFI proxy is degraded, which is exactly
  why its biggest loss is canola, the class CFI carries. Predicts the feature sets are
  COMPLEMENTARY: `SPECIES_MODEL_combined.md` (325 features) tests this.
  **If extracting bands again, also store per-scene per-pixel index medians — they are not
  recoverable from band medians.**
- Barley/oat improved in neither run; Sentinel-1 backscatter is the next candidate for cereals.
- **Validation design that must not be relaxed:** GroupKFold on `site`, not random. The same
  paddock recurs across years; a random split memorises locations and reports a fantasy score.
  Geography (lat/lon/year) excluded by default — chickpea is effectively a QLD crop, so a model
  given coordinates learns WHERE crops grow, not what they look like.
- **Measurement bug caught in my own work:** first permutation-importance pass ran in-sample on
  a boosted model and returned all-negative importances. That is a broken measurement, not a
  weak signal. Now run on the temporal holdout with n_repeats=10 and macro-F1 scoring.

## SENTINEL-1 IS THE BIGGEST FEATURE GAIN SO FAR (2026-08-09) — `output/S1_MODEL.md`
Downloaded from MPC (6 copyq shards, 1,149 AOIs, 33 GB, **91.5 SU**), paddock medians of
VV/VH/VH-VV extracted with the same polygon, erosion and median as the S2 pipeline.
- **Controlled 3-way, identical 1,588 train / 477 test rows: optical 0.812, S1 alone 0.787,
  optical+S1 0.856 temporal — and 0.822 / 0.789 / 0.866 spatial. +0.044 both splits**, ~4x the
  control sd of 0.010 and about twice what the whole hand review of 1,973 polygons bought.
- **It lands on Legume, exactly as predicted: F1 0.67 -> 0.75, precision 0.62 -> 0.75**
  (spatial 0.67 -> 0.77). The named failure — cereals leaking into Legume — is what S1 fixes.
- **S1 alone is worse than optical alone but NOT redundant**: the combination beats both by a
  lot, so the sensors carry different information rather than noisy copies of the same thing.

### THE COMPARISON THAT NEARLY HID IT — a fixed test set is necessary but NOT sufficient
The first S1 arm scored **0.819 vs the optical 0.821 on the standard 543 rows: apparently no
gain.** Cause: **66 of those 543 test rows have no S1 at all** and were scored anyway with every
backscatter feature NaN. 12 % of the exam was sat with one sensor missing, and the average of
"helps a lot on 477" and "handicapped on 66" came out flat.
**This is the MIRROR IMAGE of the `REVIEWED_MODEL.md` +0.107 mirage — same root cause, opposite
sign.** There, each arm got its own cleaner test rows and invented a gain; here, a shared test
set containing rows the treatment cannot see erased a real one.
⇒ **Rule: every arm must not only share the test rows, it must be ABLE TO SEE all of them.**
Fix is not imputation — shrink to the rows all arms can answer (`keep_s1both_SENSITIVE.csv`)
and say so. Controlled arms are `output/arms/*_ctl_*.md`; their scores are comparable ONLY to
each other, not to the 543-row numbers elsewhere.

### One S1 number beats peak CFI, in every stratum
Univariate AUC in DOY 200-300: **Canola vs Cereal — VV 0.933 vs peak CFI 0.843; Legume vs
Cereal — VV 0.836 vs CFI 0.628.** VH-VV for Legume-vs-Cereal is 0.248, i.e. inverted and just
as strong. Stratifying by state and by year so only like is compared to like, **VV beats CFI in
25 of 25 strata** (5/5 states and 8/8 years on both pairs). Not regional confounding.

### S1B failure does NOT bite — hypothesis tested and refuted
Median revisit stays **6 days** in 2022-24 (multiple relative orbits cover these sites), and VV/
VH/VH-VV levels do not shift between eras. Group separation is if anything WIDER in the test
era. Coverage 95.0-97.5 % of the training universe every year, no trend into 2023-24. Only
trace: trials with <3 scenes in DOY 200-300 go 0.0 % (2017-21) -> 3.6 % (2023) -> 8.4 % (2024).
The `NEXT_STEPS.md` §6 warning was worth checking and is not a caveat on the result.

### AOI BOX BUG: centred on the trial point, sized for the paddock (2026-08-09)
`s1_download.py` builds its box as lat/lon +- half_m **around the trial point**, but the thing
measured is the **chosen paddock**, which the matcher may move up to 150 m away and which can
exceed 300 ha. **54 trials had their paddock wholly outside the raster and produced no S1 rows
at all; 28 more captured <70 % of the paddock.** A further 25 trials lost their AOI to ordinary
download failures (expired SAS tokens on a 4 h job) — 107 needing repair in total.
- **Diagnosed by `n_px_paddock` vs `paddock_ha`** (10 m pixels, so H ha = H x 100 px). That is
  the measurement separating true clipping from the 10 m erosion every paddock loses by design.
- **A strict bounding-box test overstated it ~6x.** 282 of 1,157 boxes (24 %) fail to contain a
  bounding-box CORNER, which looks alarming, but a corner poking out costs almost no area —
  measured median capture is 0.935 and only 107 trials lost anything. The `<90 % captured` group
  is 94 % small paddocks losing area to erosion. **Sizing the repair off the geometric proxy
  would have cost 4x the transfer to fix nothing — measure the quantity you care about.**
- `s1_repair.pbs` re-fetches the **63 affected AOIs** with half_m from the paddock extent
  (median 3,500 m, max 8,500 m vs the old flat 1,500 m). **Single shard by design** — every
  shard runs the whole move-aside loop, so a second shard can move away a file the first just
  downloaded; the script now refuses a shard count > 1.

### Canola does NOT need S1
Binary Canola-vs-Other on the controlled rows: optical 0.927, S1 alone 0.922, both 0.934 macro
F1. Detection @5 % FPR swings 85.6-92.1 % across arms on n=139 canola — **treat as noise around
~88 %, not a finding.** The canola map was already publishable on optical alone.

### `train_species.py` crashed on the S1-only path (fixed 2026-08-09)
With no optical block the feature-assembly line indexed an empty `parts` list (`IndexError`),
killing the job under `set -e` before two later arms ran. `--s1` alone now works.
Also: `s1_features.pbs` skips extraction when the table exists (`S1_FORCE_EXTRACT=1` rebuilds),
so a re-run to fix one arm costs the arms alone.

## S1 GAIN REVISED DOWN AFTER THE AOI REPAIR (2026-08-09 evening) — `S1_MODEL.md` §1, §2b
Repairing 63 AOIs added 68 trials (2,065 -> 2,133; test rows 477 -> 497 of 543) and changed the
answer: **optical 0.823/0.825, S1 alone 0.812/0.800, both 0.852/0.832 ⇒ +0.029 temporal,
+0.007 spatial** — where the pre-repair run said +0.044 on BOTH splits.
- **The Legume story survives**: F1 0.69 -> 0.75, precision 0.66 -> 0.73 on temporal. The
  spatial gain did not survive and must not be quoted.
- **MODEL SEED VARIANCE IS EXACTLY ZERO.** 5 seeds gave byte-identical scores —
  `HistGradientBoostingClassifier` only uses its RNG for the binning subsample and skips it
  below 10,000 rows. **So seed-averaging measures nothing on this dataset**; all uncertainty is
  in WHICH ROWS. A 3 % row change moved the gain by 0.015 temporal / 0.037 spatial.
  **Lesson: I over-read "+0.044 on both splits, agreeing to 3 decimals" as corroboration when
  it was coincidence.** Two splits over the same rows are not independent evidence.
  Narrowing this needs a bootstrap over test rows, not more seeds.

## PRESTO WITH S1 OVERTURNS THE OLD VERDICT (2026-08-09) — `presto_s1.pbs`
Feeding VV/VH into Presto leaves only ERA5+SRTM masked (8 of 9 channel groups).
**Presto alone 0.775 -> 0.813/0.808; optical+S1+Presto 0.857/0.858 vs optical+S1's
0.852/0.832 ⇒ +0.005 temporal, +0.026 spatial** — and spatial is what the hand-built S1
features FAILED to move. Presto is now within 0.010 of the 51 hand-built features on its own.
- Constraint: **Presto's encoder asserts a uniform mask across a batch**, so trials without S1
  are DROPPED, not masked. Embedding the two populations separately would satisfy the assert
  but hand the classifier a difference that tracks S1 availability rather than the crop.

## YIELD WORKS, AND CANOLA YIELD NEEDS S1 (2026-08-09) — `YIELD_MODEL.md`
Spatial GroupKFold, identical rows, R2 against a year+state baseline:
**Canola 0.290 base / 0.271 optical / 0.371 +S1 | Wheat 0.325 / 0.583 / 0.603 |
Barley 0.089 / 0.542 / 0.529.** RMSE ~26-29 % of median for all three.
- **EXACT INVERSE OF THE CLASSIFICATION RESULT.** S1 does nothing for canola ID (+0.007) and
  everything for canola yield (+0.100); nothing for cereal yield and everything for pulse ID.
  Mechanism: canola IDENTITY is flowering colour, which CFI already saturates; canola YIELD is
  biomass/structure, which is what backscatter sees. CFI amplitude alone was Spearman 0.38;
  with S1 it is 0.625.
- **The year+state baseline is NEGATIVE on temporal transfer** (-0.28 to -0.65) because 2023-24
  year-dummies are all-zero in training. That is the honest operational bar but a WEAK one —
  quote the spatial comparison, not the +1.0 temporal "gains".
- **Target is NVT trial yield, not commercial paddock yield.** Label s.e. ~0.07 t/ha; the
  uncertainty is all in trial->paddock transfer, which `CANOLA_FLOWERING_AUDIT.md` shows is not
  even reliably one-directional. Any map inherits an unquantified offset.
- **BLOCKER for a cereal yield map**: the classifier emits Cereal, not wheat-vs-barley, and
  their yields differ (3.92 vs 4.18 t/ha median).

## NATIONAL RUN IS NOT AFFORDABLE AT prob>1 (2026-08-09) — `NATIONAL_INFERENCE_BENCHMARK.md`
`nlum_tiles.py` counts segmentation tiles; a 12-tile benchmark on real NLUM tiles gives cost.
- **prob > 1 is not a filter**: canola 80,462 tiles at **20.4x more land than NLUM says is
  planted**; cereals 142,343 tiles at 4.8x. **One year costs ~10,400 SU (canola, no S1) to
  ~32,000 SU (union, with S1) — 104 % to 320 % of the 10 KSU allocation.** At prob>2500 canola
  is 24,941 tiles / ~3,200 SU, which fits.
- **SAM IS NOT THE BOTTLENECK — pre-segment is, by ~2x.** SAM is **3 s/tile** on a V100
  (0.030 SU/tile batched); the datacube read + Fourier composite is 0.059 SU/tile and is
  I/O-bound. **Pre-segment cost TRIPLED vs the 2026-08-07 benchmark** (0.020 -> 0.059): 2x because I
  requested 8 GB not 4 GB, rest from 70-146 scenes/tile. **The 8 GB was my mistake, not a
  requirement** — see below.
- **S1 does not scale**: 72 s/tile => 2,923 h serial for 146k tiles, ~12 days at 10 concurrent
  copyq jobs. dz56 becomes a precondition, not a convenience, for any national S1 product.
- **THE REAL BLOCKER IS NOT COMPUTE — there is no "not a crop" class.** Grazing is **287.9 Mha,
  87.2 %** of NLUM agricultural land; the 3 target groups are 35.8 Mha (10.8 %). The model has
  only ever seen NVT trial paddocks and a 3-way softmax cannot say "none of these", so it will
  label pasture as Cereal at an unbounded rate. Segmentation already shows it: sampled tiles
  produced polygons of 981 ha and 196 ha median against the trial set's 57 ha — rangeland with
  no field boundaries. Fix before scaling: add a 4th class from strongly-grazing NLUM cells,
  with NLUM-prior rejection as the reported fallback.

## DO NOT SIZE PBS MEMORY OFF THE LOG (2026-08-09, user correction)
gadi's resource footer reported "Memory Used: 8.0GB" of 8 GB requested and I concluded the job
had hit its ceiling and recommended 12-16 GB nationally. **The user says that figure routinely
reads at the request without the job needing it.** Raise memory ONLY on a real out-of-memory
error (explicit OOM, or exit 137 / silent kill). Since `normal` charges
`max(ncpus, mem/4GB) x 2 SU/hr`, sizing off that log line doubles the bill for identical work —
worst exactly where it is hardest to spot, in a 100,000-tile run. Default stays 1 CPU / 4 GB.
