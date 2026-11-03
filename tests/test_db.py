import sqlite3

import pytest

from loto_research.db.core import (
    ValidationError, add_correction, add_draw, connect, count_draws, get_or_create_game, init_db,
)


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_db(c)
    yield c
    c.close()


@pytest.fixture
def game_id(conn):
    return get_or_create_game(conn, "6/49", k=6, n_max=49, bonus_range=49, bonus_exclusive=True)


def _add(conn, game_id, **kw):
    args = dict(draw_date="2020-01-04", numbers=[1, 2, 3, 4, 5, 6], bonus=7, source="test")
    args.update(kw)
    return add_draw(conn, game_id, args.pop("draw_date"), args.pop("numbers"), args.pop("bonus"), **args)


def test_get_or_create_game_is_idempotent(conn):
    a = get_or_create_game(conn, "6/49", 6, 49, 49, True)
    b = get_or_create_game(conn, "6/49", 6, 49, 49, True)
    assert a == b


def test_game_with_different_config_is_refused(conn):
    get_or_create_game(conn, "6/49", 6, 49, 49, True)
    with pytest.raises(ValidationError):
        get_or_create_game(conn, "6/49", 5, 39, 39, True)


def test_valid_draw_is_inserted_and_order_is_preserved(conn, game_id):
    _add(conn, game_id, numbers=[6, 2, 3, 4, 5, 1])
    row = conn.execute("SELECT numbers_json FROM draws").fetchone()
    assert row["numbers_json"] == "[6, 2, 3, 4, 5, 1]"  # ordre source conservé, pas de tri silencieux
    assert count_draws(conn, game_id) == 1


@pytest.mark.parametrize("kwargs", [
    dict(numbers=[1, 2, 3, 4, 5]),                 # trop peu
    dict(numbers=[1, 2, 3, 4, 5, 5]),              # doublon
    dict(numbers=[0, 2, 3, 4, 5, 6]),              # hors plage (bas)
    dict(numbers=[1, 2, 3, 4, 5, 50]),             # hors plage (haut)
    dict(numbers=[1, 2, 3, 4, 5, 6.5]),            # non entier
    dict(bonus=3),                                 # complémentaire déjà dans les principaux
    dict(bonus=0),                                 # complémentaire hors plage
    dict(bonus=None),                              # complémentaire manquant
    dict(draw_date="2020-13-45"),                  # date invalide
    dict(draw_date="04/01/2020"),                  # mauvais format
])
def test_invalid_draws_are_refused_and_not_inserted(conn, game_id, kwargs):
    with pytest.raises(ValidationError):
        _add(conn, game_id, **kwargs)
    assert count_draws(conn, game_id) == 0


def test_duplicate_draw_is_refused(conn, game_id):
    _add(conn, game_id)
    with pytest.raises(ValidationError):
        _add(conn, game_id)
    assert count_draws(conn, game_id) == 1


def test_update_and_delete_on_draws_are_blocked(conn, game_id):
    _add(conn, game_id)
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE draws SET bonus = 9")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM draws")
    assert count_draws(conn, game_id) == 1


def test_correction_is_recorded_without_touching_the_draw(conn, game_id):
    draw_id = _add(conn, game_id)
    add_correction(conn, draw_id, "bonus", 7, 8, reason="erreur de saisie constatée", author="test")
    assert conn.execute("SELECT bonus FROM draws WHERE id = ?", (draw_id,)).fetchone()["bonus"] == 7
    assert conn.execute("SELECT COUNT(*) FROM draw_corrections").fetchone()[0] == 1


def test_correction_requires_reason_and_author(conn, game_id):
    draw_id = _add(conn, game_id)
    with pytest.raises(ValidationError):
        add_correction(conn, draw_id, "bonus", 7, 8, reason="", author="test")
    with pytest.raises(ValidationError):
        add_correction(conn, draw_id, "bonus", 7, 8, reason="x", author="")


def test_game_without_bonus_refuses_a_bonus(conn):
    gid = get_or_create_game(conn, "5/39", k=5, n_max=39, bonus_range=None)
    with pytest.raises(ValidationError):
        add_draw(conn, gid, "2020-01-04", [1, 2, 3, 4, 5], 6, source="test")
    add_draw(conn, gid, "2020-01-04", [1, 2, 3, 4, 5], None, source="test")
    assert count_draws(conn, gid) == 1
