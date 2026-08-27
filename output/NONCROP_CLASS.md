# The model calls pasture "Cereal" with 0.999 confidence

Written 2026-08-10. Produces the number `NATIONAL_INFERENCE_BENCHMARK.md` §5 said did not
exist: *"the model will confidently label pasture paddocks as Cereal — and there is no number
in this project that bounds how often, because no such paddock has ever been in a test set."*

There is one now, on 125 paddocks NLUM says are grazing.

**Every single one is classified as a crop, 79 % of them as Cereal, at a median confidence of
0.999 against 1.000 on real crop paddocks. Confidence carries no usable signal about whether
the input is a crop at all.** §5's cheapest proposed fix — open-set rejection by thresholding
the softmax — is dead, and the measurement kills it rather than merely doubting it.

---

## 1. Where the negatives came from

`nlum_negatives.py` samples 3 km tiles from the NLUM 2021 probability surfaces where grazing
is high (`>= 0.50`) and crop is low (`<= 0.05`), stratified by how much cropping is in the
surrounding ~25 km:

- **`hard`** (109 paddocks) — pasture *inside cropping country*. Same soils, climate, rainfall
  and paddock geometry as the crops; only the cover differs. These are the ones that matter.
- **`easy`** (16) — rangeland, crop-free neighbourhood. A control: if the model cannot reject
  these, the hard ones are hopeless.

Sampling grazing nationally without the stratification would have landed in the Nullarbor and
the Barkly and measured a far easier problem than deployment poses.

30 tiles were segmented, 128 polygons survived a 5–1000 ha filter, and **125 extracted cleanly
— every one matched by `contains`**, so no polygon is standing in for a different one. Features
come from `extract_paddock.py` unchanged, so a fourth class cannot be separable on extraction
artefacts rather than on cover.

## 2. The result

Scored by the `<=2022` model — the same model, splits and fixed test set as every arm in
`output/arms/`. The grazing paddocks are **scored, never trained on**, so nothing about the
existing results moves. Crop rows are the 2023-24 test set, so both sides are equally
out-of-sample.

| predicted | indices model | bands model |
|---|---|---|
| Cereal | 99 (79.2 %) | 116 (92.8 %) |
| Legume | 23 (18.4 %) | 7 (5.6 %) |
| Canola | 3 (2.4 %) | 2 (1.6 %) |
| **abstained** | **0** | **0** |

**Confidence is useless here, and worse than useless — it is inverted.**

| | indices | bands |
|---|---|---|
| median max-prob, pasture | 0.999 | 0.998 |
| median max-prob, real crops | 1.000 | 1.000 |
| mean max-prob, `hard` (pasture among crops) | 0.947 | 0.950 |
| mean max-prob, **`easy` (rangeland)** | **0.968** | **0.975** |

The model is **more** confident on rangeland — the ground least like a crop — than on pasture
sitting in a cropping district. A softmax over three crop classes is not measuring "is this a
crop", and its confidence ordering does not track similarity to the training distribution.

## 3. Why open-set rejection cannot save it

§5 option 3 was to threshold the max class probability. The cost curve, indices model:

| max-prob threshold | pasture rejected | crop paddocks discarded | accuracy on what is kept |
|---|---|---|---|
| 0.50 | 0.8 % | 0.4 % | 85.0 % |
| 0.70 | 6.4 % | 5.3 % | 86.4 % |
| 0.90 | 15.2 % | 13.8 % | 89.5 % |
| 0.95 | 20.8 % | 17.5 % | 91.1 % |

**Every threshold discards almost exactly as many real crop paddocks as pasture paddocks it
rejects.** At 0.95 the trade is 20.8 % of pasture for 17.5 % of the crop map — and 79 % of
pasture still gets through. That is not a weak filter, it is no filter: rejection is
approximately independent of whether the input is a crop. The bands model is the same picture.

## 4. What the negatives actually look like, and the honest caveat

The `hard` stratum is genuinely hard, and part of it is probably cropped.

| | median NDVI amplitude | median roughness | amp / roughness |
|---|---|---|---|
| reviewed crop paddocks (n=3,219) | 0.712 | 0.075 | 9.43 |
| grazing `hard` (n=109) | 0.470 | 0.050 | 9.32 |
| grazing `easy` (n=16) | 0.195 | 0.014 | 13.75 |

**The `hard` candidates are not noise.** Their amplitude-to-roughness ratio is
indistinguishable from real crops (9.32 vs 9.43), so their seasonal curves are genuine signal,
not a small-paddock artefact — which was the obvious alternative explanation, since they are
6–17 ha against the `easy` stratum's 600–900 ha, and it is ruled out.

They sit **at about the 10th percentile of the crop amplitude distribution** (crop p10 = 0.457,
hard median = 0.470). So they are systematically weaker than crops but overlap the weak-crop
tail, and **54 % of them exceed the crop p10**. Some fraction of the `hard` stratum is
genuinely cropped land, and the number in §2 is inflated by however large that fraction is.

