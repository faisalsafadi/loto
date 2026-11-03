"""Écriture depuis le tableau de bord. Ce module est le SEUL du tableau de bord qui écrit, et il n'est importé que si
le tableau de bord est lancé avec --writable (python -m loto_research.dashboard --writable).

Il n'ajoute aucune règle : il appelle les MÊMES fonctions que la ligne de commande (validation complète, source
obligatoire, un seul tirage par date, ajout seul, raison et auteur pour toute correction, gel avant le tirage)."""
import csv
import re
import tempfile
from pathlib import Path

from loto_research.db.core import ValidationError, connect, init_db
from loto_research.db.corrections import correct_draw, parse_changes, plan_correction
from loto_research.db.ingest import add_csv, prepare_draw
from loto_research.prediction import store

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
CSV_HEADER = ["date", "n1", "n2", "n3", "n4", "n5", "n6", "bonus", "source", "source_ref", "draw_no"]


def _open(db, game_name):
    conn = connect(db)
    init_db(conn)
    game = conn.execute("SELECT * FROM games WHERE name = ?", (game_name,)).fetchone()
    if game is None:
        conn.close()
        raise ValidationError(f"Jeu introuvable : {game_name!r}")
    return conn, game


def parse_pasted(text):
    """Lignes collées du site : N R1 R2 R3 R4 R5 R6 C AAAA-MM-JJ (espaces ou tabulations). En-têtes ignorés."""
    rows, errors, headers = [], [], 0
    for ln, line in enumerate(str(text).splitlines(), start=1):
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


def preview_pasted(db, game_name, text, source):
    """Vérifie les lignes collées SANS rien écrire. Les tirages déjà présents et identiques sont ignorés ;
    toute autre anomalie est une erreur et bloque l'enregistrement."""
    rows, errors, _ = parse_pasted(text)
    if not rows and not errors:
        errors.append("Aucune ligne de tirage reconnue.")
    conn, game = _open(db, game_name)
    new, skipped, notes, seen = [], [], set(), set()
    try:
        for r in rows:
            if r["date"] in seen:
                errors.append(f"Date en double dans la liste : {r['date']}")
                continue
            seen.add(r["date"])
            try:
                prep = prepare_draw(conn, game["id"], r["date"], r["nums"], r["bonus"], source)
            except ValidationError as e:
                if "déjà dans la base" in str(e):
                    skipped.append(r)
                else:
                    errors.append(f"{r['date']} : {e}")
                continue
            new.append(r)
            notes.update(prep["notes"])
    finally:
        conn.close()
    return {"new": sorted(new, key=lambda r: r["date"]), "skipped": skipped, "errors": errors,
            "notes": sorted(notes)}


def commit_pasted(db, game_name, text, source, source_ref=None):
    """Enregistre les nouveaux tirages collés, TOUT OU RIEN (même fonction que `loto add-csv`)."""
    res = preview_pasted(db, game_name, text, source)
    if res["errors"]:
        raise ValidationError("\n".join(res["errors"]))
    if not res["new"]:
        raise ValidationError("Aucun tirage à ajouter : tout est déjà dans la base.")
    conn, game = _open(db, game_name)
    tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="", encoding="utf-8")
    try:
        w = csv.writer(tmp)
        w.writerow(CSV_HEADER)
        for r in res["new"]:
            w.writerow([r["date"], *r["nums"], r["bonus"], str(source).strip(), source_ref or "", r["no"]])
        tmp.close()
        add_csv(conn, game["id"], tmp.name)
    finally:
        tmp.close()
        Path(tmp.name).unlink(missing_ok=True)
        conn.close()
    return len(res["new"])


def _draw_id_by_date(conn, game_id, draw_date):
    rows = conn.execute("SELECT id FROM draws WHERE game_id = ? AND draw_date = ?",
                        (game_id, str(draw_date).strip())).fetchall()
    if not rows:
        raise ValidationError(f"Aucun tirage à la date {str(draw_date).strip()!r}.")
    if len(rows) > 1:
        raise ValidationError("Plusieurs tirages à cette date : utilise la ligne de commande "
                              "(loto correct --draw-id).")
    return rows[0]["id"]


def _changes(text):
    return parse_changes([p.strip() for p in str(text).split(",") if p.strip()])


def preview_correction(db, game_name, draw_date, changes_text):
    conn, game = _open(db, game_name)
    try:
        did = _draw_id_by_date(conn, game["id"], draw_date)
        return dict(plan_correction(conn, did, _changes(changes_text)), draw_id=did)
    finally:
        conn.close()


def apply_correction(db, game_name, draw_date, changes_text, reason, author):
    conn, game = _open(db, game_name)
    try:
        did = _draw_id_by_date(conn, game["id"], draw_date)
        return correct_draw(conn, did, _changes(changes_text), reason, author)
    finally:
        conn.close()


def freeze(db, game_name, payload):
    """Fige une prédiction préparée (mêmes règles que `scripts/predictions.py next`)."""
    conn, game = _open(db, game_name)
    try:
        return store.freeze_prediction(conn, game["id"], payload, out_dir=Path(db).resolve().parent / "predictions")
    finally:
        conn.close()
