#!/usr/bin/env python3
"""
Clustered paddock-median CFI heatmaps for every NVT site, three crop groups at a time.

One figure per (year, state), rows = trials, columns = calendar day-of-year, colour = CFI
over the trial's own paddock. Rows carry a NUMBER, and the same number is written into a
companion GeoPackage holding that row's paddock polygon and trial point — so a suspicious
row in the figure can be looked up directly in QGIS.

    python3 crop_heatmap.py \
        --ts "…/samgeo/ts_v2/*_SENSITIVE.csv" \
        --labeled …/nvt_trials_labeled.csv \
        --review …/review_v2/review_sites.csv …/review_v2_other/review_sites.csv \
        --chosen-dir …/review_v2 …/review_v2_other \
        --outdir …/figures/crop_heatmaps

WHY ONE FIGURE PER YEAR AND STATE. Measured on this dataset, not assumed: flowering spread
is IQR 26 d on calendar day-of-year nationally but state medians run 242 (WA) to 258 (VIC),
and absolute CFI level shifts between seasons — pooling seasons drove Youden J *below* every
individual season it pooled. Pooling smears the flowering band into invisibility no matter
how the pixels are aggregated, so year and state are held fixed and the axis is calendar DOY,
not days after sowing (DAS aligns flowering less tightly: IQR 30 d vs 26 d).

THREE GROUPS, because "is this canola?" needs a negative class that is not only wheat. CFI is
not canola-specific — about half of lupin trials clear a canola threshold, since any bright
flowering canopy lifts it — so a canola-vs-wheat figure flatters the index. Barley, chickpea,
oat, field pea, lupin, faba bean and lentil are pooled as `Other`; the exact crop is in the
GeoPackage and the row csv.

The clustering never sees the crop label: rows are ordered by their CFI trace alone and the
label only colours the number. Agreement between the clusters and the colours is therefore
evidence, and a row that clusters with the wrong crop is a candidate label or paddock
mismatch — which is the whole point of Stage 2.

SENSITIVE: the GeoPackage and row csv carry TrialCodes and coordinates.
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
from matplotlib.gridspec import GridSpec              # noqa: E402
from matplotlib.lines import Line2D                   # noqa: E402
from scipy.cluster.hierarchy import dendrogram, fcluster, leaves_list, linkage  # noqa: E402

GROUP_COLOUR = {"Canola": "#E69F00", "Wheat": "#0072B2", "Other": "#009E73"}
REFL_SCALE = 10000.0     # CFI on the raw-DN scale, so values match PaddockTS figures
DOY_STEP = 5


def crop_group(c):
    return c if c in ("Canola", "Wheat") else "Other"


def load_ts(patterns, metric, min_clear_frac):
    files = sorted({f for p in patterns for f in glob.glob(p)})
    if not files:
        raise SystemExit(f"no time-series files matched {patterns}")
    ts = pd.concat((pd.read_csv(f, parse_dates=["time"]) for f in files), ignore_index=True)
    if metric not in ts.columns:
        raise SystemExit(f"{metric} not in the time series (have: {list(ts.columns)})")
    # A trial extracted twice (resume overlap, or a chunk rerun) must not become two rows.
    ts = ts.drop_duplicates(subset=["TrialCode", "time"])
    before = ts.TrialCode.nunique()
    # Partial-cloud scenes read low in every index and bias the whole trace downward, so they
    # are dropped on clear FRACTION, not on clear pixel count — a big paddock can have many
    # clear pixels and still be mostly cloud.
    ts = ts[ts["n_clear_px"] / ts["n_px_paddock"].clip(lower=1) >= min_clear_frac].copy()
    ts["doy"] = ts["time"].dt.dayofyear
    print(f"loaded {len(files)} file(s): {before} trials -> {ts.TrialCode.nunique()} "
          f"after clear-fraction >= {min_clear_frac}")
    return ts


def load_review(paths):
    """Per-trial match-quality metrics, concatenated across the crop groups' review runs."""
    if not paths:
        return pd.DataFrame(columns=["TrialCode"])
    found = [p for p in paths if os.path.exists(p)]
    for p in set(paths) - set(found):
        print(f"  warning: review file missing, its trials keep no quality metrics: {p}")
    if not found:
        return pd.DataFrame(columns=["TrialCode"])
    r = pd.concat((pd.read_csv(p) for p in found), ignore_index=True)
    keep = ["TrialCode", "aoi_stub", "match_rule", "edge_dist_m", "area_ha", "compactness",
            "bigger_neighbour_ratio", "tree_frac", "flags", "risk"]
    return r[[c for c in keep if c in r.columns]].drop_duplicates("TrialCode")


