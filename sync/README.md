# Local ⇄ gadi sync

`sync_to_gadi.sh` is the single source of truth for **what goes where**. The repo is
structured so the split is mechanical:

| local | → gadi | contents |
|---|---|---|
| repo root **minus** `data/`, `Papers/`, `extra papers/` | `/home/147/cb8590/Projects/paddock-species` | code, docs, `output/`, `configs/`, `memory/` (tiny — `/home` has a 10 GB quota) |
| `data/raw/` | `/g/data/xe2/cb8590/paddock-species-data/raw` | NLUM tiffs, NVT xlsx (persistent, backed up) |
| `data/derived/` | `/scratch/xe2/cb8590/paddock-species-data/derived` | chunks, time series, verdicts, figures — regenerable, **purged after ~100 days** |
| `~/.claude/skills` | `~/.claude/skills` | NORA skills |
| `Papers/`, `extra papers/` | *(local only)* | reading PDFs; not needed for compute |
| *(transient)* | `/scratch/xe2/cb8590/paddock-species-logs` | PBS job logs |

## Usage
```bash
./sync/sync_to_gadi.sh all      # push everything
./sync/sync_to_gadi.sh code     # just code -> /home (after local edits)
./sync/sync_to_gadi.sh data     # just data -> /g/data (raw) + /scratch (derived)
./sync/sync_to_gadi.sh skills   # just ~/.claude/skills
./sync/sync_to_gadi.sh pull     # bring gadi results in data/derived back to local
DRYRUN=1 ./sync/sync_to_gadi.sh all   # preview, transfer nothing
```

**Typical loop:** edit locally → `code` to push → run on gadi → `pull` to bring results back.
Run `pull` before you stop caring about a result: `derived/` lives on `/scratch`, which NCI
purges after ~100 days.

Bulk `data` transfers route through the **data-mover node** `gadi-dm.nci.org.au` (NCI policy);
code/skills go via the login node. Auth is the passwordless `~/.ssh/id_rsa` key already set up
for `Host gadi`.

> **NDA:** `data/` and everything under it is GRDC/NVT trial data under a signed NDA. It is
> gitignored and only ever lives in your private `/g/data/xe2/cb8590` and
> `/scratch/xe2/cb8590` (mode 700) on gadi.
