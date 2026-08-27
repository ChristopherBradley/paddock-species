#!/usr/bin/env python3
"""
Pull ABS broadacre crop area by SA2 — the independent, presence-free validation for the national
map.

WHY THIS DATASET. Every validation this project has run so far is against labels that also
trained the model (NVT) or against a negative class the labels cannot support (AgriWebb — see
`output/PRESENCE_ONLY_LABELS.md`). ABS is neither: it is a census/survey of what farmers actually
sowed, published by region and year, and it requires no absence labels at all. If mapped canola
area by SA2 tracks the ABS series, the segmentation mask and the classifier are both working.

WHERE IT COMES FROM. ABS Data Explorer's SDMX REST API, dataflow `AG_BROADACRE`
("Australian Agriculture: Broadacre Crops"). No key, no login, ~1.6 MB.

    https://data.api.abs.gov.au/rest/data/ABS,AG_BROADACRE/all?startPeriod=2020&format=csv

RUN IT ON A LOGIN NODE. gadi compute nodes have no outbound internet; the login node and copyq
do. This is a 1.6 MB request, so it belongs on the login node, not in a job.

THREE THINGS THAT WILL BITE WHOEVER USES THIS NEXT.

1. **REGION mixes three nesting levels in one column**, distinguishable only by code length:
   1 char = state/territory, 3 char = ??? (also sums to the national total), 9 char = SA2.
   Summing the column without filtering triple-counts every hectare — the canola total comes out
   at 13.1 M ha against a true 4.4 M. This script splits them into a `level` column so that
   cannot happen silently.

2. **The series starts at 2022-23.** ABS discontinued `Agricultural Commodities, Australia`
   (7121.0) and replaced it with `Australian Agriculture` from June 2024, and the new dataflow
   carries 2022-23, 2023-24 and 2024-25 only. The demo maps cover 2020-2024, so **2020 and 2021
   have no SA2 comparison here** — for those, the historic data cube in the 2021-22 edition of
   the old publication is the fallback, and it is a manual download.

3. **TIME_PERIOD is a financial year** (`2022-07-01/P1Y` = 2022-23), which for a winter crop is
   the crop sown in the **2022** calendar year. `crop_year` below does that conversion once, so
   it is not re-derived (differently) at every call site.

    python3 abs_fetch.py --out /scratch/xe2/cb8590/paddock-species-data/derived/abs
"""
import argparse
import os
import urllib.request

import pandas as pd

URL = ("https://data.api.abs.gov.au/rest/data/ABS,AG_BROADACRE/all"
       "?startPeriod={start}&format=csv")

# The map's three groups, in ABS's vocabulary. Oats is deliberately absent: it is the crop the
# AgriWebb work found genuinely ambiguous (forage oats is sown and grazed, never harvested), and
# an area comparison cannot resolve what the labels could not.
GROUPS = {
    "Canola": ["BroadCanola_Area_Total"],
    "Cereal": ["BroadWheat_Area_Total", "BroadBarley_Area_Total"],
    "Legume": ["BroadLupins_Area_Total", "BroadChickpeas_Area_Total",
               "BroadFababeans_Area_Total", "BroadLentils_Area_Total"],
}
LEVELS = {1: "state", 3: "national_agg", 9: "SA2"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="directory for the raw and tidied csvs")
    ap.add_argument("--start", default="2020")
    ap.add_argument("--raw", help="skip the download and use this csv instead")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    raw = args.raw or os.path.join(args.out, "abs_broadacre_raw.csv")
    if not args.raw:
        url = URL.format(start=args.start)
        print(f"GET {url}")
        urllib.request.urlretrieve(url, raw)
        print(f"  {os.path.getsize(raw) / 1e6:.1f} MB -> {raw}")

    d = pd.read_csv(raw, low_memory=False)
    d = d[d.UNIT_MEASURE == "HA"].copy()
    d["level"] = d.REGION.astype(str).str.len().map(LEVELS)
    # Financial year -> the calendar year the winter crop was sown in.
    d["crop_year"] = d.TIME_PERIOD.str.slice(0, 4).astype(int)

    inv = {item: g for g, items in GROUPS.items() for item in items}
    d["group"] = d.DATAITEM.map(inv)
    d = d.dropna(subset=["group"])

    tidy = (d.groupby(["level", "REGION", "crop_year", "group"], as_index=False)
              .OBS_VALUE.sum().rename(columns={"OBS_VALUE": "area_ha", "REGION": "region"}))
    out = os.path.join(args.out, "abs_broadacre_area.csv")
    tidy.to_csv(out, index=False)

    print(f"\n{len(tidy)} rows -> {out}")
    print(f"years: {sorted(tidy.crop_year.unique())}")
    print(f"SA2 regions reporting: {tidy[tidy.level == 'SA2'].region.nunique()}")
    print("\nnational area by group and crop year (ha), SA2 level summed:")
    print(tidy[tidy.level == "SA2"].pivot_table(
        index="crop_year", columns="group", values="area_ha", aggfunc="sum").to_string())
    # The consistency check that catches a mis-parsed level column: the three nesting levels
    # must agree, because they are the same hectares aggregated three ways.
    chk = tidy.pivot_table(index="crop_year", columns="level", values="area_ha", aggfunc="sum")
    print("\nlevel cross-check (the three columns must match):")
    print(chk.to_string())


if __name__ == "__main__":
    main()
