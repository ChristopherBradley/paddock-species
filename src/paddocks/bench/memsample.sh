#!/bin/bash
# memsample.sh PID INTERVAL LOG -- append "epoch rss_gb cgroup_gb" for PID's tree every INTERVAL s.
# Gadi bills memory as cores and its epilogue "Memory Used" is RSS + page cache pinned at the
# request, so only RSS says what the job needs (shelterbelts GADI_MEMORY_QUEUE_COSTS.md sec 2).
PID=$1; INT=${2:-30}; LOG=$3
CG=""
for line in $(cat /proc/self/cgroup 2>/dev/null); do
  case "$line" in *memory*) CG=/sys/fs/cgroup/memory${line##*:};; esac
done
while kill -0 "$PID" 2>/dev/null; do
  rss=$(ps -o rss= --ppid "$PID" -p "$PID" 2>/dev/null | awk '{s+=$1} END {printf "%.2f", s/1048576}')
  cg="nan"; [ -n "$CG" ] && [ -r "$CG/memory.usage_in_bytes" ] && cg=$(awk '{printf "%.2f", $1/1073741824}' "$CG/memory.usage_in_bytes")
  echo "$(date +%s) $rss $cg" >> "$LOG"
  sleep "$INT"
done
