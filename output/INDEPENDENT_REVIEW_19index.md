# Independent review — 19-index candidate model (Sharma et al. 2026 indices)

Written 2026-08-31 by an independent reviewer with no role in building the candidate model,
per this project's generator-evaluator separation rule (`CLAUDE.md`). Reviews the claim in
`GROUP3_MODEL_19index_VALIDATION.md` (macro F1 0.892 temporal / 0.884 spatial vs. shipped
0.821/0.823) against `GROUP3_MODEL_19index.md`, `GROUP3_reviewed.md`,
`INDEX_ARCHITECTURE_SWEEP.md`, the working-tree diff of `train_species.py`, the actual PBS job
log, and the underlying band CSVs. Aggregate-only — no TrialCodes, no site-level records.

## Verdict: DO NOT ADOPT — NEEDS MORE EVIDENCE

The core mechanism (red-edge-2-based indices, especially NDRE2, carrying real signal for
Cereal/Legume separation) is plausible and the formulas, band mapping, and train/test integrity
all check out cleanly under direct inspection. But three independent problems mean the specific
claim under review — "+0.06 to +0.07 macro F1 over the actual shipped model, mostly attributable
to Sharma et al. 2026's 6 indices" — is not yet trustworthy as stated: (1) a confirmed, live bug
means the "no raw bands, pure indices" isolation this whole investigation leans on is not what it
claims to be; (2) the causal story "the win came from a bugfix, not new indices" is a real
overclaim — the isolation arm used to establish it quietly includes index families that were
never in the shipped model at all; (3) the model regresses, undisclosed, on the one canola metric
the codebase's own comments call the actual operating point the project needs. None of these
make the underlying macro-F1 gain fake — the two splits move together, the test set is
genuinely clean, and the formulas are right — but they mean the report overstates confidence in
what specifically is driving the number and undersells what it costs.

## Findings, most important first

### 1. `--bands-drop-raw` doesn't fully drop raw bands — confirmed via the job's own log

`train_species.py`'s `family()` helper (lines 64-73) recovers a feature's band/index family by
checking whether the trailing token after the last underscore is a 3-digit DOY bin:

```python
parts = base.rsplit("_", 1)
return parts[0] if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 3 else base
```

`BIN_START = 90` (line 38), so the first DOY bin is the literal string `"90"` — 2 digits, not 3.
Every other bin (110, 130, ..., 330) is 3 digits and matches fine. For the 90-bin, `family()`
falls through to `else: return base`, so e.g. `family("blue_90")` returns `"blue_90"`, not
`"blue"`. `--bands-drop-raw` (main(), line 517) drops columns via
`raw_cols = [c for c in f.columns if family(c) in BANDS]` — since `"blue_90"` is not literally in
`BANDS`, it survives the drop. This affects all 10 raw bands at the 90-bin (`blue_90`,
`green_90`, `red_90`, `red_edge_1_90`, `red_edge_2_90`, `red_edge_3_90`, `nir_1_90`, `nir_2_90`,
`swir_2_90`, `swir_3_90`).

I confirmed this directly two ways, not just by reading the code:

- Ran `family()` from the actual module against every raw-band bin/summary column
  (`/g/data/xe2/John/geospatenv/bin/python`): of 170 raw-band-derived columns, exactly 10 escape
  the drop, and they are exactly the 90-bin columns listed above.
- The production job's own stdout log
  (`/scratch/xe2/cb8590/paddock-species-logs/177827011.gadi-pbs.OU`) prints
  `--bands-drop-raw: dropped 160 raw-band columns, 333 derived-index columns remain` — 160, not
  170. The script's own accounting proves 10 raw bands leaked through, in the same run that
  produced the headline 0.892/0.884 numbers.

The feature-count arithmetic confirms this is systemic, not a one-off: every "indices only, no
raw bands" arm across both rounds of `INDEX_ARCHITECTURE_SWEEP.md` matches
`(n_index_families × 17) + 10` exactly — 146 = 8×17+10, 231 = 13×17+10, 248 = 14×17+10,
333 = 19×17+10. Every one of those arms silently carries 10 raw Sentinel-2 reflectance columns
it was documented not to have.

