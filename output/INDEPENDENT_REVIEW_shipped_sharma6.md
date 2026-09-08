# Independent review — "shipped+sharma6" candidate model

Written 2026-09-07 by an independent reviewer with no role in building this candidate, per this
project's generator-evaluator separation rule (`CLAUDE.md`). Reviews the claim in
`GROUP3_MODEL_shipped_plus_sharma6_VALIDATION.md` (macro F1 0.890 temporal / 0.892 spatial vs.
shipped 0.821/0.823, with no regression on canola-at-5%-FPR) against
`GROUP3_MODEL_shipped_plus_sharma6.md`, `train_group3_shipped_plus_sharma6.pbs`, the actual PBS
job log, the current `train_species.py` source, git history, and a from-scratch reproduction of
the training run performed independently for this review. This candidate directly superseded an
earlier "19-index" candidate that a prior independent review (`INDEPENDENT_REVIEW_19index.md`)
found three real problems with; this review treats none of that prior review's conclusions as
inherited without direct re-checking. Aggregate-only — no TrialCodes, no site-level records.

## Verdict: ADOPT — with two minor, non-blocking caveats for the record

This is the cleanest candidate this project has produced. Every load-bearing number was
independently reproduced from scratch, several at full (unrounded) precision, and none of the
three problems the precedent review found in the prior candidate reproduce here. The one number
under the most scrutiny — canola-at-5%-FPR "exact match" — checks out not just at the reported
1-decimal precision but at the level of the raw fraction and the underlying row-by-row
classification outcome. Two things fall short of the precedent's standard of full disclosure
(a loosely-cited verification claim, and an unacknowledged multiple-comparisons exposure from the
exploration process that produced this candidate) but neither casts doubt on the headline numbers
themselves. Ship it; fix the two items below when convenient, not as a gate.

## Findings, most important first

### 1. Full byte-for-byte reproduction of the training run, independently executed

I re-ran `train_group3_shipped_plus_sharma6.pbs`'s exact command line myself (same interpreter,
same input files, same flags — `--indices`, `--bands`, `--bands-keep-families ndre2 vi2 vi3 vdvi
vci evi2_sharma`, `--keep keep_reviewed_SENSITIVE.csv`, `--test-keep
testkeep_temporal_SENSITIVE.csv`, `--model hgb`, `--importance-repeats 5`), writing output to a
scratch path rather than overwriting the committed report. Exit 0.

```
diff output/GROUP3_MODEL_shipped_plus_sharma6.md <my re-run's output>.md   -> no differences
md5sum output/figures/confusion_group3_shipped_sharma6_temporal.png <my re-run's PNG>
  -> 817aa6ed86fe362bf69c3e703fe2364f  (identical)
md5sum output/figures/confusion_group3_shipped_sharma6_spatial.png <my re-run's PNG>
  -> c4fc34986967c452ad665c8dd4b63a09  (identical)
```

Every number in the report — macro F1/balanced accuracy on both splits, all three per-class
P/R/F1 rows, both confusion matrices, canola-at-5%-FPR/average-precision/ROC-AUC, and the
permutation-importance table — reproduces exactly, and the two confusion-matrix PNGs match to the
byte. This is the strongest verification available: nothing in the current codebase, run today,
produces a different answer than what's published. (HGB is deterministic below 10,000 training
rows at any feature count — `EVAL_SEED_STABILITY.md`'s finding, and this dataset trains on 1,651
rows regardless of feature count, so this reproducibility is expected, not a coincidence — but
expected-and-confirmed is a meaningfully stronger position than expected-and-assumed.)

### 2. The canola-at-5%-FPR "exact match" (89.0%) verified at full precision, not just at the reported rounding

This is the exact metric the prior candidate silently regressed on (89.0%→85.8%). The validation
report claims this candidate matches shipped exactly (89.0%, "+0.0 pp"). A match at 1 decimal
could in principle hide two different underlying values that happen to round the same way, so I
recomputed the raw (unrounded) fraction directly, calling `train_species.py`'s own `build_features`
and `family` functions and fitting fresh `HistGradientBoostingClassifier` instances myself,
independent of the script's `main()`:

