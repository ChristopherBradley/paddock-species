# Pre-push audit: is any GRDC/NVT data in the repo or its history?

**Verdict: clean.** Nothing NDA-covered is tracked now, and nothing NDA-covered has ever been
committed. Run 2026-09-11 against `master` at `facda9b`, over all 68 commits and all 936 distinct
blobs in history (not just the current checkout).

This report is aggregate only. It deliberately names no trial code and quotes no coordinate that
came from the trial data.

## What was searched for, and how

The trial data's identifying fields are the TrialCode, the site coordinate, the sown/harvest dates
and the single-site yield. A leak of any of those at site level is the thing the NDA forbids.

| Check | Method | Result |
|---|---|---|
| Exact trial codes | All 2,761 distinct codes from `review_sites_SENSITIVE.csv` as fixed strings, against every blob in history | **0 hits** |
| Trial-code-shaped strings | Regex `[A-Z][A-Za-z]{2,4}[0-9]{2}[A-Z]{3,5}[0-9]`, which is the crop-prefix, two-digit-year, site, replicate shape the codes take, against every blob in history | **0 hits** |
| Paired Australian coordinates | Any line carrying both a latitude `-[1-4]x.xxx+` and a longitude `1[1-5]x.xxx+`, against every blob in history | 7 blobs, all cleared — see below |
| Coordinate column headers | `latitude`/`longitude`/`lat`/`lon`/`x_coord`/`y_coord`/`POINT(` as a CSV header or WKT, against every blob in history | 70 blobs, all `lat`/`lon` as variable or argument names in source files, no data |
| Sensitive file paths | `*SENSITIVE*`, `*.xlsx`, `data/`, `nvt_trials_labeled`, `*_ts.csv`, `chunk_*` ever added in any commit | **0** (one match was the script `chunk_sites.py`, not data) |
| Credentials | password/secret/api-key/Snowflake account/private-key patterns, against every blob in history | **0 hits** |
| Tracked binaries | Every tracked `.png`/`.csv`/`.gpkg`/`.geojson` reviewed for site-level content | none carry sites — see below |

## The coordinate hits, and why each is not trial data

Seven historical blobs contain real Australian coordinate pairs. All seven are model output or a
public sampling frame, not NVT sites:

- `overlap_test.pbs`, `overlap_test2.pbs`, `find_boundary_pairs.py`,
  `PIPELINE_ARCHITECTURE_AND_TILING.md` — Riverina locations of **predicted polygon pairs** that
  the tile-boundary diagnostic found by searching the map. They are positions in a map that is
  itself being published, not trial sites. (The three scripts were already deleted in the
  2026-09-10 pass; they survive only in history.)
- `WALL_TO_WALL_MAPS.md` — the three demonstration-region centres (`wa_0`, `sa_1`, `nsw_2`).
  Traced to `map_regions.py`, which picks regions from the **NLUM probability surfaces**, a public
  ABARES product, and deliberately forces them apart by state. No trial input.

## Figures

`Fig02_study_area.png` is the only tracked figure that plots points. Its scatter is
`national2024/aois.csv`, the NLUM-derived national tile grid, not trial locations.
`Fig08_yield_summary.py` states in its own header that it plots no per-trial scatter "even
anonymised, because each point would be a single NVT trial's yield record". The two `nvt_*.png`
figures are distributions by crop and by distance, with no site identity.

## Why it has stayed clean

`.gitignore` blocks the data at several independent levels: `data/`, the NVT workbook by name,
`**/*SENSITIVE*` as a catch-all, the per-trial time-series and chunk patterns, and
`output/figures/*_map_*.png`. The scripts that write site-level files write them to `/scratch` or
`/g/data` and name them `*_SENSITIVE*`, so the catch-all applies even if one is ever pulled into
the repo by mistake.

## What to keep doing

The one rule that carries all the weight: any new file holding a trial code, a site coordinate or
a per-site yield must be named `*SENSITIVE*` **before** it is written to disk, and must live under
`/scratch` or `/g/data` rather than the repo. Reports that summarise those files are safe to
commit as long as every row is an aggregate.

Two files in `output/` are correctly ignored and should stay that way:
`review_sites_SENSITIVE.csv` and `SAM_SWEEP_detail_SENSITIVE.csv`. They are readable in the
editor and cannot be committed.
