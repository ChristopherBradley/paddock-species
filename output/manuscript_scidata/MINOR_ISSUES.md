# Moderate and Minor Issues — Round 1 (Scientific Data manuscript)

## Moderate

| ID | Section(s) | Description | Resolved this round |
|---|---|---|---|
| Mod1 | Methods (Data sources / Presence gating) | Two population sizes (2,194 field-verified species-labelled trials; 3,439 presence-only known-sown trials) appeared with no explanation of their relationship, leaving a reviewer to wonder if one number was wrong. | **Yes** — added one clarifying sentence in Presence gating: the 3,439-trial population is presence-only (doesn't need species identity, so more trials qualify) versus the 2,194-trial population needed for species-labelled classifier/yield training. |
| Mod2 | Methods (Presence gating table) | Same root cause as Major M2 — three of the amplitude-only row's four cells were blank even though the values exist in the evidence base. | **Yes** — fixed together with M2. |
| Mod3 | Methods (Yield estimation) | Plan §9 point 5 called for stating Cereal yield's S1 gain (+0.09 R²), but the manuscript only said S1 inclusion was gated on cost, without ever giving the number — asymmetric with the canola-yield paragraph, which does give its S1 numbers. | **Yes** — added "+0.092" R² gain sentence to the Cereal yield paragraph. |
| Mod4 | Methods (Labelling, Yield estimation) | Two sentences (~100-115 words each, multiple clauses) were harder to parse than the venue's expected descriptive register warrants. | **Yes** — both split into 2-3 shorter sentences; no content removed. |

## Minor

| ID | Section(s) | Description | Resolved this round |
|---|---|---|---|
| Min1 | Data Records | `confidence` field's null-handling for abstained polygons wasn't stated (unlike `abstain_reason` and the yield columns, which do state it). | **Yes** — added a null-handling clause. |
| Min2 | Usage Notes | "Technical Validation's sensitivity table (available in the accompanying validation reports, Code Availability)" incorrectly implied the table lives in an external report rather than in this same manuscript's Technical Validation section. | **Yes** — simplified to "(Technical Validation)". |
| Min3 | Whole manuscript | No References section exists yet. | **No action needed** — correctly deferred to a `paper-covert`-equivalent stage per `REVISION_NOTES.md`; not a drafting defect. |

All identified Moderate and Minor issues (except the correctly-deferred Min3) were fixed this round.
