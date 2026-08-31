"""
Reconstruct the boundary-split pair search from PIPELINE_ARCHITECTURE_AND_TILING.md sec 5:
"searched a 60km box around the Riverina test region for pairs of polygons whose bounding
boxes meet exactly across the same grid line -- found 30 such pairs ... 13 with a class
mismatch". That search wasn't saved to a script last time, so redo it here to pick a few
more mismatched pairs (beyond the Legume/Cereal one already tested) to run through
overlap_test.pbs.
"""
import pandas as pd
import numpy as np
from pyproj import Transformer

BBOX_CSV = "/scratch/xe2/cb8590/paddock-species-data/derived/national2024/fig_extract/national_2024_bboxes.csv"
AOIS_CSV = "/scratch/xe2/cb8590/paddock-species-data/derived/national2024/aois.csv"

TILE_EDGE = 3000.0  # half_m=1500 everywhere -> edge = 2*half_m
TOL = 10.0  # metres, "meet exactly" tolerance for bbox edges touching a grid line / each other
# (10m = one Sentinel-2 pixel, matching the table in sec 5; two independent SAM segmentations
# either side of the same boundary can differ from the exact line by up to a few metres each,
# so matching raw min/max coords to each other at 1m tolerance under-matched -- match by grid
# line INDEX instead, each side within TOL of that shared line.)

# Center of the split already tested (from overlap_test.pbs)
CENTER_LON, CENTER_LAT = 147.108290, -34.622992
HALF_BOX_M = 30_000  # "60km box"

to_albers = Transformer.from_crs("EPSG:4326", "EPSG:3577", always_xy=True)
cx, cy = to_albers.transform(CENTER_LON, CENTER_LAT)
print(f"Center in Albers: {cx:.1f}, {cy:.1f}")

# --- recover grid origin from aois.csv tile centres (same approach as sec 5) ---
aois = pd.read_csv(AOIS_CSV)
sub = aois.sample(n=min(2000, len(aois)), random_state=0)
ax, ay = to_albers.transform(sub["lon"].values, sub["lat"].values)
# tile centres should be at origin + n*TILE_EDGE ; recover origin mod TILE_EDGE
ox = np.median(ax % TILE_EDGE)
oy = np.median(ay % TILE_EDGE)
resid_x = np.abs(((ax - ox + TILE_EDGE / 2) % TILE_EDGE) - TILE_EDGE / 2)
resid_y = np.abs(((ay - oy + TILE_EDGE / 2) % TILE_EDGE) - TILE_EDGE / 2)
print(f"grid origin recovered: ox={ox:.3f} oy={oy:.3f} | max resid x={resid_x.max():.3f} y={resid_y.max():.3f}")

# tile EDGES (boundaries) are at half-tile offset from centres
edge_ox = (ox - TILE_EDGE / 2) % TILE_EDGE
edge_oy = (oy - TILE_EDGE / 2) % TILE_EDGE

# --- load bboxes, restrict to 60km box ---
df = pd.read_csv(BBOX_CSV)
box = df[
    (df.minx > cx - HALF_BOX_M) & (df.maxx < cx + HALF_BOX_M) &
    (df.miny > cy - HALF_BOX_M) & (df.maxy < cy + HALF_BOX_M)
].copy()
box = box.reset_index(drop=True)
box["pid"] = box.index
print(f"{len(box)} polygons in 60km box")

def nearest_grid_dist(v, origin, edge=TILE_EDGE):
    return np.abs(((v - origin + edge / 2) % edge) - edge / 2)

box["dx_min"] = nearest_grid_dist(box.minx, edge_ox)
box["dx_max"] = nearest_grid_dist(box.maxx, edge_ox)
box["dy_min"] = nearest_grid_dist(box.miny, edge_oy)
box["dy_max"] = nearest_grid_dist(box.maxy, edge_oy)

on_vgrid = box[(box.dx_min < TOL) | (box.dx_max < TOL)]
on_hgrid = box[(box.dy_min < TOL) | (box.dy_max < TOL)]
print(f"{len(on_vgrid)} touch a vertical grid line, {len(on_hgrid)} touch a horizontal grid line")

