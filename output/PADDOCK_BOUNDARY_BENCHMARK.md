# Paddock boundary source benchmark — SAMGeo vs Fields of The World

**Date:** 2026-08-07 · **Status:** complete, recommendation below · **Code:** `src/paddocks/`

## Why this exists

The Stage-2 heatmap diagnosis found two causes for the weaker CFI contrast in our figures
versus the colleague's PaddockTS heatmap. Cause 1 (pooling seasons and regions) is fixed.
**Cause 2 is that we average a 200 m window centred on the trial GPS, which marks a paddock
*corner*** — so the window pulls in neighbouring paddocks, roads and trees. The fix is to
take the median over the *actual paddock polygon*. This benchmark picks the boundary source.

Two arms, same test site (a Yorke Peninsula SA canola site, 2020, three co-located trials):

| | **Fields of The World (FTW)** | **SAMGeo** |
|---|---|---|
| What it is | Global model-predicted field boundaries, GeoParquet on Source Cooperative | SAM `vit_h` run on a 3-band Fourier-of-NDWI composite, per PaddockTS |
| How obtained | Targeted range-read, login node (`ftw_fetch.py`) | GPU PBS job per AOI (`samgeo_segment.py`) |
| Cost | **0 SU** (network read only) | **2.51 SU** per 0.1° AOI |
| Season-specific | No — single global snapshot (2024/25) | Yes — segments the year you ask for |

## Result: SAMGeo wins, clearly

Figure: `…/derived/figures/boundary_comparison_arth_SENSITIVE.png` (on scratch — plots site
coordinates, so it stays out of git).

The trial paddock is unambiguous in the imagery: a bright flowering-canola field bounded by
roads on two sides.

- **SAMGeo traces exactly that paddock — 57.3 ha.** It follows the roads, excludes the bare
  patch on the north-west corner, and stops at the treed southern boundary.
- **FTW merges it with the two dark paddocks to the south — 339.1 ha**, i.e. three distinct
  fields in one polygon. A median over that polygon would mix three different crops, which
  is worse than the 200 m window we are trying to replace.

Polygon populations in the same 3 km AOI around the site:

| Source | polygons | of those ≥1 ha | median ha (≥1 ha) | p90 | max | slivers <1 ha |
|---|---|---|---|---|---|---|
| SAMGeo | 25 | 25 | 32.6 | 65.0 | 76.9 | **0 (0 %)** |
| FTW | 63 | 13 | 64.2 | 230.6 | 339.1 | **50 (79 %)** |

FTW here is 50 junk slivers plus 13 over-merged blobs. Its size distribution is not a
paddock distribution; SAMGeo's is (Australian broadacre paddocks are tens of hectares).

Across the wider 4-site FTW check, the merging is systematic, not a one-off: containing
polygons of 130 ha, 339 ha (×2) and **1,307 ha**. FTW found a containing polygon for 4/4
sites and SAMGeo for 3/3, so *containment rate* does not separate them — **polygon size
does**, and it is the thing that matters.

This is consistent with what the FTW arm already knew: the FTW *benchmark* (human-labelled)
excludes Australia. Only the model-predicted global product covers us, and this is what its
predictions look like here.

## Bug found and fixed: the shape filter rejected every polygon

The first SAMGeo run reported `638 raw -> 0 after filter`. Cause, and it is a trap worth
remembering:

PaddockTS computes `area_ha = pol.area/1000` — in an equal-area CRS `.area` is m², so
hectares are `/10000` and their value is **10× too large**. Its shape filter,
`perim_area = length/area_ha <= 30`, is calibrated against that inflated area and is **not
dimensionless**. We had already corrected the area to `/10000`; that alone multiplies the
ratio by 10, so a typical 33 ha paddock scores ~76 against a threshold of 30 and *everything*
is discarded. Correcting one half of a coupled pair silently emptied the output.

Replaced with a **dimensionless compactness, `P/√A`** (square = 4.0, circle = 3.54), default
threshold 8.0. On the 638 raw polygons the rejections are now: 462 below 1 ha, 55 above
compactness 8, 1 above 1500 ha ⇒ **159 kept, median 33.1 ha (p10 3.3, p90 83.1)**.

