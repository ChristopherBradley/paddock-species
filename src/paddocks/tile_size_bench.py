#!/usr/bin/env python3
"""
Does segmenting Australia in big tiles cost less than in small ones?

The national-run estimate in NATIONAL_INFERENCE_BENCHMARK.md is priced per 3 km tile, which
silently assumes tile size is a free parameter. It is not: pre-segment reads the datacube once
per tile and pays a fixed setup regardless of area, and every tile boundary truncates the
paddocks that straddle it. Both effects favour larger tiles, and neither had been measured.

WHAT MAKES THIS A CONTROLLED COMPARISON. The 3 km tiles are the 3x3 children of the 9 km tiles
(`subtile_aois.py`), so both arms cover EXACTLY the same ground in the same year. An earlier
9 km-versus-3 km reading compared different tiles in different landscapes — one arm included
rangeland, where SAM returns a single whole-tile blob — and that confound was worth more than
the effect being measured.

Cost model is gadi's, not an estimate: `normal` bills max(ncpus, mem/4GB) x 2 SU/hr and
`gpuvolta` bills its 12-CPU/1-GPU unit at 36 SU/hr whatever fraction of it the job uses.

    python3 tile_size_bench.py --dirs A=.../bench9km B=.../bench3km_matched
"""
import argparse
import os

import numpy as np
import pandas as pd

NORMAL_SU_HR = 2.0     # x max(ncpus, mem/4GB)
GPUVOLTA_SU_HR = 36.0  # the whole 12-CPU + 1-V100 unit


def load(d):
    pre = pd.read_csv(os.path.join(d, "timings_presegment.csv"))
    seg = os.path.join(d, "timings_segment.csv")
    seg = pd.read_csv(seg) if os.path.exists(seg) else None
    return pre, seg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", required=True, help="NAME=path pairs")
    ap.add_argument("--pre-mem-gb", type=float, default=4.0)
    ap.add_argument("--report")
    args = ap.parse_args()

    rows = []
    for spec in args.dirs:
        name, d = spec.split("=", 1)
        pre, seg = load(d)
        pre = pre[pre.status == "OK"]
        half = float(pre.half_m.iloc[0])
        km2 = (2 * half / 1000.0) ** 2

        pre_s = pre.seconds.mean()
        pre_su_tile = NORMAL_SU_HR * max(1.0, args.pre_mem_gb / 4.0) * pre_s / 3600.0

        r = {"arm": name, "tile_km": 2 * half / 1000.0, "km2": km2, "n_tiles": len(pre),
             "scenes": pre.n_scenes.mean(), "pre_s": pre_s,
             "pre_su_km2": pre_su_tile / km2}

        if seg is not None:
            seg = seg[seg.status == "OK"]
            # The first AOI in a job carries the ~14 s model load in its segment time; at
            # production batch sizes that is amortised to nothing, so pricing it here would
            # penalise whichever arm had fewer tiles per job rather than measure tile size.
            s = seg.segment_s.iloc[1:] if len(seg) > 2 else seg.segment_s
            seg_su_tile = GPUVOLTA_SU_HR * (s.mean() + seg.polygonise_s.mean()) / 3600.0
            r.update(seg_s=s.mean(), seg_su_km2=seg_su_tile / km2,
                     poly_per_km2=seg.n_keep.sum() / (len(seg) * km2),
                     median_ha=np.median(seg.median_ha),
                     kept_frac=seg.n_keep.sum() / max(seg.n_raw.sum(), 1))
            r["total_su_km2"] = r["pre_su_km2"] + r["seg_su_km2"]
            # Tile edge per unit area: the mechanism behind any paddock-count difference.
            r["edge_km_per_km2"] = 4 * (2 * half / 1000.0) / km2
        rows.append(r)

    D = pd.DataFrame(rows)
    out = []
    out.append("| arm | tile | tiles | scenes | pre s/tile | pre SU/km² | SAM s/tile | "
               "SAM SU/km² | **total SU/km²** |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for _, r in D.iterrows():
        out.append(f"| {r.arm} | {r.tile_km:g} km | {r.n_tiles:.0f} | {r.scenes:.0f} | "
                   f"{r.pre_s:.0f} | {r.pre_su_km2:.5f} | "
                   f"{r.get('seg_s', float('nan')):.0f} | "
                   f"{r.get('seg_su_km2', float('nan')):.5f} | "
                   f"**{r.get('total_su_km2', float('nan')):.5f}** |")
    out.append("")
    out.append("| arm | polygons/km² | median ha | kept/raw | tile edge km per km² |")
    out.append("|---|---|---|---|---|")
    for _, r in D.iterrows():
        out.append(f"| {r.arm} | {r.get('poly_per_km2', float('nan')):.2f} | "
                   f"{r.get('median_ha', float('nan')):.1f} | "
                   f"{r.get('kept_frac', float('nan')):.2f} | "
                   f"{r.get('edge_km_per_km2', float('nan')):.2f} |")

    if len(D) == 2 and "total_su_km2" in D:
        a, b = D.iloc[0], D.iloc[1]
        out.append("")
        out.append(f"**{a.arm} against {b.arm}: {b.total_su_km2/a.total_su_km2:.2f}x on SU/km², "
                   f"{a.poly_per_km2/b.poly_per_km2:.2f}x on polygons per km².**")
    txt = "\n".join(out)
    print(txt)
    if args.report:
        with open(args.report, "w") as fh:
            fh.write(txt + "\n")


if __name__ == "__main__":
    main()
