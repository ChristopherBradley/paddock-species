# Stage 2 — Sentinel-2 phenology confirmation (run on NCI gadi)

Confirms that the paddock around each **clean** NVT trial (Stage 1) actually grew the
trial crop, by extracting a Sentinel-2 **NDVI** (growth) and **NDYI** (canola-flowering
yellowness) time series from the DEA datacube over each trial's sow→harvest window.

Scope selected for this project: **Canola + Wheat** clean trials (~1,630).

## Canonical gadi paths
| what | path |
|---|---|
| code | `/home/147/cb8590/Projects/paddock-species/src/sentinel_ndvi` |
| **raw** inputs (persistent) | `/g/data/xe2/cb8590/paddock-species-data/raw` |
| **derived** / intermediates | `/scratch/xe2/cb8590/paddock-species-data/derived` |
| Stage-1 labels (sensitive) | `…/scratch/…/derived/nvt_trials_labeled.csv` |
| job chunks | `…/derived/chunks/chunk_###.csv` |
| extracted time series | `…/derived/sentinel_ts/chunk_###_ts.csv` |
| PBS job logs | `/scratch/xe2/cb8590/paddock-species-logs/` |

> **⚠ `/scratch` is purged.** NCI deletes scratch files that go untouched for ~100 days, and
> it is not backed up. Everything under `derived/` is *regenerable* (chunks and time series
> from `raw/` via this pipeline, labels via `src/explore_nvt_sites.py`), which is why it can
> live here — but pull anything you care about back to local with
> `./sync/sync_to_gadi.sh pull` rather than treating scratch as storage. `raw/` deliberately
> stays on `/g/data`, which is not purged.

## Environment
```bash
module use /g/data/v10/public/modules/modulefiles
module load dea/20231204          # datacube 1.8.16, products ga_s2am/bm/cm_ard_3
```

## Run order
```bash
cd /home/147/cb8590/Projects/paddock-species/src/sentinel_ndvi

# 1. Build per-job chunks (clean Canola+Wheat only)
python3 make_chunks.py \
    --labeled /scratch/xe2/cb8590/paddock-species-data/derived/nvt_trials_labeled.csv \
    --outdir  /scratch/xe2/cb8590/paddock-species-data/derived \
    --per-chunk 100 --crops Canola Wheat

# 2. SMOKE TEST a handful of trials interactively (seconds, safe on a login node).
#    Do NOT run a full 100-trial chunk on the login node — it is ~1 h of heavy /g/data/ka08 I/O.
head -4 /scratch/xe2/cb8590/paddock-species-data/derived/chunks/chunk_000.csv > /tmp/chunk_smoke.csv
python3 extract_ndvi.py --chunk /tmp/chunk_smoke.csv --outdir /tmp/smoke_ts
python3 phenology_check.py --ts-dir /tmp/smoke_ts --out /tmp/smoke_confirmed.csv

# 3. BENCHMARK one real chunk as a PBS job, then check what it actually used
qsub -v CHUNK=/scratch/xe2/cb8590/paddock-species-data/derived/chunks/chunk_000.csv extract_ndvi.pbs
qstat -fx <jobid> | grep -Ei 'Exit_status|resources_used'

# 4. Submit the remaining chunks (one PBS job each; skips any chunk already extracted)
./extract_ndvi.sh

# 5a. Evaluate CFI and locate the flowering window (the discriminator that is actually used)
python3 cfi_report.py \
    --ts-dir /scratch/xe2/cb8590/paddock-species-data/derived/sentinel_ts \
    --out    /scratch/xe2/cb8590/paddock-species-data/derived/cfi_report.md

# 5b. Threshold distributions / NDVI-amplitude rejection rate (kept for the NDVI gate and
#     as the record of why NDYI was abandoned). Neither script auto-applies anything.
python3 threshold_report.py \
    --ts-dir /scratch/xe2/cb8590/paddock-species-data/derived/sentinel_ts \
    --out    /scratch/xe2/cb8590/paddock-species-data/derived/threshold_report.md

# 5c. Optional visual check — CFI/NDVI season traces, canola vs wheat (SENSITIVE output,
#     anonymised labels, stays on /scratch)
python3 plot_timeseries.py \
    --ts-dir /scratch/xe2/cb8590/paddock-species-data/derived/sentinel_ts \
    --outdir /scratch/xe2/cb8590/paddock-species-data/derived/figures --n-per-crop 10

# 6. Derive verdicts (thresholds are flags: --cfi-flower-min/--flower-start/--flower-end)
python3 phenology_check.py \
    --ts-dir /scratch/xe2/cb8590/paddock-species-data/derived/sentinel_ts \
    --out    /scratch/xe2/cb8590/paddock-species-data/derived/nvt_confirmed.csv
```

