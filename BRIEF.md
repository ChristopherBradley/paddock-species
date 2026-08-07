# Research Brief

## 1. Topic
Map cropland/paddock crop species across Australia using Sentinel-2 (and possibly Sentinel-1, if the literature supports it) imagery, using GRDC trial-site records as ground-truth labels. Canola is the likely starting species via the Canola Flower Index (obvious signal in heatmaps by timing/intensity), as referenced in the PaddockTS `indices.py` script.

## 2. Domain Focus
Remote Sensing

## 3. Reference Paper
None single paper to build on. Working references: WorldCereal's methodology (candidate to adapt/retrain on local Australian data) and the PaddockTS `indices.py` script: https://github.com/johnburley3000/PaddockTS/blob/main/Code/indices_etc/indices.py

## 4. Target Venue
Remote Sensing of Environment (RSE)

## 5. Geographic Scope
All of Australia (wherever GRDC trial sites are located nationally)

## 6. Datasets
- GRDC trial site dataset: lat/lon, crop type, planting/harvest dates, yield. **Sensitive, NDA-covered — never commit this data or derived files that expose it.** Surrounding paddocks generally share the trial's species, but some trial sites have multiple species close together, so trial location cannot always be taken as a clean paddock-wide label.
- Sentinel-2 imagery (primary); Sentinel-1 as an optional addition if literature supports the benefit.
- Australia NLUM 250m crop species data — already placed in repo root (`NLUM_v7_250_AgProbabilitySurfaces_2020_21_geo_package_20241128/`); current best comparable dataset, but a literature search for better alternatives is planned.
- WorldCereal — comparison dataset, and its methodology is a candidate to adapt/retrain on local Australian data.
- Fields of the World — candidate source for paddock boundaries.
- CSIRO ePaddocks — another paddock-boundary dataset (boundaries only, no yearly crop type inside them, similar limitation to Fields of the World).
- DEA (Digital Earth Australia) datacube, accessed directly via NCI gadi.

## 7. Compute Constraints
- Local machine: no GPU (Intel Iris Plus integrated graphics only) — all ML/DL training must route to remote compute.
- NCI gadi: v10 and ka08 projects, giving direct access to the DEA datacube. User's group has ~200 KSU/quarter allocation; up to 10 KSU earmarked for this project. Job execution is PBS-based (not a persistent SSH session).
- SU-minimization preference: always benchmark job configurations before running at scale. Prior experience (from a related project) found many small jobs (4GB RAM, 1 CPU, 10+ hour runtime, using `os.Popen`/subprocess to avoid memory accumulation) used fewer SUs than fewer large-memory/large-CPU jobs — treat this as a hypothesis to re-benchmark for this workload, not a fixed rule.
- Reference PBS scripts from a related prior project (tree/shelterbelt prediction): https://github.com/ChristopherBradley/shelterbelts/blob/main/pbs_scripts — `sentinel.sh`/`sentinel.pbs` (download Sentinel data via DEA datacube), `predictions.sh`/`predictions.pbs` (run predictions). Want an analogous setup for crop-type prediction.
- Google Earth Engine service account: free researcher tier, small monthly compute allocation (exact amount unconfirmed).
- User's Claude Code usage is on the $34/month subscription (~10 five-hour quota windows per week, no extra token purchase) — be economical with agent fan-out and expensive pipeline stages (e.g. "nightmare" reviewer difficulty, large parallel subagent runs); prefer targeted, sequential work.

## 8. Timeline
Exploratory — no fixed deadline (PhD side project).

## 9. Research Type
Improvement on an existing method: adapt/retrain a WorldCereal-style crop-classification methodology on local Australian GRDC-labeled data, rather than building a wholly new architecture from scratch.

## 10. Prior Work
- GRDC trial site dataset already available (sensitive, NDA-covered — see Section 6).
- Australia NLUM 250m crop data already placed in the repo root.
- PaddockTS demo scripts for Sentinel index computation and NCI/DEA datacube access.
- `shelterbelts` repo PBS scripts (Sentinel download + prediction jobs) from a related prior tree-shelterbelt project — to adapt for crop-type prediction.
- Canola Flower Index observation: canola shows an obvious, well-timed signal in Sentinel heatmaps, making it the likely easiest starting species.
- Local `Papers/` folder in this repo already contains PDFs the user has read during their PhD (currently: Allen 1998 FAO Irrigation and Drainage Paper No. 56; Farming for the Future 2024 Natural Capital Methods Paper) — available for `/lit-review` to check alongside arXiv/Semantic Scholar.

## 11. Non-Goals
None explicitly excluded. Implicit boundary: this project stops at crop-species/type mapping — it does not extend into the downstream analysis of tree-shelter effects on productivity, which is a separate, later project that depends on this one's output.

## 12. Seed Papers
- WorldCereal (methodology and dataset reference)
- PaddockTS `indices.py`: https://github.com/johnburley3000/PaddockTS/blob/main/Code/indices_etc/indices.py
- Local `Papers/` folder: Allen 1998, FAO Irrigation and Drainage Paper No. 56; Farming for the Future 2024, Natural Capital Methods Paper