```
SHIPPED  (3 indices, 51 feat):   canola@5%FPR = 0.890323  (138/155)  threshold(95th pct of negatives) = 0.079428
CANDIDATE (153 feat, shipped3+sharma6): canola@5%FPR = 0.890323  (138/155)  threshold = 0.053566
EXACT MATCH of raw fraction: True
```

The two models have different decision thresholds (0.079 vs 0.054 — they are genuinely different
fitted models, not a no-op), but land on the identical integer count of correctly-detected canola
paddocks (138 of the same 155 held-out canola test rows) above their respective thresholds. The
"+0.0 pp, exact match" claim is real, not a rounding artifact.

I also verified directly (not by trusting either report's stated row counts) that the two models
were scored on **exactly the same TrialCode index** — I built both feature matrices independently
and compared `F.index` for the two arms: `list(idx_shipped) == list(idx_candidate)` → `True`. This
closes the "byte-identical row sets" question with a direct check, not an inherited assumption
(see Finding #6 below for why the report's own citation for this claim is weaker than it should
be).

### 3. `family()`'s bin-suffix bug (precedent review finding #1): genuinely fixed, confirmed three ways

The prior review found that `family()`'s old digit-length heuristic let 10 raw-band 90-bin columns
(`blue_90`, `nir_1_90`, etc.) escape `--bands-drop-raw`. The current code
(`train_species.py:71-106`) replaces the heuristic with membership in `_BIN_LABELS`, a module-level
set of the actual 13 valid bin-label strings. I checked this three ways, not just by reading it:

- **Read the fix and its own docstring**, which documents both the original bug and a *first
  fix attempt that was itself wrong* (dropping the digit-length check entirely broke `nir_1`,
  `nir_2`, `swir_2`, `swir_3` — band names that themselves end in a digit — the opposite failure
  mode). This kind of self-documented "we got it wrong once already" note is a positive
  reliability signal, not just a claim.
- **Directly exercised `family()`** against 13 hand-picked cases, including exactly the ones that
  broke the original bug and the first fix attempt:
  ```
  family('blue_90')            -> 'blue'          (bug case: was 'blue_90' before the fix)
  family('nir_1_90')           -> 'nir_1'
  family('nir_1__amp')         -> 'nir_1'         (first-fix-attempt regression case: was 'nir' under the naive fix)
  family('swir_2__peak_doy')   -> 'swir_2'
  family('ndre2_230@bands')    -> 'ndre2'         (multi-source suffix case)
  family('ndvi_pad_median_330@indices') -> 'ndvi_pad_median'
  ```
  All 13 cases returned the documented-correct family.
- **Confirmed the fix is committed**, not a working-tree change that could silently disappear:
  `git diff HEAD -- src/paddocks/train_species.py` is empty, and `git log` shows the fix in
  commit `ae269c9` ("Expand vegetation indices 3->19, fix a family() drop-raw bug, and land a
  clean 3+6-index candidate"), which is the current HEAD state of this file.

### 4. No raw-band leakage into the candidate's 153 features, verified two ways independent of trusting `family()` alone

This candidate doesn't use `--bands-drop-raw` at all (the mechanism the prior bug lived in) — it
uses `--bands-keep-families`, an **allow-list** (`family(c) in keep_fams`) rather than the
vulnerable subtraction-based drop-list. I checked this is robust even to a hypothetically-still-
buggy `family()`:

```python
keep_fams = {"ndre2","vi2","vi3","vdvi","vci","evi2_sharma"}
Any raw band name collides with keep_fams?            set()   # no collision
Any OTHER (non-Sharma) index family collides?          set()   # no collision
```

None of the 10 raw band names, and none of the other 13 index families (`ndvi`, `ndyi`, `cfi`,
`ndre`, `ndwi`, `nbr`, `psri`, `swir_ratio`, `evi`, `evi2`, `savi`, `gndvi`, `cire`) can ever be
mis-classified as one of the 6 Sharma families under any plausible `family()` implementation,
because the literal names don't overlap. Separately, the column arithmetic in the job's own log
checks out exactly: `--bands-keep-families [...]: dropped 391 other columns, 102 columns remain`
— 391+102 = 493 = 29 value-columns (10 raw bands + 19 index families) × 17 (13 DOY bins + 4
summary stats), and 102 = 6 kept families × 17. The other 51 features (153−102) come from
`--indices` (3 families × 17), a separate code path that never touches `add_indices()` or
`--bands-keep-families` at all. No raw band, and no other index family, is present in the 153
features.

### 5. The shipped-model comparator (0.821/0.823, canola 89.0%) independently re-verified, not just quoted

The validation report's comparison table cites `GROUP3_reviewed.md`'s numbers as "shipped." I
found and read that report's actual job log (`175799567.gadi-pbs.OU`, arm `reviewed`), separately
from anything the candidate's own log shows:

```
=== arm: reviewed ===
indices: 3439 trials, 3 value columns
quality filter: 2194 trials kept
feature matrix (2194, 51), 3 classes
Temporal transfer — train <=2022, test 2023-24          macroF1 0.821  balAcc 0.821
spatial (GroupKFold on site)                            macroF1 0.823  balAcc 0.821
Exit Status: 0
```

This matches `GROUP3_reviewed.md`'s file contents (which also states canola@5%FPR 89.0%) exactly.
The "shipped" comparator in the candidate's report is a real, independently-locatable run, not a
number carried over from memory or another document.

### 6. Sharma et al. 2026 formulas unchanged since the prior review's independent check; the citation itself is real

`add_indices()`'s Sharma-index lines (`train_species.py:172-196`) are textually identical to what
the prior independent review hand-verified against the user-supplied Table S2 (NDRE2, Vi2, Vi3,
VDVI, VCI, EVI2_sharma) — no drift since that check. Separately, I confirmed the citation itself
isn't a fabricated or misattributed reference: `PROJ_NOTES.md`'s 2026-08-31 entry records that the
project's own citation-audit pass verified Sharma et al.'s author list and title against Crossref
directly (catching and fixing a previously-wrong paraphrased title/initials in the manuscript's
`.bib` files), and `output/manuscript/sections/11_references.md` carries the corrected, checkable
form: "Sharma, S., Eslick, H., Pires, R., Singh, B., Tareque, H. (2026). Temporal sensitivity of
in-season crop classification: an explainable multi-year Sentinel-2 analysis in Western
Australia. *Remote Sensing*, 18(10), 1653. doi:10.3390/rs18101653" — a real, well-formed DOI in a
real journal, not an invented reference.

### 7. The cited "19-idx candidate, bug-fixed" comparison numbers trace to a real file

The report's comparison table cites the bug-fixed 19-index arm at 0.886/0.893 temporal,
0.867/0.869 spatial, canola@5%FPR 85.8%, from
`output/arms/idx_arch_sweep/bands_idxonly_all19_hgb_FIXED2.md`. I read that file directly — it
contains exactly those numbers, verbatim. Not restated from memory or transcribed incorrectly.

### 8. No leakage mechanism: feature construction is per-row, and family selection is a fixed a-priori list

`build_features()`/`add_indices()` compute every feature (bin medians, p10/p90/amplitude/peak-DOY)
from each TrialCode's own time series alone — there is no global fit (no scaler, no encoder, no
statistic computed across rows) that could let a test row's value leak into a train row's feature,
or vice versa. `--bands-keep-families`'s filtering is applied via a fixed, named list decided in
advance (the paper's own 6 indices), not a statistic chosen by looking at held-out performance —
so there's no channel by which *this specific run's* feature selection could have seen test data.
(See Finding #10 for a related but distinct process-level concern: whether the *decision to try*
this exact family set was itself influenced by repeated looks at the same fixed test set across
the broader exploration sweep — that is a real, separate question from within-run leakage, which
is what this finding rules out.)

### 9. Minor: the validation report's row-identity citation is looser than it reads

`GROUP3_MODEL_shipped_plus_sharma6_VALIDATION.md` states: "1651 train / 543 test rows,
byte-identical row sets to both (confirmed in `INDEPENDENT_REVIEW_19index.md` #5, unaffected by
anything below)." Finding #5 of the prior review verified that `train_group3_reviewed.pbs` and
`train_group3_19index.pbs` point at byte-identical `--keep`/`--test-keep` paths — but
`train_group3_shipped_plus_sharma6.pbs` did not exist at the time that review was written, so #5
never examined *this* script. The underlying claim is true — I independently verified it in
Finding #2 above via direct TrialCode-index comparison, and separately by reading this candidate's
own PBS script (`--keep $D/keep_arms/keep_reviewed_SENSITIVE.csv --test-keep
$D/keep_arms/testkeep_temporal_SENSITIVE.csv`, identical paths to the shipped arm's script) — but
the report's phrasing implies a specific prior verification that, read literally, doesn't cover
this file. Small, but worth tightening: cite what was actually checked, or note that it's an
extension of #5's reasoning rather than a re-application of #5 itself.

### 10. Undisclosed: the fixed 543-row test set was scored by ~20 exploration arms before this one was recommended

`INDEX_ARCHITECTURE_SWEEP.md` scores at least 20 distinct feature-set/architecture combinations
(round 1's 12-row table, round 2's 8-row table) against the *same* fixed 543-row temporal test set
and the same spatial split, before concluding "Sharma et al.'s 6 indices are the real driver" and
recommending exactly the configuration this candidate implements. Neither that document nor the
validation report flags that repeatedly scoring many arms against one fixed, never-refreshed test
set carries some risk that the winning configuration is, to an unmeasured degree, selected partly
for fitting this particular 543-row sample rather than population performance generally — the
textbook exposure of exploratory feature engineering without a held-out validation set distinct
from the final reported test set.

This does not look large in practice: the gain is big (+0.069 temporal / +0.069 spatial macro F1
over shipped) and moves together on two structurally different evaluation protocols (temporal
holdout and GroupKFold-on-site), which a test-set-fitting artifact would not obviously produce on
both; and it lands in the same range as Sharma et al.'s own reported accuracy on a related task
(external, independent evidence in the same direction). But it is a real, unacknowledged
methodological exposure, and the honest fix — scoring the final candidate once against a genuinely
fresh holdout that no arm in the sweep ever touched — hasn't been done. Worth doing before treating
0.890/0.892 as the number to defend against a skeptical reviewer, though not a reason to withhold
adoption given the size and cross-split consistency of the effect.

### 11. Everything the report discloses as a caveat is accurate and not selectively framed

Unlike the prior candidate (which reported comparison tables for every metric that improved and
omitted one for the metric that got worse), this report's canola-operating-point table includes
*all three* threshold-free metrics with explicit deltas, including the two that move slightly the
wrong way (average precision −0.009, ROC AUC −0.003) — the same kind of selective-framing problem
the precedent review flagged does not recur here. The Caveats section (single seed, unbootstrapped
spatial split, unpruned negative-importance families) is honest about what wasn't done, matching
this report's own disclosed "Status: candidate, not yet independently reviewed" framing.

## What a human should check next

1. **Nothing blocks shipping this candidate on the evidence checked here** — reproduce cleanly,
   no leakage, no raw-band contamination, canola operating point genuinely unregressed at full
   precision, formulas and citation both verified.
2. **Tighten the row-identity citation** (Finding #9) — cite this candidate's own PBS script
   directly, or note explicitly that it extends #5's reasoning rather than restates it.
3. **Before defending 0.890/0.892 to a skeptical external reviewer**, consider scoring this exact
   153-feature configuration once against a test set that was never looked at during the
   `INDEX_ARCHITECTURE_SWEEP.md` exploration (Finding #10) — a genuinely fresh holdout, even a
   small one, would close the one methodological gap this review found that the report doesn't
   acknowledge.
4. Everything else flagged as still-open in the candidate's own Caveats section (single seed at
   153 features specifically, spatial split not bootstrapped, negative-importance families not
   pruned) remains open and was not re-litigated here since the report already discloses them
   accurately.
