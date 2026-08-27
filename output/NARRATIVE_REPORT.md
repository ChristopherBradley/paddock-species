# Narrative Report — Paddock-scale crop species mapping for Australia

Written 2026-08-27, consolidating everything from `BRIEF.md` through the national 2024 map, the
yield model, and the phenology-gate experiment. This is the first document in the project that
reads as one story rather than a sequence of dated findings — later documents (a paper draft, if
one is written) should treat this as their primary source, alongside the individual reports it
cites.

## 1. What was proposed, and what was actually built

**The brief** (`BRIEF.md`, 24 Jul): map cropland species across Australia at 10 m from Sentinel-2
(+ Sentinel-1 if the literature supported it), using GRDC/NVT trial-site records as ground truth,
as an intermediate product for a later tree-shelter-productivity project. Target venue *Remote
Sensing of Environment*.

**The idea selected after literature review** (`LIT_REVIEW_REPORT.md`, `IDEA_REPORT.md`, same
day): fine-tune a WorldCereal-style foundation model (Presto or AlphaEarth) on GRDC labels for a
full **10-species** classifier (wheat, barley, canola, chickpea, faba bean, field pea, lentil,
lupin, oat, triticale) — the "methodological gap" the literature review scored highest (0.87),
because no published work reaches species-level resolution on field-verified Australian ground
truth. The idea report flagged every candidate experiment as "needs pilot validation on NCI
Gadi" and stopped there; `novelty-check`, `idea-review`, `refine-research` and `experiment-design`
were never run.

**What was actually built, from early August onward, diverged substantially:**