def quality_filter(d, args):
    """Drop trials whose paddock is not a plausible paddock. Returns (kept, reasons).

    Deliberately NOT a filter on the full risk score. Blind review of a stratified sample put
    the usable rate at 83-92 % for every flag stratum (clean 92 %, edge_close 92 %,
    not_contained 92 %, bigger_neighbour 83 %) with 92 % reviewer agreement — so those flags
    do not track real failure and filtering on them would throw away mostly-good data. What
    review DID identify as genuinely wrong were shape and size failures: drainage lines, road
    verge triangles, and under-segmented blobs spanning several fields. Those are what this
    removes.
    """
    reasons = {}
    m = pd.Series(True, index=d.index)

    def drop(name, bad):
        nonlocal m
        bad = bad.fillna(False) & m
        reasons[name] = int(bad.sum())
        m &= ~bad

    # Long and thin: drainage lines and road verges, the failure mode review found in imagery
    # and no other flag caught. Compactness also separated a real 51.6 ha neighbour (5.4) from
    # an under-segmented 351.9 ha blob (7.2) on the user's own two worked examples.
    if "compactness" in d:
        drop("sliver (compactness > %.1f)" % args.max_compactness,
             d.compactness > args.max_compactness)
    # Under-segmented merges. The base filter admits up to 1500 ha; the user's own review
    # rubric calls >300 ha with no internal structure `too_big`, and a merged polygon spans
    # several fields, so its median mixes crops — the exact failure that disqualified FTW.
    drop("too_big (> %d ha)" % args.max_area_ha, d.area_ha_ts > args.max_area_ha)
    # Smaller than a broadacre paddock even after the upgrade rule had its chance.
    drop("too_small (< %d ha)" % args.min_area_ha, d.area_ha_ts < args.min_area_ha)
    # Pixel-level tree masking already removes canopy from the median, but a polygon that is
    # mostly canopy is not a paddock at all and its surviving pixels are not representative.
    if "tree_frac" in d:
        drop("treed (> %.0f %% canopy)" % (100 * args.max_tree_frac),
             d.tree_frac > args.max_tree_frac)
    drop("too few clear observations (< %d)" % args.min_obs, d.n_obs < args.min_obs)
    return d[m], reasons


def build_matrix(ts, trials, metric, grid):
    """Interpolate each trial's trace onto the shared DOY grid. NaN outside its own range."""
    rows, kept = [], []
    for t in trials:
        g = ts[ts.TrialCode == t].sort_values("doy").dropna(subset=[metric])
        if len(g) < 3:
            continue
        v = np.interp(grid, g.doy, g[metric], left=np.nan, right=np.nan)
        # np.interp clamps outside the data range rather than extrapolating; blank those
        # cells instead, so a flat edge is never mistaken for a measured flat trace.
        v[(grid < g.doy.min()) | (grid > g.doy.max())] = np.nan
        rows.append(v * REFL_SCALE)
        kept.append(t)
    return (np.vstack(rows) if rows else np.zeros((0, len(grid)))), kept


def cluster_order(M):
    """Leaf order from correlation/average linkage on the traces alone."""
    # Fill each row's gaps with that row's own mean: a gap then contributes zero deviation to
    # the correlation instead of pulling every gappy row toward a shared global value, which
    # would cluster rows by how cloudy they were rather than by their phenology.
    Mf = M.copy()
    rm = np.nanmean(Mf, axis=1, keepdims=True)
    rm = np.where(np.isnan(rm), np.nanmean(Mf), rm)
    Mf = np.where(np.isnan(Mf), rm, Mf)
    Z = linkage(Mf, method="average", metric="correlation")
    return Z, leaves_list(Z)


