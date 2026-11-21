#!/usr/bin/env python3
"""Phase 10 — Backtesting walk-forward (Cahier §26, IMPLEMENTATION_SPEC §35).

SEULE preuve acceptable de valeur prédictive (Niveau D, Cahier §2). Ceci est le test OFFICIEL de
H008 -- contrairement au dépistage préliminaire de la Phase 9 (split unique).

Choix pré-enregistrés (amendement A10, validés AVANT exécution) :
- Fenêtre EXPANDING (pas rolling).
- MIN_TRAIN_DRAWS = 500 (configs/default.yaml, Phase 0).
- baseline_random / frequency_baseline : évaluées nativement en expanding sur tous les points
  501..3155 (pas de « réentraînement » au sens strict, formules déjà causales).
- logistic_regression : réentraînée tous les 10 tirages, prédictions gelées entre deux
  réentraînements.
- test_no_future_features() revérifié sur 20 points de contrôle répartis sur le walk-forward (pas
  à chaque itération -- coût prohibitif pour une propriété du CODE, pas des données à cet instant
  précis).
- Comparaisons formelles : même protocole que Phase 9 (test primaire = log loss par tirage,
  Wilcoxon apparié + IC bootstrap, 3 comparaisons pré-enregistrées, correction de Holm) -- nouvelle
  famille de tests propre à cette phase, pas combinée avec celle de la Phase 9.
- AUCUN modèle plus complexe que la régression logistique n'est testé (Phase 9 n'a pas justifié
  Random Forest / Gradient Boosting / XGBoost).

Temps d'exécution attendu : quelques minutes (266 réentraînements de la régression logistique +
21 reconstructions complètes du dataset de features pour le spot-check de non-fuite).

Usage :
    python scripts/phase10_walk_forward.py
"""
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loto_research.backtesting.walk_forward import (
    LOGISTIC_RETRAIN_STEP, MIN_TRAIN_DRAWS, walk_forward_baselines, walk_forward_logistic,
)
from loto_research.features.build import build_feature_dataset
from loto_research.features.leakage import test_no_future_features
from loto_research.models import metrics as M
from loto_research.models.evaluate import pivot_to_matrix
from loto_research.models.logistic import prepare_features
from loto_research.statistics.multiple_testing import holm

ROOT = Path(__file__).resolve().parents[1]
N_LEAKAGE_CHECKS = 20
SEED = 42


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def evaluate(name, target_matrix, p_hat):
    logloss = M.log_loss_per_draw(target_matrix, p_hat)
    brier = M.brier_per_draw(target_matrix, p_hat)
    hits = M.top_k_hits_per_draw(target_matrix, p_hat, k=6)
    calib = M.calibration_table(target_matrix, p_hat)
    prob_diag = M.mean_probability_drawn_vs_not(target_matrix, p_hat)
    return {
        "name": name, "logloss_per_draw": logloss, "brier_per_draw": brier, "hits_per_draw": hits,
        "mean_logloss": float(logloss.mean()), "mean_brier": float(brier.mean()),
        "mean_hits_per_draw": float(hits.mean()),
        "hits_distribution": {int(k): int((hits == k).sum()) for k in range(7)},
        "calibration_table": calib, **prob_diag,
    }


