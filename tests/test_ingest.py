import json
from datetime import date, timedelta

import pytest

from loto_research.db.core import ValidationError, connect, count_draws, get_or_create_game, init_db
from loto_research.db.hypotheses import register_hypothesis
from loto_research.db.ingest import add_csv, add_new_draw, parse_numbers, prepare_draw

TODAY = date(2026, 11, 15)
GOOD = [5, 12, 23, 31, 40, 44]
HEADER = "date,n1,n2,n3,n4,n5,n6,bonus,source,source_ref,draw_no\n"


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_db(c)
    return c


@pytest.fixture
def game_id(conn):
    return get_or_create_game(conn, "Loto Maroc 6/49", 6, 49, bonus_range=49, bonus_exclusive=True)


def _csv(tmp_path, lines, header=HEADER):
    p = tmp_path / "d.csv"
    p.write_text(header + "".join(line + "\n" for line in lines), encoding="utf-8")
    return p


def test_parse_numbers():
    assert parse_numbers("5 12,23;31  40 44") == [5, 12, 23, 31, 40, 44]
    with pytest.raises(ValidationError):
        parse_numbers("5 12 abc")


def test_valid_draw_is_added_in_given_order(conn, game_id):
    did, _ = add_new_draw(conn, game_id, "2026-11-04", [44, 5, 31, 12, 40, 23], 7, "site officiel", today=TODAY)
    assert count_draws(conn, game_id) == 1
    row = conn.execute("SELECT numbers_json, source FROM draws WHERE id = ?", (did,)).fetchone()
    assert json.loads(row["numbers_json"]) == [44, 5, 31, 12, 40, 23]
    assert row["source"] == "site officiel"


@pytest.mark.parametrize("source", [None, "", "   "])
def test_source_is_required(conn, game_id, source):
    with pytest.raises(ValidationError):
        add_new_draw(conn, game_id, "2026-11-04", GOOD, 7, source, today=TODAY)
    assert count_draws(conn, game_id) == 0


def test_future_date_is_refused(conn, game_id):
    with pytest.raises(ValidationError):
        add_new_draw(conn, game_id, "2026-11-16", GOOD, 7, "src", today=TODAY)
    assert count_draws(conn, game_id) == 0


@pytest.mark.parametrize("draw_date, numbers, bonus", [
    ("2026-11-04", [5, 5, 23, 31, 40, 44], 7),      # doublon
    ("2026-11-04", GOOD, 5),                         # complémentaire parmi les principaux
    ("2026-11-04", [5, 12, 23, 31, 40, 50], 7),      # hors plage
    ("2026-11-04", [5, 12, 23, 31, 40], 7),          # 5 numéros au lieu de 6
    ("2026-13-45", GOOD, 7),                         # date invalide
])
def test_invalid_draws_are_refused(conn, game_id, draw_date, numbers, bonus):
    with pytest.raises(ValidationError):
        add_new_draw(conn, game_id, draw_date, numbers, bonus, "src", today=TODAY)
    assert count_draws(conn, game_id) == 0


def test_same_date_different_draw_is_refused_unless_forced(conn, game_id):
    add_new_draw(conn, game_id, "2026-11-04", GOOD, 7, "src", today=TODAY)
    other = [1, 2, 3, 4, 6, 8]
    with pytest.raises(ValidationError):
        add_new_draw(conn, game_id, "2026-11-04", other, 9, "src", today=TODAY)
    assert count_draws(conn, game_id) == 1
    add_new_draw(conn, game_id, "2026-11-04", other, 9, "src", today=TODAY, allow_same_date=True)
    assert count_draws(conn, game_id) == 2


def test_identical_draw_is_refused_even_if_forced(conn, game_id):
    add_new_draw(conn, game_id, "2026-11-04", GOOD, 7, "src", today=TODAY)
    with pytest.raises(ValidationError):
        add_new_draw(conn, game_id, "2026-11-04", list(reversed(GOOD)), 7, "src", today=TODAY,
                     allow_same_date=True)
    assert count_draws(conn, game_id) == 1


def test_note_for_draws_that_cannot_count_in_prospective_tests(conn, game_id):
    register_hypothesis(conn, game_id, "HX", "h0", "h1", "bonus_lag1", {"value": 2, "direction": "positive"},
                        correction="none", family_size=1, kind="PRE_REGISTERED", n_star=10)
    reg = date.fromisoformat(str(conn.execute("SELECT registered_date FROM hypotheses").fetchone()[0]))
    late = prepare_draw(conn, game_id, reg.isoformat(), GOOD, 7, "src", today=reg + timedelta(days=3))
    assert any("HX" in n for n in late["notes"])
    ok = prepare_draw(conn, game_id, (reg + timedelta(days=1)).isoformat(), GOOD, 7, "src",
                      today=reg + timedelta(days=3))
    assert ok["notes"] == []


def test_csv_adds_all_valid_rows(conn, game_id, tmp_path):
    p = _csv(tmp_path, ["2026-11-02,1,2,3,4,5,6,7,site,http://x,",
                        "2026-11-04,10,11,12,13,14,15,16,site,,123"])
    prepared = add_csv(conn, game_id, p, today=TODAY)
    assert len(prepared) == 2 and count_draws(conn, game_id) == 2


def test_csv_is_all_or_nothing(conn, game_id, tmp_path):
    p = _csv(tmp_path, ["2026-11-02,1,2,3,4,5,6,7,site,,",
                        "2026-11-04,10,10,12,13,14,15,16,site,,",
                        "2026-11-06,20,21,22,23,24,25,26,site,,"])
    with pytest.raises(ValidationError) as e:
        add_csv(conn, game_id, p, today=TODAY)
    assert "ligne 3" in str(e.value)
    assert count_draws(conn, game_id) == 0


def test_csv_duplicate_dates_in_file_are_refused(conn, game_id, tmp_path):
    p = _csv(tmp_path, ["2026-11-02,1,2,3,4,5,6,7,site,,",
                        "2026-11-02,10,11,12,13,14,15,16,site,,"])
    with pytest.raises(ValidationError):
        add_csv(conn, game_id, p, today=TODAY)
    assert count_draws(conn, game_id) == 0


def test_csv_missing_column_is_refused(conn, game_id, tmp_path):
    p = _csv(tmp_path, ["2026-11-02,1,2,3,4,5,6,site"], header="date,n1,n2,n3,n4,n5,n6,source\n")
    with pytest.raises(ValidationError) as e:
        add_csv(conn, game_id, p, today=TODAY)
    assert "Colonnes manquantes" in str(e.value)


def test_csv_dry_run_writes_nothing(conn, game_id, tmp_path):
    p = _csv(tmp_path, ["2026-11-02,1,2,3,4,5,6,7,site,,"])
    prepared = add_csv(conn, game_id, p, today=TODAY, dry_run=True)
    assert len(prepared) == 1 and count_draws(conn, game_id) == 0