def chosen_geoms(stubs, chosen_dirs):
    """{TrialCode: (paddock_geom, trial_point)} from the per-AOI review layers."""
    import geopandas as gpd
    out = {}
    for stub in stubs:
        # Every directory is read, not just the first that has the stub. The other-crop
        # trials that reused a canola/wheat AOI live under the SAME stub in a different
        # review directory, so stopping at the first hit would silently drop them — the
        # figure would show a row whose paddock is missing from the GeoPackage.
        for d in chosen_dirs:
            fc = os.path.join(d, f"{stub}_chosen.gpkg")
            ft = os.path.join(d, f"{stub}_trials.gpkg")
            if not os.path.exists(fc):
                continue
            c = gpd.read_file(fc)
            t = gpd.read_file(ft) if os.path.exists(ft) else None
            pts = dict(zip(t.TrialCode, t.geometry)) if t is not None else {}
            for _, r in c.iterrows():
                out[r.TrialCode] = (r.geometry, pts.get(r.TrialCode))
    return out


def write_gpkg(path, rows, geoms):
    import geopandas as gpd
    pad, pts = [], []
    for r in rows:
        g, p = geoms.get(r["TrialCode"], (None, None))
        if g is not None:
            pad.append({**r, "geometry": g})
        if p is not None:
            pts.append({**r, "geometry": p})
    if not pad:
        return 0
    gpd.GeoDataFrame(pad, crs="EPSG:3577").to_file(path, layer="paddocks", driver="GPKG")
    if pts:
        gpd.GeoDataFrame(pts, crs="EPSG:3577").to_file(path, layer="trials", driver="GPKG")
    return len(pad)


def draw(M, order, meta, grid, scope, png, vmin, vmax, label_mode):
    n = len(M)
    # Rows get thinner as they get more numerous, so a 20-row and a 200-row figure are both
    # legible without either being absurdly tall.
    rh = 0.30 if n <= 40 else (0.20 if n <= 90 else 0.13)
    fs = 8 if n <= 40 else (7 if n <= 90 else 5.5)
    fig = plt.figure(figsize=(15, max(5.0, rh * n + 2.6)))
    # Column 2 is an empty spacer reserving room for the row numbers. Without it the labels
    # are drawn underneath the colorbar axes, which is created later and paints over them —
    # the figure looks finished and is silently missing the one thing that links it to the
    # GeoPackage.
    gs = GridSpec(1, 4, width_ratios=[0.14, 1, 0.045, 0.035], wspace=0.015)
    axd, axh, axc = fig.add_subplot(gs[0]), fig.add_subplot(gs[1]), fig.add_subplot(gs[3])

    dendrogram(Z_CACHE[scope], orientation="left", ax=axd, no_labels=True,
               color_threshold=0, link_color_func=lambda k: "#555555")
    axd.invert_yaxis()
    axd.set_xticks([]); axd.set_yticks([])
    for sp in axd.spines.values():
        sp.set_visible(False)

    im = axh.imshow(M[order], aspect="auto", cmap="viridis", interpolation="nearest",
                    vmin=vmin, vmax=vmax,
                    extent=[grid[0], grid[-1], n - 0.5, -0.5])
    axh.yaxis.tick_right()
    axh.set_yticks(range(n))
    lab = []
    for row_i, i in enumerate(order):
        m = meta[i]
        lab.append(f"{m['label']}" if label_mode == "id" else f"{m['label']} {m['crop']}")
    axh.set_yticklabels(lab, fontsize=fs)
    for tick, i in zip(axh.get_yticklabels(), order):
        tick.set_color(GROUP_COLOUR[meta[i]["crop_group"]])
    axh.tick_params(axis="y", length=0)
    axh.set_xlabel("calendar day-of-year")
    axh.set_xticks(np.arange(0, 366, 30))

    counts = pd.Series([m["crop_group"] for m in meta]).value_counts()
    axh.set_title(
        f"Paddock-median CFI by day-of-year — {scope}\n"
        f"{n} paddocks: " + ", ".join(f"{k} {v}" for k, v in counts.items()) +
        "  |  rows clustered on the trace alone; number = row id in the GeoPackage",
        fontsize=11, weight="bold")
    axh.legend(handles=[Line2D([], [], color=c, lw=6, label=k)
                        for k, c in GROUP_COLOUR.items() if k in counts.index],
               loc="upper left", fontsize=8, framealpha=0.85)
    fig.colorbar(im, cax=axc, label="CFI (raw-DN scale, x10000)")
    fig.savefig(png, dpi=140, bbox_inches="tight")
    plt.close(fig)


