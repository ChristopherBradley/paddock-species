# Second cleanup pass, after the final 2024 map and the Scientific Data draft (2026-09-11)

Aggregate only. Follows `DEAD_CODE_REMOVAL.md` (2026-09-10, 26 scripts) and uses the same rule.
Everything removed is still in git history. Restore with
`git checkout <commit-before-removal> -- <path>`.

## Rule used

Unchanged from the first pass. A file was removed if it is a superseded code path, or a finished
one-off experiment whose result is already written up in a report that stays. A file was kept if
it is on the production path of the 9 km map, generated a number the current manuscript cites,
belongs to open work, or is called by `run_national.sh` / `run_map100.sh`.

Two things changed since the first pass and account for everything removed here: the RSE
manuscript was deleted on 2026-09-11, and `MANUSCRIPT_DRAFT.md` became the single source of
truth for the Scientific Data draft, which retired its own per-section copies and its
2026-09-04 review round.

## Code removed (4 files)

| file | why |
|---|---|
| `nlum_negatives.py` | samples probable non-crop paddocks for a fourth "not crop" class. The negative class was measured and rejected (`NONCROP_CLASS.md`, `PRESENCE_ONLY_LABELS.md`): 78.5% of the hard-stratum grazing negatives pass the same crop-presence gate that 91.6% of known sown crops pass. The shipped design uses the NDVI presence gate instead. |
| `noncrop_check.pbs` | the PBS wrapper for the above, and its only caller |
| `grazing_panels.py` | NDVI/CFI panels for the sampled AgriWebb grazing paddocks. AgriWebb was dropped from the manuscript on 2026-09-10 and its other scripts went in the first pass; this was the leftover. |
| `samgeo_segment.pbs` | the SAMGeo arm of the finished paddock-boundary benchmark (`PADDOCK_BOUNDARY_BENCHMARK.md`), on an old `--lat/--lon/--buffer` CLI. Production segmentation runs `samgeo_segment.py` through `presegment.pbs` and `sam_segment.pbs` / `sampredict.pbs`, all kept. |

`samgeo_segment.py` itself is **kept** — it is the production segmenter.

## Markdown removed

**Superseded copies of the manuscript** (`output/manuscript_scidata/`). `DRAFT_README.md` already
recorded these as stale; they are the 2026-09-04 first draft, and the draft has since been
rewritten around the 9 km map and the adopted classifier.

- `sections/` and `sections_revised/` (8 files each)
- `ABSTRACT_DRAFT.md`

**The 2026-09-04 review round** (same folder), which reviewed a draft that no longer exists:
`REVIEW_REPORT.md`, `MAJOR_ISSUES.md`, `MINOR_ISSUES.md`, `REVISION_LOG.md`,
`NEXT_LOOP_PRIORITIES.md`, `SECTION_REVIEW_NOTES.md`, `JOURNAL_FIT_NOTES.md`,
`CLAIM_RISK_REPORT.md`, `REVIEW_LOOP_STATE.json`, `CLAIM_SUPPORT_MAP.md`, `COVERAGE_GAPS.md`,
`CITATION_GAPS.md`, `SECTION_NOTES.md`, `REVISION_NOTES.md`.

`output/AUTO_REVIEW.md` is **kept**: it is the cumulative generator-evaluator log that later
review rounds append to, which `CLAUDE.md` requires be preserved.

**Both `paper-covert` submission packages**, `output/submission/` and
`output/submission_scidata/`, directory and all.

- `output/submission/` described `output/manuscript/MANUSCRIPT_DRAFT.md`, the RSE draft that was
  deleted on 2026-09-11. Its source no longer exists.
- `output/submission_scidata/` was built from the 2026-09-04 draft, so its
  `MANUSCRIPT_SUBMISSION_READY.pdf` and `.docx` predate the final map, the overlap merge and the
  adopted classifier. A file with that name carrying superseded numbers is a hazard, and
  `paper-covert` rebuilds the package from the current draft in one command. Added to the
  pre-submission checklist in `DRAFT_README.md`.

Only the two `SUBMISSION_MANIFEST.md` files were tracked; the LaTeX, PDF and DOCX inside were
already gitignored by the 2026-09-11 commit that stopped tracking rendered documents, so they
were not in git and are not recoverable from it. They are regenerable.

## Kept, against the letter of the rule

`PAPER_PLAN.md` is the RSE plan and the RSE draft is gone, but `PAPER_PLAN_SCIDATA.md` still
cross-references it 19 times, so it is load-bearing for the Scientific Data plan.

The intermediate comparison reports (`ABS_COMPARISON_NATIONAL_2024_9km_preboundary*.md`,
`_strict.md`, `ABS_COMPARISON_100km*.md`, `OFFSET_GRID_PILOT_V2-V4.md` and similar) look like
superseded duplicates but are the evidence for a sequence the manuscript actually quotes: the
area over-call falling 1.47x -> 1.31x -> 1.18x -> 1.10x across the 3 km map, the 9 km map, the
tile-boundary step and the overlap merge. Deleting them would leave that number unsupported.
