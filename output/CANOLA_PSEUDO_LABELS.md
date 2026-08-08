# Can we auto-label canola paddocks outside the NVT network?

Asked 2026-08-08: some paddocks look unmistakably like canola in the CFI heatmap. Could we
call those canola at >99 % confidence without ground truth, add them to the training set, and
improve the model?

**Answer: no, on both halves of the question — and for two independent reasons.** Recorded
here because the reasoning generalises to any confidence-thresholded pseudo-labelling scheme,
and because "it looked obvious in the figure" is a strong intuition that deserves a measured
rebuttal rather than a dismissal.

---

## 1. "99 % confidence" is far harder than it looks, because precision depends on prevalence

On the NVT set, thresholding peak CFI (DOY 200-300) against all other crops:

| target precision | achievable recall | threshold |
|---|---|---|
| 99 % | **0.9 %** | CFI > 2571 |
| 95 % | 2.8 % | CFI > 2438 |
| 90 % | 3.2 % | CFI > 2405 |

So even in-sample, 99 % precision buys about 20 paddocks nationally. That alone makes the
scheme uninteresting, but the deeper problem is that **the threshold does not transfer.**

The NVT set is **27.5 % canola**. A real landscape is not: canola is a minority of cropped
area even in canola-growing districts. Precision is a function of prevalence, while TPR and
FPR are not — so the same rule degrades as soon as it leaves the trial network:

| canola prevalence | best achievable precision | at recall |
|---|---|---|
| 30 % | 95.5 % | 2.8 % |
| 20 % | 92.6 % | 2.8 % |
| **10 %** | **84.7 %** | 2.8 % |
| **5 %** | **72.5 %** | 2.8 % |

To reach 99 % precision at 10 % prevalence, the false-positive rate must satisfy
`0.1·TPR / (0.1·TPR + 0.9·FPR) = 0.99`, i.e. **FPR ≈ 0.11 % of TPR** — a false-positive rate
near one in a thousand. Neither peak CFI nor the current model is within an order of magnitude
of that; the model's established operating point is 77 % sensitivity at **5 %** FPR.

**Generalisable point: a precision figure measured on a curated set is not a property of the
classifier.** Carry TPR/FPR across, never precision.

## 2. The confidently-labelled paddocks are the ones the model already gets right

Even granting a usable high-confidence pool, it would teach the model almost nothing. Measured
on the 2023-24 holdout, splitting true canola by peak CFI:

| CFI band among true canola | n | model recall |
|---|---|---|
| top 10 % | 22 | **100 %** |
| 75-90th percentile | 28 | 93 % |
| bottom 50 % | 95 | **62 %** |

A confidence rule selects from the top of that distribution by construction. Those rows are
already classified correctly, so adding more of them supplies gradient where the loss is
already near zero.

**The model's errors live at the bottom of the CFI distribution** — weak seasons, drought-
stressed crops, flowering hidden by a cloud gap. Those are precisely the paddocks no
CFI-confidence rule will ever surface, because they do not look like canola in the index. The
selection mechanism and the failure mechanism are the same mechanism, so self-training here
would sharpen the existing decision boundary rather than extend it.

## What would actually use unlabelled paddocks

The instinct that there is signal in unlabelled data is right; the pseudo-label is the wrong
way to extract it. **Self-supervised pre-training** (Presto, already the project's backbone
plan) learns crop phenology from unlabelled series and then fine-tunes on the GRDC labels. It
uses the same data without inheriting a threshold's blind spot, because nothing is selected on
confidence.

Two cheaper things also target the real failure mode more directly than pseudo-labels would:

1. **Fix the paddock labels we already have.** 31.8 % of training trials share a polygon with
   a different-crop trial (`LABEL_QUALITY.md`), which is a defect in existing data rather than
   a shortage of it.
2. **Sentinel-1 backscatter**, which separates by canopy structure rather than colour and so
   does not fail on the same paddocks CFI fails on.

## Caveats

- All figures are in-sample on NVT trials, using the quality-filtered 2,477-trial set. Real
  paddocks are not trial paddocks — the prevalence table is arithmetic applied to NVT-measured
  TPR/FPR, not a measurement made in the wild, and out-of-network performance would likely be
  worse still.
- The recall-by-CFI-band table uses the 3-index model on the temporal holdout (n=191 canola),
  so the per-band counts are small; the pattern is monotone and large, but the exact
  percentages are not precise.
- None of this argues against a canola map. It argues against manufacturing extra *training
  labels* by thresholding the same index the model already exploits.
