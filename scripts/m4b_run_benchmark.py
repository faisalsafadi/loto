#!/usr/bin/env python
"""M4b — extension POST_HOC du banc d'essai M4 : niveaux de dépendance plus faibles.

Les niveaux ci-dessous ont été choisis APRÈS avoir vu la saturation du test de recouvrement dans M4
(100 % de puissance dès rho = 0,02 à n = 3155) : cette extension est donc POST_HOC. Elle ne remplace
rien de M4 : même moteur, même calibration en cache, scénario « dépendance » uniquement.

PRÉDICTIONS ÉCRITES AVANT EXÉCUTION (test de recouvrement, calcul à la main) :
  n = 3155 : rho = 0,002 -> ~10 % ; 0,005 -> ~40 % ; 0,01 -> ~93 %   (biais minimal à 80 % ~ 0,009)
  n = 500  : rho = 0,002 -> ~6 %  ; 0,005 -> ~10 % ; 0,01 -> ~27 %

  python scripts/m4b_run_benchmark.py
"""
import argparse
import csv
import hashlib
import json
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from loto_research.simulation import bench as b
from loto_research.simulation import bench_config as cfg

LEVELS = (0.002, 0.005, 0.01)
REPS = 200
PRED = {(3155, 0.002): 0.10, (3155, 0.005): 0.40, (3155, 0.01): 0.93,
        (500, 0.002): 0.06, (500, 0.005): 0.10, (500, 0.01): 0.27}


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def load_m4_dependence(path):
    rows = []
    p = Path(path)
    if not p.exists():
        return rows
    with open(p, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["scenario"] == "dependence":
                rows.append({"n": int(r["n"]), "scenario": "dependence", "level": float(r["level"]),
                             "reps": int(r["reps"]), "test": r["test"], "rejections": int(r["rejections"]),
                             "rate": float(r["rate"]), "ci_low": float(r["ci_low"]),
                             "ci_high": float(r["ci_high"]), "source": "M4"})
    return rows


def pct(x):
    return f"{100 * x:.1f} %"


def build_report(new_rows, old_rows, meta):
    heads = list(cfg.TESTS)
    L = ["# BENCHMARK_M4B — extension POST_HOC : dépendance faible\n"]
    L.append(f"Config de base (SHA256) : `{cfg.config_hash()}` · Seed {cfg.BASE_SEED} · "
             f"Commit : {meta.get('git_commit')} · Date : {meta.get('created_at')}\n")
    L.append("Statut : **POST_HOC**. Les niveaux de rho (0,002 ; 0,005 ; 0,01) ont été choisis après avoir vu la "
             "saturation de M4. Les prédictions de la colonne « prédit » ont été écrites avant l'exécution "
             "(en tête de `scripts/m4b_run_benchmark.py`). Les lignes « M4 » viennent du lancement officiel de M4.\n")
    L.append("## 1. Puissance sous dépendance (CALCUL, DESCRIPTIVE)\n")
    for n in cfg.SIZES:
        allrows = [dict(r, source="M4b") for r in new_rows if r["n"] == n] + [r for r in old_rows if r["n"] == n]
        if not allrows:
            continue
        L.append(f"### dependence — n = {n}\n")
        L.append("| rho | source | prédit (recouvrement) | " + " | ".join(heads) + " |")
        L.append("|---|---|---|" + "---|" * len(heads))
        for lv in sorted({r["level"] for r in allrows}):
            src = next(r["source"] for r in allrows if r["level"] == lv)
            pred = PRED.get((n, lv))
            cells = []
            for t in heads:
                r = next(x for x in allrows if x["level"] == lv and x["test"] == t)
                cells.append(f"{pct(r['rate'])} [{pct(r['ci_low'])}–{pct(r['ci_high'])}]")
            L.append(f"| {lv:g} | {src} | {pct(pred) if pred is not None else '—'} | " + " | ".join(cells) + " |")
        L.append("")
    L.append("## 2. Biais minimal détectable à 80 % de puissance, test de recouvrement (CALCUL)\n")
    L.append("Interpolation linéaire entre niveaux testés (M4 + M4b combinés) : estimation grossière.\n")
    L.append("| n | rho minimal à 80 % |")
    L.append("|---|---|")
    for n in cfg.SIZES:
        sub = sorted([r for r in new_rows + old_rows if r["n"] == n and r["test"] == "consecutive_overlap"],
                     key=lambda r: r["level"])
        if not sub:
            continue
        val, note = b.min_detectable([r["level"] for r in sub], [r["rate"] for r in sub])
        L.append(f"| {n} | {f'{val:.3g} ({note})' if val is not None else note} |")
    L.append("")
    L.append("## 3. Limites (LIMITATION)\n")
    L.append("- Niveaux choisis après observation : POST_HOC, descriptif seulement.")
    L.append("- 200 répétitions par cellule : erreur type jusqu'à 3,5 points ; interpolation grossière.")
    L.append("- rho est la probabilité de reprise de chaque numéro du tirage précédent dans un modèle simple ; "
             "d'autres formes de dépendance ne sont pas couvertes.")
    L.append("- Le banc mesure la sensibilité du moteur, pas un pouvoir prédictif.")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/loto.sqlite")
    ap.add_argument("--cache-dir", default="data/simulations")
    ap.add_argument("--old-csv", default="reports/bench_m4_results.csv")
    ap.add_argument("--report", default="reports/BENCHMARK_M4B.md")
    ap.add_argument("--csv", default="reports/bench_m4b_results.csv")
    ap.add_argument("--rerun", action="store_true")
    args = ap.parse_args()

    if Path(args.report).exists() and not args.rerun:
        sys.exit(f"{args.report} existe déjà : rien n'est remplacé en silence. Utilise --rerun.")

    t0 = time.time()
    new_rows = []
    for n in cfg.SIZES:
        print(f"[n={n}] chargement de la calibration (cache : {args.cache_dir})...", flush=True)
        cal = b.calibrate(n, cfg.N_CALIBRATION, cache_dir=args.cache_dir)
        for lv in LEVELS:
            rows = b.run_cell("dependence", lv, n, REPS, cal)
            new_rows += rows
            ov = next(r for r in rows if r["test"] == "consecutive_overlap")
            print(f"[n={n}] rho={lv:<6g} réps={REPS} recouvrement={100 * ov['rate']:.1f} % "
                  f"({time.time() - t0:.0f} s)", flush=True)
        r1 = b.run_cell("dependence", LEVELS[0], n, cfg.CHUNK_REPS, cal)
        r2 = b.run_cell("dependence", LEVELS[0], n, cfg.CHUNK_REPS, cal)
        print(f"[n={n}] reproductibilité : {r1 == r2}", flush=True)
        if r1 != r2:
            sys.exit("ÉCHEC : le banc n'est pas reproductible.")

    old_rows = load_m4_dependence(args.old_csv)
    meta = {"git_commit": git_commit(), "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(build_report(new_rows, old_rows, meta), encoding="utf-8")
    with open(args.csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(new_rows[0].keys()))
        w.writeheader()
        w.writerows(new_rows)
    params = {"status": "POST_HOC", "levels": list(LEVELS), "reps": REPS, "base_config_hash": cfg.config_hash()}
    h = hashlib.sha256(json.dumps(params, sort_keys=True).encode("utf-8")).hexdigest()
    conn = sqlite3.connect(args.db)
    run_id = b.store_run(conn, cfg.BASE_SEED, "bench_m4b_post_hoc", h, params, new_rows, meta["git_commit"])
    conn.close()
    print(f"\nRapport : {args.report}\nCSV : {args.csv}\nBase : simulated_runs.id = {run_id}\n"
          f"Terminé en {time.time() - t0:.0f} s.")


if __name__ == "__main__":
    main()
