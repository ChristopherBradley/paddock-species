#!/bin/bash
# Submit the two-stage SAMGeo paddock pipeline for an AOI list.
#   ./submit_paddocks.sh AOIS.csv OUTDIR [--per-job N] [--lanes N] [--gpu-batch N]
#                                        [--pre-mem 8GB] [--tag NAME]
#
# --pre-mem overrides stage-1 memory. Revisit density grew with S2C, so a 2023+ AOI needs
# 8 GB where a 2017 one runs in 4 GB; on `normal` the charge is max(ncpus, mem/4GB), so
# giving every AOI 8 GB would double stage-1 cost for AOIs that do not need it. Submit the
# late years separately with --pre-mem 8GB --tag late instead.
# --tag namespaces the chunk files so two submissions can share ONE OUTDIR (and therefore
# one polygon directory) without overwriting each other's chunk lists.
#
# Stage 1 (presegment) is split into many 1-CPU/4GB `normal` jobs: it is I/O-bound on the
# datacube (~25 % CPU), so extra cores buy nothing while being billed, and 1 CPU / 4 GB is
# the cheapest bookable unit on that queue. More jobs = more wall-clock parallelism at the
# same SU cost, which is why this chunks rather than looping in one big job.
#
# Stage 2 (segment) is the opposite shape: `gpuvolta` bills 12 CPUs per GPU no matter what,
# so the goal is FEWER, FULLER jobs — every AOI added to a job amortises the ~49 s model
# load that would otherwise be paid per AOI.
#
# Stage 2 jobs depend on ALL stage-1 jobs (afterany, so one failed chunk cannot strand the
# run — stage 2 simply skips AOIs whose composite is missing, and re-running picks them up).
set -euo pipefail
AOIS=${1:?usage: submit_paddocks.sh AOIS.csv OUTDIR [--per-job N] [--lanes N] [--gpu-batch N]}
OUTDIR=${2:?}
shift 2
PER_JOB=8          # AOIs per stage-1 job
LANES=8            # max stage-1 jobs running at once
GPU_BATCH=40       # AOIs per stage-2 job
PRE_MEM=""         # empty = use presegment.pbs's own directive (4GB)
TAG=""
while [ $# -gt 0 ]; do
    case "$1" in
        --per-job)   PER_JOB=$2; shift 2 ;;
        --lanes)     LANES=$2; shift 2 ;;
        --gpu-batch) GPU_BATCH=$2; shift 2 ;;
        --pre-mem)   PRE_MEM=$2; shift 2 ;;
        --tag)       TAG=$2; shift 2 ;;
        *) echo "unknown arg $1" >&2; exit 2 ;;
    esac
done
P=${TAG:+${TAG}_}   # chunk-name prefix, so tagged submissions do not clobber each other

HERE=$(cd "$(dirname "$0")" && pwd)
CHUNKDIR="$OUTDIR/aoi_chunks"
mkdir -p "$CHUNKDIR" /scratch/xe2/cb8590/paddock-species-logs
rm -f "$CHUNKDIR"/pre_${P}*.csv "$CHUNKDIR"/gpu_${P}*.csv

# Split preserving the header on every chunk (the Python side reads each as a standalone csv).
hdr=$(head -1 "$AOIS")
tail -n +2 "$AOIS" > "$CHUNKDIR/.body"
split -l "$PER_JOB" -d -a 3 "$CHUNKDIR/.body" "$CHUNKDIR/.pre_"
for f in "$CHUNKDIR"/.pre_*; do
    n=$(basename "$f" | sed 's/^\.pre_//')
    { echo "$hdr"; cat "$f"; } > "$CHUNKDIR/pre_${P}${n}.csv"
    rm -f "$f"
done
split -l "$GPU_BATCH" -d -a 3 "$CHUNKDIR/.body" "$CHUNKDIR/.gpu_"
for f in "$CHUNKDIR"/.gpu_*; do
    n=$(basename "$f" | sed 's/^\.gpu_//')
    { echo "$hdr"; cat "$f"; } > "$CHUNKDIR/gpu_${P}${n}.csv"
    rm -f "$f"
done
rm -f "$CHUNKDIR/.body"

declare -a lane_tail
pre_ids=""
n=0
for f in "$CHUNKDIR"/pre_${P}*.csv; do
    lane=$(( n % LANES ))
    prev=${lane_tail[$lane]:-}
    jid=$(qsub ${PRE_MEM:+-l mem=$PRE_MEM} ${prev:+-W depend=afterany:$prev} \
               -v AOIS="$f",OUTDIR="$OUTDIR" "$HERE/presegment.pbs")
    lane_tail[$lane]=$jid
    pre_ids="${pre_ids:+$pre_ids:}$jid"
    n=$((n + 1))
    echo "stage1 $(basename "$f") -> $jid (lane $lane)"
done

m=0
for f in "$CHUNKDIR"/gpu_${P}*.csv; do
    jid=$(qsub -W depend=afterany:"$pre_ids" -v AOIS="$f",OUTDIR="$OUTDIR" "$HERE/sam_segment.pbs")
    echo "stage2 $(basename "$f") -> $jid (after all stage-1)"
    m=$((m + 1))
done
echo "submitted $n stage-1 job(s) across $LANES lane(s) and $m stage-2 job(s)"
