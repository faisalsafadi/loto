#!/usr/bin/env python3
"""Ajoute une ligne par modèle évalué en Phase 10 (walk-forward, test officiel de H008) dans
experiments/registry.csv. S'adapte à l'en-tête déjà présent."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
summary = json.loads((ROOT / "reports/walk_forward_summary_phase10.json").read_text(encoding="utf-8"))

PARAMS = {
    "baseline_random": "p=6/49 constant",
    "frequency_baseline": "alpha=10.0 (lissage bayesien ancre sur 6/49), expanding window",
    "logistic_regression": "C=1.0, max_iter=1000, expanding window, retrain_step=10, "
                            "min_train=500, features=freq_last_{10,20,50,100,250}+"
                            "gap_current_adjusted+prev_sum+prev_odd_count+prev_low_count+prev_overlap",
}
STATUS = {
    "baseline_random": "GO (baseline de reference -- H008 CONFIRMEE : aucun modele ne le bat)",
    "frequency_baseline": "NO-GO (pire que random, p_holm=1.6e-05, IC95% exclut 0)",
    "logistic_regression": "NO-GO (pire que random, p_holm=0.00717, IC95% exclut 0 ; "
                            "meilleur que frequency, p_holm=0.00168)",
}

rows = []
for model_name, res in summary["results"].items():
    rows.append({
        "experiment_id": f"EXP_PHASE10_{model_name}",
        "date": summary["created_at"],
        "dataset_version": "DATASET_v001",
        "feature_version": "FEATURES_v001",
        "model_version": model_name,
        "hypothesis": "H008 (TEST OFFICIEL -- walk-forward complet, resolu REJECTED)",
        "parameters": PARAMS[model_name],
        "seed": 42,
        "result": f"logloss={res['mean_logloss']:.6f}; brier={res['mean_brier']:.6f}; "
                  f"hits_moy={res['mean_hits_per_draw']:.4f}; n_predictions={summary['n_prediction_points']}",
        "status": STATUS[model_name],
    })

path = ROOT / "experiments/registry.csv"
with path.open("r", encoding="utf-8") as f:
    header = next(csv.reader(f))
with path.open("a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=header)
    for row in rows:
        writer.writerow({k: row.get(k, "N/A") for k in header})
print(f"{len(rows)} lignes ajoutées (en-tête existant conservé : {header})")
