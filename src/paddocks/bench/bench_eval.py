#!/usr/bin/env python
"""
bench_eval.py -- collect the KSU benchmark: PBS epilogues, per-tile timings, RSS samples, GPU
utilisation, and output agreement between arms. Writes <out>/bench_summary.json and prints it.
Aggregate only.
"""
import argparse
import glob
import json
import os
import re

import numpy as np
import pandas as pd

LOGS = "/scratch/xe2/cb8590/paddock-species-logs"


def epilogue(jobid):
    jid = jobid.split(".")[0]
    fs = glob.glob(f"{LOGS}/{jid}.gadi-pbs.OU") + glob.glob(f"{LOGS}/*.o{jid}")
    if not fs:
        return None
    txt = open(fs[0], errors="replace").read()
    g = lambda pat, cast=float: (cast(re.search(pat, txt).group(1)) if re.search(pat, txt) else None)
    hms = lambda s: sum(float(v) * m for v, m in zip(s.split(":"), (3600, 60, 1)))
    wt = re.search(r"Walltime Used:\s+(\d+:\d+:\d+)", txt)
    cpu = re.search(r"CPU Time Used:\s+(\d+:\d+:\d+)", txt)
    bench = [l for l in txt.splitlines() if l.startswith("BENCH")]
    return dict(jobid=jid, exit=g(r"Exit Status:\s+(-?\d+)", int), su=g(r"Service Units:\s+([\d.]+)"),
                walltime_s=hms(wt.group(1)) if wt else None, cpu_s=hms(cpu.group(1)) if cpu else None,
                mem_used_gb=g(r"Memory Used:\s+([\d.]+)GB"), mem_req_gb=g(r"Memory Requested:\s+([\d.]+)GB"),
                ncpus=g(r"NCPUs Used:\s+(\d+)", int), queue=(re.search(r"queue=(\S+)", txt).group(1) if re.search(r"queue=(\S+)", txt) else None),
                bench_lines=bench, log=fs[0])


def rss_peak(pattern):
    fs = glob.glob(pattern)
    if not fs:
        return None
    v = pd.concat([pd.read_csv(f, sep=" ", header=None, names=["t", "rss", "cg"]) for f in fs])
    return dict(rss_peak_gb=round(float(v.rss.max()), 2), rss_median_gb=round(float(v.rss.median()), 2),
                cgroup_peak_gb=round(float(pd.to_numeric(v.cg, errors="coerce").max()), 2), n=len(v))


def gpu_util(pattern):
    fs = glob.glob(pattern)
    if not fs:
        return None
    rows = []
    for f in fs:
        for l in open(f):
            p = [x.strip() for x in l.split(",")]
            if len(p) >= 3 and p[1].endswith("%"):
                rows.append((float(p[1].rstrip("%")), float(p[2].split()[0])))
    if not rows:
        return None
    u = np.array(rows)
    return dict(util_mean_pct=round(float(u[:, 0].mean()), 1), util_p90_pct=round(float(np.percentile(u[:, 0], 90)), 1),
                gpu_mem_max_mb=round(float(u[:, 1].max())), samples=len(u))


def timings(pattern, col):
    fs = glob.glob(pattern)
    if not fs:
        return None
    t = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    ok = t[t.status == "OK"] if "status" in t else t
    return dict(n=len(t), n_ok=len(ok), per_tile_median_s=round(float(ok[col].median()), 2),
                per_tile_mean_s=round(float(ok[col].mean()), 2), sum_s=round(float(ok[col].sum()), 1))


def sam_agreement(arm_dir, stubs, prod_dir="/scratch/xe2/cb8590/paddock-species-data/derived/national2024/samgeo"):
    """Share of production polygons with an arm polygon at IoU >= 0.9 / 0.5, and the count ratio."""
    import geopandas as gpd
    import shapely
    n_prod = n_arm = 0; best = []
    for s in stubs:
        fa, fp = f"{arm_dir}/{s}_filt.gpkg", f"{prod_dir}/{s}_filt.gpkg"
        if not (os.path.exists(fa) and os.path.exists(fp)):
            continue
        ga, gp = gpd.read_file(fa), gpd.read_file(fp)
        n_arm += len(ga); n_prod += len(gp)
        if not len(ga):
            best += [0.0] * len(gp); continue
        tree = shapely.STRtree(ga.geometry.values)
        for g in gp.geometry.values:
            c = tree.query(g, predicate="intersects")
            if len(c):
                inter = shapely.area(shapely.intersection(ga.geometry.values[c], g))
                best.append(float((inter / (g.area + shapely.area(ga.geometry.values[c]) - inter)).max()))
            else:
                best.append(0.0)
    b = np.array(best)
    return dict(n_prod=n_prod, n_arm=n_arm, matched_ge09=round(float((b >= 0.9).mean()), 4) if len(b) else None,
                matched_ge05=round(float((b >= 0.5).mean()), 4) if len(b) else None, iou_median=round(float(np.median(b)), 4) if len(b) else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True, help="benchksu dir")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    B = a.bench
    jobs = dict(l.split()[:2] for l in open(f"{B}/jobs.txt") if l.strip())
    out = {"jobs": {}}
    for name, jid in jobs.items():
        e = epilogue(jid)
        rec = {"jobid": jid, "epilogue": e}
        if name.startswith("ps2021_") or name.startswith("ps_"):
            d = {"ps2021_normal4": "ps2021_normal4", "ps2021_bw8": "ps2021_bw8", "ps2021_sl6": "ps2021_sl6"}.get(name, "tiles")
            jid = str(jid).split(".")[0]
            rec["timings"] = timings(f"{B}/{d}/timings_presegment_{jid}*.csv", "seconds")
            rec["rss"] = rss_peak(f"{B}/{d}/memsample_{jid}.log")
        elif name.startswith("pred_"):
            rec["timings"] = timings(f"{B}/{name}/*_timings.csv", "total_s") if glob.glob(f"{B}/{name}/*_timings.csv") else None
            rec["rss"] = rss_peak(f"{B}/{name}/*_memsample.log")
        elif name.startswith("sam_"):
            rec["timings"] = timings(f"{B}/{name}/timings_segment_*.csv", "segment_s")
            rec["polygonise"] = timings(f"{B}/{name}/timings_segment_*.csv", "polygonise_s")
            rec["gpu"] = gpu_util(f"{B}/{name}/gpu_*.log")
            if glob.glob(f"{B}/{name}/*_filt.gpkg"):
                rec["agreement"] = sam_agreement(f"{B}/{name}", pd.read_csv(f"{B}/aois/sam100.csv").stub.tolist())
        if e and e["su"] is not None and rec.get("timings") and rec["timings"]["n_ok"]:
            rec["su_per_tile"] = round(e["su"] / rec["timings"]["n_ok"], 4)
            rec["su_per_hour"] = round(e["su"] / (e["walltime_s"] / 3600), 2) if e["walltime_s"] else None
        out["jobs"][name] = rec
    with open(a.out, "w") as f:
        json.dump(out, f, indent=2, default=str)
    for name, rec in out["jobs"].items():
        e = rec["epilogue"] or {}
        t = rec.get("timings") or {}
        print(f"{name:16s} exit={e.get('exit')} su={e.get('su')} wall={e.get('walltime_s')} mem_used={e.get('mem_used_gb')}/{e.get('mem_req_gb')} "
              f"tiles_ok={t.get('n_ok')} median_s={t.get('per_tile_median_s')} su/tile={rec.get('su_per_tile')} rss={rec.get('rss')} gpu={rec.get('gpu')} agree={rec.get('agreement')}")


if __name__ == "__main__":
    main()
