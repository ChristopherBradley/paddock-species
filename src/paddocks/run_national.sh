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
#   ./run_national.sh sampredict   # 9 km pipeline: SAM + predict in one GPU job per 8 chunks
#                                 #   (instead of sam + predict; predict rides on the spare cores)
#   ./run_national.sh status
#   ./run_national.sh merge        # one national GeoPackage (refuses if chunks are incomplete)
#   ./run_national.sh boundary     # de-duplicate the ~350 m tile-overlap band in the merged file
#                                 #   -> national_${YEAR}_crops_merged.gpkg (TILE_BOUNDARY_MERGE.md)
#   ./run_national.sh overlaps     # merge polygons that still overlap -> national_${YEAR}_crops_final.gpkg
#   ./run_national.sh classified   # _final_classified (every predicted class) and _final_good (strict mask)
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
M=${M:-$D/national$YEAR}   # override for a second tiling of the same year, e.g. M=$D/national2024_9km
AOIS=$M/aois.csv
POLY=$M/samgeo
CH=$M/chunks
NCHUNK=${NCHUNK:-320}
# Extra flags for every SAM job (sampredict), output/BENCH_KSU.md 2026-09-09:
#   --prompt-image-only  drops the SAM prompt points that fall on samgeo's zero padding around
#                        each composite: 2.5x less GPU time per tile, polygons IDENTICAL to the
#                        2022-2024 production runs (2,467/2,467 at IoU >= 0.9). Default.
#   --fp16               a further 1.5x, 99.6 % identical polygons. Opt in per year and record it.
# SAM_EXTRA="" reproduces the exact 2022-2024 code path.
SAM_EXTRA=${SAM_EXTRA---prompt-image-only}
# Composite raster CRS. Empty reproduces the 2022-2024 runs (EPSG:6933: the raster is the rotated
# lattice square's bounding box, ~350 m of accidental overlap). The 9 km pipeline uses EPSG:3577
# so segmentation and prediction share one grid, with the overlap put into aois half_m instead
# (grid9_from_2024.py --half-m 4850). TILE_GEOMETRY_DECISION.md / VALIDATION_9KM.md.
PRESEG_EXTRA=${PRESEG_EXTRA-}
# Predict model + gates, used by `sampredict`.
MODEL=${MODEL:-$D/models/group3_map_sharma6.joblib}
# PREDICT_EXTRA appends to every predict invocation. The multi-year 9 km run passes --no-zarr
# through it: the per-batch .zarr time-series store is ~124 files per batch, ~346,000 files per
# national year, and the xe2 scratch INODE quota (not its terabytes) had only ~749,000 free when
# the eight-year run was planned -- so keeping the zarrs would have run the project out of inodes
# during the second year. The .gpkg predictions are unaffected; a zarr can be rebuilt for any year
# by re-running predict over that year's composites, which are kept.
PREDICT_EXTRA=${PREDICT_EXTRA:-}
PREDICT_ARGS="--max-area-ha 300 --crop-gate-amp 0.35 --crop-gate-shape $D/models/phenology_gate.joblib --shape-gate-skip-classes Canola Cereal Legume --yield-model $D/models/cereal_yield.joblib $PREDICT_EXTRA"
PER_SAM=${PER_SAM:-8}          # presegment chunks per SAM job -> 40 GPU jobs
LANES=${LANES:-64}             # max presegment/predict jobs running at once (datacube pooler)
# JOBPFX: prefix for every PBS job name this run submits, AND for the live-job guards that read
# those names back out of qstat. Empty reproduces the single-year behaviour exactly. It exists
# because the multi-year 9 km orchestrator runs several years at once and the guards below match
# job names, not directories: without a prefix, year A's live `ps_p000` makes year B believe its
# own p000 is already in flight, so B's chunk is skipped on every pass and quietly never runs.
# Keep it short -- PBS truncates job names at 15 characters (e.g. JOBPFX=y23_ -> y23_ps_p000).
JOBPFX=${JOBPFX:-}

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
# Only the year-dependent columns move. stub embeds the base year once, right after the grid
# prefix: nlum_<year>_r..._c... at 3 km and nlum9_<year>_r..._c... at 9 km. Anchor the rewrite to
# that prefix rather than doing a blind global year-string replace, so a coincidental "2024"
# inside lat/lon (there is none at 6dp here, but never rely on that) can never be touched.
#
# THE PREFIX IS NOT ALWAYS "nlum_". It was, until the 9 km grid arrived calling its tiles
# nlum9_2024_r63_c371: a literal f"nlum_{before}_" matches nothing in those, so `grid` silently
# copied 2024's stubs verbatim into every other year and each year's polygons would have carried
# a stub naming the wrong year. Match the prefix as a group instead and assert every row moved.
pat = rf"^(nlum\d*)_{before}_"
moved = A["stub"].str.match(rf"nlum\d*_{before}_")
if not moved.all():
    raise SystemExit(f"grid: {(~moved).sum()} of {len(A)} stubs do not start with nlum*_{before}_ "
                     f"(first: {A.loc[~moved, 'stub'].iat[0]}) — refusing to relabel blind")
