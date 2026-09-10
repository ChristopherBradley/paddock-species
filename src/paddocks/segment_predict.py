#!/usr/bin/env python
"""
segment_predict.py -- SAM on the GPU and predict_tile.py on the same node's spare cores.

A gpuvolta job bills 12 cores and SAM uses one. This runs `samgeo_segment.py segment` over the
job's AOI list and, as each tile's `<stub>_filt.gpkg` appears, hands it to one of --workers
predict processes (predict_tile.py on a small batch of tiles, so its model load and datacube
connection are amortised). At 9 km a tile's SAM wall time (~10.6 s) exceeds its predict time
spread over 11 workers (~8.5 s), so predict rides along at no extra SU
(output/FUSED_PREDICT_BENCHMARK.md); at 3 km it would not, so this is for the 9 km pipeline.

Resumable: tiles listed in <pred-dir>/done_stubs.txt are skipped; the SAM stage skips tiles
that already have a _filt.gpkg. Predictions land as <pred-dir>/p_<batch>.gpkg (+ .zarr), which
merge_national.pbs picks up with its p*.gpkg glob.
"""
import argparse
import csv
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# One BLAS/OpenMP thread per predict worker: each worker is one core by design, and a numpy
# process otherwise spawns a thread per node core (48 on gpuvolta). With 11 workers that
# oversubscription made the CPU-bound zonal step 30x slower on one node (job 178523837:
# 482 s/tile vs 16 s/tile for the same code on another node) and the job hit its walltime.
WORKER_ENV = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1",
                  NUMPY_MADVISE_HUGEPAGE="0")   # THP compaction stalls, see sampredict.pbs


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--aois", required=True)
    ap.add_argument("--outdir", required=True, help="composites in, masks/polygons out (the samgeo dir)")
    ap.add_argument("--pred-dir", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--workers", type=int, default=11)
    ap.add_argument("--batch", type=int, default=4, help="tiles per predict_tile.py call")
    ap.add_argument("--sam-args", default="", help="extra args for samgeo_segment.py segment")
    ap.add_argument("--predict-args", default="", help="extra args for predict_tile.py")
    ap.add_argument("--poll", type=float, default=5.0)
    ap.add_argument("--no-sam", action="store_true", help="only predict tiles whose polygons exist")
    a = ap.parse_args()
    os.makedirs(a.pred_dir, exist_ok=True)
    py = sys.executable
    with open(a.aois) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    stubs = [r["stub"] for r in rows]
    done_path = f"{a.pred_dir}/done_stubs.txt"
    done = set(open(done_path).read().split()) if os.path.exists(done_path) else set()
    pending = [s for s in stubs if s not in done]
    log(f"{len(stubs)} tiles, {len(done)} already predicted, {len(pending)} to do; workers={a.workers}, batch={a.batch}")

    sam = None
    if not a.no_sam:
        sam = subprocess.Popen([py, f"{HERE}/samgeo_segment.py", "segment", "--aois", a.aois, "--outdir", a.outdir] + a.sam_args.split(),
                               stdout=open(f"{a.pred_dir}/sam.log", "a"), stderr=subprocess.STDOUT)
        log(f"SAM started (pid {sam.pid})")

    def filt_ready(s):
        p = f"{a.outdir}/{s}_filt.gpkg"
        return os.path.exists(p) and (time.time() - os.path.getmtime(p)) > 2.0     # settled on disk

    row_by_stub = {r["stub"]: r for r in rows}
    running = {}            # popen -> (batch_id, stubs)
    batch_id = int(time.time()) % 100000
    dispatched = set()
    failed = []
    n_pred = 0
    t0 = time.time()

    def launch(batch):
        nonlocal batch_id
        batch_id += 1
        bfile = f"{a.pred_dir}/batch_{batch_id}.csv"
        with open(bfile, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for s in batch:
                w.writerow(row_by_stub[s])
        cmd = [py, f"{HERE}/predict_tile.py", "--aois", bfile, "--polydir", a.outdir, "--model", a.model,
               "--out", f"{a.pred_dir}/p_{batch_id}.gpkg", "--timings", f"{a.pred_dir}/timings_predict.csv",
               "--zarr-out", f"{a.pred_dir}/p_{batch_id}.zarr"] + a.predict_args.split()
        p = subprocess.Popen(cmd, stdout=open(f"{a.pred_dir}/p_{batch_id}.log", "w"), stderr=subprocess.STDOUT, env=WORKER_ENV)
        running[p] = (batch_id, list(batch))
        log(f"predict batch {batch_id}: {len(batch)} tiles ({len(running)} workers busy)")

    def reap():
        nonlocal n_pred
        for p in list(running):
            rc = p.poll()
            if rc is None:
                continue
            bid, bst = running.pop(p)
            if rc == 0:
                with open(done_path, "a") as f:
                    f.write("\n".join(bst) + "\n")
                n_pred += len(bst)
            else:
                failed.append((bid, bst, rc))
                log(f"predict batch {bid} FAILED rc={rc} ({len(bst)} tiles) -- see p_{bid}.log")

    while True:
        reap()
        sam_alive = sam is not None and sam.poll() is None
        ready = [s for s in pending if s not in dispatched and filt_ready(s)]
        # dispatch full batches while SAM is producing; flush partial batches once SAM is done
        while ready and len(running) < a.workers and (len(ready) >= a.batch or not sam_alive):
            batch, ready = ready[:a.batch], ready[a.batch:]
            dispatched.update(batch)
            launch(batch)
        if not sam_alive and not running and not ready:
            # nothing running, nothing ready: any pending tile without polygons is a SAM failure
            missing = [s for s in pending if s not in dispatched]
            if missing:
                log(f"{len(missing)} tiles never got polygons (SAM failed or composite missing): {missing[:5]}...")
            break
        time.sleep(a.poll)
    sam_rc = sam.returncode if sam is not None else 0
    dt = time.time() - t0
    log(f"done in {dt:.0f} s: SAM rc={sam_rc}, {n_pred} tiles predicted, {len(failed)} failed batches, "
        f"{dt / max(n_pred, 1):.1f} s wall per predicted tile")
    sys.exit(1 if (sam_rc or failed) else 0)


if __name__ == "__main__":
    main()
