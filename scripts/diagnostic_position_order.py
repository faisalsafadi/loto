#!/usr/bin/env python3
"""Diagnostic Phase 4 (lecture seule) : les colonnes n1..n6 sont-elles triées par ordre croissant ?

Si oui, le test de biais de position de phase4_anomalies.py utilise le MAUVAIS modèle nul
(uniforme) : les statistiques d'ordre d'un tirage sans remise ne sont jamais uniformes par
construction, ce qui expliquerait les chi2 énormes sans qu'il s'agisse d'une anomalie.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from loto_research.validation.schema import NUMBER_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_parquet(ROOT / "data/analytic/draws.parquet")

vals = df[NUMBER_COLUMNS].to_numpy()
is_sorted = (vals[:, :-1] < vals[:, 1:]).all(axis=1)
print(f"Lignes triees n1<n2<...<n6 : {is_sorted.sum()} / {len(df)} ({is_sorted.mean():.2%})")
print(f"Lignes NON triees          : {(~is_sorted).sum()}")

print("\nStatistiques descriptives par colonne (min, mean, median, max) :")
print(df[NUMBER_COLUMNS].agg(["min", "mean", "median", "max"]).round(2))

print("\nn1 est-il toujours le minimum des 6 ?", (vals.min(axis=1) == vals[:, 0]).mean())
print("n6 est-il toujours le maximum des 6 ?", (vals.max(axis=1) == vals[:, 5]).mean())

if not is_sorted.all():
    idx = (~is_sorted).nonzero()[0][:10]
    print(f"\nExemples de lignes NON triees (jusqu'a 10), chronological_id + valeurs :")
    print(df.iloc[idx][["chronological_id", "date"] + NUMBER_COLUMNS])
