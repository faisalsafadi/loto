#!/usr/bin/env python3
"""M1 — Importe DATASET_v001 dans data/loto.sqlite et vérifie : nombre de tirages, identité des
numéros et dates avec le parquet, refus de toute modification (ajout seul).

Usage (depuis la racine du dépôt) :
    python scripts/m1_import_v1_dataset.py
"""
import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loto_research.db.core import connect, count_draws, get_or_create_game, init_db
from loto_research.db.importer import import_v1_parquet

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "loto.sqlite"
PARQUET = ROOT / "data" / "analytic" / "draws.parquet"
MANIFEST = ROOT / "data" / "raw" / "MANIFEST.json"
GAME_NAME = "Loto Maroc 6/49"


def main():
    raw_sha = "UNKNOWN"
    if MANIFEST.exists():
        raw_sha = json.loads(MANIFEST.read_text(encoding="utf-8")).get("sha256", "UNKNOWN")
    print("=== M1 — IMPORT DE DATASET_v001 DANS SQLITE ===")
    print(f"RAW sha256 (MANIFEST) : {raw_sha}")

    conn = connect(DB_PATH)
    init_db(conn)
    game_id = get_or_create_game(
        conn, GAME_NAME, k=6, n_max=49, bonus_range=49, bonus_exclusive=True,
        notes="Complémentaire exclusif des 6 principaux (0/3155 recoupements, amendement A7 de v1)",
    )
    if count_draws(conn, game_id) > 0:
        sys.exit(f"ARRET : la base contient déjà {count_draws(conn, game_id)} tirages pour ce jeu. "
                 f"Supprime data/loto.sqlite pour repartir d'une base vide (aucun import en double).")

    n = import_v1_parquet(conn, game_id, PARQUET, source="DATASET_v001", source_ref=f"raw_sha256={raw_sha}")
    print(f"Tirages insérés : {n}")

    df = pd.read_parquet(PARQUET).sort_values("chronological_id").reset_index(drop=True)
    rows = conn.execute("SELECT * FROM draws WHERE game_id = ? ORDER BY id", (game_id,)).fetchall()
    ok_count = len(rows) == len(df)
    date_col = "date" if "date" in df.columns else "draw_date"
    mismatches = 0
    for r, (_, p) in zip(rows, df.iterrows()):
        same_nums = json.loads(r["numbers_json"]) == [int(p[f"n{i}"]) for i in range(1, 7)]
        same_bonus = r["bonus"] == int(p["bonus"])
        same_date = r["draw_date"] == pd.Timestamp(p[date_col]).date().isoformat()
        if not (same_nums and same_bonus and same_date):
            mismatches += 1
    print(f"Nombre identique au parquet : {ok_count} ({len(rows)} vs {len(df)})")
    print(f"Lignes différentes du parquet (numéros, complémentaire, date) : {mismatches}")
    print(f"Plage de dates : {rows[0]['draw_date']} -> {rows[-1]['draw_date']}")

    refused = {}
    for label, sql in (("UPDATE", "UPDATE draws SET bonus = 1 WHERE id = 1"),
                       ("DELETE", "DELETE FROM draws WHERE id = 1")):
        try:
            conn.execute(sql)
            conn.rollback()
            refused[label] = False
        except sqlite3.DatabaseError as e:
            conn.rollback()
            refused[label] = True
            print(f"{label} refusé : {e}")
    print(f"Ajout seul vérifié (UPDATE et DELETE refusés) : {all(refused.values())}")

    go = ok_count and mismatches == 0 and all(refused.values()) and n == 3155
    print(f"\nCritères M1 remplis : {go}  (attendu : 3155 tirages, 0 différence, UPDATE/DELETE refusés)")
    print(f"Base : {DB_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