**Materiality.** Likely small but genuinely unquantified. The one mitigating fact: the leak is
identical (same 10 columns) in every `--bands-drop-raw` arm, so isolation *deltas* computed
between two such arms (e.g. orig8 vs. orig8+Sharma6) are not confounded by it — it cancels in the
subtraction. What it does invalidate is the literal claim, repeated in the CLI help text
(`train_species.py:450-456`), `INDEX_ARCHITECTURE_SWEEP.md`, and
`GROUP3_MODEL_19index_VALIDATION.md`, that these arms isolate "derived indices only" / "no raw
bands." Neither report's Caveats section mentions it. A permutation-importance side effect of the
same bug is visible directly in the published table: `vci_90` appears as its own line
(`+0.0031`) alongside `vci` (`+0.0172`) in `GROUP3_MODEL_19index.md`'s importance table — that is
this exact bug, live, fragmenting the family-importance sums for every one of the 19 index
families (not just raw bands) by whatever their 90-bin feature contributes. This makes `ndre2`'s
reported dominance (+0.1077) a slight *understatement*, not an inflation, so it doesn't undercut
the headline importance finding — but it does mean the "Where the signal is" table is not an
accurate summation as published.

### 2. The "bugfix, not new indices" causal story is a real overclaim

`INDEX_ARCHITECTURE_SWEEP.md`'s round-1 headline states: "the win came from a bugfix, not the new
indices... `bands_orig8_hgb` at 306 features has *no* new indices and still gets the best temporal
score of the whole sweep, 0.848." This is presented against the same table's `shipped baseline`
row (0.821/0.821 temporal/spatial, 51 features).

I checked what the shipped baseline and the "orig8" arm actually contain. The shipped baseline
(`train_group3_reviewed.pbs`) is invoked with `--indices "$D/samgeo/ts_v2/*_SENSITIVE.csv"`.
I read the header of one of those files directly:

```
TrialCode,crop,sow,time,...,ndvi_pad_median,ndvi_pad_mean,ndvi_win_mean,
ndyi_pad_median,ndyi_pad_mean,ndyi_win_mean,cfi_pad_median,cfi_pad_mean,cfi_win_mean
```

The shipped model's `value_cols` (columns ending `_pad_median`) are **exactly three**: `ndvi`,
`ndyi`, `cfi` — nothing else. It has never seen NDRE, NDWI, NBR, PSRI, or swir_ratio in any form.