def draw_profiles(M_by_panel, grid, png, min_n=4):
    """Small multiples: median CFI trace per crop group, one panel per year x state.

    The heatmaps show every paddock and are where a mislabelled row is spotted; this answers
    the different question of whether the groups separate AT ALL in a given season and region,
    and where in the calendar. A band that never opens is a season where CFI cannot do the job
    — which is worth seeing directly rather than inferring from a wall of heatmaps.
    """
    panels = [k for k in sorted(M_by_panel) if len(M_by_panel[k]) >= 2]
    if not panels:
        return
    ncol = 4
    nrow = int(np.ceil(len(panels) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.0 * ncol, 2.6 * nrow),
                             sharex=True, sharey=True, squeeze=False)
    for ax, key in zip(axes.ravel(), panels):
        for g, rows in sorted(M_by_panel[key].items()):
            A = np.vstack(rows)
            if len(A) < min_n:
                continue
            med = np.nanmedian(A, axis=0)
            lo, hi = np.nanpercentile(A, [25, 75], axis=0)
            ax.fill_between(grid, lo, hi, color=GROUP_COLOUR[g], alpha=0.16, lw=0)
            ax.plot(grid, med, color=GROUP_COLOUR[g], lw=1.6, label=f"{g} ({len(A)})")
        ax.set_title(", ".join(str(k) for k in key), fontsize=9)
        ax.legend(fontsize=6.5, frameon=False, loc="upper left")
        ax.set_xlim(60, 360)
        ax.grid(alpha=0.2, lw=0.5)
    for ax in axes.ravel()[len(panels):]:
        ax.set_visible(False)
    for ax in axes[-1]:
        ax.set_xlabel("day-of-year")
    for ax in axes[:, 0]:
        ax.set_ylabel("CFI (x10000)")
    fig.suptitle("Paddock-median CFI: median and interquartile band per crop group",
                 fontsize=13, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    fig.savefig(png, dpi=140)
    plt.close(fig)


Z_CACHE = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", nargs="+", required=True, help="glob(s) of paddock time series")
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--review", nargs="*", default=[], help="review_sites.csv file(s)")
    ap.add_argument("--chosen-dir", nargs="*", default=[], help="dirs of <stub>_chosen.gpkg")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--metric", default="cfi_pad_median")
    ap.add_argument("--group-by", nargs="+", default=["Year", "state"])
    ap.add_argument("--min-rows", type=int, default=8, help="skip thinner panels")
    ap.add_argument("--min-obs", type=int, default=15)
    ap.add_argument("--min-clear-frac", type=float, default=0.5)
    ap.add_argument("--max-compactness", type=float, default=6.0)
    ap.add_argument("--max-area-ha", type=float, default=300.0)
    ap.add_argument("--min-area-ha", type=float, default=5.0)
    ap.add_argument("--max-tree-frac", type=float, default=0.20)
    ap.add_argument("--label-mode", choices=["id", "id+crop"], default="id")
    ap.add_argument("--no-filter", action="store_true", help="skip the quality filter")
    ap.add_argument("--report", help="write a markdown summary here")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    ts = load_ts(args.ts, args.metric, args.min_clear_frac)
    lab = pd.read_csv(args.labeled)[["TrialCode", "Year", "state", "region", "crop"]] \
        .drop_duplicates("TrialCode")

    per = ts.groupby("TrialCode").agg(
        n_obs=("doy", "size"), area_ha_ts=("paddock_ha", "first"),
        match_rule=("match_rule", "first")).reset_index()
    d = per.merge(lab, on="TrialCode", how="left")
    rev = load_review(args.review)
    d = d.merge(rev.drop(columns=[c for c in ("match_rule",) if c in rev]),
                on="TrialCode", how="left")
    d["crop_group"] = d.crop.map(crop_group)

    n_before = len(d)
    if args.no_filter:
        reasons = {}
    else:
        d, reasons = quality_filter(d, args)
    print(f"\nquality filter: {n_before} -> {len(d)} trials")
    for k, v in reasons.items():
        print(f"  dropped {v:5d}  {k}")
    print(d.crop_group.value_counts().to_string())

    grid = np.arange(1, 366, DOY_STEP)
    ts = ts[ts.TrialCode.isin(set(d.TrialCode))]

    # One colour scale for every panel, from the pooled distribution: per-panel autoscaling
    # would make a flat wheat-only season look as vivid as a canola flowering peak.
    allv = ts[args.metric].dropna().values * REFL_SCALE
    vmin, vmax = np.percentile(allv, [2, 98])
    print(f"\nshared colour scale: {vmin:.0f} - {vmax:.0f} (2nd-98th percentile, n={len(allv)})")

    geom_cache, made, skipped, all_rows = {}, [], [], []
    profiles = {}
    for key, grp in d.groupby(args.group_by):
        key = key if isinstance(key, tuple) else (key,)
        scope = ", ".join(str(k) for k in key)
        if len(grp) < args.min_rows or grp.crop_group.nunique() < 2:
            skipped.append((scope, len(grp), grp.crop_group.nunique()))
            continue
        M, kept = build_matrix(ts, list(grp.TrialCode), args.metric, grid)
        if len(M) < args.min_rows:
            skipped.append((scope, len(M), grp.crop_group.nunique()))
            continue
        info = grp.set_index("TrialCode")
        Z, order = cluster_order(M)
        Z_CACHE[scope] = Z

        meta = []
        for i, t in enumerate(kept):
            r = info.loc[t]
            trace = M[i]
            pk = int(np.nanargmax(trace)) if np.isfinite(trace).any() else 0
            meta.append({
                "label": 0, "TrialCode": t, "crop": r.crop, "crop_group": r.crop_group,
                "Year": int(r.Year), "state": r.state, "region": r.region,
                "paddock_ha": float(r.area_ha_ts), "match_rule": r.match_rule,
                "n_obs": int(r.n_obs),
                "compactness": None if pd.isna(r.get("compactness")) else float(r.compactness),
                "tree_frac": None if pd.isna(r.get("tree_frac")) else float(r.tree_frac),
                "cfi_peak": None if not np.isfinite(trace).any() else float(np.nanmax(trace)),
                "peak_doy": int(grid[pk]),
            })
        # Numbered TOP TO BOTTOM as drawn, so row 1 is the top row of the figure — the number
        # is only useful if it can be counted off the image without decoding the leaf order.
        for row_i, i in enumerate(order):
            meta[i]["label"] = row_i + 1

        profiles[key] = {}
        for i, m in enumerate(meta):
            profiles[key].setdefault(m["crop_group"], []).append(M[i])

        tag = "_".join(str(k).replace(" ", "") for k in key)
        png = os.path.join(args.outdir, f"cfi_heatmap_{tag}_SENSITIVE.png")
        draw(M, order, meta, grid, scope, png, vmin, vmax, args.label_mode)

        rows = sorted(meta, key=lambda m: m["label"])
        pd.DataFrame(rows).to_csv(
            os.path.join(args.outdir, f"cfi_heatmap_{tag}_rows_SENSITIVE.csv"), index=False)

        n_geom = 0
        if args.chosen_dir:
            stubs = set(info.aoi_stub.dropna()) if "aoi_stub" in info else set()
            todo = stubs - set(geom_cache)
            if todo:
                geom_cache.update(chosen_geoms(todo, args.chosen_dir))
            for r in rows:                       # panel id, so one merged layer stays usable
                r["panel"] = tag
            n_geom = write_gpkg(
                os.path.join(args.outdir, f"cfi_heatmap_{tag}_SENSITIVE.gpkg"), rows,
                geom_cache)
            all_rows.extend(rows)

        # Does the trace alone recover the crop groups? Reported, not left to the eye.
        k = grp.crop_group.nunique()
        cl = fcluster(Z, k, criterion="maxclust")
        ct = pd.crosstab(pd.Series([m["crop_group"] for m in meta]), pd.Series(cl))
        purity = ct.max(axis=0).sum() / ct.values.sum()
        canola = [m for m in meta if m["crop_group"] == "Canola"]
        made.append({"scope": scope, "n": len(M), "purity": purity, "n_geom": n_geom,
                     "canola_peak_doy": int(np.median([m["peak_doy"] for m in canola]))
                     if canola else None,
                     **{f"n_{g}": int(v) for g, v in
                        pd.Series([m["crop_group"] for m in meta]).value_counts().items()}})
        print(f"  {scope:14s} {len(M):4d} rows, purity {purity:.0%}, {n_geom} polygons -> "
              f"{os.path.basename(png)}")

    summary = pd.DataFrame(made)
    if len(summary):
        summary.to_csv(os.path.join(args.outdir, "panels.csv"), index=False)
        draw_profiles(profiles, grid,
                      os.path.join(args.outdir, "cfi_group_profiles_SENSITIVE.png"))
    # One consolidated package as well as the per-panel ones: reviewing 40+ separate files in
    # QGIS means 40+ drag-and-drops, and `panel` + `label` together are still unique.
    if all_rows:
        allg = os.path.join(args.outdir, "cfi_heatmap_ALL_SENSITIVE.gpkg")
        n = write_gpkg(allg, all_rows, geom_cache)
        pd.DataFrame(all_rows).to_csv(
            os.path.join(args.outdir, "cfi_heatmap_ALL_rows_SENSITIVE.csv"), index=False)
        print(f"consolidated: {n} paddocks -> {os.path.basename(allg)}")

    print(f"\n{len(made)} figures -> {args.outdir}")
    if skipped:
        print(f"{len(skipped)} panels skipped (fewer than {args.min_rows} rows or one crop "
              f"group): " + ", ".join(f"{s}({n})" for s, n, _ in skipped[:12]))

    if args.report and len(summary):
        with open(args.report, "w") as f:
            f.write("# Paddock-median CFI heatmaps — canola vs wheat vs other\n\n")
            f.write(f"- metric `{args.metric}`, {len(made)} panels, "
                    f"{int(summary.n.sum())} paddocks\n")
            f.write(f"- shared colour scale {vmin:.0f}-{vmax:.0f} (CFI x10000)\n")
            f.write(f"- quality filter: {n_before} -> {len(d)} trials\n\n")
            for k, v in reasons.items():
                f.write(f"  - dropped {v}: {k}\n")
            f.write("\n| panel | rows | Canola | Wheat | Other | cluster purity | "
                    "canola peak DOY |\n|---|---|---|---|---|---|---|\n")
            def cnt(r, g):        # the column exists but is NaN for a panel lacking that
                v = r.get(f"n_{g}")   # group; "nan" in a count column reads as a bug
                return 0 if pd.isna(v) else int(v)

            for _, r in summary.iterrows():
                doy = "-" if pd.isna(r["canola_peak_doy"]) else int(r["canola_peak_doy"])
                f.write(f"| {r['scope']} | {r['n']} | {cnt(r, 'Canola')} | "
                        f"{cnt(r, 'Wheat')} | {cnt(r, 'Other')} | "
                        f"{r['purity']:.0%} | {doy} |\n")
        print(f"report -> {args.report}")


if __name__ == "__main__":
    main()