## Caveat that constrains everything downstream

**The trial point sits 17–24 m from the paddock edge — about two Sentinel-2 pixels.** That is
the corner-GPS problem restated, and it does not go away by switching boundary source:

1. **Containment is marginal.** A 1–2 pixel georeferencing or segmentation error flips a site
   from "inside paddock A" to "inside paddock B". Extraction needs an explicit fallback
   (nearest polygon within a tolerance) and should record which rule fired, per trial.
2. ~~**Paddock-median assumes the whole paddock grows the trial's crop.**~~ **Largely resolved
   by NVT protocol** (user, 2026-08-07): the NVT guidelines require the paddock surrounding a
   trial to be the *same crop type*, sown within roughly two weeks of the trial. So the
   assumption is a design property of the trial network, not a hopeful guess — which is what
   makes paddock-median the right estimator here rather than a risky one.
   Provenance: stated by the user from the NVT guideline document (not yet in hand). A public
   GRDC source corroborates the *timing* half — trial managers "aim to sow at the same time as
   the grower for the paddock used or within days" — but I could not find the same-crop-type
   clause in publicly searchable material, so cite the guideline itself before it goes in a
   paper. We can also verify it ourselves from the data once the CFI canola signature is
   clean: a paddock whose median CFI matches its trial's label is direct evidence.
3. Polygons should be **eroded by ~1 pixel** before taking the median, or edge pixels mixed
   with road and tree will re-import the contamination we are removing.

## Cost at scale — this is the binding constraint

Measured: 2.51 SU per 0.1° AOI (≈11 km square, 72 scenes, V100). Stage breakdown:

| stage | time | needs GPU? |
|---|---|---|
| pre-segment (datacube load + Fourier) | 133 s | no |
| SAM model load | 49 s | yes, fixed per job |
| segment | 29 s | yes |
| polygonise | 3 s | no |
| **total** | **214 s** | GPU utilisation **21 %** |

Segmentation is season-specific, so an AOI must be re-run per year. Distinct 0.1° AOI×year
cells needed: **1,362** for the canola+wheat working set (2,761 trials), 1,900 for all crops.

- At the benchmarked config: **~3,419 SU** for canola+wheat — **34 % of the entire 10 KSU
  project allocation**, spent on preprocessing. Not acceptable as-is.
- Note the memory request (90 GB, 11.7 GB used) is *not* the waste it looks like: `gpuvolta`
  bills 12 CPUs per GPU whatever you ask for, so 1 GPU is the smallest bookable unit and
  trimming memory saves nothing.

### Measured: the split pipeline costs 0.113 SU/AOI, a 22× reduction

Superseding the earlier ~0.4 SU/AOI projection — the real number is better. Four arms, same
eight ~3 km AOIs, 2026-08-07:

| arm | queue | resources | walltime | **SU** | **SU/AOI** |
|---|---|---|---|---|---|
| **stage 1 pre-segment** | normal | **1 CPU / 4 GB** | 4:52 | **0.16** | **0.020** |
| stage 1 pre-segment | normal | 4 CPU / 16 GB | 5:06 | 0.68 | 0.085 |
| **stage 2 SAM** | **gpuvolta** | 12 CPU / 1 V100 | 1:14 | **0.74** | **0.093** |
| stage 2 SAM | normal | 4 CPU / 16 GB (CPU-only) | 46:03 | 6.14 | 0.77 |

**Winner: 1 CPU / 4 GB for stage 1, GPU for stage 2 ⇒ 0.113 SU/AOI.**

Two findings, and they point in opposite directions:

1. **Stage 1: the user's "many small jobs" heuristic holds exactly.** Quadrupling CPUs cost
   4.3× more and was *not* faster (5:06 vs 4:52; CPU-time used was 1:53 vs 2:00 — the same
   work either way). Pre-segment is I/O-bound on the datacube at ~25 % CPU, so extra cores
   are billed and idle. 1 CPU / 4 GB is the cheapest bookable unit on `normal`
   (charge = max(ncpus, mem/4GB) × 2 SU/hr) and it wins outright.
