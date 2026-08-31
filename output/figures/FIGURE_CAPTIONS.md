# Figure Captions — paddock-species

Manuscript-ready, self-contained captions. Numbers are copied from the source files named in
`FIGURE_MANIFEST.md`; none are invented. CRS given for every map (project default: GDA94 /
Australian Albers, EPSG:3577).

**Figure 1.** Pipeline overview and example output. Sentinel-2 time series drive both
SAM-based paddock segmentation and a 3-class spectral-index classifier; a presence gate
determines whether a segmented paddock is classified at all, and a calibrated model attributes
Cereal yield to classified paddocks. (a) Six-stage pipeline schematic. (b) Real classified
output over a 12km x 12km window in the Riverina, NSW (EPSG:3577), 2024 layer of the
nine-year regional consensus product (`map100/consensus_crops.gpkg`); 361 polygons — 219
Cereal, 48 Canola, 12 Legume, 82 unclassified (abstained), shown in grey rather than left
blank.

**Figure 2.** Study area. National extent of 2024 mapped tiles (grey; `national2024/aois.csv`,
99,465 tile centres), the 100km x 100km Riverina, NSW block used for the nine-year (2017-2025)
regional test (red outline), and the SA2s used for ABS composition validation (coloured by
state; EPSG:3577). 133 SA2s shown — the >=50%-covered subset re-derived from
`ABS_COMPARISON_NATIONAL.md`'s own published per-SA2 cover table; see
`FIGURE_MANIFEST.md` for a one-off-from-132 rounding note.

**Figure 3.** Classifier confusion matrices, "reviewed" arm, n=543 fixed test paddocks for
both splits (`GROUP3_reviewed.md`). (a) Temporal transfer (train <=2022, test 2023-24):
macro F1 0.821. (b) Spatial transfer (5-fold GroupKFold on site): macro F1 0.823. Legume is
the floor in both splits (recall 73% temporal, 70% spatial), driven by Cereal leaking into
Legume (23/109 and 24/109 true Legume paddocks predicted Cereal) rather than the reverse.

**Figure 4.** The national 2024 crop-species map. 1,346,582 segmented paddock polygons
(`national2024/national_2024_crops.gpkg`, EPSG:3577), rasterised to a 3km majority-class grid
for legibility at national extent (individual paddocks are far smaller than one printed pixel
at this scale — this is a density/majority visualisation, not the polygon layer itself).
Classified polygons coloured by predicted class: Cereal 32.9% (443,008), Legume 8.9%
(119,578), Canola 6.5% (88,180); unclassified polygons shown in grey (Abstained, 51.7%,
695,816) rather than left blank, carrying one of four abstain reasons (`area_below_min`,
`no_crop_signal`, `unsegmented_blob`, `too_few_observations` — full breakdown in the source
script). Percentages are by polygon count, not by area; the area-weighted abstain rate
reported elsewhere (66%, `ABS_COMPARISON_NATIONAL.md`) is not the same quantity.

**Figure 5.** ABS validation: composition and area-inflation decomposition. (a) Mapped vs.
ABS crop-share composition (Canola, Cereal, Legume), medians over the well-covered SA2-years
(`ABS_COMPARISON_100km.md`). (b) Decomposition of the area over-call by class — ABS share,
the diluted share a perfect classifier would report given the measured over-call, and the
absorbed excess — showing the over-call sits almost entirely in Cereal and Legume, not Canola.

**Figure 6.** Presence-gate trade-off. Stacked presence recall (amplitude gate AND
presence-shape gate both applied) by crop, across four gate configurations
(`PHENOLOGY_GATE.md`). The shipped (baseline) configuration trades Canola recall (94.5% ->
78.3%) for no change in Cereal/Legume recall relative to amplitude-only; two-pass gating
(Canola exempted from the shape gate) restores Canola to 94.5% at no cost to the other
classes but is not yet validated against the ABS area ratio (§16, `PAPER_PLAN.md`).

**Figure 7.** Multi-year regional evidence, with a reserved national panel. (a) Year-by-year
classified share and mean `ndvi_amp`, 2017-2025, 100km Riverina box (`ABS_COMPARISON_100km.md`);
2017 and 2018 (red) are flagged as structurally weaker years, attributed to Sentinel-2B's
mid-year operational start and a genuine drought respectively. (b) **[PENDING: E8]** — the
equivalent national series is reserved but intentionally left blank pending the national
2017-2025 multi-year run; do not read panel (b) as a null result.

**Figure 8.** Cereal yield model performance and ABS calibration. Aggregate-only by design —
no per-trial predicted-vs-actual scatter is shown, since each point would be a single NVT
trial record covered by the GRDC NDA (`CLAUDE.md`). (a) R² by model arm (year+state baseline,
satellite features, satellite+year/state) under temporal transfer (train <=2022, test 2023-24)
and spatial transfer (5-fold GroupKFold on site). (b) Calibration check: NVT-median-factor
(0.6248) calibrated yield vs. ABS-implied yield, fit on 2022 only and checked on 2023-24
(+3.1% / +18.1% error).
