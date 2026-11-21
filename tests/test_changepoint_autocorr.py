import numpy as np
import pandas as pd
import pytest

from loto_research.temporal.autocorrelation import (
    build_presence_matrix, lag1_autocorrelation_test, per_number_autocorrelation,
)
from loto_research.temporal.changepoint import (
    cusum_permutation_test, cusum_single_changepoint, ruptures_pelt_breakpoints,
)


# ---------- CUSUM ----------

def test_cusum_single_changepoint_hand_verified():
    """[0,0,0,10,10,10] : rupture exacte apres l'indice 2 (mean_before=0, mean_after=10)."""
    res = cusum_single_changepoint([0, 0, 0, 10, 10, 10])
    assert res["changepoint_index"] == 2
    assert res["mean_before"] == pytest.approx(0.0)
    assert res["mean_after"] == pytest.approx(10.0)


def test_cusum_single_changepoint_shift_gives_larger_statistic_than_noise():
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 1, 500)
    shifted = np.concatenate([rng.normal(0, 1, 250), rng.normal(20, 1, 250)])
    assert cusum_single_changepoint(shifted)["cusum_statistic"] > cusum_single_changepoint(noise)["cusum_statistic"] * 5


def test_cusum_permutation_test_reproducible_and_detects_obvious_shift():
    rng = np.random.default_rng(1)
    shifted = np.concatenate([rng.normal(0, 1, 100), rng.normal(10, 1, 100)])
    a = cusum_permutation_test(shifted, n_permutations=200, seed=42, progress=False)
    b = cusum_permutation_test(shifted, n_permutations=200, seed=42, progress=False)
    assert a["p_value_permutation"] == b["p_value_permutation"]
    assert a["p_value_permutation"] < 0.05


def test_cusum_permutation_test_valid_pvalue_range():
    rng = np.random.default_rng(2)
    noise = rng.normal(0, 1, 300)
    res = cusum_permutation_test(noise, n_permutations=500, seed=1, progress=False)
    assert 0 <= res["p_value_permutation"] <= 1


def test_ruptures_pelt_breakpoints_returns_error_or_breakpoints():
    res = ruptures_pelt_breakpoints([0, 0, 0, 10, 10, 10] * 5)
    assert "breakpoints" in res or "error" in res


# ---------- autocorrelation ----------

def test_lag1_autocorrelation_hand_verified_alternating():
    """[1,0,1,0,1,0,1,0] : rho=-0.875, z=-0.875*sqrt(8) (calcul a la main)."""
    res = lag1_autocorrelation_test([1, 0, 1, 0, 1, 0, 1, 0])
    assert res["rho"] == pytest.approx(-0.875)
    assert res["z"] == pytest.approx(-0.875 * (8 ** 0.5))


def test_lag1_autocorrelation_constant_sequence_degenerate():
    res = lag1_autocorrelation_test([1, 1, 1, 1])
    assert res["p_value"] == 1.0


def test_lag1_autocorrelation_detects_strong_persistence():
    """4 blocs de 20 (1,0,1,0) : forte persistance -> rho eleve et p petit."""
    seq = [1] * 20 + [0] * 20 + [1] * 20 + [0] * 20
    res = lag1_autocorrelation_test(seq)
    assert res["rho"] > 0.5
    assert res["p_value"] < 0.01


def test_build_presence_matrix_shape_and_counts():
    df = pd.DataFrame([
        {"n1": 1, "n2": 2, "n3": 3, "n4": 4, "n5": 5, "n6": 6, "chronological_id": 1},
        {"n1": 4, "n2": 5, "n3": 6, "n4": 7, "n5": 8, "n6": 9, "chronological_id": 2},
    ])
    presence = build_presence_matrix(df, [f"n{i}" for i in range(1, 7)])
    assert presence.shape == (2, 49)
    assert presence.sum() == 12
    assert presence[0, 0] == 1   # numero 1 present ligne 0
    assert presence[1, 0] == 0   # numero 1 absent ligne 1


def test_per_number_autocorrelation_covers_49_numbers():
    rng = np.random.default_rng(0)
    rows = [
        {**{f"n{i + 1}": v for i, v in enumerate(rng.choice(np.arange(1, 50), size=6, replace=False))},
         "chronological_id": k + 1}
        for k in range(200)
    ]
    df = pd.DataFrame(rows)
    res = per_number_autocorrelation(df, [f"n{i}" for i in range(1, 7)])
    assert len(res) == 49
    assert res["p_value"].between(0, 1).all()
