"""Accès à la base, validation généralisée k parmi N, ajout seul (SPEC_V2 §2, §4, §5)."""
import hashlib
import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from loto_research.db.schema import MIGRATIONS


class ValidationError(ValueError):
    """Tirage invalide : jamais inséré, jamais corrigé silencieusement."""


def connect(path):
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for i, sql in enumerate(MIGRATIONS, start=1):
        if i > version:
            conn.executescript(sql)
            conn.execute(f"PRAGMA user_version = {i}")
    conn.commit()


def get_or_create_game(conn, name, k, n_max, bonus_range=None, bonus_exclusive=True, notes=None):
    row = conn.execute("SELECT * FROM games WHERE name = ?", (name,)).fetchone()
    if row is not None:
        if (row["k"], row["n_max"], row["bonus_range"], bool(row["bonus_exclusive"])) != (
            k, n_max, bonus_range, bool(bonus_exclusive)
        ):
            raise ValidationError(f"Le jeu '{name}' existe déjà avec une configuration différente.")
        return row["id"]
    cur = conn.execute(
        "INSERT INTO games (name, k, n_max, bonus_range, bonus_exclusive, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (name, k, n_max, bonus_range, int(bonus_exclusive), notes),
    )
    conn.commit()
    return cur.lastrowid


def _as_int(x, label):
    try:
        v = int(x)
    except (TypeError, ValueError):
        raise ValidationError(f"{label} : valeur non entière ({x!r})")
    if v != x:
        raise ValidationError(f"{label} : valeur non entière ({x!r})")
    return v


def validate_draw(game, draw_date, numbers, bonus):
    """Règles V001-V007 généralisées. Retourne (date_iso, numbers_list, bonus_or_None).
    L'ordre des numéros est conservé tel que fourni (aucune normalisation silencieuse)."""
    try:
        d = date.fromisoformat(str(draw_date))
    except ValueError:
        raise ValidationError(f"Date invalide : {draw_date!r} (format attendu AAAA-MM-JJ)")

    nums = [_as_int(x, "numéro") for x in numbers]
    if len(nums) != game["k"]:
        raise ValidationError(f"{len(nums)} numéros fournis, {game['k']} attendus")
    if len(set(nums)) != len(nums):
        raise ValidationError(f"Numéros en double : {nums}")
    if any(not (1 <= v <= game["n_max"]) for v in nums):
        raise ValidationError(f"Numéro hors de [1, {game['n_max']}] : {nums}")

    if game["bonus_range"] is None:
        if bonus is not None:
            raise ValidationError("Ce jeu n'a pas de complémentaire")
        return d.isoformat(), nums, None
    if bonus is None:
        raise ValidationError("Complémentaire manquant")
    b = _as_int(bonus, "complémentaire")
    if not (1 <= b <= game["bonus_range"]):
        raise ValidationError(f"Complémentaire hors de [1, {game['bonus_range']}] : {b}")
    if game["bonus_exclusive"] and b in nums:
        raise ValidationError(f"Complémentaire {b} déjà présent parmi les numéros principaux")
    return d.isoformat(), nums, b


def _row_hash(game_id, draw_date, source_draw_no, numbers, bonus):
    canon = f"{game_id}|{draw_date}|{source_draw_no}|{','.join(map(str, numbers))}|{bonus}"
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def add_draw(conn, game_id, draw_date, numbers, bonus, source, source_ref=None, source_draw_no=None,
             commit=True):
    game = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    if game is None:
        raise ValidationError(f"Jeu inconnu : {game_id}")
    d, nums, b = validate_draw(game, draw_date, numbers, bonus)
    sdn = None if source_draw_no is None else _as_int(source_draw_no, "numéro de tirage")
    sha = _row_hash(game_id, d, sdn, nums, b)
    try:
        cur = conn.execute(
            "INSERT INTO draws (game_id, draw_date, source_draw_no, numbers_json, bonus, source, "
            "source_ref, ingested_at, row_sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (game_id, d, sdn, json.dumps(nums), b, source, source_ref,
             datetime.now(timezone.utc).isoformat(), sha),
        )
    except sqlite3.IntegrityError:
        raise ValidationError("Tirage déjà présent (même jeu, date, numéros, complémentaire)")
    if commit:
        conn.commit()
    return cur.lastrowid


def add_correction(conn, draw_id, field, old_value, new_value, reason, author):
    if conn.execute("SELECT 1 FROM draws WHERE id = ?", (draw_id,)).fetchone() is None:
        raise ValidationError(f"Tirage inconnu : {draw_id}")
    if not reason or not author:
        raise ValidationError("Une correction exige une raison et un auteur")
    cur = conn.execute(
        "INSERT INTO draw_corrections (draw_id, field, old_value, new_value, reason, author, at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (draw_id, field, str(old_value), str(new_value), reason, author,
         datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return cur.lastrowid


def count_draws(conn, game_id):
    return conn.execute("SELECT COUNT(*) FROM draws WHERE game_id = ?", (game_id,)).fetchone()[0]
