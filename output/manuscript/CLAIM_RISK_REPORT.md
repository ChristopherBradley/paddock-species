# Claim Risk Report — Round 1

Re-verification of every row in `CLAIM_SUPPORT_MAP.md` against the manuscript text, performed by the cold-read review agent (see `REVIEW_REPORT.md`).

**Result: no CRITICAL-overclaims found.** All numeric claims match their stated sections with correct wording calibration:
- Composition-vs-area distinction maintained throughout (never conflated).
- ABS described consistently as "an independent official statistic," never as ground truth.
- Sentinel-1 and Sharma6 stated per-task throughout, never as an unqualified single verdict.
- The "unsupported/weak claims deliberately avoided" list in `CLAIM_SUPPORT_MAP.md` was checked directly — none of those phrasings appear anywhere in the draft.
- No claim in the draft is missing from `CLAIM_SUPPORT_MAP.md`; no claim in the map is missing from the draft.

**The single risk flag identified** was not a wording-vs-evidence miscalibration but an internal-consistency defect: the claim map's rows for "S1 regresses shipped+sharma6 classifier" and "Leading classifier candidate... macro F1 0.890/0.892" are each individually sourced correctly, but the map did not surface that their two source files report different baseline numbers for nominally the same candidate model (0.887/0.886 vs. 0.890/0.892) — this is Major issue M2, now fixed with a reconciling clause in Table 7's caption (`MAJOR_ISSUES.md`).

**Critical correctness check (explicitly requested for this round)**: does any Results-section number, Abstract sentence, or Introduction contribution state or imply the classifier's accuracy is 0.890/0.892 (the unreviewed candidate) rather than 0.821/0.823 (the shipped model actually used to produce every result in this paper)? **PASS.** Every occurrence of 0.890/0.892 in the reassembled `MANUSCRIPT_DRAFT.md` is confined to Discussion §6.5 (Table 7, correctly labeled as the candidate's row-matched score), Limitations §7.1 item 10 + Table 8, and the Conclusion's third open-thread paragraph — all Discussion/Future-Work-tier locations, every occurrence carrying the "not independently reviewed, not adopted" caveat in the same sentence. No Results/Abstract/Introduction number was found to leak the candidate's numbers. This is the load-bearing check for this revision pass and it holds.

No new claim rows were added to `CLAIM_SUPPORT_MAP.md` this round (the four new tables built to fix M1 restate numbers already in the map's existing rows or in Results prose; no new evidence was introduced).
