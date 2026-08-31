#!/usr/bin/env python3
"""Fig 3 -- Classifier confusion matrices, temporal + spatial transfer.

Raw counts copied verbatim from output/arms/GROUP3_reviewed.md (the "reviewed" arm,
run 2026-08-08 by train_group3_reviewed.pbs, macro F1 0.821 temporal / 0.823 spatial --
the numbers PAPER_PLAN.md's Fig3 spec asks this figure to match). Both splits score the
identical fixed 543-row test set (testkeep_temporal_SENSITIVE.csv); only the split rule
differs (train<=2022/test 2023-24 vs. 5-fold GroupKFold on site). Aggregate confusion
counts only -- no site-level GRDC records.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUTDIR = "/home/147/cb8590/Projects/paddock-species/output/figures"
CLASSES = ["Canola", "Cereal", "Legume"]

temporal = np.array([[128, 8, 19], [2, 252, 25], [6, 23, 80]])
spatial = np.array([[133, 8, 14], [4, 253, 22], [9, 24, 76]])

fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.6))
for ax, cm, title, f1 in [
    (axes[0], temporal, "(a) Temporal transfer\n(train <=2022, test 2023-24)", 0.821),
    (axes[1], spatial, "(b) Spatial transfer\n(5-fold GroupKFold on site)", 0.823),
]:
    row_pct = cm / cm.sum(axis=1, keepdims=True)
    im = ax.imshow(row_pct, cmap="Blues", vmin=0, vmax=1)
    for i in range(3):
        for j in range(3):
            color = "white" if row_pct[i, j] > 0.6 else "black"
            ax.text(j, i, f"{cm[i, j]}\n({100*row_pct[i, j]:.0f}%)", ha="center", va="center",
                    fontsize=8, color=color)
    ax.set_xticks(range(3))
    ax.set_yticks(range(3))
    ax.set_xticklabels(CLASSES, fontsize=8)
    ax.set_yticklabels(CLASSES, fontsize=8)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(f"{title}\nmacro F1 = {f1}, n=543", fontsize=8.5)

fig.suptitle("Classifier confusion matrices, reviewed arm (n=543, fixed test set both splits)",
             fontsize=10)
fig.tight_layout(rect=[0, 0, 1, 0.90])
os.makedirs(OUTDIR, exist_ok=True)
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(OUTDIR, f"Fig03_confusion_matrices.{ext}"), dpi=300)
plt.close(fig)
print("-> Fig03_confusion_matrices.png/.pdf")
