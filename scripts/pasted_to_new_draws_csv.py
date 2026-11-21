#!/usr/bin/env python
"""Convertit des lignes copiées-collées en CSV pour `loto add-csv`. N'ÉCRIT RIEN dans la base.

Une ligne = N R1 R2 R3 R4 R5 R6 C AAAA-MM-JJ (séparateurs : espaces ou tabulations), comme dans le tableur.
 - les lignes d'en-tête sont ignorées ;
 - les tirages déjà dans la base ET identiques servent de recoupement et ne sont pas réimportés ;
 - un tirage de même date mais de contenu DIFFÉRENT arrête tout : il faut comprendre pourquoi avant d'avancer.

  python scripts/pasted_to_new_draws_csv.py data/raw/tirages_colles.txt
"""
import argparse
import csv
import re
import sqlite3
import sys
from pathlib import Path

from loto_research.db.loader import load_draws_dataframe

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_lines(text):
    rows, errors, headers = [], [], 0
    for ln, line in enumerate(text.splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        parts = re.split(r"\s+", s)
        if not parts[0].isdigit():
            headers += 1
            continue
        if len(parts) != 9 or not DATE.fullmatch(parts[8]) or not all(p.isdigit() for p in parts[:8]):
            errors.append(f"ligne {ln} illisible : {s!r}")
            continue
        rows.append({"no": int(parts[0]), "nums": [int(p) for p in parts[1:7]], "bonus": int(parts[7]),
                     "date": parts[8]})
    return rows, errors, headers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("txt", help="fichier texte contenant les lignes collées")
    ap.add_argument("--db", default="data/loto.sqlite")
    ap.add_argument("--game", default="Loto Maroc 6/49")
    ap.add_argument("--out", default="data/raw/nouveaux_tirages_log.csv")
    ap.add_argument("--source", default="liste collée par l'utilisateur (tableur loteriema, 2026-10-31)")
    ap.add_argument("--force", action="store_true", help="autorise l'écrasement du CSV de sortie")
    args = ap.parse_args()

    if Path(args.out).exists() and not args.force:
        sys.exit(f"{args.out} existe déjà : rien n'est écrasé en silence. Utilise --force si tu le veux.")
    rows, errors, headers = parse_lines(Path(args.txt).read_text(encoding="utf-8"))
    if errors:
        sys.exit("\n".join(errors))
    if not rows:
        sys.exit("Aucune ligne de tirage reconnue.")
    dates = [r["date"] for r in rows]
    dup = sorted({d for d in dates if dates.count(d) > 1})
    if dup:
        sys.exit(f"Dates en double dans la liste : {dup}")

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    game = conn.execute("SELECT * FROM games WHERE name = ?", (args.game,)).fetchone()
    if game is None:
        sys.exit(f"Jeu introuvable : {args.game!r}")
    dbf = load_draws_dataframe(conn, game["id"])
    db_map = {}
    for _, r in dbf.iterrows():
        db_map.setdefault(r["date"].strftime("%Y-%m-%d"),
                          (frozenset(int(r[f"n{j}"]) for j in range(1, 7)), int(r["bonus"])))

    same, diff, new = [], [], []
    for r in rows:
        if r["date"] not in db_map:
            new.append(r)
        elif db_map[r["date"]] == (frozenset(r["nums"]), r["bonus"]):
            same.append(r)
        else:
            diff.append(r)
    print(f"{len(rows)} lignes lues ({headers} ligne(s) d'en-tête ignorée(s)).")
    print(f"Recoupement avec la base : {len(same)} tirage(s) déjà présent(s) et identique(s) "
          f"{[r['date'] for r in same]}, {len(diff)} DIFFÉRENT(S).")
    if diff:
        for r in diff:
            print(f"  {r['date']} liste : {r['nums']} +{r['bonus']}  |  base : "
                  f"{sorted(db_map[r['date']][0])} +{db_map[r['date']][1]}")
        sys.exit("Incohérence avec la base : rien n'est écrit. À comprendre avant de continuer.")
    if not new:
        sys.exit("Aucun tirage à ajouter : tout est déjà dans la base.")

    new.sort(key=lambda r: r["date"])
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "n1", "n2", "n3", "n4", "n5", "n6", "bonus", "source", "source_ref", "draw_no"])
        for r in new:
            w.writerow([r["date"], *r["nums"], r["bonus"], args.source, "", r["no"]])
    print(f"\n=== {len(new)} nouveaux tirages, du {new[0]['date']} au {new[-1]['date']} -> {args.out} ===")
    for r in new:
        print(f"{r['date']}  {r['nums']}  +{r['bonus']}  (n° {r['no']})")
    print("\nRien n'a été écrit dans la base. Compare ces lignes à ta liste, puis :")
    print(f"  python -m loto_research.cli add-csv {args.out}")


if __name__ == "__main__":
    main()