A["stub"] = A["stub"].str.replace(pat, rf"\1_{year}_", regex=True)
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
        grep -qx "${JOBPFX}ps_$b" "$LIVE_NAMES" && { skipped=$((skipped + 1)); continue; }
        if [ $room -le 0 ]; then
            echo "STOPPING at $b — $(ls $CH/p*.csv | wc -l) chunks wanted, $i submitted."
            echo "Re-run '$0 presegment' when the queue drains; it resumes where this left off."
            break
        fi
        lane=$((i % LANES))
        DEP=""
        [ -n "${PREV[$lane]:-}" ] && DEP="-W depend=afterany:${PREV[$lane]}"
        # PS_MEM / PS_WALLTIME: 3 km chunks fit 4 GB / 3 h; 9 km chunks (NCHUNK=60, ~266 tiles at
        # ~77 s each, PILOT_9KM_COST.md) need PS_WALLTIME=10:00:00 (billed on use, not request).
        JID=$(qsub $DEP -l mem=${PS_MEM:-4GB} -l walltime=${PS_WALLTIME:-03:00:00} \
                   -v "AOIS=$f,OUTDIR=$POLY,PRESEG_EXTRA=$PRESEG_EXTRA" -N ${JOBPFX}ps_$b presegment.pbs)
        PREV[$lane]=${JID%%.*}
        echo "$b ${JID%%.*}" >> $M/chunkjobs.txt
        i=$((i + 1)); room=$((room - 1))
    done
    echo "submitted $i presegment jobs across $LANES lanes ($skipped chunks already done)"
    ;;
sampredict)
    # SAM + predict in ONE GPU job per group of chunks (segment_predict.py): SAM on the GPU,
    # predict_tile.py on the 11 spare cores as each tile's polygons land. Replaces `sam` and
    # `predict` for the 9 km pipeline, where a tile's SAM wall time exceeds its predict time
    # spread over 11 workers, so predict costs no extra SU (FUSED_PREDICT_BENCHMARK.md). At 3 km
    # it would be predict-bound: use `sam` + `predict` there. Predictions land in $M/pred/sp<k>/
    # as p_<batch>.gpkg (+ .zarr); `merge` symlinks them where merge_national.pbs's p*.gpkg glob
    # looks.
    #
    # RE-RUNNABLE, LIKE `presegment` AND `predict`: a group is skipped when every tile of it is
    # in its done_stubs.txt (predicted), or when an sp_s<k> job is live. Otherwise it is
    # (re)submitted -- segment_predict.py skips predicted tiles and SAM skips segmented ones, so a
    # walltime-killed group resumes at no extra cost. Same MAXQ ceiling as the other stages.
    #
    # SP_NODEP=1: submit a group only when EVERY composite it needs already exists, with NO PBS
    # dependency. This is how a polling launcher drives the stage: dependent jobs on gadi can be
    # destroyed the instant their dependency is met (the long note in `presegment`), and a
    # launcher that re-runs this every few minutes needs no dependency at all. Without SP_NODEP
    # the group is chained (afterany) to its chunks' presegment jobs from chunkjobs.txt, as before.
    mkdir -p $M/sam $M/pred
    MAXQ=${MAXQ:-180}
    inq=$(qstat -u cb8590 2>/dev/null | awk 'NR>5' | wc -l)
    room=$(( MAXQ - inq ))
    LIVE_NAMES=$(mktemp); qstat -u cb8590 -w 2>/dev/null | awk 'NR>5 {print $4}' > "$LIVE_NAMES"
    trap 'rm -f "$LIVE_NAMES"' EXIT
    n=$(ls $CH/p*.csv | wc -l)
    i=0; k=0; nsub=0; ndone=0; nlive=0; nwait=0
    while [ $i -lt $n ]; do
        part=$(seq -f "p%03g" $i $((i + PER_SAM - 1)) | head -$PER_SAM)
        $PY - "$CH" "$M/sam/s$k.csv" $part <<'PYEOF'
