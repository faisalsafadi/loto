import sqlite3

import numpy as np
import pytest

from loto_research.simulation import bench as b
from loto_research.simulation import bench_config as cfg
from loto_research.simulation import generators as g

P1 = 6 / 49


def rng(seed=0):
    return np.random.default_rng(seed)


def test_config_hash_is_stable():
    assert cfg.config_hash() == cfg.config_hash() and len(cfg.config_hash()) == 64


def test_weight_identity_and_roundtrip():
    assert g.weight_for_inclusion(P1) == pytest.approx(1.0)
    for d in (0.1, 0.2, 0.3):
        w = g.weight_for_inclusion(P1 * (1 + d))
        assert g.inclusion_probability(w) == pytest.approx(P1 * (1 + d))


def test_null_rows_have_exactly_six_distinct():
    x = g.gen_null(rng(), 5, 200)
    assert (x.sum(axis=2) == 6).all()


def test_number_bias_marginal():
    x = g.gen_number(rng(1), 20, 1000, 0.3)
    assert (x.sum(axis=2) == 6).all()
    freq = x[:, :, cfg.SPECIAL_NUMBER - 1].mean()
    exp = P1 * 1.3
    se = np.sqrt(exp * (1 - exp) / 20000)
    assert abs(freq - exp) < 4 * se


def test_pair_bias_joint_frequency():
    x = g.gen_pair(rng(2), 20, 1000, 3.0)
    assert (x.sum(axis=2) == 6).all()
    a, c = cfg.SPECIAL_PAIR
    joint = (x[:, :, a - 1] & x[:, :, c - 1]).mean()
    exp = 3.0 * 30 / 2352
    se = np.sqrt(exp * (1 - exp) / 20000)
    assert abs(joint - exp) < 4 * se


def test_dependence_raises_overlap():
    x = g.gen_dependence(rng(3), 10, 1000, 0.1)
    assert (x.sum(axis=2) == 6).all()
    ov = (x[:, 1:] & x[:, :-1]).sum(axis=2).mean()
    assert ov > 1.0          # attendu ~1,2 contre 0,73 sous H0
    assert np.abs(x.mean(axis=(0, 1)) - P1).max() < 0.03


def test_rupture_affects_second_half_only():
    x = g.gen_rupture(rng(4), 20, 1000, 0.3)
    i = cfg.SPECIAL_NUMBER - 1
    se = np.sqrt(P1 * (1 - P1) / 10000)
    assert abs(x[:, :500, i].mean() - P1) < 4 * se
    assert abs(x[:, 500:, i].mean() - 1.3 * P1) < 4 * se * 1.3


def test_unknown_scenario_is_refused():
    with pytest.raises(ValueError):
        g.generate("nope", 0.0, rng(), 1, 10)


def test_stats_shapes_and_values():
    x = g.gen_null(rng(5), 4, 100)
    s = b.stats_from_presence(x)
    assert s["counts"].shape == (4, 49)
    assert s["counts"].sum(axis=1).tolist() == [600] * 4
    e = 100 * 6 / 49
    assert np.allclose(s["chi2"], (((s["counts"] - e) ** 2) / e).sum(axis=1))
    d = x[0]
    manual = np.mean([(d[t] & d[t - 1]).sum() for t in range(1, 100)])
    assert s["overlap"][0] == pytest.approx(manual)


def test_p_value_helpers():
    null = np.arange(1.0, 101.0)
    assert b.p_upper(null, np.array([101.0]))[0] == pytest.approx(1 / 101)
    assert b.p_upper(null, np.array([0.0]))[0] == pytest.approx(1.0)
    assert b.p_two_sided(null, np.array([50.5]))[0] == 1.0
    assert b.p_two_sided(null, np.array([0.0]))[0] == pytest.approx(2 / 101)


def test_per_number_min_p():
    n = 3155
    ok = np.full((1, 49), 386)
    assert b.per_number_min_p(ok, n)[0] > 0.5
    bad = ok.copy()
    bad[0, 0] = 250
    assert b.per_number_min_p(bad, n)[0] < 1e-6


def test_wilson_and_min_detectable():
    lo, hi = b.wilson(50, 100)
    assert lo < 0.5 < hi
    assert b.wilson(0, 100)[0] == pytest.approx(0.0, abs=1e-12)
    v, _ = b.min_detectable([0.1, 0.2, 0.3], [0.1, 0.5, 0.9])
    assert v == pytest.approx(0.275)
    v, note = b.min_detectable([0.1, 0.2, 0.3], [0.9, 1.0, 1.0])
    assert v == 0.1 and "plus bas" in note
    v, note = b.min_detectable([0.1, 0.2, 0.3], [0.1, 0.2, 0.3])
    assert v is None


def test_calibration_is_reproducible_and_sorted():
    c1 = b.calibrate(100, 400, cache_dir=None)
    c2 = b.calibrate(100, 400, cache_dir=None)
    for k in ("chi2", "overlap", "homog"):
        assert np.array_equal(c1[k], c2[k])
        assert np.all(np.diff(c1[k]) >= 0)


def test_cell_is_reproducible():
    cal = b.calibrate(100, 300, cache_dir=None)
    assert b.run_cell("number", 0.2, 100, 25, cal) == b.run_cell("number", 0.2, 100, 25, cal)


def test_null_false_positive_rate_is_close_to_nominal():
    cal = b.calibrate(200, 3000, cache_dir=None)
    rows = {r["test"]: r for r in b.run_cell("null", 0.0, 200, 400, cal)}
    for t in ("uniformity_global", "consecutive_overlap", "half_homogeneity"):
        assert 0.01 <= rows[t]["rate"] <= 0.12
    assert rows["per_number_holm"]["rate"] <= 0.12


def test_strong_dependence_is_detected():
    cal = b.calibrate(300, 2000, cache_dir=None)
    rows = {r["test"]: r for r in b.run_cell("dependence", 0.1, 300, 50, cal)}
    assert rows["consecutive_overlap"]["rate"] >= 0.9


def test_store_is_append_only(tmp_path):
    conn = sqlite3.connect(tmp_path / "x.sqlite")
    rows = [{"n": 100, "scenario": "null", "level": 0.0, "reps": 10, "test": "uniformity_global",
             "rejections": 1, "rate": 0.1, "ci_low": 0.0, "ci_high": 0.4}]
    b.store_run(conn, 42, "bench_m4", "abc", {"a": 1}, rows)
    assert conn.execute("SELECT COUNT(*) FROM bench_cells").fetchone()[0] == 1
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE bench_cells SET reps = 1")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM simulated_runs")


def test_report_builds():
    cal = b.calibrate(100, 300, cache_dir=None)
    rows = b.run_cell("null", 0.0, 100, 30, cal) + b.run_cell("number", 0.2, 100, 30, cal)
    text = b.build_report(rows, {"config_hash": "x", "n_calibration": 300})
    assert "Faux positifs" in text and "Biais minimal" in text
