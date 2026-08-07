#!/usr/bin/env python3
"""
Render trial/paddock matches as review contact sheets — for a human in QGIS, or for Claude.

One PNG per site would be the obvious design and is the wrong one. A reviewer (human or
model) judges these far faster in a grid, and for a model each image read costs tokens, so
**many sites per image** is what makes reviewing thousands affordable. Default 6 per sheet.

Each panel: Sentinel-2 RGB near flowering, every AOI polygon in magenta, the CHOSEN polygon
in cyan, the trial point in yellow, and the automatic flags in the title.

    # worst-first, the order make_review_layers.py already sorted into
    python3 review_render.py --review .../review_sites.csv --polydir .../samgeo/full \
        --outdir .../review_sheets --n 60

    # or specific trials
    python3 review_render.py --review ... --polydir ... --trials CODE1 CODE2

Reads the same review_sites.csv the human annotates, so model and human see identical panels
and their verdicts are directly comparable — which is the point of having both.
"""
import argparse
import os

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402

FMASK_CLEAR = 1
NODATA = -999
REFL_SCALE = 10000.0
PRODUCTS = ["ga_s2am_ard_3", "ga_s2bm_ard_3", "ga_s2cm_ard_3"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", required=True, help="review_sites.csv")
    ap.add_argument("--sites", required=True, help="sites csv with lat/lon/sow")
    ap.add_argument("--polydir", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--n", type=int, default=24, help="how many sites (worst-first)")
    ap.add_argument("--trials", nargs="*", help="explicit TrialCodes instead")
    ap.add_argument("--per-sheet", type=int, default=12)
    ap.add_argument("--context-m", type=float, default=2000.0)
    ap.add_argument("--max-px", type=int, default=1560,
                    help="cap the sheet's long edge. A vision model's cost for an image is "
                         "roughly (w*h)/750 tokens and inputs are downscaled to ~1568 px "
                         "anyway, so rendering larger costs quota and buys nothing.")
    args = ap.parse_args()

    os.environ.setdefault("PROJ_NETWORK", "OFF")
    import datacube
    import geopandas as gpd
    from shapely.geometry import Point, box

    rev = pd.read_csv(args.review)
    sites = pd.read_csv(args.sites).drop_duplicates("TrialCode").set_index("TrialCode")
    if args.trials:
        rev = rev[rev.TrialCode.isin(args.trials)]
    else:
        rev = rev.head(args.n)          # already sorted worst-first
    dc = datacube.Datacube(app="review_render")
    os.makedirs(args.outdir, exist_ok=True)

    panels = []
    for _, r in rev.iterrows():
        code = r["TrialCode"]
        if code not in sites.index:
            continue
        s = sites.loc[code]
        pt = gpd.GeoSeries([Point(float(s.lon), float(s.lat))],
                           crs="EPSG:4326").to_crs("EPSG:3577").iloc[0]
        half = args.context_m / 2
        # Flowering-ish window, where canola is visually obvious in RGB.
        t0 = (pd.to_datetime(s.sow) + pd.Timedelta(days=110)).strftime("%Y-%m-%d")
        t1 = (pd.to_datetime(s.sow) + pd.Timedelta(days=200)).strftime("%Y-%m-%d")
        ds = dc.load(product=PRODUCTS, x=(pt.x - half, pt.x + half),
                     y=(pt.y - half, pt.y + half), crs="EPSG:3577", time=(t0, t1),
                     measurements=["nbart_red", "nbart_green", "nbart_blue", "oa_fmask"],
                     output_crs="EPSG:3577", resolution=(-10, 10), group_by="solar_day")
        if ds.sizes.get("time", 0) == 0:
            continue
        clear = (ds["oa_fmask"] == FMASK_CLEAR).sum(dim=("x", "y"))
        sc = ds.isel(time=int(clear.argmax()))
        m = sc["oa_fmask"] == FMASK_CLEAR
        bands = [(sc[n].where((sc[n] != NODATA) & m).astype("float32") / REFL_SCALE).values
                 for n in ("nbart_red", "nbart_green", "nbart_blue")]
        rgb = np.dstack(bands)
        rgb = np.clip(rgb / max(np.nanpercentile(rgb, 98), 1e-6), 0, 1)
        b = ds.geobox.extent.boundingbox
        extent = [b.left, b.right, b.bottom, b.top]

        p = os.path.join(args.polydir, f"{r['aoi_stub']}_filt.gpkg")
        poly = gpd.read_file(p).to_crs("EPSG:3577") if os.path.exists(p) else None
        # The CHOSEN polygon must come from the layer that recorded the decision. Recomputing
        # `poly.contains(pt)` here silently draws nothing for every `nearest_*` match — i.e.
        # exactly the 36 % of trials most in need of review would show no selection at all.
        ch = os.path.join(os.path.dirname(args.review), f"{r['aoi_stub']}_chosen.gpkg")
        chosen = None
        if os.path.exists(ch):
            g = gpd.read_file(ch).to_crs("EPSG:3577")
            chosen = g[g.TrialCode == code]
        aoi = box(*extent[:1] + extent[2:3] + extent[1:2] + extent[3:4]) \
            if False else box(extent[0], extent[2], extent[1], extent[3])
        panels.append({"code": code, "rgb": rgb, "extent": extent, "pt": pt,
                       "poly": poly[poly.intersects(aoi)] if poly is not None else None,
                       "chosen": chosen,
                       # An empty flags cell reads back from CSV as NaN, which would print
                       # "risk 0: nan" on the cleanest panels.
                       "flags": r.get("flags") if isinstance(r.get("flags"), str) else "none",
                       "crop": r.get("crop", ""),
                       "risk": r.get("risk", ""), "area": r.get("area_ha", "")})
        print(f"rendered {code}", flush=True)

    per = args.per_sheet
    manifest = []
    for k in range(0, len(panels), per):
        chunk = panels[k:k + per]
        # Keep sheets roughly square: more panels per sheet is cheaper to review (one image
        # read covers more sites) but each panel gets smaller, so legibility sets the limit.
        ncol = int(np.ceil(np.sqrt(len(chunk))))
        nrow = int(np.ceil(len(chunk) / ncol))
        fig, axes = plt.subplots(nrow, ncol, figsize=(5.2 * ncol, 5.4 * nrow), squeeze=False)
        for ax in axes.ravel():
            ax.axis("off")
        for i, p in enumerate(chunk):
            ax = axes[i // ncol][i % ncol]
            ax.axis("on")
            ax.imshow(p["rgb"], extent=p["extent"], origin="upper")
            if p["poly"] is not None and len(p["poly"]):
                p["poly"].boundary.plot(ax=ax, color="#FF00FF", lw=1.0)
            if p["chosen"] is not None and len(p["chosen"]):
                p["chosen"].boundary.plot(ax=ax, color="cyan", lw=2.6)
            ax.plot(p["pt"].x, p["pt"].y, "o", ms=9, mfc="yellow", mec="black", mew=1.4)
            ax.set_xlim(p["extent"][0], p["extent"][1])
            ax.set_ylim(p["extent"][2], p["extent"][3])
            ax.set_xticks([]); ax.set_yticks([])
            ax.set_title(f"{p['code']} ({p['crop']}, {p['area']} ha)\n"
                         f"risk {p['risk']}: {p['flags']}", fontsize=9)
        fig.tight_layout()
        out = os.path.join(args.outdir, f"review_sheet_{k//per:03d}_SENSITIVE.png")
        w_in, h_in = fig.get_size_inches()
        dpi = args.max_px / max(w_in, h_in)
        fig.savefig(out, dpi=dpi)
        plt.close(fig)
        # Manifest: sheet -> panel position -> TrialCode. A reviewer (human or model) reading
        # codes off the rendered title can silently misattribute a verdict to the wrong trial;
        # with this the mapping is data, and panel order is left-to-right, top-to-bottom.
        for i, p in enumerate(chunk):
            manifest.append({"sheet": os.path.basename(out), "panel": i + 1,
                             "row": i // ncol + 1, "col": i % ncol + 1,
                             "TrialCode": p["code"], "crop": p["crop"],
                             "area_ha": p["area"], "flags": p["flags"]})
        print(f"-> {out} ({int(w_in*dpi)}x{int(h_in*dpi)} px, "
              f"~{int(w_in*dpi*h_in*dpi/750)} image tokens)")

    if manifest:
        mpath = os.path.join(args.outdir, "sheet_manifest.csv")
        pd.DataFrame(manifest).to_csv(mpath, index=False)
        print(f"-> {mpath}")


if __name__ == "__main__":
    main()
