# Journal Fit Notes — Round 1 (Nature Scientific Data, backup ESSD)

| Expectation | Status |
|---|---|
| Abstract ≤170 words, no new-scientific-findings claims | Compliant — 166 words, verified by independent count; "we show/we find" language absent by grep across the whole manuscript, not just the Abstract. |
| Background & Summary ≤700 words | Compliant — 579/581 words (two independent counts, minor regex-boundary difference, both well under). |
| Data Descriptor structure (Abstract / Background & Summary / Methods / Data Records / Technical Validation / Usage Notes / Data Availability / Code Availability) | Present and correctly ordered; no Introduction/Related Work/Results/Discussion/Conclusion, correctly, per this venue's fixed template. |
| Discussion-shaped content (a research article would have) redistributed cleanly into Methods as design-justification | Confirmed by the reviewer via a targeted grep for generalizable-lesson phrasing ("more broadly," "transferable," "generalizable") — zero hits. The reframing is genuine rhetorical conversion, not just section relocation. |
| Data Availability / Code Availability as named, required sections | Present; both correctly marked `[PENDING]` for the two genuine, not-yet-done deposit prerequisites rather than faked. |
| Figure/table reporting | 8 figures reused from the RSE manuscript's figure set (Scientific Data has no hard figure-count cap; typical range 4-8, this project's 8 is at the high end but justified), all correctly placed and captioned for this venue's register. |
| Reusability / independent validation (Scientific Data's explicit evaluation axis) | Technical Validation is the manuscript's clear strength — every planned validation procedure present, ABS/ABARES 6.8% floor correctly invoked, three additional tables (argmax-vs-mean-probability, threshold sensitivity, ABS/ABARES per-year disagreement) added this round's predecessor pass, strengthening rather than padding. |
| ESSD backup structural fit (Introduction / Data and Methods / Data availability / Code availability / Conclusions, required "uncertainty and its evaluation" section) | Not built this pass (Scientific Data is primary) — `PAPER_PLAN_SCIDATA.md` §19 has the conversion mapping ready if the venue switches. Technical Validation already satisfies ESSD's required "dedicated section on uncertainty and its evaluation." |

**Overall**: no journal-fit blockers found this round. Both majors (M1, M2) were precision problems in load-bearing claims — exactly the kind of thing a Scientific Data reviewer scrutinizes hardest (Abstract precision; a dataset's disclosed design trade-offs) — now fixed. The candidate-model exclusion, the venue's single hardest content-scoping decision, was independently verified clean.
