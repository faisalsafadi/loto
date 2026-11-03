#!/usr/bin/env python3
"""M2 — Vérifie que (1) le chargeur base -> DataFrame reproduit DATASET_v001 et (2) l'analyse
rapide redonne les valeurs de v1 (seed 42, 100000 simulations, 20000 permutations).

Usage (depuis la racine du dépôt) :
    python scripts/m2_check_reproduction.py
"""
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loto_research.analysis.core import run_quick_analysis
from loto_research.db.core import connect, init_db
from loto_research.db.loader import load_draws_dataframe

ROOT = Path(__file__).resolve().parents[1]
SHARED = ["date", "draw_number_source", "n1", "n2", "n3", "n4", "n5", "n6", "bonus", "year", "month",
          "day", "chronological_id"]

# Valeurs de v1 (FINAL.md / rapports de phase), avec la tolérance = demi-unité du dernier chiffre publié.
EXPECTED = [
    ("H001", "p_raw", 0.899, 0.0006),
    ("H002", "statistic", 69.355, 0.0006),
    ("H002", "p_raw", 0.0235, 0.00006),
    ("H003", "p_raw", 0.946, 0.0006),
    ("H007_main", "p_raw", 0.741, 0.0006),
    ("H007_bonus", "p_raw", 0.542, 0.0006),
    ("H004_main", "statistic", 0.0, 0.0),
    ("H004_bonus", "statistic", 0.0, 0.0),
]


def main():
    print("=== M2 — REPRODUCTION DES RÉSULTATS DE v1 DEPUIS LA BASE ===")
    conn = connect(ROOT / "data" / "loto.sqlite")
    init_db(conn)
    game_id = conn.execute("SELECT id FROM games WHERE name = 'Loto Maroc 6/49'").fetchone()["id"]
    df = load_draws_dataframe(conn, game_id)
    ref = pd.read_parquet(ROOT / "data" / "analytic" / "draws.parquet").sort_values("chronological_id").reset_index(drop=True)

    loader_ok = True
    for col in SHARED:
        try:
            pd.testing.assert_series_equal(df[col], ref[col], check_dtype=False, check_names=False)
        except AssertionError as e:
            loader_ok = False
            print(f"  Colonne {col} : DIFFÉRENTE ({str(e).splitlines()[0]})")
    if not (df["weekday"].astype(str).to_numpy() == ref["weekday"].astype(str).to_numpy()).all():
        loader_ok = False
        print("  Colonne weekday : DIFFÉRENTE")
    print(f"Chargeur identique à DATASET_v001 (13 colonnes + weekday) : {loader_ok}")

    t0 = time.time()
    results = run_quick_analysis(df, n_sim=100000, n_perm=20000, seed=42, progress=False)
    print(f"Analyse rapide terminée en {time.time() - t0:.0f}s\n")
    by_label = {r["label"]: r for r in results}

    all_ok = loader_ok
    for label, key, expected, tol in EXPECTED:
        got = by_label[label][key]
        ok = got is not None and abs(got - expected) <= tol
        all_ok = all_ok and ok
        print(f"{label:<11} {key:<10} obtenu={got!s:>22}  attendu v1={expected}  {'OK' if ok else 'ÉCART'}")

    print(f"\nCritères M2 remplis : {all_ok}")


if __name__ == "__main__":
    main()