## Method notes
- **Window:** 200 m square (~20×20 @ 10 m) centred on the trial GPS *corner*; the paddock
  extends in an unknown direction, so we take the window mean/std **and** the corner pixel.
- **Cloud masking:** `oa_fmask == 1` (clear). `extract_ndvi.py` drops only fully-cloudy dates
  and records `n_clear_px` / `n_px_total`; `phenology_check.py` then drops scenes below
  `--min-clear-frac` (default 0.5). This two-step split keeps the raw extraction reusable
  while removing a **one-directional bias**: sparse-clear scenes (swath edge / cloud halo)
  sit systematically low in *both* indices, so leaving them in depresses the p5/p20
  baselines and inflates both `ndvi_amp` and `ndyi_peak` — pushing trials toward CONFIRMED
  and wheat toward UNCERTAIN. Seen in the smoke test: 44/462 clear px reporting NDVI 0.28
  between neighbours of 0.34 and 0.56.
- **Indices:** `NDVI = (NIR−Red)/(NIR+Red)`; `NDYI = (Green−Blue)/(Green+Blue)` (Sulik & Long
  2016); and the one that actually does the work —
  **`CFI = NDVI × ((Red + Green) + (Green − Blue))`** (Canola Flower Index, Tian et al. 2022
  *Remote Sensing*; same form as PaddockTS `Code/indices_etc/indices.py`).
  Raw band means (`red/green/blue/nir_win_mean`, 0-1 reflectance) are stored too, so a future
  index can be derived without touching the datacube again.

  **Why CFI replaced NDYI as the discriminator.** NDYI is pure visible-band yellowness, so
  bare and senescing soil scores high. Measured across all 1,630 trials, NDYI was close to
  useless for this job: at the shipped `0.12` it flagged 95.8 % of Canola *and* 78.4 % of
  Wheat (Youden J = 0.17), and its best achievable J was only 0.458. CFI's `NDVI ×` factor
  suppresses soil — the signal survives only where there is both green biomass and
  yellowness, i.e. an actual flowering canopy.

  **CFI must be maximised over the flowering window, not the season.** CFI rises a second
  time during senescence, when the canopy yellows while NDVI is still moderate. On a worked
  canola example the seasonal max landed in mid-October (ripening, CFI 0.217) rather than at
  flowering — so an unrestricted max measures the wrong event. `extract_ndvi.py` therefore
  carries `sow` through, and `cfi_report.py` scans window placements in days-after-sowing
  rather than assuming one.

  CFI is computed on 0-1 reflectance; multiply by `REFL_SCALE` (10000) to compare with
  PaddockTS values computed on raw DN. Being linear in reflectance, CFI is scale-dependent
  (unlike NDVI/NDYI) — separability is unaffected, but absolute thresholds are not portable.
- **Verdict rule** (`phenology_check.py`, all settable via CLI flags):
  `NDVI_AMP_MIN=0.35` (crop-presence gate) and **max CFI within 120-190 days after sowing
  >= 0.1309**. Canola needs a flowering peak to be CONFIRMED; a flowering peak on a *wheat*
  site is UNCERTAIN. A trial with no clear observation inside the flowering window is
  UNCERTAIN, never CONFIRMED — "could not be assessed" must stay distinct from "assessed and
  found nothing".
- **Where that operating point came from** (`cfi_report.py`, run on all 1,630 trials):
  a grid scan over window start x width, then a temporal held-out check. **Held-out
  J = 0.535**; the in-sample figure is 0.604, so quote the held-out one. Two traps worth
  remembering: the first scan's optimum sat on the *edge* of the scanned grid (meaningless
  until widened past the peak — the script now flags this automatically), and window and
  threshold were both tuned on the same data until the held-out split was added.
