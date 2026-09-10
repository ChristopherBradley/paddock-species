---
section: study_area_and_data
mode: full
word_target: 700
---

# 3. Study Area and Data

## 3.1 Study area

The completed national map covers continent-wide Australia, comprising XXX tiles for the 2024 growing season, which cover XXX% of the national extent where the National Land Use Map (NLUM) probability surfaces indicate agricultural probability for one of the three target crop groups. A 100 km × 100 km block in the Riverina region of New South Wales, a major mixed-cropping district, was used for a nine-season (2017-2025) regional test of the same pipeline. It is reported separately from the national result because only the regional extent has multi-year coverage (Section 3.2; Section 7, Limitation 4). Fig. 2 [XXX: regenerate from the re-run] shows the national tile coverage, the Riverina block and the SA2 regions used for validation (Section 3.3).

## 3.2 Temporal scope

A single growing season, 2024, is complete and validated at national scale. Nine seasons (2017-2025) are complete at the 100 km regional scale. A national extension to the remaining eight seasons (2017-2023, 2025) is planned but has not yet been run at the time of this draft [PENDING: national 2017-2025 run, E8]. All multi-year results and figures in this paper are regional, and are evidence for but not proof of national multi-year generalisation (Section 6.6).

## 3.3 Data sources

Table 1 summarises the datasets used. Sentinel-2 surface-reflectance imagery was accessed via Digital Earth Australia's Analysis Ready Data product (`ga_s2am/bm/cm_ard_3`) through the National Computational Infrastructure's datacube, at 10 m resolution, nationally, 2017-2025. Ground truth for training and validation is drawn from the Grains Research and Development Corporation (GRDC) National Variety Trial (NVT) network: recorded, point-located records of sown crop per trial site, spanning 2017-2025 nationally. This dataset is covered by a data-use agreement and cannot be released or described at the site level (coordinates, trial identifiers or yields); all reporting in this paper is aggregate. Independent validation uses ABS sown-area statistics aggregated to the SA2 level, which have no connection to the training pipeline. ABARES production statistics provide a cross-check on ABS itself, and the two agencies' median 6.8% disagreement on national sown area is the accuracy floor this paper measures its map against (Section 5.2). The NLUM v7 250 m per-commodity agricultural probability surfaces (2020-21) were used for two purposes: during national inference, to restrict segmentation and classification to tiles with non-trivial probability for one of the three target crop groups; and afterwards, as an independent spatial-comparison product (Section 5.5). Paddock boundaries were delineated with the Segment Anything Model (`vit_h` checkpoint, stock parameters; Kirillov et al., 2023) via the SAMGeo/PaddockTS wrapper. Re-tuning SAM's parameters was tested as a fix for poorly segmented polygons and ruled out (Section 4.1).

**Table 1.** Dataset and pipeline summary.

| Dataset | Role | Resolution / extent | Access |
|---|---|---|---|
| Sentinel-2 (DEA ARD) | Primary imagery; day-of-year-binned spectral indices | 10 m, national, 2017-2025 | Open |
| GRDC / NVT trial records | Training and validation ground truth | Point-in-paddock, national, 2017-2025 | Data-use agreement; not releasable; aggregate reporting only |
| ABS sown-area statistics | Independent validation reference | SA2-level, XXX SA2s, national | Public |
| ABARES production statistics | Cross-check on ABS (6.8% median mutual disagreement) | State / national | Public |
| NLUM v7 250 m Ag. Probability Surfaces | (a) National-run coverage mask; (b) independent spatial-comparison product | 250 m, national | Public |
| WorldCereal 2021 v100 | Independent spatial-comparison product | 10 m, national AU extent | Public (CC-BY 4.0) |
| Segment Anything Model (SAM) | Paddock-scale segmentation, stock parameters | 10 m-derived polygons | Open weights |

## 3.4 Preprocessing

Segmented polygons were retained only within a 5-300 ha area range and with a compactness ratio (perimeter / sqrt(area)) of at most 8. This geometric filter is also a non-spectral presence signal, since land without paddock-scale field boundaries is rarely segmented into polygons in this size range; it retains XXX% of NVT trial paddocks and excludes the remainder as too small, too large or too irregular. Per retained polygon, 153 paddock-median spectral features were computed (17 per index, binned by day of year across the growing season) from nine indices: NDVI, a canola-specific flowering index following the general approach of Ashourloo et al. (2019), a chlorophyll-fluorescence-related index and six band-derived indices used by Sharma et al. (2026): NDRE2, VI2, VI3, VDVI, VCI and EVI2 (Section 4.3). NVT trial points were matched to their enclosing (or, where no polygon contained the point, nearest plausible) SAM polygon. Because 69.7% of training trials share a segmented paddock with another NVT trial (31.8% with a different crop, reflecting how trial networks co-locate multiple varieties), the original nine-species label scheme was collapsed to three broad groups, resolving 69% of these label conflicts, and the remainder were resolved by hand review (Section 4.2).
