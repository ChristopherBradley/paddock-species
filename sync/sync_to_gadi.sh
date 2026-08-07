#!/bin/bash
# ---------------------------------------------------------------------------
# Re-runnable sync between this local repo and NCI gadi.
#
#   ./sync/sync_to_gadi.sh code     # repo code/docs  -> gadi /home  (small)
#   ./sync/sync_to_gadi.sh data     # local data/     -> gadi /g/data + /scratch (via data-mover)
#   ./sync/sync_to_gadi.sh skills    # ~/.claude/skills -> gadi ~/.claude/skills
#   ./sync/sync_to_gadi.sh all      # code + data + skills
#   ./sync/sync_to_gadi.sh pull     # gadi derived outputs -> local data/derived  (pull back)
#
# Mapping (single source of truth for the home/gdata/scratch split):
#   repo root (minus data/, Papers/, extra papers/)  <->  /home/147/cb8590/Projects/paddock-species
#   data/raw/                                         <->  /g/data/xe2/cb8590/paddock-species-data/raw
#   data/derived/                                     <->  /scratch/xe2/cb8590/paddock-species-data/derived
#   ~/.claude/skills                                  <->  ~/.claude/skills
#
# WHY THE SPLIT: raw inputs are irreplaceable, so they sit on /g/data (persistent, backed up).
# Everything under derived/ is regenerable by rerunning the pipeline, so it sits on /scratch
# — larger and faster, but NCI PURGES files untouched for ~100 days and does not back it up.
# Treat scratch as a workspace, not storage: `pull` anything you want to keep.
#
# rsync is incremental: safe to run repeatedly. Add --dry-run via DRYRUN=1.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
USER_REMOTE=cb8590
LOGIN=gadi.nci.org.au           # login node — code/skills (small)
DM=gadi-dm.nci.org.au           # data-mover node — bulk data (NCI policy)
HOME_DST=/home/147/cb8590/Projects/paddock-species
GDATA_DST=/g/data/xe2/cb8590/paddock-species-data          # raw only (persistent)
SCRATCH_DST=/scratch/xe2/cb8590/paddock-species-data       # derived only (purged ~100 days)
SKILLS_SRC="$HOME/.claude/skills/"
SKILLS_DST=/home/147/cb8590/.claude/skills

RSYNC=(rsync -avz --human-readable)
[ "${DRYRUN:-0}" = "1" ] && RSYNC+=(--dry-run)

CODE_EXCLUDES=(
  --exclude 'data/' --exclude 'Papers/' --exclude 'extra papers/'
  --exclude '.git/' --exclude '__pycache__/' --exclude '*.pyc'
  --exclude '.DS_Store' --exclude '.ipynb_checkpoints/'
  --exclude 'data/derived/'   # sensitive; travels with `data`, never to /home
)

sync_code() {
  echo ">> code  ->  ${LOGIN}:${HOME_DST}"
  ssh "${USER_REMOTE}@${LOGIN}" "mkdir -p '${HOME_DST}'"
  "${RSYNC[@]}" "${CODE_EXCLUDES[@]}" "${REPO}/" "${USER_REMOTE}@${LOGIN}:${HOME_DST}/"
}

sync_data() {
  echo ">> raw     ->  ${DM}:${GDATA_DST}/raw       (via data-mover)"
  ssh "${USER_REMOTE}@${LOGIN}" "mkdir -p '${GDATA_DST}/raw' '${SCRATCH_DST}/derived'"
  if [ -d "${REPO}/data/raw" ]; then
    "${RSYNC[@]}" "${REPO}/data/raw/" "${USER_REMOTE}@${DM}:${GDATA_DST}/raw/"
  else
    echo "   (no local data/raw — skipped)"
  fi
  # derived/ normally flows gadi -> local (it is generated on gadi), but Stage-1 outputs such
  # as nvt_trials_labeled.csv are produced locally and are inputs to Stage 2, so push too.
  echo ">> derived ->  ${DM}:${SCRATCH_DST}/derived (via data-mover)"
  if [ -d "${REPO}/data/derived" ]; then
    "${RSYNC[@]}" "${REPO}/data/derived/" "${USER_REMOTE}@${DM}:${SCRATCH_DST}/derived/"
  else
    echo "   (no local data/derived — skipped)"
  fi
}

sync_skills() {
  echo ">> skills ->  ${LOGIN}:${SKILLS_DST}"
  ssh "${USER_REMOTE}@${LOGIN}" "mkdir -p '${SKILLS_DST}'"
  "${RSYNC[@]}" --exclude '__pycache__/' "${SKILLS_SRC}" "${USER_REMOTE}@${LOGIN}:${SKILLS_DST}/"
}

pull_outputs() {
  echo "<< pull ${DM}:${SCRATCH_DST}/derived  ->  ${REPO}/data/derived"
  mkdir -p "${REPO}/data/derived"
  "${RSYNC[@]}" "${USER_REMOTE}@${DM}:${SCRATCH_DST}/derived/" "${REPO}/data/derived/"
}

case "${1:-}" in
  code)   sync_code ;;
  data)   sync_data ;;
  skills) sync_skills ;;
  all)    sync_code; sync_data; sync_skills ;;
  pull)   pull_outputs ;;
  *) echo "usage: $0 {code|data|skills|all|pull}   (DRYRUN=1 to preview)"; exit 1 ;;
esac
echo "done."
