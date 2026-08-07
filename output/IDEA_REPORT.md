# Research Idea Report

**Direction**: Fine-tune a WorldCereal-style geospatial foundation model (Presto and/or AlphaEarth Foundations) on Australian GRDC trial-site ground truth to produce a species-level (not binary) crop classification map of Australia at 10 m resolution throughout — Gap #1 from `output/LIT_REVIEW_REPORT.md`, the only gap selected for this project.
**Generated**: 2026-07-24
**Ideas evaluated**: 12 generated (brainstormed by an opus subagent, Codex/GPT-5.4 MCP not configured in this environment) → 10 survived first-pass filtering → 0 piloted (see note below) → 10 recommended, ranked and grouped into one coherent research program (all sit inside Gap #1, not competing separate directions)

**Note on Phase 5 (pilot experiments):** this project has no local GPU (Intel Iris Plus only, per `CLAUDE.md`) and NCI Gadi is a PBS batch queue, not an interactive GPU host suited to the skill's default "launch a 30–90 min pilot and watch it" pattern. Per the skill's own fallback rule, all ideas below are flagged **"needs pilot validation on NCI Gadi"** rather than actually launched — running real pilots now, before `/experiment-design-pipeline` sizes them properly, would risk spending SU budget and Claude quota on unvalidated job configurations. This should happen in `/deploy-experiment`, benchmarked small-first per the SU-minimization note in `CLAUDE.md`.

## Landscape Summary

The closest existing work (Sharma et al. 2026, WA; Al-Shammari et al. 2024, Murray-Darling Basin — both read in full, see `output/LIT_REVIEW_REPORT.md`) already gets >90% accuracy on 2–6 crop classes in Australia, but neither is continent-wide, neither reaches species-level resolution beyond cereals+canola, and — critically — neither trains on genuinely field-verified ground truth (both use another system's model output or opportunistic harvester data as "reference labels"). No foundation-model generalizability study to date includes Australia as one of its regions. This leaves a real, defensible gap: a foundation-model-based, continent-scale, ~10-species classifier trained on real field-verified trial data, held to a strict 10 m resolution because of the downstream tree-shelter use case.

A quick novelty pass (WebSearch, 2026-07-24) found adjacent-but-distinct work worth citing rather than worrying about as prior art: Presto has been shown to help under-represented crop classes in non-Australian, ≤8-class benchmarks (label-efficiency gains, e.g. +0.13 F1 for a 1.3%-prevalence class); a 2025 paper fine-tunes Prithvi-EO-2.0 for canola *yield regression* at 30 m (FARM); and a 2025 preprint benchmarks foundation models specifically for cereal (not full-species) mapping. None of these overlap with a 10-species, 10 m, field-verified-ground-truth, continent-wide design.

## Recommended Ideas (ranked)

All ten ideas below compose into a single research program under Gap #1 — they are facets of one paper's experiment plan, not competing directions. Idea 3 is the backbone; the rest are ablations, secondary results, or necessary methodology.

### Idea 1 (backbone): National 10-species confusability map via foundation-model fine-tuning
- **Hypothesis**: Cereal species (wheat/barley/oat/triticale) separate well at 10 m from Sentinel-2 time series; confusion is dominated by within-legume pairs (chickpea/faba bean/field pea/lentil/lupin) and driven by genuine phenological overlap, not model capacity.
- **Minimum experiment**: Fine-tune Presto on all ~10 GRDC classes nationally; analyze the resulting confusion matrix and embedding-space distances between species.
- **Expected outcome**: A concrete, publishable map of *which* species pairs are fundamentally hard vs. easy at 10 m — directly useful for prioritizing which species this project (and the downstream tree-shelter project) can actually resolve.
- **Novelty**: 8/10 — closest work (Sharma et al. 2026) tops out at 6 classes with 3 real crop species; no continent-wide, full-GRDC-roster equivalent exists.
- **Feasibility**: One national Presto fine-tune run; Presto is designed to be cheap (fraction of ViT-scale parameters) — should fit comfortably inside the ~10 KSU budget, but size the first run small and benchmark per `CLAUDE.md`'s SU-minimization note before scaling.
- **Risk**: LOW.
- **Contribution type**: Empirical finding (the confusability structure itself is the result).
- **Pilot result**: needs pilot validation on NCI Gadi.
- **Reviewer's likely objection**: "Isn't this just applying Presto to a new country?" — Answer: the value is in what the confusion structure reveals (which species need better features / more labels / an entirely different sensor), not the application itself; also the ground-truth quality (field-verified vs. pseudo-labels in both precedents) is a genuine methodological improvement.
- **Why we should do this**: It's the direct, most defensible reading of Gap #1, and every other idea below builds on its output.

### Idea 2: Minimum labelled-sample budget per species (learning-curve / label efficiency)
- **Hypothesis**: Presto/AlphaEarth-based classifiers saturate at a surprisingly small number of GRDC labels per species (hundreds, not thousands) — the key result enabling continent-wide species mapping from a necessarily finite trial network.
- **Minimum experiment**: Subsample GRDC labels at 5–6 fractions per species, fine-tune Presto at each, plot the saturation curve.
- **Expected outcome**: A practical "how much ground truth do you actually need" answer, directly relevant to anyone with limited field data (not just this project).
- **Novelty**: 6/10 — Presto label-efficiency has been shown before (non-Australian, ≤8-class, no legumes) — this extends it to a legume-heavy 10-species, field-verified-label setting, which is a real but incremental novelty gain, not a from-scratch result.
- **Feasibility**: Many small, cheap PBS jobs — this is the single best-fitting idea for the "many small jobs beat few large jobs" SU hypothesis in `CLAUDE.md`; ideal as an early benchmarking exercise regardless of which other ideas proceed.
- **Risk**: LOW.
- **Contribution type**: Empirical finding.
- **Pilot result**: needs pilot validation on NCI Gadi.
- **Reviewer's likely objection**: "This has been shown for other crops already." — Answer: legumes are the specific case where label efficiency is least established and most needed, given they're the hardest classes per Idea 1.
- **Why we should do this**: Directly informs how much of the GRDC dataset is actually necessary to use per species, and doubles as the SU-budget benchmarking `CLAUDE.md` already asks for.

### Idea 3: Trial-point-to-paddock label propagation as a methods contribution
- **Hypothesis**: Constraining GRDC trial points to CSIRO ePaddocks polygons, plus a within-paddock spectral-homogeneity filter, recovers materially cleaner training labels than naive point-buffering — directly addressing the brief's own noted ambiguity (multi-species trial sites).
- **Minimum experiment**: Build point-buffer, paddock-constrained, and homogeneity-filtered label sets from the same GRDC points + ePaddocks; feed each into an identical Presto run; compare downstream accuracy.
- **Expected outcome**: A defensible, reusable labelling protocol — likely a required methods section for any of the other ideas, not an optional extra.
- **Novelty**: 7/10 — no existing paper combines ePaddocks with trial-point ambiguity resolution this way.
- **Feasibility**: Geometry work in GEE/GIS is cheap; only the final comparison needs a model run.
- **Risk**: LOW.
- **Contribution type**: New method.
- **Pilot result**: needs pilot validation on NCI Gadi (geometry stage doesn't need one).
- **Reviewer's likely objection**: "How do you know the homogeneity filter isn't just removing hard/informative examples?" — worth pre-registering a check for this.
- **Why we should do this**: This is close to a required preprocessing step regardless of which other idea is pursued — worth doing early.

### Idea 4: Spatial vs. temporal transfer for a foundation model
- **Hypothesis**: Al-Shammari et al. (2024) found spatial transfer (leave-one-site-out) outperformed temporal transfer (leave-one-season-out) for an RF on 2 classes. A pretrained foundation model may narrow or reverse this gap, since pretraining already encodes some cross-region invariance.
- **Minimum experiment**: Leave-one-region-out vs. leave-one-year-out CV on GRDC data with Presto fine-tuning.
- **Expected outcome**: Either confirms the RF-era finding still holds for FMs (useful negative result) or shows FM pretraining changes the picture (more interesting positive result) — both publishable.
- **Novelty**: 7/10 — directly extends a finding from a paper this project already engaged with in the lit review.
- **Feasibility**: A handful of small PBS jobs, same infrastructure as Idea 1.
- **Risk**: MEDIUM.
- **Contribution type**: Empirical finding.
- **Pilot result**: needs pilot validation on NCI Gadi.
- **Reviewer's likely objection**: "Only 2 crop classes in the original study vs. 10 here — is the comparison fair?" — frame as an extension/stress-test, not a strict replication.
- **Why we should do this**: Directly shapes how this project should design its own train/test splits — needed regardless of publication value.

### Idea 5: Sentinel-1's marginal value under the strict 10 m, no-MODIS constraint
- **Hypothesis**: Since MODIS-based features are ruled out (10 m constraint), Sentinel-1 radar recovers most of the classification skill MODIS provided in Al-Shammari's cloud-limited regions, but its national marginal gain over Sentinel-2 alone is small — justifying an S2-primary design without over-engineering S1 integration.
- **Minimum experiment**: Presto fine-tune with S2-only vs. S2+S1, stratified by a cloud-frequency zone map.
- **Expected outcome**: A direct, evidence-based answer to the brief's own open question ("Sentinel-1 if literature supports the benefit").
- **Novelty**: 6/10 — the S1-marginal-value question is well-studied generally, but not under this specific 10 m/no-MODIS/species-level Australian setting.
- **Feasibility**: Two national runs, same infra as Idea 1.
- **Risk**: MEDIUM.
- **Contribution type**: Empirical finding.
- **Pilot result**: needs pilot validation on NCI Gadi.
- **Reviewer's likely objection**: Minimal — this is a natural ablation reviewers will expect regardless.
- **Why we should do this**: Answers a question the brief already poses explicitly; low risk of being "uninteresting" either way.

### Idea 6: AlphaEarth embeddings vs. Presto fine-tuning — which wins, and why
- **Hypothesis**: AlphaEarth's annual-compression embeddings will match Presto on cereals but lose noticeably on legumes, because annual summarization discards the intra-season phenological signal that separates legume species — a concrete, publishable failure mode of embedding-field models for fine-grained agriculture.
- **Minimum experiment**: Extract AlphaEarth embeddings at GRDC points (GEE, no training needed) vs. a Presto fine-tune on the same points; compare per-species accuracy.
- **Expected outcome**: A model-choice justification for the rest of the project, plus a standalone methods-comparison finding.
- **Novelty**: 7/10 — AlphaEarth is very recent (July 2025); no fine-grained agricultural species comparison against Presto has been published yet.
- **Feasibility**: AlphaEarth side is nearly free (precomputed embeddings, GEE extraction only); Presto side reuses Idea 1's run.
- **Risk**: MEDIUM.
- **Contribution type**: Empirical finding / diagnostic.
- **Pilot result**: needs pilot validation on NCI Gadi (AlphaEarth extraction needs no pilot at all — GEE-only).
- **Reviewer's likely objection**: "AlphaEarth wasn't designed for this task" — legitimate, but that's exactly the point of testing it.
- **Why we should do this**: Cheap, timely (AlphaEarth is brand new), and directly justifies Presto as the primary model choice if the hypothesis holds.

### Idea 7: Yield-conditioned label noise
- **Hypothesis**: Low-yielding or failed GRDC trial sites have atypical (thin-canopy) spectral signatures that inject label noise; filtering or reweighting training data by yield improves map quality — a use of the yield attribute no existing precedent can make, since neither Sharma nor Al-Shammari has yield-linked labels at this density.
- **Minimum experiment**: Stratify training by yield quantile; compare Presto accuracy with/without low-yield reweighting.
- **Expected outcome**: Either a modest but genuine accuracy improvement, or a clean negative result ("yield doesn't predict label reliability") — both worth reporting given how unique the yield-linked ground truth is.
- **Novelty**: 8/10 — this specific use of yield-as-noise-signal appears nowhere in the reviewed literature.
- **Feasibility**: Cheap — reuses Idea 1's infrastructure with a different training-sample weighting scheme.
- **Risk**: MEDIUM.
- **Contribution type**: Empirical finding / new method.
- **Pilot result**: needs pilot validation on NCI Gadi.
- **Reviewer's likely objection**: "Yield variation could be agronomic (drought, disease), not spectral-signal noise — how do you disentangle?" — worth a careful check before over-claiming.
- **Why we should do this**: Leans directly into what makes this project's dataset different from every precedent — a distinctive, hard-to-copy result.

### Idea 8: Species-specific earliest reliable classification date
- **Hypothesis**: Legumes become reliably separable much later in the season than cereals, so a single fixed "classify at date X" approach (as used by Sharma et al. for 6 classes) is suboptimal for the full GRDC species roster — species-specific decision dates materially improve in-season mapping.
- **Minimum experiment**: Fine-tune Presto on time series truncated at monthly cutoffs; plot per-species accuracy vs. cutoff date.
- **Expected outcome**: A practical in-season mapping guideline extending Sharma et al.'s single-date-window finding to the full species set.
- **Novelty**: 6/10 — directly extends an existing precedent's method to more species; the extension itself, not the technique, is the novel part.
- **Feasibility**: Several small PBS jobs, same infra as Idea 1.
- **Risk**: LOW.
- **Contribution type**: Empirical finding.
- **Pilot result**: needs pilot validation on NCI Gadi.
- **Reviewer's likely objection**: "This is basically Sharma et al. with more classes" — true, so frame as a natural but necessary extension rather than a standalone novelty claim.
- **Why we should do this**: Cheap add-on once Idea 1's national run exists; useful operational output even if not the paper's main hook.

### Idea 9: Canola flower index as an interpretability probe
- **Hypothesis**: Presto/AlphaEarth already implicitly encode the flowering signal the brief's Canola Flower Index captures; adding the index explicitly gives little accuracy gain for canola, but linear-probing the embeddings for flowering timing cleanly demonstrates the foundation model has learned phenology.
- **Minimum experiment**: Add the flower index as an extra input channel in one run; separately, linear-probe frozen embeddings against flowering date.
- **Expected outcome**: A nice interpretability side-result connecting the brief's original motivating observation (Canola Flower Index) to what the foundation model learns.
- **Novelty**: 6/10 — interpretability probes for phenology are known in ML generally, but not tied to this specific index/species.
- **Feasibility**: Cheap, reuses existing runs.
- **Risk**: MEDIUM.
- **Contribution type**: Diagnostic.
- **Pilot result**: needs pilot validation on NCI Gadi.
- **Reviewer's likely objection**: Low risk of objection — mostly a "nice to have" rather than a load-bearing result.
- **Why we should do this**: Directly ties the paper back to the brief's original motivating observation; good narrative value, low cost.

### Idea 10: WorldCereal / NLUM error audit using GRDC as an independent gold standard
- **Hypothesis**: Both WorldCereal and NLUM — validated only against pseudo-labels or sparse in-situ data — systematically misclassify legumes (chickpea/faba bean/field pea/lentil) into a generic "cereal/other" bucket, and this error is spatially structured by agro-ecological zone rather than random.
- **Minimum experiment**: Point-sample both products at GRDC lat/lons (GEE zonal extraction, no model training); build confusion matrices by species and zone.
- **Expected outcome**: A near-free motivating result for the whole paper's introduction — quantifying exactly how much better this project needs to be.
- **Novelty**: 5/10 — closer to a validation exercise than a standalone contribution ("apply X to Y"), but genuinely useful and essentially free.
- **Feasibility**: Trivial — pure data extraction, no training, negligible SU cost.
- **Risk**: LOW.
- **Contribution type**: Diagnostic.
- **Pilot result**: needs pilot validation — actually none needed, this can run today in GEE with no PBS job at all.
- **Reviewer's likely objection**: "This isn't really a contribution on its own" — correct; position it as Section 1 motivation/baseline, not a headline result.
- **Why we should do this**: Cheapest possible thing to do first — establishes the baseline this project needs to beat, before any GPU/PBS time is spent.

## Eliminated / Deferred Ideas

| Idea | Reason eliminated/deferred |
|------|-------------------|
| Pseudo-label vs. field-verified label comparison (same region as Sharma et al.) | No access to DAS's actual pseudo-label dataset to replicate the comparison fairly; NLUM could substitute but weakens the comparison's cleanliness. Revisit only if DAS data access becomes possible. |
| Public benchmark release (Fields-of-the-World-style, GRDC-derived) | **Deferred, high legal risk.** GRDC already contested publication of this same trial-network lineage once (Newman & Furbank 2021 — see `grdc-data-legal-sensitivity` memory). Any anonymization scheme would need explicit GRDC sign-off before proceeding, not just a technical anonymization design. Do not pursue without the user explicitly raising it with GRDC first. |

## Suggested Execution Order

1. **Idea 10** (WorldCereal/NLUM audit) — near-zero cost, run first, motivates the whole paper.
2. **Idea 3** (label propagation methodology) — needed as a clean preprocessing step before any model training.
3. **Idea 1** (national 10-species confusability map) — the backbone result; benchmark job size small-first per `CLAUDE.md`'s SU-minimization note.
4. **Idea 2** (label-efficiency learning curve) — cheap, many-small-jobs-friendly, doubles as further SU benchmarking.
5. **Idea 6** (AlphaEarth vs. Presto) — cheap on the AlphaEarth side, clarifies model choice for everything after.
6. **Ideas 4, 5, 7, 8, 9** — ablations/secondary results layered onto Idea 1's infrastructure once it's working, in roughly that priority order.

## Next Steps
- [ ] Run Idea 10 (GEE point-sampling only) as a first, essentially free sanity check.
- [ ] Take this report + `output/LIT_REVIEW_REPORT.md` into `/novelty-check` and/or `/idea-review` if the user wants independent/external validation before committing to `/experiment-design-pipeline`.
- [ ] Otherwise proceed straight to `/experiment-design-pipeline` (or `/experiment-design`) to turn Ideas 1–3 into a concrete, claim-driven experiment roadmap with PBS job sizing.
