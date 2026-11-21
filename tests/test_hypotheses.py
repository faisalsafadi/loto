import random
import sqlite3
from datetime import date, datetime, timedelta, timezone

import pytest

from loto_research.db.core import ValidationError, add_draw, connect, get_or_create_game, init_db
from loto_research.db.hypotheses import available_draws, decide, register_hypothesis, run_confirmatory_test
from loto_research.db.runs import log_result, start_run

REG = datetime(2020, 1, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_db(c)
    yield c
    c.close()


@pytest.fixture
def game_id(conn):
    return get_or_create_game(conn, "6/49", 6, 49, 49, True)


def _add_synthetic(conn, game_id, n, start="2020-01-02", seed=0, first_no=1):
    rng = random.Random(seed)
    d0 = date.fromisoformat(start)
    for i in range(n):
        nums = rng.sample(range(1, 50), 6)
        bonus = rng.choice([v for v in range(1, 50) if v not in nums])
        add_draw(conn, game_id, (d0 + timedelta(days=3 * i)).isoformat(), nums, bonus,
                 source="synthetic", source_draw_no=first_no + i)


def _register(conn, game_id, **kw):
    args = dict(code="H009-v2", h0="rho = 0", h1="rho > 0", test_name="bonus_lag1",
                test_params={"value": 2, "direction": "positive"}, correction="bonferroni",
                family_size=2, kind="PRE_REGISTERED", n_star=200, now=REG)
    args.update(kw)
    return register_hypothesis(conn, game_id, **args)


def _get(conn, hid):
    return conn.execute("SELECT * FROM hypotheses WHERE id = ?", (hid,)).fetchone()


def test_pre_registered_requires_n_star(conn, game_id):
    with pytest.raises(ValidationError, match="n_star"):
        _register(conn, game_id, n_star=None)


@pytest.mark.parametrize("kw", [
    dict(test_name="inconnu", test_params={}),
    dict(test_params={"value": 99, "direction": "positive"}),
    dict(test_params={"value": 2, "direction": "sideways"}),
    dict(test_params={"value": 2, "typo": 1}),
])
def test_unknown_test_and_bad_params_are_refused(conn, game_id, kw):
    with pytest.raises(ValidationError):
        _register(conn, game_id, **kw)


def test_family_size_above_one_requires_a_correction(conn, game_id):
    with pytest.raises(ValidationError):
        _register(conn, game_id, correction="none", family_size=2)


def test_duplicate_code_is_refused(conn, game_id):
    _register(conn, game_id)
    with pytest.raises(ValidationError, match="existe déjà"):
        _register(conn, game_id)


def test_only_strictly_later_draws_are_available(conn, game_id):
    add_draw(conn, game_id, "2019-12-28", [1, 2, 3, 4, 5, 6], 7, source="t")
    add_draw(conn, game_id, "2020-01-01", [7, 8, 9, 10, 11, 12], 13, source="t")  # même jour : exclu
    _add_synthetic(conn, game_id, 3)
    hid = _register(conn, game_id)
    assert available_draws(conn, _get(conn, hid)) == 3


def test_confirmatory_test_is_refused_before_n_star(conn, game_id):
    _add_synthetic(conn, game_id, 50)
    hid = _register(conn, game_id)
    with pytest.raises(ValidationError, match="n_star"):
        run_confirmatory_test(conn, hid)
    assert conn.execute("SELECT COUNT(*) FROM hypothesis_outcomes").fetchone()[0] == 0


@pytest.mark.parametrize("kind", ["POST_HOC", "EXPLORATORY"])
def test_exploratory_and_post_hoc_are_never_confirmatory(conn, game_id, kind):
    _add_synthetic(conn, game_id, 250)
    hid = _register(conn, game_id, kind=kind, n_star=None)
    with pytest.raises(ValidationError, match="jamais testée"):
        run_confirmatory_test(conn, hid)


def test_confirmatory_test_runs_once_on_the_first_n_star_draws(conn, game_id):
    _add_synthetic(conn, game_id, 230)
    hid = _register(conn, game_id)
    r = run_confirmatory_test(conn, hid)
    assert r["n_draws_used"] == 200  # exactement n_star, même si 230 sont disponibles
    assert r["decision"] in ("CONFIRMED", "NOT_CONFIRMED")
    assert 0 <= r["p_value"] <= 1
    assert r["alpha_effective"] == pytest.approx(0.025)  # Bonferroni, famille de 2

    res = conn.execute("SELECT * FROM test_results WHERE hypothesis_id = ?", (hid,)).fetchall()
    assert len(res) == 1 and res[0]["tag"] == "CONFIRMATORY"

    with pytest.raises(ValidationError, match="un seul"):
        run_confirmatory_test(conn, hid)
    assert conn.execute("SELECT COUNT(*) FROM hypothesis_outcomes").fetchone()[0] == 1


def test_hypotheses_and_outcomes_are_append_only(conn, game_id):
    _add_synthetic(conn, game_id, 200)
    hid = _register(conn, game_id)
    run_confirmatory_test(conn, hid)
    for sql in ("UPDATE hypotheses SET n_star = 1", "DELETE FROM hypotheses",
                "UPDATE hypothesis_outcomes SET decision = 'CONFIRMED'", "DELETE FROM hypothesis_outcomes"):
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute(sql)


def test_decide_applies_bonferroni_only_when_declared():
    assert decide(0.02, 0.05, "bonferroni", 2) == ("CONFIRMED", 0.025)
    assert decide(0.03, 0.05, "bonferroni", 2) == ("NOT_CONFIRMED", 0.025)
    assert decide(0.03, 0.05, "none", 1) == ("CONFIRMED", 0.05)


def test_confirmatory_result_without_hypothesis_is_refused_everywhere(conn, game_id):
    run_id = start_run(conn, game_id, "x", {})
    with pytest.raises(ValidationError):
        log_result(conn, run_id, "H", tag="CONFIRMATORY")
    with pytest.raises(sqlite3.DatabaseError):  # même en SQL direct, sans passer par Python
        conn.execute("INSERT INTO test_results (run_id, label, tag) VALUES (?, 'H', 'CONFIRMATORY')", (run_id,))


@pytest.mark.parametrize("test_name, params", [
    ("uniformity_main", {"n_sim": 1000}),
    ("uniformity_bonus", {}),
    ("consecutive_overlap", {"n_perm": 1000}),
])
def test_other_catalog_tests_run_end_to_end(conn, game_id, test_name, params):
    _add_synthetic(conn, game_id, 150)
    hid = _register(conn, game_id, code=f"T-{test_name}", test_name=test_name, test_params=params,
                    correction="none", family_size=1, n_star=150)
    r = run_confirmatory_test(conn, hid)
    assert r["n_draws_used"] == 150 and 0 <= r["p_value"] <= 1
