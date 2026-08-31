#!/bin/bash
# The 100 x 100 km, 9-year map: one region, 2017-2025, at the production 3 km tile.
#
# WHY ONE REGION FOR NINE YEARS RATHER THAN THREE FOR THREE. The question this run answers is
# how a paddock's segmentation and classification move year to year on the SAME ground —
# rotation is the only plausibility check a map with no ground truth has, and a polygon that is
# stable across nine years is a different object from one that appears once. Three regions for
# three years would answer a different question (does it generalise across districts) that the
# demo maps already touched.
#
# WHY THE RIVERINA. It is the region NLUM already picked for the demo (`mapdemo/regions.csv`,
# nsw_2) and the one with the best coverage there, 78-96 %. Re-running the NLUM search at a
# 102 km block would move the winning cell, and a time series that changes location between
# runs is not a time series — hence `map_regions.py --centre`.
#
# SCALE. 34 x 34 = 1,156 tiles x 9 years = 10,404 tile-years. At the measured 0.0553 SU/tile
# that is ~575 SU all in, of which ~80 % is segmentation and ~20 % inference.
#
# 2017 IS NOT LIKE THE OTHERS. Sentinel-2B only became operational mid-2017, so 2017 carries
# roughly half the revisit of later years. Expect fewer and worse polygons that year, and do
# NOT read the difference as land-use change.
#
#   ./run_map100.sh aois       # chunk the AOI list for the queue
#   ./run_map100.sh presegment # ~30 jobs
#   ./run_map100.sh sam        # ~6 GPU jobs, after presegment
#   ./run_map100.sh status     # how far it has got
#   ./run_map100.sh predict    # inference, once the abstain path is settled
#   ./run_map100.sh predict-shapegate          # baseline shape gate, PHENOLOGY_GATE.md
#   ./run_map100.sh predict-shapegate-twopass  # + Canola exempted, 'Next step' #2
#   ./run_map100.sh predict-shapegate-loose    # loosened senescence_drop, 'Next step' #1
#   ./run_map100.sh stability  # year-to-year polygon agreement (20 jobs), then `stability-merge`
#   ./run_map100.sh stability-merge
set -euo pipefail
PY=/g/data/xe2/John/geospatenv/bin/python
D=/scratch/xe2/cb8590/paddock-species-data/derived
REPO=/home/147/cb8590/Projects/paddock-species
cd "$REPO/src/paddocks"
export PROJ_NETWORK=OFF

M=$D/map100
AOIS=$M/aois.csv
POLY=$M/samgeo
CH=$M/chunks

