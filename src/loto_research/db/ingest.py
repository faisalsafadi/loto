"""Ajout de nouveaux tirages (SPEC_V2 §4) : validation avant toute écriture, provenance obligatoire,
un seul tirage par date, ajout seul. Rien n'est jamais corrigé, trié ou normalisé en silence."""
import csv
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

from loto_research.db.core import ValidationError, add_draw, validate_draw
from loto_research.db.corrections import apply_corrections


def parse_numbers(text):
    parts = [p for p in re.split(r"[,\s;]+", str(text).strip()) if p]
    try:
        return [int(p) for p in parts]
    except ValueError:
        raise ValidationError(f"Numéros illisibles : {text!r} (entiers séparés par des espaces ou des virgules)")


def prepare_draw(conn, game_id, draw_date, numbers, bonus, source, today=None, allow_same_date=False):
    """Valide un tirage SANS rien écrire. Retourne {draw_date, numbers, bonus, notes}."""
    game = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    if game is None:
        raise ValidationError(f"Jeu inconnu : {game_id}")
    if source is None or not str(source).strip():
        raise ValidationError("La source est obligatoire : d'où vient ce tirage ?")
    d, nums, b = validate_draw(game, draw_date, numbers, bonus)
    today = today or datetime.now(timezone.utc).date()
    if date.fromisoformat(d) > today:
        raise ValidationError(f"Date dans le futur : {d} (aujourd'hui, UTC : {today.isoformat()})")
    for row in conn.execute("SELECT id, numbers_json, bonus FROM draws WHERE game_id = ? AND draw_date = ?",
                            (game_id, d)).fetchall():
        corr = [(r["field"], r["new_value"]) for r in conn.execute(
            "SELECT field, new_value FROM draw_corrections WHERE draw_id = ? ORDER BY id", (row["id"],))]
        ex_nums, ex_bonus = apply_corrections(json.loads(row["numbers_json"]), row["bonus"], corr)
        if set(ex_nums) == set(nums) and ex_bonus == b:
            raise ValidationError(f"Ce tirage est déjà dans la base ({d}).")
        if not allow_same_date:
            raise ValidationError(
                f"Un tirage différent existe déjà à la date {d} (numéros {ex_nums}, complémentaire {ex_bonus}). "
                f"Pour corriger une erreur de saisie, utilise `loto correct` : un second tirage serait analysé "
                f"en plus du premier. (--allow-same-date pour forcer, à tes risques.)")
    notes = []
    late = [r["code"] for r in conn.execute(
        "SELECT code, registered_date FROM hypotheses WHERE game_id = ? AND kind = 'PRE_REGISTERED'", (game_id,))
        if d <= str(r["registered_date"])]
    if late:
        notes.append(f"Ce tirage est daté au plus tard du jour d'enregistrement de {', '.join(late)} : "
                     f"il ne comptera PAS dans leurs tests prospectifs (il entre seulement dans les données).")
    return {"draw_date": d, "numbers": nums, "bonus": b, "notes": notes}


def add_new_draw(conn, game_id, draw_date, numbers, bonus, source, source_ref=None, source_draw_no=None,
                 today=None, allow_same_date=False, commit=True):
    prep = prepare_draw(conn, game_id, draw_date, numbers, bonus, source, today=today,
                        allow_same_date=allow_same_date)
    draw_id = add_draw(conn, game_id, prep["draw_date"], prep["numbers"], prep["bonus"], str(source).strip(),
                       source_ref=source_ref, source_draw_no=source_draw_no, commit=commit)
    return draw_id, prep


def _read_csv(path, k):
    p = Path(path)
    if not p.exists():
        raise ValidationError(f"Fichier introuvable : {path}")
    with open(p, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        needed = ["date"] + [f"n{i}" for i in range(1, k + 1)] + ["bonus", "source"]
        missing = [c for c in needed if c not in (reader.fieldnames or [])]
        if missing:
            raise ValidationError(f"Colonnes manquantes dans le CSV : {missing}")
        return list(enumerate(reader, start=2))   # la ligne 1 est l'en-tête


def add_csv(conn, game_id, path, today=None, allow_same_date=False, dry_run=False):
    """Ajoute les tirages d'un CSV, TOUT OU RIEN : si une seule ligne est invalide, rien n'est écrit et
    toutes les erreurs sont listées. Colonnes : date,n1..nk,bonus,source[,source_ref,draw_no]."""
    game = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    if game is None:
        raise ValidationError(f"Jeu inconnu : {game_id}")
    rows = _read_csv(path, game["k"])
    if not rows:
        raise ValidationError("CSV vide : aucune ligne de tirage.")
    errors, prepared, seen = [], [], set()
    for line, r in rows:
        try:
            nums = parse_numbers(" ".join(str(r[f"n{i}"]) for i in range(1, game["k"] + 1)))
            raw_bonus = (r.get("bonus") or "").strip()
            try:
                bonus = int(raw_bonus) if raw_bonus else None
            except ValueError:
                raise ValidationError(f"Complémentaire illisible : {raw_bonus!r}")
            draw_date = (r.get("date") or "").strip()
            prep = prepare_draw(conn, game_id, draw_date, nums, bonus, r.get("source"), today=today,
                                allow_same_date=allow_same_date)
            if prep["draw_date"] in seen and not allow_same_date:
                raise ValidationError(f"Date en double dans le fichier : {prep['draw_date']}")
            seen.add(prep["draw_date"])
            raw_no = (r.get("draw_no") or "").strip()
            try:
                draw_no = int(raw_no) if raw_no else None
            except ValueError:
                raise ValidationError(f"Numéro de tirage illisible : {raw_no!r}")
            prepared.append(dict(prep, source=str(r["source"]).strip(),
                                 source_ref=(r.get("source_ref") or "").strip() or None,
                                 draw_no=draw_no, line=line))
        except ValidationError as e:
            errors.append(f"ligne {line} : {e}")
    if errors:
        raise ValidationError("\n".join(errors))
    if dry_run:
        return prepared
    try:
        for p in prepared:
            add_draw(conn, game_id, p["draw_date"], p["numbers"], p["bonus"], p["source"],
                     source_ref=p["source_ref"], source_draw_no=p["draw_no"], commit=False)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return prepared
