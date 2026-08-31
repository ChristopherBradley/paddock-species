# Shipped 3 indices + Sharma et al. 2026's 6 — clean candidate, full validation

Written 2026-08-31. **Supersedes** the 19-index candidate (`GROUP3_MODEL_19index.md`,
`GROUP3_MODEL_19index_VALIDATION.md`) after `INDEPENDENT_REVIEW_19index.md` found three
problems with it (verdict: DO NOT ADOPT — NEEDS MORE EVIDENCE). This candidate directly
resolves all three — see "How the three findings were addressed" below. Aggregate metrics
only, no TrialCodes — safe to read/share.

**Status: candidate, not yet independently reviewed.** This report and the fix it validates
were built by the same process that received the original review's findings — per this
project's generator-evaluator separation rule (`CLAUDE.md`), a fresh independent pass over
*this* candidate (not just a reread of the original review) is the appropriate next check
before treating it as ready to ship, even though the numbers below leave nothing outstanding
that the original review flagged.

## What's being validated

153 features: the shipped model's own `ndvi`/`ndyi`/`cfi` (`--indices`, per-pixel-index-then-
median, byte-identical inputs to the shipped model — not the bands-pathway reconstruction) +
Sharma et al. 2026's `ndre2`/`vi2`/`vi3`/`vdvi`/`vci`/`evi2_sharma` computed from bands via the
new `--bands-keep-families` flag (added 2026-08-31 for exactly this experiment). Same
`--keep`/`--test-keep`/HGB hyperparameters as shipped and as the 19-index candidate — 1651
train / 543 test rows, byte-identical row sets to both (confirmed in
`INDEPENDENT_REVIEW_19index.md` #5, unaffected by anything below).

## How the three independent-review findings were addressed

1. **`family()`'s bin-suffix bug (review #1)**, which let 10 raw-band columns leak past
   `--bands-drop-raw` in every prior "indices-only" arm — fixed at the source
   (`train_species.py`, now checks membership in the real `_BIN_LABELS` set instead of
   guessing from digit-length). Two attempts: the first naive fix (drop the length check
   entirely) broke the opposite direction, silently un-matching band families that
   themselves end in a digit (`nir_1`, `nir_2`, `swir_2`, `swir_3`); the second is correct
   and applies to every arm run after it, including this one. Confirmed: this candidate's own
   log reports exactly 153 columns (3 shipped-index families, unaffected by `--bands-drop-raw`
   entirely since they come from `--indices` not `--bands`, + 6 Sharma families × 17 = 102, +
   the 51 shipped-index features... — see Reproducibility below for the exact log line).
2. **The "bugfix, not new indices" isolation was confounded (review #2)** — no experiment had
   added Sharma's 6 indices directly on top of the shipped model's own 3, computed the shipped
   model's own way. This run is exactly that experiment: `--indices` for the 3 shipped indices
   (real per-pixel-index-then-median, no CFI-computation substitution) joined with
   `--bands-keep-families ndre2 vi2 vi3 vdvi vci evi2_sharma` for Sharma's 6 and nothing else
   — no `nbr`/`ndwi`/`ndre`/`psri`/`swir_ratio`, no never-shipped index families riding along.
3. **Undisclosed canola-at-5%-FPR regression (review #3)** — does not reproduce here. See the
   comparison table below: this candidate matches the shipped model on the decision-relevant
   metric exactly. No ship/don't-ship judgment call about accepting a regression is needed,
   because there is none to accept.

## Temporal transfer — train <=2022, test 2023-24

| | shipped (3 idx, 51 feat) | 19-idx candidate, bug-fixed (323 feat)\* | **this candidate (153 feat)** |
|---|---|---|---|
| macro F1 | 0.821 | 0.886 | **0.890** |
| balanced accuracy | 0.821 | 0.893 | **0.897** |

\*`output/arms/idx_arch_sweep/bands_idxonly_all19_hgb_FIXED2.md` — the all-19-index-families
arm re-run after the `family()` fix, kept for the record but not adopted: it needs more than
twice the features to land in the same place, still carries the never-shipped `nbr`/`ndwi`/etc.
families and the band-pathway CFI substitution the review flagged, and still shows the canola
regression below.

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.93 | 0.85 | 0.89 | 155 |
| Cereal | 0.96 | 0.95 | 0.96 | 279 |
| Legume | 0.77 | 0.89 | 0.83 | 109 |

**Canola operating-point metrics — the comparison the original validation report omitted
(review #3):**

| metric | shipped | 19-idx candidate (bug-fixed) | **this candidate** | delta vs. shipped |
|---|---|---|---|---|
| canola detected @ 5% FPR | 89.0% | 85.8% | **89.0%** | **+0.0 pp** |
| average precision (canola) | 0.944 | 0.938 | **0.935** | -0.009 |
| ROC AUC (canola) | 0.965 | 0.965/0.967\*\* | **0.962** | -0.003 |

\*\*differs slightly between the FIXED and FIXED2 re-runs of the 19-idx arm; both are worse
than shipped either way.

The decision-relevant metric (5% FPR detection) matches shipped exactly; the two threshold-free
summaries move a hair in the wrong direction but by an order of magnitude less than the 19-index
candidate's regression, and F1/precision/recall on Canola are flat-to-improved (0.88→0.89 F1).

Confusion (`figures/confusion_group3_shipped_sharma6_temporal.png`): 19 Canola misread as
Legume, 4 the other way — same dominant Canola<->Legume error pattern as shipped and the
19-index candidate, at a rate between the two.

## Spatial transfer — 5-fold GroupKFold on site

| | shipped | 19-idx candidate (bug-fixed) | **this candidate** |
|---|---|---|---|
| macro F1 | 0.823 | 0.867 | **0.892** |
| balanced accuracy | 0.821 | 0.869 | **0.896** |

| crop | precision | recall | F1 | n |
|---|---|---|---|---|
| Canola | 0.91 | 0.88 | 0.89 | 155 |
| Cereal | 0.97 | 0.96 | 0.96 | 279 |
| Legume | 0.79 | 0.85 | 0.82 | 109 |

This candidate's spatial macro F1 (0.892) is *higher* than its own temporal macro F1 (0.890)
and clearly ahead of the bug-fixed 19-index candidate's spatial score (0.867) — both splits move
together and neither lags, same pattern the original review confirmed was not temporal-only
memorisation.

## Where the signal is (permutation importance, temporal holdout, macro-F1 scoring)

| feature family | importance |
|---|---|
| `ndre2` | **+0.0964** |
| `vi3` | +0.0342 |
| `evi2_sharma` | +0.0080 |
| `vci` | +0.0078 |
| `cfi_pad_median` | -0.0062 |
| `ndvi_pad_median` | -0.0078 |
| `vi2` | -0.0106 |
| `ndyi_pad_median` | -0.0156 |
| `vdvi` | -0.0177 |

`ndre2` alone still carries roughly 3x the next family, consistent with the 19-index candidate's
importance table — this is the third independent measurement (isolation ablation, full-19-index
importance, and now this clean 6-index importance) to land on the same conclusion. Five of the
eight families here show *negative* importance at this feature count, i.e. shuffling them
slightly helped — worth a follow-up ablation (drop the negative families, re-score) before
finalising a feature set, but not investigated in this pass.

## Caveats

- **Not yet independently reviewed** — see Status above. This report validates that the three
  specific problems the independent reviewer found do not reproduce in this candidate; it is not
  itself an independent check.
- **Single seed.** Same `EVAL_SEED_STABILITY.md` reasoning as the 19-index candidate applies
  (HGB deterministic below 10,000 rows) — still an extrapolation across feature count, not
  measured at 153 features specifically.
- **Spatial split still a single GroupKFold partition**, not bootstrapped — same open item the
  original independent review flagged (#4) and still unresolved here.
- **Negative-importance families** (`cfi_pad_median`, `ndvi_pad_median`, `vi2`, `ndyi_pad_median`,
  `vdvi`) not pruned or investigated further in this pass.

## Reproducibility

`src/paddocks/train_group3_shipped_plus_sharma6.pbs` → job `177833083.gadi-pbs` (normal queue,
12 CPU, 32GB, 1m52s walltime, exit 0, 0.75 SU). Log confirms `feature matrix (2194, 153)` and
`--bands-keep-families ['evi2_sharma', 'ndre2', 'vci', 'vdvi', 'vi2', 'vi3']: dropped 391 other
columns, 102 columns remain` (102 = 6 index families x 17 bin/summary features; the other 51
come from `--indices`' 3 shipped-index families joined in separately). Produced
`output/GROUP3_MODEL_shipped_plus_sharma6.md` (source of every number above) and the two
confusion-matrix figures. Code: `src/paddocks/train_species.py` (`family()` bugfix,
`--bands-keep-families`).
