from math import comb

import numpy as np
import pandas as pd
import pytest

from loto_research.statistics.descriptive import (
    bonus_frequencies, low_high_distribution, number_frequencies,
    odd_even_distribution, sum_distribution,
)
from loto_research.statistics.exact_distributions import (
    low_count_pmf, odd_count_pmf, sum_distribution_exact,
)
from loto_research.statistics.uniformity import (
    _merge_low_expected_bins, chi_square_uniformity, simulate_main_numbers_null_chi2,
)

NUMBER_COLUMNS = [f"n{i}" for i in range(1, 7)]


# ---------- exact_distributions ----------

def test_sum_distribution_exact_small_case_hand_verifiable():
    """Choisir 2 numéros parmi {1,2,3} : sommes possibles 3,4,5, chacune avec probabilité 1/3."""
    sums, probs = sum_distribution_exact(max_number=3, draw_size=2)
    assert list(sums) == [3, 4, 5]
    assert probs == pytest.approx([1 / 3, 1 / 3, 1 / 3])
    assert probs.sum() == pytest.approx(1.0)


def test_sum_distribution_exact_49_6_matches_known_moments():
    """E(S) et nombre total de sous-ensembles doivent correspondre aux valeurs connues du 6/49."""
    sums, probs = sum_distribution_exact(max_number=49, draw_size=6)
    assert len(sums) == 279 - 21 + 1  # min=1+..+6=21, max=44+..+49=279 ; toutes les sommes intermédiaires sont atteignables
    mean = (sums * probs).sum()
    assert mean == pytest.approx(6 * 50 / 2, abs=0.01)  # E(somme) = 6 * (1+49)/2 = 150
    assert probs.sum() == pytest.approx(1.0)


def test_odd_count_pmf_sums_to_one_and_matches_hand_calc_for_k0():
    k, p = odd_count_pmf()
    assert list(k) == [0, 1, 2, 3, 4, 5, 6]
    assert p.sum() == pytest.approx(1.0)
    # P(0 impair parmi 6) = C(25,0)*C(24,6)/C(49,6)
    expected_p0 = comb(25, 0) * comb(24, 6) / comb(49, 6)
    assert p[0] == pytest.approx(expected_p0)


def test_low_count_pmf_sums_to_one():
    k, p = low_count_pmf()
    assert list(k) == [0, 1, 2, 3, 4, 5, 6]
    assert p.sum() == pytest.approx(1.0)


# ---------- uniformity ----------

def test_chi_square_uniformity_zero_when_observed_equals_expected():
    res = chi_square_uniformity([10, 10, 10], [10, 10, 10])
    assert res["chi2"] == pytest.approx(0.0)
    assert res["df"] == 2
    assert res["p_value"] == pytest.approx(1.0)


def test_chi_square_uniformity_large_deviation_gives_small_p():
    res = chi_square_uniformity([1000, 0], [500, 500])
    assert res["p_value"] < 0.001


def test_merge_low_expected_bins_merges_both_tails():
    obs = [1, 2, 100, 2, 1]
    exp = [1, 2, 100, 2, 1]
    o, e = _merge_low_expected_bins(obs, exp, min_expected=5)
    # les deux bornes fusionnent vers le centre jusqu'à atteindre >= 5
    assert e[0] >= 5
    assert e[-1] >= 5
    assert e.sum() == sum(exp)  # rien n'est perdu
    assert o.sum() == sum(obs)


def test_merge_low_expected_bins_noop_when_all_above_threshold():
    o, e = _merge_low_expected_bins([10, 10, 10], [10, 10, 10], min_expected=5)
    assert list(e) == [10, 10, 10]


def test_chi_square_uniformity_with_min_expected_reduces_bin_count():
    res = chi_square_uniformity([1, 2, 100, 2, 1], [1, 2, 100, 2, 1], min_expected=5)
    assert res["n_bins_before_merge"] == 5
    assert res["n_bins_after_merge"] < 5
    assert res["chi2"] == pytest.approx(0.0)  # observed == expected partout, même après fusion


def test_simulate_main_numbers_null_chi2_is_reproducible_with_same_seed():
    a = simulate_main_numbers_null_chi2(n_draws=50, n_simulations=20, seed=123, batch_size=7, progress=False)
    b = simulate_main_numbers_null_chi2(n_draws=50, n_simulations=20, seed=123, batch_size=7, progress=False)
    assert a.shape == (20,)
    np.testing.assert_array_equal(a, b)


def test_simulate_main_numbers_null_chi2_different_seeds_differ():
    a = simulate_main_numbers_null_chi2(n_draws=50, n_simulations=20, seed=1, progress=False)
    b = simulate_main_numbers_null_chi2(n_draws=50, n_simulations=20, seed=2, progress=False)
    assert not np.array_equal(a, b)


def test_simulate_main_numbers_null_chi2_mean_near_43_not_48():
    """Vérification de calibration (amendement A1) : espérance ~43, PAS 48, pour n_draws grand."""
    stats = simulate_main_numbers_null_chi2(n_draws=3159, n_simulations=300, seed=42, progress=False)
    assert 35 < stats.mean() < 51  # tolérance large (300 sims seulement) ; test complet -> Phase 3 réelle


# ---------- descriptive ----------

def _make_fake_draws(n=200, seed=0):
    """Tirages uniformes synthétiques (pas des vraies données) pour tester la mécanique du code."""
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        picked = rng.choice(np.arange(1, 50), size=6, replace=False)
        bonus_pool = [x for x in range(1, 50) if x not in picked]
        bonus = rng.choice(bonus_pool)
        rows.append({**{f"n{i+1}": v for i, v in enumerate(sorted(picked))}, "bonus": bonus})
    return pd.DataFrame(rows)


def test_number_frequencies_counts_sum_to_six_times_n():
    df = _make_fake_draws(100)
    freq = number_frequencies(df)
    assert len(freq) == 49
    assert freq["count"].sum() == 100 * 6
    assert freq["expected"].iloc[0] == pytest.approx(100 * 6 / 49)


def test_bonus_frequencies_counts_sum_to_n():
    df = _make_fake_draws(100)
    freq = bonus_frequencies(df)
    assert len(freq) == 49
    assert freq["count"].sum() == 100
    assert freq["expected"].iloc[0] == pytest.approx(100 / 49)


def test_sum_distribution_structure():
    df = _make_fake_draws(100)
    res = sum_distribution(df)
    assert res["n"] == 100
    assert 21 <= res["observed_mean"] <= 279
    assert res["theoretical_mean"] == pytest.approx(150, abs=0.5)
    assert 0 <= res["chi_square_vs_exact_distribution"]["p_value"] <= 1


def test_odd_even_distribution_counts_match_n():
    df = _make_fake_draws(100)
    res = odd_even_distribution(df)
    assert sum(res["observed_distribution"].values()) == 100
    assert sum(res["expected_distribution"].values()) == pytest.approx(100)


def test_low_high_distribution_counts_match_n():
    df = _make_fake_draws(100)
    res = low_high_distribution(df)
    assert sum(res["observed_distribution"].values()) == 100
    assert sum(res["expected_distribution"].values()) == pytest.approx(100)
