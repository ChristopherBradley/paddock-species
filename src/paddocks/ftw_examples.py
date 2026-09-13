#!/usr/bin/env python3
"""
Side-by-side Fields of the World (FTW) and SAM boundaries at a sample of 2024 NVT trials, as
PNG panels over the clearest spring Sentinel-2 scene plus one GeoPackage of everything drawn.

FTW_COMPARISON.md gives the numbers over all 557 trials. This gives the user something to look
at (2026-09-12: "I want more example comparisons to compare FTW with SAM. Either png's or gpkg's
that I can copy to my local computer to see for myself"). Sites are sampled per state and
spread across the outcomes the comparison found: both sources give a passing polygon, FTW
contains the point where SAM does not, FTW's polygon is at least 3x SAM's (merged fields), and
everything else.

    python3 ftw_examples.py --detail .../ftw_site_detail_SENSITIVE.csv \
        --sites .../nvt_trials_labeled.csv --ftw .../ftw_2024_sites_SENSITIVE.gpkg \
        --sam .../national_2024_crops_final.gpkg --out-dir .../ftw/examples --per-state 8

Runs on a login node: each site is one small dc.load (about 2 km square at 10 m). Every output
carries a TrialCode and coordinates, so every file is SENSITIVE and stays on /scratch.
"""
import argparse
import os

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ALBERS = "EPSG:3577"
FMASK_CLEAR = 1
REFL_SCALE = 10000.0
MIN_HA, MAX_HA, MAX_COMPACT = 5.0, 300.0, 8.0


def pick_sites(detail, sites, per_state, seed):
    d = detail.merge(sites[["TrialCode", "lat", "lon", "Year"]], on="TrialCode")
    d = d[d.Year == 2024].copy()
    d["outcome"] = np.select(
        [(d.ftw_pass == 1) & (d.sam_pass == 1),
         (d.ftw_contains == 1) & (d.sam_contains == 0),
         (d.ftw_contains == 1) & (d.sam_contains == 1) & (d.ftw_area_ha >= 3 * d.sam_area_ha)],
        ["both_pass", "ftw_only", "ftw_merged"], default="other")
    rng = np.random.default_rng(seed)
    chosen = []
    for st, g in d.groupby("state"):
        pools = {oc: gg.sample(frac=1, random_state=int(rng.integers(1e9)))
                 for oc, gg in g.groupby("outcome")}
        order = ["both_pass", "ftw_only", "ftw_merged", "other"]
        n = 0
        while n < min(per_state, len(g)):
            for oc in order:
                if oc in pools and len(pools[oc]) and n < per_state:
                    chosen.append(pools[oc].iloc[0])
                    pools[oc] = pools[oc].iloc[1:]
                    n += 1
    return pd.DataFrame(chosen).reset_index(drop=True)


