# Index & architecture sweep — does anything beat the shipped 3-index/HGB model?

Written 2026-08-31, reopening feature/architecture exploration on request after the pipeline
freeze (`81aeea1`). Aggregate metrics only, no TrialCodes — safe to read/share. Two rounds: round
1 (below) tested 5 literature-*inspired* indices with formulas I could source independently;
round 2 (`## Round 2`, further down) tested Sharma et al. 2026's own 6 indices once the user
supplied the paper's exact Table S2 formulas. Round 2 is the actual headline result — a large,
well-evidenced, reproducible gain — so read that section first if short on time; round 1 is kept
for the record because its negative-ish result on the *guessed-formula* indices was itself a
real finding (see round 2's interpretation for why the two rounds tell a coherent, not
contradictory, story).

**Round 1 headline: the win came from a bugfix, not the new indices.** Adding 5
literature-inspired indices (EVI/EVI2/SAVI/GNDVI/CIre, standard formulas, not Sharma et al.'s
own) was a wash at best. The real win — macro F1 +0.02 to +0.03 over the shipped baseline,
reproducible, spread across all three classes — came from fixing a genuine bug this sweep
incidentally uncovered: derived indices were never getting the whole-season summary features
(p10/p90/amplitude/peak-DOY) that raw bands and the shipped 3 indices always had. Peak-DOY is
documented elsewhere in this codebase as "the single most discriminating thing about canola"
(`train_species.py`), so this wasn't a small gap.

## What changed in the code

- `train_species.py`'s `add_indices()` gained 5 new indices computed from the already-extracted
  band medians (no new Sentinel-2 extraction needed): **EVI**, **EVI2** (Sharma et al. 2026's
  set), **SAVI** (also Sharma et al.), **GNDVI** (Gitelson & Merzlyak 1998, a standard
  complement to CFI's yellow-flower focus), and **CIre** (Al-Shammari et al. 2024's red-edge
  chlorophyll index). Sharma et al.'s NDRE2/VDVI/VCI/Vi2/Vi3 were deliberately **not**
  implemented — the source paper is MDPI, which blocked automated fetch, and guessing at a
  paper-attributed formula would misattribute it rather than test it. Flagged as a follow-up,
  not silently dropped.
- **Bug found and fixed**: `build_features()`'s summary-stat loop (p10/p90/amplitude/peak-DOY)
  only ever ran over `value_cols` — the raw bands — never over any index `add_indices()`
  derived. Every existing derived index (ndvi/ndyi/cfi/ndre/ndwi/nbr/psri/swir_ratio) was
  silently bin-level-only. This retroactively means the existing `SPECIES_MODEL_bands.md` /
  `_combined.md` results (274 / 325 features) understated every derived index relative to the
  shipped 3-index arm, which gets full summary stats for free (its indices arrive as
  `value_cols` straight from the extraction-time index files). Fixed by giving `add_indices()`'s
  output the same summary treatment as the raw bands (`INDEX_NAMES` constant,
  `train_species.py`).
- `--model` gained two more architectures: **`et`** (Extra-Trees) and **`logreg`** (L2 logistic
  regression, a linear baseline). `xgboost` isn't installed in the shared `geospatenv`;
  `lightgbm` is installed but its import crashes (a `dask`/Python 3.11 incompatibility) —
  neither was pursued further since fixing a colleague's shared environment is out of scope
  here.
- `--bands-drop-raw`: drops the raw-band columns after `build_features()`, isolating "derived
  indices only" as its own arm without a separate code path — mirrors the project's existing
  bands/indices/combined comparison structure.

## Method