case "${1:-}" in
aois)
    mkdir -p $CH; rm -f $CH/*.csv
    # Contiguous slices of the already-sorted AOI list, so each job walks tiles that share
    # Sentinel-2 scenes. The sort is done in map_regions.py by (region, year, grid_r, grid_c) —
    # slicing it here preserves that; re-sorting or shuffling would throw away a 4x saving.
    $PY - "$AOIS" "$CH" 30 <<'PYEOF'
import sys, pandas as pd, numpy as np
aois, out, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
A = pd.read_csv(aois)
for i, part in enumerate(np.array_split(A, n)):
    part.to_csv(f"{out}/p{i:02d}.csv", index=False)
print(f"{len(A)} tile-years -> {n} chunks of ~{len(A)//n} in {out}")
PYEOF
    ;;
presegment)
    mkdir -p $POLY
    # 4 GB, not 8. Measured on the same 16 tiles of 2024: 0.31 SU at 8 GB against 0.08 SU at
    # 4 GB, both exit 0, the 4 GB job reporting a genuine 3.08 GB used. If a chunk does OOM
    # (exit 137, no traceback) it resumes — every composite is written as it is built and an
    # existing one is skipped — so re-submit just that chunk with -l mem=8GB.
    for f in $CH/p*.csv; do
        b=$(basename "$f" .csv)
        qsub -l mem=4GB -l walltime=06:00:00 -v AOIS="$f",OUTDIR=$POLY -N ps_$b presegment.pbs
    done
    ;;
sam)
    # Chained `afterany` behind every presegment job, because SAM only sees tiles whose
    # composite already exists: submitted early it would find nothing and exit "nothing to
    # segment", having still paid the gpuvolta booking. `afterany` not `afterok`, so one failed
    # presegment chunk does not strand the whole GPU stage — SAM segments whatever is there and
    # a re-submission picks up the rest.
    #
    # Six jobs, because the ~49 s model load wants amortising over as many tiles as a 3 h
    # walltime allows, and each takes every 6th presegment chunk so its tiles stay spatially
    # contiguous.
    IDS=$(qstat -u cb8590 2>/dev/null | grep "ps_p" | awk '{print $1}' | cut -d. -f1 \
          | tr '\n' ':' | sed 's/:$//')
    [ -n "$IDS" ] && DEP="-W depend=afterany:$IDS" || DEP=""
    for i in 0 1 2 3 4 5; do
        $PY - "$CH" "$M" "$i" <<'PYEOF'
import sys, glob, pandas as pd
ch, m, i = sys.argv[1], sys.argv[2], int(sys.argv[3])
fs = sorted(glob.glob(f"{ch}/p*.csv"))
part = [f for k, f in enumerate(fs) if k % 6 == i]
pd.concat([pd.read_csv(f) for f in part], ignore_index=True).to_csv(f"{m}/sam_{i}.csv", index=False)
PYEOF
        qsub $DEP -l walltime=03:00:00 -v AOIS=$M/sam_$i.csv,OUTDIR=$POLY -N sam100_$i sam_segment.pbs
    done
    ;;
status)
    n=$(wc -l < $AOIS); n=$((n-1))
    echo "AOIs:        $n tile-years"
    # `grep -c` exits 1 on zero matches, so it must not be the last command in a $( ) that is
    # also given an `|| echo 0` fallback — both would print. Pipe into wc instead.
    echo "composites:  $(ls $POLY/*.tif 2>/dev/null | grep -v _segment | wc -l)"
    echo "segmented:   $(ls $POLY/*_filt.gpkg 2>/dev/null | wc -l)"
    echo "queue:       $(qstat -u cb8590 2>/dev/null | grep -E 'ps_p|sam100' | wc -l) jobs "\
         "($(qstat -u cb8590 2>/dev/null | grep -E 'ps_p|sam100' | awk '{print $10}' | grep -c R) running)"
    ;;
predict)
    mkdir -p $M/pred
    # The abstain path: both classes of mask, and the 3-class crop model — NOT group4. See
    # output/PRESENCE_ONLY_LABELS.md for why the Grazing class is retired.
    for f in $CH/p*.csv; do
        b=$(basename "$f" .csv)
        qsub -l mem=8GB -v AOIS="$f",POLYDIR=$POLY,MODEL=$D/models/group3_map.joblib,\
OUT=$M/pred/${b}.gpkg,EXTRA_ARGS="--max-area-ha 300 --crop-gate-amp 0.35" \
             -N pr_$b predict_tile.pbs
    done
    ;;
predict-shapegate)
    # Same run, same segmentation, `--crop-gate-shape` stacked on top of the existing amplitude
    # gate — isolates the phenology-shape gate's effect for output/PHENOLOGY_GATE.md's still-open
    # question (NEXT_STEPS.md #6.2): does the area ratio move toward 1.0 while presence recall
    # holds? Separate output dir so the validated baseline in $M/pred is never touched.
    mkdir -p $M/pred_shapegate
    for f in $CH/p*.csv; do
        b=$(basename "$f" .csv)
        qsub -l mem=8GB -v AOIS="$f",POLYDIR=$POLY,MODEL=$D/models/group3_map.joblib,\
OUT=$M/pred_shapegate/${b}.gpkg,EXTRA_ARGS="--max-area-ha 300 --crop-gate-amp 0.35 --crop-gate-shape $D/models/phenology_gate.joblib" \
             -N prs_$b predict_tile.pbs
    done
    ;;
predict-shapegate-twopass)
    # PHENOLOGY_GATE.md 'Next step' #2: same shape-gate model, but Canola predictions are
    # exempted from it (amplitude gate only) -- the shape gate's canola-specific recall
    # shortfall (83.4% vs cereal/legume ~95%) should not cost canola while it is still doing
    # its job filtering excess Cereal/Legume land. Separate output dir, same segmentation.
    mkdir -p $M/pred_shapegate_twopass
    for f in $CH/p*.csv; do
        b=$(basename "$f" .csv)
        qsub -l mem=8GB -v AOIS="$f",POLYDIR=$POLY,MODEL=$D/models/group3_map.joblib,\
OUT=$M/pred_shapegate_twopass/${b}.gpkg,EXTRA_ARGS="--max-area-ha 300 --crop-gate-amp 0.35 --crop-gate-shape $D/models/phenology_gate.joblib --shape-gate-skip-classes Canola" \
             -N prtp_$b predict_tile.pbs
    done
    ;;
predict-shapegate-loose)
    # PHENOLOGY_GATE.md 'Next step' #1: a phenology_gate_loose.joblib fit with
    # --senescence-slack-pct (see phenology_gate.py), applied to every class alike.
    mkdir -p $M/pred_shapegate_loose
    for f in $CH/p*.csv; do
        b=$(basename "$f" .csv)
        qsub -l mem=8GB -v AOIS="$f",POLYDIR=$POLY,MODEL=$D/models/group3_map.joblib,\
OUT=$M/pred_shapegate_loose/${b}.gpkg,EXTRA_ARGS="--max-area-ha 300 --crop-gate-amp 0.35 --crop-gate-shape $D/models/phenology_gate_loose.joblib" \
             -N prl_$b predict_tile.pbs
    done
    ;;
stability)
    mkdir -p $M/stability
    # 20 shards: ~9 CPU-hours of GeoPackage opening split into ~27 min each. See stability.pbs
    # for why the cost is I/O and not geometry.
    for i in $(seq 0 19); do
        qsub -v POLYDIR=$POLY,OUT=$M/stability/s$i.csv,SHARD=$i/20 -N st_$i stability.pbs
    done
    ;;
stability-merge)
    # --pred is optional: run the merge without it as soon as segmentation is done, and again
    # with it once inference has landed, to get the rotation-plausibility section.
    $PY polygon_stability.py --polydir $POLY --merge "$M/stability/s*.csv" \
        --out $M/stability_all.csv --consensus $M/consensus.gpkg --min-years 5 \
        ${PRED:+--pred "$M/pred/*.gpkg"} \
        --report $REPO/output/POLYGON_STABILITY.md
    ;;
*)
    echo "usage: $0 {aois|presegment|sam|status|predict|predict-shapegate|predict-shapegate-twopass|predict-shapegate-loose|stability|stability-merge}" >&2; exit 2 ;;
esac