- Caveat on every separability number here: it is scored against the *claimed* NVT crop
  label, and Stage 2 exists precisely because the surrounding paddock may not match it. So
  these measure signal strength, not accuracy — a perfect score would be suspicious rather
  than reassuring.
- **Result:** CONFIRMED 1,229 (75.4 %) | UNCERTAIN 284 (17.4 %) | REJECTED 117 (7.2 %);
  Canola 756/103/41, Wheat 473/181/76.

## ⚠ `PROJ_NETWORK=OFF` is mandatory — read before submitting
**`module load dea/20231204` exports `PROJ_NETWORK=ON`.** PROJ then tries to download datum
grids from `cdn.proj.org` (AWS CloudFront, `108.158.20.x`). **Gadi compute nodes have no
outbound internet**, so the attempt neither connects nor fails — it retries forever at ~0 %
CPU until walltime kills the job. `extract_ndvi.pbs` exports `PROJ_NETWORK=OFF` *after* the
module load (order matters), and `extract_ndvi.py` sets it defensively too.

Whether a given trial hangs depends on its **location** — some sites need a grid, others
resolve from built-in parameters. So the failure looks random and load-dependent when it is
neither, which is exactly what made it easy to misdiagnose.

**Incident 2026-08-06/07.** Two runs lost to this (~136 SU on the first, plus a second
stalled attempt) and it was twice misdiagnosed as DEA index connection-pool exhaustion.
Wrong both times. The sequence that actually settled it is worth repeating:
1. `resources_used.cput` ≈ 4-8 s against 21 min walltime ⇒ blocked, not slow.
2. The index answered a login-node `dc.list_products()` in 0.1 s **while jobs were stuck**
   ⇒ not the database.
3. `dc.find_datasets(...)` returned **only `file:///g/data/ka08/...` URIs** ⇒ not S3.
4. `strace -p <pid>` on the compute node: `connect(..., 443) = ENETUNREACH` retrying against
   `108.158.20.x`, which is what `cdn.proj.org` resolves to. Root cause.

Accuracy cost of disabling it is negligible here: WGS84→GDA94 falls back to a built-in
transform (~1.8 m, plate motion since 1994) — under one 10 m pixel, on a 200 m window that
gets averaged anyway.

**Concurrency was a red herring.** The index was never stressed and a single job fails
identically. `--lanes` is kept as a throttle but is not needed for this fault; the author
routinely runs ~200 concurrent jobs against the same index without trouble.

### Why there are two watchdogs
`SIGALRM` alone is **not** sufficient. Python runs signal handlers only when the interpreter
regains control, and curl/libpq/GDAL restart their poll loops on `EINTR`, so a hang inside
native code swallows the alarm. Observed directly here: `SigCgt` showed SIGALRM armed,
`SigPnd` was 0, and the job still sat blocked for hours. `extract_ndvi.py` therefore also
runs a **watchdog thread** (`--stall-timeout`, default 900 s) that force-exits the process —
the GIL is released during blocking I/O, so it still runs while the main thread is stuck.
Per-trial results are flushed as they go, so a force-exit loses nothing.

Other defences, all verified: a 60 s index pre-flight probe exiting 75; per-trial
`--trial-timeout` recording `FAILED`/`TIMEOUT` (useful for Python-level hangs);
`--max-consecutive-timeouts` aborting the job; and `FAILED` trials **retried on resume**, so
a transient fault cannot silently become permanent missing data.

## Compute / SU
Small-job design (1 CPU, **4 GB**, 4 h walltime per 100-trial chunk) following the CLAUDE.md
SU-minimisation note. Benchmarked 2026-08-06: peak RSS **240 MB**, ~33 s/trial, 25 % CPU
(I/O-bound on `/g/data`). Each trial loads only a ~20×20 px window, so memory is flat in both
chunk size and year — the original 16 GB request would have billed 4 CPU-equivalents on the
`normal` queue for headroom nothing uses. Walltime stays at 4 h (unused walltime is free) since
later years have denser S2 revisit than the 2017-2020 benchmark chunk.

Scope: 1,630 trials → **17 chunks**. Never fabricate a result: failed trials are logged
`FAILED` in `chunk_###_status.csv`; re-benchmark via `qstat -fx <jobid>` if the workload changes.

## Verify products (optional)
```bash
python3 -c "import datacube; dc=datacube.Datacube(); print([p for p in dc.list_products().name if 's2' in p])"
```
