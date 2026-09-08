# Citation Gaps

All citations flagged by `PAPER_PLAN.md` §22/§24 Open Issue #6 as needing a fresh lookup were verified via WebSearch during this drafting pass (2026-08-30), not typed from memory:

| Citation | Status | Verified form |
|---|---|---|
| Kirillov et al. 2023 (Segment Anything) | **Verified** | Kirillov, A., Mintun, E., Ravi, N., Mao, H., Rolland, C., Gustafson, L., Xiao, T., Whitehead, S., Berg, A.C., Lo, W.-Y., Dollár, P., Girshick, R. (2023). Segment Anything. *2023 IEEE/CVF International Conference on Computer Vision (ICCV)*, 3992-4003. |
| Olofsson et al. 2014 | **Verified** | Olofsson, P., Foody, G.M., Herold, M., Stehman, S.V., Woodcock, C.E., Wulder, M.A. (2014). Good practices for estimating area and assessing accuracy of land change. *Remote Sensing of Environment*, 148, 42-57. doi:10.1016/j.rse.2014.02.015 |
| Ashourloo et al. 2019 | **Verified** | Ashourloo, D., Shahrabi, H.S., Azadbakht, M., Aghighi, H., Nematollahi, H., Alimohammadi, A., Matkan, A.A. (2019). Automatic canola mapping using time series of sentinel 2 images. *ISPRS Journal of Photogrammetry and Remote Sensing*, 156, 63-76. |
| Lawes et al. (Graincast/ePaddocks) | **Verified — year corrected** | `PAPER_PLAN.md` guessed "2021/2023"; the actual peer-reviewed citation is Lawes, R., Hochman, Z., Jakku, E., Butler, R., Chai, J., Waldner, F., Donohue, R. (2022). Graincast™: monitoring crop production across the Australian grainbelt. *Crop & Pasture Science*. doi:10.1071/CP21386 |

Citations present with full detail in `PAPER_PLAN.md` §22 and used as-is (not re-verified this pass): Van Tricht et al. 2023 (WorldCereal, ESSD); Tseng et al. 2024 (Presto, arXiv 2304.14065); Brown et al. 2025 (AlphaEarth, arXiv 2507.22291); Karra et al. 2021 (Esri/Impact Obs LULC, IGARSS); Kerner et al. 2024 (Fields of the World, arXiv 2409.16252); Newman & Furbank 2021 (*Scientific Data* — cited per the resolved Open Issue #2, framed as shared data lineage only).

| Citation | Status | Verified form |
|---|---|---|
| Sharma et al. 2026 | **CORRECTED 2026-09-07 — was wrong.** This row previously said "already complete," but `references.bib` (both `output/submission/` and `output/submission_scidata/`) carried a fabricated-looking author list (`Sharma, R., Eslick, C., Pires, A., Singh, K., Tareque, A.`) and a paraphrased title, self-flagged in the .bib's own `note` field as "not re-verified." Checked against Crossref metadata for the DOI (authoritative, not a guess): actual authors are Sneha Sharma, Harry Eslick, Rodrigo Pires, Balwinder Singh, Hasnein Tareque; actual title is "Temporal Sensitivity of In-Season Crop Classification: An Explainable Multi-Year Sentinel-2 Analysis in Western Australia" — matching `LIT_REVIEW_REPORT.md`'s entry exactly (which was read from the source PDF, not guessed). Both `references.bib` files fixed in place. |
| Al-Shammari et al. 2024 | **CORRECTED 2026-09-07 — was wrong.** Same issue: the .bib had `Whelan, B.` (missing "M.") and `Wang, X.` (should be `Wang, Chen` — wrong initial, not just missing one) and a paraphrased title. Crossref-verified authors: Dhahi Al-Shammari, Ignacio Fuentes, Brett M. Whelan, Chen Wang, Patrick Filippi, Thomas F.A. Bishop; actual title "Combining Sentinel 1, Sentinel 2 and MODIS data for major winter crop type classification over the Murray Darling Basin in Australia" — again matching `LIT_REVIEW_REPORT.md` exactly. Both `references.bib` files fixed in place. |

**Root cause, for future drafting passes**: these two entries were typed from `PAPER_PLAN.md` §22's own citation-scaffolding text rather than sourced from `LIT_REVIEW_REPORT.md` (which had the correct, source-verified entries the whole time) or checked against Crossref/the DOI directly. The .bib's own honesty note ("not re-verified") was the right caveat to write, but nothing ever came back to close it out until now.

**Recommended before final submission**: a full reference-manager pass (DOI resolution, publisher-exact formatting per RSE's house style) for the remaining entries — not done here, as it is a mechanical `paper-covert`-stage task rather than a drafting concern.