pairs = []

def line_index(v, origin, edge=TILE_EDGE):
    return np.round((v - origin) / edge).astype(int)

box["vline_min"] = line_index(box.minx, edge_ox)
box["vline_max"] = line_index(box.maxx, edge_ox)
box["hline_min"] = line_index(box.miny, edge_oy)
box["hline_max"] = line_index(box.maxy, edge_oy)

# vertical-line pairs: one poly's maxx on line k, another's minx on the SAME line k, y-ranges overlap
left = box[box.dx_max < TOL]
right = box[box.dx_min < TOL]
for _, L in left.iterrows():
    cand = right[right.vline_min == L.vline_max]
    for _, R in cand.iterrows():
        if R.pid == L.pid:
            continue
        y_overlap = min(L.maxy, R.maxy) - max(L.miny, R.miny)
        if y_overlap > 0:
            pairs.append(dict(axis="v", x=L.maxx, a_pid=L.pid, b_pid=R.pid,
                               a_pred=L.pred, b_pred=R.pred,
                               a_area=L.area_ha, b_area=R.area_ha,
                               a_abstain=L.abstain_reason, b_abstain=R.abstain_reason,
                               ymid=(max(L.miny, R.miny) + min(L.maxy, R.maxy)) / 2,
                               xmid=L.maxx))

# horizontal-line pairs
bottom = box[box.dy_max < TOL]
top = box[box.dy_min < TOL]
for _, B in bottom.iterrows():
    cand = top[top.hline_min == B.hline_max]
    for _, T in cand.iterrows():
        if T.pid == B.pid:
            continue
        x_overlap = min(B.maxx, T.maxx) - max(B.minx, T.minx)
        if x_overlap > 0:
            pairs.append(dict(axis="h", y=B.maxy, a_pid=B.pid, b_pid=T.pid,
                               a_pred=B.pred, b_pred=T.pred,
                               a_area=B.area_ha, b_area=T.area_ha,
                               a_abstain=B.abstain_reason, b_abstain=T.abstain_reason,
                               xmid=(max(B.minx, T.minx) + min(B.maxx, T.maxx)) / 2,
                               ymid=B.maxy))

pdf = pd.DataFrame(pairs)
print(f"\n{len(pdf)} touching pairs total across the 60km box")

def is_mismatch(row):
    a, b = row["a_pred"], row["b_pred"]
    a_ok = isinstance(a, str) and a not in ("", "nan")
    b_ok = isinstance(b, str) and b not in ("", "nan")
    return a_ok and b_ok and a != b

pdf["a_pred"] = pdf["a_pred"].fillna("")
pdf["b_pred"] = pdf["b_pred"].fillna("")
mismatch = pdf[pdf.apply(is_mismatch, axis=1)].copy()
print(f"{len(mismatch)} pairs with a genuine class mismatch (both classified, different classes)")

# convert xmid/ymid back to lon/lat for each mismatch pair
to_wgs = Transformer.from_crs("EPSG:3577", "EPSG:4326", always_xy=True)
lons, lats = to_wgs.transform(mismatch["xmid"].values, mismatch["ymid"].values)
mismatch["lon"] = lons
mismatch["lat"] = lats
mismatch["max_area"] = mismatch[["a_area", "b_area"]].max(axis=1)
mismatch["min_area"] = mismatch[["a_area", "b_area"]].min(axis=1)

mismatch = mismatch.sort_values("min_area")  # smallest-fragment-first, like the original Legume find
cols = ["axis", "lon", "lat", "a_pred", "b_pred", "a_area", "b_area", "a_abstain", "b_abstain"]
pd.set_option("display.width", 160)
pd.set_option("display.max_rows", 60)
print(mismatch[cols].to_string())

out_csv = "/scratch/xe2/cb8590/tmp/claude-15128/-home-147-cb8590-Projects-paddock-species/fdb311d4-b112-4fa4-b271-2d38da26fca8/scratchpad/mismatch_pairs.csv"
mismatch[cols].to_csv(out_csv, index=False)
print(f"\nwrote {out_csv}")
