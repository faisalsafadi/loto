import json
import sqlite3

import pytest

from loto_research.db.core import add_correction, add_draw, connect, get_or_create_game, init_db
from loto_research.db.runs import cumulative_test_count, dataset_hash, log_result, start_run


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_db(c)
    yield c
    c.close()


@pytest.fixture
def game_id(conn):
    gid = get_or_create_game(conn, "6/49", 6, 49, 49, True)
    add_draw(conn, gid, "2020-01-04", [1, 2, 3, 4, 5, 6], 7, source="test")
    return gid


def test_fresh_db_applies_all_migrations(conn):
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 3


def test_start_run_records_dataset_state(conn, game_id):
    run_id = start_run(conn, game_id, "quick", {"seed": 42}, git_commit="abc123")
    row = conn.execute("SELECT * FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
    assert row["n_draws"] == 1
    assert row["dataset_hash"] == dataset_hash(conn, game_id)
    assert json.loads(row["config_json"]) == {"seed": 42}
    assert row["git_commit"] == "abc123"


def test_dataset_hash_is_stable_and_changes_with_new_draw(conn, game_id):
    h1 = dataset_hash(conn, game_id)
    assert dataset_hash(conn, game_id) == h1
    add_draw(conn, game_id, "2020-01-08", [7, 8, 9, 10, 11, 12], 13, source="test")
    assert dataset_hash(conn, game_id) != h1


def test_dataset_hash_changes_with_a_correction(conn, game_id):
    h1 = dataset_hash(conn, game_id)
    draw_id = conn.execute("SELECT id FROM draws").fetchone()["id"]
    add_correction(conn, draw_id, "bonus", 7, 8, reason="test", author="test")
    assert dataset_hash(conn, game_id) != h1


def test_cumulative_count_counts_each_test_once_per_dataset_version(conn, game_id):
    r1 = start_run(conn, game_id, "quick", {})
    log_result(conn, r1, "H001", statistic=43.0, p_raw=0.9, method="monte_carlo", family_size=1)
    log_result(conn, r1, "H004", p_raw=0.5, method="fdr_bh", family_size=49)
    # relance sur des données identiques : aucune information nouvelle, le total ne bouge pas
    r2 = start_run(conn, game_id, "quick", {})
    log_result(conn, r2, "H001", p_raw=0.9, family_size=1)
    assert cumulative_test_count(conn, game_id) == 1 + 49
    # après l'ajout d'un tirage, la même hypothèse compte à nouveau
    add_draw(conn, game_id, "2020-01-08", [7, 8, 9, 10, 11, 12], 13, source="test")
    r3 = start_run(conn, game_id, "quick", {})
    log_result(conn, r3, "H001", p_raw=0.9, family_size=1)
    assert cumulative_test_count(conn, game_id) == 1 + 49 + 1


def test_invalid_tag_is_refused(conn, game_id):
    r = start_run(conn, game_id, "quick", {})
    with pytest.raises(sqlite3.DatabaseError):
        log_result(conn, r, "H001", tag="WHATEVER")


def test_runs_and_results_are_append_only(conn, game_id):
    r = start_run(conn, game_id, "quick", {})
    log_result(conn, r, "H001", p_raw=0.5)
    for sql in ("UPDATE analysis_runs SET mode = 'x'", "DELETE FROM analysis_runs",
                "UPDATE test_results SET p_raw = 0", "DELETE FROM test_results"):
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute(sql)
