#!/usr/bin/env python3
"""
Upload the national 2024 crop-type polygons to Earth Engine as a folder of table assets,
staged through the same GCS bucket the shelterbelts raster uploads use
(see `Projects/shelterbelts/analysis/upload_indices_gch.sh` / `upload_to_gee.py`).

WHY THIS ISN'T THE SAME SCRIPT. That reference stages per-tile GeoTIFFs into an
ImageCollection: each source file becomes one Image, and EE's Image model makes an
ImageCollection the natural container. There is no vector equivalent of ImageCollection —
Earth Engine's building block for many small vector uploads is a plain Folder of Table assets,
merged back into one FeatureCollection client-side with `.merge()`. And the source here is one
finished 2.8 GB GeoPackage in EPSG:3577, not tiles: GEE table ingestion wants WGS84 GeoJSON (or
shapefile), so it has to be reprojected and split rather than just copied.

WHY FID-RANGE SHARDS, NOT THE 374 PREDICTION CHUNKS. The chunks already exist and would be the
obvious shard, but converting each with ogr2ogr and asking Earth Engine to ingest 374 tiny
tables is 374x the ingestion overhead for no benefit once the polygons are merged; the reader
never cares which prediction job a paddock came from. `national_2024_crops.gpkg`'s `fid` is
GeoPackage's own primary key, dense and contiguous 1..1,346,582 (verified), so it can be sliced
into arbitrary equal-sized ranges with a single indexed SQL WHERE per shard — SQLite's INTEGER
PRIMARY KEY IS the rowid, so this is a range scan, not 20 full-table scans.

WHY 20 SHARDS. Measured: one range of ~67k features converts to a 265 MB GeoJSON in ~37s.
20 shards keeps each ingestion comfortably inside limits that have bitten single huge uploads
in the past, keeps the EE asset browser to 20 children instead of 374, and lets the JS side
name every shard explicitly rather than trying to enumerate a folder from the Code Editor.

WHY A ZIPPED SHAPEFILE, NOT GEOJSON. Tried GeoJSON first — `startTableIngestion` rejected
every one of it with "All URIs must have a '.shp' or '.zip' extension", confirmed with a
`.json`-renamed copy too, so it is a real server-side constraint on this account/API version,
not a naming quirk. Shapefile's DBF format then imposes its own limit: field names truncate
silently at 10 characters, which breaks a filter that names a field expecting a value it no
longer has. `abstain_reason` (14), `compactness` (11) and `n_feat_present` (15) all exceed it,
so the extraction SQL renames them (`abstain`, `compact`, `n_feat`) rather than letting GDAL
truncate them into whatever happens to still be unique. Confirmed on a live ingested asset:
all 16 properties survive intact under the short names, geometry included (the naive
`SELECT col, ... FROM crops WHERE ...` silently drops geometry against a GeoPackage's SQLite
backend — the geometry column must be selected explicitly, as `geom`, or the shard has no
shapes at all and no error is raised to say so).

WHY `pred IN (...)` AND NOT `notNull('pred')` IN THE COMPANION JS. Confirmed on the same test
asset: DBF has no true NULL for text fields, so an abstained polygon's `pred` round-trips as
an empty string, not a missing property. `ee.Filter.notNull` would silently mis-classify every
abstained polygon as "classified". An allow-list filter on the three real class names is
correct regardless of how the empty case is represented.

WHY POLL THE ASSET LIST, NOT THE TASK STATUS. `upload_to_gee.py`'s `wait_and_cleanup` already
found that `ee.data.getTaskStatus` lags badly against Earth Engine's own state — it kept
reporting tasks as running long after the Cloud API showed them landed. Presence in
`ee.data.listAssets` is the ground truth there and here too.

    python3 upload_polygons_to_gee.py \
        --gpkg /scratch/.../national2024/national_2024_crops.gpkg \
        --stage-dir /scratch/.../national2024/gee_stage \
        --asset-ids-out /scratch/.../national2024/gee_asset_ids.txt
"""
import argparse
import os
import subprocess
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

OGR2OGR = "/apps/gdal/3.7.3/bin/ogr2ogr"
OGRINFO = "/apps/gdal/3.7.3/bin/ogrinfo"

# "Anyone can read" — the same box you'd tick per-asset in the Code Editor's Share dialog.
# Applied to the Folder and to each shard individually: a Folder's own ACL does not cascade
# to its Table children (confirmed live — a public folder with private children is exactly
# the state this project's assets were found in), so both need it set explicitly.
PUBLIC_POLICY = {"bindings": [{"role": "roles/viewer", "members": ["allUsers"]}]}


