#!/bin/bash
# The national single-year run: every tile the NLUM winter-crop mask touches, for one year.
#
# WHY 2024 AND NOT 2025. 2025 has the better imagery — the Riverina run measured 43.5 clear
# observations per paddock in 2025 against 35.9 in 2024, and the highest classified share of any
# of the nine years. It also has NO independent reference. ABS publishes sown area by SA2 for
# 2022, 2023 and 2024 only, and ABARES' 2025 state figures still carry its `f` forecast flag.
# Everything this project has learned in the last day came from scoring the map against ABS at
# SA2 (`ABS_COMPARISON_100km.md`), and that check is simply unavailable for 2025. A map that
# cannot be scored is not the one to spend 5 KSU on.
#
# WHY THE UNION AT prob > 2500. That is the mask the cost benchmark was measured on: 99,465
# tiles, of which 96.4 % are already in the cereal surface, so adding canola and legumes costs
# 3.6 % more tiles rather than 44 % more. Raising the threshold to fit a budget would not make
# the run cheaper per tile, it would make the product something other than national — a map with
# holes in the marginal cropping country, which is exactly where a crop-type map is interesting.
#
# WHY MANY SMALL JOBS. NCI bills walltime USED, not requested, so 320 short jobs and 40 long
# ones cost the same SUs — but short jobs schedule into gaps and long ones wait for a clean
# window. This is the user's "many small jobs" heuristic (CLAUDE.md), and here it costs nothing
# to follow.
#
# WHY EACH SAM JOB DEPENDS ON ONLY ITS OWN CHUNKS. `run_map100.sh` chains every SAM job behind
# EVERY presegment job, which serialises the two stages: no GPU work starts until the slowest
# CPU chunk on the continent finishes. At 10,404 tiles that cost minutes. At 99,465 it would
# cost hours, so here SAM job i waits only on the presegment chunks whose tiles it will read.
#
#   YEAR=2023 ./run_national.sh grid       # copy the 2024 tile grid, relabelled to this year
#   ./run_national.sh chunks       # split the AOI list, preserving block order
#   ./run_national.sh presegment   # ~320 jobs
#   ./run_national.sh sam          # ~40 GPU jobs, each chained to its own 8 chunks
#   ./run_national.sh predict      # inference, chained per chunk to its SAM job
#   ./run_national.sh status
#   ./run_national.sh repair       # re-derive and re-run whatever is missing on disk
#   ./run_national.sh repair-check # did any repair job vanish on dependency release?
#   ./run_national.sh repair-sam   # SAM over the repaired tiles
#   ./run_national.sh resam        # SAM over tiles with a composite but no segmentation yet
#                                 #   (covers SAM jobs killed at their 4h walltime mid-chunk —
#                                 #    repair-sam only catches the missing-composite subset)
#   ./run_national.sh repredict    # drop predictions written over unsegmented ground
#   ./run_national.sh audit        # do the predictions CONTAIN every tile they were given?
#                                 #   (the only check that sees a prediction written before
#                                 #    its segmentation existed — status cannot)
#   ./run_national.sh merge        # one national GeoPackage (refuses if chunks are incomplete)
#   ./run_national.sh boundary     # de-duplicate the ~350 m tile-overlap band in the merged file
#                                 #   -> national_${YEAR}_crops_merged.gpkg (TILE_BOUNDARY_MERGE.md)
#   ./run_national.sh summary      # per-category polygon count/area for this year, from pred/*.gpkg
#   ./run_national.sh cost         # SUs billed so far, by stage
#
# MULTI-YEAR RUNS. YEAR selects the working directory ($D/national$YEAR) and the imagery window;
# it defaults to 2024 so every command above is unchanged for the year that already exists. Every
# other year MUST start with `grid`, which copies 2024's aois.csv verbatim (same lat/lon/half_m/
# grid_r/grid_c/block_r/block_c — only stub/year/start/end change) rather than re-deriving it from
# the NLUM raster: nlum_tiles.py's mask is a static ~2020-21 survey, so a fresh derivation would
# be numerically identical, but copying is the more honest guarantee and avoids any risk of the
# raster path or a library version drifting between now and whenever 2024's grid was built.
# OVERNIGHT_IMPROVEMENTS_SUMMARY.md's recommendation to keep one fixed grid across years (the
# same convention run_map100.sh has always used for its 9-year Riverina pilot) is what this
# generalises to national scale — do NOT pass map_regions.py's --offset-seed here, and do not
# regenerate aois.csv from the raster for a non-2024 year.
set -euo pipefail
PY=/g/data/xe2/John/geospatenv/bin/python
D=/scratch/xe2/cb8590/paddock-species-data/derived
REPO=/home/147/cb8590/Projects/paddock-species
cd "$REPO/src/paddocks"
export PROJ_NETWORK=OFF

YEAR=${YEAR:-2024}
GRID_FROM=${GRID_FROM:-2024}   # which year's aois.csv `grid` copies from
M=$D/national$YEAR
AOIS=$M/aois.csv
POLY=$M/samgeo
CH=$M/chunks
NCHUNK=${NCHUNK:-320}
PER_SAM=${PER_SAM:-8}          # presegment chunks per SAM job -> 40 GPU jobs
LANES=${LANES:-64}             # max presegment/predict jobs running at once (datacube pooler)

case "${1:-}" in
grid)
    if [ "$YEAR" = "$GRID_FROM" ]; then
        echo "YEAR=$GRID_FROM equals GRID_FROM — $AOIS already exists, nothing to do" >&2
        exit 0
    fi
    BASE=$D/national$GRID_FROM/aois.csv
    [ -f "$BASE" ] || { echo "base grid $BASE not found" >&2; exit 1; }
    mkdir -p $M
    $PY - "$BASE" "$YEAR" "$AOIS" <<'PYEOF'
