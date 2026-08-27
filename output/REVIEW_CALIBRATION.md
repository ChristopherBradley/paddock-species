# Trial→paddock match review — calibration

Reviewed 60 of 96 sampled trials from 3 reviewer file(s).

**36 sampled trials have no verdict** — treat their strata as under-sampled.

## Verdict distribution

| verdict | n | share |
|---|---|---|
| `good` | 39 | 65% |
| `no_paddock` | 12 | 20% |
| `trial_plot` | 4 | 7% |
| `unsure` | 3 | 5% |
| `wrong_polygon` | 2 | 3% |

## Usable rate per stratum (`good` or `trial_plot`)

| stratum | reviewed | usable | rate | 95% CI | population | est. bad |
|---|---|---|---|---|---|---|
| `bigger_neighbour` | 12 | 10 | 83% | [55%, 95%] | 266 | 44 |
| `clean` | 12 | 11 | 92% | [65%, 99%] | 887 | 74 |
| `edge_close` | 12 | 11 | 92% | [65%, 99%] | 657 | 55 |
| `none` | 12 | 0 | 0% | [0%, 24%] | 657 | 657 |
| `not_contained` | 12 | 11 | 92% | [65%, 99%] | 1100 | 92 |

Extrapolated unusable matches across the dataset: **~922**. Strata overlap (a trial can carry several flags), so this double-counts and is an upper bound, not a total.

## Reviewer agreement (overlap n=24)

- exact verdict match: **92%**
- agree on usable vs not: **96%** (the decision that actually matters downstream)

Disagreements (2). Per-trial shortlist (TrialCode, stratum, verdicts, notes) is site-level —
kept only in the gitignored `REVIEW_CALIBRATION_SENSITIVE.md`, not here.

## Trials judged unusable (17) — shortlist to verify

Same as above: the per-trial table (TrialCode + reviewer note) lives only in
`REVIEW_CALIBRATION_SENSITIVE.md`. Aggregate picture: all 12 reviewed `none`-stratum trials
were unusable and 10 of 12 notes report a crop visibly present at the trial dot anyway — see
the diagnosis below.

## Why 657 trials (24 %) have no paddock — diagnosed, and the obvious fix is WRONG

Reviewers were unanimous on the `none` stratum: 0/12 usable, and **10 of 12 notes say a
cropped field is plainly visible at the trial dot**. So these are not barren or non-cropped
sites. Chased it down with geometry only (no imagery):

1. Every one of their AOIs *does* contain polygons — none is a segmentation blank.
   Distance from trial to nearest kept polygon: median **161 m** (24 % within 75 m).
2. Against the RAW, unfiltered segmentation, **97 % (58/60) have a polygon that CONTAINS the
   trial point.** So the polygon exists and the **filter removed it** — 98 % of them by the
   compactness rule (`P/sqrt(A) > 8`), 12 % also over the 1500 ha cap.

The tempting fix is to relax compactness. **Do not.** Those recovered polygons have median
area **632 ha** (p90 1,902 ha) and median compactness **12.8** — they are not paddocks, they
are large amorphous regions where SAM failed to resolve individual fields and merged many
into one blob. Admitting them would reproduce exactly the Fields of The World failure this
project rejected: a median taken across several different crops.

**So the filter is behaving correctly and the real defect is upstream — SAM under-segments in
these ~24 % of locations.** Genuine options, in order of cost:

1. **Hybrid fallback (recommended, free).** These trials already have 200 m window CFI from
   Stage 2. Use paddock median where a real paddock exists, window mean where it does not.
   Nothing is lost relative to today; 76 % of trials get the upgrade.
2. **Re-segment the affected AOIs** with different SAM settings (finer `points_per_side`,
   or a different pre-segment composite). Costs ~0.11 SU/AOI, so a few tens of SU — cheap,
   but unproven and needs its own benchmark.
3. Accept the loss. Only sensible if 1 and 2 both fail.

**Lesson for the record:** "the filter is too strict" was the natural read of the first
result and it was wrong. Checking *what* the filter had removed — before relaxing it — is
what caught it. A parameter change that looked like it would recover 657 trials would in fact
have injected 632-hectare multi-crop blobs into the training labels.
