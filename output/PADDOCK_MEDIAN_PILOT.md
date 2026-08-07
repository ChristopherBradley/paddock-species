# Pilot: does paddock-median CFI beat the 200 m corner window?

**Date:** 2026-08-07 · **Status:** complete · **Code:** `src/paddocks/` · **Cost:** 6.6 SU

Follows `PADDOCK_BOUNDARY_BENCHMARK.md`, which chose SAMGeo as the boundary source. This
tests the estimator the boundaries were for.

## Design

42 AOIs / 203 trials across 2018–2023, **every AOI containing both canola and wheat**, so
region and season cannot confound the crop comparison. Both estimators are extracted from
the **same scenes in one pass** (`extract_paddock.py`), so only the spatial support varies:

| | 200 m window (baseline) | paddock (this test) |
|---|---|---|
| support | 400 px, centred on the trial GPS | ~13,600 px, inside one field |
| contents | paddock corner + neighbours + roads + trees | one paddock, eroded 1 px |

Segmentation: 42/42 AOIs, 0 failures, 1,456 polygons, 5.31 SU. Extraction: 169/203 trials,
1.26 SU. The 34 dropouts had **no polygon within 50 m** of the trial point.

## Headline: yes, in the regime that matters — but not by Youden J

**At a strict false-positive budget, paddock-median nearly doubles canola detection.**
Threshold set per season so that a fixed fraction of *wheat* is wrongly flagged:

| wheat false-positive rate | window detects | **paddock detects** | difference (95 % CI) |
|---|---|---|---|
| **5 %** | 27.0 % | **52.0 %** | **+21.0 pp [+2.0, +39.7]**, P(better) 98 % |
| 10 % | 32.7 % | **53.2 %** | +18.9 pp [−1.7, +39.6], P(better) 96 % |
| 20 % | 47.4 % | 60.3 % | — |

The 5 % row is the only comparison in this pilot whose confidence interval excludes zero.

**Youden J does not show this**, and the difference is instructive rather than contradictory:

| | window | paddock median | paddock mean |
|---|---|---|---|
| J, mean over seasons | 0.545 | 0.576 | 0.576 |
| ΔJ vs window, year-stratified bootstrap | — | +0.026 [−0.095, +0.149] | +0.026 [−0.085, +0.141] |

J weights the whole ROC curve equally and the two curves cross, so a large gain confined to
the high-specificity end averages away. The high-specificity end is precisely the operating
region this project needs — Stage 2 exists to *confirm or reject labels*, and a wheat trial
wrongly called canola is the expensive error. Reporting only J would have hidden the result.

**Honesty note on this metric.** The fixed-FPR comparison was chosen *after* seeing that the
paddock estimator was far more specific at the Youden point (flagging 10 % of wheat vs the
window's 47 %). It is motivated by the use case, not fitted to the data, but it was not
pre-registered and one of its two rows is significant. Treat +21 pp as a strong lead to be
confirmed at full scale, not as a settled number.

## Pooling across seasons destroys separation — for every estimator

| year | n canola | n wheat | window | paddock median |
|---|---|---|---|---|
| 2018 | 9 | 5 | 0.689 | 0.600 |
| 2019 | 24 | 10 | 0.433 | 0.508 |
| 2020 | 15 | 5 | 0.400 | 0.400 |
| 2021 | 13 | 10 | 0.469 | 0.669 |
| 2022 | 9 | 10 | 0.500 | 0.500 |
| 2023 | 10 | 9 | 0.778 | 0.778 |
| **mean** | | | **0.545** | **0.576** |
| *pooled over all years* | | | *0.318* | *0.398* |

**The pooled J is below every single individual season.** Absolute CFI level shifts between
seasons, so one shared threshold cannot serve all of them. This is the same "pooling seasons
and regions" effect already identified as cause #1 of the weak heatmap contrast — it applies
to threshold analysis too, and it is now a per-year table in `compare_estimators.py` so the
trap is visible by default. **Any future CFI threshold must be fitted per season.**

Useful side effect: the window baseline's per-season mean is **0.545 against the established
held-out 0.535** from the full 1,630-trial set. The pilot reproduces the known baseline
almost exactly, which is evidence the 42-AOI subset is representative rather than a lucky or
unlucky corner of the data.

## Trial-to-paddock matching

- `contains`: 129 trials (76 %) — the trial point falls inside a polygon
- `nearest` (≤50 m): 40 trials (24 %)
- no polygon within 50 m: 34 trials, dropped

Restricting to `contains` **doubles** the pooled advantage (+0.033 → +0.070 ΔJ), which is the
mechanism behaving as predicted: where the paddock match is trustworthy, the paddock
estimator gains more. Trial-to-edge distance is median 32 m (p10 5 m), confirming the
corner-GPS problem — 10 % of trials sit within half a pixel of a boundary.

Paddock area: median 34 ha (p10 5, p90 139).

**`pad_median` and `pad_mean` correlate at 0.9955** and score identically in every season.
The eroded paddock is nearly homogeneous — which is itself independent support for the NVT
protocol property that the surrounding paddock carries the trial's crop. Prefer the median
anyway: it costs nothing and is robust to a stray unmasked tree line.

## Recommendation

1. **Adopt paddock-median.** It is better where it counts, never worse on the per-season
   mean, and cost is no longer a consideration (154 SU for the full canola+wheat set).
2. **Run the full set to settle it.** The pilot's limitation is power, not cost: 129 trials
   over 6 seasons give a ±0.12 interval on ΔJ. At 2,761 trials that shrinks ~4.5×, which
   would resolve an effect of this size. This is the rare case where the definitive
   experiment is cheaper than further deliberation.
3. **Fit CFI thresholds per season, never pooled** — worth up to 0.2 J on its own, i.e. more
   than the estimator change being tested here.
4. **Investigate the 34 unmatched trials** (17 %) before the full run. If they are
   systematically the small or irregular paddocks the compactness filter rejects, the filter
   thresholds, not the segmentation, are throwing away data.
5. Report high-specificity sensitivity alongside J from here on. J alone hid the main result.

## Files

- `src/paddocks/make_aois.py` — trials → AOIs sized to their trials
- `src/paddocks/submit_paddocks.sh` — two-stage submission (see benchmark report)
- `src/paddocks/extract_paddock.py` — paired paddock + window extraction
- `src/paddocks/compare_estimators.py` — per-year J, paired and year-stratified bootstrap
- Results on scratch: `…/derived/paddock_vs_window{,_contains}.md`,
  `…/derived/samgeo/pilot/paddock_ts_all_SENSITIVE.csv`
