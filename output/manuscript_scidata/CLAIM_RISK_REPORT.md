# Claim Risk Report — Round 1 (Scientific Data manuscript)

Re-verification performed by the cold-read review agent against `CLAIM_SUPPORT_MAP.md` and the manuscript text.

**Result**: two claim-risk flags found, both Major (M1, M2 — see `MAJOR_ISSUES.md`), both fixed this round. No claim elsewhere in the document was found stated more strongly than its evidence file supports — the "we show/we find/this reveals" ban (Scientific Data's Abstract rule, extended manuscript-wide per this project's own writing instructions) was confirmed honored by direct grep, zero hits.

**Critical correctness checks, both explicitly requested for this round**:

1. **Leading classifier candidate leak (0.890/0.892, "sharma6", "candidate", "153 feat")**: **PASS, clean.** Zero hits via `grep -ni -E "0\.890|0\.892|sharma6|candidate|153 feat"` against the assembled manuscript. The one "Sharma et al." occurrence is a clean literature citation (Background & Summary, naming the closest Australian precedent) unconnected to the excluded candidate model. The deliberate exclusion decision (`PAPER_PLAN_SCIDATA.md` §24 point 6) was executed cleanly — verified independently by a reader with no role in drafting.
2. **Both newly-confirmed findings present and correctly worded**: confirmed by direct quotation from the manuscript — (a) the 3-groups-vs-9-species dual justification (label-conflict resolution AND macro F1 0.38-vs-0.82 accuracy justification, stated together in Methods/Labelling); (b) canola yield's "needs S1, confirmed on re-test" framing (spatial R² 0.271 vs. 0.290 baseline vs. 0.371 with S1, Methods/Yield estimation, echoed in Usage Notes).

**Hard word-limit verification** (counted independently by the reviewer, not trusted from the file's own claims): Abstract 166/170 words, Background & Summary 579/700 words — both compliant.

**Figure reference audit**: all 8 figures (Fig. 1-8) referenced exactly once each (Fig. 4 referenced twice within one introductory sentence pair in Data Records, by design), all placements match `PAPER_PLAN_SCIDATA.md` §13's mapping, no phantom references, none missing.

No new claim rows were added to `CLAIM_SUPPORT_MAP.md` this round — both fixes (M1, M2) corrected wording/table-completeness issues around claims already present in the map, not new evidence.
