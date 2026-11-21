#!/usr/bin/env python3
"""Phase 5 — Analyse temporelle.

Usage :
    # Essai chronometre d'abord :
    python scripts/phase5_temporal.py --n-permutations 2000 --quick-test

    # Run officiel (20000 permutations, seed 42) :
    python scripts/phase5_temporal.py
"""
import argparse
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loto_research.temporal.consecutive_pairs import (
    build_consecutive_mask, draws_to_bitmasks, intersection_size_distribution,
    permutation_test_mean_intersection,
)
from loto_research.temporal.period_homogeneity import homogeneity_test
from loto_research.temporal.runs import runs_test
from loto_research.validation.schema import NUMBER_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_N_PERMUTATIONS = 20000
SEED = 42


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def guard_amendments():
    checks = [
        (ROOT / "docs/Cahier_des_charges", "AMENDEMENT A1"),
        (ROOT / "HYPOTHESES.md", "A5 — Tirages consécutifs"),
        (ROOT / "HYPOTHESES.md", "A3 — Découpage temporel unique"),
    ]
    for path, needle in checks:
        if not path.exists() or needle not in path.read_text(encoding="utf-8"):
            sys.exit(f"ARRET : amendement manquant dans {path.relative_to(ROOT)} ('{needle}').")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-permutations", type=int, default=None)
    ap.add_argument("--quick-test", action="store_true")
    args = ap.parse_args()

    guard_amendments()

    n_permutations = args.n_permutations or DEFAULT_N_PERMUTATIONS
    is_official_run = (not args.quick_test) and args.n_permutations is None

    parquet_path = ROOT / "data/analytic/draws.parquet"
    if not parquet_path.exists():
        sys.exit("ARRET : data/analytic/draws.parquet introuvable. Lancer la Phase 2 d'abord.")
    df = pd.read_parquet(parquet_path)
    n_draws = len(df)

    print("=== PHASE 5 — ANALYSE TEMPORELLE ===")
    print(f"Dataset : {n_draws} tirages (DATASET_v001)")
    print(f"{'RUN OFFICIEL' if is_official_run else 'ESSAI / TEST (pas confirmatoire)'} "
          f"— n_permutations={n_permutations}, seed={SEED}\n")

    # --- H003 : dépendance entre tirages consécutifs (test PRIMAIRE, A2/A3/A5) ---
    valid_mask = build_consecutive_mask(df)
    masks = draws_to_bitmasks(df, NUMBER_COLUMNS)
    t0 = time.time()
    h003 = permutation_test_mean_intersection(masks, valid_mask, n_permutations, SEED, progress=True)
    elapsed_h003 = time.time() - t0
    print(f"[H003] {h003['n_valid_pairs']} paires réellement consécutives sur {n_draws - 1} paires "
          f"chronologiques ({n_draws - 1 - h003['n_valid_pairs']} exclues, amendement A5).")
    print(f"[H003] Moyenne observée = {h003['observed_mean_intersection']:.4f}  "
          f"E[H0] = {h003['expected_under_h0']:.4f}  "
          f"p_value_permutation = {h003['p_value_permutation']:.5f}  ({elapsed_h003:.1f}s)")

    intersection_dist = intersection_size_distribution(masks, valid_mask)

    # --- H007 : comparaison inter-périodes (test PRIMAIRE, A3), principaux et complémentaire ---
    h007_main = homogeneity_test(df, NUMBER_COLUMNS)
    h007_bonus = homogeneity_test(df, ["bonus"])
    print(f"\n[H007] Principaux : chi2={h007_main['chi2']:.2f}  df={h007_main['df']}  "
          f"p={h007_main['p_value']:.4f}")
    print(f"[H007] Complémentaire : chi2={h007_bonus['chi2']:.2f}  df={h007_bonus['df']}  "
          f"p={h007_bonus['p_value']:.4f}")

    # --- Runs test (EXPLORATOIRE, A2) sur la parité de la somme, ordre chronologique ---
    d_sorted = df.sort_values("chronological_id")
    sums = d_sorted[NUMBER_COLUMNS].sum(axis=1)
    parity_seq = (sums % 2 == 0).astype(int).to_numpy()  # 1 = somme paire, 0 = somme impaire
    runs_res = runs_test(parity_seq)
    print(f"\n[Runs test, EXPLORATOIRE] parité de la somme : n_runs={runs_res['n_runs']} "
          f"(attendu {runs_res['expected_runs']:.1f}), z={runs_res['z']:.3f}, p={runs_res['p_value']:.4f}")

    if not is_official_run:
        print("\n(Rapport non ecrit : ceci est un essai. Relancer sans option pour le run officiel.)")
        return

    # --- Rapport ---
    now = datetime.now(timezone.utc)

    def period_table_md(res, label):
        t = res["table"]
        row_totals = t.sum(axis=1)
        return "\n".join(f"  - {idx} : {row_totals[idx]} {label}" for idx in t.index)

    lines = [
        "# TEMPORAL_REPORT.md", "",
        "## LOTO MAROC Research Engine — Analyse temporelle (Phase 5)", "",
        f"Généré le {now.isoformat()}. Dataset : DATASET_v001, {n_draws} tirages.", "",
        "Toute différence entre périodes est qualifiée comme une différence de propriétés statistiques "
        "entre périodes, jamais comme preuve de fraude (Cahier des charges §19).", "",

        "## OBSERVATION", "",
        f"- Tirages réellement consécutifs (amendement A5) : {h003['n_valid_pairs']} sur "
        f"{n_draws - 1} paires chronologiques ({n_draws - 1 - h003['n_valid_pairs']} exclues : tirage "
        "absent entre les deux, ou écart calendaire > 4 jours).",
        f"- Moyenne observée de numéros communs entre tirages consécutifs : "
        f"{h003['observed_mean_intersection']:.4f} (référence théorique sous indépendance : "
        f"6×6/49 = {6 * 6 / 49:.4f}).",
        f"- Distribution des tailles d'intersection (0 à 6), sur {intersection_dist['n_pairs']} paires : "
        f"observé {intersection_dist['observed_counts']} vs hypergéométrique exacte "
        f"{[round(x, 1) for x in intersection_dist['expected_counts']]}.",
        "- Effectifs par période (A3), 6 principaux :\n" + period_table_md(h007_main, "tirages-numéros"),
        "- Effectifs par période (A3), complémentaire :\n" + period_table_md(h007_bonus, "tirages"),
        "- Rappel (amendement A6) : passage de 2 à 3 tirages/semaine entre 2015 et 2016, quasiment à "
        "la frontière des périodes 2011-2015 et 2016-2020 — cause connue à considérer en premier pour "
        "toute différence entre ces deux périodes précises.",
        "",

        "## CALCUL", "",
        "### H003 — Dépendance entre tirages consécutifs",
        f"- **Test PRIMAIRE (permutation, {n_permutations} permutations, seed={SEED})** : "
        f"p_value_permutation = **{h003['p_value_permutation']:.5f}**",
        f"- Espérance sous H0 (permutée) : {h003['expected_under_h0']:.4f} "
        f"(écart-type {h003['std_under_h0']:.4f})",
        "",
        "### H007 — Stabilité inter-périodes (test PRIMAIRE : χ² d'homogénéité période × numéro)",
        f"- 6 numéros principaux : χ²={h007_main['chi2']:.3f}, df={h007_main['df']}, "
        f"p={h007_main['p_value']:.4f}",
        f"- Complémentaire : χ²={h007_bonus['chi2']:.3f}, df={h007_bonus['df']}, "
        f"p={h007_bonus['p_value']:.4f}",
        "",
        "### Runs test — parité de la somme (EXPLORATOIRE, amendement A2)",
        f"- n={runs_res['n']} (pair={runs_res['n1']}, impair={runs_res['n2']}), "
        f"suites observées={runs_res['n_runs']} (attendu {runs_res['expected_runs']:.2f}), "
        f"z={runs_res['z']:.3f}, p={runs_res['p_value']:.4f}",
        "",

        "## INTERPRÉTATION", "",
        "- H003 et H007 sont évaluées par leur test PRIMAIRE pré-enregistré (permutation pour H003, "
        "χ² d'homogénéité pour H007) — aucune autre statistique n'est utilisée comme base de décision.",
        "- Si H007 rejette H0 pour une comparaison touchant la frontière 2015/2016, le changement de "
        "fréquence des tirages (amendement A6) est l'explication de premier ordre à examiner avant "
        "toute autre interprétation (Cahier §18-19).",
        "- Le runs test est EXPLORATOIRE (A2) : un résultat significatif ne devient pas confirmatoire "
        "sans être ajouté à HYPOTHESES.md comme POST_HOC et testé indépendamment.",
        "",

        "## LIMITATION", "",
        f"- H003 exclut {n_draws - 1 - h003['n_valid_pairs']} paires chronologiques sur {n_draws - 1} "
        "(tirage absent entre les deux ou écart calendaire trop grand) : le résultat porte sur les "
        "tirages réellement adjacents, pas sur l'ensemble de la séquence brute.",
        "- H007 teste l'homogénéité globale des 49 fréquences entre périodes, pas une rupture datée "
        "précisément : une détection de rupture par change-point (CUSUM/`ruptures`) reste à faire "
        "séparément si H007 rejette H0 (hors du périmètre pré-enregistré de cette phase).",
        "- Le runs test traite les tirages en séquence continue ; les tirages absents (A5) ne sont pas "
        "comblés, ce qui peut légèrement affecter le compte de suites sans invalider le test.",
    ]
    (ROOT / "reports/TEMPORAL_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    audit_path = ROOT / "research_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
    audit.setdefault("test_batches", [])
    audit["test_batches"].append({
        "phase": 5, "label": "phase5_h003_permutation", "timestamp": now.isoformat(),
        "number_of_tests": 1, "method": "permutation", "n_permutations": n_permutations, "seed": SEED,
    })
    audit["test_batches"].append({
        "phase": 5, "label": "phase5_h007_homogeneity_main", "timestamp": now.isoformat(),
        "number_of_tests": 1, "method": "chi2_contingency",
    })
    audit["test_batches"].append({
        "phase": 5, "label": "phase5_h007_homogeneity_bonus", "timestamp": now.isoformat(),
        "number_of_tests": 1, "method": "chi2_contingency",
    })
    audit["total_tests_registered"] = audit.get("total_tests_registered", 0) + 3
    audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")

    deps = {}
    for name in ("pandas", "numpy", "scipy"):
        try:
            deps[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            deps[name] = "absent"
    run = {"run_id": now.isoformat(), "timestamp": now.isoformat(), "phase": 5,
           "dataset_version": "DATASET_v001", "git_commit": git_head(),
           "python_version": platform.python_version(), "dependencies": deps,
           "seed": SEED, "n_permutations": n_permutations, "elapsed_seconds_h003": elapsed_h003}
    (ROOT / "logs" / f"run_phase5_{now:%Y%m%d_%H%M%S}.json").write_text(json.dumps(run, indent=2), encoding="utf-8")

    print("\nRapport ecrit : reports/TEMPORAL_REPORT.md")
    print(f"Git HEAD : {git_head()}")


if __name__ == "__main__":
    main()