| planned | built | why |
|---|---|---|
| CSIRO ePaddocks boundaries | SAMGeo (Meta's Segment Anything, via PaddockTS) | ePaddocks was never adopted; SAMGeo segmentation became the core geometry source and its own methods contribution (segmentability-as-mask, `PRESENCE_ONLY_LABELS.md`) |
| Presto/AlphaEarth fine-tuning | Hand-built spectral indices (NDVI/NDYI/CFI, DOY-binned) + gradient boosting | Presto was tried (`presto_embed.py`) and measured *worse* than hand-built features (macro F1 0.775 vs 0.821, `REVIEWED_MODEL.md`) — a genuine negative result for the original plan's backbone idea |
| 10-species classification | 3 groups: Canola / Cereal / Legume | 9-class macro F1 was 0.38 against 3-group's 0.78-0.82 (memory log, "TARGET IS NOW 3 GROUPS"); species-level was not reachable at this label volume |
| A confusability study (the idea report's stated deliverable) | A deployed national wall-to-wall map + yield attribute + a presence-gate methodology fight | The project became product-shaped rather than paper-shaped somewhere around the co-located-trial-label discovery (early August) and never reverted |

None of this is a failure of the original plan — Presto losing to hand-built features and 9-class
losing to 3-group are *findings*, not process breakdowns — but a paper built from this project
would be about a different, more empirical set of questions than the one `IDEA_REPORT.md`
proposed, and should be planned as such rather than forced into the original framing.

## 2. Methodology, as shipped

1. **Segmentation.** SAMGeo, stock `vit_h` checkpoint, default parameters (re-tuning was tried and
   ruled out, commit `8283a8d`). Segmentability itself is used as a crop-presence mask: polygons
   are kept only at paddock scale (5-300 ha + compactness ≤ 8), which keeps 77.9% of known crop
   paddocks and rejects 65% of pasture in cropping country — a free, non-spectral signal that
   costs 22% of real crop paddocks.
2. **Labels.** The paddock polygon surrounding each NVT trial site, labelled with that trial's
   sown crop. **The central label-quality finding**: NVT runs multiple trials in one field that
   SAM segments as a single polygon — 69.7% of training trials share their paddock with another
   trial, 31.8% with a *different* crop. Collapsing 9 species to 3 broad groups resolves 69% of
   those conflicts (co-located trials are usually the same agronomic group); hand-reviewing the
   trial-to-polygon matches added a further +0.019 macro F1 on top (`REVIEWED_MODEL.md`).
3. **Classification.** `HistGradientBoostingClassifier` on 51 paddock-median spectral features
   (DOY-binned NDVI/NDYI/CFI), 3 classes. Validated both temporally (train ≤2022, test 2023-24)
   and spatially (5-fold GroupKFold on site) — **macro F1 0.821 / 0.823**, canola detected at
   89.0% recall at a 5% false-positive rate. Per-class precision: Canola 0.94/0.91, Cereal
   0.89/0.89, Legume 0.65/0.68 (temporal/spatial) — Legume is the floor, cereal leaking into it.
4. **Presence gate.** A segmentable paddock is only classified if its NDVI amplitude (p90-p10)
   clears 0.35, a threshold fitted presence-only on the 3,439 NVT trials (91.6% recall);
   otherwise it abstains with a reason. This replaced an earlier 4-class design that added
   AgriWebb farmer-recorded "Grazing" paddocks as a negative class — retired after finding 78.5%
   of "hard stratum" grazing paddocks pass the same crop-presence test as known crops
   (`PRESENCE_ONLY_LABELS.md`): the negative class was absorbing real crop phenology and pulling
   genuine crops into itself at test time (the source of a 39.4% "known crops called Grazing"
   error). AgriWebb-derived code and data were subsequently removed from this repository entirely
   ahead of a wider publish (see git history, commit `2b1f4a2`).
5. **Yield (Cereal only).** Same 51-feature contract, `HistGradientBoostingRegressor`, Wheat +
   Barley + Oat pooled to match the classifier's own `Cereal` class (not just Wheat+Barley — Oat
   would otherwise be scored by a model that never saw one). Spatial-transfer RMSE 1.21 t/ha
   (30.4% of the 3.97 t/ha median), against 1.10-1.14 t/ha (26-29%) for wheat or barley scored
   separately — the measured cost of pooling. Calibrated to ABS commercial yield with a single
   multiplicative factor (0.6248, fit on 2022, checked +3.1% to +18.1% on 2023-24) — both the raw
   (NVT-equivalent) and calibrated columns ship, never only the calibrated one. Canola yield is
   not shipped: optical-only R² (0.27) does not beat guessing the year and state (0.29).

## 3. The national 2024 map, and what it says about itself

`NATIONAL_2024_RUN.md`. 99,465 tiles, **1,346,582 polygons** (2.8 GB), scored against ABS sown-
area statistics in 132 censused SA2s — a source with no connection to NVT or the training
pipeline. **The map calls 1.47x as much land "crop" as ABS says was sown**, concentrated almost
entirely in Cereal (+23.2 points) and Legume (+10.8), essentially never Canola (-0.3). Once the
over-call is divided out arithmetically, mapped canola share matches ABS almost exactly (13.1%
against a diluted 13.4%) — **this is a crop-presence problem, not a canola classification
problem**, a finding reproduced independently on both the 102 km Riverina region (ratio 1.59) and
the full continent (ratio 1.47, same class signature).

Legume is the largest error that is *not* explained by the over-call: 18.4% mapped against ABS
8.7%, with argmax and mean-probability agreeing to within 0.5 points (ruling out a decision-rule
fix). This is untouched by any work in this report and is the most promising open thread.

## 4. The presence-gate fix that was tried, and rejected

`PHENOLOGY_GATE.md`. A gate on the season's *shape* — a real green-up, ending in a real
senescence — rather than just its amplitude, on the theory that sown-but-not-harvested pasture
can green up as hard as a crop but rarely senesces like one. Built as two variants: an oracle
version anchored on each NVT trial's true sowing/harvest date (92.2% held-out recall, not
deployable — no polygon on a wall-to-wall map has a known date), and a deployable version that
detects its own peak instead (91.9% recall, almost no cost relative to oracle).