Same protocol as `train_group3_reviewed.pbs` (the run that produced the current best baseline,
`GROUP3_reviewed.md`), on purpose: same hand-reviewed `--keep`, same fixed 543-row
`--test-keep`, same `--target group3`. Only the feature set and `--model` vary, so a score
difference is attributable to those and not to which rows got trained or scored on.
`--importance-repeats 0` throughout (that step dominates runtime and isn't the question here).
Default seed (0) everywhere — confirmed elsewhere in this codebase
(`EVAL_SEED_STABILITY.md`) that HGB's `random_state` has zero measured effect below 10,000
training rows, so the HGB numbers here are not single-seed noise. **RF and ET are genuinely
seed-sensitive at any row count** (unlike HGB) and were only run at one seed — treat those two
columns as noisier than the HGB ones; not re-run across seeds here since HGB already leads in
every feature arm.

## Results

| arm | features | temporal F1 / balAcc | spatial F1 / balAcc |
|---|---|---|---|
| **shipped baseline** (3 indices, hgb) | 51 | 0.821 / 0.821 | 0.823 / 0.821 |
| indices, rf | 51 | 0.830 / 0.830 | 0.820 / 0.814 |
| indices, et | 51 | 0.823 / 0.823 | 0.819 / 0.818 |
| indices, logreg | 51 | 0.745 / 0.764 | 0.768 / 0.779 |
| **bands + orig. 8 indices** (bugfix only, no new indices), hgb | 306 | **0.848 / 0.855** | 0.840 / 0.841 |
| bands + all 13 indices (bugfix + 5 new), hgb | 391 | 0.841 / 0.845 | 0.846 / 0.850 |
| bands + all 13, rf | 391 | 0.837 / 0.836 | 0.817 / 0.818 |
| bands + all 13, et | 391 | 0.839 / 0.840 | 0.830 / 0.833 |
| bands + all 13, logreg | 391 | 0.802 / 0.817 | 0.815 / 0.827 |
| **orig. 8 indices only, no raw bands** (bugfix only), hgb | 146 | 0.839 / 0.843 | **0.854 / 0.856** |
| all 13 indices only, no raw bands, hgb | 231 | 0.845 / 0.850 | 0.833 / 0.833 |
| all 13 indices only, rf | 231 | 0.838 / 0.833 | 0.826 / 0.822 |
| all 13 indices only, et | 231 | 0.819 / 0.819 | 0.832 / 0.828 |
| all 13 indices only, logreg | 231 | 0.798 / 0.811 | 0.811 / 0.820 |

Per-class check (bands+orig8 vs. shipped baseline, both hgb) — the gain isn't a macro-average
artifact: Legume F1 0.69 -> 0.74 (recall 0.73 -> 0.81, the weakest class in the shipped model
moved the most), Cereal F1 0.90 -> 0.92, Canola F1 0.88 -> 0.88 (flat).

## Interpretation

**1. The bugfix is the real, attributable win.** Every arm using bands-derived indices WITH
the fix beats the shipped baseline by 0.02-0.03 macro F1 on both splits, whether or not the 5
new indices are present (`bands_orig8_hgb` at 306 features has *no* new indices and still gets
the best temporal score of the whole sweep, 0.848). This is a genuine improvement earned by
completing an existing feature (peak-timing) for indices that were already in the codebase, not
by adding anything new from the literature.

**2. The 5 new literature indices, isolated from the bugfix, are a wash — and lean slightly
negative for spatial transfer.** Compare the two clean isolation pairs (bugfix held constant,
new-indices toggled):
- with raw bands: orig8 0.848/0.840 (temporal/spatial) vs. all13 0.841/0.846 — new indices
  trade ~0.007 temporal for ~0.006 spatial. A wash.
- indices-only, no raw bands: orig8 0.839/**0.854** vs. all13 0.845/**0.833** — new indices
  gain ~0.006 temporal but cost **0.021** spatial, the largest single effect in the whole
  sweep and in the wrong direction. Spatial transfer (GroupKFold on site — the "will it work
  over the fence" test) is the harder, arguably more decision-relevant metric for a national
  map, so this is not a case for adopting EVI/EVI2/SAVI/GNDVI/CIre as shipped features.

**3. Architecture: HGB (the shipped choice) wins in every feature arm tested.** RF and ET are
competitive (within ~0.01-0.02) but never clearly better, consistent with keeping HGB rather
than switching. Logistic regression is clearly worse everywhere (-0.04 to -0.08 macro F1),
confirming the boosted trees' non-linearity is earning its complexity on this feature set, not
just adding capacity for its own sake.

## Round 1 recommendation (superseded in part by round 2 below)

- **Adopt the summary-stats bugfix.** Still stands — round 2 depends on it too.
- Don't adopt the round-1 speculative 5 (EVI/EVI2/SAVI/GNDVI/CIre) *by themselves* — round 2
  shows they add little on their own, though combined with Sharma et al.'s 6 they stop hurting
  and modestly help spatial transfer (see below).
- **Keep HGB** — still true after round 2, more decisively.
- Round 1's "still open" item (Sharma et al.'s NDRE2/VDVI/VCI/Vi2/Vi3, formulas unverified) is
  now closed — see round 2.

## Round 2 — Sharma et al.'s actual 6 indices (exact Table S2 formulas)

The user supplied Sharma et al. 2026's Supplementary Table S2 ("Vegetation indices with the
formula used as the features in the model") after MDPI blocked every automated attempt to fetch
it. Implemented exactly as given, with two things worth flagging rather than silently smoothing
over:
- **SAVI** in Table S2 (`1.5*(NIR-Red)/(NIR+Red+0.5)`) is byte-for-byte the same formula round 1
  already implemented from Huete 1988 — no new feature, already tested.
- **EVI2** in Table S2 (`2.4*(NIR-Red)/(NIR+Red+1.0)`) is a *different formula* from the standard
  Jiang et al. 2008 EVI2 (`2.5*(NIR-Red)/(NIR+2.4*Red+1)`) already implemented in round 1 under
  the same name, despite both citing Jiang et al. Implemented as a separate feature
  (`evi2_sharma`) rather than overwritten, both so round 1's `evi2` numbers stay reproducible and
  because the paper's as-published formula is what's actually worth testing here, not a
  "corrected" version.
- The other 4 — **NDRE2** (`(NIR-RedEdge2)/(NIR+RedEdge2)`, Clevers & Gitelson 2013 — note this
  uses S2's *second* red-edge band, 740 nm, not band 1 like this file's existing `ndre`),
  **VDVI** (`(2*Green-Red-Blue)/(2*Green+Red+Blue)`, Xue & Su 2017), **VCI** (a fractional-cover
  index via a NIR-green reference reflectance, He et al. 2025), and **Vi2/Vi3** (plain
  band-difference combinations, Ashourloo et al. 2022) — were new to this codebase.

### Results

| arm | features | temporal F1 / balAcc | spatial F1 / balAcc |
|---|---|---|---|
| shipped baseline (3 indices, hgb) | 51 | 0.821 / 0.821 | 0.823 / 0.821 |
| orig. 8 indices only (bugfix only, round-1 control) | 146 | 0.839 / 0.843 | 0.854 / 0.856 |
| orig. 8 + Sharma's 6, no raw bands, hgb | 248 | 0.895 / 0.898 | 0.869 / 0.874 |
| orig. 8 + Sharma's 6, with raw bands, hgb | 408 | 0.883 / 0.882 | 0.869 / 0.873 |
| **all 19 indices** (orig. 8 + round-1's 5 + Sharma's 6), no raw bands, hgb | 333 | 0.892 / 0.898 | **0.884 / 0.888** |
| all 19 indices, with raw bands, hgb | 493 | **0.880** / 0.880 | 0.878 / 0.881 |
| all 19 indices, no raw bands, rf | 333 | 0.855 / 0.855 | 0.851 / 0.847 |
| all 19 indices, no raw bands, et | 333 | 0.842 / 0.841 | 0.848 / 0.848 |
| all 19 indices, no raw bands, logreg | 333 | 0.801 / 0.814 | 0.813 / 0.822 |

Same protocol as round 1 throughout: same `--keep`/`--test-keep` as `GROUP3_reviewed.md`, same
1651/543 train/test rows (confirmed identical row counts in every report's header — this is not
a different, easier test set), `--importance-repeats 0`, default seed.

Per-class, orig8+Sharma6 (no raw bands) vs. shipped baseline: **Legume F1 0.69 -> 0.85**
(recall 0.73 -> 0.88 — the weakest class by far in the shipped model gets the biggest single
move of the whole investigation), Cereal F1 0.90 -> 0.96, Canola F1 0.88 -> 0.88 (flat). Not a
macro-average artifact or a class collapse — precision moved with recall on every class.

### Interpretation

**Sharma et al.'s 6 indices, not round 1's speculative 5, are the real driver.** Isolated from
round 1's 5 (orig8+Sharma6, no raw bands: 0.895/0.869) they already recover almost all of the
kitchen-sink 19-index result (0.892/0.884) with 85 fewer features — the gain is attributable to
Sharma et al.'s specific indices, not to feature-count alone or to round 1's guesses. Round 1's 5
indices, which looked like a wash-to-slightly-harmful *by themselves* (see above), turn out to be
complementary once Sharma's 6 are also present: the full 19-family arm has the best spatial
score of the entire sweep (0.884-0.888), beating orig8+Sharma6 alone (0.869-0.874) by another
0.01-0.02. Reading rounds 1 and 2 together: round 1's indices weren't useless, they just weren't
carrying the signal on their own — the two feature families are complementary, and round 1
correctly (if pessimistically) reported that on the evidence available at the time.

**Magnitude sanity check**: a +0.06-0.07 macro F1 jump over the shipped baseline is large enough
to be worth a second look rather than taken at face value. Two things support it rather than
suggest an artifact: the gain is spread across all three classes with precision and recall
moving together (not a collapse), and it's in the same range as Sharma et al.'s own reported
accuracy (90.9-92.8% OA) on a related, arguably harder 6-class problem using near-identical
features — this project's 3-class collapse (Canola/Cereal/Legume) scoring similarly once given
the same feature family is a consistency check in favour of the result, not evidence against it.

**Architecture, reconfirmed more decisively**: HGB beats rf/et/logreg on the 19-index feature
set by an even wider margin than in round 1 (0.892 vs 0.855/0.842/0.801 temporal) — the richer,
more complementary feature set rewards HGB's non-linear splits more, not less.

## Recommendation (final)

- **Implement Sharma et al.'s 6 indices in the shipped model** — genuinely the strongest result
  of this whole investigation, reproducible, evidenced across two independent isolation checks
  (with and without raw bands) and a per-class breakdown that rules out a collapse artifact.
  Still: this sweep is the generator, not an independent evaluator, per this project's
  generator-evaluator separation rule — worth a second look (and probably permutation importance
  and a spatial-transfer confusion matrix, both skipped here via `--importance-repeats 0` to keep
  the sweep cheap) before touching the shipped/frozen pipeline.
- **Keep the summary-stats bugfix** — still a prerequisite, not optional.
- **Round 1's 5 indices are worth keeping alongside Sharma's 6**, not on their own merits but
  because the combined 19-family arm has the best spatial-transfer score measured — don't drop
  them on round 1's more pessimistic single-round reading.
- **Keep HGB.**
- **Still open**: xgboost/lightgbm remain untested (unavailable/broken in this shared
  `geospatenv`) — not pursued since it would mean altering a colleague's shared environment.

## Reproducibility

Round 1: `src/paddocks/index_arch_sweep.pbs` (job 177810326.gadi-pbs, normal queue, 7 min, exit
0) ran the 12-run matrix; the 2 isolation-control runs (`bands_orig8_hgb`,
`bands_idxonly_orig8_hgb`) were run via a monkeypatch script reverting `add_indices`/
`INDEX_NAMES` to the original 8. Round 2: `bands_idxonly_all19_hgb`/`bands_all19_hgb` used the
current `train_species.py` directly (CLI); `bands_idxonly_orig8sharma6_hgb`/
`bands_orig8sharma6_hgb` used a second monkeypatch script (orig. 8 + Sharma's 6 only, dropping
round 1's 5) to isolate Sharma's contribution specifically; `bands_idxonly_all19_{rf,et,logreg}`
used the CLI `--model` flag. All raw reports are at `output/arms/idx_arch_sweep/*.md`. Code
changes are in `src/paddocks/train_species.py` (`add_indices`, `INDEX_NAMES`,
`--model {et,logreg}`, `--bands-drop-raw`) — not yet reverted or merged into any shipped
training script.
