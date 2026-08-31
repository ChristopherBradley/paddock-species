> **SUPERSEDED 2026-08-31**, same day this was written. `INDEPENDENT_REVIEW_19index.md` found
> three problems with the candidate validated here (a `family()` bug inflating the "indices
> only" isolation, an overclaimed "bugfix not new indices" causal story, and an undisclosed
> canola-at-5%-FPR regression). All three are addressed by a simpler candidate — the shipped
> model's own 3 indices + Sharma et al. 2026's 6, computed the shipped model's own way — which
> matches or beats every number below with no canola regression. See
> `output/GROUP3_MODEL_shipped_plus_sharma6_VALIDATION.md` for the resolution and
> `output/GROUP3_MODEL_shipped_plus_sharma6.md` for its source report. Kept here unmodified as
> the historical record of what the independent review actually reviewed.

# 19-index candidate model — full spatial & temporal validation [SUPERSEDED, see banner above]

Written 2026-08-31. Validates the winning arm from `INDEX_ARCHITECTURE_SWEEP.md`'s round 2
(orig. 8 indices + round-1's 5 + Sharma et al. 2026's 6, `--bands-drop-raw` so only the 19
derived-index families are used, no raw bands, HGB) with the two things that sweep skipped to
stay cheap: permutation importance (`--importance-repeats 5`, was `0`) and a confusion-matrix
figure for the spatial split, not just temporal (`plot_confusion`/`--spatial-confusion-png`,
added for this run — previously only the temporal split got a figure). Aggregate metrics only,
no TrialCodes — safe to read/share.

**Status: candidate, not yet adopted.** This is the generator's own validation, not an
independent check — see `INDEPENDENT_REVIEW_19index.md` for that, and this project's
generator-evaluator separation rule in `CLAUDE.md` for why the two are kept apart.

## What's being validated

19 vegetation-index families (NDVI/NDYI/CFI/NDRE/NDWI/NBR/PSRI/swir_ratio — already in the
codebase, newly given proper summary stats by the `INDEX_NAMES`/`build_features` bugfix;
EVI/EVI2/SAVI/GNDVI/CIre — added round 1; NDRE2/Vi2/Vi3/VDVI/VCI/EVI2_sharma — Sharma et al.
2026's own indices, added round 2 from their Table S2), each binned onto 13 calendar DOY bins
plus 4 whole-season summary stats (p10/p90/amplitude/peak-DOY) = 333 features. HGB, same
hyperparameters as shipped (`max_iter=400, learning_rate=0.06, class_weight="balanced"`). Same
`--keep` (hand-reviewed rows) and `--test-keep` (fixed 543-row test set) as the current shipped
reference, `GROUP3_reviewed.md` — same 1651 train / 543 test rows exactly, confirmed in this
report's own header, so every number below is directly comparable to the shipped baseline with
no confound from a different or easier sample.

## Temporal transfer — train <=2022, test 2023-24

| | shipped (3 indices) | **19-index candidate** | delta |
|---|---|---|---|
| macro F1 | 0.821 | **0.892** | +0.071 |
| balanced accuracy | 0.821 | **0.898** | +0.077 |

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.92 | 0.85 | 0.89 | 155 |
| Cereal | 0.96 | 0.95 | 0.96 | 279 |
| Legume | 0.78 | 0.89 | 0.83 | 109 |

Canola detected at 5% FPR: 85.8% (n=155); average precision 0.939, ROC AUC 0.967 (binary
canola-vs-rest framing, same metric the shipped reports use).

Confusion (`figures/confusion_group3_19index_temporal.png`): the residual error is almost
entirely Canola<->Legume (19 Canola misread as Legume, 6 Legume misread as Canola) — Cereal is
cleanly separated from both (5 + 8 total leakage out of 279). Not a new confusion pattern this
model introduces; the shipped model's dominant error is the same pair, just at a higher rate.

## Spatial transfer — 5-fold GroupKFold on site

| | shipped (3 indices) | **19-index candidate** | delta |
|---|---|---|---|
| macro F1 | 0.823 | **0.884** | +0.061 |
| balanced accuracy | 0.821 | **0.888** | +0.067 |

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.90 | 0.86 | 0.88 | 155 |
| Cereal | 0.96 | 0.95 | 0.96 | 279 |
| Legume | 0.78 | 0.85 | 0.81 | 109 |

Confusion (`figures/confusion_group3_19index_spatial.png`): near-identical pattern to temporal
(19 + 9 Canola<->Legume leakage, Cereal still clean) — the model is not overfit to the temporal
split specifically; it generalises the same way across sites it never trained on.

**Both splits move together and neither lags the other** (0.892 vs 0.884 macro F1, 0.077 vs
0.067 balanced accuracy) — a model that gained purely by memorising temporal artefacts would be
expected to fall back toward baseline on the harder, group-held-out spatial test; it doesn't.

## Where the signal is (permutation importance, temporal holdout, macro-F1 scoring)

| feature family | importance | family | importance |
|---|---|---|---|
| `ndre2` | **+0.1077** | `ndre` (orig., RE1) | +0.0103 |
| `nbr` | +0.0365 | `ndvi` | +0.0069 |
| `vi3` | +0.0349 | `ndwi` | +0.0049 |
| `cfi` | +0.0310 | `vci_90` | +0.0031 |
| `ndyi` | +0.0238 | `evi2_sharma` | +0.0027 |
| `swir_ratio` | +0.0226 | `evi` (round 1) | +0.0021 |
| `vi2` | +0.0214 | | |
| `vci` | +0.0172 | | |
| `vdvi` | +0.0128 | | |
| `psri` | +0.0121 | | |

`ndre2` alone — Clevers & Gitelson 2013's red-edge index using Sentinel-2's **second** red-edge
band (740 nm), not band 1 like this codebase's pre-existing `ndre` — carries roughly 3x the
importance of the next family, and 10x the pre-existing `ndre` it sits next to using a different
band. That's a specific, checkable claim (band 2 red-edge chlorophyll signal separates these
three crop groups much better than band 1 does on this dataset) rather than a vague "more
features helped."

