# Experiment Tracker — fj7 Sentinel-1 / full-layer Presto

Companion to `EXPERIMENT_PLAN.md`. Run IDs match that plan's milestones/blocks.

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|--------|-----------|---------|-------------------|-------|---------|----------|--------|-------|
| R000a | M0 | Request fj7 filelists read access | — | — | access granted y/n | MUST | TODO | ask owner `mp2758` or NCI helpdesk |
| R000b | M0 | Check THREDDS catalogue for fj7 as AOI+date index | — | — | usable index y/n | MUST | TODO | public, no account needed — check before waiting on R000a |
| R000c | M0 | Install/module-check pyroSAR + SNAP (or GAMMA) | — | — | toolchain runs y/n | MUST | TODO | `module avail` found nothing this session |
| R000d | M0 | Process 1 known GRDH scene to RTC as a smoke test | pyroSAR/SNAP | 1 scene | sane dB output y/n | MUST | TODO | use scene found this session under `Sentinel-1/00/24/...` |
| R001 | M1 | fj7 RTC processing cost, 10 scenes | fj7 filesystem read + RTC | 10 scenes, `normal` | SU/scene | MUST | TODO | hard cap 100 SU; gated on R000 |
| R002 | M2 | shipped+sharma6 baseline, S1-availability-restricted rows | HGB, shipped+sharma6 | `keep_s1both`, temporal + spatial | macro F1, per-class F1, canola@5%FPR | MUST | **DONE** | 0.887/0.886 macroF1, canola@5%FPR 84.0%. `GROUP3_ctl_shipped_sharma6_only.md` |
| R003 | M2 | shipped+sharma6 + S1 | HGB, shipped+sharma6+S1 | `keep_s1both`, temporal + spatial | macro F1, per-class F1, canola@5%FPR | MUST | **DONE** | 0.864/0.868 macroF1 — **REGRESSION**, −0.023/−0.018, concentrated on Legume F1 (0.82→0.77). C1 REFUTED. `GROUP3_ctl_shipped_sharma6_s1.md`, writeup `S1_VS_LATEST_MODEL.md` |
| R002y | M2 | cereal_yield.joblib baseline (pooled Wheat+Barley+Oat), S1-restricted rows | HGB regressor, indices only | `keep_s1both`, temporal + spatial | R2, RMSE | MUST | **DONE** | temporal R2 0.419 (sat+year/state), spatial 0.569. `YIELD_cereal_pooled_ctl.md` — added mid-session, not in original plan |
| R003y | M2 | cereal_yield.joblib + S1 | HGB regressor, indices+S1 | `keep_s1both`, temporal + spatial | R2, RMSE | MUST | **DONE** | temporal R2 **0.511 (+0.092)**, spatial 0.591 (+0.022) — **clear gain**, opposite direction from the classifier. `YIELD_cereal_pooled_s1.md` |
| R004 | M3 | ERA5 monthly temp/precip per trial | GEE `ECMWF/ERA5_LAND/MONTHLY_AGGR` | 2,320 trials | coverage % | MUST | TODO | check GEE quota with user first |
| R005 | M3 | SRTM elevation/slope per trial | GEE `USGS/SRTMGL1_003` | 2,320 trials | coverage % | MUST | TODO | negligible volume |
| R006 | M3 | Presto(S1+ERA5+SRTM) alone, 0/9 masked | Presto, full article | `keep_s1both`, temporal + spatial | macro F1 | MUST | TODO | compare to 0.813/0.808 (7/9 masked) |
| R007 | M3 | shipped+sharma6+S1 + Presto(full) | HGB + Presto embedding | `keep_s1both`, temporal + spatial | macro F1 | MUST | TODO | compare to R003 and to 0.857/0.858 (7/9 masked stacked) |
| R008 | M4 | shipped+sharma6+S1 + plain ERA5/SRTM columns | HGB, 4 extra features | `keep_s1both`, temporal + spatial | macro F1 | NICE | TODO | frontier-necessity check vs R007 |
| R009 | M5 | S1 on AgriWebb ordinary-geometry holdout | HGB, shipped+sharma6+S1 | 104 AgriWebb sites | macro F1 | ~~COND. MUST~~ DROPPED | **CUT** | R003 refuted C1 for the classifier — no accuracy case left to validate on ordinary geometry. Superseded by R009y below. |
| R009y | M5 | S1-for-yield on ordinary-geometry ground truth | HGB regressor, indices+S1 | TBD — no yield-labelled AgriWebb-equivalent set identified yet | R2 | COND. MUST | BLOCKED | new row, follows from R003y's positive result; blocked on finding a non-NVT-trial yield ground truth to test against (see `S1_VS_LATEST_MODEL.md` §4) |
| R010 | M5 | Revisit-density covariate for S1B discontinuity | new feature | 2017-2025 | — | MUST (before any multi-year S1 claim) | TODO | not implemented anywhere yet — confirmed by grep; now specifically gates the yield claim, not the classifier claim |
| R011 | M5 | National multi-year S1 extraction via fj7 | fj7 RTC pipeline | national | SU, coverage | COND. MUST | BLOCKED | gated on R001's actual cost number; success criterion is now the yield gain (+0.09 R2 class), not classifier macro F1 |
