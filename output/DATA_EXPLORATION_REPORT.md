# NVT Ground-Truth Exploration — Site Cleanliness

**Purpose:** Before committing to the `IDEA_REPORT.md` directions, quantify how much of the
NVT trial network is usable as clean, single-species ground truth for training/validating a
Sentinel-2 crop-type model. Source: `2017-2024 NVT Yield and Grain Quality.xlsx`
(sheets: Cereals, Pulses, Canola). **All per-site outputs are NDA-sensitive — aggregates only here.**

## 1. Dataset shape

| | count |
|---|---|
| Rows (trial × variety) | 87,919 |
| Unique trials (`TrialCode`) | 4,502 |
| Abandoned trials (excluded) | 12 |
| Missing/invalid GPS (excluded) | 11 |
| **Usable trials (valid GPS, not abandoned)** | **4,479** |
| Distinct exact-GPS coordinates | 3,698 |
| Years covered | 2017–2024 (fairly even, 474–611/yr) |
| `SowingDate` / `HarvestDate` present | 4,479 / 4,479 (100%) — good for Sentinel windowing |

Each trial GPS is the **corner** of a small multi-plot/multi-variety block; one trial = one species
(confirmed: 0 `TrialCode`s span >1 species).

Species (trial-level): Wheat 1,593 · Canola 1,185 · Barley 630 · Chickpea 227 · Oat 210 ·
Field Pea 200 · Lupin 190 · Faba Bean 142 · Lentil 125.

## 2. Two cleanliness lenses

**(a) Exact-corner pixel** — group by exact GPS:
- 3,452 / 3,698 (93%) coordinates host a **single** species across all years.
- 246 host multiple species (rotation across years, or shared host-farm coordinate).

**(b) Surrounding-paddock contamination** — the concern that NVT co-locates *different-crop*
trials at one host farm, so a 10 m Sentinel pixel (or the paddock) may straddle multiple crops.
For each trial we computed the haversine distance to the nearest **different-crop trial in the
same year**:

| No different-crop trial within… | trials isolated | % |
|---|---|---|
| 50 m | 3,058 | 68% |
| 100 m | 2,448 | 55% |
| **200 m** | **2,163** | **48%** |
| 300 m | 2,113 | 47% |
| 1000 m | 1,995 | 45% |

The distribution is **bimodal**: a trial is either solo-in-a-paddock (nearest different crop >1 km)
or packed into a mixed NVT cluster (<50 m). The curve is nearly flat past 300 m, so the exact
threshold in 200–500 m barely matters — ~2,100 trials are cleanly isolated either way.

## 3. Clean trials by species (200 m isolation)

| Species | clean / total | % clean |
|---|---|---|
| Canola | 900 / 1,179 | **76%** |
| Wheat | 730 / 1,582 | 46% |
| Lupin | 127 / 189 | 67% |
| Oat | 67 / 210 | 32% |
| Chickpea | 90 / 224 | 40% |
| Barley | 115 / 629 | 18% |
| Field Pea | 57 / 199 | 29% |
| Faba Bean | 64 / 142 | 45% |
| Lentil | 13 / 125 | 10% |

**Canola and Wheat are both the largest and (for canola) the cleanest** — together 1,630 clean
trials. Barley is heavily co-located with wheat (18% clean), and pulses are mostly clustered.

Figures: `output/figures/nvt_contamination_distance.png`,
`output/figures/nvt_clean_by_crop.png`. (Site map with coordinates is written only to the
gitignored `data/derived/`.)

## 4. Implications

- A defensible **clean training/validation set of ~2,100 trial-years** exists without any imagery —
  enough for a supervised crop-type / canola-detection model.
- The set skews **Canola + Wheat**, which supports the canola-flowering-index angle and a
  binary/few-class formulation over a 9-class one. Pulses are too contaminated to treat as reliable
  paddock labels without per-site imagery vetting.
- Isolation (NVT-only) is a **necessary but not sufficient** filter: it removes co-located mixing but
  cannot confirm the *surrounding paddock actually grew the trial crop* (could be fallow/pasture/
  a non-NVT crop). That confirmation needs Stage 2.

## 5. Recommended two-stage labelling pipeline

1. **Stage 1 — NVT isolation filter (done, local):** keep trials with no different-crop trial within
   200 m same year → ~2,163 candidate clean sites. Cheap, no imagery.
2. **Stage 2 — Sentinel-2 phenology confirmation (gadi/DEA):** for each candidate, extract an
   NDVI (and canola-flowering-band) time series for the corner pixel **and** a small surrounding
   window over the sow→harvest window; confirm the signal matches the expected crop phenology
   (green-up/senescence timing; canola's yellow-flower spectral spike). Flag mismatches as
   likely fallow/rotation/other and drop or downweight them. Runs where the datacube lives.

## 6. Caveats

- Trial GPS is the plot **corner**, not centroid — the paddock extends in an unknown direction;
  Stage 2 should sample a window, not a single pixel.
- "Same crop as surrounding paddock" is an assumption that holds best for solo trials; Stage 2 tests it.
- 2020/21 is the NLUM reference year — those trial-years can be cross-checked against NLUM
  probability surfaces as an independent label sanity check.
