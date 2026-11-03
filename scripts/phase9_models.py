#!/usr/bin/env python3
"""Phase 9 — Baselines et modèles statistiques (Cahier §23-28, IMPLEMENTATION_SPEC §32-34).

Ordre imposé (non négociable) : random baseline -> frequency baseline -> régression logistique.
Si la régression logistique ne bat pas les baselines de manière formellement significative (après
correction de Holm sur les 3 comparaisons pré-enregistrées), aucun modèle plus complexe n'est
ajouté à cette itération (Cahier §27, IMPLEMENTATION_SPEC §33) : « aucun modèle complexe n'est
ajouté sans que le précédent ait justifié l'expérience ».

SPLIT TEMPOREL UNIQUE (PAS un walk-forward complet, réservé à la Phase 10, seul test officiel de
H008) : train = 80% des tirages les plus anciens, test = 20% des tirages les plus récents, coupé
au niveau du TIRAGE ENTIER (jamais à l'intérieur, dépendance structurelle documentée en Phase 8).
Ce split, et tous les autres choix de ce script (alpha, C, test primaire), sont pré-enregistrés
(amendement A9) avant toute exécution.

Usage :
    python scripts/phase9_models.py
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

from loto_research.models.baselines import frequency_baseline_predictions, random_baseline_predictions
from loto_research.models.evaluate import compare_models, evaluate_predictions, pivot_to_matrix
from loto_research.models.logistic import fit_and_predict, prepare_features
from loto_research.statistics.multiple_testing import holm

ROOT = Path(__file__).resolve().parents[1]
TRAIN_FRACTION = 0.8  # pré-enregistré (amendement A9), non ajusté sur les résultats
SEED = 42


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def main():
    draws = pd.read_parquet(ROOT / "data/analytic/draws.parquet")
    feats_manifest = json.loads((ROOT / "data/features/features_manifest.json").read_text(encoding="utf-8"))
    if feats_manifest["dataset_version"] != "DATASET_v001":
        sys.exit(f"ARRET : FEATURES_v001 a été construit sur {feats_manifest['dataset_version']}, "
                 f"pas DATASET_v001. Versions incohérentes.")

    feats = pd.read_parquet(ROOT / "data/features/FEATURES_v001.parquet")
    feats = prepare_features(feats)

    n_draws = int(feats["chronological_id"].max())
    cutoff = int(round(n_draws * TRAIN_FRACTION))
    train_ids = np.arange(1, cutoff + 1)
    test_ids = np.arange(cutoff + 1, n_draws + 1)
    print("=== PHASE 9 — BASELINES ET MODÈLES STATISTIQUES ===")
    print(f"Tirages totaux : {n_draws} | Train : {len(train_ids)} (id 1-{cutoff}) | "
          f"Test : {len(test_ids)} (id {cutoff + 1}-{n_draws})")
    print("[Rappel] Ce split unique n'est PAS le walk-forward complet (Phase 10) ; H008 reste "
          "UNTESTED après cette phase, quel que soit le résultat.\n")

    train_df = feats[feats["chronological_id"].isin(train_ids)]
    test_df = feats[feats["chronological_id"].isin(test_ids)]

    target_test = pivot_to_matrix(test_df, "target", test_ids)

    # --- Baseline 1 : random ---
    p_random_test = random_baseline_predictions(len(test_ids))
    res_random = evaluate_predictions("baseline_random", target_test, p_random_test)

    # --- Baseline 2 : frequency ---
    freq_full = frequency_baseline_predictions(draws)
    p_freq_test = freq_full[cutoff:n_draws]
    res_freq = evaluate_predictions("frequency_baseline", target_test, p_freq_test)

    # --- Modèle 3 : régression logistique ---
    model, p_train_logit, p_test_logit_flat = fit_and_predict(train_df, test_df)
    test_df_pred = test_df.copy()
    test_df_pred["p_hat"] = p_test_logit_flat
    p_logit_test = pivot_to_matrix(test_df_pred, "p_hat", test_ids)
    res_logit = evaluate_predictions("logistic_regression", target_test, p_logit_test)

    print("--- Résultats (test, hors-échantillon) ---")
    for res in (res_random, res_freq, res_logit):
        print(f"{res['name']:>22s} | logloss={res['mean_logloss']:.5f} | brier={res['mean_brier']:.5f} | "
              f"hits/tirage moy={res['mean_hits_per_draw']:.4f} | "
              f"P(drawn)={res['mean_p_drawn']:.5f} vs P(not drawn)={res['mean_p_not_drawn']:.5f}")
        print(f"    distribution des hits (0-6) : {res['hits_distribution']}")

    # --- Comparaisons formelles (test primaire désigné à l'avance : log loss, Wilcoxon apparié
    #     au niveau du tirage, amendement A9) ---
    comparisons = {
        "frequency_vs_random": compare_models(res_freq, res_random),
        "logistic_vs_random": compare_models(res_logit, res_random),
        "logistic_vs_frequency": compare_models(res_logit, res_freq),
    }
    labels = list(comparisons.keys())
    raw_p = [comparisons[k]["p_value"] for k in labels]

    # holm() renvoie un dict : {"method", "alpha", "number_of_tests", "raw_p_value",
    # "adjusted_p_value", "reject"} -- PAS une structure directement zip-able avec `labels`.
    holm_result = holm(raw_p)
    adjusted = holm_result["adjusted_p_value"]
    rejections = holm_result["reject"]

    print(f"\n--- Comparaisons formelles (Wilcoxon apparié, log loss par tirage, n={len(test_ids)}) ---")
    print(f"Correction : {holm_result['method']}, alpha={holm_result['alpha']}, "
          f"nombre de tests={holm_result['number_of_tests']}")
    for label, p_adj, rej in zip(labels, adjusted, rejections):
        c = comparisons[label]
        print(f"{label:>24s} | diff. moyenne={c['mean_diff']:+.5f} | p_brut={c['p_value']:.5f} | "
              f"p_ajusté_Holm={p_adj:.5f} | rejet_H0={rej}")

    any_significant = any(rejections)
    print(f"\nAu moins une comparaison significative après Holm (alpha={holm_result['alpha']}) : {any_significant}")
    print("[Rappel] Même si oui : ceci est un dépistage préliminaire sur UN split, pas le test "
          "officiel de H008 (réservé à la Phase 10).")

    # --- Sauvegarde ---
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    res_random["calibration_table"].to_csv(reports_dir / "calibration_random.csv", index=False)
    res_freq["calibration_table"].to_csv(reports_dir / "calibration_frequency.csv", index=False)
    res_logit["calibration_table"].to_csv(reports_dir / "calibration_logistic.csv", index=False)

    now = datetime.now(timezone.utc)
    summary = {
        "n_draws_total": n_draws, "train_fraction": TRAIN_FRACTION, "cutoff_chronological_id": cutoff,
        "n_train": len(train_ids), "n_test": len(test_ids),
        "results": {
            r["name"]: {"mean_logloss": r["mean_logloss"], "mean_brier": r["mean_brier"],
                        "mean_hits_per_draw": r["mean_hits_per_draw"],
                        "hits_distribution": r["hits_distribution"],
                        "mean_p_drawn": r["mean_p_drawn"], "mean_p_not_drawn": r["mean_p_not_drawn"]}
            for r in (res_random, res_freq, res_logit)
        },
        "comparisons": {
            label: {**comparisons[label], "p_value_holm": float(p_adj), "reject_h0": bool(rej)}
            for label, p_adj, rej in zip(labels, adjusted, rejections)
        },
        "holm_correction": {"method": holm_result["method"], "alpha": holm_result["alpha"],
                             "number_of_tests": holm_result["number_of_tests"]},
        "any_significant_after_holm": any_significant,
        "logistic_regression_coefficients": dict(zip(
            ["freq_last_10", "freq_last_20", "freq_last_50", "freq_last_100", "freq_last_250",
             "gap_current_adjusted", "prev_sum", "prev_odd_count", "prev_low_count", "prev_overlap"],
            [float(c) for c in model.coef_[0]]
        )),
        "note": "Split unique train/test (pas walk-forward). H008 reste UNTESTED ; test officiel en Phase 10.",
        "created_at": now.isoformat(),
    }
    (reports_dir / "model_summary_phase9.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    deps = {}
    for name in ("pandas", "numpy", "scikit-learn", "scipy"):
        try:
            deps[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            deps[name] = "absent"
    run = {"run_id": now.isoformat(), "timestamp": now.isoformat(), "phase": 9,
           "dataset_version": "DATASET_v001", "features_version": "FEATURES_v001",
           "git_commit": git_head(), "python_version": platform.python_version(),
           "dependencies": deps, "seed": SEED, "train_fraction": TRAIN_FRACTION}
    (ROOT / "logs" / f"run_phase9_{now:%Y%m%d_%H%M%S}.json").write_text(json.dumps(run, indent=2), encoding="utf-8")

    print("\nRésumé : reports/model_summary_phase9.json")
    print("Tables de calibration : reports/calibration_{random,frequency,logistic}.csv")
    print(f"Git HEAD : {git_head()}")


if __name__ == "__main__":
    main()
