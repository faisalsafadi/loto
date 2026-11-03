#!/usr/bin/env python3
"""Ajoute une ligne par modèle évalué en Phase 9 dans experiments/registry.csv (IMPLEMENTATION_SPEC
§45 : une ligne par expérience). S'adapte à l'en-tête déjà présent."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
summary = json.loads((ROOT / "reports/model_summary_phase9.json").read_text(encoding="utf-8"))

PARAMS = {
    "baseline_random": "p=6/49 constant",
    "frequency_baseline": "alpha=10.0 (lissage bayesien ancre sur 6/49)",
    "logistic_regression": "C=1.0, max_iter=1000, features=freq_last_{10,20,50,100,250}+"
                            "gap_current_adjusted+prev_sum+prev_odd_count+prev_low_count+prev_overlap",
}
STATUS = {
    "baseline_random": "GO (baseline de reference)",
    "frequency_baseline": "NO-GO (pire que random, p_holm=0.00755)",
    "logistic_regression": "NO-GO (pire que random, p_holm=0.00755 ; meilleur que frequency, p_holm=0.0497)",
}

rows = []
for model_name, res in summary["results"].items():
    rows.append({
        "experiment_id": f"EXP_PHASE9_{model_name}",
        "date": summary["created_at"],
        "dataset_version": "DATASET_v001",
        "feature_version": "FEATURES_v001",
        "model_version": model_name,
        "hypothesis": "H008 (depistage preliminaire, split unique -- test officiel reserve a la Phase 10)",
        "parameters": PARAMS[model_name],
        "seed": 42,
        "result": f"logloss={res['mean_logloss']:.6f}; brier={res['mean_brier']:.6f}; "
                  f"hits_moy={res['mean_hits_per_draw']:.4f}",
        "status": STATUS[model_name],
    })

path = ROOT / "experiments/registry.csv"
if path.exists() and path.stat().st_size > 0:
    with path.open("r", encoding="utf-8") as f:
        header = next(csv.reader(f))
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        for row in rows:
            writer.writerow({k: row.get(k, "N/A") for k in header})
    print(f"{len(rows)} lignes ajoutées (en-tête existant conservé : {header})")
else:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Fichier créé avec {len(rows)} lignes, en-tête : {list(rows[0].keys())}")