2. **Stage 2: the heuristic inverts — the GPU is 8.3× *cheaper*.** SAM is genuinely
   compute-bound: 2.8 s/AOI on a V100 against 339 s on 4 CPUs, a **121× speedup** that easily
   repays `gpuvolta`'s 4.5× higher hourly rate. Polygon outputs were equivalent
   between devices (identical `n_raw`, `n_keep`, `median_ha`), so this is a pure cost choice.

So the right split is *not* "put everything on small CPU jobs" — it is to separate the
I/O-bound half from the compute-bound half and apply the opposite rule to each. That is only
visible once the stages are split; the monolithic job hid a 121× GPU speedup behind a
datacube read that was 62 % of its runtime.

Smaller effects, now that the big ones are measured:
- The 49 s model load in the original run was cold-cache; warm it is **9.4 s**, so
  amortising it matters less than expected. Batching still helps — fixed job overhead
  (imports, torch init) is ~40 s, so 40 AOIs/job beats 8.
- Segment time scales with area as expected: 2.8 s for a 3 km AOI vs 29 s for the 11 km one.
- Stage-1 memory: the 4 GB arm reported 4.0 GB used (i.e. it filled the cgroup) while the
  16 GB arm reported 9.5 GB. Both exited 0 with identical output, so 4 GB suffices for ~3 km
  AOIs — but going to 8 GB would *double* the stage-1 charge under `max(ncpus, mem/4GB)`, so
  don't raise it reflexively. Re-check if AOIs get much bigger.

### Revised cost at scale

| | AOIs | old (2.51 SU, 11 km box) | **new (0.113 SU, sized AOI)** |
|---|---|---|---|
| canola + wheat | 1,362 | 3,419 SU (34 % of allocation) | **154 SU (1.5 %)** |
| all crops | 1,900 | 4,769 SU | **215 SU** |

Two independent gains multiply: **10.9× less area** (sizing AOIs to their trials instead of a
fixed 0.1° box — the median cell holds just 2 trials, so most of that box was segmented for
nothing) and the **queue split** above. Segmentation is no longer a budget question.

## Recommendation

1. **Use SAMGeo, not FTW.** FTW's Australian predictions merge adjacent paddocks badly enough
   to defeat the purpose.
2. **Run the two-stage split**: `submit_paddocks.sh` — 1 CPU / 4 GB `normal` jobs for
   pre-segment, batched `gpuvolta` jobs for SAM. **0.113 SU/AOI, measured.**
3. **Cost is no longer the blocker** — 154 SU for the whole canola+wheat set, 1.5 % of the
   allocation, down from 3,419 SU. The decision is now purely about whether paddock-median
   *works*, not whether it is affordable.
4. **Validate on the pilot before the bulk run.** 42 AOIs / 203 trials (123 canola, 80 wheat)
   across 2018–2023, every AOI containing both crops. Paddock-median must out-separate the
   200 m window on the same trials, judged by paired bootstrap — not by whichever J is larger.
5. Keep the FTW fetcher — it cost 0 SU and is a useful independent cross-check on any site
   where SAMGeo's polygon looks wrong.

## Files

- `src/paddocks/make_aois.py` — group trials into AOIs sized to their trials (the 10.9× gain)
- `src/paddocks/samgeo_segment.py` — `presegment` / `segment` / `all` subcommands
- `src/paddocks/presegment.pbs`, `sam_segment.pbs`, `submit_paddocks.sh` — two-stage submission
- `src/paddocks/ftw_fetch.py` — FTW targeted download (login node; needs internet)
- `src/paddocks/check_polygons.py` — per-site containment check at the 200 m window
- `src/paddocks/compare_boundaries.py` — wide-AOI side-by-side comparison (this report's figure)
- `src/paddocks/extract_paddock.py` — paired paddock-median + window CFI extraction
- `src/paddocks/compare_estimators.py` — paired-bootstrap comparison of the two estimators
- Outputs on scratch: `…/derived/samgeo/`, `…/derived/ftw/`, `…/derived/figures/{samgeo,ftw}/`
