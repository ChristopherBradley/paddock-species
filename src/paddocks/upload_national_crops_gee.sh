#!/bin/bash
# Upload the finished national 2024 crop-type map to Earth Engine as a folder of 20 table
# assets (`upload_polygons_to_gee.py` does the conversion/upload/ingestion).
# Pass "dry" as the first arg to preview the shard plan without converting, uploading or
# ingesting anything.
set -uo pipefail

DRY=""
[ "${1:-}" = "dry" ] && DRY="--dry-run"

PY=/g/data/xe2/cb8590/miniconda/envs/shelterbelts/bin/python
SCRIPT=/home/147/cb8590/Projects/paddock-species/src/paddocks/upload_polygons_to_gee.py
GPKG=/scratch/xe2/cb8590/paddock-species-data/derived/national2024/national_2024_crops.gpkg
STAGE=/scratch/xe2/cb8590/paddock-species-data/derived/national2024/gee_stage
OUT=/scratch/xe2/cb8590/paddock-species-data/derived/national2024/gee_asset_ids.txt
BUCKET=cb8590-shelterbelts-gee
FOLDER=projects/ee-christopher-bradley/assets/paddock_species_national_2024_crops
PROJECT=ee-christopher-bradley
KEY=/home/147/cb8590/gee-uploader-key.json

echo "=================================================================="
echo ">>> $(date '+%F %T')  uploading national_2024_crops.gpkg -> $FOLDER"
echo "=================================================================="
"$PY" "$SCRIPT" \
    --gpkg "$GPKG" \
    --stage-dir "$STAGE" \
    --asset-ids-out "$OUT" \
    --bucket "$BUCKET" \
    --gcs-prefix paddock_species_national_2024_crops \
    --folder "$FOLDER" \
    --project "$PROJECT" \
    --key "$KEY" \
    --n-shards 20 \
    --workers 4 \
    $DRY
echo "=================================================================="
echo ">>> DONE $(date '+%F %T')"