import sys, pandas as pd
base, year, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
A = pd.read_csv(base)
before = A["year"].iat[0]
# Only the year-dependent columns move. stub embeds the base year once (nlum_<year>_r..._c...)
# — replace that exact substring rather than doing a blind global year-string replace, so a
# coincidental "2024" inside lat/lon (there is none at 6dp here, but never rely on that) can
# never be touched.
A["stub"] = A["stub"].str.replace(f"nlum_{before}_", f"nlum_{year}_", regex=False)
A["year"] = year
A["start"] = f"{year}-01-01"
A["end"] = f"{year}-12-31"
A.to_csv(out, index=False)
print(f"{len(A):,} tiles -> {out} (grid copied from {base}, relabelled {before} -> {year})")
PYEOF
    ;;
chunks)
    mkdir -p $CH; rm -f $CH/*.csv
    # Contiguous slices of the already block-sorted AOI list. nlum_tiles.py --all sorts by
    # (block_r, block_c, grid_r, grid_c), so slicing preserves the scene locality that is worth
    # 4.0x on pre-segment. Re-sorting or shuffling here would throw that away.
    $PY - "$AOIS" "$CH" "$NCHUNK" <<'PYEOF'
import sys, pandas as pd, numpy as np
aois, out, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
A = pd.read_csv(aois)
for i, part in enumerate(np.array_split(A, n)):
    part.to_csv(f"{out}/p{i:03d}.csv", index=False)
print(f"{len(A)} tiles -> {n} chunks of ~{len(A)//n} in {out}")
PYEOF
    ;;
presegment)
    mkdir -p $POLY
    rm -f $M/chunkjobs.txt
    # 4 GB, not 8. presegment.pbs warns that 4 GB OOMs on 2023+ — that warning was measured on
    # AOIs wider than 5 km. The Riverina run put 10,404 tile-years THROUGH 2024 AND 2025 at 3 km
    # and 4 GB with zero failures, so the warning does not apply at this tile size. If a chunk
    # does OOM (exit 137, no traceback) it resumes: every composite is written as it is built
    # and an existing one is skipped, so re-submit that chunk alone with -l mem=8GB.
    #
    # LANES, NOT A FREE-FOR-ALL. The first national attempt submitted all 320 chunks at once and
    # every one of them ran. That exhausted the DEA datacube's shared connection pooler
    # ("FATAL: no more connections allowed"), and because each AOI is individually wrapped in
    # try/except, **79 % of tiles failed while every PBS job still exited 0**. The composites
    # were missing and nothing downstream would have flagged it.
    #
    # So concurrency is capped at LANES chains, each running its chunks one after another. The
    # pooler is shared with every other DEA user on gadi, so this is courtesy as much as
    # correctness — and it costs no SUs, only wall time, because the work is identical.
    #
    # LANES IS NOT ENOUGH ON ITS OWN, AND THE SECOND ATTEMPT PROVED IT. 56 of these 320 jobs
    # never ran a single tile: chunks p264-p319, 17,361 tiles, 90 % of it Victoria, missing from
    # the finished run with every PBS job reporting success.
    #
    # WHAT ACTUALLY HAPPENED, from the PBS records. Each of the 56 was DESTROYED AT THE INSTANT
    # ITS DEPENDENCY WAS SATISFIED, rather than being released into the queue — every one has an
    # mtime 7-10 s BEFORE its parent's completion:
    #     ps_p264 died 05:15:27   parent ps_p200 finished 05:15:36  (exit 0)
    #     ps_p300 died 04:02:34   parent ps_p236 finished 04:02:41  (exit 0)
    #     ps_p316 died 05:31:27   parent ps_p252 finished 05:31:36  (exit -29)
    # They left no log, no Exit_status and no comment, which is why this was invisible. The
    # parent's exit status is irrelevant (both 0 and -29 appear), so `afterany` behaved
    # correctly; the failure is in the requeue on the far side of it.
    #
    # WHY THE REQUEUE WAS REFUSED IS INFERRED, NOT PROVEN — PBS recorded no reason. The
    # available evidence points at the per-user queued-job ceiling:
    #     queued_jobs_threshold = [u:PBS_GENERIC=200]     (qstat -Qf normal-exec)
    # All 320 sat in the queue from submit time (a dependency staggers when a job STARTS, not
    # when it is QUEUED), and the casualties are exactly the LAST job in each of lanes 8-63 —
    # the deepest in their chains, released last, while ~300 siblings still occupied the queue.
    # The 5th jobs of lanes 0-7 (p256-p263) released early enough and survived.
    #
    # NOTE `Hold_Types = s` IS NOT EVIDENCE OF THIS. It is simply how PBS marks any job held on
    # a dependency; every healthy chained job here carries it too. It was misread as a smoking
    # gun once already — do not read it as one again.
    #
    # So the ceiling is respected here rather than discovered: submission stops at MAXQ instead
    # of building a queue deep enough for a release to be refused. Re-run to submit the rest —
    # presegment skips AOIs whose composite exists, so a second pass costs only the remainder.
    MAXQ=${MAXQ:-180}
    inq=$(qstat -u cb8590 2>/dev/null | awk 'NR>5' | wc -l)
    room=$(( MAXQ - inq ))
    echo "queue holds $inq jobs; headroom to MAXQ=$MAXQ is $room"
    # Which chunks already have every composite they need. Without this the resume advice above
    # is false — the loop would re-submit all 320 and blow the ceiling again on the second pass.
    DONE=$(mktemp); trap 'rm -f "$DONE"' EXIT
    $PY - "$CH" "$POLY" > "$DONE" <<'PYEOF'
import csv, glob, os, sys
ch, poly = sys.argv[1], sys.argv[2]
comp = {f[:-4] for f in os.listdir(poly)
        if f.endswith('.tif') and not f.endswith('_segment.tif')} if os.path.isdir(poly) else set()
for cf in sorted(glob.glob(os.path.join(ch, 'p*.csv'))):
    names = [r['stub'] for r in csv.DictReader(open(cf))]
    if names and all(n in comp for n in names):
        print(os.path.basename(cf)[:-4])
PYEOF
    echo "$(wc -l < "$DONE") chunks already fully composited — skipping them"
    # Same in-flight guard as `predict` (see its comment) — a chunk with a live ps_$b job is
    # not yet in $DONE (its composites aren't finished) but must not be resubmitted either.
    LIVE_NAMES=$(mktemp); qstat -u cb8590 -w 2>/dev/null | awk 'NR>5 {print $4}' > "$LIVE_NAMES"
    trap 'rm -f "$LIVE_NAMES"' EXIT
    i=0; skipped=0; declare -a PREV
    for f in $CH/p*.csv; do
        b=$(basename "$f" .csv)
        if grep -qx "$b" "$DONE"; then skipped=$((skipped + 1)); continue; fi
        grep -qx "ps_$b" "$LIVE_NAMES" && { skipped=$((skipped + 1)); continue; }
        if [ $room -le 0 ]; then
            echo "STOPPING at $b — $(ls $CH/p*.csv | wc -l) chunks wanted, $i submitted."
            echo "Re-run '$0 presegment' when the queue drains; it resumes where this left off."
            break
        fi
        lane=$((i % LANES))
        DEP=""
        [ -n "${PREV[$lane]:-}" ] && DEP="-W depend=afterany:${PREV[$lane]}"
        JID=$(qsub $DEP -l mem=4GB -l walltime=03:00:00 \
                   -v AOIS="$f",OUTDIR=$POLY -N ps_$b presegment.pbs)
        PREV[$lane]=${JID%%.*}
        echo "$b ${JID%%.*}" >> $M/chunkjobs.txt
        i=$((i + 1)); room=$((room - 1))
    done
    echo "submitted $i presegment jobs across $LANES lanes ($skipped chunks already done)"
    ;;
sam)
    mkdir -p $M/sam
    rm -f $M/sam/jobmap.txt
    n=$(ls $CH/p*.csv | wc -l)
    i=0; k=0
    while [ $i -lt $n ]; do
        part=$(seq -f "p%03g" $i $((i + PER_SAM - 1)) | head -$PER_SAM)
        # The AOI list this GPU job will segment: its own chunks, concatenated in order.
        $PY - "$CH" "$M/sam/s$k.csv" $part <<'PYEOF'
import sys, os, pandas as pd
ch, out = sys.argv[1], sys.argv[2]
fs = [os.path.join(ch, f"{b}.csv") for b in sys.argv[3:]]
fs = [f for f in fs if os.path.exists(f)]
pd.concat([pd.read_csv(f) for f in fs], ignore_index=True).to_csv(out, index=False)
PYEOF
        # Depend ONLY on the presegment jobs feeding this GPU job, read from the map written at
        # submit time. Looked up by NAME through qstat this used to miss under load, and a
        # missing dependency is invisible: the GPU job runs early, finds no composites, exits
        # "nothing to segment" and still costs a gpuvolta booking.
        IDS=$(for b in $part; do awk -v b="$b" '$1==b {print $2}' $M/chunkjobs.txt; done \
              | tr '\n' ':' | sed 's/:$//')
        [ -n "$IDS" ] && DEP="-W depend=afterany:$IDS" || DEP=""
        JID=$(qsub $DEP -l walltime=04:00:00 -v AOIS=$M/sam/s$k.csv,OUTDIR=$POLY \
              -N sam_s$k sam_segment.pbs)
        # Record which GPU job covers which chunks, so `predict` can depend on exactly the one
        # that produces its polygons instead of waiting for the whole GPU stage.
        for b in $part; do echo "$b ${JID%%.*}" >> $M/sam/jobmap.txt; done
        i=$((i + PER_SAM)); k=$((k + 1))
    done
    echo "submitted $k SAM jobs of $PER_SAM chunks each"
    ;;
predict)
    mkdir -p $M/pred
    LIVE=$(mktemp); qstat -u cb8590 2>/dev/null | awk 'NR>5 {print $1}' > "$LIVE"
    # Chunk names with a job ALREADY queued or running for them. Without this, re-running
    # `predict` before every prior job has finished (the normal way to resume once headroom
    # frees up — predict jobs run up to 5h, so this is the common case, not an edge case)
    # resubmits a duplicate job for every chunk still in flight: found 2026-09-03 when a 15-min
    # polling loop did exactly this and produced 2-3x duplicate jobs racing to write the same
    # output path (`P.to_file` truncates-then-writes, so two concurrent writers risk corrupting
    # the GeoPackage, not just wasting the SU of the redundant run).
    LIVE_NAMES=$(mktemp); qstat -u cb8590 -w 2>/dev/null | awk 'NR>5 {print $4}' > "$LIVE_NAMES"
    trap 'rm -f "$LIVE" "$LIVE_NAMES"' EXIT
    # The abstain path stays PERMISSIVE on purpose: --crop-gate-amp 0.35 keeps everything with a
    # crop-like season, and every polygon ships its ndvi_amp, confidence and class probabilities
    # so a reader can tighten it afterwards. CONFIDENCE_FILTER.md measured what that filtering
    # buys: raising the gate to ~0.58 brings mapped crop area from 1.59x ABS to 1.03x and cuts
    # the canola share error from 12.2 to 5.1 points. Baking that threshold in here would (a)
    # fit the map to ABS, destroying the only independent validation, and (b) throw away the
    # sown-but-not-harvested land, which is a real land use somebody may want.
    #
    # --crop-gate-shape + --shape-gate-skip-classes Canola Cereal Legume: the two-pass phenology
    # gate (OVERNIGHT_IMPROVEMENTS_SUMMARY.md, ABS_COMPARISON_100km_shapegate_twopass.md) — the
    # only config that improved BOTH the area ratio (1.59->1.19) and canola share error
    # (9.4->5.2 pts) on the 9-year Riverina check, at zero extra SU since it only changes
    # predict_tile.py's flags.
    #
    # ALL THREE CLASSES SKIP THE GATE (changed 2026-09-07, user request) -- previously only
    # Canola did, and every OTHER class's shape-gate failure set abstain_reason=no_crop_shape
    # AND nulled pred, discarding the class label. Now every class keeps its pred even on a
    # shape-gate failure; predict_tile.py's shape-gate logic (see its own comment, same date)
    # was fixed so abstain_reason is still recorded for a skipped class's failure, so nothing is
    # made LESS auditable by this -- a reader filtering on `abstain_reason == ''` (or the
    # inverse, to inspect what the gate would have rejected) gets exactly the same view as
    # before. What changes is the RAW/default file: it now shows a classified label for every
    # polygon regardless of the shape gate, matching the amplitude gate's existing permissive
    # design (see above) rather than being the one gate that silently dropped the label.
    #
    # DOWNSTREAM CONSUMERS MUST KEY OFF abstain_reason, NOT pred.notna(). `pred` alone no longer
    # means "passed every gate" for any class. Already updated for this: run_national.sh's own
    # `summary` SQL, abs_compare.py, filter_sweep.py, consensus_layer.py, polygon_stability.py.
    # Any NEW analysis script reading these predictions needs the same care.
    # Same ceiling as `presegment` — see the long note there. `repredict` hands this stage ~67
    # chunks at once, which is exactly the shape of submission that lost 56 jobs.
    MAXQ=${MAXQ:-180}
    inq=$(qstat -u cb8590 2>/dev/null | awk 'NR>5' | wc -l)
    room=$(( MAXQ - inq ))
    echo "queue holds $inq jobs; headroom to MAXQ=$MAXQ is $room"
    pi=0; declare -a PPREV
    for f in $CH/p*.csv; do
        b=$(basename "$f" .csv)
        [ -s "$M/pred/${b}.gpkg" ] && continue
        grep -qx "pr_$b" "$LIVE_NAMES" && continue
        if [ $room -le 0 ]; then
            echo "STOPPING at $b — re-run '$0 predict' when the queue drains (it skips finished AND in-flight chunks)"
            break
        fi
        # Two dependencies, collected as a list and turned into ONE flag at the end:
        #   * the SAM job that segments this chunk's tiles — without it the job runs early,
        #     finds no polygons and writes an empty GeoPackage that the `-s` guard above would
        #     then treat as done, leaving a permanent hole nothing downstream flags;
        #   * the previous predict job in this lane, because predict_tile.py also reads the
        #     datacube and 320 simultaneous clients is what broke pre-segment.
        DEPS=""
        if [ -f $M/sam/jobmap.txt ]; then
            j=$(awk -v b="$b" '$1==b {print $2}' $M/sam/jobmap.txt | head -1)
            [ -n "$j" ] && grep -q "^$j\." "$LIVE" && DEPS="$j"
        fi
        lane=$((pi % LANES))
        [ -n "${PPREV[$lane]:-}" ] && DEPS="${DEPS:+$DEPS:}${PPREV[$lane]}"
        DEP=""; [ -n "$DEPS" ] && DEP="-W depend=afterany:$DEPS"
        # MODEL: group3_map_sharma6.joblib (adopted 2026-09-08 after INDEPENDENT_REVIEW_shipped_
        # sharma6.md, verdict ADOPT: macro F1 0.890/0.892 vs the retired group3_map.joblib's
        # 0.821/0.823, canola@5%FPR unchanged). Two-source bundle (indices + bands-keep-families);
        # predict_tile.py runs one zonal pass per source -- do NOT point this back at
        # group3_map.joblib, which is kept on disk only so 2023/2024's pre-adoption outputs
        # stay reproducible until they are re-predicted.
        JID=$(qsub $DEP -l mem=8GB -l walltime=05:00:00 \
             -v AOIS="$f",POLYDIR=$POLY,MODEL=$D/models/group3_map_sharma6.joblib,\
OUT=$M/pred/${b}.gpkg,EXTRA_ARGS="--max-area-ha 300 --crop-gate-amp 0.35 --crop-gate-shape $D/models/phenology_gate.joblib --shape-gate-skip-classes Canola Cereal Legume --yield-model $D/models/cereal_yield.joblib" \
             -N pr_$b predict_tile.pbs)
        PPREV[$lane]=${JID%%.*}
        pi=$((pi + 1)); room=$((room - 1))
    done
    echo "submitted $pi predict jobs across $LANES lanes"
    ;;
status)
    # `ls $POLY/*.tif` USED TO BE HERE AND IT LIED. At 162,334 files the glob blows past
    # ARG_MAX, `ls` dies with "Argument list too long", and `wc -l` counts an empty pipe — so
    # the line read `composites: 0` whether the true count was 0 or 81,540. That is worse than
    # no check at all: it is the instrument that should have caught the 56 missing chunks
    # (§ the queued_jobs_threshold note in `presegment`) reading zero for hours while nothing
    # was wrong with it. `find` streams its results and never builds an argv, so it cannot
    # develop this failure at any scale.
    #
    # mkdir -p HERE, NOT JUST A COMMENT. `find` on a directory that does not exist yet (e.g.
    # $M/pred before `predict` has ever run for this year) exits non-zero even with its stderr
    # redirected to /dev/null, and pipefail propagates that through the `| wc -l` pipeline and
    # aborts the whole script under set -e — found 2026-09-01 checking status on a fresh
    # national2023 right after `presegment`, before `predict` had created $M/pred. Silent to
    # `status`'s caller too: no error text, just a dead script. Both mkdirs are idempotent no-ops
    # once the later stage creates the directory for real.
    mkdir -p $POLY $M/pred
    n=$(( $(wc -l < $AOIS) - 1 ))
    nc=$(find $POLY -maxdepth 1 -name '*.tif' ! -name '*_segment.tif' 2>/dev/null | wc -l)
    ns=$(find $POLY -maxdepth 1 -name '*_filt.gpkg' 2>/dev/null | wc -l)
    np=$(find $M/pred -maxdepth 1 -name 'p*.gpkg' 2>/dev/null | wc -l)
    ncc=$(find $CH -maxdepth 1 -name 'p*.csv' 2>/dev/null | wc -l)
    echo "AOIs:        $n tiles"
    printf "composites:  %d (%.1f %%)\n" $nc $(echo "$nc $n" | awk '{print 100*$1/$2}')
    printf "segmented:   %d (%.1f %%)\n" $ns $(echo "$ns $n" | awk '{print 100*$1/$2}')
    echo "predicted:   $np of $ncc chunks"
    # MATCH THE REPAIR JOBS TOO. This pattern listed only ps_/sam_/pr_ and so reported
    # "queue: 0 jobs" while four rs_s* GPU jobs were an hour into their walltime — which read
    # exactly like the vanishing-job failure and sent one investigation down a blind alley.
    # A status line that omits a whole class of job is the same liability as one that overflows.
    JOBS='ps_p|sam_s|pr_p|rp_r|rs_s|rsm_z'
    q=$(qstat -u cb8590 2>/dev/null | grep -cE "$JOBS" || true)
    r=$(qstat -u cb8590 2>/dev/null | grep -E "$JOBS" | awk '$10=="R"' | wc -l || true)
    echo "queue:       $q jobs ($r running)"
    # A count of files is not a count of FINISHED WORK. Report the two ways a chunk can be
    # quietly incomplete: never segmented, and — the one that actually bit — predicted anyway.
    $PY - "$CH" "$POLY" "$M/pred" <<'PYEOF'
import csv, glob, os, sys
ch, poly, pred = sys.argv[1:4]
seg = {f[:-len('_filt.gpkg')] for f in os.listdir(poly) if f.endswith('_filt.gpkg')}
done = {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(pred, 'p*.gpkg'))}
gaps, holes, miss = [], [], 0
for cf in sorted(glob.glob(os.path.join(ch, 'p*.csv'))):
    b = os.path.basename(cf)[:-4]
    names = [r['stub'] for r in csv.DictReader(open(cf))]
    frac = sum(n in seg for n in names) / len(names)
    if frac < 0.98:
        gaps.append(b); miss += len(names) - sum(n in seg for n in names)
        if b in done:
            holes.append(b)
print(f"incomplete:  {len(gaps)} chunks below 98 % segmented ({miss} tiles)")
print(f"SILENT HOLES:{len(holes):4d} chunks PREDICTED over incomplete segmentation"
      + (f" -> {' '.join(holes[:8])}{' ...' if len(holes) > 8 else ''}" if holes else ""))
PYEOF
    ;;
repair)
    # WHAT THIS EXISTS FOR. The first national run finished with 74 of 320 chunks incomplete:
    # 56 that never ran a single tile, and 16 killed at the 3 h walltime part-way through.
    # Neither showed up anywhere — SAM printed "nothing to segment" and returned 0, predict
    # wrote a near-empty GeoPackage and returned 0, and `status` was reading 0 composites for
    # unrelated reasons. `repair` re-derives what is missing FROM THE FILES ON DISK rather than
    # from any job record, so it is correct no matter how the gap was produced.
    #
    # KEEP THE QUEUE SHALLOW. See the long note in `presegment`: the 56 lost chunks were each
    # destroyed at the moment their dependency was satisfied, and the best available explanation
    # is the per-user queued-job ceiling refusing the requeue —
    #     queued_jobs_threshold = [u:PBS_GENERIC=200]     (qstat -Qf normal-exec)
    # — with ~300 siblings still in the queue ahead of them. So this path measures real headroom
    # before every qsub and stops when it runs out, and uses shallower chains (24 lanes over 72
    # jobs = 3 deep, against 64 lanes x 5) so fewer releases happen under a loaded queue.
    # Re-running is free: the lists are rebuilt from what is on disk, not from a job record.
    mkdir -p $M/repair
    # Only the tiles that are actually missing a composite, packed into evenly sized jobs.
    # Re-submitting whole chunks would work (presegment skips existing composites) but would
    # size the jobs by tiles already done, which is how the 3 h walltime kills happened.
    $PY - "$CH" "$POLY" "$M/repair" "${REPAIR_TILES:-250}" <<'PYEOF'
import csv, glob, os, sys
ch, poly, out, per = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
comp = {f[:-4] for f in os.listdir(poly)
        if f.endswith('.tif') and not f.endswith('_segment.tif')}
rows, hdr = [], None
for cf in sorted(glob.glob(os.path.join(ch, 'p*.csv'))):
    r = csv.DictReader(open(cf))
    for x in r:
        if x['stub'] not in comp:
            hdr = hdr or list(x.keys()); rows.append(x)
for f in glob.glob(os.path.join(out, 'r*.csv')):
    os.remove(f)
for i in range(0, len(rows), per):
    with open(os.path.join(out, f"r{i // per:03d}.csv"), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=hdr); w.writeheader(); w.writerows(rows[i:i + per])
print(f"{len(rows)} tiles missing a composite -> {(len(rows) + per - 1) // per} repair jobs")
PYEOF
    rm -f $M/repair/jobs.txt
    # Headroom against the per-user queued-job ceiling, measured now and decremented as we go.
    MAXQ=${MAXQ:-180}
    inq=$(qstat -u cb8590 2>/dev/null | awk 'NR>5' | wc -l)
    room=$(( MAXQ - inq ))
    echo "queue holds $inq jobs; headroom to MAXQ=$MAXQ is $room"
    i=0; declare -a RPREV
    for f in $M/repair/r*.csv; do
        b=$(basename "$f" .csv)
        if [ $room -le 0 ]; then
            echo "OUT OF HEADROOM at $b — re-run '$0 repair' when the queue drains (idempotent)"
            break
        fi
        lane=$((i % ${RLANES:-24}))
        DEP=""
        [ -n "${RPREV[$lane]:-}" ] && DEP="-W depend=afterany:${RPREV[$lane]}"
        # 6 h, not 3. The 16 walltime kills were 310-tile chunks at a 3 h cap; these are 250
        # tiles with double the headroom, and a job that still runs out resumes on re-submit
        # because every composite is written as it is built.
        JID=$(qsub $DEP -l mem=4GB -l walltime=06:00:00 \
                   -v AOIS="$f",OUTDIR=$POLY -N rp_$b presegment.pbs)
        RPREV[$lane]=${JID%%.*}
        echo "$b ${JID%%.*}" >> $M/repair/jobs.txt
        i=$((i + 1)); room=$((room - 1))
    done
    echo "submitted $i repair presegment jobs across ${RLANES:-24} lanes"
    echo "next: '$0 repair-sam' once these finish, then '$0 repredict'"
    ;;
repair-check)
    # THE WATCHDOG FOR THE FAILURE THAT STARTED ALL THIS. A repair job can die exactly the way
    # the original 56 did — destroyed on dependency release, no log, no Exit_status, PBS content
    # that nothing is wrong. The only way to see it is to ask, per submitted job, whether it
    # ever produced a log; a job that is neither live nor logged did not run.
    [ -f $M/repair/jobs.txt ] || { echo "no repair submitted"; exit 0; }
    LOGS=/scratch/xe2/cb8590/paddock-species-logs
    live=$(qstat -u cb8590 2>/dev/null | awk 'NR>5 {print $1}' | cut -d. -f1)
    # ORDER MATTERS: check the LIVE queue before the log file. A running job has no log yet, so
    # "no log" alone means vanished-or-running and cannot tell them apart — reading it as
    # vanished raises a false alarm on every healthy in-flight job.
    check() {                       # $1 = label, $2 = "name jobid" file
        local nlive=0 nran=0 dead="" b j
        while read b j; do
            if echo "$live" | grep -qx "$j"; then nlive=$((nlive + 1))
            elif [ -f "$LOGS/$j.gadi-pbs.OU" ]; then nran=$((nran + 1))
            else dead="$dead $b($j)"
            fi
        done < "$2"
        echo "$1: $nran ran, $nlive still queued/running"
        [ -n "$dead" ] && { echo "DIED WITHOUT RUNNING:$dead" >&2; return 1; }
        return 0
    }
    rc=0
    check "repair presegment" $M/repair/jobs.txt || rc=1
    # The SAM half was unwatched, which is how 4 of its 9 jobs went unaccounted for long enough
    # to look like a second outbreak of the vanishing failure. Both halves are checked now.
    if [ -f $M/repair/sam/jobmap.txt ]; then
        sort -u -k2 $M/repair/sam/jobmap.txt | awk '!seen[$2]++ {print $1, $2}' > /tmp/rsam.$$
        check "repair SAM" /tmp/rsam.$$ || rc=1
        rm -f /tmp/rsam.$$
    fi
    [ $rc -ne 0 ] && {
        echo "-> re-run '$0 repair' / 'repair-sam' (idempotent) once the queue drains" >&2; exit 1; }
    echo "no jobs vanished — the dependency releases are holding"
    ;;
repair-sam)
    # SAM over the repaired tiles only. Same batching rationale as `sam` — one model load
    # amortised over many AOIs — but chained to the repair presegment jobs that feed it.
    mkdir -p $M/repair/sam
    rm -f $M/repair/sam/jobmap.txt
    n=$(ls $M/repair/r*.csv 2>/dev/null | wc -l)
    [ "$n" -eq 0 ] && { echo "no repair lists — run '$0 repair' first" >&2; exit 1; }
    MAXQ=${MAXQ:-180}
    inq=$(qstat -u cb8590 2>/dev/null | awk 'NR>5' | wc -l)
    room=$(( MAXQ - inq )); echo "headroom $room"
    i=0; k=0
    while [ $i -lt $n ]; do
        [ $room -le 0 ] && { echo "OUT OF HEADROOM — re-run '$0 repair-sam' later"; break; }
        part=$(seq -f "r%03g" $i $((i + PER_SAM - 1)) | head -$PER_SAM)
        $PY - "$M/repair" "$M/repair/sam/s$k.csv" $part <<'PYEOF'
import sys, os, pandas as pd
d, out = sys.argv[1], sys.argv[2]
fs = [os.path.join(d, f"{b}.csv") for b in sys.argv[3:]]
fs = [f for f in fs if os.path.exists(f)]
pd.concat([pd.read_csv(f) for f in fs], ignore_index=True).to_csv(out, index=False)
PYEOF
        IDS=$(for b in $part; do awk -v b="$b" '$1==b {print $2}' $M/repair/jobs.txt; done \
              | tr '\n' ':' | sed 's/:$//')
        [ -n "$IDS" ] && DEP="-W depend=afterany:$IDS" || DEP=""
        JID=$(qsub $DEP -l walltime=04:00:00 -v AOIS=$M/repair/sam/s$k.csv,OUTDIR=$POLY \
              -N rs_s$k sam_segment.pbs)
        for b in $part; do echo "$b ${JID%%.*}" >> $M/repair/sam/jobmap.txt; done
        i=$((i + PER_SAM)); k=$((k + 1)); room=$((room - 1))
    done
    echo "submitted $k repair SAM jobs"
    ;;
audit)
    # THE CHECK THAT `status` AND `repredict` CANNOT MAKE, and the one that caught the third
    # instance of this project's recurring failure.
    #
    # Both of those ask whether the SEGMENTATION exists on disk. That is the right question
    # while a run is in flight and the wrong one afterwards, because it is answered by the state
    # of the world NOW, not by what a prediction job actually read when it ran. On 2026-08-26 the
    # repair re-segmented 17,925 tiles between 12:47 and 15:56 — hours AFTER 314 of the 320
    # prediction files had already been written. Every chunk then looked healthy to both
    # commands (segmented 100 %, SILENT HOLES 0) while 17,146 tiles were absent from the
    # predictions — 90 % of everything the repair had just rebuilt. Victoria came out of the ABS
    # comparison at an area ratio of 0.09 against 1.46 in NSW, and nothing else showed it.
    #
    # So ask the prediction what it CONTAINS. Every polygon carries the `stub` of the tile it
    # came from, so the set of tiles a chunk actually predicted is recoverable from its own
    # output: no job record, no timestamp, no trust in an exit status. A tile that is in the
    # chunk list and absent from the chunk's own GeoPackage was not predicted, whatever the
    # scheduler, the logs or the segmentation directory say.
    #
    # Costs ~90 s over 320 files, which is why it is a subcommand and not part of `status` —
    # `status` gets polled in a loop and has to stay cheap.
    $PY - "$CH" "$M/pred" "$POLY" "$M" <<'AUDITPY'
import csv, glob, os, sys
import fiona
ch, pred, poly, root = sys.argv[1:5]
# ASK WHETHER A TILE IS PREDICTED ANYWHERE, not whether it is in its own chunk's file. A gap
# re-run writes recovered tiles into new chunk files (`p4*.gpkg`), so a per-file comparison
# would keep reporting them missing forever and send the next person round the same loop.
# The union is also the honest question: the national map is the union of these files.
got = set()
for pf in sorted(glob.glob(os.path.join(pred, 'p*.gpkg'))):
    with fiona.open(pf) as src:
        got |= {f['properties']['stub'] for f in src}
print(f"{len(got):,} distinct tiles appear in {len(glob.glob(os.path.join(pred, 'p*.gpkg')))} "
      f"prediction files")
stale, tiles = [], 0
for cf in sorted(glob.glob(os.path.join(ch, 'p*.csv'))):
    b = os.path.basename(cf)[:-4]
    names = [r['stub'] for r in csv.DictReader(open(cf))]
    # A tile whose segmentation is genuinely empty legitimately contributes nothing, so it is
    # not evidence of anything. Only count an absent tile if there ARE polygons on disk for it
    # that the prediction failed to read.
    real = 0
    for n in names:
        if n in got:
            continue
        sp = os.path.join(poly, n + '_filt.gpkg')
        if os.path.exists(sp) and len(fiona.open(sp)) > 0:
            real += 1
    if real:
        stale.append((b, len(names), real))
        tiles += real
print(f"STALE: {len(stale)} chunks omit segmented tiles from their own predictions "
      f"({tiles:,} tiles)")
for b, n, m in sorted(stale, key=lambda r: -r[2])[:10]:
    print(f"  {b}  {m}/{n} tiles absent ({100 * m / n:.1f} %)")
if stale:
    out = os.path.join(root, 'stale_chunks.txt')
    open(out, 'w').write('\n'.join(b for b, _, _ in stale) + '\n')
    print(f"-> {len(stale)} chunk names written to {out}")
AUDITPY
    ;;
repredict)
    # Re-run predict for every chunk whose predictions were written over ground that was not
    # segmented at the time. Their existing GeoPackages are DELETED first, because `predict`
    # skips any chunk with a non-empty output — the same `-s` guard that made these holes
    # permanent would otherwise skip them forever.
    stale=$($PY - "$CH" "$POLY" "$M/pred" <<'PYEOF'
import csv, glob, os, sys
ch, poly, pred = sys.argv[1:4]
seg = {f[:-len('_filt.gpkg')] for f in os.listdir(poly) if f.endswith('_filt.gpkg')}
for cf in sorted(glob.glob(os.path.join(ch, 'p*.csv'))):
    b = os.path.basename(cf)[:-4]
    if not os.path.exists(os.path.join(pred, b + '.gpkg')):
        continue
    names = [r['stub'] for r in csv.DictReader(open(cf))]
    if sum(n in seg for n in names) / len(names) < 0.98:
        print(b)
PYEOF
)
    [ -z "$stale" ] && { echo "no stale predictions — nothing to redo"; exit 0; }
    echo "$stale" | tr '\n' ' '; echo
    echo "deleting $(echo "$stale" | wc -w) stale prediction files"
    for b in $stale; do rm -f "$M/pred/$b.gpkg"; done
    echo "now run '$0 predict' — it will resubmit exactly the deleted chunks"
    ;;
resam)
    # THE GAP `repair-sam` DOESN'T COVER. `repair`/`repair-sam` only re-segment tiles that were
    # missing a COMPOSITE. national2022 exposed a different failure: 38 of the original 40 SAM
    # jobs (8 chunks / ~2,488 tiles each) ran to their full 4 h walltime and were killed mid-chunk
    # — every one logged "Walltime Used: 04:00-04:02" — leaving composites built but never
    # segmented for ~30k tiles that `repair` sees as already done. samgeo_segment.py is idempotent
    # (an AOI whose _filt.gpkg exists is skipped, see its module docstring), so the fix is not to
    # redo the whole `sam` stage but to hand SAM small enough batches that a job actually
    # FINISHES: only tiles with a composite but no segmentation yet, in ${RESAM_TILES:-250}-tile
    # jobs rather than 8-chunk ones. Safe to re-run — it only lists what is still unsegmented.
    mkdir -p $M/resam
    $PY - "$CH" "$POLY" "$M/resam" "${RESAM_TILES:-250}" <<'PYEOF'
import csv, glob, os, sys
ch, poly, out, per = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
comp = {f[:-4] for f in os.listdir(poly)
        if f.endswith('.tif') and not f.endswith('_segment.tif')}
seg = {f[:-len('_filt.gpkg')] for f in os.listdir(poly) if f.endswith('_filt.gpkg')}
rows, hdr = [], None
for cf in sorted(glob.glob(os.path.join(ch, 'p*.csv'))):
    r = csv.DictReader(open(cf))
    for x in r:
        if x['stub'] in comp and x['stub'] not in seg:
            hdr = hdr or list(x.keys()); rows.append(x)
for f in glob.glob(os.path.join(out, 'z*.csv')):
    os.remove(f)
for i in range(0, len(rows), per):
    with open(os.path.join(out, f"z{i // per:04d}.csv"), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=hdr); w.writeheader(); w.writerows(rows[i:i + per])
print(f"{len(rows)} tiles have a composite but no segmentation -> "
      f"{(len(rows) + per - 1) // per} resam jobs")
PYEOF
    rm -f $M/resam/jobs.txt
    # Same per-user queued-job ceiling as every other stage — see the long note in `presegment`.
    MAXQ=${MAXQ:-180}
    inq=$(qstat -u cb8590 2>/dev/null | awk 'NR>5' | wc -l)
    room=$(( MAXQ - inq ))
    echo "queue holds $inq jobs; headroom to MAXQ=$MAXQ is $room"
    i=0
    for f in $M/resam/z*.csv; do
        [ -e "$f" ] || continue
        b=$(basename "$f" .csv)
        if [ $room -le 0 ]; then
            echo "OUT OF HEADROOM at $b — re-run '$0 resam' when the queue drains (idempotent)"
            break
        fi
        # No lane chaining: unlike presegment/predict, SAM never touches the DEA connection
        # pooler (it only reads composite .tif files already on disk), so there is nothing here
        # for chaining to protect — PBS's own scheduler manages gpuvolta concurrency.
        JID=$(qsub -l walltime=02:00:00 -v AOIS="$f",OUTDIR=$POLY -N rsm_$b sam_segment.pbs)
        echo "$b ${JID%%.*}" >> $M/resam/jobs.txt
        i=$((i + 1)); room=$((room - 1))
    done
    echo "submitted $i resam jobs of up to ${RESAM_TILES:-250} tiles each"
    ;;
merge)
    # Refuse to build a national map out of a run with known holes. A merge is the last point
    # at which the gap is still attributable to a chunk; afterwards it is just missing ground.
    inc=$($PY - "$CH" "$POLY" <<'PYEOF'
import csv, glob, os, sys
ch, poly = sys.argv[1], sys.argv[2]
seg = {f[:-len('_filt.gpkg')] for f in os.listdir(poly) if f.endswith('_filt.gpkg')}
n = 0
for cf in sorted(glob.glob(os.path.join(ch, 'p*.csv'))):
    names = [r['stub'] for r in csv.DictReader(open(cf))]
    if sum(x in seg for x in names) / len(names) < 0.98:
        n += 1
print(n)
PYEOF
)
    if [ "$inc" -gt 0 ] && [ -z "${FORCE_MERGE:-}" ]; then
        echo "REFUSING: $inc chunks are below 98 % segmented. Run '$0 repair' first," >&2
        echo "or set FORCE_MERGE=1 to merge a map with known holes." >&2
        exit 1
    fi
    qsub -v M=$M,YEAR=$YEAR merge_national.pbs
    ;;
boundary)
    # Post-hoc cross-tile de-duplication of the merged national file. Adjacent tiles' rasters
    # overlap by ~350 m (each is the EPSG:6933 bbox of a rotated 3 km Albers square), so every
    # paddock in that band is in the merged file twice, sometimes with two classes, and views
    # are cut 2 px inside their own raster. merge_tile_boundaries.py resolves ownership by the
    # lattice square, unions the two views of one paddock, reconciles classes, clips residual
    # slivers to the owning tile and writes a raster_cut_m quality column. One small CPU job.
    # Never edits the input; output is national_${YEAR}_crops_merged.gpkg. Rule set, thresholds
    # and the Riverina evidence: output/TILE_BOUNDARY_MERGE.md.
    IN=$M/national_${YEAR}_crops.gpkg
    [ -f "$IN" ] || { echo "no merged file at $IN — run '$0 merge' first" >&2; exit 1; }
    qsub -v M=$M,YEAR=$YEAR boundary_national.pbs
    ;;
summary)
    # Per-category polygon count and area, for comparing one year against another (and against
    # NATIONAL_2024_RUN.md's original numbers, which predate --yield-model and the two-pass
    # gate). Reads the merged file so it needs `merge` to have finished first — ogrinfo's own SQL
    # engine does the aggregation, the same reason merge_national.pbs uses ogr2ogr rather than
    # pulling everything through geopandas.
    OUT=$M/national_${YEAR}_crops.gpkg
    [ -f "$OUT" ] || { echo "no merged file at $OUT — run '$0 merge' first" >&2; exit 1; }
    module load gdal/3.7.3
    echo "== $YEAR: polygon count and area by category =="
    # abstain_reason, not pred, is authoritative for "did this actually pass the gates" --
    # since 2026-09-07 a class in --shape-gate-skip-classes can carry a non-null `pred` AND a
    # non-empty abstain_reason at the same time (the class label is kept, but the shape-gate
    # failure is still recorded so it stays filterable). COALESCE(pred, ...) would have grouped
    # those rows under their class name instead of "abstain: no_crop_shape", silently hiding
    # exactly the gate-failed polygons this report exists to surface.
    ogrinfo -q -dialect sqlite -sql \
      "SELECT CASE WHEN abstain_reason IS NOT NULL AND abstain_reason != '' \
                   THEN 'abstain: ' || abstain_reason ELSE pred END AS category, \
              COUNT(*) AS n, ROUND(SUM(area_ha)) AS ha \
       FROM crops GROUP BY category ORDER BY ha DESC" "$OUT"
    echo
    echo "== touches_grid (candidate tile-boundary cuts) =="
    ogrinfo -q -dialect sqlite -sql \
      "SELECT touches_grid, COUNT(*) AS n, ROUND(SUM(area_ha)) AS ha \
       FROM crops GROUP BY touches_grid" "$OUT"
    if ogrinfo -q -so "$OUT" crops | grep -q yield_tha_calibrated; then
        echo
        echo "== cereal yield (calibrated t/ha) =="
        ogrinfo -q -dialect sqlite -sql \
          "SELECT COUNT(*) AS n_scored, ROUND(AVG(yield_tha_calibrated),2) AS mean_tha, \
                  ROUND(SUM(area_ha)) AS ha_scored \
           FROM crops WHERE yield_tha_calibrated IS NOT NULL" "$OUT"
    fi
    ;;
cost)
    grep -h "Service Units" /scratch/xe2/cb8590/paddock-species-logs/*.OU 2>/dev/null \
      | awk '{s+=$3} END {printf "all logs: %.1f SU\n", s}'
    ;;
*)
    echo "usage: $0 {grid|chunks|presegment|sam|predict|status|repair|repair-check|repair-sam|resam|repredict|merge|summary|cost}" >&2
    exit 2 ;;
esac