def clearest_rgb(dc, x0, x1, y0, y1, start, end):
    ds = dc.load(product=["ga_s2am_ard_3", "ga_s2bm_ard_3", "ga_s2cm_ard_3"],
                 x=(x0, x1), y=(y0, y1), crs=ALBERS, time=(start, end),
                 measurements=["nbart_red", "nbart_green", "nbart_blue", "oa_fmask"],
                 output_crs=ALBERS, resolution=(-10, 10), group_by="solar_day")
    if ds.time.size == 0:
        return None, None, None
    clear = (ds.oa_fmask == FMASK_CLEAR).mean(dim=("x", "y")).values
    i = int(np.argmax(clear))
    s = ds.isel(time=i)
    rgb = np.dstack([s.nbart_red.values, s.nbart_green.values, s.nbart_blue.values]).astype(float)
    rgb = np.clip(rgb / REFL_SCALE / 0.30, 0, 1)
    ext = [float(ds.x.min()) - 5, float(ds.x.max()) + 5, float(ds.y.min()) - 5, float(ds.y.max()) + 5]
    return rgb, ext, str(ds.time.values[i])[:10]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detail", required=True)
    ap.add_argument("--sites", required=True)
    ap.add_argument("--ftw", required=True)
    ap.add_argument("--sam", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--per-state", type=int, default=8)
    ap.add_argument("--half-m", type=float, default=1000.0, help="half-width of the drawn box")
    ap.add_argument("--start", default="2024-08-01")
    ap.add_argument("--end", default="2024-10-15")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-imagery", action="store_true")
    a = ap.parse_args()

    import geopandas as gpd
    from shapely.geometry import Point, box
    os.makedirs(a.out_dir, exist_ok=True)

    detail = pd.read_csv(a.detail)
    sites = pd.read_csv(a.sites)
    S = pick_sites(detail, sites, a.per_state, a.seed)
    print(f"{len(S)} sites: " + ", ".join(f"{k} {v}" for k, v in S.outcome.value_counts().items()), flush=True)

    ftw = gpd.read_file(a.ftw).to_crs(ALBERS)
    ftw["area_ha"] = ftw.geometry.area / 1e4
    ftw["compactness"] = ftw.geometry.length / np.sqrt(ftw.geometry.area)
    ftw["passes_filter"] = ftw.area_ha.between(MIN_HA, MAX_HA) & (ftw.compactness <= MAX_COMPACT)

    dc = None
    if not a.no_imagery:
        os.environ.setdefault("DATACUBE_CONFIG_PATH",
                              "/g/data/v10/public/modules/dea/20231204/datacube.conf")
        import datacube
        dc = datacube.Datacube(app="ftw_examples")

    pts = gpd.GeoDataFrame(S, geometry=[Point(xy) for xy in zip(S.lon, S.lat)], crs="EPSG:4326").to_crs(ALBERS)
    out_ftw, out_sam, out_aoi = [], [], []
    for k, r in pts.iterrows():
        x, y = r.geometry.x, r.geometry.y
        aoi = box(x - a.half_m, y - a.half_m, x + a.half_m, y + a.half_m)
        f = ftw[ftw.intersects(aoi)].copy()
        s = gpd.read_file(a.sam, bbox=aoi.bounds).to_crs(ALBERS)
        s = s[s.intersects(aoi)].copy()
        for g in (f, s):
            g["TrialCode"] = r.TrialCode
            g["contains_trial"] = g.geometry.contains(r.geometry)
        out_ftw.append(f)
        out_sam.append(s)
        out_aoi.append(gpd.GeoDataFrame({"TrialCode": [r.TrialCode], "crop": [r.crop], "state": [r.state],
                                         "outcome": [r.outcome]}, geometry=[aoi], crs=ALBERS))

        fc = f[f.contains_trial]
        sc = s[s.contains_trial]
        fa = f"{fc.area_ha.iloc[0]:.0f} ha{'' if fc.passes_filter.iloc[0] else ', fails filter'}" if len(fc) else "none"
        if len(sc):
            sa = f"{sc.area_ha.iloc[0]:.0f} ha, {sc.pred.iloc[0] if pd.notna(sc.pred.iloc[0]) else sc.abstain_reason.iloc[0]}"
        else:
            sa = "none"

        rgb, ext, date = (None, None, None)
        if dc is not None:
            try:
                rgb, ext, date = clearest_rgb(dc, x - a.half_m, x + a.half_m, y - a.half_m, y + a.half_m, a.start, a.end)
            except Exception as e:
                print(f"  imagery failed at {r.TrialCode}: {type(e).__name__}", flush=True)
        fig, axes = plt.subplots(1, 2, figsize=(13, 6.6))
        for ax, g, col, name, note in [(axes[0], f, "magenta", "Fields of the World", fa),
                                       (axes[1], s, "cyan", "SAM (released map)", sa)]:
            if rgb is not None:
                ax.imshow(rgb, extent=ext, interpolation="nearest")
            if len(g):
                g.boundary.plot(ax=ax, color=col, linewidth=1.2)
                gc = g[g.contains_trial]
                if len(gc):
                    gc.boundary.plot(ax=ax, color=col, linewidth=3)
            ax.plot(x, y, "o", mfc="yellow", mec="black", ms=9)
            ax.set_xlim(x - a.half_m, x + a.half_m)
            ax.set_ylim(y - a.half_m, y + a.half_m)
            ax.set_title(f"{name}: {len(g)} polygons, containing {note}", fontsize=11)
            ax.set_xticks([])
            ax.set_yticks([])
        fig.suptitle(f"{r.TrialCode} ({r.crop}, {r.state}, {r.outcome}){'' if date is None else ', S2 ' + date}",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
        fig.savefig(os.path.join(a.out_dir, f"ftw_vs_sam_{r.state}_{r.TrialCode}_SENSITIVE.png"), dpi=110)
        plt.close(fig)
        print(f"  {k + 1}/{len(pts)} {r.TrialCode} {r.state} {r.outcome}: FTW {fa} | SAM {sa}", flush=True)

    gp = os.path.join(a.out_dir, "ftw_vs_sam_examples_SENSITIVE.gpkg")
    if os.path.exists(gp):
        os.remove(gp)
    pd.concat(out_aoi).to_file(gp, layer="aoi", driver="GPKG")
    pts.drop(columns=[c for c in pts.columns if c in ("lat", "lon")]).to_file(gp, layer="trial_points", driver="GPKG")
    F = pd.concat(out_ftw)
    F["time"] = F["time"].astype(str)
    F.to_file(gp, layer="ftw", driver="GPKG")
    pd.concat(out_sam).to_file(gp, layer="sam", driver="GPKG")
    S.to_csv(os.path.join(a.out_dir, "ftw_vs_sam_examples_SENSITIVE.csv"), index=False)
    print(f"wrote {gp} and {len(pts)} PNGs to {a.out_dir}")


if __name__ == "__main__":
    main()
