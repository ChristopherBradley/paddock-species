#!/bin/bash
# PREPARED, NOT LAUNCHED. Re-predict 2022/2023/2024 on the adopted shipped+sharma6 classifier.
#
# WHY THIS EXISTS RATHER THAN JUST `run_national.sh predict`. Two of the three years are already
# predicted and merged with the RETIRED group3_map.joblib, and `run_national.sh predict` skips
# any chunk that already has a non-empty output (`[ -s "$M/pred/$b.gpkg" ] && continue`) — the
# same guard that makes a resumed run cheap makes a MODEL SWAP a silent no-op. So the old
# outputs have to be moved out of the way first, and they are ARCHIVED rather than deleted:
# every classifier number currently in the manuscript, PAPER_PLAN.md and the two submission
# packages came from them, and they must stay reproducible until the new run replaces those
# numbers too.
#
#   ./repredict_new_model.sh check              # preflight, launches nothing — safe any time
#   ./repredict_new_model.sh archive 2023       # move retired-model outputs aside (one year)
#   ./repredict_new_model.sh go 2022            # submit predict for one year
#   ./repredict_new_model.sh finish 2022        # audit -> merge -> summary, after predict is done
#
# ORDER (user's plan, 2026-09-08): all three of these years BEFORE segmenting 2017-2021/2025.
#   2022 (never predicted, no archive step) -> 2023 (archive first) -> 2024 (archive first)
#
# Every stage is resumable: re-run `go` to submit whatever is still missing (it respects the
# MAXQ headroom ceiling exactly as run_national.sh does).
set -euo pipefail
cd "$(dirname "$0")"
D=/scratch/xe2/cb8590/paddock-species-data/derived
MODEL=$D/models/group3_map_sharma6.joblib
RETIRED=group3_map_retired          # suffix for the archived pre-adoption outputs

usage() { echo "usage: $0 {check|archive YEAR|go YEAR|finish YEAR}" >&2; exit 2; }

# `find` on a directory that does not exist yet exits non-zero even with stderr silenced, and
# `set -o pipefail` propagates that through `| wc -l` and kills the script — the same trap
# run_national.sh's `status` case documents and dodges with a bare `mkdir -p`. Counting a
# not-yet-created output dir as 0 is the wanted answer here, so swallow it explicitly.
count() { { find "$1" -maxdepth 1 -name "$2" 2>/dev/null || true; } | wc -l; }

case "${1:-}" in
check)
    echo "== model =="
    [ -f "$MODEL" ] && echo "  OK   $MODEL" || { echo "  MISSING $MODEL"; exit 1; }
    /g/data/xe2/John/geospatenv/bin/python - "$MODEL" <<'PY'
import joblib, sys
B = joblib.load(sys.argv[1])
src = B.get("sources")
print(f"  sources={[(k, len(v)) for k, v in src] if src else 'SINGLE-SOURCE (old bundle!)'} "
      f"columns={len(B['columns'])} n_train={B['n_train']} classes={B['classes']}")
assert src and len(src) == 2 and len(B["columns"]) == 153, "not the adopted 153-feature bundle"
print("  OK   two-source 153-feature bundle, as reviewed")
PY
    echo "== per-year state =="
    for y in 2022 2023 2024; do
        M=$D/national$y
        nseg=$(count "$M/samgeo" '*_filt.gpkg')
        naoi=$(( $(wc -l < $M/aois.csv) - 1 ))
        npred=$(count "$M/pred" 'p*.gpkg')
        narch=$(count "$M/pred_$RETIRED" 'p*.gpkg')
        printf "  %s  segmented %6d/%6d (%.1f%%)  pred %3d  archived %3d\n" \
               "$y" "$nseg" "$naoi" "$(echo "$nseg $naoi" | awk '{print 100*$1/$2}')" "$npred" "$narch"
    done
    echo "== queue (must be quiet before submitting: user runs other projects here) =="
    qstat -u cb8590 2>/dev/null | awk 'NR>5' | wc -l | xargs echo "  jobs in queue:"
    echo "== scratch =="
    lquota 2>/dev/null | awk '/xe2 scratch/ {print "  " $0}'
    ;;
archive)
    Y=${2:?year}; M=$D/national$Y
    [ -d "$M/pred" ] || { echo "no $M/pred — nothing to archive"; exit 0; }
    n=$(count "$M/pred" 'p*.gpkg')
    [ "$n" -eq 0 ] && { echo "$M/pred is empty — nothing to archive"; exit 0; }
    [ -e "$M/pred_$RETIRED" ] && { echo "REFUSING: $M/pred_$RETIRED already exists" >&2; exit 1; }
    mv "$M/pred" "$M/pred_$RETIRED"
    echo "archived $n prediction chunks -> $M/pred_$RETIRED"
    for f in $M/national_${Y}_crops.gpkg $M/national_${Y}_crops_classified.gpkg; do
        [ -f "$f" ] && { mv "$f" "${f%.gpkg}_$RETIRED.gpkg"; echo "archived $(basename $f)"; }
    done
    mkdir -p "$M/pred"
    echo "next: $0 go $Y"
    ;;
go)
    Y=${2:?year}; M=$D/national$Y
    npred=$(count "$M/pred" 'p*.gpkg')
    if [ "$npred" -gt 0 ] && [ ! -d "$M/pred_$RETIRED" ]; then
        echo "REFUSING: $M/pred already holds $npred chunks and nothing is archived." >&2
        echo "Those are retired-model outputs — run '$0 archive $Y' first." >&2
        exit 1
    fi
    grep -q group3_map_sharma6 run_national.sh || { echo "run_national.sh MODEL= is not the new model" >&2; exit 1; }
    echo "submitting predict for $Y on $(basename $MODEL) (zarr on by default)"
    YEAR=$Y ./run_national.sh predict
    echo "re-run '$0 go $Y' as the queue drains until all 320 chunks exist, then '$0 finish $Y'"
    ;;
finish)
    Y=${2:?year}
    echo "== audit (does each chunk CONTAIN the tiles it was given?) =="
    YEAR=$Y ./run_national.sh audit
    echo "== merge =="
    YEAR=$Y ./run_national.sh merge
    echo "when the merge job finishes: YEAR=$Y ./run_national.sh summary"
    echo "then re-run the ABS validation so Results reflect the adopted model:"
    echo "  see abs_national.pbs / abs_compare.py (PAPER_PLAN.md Open Issue #8, step 2)"
    ;;
*) usage ;;
esac
