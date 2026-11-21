import numpy as np

from loto_research.models.metrics import bootstrap_mean_diff_ci


def test_bootstrap_ci_point_estimate_matches_simple_mean_diff():
    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    b = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
    res = bootstrap_mean_diff_ci(a, b, n_boot=500, seed=0)
    assert res["point_estimate"] == pytest_approx(a.mean() - b.mean())


def pytest_approx(x, tol=1e-9):
    class _Approx:
        def __eq__(self, other):
            return abs(other - x) < tol
    return _Approx()


def test_bootstrap_ci_is_reproducible_with_same_seed():
    rng = np.random.default_rng(0)
    a = rng.normal(1.0, 0.1, size=200)
    b = rng.normal(0.0, 0.1, size=200)
    res1 = bootstrap_mean_diff_ci(a, b, n_boot=300, seed=7)
    res2 = bootstrap_mean_diff_ci(a, b, n_boot=300, seed=7)
    assert res1 == res2


def test_bootstrap_ci_brackets_a_clear_positive_difference():
    rng = np.random.default_rng(1)
    a = rng.normal(1.0, 0.05, size=300)
    b = rng.normal(0.0, 0.05, size=300)
    res = bootstrap_mean_diff_ci(a, b, n_boot=1000, seed=3)
    assert res["ci_lower"] > 0  # difference clairement positive, l'IC ne doit pas contenir 0
    assert res["ci_lower"] < res["point_estimate"] < res["ci_upper"]


def test_bootstrap_ci_contains_zero_when_no_real_difference():
    rng = np.random.default_rng(2)
    a = rng.normal(0.0, 0.1, size=300)
    b = rng.normal(0.0, 0.1, size=300)
    res = bootstrap_mean_diff_ci(a, b, n_boot=1000, seed=5)
    assert res["ci_lower"] < 0 < res["ci_upper"]