**Regional test, 100 km x 9 years, 120 SU:** the area ratio moved exactly where hoped, 1.59 to
1.00. But per-crop recall (checked only after the regional result made it worth checking) showed
canola-specific presence recall of just 83.4%, against cereal's 95.1% and legume's 95.5% — canola
senesces less sharply post-flowering by this metric, so one shared threshold screens out
disproportionately more of it. Mapped canola share did not move at all (still 23.4% vs ABS
36.2%). **Verdict: the gate trades an area-inflation problem for a canola-undercount problem, not
a smaller problem, for the map's most important species.** Not adopted. Two untried refinements
are recorded for whoever picks this up: a looser senescence threshold, or two-pass gating that
leaves canola on the amplitude gate.

## 5. Sentinel-1 — measured, not bought

`SENTINEL1_VALUE.md`, `S1_MODEL.md`. +0.03 macro F1 on NVT trial paddocks (temporal transfer;
spatial gain within noise), concentrated entirely in Legume (F1 0.69 → 0.75). The case weakened
once the area-inflation finding landed: most of the mapped legume over-prediction turned out to be
the presence-gate problem (§3), not classifier confusion, so S1's real-world benefit is likely
smaller than +0.03. Never purchased or run at wall-to-wall scale.

## 6. Decision and current status

As of `NEXT_STEPS.md` (rewritten alongside this report): **the pipeline is shipped and frozen** —
segmentation, 3-class classifier, amplitude gate, calibrated Cereal yield, exactly as used for the
2024 national run — with the 1.47x area-inflation limitation documented and accepted rather than
blocking further work. The next planned step is running the remaining years (2017-2023, 2025)
with this identical configuration.

## 7. What a paper from this project would actually be about

Not the originally-proposed foundation-model confusability study. The defensible empirical
contributions, as the work actually stands:
- A label-conflict finding specific to trial-network ground truth (co-located NVT trials sharing
  one segmented polygon) and a resolution (group collapsing + hand review), likely generalisable
  to any crop-classification project using point-based agronomic trial networks as labels.
- A negative result for foundation-model embeddings (Presto) against hand-built spectral features
  on this label volume and class structure.
- A demonstrated failure mode for absence-labelled negative classes built from presence-only
  farmer records (the AgriWebb Grazing retirement), and a presence-only alternative
  (segmentability-as-mask + phenology gate) validated at national scale against an independent
  official statistic — ABS sown area — rather than a held-out label split.
- A quantified trade-off between two different gate designs (amplitude vs. phenology-shape) on
  the *same* independent validation, including the specific mechanism (differential per-crop
  recall) that made the more sophisticated gate the wrong choice — a useful cautionary result in
  its own right.
- A measured, honestly-caveated NVT-trial-to-commercial-yield offset, using ABS production data as
  the calibration reference at national scale.

## 8. Evidence map

| claim in this report | source document |
|---|---|
| Original idea and gap analysis | `LIT_REVIEW_REPORT.md`, `IDEA_REPORT.md` |
| Label-conflict finding | `memory/MEMORY.md` ("CO-LOCATED TRIALS..."), `REVIEWED_MODEL.md` |
| Classifier accuracy | `REVIEWED_MODEL.md`, `output/arms/GROUP3_reviewed.md` |
| Presence gate design and AgriWebb retirement | `PRESENCE_ONLY_LABELS.md` |
| National run and ABS validation | `NATIONAL_2024_RUN.md`, `ABS_COMPARISON_NATIONAL.md`, `ABS_COMPARISON_100km.md` |
| Yield model and calibration | `YIELD_FEASIBILITY.md`, `YIELD_cereal_pooled.md`, `YIELD_CALIBRATION.md` |
| Phenology-shape gate, oracle vs deployable, regional test | `PHENOLOGY_GATE.md`, `ABS_COMPARISON_100km_shapegate.md` |
| Sentinel-1 | `SENTINEL1_VALUE.md`, `S1_MODEL.md` |
| 9-year geometric stability | `POLYGON_STABILITY.md`, `CONSENSUS_LAYER.md` |
| Current decision and status | `NEXT_STEPS.md` |
