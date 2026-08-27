# Sentinel-1 on NCI: which project to ask for, and a draft email

Written 2026-08-25 in response to "dz56 still hasn't accepted my request — is there another way
to get Sentinel-1 at national scale?"

> **Short answer: dz56 is probably the wrong project to be asking for.** The evidence below says
> it is Geoscience Australia's InSAR *working area*, not a maintained Sentinel-1 collection. The
> project that actually holds the national Sentinel-1 archive on NCI is **`fj7`, the Copernicus
> Australasia Regional Data Hub**. Redirect the request there — and, separately, note that DEA
> has no SAR product at all, which is worth knowing before any more time goes into this.

---

## 1. What dz56 actually is

`/g/data/dz56` is world-listable from gadi even without membership, so its top level can be
inspected directly. It does not look like a data collection:

```
drwxrws---   3 fxy120 dz56   Dec 18  2019  backscatter          <- permission denied to us
drwxr-sr-x   2 fxy120 dz56   Dec 21  2019  backscatter_yamls
drwxrws---   3 jps547 dz56   Apr 26  2019  file-check-test_DELETE
drwxrws---+  4 sao547 dz56   Dec  9  2022  ga_DELETE
drwxrws---+  3 sc0554 dz56   Dec  7  2021  insar_ascending_processing_DELETE
drwxrws--- 115 mmw547 dz56   Aug 10  2021  insar_final_processing
drwxrwsrwx   5 lww554 dz56   Jul 30  2021  MEXICO_DELETE
drwxrws---   2 txf547 dz56   Jan 15  2020  sample_InSAR_ARD_DELETE
-rw-rw----+  1 jps547 v10    Apr  2  2019  GAMMA_DEM_SRTM_1as_mosaic.ige   (112 GB)
```

Read that as: a GAMMA/InSAR processing area belonging to GA staff, where most directories are
explicitly named `_DELETE` or `_CHECK`, and the one `backscatter` directory was last touched in
**December 2019**. There is a 112 GB GAMMA SRTM DEM mosaic, which is an InSAR processing input,
not a Sentinel-1 archive.

**Corroborating evidence from GA's own documentation.** `ga_sar_workflow` is the InSAR/backscatter
processing workflow Geoscience Australia runs on gadi. Its installation guide lists the NCI
project memberships required to operate it — and **dz56 is not among them**:

| project | what the doc says it is |
|---|---|
| **`fj7`** | "Copernicus Australia Regional Data Hub … gives you access to the directory `/g/data/fj7` where all the ESA data for our local region is stored" |
| **`dg9`** | "InSAR research" |
| `v10` | DEA Operations and code repositories (optional; **we already have this**) |
| `u46` | DEA Development and Science, GA internal (optional) |
| `up71` | Storage resources for GA ARD development (optional) |

