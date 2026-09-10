#!/usr/bin/env python3
"""
Score the mapped crop composition against ABS broadacre area by SA2 — the first validation in
this project that depends on neither NVT nor AgriWebb.

WHAT IS COMPARED, AND WHY IT WAS ORIGINALLY A SHARE AND NOT AN AREA (`--aois` lifts this for a
large footprint — see "AREA" below). The demo maps cover 12 x 12 km boxes; a rural SA2 runs to
thousands of km2. Mapped hectares can therefore never equal ABS hectares, and
any report of "we mapped 3,000 ha, ABS says 180,000 ha" is measuring the size of the box, not the
quality of the map. What *is* comparable is **composition**: of the land that carries a winter
crop, what share is canola? That is scale-free, so a representative 144 km2 sample of an SA2
should reproduce it — and it is exactly the quantity a crop-type map is claiming to know.

Grazing is excluded from both sides. ABS counts sown area only, and per
`output/PRESENCE_ONLY_LABELS.md` the Grazing class is being retired anyway; including it would
compare a crop-share against a crop-and-pasture-share.

THE SAMPLING CAVEAT IS THE WHOLE STORY AT THIS SCALE. A 12 km box inside a large SA2 is one
sample of that SA2's paddock mix, and paddock mix is spatially clustered — a box that happens to
sit on a run of canola will read high whatever the model does. Read a disagreement on a small
footprint as noise until a larger one says otherwise. Measured 2026-08-25: the demo boxes, at a
1.56 % sample, reported a 4.6-point canola error; the 102 km run over censused SA2s reported
12.2, negative in 14 of 15 SA2-years. The small number was not a noisy version of the large one.

DO NOT USE `sample_frac` AS THE FOOTPRINT. It is mapped crop ha / ABS crop ha, so it *rises* when
the model over-calls crop — a map that hallucinates canola scores as though it had better
coverage. `cover_frac`, from `--aois`, is the real thing: mapped ground / SA2 ground, and it
cannot be moved by the model at all. `sample_frac` is kept in the table only because the ratio
between the two is itself informative.

AREA, ONCE THE BOX IS BIG ENOUGH. Give `--aois` and the tile grid is reconstructed exactly
(true 3 km Albers squares, `map_regions.py`), intersected with each SA2, and the covered
fraction reported per row. Where that fraction is high the SA2 has been censused rather than
sampled, and mapped hectares can be held against ABS hectares scaled to the covered part. This
is the only test that can see a map which calls twice as much land crop as was sown — every
share is blind to it.

    python3 abs_compare.py --pred '.../map100/pred/*.gpkg' --abs .../abs/abs_broadacre_area.csv \
        --sa2 .../abs/SA2_2021_AUST_GDA2020.shp --abares .../abs/abares_state_area.csv \
        --aois .../map100/aois.csv --out ../../output/ABS_COMPARISON_100km.md

It reads every prediction GeoPackage in full, so it takes ~5 min on a quiet login node and ~20 on
a busy one. Nothing here needs a PBS job; it peaks at ~1.3 GB.
"""
import argparse
import glob

import numpy as np
import pandas as pd