def feature_count(gpkg, layer):
    out = subprocess.run([OGRINFO, "-q", gpkg, "-sql", f"SELECT COUNT(*) AS n FROM {layer}"],
                          capture_output=True, text=True, check=True).stdout
    for line in out.splitlines():
        if line.strip().startswith("n ("):
            return int(line.split("=")[1].strip())
    raise RuntimeError(f"could not parse feature count from: {out}")


def fid_max(gpkg, layer):
    out = subprocess.run([OGRINFO, "-q", gpkg, "-sql", f"SELECT MAX(fid) AS m FROM {layer}"],
                          capture_output=True, text=True, check=True).stdout
    for line in out.splitlines():
        if line.strip().startswith("m ("):
            return int(line.split("=")[1].strip())
    raise RuntimeError(f"could not parse max fid from: {out}")


def shard_ranges(n_features, n_shards):
    """(lo, hi) fid ranges, inclusive/exclusive, covering 1..n_features with no gaps or overlap."""
    size = -(-n_features // n_shards)  # ceil
    ranges = []
    lo = 1
    while lo <= n_features:
        hi = min(lo + size, n_features + 1)
        ranges.append((lo, hi))
        lo = hi
    return ranges


# Renamed to fit inside the Shapefile DBF's 10-character field-name limit. Values are
# unchanged; only the name a caller (the companion JS) must use to read them changes.
SELECT_COLS = (
    "area_ha, compactness AS compact, abstain_reason AS abstain, stub, year, poly_idx, "
    "ndvi_amp, pred, confidence, p_canola, p_cereal, p_legume, n_obs, clear_frac, "
    "treed_frac, n_feat_present AS n_feat, geom"
)


def convert_shard(gpkg, layer, lo, hi, out_stem):
    """Write out_stem.shp (+ .shx/.dbf/.prj/.cpg) and zip them into out_stem.zip."""
    shp_path = out_stem + ".shp"
    subprocess.run([OGR2OGR, "-f", "ESRI Shapefile", shp_path, gpkg,
                     "-t_srs", "EPSG:4326", "-lco", "ENCODING=UTF-8",
                     "-sql", f"SELECT {SELECT_COLS} FROM {layer} "
                             f"WHERE fid >= {lo} AND fid < {hi}"],
                    check=True, capture_output=True, text=True)
    parts = [out_stem + ext for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg")
             if os.path.exists(out_stem + ext)]
    zip_path = out_stem + ".zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for part in parts:
            zf.write(part, arcname=os.path.basename(part))
    for part in parts:
        os.remove(part)
    return zip_path


def ensure_folder(folder_id, public):
    import ee
    try:
        ee.data.getAsset(folder_id)
        print(f"folder already exists: {folder_id}")
    except ee.EEException:
        ee.data.createAsset({"type": "FOLDER"}, folder_id)
        print(f"created folder: {folder_id}")
    if public:
        set_public(folder_id)


def set_public(asset_id):
    import ee
    try:
        ee.data.setIamPolicy(asset_id, PUBLIC_POLICY)
    except Exception as e:
        print(f"  WARNING: could not set public ACL on {asset_id}: {type(e).__name__}: {str(e)[:200]}")


def folder_children(folder_id):
    import ee
    ids, params = set(), {"parent": folder_id}
    while True:
        resp = ee.data.listAssets(params)
        ids.update(a["id"] for a in resp.get("assets", []))
        token = resp.get("nextPageToken")
        if not token:
            return ids
        params["pageToken"] = token


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpkg", required=True)
    ap.add_argument("--layer", default="crops")
    ap.add_argument("--n-shards", type=int, default=20)
    ap.add_argument("--stage-dir", required=True, help="local dir for intermediate GeoJSON shards")
    ap.add_argument("--bucket", default="cb8590-shelterbelts-gee")
    ap.add_argument("--gcs-prefix", default="paddock_species_national_2024_crops")
    ap.add_argument("--folder", default="projects/ee-christopher-bradley/assets/"
                                         "paddock_species_national_2024_crops")
    ap.add_argument("--project", default="ee-christopher-bradley")
    ap.add_argument("--key", default=os.path.expanduser("~/gee-uploader-key.json"))
    ap.add_argument("--asset-ids-out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--stall-timeout", type=int, default=1800,
                     help="give up waiting on a shard once no NEW shard has landed for this long")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--private", action="store_true",
                     help="Skip setting 'Anyone can read' (default: public, so the app doesn't "
                          "need per-layer sharing set by hand in the Code Editor).")
    args = ap.parse_args()

    n = feature_count(args.gpkg, args.layer)
    # Shard on the fid extent, not the count. A boundary-merged file (merge_tile_boundaries.py)
    # deletes duplicate rows, so its fids have gaps and max(fid) > n. Ranges built from n
    # would silently leave out every row above fid n.
    top = fid_max(args.gpkg, args.layer)
    ranges = shard_ranges(top, args.n_shards)
    print(f"{n:,} features, fid 1..{top:,} -> {len(ranges)} shards of ~{ranges[0][1] - ranges[0][0]:,} fids each")

    os.makedirs(args.stage_dir, exist_ok=True)
    shards = [(f"p{i:03d}", lo, hi) for i, (lo, hi) in enumerate(ranges)]

    if args.dry_run:
        for name, lo, hi in shards:
            print(f"  {name}: fid [{lo}, {hi})  -> {args.folder}/{name}")
        print(f"DRY RUN — nothing converted, uploaded or ingested")
        return

    import ee
    import json as _json
    from google.cloud import storage

    email = _json.load(open(args.key))["client_email"]
    ee.Initialize(ee.ServiceAccountCredentials(email, args.key), project=args.project)
    gcs = storage.Client.from_service_account_json(args.key, project=args.project)
    bucket = gcs.bucket(args.bucket)
    print(f"authenticated as {email}")

    ensure_folder(args.folder, public=not args.private)

    def process(name, lo, hi):
        zip_path = os.path.join(args.stage_dir, f"{name}.zip")
        if not os.path.exists(zip_path):
            convert_shard(args.gpkg, args.layer, lo, hi, os.path.join(args.stage_dir, name))
        size_mb = os.path.getsize(zip_path) / 1e6
        blob_name = f"{args.gcs_prefix}/{name}.zip"
        bucket.blob(blob_name).upload_from_filename(zip_path)
        asset_id = f"{args.folder}/{name}"
        req_id = ee.data.newTaskId()[0]
        ee.data.startTableIngestion(req_id,
            {"name": asset_id, "sources": [{"uris": [f"gs://{args.bucket}/{blob_name}"]}]},
            allow_overwrite=True)
        return name, asset_id, blob_name, size_mb

    pending = {}  # asset_id -> (name, blob_name)
    print(f"\nconverting, uploading and submitting {len(shards)} shards ({args.workers} at a time)...")
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process, *s): s[0] for s in shards}
        for fut in as_completed(futs):
            name = futs[fut]
            try:
                name, asset_id, blob_name, size_mb = fut.result()
                pending[asset_id] = (name, blob_name)
                print(f"  {name}: {size_mb:.0f} MB submitted -> {asset_id}")
            except Exception as e:
                print(f"  {name}: FAILED — {type(e).__name__}: {str(e)[:200]}")

    print(f"\n{len(pending)} of {len(shards)} shards submitted; waiting for ingestion to land...")
    landed = []
    last_progress = time.time()
    while pending:
        present = folder_children(args.folder)
        done_now = [a for a in pending if a in present]
        for asset_id in done_now:
            name, blob_name = pending.pop(asset_id)
            if not args.private:
                set_public(asset_id)
            bucket.blob(blob_name).delete()
            landed.append(asset_id)
            last_progress = time.time()
            print(f"  landed [{len(landed)}/{len(landed) + len(pending)}]: {asset_id} "
                  f"(staging blob deleted)")
        if pending:
            if time.time() - last_progress > args.stall_timeout:
                print(f"  no progress for {args.stall_timeout}s — giving up on "
                      f"{len(pending)} still-pending shard(s), their staging blobs are kept:")
                for asset_id, (name, blob_name) in pending.items():
                    print(f"    {name}: gs://{args.bucket}/{blob_name}")
                break
            time.sleep(20)

    landed.sort()
    with open(args.asset_ids_out, "w") as f:
        f.write("\n".join(landed) + "\n")
    print(f"\n{len(landed)} of {len(shards)} shards landed. Asset IDs -> {args.asset_ids_out}")
    if len(landed) < len(shards):
        sys.exit(1)


if __name__ == "__main__":
    main()
