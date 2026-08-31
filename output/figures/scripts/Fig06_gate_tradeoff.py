#!/usr/bin/env python3
"""Fig 6 — presence-gate trade-off: stacked (amplitude AND shape) recall by crop,
across gate configurations. Numbers from output/PHENOLOGY_GATE.md,
"Stacked with amplitude -- the number that actually ships".
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUTDIR = "/home/147/cb8590/Projects/paddock-species/output/figures"
COLORS = {"Canola": "#f2c200", "Cereal": "#c98b52", "Legume": "#4f9d4f"}

configs = ["amplitude only\n(no shape gate)", "baseline\n(shipped)",
           "loosened senescence\n(-3 pts)", "two-pass\n(Canola exempt)"]
# amplitude-only recall per crop, from PHENOLOGY_GATE.md "Recall by crop" table
amplitude_only = {"Canola": 94.5, "Cereal": 96.0, "Legume": 91.3}
data = {
    "Canola":  [amplitude_only["Canola"], 78.3, 87.6, 94.5],
    "Cereal":  [amplitude_only["Cereal"], 91.4, 91.6, 91.4],
    "Legume":  [amplitude_only["Legume"], 87.2, 87.6, 87.2],
}

fig, ax = plt.subplots(figsize=(7.2, 4.2))
x = np.arange(len(configs))
w = 0.25
for i, crop in enumerate(["Canola", "Cereal", "Legume"]):
    ax.bar(x + (i - 1) * w, data[crop], w, label=crop, color=COLORS[crop])
ax.axhline(91.6, color="black", linestyle=":", linewidth=1, label="91.6% target (amplitude-gate recall)")
ax.set_xticks(x)
ax.set_xticklabels(configs, fontsize=8)
ax.set_ylabel("stacked presence recall (%)")
ax.set_ylim(70, 100)
fig.suptitle("Presence-gate recall by crop: the shipped shape gate costs Canola\n"
             "specifically; two-pass gating does not", fontsize=10, y=0.99)
ax.legend(frameon=False, fontsize=7.5, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.13))
ax.spines[["top", "right"]].set_visible(False)
for i, crop in enumerate(["Canola", "Cereal", "Legume"]):
    for j, v in enumerate(data[crop]):
        ax.text(j + (i - 1) * w, v + 0.4, f"{v:.1f}", ha="center", fontsize=6.5)

fig.tight_layout(rect=[0, 0, 1, 0.86])
os.makedirs(OUTDIR, exist_ok=True)
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(OUTDIR, f"Fig06_gate_tradeoff.{ext}"), dpi=300)
plt.close(fig)
print("-> Fig06_gate_tradeoff.png/.pdf")
