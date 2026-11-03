#!/usr/bin/env python3
"""Ajoute une ligne dans experiments/registry.csv pour la Phase 8. S'adapte à l'en-tête déjà
présent dans le fichier (ne suppose pas un ordre de colonnes figé)."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "data/features/features_manifest.json").read_text(encoding="utf-8"))

row = {
    "experiment_id": "EXP_PHASE8_FEATURES_v001",
    "date": manifest["created_at"],
    "dataset_version": manifest["dataset_version"],
    "feature_version": manifest["features_version"],
    "model_version": "N/A",
    "hypothesis": "N/A (construction de features, pas de test d'hypothese)",
    "parameters": f"windows={manifest['windows']}; leakage_checkpoints={len(manifest['leakage_test']['checkpoints_tested'])}",
    "seed": 42,
    "result": f"leakage_passed={manifest['leakage_test']['passed']}; n_rows={manifest['n_rows']}",
    "status": "GO",
}

path = ROOT / "experiments/registry.csv"
if path.exists() and path.stat().st_size > 0:
    with path.open("r", encoding="utf-8") as f:
        header = next(csv.reader(f))
    with path.open("a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=header).writerow({k: row.get(k, "N/A") for k in header})
    print(f"Ligne ajoutée (en-tête existant conservé : {header})")
else:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)
    print(f"Fichier créé avec en-tête : {list(row.keys())}")
