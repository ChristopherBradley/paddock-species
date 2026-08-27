#!/usr/bin/env python3
"""
Tidy the ABARES Australian Crop Report state workbook into one long CSV — the second independent
reference series, and the only one that covers 2020 and 2021.

WHY BOTH ABARES AND ABS. They are not the same measurement and disagreeing with one is not the
same as disagreeing with the other:

* **ABS `AG_BROADACRE`** is a survey/census of what farmers reported sowing, published at **SA2**
  resolution — fine enough to compare against a 100 km map tile — but the current dataflow starts
  at **2022-23**, because ABS discontinued `Agricultural Commodities` (7121.0) and replaced it
  with `Australian Agriculture` in June 2024.
* **ABARES** is a forecast/estimate series at **state** resolution only, but it runs from
  **1989-90** to the current forecast year. It is the only way to put a number against the 2020
  and 2021 maps.

So: ABS for spatial detail, ABARES for the long series and as a sanity check that the two
independent agencies agree before either is used to judge a map.

WHERE THE FILE COMES FROM. The workbook is re-issued every quarter with a new filename, so there
is no stable URL. Scrape the current one from the report page:

    curl -sL https://www.agriculture.gov.au/abares/research-topics/agricultural-outlook/\\
australian-crop-report/june-2026 | grep -oE 'href="[^"]*StateCropData[^"]*\\.xlsx"'

LAYOUT, AND THE TRAP IN IT. Each state is a sheet. Within a sheet the rows are a repeating
three-row block — a crop name on its own row, then `Area` in **'000 ha**, then `Production` in kt
— and the columns are financial years. **The units row is what disambiguates area from
production**, not the position, because the block is not always three rows (some crops carry
extra rows in some years). This parser keys on the `'000 ha` unit string and the most recent crop
name seen above it, which survives that.

    python3 abares_fetch.py --xlsx .../03_AustCropRrt..._StateCropData_v1.0.0.xlsx \\
        --out .../abs/abares_state_area.csv
"""
import argparse
import re

import pandas as pd

# ABARES crop names -> the map's three groups. Anything unmapped is dropped, which is deliberate:
# oats is excluded for the same reason as in abs_fetch.py (forage oats is sown and grazed, never
# harvested, so it is the one crop an area comparison cannot adjudicate), and hay/other likewise.
GROUPS = {
    "Canola": "Canola",
    "Wheat": "Cereal", "Barley": "Cereal", "Triticale": "Cereal", "Cereal rye": "Cereal",
    "Chickpeas": "Legume", "Faba beans": "Legume", "Field peas": "Legume",
    "Lentils": "Legume", "Lupins": "Legume",
}


def fy_to_crop_year(s):
    """'2022–23 s' -> (2022, 's'). The winter crop of a financial year is sown in its first
    calendar year, and the trailing letter is ABARES' own quality flag — `s` estimate, `f`
    forecast, absent for a settled historical figure. It is carried through rather than stripped:
    judging a 2024 map against a *forecast* is a different claim from judging it against history,
    and whoever reads the comparison has to be able to tell."""
    m = re.match(r"^(\d{4})[–-]\d{2}\s*([a-z]?)$", str(s).strip())
    return (int(m.group(1)), m.group(2) or "final") if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    xl = pd.ExcelFile(args.xlsx)
    sheets = [s for s in xl.sheet_names if s not in ("Index",)]
    rows = []
    for sheet in sheets:
        d = xl.parse(sheet, header=None)
        # The header row is the one carrying the financial years; find it rather than assuming 6.
        hdr = next((i for i in range(len(d))
                    if d.iloc[i].astype(str).str.match(r"^\d{4}[–-]\d{2}").sum() >= 5), None)
        if hdr is None:
            print(f"  {sheet}: no year header found, skipped")
            continue
        # The `Australia` sheet is shifted one column left of the state sheets, so the label and
        # unit columns are located by the header text, never by a fixed index.
        lab_c = next(c for c in d.columns if str(d.iat[hdr, c]).strip() == "Crops")
        unit_c = lab_c + 1
        years = {c: fy_to_crop_year(d.iat[hdr, c]) for c in d.columns
                 if fy_to_crop_year(d.iat[hdr, c])}
        crop = None
        for i in range(hdr + 1, len(d)):
            label = str(d.iat[i, lab_c]).strip() if not pd.isna(d.iat[i, lab_c]) else ""
            unit = str(d.iat[i, unit_c]).strip() if not pd.isna(d.iat[i, unit_c]) else ""
            if label in GROUPS:
                crop = label
            elif label == "Area" and "000 ha" in unit and crop:
                for c, (yr, status) in years.items():
                    v = d.iat[i, c]
                    if pd.notna(v) and isinstance(v, (int, float)):
                        rows.append({"state": sheet, "crop": crop, "group": GROUPS[crop],
                                     "crop_year": yr, "status": status,
                                     "area_ha": float(v) * 1000})
            elif label in ("Production", ""):
                pass
            elif label and label[0].isupper() and label not in ("Winter crops", "Summer crops"):
                crop = None      # a crop we do not map — stop attributing Area rows to the last one

    t = pd.DataFrame(rows)
    t.to_csv(args.out, index=False)
    print(f"{len(t)} rows -> {args.out}")
    print(f"states: {sorted(t.state.unique())}")
    print(f"years: {t.crop_year.min()}–{t.crop_year.max()}")
    print(f"quality flags: {t.status.value_counts().to_dict()}")
    aus = t[t.state == "Australia"]
    if len(aus):
        print("\nAustralia, area sown (ha) by group, recent years:")
        print(aus[aus.crop_year >= 2020].pivot_table(
            index="crop_year", columns="group", values="area_ha", aggfunc="sum").to_string())


if __name__ == "__main__":
    main()