import sys, os, pandas as pd
ch, out = sys.argv[1], sys.argv[2]
fs = [os.path.join(ch, f"{b}.csv") for b in sys.argv[3:]]
fs = [f for f in fs if os.path.exists(f)]
pd.concat([pd.read_csv(f) for f in fs], ignore_index=True).to_csv(out, index=False)
PYEOF
        mkdir -p $M/pred/sp$k
        # state of this group: tiles left to predict, composites still missing
        read -r left missing <<< "$($PY - "$M/sam/s$k.csv" "$M/pred/sp$k/done_stubs.txt" "$POLY" <<'PYEOF'
import sys, os, pandas as pd
aois, done_p, poly = sys.argv[1:4]
stubs = pd.read_csv(aois).stub.tolist()
done = set(open(done_p).read().split()) if os.path.exists(done_p) else set()
print(sum(s not in done for s in stubs), sum(not os.path.exists(f"{poly}/{s}.tif") for s in stubs))
PYEOF
)"
        if [ "$left" -eq 0 ]; then ndone=$((ndone + 1)); i=$((i + PER_SAM)); k=$((k + 1)); continue; fi
        if grep -qx "${JOBPFX}sp_s$k" "$LIVE_NAMES"; then nlive=$((nlive + 1)); i=$((i + PER_SAM)); k=$((k + 1)); continue; fi
        if [ -n "${SP_NODEP:-}" ]; then
            if [ "$missing" -gt 0 ]; then nwait=$((nwait + 1)); i=$((i + PER_SAM)); k=$((k + 1)); continue; fi
            DEP=""
        else
            IDS=$(for b in $part; do awk -v b="$b" '$1==b {print $2}' $M/chunkjobs.txt 2>/dev/null; done \
                  | tr '\n' ':' | sed 's/:$//')
            [ -n "$IDS" ] && DEP="-W depend=afterany:$IDS" || DEP=""
        fi
        if [ $room -le 0 ]; then
            echo "STOPPING at sp_s$k -- queue at MAXQ=$MAXQ; re-run '$0 sampredict' when it drains (skips done and live groups)"
            break
        fi
        JID=$(qsub $DEP -l walltime=${SP_WALLTIME:-06:00:00} \
              -v "AOIS=$M/sam/s$k.csv,OUTDIR=$POLY,PREDDIR=$M/pred/sp$k,MODEL=$MODEL,WORKERS=${WORKERS:-11},SAM_EXTRA=$SAM_EXTRA,EXTRA_ARGS=$PREDICT_ARGS" \
              -N ${JOBPFX}sp_s$k sampredict.pbs)
        for b in $part; do echo "$b ${JID%%.*}" >> $M/sam/jobmap.txt; done
        echo "sp_s$k ${JID%%.*} $(date +%FT%T) left=$left" >> $M/sam/spjobs.txt
        nsub=$((nsub + 1)); room=$((room - 1))
        i=$((i + PER_SAM)); k=$((k + 1))
    done
    echo "sampredict: $nsub submitted, $ndone groups done, $nlive live, $nwait waiting for composites (of $k groups, PER_SAM=$PER_SAM)"
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
    JOBS='ps_p|sam_s|sp_s|pr_p|rp_r|rs_s|rsm_z'
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
        echo "REFUSING: $inc chunks are below 98 % segmented. Re-run '$0 presegment' then '$0 sampredict' (both resume)," >&2
        echo "or set FORCE_MERGE=1 to merge a map with known holes." >&2
        exit 1
    fi
    # sampredict writes $M/pred/sp<k>/p_<batch>.gpkg. Expose them to the p*.gpkg glob that
    # merge_national.pbs and abs_national.pbs both use. The link name MUST start with "p":
    # sp<k>_p_<batch>.gpkg matched nothing and the 2024 9 km merge merged 0 chunks (2026-09-10).
    for f in $M/pred/sp*/p_*.gpkg; do
        [ -f "$f" ] || continue
        b=$(basename "$f" .gpkg); ln -sf "$f" "$M/pred/p_$(basename "$(dirname "$f")")_${b#p_}.gpkg"
    done
    qsub -N ${JOBPFX}merge_nat -v M=$M,YEAR=$YEAR merge_national.pbs
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
    qsub -N ${JOBPFX}boundary_n -v M=$M,YEAR=$YEAR boundary_national.pbs
    ;;
