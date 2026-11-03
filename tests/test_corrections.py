import json
from datetime import date

import pytest

from loto_research.db.core import ValidationError, add_draw, connect, get_or_create_game, init_db
from loto_research.db.corrections import (apply_corrections, correct_draw, list_corrections, parse_changes,
                                          plan_correction)
from loto_research.db.ingest import prepare_draw
from loto_research.db.loader import load_draws_dataframe

TODAY = date(2026, 11, 15)
DRAW = [44, 5, 31, 12, 40, 23]


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_db(c)
    return c


@pytest.fixture
def game_id(conn):
    return get_or_create_game(conn, "Loto Maroc 6/49", 6, 49, bonus_range=49, bonus_exclusive=True)


@pytest.fixture
def draw_id(conn, game_id):
    return add_draw(conn, game_id, "2026-11-04", DRAW, 7, "src")


def _row(conn, draw_id):
    return conn.execute("SELECT numbers_json, bonus FROM draws WHERE id = ?", (draw_id,)).fetchone()


def test_parse_changes():
    assert parse_changes(["n3=17", "bonus=9"]) == {"n3": 17, "bonus": 9}
    for bad in (["n3"], ["n3=abc"], ["n3=1", "n3=2"]):
        with pytest.raises(ValidationError):
            parse_changes(bad)


def test_apply_corrections_keeps_order_and_bonus():
    nums, b = apply_corrections(DRAW, 7, [("n3", "17"), ("bonus", "9")])
    assert nums == [44, 5, 17, 12, 40, 23] and b == 9
    with pytest.raises(ValidationError):
        apply_corrections(DRAW, 7, [("n9", "1")])
    with pytest.raises(ValidationError):
        apply_corrections(DRAW, 7, [("draw_date", "2026-01-01")])


def test_plan_reads_old_value_from_the_database(conn, draw_id):
    plan = plan_correction(conn, draw_id, {"n3": 17})
    assert plan["rows"] == [("n3", 31, 17)]
    assert plan["before"][0] == DRAW and plan["after"][0] == [44, 5, 17, 12, 40, 23]


def test_correction_leaves_the_original_and_is_applied_by_the_loader(conn, game_id, draw_id):
    correct_draw(conn, draw_id, {"n3": 17}, "faute de frappe", "faisal")
    row = _row(conn, draw_id)
    assert json.loads(row["numbers_json"]) == DRAW and row["bonus"] == 7        # origine intacte
    df = load_draws_dataframe(conn, game_id)
    assert int(df.loc[0, "n3"]) == 17 and int(df.loc[0, "n1"]) == 44
    assert len(list_corrections(conn, game_id)) == 1


def test_invalid_final_state_is_refused_and_nothing_is_written(conn, game_id, draw_id):
    with pytest.raises(ValidationError):
        correct_draw(conn, draw_id, {"n3": 5}, "test", "faisal")          # 5 est déjà en position 2
    with pytest.raises(ValidationError):
        correct_draw(conn, draw_id, {"bonus": 44}, "test", "faisal")      # complémentaire parmi les principaux
    with pytest.raises(ValidationError):
        correct_draw(conn, draw_id, {"n1": 50}, "test", "faisal")         # hors plage
    assert list_corrections(conn, game_id) == []


def test_multi_field_correction_is_validated_on_the_final_state(conn, game_id, draw_id):
    # permutation de deux numéros : chaque changement isolé serait un doublon, l'état final est valide
    correct_draw(conn, draw_id, {"n1": 5, "n2": 44}, "numéros permutés", "faisal")
    df = load_draws_dataframe(conn, game_id)
    assert int(df.loc[0, "n1"]) == 5 and int(df.loc[0, "n2"]) == 44
    assert len(list_corrections(conn, game_id)) == 2


def test_second_correction_records_the_effective_old_value(conn, game_id, draw_id):
    correct_draw(conn, draw_id, {"n3": 17}, "première", "faisal")
    correct_draw(conn, draw_id, {"n3": 18}, "seconde", "faisal")
    rows = list_corrections(conn, game_id)
    assert [(r["old_value"], r["new_value"]) for r in rows] == [("31", "17"), ("17", "18")]
    assert int(load_draws_dataframe(conn, game_id).loc[0, "n3"]) == 18


def test_noop_unknown_field_date_and_unknown_draw_are_refused(conn, game_id, draw_id):
    with pytest.raises(ValidationError):
        plan_correction(conn, draw_id, {"n1": 44})                         # déjà 44
    with pytest.raises(ValidationError):
        plan_correction(conn, draw_id, {"draw_date": 20261105})            # la date n'est pas corrigeable
    with pytest.raises(ValidationError):
        plan_correction(conn, draw_id, {"n7": 3})
    with pytest.raises(ValidationError):
        plan_correction(conn, draw_id, {})
    with pytest.raises(ValidationError):
        plan_correction(conn, 9999, {"n1": 1})


@pytest.mark.parametrize("reason, author", [("", "faisal"), ("raison", ""), (None, "faisal"), ("raison", "  ")])
def test_reason_and_author_are_required(conn, game_id, draw_id, reason, author):
    with pytest.raises(ValidationError):
        correct_draw(conn, draw_id, {"n3": 17}, reason, author)
    assert list_corrections(conn, game_id) == []


def test_same_date_check_uses_the_corrected_draw(conn, game_id):
    # saisie erronée, puis corrigée : le tirage correct ne peut pas être ajouté une seconde fois
    did = add_draw(conn, game_id, "2026-11-04", [44, 5, 31, 12, 40, 22], 7, "src")
    correct_draw(conn, did, {"n6": 23}, "faute de frappe", "faisal")
    with pytest.raises(ValidationError) as e:
        prepare_draw(conn, game_id, "2026-11-04", DRAW, 7, "src", today=TODAY)
    assert "déjà dans la base" in str(e.value)