def main():
    draws = pd.read_parquet(ROOT / "data/analytic/draws.parquet")
    feats_manifest = json.loads((ROOT / "data/features/features_manifest.json").read_text(encoding="utf-8"))
    if feats_manifest["dataset_version"] != "DATASET_v001":
        sys.exit("ARRET : FEATURES_v001 incohérent avec DATASET_v001.")

    feats_raw = pd.read_parquet(ROOT / "data/features/FEATURES_v001.parquet")
    n_draws = int(feats_raw["chronological_id"].max())

    print("=== PHASE 10 — BACKTESTING WALK-FORWARD (test officiel de H008) ===")
    print(f"Tirages totaux : {n_draws} | Entraînement minimal : {MIN_TRAIN_DRAWS} | "
          f"Points de prédiction évalués : {n_draws - MIN_TRAIN_DRAWS} "
          f"(id {MIN_TRAIN_DRAWS + 1}-{n_draws})")
    print(f"Fenêtre : EXPANDING | Pas de réentraînement logistique : {LOGISTIC_RETRAIN_STEP} tirages\n")

    print(f"[Test de non-fuite] {N_LEAKAGE_CHECKS} points de contrôle sur la plage du walk-forward...")
    leakage_result = test_no_future_features(draws, build_feature_dataset, n_checks=N_LEAKAGE_CHECKS, seed=SEED)
    print(f"[Test de non-fuite] points testés : {leakage_result['checkpoints_tested']}")
    print(f"[Test de non-fuite] PASSÉ : {leakage_result['passed']}")
    if not leakage_result["passed"]:
        print("\n*** NO-GO BLOQUANT ABSOLU *** -- fuite détectée, arrêt avant tout calcul de walk-forward.")
        sys.exit(1)

    pred_ids_b, p_random, p_freq = walk_forward_baselines(draws, feats_raw, min_train=MIN_TRAIN_DRAWS)
    assert pred_ids_b[0] == MIN_TRAIN_DRAWS + 1 and pred_ids_b[-1] == n_draws

    feats_logit = prepare_features(feats_raw)
    n_checkpoints = len(range(MIN_TRAIN_DRAWS, n_draws, LOGISTIC_RETRAIN_STEP))
    print(f"\nWalk-forward régression logistique ({n_checkpoints} réentraînements)...")
    pred_ids_l, p_logit = walk_forward_logistic(feats_logit, min_train=MIN_TRAIN_DRAWS,
                                                 retrain_step=LOGISTIC_RETRAIN_STEP, verbose=True)
    assert np.array_equal(pred_ids_b, pred_ids_l), "Désalignement des points de prédiction."

    target_matrix = pivot_to_matrix(feats_raw, "target", pred_ids_b)

    res_random = evaluate("baseline_random", target_matrix, p_random)
    res_freq = evaluate("frequency_baseline", target_matrix, p_freq)
    res_logit = evaluate("logistic_regression", target_matrix, p_logit)

    print(f"\n--- Résultats (walk-forward complet, n={len(pred_ids_b)} tirages) ---")
    for res in (res_random, res_freq, res_logit):
        print(f"{res['name']:>22s} | logloss={res['mean_logloss']:.6f} | brier={res['mean_brier']:.6f} | "
              f"hits/tirage moy={res['mean_hits_per_draw']:.4f} | "
              f"P(drawn)={res['mean_p_drawn']:.6f} vs P(not drawn)={res['mean_p_not_drawn']:.6f}")
        print(f"    distribution des hits (0-6) : {res['hits_distribution']}")

    comparisons = {
        "frequency_vs_random": M.paired_wilcoxon(res_freq["logloss_per_draw"], res_random["logloss_per_draw"]),
        "logistic_vs_random": M.paired_wilcoxon(res_logit["logloss_per_draw"], res_random["logloss_per_draw"]),
        "logistic_vs_frequency": M.paired_wilcoxon(res_logit["logloss_per_draw"], res_freq["logloss_per_draw"]),
    }
    boot_ci = {
        "frequency_vs_random": M.bootstrap_mean_diff_ci(res_freq["logloss_per_draw"], res_random["logloss_per_draw"]),
        "logistic_vs_random": M.bootstrap_mean_diff_ci(res_logit["logloss_per_draw"], res_random["logloss_per_draw"]),
        "logistic_vs_frequency": M.bootstrap_mean_diff_ci(res_logit["logloss_per_draw"], res_freq["logloss_per_draw"]),
    }
    labels = list(comparisons.keys())
    raw_p = [comparisons[k]["p_value"] for k in labels]
    holm_result = holm(raw_p)
    adjusted = holm_result["adjusted_p_value"]
    rejections = holm_result["reject"]

    print(f"\n--- Comparaisons formelles OFFICIELLES (H008) — Wilcoxon apparié, log loss par tirage, "
          f"n={len(pred_ids_b)} ---")
    print(f"Correction : {holm_result['method']}, alpha={holm_result['alpha']}, "
          f"nombre de tests={holm_result['number_of_tests']}")
    for label, p_adj, rej in zip(labels, adjusted, rejections):
        c = comparisons[label]
        ci = boot_ci[label]
        print(f"{label:>24s} | diff. moyenne={c['mean_diff']:+.6f} "
              f"[IC95% {ci['ci_lower']:+.6f}, {ci['ci_upper']:+.6f}] | "
              f"p_brut={c['p_value']:.6f} | p_ajusté_Holm={p_adj:.6f} | rejet_H0={rej}")

    any_significant = any(rejections)
    print(f"\nAu moins une comparaison significative après Holm : {any_significant}")

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    res_random["calibration_table"].to_csv(reports_dir / "calibration_walkforward_random.csv", index=False)
    res_freq["calibration_table"].to_csv(reports_dir / "calibration_walkforward_frequency.csv", index=False)
    res_logit["calibration_table"].to_csv(reports_dir / "calibration_walkforward_logistic.csv", index=False)

    now = datetime.now(timezone.utc)
    summary = {
        "n_draws_total": n_draws, "min_train_draws": MIN_TRAIN_DRAWS,
        "logistic_retrain_step": LOGISTIC_RETRAIN_STEP,
        "n_prediction_points": int(len(pred_ids_b)),
        "prediction_id_range": [int(pred_ids_b[0]), int(pred_ids_b[-1])],
        "leakage_test": leakage_result,
        "results": {
            r["name"]: {"mean_logloss": r["mean_logloss"], "mean_brier": r["mean_brier"],
                        "mean_hits_per_draw": r["mean_hits_per_draw"],
                        "hits_distribution": r["hits_distribution"],
                        "mean_p_drawn": r["mean_p_drawn"], "mean_p_not_drawn": r["mean_p_not_drawn"]}
            for r in (res_random, res_freq, res_logit)
        },
        "comparisons": {
            label: {**comparisons[label], "p_value_holm": float(p_adj), "reject_h0": bool(rej),
                    "bootstrap_ci": boot_ci[label]}
            for label, p_adj, rej in zip(labels, adjusted, rejections)
        },
        "holm_correction": {"method": holm_result["method"], "alpha": holm_result["alpha"],
                             "number_of_tests": holm_result["number_of_tests"]},
        "any_significant_after_holm": any_significant,
        "note": "Walk-forward complet, expanding window, test OFFICIEL de H008. "
                "Interprétation détaillée dans reports/BACKTEST_REPORT.md.",
        "created_at": now.isoformat(),
    }
    (reports_dir / "walk_forward_summary_phase10.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    deps = {}
    for name in ("pandas", "numpy", "scikit-learn", "scipy"):
        try:
            deps[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            deps[name] = "absent"
    run = {"run_id": now.isoformat(), "timestamp": now.isoformat(), "phase": 10,
           "dataset_version": "DATASET_v001", "features_version": "FEATURES_v001",
           "git_commit": git_head(), "python_version": platform.python_version(),
           "dependencies": deps, "seed": SEED, "min_train_draws": MIN_TRAIN_DRAWS,
           "logistic_retrain_step": LOGISTIC_RETRAIN_STEP}
    (ROOT / "logs" / f"run_phase10_{now:%Y%m%d_%H%M%S}.json").write_text(json.dumps(run, indent=2), encoding="utf-8")

    print("\nRésumé : reports/walk_forward_summary_phase10.json")
    print("Tables de calibration : reports/calibration_walkforward_{random,frequency,logistic}.csv")
    print(f"Git HEAD : {git_head()}")


if __name__ == "__main__":
    main()