overlaps)
    # Merge every polygon group that still overlaps after `boundary` (merge_overlaps.py): a chain of
    # overlaps becomes one polygon with the attributes (crop type, yield, ...) of its largest member.
    # User decision 2026-09-11, after 165,081 pairs (2.75 M ha, nearly all one paddock seen by two
    # tiles) survived `boundary` on the 2024 9 km map. A merged polygon over 300 ha is then abstained as
    # unsegmented_blob, as predict_tile.py does for a single one. -> national_${YEAR}_crops_final.gpkg
    IN=$M/national_${YEAR}_crops_merged.gpkg
    [ -f "$IN" ] || { echo "no boundary-merged file at $IN - run '$0 boundary' first" >&2; exit 1; }
    qsub -N ${JOBPFX}overlaps_n -v M=$M,YEAR=$YEAR overlaps_national.pbs
    ;;
classified)
    # Two products from the final (overlap-merged) file, both with `pred` renamed `predicted_crop_type` and
    # the QGIS style of the 2024 release copied in so they open coloured.
    #   _classified.gpkg  every polygon with a predicted class, the equivalent of the retired 3 km
    #                     release (650,766 of 1,346,582). It includes polygons that failed the
    #                     phenology-shape check: the run predicts every class regardless
    #                     (--shape-gate-skip-classes Canola Cereal Legume) and records the failure as
    #                     abstain_reason = no_crop_shape, so it can be masked later (PROJ_NOTES
    #                     2026-09-07 (2a)).
    #   _good.gpkg        the strict mask: a predicted class AND every gate passed (abstain_reason empty).
    # raster_cut_m and class_conflict stay as columns for a further, optional mask.
    IN=$M/national_${YEAR}_crops_final.gpkg
    STYLE=${STYLE:-$D/national2024/national_2024_crops_classified.gpkg}
    OGR=/apps/gdal/3.7.3/bin
    [ -s "$IN" ] || { echo "no final file at $IN - run '$0 overlaps' first" >&2; exit 1; }
    for kind in classified good; do
        OUTC=$M/national_${YEAR}_crops_final_${kind}.gpkg
        if [ "$kind" = classified ]; then W="pred IS NOT NULL AND pred <> ''"; else W="abstain_reason = '' OR abstain_reason IS NULL"; fi
        rm -f "$OUTC"
        $OGR/ogr2ogr -f GPKG "$OUTC" "$IN" crops -nln crops -where "$W"
        $PY - "$OUTC" <<'PYEOF'
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
c.execute("ALTER TABLE crops RENAME COLUMN pred TO predicted_crop_type")
c.commit()
print(f"{sys.argv[1].rsplit('/', 1)[1]}: {c.execute('SELECT COUNT(*) FROM crops').fetchone()[0]:,} polygons")
PYEOF
        if [ -s "$STYLE" ]; then $OGR/ogr2ogr -update -append "$OUTC" "$STYLE" layer_styles; else echo "no style source at $STYLE; left unstyled"; fi
    done
    ls -la $M/national_${YEAR}_crops_final_classified.gpkg $M/national_${YEAR}_crops_final_good.gpkg
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