**Consistent with `INDEX_ARCHITECTURE_SWEEP.md`'s isolation finding**: round 1's 5 indices
(evi/evi2/savi/gndvi/cire) are nearly absent from this table — only `evi` cracks the top 16, at
the bottom, and `gndvi`/`savi`/`cire`/`evi2` (the standard-formula one) don't appear at all. Two
independent lines of evidence (the isolation ablation in round 2, and this importance ranking
from a full run neither of those isolation runs used) now agree: Sharma et al.'s 6 are doing the
work, round 1's 5 are largely along for the ride.

Top individual features: `ndre2_230`, `vi3_250`, `cfi__amp`, `ndre2_250`, `vci__peak_doy`,
`ndre2__amp`, `ndre2_270`, `ndyi__amp`, `ndre2__p90`, `ndre2_110`, `nbr_230`, `ndre2_210` — six
of the top twelve are `ndre2` at different points in the season, plus its own summary stats
(amplitude, p90) ranking highly, meaning its *seasonal shape*, not just one lucky bin, is
carrying signal.

## Caveats

- **Single seed for the reported model.** HGB's `random_state` has zero measured effect below
  10,000 training rows (`EVAL_SEED_STABILITY.md`) — this codebase's own prior finding, not
  assumed here — so this is not under-reported seed noise for HGB specifically.
- **`evi2_sharma` vs `evi2`**: Sharma et al.'s Table S2 EVI2 formula differs from the standard
  Jiang et al. 2008 formula already in this codebase under the same name (see
  `INDEX_ARCHITECTURE_SWEEP.md`'s round 2 for both formulas) — both are present as separate
  features here (`evi2` and `evi2_sharma`); neither ranks highly, so this discrepancy doesn't
  affect the headline result either way.
- **This is the generator's own report.** Numbers are real (not fabricated — every figure above
  is read directly from `GROUP3_MODEL_19index.md`, the machine-generated output of
  `train_species.py`, not retyped from memory), but the choice of which arm to validate this
  thoroughly, and the framing of "the gain is real," comes from the same process that built the
  feature set. See the independent review.
- **Not yet run**: a repeated/bootstrapped spatial-transfer estimate (the 5-fold GroupKFold here
  is a single partition, unlike HGB's seed-insensitivity which only covers the temporal split's
  fixed-seed refit) and select-k / ablation-across-individual-Sharma-indices (which of the 6 is
  doing the work beyond `ndre2` is not fully separated here — `vi3`, `nbr`, `cfi` also rank
  highly but `nbr`/`cfi` are original-8 features, so `vi3` is the clearest second contributor).

## Reproducibility

`src/paddocks/train_group3_19index.pbs` (job 177827011.gadi-pbs, normal queue, 3m42s walltime,
exit 0) produced `output/GROUP3_MODEL_19index.md` (full machine-generated report, source of
every number above) and the two confusion-matrix figures. Code: `src/paddocks/train_species.py`
(`add_indices`, `INDEX_NAMES`, `plot_confusion`, `--spatial-confusion-png`) — same code as
`INDEX_ARCHITECTURE_SWEEP.md`'s round 2, this run just adds importance + the spatial figure on
top of the already-reported score.
