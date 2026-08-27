# Where the project stands, and what to do next

Rewritten 2026-08-27 (evening), after the phenology-shape gate was tried, tested at regional
scale, and rejected. The long history is `output/archive/NEXT_STEPS_2026-08-25_full.md` and
`output/archive/NEXT_STEPS_2026-08-27_full.md`.

> **One paragraph.** The pipeline is **shipped and frozen for the remaining years**: SAMGeo
> segmentation (5-300 ha + compactness mask) → 3-class classifier (macro F1 0.821/0.823) → NDVI-
> amplitude presence gate (0.35) → Cereal yield, ABS-calibrated. The national 2024 run is complete
> and scored: it over-calls crop-present area by **1.47x** (Cereal and Legume, essentially never
> Canola), a **known, accepted, documented limitation**, not a blocker. A phenology-shape gate was
> built and tested specifically to fix that over-call — it worked (ratio 1.59 → 1.00 on the 100 km
> Riverina test) but broke canola presence recall (83.4% against a 91.6% requirement), so it is
> **not adopted**. **Decision: run the remaining years (2017-2023, 2025) with the current pipeline
> exactly as used for 2024, acknowledging the area-inflation limitation rather than blocking on
> it.**

---

## 1. The decision, stated plainly

Two ways to reduce the 1.47x area over-call were tried after the national run: a stricter NDVI-
amplitude threshold (`CONFIDENCE_FILTER.md` / `ndvi_amp` filter, applied by the reader, not baked
in) and a phenology-shape gate (`PHENOLOGY_GATE.md`, built and regionally tested this session).
The shape gate is the more principled of the two and it **worked on the metric it targeted** —
but it repaired the over-call by disproportionately rejecting real canola paddocks (83.4% presence
recall against cereal's 95.1%), which is a worse trade for a project whose founding brief named
canola the easiest and most important species. **Neither fix ships.** The map goes out permissive,
exactly as `NATIONAL_2024_RUN.md` already described it, with `ndvi_amp` and the abstain reason
attached to every polygon so a reader can filter afterward if they want the tighter, less-complete
version.

**What this means operationally:** `run_national.sh predict` is unchanged — `group3_map.joblib`,
`--crop-gate-amp 0.35`, `--max-area-ha 300`, `--yield-model cereal_yield.joblib`. No code path
defaults to `--crop-gate-shape`; it exists as an opt-in flag for anyone who wants to reproduce or
extend the rejected experiment, not as production behaviour.

## 2. The shipped pipeline

| stage | what runs | key numbers |
|---|---|---|
| Segmentation | SAMGeo (PaddockTS/John Burley's repo), stock `vit_h`, no fine-tuning | 5-300 ha + compactness ≤ 8 mask |
| Classification | 3-class gradient-boosted model, paddock-median Sentinel-2 indices | macro F1 **0.821** temporal / **0.823** spatial |
| Presence gate | NDVI amplitude ≥ 0.35, fitted presence-only on 3,439 NVT trials | 91.6% recall on that population |
| Yield (Cereal only) | `cereal_yield.joblib`, Wheat+Barley+Oat pooled | RMSE 1.21 t/ha (30.4% of median); raw + ABS-calibrated (x0.6248) columns both ship |

Full detail: `README.md` (colleague-facing summary), `NATIONAL_2024_RUN.md` (the 2024 run itself),
`REVIEWED_MODEL.md` (classifier accuracy), `YIELD_cereal_pooled.md` + `YIELD_CALIBRATION.md`
(yield).

## 3. Known, accepted limitations — read before trusting a number from this map

- **1.47x area over-call**, nationally. Excess land is labelled Cereal (+23.2 points) and Legume
  (+10.8), essentially never Canola (-0.3) — `NATIONAL_2024_RUN.md` §4. Once the over-call is
  divided out, mapped canola share matches ABS almost exactly (13.1% vs a diluted 13.4%): **this
  is a presence-gate problem, not a canola classification problem**, and both attempted fixes
  changed that trade without eliminating it (see §1).
- **Legume is the largest remaining *classification* error** distinct from the presence-gate
  issue: 18.4% mapped against ABS 8.7%, not explained by argmax/probability disagreement
  (`NATIONAL_2024_RUN.md` §4). Untouched by this round of work.
- **`unsegmented_blob` holds 37 Mha** across ~48k polygons — SAM failing to split large tracts,
  four times every other abstain reason combined. A size-aware second segmentation pass was
  never attempted.
- **2017-2018 are the two weak years** in any multi-year run: 2017 for Sentinel-2B's mid-year
  start (half revisit), 2018 for a genuine drought (lowest NDVI amplitude of any year measured,
  `POLYGON_STABILITY.md`/`NATIONAL_2024_RUN.md`). Expect lower coverage in both, and do not read
  it as a pipeline defect.
- **Yield is NVT-trial-equivalent, calibrated by a single national multiplicative factor** with
  its own measured uncertainty (checked +3.1% to +18.1% against ABS on the two check years) on
  top of the model's own RMSE (30.4% of median). Report both the raw and calibrated columns;
  never only the calibrated one.
- **No canola yield.** Optical-only canola yield (R² 0.27) does not beat guessing the year and
  state (R² 0.29) — shipping it would be worse than leaving the column blank.
- **Sentinel-1 is not used anywhere in the shipped pipeline.** Its measured classification gain
  (+0.03 macro F1, concentrated in Legume) was found to mostly overlap with the presence-gate
  problem above, not distinct crop-vs-crop confusion (`SENTINEL1_VALUE.md`), so it was never
  bought at scale.

## 4. What was tried and explicitly rejected this session

**Phenology-shape presence gate** (`PHENOLOGY_GATE.md`). Peak-anchored green-up + post-harvest-
senescence check, fit on NVT presence labels (91.9% held-out recall, deployable variant),
regionally tested on the full 100 km x 9-year Riverina run (120 SU): moved the area ratio from
1.59 to 1.00, but canola-specific presence recall was only 83.4% and mapped canola share did not
move at all. **Verdict: trades an area-inflation problem for a canola-undercount problem, not a
smaller problem.** Two untried refinements are recorded in `PHENOLOGY_GATE.md`'s own next-step
section (a looser senescence threshold; two-pass gating that leaves canola on the amplitude gate)
for whoever picks this up next — not pursued now, because the point of this round was to test the
idea honestly, not to keep tuning until a number looked good.

## 5. What to do next, in order

1. **Run the remaining years (2017-2023, 2025) with the pipeline exactly as shipped for 2024.**
   Same mask, same gate, same classifier, same yield model. No code changes needed —
   `run_national.sh` already defaults to the shipped configuration. Budget: consistent with the
   ~45 KSU already discussed for the remaining years, against the national 2024 run's actual
   6,622.6 SU (`NATIONAL_2024_RUN.md` §3) as the per-year reference point.
2. **Legume over-prediction** (§3) is the largest untouched classification error and has no
   attempted fix yet — the natural next research thread once the remaining years are mapped.
3. **`unsegmented_blob`** (§3) — a size-aware second SAM pass, never attempted.
4. Do not re-tune SAM parameters (ruled out, commit `8283a8d`).
5. If someone wants to revisit the presence gate: `PHENOLOGY_GATE.md`'s two untried refinements
   are the starting point, not a fresh design.

## 6. Where the artefacts are

| artefact | location |
|---|---|
| production models | `derived/models/group3_map.joblib`, `cereal_yield.joblib` |
| the national 2024 map | `derived/national2024/national_2024_crops.gpkg` (1,346,582 polygons), and the classified-only, publicly-styled `national_2024_crops_classified.gpkg` |
| the 100 km x 9-year Riverina validation | `derived/map100/` — baseline `pred/`, phenology-shape test `pred_shapegate/` |
| phenology-gate model (opt-in only) | `derived/models/phenology_gate.joblib` |
| reference series | `derived/abs/` |
| per-arm reports | `output/arms/` |
| the long history | `output/archive/` |

## 7. Reports, in reading order

`README.md` (colleague-facing summary) → `NATIONAL_2024_RUN.md` (the 2024 run and its ABS score)
→ `PRESENCE_ONLY_LABELS.md` (why the gate is a mask, not a class) → `PHENOLOGY_GATE.md` (the
rejected fix, and why) → `YIELD_cereal_pooled.md` + `YIELD_CALIBRATION.md` (yield) →
`POLYGON_STABILITY.md` (nine years of geometry) → `SENTINEL1_VALUE.md` (why S1 isn't shipped).
Superseded: `ABS_COMPARISON.md`, `NONCROP_CLASS.md`, `CONFIDENCE_FILTER.md` (the ndvi_amp-only
filter sweep, superseded by the shape-gate test's more complete picture).
