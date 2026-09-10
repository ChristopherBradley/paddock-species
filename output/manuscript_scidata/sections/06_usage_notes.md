---
section: usage_notes
mode: full
word_target: 650
---

# Usage Notes

**Filtering toward area-accurate rather than composition-accurate output.** Because every polygon carries either a predicted class or one of four explicit abstain reasons, plus `ndvi_amp` and classifier `confidence`, a user who needs area-accurate rather than composition-accurate output already has the information required to filter toward a tighter, more conservative view of the dataset without waiting for a future methodological revision. Raising the `ndvi_amp` threshold above the shipped 0.35 cutoff trades completeness for a lower area over-call; Technical Validation's sensitivity table quantifies this trade-off at several thresholds and should be consulted before choosing a project-specific cutoff. This design was itself informed by an earlier failure mode: an initial design considered building an explicit absence-labelled "non-crop" class from presence-only farmer-recorded grazing records, and was abandoned after finding that 78.5% of a deliberately hard stratum of grazing paddocks passed the same crop-presence test as known crop paddocks — presence-only farmer records could not be reliably inverted into confirmed absence labels. The abstain-reason and confidence fields shipped instead are this dataset's considered response: rather than force a binary crop/non-crop decision the available negative-label data could not support reliably, every polygon reports its uncertainty explicitly as a first-class field.

**The area over-call is the single most consequential characteristic to account for.** Users computing absolute crop area from this dataset (rather than composition/share, which is comparatively well validated) should expect a 1.47-1.59x over-call relative to ABS unless they filter using the fields above; the over-call is concentrated in Cereal and Legume and essentially absent from Canola (Technical Validation), so composition estimates that rely primarily on Canola are the most directly trustworthy use of this dataset as released.

**Cereal yield: use both columns, never only the calibrated one.** `yield_tha_raw` reflects National Variety Trial management conditions, which generally out-yield commercial paddocks; `yield_tha_calibrated` applies a single national multiplicative factor to correct for this, checked against ABS-implied yield on two held-out years (+3.1% to +18.1% error) but not validated at finer spatial resolution than state level. Users needing paddock-level yield accuracy should treat the calibrated column as indicative, not exact, and consult both columns rather than the calibrated one alone.

**No canola or legume yield is shipped, and canola yield's absence has a specific, addressable cause.** Canola yield requires Sentinel-1 backscatter to clear a trivial year-and-state-mean baseline (Methods); Sentinel-1 is not yet part of this dataset's production pipeline, pending a national acquisition-cost assessment. This is disclosed rather than silently omitted so that a user is not left guessing whether canola yield was attempted and failed outright, or is simply not yet built.

**The Legume-class discrepancy (18.4% mapped vs. 8.7% ABS) has no established mechanism** and should be treated as an open, disclosed limitation rather than a solved or well-understood one; users relying on Legume-class output specifically should weight it accordingly against Cereal or Canola output.

**`unsegmented_blob`** is SAM's single largest segmentation failure mode (48,016 polygons nationally, Data Records); these polygons carry no class prediction and are not recoverable from this release without a separate segmentation pass.

**Sensitive underlying ground truth.** The GRDC/NVT trial records used to build and validate this dataset cannot be released at the site level (coordinates, trial identifiers, or yields) under the data-use agreement covering them; this dataset and its accompanying validation reports contain only aggregate statistics derived from those records, never site-level values.