Source: [ga_sar_workflow — Installation.md](https://github.com/GeoscienceAustralia/ga_sar_workflow/blob/main/insar/docs/Installation.md)

## 2. What fj7 is, and why it is the right ask

The **Copernicus Australasia Regional Data Hub** is the ESA-sanctioned regional mirror of the
Sentinel archive, and **it is physically operated from NCI in Canberra** — NCI is the master
repository for the South-East Asia and South Pacific region. It mirrors Sentinel-1, -2 and -3,
polling the European hubs hourly and targeting 90 % of products available within 24 hours.

On gadi it is `/g/data/fj7`, and it is also exposed publicly through NCI's THREDDS server, which
is a link you can check without any account:

* [Copernicus Australasia — About](https://www.copernicus.gov.au/about)
* [Copernicus Australasia — Data access](https://www.copernicus.gov.au/data-access) — "If you are
  a registered NCI user, you can also access the Hub data through the NCI THREDDS server and file
  system."
* [NCI THREDDS catalogue for fj7](https://thredds.nci.org.au/thredds/catalog/catalogs/fj7/catalog.html)
* [Copernicus Australia Hub Sentinel-1 SAR — GA product catalogue record](https://ecat.ga.gov.au/geonetwork/srv/api/records/14ff1542-0375-afc5-e053-10a3070a0565?language=eng)

Neither `/g/data/fj7` nor `/g/data/dg9` is even mounted for our account, which is consistent with
not being a member of either.

## 3. The thing worth knowing before anything else: DEA has no SAR at all

Checked directly against the datacube index we already use
(`dea/20231204`, the config this project runs on):

```
120 products indexed
products matching s1 / sar / radar:  NONE
```

So there is **no Sentinel-1 route through DEA**, and no amount of `ka08`/`v10` access will produce
one. Any national Sentinel-1 on NCI means either fj7's raw archive plus our own processing, or
pulling analysis-ready backscatter from outside NCI.

## 4. The three real options, with their actual costs

| route | what you get | the catch |
|---|---|---|
| **fj7 on NCI** | the full Sentinel-1 SLC/GRD archive, on-site | **raw, not analysis-ready.** Terrain-corrected backscatter has to be produced with GAMMA/SNAP/pyroSAR. That processing is the expensive part, and GA's `ga_sar_workflow` (which needs fj7 **and** dg9) exists because it is not a weekend job |
| **Microsoft Planetary Computer** | `sentinel-1-rtc` — already radiometrically terrain corrected, ready to use | outbound queries, and download-bound: previously costed at ~12 days of copyq for national coverage. Also the reason this is currently blocked — it means sending AgriWebb farm coordinates off-site |
| Copernicus Data Space / ASF | same as MPC in kind | same outbound problem, no NCI locality advantage |

**Two arguments favour fj7, and the cost one (§4a) is the stronger.** The governance argument was
that fetching from MPC means sending AgriWebb farm coordinates to a third party, whereas data on
`/g/data` never leaves the machine. **That argument weakens if AgriWebb is dropped**, as
`PRESENCE_ONLY_LABELS.md` recommends: the outbound-query decision for NVT trial AOIs was already
taken, so an NVT-only pipeline reopens MPC without any new call. What does *not* weaken is §4a —
MPC costs ~7,957 SU in copyq charges that a filesystem read does not.

---

## 4a. What the "12 days of copyq" actually costs — the wait is not the problem

Asked directly (2026-08-25): 14 days of waiting is acceptable if the compute is reasonable. It is
not the wait that rules this out.

**copyq bills at 4.00 SU/hr per CPU, twice the `normal` rate** — measured from this project's own
six S1 download jobs (15.41 SU / 3:51:07 and 14.85 SU / 3:42:42, both 1 CPU, both exactly 4.00).
That is easy to get wrong, because copyq is the only queue with outbound internet, so every
external download is billed at double rate whether or not anyone notices.

At the measured **72 s/tile** for the MPC Sentinel-1 RTC pull:

| tile count | CPU-hours | **SU at 4.00/hr** | share of the 10 KSU project earmark |
|---|---|---|---|
| 99,465 (the V2 union-of-crops mask) | 1,989 | **7,957** | **80 %** |
| 146,152 (the older, larger mask) | 2,923 | 11,692 | 117 % |

Against a mapping run that already costs **5,497 SU**, national Sentinel-1 from MPC comes to
roughly **13.5 KSU all-in — over the whole project allocation, on the smaller tile count.** The
12-day figure was the wall-clock consequence of a contended queue; the binding constraint is
money, and no amount of patience moves it.

**This is the real argument for fj7, and it is stronger than the governance one.** Reading
Sentinel-1 from `/g/data` is a filesystem read on `normal` at 2 SU/hr with no download at all —
it deletes the entire 7,957 SU line.

**What it does not delete, and what must be benchmarked the moment access lands.** fj7 holds
ESA's raw SLC/GRD, not analysis-ready backscatter. Terrain-corrected RTC has to be produced
locally (GAMMA/SNAP/pyroSAR — this is what `ga_sar_workflow` exists to do), and **that processing
cost is unmeasured.** It could plausibly exceed the download it replaces. Do not treat fj7 as
free until a pilot of a few tiles has been costed the same way everything else here has:

1. `ls /g/data/fj7` — check first whether any processed backscatter product is already there,
   which would settle the question outright.
2. If not, process ~10 tiles end to end on `normal`, measure SU/tile, multiply by 99,465.
3. Only then compare against the 7,957 SU MPC route and decide.

---

## 5. Draft email

Send to the lead CI of `fj7`. Their name is on the project page at
`https://my.nci.org.au/mancini/project/fj7` once you are logged in; NCI's help desk
(help@nci.org.au) will also route it if the lead is not listed. Worth ccing whoever you asked
about dz56, so that request can be closed off rather than left pending.

> **Subject:** Membership request — fj7 (Copernicus Australasia Hub) for national crop-type mapping
>
> Dear [name],
>
> I'm a PhD researcher at [institution] working on national-scale crop type mapping for Australian
> broadacre agriculture, with an NCI account under project xe2 (and access to v10 and ka08 for
> DEA).
>
> I'd like to request membership of fj7 so I can use the Sentinel-1 holdings in
> `/g/data/fj7` from gadi.
>
> **What I'm doing.** I'm building a paddock-level crop type classifier (canola / cereals /
> legumes) from Sentinel-2 phenology, segmenting paddock boundaries with SAM and taking
> paddock-median time series. It works well for distinguishing crops from each other. Where it
> struggles is separating a grazed pasture paddock from a cropped one — the two are similar in
> optical indices, and this is the main error mode standing between me and a national map.
>
> **Why Sentinel-1.** C-band backscatter responds to canopy structure rather than greenness, so it
> is the most likely single addition to separate pasture from crop. I have run a controlled
> optical-vs-radar comparison on a small sample already and want to test it at scale.
>
> **Why fj7 specifically, rather than fetching the data externally.** Some of my training labels
> come from commercial farm records supplied under an NDA. Querying an external archive would mean
> sending farm coordinates off-site, which I would rather not do. Data that already resides on
> NCI storage avoids that entirely, and it also avoids moving several TB across the network.
>
> **Two questions, if you have a moment:**
>
> 1. Is there an existing terrain-corrected Sentinel-1 backscatter collection on NCI you'd point
>    me to, rather than my processing GRDs myself? I can see `/g/data/dz56/backscatter` exists but
>    it appears to be a Geoscience Australia InSAR working area last updated in 2019, so I suspect
>    it is not intended as a general-purpose collection — I had requested dz56 membership before
>    realising this, and would be glad to be corrected.
> 2. If self-processing is the expected path, is `ga_sar_workflow` the recommended toolchain for
>    a non-GA user, and would that also require dg9?
>
> I'd be happy to discuss the compute footprint; I've been careful to benchmark before scaling
> and my current usage is well inside my allocation.
>
> Many thanks for your time,
>
> [name]
> [institution] · [NCI username cb8590]

### Before you send it

Two claims in the email are yours to confirm — I have not verified either:

* **"I have run a controlled optical-vs-radar comparison on a small sample already."** True per
  `output/S1_MODEL.md` and `YIELD_optical_s1.md`, but check the framing matches what you want to
  claim, since the measured S1 gain moved between samples (+0.044 → +0.029).
* **Your institution and supervisor.** A membership request from a named group with a named
  supervisor is approved faster than one from an individual.
