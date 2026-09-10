# Moderate and Minor Issues — Round 1

## Moderate

| ID | Section(s) | Description | Resolved this round | Carry-over |
|---|---|---|---|---|
| Mod1 | Highlights | Two of five Highlights bullets exceeded RSE's ≤85-character limit (`PAPER_PLAN.md` §2): bullet 1 was 88 chars, bullet 5 was 86 chars. | **Yes** — trimmed to 80 and 76 chars respectively. | No |
| Mod2 | Abstract | Abstract was 255 words, over the 200-250 target (`PAPER_PLAN.md` §20) and RSE's ~250-word guidance. | **Yes** — trimmed while adding the M4 floor caveat; net result exactly 250 words. | No |
| Mod3 | 7 (Limitations and Future Work) | Limitations/Future Work has grown to ~1,300+ words (post-M1/M3 additions), now longer than Results and close to Discussion — a structural imbalance for an applied dataset paper. Real content overlap exists between Discussion §6.5 and Limitations items 6/10 (the S1 task-split and candidate-model findings are stated in near-full detail in both places, then restated a third time in Conclusion). | **No** — flagged for next round. Each restatement currently serves a distinct function (interpret / disclose / summarize per section convention), so trimming needs care, not a mechanical cut; better done as a dedicated pass with fresh eyes once E8/Open Issue #8 land and the sections are edited again anyway, rather than risk removing content mid-review-loop. | **Yes — next round** |
| Mod4 | 2 (Related Work) | Related Work is under its word budget (1,248 vs. 1,300-1,600) — not a defect on its own, but undocumented (DRAFT_README's word-count table shows it as "unchanged," predates this pass). | **No** — not actionable without new content; the section is complete and accurate, just concise. No action taken. | No (accepted as-is) |
| Mod5 | Abstract | "trained on 2,194... records" was a slight imprecision — 2,194 is the total labelled population (train+test), not literally the training set. | **Yes** — changed to "built from 2,194... records" in the Abstract. (Introduction and Conclusion already used "built... from," not "trained on," and needed no change.) | No |

## Minor

| ID | Section(s) | Description | Resolved this round |
|---|---|---|---|
| Min1 | `COVERAGE_GAPS.md` | Bookkeeping said "Table 6... is not referenced in the draft," which was already slightly inaccurate (it's referenced once, correctly, inside the `[PENDING: E8]` block). | **Yes** — corrected. |
| Min2 | Introduction | Contributions are prose-numbered ("First,... Second,...") rather than a literal numbered list; `PAPER_PLAN.md` §19 says "end with numbered contributions." | **No** — stylistically acceptable for RSE, not worth a structural change. Accepted as-is. |
| Min3 | Whole manuscript | No compiled References/Bibliography section exists yet, despite ~12 in-text citations. | **No action needed** — correctly deferred to `paper-covert` per `DRAFT_README.md`/`REVISION_NOTES.md`; not a `paper-draft`/`paper-review-loop` defect. |

No sensitive GRDC/NVT site-level data (coordinates, TrialCodes) was found anywhere in the manuscript text — checked directly by the reviewer, clean.