**Raising the NLUM grazing threshold does not fix this.** Among the `hard` candidates,
`graz_prob` is uncorrelated with crop-like phenology (**r = 0.051**); even at `graz_prob`
0.8–1.0, 65 % are crop-like. What does correlate is neighbourhood cropping intensity
(r = 0.376) — the axis that defines the stratum.

**The reason is structural, and it is the finding to carry forward: NLUM's grazing probability
is a long-run land-use prior, not a statement about what grew in 2021.** Paddocks rotate
between pasture and crop, so a genuinely "grazing" paddock is cropped in some years. No
threshold on a static surface recovers the year.

This is why **§5 option 2 — "add a fourth class from unlabelled paddocks, accept NLUM's labels"
— is not viable as written.** Its stated caveat was to accept NLUM labels rather than ground
truth; this measures that cost and it is roughly a coin flip in exactly the districts where
the class matters.

**And the tempting fix is a trap.** Filtering candidates by NDVI amplitude before training
would make the negatives separable by construction, on the very signal the classifier uses. It
would manufacture a good number the same way the discarded `0.823 vs 0.716` comparison in
`NEXT_STEPS.md` §2 did, by making the exam easier rather than the model better. Do not do it.

## 5. What survives

- **The `easy`/rangeland negatives are trustworthy** — 6 % crop-like, clearly separable
  phenology — and the model still classifies 100 % of them as crops with *higher* confidence
  than it manages on anything else. The failure is not confined to ambiguous ground.
- **§2's headline stands regardless of contamination.** Even if every one of the 59 crop-like
  `hard` candidates were truly a crop, the remaining 66 paddocks were still classified as crops
  at 0 % abstention, and the 16 rangeland paddocks alone settle the confidence question.
- **The review is now load-bearing, not optional.** `GRAZING_REVIEW.gpkg` (128 polygons,
  `verdict`/`note` columns) plus `grazing_panels/*.png` — each candidate's NDVI and CFI against
  the 10–90 % crop envelopes — and `grazing_ranked.csv`, sorted so the crop-like ones surface
  first. Verdicts turn a provisional bound into a real one.

## 6. Recommendation

1. **Drop §5 option 3 (open-set rejection).** Measured, not suspected: §3.
2. **§5 option 2 needs real labels, not NLUM's.** The prior cannot distinguish a pasture
   paddock from a cropped one within a cropping district, and cannot in principle, being a
   static long-run surface (§4).
3. **§5 option 1 (reject on the NLUM prior, label the rest "not assessed") is now the
   realistic default** — with the honest framing that it makes the product a refinement of
   NLUM rather than an independent map. §5 already called that out as weakening the paper's
   claim, and this report is the evidence that the weakening is unavoidable rather than a
   choice.
4. **Do the review** (§5), then re-run this with verdicts to convert the bound.
5. **Nothing here changes any existing model result** — the negatives were only ever scored.

## 7. Exact commands

```bash
cd src/paddocks
D=/scratch/xe2/cb8590/paddock-species-data/derived
PY=/g/data/xe2/John/geospatenv/bin/python
NLUM=/g/data/xe2/cb8590/paddock-species-data/raw/NLUM_v7_250_AgProbabilitySurfaces_2020_21_geo_package_20241128

# 1. sample tiles, stratified hard/easy   2. segment   3. review package   4. pseudo-trials
$PY nlum_negatives.py tiles --nlum-dir $NLUM --n 30 --out $D/samgeo/aois_grazing.csv
qsub -v AOIS=$D/samgeo/aois_grazing.csv,OUTDIR=$D/samgeo/grazing presegment.pbs
qsub -v AOIS=$D/samgeo/aois_grazing.csv,OUTDIR=$D/samgeo/grazing sam_segment.pbs
$PY nlum_negatives.py package --polydir $D/samgeo/grazing --aois $D/samgeo/aois_grazing.csv \
    --out $D/figures/GRAZING_REVIEW.gpkg
$PY nlum_negatives.py sites --gpkg $D/figures/GRAZING_REVIEW.gpkg --out $D/grazing_sites.csv

# 5. features, via the SAME extractor as the crop paddocks (--no-upgrade: each polygon is its own)
qsub -v SITES=$D/grazing_sites.csv,POLYDIR=$D/samgeo/grazing,\
OUT=$D/samgeo/ts_grazing.csv,EXTRA_ARGS="--no-upgrade" extract_paddock.pbs

# 6. review panels: NDVI/CFI against the crop envelopes, plus a ranked shortlist
$PY grazing_panels.py --ts $D/samgeo/ts_grazing.csv --sites $D/grazing_sites.csv \
    --crop-ts "$D/samgeo/ts_v2/*_SENSITIVE.csv" --labeled $D/nvt_trials_labeled.csv \
    --reviewed $D/reviewed_trials_SENSITIVE.csv --outdir $D/figures/grazing_panels

# 7. the number
qsub noncrop_check.pbs        # -> output/arms/NONCROP_indices.md, NONCROP_bands.md
```

After the review, add `--verdict <good...>` to the `sites` call to keep only confirmed
non-crop polygons, then re-run steps 5 and 7.
