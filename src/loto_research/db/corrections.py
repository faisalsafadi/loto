"""Corrections de tirages (SPEC_V2 §5). Le tirage d'origine n'est JAMAIS modifié : une correction est une
ligne ajoutée (champ, ancienne valeur, nouvelle valeur, raison, auteur, date) que le chargeur applique.
Seuls les numéros et le complémentaire sont corrigeables : une date corrigée pourrait faire entrer ou
sortir un tirage d'un test pré-enregistré, ce risque d'intégrité est exclu."""
import json
import re
from datetime import datetime, timezone

from loto_research.db.core import ValidationError, validate_draw

_NUM_FIELD = re.compile(r"n(\d+)")


def correctable_fields(game):
    fields = [f"n{j}" for j in range(1, game["k"] + 1)]
    if game["bonus_range"] is not None:
        fields.append("bonus")
    return fields


def load_corrections(conn, game_id):
    """{draw_id: [(field, new_value), ...]} dans l'ordre d'enregistrement des corrections."""
    out = {}
    for r in conn.execute(
        "SELECT c.draw_id, c.field, c.new_value FROM draw_corrections c "
        "JOIN draws d ON d.id = c.draw_id WHERE d.game_id = ? ORDER BY c.id", (game_id,)
    ):
        out.setdefault(r["draw_id"], []).append((r["field"], r["new_value"]))
    return out


def apply_corrections(numbers, bonus, corrections):
    """Applique des corrections (field, new_value) à un tirage ; l'ordre des numéros est conservé."""
    nums = list(numbers)
    b = bonus
    for field, new in corrections:
        try:
            value = int(new)
        except (TypeError, ValueError):
            raise ValidationError(f"Correction illisible : {field}={new!r}")
        if field == "bonus":
            b = value
            continue
        m = _NUM_FIELD.fullmatch(field)
        if m is None or not (1 <= int(m.group(1)) <= len(nums)):
            raise ValidationError(f"Champ de correction non applicable : {field!r}")
        nums[int(m.group(1)) - 1] = value
    return nums, b


def parse_changes(items):
    """['n3=17', 'bonus=9'] -> {'n3': 17, 'bonus': 9}"""
    changes = {}
    for item in items:
        if "=" not in item:
            raise ValidationError(f"Changement illisible : {item!r} (attendu : champ=valeur, ex. n3=17)")
        field, value = (s.strip() for s in item.split("=", 1))
        if field in changes:
            raise ValidationError(f"Champ répété : {field}")
        try:
            changes[field] = int(value)
        except ValueError:
            raise ValidationError(f"Valeur illisible pour {field} : {value!r}")
    return changes


def _get_draw(conn, draw_id):
    draw = conn.execute("SELECT * FROM draws WHERE id = ?", (draw_id,)).fetchone()
    if draw is None:
        raise ValidationError(f"Tirage inconnu : {draw_id}")
    game = conn.execute("SELECT * FROM games WHERE id = ?", (draw["game_id"],)).fetchone()
    corr = [(r["field"], r["new_value"]) for r in conn.execute(
        "SELECT field, new_value FROM draw_corrections WHERE draw_id = ? ORDER BY id", (draw_id,))]
    nums, bonus = apply_corrections(json.loads(draw["numbers_json"]), draw["bonus"], corr)
    return draw, game, nums, bonus


def plan_correction(conn, draw_id, changes):
    """Valide une correction SANS rien écrire. Le tirage résultant (après TOUS les changements) doit rester
    valide ; les valeurs anciennes sont lues dans la base, jamais saisies."""
    draw, game, nums, bonus = _get_draw(conn, draw_id)
    if not changes:
        raise ValidationError("Aucun changement demandé.")
    allowed = correctable_fields(game)
    bad = [f for f in changes if f not in allowed]
    if bad:
        raise ValidationError(f"Champ(s) non corrigeable(s) : {bad}. Autorisés : {allowed} "
                              f"(la date n'est pas corrigeable).")
    new_nums, new_bonus = list(nums), bonus
    rows = []
    for field, value in changes.items():
        if field == "bonus":
            old = bonus
            new_bonus = value
        else:
            idx = int(field[1:]) - 1
            old = nums[idx]
            new_nums[idx] = value
        if old == value:
            raise ValidationError(f"{field} vaut déjà {value} : rien à corriger.")
        rows.append((field, old, value))
    validate_draw(game, draw["draw_date"], new_nums, new_bonus)
    return {"game_id": draw["game_id"], "draw_date": draw["draw_date"], "before": (nums, bonus),
            "after": (new_nums, new_bonus), "rows": rows}


def correct_draw(conn, draw_id, changes, reason, author):
    """Enregistre une correction (ajout seul), atomiquement : tous les champs ou aucun."""
    if not reason or not str(reason).strip() or not author or not str(author).strip():
        raise ValidationError("Une correction exige une raison et un auteur")
    plan = plan_correction(conn, draw_id, changes)
    now = datetime.now(timezone.utc).isoformat()
    try:
        for field, old, new in plan["rows"]:
            conn.execute(
                "INSERT INTO draw_corrections (draw_id, field, old_value, new_value, reason, author, at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (draw_id, field, str(old), str(new), str(reason).strip(), str(author).strip(), now))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return plan


def list_corrections(conn, game_id):
    return conn.execute(
        "SELECT c.id, c.draw_id, d.draw_date, c.field, c.old_value, c.new_value, c.reason, c.author, c.at "
        "FROM draw_corrections c JOIN draws d ON d.id = c.draw_id WHERE d.game_id = ? ORDER BY c.id",
        (game_id,)).fetchall()
