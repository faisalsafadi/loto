"""Export des tirages en CSV public (même format que `loto add-csv`). N'exporte QUE les tirages (valeurs corrigées
appliquées) : jamais les hypothèses, les prédictions ni les journaux de l'utilisateur."""
import csv
import json

from loto_research.db.corrections import apply_corrections, load_corrections

CSV_HEADER = ["date", "n1", "n2", "n3", "n4", "n5", "n6", "bonus", "source", "source_ref", "draw_no"]


def export_draws_csv(conn, game_id, path):
    """Écrit les tirages du jeu, par date puis par identifiant, avec leur source. Retourne le nombre de lignes."""
    corrections = load_corrections(conn, game_id)
    rows = conn.execute(
        "SELECT id, draw_date, source_draw_no, numbers_json, bonus, source, source_ref FROM draws "
        "WHERE game_id = ? ORDER BY draw_date, id", (game_id,)).fetchall()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER)
        for r in rows:
            nums, bonus = apply_corrections(json.loads(r["numbers_json"]), r["bonus"], corrections.get(r["id"], []))
            w.writerow([r["draw_date"], *nums, "" if bonus is None else bonus, r["source"], r["source_ref"] or "",
                        "" if r["source_draw_no"] is None else r["source_draw_no"]])
    return len(rows)
