import json

import pytest

from loto_research.analysis.core import ensure_supported_game
from loto_research.db.core import add_draw, connect, get_or_create_game, init_db
from loto_research.db.loader import load_draws_dataframe


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_db(c)
    yield c
    c.close()


@pytest.fixture
def game_id(conn):
    return get_or_create_game(conn, "6/49", 6, 49, 49, True)


def test_loader_orders_by_date_then_id_and_assigns_chronological_ids(conn, game_id):
    add_draw(conn, game_id, "2020-01-08", [7, 8, 9, 10, 11, 12], 13, source="t", source_draw_no=2)
    add_draw(conn, game_id, "2020-01-04", [1, 2, 3, 4, 5, 6], 7, source="t", source_draw_no=1)
    df = load_draws_dataframe(conn, game_id)
    assert list(df["chronological_id"]) == [1, 2]
    assert list(df["n1"]) == [1, 7]
    assert list(df["draw_number_source"]) == [1, 2]


def test_loader_preserves_source_order_of_numbers(conn, game_id):
    add_draw(conn, game_id, "2020-01-04", [6, 2, 3, 4, 5, 1], 7, source="t")
    df = load_draws_dataframe(conn, game_id)
    assert [int(df.loc[0, f"n{i}"]) for i in range(1, 7)] == [6, 2, 3, 4, 5, 1]


def test_loader_derived_columns(conn, game_id):
    add_draw(conn, game_id, "2020-01-04", [1, 2, 3, 4, 5, 6], 7, source="t")  # un samedi
    df = load_draws_dataframe(conn, game_id)
    assert (int(df.loc[0, "year"]), int(df.loc[0, "month"]), int(df.loc[0, "day"])) == (2020, 1, 4)
    assert str(df.loc[0, "weekday"]) == "sam"


def test_loader_handles_missing_source_draw_number(conn, game_id):
    add_draw(conn, game_id, "2020-01-04", [1, 2, 3, 4, 5, 6], 7, source="t")
    df = load_draws_dataframe(conn, game_id)
    assert df["draw_number_source"].isna().all()


def test_ensure_supported_game_accepts_6_49(conn, game_id):
    game = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    ensure_supported_game(game)


def test_ensure_supported_game_refuses_other_games_explicitly(conn):
    gid = get_or_create_game(conn, "5/39", 5, 39, None)
    game = conn.execute("SELECT * FROM games WHERE id = ?", (gid,)).fetchone()
    with pytest.raises(NotImplementedError, match="pas encore supporté"):
        ensure_supported_game(game)