CROPS = ["Canola", "Cereal", "Legume"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True, help="glob of prediction gpkgs")
    ap.add_argument("--abs", required=True)
    ap.add_argument("--sa2", required=True)
    ap.add_argument("--abares", help="abares_state_area.csv — the second reference series")
    ap.add_argument("--gate-sweep", nargs="*", type=float,
                    default=[0.25, 0.30, 0.35, 0.40, 0.45, 0.50],
                    help="NDVI-amplitude thresholds to report. The crop-presence gate is a knob, "
                         "and a single chosen value hides how much the answer depends on it. "
                         "`ndvi_amp` is stored per polygon, so the whole sweep is a filter on "
                         "the existing output — no re-inference. NOTE: this is a SENSITIVITY "
                         "table, not a fitting procedure. Choosing the threshold that best "
                         "matches ABS would make ABS a training set and destroy the one "
                         "independent validation this project has; the gate must be set on "
                         "presence recall and ABS read afterwards.")
    ap.add_argument("--min-abs-ha", type=float, default=5000.0,
                    help="drop SA2-years whose ABS sown area is below this. The cover filter "
                         "alone is not enough: a peri-urban SA2 can be 100 %% inside the box "
                         "while carrying 500 ha of crop, and its share is then computed over a "
                         "few paddocks. This drops SA2s that are not cropping regions, which is "
                         "a judgement about the reference data and not about the map.")
    ap.add_argument("--min-cover", type=float, default=0.5,
                    help="fraction of an SA2 the mapped box must cover before its row is used "
                         "for the headline numbers. Needs --aois. A partly-covered SA2 is a "
                         "sample of its paddock mix and paddock mix is spatially clustered; a "
                         "nearly-covered one is a census of it, and only the second can carry "
                         "a claim about the map rather than about where the box landed.")
    ap.add_argument("--aois", help="aois.csv for the run — the tile centres. With it the "
                                   "report can measure how much of each SA2 the mapped box "
                                   "actually covers, which turns the comparison from a share "
                                   "against a share into an area against an area.")
    ap.add_argument("--count-as-classified", nargs="*", default=[],
                    help="abstain reasons that still carry a class and count as classified. The 9 km run "
                         "predicts every class and only FLAGS a phenology-shape failure as no_crop_shape "
                         "(PROJ_NOTES 2026-09-07 (2a)); pass no_crop_shape to score the map as published "
                         "rather than with the rejected shape gate applied.")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-mapped-ha", type=float, default=100.0,
                    help="drop SA2-years with less mapped crop than this; a share computed over "
                         "a handful of paddocks is noise with a decimal point on it")
    args = ap.parse_args()

    import geopandas as gpd

    files = sorted(glob.glob(args.pred))
    P = pd.concat([gpd.read_file(f) for f in files], ignore_index=True)
    P = gpd.GeoDataFrame(P, crs=gpd.read_file(files[0]).crs)
    P["region"] = P.stub.str.rsplit("_", n=2).str[0]
    if args.count_as_classified:
        flag = P.abstain_reason.isin(args.count_as_classified) & P.pred.notna()
        print(f"counting {int(flag.sum()):,} polygons flagged {args.count_as_classified} as classified")
        P.loc[flag, "abstain_reason"] = ""
    print(f"{len(files)} files, {len(P)} paddocks, years {sorted(P.year.unique())}")

    S = gpd.read_file(args.sa2)[["SA2_CODE21", "SA2_NAME21", "STE_NAME21", "geometry"]]
    S = S.to_crs(P.crs)
    S["sa2_ha"] = S.area / 1e4

    # Join on the paddock CENTROID, not the polygon: a polygon straddling an SA2 boundary would
    # otherwise be counted in both, inflating every share it touches.
    C = P.copy()
    C["geometry"] = C.geometry.centroid
    J = gpd.sjoin(C, S, how="inner", predicate="within")
    print(f"{len(J)} paddocks fell inside an SA2 ({100 * len(J) / len(P):.1f} %)")

    # COVERAGE FIRST, COMPOSITION SECOND. A composition that looks right over 30 % of the ground
    # is a different claim from the same composition over 90 %, and the abstain path makes that
    # difference explicit and measurable rather than leaving it as unexplained white space.
    cov_lines = []
    if "abstain_reason" in J.columns:
        cls = J.abstain_reason.fillna("") == ""
        cov_lines = ["", "## Coverage", "",
                     f"- **{int(cls.sum()):,} of {len(J):,} polygons classified "
                     f"({100 * cls.mean():.1f} %)**, "
                     f"{100 * J.loc[cls, 'area_ha'].sum() / J.area_ha.sum():.1f} % by area", "",
                     "| reason not classified | polygons | ha |", "|---|---|---|"]
        for reason, g in J[~cls].groupby("abstain_reason"):
            cov_lines.append(f"| `{reason}` | {len(g):,} | {g.area_ha.sum():,.0f} |")
        # BY YEAR, because a gate that is measuring anything real should move with the season.
        # A drought year should reject more paddocks than a wet one; if the classified share is
        # flat across nine years including a failed one, the gate is keying on something that is
        # not the crop.
        # The observation columns are here so the seasonal reading can be checked rather than
        # assumed: a year can classify badly because the satellite saw little of it, or because
        # there was little crop to see, and only `n_obs`/`clear_frac` against `ndvi_amp`
        # separates those.
        cov_lines += ["", "| year | polygons | classified | by area | `no_crop_signal` | "
                          "mean n_obs | mean clear_frac | mean ndvi_amp |",
                      "|---|---|---|---|---|---|---|---|"]
        for y, g in J.groupby("year"):
            c = g.abstain_reason.fillna("") == ""
            cov_lines.append(
                f"| {int(y)} | {len(g):,} | {100 * c.mean():.1f} % | "
                f"{100 * g.loc[c, 'area_ha'].sum() / g.area_ha.sum():.1f} % | "
                f"{100 * (g.abstain_reason.fillna('') == 'no_crop_signal').mean():.1f} % | "
                f"{g.n_obs.mean():.1f} | {g.clear_frac.mean():.2f} | {g.ndvi_amp.mean():.2f} |")
        cov_lines.append("")

    # HOW MUCH OF EACH SA2 DID WE ACTUALLY LOOK AT? Without this the only available measure of
    # footprint is `sample_frac` = mapped crop / ABS crop, which is not a footprint at all: it
    # moves when the model over-calls crop, so a map that hallucinates canola looks like a map
    # with better coverage. The tile grid is known exactly — true 3 km squares on an integer
    # Albers grid (`map_regions.py`) — so intersecting it with the SA2 gives the real number.
    cover = None
    if args.aois:
        from shapely.geometry import box
        from shapely.ops import unary_union
        A_t = pd.read_csv(args.aois)
        # `region` names the run's area of interest, and it is here only to keep two runs' grid
        # indices apart in the dedupe below — the Riverina list repeats each tile once per year,
        # so (region, grid_r, grid_c) is what makes a tile unique. The NATIONAL list has no such
        # column: it is one continent-wide grid whose grid_r/grid_c are NLUM raster indices,
        # already globally unique (99,465 rows, 99,465 distinct pairs). Derive it from the stub
        # exactly as the polygons are at the top of main(), so the dedupe key keeps its meaning
        # for both shapes of run. Without this the national run dies here with
        # `KeyError: Index(['region'])` AFTER the ~5 minute read of every prediction
        # GeoPackage — an expensive place to discover a missing column.
        if "region" not in A_t.columns:
            A_t["region"] = A_t.stub.str.rsplit("_", n=2).str[0]
        A_t = A_t.drop_duplicates(["region", "grid_r", "grid_c"])
        fwd = __import__("pyproj").Transformer.from_crs("EPSG:4326", "EPSG:3577", always_xy=True)
        x, y = fwd.transform(A_t.lon.values, A_t.lat.values)
        h = A_t.half_m.values
        foot = gpd.GeoDataFrame(
            {"region": A_t.region.values},
            geometry=[box(xi - hi, yi - hi, xi + hi, yi + hi) for xi, yi, hi in zip(x, y, h)],
            crs="EPSG:3577").to_crs(S.crs)
        foot = gpd.GeoDataFrame(geometry=[unary_union(foot.geometry.values)], crs=S.crs)
        ov = gpd.overlay(S, foot, how="intersection")
        ov["covered_ha"] = ov.area / 1e4
        cover = ov.groupby("SA2_CODE21").agg(covered_ha=("covered_ha", "sum"),
                                             sa2_ha=("sa2_ha", "first"))
        cover["cover_frac"] = cover.covered_ha / cover.sa2_ha
        print(f"footprint touches {len(cover)} SA2s; "
              f"{int((cover.cover_frac >= 0.5).sum())} of them >= 50 % covered")

    crop = J[J.pred.isin(CROPS)]
    mapped = (crop.pivot_table(index=["SA2_CODE21", "SA2_NAME21", "STE_NAME21", "year"],
                               columns="pred", values="area_ha", aggfunc="sum")
                  .reindex(columns=CROPS).fillna(0.0).reset_index())
    mapped["mapped_crop_ha"] = mapped[CROPS].sum(axis=1)

    A = pd.read_csv(args.abs)
    A = A[A.level == "SA2"]
    abs_w = (A.pivot_table(index=["region", "crop_year"], columns="group", values="area_ha",
                           aggfunc="sum").reindex(columns=CROPS).fillna(0.0).reset_index())
    abs_w["abs_crop_ha"] = abs_w[CROPS].sum(axis=1)

    m = mapped.merge(abs_w, left_on=["SA2_CODE21", "year"], right_on=["region", "crop_year"],
                     suffixes=("_map", "_abs"))
    m = m[(m.mapped_crop_ha >= args.min_mapped_ha) & (m.abs_crop_ha >= args.min_abs_ha)]
    m["sample_frac"] = m.mapped_crop_ha / m.abs_crop_ha
    for c in CROPS:
        m[f"{c}_share_map"] = m[f"{c}_map"] / m.mapped_crop_ha
        m[f"{c}_share_abs"] = m[f"{c}_abs"] / m.abs_crop_ha
    m["canola_err"] = m.Canola_share_map - m.Canola_share_abs
    if cover is not None:
        m = m.merge(cover[["cover_frac", "covered_ha"]], left_on="SA2_CODE21", right_index=True,
                    how="left")
        # If crop were spread evenly through the SA2, this is how many hectares of it should sit
        # inside the part we mapped. Comparing that against the mapped hectares is an AREA test,
        # which the share test cannot do — a map can get every share right while calling twice
        # as much land crop as exists.
        m["expected_crop_ha"] = m.abs_crop_ha * m.cover_frac
        m["area_ratio"] = m.mapped_crop_ha / m.expected_crop_ha

    lines = ["# Mapped crop composition vs ABS broadacre area, by SA2", "",
             "Generated by `abs_compare.py`. Composition is the primary comparison: a box that "
             "samples an SA2 can never match its hectares, so a share is the only scale-free "
             "thing to check.", ""]
    if cover is not None:
        lines += ["**With `--aois` the footprint is known exactly**, so where the box nearly "
                  "covers an SA2 the area comparison becomes legitimate too — and it asks a "
                  "question the share comparison cannot: how much land does the map call crop? "
                  "Doubling every class leaves every share untouched.", ""]
    lines += cov_lines
    if not len(m):
        lines += ["**No SA2-year matched.** Either the demo years predate the ABS series "
                  "(it starts 2022-23) or no SA2 carried enough mapped crop.", ""]
    else:
        # The rows the headline is allowed to speak for. Where the footprint is known, a
        # partly-covered SA2 stays in the table but out of the headline: its number describes
        # where the box landed as much as it describes the map.
        w = m[m.cover_frac >= args.min_cover] if cover is not None else m
        if cover is not None:
            lines += [f"- **{len(w)} of {len(m)} SA2-years are at least "
                      f"{100 * args.min_cover:.0f} % covered by the mapped box** — the headline "
                      f"numbers below use only those; the full table follows",
                      f"- canola share over those: mapped **{100 * w.Canola_share_map.median():.1f} %** "
                      f"vs ABS **{100 * w.Canola_share_abs.median():.1f} %**, "
                      f"median absolute error **{100 * w.canola_err.abs().median():.1f} points**, "
                      f"median signed error **{100 * w.canola_err.median():+.1f}**",
                      f"- r = **{w.Canola_share_map.corr(w.Canola_share_abs):.2f}** (n = {len(w)})",
                      ""]
        lines += [f"- {len(m)} SA2-years matched, across {m.SA2_CODE21.nunique()} SA2s and "
                  f"years {sorted(m.year.unique())}",
                  f"- median sample fraction: **{100 * m.sample_frac.median():.2f} %** of the "
                  f"SA2's ABS crop area falls inside the mapped box",
                  f"- canola share, mapped vs ABS: median **{100 * m.Canola_share_map.median():.1f} %** "
                  f"vs **{100 * m.Canola_share_abs.median():.1f} %**",
                  f"- **median absolute error on canola share: "
                  f"{100 * m.canola_err.abs().median():.1f} points**",
                  f"- correlation across SA2-years: **r = {m.Canola_share_map.corr(m.Canola_share_abs):.2f}** "
                  f"(n = {len(m)})", "",
                  "| SA2 | state | year | cover | mapped crop ha | ABS crop ha | sample | canola map | canola ABS | error |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in m.sort_values(["year", "SA2_NAME21"]).iterrows():
            cv = f"{100 * r.cover_frac:.0f} %" if cover is not None else "-"
            lines.append(
                f"| {r.SA2_NAME21} | {r.STE_NAME21} | {int(r.year)} | {cv} | {r.mapped_crop_ha:,.0f} | "
                f"{r.abs_crop_ha:,.0f} | {100 * r.sample_frac:.2f} % | "
                f"{100 * r.Canola_share_map:.1f} % | {100 * r.Canola_share_abs:.1f} % | "
                f"{100 * r.canola_err:+.1f} |")
        lines += ["", "### Cereal and legume shares", "",
                  f"Medians over {'the ' + str(len(w)) + ' well-covered SA2-years' if cover is not None else 'all matched SA2-years'}.", "",
                  "| | mapped (median) | ABS (median) |", "|---|---|---|"]
        for c in CROPS:
            lines.append(f"| {c} | {100 * w[f'{c}_share_map'].median():.1f} % | "
                         f"{100 * w[f'{c}_share_abs'].median():.1f} % |")

        # AREA, NOT SHARE. Only possible where the box nearly covers the SA2 — which is exactly
        # what `--aois` measures. A share comparison is blind to a map that calls twice as much
        # land crop as exists, because doubling every class leaves every share unchanged.
        if cover is not None and len(w):
            lines += ["", "### Area, not just composition", "",
                      f"SA2-years where the mapped box covers at least "
                      f"{100 * args.min_cover:.0f} % of the SA2. `expected` spreads the SA2's "
                      f"ABS sown area evenly over the covered fraction; `ratio` above 1 means "
                      f"**more land was called crop than ABS says was sown**.", "",
                      "| SA2 | year | cover | covered ha | mapped crop ha | crop share of "
                      "covered land | ABS crop share of SA2 | ratio |",
                      "|---|---|---|---|---|---|---|---|"]
            for _, r in w.sort_values(["year", "SA2_NAME21"]).iterrows():
                lines.append(f"| {r.SA2_NAME21} | {int(r.year)} | {100 * r.cover_frac:.0f} % | "
                             f"{r.covered_ha:,.0f} | {r.mapped_crop_ha:,.0f} | "
                             f"{100 * r.mapped_crop_ha / r.covered_ha:.0f} % | "
                             f"{100 * r.abs_crop_ha / (r.covered_ha / r.cover_frac):.0f} % | "
                             f"{r.area_ratio:.2f} |")
            # abstain_reason, not pred, is authoritative for "cleanly classified" -- since
            # 2026-09-07 a class in --shape-gate-skip-classes can carry a non-null pred AND a
            # non-empty abstain_reason (the label is kept, the gate failure still recorded), so
            # pred.notna() alone would undercount how much area is actually still gated.
            clean = J.abstain_reason.fillna("") == ""
            lines += ["", f"**Median ratio {w.area_ratio.median():.2f}** over {len(w)} "
                          f"SA2-years — and the classifier abstained on "
                          f"{100 * (1 - J.loc[clean, 'area_ha'].sum() / J.area_ha.sum()):.0f} % "
                          f"of the mapped area besides, so this is a floor on how much land the "
                          f"map calls crop.", ""]
            # THE SHARE RESULT AND THE AREA RESULT ARE THE SAME RESULT, AND THIS SEPARATES THEM.
            # If the map calls `ratio` times as much land crop as was sown, then even a perfect
            # classifier reads a share of ABS_share / ratio for any crop the excess land does
            # not contain — the extra hectares are in the denominator. Subtracting that from the
            # observed share leaves the hectares of excess land each class actually absorbed,
            # and those residuals must sum to 1 - 1/ratio. So this decomposes one number into
            # "diluted by the over-call" and "wrongly labelled this crop", which have completely
            # different remedies.
            ratio = float(w.area_ratio.median())
            lines += ["", "### The share deficit and the area over-call are one result", "",
                      f"The map calls **{ratio:.2f}x** as much land crop as ABS says was sown "
                      f"(median over the same rows). Those extra hectares sit in the denominator "
                      f"of every share. `diluted` is the share a **perfect** classifier would "
                      f"report on this footprint — the ABS share divided by the over-call — and "
                      f"`absorbed` is what is left over: the share of the map that is excess "
                      f"land carrying this label. The `absorbed` column must sum to "
                      f"**{100 * (1 - 1 / ratio):.0f} points**, which is the excess itself.", "",
                      "| | ABS | diluted | mapped | absorbed |", "|---|---|---|---|---|"]
            for c in CROPS:
                ref = float(w[f"{c}_share_abs"].median())
                got = float(w[f"{c}_share_map"].median())
                lines.append(f"| {c} | {100 * ref:.1f} % | {100 * ref / ratio:.1f} % | "
                             f"{100 * got:.1f} % | **{100 * (got - ref / ratio):+.1f}** |")
            lines.append("")

    # ARGMAX OR SIGNAL? A class share can come out low for two quite different reasons: the
    # model may not see the crop, or it may see it and still not pick it, because argmax over a
    # 3-class softmax hands every marginal paddock to whichever class the training set made most
    # common. Area-weighted mean probability against area-weighted argmax share separates them,
    # and they have different fixes — more/better features against a prior correction. NOTE this
    # is a DIAGNOSTIC: re-weighting the priors to match ABS would make ABS a training set.
    if len(m) and {"p_canola", "p_cereal", "p_legume"} <= set(J.columns):
        cl = J[J.pred.isin(CROPS)].copy()
        if cover is not None and len(w):
            keys = set(zip(w.SA2_CODE21, w.year))
            cl = cl[[k in keys for k in zip(cl.SA2_CODE21, cl.year)]]
        if len(cl):
            a = cl.area_ha
            lines += ["", "### Argmax share against mean probability", "",
                      "Area-weighted, over the same polygons. **A gap between the two columns "
                      "is a decision-rule problem; agreement between them means the model "
                      "genuinely does not see the crop.**", "",
                      "| | argmax share | mean probability | ABS |", "|---|---|---|---|"]
            for c in CROPS:
                soft = float((cl[f"p_{c.lower()}"] * a).sum() / a.sum())
                hard = float(a[cl.pred == c].sum() / a.sum())
                ref = float(w[f"{c}_share_abs"].median()) if cover is not None and len(w) \
                    else float(m[f"{c}_share_abs"].median())
                lines.append(f"| {c} | {100 * hard:.1f} % | {100 * soft:.1f} % | "
                             f"{100 * ref:.1f} % |")
            lines.append("")

    # HOW SENSITIVE IS ALL OF THIS TO THE GATE? Every threshold is applied to the same polygons,
    # so the rows move between "classified" and "abstained" and nothing is re-computed.
    if "ndvi_amp" in J.columns and args.gate_sweep and len(m):
        sweep = []
        for t in sorted(args.gate_sweep):
            gated = J[(J.abstain_reason.fillna("").isin(["", "no_crop_signal"])) &
                      (J.ndvi_amp >= t) & (J.pred.notna() | (J.abstain_reason == "no_crop_signal"))]
            gated = gated[gated.pred.isin(CROPS)]
            if not len(gated):
                continue
            mp = (gated.pivot_table(index=["SA2_CODE21", "year"], columns="pred",
                                    values="area_ha", aggfunc="sum")
                       .reindex(columns=CROPS).fillna(0.0))
            tot = mp.sum(axis=1)
            share = mp.div(tot, axis=0)
            # Same keys, different names: the mapped side is indexed (SA2_CODE21, year) and
            # the ABS side (region, crop_year). pandas refuses to join MultiIndexes whose names
            # do not overlap, so rename before joining rather than resetting and merging.
            abs_i = abs_w.set_index(["region", "crop_year"])
            abs_share = abs_i[CROPS].div(abs_i.abs_crop_ha, axis=0)
            abs_share.index.names = share.index.names
            j = share.join(abs_share, rsuffix="_abs", how="inner")
            if not len(j):
                continue
            sweep.append({"gate": t,
                          "classified_ha": tot.sum(),
                          "canola_err": float((j.Canola - j.Canola_abs).abs().median()),
                          "legume_err": float((j.Legume - j.Legume_abs).abs().median())})
        if sweep:
            lines += ["", "## Sensitivity to the crop-presence gate", "",
                      "Same polygons, different NDVI-amplitude thresholds. **This is a "
                      "sensitivity table, not a fitting procedure** — choosing the gate that "
                      "best matches ABS would make ABS a training set and destroy the only "
                      "independent validation this project has.", "",
                      "| gate | classified ha | canola share error | legume share error |",
                      "|---|---|---|---|"]
            for r in sweep:
                lines.append(f"| {r['gate']:.2f} | {r['classified_ha']:,.0f} | "
                             f"{100 * r['canola_err']:.1f} pts | {100 * r['legume_err']:.1f} pts |")
            lines.append("")

    # HOW MUCH DO THE TWO AGENCIES AGREE WITH EACH OTHER? This is the floor on how precisely any
    # map can be validated: a 5-point disagreement with ABS means nothing if ABS and ABARES
    # disagree by 8. It has to be stated before any map error is called large or small.
    if args.abares:
        B = pd.read_csv(args.abares)
        B = B[B.state == "Australia"].pivot_table(index="crop_year", columns="group",
                                                  values="area_ha", aggfunc="sum")
        Anat = (A[A.level == "SA2"].pivot_table(index="crop_year", columns="group",
                                                values="area_ha", aggfunc="sum"))
        yrs = sorted(set(B.index) & set(Anat.index))
        lines += ["", "## The two reference series against each other", "",
                  "National area sown (ha). Neither is ground truth; the gap between them is the "
                  "precision floor for judging any map.", "",
                  "| year | group | ABS | ABARES | ABS/ABARES |", "|---|---|---|---|---|"]
        gaps = []
        for y in yrs:
            for g in CROPS:
                a, b = Anat.loc[y, g], B.loc[y, g]
                gaps.append(abs(a / b - 1))
                lines.append(f"| {y} | {g} | {a:,.0f} | {b:,.0f} | {a / b:.2f} |")
        lines += ["", f"**Median disagreement between ABS and ABARES: "
                      f"{100 * float(np.median(gaps)):.1f} %.** Any map-vs-reference difference "
                      f"smaller than this is inside the noise between two official sources and "
                      f"should not be reported as a map error.", ""]

    open(args.out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines[:16]))
    print(f"\n-> {args.out}")


if __name__ == "__main__":
    main()
