#!/usr/bin/env python3
"""Fig 8 -- Cereal yield model performance and ABS calibration.

Deliberately aggregate-only: NO per-trial predicted-vs-actual scatter is plotted, even
anonymised, because each point would be a single NVT trial's yield record -- covered by
the GRDC NDA (CLAUDE.md, "Sensitive Data"). Panel (a) uses only the already-published
arm-level R^2 (output/YIELD_cereal_pooled.md); panel (b) uses only the already-published
year-level calibration check (output/YIELD_CALIBRATION.md), which is itself an aggregate
(state/national) comparison, not a site-level one.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUTDIR = "/home/147/cb8590/Projects/paddock-species/output/figures"

arms = ["year+state\nbaseline", "satellite\nfeatures", "satellite +\nyear/state"]
r2_temporal = [-0.643, 0.471, 0.486]
r2_spatial = [0.294, 0.526, 0.577]

fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.0))

ax = axes[0]
x = np.arange(len(arms))
w = 0.35
ax.bar(x - w / 2, r2_temporal, w, label="temporal transfer\n(train<=2022, test 2023-24)",
       color="#c98b52")
ax.bar(x + w / 2, r2_spatial, w, label="spatial transfer\n(5-fold GroupKFold on site)",
       color="#4472c4")
ax.axhline(0, color="black", linewidth=0.6)
ax.set_xticks(x)
ax.set_xticklabels(arms, fontsize=8)
ax.set_ylabel("R$^2$")
ax.set_title("(a) Cereal yield model, by arm and split")
ax.legend(frameon=False, fontsize=7)
ax.spines[["top", "right"]].set_visible(False)

ax = axes[1]
years = ["2022\n(fit)", "2023\n(check)", "2024\n(check)"]
nvt_calibrated = [3.216, 2.162, 2.580]
abs_actual = [3.216, 2.640, 2.663]
x = np.arange(len(years))
ax.plot(x, nvt_calibrated, marker="o", label="NVT median x factor (0.6248)", color="#c98b52")
ax.plot(x, abs_actual, marker="s", label="ABS implied yield", color="#333333")
for i in range(1, 3):
    err = (nvt_calibrated[i] - abs_actual[i]) / abs_actual[i] * 100
    ax.annotate(f"{err:+.1f}%", (x[i], nvt_calibrated[i]), textcoords="offset points",
                xytext=(6, 6), fontsize=8)
ax.set_xticks(x)
ax.set_xticklabels(years)
ax.set_ylabel("t/ha (Wheat+Barley+Oat pooled)")
ax.set_title("(b) Calibration check against ABS\n(fit on 2022 only, checked on 2023-24)")
ax.legend(frameon=False, fontsize=7)
ax.spines[["top", "right"]].set_visible(False)

fig.tight_layout(pad=1.5)
os.makedirs(OUTDIR, exist_ok=True)
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(OUTDIR, f"Fig08_yield_summary.{ext}"), dpi=300)
plt.close(fig)
print("-> Fig08_yield_summary.png/.pdf")
