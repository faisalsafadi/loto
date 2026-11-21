"""Chargeur base -> DataFrame au format de DATASET_v001 (SPEC_V2 §4, M2). Les fonctions d'analyse
de v1 attendent ces colonnes : le chargeur les reproduit sans rien modifier aux données.
Les corrections enregistrées (table draw_corrections) sont appliquées au chargement : le tirage
d'origine reste intact dans la base, seul le résultat chargé est corrigé."""
import json

import pandas as pd

from loto_research.db.corrections import apply_corrections, load_corrections

WEEKDAYS_FR = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]


def load_draws_dataframe(conn, game_id, after_date=None, limit=None):
    """Tirages d'un jeu, ordonnés par (date, id) ; chronological_id = rang 1..N dans cet ordre.
    Les numéros sont restitués dans l'ordre source (n1..nk), sans tri, avec les corrections appliquées.
    after_date : ne garde que les tirages de date STRICTEMENT postérieure (règle anti-peeking, M3).
    limit : ne garde que les `limit` premiers tirages dans l'ordre chronologique."""
    game = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    if game is None:
        raise ValueError(f"Jeu inconnu : {game_id}")
    k = game["k"]
    sql = "SELECT id, draw_date, source_draw_no, numbers_json, bonus FROM draws WHERE game_id = ?"
    args = [game_id]
    if after_date is not None:
        sql += " AND draw_date > ?"
        args.append(str(after_date))
    sql += " ORDER BY draw_date, id"
    if limit is not None:
        sql += " LIMIT ?"
        args.append(int(limit))
    rows = conn.execute(sql, args).fetchall()
    corrections = load_corrections(conn, game_id)

    records = []
    for i, r in enumerate(rows, start=1):
        nums, bonus = apply_corrections(json.loads(r["numbers_json"]), r["bonus"], corrections.get(r["id"], []))
        rec = {"date": r["draw_date"], "draw_number_source": r["source_draw_no"]}
        for j, v in enumerate(nums, start=1):
            rec[f"n{j}"] = v
        rec["bonus"] = bonus
        rec["chronological_id"] = i
        records.append(rec)

    number_cols = [f"n{j}" for j in range(1, k + 1)]
    columns = ["date", "draw_number_source"] + number_cols + ["bonus", "chronological_id"]
    df = pd.DataFrame(records, columns=columns)

    dates = pd.to_datetime(df["date"])
    df["date"] = dates.astype("datetime64[ms]")
    for c in ["draw_number_source"] + number_cols + ["bonus", "chronological_id"]:
        df[c] = df[c].astype("Int64")
    df["year"] = dates.dt.year.astype("Int16")
    df["month"] = dates.dt.month.astype("Int8")
    df["day"] = dates.dt.day.astype("Int8")
    df["weekday"] = pd.Categorical(dates.dt.day_of_week.map(lambda d: WEEKDAYS_FR[d]))
    return df[["date", "draw_number_source"] + number_cols + ["bonus", "year", "month", "day", "weekday",
                                                                 "chronological_id"]]
