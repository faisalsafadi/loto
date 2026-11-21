#!/usr/bin/env python
"""M4 — lance le banc d'essai (configuration figée dans bench_config.py).

  python scripts/m4_run_benchmark.py --smoke      # essai rapide, n'écrit rien
  python scripts/m4_run_benchmark.py              # lancement officiel (long), écrit rapport, CSV, base
"""
import argparse
import csv
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from loto_research.simulation import bench as b
from loto_research.simulation import bench_config as cfg


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/loto.sqlite")
    ap.add_argument("--cache-dir", default="data/simulations")
    ap.add_argument("--report", default="reports/BENCHMARK_M4.md")
    ap.add_argument("--csv", default="reports/bench_m4_results.csv")
    ap.add_argument("--smoke", action="store_true", help="essai réduit, rien n'est écrit")
    ap.add_argument("--rerun", action="store_true", help="autorise un nouveau lancement officiel")
    args = ap.parse_args()

    if args.smoke:
        sizes, n_sim, reps_null, reps_bias, cache = (200,), 2000, 100, 30, None
    else:
        if Path(args.report).exists() and not args.rerun:
            sys.exit(f"{args.report} existe déjà : un lancement officiel ne remplace rien en silence. "
                     "Utilise --rerun pour en journaliser un nouveau.")
        sizes, n_sim, reps_null, reps_bias, cache = (cfg.SIZES, cfg.N_CALIBRATION, cfg.N_REPS_NULL,
                                                      cfg.N_REPS_BIAS, args.cache_dir)

    t0 = time.time()
    all_rows = []
    for n in sizes:
        print(f"\n[n={n}] calibration de la loi nulle ({n_sim} simulations)...", flush=True)
        last = {"p": -1}

        def progress(done, total):
            p = int(10 * done / total)
            if p != last["p"]:
                last["p"] = p
                print(f"   {done}/{total}  ({time.time() - t0:.0f} s écoulées)", flush=True)

        cal = b.calibrate(n, n_sim, cache_dir=cache, progress=progress)
        cells = [("null", 0.0, reps_null)]
        cells += [(sc, lv, reps_bias) for sc, lvls in cfg.SCENARIOS.items() for lv in lvls]
        for sc, lv, reps in cells:
            rows = b.run_cell(sc, lv, n, reps, cal)
            all_rows += rows
            best = next(r for r in rows if r["test"] == "per_number_holm")
            print(f"[n={n}] {sc:10s} niveau={lv:<5g} réps={reps:<5d} per_number_holm={100 * best['rate']:.1f} % "
                  f"({time.time() - t0:.0f} s)", flush=True)
        # reproductibilité : même cellule relancée => résultats identiques
        r1 = b.run_cell("number", 0.2, n, cfg.CHUNK_REPS, cal)
        r2 = b.run_cell("number", 0.2, n, cfg.CHUNK_REPS, cal)
        print(f"[n={n}] reproductibilité (même graine, mêmes résultats) : {r1 == r2}", flush=True)
        if r1 != r2:
            sys.exit("ÉCHEC : le banc n'est pas reproductible.")

    meta = {"config_hash": cfg.config_hash(), "n_calibration": n_sim, "git_commit": git_commit(),
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    text = b.build_report(all_rows, meta)
    ok = b.fpr_all_ok(all_rows)

    if args.smoke:
        print("\n" + text)
        print(f"SMOKE terminé en {time.time() - t0:.0f} s. Critère FPR (indicatif, échantillon réduit) : {ok}")
        return

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(text, encoding="utf-8")
    with open(args.csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)
    conn = sqlite3.connect(args.db)
    run_id = b.store_run(conn, cfg.BASE_SEED, "bench_m4", cfg.config_hash(),
                         {"config": cfg.CONFIG, "n_calibration": n_sim}, all_rows, meta["git_commit"])
    conn.close()
    print(f"\nRapport : {args.report}\nCSV : {args.csv}\nBase : simulated_runs.id = {run_id}")
    print(f"Terminé en {time.time() - t0:.0f} s. Critère FPR rempli : {ok}")


if __name__ == "__main__":
    main()
