#!/usr/bin/env python
"""Exporte les tirages de la base vers le CSV public livré avec le logiciel.

  python scripts/export_public_dataset.py            # écrit data/public/loto_maroc_draws.csv

N'exporte que les tirages. Affiche le nombre de lignes, l'empreinte SHA256 du fichier et l'empreinte des données de
la base : une base recréée avec `loto init-db` à partir de ce CSV doit afficher la MÊME empreinte des données."""
import argparse
import hashlib
import sys
from pathlib import Path

from loto_research.db.core import connect
from loto_research.db.export import export_draws_csv
from loto_research.db.runs import dataset_hash


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/loto.sqlite")
    ap.add_argument("--game", default="Loto Maroc 6/49")
    ap.add_argument("--out", default="data/public/loto_maroc_draws.csv")
    ap.add_argument("--force", action="store_true", help="autorise l'écrasement du CSV de sortie")
    args = ap.parse_args()

    if Path(args.out).exists() and not args.force:
        sys.exit(f"{args.out} existe déjà : rien n'est écrasé en silence. Utilise --force si tu le veux.")
    conn = connect(args.db)
    game = conn.execute("SELECT * FROM games WHERE name = ?", (args.game,)).fetchone()
    if game is None:
        sys.exit(f"Jeu introuvable : {args.game!r}")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    n = export_draws_csv(conn, game["id"], args.out)
    sha = hashlib.sha256(Path(args.out).read_bytes()).hexdigest()
    print(f"{n} tirages exportés dans {args.out}")
    print(f"SHA256 du fichier : {sha}")
    print(f"Empreinte des données de la base : {dataset_hash(conn, game['id'])}")
    print("Une base recréée par `loto init-db` doit afficher la même empreinte des données (début).")


if __name__ == "__main__":
    main()
