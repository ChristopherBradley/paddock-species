# Trial→paddock match review rubric

Shared by human reviewers (QGIS) and model reviewers (contact sheets) so their verdicts are
directly comparable. If you change a category here, change it for both.

## What you are judging

Each panel is a Sentinel-2 RGB chip, ~2 km across, near flowering for that trial's season:

- **yellow dot** — the NVT trial's recorded GPS. It marks a paddock **corner**, not the
  centre, and typically sits within ~30 m of a boundary. A dot on or just outside a line is
  normal and is *not* by itself a fault.
- **magenta outlines** — every SAMGeo polygon in view (candidates).
- **cyan outline** — the polygon **chosen** for this trial. This is what you are judging.

The chosen polygon supplies the pixels whose median CFI decides whether the trial's crop
label is confirmed. So the question is always: **would averaging inside the cyan outline give
a clean read of this trial's crop?**

## Verdicts

Write exactly one per trial.

| verdict | when |
|---|---|
| `good` | cyan traces a single coherent cropped field containing or immediately adjoining the dot |
| `trial_plot` | cyan traces the **NVT trial plot itself** — a small (~3–15 ha) rectangle with visible fine parallel **variety striping**. Not an error; record it separately because the project prefers the surrounding paddock |
| `wrong_polygon` | a clearly better candidate is visible — cyan is a road verge, laneway, headland strip or the neighbouring field while the obvious paddock sits alongside |
| `treed` | cyan is substantially timber, scrub or a shelterbelt rather than crop |
| `linear` | cyan is a long thin feature — drainage line, creek, track, fence line. Often large in area, which hides it from area-based checks |
| `merged` | cyan spans two or more visibly different fields (different colour/texture either side of an internal boundary) |
| `too_big` | one field but implausibly large for broadacre (rule of thumb >300 ha) with no internal structure |
| `no_paddock` | no cyan drawn, or the site is clearly not cropped (bare, urban, water, native veg) |
| `unsure` | genuinely cannot tell — cloud, poor contrast, ambiguous boundaries. Use it rather than guessing |

## Judgement calls that have already caused mistakes

1. **Small ≠ wrong.** SAM segments NVT trial plots as their own polygons; ~22 % of chosen
   polygons are 3–15 ha and many show variety striping. Call those `trial_plot`, **not**
   `wrong_polygon`. Only use `wrong_polygon` when a genuinely better field is visible.
2. **Big ≠ right.** A 448 ha polygon in this dataset was a drainage line. Judge shape, not
   area — that is what `linear` is for.
3. **The dot sits on boundaries by design.** Do not mark `wrong_polygon` merely because the
   dot is outside the cyan line; the GPS marks a corner. Mark it only if a *different* polygon
   is the obviously better home for the trial.
4. **Colour is season-dependent.** Bare/brown is normal outside the growing window and does
   not imply the paddock is uncropped. Judge field structure — boundaries, uniform texture —
   over hue.
5. **Flags are hints, not answers.** The flags in each title are cheap geometric heuristics
   and are wrong often enough to matter. Judge the imagery; disagreeing with a flag is a
   useful result, not a mistake.

## Output format

One CSV row per trial: `TrialCode,verdict,note`

- Use the supplied manifest to map panel position → TrialCode. Panels run left-to-right,
  top-to-bottom. **Do not read codes off the image**; titles can be clipped.
- `note`: a short phrase only where it adds something ("cyan is roadside strip, 40 ha field
  to the east"). Leave empty for straightforward `good`.
- Every trial in the manifest gets exactly one row, including `unsure`.