The "orig8, bugfix only, no new indices" isolation arm, by contrast, runs on `--bands` input and
computes all 8 of `INDEX_NAMES`'s original entries (`ndvi, ndyi, cfi, ndre, ndwi, nbr, psri,
swir_ratio`) via `add_indices()`. Five of those eight (`ndre`, `ndwi`, `nbr`, `psri`,
`swir_ratio`) are **new information the shipped model never had**, not a bugfix to something
already present. In the permutation-importance table for the final 19-index model, two of these
never-shipped families rank #2 (`nbr`, +0.0365) and #6 (`swir_ratio`, +0.0226) — ahead of most of
Sharma et al.'s own indices. On top of that, even the 3 indices the "orig8" arm shares in name
with the shipped model (`ndvi`, `ndyi`, `cfi`) are computed differently: the shipped model takes
the median of the per-pixel index (`ndvi_pad_median` etc., straight from the extraction-time
index files); the bands-pathway arm computes the index from the median of the raw bands instead.
`train_species.py`'s own comment at line 505-509 flags this as a real difference for a non-linear
index like CFI ("the median of per-pixel CFI... is not CFI computed from the median reflectance
... the most likely reason a 10-band model scored WORSE on canola than a 3-index one").

So the round-1 "bugfix, not new indices" framing, read against the actual shipped baseline (which
is the comparator used in the same results table), bundles at least three distinct changes under
one label: (a) the genuine summary-stats bugfix, (b) five new-to-the-shipped-model index families,
and (c) a changed computation pathway for the three original indices. Nobody has cleanly isolated
how much of the ~0.02-0.03 macro-F1 gap this arm shows over the true shipped baseline is (a) vs.
(b)+(c). This matters for trusting the final number: the marginal "Sharma6 vs orig8" and
"all19 vs orig8+Sharma6" isolations in round 2 are internally clean (they hold the bands pathway
and the orig-8 set fixed, so Sharma's contribution really is isolated *relative to that
intermediate baseline*) — but the chain from the **actual shipped 3-index model** to the
candidate has never been decomposed the same way. No experiment in either report adds Sharma's 6
indices directly on top of the shipped model's own 3 indices computed the shipped model's own way
(per-pixel-index-then-median, not band-median-then-index) — the one comparison that would
cleanly answer "how much of the total gain is Sharma et al. 2026's indices, full stop."

### 3. Unflagged regression on the canola-detection operating point

`train_species.py`'s own comment (`evaluate()`, line 284) describes "canola at a 5% false-positive
budget" as "the operating point Stage 2 actually needs" — this is the number the codebase treats
as the actual decision-relevant metric for canola, distinct from macro F1. Comparing the two
source reports directly:

| metric | shipped (`GROUP3_reviewed.md`) | candidate (`GROUP3_MODEL_19index.md`) | delta |
|---|---|---|---|
| canola detected @ 5% FPR | 89.0% | 85.8% | **-3.2 pp** |
| average precision (canola) | 0.944 | 0.939 | **-0.005** |
| ROC AUC (canola) | 0.965 | 0.967 | +0.002 |

Two of the three canola-specific threshold-free metrics get *worse* in the candidate model. This
is consistent with the per-class breakdown: Canola F1 is essentially flat (0.88→0.89 temporal,
0.88→0.88 spatial; precision actually drops 0.94→0.92 temporal, 0.91→0.90 spatial) while nearly
all of the macro-F1 gain comes from Legume (F1 0.69→0.83/0.81) and Cereal (F1 0.90→0.96/0.96).

`GROUP3_MODEL_19index_VALIDATION.md` reports every other headline metric (macro F1, balanced
accuracy, per-class P/R/F1) as an explicit shipped-vs-candidate table with a `delta` column. For
canola-at-5%-FPR / average precision / ROC AUC — the one place two of three numbers move the
wrong way — the report states only the candidate's own numbers (line 41: "Canola detected at 5%
FPR: 85.8%... average precision 0.939, ROC AUC 0.967") with no comparison table and no delta. The
Caveats section (lines 105-124) does not mention this regression at all, despite covering four
other, smaller caveats. Both raw numbers are genuine — they trace correctly to
`GROUP3_reviewed.md` and `GROUP3_MODEL_19index.md`, nothing is fabricated — but the selective
framing (comparison tables for every metric that improved, none for the one that didn't) is a
real honesty gap for a report whose stated purpose is "so every number below is directly
comparable to the shipped baseline" (line 25-26).

### 4. Formulas and band mapping: confirmed correct

Checked every formula in `add_indices()` (`train_species.py:97-164`, current working-tree diff)
against the user-supplied Sharma et al. 2026 Table S2 ground truth:

| index | code (train_species.py) | matches Table S2 |
|---|---|---|
| SAVI | `1.5*(nir-red)/(nir+red+0.5)` (line 133-135) | yes, exact |
| NDRE2 | `safe_ratio(nir, re2)` = `(nir-re2)/(nir+re2)` (line 142) | yes, exact |
| Vi2 | `(re2+red)-(re1-blue)` (line 144) | yes, exact |
| Vi3 | `(re1+green)-(blue+red)` (line 145) | yes, exact |
| VDVI | `(2*green-red-blue)/(2*green+red+blue)` (line 147-149) | yes, exact |
| VCI | `(r_ng-red)**2 / (r_ng-blue)**2`, `r_ng=0.38*(nir-green)+green` (line 150-155) | yes, exact |
| EVI2_sharma | `2.4*(nir-red)/(nir+red+1.0)` (line 161-163) | yes, exact |

`safe_ratio(a, b)` (line 76-78) is `(a-b)/(a+b)` with a NaN guard — confirmed by reading the
function body, and independently by hand-computing NDRE2 from 5 raw rows of
`bands_ts/A_045_SENSITIVE.csv` (reflectance values in [0,1], red_edge bands in the expected
increasing order re1 < re2 < re3) and matching the formula's output.

The single most likely failure mode flagged for this review — a red-edge band mixup — is ruled
out. `extract_paddock.py:56-57` defines `ALL_BANDS` with `nbart_red_edge_1/2/3` in that order
(DEA's Collection-3 naming for Sentinel-2 bands 5/6/7, i.e. 705/740/783 nm), and line 344
(`cols[b.replace("nbart_", "")] = ...`) is what produces the `red_edge_1/2/3` column names
`train_species.py` reads. `add_indices()` correctly binds `re2 = g("red_edge_2")` (line 108) and
uses it only for NDRE2 and Vi2 — never swapped with `re1` or `re3`.

### 5. Test-set and spatial-split integrity: confirmed clean

Verified directly against the underlying (sensitive, not reproduced here) CSVs rather than
trusting the reports' own header lines:

- `testkeep_temporal_SENSITIVE.csv`: exactly 543 unique TrialCodes, 100% with `Year` in
  {2023, 2024}, 0 rows with `Year <= 2022`. It is a full subset of
  `keep_reviewed_SENSITIVE.csv` (0 TrialCodes missing).
- `keep_reviewed_SENSITIVE.csv`: 2,194 rows total, splitting cleanly into 1,651 (`Year<=2022`)
  + 543 (`Year>=2023`) — matching the "train 1651, test 543" line in both `GROUP3_reviewed.md`
  and `GROUP3_MODEL_19index.md` exactly.
- `train_group3_reviewed.pbs` and `train_group3_19index.pbs` point at byte-identical
  `--keep`/`--test-keep` paths (`keep_reviewed_SENSITIVE.csv` / `testkeep_temporal_SENSITIVE.csv`)
  and the same `--labeled` file. This really is an apples-to-apples comparison on row identity —
  the two arms differ only in feature construction (`--indices` vs. `--bands --bands-drop-raw`),
  not in which rows get trained or scored.
- `meta.site` (the `GroupKFold` grouping column) has **zero nulls** across all 4,479 rows in
  `nvt_trials_labeled.csv` (249 unique real site values), so the code's
  `.fillna(meta.index.to_series())` fallback (line 659) never fires. The "spatial" split is
  genuinely grouped on real site identity for every row, not silently degraded to a per-row
  split.

### 6. Seed-stability caveat: legitimate, not a stretch

The Caveats section leans on "HGB's `random_state` has zero measured effect below 10,000 training
rows" (`EVAL_SEED_STABILITY.md`). That file only tests the 51-feature shipped baseline at 1,651
rows, not the 333-feature candidate — so applying it here is an extrapolation across feature
count, though not across row count (both are far under 10,000). The underlying mechanism is
real and independently documented across at least five other reports in this repo
(`MODEL_UNCERTAINTY.md:45`, `SENTINEL1_VALUE.md:79`, `S1_MODEL.md:57`, `YIELD_MODEL.md:97`,
`PROJ_NOTES.md:13`): `HistGradientBoostingClassifier`'s default `early_stopping="auto"` only
engages its (seed-dependent) internal train/validation split above 10,000 samples; below that,
the fit is deterministic regardless of feature count, since HGB has no row-subsampling parameter
of its own. The claim is sound.

### 7. Minor: a small numerical slip, in the conservative direction

`GROUP3_MODEL_19index_VALIDATION.md:99-103` states "six of the top twelve are `ndre2`." Recounting
the actual list (`ndre2_230, vi3_250, cfi__amp, ndre2_250, vci__peak_doy, ndre2__amp, ndre2_270,
ndyi__amp, ndre2__p90, ndre2_110, nbr_230, ndre2_210`) gives **seven** `ndre2` entries, not six.
This understates rather than inflates the claim, so it doesn't affect the conclusion, but it's a
transcription slip worth fixing.

### 8. Reproducibility: confirmed, exit 0, numbers match the log

`train_group3_19index.pbs` → job `177827011.gadi-pbs`. Its `.OU` log confirms `Exit Status: 0`,
`Walltime Used: 00:03:42` (report says "3m42s"), and prints the exact macro F1/balanced accuracy
pairs (0.892/0.898 temporal, 0.884/0.888 spatial) that appear in `GROUP3_MODEL_19index.md` and
`GROUP3_MODEL_19index_VALIDATION.md`. Nothing here is fabricated or retyped incorrectly — the
same log is what exposed finding #1 above ("dropped 160 raw-band columns" instead of 170).

## What a human should check next

1. **Fix `family()`'s bin-suffix check** (allow 2-4 digit bins, not exactly 3) and re-run the
   19-index arm to confirm `--bands-drop-raw` actually drops all 170 raw-band columns, then
   re-verify the 333-feature headline number still holds (it will shift slightly — check the
   direction and size of the shift before trusting the current figures as final).
2. **Run the one experiment that would actually answer "how much of the gain is Sharma et al.
   2026's indices, full stop"**: add Sharma's 6 indices directly on top of the shipped model's
   own 3 indices, computed the shipped model's own way (`--indices` pathway, per-pixel-index-
   then-median), rather than only ever testing them stacked on top of the bands-pathway "orig8"
   arm that already contains 5 never-shipped index families and a different CFI computation.
3. **Decide explicitly whether the canola-detection-at-5%-FPR regression (89.0%→85.8%) is
   acceptable** before shipping this as a replacement for the current model — this needs a
   decision from whoever owns the canola map deliverable, not a default "macro F1 went up so
   ship it."
4. **Bootstrap the spatial 5-fold split** (currently a single partition, flagged as not-yet-done
   in the candidate report's own Caveats) and re-run seed stability specifically on the
   333-feature/19-index configuration rather than relying on the 51-feature baseline's
   seed-stability result.
