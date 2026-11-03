#!/usr/bin/env python
"""Prépare le CSV des nouveaux tirages à partir d'un loteriema.xlsx mis à jour. N'ÉCRIT RIEN dans la base.

 - ne garde que les tirages de date STRICTEMENT postérieure au dernier tirage de la base ;
 - compare aussi les anciennes lignes du fichier à la base (contrôle d'intégrité, informatif) ;
 - écrit un CSV au format de `loto add-csv` (aucune saisie à la main, donc aucune faute de transcription).

  python scripts/xlsx_to_new_draws_csv.py CHEMIN/loteriema.xlsx
"""
import argparse
import csv
import sqlite3
import sys
from pathlib import Path

import pandas as pd

from loto_research.db.loader import load_draws_dataframe

COLS_NUM = [f"Résultats {i}" for i in range(1, 7)]


def find(df, name):
    for c in df.columns:
        if str(c).strip().lower() == name.lower():
            return c
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx", help="fichier loteriema.xlsx mis à jour")
    ap.add_argument("--db", default="data/loto.sqlite")
    ap.add_argument("--game", default="Loto Maroc 6/49")
    ap.add_argument("--out", default="data/raw/nouveaux_tirages_log.csv")
    ap.add_argument("--source", default="loteriema.xlsx (fichier de l'utilisateur)")
    ap.add_argument("--force", action="store_true", help="autorise l'écrasement du CSV de sortie")
    args = ap.parse_args()

    if Path(args.out).exists() and not args.force:
        sys.exit(f"{args.out} existe déjà : rien n'est écrasé en silence. Utilise --force si tu le veux.")

    df = pd.read_excel(args.xlsx)
    cols = {n: find(df, n) for n in ["DATE TIRAGE", "C", "N. du tirage"] + COLS_NUM}
    missing = [n for n, c in cols.items() if c is None and n != "N. du tirage"]
    if missing:
        sys.exit(f"Colonnes introuvables : {missing}. Colonnes du fichier : {list(df.columns)}")

    dates = pd.to_datetime(df[cols["DATE TIRAGE"]], errors="coerce")
    nums = df[[cols[n] for n in COLS_NUM]].apply(pd.to_numeric, errors="coerce")
    bonus = pd.to_numeric(df[cols["C"]], errors="coerce")
    valid = dates.notna() & nums.notna().all(axis=1) & bonus.notna()
    draw_no = pd.to_numeric(df[cols["N. du tirage"]], errors="coerce") if cols["N. du tirage"] else None

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    game = conn.execute("SELECT * FROM games WHERE name = ?", (args.game,)).fetchone()
    if game is None:
        sys.exit(f"Jeu introuvable : {args.game!r}")
    dbf = load_draws_dataframe(conn, game["id"])
    max_date = dbf["date"].max()
    db_map = {}
    for _, r in dbf.iterrows():
        db_map.setdefault(r["date"].strftime("%Y-%m-%d"),
                          (frozenset(int(r[f"n{j}"]) for j in range(1, 7)), int(r["bonus"])))

    # 1. contrôle d'intégrité des anciennes lignes (informatif)
    old_map = {}
    for i in df.index[valid & (dates <= max_date)]:
        key = dates[i].strftime("%Y-%m-%d")
        old_map.setdefault(key, (frozenset(int(nums.loc[i, c]) for c in nums.columns), int(bonus[i])))
    common = set(old_map) & set(db_map)
    mismatch = sorted(k for k in common if old_map[k] != db_map[k])
    xlsx_only = sorted(set(old_map) - set(db_map))
    db_only = sorted(set(db_map) - set(old_map))
    print(f"=== Contrôle des anciennes lignes (jusqu'au {max_date.date()}) ===")
    print(f"dates communes identiques : {len(common) - len(mismatch)} / {len(common)}")
    print(f"dates communes AVEC DIFFÉRENCE de contenu : {len(mismatch)} {mismatch[:10]}")
    print(f"dates seulement dans le xlsx : {len(xlsx_only)} {xlsx_only[:10]}")
    print(f"dates seulement dans la base : {len(db_only)} {db_only[:10]}")

    # 2. nouvelles lignes
    broken = df.index[(dates > max_date) & ~valid]
    if len(broken):
        sys.exit(f"Lignes récentes illisibles (numéros ou complémentaire manquants), lignes Excel : "
                 f"{[int(i) + 2 for i in broken]}. Corrige le fichier puis relance.")
    new_idx = [i for i in df.index[valid & (dates > max_date)]]
    new_idx.sort(key=lambda i: dates[i])
    if not new_idx:
        sys.exit("Aucun tirage postérieur au dernier tirage de la base.")
    rows = []
    for i in new_idx:
        n = int(draw_no[i]) if draw_no is not None and pd.notna(draw_no[i]) else ""
        rows.append([dates[i].strftime("%Y-%m-%d")] + [int(nums.loc[i, c]) for c in nums.columns]
                    + [int(bonus[i]), args.source, "", n])
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "n1", "n2", "n3", "n4", "n5", "n6", "bonus", "source", "source_ref", "draw_no"])
        w.writerows(rows)
    print(f"\n=== {len(rows)} nouveaux tirages, du {rows[0][0]} au {rows[-1][0]} -> {args.out} ===")
    for r in rows:
        print(f"{r[0]}  {r[1:7]}  +{r[7]}  (n° {r[10]})")
    print("\nRien n'a été écrit dans la base. Vérifie ces lignes, puis :")
    print(f"  python -m loto_research.cli add-csv {args.out}")


if __name__ == "__main__":
    main()
