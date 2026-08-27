# Project Dashboard — paddock-species

NORA (Night Owl Research Agent) project dashboard. Skills read this file for control flags, environment config, and canonical output paths.

## Control Flags

```yaml
AUTO_PROCEED: true
HUMAN_CHECKPOINT: true
COMPACT_MODE: false
EXTERNAL_REVIEW: false
REVIEWER_DIFFICULTY: medium
ARXIV_DOWNLOAD: true
```

## Key Files

- `BRIEF.md` — 12-section research brief (authoritative; see precedence rule below). Written by `/launcher`.
- `RESEARCH_PLAN.md` — if present, outranks `BRIEF.md`. Not yet created for this project.
- **Brief precedence**: `RESEARCH_PLAN.md` > `BRIEF.md` > `$ARGUMENTS`.
- `handoff.json` — session recovery state (stage, next step, resume skill). Not yet created.
- `memory/MEMORY.md` — pipeline stage flags and prior token usage, updated after each stage.
- `Papers/` — local PDFs the user has already read during their PhD; `/lit-review` should check this folder alongside arXiv/Semantic Scholar. Local-only (gitignored, not synced to gadi).
- `data/raw/NLUM_v7_250_AgProbabilitySurfaces_2020_21_geo_package_20241128/` — Australia NLUM 250m crop species probability surfaces (per-commodity GeoTIFFs).
- `data/raw/2017-2024 NVT Yield and Grain Quality - cbradley - 01.05.2025.xlsx` — GRDC/NVT yield/grain-quality data (NDA-sensitive).
- `data/derived/` — sensitive derived tables/figures (e.g. `nvt_trials_labeled.csv`); gitignored.
- `src/explore_nvt_sites.py` — Stage-1 site-cleanliness labeller (local, pandas-only). See `output/DATA_EXPLORATION_REPORT.md`.
- `src/sentinel_ndvi/` — Stage-2 Sentinel-2 NDVI/NDYI phenology confirmation for gadi/DEA (PBS scripts + README).
- `sync/sync_to_gadi.sh` — re-runnable local⇄gadi sync; see `sync/README.md`.

## Repo layout / gadi split (home vs /g/data)

The repo is structured so transfers are mechanical (see `sync/README.md`):
- **Code/docs** (repo root minus `data/`, `Papers/`, `extra papers/`) → gadi `/home/147/cb8590/Projects/paddock-species`.
- **`data/raw/`** (sensitive, irreplaceable) → gadi `/g/data/xe2/cb8590/paddock-species-data/raw`. Never on `/home` or in git.
- **`data/derived/`** (sensitive, regenerable) → gadi `/scratch/xe2/cb8590/paddock-species-data/derived`. NCI purges scratch after ~100 days — pull anything worth keeping.
- **`~/.claude/skills`** → gadi `~/.claude/skills`.
- PBS job logs → `/scratch/xe2/cb8590/paddock-species-logs/`.
- gadi env confirmed: DEA `module load dea/20231204` (datacube 1.8.16); S2 ARD products `ga_s2am_ard_3`/`ga_s2bm_ard_3`/`ga_s2cm_ard_3`; projects `xe2` (primary), `v10`, `ka08`.

## Sensitive Data — Do Not Commit

The GRDC trial site dataset (lat/lon, crop type, planting/harvest dates, yield) is covered by a signed NDA. **Never commit this data, or any derived file that exposes site-level records, to git.** Add any new sensitive data paths to `.gitignore` before they are written to disk.

## Committing

Committing on the user's behalf is fine. **The hard constraint is that no commit may contain
GRDC/NVT sensitive data** (TrialCodes, site coordinates, yields, or any site-level record) —
see the Sensitive Data section above. Before every commit, check what is being staged: any
file matching `**/*SENSITIVE*` is gitignored and must stay that way, and no tracked file may
contain a TrialCode. Do not `git push` without the user asking.

## Local Environment

