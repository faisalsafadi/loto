#!/usr/bin/env python3
"""Phase 3 — Analyse statistique fondamentale.

Usage :
    # 1) ESSAI RAPIDE d'abord, pour chronométrer avant de lancer les 100 000 simulations officielles :
    python scripts/phase3_statistics.py --n-simulations 2000 --quick-test

    # 2) Run officiel (valeurs de configs/default.yaml : 100000 simulations, seed 42) :
    python scripts/phase3_statistics.py
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
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loto_research.statistics.descriptive import (
    bonus_frequencies, low_high_distribution, number_frequencies,
    odd_even_distribution, sum_distribution,
)
from loto_research.statistics.uniformity import chi_square_uniformity, monte_carlo_uniformity_pvalue

ROOT = Path(__file__).resolve().parents[1]


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def guard_amendments():
    checks = [
        (ROOT / "docs/Cahier_des_charges", "AMENDEMENT A1"),
        (ROOT / "docs/IMPLEMENTATION_SPEC.md", "AMENDEMENT A1"),
        (ROOT / "HYPOTHESES.md", "A7"),
    ]
    for path, needle in checks:
        if not path.exists() or needle not in path.read_text(encoding="utf-8"):
            sys.exit(f"ARRET : amendement manquant dans {path.relative_to(ROOT)} ('{needle}').")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-simulations", type=int, default=None,
                     help="Defaut : valeur de configs/default.yaml (100000).")
    ap.add_argument("--quick-test", action="store_true",
                     help="Marque explicitement ce run comme un ESSAI (pas la reference confirmatoire H001).")
    ap.add_argument("--batch-size", type=int, default=100)
    args = ap.parse_args()

    guard_amendments()

    config = yaml.safe_load((ROOT / "configs/default.yaml").read_text(encoding="utf-8"))
    seed = config["simulation"]["seed"]
    n_simulations = args.n_simulations or config["simulation"]["n_simulations"]
    is_official_run = (not args.quick_test) and args.n_simulations is None

    parquet_path = ROOT / "data/analytic/draws.parquet"
    if not parquet_path.exists():
        sys.exit("ARRET : data/analytic/draws.parquet introuvable. Lancer la Phase 2 d'abord.")
    df = pd.read_parquet(parquet_path)
    n_draws = len(df)

    print("=== PHASE 3 — ANALYSE STATISTIQUE FONDAMENTALE ===")
    print(f"Dataset               : {n_draws} tirages (DATASET_v001)")
    print(f"{'RUN OFFICIEL' if is_official_run else 'ESSAI / TEST (pas confirmatoire)'} "
          f"— n_simulations={n_simulations}, seed={seed}")
    if not is_official_run:
        print("  ATTENTION : ce run ne fait PAS foi pour le verdict de la Phase 3. "
              "Relancer sans --n-simulations/--quick-test pour le run officiel.")

    # --- H001 : uniformité des 6 numéros principaux ---
    freq_main = number_frequencies(df)
    chi2_naive = chi_square_uniformity(freq_main["count"].values, freq_main["expected"].values)
    print(f"\n[H001] chi2 naif (df=48, INDICATIF SEULEMENT, cf. amendement A1) : "
          f"chi2={chi2_naive['chi2']:.2f}  p={chi2_naive['p_value']:.4f}")

    t0 = time.time()
    mc = monte_carlo_uniformity_pvalue(chi2_naive["chi2"], n_draws, n_simulations, seed,
                                        batch_size=args.batch_size, progress=True)
    elapsed = time.time() - t0
    print(f"[H001] Monte-Carlo (test PRIMAIRE, amendement A1) : "
          f"p_value_monte_carlo={mc['p_value_monte_carlo']:.5f}  "
          f"E_null={mc['expected_statistic_null']:.2f} (attendu ~43, PAS 48)  "
          f"({elapsed:.1f}s pour {n_simulations} simulations)")

    # --- H002 : uniformité du complémentaire (amendement A7 : chi2(48) classique suffit) ---
    freq_bonus = bonus_frequencies(df)
    chi2_bonus = chi_square_uniformity(freq_bonus["count"].values, freq_bonus["expected"].values)
    print(f"\n[H002] chi2(48) du complementaire (test PRIMAIRE, amendement A7) : "
          f"chi2={chi2_bonus['chi2']:.2f}  p={chi2_bonus['p_value']:.4f}")

    # --- Sommes, pair/impair, bas/haut (descriptif, Cahier §15) ---
    sum_res = sum_distribution(df)
    odd_res = odd_even_distribution(df)
    lowhigh_res = low_high_distribution(df)
    print(f"\n[Somme]      moyenne={sum_res['observed_mean']:.3f} (theorique {sum_res['theoretical_mean']:.1f})  "
          f"chi2 vs distribution exacte p={sum_res['chi_square_vs_exact_distribution']['p_value']:.4f}")
    print(f"[Pair/impair] chi2 vs hypergeometrique exacte p={odd_res['chi_square_vs_exact_hypergeometric']['p_value']:.4f}")
    print(f"[Bas/haut]    chi2 vs hypergeometrique exacte p={lowhigh_res['chi_square_vs_exact_hypergeometric']['p_value']:.4f}")

    # --- Numeros extremes (OBSERVATION seule, aucune interpretation predictive - Cahier §11) ---
    top5 = freq_main.nlargest(5, "count")[["number", "count", "z_score"]]
    bot5 = freq_main.nsmallest(5, "count")[["number", "count", "z_score"]]

    if not is_official_run:
        print("\n(Rapport non ecrit : ceci est un essai. Relancer sans option pour le run officiel.)")
        return

    # --- Rapport ---
    now = datetime.now(timezone.utc)
    lines = [
        "# STATISTICAL_REPORT.md", "",
        "## LOTO MAROC Research Engine — Analyse statistique fondamentale (Phase 3)", "",
        f"Généré le {now.isoformat()}. Dataset : DATASET_v001, {n_draws} tirages, "
        f"{df['date'].min().date()} -> {df['date'].max().date()}.", "",
        "Aucun numéro n'est qualifié de « chaud » ou « froid » avec implication prédictive à ce stade "
        "(Cahier des charges §11) : ce rapport est descriptif et confirmatoire, pas prédictif.", "",

        "## OBSERVATION", "",
        f"- 6 numéros principaux : {n_draws * 6} tirages-numéros au total sur 49 numéros, "
        f"attendu {freq_main['expected'].iloc[0]:.2f} par numéro.",
        "- Numéro(s) les plus fréquents : " + ", ".join(
            f"{r.number} ({r.count}, z={r.z_score:+.2f})" for r in top5.itertuples()),
        "- Numéro(s) les moins fréquents : " + ", ".join(
            f"{r.number} ({r.count}, z={r.z_score:+.2f})" for r in bot5.itertuples()),
        f"- Complémentaire : attendu {freq_bonus['expected'].iloc[0]:.2f} par numéro sur {n_draws} tirages.",
        f"- Somme des 6 numéros : moyenne observée {sum_res['observed_mean']:.3f} "
        f"(théorique exacte {sum_res['theoretical_mean']:.3f}), écart-type observé "
        f"{sum_res['observed_var'] ** 0.5:.3f} (théorique {sum_res['theoretical_var'] ** 0.5:.3f}).",
        "",

        "## CALCUL", "",
        "### H001 — Équirépartition des 6 numéros principaux",
        f"- χ² naïf (df=48, RAPPORTÉ À TITRE INDICATIF SEULEMENT, cf. amendement A1) : "
        f"χ²={chi2_naive['chi2']:.3f}, p={chi2_naive['p_value']:.4f}",
        f"- **Test PRIMAIRE (Monte-Carlo, {n_simulations} simulations, seed={seed})** : "
        f"p_value_monte_carlo = **{mc['p_value_monte_carlo']:.5f}**",
        f"- Espérance de la statistique sous H0 (simulée) : {mc['expected_statistic_null']:.2f} "
        f"(écart-type {mc['std_statistic_null']:.2f}) — référence théorique ≈43 (PAS 48, amendement A1).",
        "",
        "### H002 — Équirépartition du complémentaire",
        "- **Test PRIMAIRE (χ²(48) classique, amendement A7 — complémentaire confirmé exclusif "
        "des 6 principaux en Phase 2, loi marginale uniforme sur 49)** : "
        f"χ²={chi2_bonus['chi2']:.3f}, p={chi2_bonus['p_value']:.4f}",
        "",
        "### Somme des 6 numéros (distribution EXACTE par dénombrement, pas d'approximation CLT)",
        f"- χ² vs distribution exacte : χ²={sum_res['chi_square_vs_exact_distribution']['chi2']:.3f}, "
        f"df={sum_res['chi_square_vs_exact_distribution']['df']}, "
        f"p={sum_res['chi_square_vs_exact_distribution']['p_value']:.4f} "
        f"({sum_res['chi_square_vs_exact_distribution']['n_bins_before_merge']} classes -> "
        f"{sum_res['chi_square_vs_exact_distribution']['n_bins_after_merge']} après fusion des queues, effectif attendu < 5)",
        "",
        "### Pair/impair (distribution EXACTE hypergéométrique)",
        f"- χ²={odd_res['chi_square_vs_exact_hypergeometric']['chi2']:.3f}, "
        f"df={odd_res['chi_square_vs_exact_hypergeometric']['df']}, "
        f"p={odd_res['chi_square_vs_exact_hypergeometric']['p_value']:.4f}",
        f"- Observé : {odd_res['observed_distribution']}",
        "- Attendu : {" + ", ".join(f"{k}: {v:.1f}" for k, v in odd_res['expected_distribution'].items()) + "}",
        "",
        "### Bas (1-24) / haut (25-49) (distribution EXACTE hypergéométrique)",
        f"- χ²={lowhigh_res['chi_square_vs_exact_hypergeometric']['chi2']:.3f}, "
        f"df={lowhigh_res['chi_square_vs_exact_hypergeometric']['df']}, "
        f"p={lowhigh_res['chi_square_vs_exact_hypergeometric']['p_value']:.4f}",
        "",

        "## INTERPRÉTATION", "",
        "- H001 et H002 sont évaluées par leur test PRIMAIRE pré-enregistré (Monte-Carlo pour les 6 "
        "principaux, χ²(48) pour le complémentaire) — les statistiques asymptotiques naïves sont "
        "rapportées uniquement à titre indicatif, jamais comme base de décision.",
        "- Un résultat non significatif ici (p élevé) est une absence de preuve de structure, pas une "
        "preuve d'absence — voir les Phases 4 à 7 pour les tests de structures plus fines "
        "(paires, triplets, ruptures temporelles).",
        "- Le statut UNTESTED de H001/H002 dans HYPOTHESES.md doit être mis à jour manuellement "
        "après revue de ce rapport (pas automatiquement par ce script).",
        "",

        "## LIMITATION", "",
        "- La variance utilisée pour les z-scores descriptifs par numéro (IMPLEMENTATION_SPEC §14) est "
        "MARGINALE et ne tient pas compte des corrélations négatives entre numéros dues au tirage sans "
        "remise (voir amendement A1) : elle sert à une lecture rapide, pas de test formel.",
        "- Les ~33 tirages numérotés absents (amendement A5) ne sont pas inclus : ce rapport porte sur "
        "les 3155 tirages réellement présents dans DATASET_v001, pas sur un historique complet reconstitué.",
        f"- Run Monte-Carlo : {'OFFICIEL' if is_official_run else 'ESSAI, NON CONFIRMATOIRE'} "
        f"({n_simulations} simulations, seed {seed}, {elapsed:.1f}s).",
    ]
    (ROOT / "reports/STATISTICAL_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    deps = {}
    for name in ("pandas", "numpy", "scipy"):
        try:
            deps[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            deps[name] = "absent"
    run = {"run_id": now.isoformat(), "timestamp": now.isoformat(), "phase": 3,
           "dataset_version": "DATASET_v001", "git_commit": git_head(),
           "python_version": platform.python_version(), "dependencies": deps,
           "seed": seed, "n_simulations": n_simulations, "monte_carlo_elapsed_seconds": elapsed}
    (ROOT / "logs" / f"run_phase3_{now:%Y%m%d_%H%M%S}.json").write_text(json.dumps(run, indent=2), encoding="utf-8")

    print("\nRapport ecrit : reports/STATISTICAL_REPORT.md")
    print(f"Git HEAD      : {git_head()}")


if __name__ == "__main__":
    main()
