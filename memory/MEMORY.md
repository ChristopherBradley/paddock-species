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
- [ ] `/novelty-check`
- [ ] `/idea-review`
- [ ] `/experiment-design-pipeline`
- [ ] `/deploy-experiment`
- [ ] `/auto-review-loop`
- [ ] `/generate-report`
- [ ] paper-writing-pipeline stages

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
