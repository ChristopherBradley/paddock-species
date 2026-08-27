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
./sync/sync_to_gadi.sh pull-figures
./sync/sync_to_gadi.sh pull-code   # bring gadi /home code/docs back to local (reverse of `code`)
DRYRUN=1 ./sync/sync_to_gadi.sh all   # preview, transfer nothing
PULL_DELETE=1 ./sync/sync_to_gadi.sh pull-code   # also remove local files gadi no longer has
```

**Typical loop:** edit locally → `code` to push → run on gadi → `pull` to bring results back.
Run `pull` before you stop caring about a result: `derived/` lives on `/scratch`, which NCI
purges after ~100 days.

**If you've been editing on gadi instead:** run `pull-code` to bring those edits back to local.
It's a plain rsync (excludes `.git/`), so your local git history is untouched — review with
`git status`/`git diff` and commit as usual. It overwrites local files that also exist on gadi
but, by default, leaves local-only files alone; pass `PULL_DELETE=1` if you want an exact
mirror of gadi instead (this **deletes** local files gadi doesn't have — check `git status`
first so nothing uncommitted gets lost).

> **This cuts both ways:** `pull-code` overwrites local files with whatever gadi has —
> including `sync_to_gadi.sh` itself. If you edit this script locally, run `code` to push
> those edits to gadi before your next `pull-code`, or the pull will revert the script.

Bulk `data` transfers route through the **data-mover node** `gadi-dm.nci.org.au` (NCI policy);
code/skills go via the login node. Auth is the passwordless `~/.ssh/id_rsa` key already set up
for `Host gadi`.

> **NDA:** `data/` and everything under it is GRDC/NVT trial data under a signed NDA. It is
> gitignored and only ever lives in your private `/g/data/xe2/cb8590` and
> `/scratch/xe2/cb8590` (mode 700) on gadi.
