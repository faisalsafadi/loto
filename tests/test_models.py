import numpy as np
import pandas as pd
import pytest

from loto_research.models.baselines import frequency_baseline_predictions, random_baseline_predictions
from loto_research.models.logistic import prepare_features
from loto_research.models.metrics import (
    brier_per_draw, calibration_table, log_loss_per_draw, mean_probability_drawn_vs_not,
    paired_wilcoxon, top_k_hits_per_draw,
)

NUMBER_COLUMNS = [f"n{i}" for i in range(1, 7)]


def _row(values, chronological_id):
    return {**{f"n{i + 1}": v for i, v in enumerate(values)}, "chronological_id": chronological_id}


def test_random_baseline_is_exactly_6_over_49():
    p = random_baseline_predictions(5)
    assert p.shape == (5, 49)
    np.testing.assert_allclose(p, 6 / 49)


def test_frequency_baseline_hand_verified():
    """3 tirages, numero 1 present au tirage 1 et 3, absent au tirage 2. alpha=10."""
    df = pd.DataFrame([
        _row([1, 2, 3, 4, 5, 6], 1),
        _row([7, 8, 9, 10, 11, 12], 2),
        _row([1, 13, 14, 15, 16, 17], 3),
    ])
    p = frequency_baseline_predictions(df, alpha=10.0)
    number1_idx = 0  # numero 1 -> colonne 0
    assert p[0, number1_idx] == pytest.approx(6 / 49)  # t=0 : aucun historique
    assert p[1, number1_idx] == pytest.approx((1 + 10 * 6 / 49) / 11)  # t=1 : vu 1 fois sur 1 tirage passe
    assert p[2, number1_idx] == pytest.approx((1 + 10 * 6 / 49) / 12)  # t=2 : vu 1 fois sur 2 tirages passes


def test_log_loss_and_brier_hand_verified():
    target = np.array([[1.0, 0.0]])
    p_hat = np.array([[0.8, 0.3]])
    expected_logloss = (-np.log(0.8) + -np.log(0.7)) / 2
    assert log_loss_per_draw(target, p_hat)[0] == pytest.approx(expected_logloss, abs=1e-9)
    expected_brier = ((0.8 - 1) ** 2 + (0.3 - 0) ** 2) / 2
    assert brier_per_draw(target, p_hat)[0] == pytest.approx(expected_brier)


def test_top_k_hits_hand_verified():
    target = np.array([[1, 0, 1, 0, 0]])
    p_hat = np.array([[0.9, 0.1, 0.8, 0.05, 0.05]])
    hits = top_k_hits_per_draw(target, p_hat, k=2)
    assert hits[0] == 2  # les 2 numeros de plus forte proba (idx 0 et 2) sont bien les 2 tires


def test_top_k_hits_tie_break_is_deterministic_by_ascending_index():
    target = np.array([[0, 1, 0, 0, 0]])
    p_hat = np.array([[0.5, 0.5, 0.5, 0.1, 0.1]])  # ex-aequo sur idx 0,1,2
    hits = top_k_hits_per_draw(target, p_hat, k=2)
    # tri par indice croissant parmi les ex-aequo -> top2 = [0,1] -> hits = target[0]+target[1] = 0+1
    assert hits[0] == 1


def test_mean_probability_drawn_vs_not():
    target = np.array([[1, 0], [0, 1]])
    p_hat = np.array([[0.8, 0.2], [0.3, 0.7]])
    res = mean_probability_drawn_vs_not(target, p_hat)
    assert res["mean_p_drawn"] == pytest.approx((0.8 + 0.7) / 2)
    assert res["mean_p_not_drawn"] == pytest.approx((0.2 + 0.3) / 2)


def test_calibration_table_bins_sum_to_total_observations():
    rng = np.random.default_rng(0)
    target = rng.integers(0, 2, size=(20, 49)).astype(float)
    p_hat = rng.uniform(0, 1, size=(20, 49))
    table = calibration_table(target, p_hat, n_bins=10)
    assert table["n"].sum() == 20 * 49


def test_paired_wilcoxon_identical_arrays_gives_p_value_1():
    a = np.array([1.0, 2.0, 3.0, 4.0])
    res = paired_wilcoxon(a, a)
    assert res["p_value"] == 1.0
    assert res["mean_diff"] == 0.0


def test_paired_wilcoxon_detects_a_clear_systematic_difference():
    rng = np.random.default_rng(0)
    a = rng.normal(loc=1.0, scale=0.1, size=100)
    b = rng.normal(loc=0.0, scale=0.1, size=100)
    res = paired_wilcoxon(a, b)
    assert res["p_value"] < 0.001
    assert res["mean_diff"] > 0.5


def test_prepare_features_replaces_sentinel_gap_with_chronological_id_minus_1():
    df = pd.DataFrame({"chronological_id": [1, 2, 3], "gap_current": [-1, 5, -1]})
    out = prepare_features(df)
    np.testing.assert_array_equal(out["gap_current_adjusted"], [0, 5, 2])
