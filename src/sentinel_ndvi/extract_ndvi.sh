#!/bin/bash
# Submit PBS jobs to extract one chunk each, capped at LANES running concurrently.
#   ./extract_ndvi.sh [--force] [--lanes N] [CHUNK_DIR]
#
# CONCURRENCY IS NOT A TUNING KNOB — it is a correctness constraint.
# Every job holds an open connection to the SHARED DEA index database (pgbouncer on
# dea-db.nci.org.au:6432) for its whole run. On 2026-08-06 a fan-out of 17 simultaneous
# jobs exhausted that pool: all 17 blocked forever mid-chunk, a login-node
# `dc.list_products()` also hung, and 16 jobs were killed at the 4 h walltime having done
# almost nothing (~136 SU for 130/1630 trials). One job alone had been running fine. The
# pool recovered the moment the jobs were killed. This is shared infrastructure — other
# NCI users were affected too. Raise LANES only with evidence the pool can take it.
#
# Jobs within a lane are chained with `-W depend=afterany`, so exactly LANES run at once
# ('afterany', not 'afterok', so one bad chunk does not strand the rest of its lane).
# Idempotent: complete chunks are skipped, in-flight chunks are skipped, partial chunks
# resume. --force resubmits everything (e.g. after changing the extraction method).
set -euo pipefail
FORCE=0
LANES=4
while [ $# -gt 0 ]; do
    case "$1" in
        --force) FORCE=1; shift ;;
        --lanes) LANES=$2; shift 2 ;;
        *) break ;;
    esac
done
CHUNK_DIR=${1:-/scratch/xe2/cb8590/paddock-species-data/derived/chunks}
OUTDIR=/scratch/xe2/cb8590/paddock-species-data/derived/sentinel_ts

# PBS -o/-e point here; the dir must exist before the job exits. Kept off /home so
# job logs never land in the git repo.
mkdir -p /scratch/xe2/cb8590/paddock-species-logs

# Chunks already queued/running. Without this, the resume logic below would treat a chunk
# that is mid-flight as "incomplete" and submit a SECOND job appending to the same files.
# Note: on gadi `-u` overrides `-f` and yields only the short listing, so the job ids have
# to be collected first and passed to `qstat -f` individually. `qstat -f` wraps long values
# across tab-indented lines, hence the tr's before grepping the Variable_List entry.
inflight=""
jobids=$(qstat -u "$USER" 2>/dev/null | awk '/^[0-9]+\./ {print $1}')
if [ -n "$jobids" ]; then
    # Anchored on .csv because CHUNK= also appears in Submit_arguments, where the stripped
    # newlines leave no comma to terminate the match.
    inflight=$(qstat -f $jobids 2>/dev/null | tr -d ' \t' | tr -d '\n' \
               | grep -o 'CHUNK=[^,]*\.csv' | sed 's/CHUNK=//' | sort -u || true)
fi

shopt -s nullglob
chunks=("$CHUNK_DIR"/chunk_*.csv)
if [ ${#chunks[@]} -eq 0 ]; then
    echo "No chunk_*.csv in $CHUNK_DIR — run make_chunks.py first." >&2
    exit 1
fi
n_sub=0
n_skip=0
declare -a lane_tail          # last job id submitted in each lane, for the depend chain
for f in "${chunks[@]}"; do
    name=$(basename "$f" .csv)
    status="$OUTDIR/${name}_status.csv"
    if grep -qxF "$f" <<<"$inflight"; then
        echo "skip $name (already queued/running)"
        n_skip=$((n_skip + 1))
        continue
    fi
    # Only skip a *complete* chunk. extract_ndvi.py appends status per trial, so a chunk
    # killed mid-run leaves a short file — resubmitting it resumes from where it stopped.
    if [ "$FORCE" -eq 0 ] && [ -f "$status" ]; then
        want=$(( $(wc -l < "$f") - 1 ))
        # Count only OK/EMPTY, matching what extract_ndvi.py treats as done. Counting ALL
        # status rows would let a chunk of 97 OK + 3 FAILED read as 100/100 complete, so the
        # failures would never be resubmitted — the shell would call the chunk finished while
        # the Python resume logic was still willing to retry them.
        have=$(tail -n +2 "$status" | grep -cE ',(OK|EMPTY),' || true)
        if [ "$have" -ge "$want" ]; then
            echo "skip $name ($have/$want trials succeeded)"
            n_skip=$((n_skip + 1))
            continue
        fi
        echo "resubmit $name ($have/$want succeeded — retrying the rest)"
    fi
    lane=$(( n_sub % LANES ))
    prev=${lane_tail[$lane]:-}
    if [ -n "$prev" ]; then
        jid=$(qsub -W depend=afterany:"$prev" -v CHUNK="$f" extract_ndvi.pbs)
        echo "$name -> $jid (lane $lane, after $prev)"
    else
        jid=$(qsub -v CHUNK="$f" extract_ndvi.pbs)
        echo "$name -> $jid (lane $lane, head)"
    fi
    lane_tail[$lane]=$jid
    n_sub=$((n_sub + 1))
done
echo "submitted $n_sub job(s) across $LANES lane(s), skipped $n_skip of ${#chunks[@]} chunks"
if [ "$n_sub" -gt 0 ]; then
    echo "at most $LANES will run concurrently — see the header comment before raising this"
fi