- gpu: none (Intel Iris Plus integrated graphics only — no CUDA/MPS). All ML/DL training must route to remote compute.
- OS: macOS (Darwin), Intel x86_64.

## Remote Environment — NCI Gadi

- gpu: remote
- Access: NCI gadi, projects `v10` and `ka08` (direct access to the DEA — Digital Earth Australia — datacube).
- Scheduling: PBS job queue (not a persistent SSH session) — deploy via qsub-style PBS scripts, not `ssh <server> <command>`.
- Allocation: user's group has ~200 KSU/quarter; up to 50 KSU earmarked for this project. Always benchmark job configurations (memory/CPU/walltime) before scaling up — see SU-minimization note below.
- Alternative launch path: user can relaunch a session directly on gadi via VSCode remote instead of SSH-ing from local.
- Reference PBS scripts (from a related prior project, same user): https://github.com/ChristopherBradley/shelterbelts/blob/main/pbs_scripts — `sentinel.sh`/`sentinel.pbs` (Sentinel download via DEA datacube), `predictions.sh`/`predictions.pbs` (run predictions). Build an analogous PBS setup for crop-type prediction in this project.
- SU-minimization note: prior experience found many small jobs (4GB RAM, 1 CPU, 10+ hour walltime, using `os.Popen`/subprocess to avoid memory accumulation) used fewer SUs than fewer large-memory/large-CPU jobs. Treat as a starting hypothesis to re-benchmark for this workload, not a fixed rule.
- code_sync: rsync (default until confirmed otherwise)
- wandb: not yet configured

## Other Compute Access

- Google Earth Engine: free researcher-tier service account, small monthly compute allocation (exact amount unconfirmed — ask the user to check if it becomes a constraint).
- Claude Code usage: user is on the $34/month subscription, ~10 five-hour quota windows per week, no additional token purchase available. Be economical with agent fan-out (parallel/background subagents) and expensive pipeline stages (e.g. `REVIEWER_DIFFICULTY: nightmare`, large multi-round loops) — flag the cost tradeoff before running something heavy.

## Spatial Environment

- conda env: not yet created (candidate packages: geopandas, rasterio, xarray, odc-stac / datacube for DEA access)
- CRS default: not yet decided — likely a suitable Australian projected CRS (e.g. GDA2020 / MGA zone appropriate to region, or EPSG:3577 Australian Albers for national-scale work)

## Generator-Evaluator Separation

Never let the entity that wrote a section (idea, proposal, code, manuscript text) also score or approve it. `/auto-review-loop` and `/paper-review-loop` enforce this structurally — do not bypass it by having the same pass act as both author and reviewer.

## Prohibited Behaviors

- Never fabricate results, metrics, numbers, or citations. If a run fails, record it as FAILED — do not invent a plausible result.
- Never silently relax experiment pass/fail criteria, review thresholds, or acceptance criteria to force a positive outcome. If genuinely stuck, write `output/CONTRACT_VIOLATION.md` and surface it to the user instead.
- Never commit to git without the user's explicit in-the-moment request (see above).
- Never commit or expose the GRDC trial site data (see Sensitive Data section above).

## Session Start Checklist

1. Read this file (`CLAUDE.md`) for control flags and environment config.
2. Read `handoff.json` if present, for pipeline stage and resume instructions.
3. Read `memory/MEMORY.md` for prior pipeline state.
4. Read `BRIEF.md` (or `RESEARCH_PLAN.md` if it exists) for the authoritative research brief.

## Where reports go

Write markdown reports into **`output/` in this repo** (not `/scratch`) — the user has VSCode
open here and reads them directly. Anything containing TrialCodes, coordinates or other
site-level records must be named `*_SENSITIVE.md` / `*_SENSITIVE.csv`, which `.gitignore`
catches via the `**/*SENSITIVE*` rule, so it is readable in the editor but can never be
committed. Aggregate-only reports (no site-level records) can use a plain name and be
committed normally.
