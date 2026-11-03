import sqlite3
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from loto_research.dashboard import data as D
from loto_research.db.core import add_draw, connect, get_or_create_game, init_db
from loto_research.db.hypotheses import register_hypothesis
from loto_research.db.loader import load_draws_dataframe
from loto_research.simulation import bench as bench_mod

FORBIDDEN_WORDS = ["chaud", "froid", "en retard", "favori", "gagnant", "à jouer"]
WRITE_TOKENS = ["INSERT ", "UPDATE ", "DELETE ", "CREATE ", "DROP ", ".commit(", "executescript"]


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "t.sqlite"
    conn = connect(path)
    init_db(conn)
    gid = get_or_create_game(conn, "Loto Maroc 6/49", 6, 49, bonus_range=49, bonus_exclusive=True)
    for i in range(30):
        nums = [(3 * i + 7 * j) % 49 + 1 for j in range(6)]
        bonus = (3 * i + 3) % 49 + 1
        add_draw(conn, gid, (date(2020, 1, 1) + timedelta(days=3 * i)).isoformat(), nums, bonus, "src")
    conn.close()
    return path, gid


def test_banner_text():
    assert D.banner_text(49, 6) == "Toute combinaison a la même probabilité : 1 sur 13 983 816."


def test_readonly_connection_refuses_writes_and_never_creates_a_file(db, tmp_path):
    path, _ = db
    ro = D.open_readonly(path)
    with pytest.raises(sqlite3.OperationalError):
        ro.execute("CREATE TABLE x (a)")
    with pytest.raises(sqlite3.OperationalError):
        D.open_readonly(tmp_path / "absent.sqlite")
    assert not (tmp_path / "absent.sqlite").exists()


def test_periods_are_the_preregistered_blocks():
    bounds = [b for b in D.PERIODS.values() if b is not None]
    assert bounds == [(2001, 2005), (2006, 2010), (2011, 2015), (2016, 2020), (2021, 2026)]
    assert list(D.PERIODS)[0] == "Historique complet" and len(D.PERIODS) == 6


def test_frequency_bands_are_symmetric_and_nested():
    n = 3155
    tab = D.frequency_from_counts(np.full(49, n * 6 / 49), n)
    exp = n * 6 / 49
    assert len(tab) == 49 and tab["numero"].tolist() == list(range(1, 50))
    assert np.allclose(tab["z"], 0)
    assert np.allclose(tab["lo95"] + tab["hi95"], 2 * exp)
    assert (tab["hiB"] > tab["hi95"]).all() and (tab["loB"] < tab["lo95"]).all()
    assert D.outside_counts(tab) == (0, 0)


def test_a_large_deviation_is_flagged_by_both_bands():
    counts = np.full(49, 386)
    counts[0] = 600
    tab = D.frequency_from_counts(counts, 3155)
    assert bool(tab.loc[0, "outside95"]) and bool(tab.loc[0, "outsideB"])
    assert D.outside_counts(tab) == (1, 1)


def test_expected_outside_counts():
    exp95, expb = D.expected_outside(49)
    assert exp95 == pytest.approx(2.45) and expb == pytest.approx(0.05)


def test_simulation_is_reproducible_and_conserves_totals():
    a = D.simulate_counts(500, 42)
    assert a.shape == (49,) and int(a.sum()) == 6 * 500
    assert np.array_equal(a, D.simulate_counts(500, 42))
    assert not np.array_equal(a, D.simulate_counts(500, 43))


def test_period_filter_and_counts(db):
    path, gid = db
    ro = D.open_readonly(path)
    df = load_draws_dataframe(ro, gid)
    assert len(D.filter_period(df, "Historique complet")) == 30
    assert len(D.filter_period(df, "2016–2020")) == 30
    assert len(D.filter_period(df, "2021–2026")) == 0
    assert int(D.counts_from_df(df).sum()) == 6 * 30
    assert len(D.frequency_table(df)) == 49
    assert len(D.last_draws(df, 5)) == 5 and len(D.draws_per_year(df)) == 1


def test_tables_are_empty_but_well_formed_on_a_fresh_database(db):
    path, gid = db
    ro = D.open_readonly(path)
    assert D.runs_table(ro, gid).empty
    assert D.results_table(ro, gid).empty
    assert D.hypotheses_progress(ro, gid).empty
    assert D.corrections_table(ro, gid).empty
    assert D.bench_results(ro).empty
    assert D.ingestion_by_source(ro, gid)["tirages"].tolist() == [30]


def test_hypothesis_progress_is_read_from_the_registry(db):
    path, gid = db
    w = connect(path)
    register_hypothesis(w, gid, "HX", "h0", "h1", "bonus_lag1", {"value": 2, "direction": "positive"},
                        correction="none", family_size=1, kind="PRE_REGISTERED", n_star=10)
    w.close()
    hp = D.hypotheses_progress(D.open_readonly(path), gid)
    assert hp.loc[0, "code"] == "HX" and int(hp.loc[0, "n_star"]) == 10
    assert int(hp.loc[0, "tirages_posterieurs"]) == 0 and hp.loc[0, "decision"] is None


def test_bench_results_are_read_back(db):
    path, _ = db
    w = connect(path)
    rows = [{"n": 100, "scenario": "null", "level": 0.0, "reps": 10, "test": "uniformity_global",
             "rejections": 1, "rate": 0.1, "ci_low": 0.0, "ci_high": 0.4}]
    bench_mod.store_run(w, 42, "bench_m4", "abc", {}, rows)
    w.close()
    out = D.bench_results(D.open_readonly(path))
    assert len(out) == 1 and out.loc[0, "scenario"] == "null"


def test_dashboard_sources_contain_no_forbidden_wording():
    folder = Path(D.__file__).parent
    for name in ("app.py", "data.py"):
        text = (folder / name).read_text(encoding="utf-8").lower()
        for word in FORBIDDEN_WORDS:
            assert word not in text, f"{name} contient {word!r}"


def test_dashboard_sources_never_write_and_always_show_the_banner():
    folder = Path(D.__file__).parent
    for name in ("app.py", "data.py"):
        text = (folder / name).read_text(encoding="utf-8")
        for token in WRITE_TOKENS:
            assert token not in text, f"{name} contient {token!r}"
    assert "st.warning(D.banner_text" in (folder / "app.py").read_text(encoding="utf-8")
