# Overnight session: phenology-gate fix (ship it) and boundary-matcher (don't, yet)

One clear, validated win and one investigation that made real progress without reaching a
shippable state. Recommendation for tomorrow's national 9-year run: **ship the phenology-gate
two-pass fix, leave the tile grid as-is.**

## 1. Phenology-gate two-pass fix — validated win, ship it

`PHENOLOGY_GATE.md` had two untried fixes for the shape gate's canola recall shortfall, each
locally validated on trial data but never run through the regional ABS check. Ran both tonight
(reusing the existing 9-year Riverina segmentation — no re-segmentation cost):

| config | area ratio | canola share error | note |
|---|---|---|---|
| baseline (amplitude only, current default) | 1.59 | 9.4 pts | ships today |
| shape gate (single-pass) | 1.00 | 11.4 pts | fixes area, breaks canola |
| **two-pass (Canola exempt from shape gate)** | **1.19** | **5.2 pts** | **best on both** |
| loosened senescence threshold | 1.18 | 6.7 pts | close second |

Two-pass gating is the only config that improves *both* numbers at once relative to baseline —
it's not even close on canola accuracy (5.2 vs 9.4 vs 11.4 points of error). Full detail in
`ABS_COMPARISON_100km_shapegate_twopass.md` / `_loose.md`.

**Found and fixed one real bug along the way**: the "loose" gate's model bundle saved its recall
under `held_out_recall_baseline` instead of the `held_out_recall` key `predict_tile.py` reads —
crashed all 30 of its first-attempt jobs before writing anything. This candidate had literally
never been run through `predict_tile.py` before tonight; PHENOLOGY_GATE.md's numbers all came
from a separate local-recall script. Fixed with a two-key fallback (`predict_tile.py`), not a
re-fit — see the fix's own comment.

**Recommendation**: ship two-pass gating (`--crop-gate-amp 0.35 --crop-gate-shape
phenology_gate.joblib --shape-gate-skip-classes Canola`) as the default for tomorrow's run. It
costs **zero additional SU** — it only changes which `predict_tile.py` flags are passed, not the
segmentation, and predict is going to run regardless.

## 2. Boundary-grid matching — real progress, not a shippable state

Picking up from last night's pilot, which found `--spatial-match` (needed for any offset grid)
corrupted 30.7% of the dataset via transitive containment matches. Four rounds of safeguards
tonight, each validated at full pilot scale (1.1-1.5 SU, ~35-45 min per full-scale run):

| version | safeguards | n_cells>=4 corruption | year 2024's own median n_years / IoU |
|---|---|---|---|
| v1 (last night) | none | 30.7% (worst: 208 cells, 18,159 rows) | 5 / 0.523 |
| v2 | +max-area(300ha) +max-diag(3000m) +max-ratio(8x) +max-group-ratio(8x) +cross-cell-only-if-**touching** | 0.96% | **1 / 0.269 (broken)** |
| v3 | same 4 caps, dropped the touching-based restriction | 8.44% | 5 / 0.525 |
| v4 | same 4 caps + **same-grid-restrict** (year-PAIR based, not anchor-based) | 6.84% | 5 / 0.525 |

**v2's flaw, found and explained**: restricting cross-cell search to anchors flagged
`touches_grid=True` assumes "same cell label" is a safe fallback for every other anchor — true
for two years that share a grid, false the moment one of them is the offset year (a cell label
means nothing across a shifted grid, touching or not). That's why v2's corruption looks great but
year 2024 is nearly unmatched to anything.

**v4's more principled fix, and what it revealed**: restrict same-cell search only when the two
years being compared actually share a grid (checked directly from each year's cell `r0c0`
coordinates). A clean diagnostic — re-running with the offset year removed entirely — confirms
this works exactly as designed: **zero cross-cell corruption among the 8 fixed years compared
against each other** (`n_cells` is 1 for every one of 40,832 identities). So the technique is
sound for same-grid matching. It also surfaced a smaller, separate finding: even confined to one
cell, `--min-containment` can still merge multiple distinct same-cell paddocks across years via
one year's larger (sub-300ha) blob — a pre-existing risk in the containment metric itself, not
something the offset grid caused, and not live today since production doesn't use
`--min-containment` at all yet.

**What's still unsolved**: every safeguard combination tested trades off match quality for the
offset year against overall corruption. Loosening the restriction (v3/v4) partially recovers
2024's match quality (n_years 1->5) but corruption rises with it (0.96%->6.84-8.44%); neither
reaches a state that's both clean AND functional. The full 6.84-8.44% is entirely attributable to
year 2024's cross-grid comparisons (confirmed directly: every corrupted group in v4 involves
2024, zero are fixed-years-only).

**Recommendation: do not include the offset grid in tomorrow's national run.**
1. It isn't validated to a safe state after four iterations — shipping it risks a *worse*
   consensus than the status quo, not a better one, and the failure mode (silently merged
   distinct paddocks) is harder to notice than the boundary-split problem it targets.
2. It isn't free like the phenology-gate fix: an offset grid needs 9 NEW national grids
   re-segmented from scratch, at the same ~59,600 SU scale as the run itself (below) — a second
   full national run's worth of compute for an unresolved fix.
3. The boundary-split problem it targets affects ~7-10% of polygons; the phenology-gate fix
   already shipping tonight addresses a whole-map problem (the 1.35-1.77x area over-call).

All new `polygon_stability.py`/`map_regions.py` flags remain opt-in and verified byte-identical
to production when omitted, so none of tonight's work is at risk of leaking into a plain
production run by accident.

## 3. Cost of tomorrow's planned national 9-year run

`NATIONAL_2024_RUN.md`: one year, national scale, cost **6,622.6 SU** (62% SAM segmentation,
gpuvolta's 36 SU/hr). Nine years at the same scale: **~59,600 SU** — about **29% of the entire
204 KSU quarterly grant**, before accounting for any re-run overhead like 2024's own 216.8 SU gap
re-run. This is the same whether or not the phenology-gate fix ships (predict-stage only, no
segmentation change); it does NOT include a 9-year consensus/stability layer at national scale,
which doesn't exist as infrastructure yet and would be a separate, later undertaking if wanted.
Flagging this clearly before the run, per the standing SU-minimization guidance — not a reason to
hold off, just worth seeing the number before committing.

## Everything produced tonight

- Code (all opt-in, all verified byte-identical to production when their flags are omitted):
  `predict_tile.py` (bug fix), `polygon_stability.py` (`--spatial-match`, `--aois`,
  `--max-match-area-ha`, `--max-group-diag-m`, `--max-containment-ratio`,
  `--max-group-area-ratio`, `--same-grid-restrict`), `map_regions.py` (`--offset-seed`).
- Reports: `ABS_COMPARISON_100km_shapegate_twopass.md`, `_loose.md`, `OFFSET_GRID_PILOT.md`
  (v1), `_V2.md`, `_V3.md`, `_V4.md`, this summary.
- Nothing committed to git — all changes sit in the working tree for review.
